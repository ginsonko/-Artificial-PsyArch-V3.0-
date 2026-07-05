# Phase20.13b — L3 行动后果在线嵌入 · 最终汇总报告

日期: 2026-06-30
子项目: APV3.0test
白皮书依据: §1657 / §173.2 / §173.3-§173.5 / §1726 / §1727/§37.3 / §33.1 / §35.4 / §1742 / §132 / §173.6
设计文档: `docs/Design_Phase20_13b_L3ActionConsequenceEmbedding_20260630.md`

---

## 1. 做了什么

实现了白皮书三层在线嵌入（§173.7"最后实现 L3"）的最后一步：**L3 行动后果层**。L1（现状召回）、L2（时序/因果）已闭合；L3 填既有 `vector_l3` BLOB 列（`models.py:161` 早已存在），由行动结局驱动 triplet/退火更新，注入为 `action_competition` 的有界 drive 调制（§1726"行动失败会降低相同状态下该行动 drive"）。

**不增实体**：无新表/列/认知实体/路由/答案表/正则路由。L3 edge 的 `sa_type` 只是既有 `vector_l3` 列的键，与 L1/L2 同构；向量是派生可重建的，非真相源（§24/§132）。

## 2. 落地文件

| 文件 | 改动 |
|---|---|
| `apv3test/runtime/phase20_7/experience_log.py` | L3 向量函数块（`l3_action_consequence_update_vector` 等同 L1/L2 同构 7 函数+常量）；`L3_OUTWARD_ACTION_TYPES` 单一定义点；`rebuild_phase20_7_indexes` 内 L3 replay 段；SQL 参数化（见 §5） |
| `apv3test/runtime/phase20_7/runtime.py` | `_apply_l3_action_consequence_update`（live 触发，L1/L2 之后）；`_apply_l3_action_consequence_modulation`（§1726 drive 调制）；`_competition` 新增可选 `l3_context`；2 个外向动作接入点（write_cell/integrate_feedback）传入 `l3_context`；delta 收纳 `l3_action_delta` |
| `apv3test/runtime/phase20_7/__init__.py` | L3 全部导出 |
| `tests/test_phase20_13b_l3_action_consequence_embedding.py` | 新增 6 个测试（镜像 L2 结构） |

## 3. 白皮书合规逐条核对

| 条款 | 落地 |
|---|---|
| §173.3 `z += lr*outcome*direction` | `l3_action_consequence_update_vector`: `value = edge[i] + lr*outcome*(ctx[i]-edge[i])` ✓ |
| §173.4 负向（失败推离） | outcome<0 时符号翻转，推离锚点 ✓ |
| §173.5 退火 `lr_min+(lr_max-lr_min)*exp(-sc/tau)` | 0.08/0.008/120，与 L1/L2 同范式 ✓ |
| §173.6 初学易被影响、熟练更稳 | sc 增大退火 ✓ |
| §1726 失败降低同 state 同 action drive | `_apply_l3_action_consequence_modulation` multiplier ✓ |
| §1727/§37.3 源分化 | state=observation.signature（不含 idle/move_focus 内部 tick），不混"想象火躲开/真实火躲开" ✓ |
| §33.1 triplet 非对称 | action_context（成功锚点）是参考、不被 co-update ✓ |
| §35.4 红线1 不替代显式通道 | L3 只调制 drive、不改 selected、不写答案、projection_only ✓ |
| §1742 有界不归零 | multiplier ∈ [0.7,1.3] ✓ |
| §132 索引可重建非真相源 | rebuild replay 从 action_records+experience_events 重建 ✓ |
| §173.7 退火 boost | `lr *= 1.0 + 0.6*abs(outcome)`，与 L1(0.6*pe)/L2(0.6*sup) 统一 ✓ |

## 4. 关键对抗性自审修正（coding 前 + coding 后）

1. **support_count=0 中性（最关键，coding 前）**：初版让未学 edge 也调制 → 乘子 0.7-0.8 → 会在 L3 学到任何东西之前压低所有 action drive 20-30%，破坏首教和未知请求教师。修正：support_count=0 → multiplier=1.0。脚本验证：未学→1.0、成功→1.3、失败→0.7、不归零。
2. **output_intent 可达性（coding 前）**：feedback 时 output_intent 常是内部动作（integrate_feedback/observe_text）。修正：加 action recovery——若 output_intent 不在外向集，从 action_records 查 `session_id, selected=1, tick<feedback_tick, action_type∈外向集` 的最近一条（教师正在评价的那个动作）。
3. **L3 仅在第二次 teach 触发（design 验收）**：第一次 teach 无前置外向 action，L3 无动作可归属——符合 §173.6"初学时经验少"。第二次起触发。测试 seeding 需同 session 教两次。
4. **SQL `%` 拼接隐患（coding 后审阅，用户要求"更优雅/无隐患"）**：发现 `_apply_l3_action_consequence_update` 和 rebuild replay 两处用 `% ",".join("'" + a + "'" ...)` 把 action_type 常量拼进 SQL `IN(...)`。虽然当前安全（frozenset 常量），但留有未来注入面且不优雅。**已修**：改为参数化占位符 `IN(?,?,?,...)` + 常量 tuple 作为绑定参数。复测 6/6 通过 — 行为不变，仅消除拼接。

## 5. 严谨验收（实际跑过，非承诺）

| 项 | 实际结果 |
|---|---|
| `byte-compile` 三个模块 | EXIT=0 ✓ |
| `tests/test_phase20_13b_l3_action_consequence_embedding.py` | **6/6 通过**（4.37s）✓ |
| L3 范围内权威复测（L1+L2+L2b+L2c+L3+stage2 索引，6 文件 33 测试） | **33/33 通过**（81s）✓ |
| phase20_2-7 stage 批（含 L1/L2/L3 embedding、stage2 索引，13 文件） | **86/86 通过**（230s）✓ |
| phase20_8b-o 批 | 56/56 ✓ |
| phase20_8p-r + 9*-p 批 | 61/61 ✓ |
| phase20_9q-z + 10* 批 | 43/43 ✓ |
| phase17-19 批 | 82/82 ✓ |
| phase8 其余 批 | 59/59 ✓ |
| phase1-7_2 批 | 128/128 ✓ |
| red_line_check_v14 main gate | `OK: All red line checks pass on runtime/cognitive` ✓ |
| 三组样本探针 | s1 教两次→commit_reply 记下；s2 未知"天气怎么样"→`我还不太知道怎么说`（中立）；s3 未知→中立 ✓ |
| 可重建 | `rebuild_phase20_7_indexes` 返回 `l3_vector_index.indexed_rows=1`，index_registry 标 rebuildable=1 ✓ |
| 污染库（`??` 模拟） | 三次都不崩、返回连贯回复 ✓ |
| node --check（上一篇报告所列） | 通过 ✓ |
| `from apv3test.runtime.phase20_7 import L3_*` | IMPORTS_OK ✓ |

**L3 路径全绿**：直接相关测试（embeddings + stage2）共 86+33 全部通过，0 回归。

## 6. 既存失败（与 L3 无关，需用户决策）

回归途中暴露 **4 个既存失败**，全部经核实与本次 L3 改动无关（我未碰 web_chat.py / phase20_open_dialogue / SQLiteRuntimeStore ontology / HTML 模板）：

1. `test_phase7_9_runtime_redline_has_no_multiturn_script_routes` — 红线测试禁止 `if record.phrase_kind` 出现在 `apv3test/runtime/*.py`，但 `phase20_open_dialogue.py:663` 含 `if record.phrase_kind != "teacher_event_cooccurrence"`（白名单过滤，按 kind 路由硬编码）。属于 phase20_open_dialogue 既有设计遗留。
2. `test_phase8_1_web_api_message_feedback_and_snapshot` — 测根路由 HTML 含 `"APV3 本地对话工作台"`（Phase8 旧模板）。实际根路由已演进到 `phase20_6_workbench.html`（标题"APV3 Phase20.6 真实运行工作台"）。Web app 演进 + 旧测试陈旧。
3. `test_phase8_11_web_api_serves_phase8_audit_payload` — 测 HTML 含 `"Phase8"`，根因同上（模板演进）。
4. `test_runtime_store_projects_ontology_tables` — `SQLiteRuntimeStore.ontology_counts` 多投影了 `phase20_6_fast_action_chains`/`phase20_6_slow_memory` 两表，contract 测试期望字典没这两键。属于 phase20_6 ontology 改动 + contract 未同步。

**判定**：这 4 个独立于 13b，且各自有"改测试以匹配演进"或"按 AP 主流重构该路由"的不同方向，需用户决策再处理（见下一步）。

## 7. 设计文档与实现的一致性

设计文档 §3（7 函数块 + 触发 + 调制 + replay）与落地一致。设计 §3.2 提到的 `l3_compose / l3_action_code` 在实现中收敛为单一 `l3_action_context_code`（成功锚点 = (state,action) 哈希码），更简洁且语义不变——这是审查后的优雅收敛，已记录在代码注释。

## 8. 勿增实体边界守住

- L1/L2/L3 在已有 `vector_l1/vector_l2/vector_l3` 列上，无新表。
- L3 edge sa_type 是既有列的键，非"后果评估器"新实体。
- 调制只乘性调 drive、不改 selected、不直接写答案（§35.4 红线1）。
- 无禁词：`l3_vector_converged / l1_l2_l3_complete / online_embedding_converged / six_stage_learning_complete` 均未出现。
- 三层 boost 系数统一 0.6（L1:prediction error / L2:support / L3:outcome magnitude）——同一学习率退火范式，无新超参实体。

## 9. 下一步

- **13b 已闭合**。三层在线嵌入（L1/L2/L3）全部落地，§173.7"最后实现 L3"完成。
- **建议**：把 4 个既存失败作为独立的 phase20.x 清理任务（非 13b 回归），方向待用户决策。
- **正式下一步**：Phase20.13c 六阶段学习协议（whitepaper §36），需独立走"设计→审查→落地→验收→报告"循环。这是用户本次明确期待的方向。