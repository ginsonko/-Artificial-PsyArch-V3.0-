# Phase20.13b — L3 行动后果在线嵌入

日期: 2026-06-30
子项目: APV3.0test
白皮书依据: §1657 L3 行动后果层 / §173.2 L3 帮 action competition / §173.3-§173.5 数学形式 / §1726 行动失败降低 drive / §1727/§37.3 源分化防混淆 / §35.4 红线 / §24/§132 真相源

## 1. 目标

实现白皮书三层在线嵌入的最后一步：**L3 行动后果层**（§1657"学场景-行动-奖惩后果，支持 Agent/具身"；§173.7"最后实现 L3，接 action competition"）。L1（现状召回）、L2（时序/因果）已闭合；L3 填既有 `vector_l3` 列，由行动结局驱动 triplet/退火更新，注入为 action_competition 的调制（§1726"行动失败会降低相同状态下该行动 drive"）。

**勿增实体**：只填既有 `vector_l3` BLOB 列（models.py:161 已存在），不新增表/列/认知实体/路由。L3 edge sa_type 只是既有列的键，与 L1/L2 同构。

## 2. 白皮书数学形式（§173.3 line 7178-7181）

```
L3 行动后果更新:
  outcome_value = reward_prediction - punish_prediction
  z_action_context <- z_action_context + lr_L3 * outcome_value * direction_to_success_or_failure
```
退火（§173.5）：`lr_t = lr_0 / sqrt(1 + support_count)`，与 L1/L2 同范式。
负样本（§173.4）：行动了但失败 → 负更新（降低该 state-action 的 z 向量）。
§1726：行动失败降低相同状态下该行动 drive。

## 3. 具体设计

### 3.1 L3 edge = (state_signature, action_type) → outcome 向量
- **state** = observation.signature（教师反馈所回应的输入上下文签名，即"场景"）。
  对抗性决策：不用全 tick action_records 恢复（含 idle_observe/move_focus 等内部 tick 动作，噪声大、易把"想象火躲开"和"真实火躲开"混成同一行动后果，违反 §1727/§37.3）。用 feedback 时的 observation.signature 作为 state——这是教师正在评价 AP 回应的那个场景，语义干净。
- **action** = AP 对该 state 的外向动作类别。在 `_record_teacher_feedback` 时，AP 已对 observation 做了回应（write_cell 生成回复 / request_teacher 请求教师 / maintain_unclosed 等）。L3 学的是"在这个场景下，做这类动作的后果"。
- **outcome** = `reward_mag - punish_mag`（§173.3 outcome_value）。
- **edge sa_type_id** = `l3_edge_sa_type_id(state_signature, action_type)`，存入既有 `vector_l3` 列。substrate="action_edge", modality="structure"。

### 3.2 L3 向量函数（experience_log.py，紧邻 L2 块）
与 L1/L2 同构的 7 个函数 + 常量：
```python
L3_VECTOR_DIM = 24
L3_VECTOR_INDEX_NAME = "l3_vector_index/v1"
L3_RELATION_ACTION_CONSEQUENCE = "action_consequence"

def l3_initial_vector_for(edge_sa_type_id) -> list[float]:  # 确定性初始向量(内容寻址)
def l3_action_code(state_signature, action_type) -> list[float]:  # 关系编码
def l3_edge_sa_type_id(state_signature, action_type) -> str:  # 键
def l3_vector_to_bytes(support_count, vector) -> bytes:  # 序列化(同 L1/L2)
def bytes_to_l3_vector(raw) -> tuple[int, list[float]]:  # 反序列化
def l3_compose(state_vec, action_type, outcome_vec) -> list[float]:  # compose(§173.3)
def load_sa_type_vector_l3(conn, sa_type_ids) -> dict:  # 读取+回退初始
def update_sa_type_vector_l3(conn, *, sa_type_id, support_count, vector, tick):  # 写入
def l3_action_consequence_update_vector(edge_vector, *, action_context, outcome_value, support_count) -> tuple[list[float], int]:
    # §173.3: z_action_context += lr_L3 * outcome_value * direction
    # lr 退火 §173.5: lr_min+(lr_max-lr_min)*exp(-support_count/tau)
    # direction = normalize(action_context - edge_vector) (向成功/失败方向)
    # outcome_value>0 (奖励) 拉向 action_context (该 state-action 成功模式)
    # outcome_value<0 (惩罚) 推离 (§173.4 行动失败负更新)
```
**direction 的设计**（关键，对抗性自审重点）：
- `action_context` = compose(state 的哈希码向量, action_type 码) —— 代表"在这个场景做这个动作"的目标模式。
- outcome>0：`z_edge += lr * outcome * (action_context - z_edge)` —— 向成功模式靠近。
- outcome<0：`z_edge += lr * outcome * (z_edge - action_context)` —— 即 `z_edge -= lr*|outcome|*(action_context - z_edge)`，推离失败模式。等价于 §173.4 负更新。
- 与 L2 `l2_structure_update_vector` 同形（`z_edge + lr*support*(ctx-z_edge)`），只是 support 换成可负的 outcome_value。

### 3.3 运行时更新触发（runtime.py `_record_teacher_feedback`）
在 L1/L2 更新之后（line ~2037 后）新增 `_apply_l3_action_consequence_update`：
```python
def _apply_l3_action_consequence_update(conn, pool, *, session_id, tick, observation, feedback, output_intent):
    """白皮书 §173.3 L3 行动后果更新. 在教师反馈时触发:
    state=observation.signature, action=output_intent(AP对此场景的回应动作),
    outcome=reward-punish. 更新 (state,action) edge 的 vector_l3.
    """
```
- **output_intent 来源**：AP 在该 turn 选定的外向动作（write_cell/request_teacher/maintain_unclosed/integrate_feedback）。这是 AP 对 observation 的回应，教师反馈正是评价这个回应。需从 turn 上下文传入 output_intent。
- **guardrail**：`projection_only=True, creates_reply_candidate=False, writes_answer_directly=False`（同 L1/L2，§35.4 红线1：在线嵌入不替代显式通道）。
- 返回 delta dict（同 L1/L2 形状），加入 turn 的 learning_deltas。

### 3.4 action_competition 调制（runtime.py `_competition`）
§1726"行动失败降低相同状态下该行动 drive"。在 `_competition` 返回 sorted_rows 前，加 L3 调制 pass（仿 `_apply_learning_protocol_competition_modulation`）：
```python
def _apply_l3_action_consequence_modulation(conn, *, state_signature, competition_rows):
    """§1726: 用 L3 (state,action) 向量调制各 action 的 drive.
    查询当前 state 下各 action 的 L3 向量与"成功模式"的相似度,
    成功过的 action drive 上调, 失败过的下调. 乘性调制, 不改 selected, 不新增行.
    """
```
- 对每个 competition row（action_type），查 `l3_edge_sa_type_id(state_signature, action_type)` 的 vector_l3。
- **对抗性自审关键修正**：support_count=0（未学）时乘子=**1.0 中性**，不调制。否则初始向量与锚点 cosine≈0 → 乘子≈0.7，会在 L3 学到任何东西之前就把所有 action drive 压低 20-30%，破坏首教和未知请求教师（三组样本组2）。这是 §173.6"初学时易被一次经验影响"的反面——**学习之前不应有任何影响**。
- support_count>0（已学）时：用该向量与 action 的"成功锚点"的 cosine 作为 outcome_expectation（§173.3 outcome_value 的预测），`drive *= (0.7 + 0.6 * outcome_expectation)`。
  - 学过且成功（向量拉向锚点）→ cosine 高 → 乘子>1 上调；
  - 学过且失败（向量推离锚点）→ cosine 低 → 乘子<1 下调（§1726）；
  - **乘子范围 [0.7, 1.3] 有界、不归零**（§1742 红线：不许某候选压倒所有上下文，也不许被完全抹杀）。
- `_competition` 需新增可选参数 `l3_modulation_context: dict|None`（含 state_signature + conn），默认 None 时不调制（保持现有行为，零回归风险）。
- **关键**：调制只调整 drive 数值，不改 `selected` 字段、不新增/删除行、不改变排序逻辑的结构。selected 仍由 AP 主闭环决定，L3 只调制倾向（§370 行动通过 drive 竞争，L3 是 drive 的经验调制源）。

### 3.5 可重建（experience_log.py `rebuild_phase20_7_indexes`）
在 L2 replay 之后新增 L3 replay：
- 真相源：`phase20_7_action_records`（selected=1 的 action_type + tick）+ `phase20_7_experience_events`（teacher_feedback_event 的 reward/punish + 对应 observation 的 signature）。
- 按 created_at 升序重放：每个 teacher_feedback_event，恢复其 state（observation.signature）+ action（该 state 下最近的 selected 外向 action）+ outcome（reward-punish），重跑 `l3_action_consequence_update_vector`。
- 写 `l3_vector_index/v1` 到 index_registry（同 L1/L2）。
- **对抗性注意**：rebuild 时无 live output_intent，需从 action_records 恢复 action_type。用"该 session 中、tick<=feedback_tick、selected=1、action_type∈外向动作集"的最近一条。这比运行时弱（运行时有确切 output_intent），但 rebuild 是派生重建、允许近似（§132 索引可重建，非真相源）。

### 3.6 red-line / guardrail 对齐（与 L1/L2 测试同构）
- far-text no-leak：无关 state 不产生 L3 调制（无匹配 edge）。
- no-completion：不 emit `l3_converged`/`l1_l2_l3_complete` 等禁词。
- projection_only / creates_reply_candidate=False / writes_answer_directly=False。
- 不替代显式通道（§35.4 红线1）：L3 只调制 drive，不直接选 action、不直接写答案。

## 4. 对抗性自审结论（coding 前）

1. **首教/未知中性（最关键）**：初版设计让未学 edge 也调制（乘子 0.7-0.8），会压低首教和未知请求教师。**修正**：support_count=0 时乘子=1.0。已用脚本验证：未学→1.0、成功→1.3、失败→0.7、不归零。
2. **output_intent 可达**：`run_phase20_7_turn` line 349 定义 `output_intent`，在 `_record_teacher_feedback`(line 518) 调用时已是 AP 对当前 observation 的选定动作，可传入。✓
3. **_competition 纯函数性**：`_competition` 无 conn，L3 需查 DB。方案：新增可选参数 `l3_context: dict|None=None`，含 conn+state_signature。**只在主外向动作点传入**（611/887/1002 等），不传 31 个全部调用点（idle/内部 tick 不需要 L3——L3 关心外向后果）。默认 None→不调制→零回归。✓
4. **rebuild 近似性**：rebuild 时无 live output_intent，从 action_records 恢复。rebuild 是派生重建、允许近似（§132 索引可重建非真相源）。运行时用确切 output_intent，rebuild 用"该 session 最近 selected 外向 action"。✓
5. **§1727 源分化**：L3 state 用 observation.signature（教师正在评价的场景），不用全 tick action（含 idle/move_focus 内部动作），避免"想象火躲开/真实火躲开"混成同一行动后果。✓
6. **不改 selected**：L3 只乘性调制 drive 数值，不改 `selected` 字段、不增删行。selected 仍由 AP 主闭环决定。✓
7. **不替换 write_drive 魔数**：本步只新增 L3 调制 pass，不删旧系数（替换风险大，留 L3 验收后逐步）。✓

## 5. 不做什么（边界）

- **不新增表/列**：vector_l3 已存在。
- **不新增认知实体**：L3 是既有 sa_type 列上的派生向量，不是"决策模块""后果评估器"。
- **不改 `_competition` 的 selected 逻辑**：L3 只乘性调制 drive，不改选中。
- **不替换 `_write_drive_from_recall_state` 魔数系数**：那是 L3 的下游消费点，但替换风险大，本步只"新增 L3 调制 pass"，不删旧系数。魔数替换留到 L3 验收后逐步进行。
- **不上六阶段协议**：那是 L3 之后的下一步。
- **L3 state 不用全 tick action**：避免内部动作污染（§1727）。

## 5. 验收标准
1. L3 新测试（~6 个，镜像 L2 测试结构）：
   - 教学后填 vector_l3 + 发 l3 delta
   - outcome 正负方向正确（奖励拉近、惩罚推离）
   - rebuild 可重建 l3_vector_index
   - far-text no-leak
   - action_competition 调制存在但不改 selected
   - no over-claiming
2. 三组样本稳（泛化/纯文本未知/视觉引用）。
3. 全套回归通过（≥235）。
4. red_line_check_v14 main gate 通过。
5. byte-compile + node --check。
6. 污染 DB 不崩。
