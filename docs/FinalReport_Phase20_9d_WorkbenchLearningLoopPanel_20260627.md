# Phase20.9d 最终报告：工作台学习闭环可视化面板

日期：2026-06-27

## 1. 完成内容

本轮完成 Phase20.9d：把 Phase20.9c 的 `learning_loop_metrics` 接入 Phase20.7 工作台 HTML，让用户可以直接在底座页面上看到 AP 当前学习闭环倾向。

改动文件：

- `apv3test/web/static/phase20_7_workbench.html`
  - 新增 `learningLoopPanel`。
- `apv3test/web/static/phase20_7_workbench.css`
  - 新增学习闭环卡片、能量条、证据标签样式。
- `apv3test/web/static/phase20_7_workbench.js`
  - 新增 `learningLoopMetric(...)`。
  - 新增 `learningProjection(...)`。
  - 新增 `renderLearningLoop(...)`。
  - tick 回放新增学习阶段与主导倾向标签。
  - tick 解释新增闭环指标解释。
  - 审计曲线新增学习反馈、学习退场、学习冷测、学习脚手架四条曲线。
- `tests/test_phase20_9d_workbench_learning_loop_panel.py`
  - 验证静态页面只读真实 runtime 字段。
  - 验证 API 返回闭环指标。
  - 验证教学后召回能展示 teacher-off 倾向。

## 2. 可以证明什么

本轮可以证明：

1. 工作台已经能展示 20.9c 的学习闭环指标。
2. 用户不需要看测试日志，也能在 HTML 页面看到 AP 当前更像“要脚手架 / 听反馈 / 自己尝试 / 冷重测”。
3. 展示数据来自 `RuntimeTickEvent.learning_deltas`，不是前端假数据。
4. 这个面板是审计视图，不参与回复生成，不改变 AP 行动竞争。

## 3. 可见效果

HTTP 真实工作台 API 演示结果：

```text
first_unknown:
  stage=demonstrate
  dominant=return_to_scaffold
  tendencies={
    feedback_only: 0.0677,
    teacher_off_probe: 0.0,
    cold_retest_probe: 0.0,
    return_to_scaffold: 0.1338
  }

teacher_feedback:
  stage=strong_scaffold
  dominant=feedback_only
  tendencies={
    feedback_only: 0.4829,
    teacher_off_probe: 0.0,
    cold_retest_probe: 0.0,
    return_to_scaffold: 0.0809
  }

teacher_off_recall:
  stage=teacher_off
  dominant=teacher_off_probe
  tendencies={
    feedback_only: 0.063,
    teacher_off_probe: 0.7928,
    cold_retest_probe: 0.5708,
    return_to_scaffold: 0.1149
  }
```

小白解释：

- 第一次不会：页面会显示更需要脚手架。
- 老师教它：页面会显示更像先听反馈。
- 学过后再问：页面会显示更像自己尝试回答。

## 4. 如何测试

本轮已启动新工作台：

```text
http://127.0.0.1:8776/phase20_7
```

建议直接这样测：

1. 打开页面，看中间列“学习闭环”卡片。
2. 输入：`你知道 phase20.9d 测试问题吗`
3. 发送后看“学习闭环”，通常会显示偏向“回到脚手架”。
4. 在“教学纠正”填：`我知道这个测试问题`
5. 发送后看“学习闭环”，会偏向“先听反馈”。
6. 再输入：`你知道 phase20.9d 测试问题吗`
7. 发送后看“学习闭环”，会偏向“尝试自己来”。

若页面不显示新卡片，说明打开了旧端口；请使用 `8776`。

## 5. 验收结果

前端语法：

```powershell
node --check apv3test\web\static\phase20_7_workbench.js
```

结果：通过。

20.9d 定向测试：

```powershell
python -m pytest tests\test_phase20_9d_workbench_learning_loop_panel.py -q
```

结果：`3 passed`

相邻链路：

```powershell
python -m pytest tests\test_phase20_9d_workbench_learning_loop_panel.py tests\test_phase20_9c_learning_loop_metrics.py tests\test_phase20_9b_learning_protocol_drive_modulation.py tests\test_phase20_9a_learning_protocol_projection.py tests\test_phase20_7_stage7_api_workbench.py -q
```

结果：`21 passed in 25.76s`

Phase20.7 + Phase20.8 + Phase20.9 全链路：

```powershell
$tests = @(rg --files tests | rg "test_phase20_(7|8|9)")
python -m pytest @tests -q
```

结果：`121 passed in 55.23s`

红线扫描：

```powershell
rg -n "raw_source_asset_used_for_render.*True|visual_environment_frame_payload|environment_frame|environment_payload_ref|label_map|image_label_map|taught_answer|direct_reply|reply_text\s*=\s*taught|answer_table|hidden_solver|student_side_llm|student-side LLM|enumerate_objects_in_image|regex|keyword_route|six_stage_complete|six_stage_learning_complete|online_embedding_converged|l1_l2_l3_complete" apv3test\runtime\phase20_7 apv3test\web\static\phase20_7_workbench.html apv3test\web\static\phase20_7_workbench.js apv3test\web\static\phase20_7_workbench.css tests\test_phase20_9d_workbench_learning_loop_panel.py -g "*.py" -g "*.js" -g "*.html" -g "*.css"
```

结果：无命中。

Release demo：

```powershell
python scripts\verify_phase20_7_release_demo.py
```

结果：`OK: Phase20.7 release demo package verified`

## 6. 自审

符合 AP 哲学的点：

- UI 只读真实 tick，不生产认知。
- 没有新增答案表、关键词路由、隐藏求解器。
- 学习闭环仍是连续能量倾向，不是外部课程状态机。
- 展示能帮助用户理解 AP 的拟人学习状态：不会时想问，被教时先听，学过后尝试自己来。

不足与边界：

- 这只是可视化接入，不是完整六阶段 runtime。
- cold-retest 仍只是压力显示，不是完整冷重测调度。
- teacher-off 仍是当前 tick 倾向，不是全局成熟能力证明。
- L1/L2/L3 在线嵌入、完整范式自学习、数学列竖式、object-centric 视觉想象仍未完成。

## 7. 下一步

下一步进入 Phase20.9e：让 `learning_loop_metrics` 开始 AP-native 地影响后继 tick 的学习行为，例如降低重复请教、触发短暂 teacher-off probe、安排冷重测压力进入未闭合/闲时思考，但仍必须通过 AP 主流程的能量和行动竞争完成，不能新增外部课程脚本。

