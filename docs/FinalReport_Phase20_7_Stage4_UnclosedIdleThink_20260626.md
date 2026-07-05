# Phase20.7 Stage 4 Unclosed IdleThink 验收报告

日期: 2026-06-26  
范围: 未闭合感 U、重复未知降噪、idle_think、教师反馈解决 U。

---

## 1. 本阶段目标

Stage 4 的目标是让“不会/低把握”成为 AP 经验流中的持续痕迹, 而不是一次性固定回复:

1. 未知输入在低把握时产生 active unclosed item。
2. 同一结构重复未知时不反复追问, 而是维持未闭合感。
3. 无外部输入时, idle_think 能把注意拉回高 U 项。
4. 教师反馈被整合后, 匹配的 U 下降并 resolved。
5. idle_think 默认不直接对用户提交回复, 只写入 RuntimeTickEvent 和经验流。

---

## 2. 已落地内容

### 2.1 未闭合表

`models.py` 新增:

1. `phase20_7_unclosed_items`
2. `idx_phase20_7_unclosed_status`

字段包含:

```text
unclosed_id
source_event_id
source_signature
source_text
u_value
status
attempt_count
reason_json
```

它引用文本感受器事件和结构签名, 不新增脱离经验流的任务实体。

### 2.2 未闭合 API

`experience_log.py` 新增:

1. `active_unclosed_for_signature(...)`
2. `upsert_unclosed_item(...)`
3. `resolve_unclosed_items(...)`
4. `list_active_unclosed_items(...)`

### 2.3 Runtime 行动

`runtime.py` 新增:

1. `PHASE20_7_STAGE4_SCHEMA_ID`
2. `MAINTAIN_UNCLOSED_TEXT`
3. `_run_idle_think_tick(...)`

行为:

```text
低把握 + 无 B/C:
  第一次: request_teacher -> "我还不太知道怎么说。" -> 写入 unclosed_item_update
  重复: maintain_unclosed -> "我还在想这个。" -> attempt_count 增长

无输入 + active U:
  idle_think -> committed=False -> RuntimeTickEvent.unclosed_items 展示被拉回的项

教师反馈:
  experience_alignment 写入后 resolve_unclosed_items -> unclosed_item_resolved
```

---

## 3. 当前可展示效果

```text
用户: 猫是什么
AP: 我还不太知道怎么说。
U: active, source_text=猫是什么

用户: 猫是什么
AP: 我还在想这个。
U: attempt_count >= 2

无输入 idle tick:
action=idle_think
committed=False
unclosed_items[0].source_text=猫是什么

教师反馈: 猫是一种动物
AP: 嗯,记下了。
U: resolved

用户: 猫是什么
AP: 猫是一种动物
```

---

## 4. 本阶段能证明什么

Stage 4 可以证明:

1. “不会”能留下可追踪的 AP-native 未闭合痕迹。
2. 未闭合感来自低把握与无召回, 引用经验事件和结构签名。
3. 重复未知不会一直主动追问。
4. 闲时 tick 可以被 U 拉回, 但不直接打扰用户。
5. 教师反馈能解决对应 U, 形成拟人闭合感。

---

## 5. 本阶段尚未证明什么

Stage 4 还不证明:

1. 长时间后台调度策略。
2. 多 U 项的复杂优先级仲裁。
3. 放弃、来源移除、代价重估等更完整 U 下降路径。
4. 视觉和听觉的未闭合感。
5. 发布版 UI 展示。

这些应在后续 Stage 继续扩展。

---

## 6. 验收命令

### 6.1 Stage 0-4 单测

```powershell
python -m pytest .\tests\test_phase20_7_stage0_runtime_boundary.py .\tests\test_phase20_7_stage1_text_closed_loop.py .\tests\test_phase20_7_stage2_experience_memory_indexes.py .\tests\test_phase20_7_stage3_structural_bccstar.py .\tests\test_phase20_7_stage4_unclosed_idle.py -q
```

结果: `22 passed`。

### 6.2 Stage 4 红线扫描

```powershell
python .\scripts\red_line_check_v14.py --phase 20.7-stage4
```

结果: 见最终运行记录。

---

## 7. 下一阶段入口

Stage 5 应实现视觉 patch payload、焦点采样、clarity map 与内心画面重建。视觉感受器只提供证据与状态池能量, 不提供整图标签答案。

