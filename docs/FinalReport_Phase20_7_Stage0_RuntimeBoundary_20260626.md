# Phase20.7 Stage 0 Runtime Boundary 验收报告

日期: 2026-06-26  
范围: Phase20.7 Stage 0 边界隔离、SQLite 真相源 schema、RuntimeTickEvent v2 外壳、红线扫描。

---

## 1. 本阶段目标

Stage 0 的目标不是让 AP 开始回答问题, 而是先把 Phase20.7 的新主路径从旧的 Phase20.6 投影式/候选式路径中隔离出来。

本阶段必须完成:

1. 新建 `apv3test/runtime/phase20_7/` 作为 Phase20.7 唯一入口边界。
2. 建立统一经验流相关 SQLite schema, 但暂不写入经验事件。
3. 暴露 `run_phase20_7_turn(...)` 与 `RuntimeTickEventV2`。
4. 明确 Stage 0 不生成回复、不写记忆、不伪造 tick。
5. 红线扫描禁止旧投影、教学命中、整图识别、完整回复候选、OCR、云端 TTS、学生侧 LLM 等捷径进入新路径。

---

## 2. 已落地文件

新增:

1. `apv3test/runtime/phase20_7/models.py`
   - 定义 `RuntimeTickEventV2`、`Phase207TurnResult`、`MediaInput`、`TeacherFeedback`、`SourceTrustKey`。
   - 定义 Phase20.7 Stage 0 SQLite schema。
   - schema 包含经验事件、occurrence、结构边、payload blob、来源包、行动记录、记忆包归属、派生快照、索引注册等表。

2. `apv3test/runtime/phase20_7/experience_log.py`
   - 提供 `initialize_phase20_7_store(...)`。
   - 提供 schema 状态检查与表枚举。
   - Stage 0 只建表, 不写入经验事件。

3. `apv3test/runtime/phase20_7/runtime.py`
   - 提供 `run_phase20_7_turn(...)`。
   - 当前只返回一个 `stage0_boundary_only` tick。
   - `committed=False`, `reply_text=""`, `experience_event_ids_written=[]`。

4. `apv3test/runtime/phase20_7/api_schema.py`
   - 对外导出 Stage 0 API dataclass。

5. `apv3test/runtime/phase20_7/__init__.py`
   - 暴露 Phase20.7 Stage 0 入口。

6. `tests/test_phase20_7_stage0_runtime_boundary.py`
   - 覆盖 Stage 0 schema、边界 turn、无经验写入、RuntimeTickEvent v2 审计字段、source trust 局部 key。

修改:

1. `scripts/red_line_check_v14.py`
   - 新增 `--phase 20.7-stage0` deliverable。
   - 新增 Phase20.7 Stage 0 专属红线扫描。

---

## 3. 当前 Stage 0 行为

调用 `run_phase20_7_turn(...)` 时:

1. 初始化 Phase20.7 SQLite schema。
2. 返回一个 `RuntimeTickEventV2`。
3. tick 的 `selected_action.action_type` 为 `stage0_boundary_only`。
4. `is_projection=False`。
5. 不提交回复。
6. 不写入经验事件。
7. 不调用旧 Phase20.6 回复候选、教学命中、整图识别、假 tick 或 UI 投影。

这保证后续 Stage 1 必须从 StatePool + SSP + 最小 EventLog + DraftGrid 文本闭环继续, 而不能回到旧路径。

---

## 4. 本阶段能证明什么

Stage 0 可以证明:

1. Phase20.7 已有独立 runtime 边界。
2. 经验流数据库的真相源位置已经预留。
3. RuntimeTickEvent v2 已具备后续白箱审计链所需字段。
4. source trust key 已按 `source x context x modality` 局部化, 不会天然变成全局教师权威。
5. 新路径当前不会通过旧教学表、旧候选文本、整图标签、OCR 或 LLM 获得回答。

---

## 5. 本阶段尚未证明什么

Stage 0 还不证明:

1. AP 已能对话。
2. StatePool/SSP 已运行。
3. B/C/C* 召回已运行。
4. DraftGrid 已逐字提交。
5. 教学已进入统一经验流。
6. 视觉 patch payload 与内心画面重建已运行。
7. idle_think、主动询问、未闭合感、TTS、画板、录音、记忆包产品化已运行。

这些能力必须在 Stage 1-8 逐层验收。

---

## 6. 验收命令

### 6.1 语法编译

```powershell
python -m py_compile .\apv3test\runtime\phase20_7\models.py .\apv3test\runtime\phase20_7\experience_log.py .\apv3test\runtime\phase20_7\runtime.py .\apv3test\runtime\phase20_7\api_schema.py .\apv3test\runtime\phase20_7\__init__.py .\tests\test_phase20_7_stage0_runtime_boundary.py
```

结果: PASS。

### 6.2 Stage 0 单测

```powershell
python -m pytest .\tests\test_phase20_7_stage0_runtime_boundary.py -q
```

结果: `5 passed`。

### 6.3 红线扫描

```powershell
python .\scripts\red_line_check_v14.py --phase 20.7-stage0
```

结果: 见最终运行记录。

---

## 7. 红线

Phase20.7 Stage 0 禁止:

1. 调用旧 `phase20_6_runtime` 或旧 open dialogue 回复路径作为答案来源。
2. 使用 direct teaching hit、taught answer、完整回复候选、关键词/正则答案路由。
3. 使用整图识别标签、文件名标签、OCR 作为学生侧认知结果。
4. 使用学生侧 LLM 直接生成回复。
5. 伪造 staged tick 或 workbench projection。
6. 将 TTS、音频识别、画板、UI 作为认知主路径捷径。

---

## 8. 下一阶段入口

Stage 1 必须实现:

1. StatePool type projection。
2. SSP occurrence flow。
3. 最小 EventLog 写入。
4. exact structural B0 召回。
5. DraftGrid 文本闭环。
6. action competition 在 `write_cell / commit_reply / stop_generating / request_teacher / idle_observe` 等行动之间竞争。
7. 教学反馈写入统一经验流, 不再走独立教学答案表。

Stage 1 验收目标是最小文本闭环成立: 用户输入与教学能够进入经验流, 后续 turn 通过结构召回影响 DraftGrid, 并能证明没有旧 shortcut。

