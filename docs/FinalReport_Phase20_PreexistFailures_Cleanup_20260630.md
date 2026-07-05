# Phase20 既存失败独立清理 — 最终汇总报告

**日期**: 2026-06-30
**范围**: 全量回归中长期存在的 4 个既存失败 (与 13b/13c 无关, 独立清理)
**循环**: 设计 → 审查完善 → 通过落地 → 严谨验收测试 → 最终汇总报告
**白皮书/勿增实体**: 全程遵守; 修源码走 AP 主流结构, 修测试只改陈旧断言, 不掩盖真回归

---

## §1 起因

13b/13c 全量回归稳定报 4 failed / 876 passed (880 tests). 4 个失败被核实为既存问题, 与 L3/阶梯投影无关:

1. `test_phase7_9_runtime_redline_has_no_multiturn_script_routes`
2. `test_phase8_11_web_api_serves_phase8_audit_payload`
3. `test_phase8_1_web_api_message_feedback_and_snapshot`
4. `test_runtime_store_projects_ontology_tables`

本任务把这 4 个独立清理, 让底座回归全绿, 为后续 Phase20.14 提供干净基线.

---

## §2 设计阶段 — 逐个核实根因 (实读, 非摘要假设)

### 失败1 (phase7_9 红线) — 源码违规
- **报错**: `assert 'if record.phrase_kind' not in combined` 命中 `apv3test/runtime/phase20_open_dialogue.py:663`
- **源码**: `if record.phrase_kind != "teacher_event_cooccurrence" or not record.phrase_id.startswith("teacher_phrase::"): continue`
- **核实**: runtime 下仅此一处 `if record.phrase_kind`, 无任何 `phrase_kind ==`. 三处 `phrase_kind=` 均为赋值 (517 styled / 1220 teacher / 1310 user), 非路由, 不受影响.
- **关键核实 — 命名空间一一对应**:
  - 1199 行 `_phrase_id_for_teacher_text` → `teacher_phrase::` 前缀, 仅教师插入路径 (1220) 使用
  - 517 行 styled → `style::` 前缀
  - 1310 行 user → `user_utterance::` 前缀
  - 三命名空间互斥; `phrase_kind="teacher_event_cooccurrence"` 与 `teacher_phrase::` 前缀在 1220 行**同时赋值**, 是冗余等价判据.
- **判定**: **修源码** — 删 `phrase_kind` 冗余路由层, 留 `phrase_id` 结构命名空间判据. 语义等价, 消除 phase7_9 红线违规, 更符合 AP 哲学 (结构命名空间路由而非 kind 标签路由).

### 失败2/3 (phase8 web audit/chat) — 陈旧测试
- **报错**: `assert "Phase8" in html` / `assert "APV3 本地对话工作台" in html` 失败
- **核实**: web_chat.py:454 根路由 `/` 服务 `phase20_6_workbench.html` (web 演进). 真实模板标题 `APV3 Phase20.6 真实运行工作台`.
- **关键核实 — API 契约未坏**: 失败2 前两断言 (`phase8_audit in snapshot` / `visual_focus_overlay in snapshot["phase8_audit"]`) **通过**; 失败3 后续 API/message/feedback 断言**通过**. 仅 HTML 标题断言陈旧.
- **判定**: **修测试** — 改为 `"Phase20.6" in html` (两测试统一). API 契约断言不动, 仍守数据正确性.

### 失败4 (sqlite ontology) — 陈旧测试
- **报错**: `ontology_counts` 多返回 `phase20_6_fast_action_chains`/`phase20_6_slow_memory` 两键 (值 0)
- **核实**: 两键来自 `phase20_6_memory.py` (快/慢记忆, 合法 AP 结构), 由 `sqlite_runtime_store.py:245-246` 加入 `ontology_counts` 表字典. `load_ontology_projection` 返回字典**不含**这两键, 测试断言的 3 个 projection 键 (`online_embedding_tokens`/`explicit_transitions`/`action_outcomes`) 仍有效.
- **关键核实 — 不掩盖漏写**: `_runtime_state()` 未填这两类, 空投影计数 0 是真实结果; 若 `_write_projection`/`_clear_projection` 漏建表, `ontology_counts` 会抛 KeyError 而非返回 0, 那是真回归.
- **判定**: **修测试** — counts 断言加两键值 0.

---

## §3 审查完善 — 对抗性预审 (落地前)

| 预审项 | 结论 |
|---|---|
| 失败1改源码会破坏其他 phrase_kind 依赖? | 否. runtime 下仅 663 一处路由, 三处赋值不受影响 |
| 失败1改后教师候选过滤等价? | 等价. `teacher_phrase::` 前缀由单一函数产出, 命名空间互斥, 过滤结果相同 |
| 失败2/3改断言掩盖真回归? | 否. API 契约断言仍守数据; `"Phase20.6" in html` 仍能捕获模板丢/404 |
| 失败4加 0 键掩盖投影漏写? | 否. 漏建表会抛 KeyError, 非 0 |

预审通过, 进入落地.

---

## §4 通过落地 — 改动清单

### 源码 (1 处)
**`apv3test/runtime/phase20_open_dialogue.py:663`** — 删 `phrase_kind` 冗余路由层:
```python
# 改前
if record.phrase_kind != "teacher_event_cooccurrence" or not record.phrase_id.startswith("teacher_phrase::"):
    continue
# 改后 (含注释说明判据来源)
# 只用结构命名空间判据过滤教师短语候选: teacher_phrase:: 前缀由
# _phrase_id_for_teacher_text 唯一产出, 与 style:: / user_utterance::
# 互斥; 不再用 phrase_kind 标签路由 (phase7_9 红线: 勿按 kind 脚本路由)。
if not record.phrase_id.startswith("teacher_phrase::"):
    continue
```

### 测试 (3 处, 仅改陈旧断言)
- `tests/test_phase8_11_web_workbench_audit.py:36` — `"Phase8" in html` → `"Phase20.6" in html`
- `tests/test_phase8_1_real_trial_and_web_chat.py:57` — `"APV3 本地对话工作台" in html` → `"Phase20.6" in html`
- `tests/test_sqlite_store_contract.py:40-46` — counts 断言加 `phase20_6_fast_action_chains: 0` / `phase20_6_slow_memory: 0`

---

## §5 严谨验收测试

### 5.1 4 失败转绿
```
tests/test_phase7_9_...::test_phase7_9_runtime_redline_has_no_multiturn_script_routes PASSED
tests/test_phase8_11_...::test_phase8_11_web_api_serves_phase8_audit_payload PASSED
tests/test_phase8_1_...::test_phase8_1_web_api_message_feedback_and_snapshot PASSED
tests/test_sqlite_store_contract.py::test_runtime_store_projects_ontology_tables PASSED
4 passed in 6.97s
```

### 5.2 受影响文件全文 (零文件内回归)
4 个受影响测试文件全文: **17 passed** (含同文件其他 13 个测试).

### 5.3 邻批 — 教师候选/共现记忆路径 (源码改动波及面)
- `test_phase20_1_teaching_paradigm.py`
- `test_phase20_2_3_cooccurrence_memory.py`
- `test_phase20_6_history_package_canvas.py`
- `test_phase20_6_stage0_runtime_boundary.py`
- `test_phase7_8_minimalist_expression_corpus.py`
→ **40 passed in 174.28s**. 源码删 `phrase_kind` 路由层零回归.

### 5.4 全量回归 (权威, 单进程)
```
880 passed in 1395.88s (0:23:15)
exit code 0
```
**880 passed / 0 failed** — 底座首次全绿. 从 13b/13c 时代的 876 passed / 4 failed → 清理后 880 passed / 0 failed, 4 个既存失败全部转绿, **零新增回归**.

---

## §6 对抗性审阅 (写完后二次自检)

| 审阅项 | 结论 |
|---|---|
| 硬编码? | 否. 失败1留的是结构命名空间判据 (单一函数产出的前缀), 非答案/路由. 失败2/3验证模板标题存在. 失败4值 0 是真实空投影结果 |
| 隐患? | 比原双判据更低. 原方案约束点 2 处 (kind 赋值 + 前缀), 新方案约束点 1 处 (单一前缀函数), 误通过面更小 |
| 白皮书不符? | 否. 正是合规 phase7_9 红线 (禁 kind 脚本路由). 改后用结构命名空间, 更符合 AP "用既有结构而非新标签路由" |
| 可更泛化/优雅? | 已做到 — 双冗余判据收敛为单一结构命名空间判据, 为本次最优雅化点 |
| phrase_kind 字段该删吗? | 不该. 517/1220/1310 三处 `phrase_kind=` 是合法元数据标注 (记录来源类型, 供投影/审计), 非路由. 删路由 ≠ 删元数据, 分寸正确 |

对抗性审阅通过.

---

## §7 勿增实体 / 白皮书合规

- 未新增任何认知实体/答题模块/隐藏解题器/外部课程脚本/答案表/关键词路由/学生侧 LLM/UI 决策逻辑.
- 失败1改源码是**删除**冗余路由 (做减法), 不是新增; 改后走 AP 既有结构命名空间, 勿增实体.
- 失败2/3/4 改测试仅修正陈旧断言以匹配已演进的合法结构 (web 模板 phase20_6 / phase20_6 快慢记忆表), 未掩盖任何真回归.
- §35.4 红线1 (在线嵌入不替代显式通道) / §132 (向量索引派生可重建) / §19.3b (学生侧无外部语义权威) 全程未触碰, 本次为底层红线/契约清理, 与之无交集.

---

## §8 边界

- 本任务只清理 4 个既存失败, 不触及 L3/阶梯投影 (13b/13c 已闭合).
- 4 个失败清理后, 底座回归全绿, 为 Phase20.14 (统一学成判据) 提供干净基线.
- `phrase_kind` 元数据字段保留 (合法标注), 仅删路由用途; 若未来投影/审计需读 `phrase_kind` 元数据, 仍可用.

---

## §9 下一步

**Phase20.14 候选 — 统一"场景学成判据"** (已用户授权, 排在本任务之后):
把阶梯判据 (13c) + lifecycle 的 teacher_exit/cold_retest 就绪度 (10b), 合成一个**纯派生**的"该场景在 teacher_off + cold_retest 条件下是否走完 keyword_organization"投影, 供课程编排读取. 需独立走完整 设计→审查→落地→验收→报告 循环.
