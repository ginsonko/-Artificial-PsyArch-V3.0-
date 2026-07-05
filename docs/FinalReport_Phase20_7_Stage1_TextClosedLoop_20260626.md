# Phase20.7 Stage 1 Text Closed Loop 验收报告

日期: 2026-06-26  
范围: StatePool + SSP + 最小 EventLog + exact B0 + DraftGrid 文本闭环。

---

## 1. 本阶段目标

Stage 1 的目标是让 Phase20.7 第一次拥有真实的最小 AP-native 文本闭环:

1. 用户文本进入 StatePool 与 SSP occurrence flow。
2. 每个运行 tick 写入最小 `ExperienceEvent`。
3. 教师反馈写入统一经验流, 不走独立答案表。
4. 只允许 exact B0 结构召回, 不做语义泛化。
5. DraftGrid 通过逐 tick 行动写入, 不是预生成完整回复后伪装回放。
6. 同一结构可以回忆, 不同结构不能串场。

---

## 2. 已落地内容

### 2.1 经验流写入工具

`apv3test/runtime/phase20_7/experience_log.py` 新增:

1. `insert_source_packet(...)`
2. `insert_action_record(...)`
3. `insert_experience_event(...)`
4. `upsert_sa_type(...)`
5. `insert_occurrence(...)`
6. `insert_structure_edge(...)`

这些函数都写入 Stage 0 已建立的 Phase20.7 SQLite 真相源表。

### 2.2 Stage 1 runtime 主循环

`apv3test/runtime/phase20_7/runtime.py` 已扩展:

1. `run_phase20_7_turn(..., runtime_stage="stage1")` 为默认主入口。
2. `runtime_stage="stage0"` 保留 Stage 0 空边界回归检查。
3. 文本输入写入 `text_receptor_observation`。
4. 教师反馈写入 `teacher_feedback_event` 与 `experience_alignment`。
5. exact B0 只按当前 SSP 结构签名匹配历史 `experience_alignment`。
6. DraftGrid 每 tick 写入一个文字单元, 并记录 `draft_grid_write`。
7. 完成后记录 `draft_grid_commit`。
8. 低把握且无 exact B0 时, 行动竞争选择 `request_teacher`, 输出“我还不太知道怎么说。”。

### 2.3 Stage 1 单测

新增 `tests/test_phase20_7_stage1_text_closed_loop.py`, 覆盖:

1. 文本输入写入 StatePool/SSP/EventLog。
2. 教师反馈进入统一经验流。
3. 同一结构通过 exact B0 召回。
4. 不同输入不串到上一条反馈。
5. DraftGrid 逐 tick 增长。
6. occurrence、structure edge、action record、source packet 都落库。

### 2.4 红线

`scripts/red_line_check_v14.py` 新增 `20.7-stage1` deliverable 与 Stage 1 扫描项。

---

## 3. 当前可展示效果

示例:

```text
用户: 你好啊
教师反馈: 你也好
AP: 嗯,记下了。

用户: 你好啊
AP: 你也好

用户: 你是谁
AP: 我还不太知道怎么说。
```

其中第二次“你好啊”不是从独立教学表命中, 而是:

```text
text_receptor_observation
→ SSP linear_text signature
→ phase20_7_experience_events 中 exact_b0 匹配 experience_alignment
→ action competition 逐 tick 选择 write_cell
→ DraftGrid: 你 / 你也 / 你也好
→ commit_reply
```

“你是谁”不会召回“你也好”, 因为它的 SSP 结构签名不同, Stage 1 不允许泛化。

---

## 4. 本阶段能证明什么

Stage 1 可以证明:

1. 用户文本已经进入 Phase20.7 新真相源。
2. 教师反馈已经进入同一条经验流。
3. 最小 StatePool type projection 与 SSP occurrence flow 已接入。
4. exact B0 可以从经验流召回历史结构。
5. DraftGrid 是行动结果, 不是纯字符串缓存。
6. RuntimeTickEvent v2 每 tick 都有真实 `experience_event_ids_written`。
7. 教学不会作为全局 fallback 串到不同输入。

---

## 5. 本阶段尚未证明什么

Stage 1 还不证明:

1. near-exact 或相似结构泛化。
2. C_forward / C_backward / C*。
3. 未闭合感与 idle_think。
4. 视觉 patch payload 与内心画面重建。
5. 听觉焦点、录音、xiaoyi TTS actuator。
6. 画板、教师辅助视焦点、记忆包产品化。
7. 发布版工作台 UI。

这些必须在 Stage 2-8 继续完成。

---

## 6. 验收命令

### 6.1 语法编译

```powershell
python -m py_compile .\apv3test\runtime\phase20_7\models.py .\apv3test\runtime\phase20_7\experience_log.py .\apv3test\runtime\phase20_7\runtime.py .\apv3test\runtime\phase20_7\api_schema.py .\apv3test\runtime\phase20_7\__init__.py .\tests\test_phase20_7_stage0_runtime_boundary.py .\tests\test_phase20_7_stage1_text_closed_loop.py
```

结果: PASS。

### 6.2 Stage 0/1 单测

```powershell
python -m pytest .\tests\test_phase20_7_stage0_runtime_boundary.py .\tests\test_phase20_7_stage1_text_closed_loop.py -q
```

结果: `10 passed`。

### 6.3 Stage 1 红线扫描

```powershell
python .\scripts\red_line_check_v14.py --phase 20.7-stage1
```

结果: 见最终运行记录。

---

## 7. 下一阶段入口

Stage 2 应继续扩展:

1. 完整统一经验流 schema 的查询与重建接口。
2. 可重建索引注册与 rebuild 检查。
3. 本地记忆统一入口, 内部区分快处理倾向与慢处理痕迹。
4. import batch / package membership 的可卸载等价性测试。
5. 保持 Stage 1 exact B0 不退化为答案表。

