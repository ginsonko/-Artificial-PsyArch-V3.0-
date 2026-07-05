# APV3 v0.1 → v0.2 底层链路修复计划

**计划日期：** 2026-07-05  
**依据：** APV3_Phase20_7_Defect_Report_20260705.md（18项CRITICAL缺陷）  
**目标：** 确保白皮书核心链路在代码中真正打通，消灭设计与实现的背离

> **重要更新：** 对抗性审查发现，当前路线图v0.1"已实现"快照中至少5项标注有误：  
> - "8通道NT情感场 ✓ 已实现" → **FALSE**（无数据类，无DB表）  
> - "13条feeling::*感受SA ✓ 已实现" → **FALSE**（视觉/音频通道均未注入）  
> - "C*虚能量回灌状态池 ✓ 已实现" → **FALSE**（仅计算，未注入）  
> - "B召回残差中和 ✓" → **FALSE**（仅打标签，无能量操作）  
> - "L1在线向量更新 ✓" → **FALSE**（仅批量离线重建）  
> v0.2的工作量因此比原预估显著增大。

---

## 一、修复优先级矩阵

按"链路依赖"排序：下游依赖上游必须先修复。

| 优先级 | 修复组 | 涉及文件 | 缺陷编号 | 影响范围 |
|---|---|---|---|---|
| P0 | 认知周期卫兵修复 | cognitive_cycle.py | CC-1 | 所有B/C/feeling处理 |
| P0 | 情感场数据模型 | models.py | EM-1 | 所有情感相关下游 |
| P1 | 行动SA一等公民 | runtime.py | RT-1 | L1/L2/L3/B召回 |
| P1 | 常驻tick循环 | runtime.py | RT-2,RT-5 | 内驱/idle SA衰减 |
| P1 | wall-clock性能预算 | runtime.py | RT-3,RT-4 | 超预算降级 |
| P2 | B召回残差三路能量 | cognitive_cycle.py, runtime.py | CC-2,RT-6,RT-8 | 黄苹果机制 |
| P2 | C*虚能量注入状态池 | cognitive_cycle.py | CC-3 | 内心活动驱动 |
| P3 | L1实时在线更新 | experience_log.py | L1-1,L1-2,L1-3 | 语义邻近学习 |
| P3 | L2 group-level共现 | experience_log.py | L2-1,L2-2,L2-3 | 结构关系学习 |
| P3 | L1召回路径接入 | experience_flow.py | L1-4 | L1学习成果可用 |
| P4 | 范式动态注册 | paradigm_process.py | PD-1,PD-2,PD-3,PD-4 | 可注册新技能 |
| P4 | 跨turn情感持久化 | models.py + runtime.py | EM-2 | 消灭情感重置 |
| P5 | 视觉feeling::*注入 | vision.py | VS-1,VS-2 | 视觉感知情感响应 |
| P5 | 音频全链路修复 | audio.py | AU-1,AU-2,AU-3 | 听觉通道完整性 |

---

## 二、P0：认知周期卫兵修复（1天）

### 任务P0-1：移除no_write_reason提前返回

**文件:** `cognitive_cycle.py:33-34`  
**问题:** `if event.no_write_reason: return event` 让整个认知周期被跳过  
**修复方案:**
```python
# 删除这两行:
# if event.no_write_reason:
#     return event

# 改为：让认知周期完整执行，no_write_reason只影响最终写入步骤
# 在cycle末尾的实际写入阶段检查 no_write_reason
```
**影响:** 修复后B召回、C_forward/backward、C*回灌、feeling通道在所有tick中均能执行。

**验收（自动化）:**
```sql
-- 制造一个no_write_reason事件，验证认知周期仍有B召回痕迹
SELECT count(*) FROM occurrences 
WHERE created_at > ? AND sa_type_name LIKE 'feeling::%';
-- 期望 > 0（之前固定为0）
```

---

### 任务P0-2：8通道NT情感场数据模型建立

**文件:** `models.py`  
**问题:** emotion是无类型dict，无数据类，无DB持久化表  
**修复方案 — 新增EmotionField数据类:**
```python
@dataclass
class EmotionField:
    DA: float = 0.0   # 多巴胺 — 奖励预期
    ADR: float = 0.0  # 肾上腺素 — 警觉/应激
    OXY: float = 0.0  # 催产素 — 亲密/连接
    SER: float = 0.0  # 血清素 — 满足/稳定
    END: float = 0.0  # 内啡肽 — 愉悦/疼痛耐受
    COR: float = 0.0  # 皮质醇 — 压力/挫败
    NOV: float = 0.0  # 新奇素（拟人NT）— 好奇/探索
    FOC: float = 0.0  # 专注素（拟人NT）— 注意力集中

    def to_dict(self) -> dict:
        return dataclasses.asdict(self)
    
    @classmethod
    def from_dict(cls, d: dict) -> 'EmotionField':
        return cls(**{k: float(v) for k, v in d.items() if k in cls.__dataclass_fields__})
    
    def clamp(self) -> 'EmotionField':
        """所有通道值约束到[0,1]"""
        return EmotionField(**{k: max(0.0, min(1.0, v)) for k, v in dataclasses.asdict(self).items()})
```

**修复方案 — 新增DB持久化表（追加到PHASE20_7_SCHEMA_SQL）:**
```sql
CREATE TABLE IF NOT EXISTS phase20_7_emotion_snapshot (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    tick        INTEGER NOT NULL,
    turn_id     TEXT,
    da          REAL NOT NULL DEFAULT 0.0,
    adr         REAL NOT NULL DEFAULT 0.0,
    oxy         REAL NOT NULL DEFAULT 0.0,
    ser         REAL NOT NULL DEFAULT 0.0,
    end_val     REAL NOT NULL DEFAULT 0.0,
    cor         REAL NOT NULL DEFAULT 0.0,
    nov         REAL NOT NULL DEFAULT 0.0,
    foc         REAL NOT NULL DEFAULT 0.0,
    created_at  INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);
CREATE INDEX IF NOT EXISTS idx_emotion_snap_tick ON phase20_7_emotion_snapshot(tick DESC);
CREATE INDEX IF NOT EXISTS idx_emotion_snap_turn ON phase20_7_emotion_snapshot(turn_id);
```

**同步更新 RuntimeTickEventV2:**
```python
# models.py:75
# 旧: emotion: Mapping[str, Any]
# 新:
emotion: EmotionField = dataclasses.field(default_factory=EmotionField)
```

**验收（自动化）:**
```sql
SELECT count(*) FROM sqlite_master 
WHERE type='table' AND name='phase20_7_emotion_snapshot';
-- 期望 = 1
```

---

## 三、P1：行动SA一等公民（2-3天）

### 任务P1-1：insert_action_record后追加SA登记

**文件:** `runtime.py`（14个调用点）  
**修复方案 — 新增辅助函数（在runtime.py中）:**
```python
def _register_action_sa(
    db_path: str,
    action_type: str,
    context_key: str,
    determination: float,
    tick: int,
) -> None:
    """insert_action_record后调用，将行动登记为一等公民SA。"""
    sa_type_name = f"action::{action_type}::{context_key}"
    sa_type_id = upsert_sa_type(db_path, sa_type_name, modality="action")
    insert_occurrence(
        db_path,
        sa_type_id=sa_type_id,
        tick=tick,
        r=determination,  # R能量 = 竞争胜出量
        v=0.0,
        a=1.0,
    )
```

**14个调用点修复模板（以write_cell为例，runtime.py:1033）:**
```python
# 现有代码（保持不变）:
action_rec_id = insert_action_record(db_path, action_type="write_cell", ...)

# 追加（紧跟其后）:
_register_action_sa(
    db_path,
    action_type="write_cell",
    context_key=current_context_key,  # 取当前范式key或turn_id
    determination=determination,       # 从竞争结果取
    tick=current_tick,
)
```

**注意：** 需同步修复DEFECT-RT-7（determination计算）。

**验收（自动化）:**
```sql
-- 执行一次write_cell行动后:
SELECT count(*) FROM occurrences o
JOIN sa_types s ON o.sa_type_id = s.id
WHERE s.name LIKE 'action::%';
-- 期望 > 0
```

---

### 任务P1-2：determination改为竞争胜出量

**文件:** `runtime.py:7221-7228`（_selected_drive_from_competition）  
**修复方案:**
```python
def _selected_drive_from_competition(competitors: list) -> tuple[str, float, float]:
    """返回 (winner_id, winner_drive, determination)"""
    if not competitors:
        return None, 0.0, 0.0
    sorted_c = sorted(competitors, key=lambda x: x.drive, reverse=True)
    winner = sorted_c[0]
    second_drive = sorted_c[1].drive if len(sorted_c) > 1 else 0.0
    determination = winner.drive - second_drive  # 胜出量，非绝对值
    return winner.id, winner.drive, determination
```

---

### 任务P1-3：常驻Tick循环（asyncio后台任务）

**文件:** `runtime.py`  
**修复方案 — 核心架构变更:**
```python
import asyncio
import time

TICK_BUDGET_MS = 100  # wall-clock预算，可配置

class APV3Runtime:
    def __init__(self, db_path: str, config: dict):
        self._db_path = db_path
        self._input_queue: asyncio.Queue = asyncio.Queue()
        self._tick_task: asyncio.Task | None = None
        self._running = False
    
    async def start(self):
        """启动常驻tick循环"""
        self._running = True
        self._tick_task = asyncio.create_task(self._tick_loop())
    
    async def stop(self):
        self._running = False
        if self._tick_task:
            self._tick_task.cancel()
    
    async def submit_user_turn(self, user_text: str, **kwargs) -> str:
        """用户输入以injection方式入队，不直接调用tick"""
        future = asyncio.Future()
        await self._input_queue.put((user_text, kwargs, future))
        return await future
    
    async def _tick_loop(self):
        """常驻tick循环 — 无外部输入时执行idle tick"""
        while self._running:
            t0 = time.perf_counter()
            
            if not self._input_queue.empty():
                user_text, kwargs, future = await self._input_queue.get()
                result = await self._run_active_tick(user_text, **kwargs)
                future.set_result(result)
            else:
                await self._run_idle_tick()  # SA衰减 + C*回灌
            
            elapsed_ms = (time.perf_counter() - t0) * 1000
            sleep_ms = max(0, 100 - elapsed_ms)  # 目标100ms一tick
            await asyncio.sleep(sleep_ms / 1000)
    
    async def _run_idle_tick(self):
        """idle tick: SA衰减 + C*回灌。不调感受器。CPU<5%目标。"""
        await self._decay_occurrences()
        await self._apply_cstar_feedback_idle()
```

**验收（自动化）:**
```sql
-- 启动后60秒不发消息:
SELECT count(*) FROM occurrences 
WHERE created_at > strftime('%s','now') - 60;
-- 期望 > 0 (idle tick的C*注入记录)
```

---

### 任务P1-4：wall-clock性能预算 + 超预算降级

**文件:** `runtime.py`  
**修复方案:**
```python
import time

TICK_BUDGET_MS = 100  # 默认预算，可通过config覆盖

class TickBudget:
    def __init__(self, budget_ms: float = TICK_BUDGET_MS):
        self._deadline = time.perf_counter() + budget_ms / 1000
        self.segments: list[tuple[str, float]] = []
        self._stage_start = time.perf_counter()
    
    def checkpoint(self, stage_name: str):
        now = time.perf_counter()
        self.segments.append((stage_name, (now - self._stage_start) * 1000))
        self._stage_start = now
    
    def is_overbudget(self) -> bool:
        return time.perf_counter() > self._deadline
    
    def remaining_ms(self) -> float:
        return max(0.0, (self._deadline - time.perf_counter()) * 1000)

# 在tick入口创建预算对象:
budget = TickBudget(budget_ms=config.get("tick_budget_ms", TICK_BUDGET_MS))

# 超预算降级（替换现有break逻辑）:
if budget.is_overbudget():
    K_factor = max(0.1, K_factor * 0.5)      # K减半
    request_teacher_bias = True               # request_teacher偏置
    event.tick_segments = budget.segments     # 写入分段耗时
    break
```

**验收（自动化）:**
```python
# 强制单tick耗时>150ms，验证降级行为
config["tick_budget_ms"] = 50  # 极短预算
result = runtime.run_turn("测试")
assert result.k_factor < original_k_factor  # K减半验证
```

---

## 五、P2：B召回残差三路能量 + C*注入（2天）

### 任务P2-1：B召回残差中和三路能量实现

**文件:** `cognitive_cycle.py:759-770`  
**修复方案（三路机制）：**
```python
@dataclass
class MatchedPair:
    memory_occ_id: int
    reality_occ_id: int
    overlap_r: float
    overlap_v: float
    overlap_score: float

@dataclass  
class SAUnit:
    sa_type_id: int
    r: float
    v: float

@dataclass
class StructuralBResult:
    matched_pairs: list[MatchedPair]     # 路1：完全匹配
    memory_only_units: list[SAUnit]      # 路2：记忆多余→虚能量
    reality_only_units: list[SAUnit]     # 路3：现实多余→实能量保留

def _neutralized_occurrences(self, recall: StructuralBResult, pool: StatePool):
    for m in recall.matched_pairs:
        # 路1：中和
        pool.modify_occurrence(m.memory_occ_id, delta_r=-m.overlap_r, delta_v=-m.overlap_v)
    
    for u in recall.memory_only_units:
        # 路2：记忆多余 → 转虚能量（"想到了但没发生"）
        pool.inject_virtual(u.sa_type_id, v=u.r * 0.3, source="b_memory_excess")
    
    # 路3：reality_only_units 不操作，保留在池中自然衰减
```

**验收（自动化）：**
```python
# 构造一个有一半记忆匹配、一半记忆多余的场景
# 验证memory_only部分产生了虚能量SA
virtual_sas = pool.get_by_source("b_memory_excess")
assert len(virtual_sas) > 0
assert all(sa.v > 0 and sa.r == 0 for sa in virtual_sas)
```

---

### 任务P2-2：C*虚能量注入状态池

**文件:** `cognitive_cycle.py:554`  
**修复方案（一行修复）：**
```python
cstar_value = self._compute_cstar(prediction_error, reward)
event.cstar_value = cstar_value
# 新增：注入状态池
if cstar_value > 0.05:
    _inject_cstar_to_pool(db_path, tick=event.tick, v=cstar_value)
```

**验收（自动化）：**
```sql
SELECT count(*) FROM occurrences o
JOIN sa_types s ON o.sa_type_id = s.id
WHERE s.name LIKE 'cstar::%' AND o.v > 0;
-- 期望 > 0（每次tick误差超阈值均注入）
```

---

## 六、P3：L1/L2在线学习修复（3天）

### 任务P3-1：L1实时在线梯度更新（最高优先）

**文件:** `experience_log.py`  
**问题:** L1只有批量rebuild，无实时路径  
**修复方案 — 新增函数，在每次共现时调用：**

```python
ALPHA_L1 = 0.01  # 白皮书固定学习率，替换退火公式

def l1_online_update(
    db_path: str,
    sa_type_id_a: int,
    sa_type_id_b: int,
    tick: int,
) -> None:
    """每次两个SA共现时立即调用。对称双向更新（A→B，B→A）。"""
    vec_a = _load_l1_vector(db_path, sa_type_id_a)
    vec_b = _load_l1_vector(db_path, sa_type_id_b)
    if vec_a is None or vec_b is None:
        return  # 尚无向量的SA跳过

    # 余弦相似度驱动的梯度：将两向量拉近
    grad_a = ALPHA_L1 * (vec_b - vec_a)  # A向B靠近
    grad_b = ALPHA_L1 * (vec_a - vec_b)  # B向A靠近

    new_a = _normalize(vec_a + grad_a)
    new_b = _normalize(vec_b + grad_b)

    _save_l1_vector(db_path, sa_type_id_a, new_a)
    _save_l1_vector(db_path, sa_type_id_b, new_b)
```

**调用点：** 在 `experience_flow.py` 中每次共现事件入库后调用：
```python
# experience_flow.py — 共现窗口处理完成后
for (sa_a, sa_b) in cooccurrence_pairs_this_tick:
    l1_online_update(db_path, sa_a.sa_type_id, sa_b.sa_type_id, tick)
```

**同步修复DEFECT-L1-4 — 召回时传入L1相似度：**
```python
# experience_flow.py:564-596
support = compute_unified_experience_support(
    ...,
    l1_vector_similarity=_compute_l1_similarity(sa_a, sa_b, db_path),  # 修复：实际传值
)
```

**验收（自动化）：**
```python
# 教学10轮后，两个共现SA的L1向量余弦相似度应>0.3
cos_sim = compute_l1_cosine(db_path, sa_id_a, sa_id_b)
assert cos_sim > 0.3
```

---

### 任务P3-2：L2升级为group-level超图共现

**文件:** `experience_log.py:1091-1133`  
**问题:** 当前是pair-level线性对，需改为同tick所有活跃SA作为组  
**修复方案 — 重构L2记录结构：**

```sql
-- 新增group-level共现表
CREATE TABLE IF NOT EXISTS l2_cooccurrence_group (
    group_id    INTEGER PRIMARY KEY AUTOINCREMENT,
    tick        INTEGER NOT NULL,
    sa_ids      TEXT NOT NULL,  -- JSON数组，同tick所有活跃SA的id列表
    modalities  TEXT NOT NULL,  -- JSON数组，各SA的模态标签
    created_at  INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);
CREATE INDEX IF NOT EXISTS idx_l2_group_tick ON l2_cooccurrence_group(tick);
```

```python
def l2_online_group_record(
    db_path: str,
    tick: int,
    active_sa_ids: list[int],
    modalities: list[str],
) -> None:
    """每tick结束时，将所有有能量的SA作为一个组记录共现。"""
    if len(active_sa_ids) < 2:
        return
    import json
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO l2_cooccurrence_group (tick, sa_ids, modalities) VALUES (?,?,?)",
            (tick, json.dumps(active_sa_ids), json.dumps(modalities))
        )
```

**调用点：** 在每个tick结束时：
```python
# runtime.py — tick结束后
active_sas = pool.get_active_above_threshold(r_threshold=0.05)
l2_online_group_record(
    db_path, tick=current_tick,
    active_sa_ids=[sa.sa_type_id for sa in active_sas],
    modalities=[sa.modality for sa in active_sas],
)
```

**同步修复DEFECT-COV-1 — 共现统计窗口加入行动事件：**
```python
# experience_flow.py:88-99 的 event_kind IN 列表
EVENT_KINDS_FOR_COOCCURRENCE = (
    "experience_alignment",
    "experience_observation", 
    "action_outcome",       # 新增行动事件
    "commit_reply_event",   # 新增提交事件
    "feeling_update",       # 新增感受事件
    "visual_receptor_tick", # 新增视觉事件
    "audio_receptor_tick",  # 新增音频事件
)
```

**验收（自动化）：**
```sql
-- 执行一次完整对话轮次后
SELECT count(*) FROM l2_cooccurrence_group WHERE tick = ?;
-- 期望 > 0（每tick至少一个group记录）

-- 验证包含行动SA
SELECT sa_ids FROM l2_cooccurrence_group WHERE tick = ?;
-- 返回的JSON应包含action::类SA的id
```

---

## 七、P4：范式动态注册 + 跨turn情感持久化（2-3天）

### 任务P4-1：范式注册表建立与硬编码消除

**文件:** `paradigm_process.py:47-56, 73, 127-146, 211`  
**修复方案 — 新增DB注册表：**

```sql
CREATE TABLE IF NOT EXISTS phase20_7_paradigm_registry (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    paradigm_key      TEXT NOT NULL UNIQUE,
    state_set         TEXT NOT NULL,  -- JSON数组
    anchor_set        TEXT NOT NULL,  -- JSON数组
    content_src_set   TEXT NOT NULL,  -- JSON数组
    trigger_condition TEXT,           -- JSON或NULL
    is_seed           INTEGER NOT NULL DEFAULT 0,
    created_at        INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);

CREATE TABLE IF NOT EXISTS phase20_7_anchor_registry (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    anchor_name   TEXT NOT NULL UNIQUE,
    resolve_spec  TEXT NOT NULL,  -- JSON: {"type": "coordinate", "coords": [0,2]}
    description   TEXT
);
```

**修复 derive_paradigm_key()（paradigm_process.py:73）：**
```python
# 旧：return "digit_pair_colproc"
# 新：
def derive_paradigm_key(db_path: str, current_state: dict) -> str:
    rows = _query_paradigm_registry(db_path)
    for row in rows:
        if _matches_trigger_condition(row.trigger_condition, current_state):
            return row.paradigm_key
    return ""  # 无匹配范式
```

**修复 resolve_anchor()（paradigm_process.py:127-146）：**
```python
# 旧：if/elif分发表
# 新：
def resolve_anchor(db_path: str, anchor_name: str) -> tuple:
    row = _query_anchor_registry(db_path, anchor_name)
    if row is None:
        raise ValueError(f"未注册的锚点: {anchor_name}")
    spec = json.loads(row.resolve_spec)
    return tuple(spec["coords"])  # 从注册表读取坐标
```

**修复 query_paradigm_next_steps()（paradigm_process.py:211）：**
```python
# 删除 `anchor not in ANCHORS` 静态白名单过滤
# 改为：查注册表的anchor_set，包含动态注册锚点
```

**迁移：** 将当前硬编码的 digit_pair_colproc 数据作为种子插入注册表（is_seed=1）。

**验收（自动化）：**
```python
# 运行时注册新范式，不修改任何Python文件
register_paradigm(db_path, paradigm_key="test_addition", 
                  state_set=["num_a","num_b"], anchor_set=["result"])
result = derive_paradigm_key(db_path, current_state={"active": ["num_a","num_b"]})
assert result == "test_addition"
```

---

### 任务P4-2：跨turn情感持久化

**文件:** `models.py`（新增表已在P0创建），`runtime.py`（turn开始/结束逻辑）  
**修复方案：**

```python
# runtime.py — turn开始时从快照恢复
def _load_emotion_state(db_path: str, turn_id: str) -> EmotionField:
    row = db_query_one(
        "SELECT * FROM phase20_7_emotion_snapshot ORDER BY tick DESC LIMIT 1"
    )
    if row:
        return EmotionField.from_dict(row)
    return EmotionField()  # 全新AP用默认值

# runtime.py — turn结束时写入快照
def _save_emotion_state(db_path: str, turn_id: str, emotion: EmotionField, tick: int):
    db_execute(
        "INSERT INTO phase20_7_emotion_snapshot (tick, turn_id, da, adr, oxy, ser, end_val, cor, nov, foc) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (tick, turn_id, emotion.DA, emotion.ADR, emotion.OXY, emotion.SER, 
         emotion.END, emotion.COR, emotion.NOV, emotion.FOC)
    )

# runtime.py — 时间衰减（每次turn开始时应用）
def _apply_emotion_time_decay(emotion: EmotionField, seconds_since_last: float) -> EmotionField:
    minutes = seconds_since_last / 60
    return EmotionField(
        DA=emotion.DA * (0.97 ** minutes),
        COR=emotion.COR + (0.5 - emotion.COR) * min(1.0, 0.05 * minutes),  # 向基线恢复5%/分钟
        SER=emotion.SER + (0.5 - emotion.SER) * min(1.0, 0.03 * minutes),  # 向基线恢复3%/分钟
        NOV=max(0.1, emotion.NOV * (0.95 ** minutes)),   # 新奇感随时间衰退
        OXY=emotion.OXY,  # 催产素（连接感）相对稳定
        ADR=emotion.ADR * (0.9 ** minutes),              # 应激快速衰减
        END=emotion.END * (0.98 ** minutes),
        FOC=emotion.FOC * (0.9 ** minutes),              # 专注随时间分散
    ).clamp()
```

**验收（自动化）：**
```python
# 3轮对话，第3轮情感值与第1轮可量化不同（不是重置）
e1 = get_emotion_after_turn(1)
e3 = get_emotion_after_turn(3)
delta = sum(abs(getattr(e3,f) - getattr(e1,f)) for f in ['DA','COR','NOV'])
assert delta > 0.05  # 有可量化变化
```

---

## 八、P5：视觉感受器修复（2天）

### 任务P5-1：视觉SA虚能量与FOC耦合

**文件:** `vision.py:1033/1048`（v=0.0硬编码），`vision.py:1134-1148`（_inject_visual_state）

```python
def _inject_visual_state(db_path, tick, clarity, novelty, emotion: EmotionField):
    real_energy = clarity * 0.8 + novelty * 0.2
    virtual_energy = emotion.FOC * 0.5 * novelty  # 高专注+高新奇→高虚能量
    sa_type_id = upsert_sa_type(db_path, f"visual::scene::{scene_hash}", modality="visual")
    insert_occurrence(db_path, sa_type_id=sa_type_id, tick=tick,
                      r=real_energy, v=virtual_energy, a=1.0, source="visual_receptor")
```

**验收（自动化）：**
```python
occ = get_latest_visual_occurrence(db_path)
assert occ.r > 0.5   # 清晰度映射到实能量
assert occ.v > 0.1   # FOC耦合到虚能量（不再是0.0）
```

---

### 任务P5-2：视觉feeling::* SA注入

**文件:** `vision.py`（run_visual_receptor_ticks末尾追加）

```python
def _inject_visual_feelings(db_path, tick, novelty, clarity, complexity):
    feelings = []
    if novelty > 0.6:
        feelings.append(("feeling::curious", novelty * 0.8))
    if clarity > 0.8:
        feelings.append(("feeling::focused", clarity * 0.6))
    if complexity > 0.7:
        feelings.append(("feeling::overwhelmed", complexity * 0.4))
    for sa_name, r_energy in feelings:
        sa_id = upsert_sa_type(db_path, sa_name, modality="feeling")
        insert_occurrence(db_path, sa_type_id=sa_id, tick=tick,
                          r=r_energy, v=0.0, a=1.0, source="visual_feeling")
```

**验收（自动化）：**
```sql
SELECT count(*) FROM occurrences o
JOIN sa_types s ON o.sa_type_id = s.id
WHERE s.name LIKE 'feeling::%' AND o.source = 'visual_feeling';
-- 处理一张新奇图像后期望 > 0
```

---

## 九、P5续：音频感受器修复（3天）

### 任务P5-3：频率带特征提取

**文件:** `audio.py:422-434`（_inject_audio_state）

```python
def _extract_audio_features(wav_path: str) -> dict:
    import wave, numpy as np
    with wave.open(wav_path, 'rb') as wf:
        samples = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(float)/32768.0
        sr = wf.getframerate()
    fft = np.abs(np.fft.rfft(samples))
    freqs = np.fft.rfftfreq(len(samples), 1/sr)
    mx = fft.max() + 1e-9
    return {
        "low_band":  float(fft[(freqs>=20)&(freqs<300)].mean() / mx),
        "mid_band":  float(fft[(freqs>=300)&(freqs<3000)].mean() / mx),
        "high_band": float(fft[(freqs>=3000)&(freqs<8000)].mean() / mx),
        "amplitude": float(np.abs(samples).mean()),
        "duration_ms": len(samples)/sr*1000,
    }

def _inject_audio_state(db_path, tick, wav_path, emotion: EmotionField):
    f = _extract_audio_features(wav_path)
    for band in ("low_band", "mid_band", "high_band"):
        if f[band] < 0.05: continue
        sa_id = upsert_sa_type(db_path, f"audio_unit::{band}", modality="audio")
        insert_occurrence(db_path, sa_type_id=sa_id, tick=tick,
                          r=f[band], v=0.0, a=1.0, source="audio_receptor")
    _inject_audio_feelings(db_path, tick, f)
```

**验收（自动化）：**
```sql
SELECT count(*) FROM occurrences o
JOIN sa_types s ON o.sa_type_id = s.id
WHERE s.name LIKE 'audio_unit::%';
-- 处理音频文件后期望 > 0
```

---

### 任务P5-4：TTS输出回路修复

**文件:** `audio.py:283-340`（TTS合成后追加）

```python
async def _synthesize_and_replay(db_path, tick, text, emotion: EmotionField):
    wav_path = await _tts_synthesize(text)          # 现有合成逻辑不变
    # 新增：AP听到自己说话
    _inject_audio_state(db_path, tick=tick+1, wav_path=wav_path, emotion=emotion)
```

**验收（自动化）：**
```sql
SELECT count(*) FROM occurrences o
JOIN sa_types s ON o.sa_type_id = s.id
WHERE s.name LIKE 'audio_unit::%' AND o.source = 'audio_receptor' AND o.tick > ?;
-- TTS合成后期望 > 0
```

---

## 十、v0.2 总体验收门控

| 编号 | 验收条件 | 对应修复 |
|---|---|---|
| G1 | action::类SA在occurrences中count>0（执行1次行动后） | P1-1 |
| G2 | 60秒idle后occurrences新增C*注入记录 | P1-3 |
| G3 | 超预算场景K_factor减半触发 | P1-4 |
| G4 | 3轮对话情感delta>0.05（不重置） | P4-2 |
| G5 | no_write_reason事件仍有feeling::*注入 | P0-1 |
| G6 | B召回后b_memory_excess虚能量SA>0 | P2-1 |
| G7 | cstar::类SA在occurrences中count>0 | P2-2 |
| G8 | 10轮共现后L1余弦相似度>0.3 | P3-1 |
| G9 | l2_cooccurrence_group每tick有记录且含action::类SA | P3-2 |
| G10 | 运行时注册新范式后derive_paradigm_key正确触发 | P4-1 |
| G11 | 视觉SA的v字段>0（不再硬编码0.0） | P5-1 |
| G12 | 音频处理后audio_unit::类SA存在 | P5-3 |
| G13 | TTS输出后同tick+1有audio_unit::类SA | P5-4 |

**回归测试（无回归才通过）：**
- [ ] `pytest tests/` 全通过
- [ ] `pytest GL_TaskBuilder/tests/` 全通过（两套分开跑）
- [ ] Phase 16 Styled Corpus 15/15
- [ ] Phase 19 同域LOO 10/10

---

## 十一、工作量修订说明

原路线图v0.2预估~2周。实际审查后：

| 原标注"已实现" | 实际状态 | 额外工作 |
|---|---|---|
| 8通道NT ✓ | 完全未实现 | +2天 |
| C*回灌 ✓ | 计算但未注入 | +1天 |
| L1在线 ✓ | 仅离线批量重建 | +2天 |
| asyncio常驻tick | 架构变更，影响全部调用点 | +3天 |
| 范式硬编码1处 | 实际4处，需全文重构 | +1天 |

**修订后v0.2估算：约3周**（原2周）。v0.3可在v0.2部分门控通过后并行启动以减少延误。

---

*本计划覆盖全部18项CRITICAL缺陷，修复方案均为方向示意，实际实现前应通过回归测试验证。*
