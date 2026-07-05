# APV3.0 草稿内省感受 + 表达范式共现学习 — 落地实现稿 v3.1

日期: 2026-06-17
作者: 接手线程
状态: **路径 C 整合产物。v3 设计稿 + 6 blocker + 12 serious 全部修正,Codex 拿到本文档即可开工 Phase 7.3b → 7.3f。**
配套基础: v3 设计稿 `Design_APV3.0_DraftIntrospection_ExpressionLearning_v3_20260616.md`
审阅源: v3 自审报告(2026-06-17,task wzf3wsy89,30 raw / 22 verified)

---

## 0. 本文档怎么读

**这不是新设计** —— 是 v3 设计稿的"实施修正层"。Codex 实现时:

1. **底层数学/架构**:遵循 v3 设计稿(§1-§7)
2. **每条具体实现**:遵循本文档 §1-§3 列出的修正(优先级高于 v3)
3. **每条修正都有定位 + 失败场景 + AP-native 修法**,不许糊弄

## 路径 C 的决定逻辑(必读)

v1 → v2 → v3 三轮对抗审阅后,**仍能找到 6 个 blocker**。这不是 v3 不行——是任何复杂数学模型在落地前总能找出角落 case。无限审阅会发散不收敛。

所以:**v3.1 是设计稿的最后一个版本。落地后用真实运行 trace 验证哪些是真问题,而不是再审一轮**。

---

## 1. 必须修正的 BLOCKER(6 条,落地时一条都不许漏)

### B1 — 衰减公式的"超指数塌陷"陷阱(`** age` 必须删掉)

**位置**: v3 §1.2.4 + §2.2 `decay_unactivated` + §1.4.2 `update_energy_per_tick`

**问题**: v3 写的 `p.activation_ema *= half_life_decay ** age`,其中 `age = current_tick - last_activated_tick`,而 decay_unactivated **每 tick 跑一次**。对一个空闲 N tick 的 prototype,实际乘数是 `decay^(1+2+...+N) = decay^(N(N+1)/2)`,**不是** `decay^N`。

实测:`half_life_decay=0.99, age=100`,intended `0.99^100 ≈ 0.366`,actual `0.99^5050 ≈ 1.6e-22`。任何空闲 ~30 tick 的 prototype 会被瞬间归零,**eviction_floor 这个旋钮形同虚设**。

**必须修正**:删掉 `** age`,改成每 tick 一次单步乘法。

```python
# 错的(v3 当前):
def decay_unactivated(self, current_tick: int):
    for p in self.prototypes:
        age = current_tick - p.last_activated_tick
        p.activation_ema *= self.config.half_life_decay ** age  # ❌ 超指数

# 对的(v3.1 必须改成):
def decay_unactivated(self, current_tick: int):
    for p in self.prototypes:
        if p.last_activated_tick == current_tick:
            continue  # 本 tick 刚激活,跳过
        p.activation_ema *= self.config.half_life_decay  # ✅ 每 tick 单步
    self.prototypes = [p for p in self.prototypes
                       if p.activation_ema > self.config.eviction_floor]
    if len(self.prototypes) > self.config.max_prototypes:
        self.prototypes.sort(key=lambda p: -p.activation_ema)
        self.prototypes = self.prototypes[:self.config.max_prototypes]
```

同样的修正应用到 **`§1.4.2` 所有 pressure SA 的 `update_energy_per_tick`**:删 `age` 参数和 `** age`,签名改为 `update_energy_per_tick(self)`,每 tick 单步乘衰减。

**新 config 语义**:`half_life_decay` 是**每 tick 留存因子** ∈ (0,1)。如果想要半衰期 H ticks,设 `half_life_decay = 0.5**(1/H)`。

**新增验收测试 §4.10b**(替换 v3 当前 §4.10 不充分的版本):

```python
def test_prototype_decay_is_true_half_life():
    store, _ = bootstrap_empty()
    phi = make_phi_at_position([0.5]*7)
    p, _ = store.respond_or_spawn(phi, current_tick=0)
    H = int(round(math.log(0.5) / math.log(store.config.half_life_decay)))
    for t in range(1, H+1):
        store.decay_unactivated(current_tick=t)
    assert 0.45 < p.activation_ema < 0.55, f"after H ticks expected ~0.5, got {p.activation_ema}"
    for t in range(H+1, 2*H+1):
        store.decay_unactivated(current_tick=t)
    assert 0.20 < p.activation_ema < 0.30
```

---

### B2 — Warm-load 的 prototype_id 重用陷阱

**位置**: v3 §1.2.5 / §2.2 `warm_load`

**问题**: warm_load 用 `max(p.id, default=-1) + 1` 算 next_id,但如果 aggressive_decay 把 prototypes 全清空,SQLite 里 `prototypes=[]`,next_id 退回 0。而 **CooccurrenceAssociationStore 里还有 `feeling::draft::proto_0` 的活关联**(它的衰减比 prototype 慢),**新 spawn 的 proto_0 会继承死亡 proto_0 的关联记忆**。

**必须修正**:两个改动一起做,缺一不可。

#### B2-Fix-1:把 `next_id` 持久化为 first-class 字段

```python
def export_state(self) -> dict:
    return {
        "prototypes": [p.to_dict() for p in self.prototypes],
        "next_id": self._next_id,        # NEW: 一等持久化字段
        "schema_version": 2,
    }

def warm_load(self, persisted: dict):
    self.prototypes = [Prototype.from_dict(row) for row in persisted.get("prototypes", [])]
    if "next_id" in persisted:
        self._next_id = persisted["next_id"]
    else:
        # 旧 schema fallback:扫 assoc store 找最大 proto_id
        live_max = max((p.id for p in self.prototypes), default=-1)
        assoc_max = self._scan_assoc_store_for_max_proto_id()
        self._next_id = max(live_max, assoc_max) + 1
```

#### B2-Fix-2:Prototype 驱逐 + Assoc 关联原子退役

`decay_unactivated` 必须接受 `association_store` 句柄,**驱逐 prototype 时同步删它名下的所有 assoc 关联**:

```python
def decay_unactivated(self, current_tick: int, association_store):
    for p in self.prototypes:
        if p.last_activated_tick == current_tick:
            continue
        p.activation_ema *= self.config.half_life_decay
    live_ids = {p.id for p in self.prototypes if p.activation_ema > self.config.eviction_floor}
    evicted_labels = {make_feeling_label(p.id) for p in self.prototypes
                      if p.id not in live_ids}
    self.prototypes = [p for p in self.prototypes if p.id in live_ids]
    # max_prototypes 软上限
    if len(self.prototypes) > self.config.max_prototypes:
        self.prototypes.sort(key=lambda p: -p.activation_ema)
        evicted_labels.update(
            make_feeling_label(p.id) for p in self.prototypes[self.config.max_prototypes:]
        )
        self.prototypes = self.prototypes[:self.config.max_prototypes]
    # 原子 retire
    for lab in evicted_labels:
        association_store.retire_label(lab, current_tick)
```

在 `CooccurrenceAssociationStore` 里加:

```python
def retire_label(self, key_a: str, current_tick: int) -> None:
    """原子删除 key_a 下所有 pair。"""
    for key_b in list(self._by_a.get(key_a, ())):
        self._pairs.pop((key_a, key_b), None)
        self._by_b[key_b].discard(key_a)
    self._by_a.pop(key_a, None)
```

---

### B3 — CooccurrenceAssociationStore 的 SQLite 契约必须 normative,不是 stub

**位置**: v3 §1.3.1 `export_to_sqlite` / `import_from_sqlite`(目前是 `...` 空体)

**必须做**:

#### B3-Fix-1:Normative DDL

```sql
CREATE TABLE cooccurrence_assoc (
    key_a              TEXT    NOT NULL,
    key_b              TEXT    NOT NULL,
    cumulative_weight  REAL    NOT NULL,
    last_update_tick   INTEGER NOT NULL,
    update_count       INTEGER NOT NULL,
    PRIMARY KEY (key_a, key_b)
);
CREATE INDEX idx_assoc_by_a ON cooccurrence_assoc(key_a);
CREATE INDEX idx_assoc_by_b ON cooccurrence_assoc(key_b);

CREATE TABLE cooccurrence_meta (
    schema_version INTEGER NOT NULL
);
```

#### B3-Fix-2:Import 语义契约(必须按字面实现)

- (a) 保留 `last_update_tick` 原值,**严禁 re-anchor 到 `current_tick`**(那会重置衰减年龄,假延长记忆)。
- (b) 用 `half_life_decay ** (current_tick - last_update_tick)` 算衰减权重,**< eviction_floor 的行直接丢弃**(匹配活跃 eviction 策略)。
- (c) `_by_a / _by_b` 单 pass 重建,按 `(key_a, key_b)` 字典序确定性插入。
- (d) **幂等性**:同 `(conn, current_tick)` 重复 import 必须产生 bit-identical 状态。

#### B3-Fix-3:Export 语义

- (a) `INSERT OR REPLACE` 写原始 `cumulative_weight` 与 `last_update_tick`,**不预衰减**。衰减只在 read 路径应用,绝不烘焙进存储。
- (b) 可在任意 tick 中点调用,无需先 lazy-decay。

#### B3-Fix-4:Warm-load parity 验收(§4.11 新增)

```python
def test_cooccurrence_store_warmload_parity():
    cfg = AssocConfig(half_life_decay=0.99, eviction_floor=1e-6)
    store = CooccurrenceAssociationStore(cfg)
    store.observe("feeling::draft::proto_1", "expr::a", weight=0.7, current_tick=10)
    store.observe("feeling::draft::proto_1", "expr::b", weight=0.3, current_tick=20)
    store.observe("feeling::draft::proto_2", "expr::a", weight=0.5, current_tick=15)

    query_tick = 100
    sims_before = {
        ("feeling::draft::proto_1", "expr::a"):
            store.similarity("feeling::draft::proto_1", "expr::a", query_tick),
        ("feeling::draft::proto_1", "expr::b"):
            store.similarity("feeling::draft::proto_1", "expr::b", query_tick),
        ("feeling::draft::proto_2", "expr::a"):
            store.similarity("feeling::draft::proto_2", "expr::a", query_tick),
    }
    fanout_before = sorted(store.nearest_by_label(["feeling::draft::proto_1"], top_k=5, current_tick=query_tick))

    conn = sqlite3.connect(":memory:")
    store.export_to_sqlite(conn)
    del store

    reloaded = CooccurrenceAssociationStore(cfg)
    reloaded.import_from_sqlite(conn, current_tick=query_tick)

    for (a, b), expected in sims_before.items():
        assert abs(reloaded.similarity(a, b, query_tick) - expected) < 1e-9
    assert sorted(reloaded.nearest_by_label(["feeling::draft::proto_1"], top_k=5, current_tick=query_tick)) == fanout_before
```

加 §4.11b/c 两个边界测试(sub-floor 丢弃 / 不 re-anchor tick),完整代码见 v3 自审 task wzf3wsy89 line 40。

---

### B4 — SilenceSA 是单调增不衰减,违反 G9

**位置**: v3 §1.4.2 SilenceSA.update_energy_per_tick

**问题**:
```python
self.real_energy = min(1.0, age / config.silence_normalizer)  # ❌ 单调爬升
```
**永不衰减且永不重置**。一旦沉默 `silence_normalizer` ticks 以上,real_energy 被钉死在 1.0,**即使后来 commit 成功也回不去**。reply_pressure 永久高位,系统进入"必须回复但没什么可说"的死循环。

**必须修正**:reset-on-commit + bounded-ramp + post-saturation-decay。

```python
class SilenceSA(SA):
    sa_type = "silence"
    def update_energy_per_tick(self, state, current_tick):
        elapsed = current_tick - state.last_commit_tick
        ramp = min(1.0, elapsed / config.silence_normalizer)
        decay = config.silence_half_life_decay ** max(0, elapsed - config.silence_normalizer)
        self.real_energy = ramp * decay

    @classmethod
    def on_commit(cls, state, current_tick):
        """任何 commit 必须清零 silence,并刷新 last_commit_tick。"""
        state.last_commit_tick = current_tick
        for sa in state.state_field_items:
            if sa.sa_type == "silence":
                sa.real_energy = 0.0
```

**必须新增验收测试**:

```python
def test_silence_sa_resets_on_commit():
    state, _ = bootstrap_empty()
    for _ in range(2 * config.silence_normalizer):
        state = tick_with_introspection(state, TickInput())
    silence_before = next(sa for sa in state["state_field_items"]
                          if sa["sa_type"] == "silence")["real_energy"]
    assert silence_before > 0.9
    state = tick_with_introspection(state, TickInput(commit_happened=True))
    silence_after = next((sa for sa in state["state_field_items"]
                          if sa["sa_type"] == "silence"), None)
    assert silence_after is None or silence_after["real_energy"] < 0.05

def test_silence_sa_decays_after_saturation():
    state, _ = bootstrap_empty()
    for _ in range(10 * config.silence_normalizer):
        state = tick_with_introspection(state, TickInput())
    silence_long = next(sa for sa in state["state_field_items"]
                        if sa["sa_type"] == "silence")["real_energy"]
    assert silence_long < 0.3, "even without commit, must decay after saturation"
```

---

### B5 — `find_by_cue_token` 未定义 ⇒ 走 Codex B4 的老坑

**位置**: v3 §1.4.1 line 310 `paradigm_directory.find_by_cue_token(token)`

**问题**: `paradigm_directory` 在 v3 整个文档里**只是注释 `# 普通范式索引`**,**没有定义、没有 schema、没有 SQLite parity、没有 warm-load 语义**。两种实现路径都出问题:

- (a) Codex 把它实现成线性扫所有 paradigm:O(|paradigms| × |cue_tokens|),Stage 1 的 K_fast 裁剪被废
- (b) Codex 偷偷加一个新 ParadigmCueIndex 模块,Phase 7.3e 变成"接两 store"+"建反向索引带 SQLite parity"的 scope creep

**这正是 Codex B4 原本拒绝的同样模式:引用了不存在的接口**。

**必须修正**(采纳 fix (a),少代码量):**消除 paradigm_directory.find_by_cue_token 这一步,改让 CooccurrenceAssociationStore 直接维护 `(feeling_label, paradigm_id)` 聚合**。

```python
def recall_expression_paradigms_for_feelings(
    feelings: Sequence[FeelingSA],
    paradigm_store,                              # 既有
    association_store: CooccurrenceAssociationStore,
    current_tick: int,
    config,
) -> list[tuple[ParadigmSA, float]]:
    feeling_labels = [f.sa_label for f in feelings]
    # Stage 1: 直接拿到候选 paradigm_id(不绕道 cue_token)
    candidate_paradigm_ids = association_store.nearest_paradigms_by_label(
        feeling_labels, top_k=config.K_fast, current_tick=current_tick
    )
    # Stage 2: 精排
    scored = []
    for pid in candidate_paradigm_ids:
        p = paradigm_store.lookup(pid)
        if not p:
            continue
        total = sum(
            f.real_energy * association_store.similarity_paradigm(
                f.sa_label, pid, current_tick
            )
            for f in feelings
        )
        if total > 0:
            scored.append((p, total))
    scored.sort(key=lambda x: -x[1])
    return scored
```

CooccurrenceAssociationStore 加两个方法 `nearest_paradigms_by_label / similarity_paradigm`:**观察时,如果外部 token 恰好是某 paradigm 的 cue_token,则同步累加到 `(feeling_label, paradigm_id)` 聚合表**。schema 里加一张 `cooccurrence_assoc_by_paradigm` 表(同样的 DDL 模式,key_b 改成 paradigm_id),warm-load 走同样契约。

---

### B6 — φ_6 的 pooling 规则未定义,会跨版本几何漂移

**位置**: v3 §1.1(沿用 v2 §1.1.2 φ_6 `recent_punishment_resemblance`)

**问题**: φ_6 = `cos(draft_vector, recent_punished_commit_vector)`,但 draft 是 token 序列、commit 是 token 序列,**怎么变成向量(sum / mean / last / attention-pooled)从未定义**。不同选择给不同 φ_6,不同 prototype 几何,不同 feeling labels。

**更严重**:v3 §1.2.5 的 prototype_id 是 spawn 时分配并持久化的——如果未来实现者改了 pooling 规则,μ[5] 还在但**度量的已是另一个量**,而 prototype_id 仍合法。**B3 防的是 id 漂移,这里漏防几何漂移**。

**必须修正**:

#### B6-Fix-1:在 §1.1.2 给精确公式

```python
def draft_to_vec(views: Sequence[DraftSAEnergyView]) -> np.ndarray:
    """attention-weighted pooling over filled positions."""
    vecs = []
    weights = []
    for v in views:
        if v.is_filled:                            # 注意:用 is_filled 而非 .filler
            vecs.append(token_vec_for_view(v))     # 从 OnlineEmbeddingStore 取
            weights.append(v.attention_or_occupancy)
    if not vecs:
        return np.zeros(token_vec_dim)             # degenerate-case
    return normalize(np.average(vecs, axis=0, weights=weights))

def commit_to_vec(commit) -> np.ndarray:
    """token-level pooling weighted by commit-time real_energy."""
    ...
```

#### B6-Fix-2:Schema versioning

config 加 `phi_pooling_schema_version: str`(如 `"phi6.draft_to_vec.v1"`)。**持久化每个 prototype 时记录当时的 schema_version**。warm_load 时如果当前代码版本和持久化版本不匹配:

- 选项 A:抛异常,refuse warm-load
- 选项 B(推荐):无效化 μ[5]/τ[5],从下一次观测重新种子(其他维度保留)

#### B6-Fix-3:验收测试

```python
def test_phi_pooling_schema_version_guard():
    # 用 schema v1 持久化
    store = IntrospectionPrototypeStore(config_v1)
    store.respond_or_spawn(phi, current_tick=0)
    persisted = store.export_state()
    persisted["phi_pooling_schema_version"] = "phi6.draft_to_vec.v1"

    # 用 v2 加载(模拟代码升级)
    store_v2 = IntrospectionPrototypeStore(config_v2)  # config 现在是 v2
    store_v2.warm_load(persisted)
    # 必须 refuse 或 invalidate,绝不能静默使用旧 μ[5]
    assert store_v2.prototypes[0].mu[5] == 0.0  # B 路径: invalidated
    # 或:
    # with pytest.raises(SchemaVersionMismatch): store_v2.warm_load(persisted)
```

---

## 2. 必须修正的 SERIOUS(12 条精简版)

### S1 — 内省 feeling SA 必须进**子池**,不进 state_field_items 共享池

**位置**: v3 §7.3b + §2.3 `state.setdefault("state_field_items", []).append(feeling.to_dict())`

**修正**:Phase 7.3b 写到 `state["introspection_feelings"]` **子池**;reply_pressure 写到 `state["introspection_pressure"]`。这样 Phase 7.0/7.1 看不到新条目,容量/驱逐策略不被扰动。Phase 7.3e 接 expression recall 时,显式从两个池 union 读,不要悄悄 merge。

加回归测试:
```python
def test_7_3b_does_not_evict_existing_state_field_items():
    state_before = run_phase_7_0_7_1_workload()
    baseline_items = list(state_before["state_field_items"])
    state_after = run_with_7_3b_introspection(state_before)
    for sa in baseline_items:
        assert sa in state_after["state_field_items"]
```

### S2 — Attention 来源必须明确(或诚实 defer)

**位置**: v3 §1.3.2 + §4.9

**选项 A(推荐)**:在 §1.3.2 给 attention_weight 的具体公式:
```
attention_weight(e) = softmax_over_tick_external_tokens( s(e) )
s(e) = w_focus * focus_overlap(e.segment_id, active_focus_segments)
     + w_salience * salience_SA_energy_at(e.segment_id)
     + w_recency * recency_kernel(e.segment_id)
     - w_background * background_density(e.segment_id)
```
所有 w_* 是 tuner-owned,从 state_field_items 已有 SA 取信号。同时**§4.9 改成喂 raw token,attention 由 ingest 自己算**——不许测试硬塞 0.9/0.1。

**选项 B(老实 defer)**:`attention_weight` 在 ExternalExpressionToken 上加 `# DEFERRED to 7.3c-attention-extension`,§4.9 改成单元测试乘法律,**§0.3 G7 状态改成 DEFERRED**(像 §4.5b 那样)。

如果不能给出选项 A 的具体公式,**必须走选项 B,不许糊弄**。

### S3 — 共现学习的"噪声拒斥"测试必须真正测时间规律性,而非 attention 乘数

**位置**: v3 §4.9

**修正**:保留 §4.9 做 attention 乘数 sanity 检查,**新增 §4.9b 真 S3 acceptance**——target 和 distractor 都用 attention=0.5,但 target 与 feeling_a 时间规律共现,distractor 在 feeling_a/feeling_b 间随机翻。代码见 task wzf3wsy89 line 70。

### S4 — Compact 共现 store,与 prototype 驱逐对称

**位置**: v3 §1.3.1 CooccurrenceAssociationStore

**修正**:加 `compact(current_tick)` 方法,sub-`eviction_floor` 的 pair 全部 evict 含正反向索引;在 §2.7 tick 主循环按 `assoc_compact_every_n_ticks` 周期触发;在 `observe` 末尾对**当前 key_a 的 bucket** 做 opportunistic ejection(O(bucket size) 不是 O(全表))。

### S5 — Label-bijection 必须用 property test,不是 7 surface 枚举

**位置**: v3 §4.6.5

**修正**:把 §4.6.5 改造成 property-based 测试:两个 runtime 用不同 minter 跑同样输入,所有内部 opaque label 在两端 minter 下产生不同字面值;每 tick 对比所有 label-bearing 路径(state_field_items[*].sa_label / provenance[*].sa_label / association_store keys / cue_tokens 出现的 internal label),用 inverse bijection 必须匹配;外部 commit_text_log / recalled_paradigm_id_log / commit_pressure_log 必须 byte-identical(无 bijection 应用)。代码见 task wzf3wsy89 line 60。

同时:**删掉 `FeelingSA.prototype_id` 这个字段**(只留 `sa_label`),否则它是绕过 bijection 的并行通道。

### S6 — `pressure_type_weights` 改为 `sa_kind` 结构属性

**位置**: v3 §1.4.2

**修正**:取消 sa_type → weight 的开放清单(易退化为策略表)。改成 SA 自带 `sa_kind ∈ {external_demand, social_presence, internal_unfinished, recent_action, temporal_idleness}` 结构属性,reply_pressure 用固定结构规则 `Σ sign(sa_kind) × real_energy`。新增 sa_type 必须声明 sa_kind 才能进 pressure,sign 不由它自己定。

### S7 — `_update_prototype` τ 更新顺序错(导致 τ 系统性低估)

**位置**: v3 §2.2 `_update_prototype` 先更 μ 再算 residual

**修正**:**交换顺序**——先用旧 μ 算 residual,再更 μ。

```python
def _update_prototype(self, p, phi, r, current_tick):
    eta = self.config.eta_mu * r
    # τ 先(用旧 μ)
    residual_sq = (phi - p.mu) ** 2
    p.tau = np.sqrt((1 - eta) * p.tau ** 2 + eta * residual_sq)
    p.tau = np.maximum(p.tau, self.config.tau_floor)
    # μ 后
    p.mu = (1 - eta) * p.mu + eta * phi
    p.activation_ema = p.activation_ema * self.config.activation_decay + r
    p.last_activated_tick = current_tick
```

### S8 — DraftSAEnergyView 必须删 `filler` 字段(它是内容)

**位置**: v3 §1.1.1 Protocol + §4.6.4 forbidden patterns

**修正**:
- 从 Protocol 删 `filler: str | None`,加 `is_filled: bool`
- §4.6.4 forbidden list 加:`.filler`, `.value`, `.cue`, `.label`, `.sa_label`, `.anchor_meta`, `.meta`, `.attrs`, `__dict__`
- §4.6.4 测试从 regex 升级为 AST sweep(whitelist 模式):只允许读 `{fit_margin, occupancy, commit_readiness, role, is_filled}`,禁用所有其他 Attribute/Subscript/getattr/Compare-with-string-literal 模式

### S9 — `tick` 必须显式自增,§4.10 测试必须验等式

**位置**: v3 §2.7 + §4.10

**修正**:`tick_with_introspection` 末尾加 `state["tick"] = current_tick + 1`。§4.10 测试改成验闭式数学(`expected = initial * decay^age`),不再只验"SA 消失"。

### S10 — Phase 7.3d Phase 7.2 测试迁移路径必须列清

**位置**: v3 §7.3d

**修正**:加 7.3d.1 子节,显式说:
- Phase 7.0/7.1 测试不用 `must_reply`,grep 验证 0 hit,不会破
- Phase 7.2 的两个测试在 7.3d/7.3e 一并改写:把 `must_reply=True` 换成 `incoming_external_query="..."`,把 `undecidable_feeling_tokens=...` 删掉,改用 commit_blocked 结构事实

### S11 — provenance 字段不能暴露在 ReplyPressureSA 上,要走 out-of-band trace

**位置**: v3 §1.4.2 + §3 红线表

**修正**:`derive_reply_pressure_sa` 返回 `(ReplyPressureSA, trace_record)` 二元组,trace 给观测台,SA 本体只暴露 `real_energy / cognitive_pressure / sa_label / sa_type`。加 AST 扫描 `(reply_pressure|pressure)\.(provenance|sources|dominant_source)` 在运行时模块必须为空。

### S12 — `acceptance test` 全是 white-box,需要至少一条 end-to-end replay

**位置**: §4 全部测试

**修正**:加一条 §4.12 端到端回放测试:用一段真实对话日志(可手工构造,带 query/answer/silence/punishment 序列),让 7.3a-7.3f 全套跑完,断言"系统能学会某个表达 → 后续相同情境召回到它"。这是黑盒回归,防止白盒测试集体过但行为荒谬。

---

## 3. MINOR(7 条,落地时顺手改)

| ID | 位置 | 修正 |
|---|---|---|
| M1 | §4.6.4 AST 扫描 | 加 `.role.startswith` 等 startswith/endswith/__contains__ 禁用模式 |
| M2 | §4.9 `* 3` 魔数 | 改成 config 取 `test_target_distractor_ratio_min` |
| M3 | §1.2.4 `max_prototypes` | 文档说是"软上限"但代码是硬截断;统一表述,实现按"超时触发 aggressive decay" |
| M4 | §2.2 `activation_decay` 与 `half_life_decay` | 两个常数同方向作用,合并成一个 `combined_decay = h * activation_decay`,避免双旋钮 |
| M5 | §4.9 `first_feeling_label(state)` | 测试不许假定特定顺序;改成 ground-truth(用 driver_phi 反推 expected label) |
| M6 | §1.3.1 `_by_b` 反向索引 | v3 定义了但从未读;要么补 nearest_by_token 用法,要么删 |
| M7 | §5 Phase 7.3a-7.3f 依赖 | 加 rollback 故事:若 7.3c 共现 store 落地不顺,7.3d/e 可以怎么 fallback |

---

## 4. Codex 落地路线(7.3a → 7.3f,沿用 v3 §5,所有 blocker/serious 必须在对应 phase 修)

### 7.3a — 设计修订门(本文档即产物)
✅ 已完成。Codex 看本文档,如有疑问回头问。

### 7.3b — 内省原型 observer-only
**必须做的修正**:B1 衰减 / B2 next_id 持久化 + 退役耦合(虽然此 phase 还没接 assoc store,先把接口留好)/ B6 phi_6 pooling 公式 + schema_version / S1 子池隔离 / S7 τ 更新顺序 / S8 Protocol 改 is_filled / S9 tick 自增

**验收**:§4.1 + §4.7 + §4.8 + §4.10b(B1 半衰期等式)+ S1 回归测试 + S7 τ 收敛测试 + B6 schema version guard 测试 + Phase 7.0/7.1 完全不破

### 7.3c — 共现关联 store
**必须做的修正**:B3 SQLite normative DDL + import 契约 / B5 nearest_paradigms_by_label 直接接 paradigm 不绕 cue_token / S4 compact + 与 prototype 退役对称 / M6 _by_b 决断

**验收**:§4.2 + §4.7 + §4.9 + §4.9b(S3 噪声拒斥)+ §4.11(B3 warm-load parity)+ §4.11b/c

### 7.3d — reply_pressure SA
**必须做的修正**:B1 pressure SA 衰减 / B4 SilenceSA 重置 / S6 sa_kind 结构属性 / S10 Phase 7.2 测试迁移 / S11 provenance 外移

**验收**:§4.3 + §4.10(B4 commit 重置 + 饱和后衰减)+ Phase 7.0/7.1/7.2 全部相应迁移后通过

### 7.3e — expression recall + rebind
**必须做的修正**:B5 直接调 nearest_paradigms_by_label / 删 paradigm_fill_draft vs rebind_slots 区分如 v3 §2.7

**验收**:Phase 7.0/7.1 teacher-off 全部仍通过 + §4.12 端到端回放

### 7.3f — 红线与不变量
**必须做的修正**:S5 property-based bijection / S8 AST sweep whitelist / S11 AST 扫 provenance 引用 / M1 startswith 等模式

**验收**:三层红线全过 + §4.12 端到端

---

## 5. Codex 实施红线(看一眼必懂)

1. **不许偷工:任何 blocker/serious 没修就跑测试 = 自动 fail**
2. **不许糊弄:S2 不写 attention 公式就走 defer(老实标 DEFERRED),不许塞硬编码**
3. **不许测试串通:B5/§4.9b 用 driver_phi 反推 expected,不许硬编码 attention_weight**
4. **必须分 phase 落:7.3b 不许偷跑 7.3e 的代码,每 phase 都跑回归**
5. **回归不绿就回退**:Phase 7.0/7.1 任何一条挂了立即停,排查后再走

---

## 6. 写在最后

经 v1 → v2 → v3 三轮对抗 + 这次自审,我们做了能做的所有理论审查。**剩下的真问题只有让代码跑起来才能发现**。

如果 7.3b 落地后发现新问题,我们重新讨论;但**绝不再回头审 v3.1 设计稿,设计阶段到此结束**。

— 接手线程,2026-06-17
