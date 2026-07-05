# Phase20.9e 最终报告: 学习闭环指标回灌后继 tick 行动竞争

日期: 2026-06-27

## 1. 完成内容

本轮完成 Phase20.9e: `learning_loop_metrics` 已经不再只是工作台展示字段, 而是能通过 AP 主流程影响后继 tick 的行动竞争。

改动文件:

- `apv3test/runtime/phase20_7/runtime.py`
  - 新增 `PHASE20_9E_LEARNING_LOOP_CARRYOVER_ID`。
  - 新增 `_append_runtime_tick(...)`, 让 tick 生成后立刻补全 B/C/C* 与学习闭环指标。
  - 新增 `_learning_loop_carryover_from_events(...)` 和 `_learning_loop_carryover(...)`。
  - 新增 `_apply_learning_loop_carryover_to_competition(...)`。
  - `request_teacher / maintain_unclosed / write_cell / commit_reply / idle_think / integrate_feedback` 的行动竞争可以读取上一 tick 的闭环倾向。
  - 修正一次对抗性审查发现的双重加权风险: `teacher_request_drive_context` 只保留审计来源, 真正赋能只在 competition 层发生一次。

- `tests/test_phase20_9e_learning_loop_carryover.py`
  - 验证未知输入后的请教 carryover。
  - 验证反馈后的写入整合 carryover。
  - 验证已学召回后的教师退场 carryover。

- `tests/test_phase20_8n_request_teacher_unified_drive.py`
  - 更新旧验收公式, 明确新分层。

- `docs/Showcase_Phase20_9e_LearningLoopCarryover_20260627.html`
  - 新增一份可打开的 HTML 效果说明页, 方便不看测试代码也能理解本轮做了什么。

## 2. 可以证明什么

本轮可以证明:

1. 每 tick 的学习闭环指标已经能影响后继 tick 行动竞争。
2. 这种影响通过已有 AP 行动竞争发生, 没有新增课程脚本或回答捷径。
3. 未知输入会轻微增强 `request_teacher / maintain_unclosed`。
4. 教师反馈会轻微增强 `write_cell / integrate_feedback`。
5. exact B0 或结构召回支持较强时, 会轻微增强 `write_cell / commit_reply`, 形成教师退场倾向。
6. 20.8n 的请教驱动、20.9b 的学习协议调制、20.9c 的闭环指标、20.9d 的工作台展示仍然兼容。

## 3. 可见效果

真实追踪脚本观察到的三类效果:

```text
UNKNOWN
  tick=2
  action=request_teacher
  tendency=return_to_scaffold
  context_drive=0.6200
  learning_loop_delta=0.0151
  final_drive=0.7499

FEEDBACK
  tick=3
  action=write_cell
  tendency=feedback_only
  drive_before_learning=0.4500
  learning_loop_delta=0.0193
  final_drive=0.4978

TEACHER_OFF
  tick=11
  action=write_cell
  tendency=teacher_off_probe
  drive_before_learning=0.8200
  learning_loop_delta=0.0674
  final_drive=0.9048
```

小白解释:

- 不会: 上一个 tick 判断“需要脚手架”, 下一 tick 请教动作更容易赢。
- 被教: 上一个 tick 判断“先听反馈”, 下一 tick 更容易写入和整合。
- 学过: 上一个 tick 判断“可以试着自己来”, 下一 tick 写入动作更有力。

## 4. 如何在底座里测试

打开工作台:

```text
http://127.0.0.1:8776/phase20_7
```

建议这样测:

1. 输入一个新问题, 例如 `phase20.9e 我还没教过的问题`, 发送。
   - 看 tick 回放和学习闭环卡片, 应该出现偏向“回到脚手架”的状态。
   - 点中 `request_teacher` tick, 看“行动竞争”里请教动作的 drive。

2. 在“教学纠正”里输入一个回复, 例如 `这是 phase20.9e 的教学答案`, 发送。
   - 看学习闭环卡片, 应该偏向“先听反馈”。
   - 后继写入 tick 会带有 `feedback_only` 倾向。

3. 再次输入同一个问题。
   - 如果 exact B0 召回成立, 学习闭环会更偏向“尝试自己来”。
   - 后继 `write_cell` tick 的 drive 会因为 `teacher_off_probe` carryover 上升。

注意: 工作台展示的是 runtime tick 字段。HTML 不参与认知, 也不生成任何答案。

## 5. 验收结果

语法检查:

```powershell
python -m py_compile apv3test\runtime\phase20_7\runtime.py apv3test\runtime\phase20_7\cognitive_cycle.py tests\test_phase20_8n_request_teacher_unified_drive.py tests\test_phase20_9e_learning_loop_carryover.py
```

结果: 通过。

20.9e 定向测试:

```powershell
python -m pytest tests\test_phase20_9e_learning_loop_carryover.py -q
```

结果: `3 passed in 2.36s`

相邻链路:

```powershell
python -m pytest tests\test_phase20_9e_learning_loop_carryover.py tests\test_phase20_9d_workbench_learning_loop_panel.py tests\test_phase20_9c_learning_loop_metrics.py tests\test_phase20_9b_learning_protocol_drive_modulation.py tests\test_phase20_9a_learning_protocol_projection.py tests\test_phase20_8n_request_teacher_unified_drive.py tests\test_phase20_8h_unified_cstar_min_error_integration.py -q
```

结果: `27 passed in 17.50s`

Phase20.7 + Phase20.8 + Phase20.9 全链路:

```powershell
$tests = @(rg --files tests | rg "test_phase20_(7|8|9)")
python -m pytest @tests -q
```

结果: `124 passed in 69.42s`

红线扫描:

```powershell
使用既有 Phase20 红线扫描表达式覆盖 runtime 与本轮测试文件。
```

结果: 无命中。

Release demo:

```powershell
python scripts\verify_phase20_7_release_demo.py
```

结果: `OK: Phase20.7 release demo package verified`

## 6. 自审

符合 AP 哲学的点:

- 闭环指标不是外部实体, 而是现有 B/C/C*、把握感、反馈、未闭合和行动竞争的投影。
- carryover 没有写答案, 只改变动作竞争能量。
- 未知、反馈、教师退场三类行为更接近人类学习过程: 不懂会问, 被教会先听, 有把握会试。
- 双重加权风险已修正, 同一股学习压力只在行动竞争层赋能一次。

仍不能声明:

- 不能声明完整六阶段 runtime 已完成。
- 不能声明 L1/L2/L3 在线嵌入已完成。
- 不能声明完整范式自学习已完成。
- 不能声明数学列竖式已完成。
- 不能声明 object-centric 视觉想象已完成。
- 不能声明 Phase21 视觉教学泛化闭环已完成。

## 7. 下一步

下一步可以进入 Phase20.9f 或 Phase21 前置:

1. 把这些闭环 carryover 更细粒度地影响 `idle_think` 的闲时复盘, 让它在无人输入时更自然地整理“没懂的东西”和“刚学会的东西”。
2. 把 teacher-off/cold-retest 从单 tick 倾向继续推进成跨 session 的真实验收事件。
3. 再进入 Phase21 视觉教学泛化闭环, 解决苹果/香蕉/绿色橙子的视觉证据绑定和 object-centric 想象。
