# APV3.0 Phase 20.6 v1e Errata — Final Sealing: State Field Compat, Affect Loop, Canvas Lifecycle, Concurrent Sessions

Date: 2026-06-21
Author: Claude(架构),银子老师(风格定调与最终签收)
Status: **最后一份**封口 micro errata(v1 + v1b + v1c + v1d + v1e 合读后,五份合读总 ≈ 155 KB,开工就绪)
Source: 第四轮对抗审阅 — 我读完 Codex v1b/v1c/v1d 三轮后,再做独立审阅,找出 5 处所有前述设计都没覆盖的真漏项
License intent: AGPL-3.0-or-later
Real name handling: 全文件 grep 真名 = 0

---

## 0. 这一份做什么(一句话)

把 v1 + v1b + v1c + v1d 四份合读后仍存在的 **5 处真漏项**钉死:既有状态字段冲突(F1)、能量公式互踩(F2)、共情/情绪通路完全缺失(F3)、sensory_canvas turn 间生命周期未定义(F4)、多 session 并发互斥未处理(F5)。这 5 项每一项实施时**必然**炸 / 出 bug / 缺拟人维度,补完即可放心开工。

---

## 1. 全部修订清单(5 自查项)

| ID | 内容 | §X |
|---|---|---|
| **F1** | v1d §2 新 7 字段 vs 既有 StateItem 5 字段冲突 | §2 |
| **F2** | v1d §2 新 P 公式 vs 既有 `cognitive_pressure = R - V` 冲突 | §3 |
| **F3** | 共情 / 情绪 / EMPATHY_RESONANCE marker / affect_bucket 完全缺失 | §4 |
| **F4** | sensory_canvas turn 间生命周期未定义 | §5 |
| **F5** | 多 session 并发互斥未处理 | §6 |

---

## 2. F1 — StateItem 字段扩展兼容路径(实施级)

### 2.1 实证发现

读 [runtime/cognitive/state_pool/state_pool.py](runtime/cognitive/state_pool/state_pool.py):

```python
@dataclass
class StateItem:
    real_energy: float = 0.0
    virtual_energy: float = 0.0
    attention_energy: float = 0.0
    cognitive_pressure: float = 0.0
    fatigue: float = 0.0
    # 5 字段
```

v1d §2 形式化为:

```
R, V, A, P, F, T, U
其中 T = trust_promoted_value
     U = unresolved_carry_value
# 7 字段
```

**实施时如果直接改 StateItem dataclass 加 T/U** → 580+ 既有测试,几乎所有都构造 StateItem,**全炸**。

### 2.2 v1e 修正:**不破坏既有 dataclass,加 metadata 字段承载**

```python
@dataclass
class StateItem:
    # 既有 5 字段不动
    real_energy: float = 0.0
    virtual_energy: float = 0.0
    attention_energy: float = 0.0
    cognitive_pressure: float = 0.0
    fatigue: float = 0.0
    # ... 既有所有字段
    
    metadata: dict[str, Any] = field(default_factory=dict)
    
    # v1d 新增 T/U 通过 metadata helper 存取(不改 dataclass schema)
    @property
    def trust_value(self) -> float:
        return float(self.metadata.get("phase20_6_trust_value", 0.0))
    
    @trust_value.setter
    def trust_value(self, v: float):
        self.metadata["phase20_6_trust_value"] = float(max(0.0, min(1.0, v)))
    
    @property
    def unresolved_carry(self) -> float:
        return float(self.metadata.get("phase20_6_unresolved_carry", 0.0))
    
    @unresolved_carry.setter
    def unresolved_carry(self, v: float):
        self.metadata["phase20_6_unresolved_carry"] = float(max(0.0, min(1.0, v)))
```

### 2.3 红线

```
RL-20.6-v1e-F1-01: StateItem dataclass 不允许新增 phase20_6_* 字段
                    trust_value / unresolved_carry 必须走 metadata
RL-20.6-v1e-F1-02: 既有 580+ tests 不允许破坏(全量回归 PASS)
RL-20.6-v1e-F1-03: v1d §2 数学公式中所有 T_i / U_i 引用 → 实施时映射为
                    item.trust_value / item.unresolved_carry property
```

### 2.4 Gate

```
G-20.6-v1e-F1-01: StateItem schema 不变(grep test:phase20_open_dialogue 不改 StateItem dataclass)
G-20.6-v1e-F1-02: 全量回归 ≥ 当前 614 passed
G-20.6-v1e-F1-03: 新建 SA 不影响既有 SA dataclass 操作(单测)
```

---

## 3. F2 — P 公式互踩

### 3.1 实证发现

[state_pool.py:74](runtime/cognitive/state_pool/state_pool.py#L74):

```python
item.cognitive_pressure = item.real_energy - item.virtual_energy
```

**既有 P 公式 = R - V**(实/虚差)。

v1d §2 写了**新动态方程**:

```
P_{i,t+1} = clip01(decay_P * P_{i,t} + sources_P)
```

**冲突**:
- 既有 update_from_event 每次注入都赋值 `P = R - V`
- v1d 新公式想自演化 `P_{t+1} = decay * P_t + sources`
- 两套同时跑 → P 行为不可预测

### 3.2 v1e 修正:既有公式保留为"基础态",v1d 新公式作为 turn loop 层叠加

```python
def compute_cognitive_pressure_v1d(item, tick, last_tick_state) -> float:
    """
    v1d §2 新公式实施版.
    每 tick step 1 调用,叠加在既有 R - V 之上(不覆盖).
    """
    # 既有公式产生的"基础态"(R - V)保留
    base_p = max(0.0, item.real_energy - item.virtual_energy)
    
    # v1d 新增的动态衰减项
    decay_p = float(load_constant("phase20_6.cognitive_pressure_decay"))  # 0.95
    last_p = last_tick_state.get(item.sa_id, {}).get("cognitive_pressure", base_p)
    
    # 新 P = max(基础态, 衰减过的旧 P)
    # 这样既保留既有"R - V 反映即时压力",又有 v1d "压力衰减但不归零"
    return max(base_p, decay_p * last_p)
```

### 3.3 红线

```
RL-20.6-v1e-F2-01: 既有 state_pool.update_from_event 中的 P = R - V 公式不删
RL-20.6-v1e-F2-02: v1d turn loop 中 P 演化函数与既有公式**叠加**(取 max),不覆盖
RL-20.6-v1e-F2-03: 未闭合 SA 的 P 不允许低于 phase20_6.unresolved_pressure_floor(继承 v1 §4.1)
                    防止"基础态归零 + 新公式衰减"双归零
```

### 3.4 Gate

```
G-20.6-v1e-F2-01: 单测:既有 update_from_event P = R - V 行为不变
G-20.6-v1e-F2-02: 单测:v1d turn loop 中 P 多 tick 演化 = max(基础态, 衰减)
G-20.6-v1e-F2-03: 未闭合 SA P 不归零(跨 tick)
```

---

## 4. F3 — 共情 / 情绪通路(关键拟人维度漏)

### 4.1 实证发现

读 v1b / v1c / v1d 三份 errata,**完全没出现以下任何概念**:
- 共情 (empathy)
- EMPATHY_RESONANCE marker(Phase 8.10 + Phase 9.6 既有)
- affect_bucket(Phase 16 styled corpus 已有,calm/curious/sleepy/shy/warm)
- emotion / feeling 在 action 候选打分中的角色

但 Phase 16 styled corpus(已上线)就是按 affect 索引的;Phase 9.6 共情已实施;Phase 20.6 turn loop **必须**让用户难过 → AP 选 styled empathy 范式而不是数物体。

### 4.2 v1e 补充:Affect Bucket → Candidate Score Modulator

```python
def compute_affect_modulator(
    state_pool, candidate: ActionCandidate
) -> float:
    """
    根据当前 affect_bucket(用户语调 / Phase 9.6 共情 marker 推算)
    给 candidate 的 raw_drive 乘 modulator.
    """
    # 1. 当前推算 affect bucket(来自 EMPATHY_RESONANCE marker + 用户文本 SA 的情感倾向)
    current_affect = infer_current_affect(state_pool)
    # ∈ {calm, curious, sleepy, shy, warm}
    
    # 2. 若 candidate 是 write_char,看其 token 是否来自匹配 affect 的 styled corpus 范式
    if candidate.kind == "write_char":
        token_sa = candidate.params.get("token_sa_id")
        if token_sa:
            paradigm_affect = sparse_pairwise.get_affect_bucket_for_token(token_sa)
            if paradigm_affect == current_affect:
                return float(load_constant("phase20_6.affect_match_bonus"))  # 1.3
            elif paradigm_affect == "warm" and current_affect in ("sad", "anxious"):
                return float(load_constant("phase20_6.empathy_resonance_bonus"))  # 1.5
    
    # 3. 共情场景:用户难过/焦虑 → 数物体/解释 candidate 降权
    if current_affect in ("sad", "anxious") and candidate.kind in ("write_char_explain", "write_char_enumerate"):
        return float(load_constant("phase20_6.empathy_demote"))  # 0.6
    
    return 1.0
```

### 4.3 turn loop step 5 集成

```python
def step_5_build_action_candidates(...):
    candidates = build_raw_candidates(...)
    
    # v1e 新增:affect modulator
    for c in candidates:
        c.score *= compute_affect_modulator(state_pool, c)
    
    return candidates
```

### 4.4 EMPATHY_RESONANCE marker 接通

既有 [Phase 8.10 EMPATHY_RESONANCE marker](runtime/cognitive/state_pool/state_pool.py) 在 turn loop 中**必须被读取**:

- 每 tick step 1 检查 state_pool 中 EMPATHY_RESONANCE marker 强度
- 强度 > threshold → current_affect 偏向 warm / shy
- 影响 step 5 candidate 打分

### 4.5 红线

```
RL-20.6-v1e-F3-01: turn loop step 5 必须调用 compute_affect_modulator
RL-20.6-v1e-F3-02: EMPATHY_RESONANCE marker 强度必须读入 state_pool snapshot 字段
RL-20.6-v1e-F3-03: 用户难过(low affect)+ 数物体 candidate 高分时,必须 demote
                    单测:模拟"用户说'我今天很难过'" + 同时传图,AP 不选"嗯,看到三个"
RL-20.6-v1e-F3-04: Phase 16 styled corpus 的 affect_bucket 必须真正被 candidate 选用
                    grep test: sparse_pairwise 有接 affect_bucket 字段
```

### 4.6 Gate

```
G-20.6-v1e-F3-01: affect_modulator 实施 + 单测 4 路径(calm/curious/warm/共情场景)
G-20.6-v1e-F3-02: 共情 demo 5 turn 银子老师签收(用户"难过" → AP 选 styled empathy 不选数物体)
G-20.6-v1e-F3-03: EMPATHY_RESONANCE marker 真接入 step 1 state pool 演化
```

---

## 5. F4 — sensory_canvas turn 间生命周期

### 5.1 漏项

v1 §4.2 写"sensory_canvas 累积 N tick foveated patches",但**没说**:

- Turn 1 用户上传苹果图,canvas 累积 6 tick 后 commit
- Turn 2 用户**没传新图**,只说"还有别的吗" → canvas 还在不在?
- Turn 3 用户上传**香蕉图** → canvas 上次还有苹果痕迹,跟香蕉混?
- Turn 100 后 canvas 累积所有图,内存爆?

**这是 turn 间状态泄漏的高风险点**。

### 5.2 v1e 修正:四档生命周期

| 场景 | sensory_canvas 处理 |
|---|---|
| Turn N → Turn N+1 **同图**(用户上轮传图后这轮继续问相关问题) | 保留 canvas,累积更多 fixation |
| Turn N → Turn N+1 **新图** | reset canvas,从新图重新 foveated |
| Turn N → Turn N+1 **无图** | canvas 标 "stale",前 5 tick 仍可用作 remembered_overlay(v1e 既有 v1c R_sketch 三层分离),之后衰减消失 |
| Turn 100 累积 | 跨 turn canvas 至多保留 3 个 ring buffer(MRU),旧的扔 |

### 5.3 数学化

```python
class SensoryCanvasLifecycle:
    """v1e 新增:跨 turn canvas 管理"""
    
    canvases: dict[str, SensoryCanvas]  # image_hash → canvas
    mru_order: list[str]                 # most recently used 顺序
    
    def get_or_create(self, image_hash: str | None, current_turn_id: str) -> SensoryCanvas:
        if image_hash is None:
            # 无图 turn:返回最近一个 canvas 标 stale
            if self.mru_order:
                canvas = self.canvases[self.mru_order[0]]
                canvas.staleness_ticks_since_last_view += 1
                return canvas
            return SensoryCanvas.empty()
        
        if image_hash in self.canvases:
            # 同图:继续累积
            canvas = self.canvases[image_hash]
            canvas.staleness_ticks_since_last_view = 0
            self._mru_promote(image_hash)
            return canvas
        
        # 新图:创建
        new_canvas = SensoryCanvas.from_native_image(image_hash)
        self.canvases[image_hash] = new_canvas
        self.mru_order.insert(0, image_hash)
        
        # ring buffer 上限
        if len(self.mru_order) > int(load_constant("phase20_6.canvas_ring_buffer_size")):  # 3
            old_hash = self.mru_order.pop()
            del self.canvases[old_hash]
        
        return new_canvas
    
    def get_stale_canvas_for_remembered_overlay(self, current_turn_id: str) -> SensoryCanvas | None:
        """无图 turn 时,提供"刚才看的那图"作为 remembered_overlay 源."""
        if self.mru_order:
            canvas = self.canvases[self.mru_order[0]]
            stale_window = int(load_constant("phase20_6.canvas_stale_window_ticks"))  # 30
            if canvas.staleness_ticks_since_last_view < stale_window:
                return canvas
        return None
```

### 5.4 与 v1c §10 consolidation 协调

v1c §10 已有 post-turn consolidation。v1e §5 增加的 canvas lifecycle 与之协调:

- post-turn consolidation 阶段:对每个 canvas 提取 "stable visual feature" → 沉积到 SlowMemoryStore
- 即使 canvas 后被 ring buffer 扔了,其知识已沉积慢系统
- 这就是"睡眠固化"的拟人形式

### 5.5 红线

```
RL-20.6-v1e-F4-01: SensoryCanvasLifecycle 用 ring buffer,上限 3 个(防内存累积)
RL-20.6-v1e-F4-02: 无图 turn 时,stale canvas 可作 remembered_overlay 源(继承 v1c R_sketch 三层分离),
                    但必须标 source="REMEMBERED_SKETCH"
RL-20.6-v1e-F4-03: 新图 turn 时,旧 canvas 不参与本 turn 视觉计算
RL-20.6-v1e-F4-04: post-turn consolidation 沉积稳定特征到 SlowMemoryStore
                    防止 canvas 扔掉后知识丢失
```

### 5.6 Gate

```
G-20.6-v1e-F4-01: 单测:同图连续 turn,canvas 累积
G-20.6-v1e-F4-02: 单测:新图 turn,旧 canvas 不参与计算
G-20.6-v1e-F4-03: 单测:无图 turn,stale canvas 作 remembered overlay
G-20.6-v1e-F4-04: 单测:ring buffer 上限 3,第 4 个图创建时第 1 个被踢
G-20.6-v1e-F4-05: 单测:被踢前,post-turn consolidation 沉积特征
G-20.6-v1e-F4-06: 100 turn 后内存不爆(单测 + 性能 gate)
```

---

## 6. F5 — 多 session 并发互斥

### 6.1 漏项

设计稿全文假设单 session。但实际**用户开 2 个浏览器 tab**,或**用户演示给朋友看时多人同时操作**:

- Fast SQLite 同时写 → 锁竞争 / 数据损坏
- Slow SQLite (sparse_pairwise) 同时累共现 → 竞态条件
- state_pool 全局变量被两个 turn 同时改 → 状态错乱

**真发布时一定遇到**。

### 6.2 v1e 修正:Session 级 lock + 全局共享 store 的安全并发

```python
class Phase20MultimodalSession:
    """每个浏览器 tab 一个 session,session 间独立 state_pool."""
    
    def __init__(self, session_id: str, *, shared_fast_store, shared_slow_store):
        self.session_id = session_id
        self.state_pool = StatePool()              # 每 session 独立
        self.draft_grid = DraftGrid()              # 每 session 独立
        self.sensory_canvas_lifecycle = SensoryCanvasLifecycle()  # 每 session 独立
        
        # 共享(跨 session)
        self.fast_store = shared_fast_store        # FastActionChainStore(全用户共用)
        self.slow_store = shared_slow_store        # SlowMemoryStore(全用户共用)
        
        # 并发互斥
        self._turn_lock = threading.Lock()         # 单 session 内 turn 串行
    
    def turn(self, ...) -> TurnResult:
        with self._turn_lock:
            # 单 session 一次只跑一个 turn
            ...
```

### 6.3 共享 store 的并发

```python
class FastActionChainStore:
    def __init__(self, sqlite_path):
        self.db = sqlite3.connect(sqlite_path, check_same_thread=False)
        self._write_lock = threading.Lock()
    
    def observe_action_executed(self, ...):
        with self._write_lock:
            # 写入互斥
            self.db.execute(...)
            self.db.commit()
    
    def recall_by_context(self, ...) -> list:
        # 读不需锁(SQLite 同时支持多读单写)
        return self.db.execute(...).fetchall()
```

### 6.4 跨 session 数据隔离 vs 共享

| 数据 | 隔离 vs 共享 |
|---|---|
| state_pool | **隔离**(每 session 独立) |
| draft_grid | **隔离** |
| sensory_canvas | **隔离** |
| chat_session_history | **隔离**(每 session 独立 SQLite 表 / 加 session_id 列) |
| **Fast/Slow store** | **共享**(因为 = AP 的长期记忆,跨 session 是同一个 AP) |
| cooccurrence_store | **共享** |

### 6.5 用户教学跨 session 影响

用户 A 在 session A 里教 AP 一个新词 → Fast/Slow 共享 store 写入 → 用户 B 在 session B 里也能召回这个词。**这是 AP-native 拟人**(同一个 AP 不分 session,记忆是全局的)。

### 6.6 red 线

```
RL-20.6-v1e-F5-01: state_pool / draft_grid / sensory_canvas 必须按 session 隔离
RL-20.6-v1e-F5-02: Fast/Slow store 必须支持并发写(write_lock)+ 并发读(SQLite WAL mode)
RL-20.6-v1e-F5-03: 单 session 内 turn 必须 _turn_lock 串行
                    防止用户连续点 2 次发送
RL-20.6-v1e-F5-04: web_chat 路由按 session_id 路由
```

### 6.7 Gate

```
G-20.6-v1e-F5-01: 单测:2 个 session 并发跑 turn,各自 state_pool 独立
G-20.6-v1e-F5-02: 单测:2 个 session 共享 Fast/Slow store,session A 教,session B 召回
G-20.6-v1e-F5-03: 单测:单 session 内连续 2 次 turn 请求,第 2 次等第 1 次完
G-20.6-v1e-F5-04: 压测:10 session × 5 turn 并发,无数据损坏 + 无 deadlock
```

---

## 7. 修订后 Gate 增量(共 22 条)

| Gate | §X |
|---|---|
| G-20.6-v1e-F1-01..03 | §2 StateItem schema 兼容 |
| G-20.6-v1e-F2-01..03 | §3 P 公式兼容 |
| G-20.6-v1e-F3-01..03 | §4 Affect modulator |
| G-20.6-v1e-F4-01..06 | §5 Canvas lifecycle |
| G-20.6-v1e-F5-01..04 | §6 Session 并发 |
| G-20.6-v1e-Final-01 | 全量回归 ≥ 614 passed + 上述 22 条全过 |
| G-20.6-v1e-Final-02 | v1 + v1b + v1c + v1d + v1e 五份合读 = 实施正本 |
| G-20.6-v1e-Final-03 | 真名 0 命中(五份合读全 grep) |

---

## 8. 五份合读最终落地顺序(替换 v1 §16)

按 v1d §15 final go/no-go + v1e 自查后,修订实施顺序:

| 阶段 | 内容 | 工作量 |
|---|---|---|
| **Stage 0** | 删除清单(v1 §14)+ 旧路径隔离(F1 StateItem 兼容)+ 真 RuntimeTickEvent 骨架 + 无预生成回复单测 | 2 天 |
| **Stage 1** | turn loop §4 主循环 8 step + state_pool 演化(F2 P 公式协调)+ 焦点采样 + sensory_canvas lifecycle (F4)| 2 天 |
| **Stage 2** | Fast System 全实施(模仿/抽象/泛化)+ Slow System 接通 + 候选打分(F3 affect modulator)| 2 天 |
| **Stage 3** | DraftGrid 完整生命周期(read/write/edit/delete/look_again/commit)+ 未闭合恢复 + 多任务打断 demo | 2 天 |
| **Stage 4** | 教学路径整改 + 共现接通 + 删 PHASE20_1 + v1c R_sketch 真接通 + 真反向重建 + 共情 demo | 1 天 |
| **Stage 5** | UI Workbench 8 面板 + Session 并发(F5)+ 历史会话列表 + 扩展能力(TTS / 画布 / 录音 / 教师辅助 / 竖式)| 2 天 |
| **Stage 6** | 所有 Gate 跑通 + Final Report + 银子老师端到端实测演示 | 1 天 |

**总:12 天**(从 v1 的 10 天扩 2 天,为 v1e 补的 5 项)。

---

## 9. 银子老师拍板项

1. **5 处 v1e 补漏全收**(F1 StateItem 兼容 / F2 P 公式协调 / F3 affect modulator / F4 canvas lifecycle / F5 session 并发):同意吗?
2. **12 天工作量**(从 10 天扩 2 天):接受吗?
3. **共情 demo 银子老师签收**(F3 G-20.6-v1e-F3-02):您给一段"用户难过 + 传图"的真场景,Codex 写进单测防回归?
4. **多 session 并发压测**(F5 G-20.6-v1e-F5-04):10 session × 5 turn 并发,接受 30 秒压测时间?

---

## 10. 最终 go/no-go

**Go**:经 v1 + v1b + v1c + v1d + v1e 五份合读后,**所有已知漏项闭合**。

**No-go conditions**(若以下任一为真,延后开工):
- StateItem dataclass 被 v1d T/U 字段直接改(F1)
- v1d P 公式覆盖既有 R - V(F2)
- turn loop step 5 跳过 affect_modulator(F3)
- sensory_canvas 跨 turn 无限累积(F4)
- 多 session 共享 store 无锁(F5)
- 旧 _phase20_5a2_turn / enumerate_objects_in_image / 命中教学 任一路径残留

---

## 11. 署名

- 原架构设计:银子老师(笔名)
- v1e 第四轮对抗审阅 + 5 项补漏:Claude (Anthropic) 在 Codex v1b/v1c/v1d 完成后,通过**实际读既有代码**发现 5 处所有前述设计稿未覆盖的真漏项后产出
- 落地:Codex 在五份合读(v1 + v1b + v1c + v1d + v1e)通过最终审查后,按 §8 修订顺序 12 天实施

End of Phase 20.6 v1e Errata.
