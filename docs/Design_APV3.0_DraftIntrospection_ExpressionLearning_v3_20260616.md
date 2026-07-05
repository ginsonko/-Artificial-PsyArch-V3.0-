# APV3.0 草稿内省感受 + 表达范式共现学习 — 完整设计方案 v3(Codex 反向审阅后)

日期: 2026-06-16
作者: 接手线程
状态: **数学模型 + 伪代码完整,经 3 路对抗审阅(v1→v2)+ Codex 反向审阅(v2→v3),所有 blocker/serious 已整合。准备交 Codex Phase 7.3a 修订门审查 → 7.3b-7.3f 分步落地。**
配套: 与 `Design_APV3.0能量本体数学模型_20260615.md`(v3.0)、`Design_持久化中文对话底座_范式通道重构_v2_20260615.md`(v2.1)共同构成 APV3.0 的"输入-感受-表达"完整链路
前身: v1(2026-06-16,9 处真缺陷)→ v2(整合 9 条)→ v3(本稿,整合 Codex 反向审阅 12 条)

---

## v2 → v3 关键修正一览

| # | v2 缺陷(Codex 反向审阅坐实) | v3 修正方向 |
|---|---|---|
| B1+B2 | spawn 判定混合 softmax 响应度 + max_distance,前者矛盾后者写反 | **spawn 完全独立于 softmax**,只看 `min_distance > θ_spawn` 单一判据。softmax 永远软分配,不再用低响应度作 spawn 信号 |
| B3 | `stable_id(mu_f)` 依赖会漂移的 μ,导致 label 随经验更新而变 | **prototype_id 在 spawn 时一次性分配并持久化**,后续 μ/τ 更新都不动 id;warm-load 时从最大已用 id 推 next_id |
| B4 | v2 假设的 `observe_positive_pair / nearest_by_label` 在 APV3.0test 当前接口不存在 | **必须先建 `CooccurrenceAssociationStore` 最小模块**,作 Phase 7.3c 的独立工作产物,带 SQLite parity |
| B5 | label-bijection 测试作用域没说清,可能误报或漏报 | **bijection 只作用于内部 opaque feeling label**,精确列出必须一致重写的 7 处引用;外部表达 token 不重写 |
| S1 | pressure_type_weights 可能退化为"什么时候说什么"的策略表;且 pressure SA 必须衰减 | **pressure 只决定是否回复,绝不决定说什么**;v3 显式声明所有 pressure SA(silence/external_query/recent_commit)必须按 v3.0 §12.4 衰减 |
| S2 | DraftSAEnergyView 适配器可能藏 if text/if vision 模态捷径 | **adapter 红线扫描进 §4.6**;text-only adapter 显式 grep `d.token / d.case_name / d.display_text` 必须为空 |
| S3 | 同 tick 多 token(教师 + 干扰 + 上下文)同权重学进去,共现污染 | **token attention/segment 权重** + 必须的 distractor 验收(目标 token 增量显著高于干扰) |
| S4 | 一次性切到 rebind + 单 token/tick 会破坏 Phase 7.0/7.1 既有 echo/successor/multi-reply | **分 6 步落地**:7.3a 设计修订 → 7.3b 内省 observer-only → 7.3c 共现 store → 7.3d reply_pressure → 7.3e expression recall/rebind → 7.3f 红线 |
| S5 | max_prototypes / decay 标"未决"是错的 | **首批实现强制**:half_life_decay、eviction_floor、max_prototypes 软上限(超时触发 aggressive decay)进入 §1.2.4 必备机制 |
| S6 | teacher_reply 必须只作 provenance,不能让学生侧产生自然学不出的字段 | **§1.3.3 显式约束**:teacher_reply 与 perception_other 写入同构 evidence;association store schema 不含"LLM said so"路由字段 |
| B1 误读 | Codex 把"远离触发 spawn"误读成 softmax 矛盾 | v3 把 spawn 判据与 softmax 响应度**显式解耦**,文档强调两者独立 |

---

## 0. 问题陈述与设计目标(沿用 v2)

### 0.1 用户哲学要求

> "我们人类更多的是先产生了一些内在的感受和表达倾向,然后后来根据这些来选取的表达范式来进行语言组织的。"

### 0.2 当前缺口

Phase 7.2 把 `feeling::undecidable` 字符串写死、`must_reply` bool 外塞、用 cue=feeling 教 reply=expression 的直接配对。

### 0.3 设计目标 G1-G6(沿用 v2)+ 新增 v3 验收

| # | 目标 | 验收依据 v3 |
|---|---|---|
| G1 | feeling label 自动派生不由外部约定 | §4.6 三层语义扫描 + 精确 bijection scope |
| G2 | 同一机制涌现任意内省感受 | 加新原型不需新代码 |
| G3 | 表达关联完全由共现学习 | §4.2 相对增量 + distractor 区分 |
| G4 | 回复压力从状态池 SA 涌现 | ingest 注入 + pressure SA 显式衰减 |
| G5 | 没学过就不该有表达 | bootstrap_truly_empty + 负例 |
| G6 | 红线干净 | AST + bijection + 内联禁止 + adapter 内容捷径扫描 |
| **G7(新)** | 共现学习能区分目标 vs 干扰 | §4.2 distractor 增长显著低于目标 |
| **G8(新)** | prototype id 持久稳定 | §4.7 spawn 后 μ 更新 100 次,id 不变 |
| **G9(新)** | 所有 pressure SA 按 §12.4 半衰期衰减 | §4.10 silence/query SA 长期 ema 测试 |

---

## 1. 完整数学模型 v3

### 1.1 草稿结构特征空间(沿用 v2,模态适配)

`DraftSAEnergyView` Protocol 沿用 v2 §1.1.1,7 个特征 φ_1..φ_7 沿用 v2 §1.1.2。

**v3 新增 §4.6 adapter 红线扫描**:text adapter 实现里 `grep -rn "v.token\|v.case_name\|v.display_text\|v.role.startswith" modality_adapters.py` 必须为空——adapter 只能读输入 SA 的**数值能量信息**,不能读 token 字面。

### 1.2 涌现 feeling SA 的机制(v3 核心:spawn 与 softmax 解耦)

#### 1.2.1 内省原型集合(沿用 v2 框架)

维护 $\Phi$-空间(7 维)原型集合 $M = \{\mu_1, ..., \mu_K\}$,每个原型有:
- `id`: spawn 时一次性分配的稳定 id(v3 修正 B3)
- `mu`: $\mathbb{R}^7$ 中的位置,随经验更新
- `tau`: 逐坐标尺度,EMA 残差平方更新
- `activation_ema`: 激活频率指数移动平均
- `last_activated_tick`: 用于衰减

#### 1.2.2 软响应度 r_f(φ)(沿用 v2 §1.2.2)

$$
r_f(\phi) = \frac{\exp\left(-\sum_i (\phi_i - \mu_{f,i})^2 / (2\tau_{f,i}^2)\right)}{\sum_{g \in M} \exp\left(-\sum_i (\phi_i - \mu_{g,i})^2 / (2\tau_{g,i}^2)\right)}
$$

性质:$r_f \in (0, 1)$,$\sum_f r_f = 1$,平滑跨原型。

#### 1.2.3 spawn 判据(v3 核心修正,完全独立于响应度)

**v2 错处**:同时用 `best_r < floor` 和 `max_distance > threshold` 两个条件,前者与 softmax 矛盾(Codex B1),后者写错方向(Codex B2)。

**v3 解法**:**spawn 判据完全独立于 softmax 响应度,只看白化最小距离**。

$$
d_{min}(\phi) = \min_{f \in M} \sqrt{\sum_i (\phi_i - \mu_{f,i})^2 / \tau_{f,i}^2}
$$

**Spawn 条件**:
$$
M = \emptyset \quad \lor \quad d_{min}(\phi) > \theta_{spawn}
$$

第一个条件处理冷启动(空集合)。$\theta_{spawn}$ 是 tuner-owned 配置项。

**注意**:这是"够远就孵化",不是"响应度低就孵化"。两者在数学上独立:
- 响应度软分配给所有现有原型(softmax 性质,总和 = 1)
- spawn 由 novelty 距离决定,不读响应度
- 只有 1 个原型时 r = 1(softmax 性质,正确),但若 φ 离它够远,仍然 spawn(novelty 性质)

#### 1.2.4 衰减/驱逐(v3 强制纳入,不再是"未决问题")

**v2 错处**:§6 标"未决"是错的(Codex S5)。

**v3**:每 tick 主动衰减,不依赖访问触发(避免 stale freq):
```python
for p in store.prototypes:
    age = current_tick - p.last_activated_tick
    p.activation_ema *= config.half_life_decay ** age
# 驱逐
store.prototypes = [p for p in store.prototypes
                    if p.activation_ema > config.eviction_floor]
# 软上限保护
if len(store.prototypes) > config.max_prototypes:
    # 触发 aggressive decay(把 half_life 缩短一半再衰减一次)
    aggressive_decay_pass(store, config)
```

`half_life_decay`, `eviction_floor`, `max_prototypes`, `aggressive_decay_factor` 全部 tuner-owned。

#### 1.2.5 prototype_id 持久稳定(v3 修正 B3)

```python
class IntrospectionPrototypeStore:
    def __init__(self, config):
        self.prototypes: list[Prototype] = []
        self._next_id = 0  # spawn 单调自增

    def respond_or_spawn(self, phi, current_tick):
        if not self.prototypes:
            return self._spawn(phi, current_tick)
        d_min = min(self._whitened_distance(phi, p) for p in self.prototypes)
        if d_min > self.config.theta_spawn:
            return self._spawn(phi, current_tick)
        # 否则 softmax 软分配,best 原型作为代表
        responsibilities = self._softmax_responsibilities(phi)
        # 所有原型按 r 更新 μ/τ
        for p, r in responsibilities.items():
            self._update_prototype(p, phi, r)
        best_p = max(responsibilities, key=responsibilities.get)
        return best_p, responsibilities[best_p]

    def _spawn(self, phi, current_tick) -> tuple[Prototype, float]:
        p = Prototype(
            id=self._next_id,  # 一次性分配,持久化
            mu=phi.copy(),
            tau=np.full_like(phi, self.config.tau_init),
            activation_ema=1.0,
            last_activated_tick=current_tick,
        )
        self._next_id += 1
        self.prototypes.append(p)
        return p, 1.0

    def warm_load(self, persisted: dict):
        """SQLite 恢复后,从最大已用 id 推 next_id 防重号"""
        self.prototypes = [Prototype(**row) for row in persisted["prototypes"]]
        self._next_id = max((p.id for p in self.prototypes), default=-1) + 1
```

**关键**:`id` 在 `_spawn` 里**一次性赋值**;后续 `_update_prototype` 只动 μ/τ/activation_ema/last_activated_tick,**不动 id**。warm-load 后从持久化的最大 id 推 next_id 防重号。

#### 1.2.6 feeling SA 标签(v3 修正 B3)

```python
def make_feeling_label(prototype_id: int) -> str:
    return f"feeling::draft::proto_{prototype_id}"
```

只依赖 spawn 时分配的稳定 id,**不依赖 μ**。

### 1.3 共现学习契约(v3 修正 B4 + S3 + S6)

#### 1.3.1 关键基础设施:新建 CooccurrenceAssociationStore(v3 必需,B4 修正)

**v2 错处**:假设 `observe_positive_pair / nearest_by_label` 接口在 APV3.0test 已存在(Codex B4 坐实当前只有简化 token vector + centroid)。

**v3 解法**:**Phase 7.3c 必须建最小独立 store**,不能假设。

```python
# APV3.0test/apv3test/runtime/cooccurrence_store.py(新增)

@dataclass(frozen=True)
class AssociationPair:
    key_a: str               # opaque internal label (e.g., feeling::draft::proto_3)
    key_b: str               # external expression token (e.g., expr::xyz_a8b2c3)
    cumulative_weight: float
    last_update_tick: int
    update_count: int

class CooccurrenceAssociationStore:
    """Minimal pair-association index for feeling-expression cooccurrence.

    Not a duplicate of OnlineEmbeddingStore: this is a sparse association
    table keyed by (label, token) -> cumulative weight. Used for
    feeling-driven expression paradigm recall. SQLite-persistable.
    """
    def __init__(self, config):
        self._pairs: dict[tuple[str, str], AssociationPair] = {}
        self._by_a: dict[str, set[str]] = defaultdict(set)  # forward index
        self._by_b: dict[str, set[str]] = defaultdict(set)  # reverse index
        self.config = config

    def observe(self, key_a: str, key_b: str, weight: float, current_tick: int):
        """Cumulate weight; decay applied lazily on next access."""
        if weight <= 0:
            return
        key = (key_a, key_b)
        existing = self._pairs.get(key)
        if existing is None:
            self._pairs[key] = AssociationPair(
                key_a=key_a, key_b=key_b,
                cumulative_weight=weight,
                last_update_tick=current_tick,
                update_count=1,
            )
        else:
            # 先应用半衰期衰减再加新权重
            age = current_tick - existing.last_update_tick
            decayed = existing.cumulative_weight * (self.config.half_life_decay ** age)
            self._pairs[key] = AssociationPair(
                key_a=key_a, key_b=key_b,
                cumulative_weight=decayed + weight,
                last_update_tick=current_tick,
                update_count=existing.update_count + 1,
            )
        self._by_a[key_a].add(key_b)
        self._by_b[key_b].add(key_a)

    def similarity(self, key_a: str, key_b: str, current_tick: int) -> float:
        """Returns the decayed cumulative weight for the pair (0 if none)."""
        existing = self._pairs.get((key_a, key_b))
        if existing is None:
            return 0.0
        age = current_tick - existing.last_update_tick
        return existing.cumulative_weight * (self.config.half_life_decay ** age)

    def nearest_by_label(self, labels: Sequence[str], top_k: int, current_tick: int) -> list[str]:
        """Forward-indexed lookup: for each label, get associated tokens, rank by decayed weight."""
        scores: dict[str, float] = defaultdict(float)
        for lab in labels:
            for token in self._by_a.get(lab, set()):
                scores[token] += self.similarity(lab, token, current_tick)
        return sorted(scores, key=scores.get, reverse=True)[:top_k]

    def export_to_sqlite(self, conn) -> None:
        """Persistence: schema (key_a TEXT, key_b TEXT, weight REAL, tick INT, count INT)."""
        ...

    def import_from_sqlite(self, conn, current_tick: int) -> None:
        """Warm-load with decay applied."""
        ...
```

**这是 Phase 7.3c 的独立工作产物**,**必须先做出来,再做 Phase 7.3e 的 expression recall**。

#### 1.3.2 token provenance + attention(v3 修正 S3)

**v2 错处**:同 tick 多 token 同权重学进去(教师 + 干扰 + 上下文),共现污染。

**v3 解法**:`ExternalExpressionToken` 加 attention 权重:

```python
@dataclass(frozen=True)
class ExternalExpressionToken:
    token: str
    origin: str             # "perception_other" | "teacher_reply" | "self_emission"
    attention_weight: float # [0,1],由 ingest 阶段的注意力机制赋值
    segment_id: str         # 用于同段 token 聚合
```

`attention_weight` 由 ingest 层既有的注意力机制赋值:
- 处于焦点窗口的 token 高 attention
- 背景噪声/上下文 token 低 attention
- 这是状态池注意力的副产品,不是新机制

#### 1.3.3 学习律(v3:provenance + attention 复合权重)

$$
w(f, e^j) = \frac{R_f}{R_f + \kappa} \cdot \gamma_{co} \cdot \gamma_{\text{origin}}[\text{origin}(e^j)] \cdot \text{attention}(e^j)
$$

调用:`store.observe(f.label, e^j.token, weight=w(f, e^j), current_tick=t)`

**S6 修正(teacher 与 natural 等价)**:`gamma_origin[teacher_reply]` 可以比 `perception_other` 略高(可信度差异,tuner-owned),但**写入的 evidence 字段完全同构**——association store 的 schema 只有 (key_a, key_b, cumulative_weight, ..., update_count),**没有"是不是 LLM 教的"路由字段**。同一对 (feeling, expression) 自然教学与 LLM 教学**累加到同一条记录**,只是权重差异。

### 1.4 召回链路(v3:接 CooccurrenceAssociationStore)

#### 1.4.1 两阶段召回(v3:用新 store 而非假想接口)

```python
def recall_expression_paradigms_for_feelings(
    feelings: Sequence[FeelingSA],
    paradigm_directory,  # 普通范式索引
    association_store: CooccurrenceAssociationStore,
    current_tick: int,
    config,
) -> list[tuple[ParadigmSA, float]]:
    # Stage 1: 通过 association store 找哪些表达 token 与活跃 feeling 关联强
    feeling_labels = [f.sa_label for f in feelings]
    candidate_tokens = association_store.nearest_by_label(
        feeling_labels, top_k=config.K_fast, current_tick=current_tick
    )
    # Stage 2: 通过这些 token 反查包含它们 cue 的 ParadigmSA
    candidate_paradigms = set()
    for token in candidate_tokens:
        candidate_paradigms.update(paradigm_directory.find_by_cue_token(token))
    # Stage 3: 精排
    scored = []
    for p in candidate_paradigms:
        total = 0.0
        for f in feelings:
            for token in p.cue_tokens:
                total += f.real_energy * association_store.similarity(
                    f.sa_label, token, current_tick
                )
        if total > 0:
            scored.append((p, total))
    scored.sort(key=lambda x: -x[1])
    return scored
```

#### 1.4.2 涌现回复压力(v3 修正 S1)

**v2 已有方向对**(iterate state_field_items + sa_type 加权),v3 显式加两条约束:

1. **pressure 只决定"是否回复",绝不决定"说什么"**(S1 修正)
2. **所有 pressure 输入 SA 必须按 v3.0 §12.4 半衰期衰减**(G9 新增)

```python
# 在 ingest 阶段,所有 pressure-type SA 入池时设置衰减
class ExternalQuerySA(SA):
    sa_type = "external_query"
    def update_energy_per_tick(self, age):
        self.real_energy *= config.query_half_life_decay ** age

class SilenceSA(SA):
    sa_type = "silence"
    # silence 是单调增加而不是衰减(沉默越久压力越大),但有上限
    def update_energy_per_tick(self, age):
        self.real_energy = min(1.0, age / config.silence_normalizer)

class RecentCommitSA(SA):
    sa_type = "recent_commit"
    def update_energy_per_tick(self, age):
        self.real_energy *= config.commit_half_life_decay ** age
```

**关键**:`pressure_type_weights` 的设计**只能涉及 sa_type → 权重映射**,**不能涉及 sa_type → 表达内容映射**。表达内容选择**完全由 feeling-expression association 决定**,reply_pressure 只决定"是否进入表达召回 gate"。

```python
# 这是 OK 的(只管 gate)
if reply_pressure.real_energy > config.must_reply_threshold and commit_blocked:
    expr_candidates = recall_expression_paradigms_for_feelings(...)

# 这是不许的(管说什么)
if reply_pressure.real_energy > config.must_reply_threshold:
    if pressure.dominant_source == "external_query":
        say_explicitly("回答查询")  # ❌ 这就退化成策略表了
```

### 1.5 自言自语回路(沿用 v2 §1.5)

`gamma_origin[self_emission] = 0` 默认。

---

## 2. 伪代码 v3

仅展示有 v2 → v3 变化的部分。其余沿用 v2。

### 2.2 IntrospectionPrototypeStore(v3 修正 B1+B2+B3)

```python
class IntrospectionPrototypeStore:
    def __init__(self, config):
        self.prototypes: list[Prototype] = []
        self._next_id = 0
        self.config = config

    def respond_or_spawn(self, phi: np.ndarray, current_tick: int) -> tuple[Prototype, float]:
        # 冷启动 / novelty spawn(独立于响应度!)
        if not self.prototypes:
            return self._spawn(phi, current_tick)
        distances = {p.id: self._whitened_distance(phi, p) for p in self.prototypes}
        d_min = min(distances.values())  # ✅ min 不是 max(B2 修正)
        if d_min > self.config.theta_spawn:  # ✅ 独立判据(B1 修正)
            return self._spawn(phi, current_tick)
        # 否则 softmax 软分配更新
        responsibilities = self._softmax_responsibilities(distances)
        for p_id, r in responsibilities.items():
            p = self._lookup(p_id)
            self._update_prototype(p, phi, r, current_tick)
        best_id = max(responsibilities, key=responsibilities.get)
        return self._lookup(best_id), responsibilities[best_id]

    def _whitened_distance(self, phi, p) -> float:
        return math.sqrt(sum(
            ((phi[i] - p.mu[i]) / max(p.tau[i], self.config.tau_floor)) ** 2
            for i in range(len(phi))
        ))

    def _softmax_responsibilities(self, distances: dict[int, float]) -> dict[int, float]:
        # logit = -d²/2(因为 d 已经白化)
        logits = {pid: -d * d / 2 for pid, d in distances.items()}
        max_l = max(logits.values())
        exp_l = {pid: math.exp(l - max_l) for pid, l in logits.items()}
        z = sum(exp_l.values())
        return {pid: v / z for pid, v in exp_l.items()}

    def _spawn(self, phi, current_tick) -> tuple[Prototype, float]:
        p = Prototype(
            id=self._next_id,  # ✅ B3 修正:一次性分配
            mu=phi.copy(),
            tau=np.full_like(phi, self.config.tau_init),
            activation_ema=1.0,
            last_activated_tick=current_tick,
        )
        self._next_id += 1
        self.prototypes.append(p)
        return p, 1.0

    def _update_prototype(self, p, phi, r, current_tick):
        # μ 按软分配更新
        eta = self.config.eta_mu * r
        p.mu = (1 - eta) * p.mu + eta * phi
        # τ 按 EMA 残差平方
        residual_sq = (phi - p.mu) ** 2
        p.tau = np.sqrt((1 - eta) * p.tau ** 2 + eta * residual_sq)
        p.tau = np.maximum(p.tau, self.config.tau_floor)
        p.activation_ema = p.activation_ema * self.config.activation_decay + r
        p.last_activated_tick = current_tick
        # ⚠️ p.id 绝不更新

    def decay_unactivated(self, current_tick: int):
        for p in self.prototypes:
            age = current_tick - p.last_activated_tick
            p.activation_ema *= self.config.half_life_decay ** age
        self.prototypes = [p for p in self.prototypes
                          if p.activation_ema > self.config.eviction_floor]
        # 软上限保护(S5 修正)
        if len(self.prototypes) > self.config.max_prototypes:
            self.prototypes.sort(key=lambda p: -p.activation_ema)
            self.prototypes = self.prototypes[:self.config.max_prototypes]

    def warm_load(self, persisted: dict):
        # B3 修正:从最大已用 id 推 next_id
        self.prototypes = [Prototype.from_dict(row) for row in persisted.get("prototypes", [])]
        self._next_id = max((p.id for p in self.prototypes), default=-1) + 1
```

### 2.4 共现学习契约 v3(provenance + attention)

```python
def observe_feeling_expression_cooccurrence(
    feelings: Sequence[FeelingSA],
    external_tokens: Sequence[ExternalExpressionToken],
    association_store: CooccurrenceAssociationStore,
    config,
    current_tick: int,
) -> None:
    if not feelings or not external_tokens:
        return
    for f in feelings:
        for e in external_tokens:
            gamma_origin = config.gamma_origin.get(e.origin, 0.0)
            if gamma_origin <= 0:
                continue
            energy_factor = f.real_energy / (f.real_energy + config.cooccurrence_saturation)
            w = (energy_factor *
                 config.cooccurrence_lr *
                 gamma_origin *
                 e.attention_weight)  # S3 修正:加 attention
            w = min(w, config.cooccurrence_max_weight)
            if w <= 0:
                continue
            association_store.observe(
                key_a=f.sa_label,
                key_b=e.token,
                weight=w,
                current_tick=current_tick,
            )
```

### 2.7 tick 编排 v3(沿用 v2 §2.7,补一条强制衰减)

```python
def tick_with_introspection(state, input, prototype_store, association_store, config):
    current_tick = state.get("tick", 0)

    # Phase -1: prototype 主动衰减(每 tick 都做,不依赖访问触发)
    prototype_store.decay_unactivated(current_tick)

    # Phase 0: ingest → 铸造 pressure 类 SA 入池(注意每个 SA 自带衰减规则)
    ingest(input, state)

    # Phase 1-6: 沿用 v2 §2.7
    ...
```

---

## 3. 红线核对(v3 扩展)

| v3.1 红线 | v3 是否合规 | 说明 |
|---|---|---|
| 不新增关键词 if-else | ✅ | label 不参与分支 |
| 不新增答案表 | ✅ | 表达靠共现学到 |
| 不新增整句宏 | ✅ | 每 tick 单 token emit |
| 不用学生侧 LLM | ✅ | |
| 自生成草稿不抬 support | ✅ | gamma_origin[self_emission]=0 |
| 阈值是 config/tuner | ✅ | θ_spawn / half_life / γ / attention_weight 等全 tuner |
| 每 tick 最多 1 emit | ✅ | paradigm_fill_draft vs rebind_slots |
| 不读 token 字面 | ✅ | adapter 红线扫描(v3 新增 §4.6.4) |
| pressure 输入是池 SA 不是 dict | ✅ | iterate state_field_items |
| **pressure 只管"是否说",不管"说什么"** | ✅(v3 新增 S1) | gate 用法明确写死 |
| **prototype_id 持久稳定** | ✅(v3 新增 B3) | spawn 一次分配 |
| **共现 store 独立模块,带 SQLite parity** | ✅(v3 新增 B4) | CooccurrenceAssociationStore |
| **teacher 与 natural 在 evidence 层等价** | ✅(v3 新增 S6) | schema 无 LLM 路由字段 |

---

## 4. 验收门 v3

沿用 v2 §4.1-4.7 全部测试,**新增 4 条**:

### 4.7 prototype_id 持久稳定(G8 新增)

```python
def test_prototype_id_stable_under_mu_drift():
    store, _ = bootstrap_empty()
    phi = make_phi_at_position([0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.5])
    p1, _ = store.respond_or_spawn(phi, current_tick=1)
    original_id = p1.id

    # 喂 100 个稍漂的 phi
    for i in range(100):
        drifted = phi + np.random.normal(0, 0.05, 7)
        store.respond_or_spawn(drifted, current_tick=2 + i)

    # 100 个 tick 后,p1 的 id 必须没变
    p_now = store._lookup(original_id)
    assert p_now is not None
    assert p_now.id == original_id
    # μ 应该已经漂移
    assert not np.allclose(p_now.mu, phi)
```

### 4.8 spawn 在单原型场景仍能触发(B1+B2 修正验证)

```python
def test_spawn_works_with_single_existing_prototype():
    store, _ = bootstrap_empty()
    phi_a = make_phi_at_position([0.0]*7)
    p_a, r_a = store.respond_or_spawn(phi_a, current_tick=1)
    assert r_a == 1.0  # 单原型 softmax 必然 r=1(B1 数学真相)

    # 远离 p_a 的 phi_b 必须触发新原型,即使 r_a 因 softmax 仍 = 1
    phi_b = make_phi_at_position([1.0]*7)  # 距 p_a 很远
    p_b, r_b = store.respond_or_spawn(phi_b, current_tick=2)
    assert p_b.id != p_a.id  # 真的 spawn 了
    assert len(store.prototypes) == 2
```

### 4.9 共现学习区分目标 vs 干扰(G7 新增,S3 修正验证)

```python
def test_cooccurrence_distinguishes_target_from_distractor():
    state, store, embed, assoc_store = bootstrap_empty()

    # 教 50 轮:目标 token 高 attention,干扰 token 低 attention
    target_token = f"expr::tgt_{random_id()}"
    distractor_token = f"expr::dis_{random_id()}"

    for _ in range(50):
        state = tick_with_introspection(state, TickInput(
            draft=make_unresolved_text_draft(),
            external_tokens=[
                ExternalExpressionToken(target_token, "teacher_reply", attention_weight=0.9, segment_id="s1"),
                ExternalExpressionToken(distractor_token, "perception_other", attention_weight=0.1, segment_id="s2"),
            ],
        ))

    feeling_label = first_feeling_label(state)
    sim_target = assoc_store.similarity(feeling_label, target_token, current_tick=state["tick"])
    sim_distractor = assoc_store.similarity(feeling_label, distractor_token, current_tick=state["tick"])

    # 目标的关联权重必须显著高于干扰
    assert sim_target > sim_distractor * 3  # 至少 3 倍差距(tuner_owned config 化)
```

### 4.10 所有 pressure SA 显式衰减(G9 新增)

```python
def test_external_query_sa_decays_over_ticks():
    state, _ = bootstrap_empty()
    # 注入 external_query SA
    state = tick_with_introspection(state, TickInput(
        incoming_external_query="test_question",
    ))
    initial_energy = next(sa for sa in state["state_field_items"]
                         if sa["sa_type"] == "external_query")["real_energy"]
    assert initial_energy > 0.5

    # 跑 100 个空 tick
    for _ in range(100):
        state = tick_with_introspection(state, TickInput())

    # SA 应该已经衰减到接近 0
    final_query_sa = next(
        (sa for sa in state["state_field_items"] if sa["sa_type"] == "external_query"),
        None
    )
    assert final_query_sa is None or final_query_sa["real_energy"] < 0.05
```

### 4.6.4 adapter 内容捷径扫描(v3 修正 S2)

```python
def test_modality_adapters_have_no_content_shortcuts():
    """text adapter 实现里不许读 token 字面/case_name/display_text"""
    import re
    adapter_file = Path("APV3.0test/apv3test/runtime/modality_adapters.py")
    src = adapter_file.read_text()
    # 严格禁止内容字段读取
    forbidden = [
        r"\.token\b", r"\.case_name\b", r"\.display_text\b",
        r"\.tokens\b", r"\.text\b",
        # 字面比较
        r"==\s*['\"]\w+['\"]", r"in\s*\(['\"]\w+['\"]",
    ]
    for pattern in forbidden:
        matches = re.findall(pattern, src)
        assert not matches, f"adapter 含内容捷径 {pattern}: {matches}"
```

### 4.6.5 label-bijection 精确作用域(v3 修正 B5)

```python
def test_label_bijection_within_internal_scope_only():
    """随机重命名所有内部 opaque feeling label,行为必须不变。
    精确作用域: 必须一致重写以下 7 处:
      1. prototype store id/label 引用
      2. state_field_items 里的 feeling SA label
      3. CooccurrenceAssociationStore 的 key_a(feeling 端)
      4. Expression paradigm 的 cue_tokens 里出现的 feeling label
      5. Recall index 的 forward map (_by_a) keys
      6. Persistence projection 的 label 列
      7. Trace 中用 label 计算的字段
    不重写:
      - 外部表达 token(expr::*, perception_other 接收的 token)
      - association_store 的 key_b
    """
    state, store, embed, assoc_store = bootstrap_empty()
    state = train_cooccurrence_learning(state, n=50)

    # 跑一次,记录基线
    result_baseline = tick_with_introspection(state, TickInput(
        incoming_external_query="trigger_pressure",
        draft=make_unresolved_text_draft(),
    ))

    # 应用 bijection 到 7 处内部引用
    state2, store2, assoc_store2 = apply_internal_label_bijection(
        state, store, assoc_store, random_bijection=lambda lab: f"feeling::draft::bijected_{lab}"
    )

    # 外部 token (e.g. "expr::test") 必须未被重写
    for pair_key in assoc_store2._pairs:
        key_b = pair_key[1]
        assert not key_b.startswith("feeling::draft::bijected_"), \
            "外部 token 不应被重命名"

    # 行为必须不变
    result_bijected = tick_with_introspection(state2, TickInput(
        incoming_external_query="trigger_pressure",
        draft=make_unresolved_text_draft(),
    ))

    # 召回的 paradigm IDs 必须相同顺序(因为 paradigm 内部 cue 也被一致重写)
    assert result_baseline.recalled_paradigm_ids == result_bijected.recalled_paradigm_ids
    # commit pressure 必须几乎不变
    assert abs(result_baseline.commit_pressure - result_bijected.commit_pressure) < 1e-6
```

---

## 5. 工程落地步骤(v3 分阶段,采纳 Codex S4 建议)

按 Codex Phase 7.3a-7.3f 分步走,每步保留前面已通过的 teacher-off echo/successor/multi-reply 回归:

### 7.3a — 设计修订门(本文)
- 已落地:本 v3 设计稿
- 验收:Codex 再次审阅本 v3 文档,无新 blocker

### 7.3b — 内省原型 observer-only
- 落地 `IntrospectionPrototypeStore` + `extract_facts` + `emit_draft_introspection_feelings`
- **只产生 feeling SA,不改变发声**
- 验收:§4.1 + §4.7 + §4.8 + §4.5(within-text)
- Phase 7.0/7.1 teacher-off echo/successor/multi-reply 回归必须仍通过

### 7.3c — 共现关联 store
- 落地 `CooccurrenceAssociationStore` + `observe_feeling_expression_cooccurrence`
- SQLite parity
- 验收:§4.2 相对增量 + §4.7 self_emission 隔离 + §4.9 distractor 区分

### 7.3d — reply_pressure SA
- 落地 `derive_reply_pressure_sa` + 各 pressure-type SA(external_query/silence/recent_commit)
- 删除 `must_reply: bool` 参数和 `undecidable_feeling_tokens`
- 验收:§4.3 + §4.10 衰减测试

### 7.3e — expression recall + rebind
- 落地 `recall_expression_paradigms_for_feelings`(用 association store)+ `paradigm_rebind_slots`
- 删除 `_has_undecidable_fragment` 这种 ad-hoc gate,改用 `commit_blocked` 结构事实
- 验收:Phase 7.0/7.1 teacher-off 全部仍通过

### 7.3f — 红线与不变量
- §4.6.1 AST 扫描
- §4.6.2 label-bijection 不变量测试(精确 7 处作用域)
- §4.6.3 测试不许内联 prototype id
- §4.6.4 adapter 内容捷径扫描
- 验收:三层全过

---

## 6. 已删除的"未决问题"(v3 强制实施)

v2 §6 列了 6 项未决,其中 1/5 现在强制实施:

- ~~1. 原型集合过度增长~~ → **§1.2.4 强制实施**:half_life_decay + eviction_floor + max_prototypes 软上限
- ~~5. 多 feeling 同时活跃~~ → 当前用 §2.5 线性加权,作为基线接受;若实测有问题再迭代

剩余真未决(v3 保留):
1. 跨模态适配器尚无第二模态可验(deferred 到 vision 阶段)
2. τ_f 学习速率初值标定
3. gamma_origin[self_emission] 是否将来给小正值
4. EMA 校准初始化平滑

---

## 7. 哲学总判 v3

v3 在 v2 基础上**修正了所有 Codex 反向审阅指出的真问题**,使设计在数学和工程两层都经得起反复盘问:

- **B1+B2 数学修正**:spawn 判据与 softmax 响应度**显式解耦**,使"足够远就 spawn"和"软响应分配"在数学上独立、协调
- **B3 工程修正**:prototype_id 持久稳定,μ 漂移不动 id,保证持久化引用不断裂
- **B4 接口现实**:Phase 7.3c 必须先建 `CooccurrenceAssociationStore`,不假设接口存在
- **B5 验收精化**:label-bijection 精确指明 7 处必须重写、外部 token 不重写
- **S1 哲学守护**:pressure 只管"是否说",不管"说什么"——避免退化成策略表
- **S3 学习健壮**:token attention 权重 + distractor 必须的验收测试,防共现污染
- **S5 强制实施**:prototype decay 不再是未决问题,首批实现
- **S6 教学等价**:teacher 与 natural 在 evidence 层完全等价,schema 无路由字段

**用户的核心要求依然守住**:
> "我们人类更多的是先产生了一些内在的感受和表达倾向,然后后来根据这些来选取的表达范式来进行语言组织的。"

v3 用真正可实现的数学回答了它,且在 v2 → Codex 反向审阅的循环中,**每一条 Codex 提出的真问题都被吸收**,而 Codex 误读的部分(B1)被诚实指出并精化。这是设计在多轮对抗中越走越严的标志。
