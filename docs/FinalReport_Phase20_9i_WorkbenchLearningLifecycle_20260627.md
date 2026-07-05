# Phase20.9i 最终报告: 工作台学习生命周期验收视图

日期: 2026-06-27

## 1. 完成内容

本轮完成 Phase20.9i: 工作台已经可以把真实 `RuntimeTickEvent` 中的学习链路串成一张可读的“学习生命周期验收”视图:

```text
教学/反馈 -> 闲时复盘 -> 私有自测 -> 自测反馈稳定
```

改动文件:

- `apv3test/web/static/phase20_7_workbench.html`
  - 新增 `learningLifecyclePanel`。

- `apv3test/web/static/phase20_7_workbench.js`
  - 新增 `renderLearningLifecycle(...)`、`learningLifecycleState(...)`。
  - 新增 `alignmentWrittenDelta(...)`、`idleLearningReview(...)`、`idleSelfTest(...)`、`selfTestFeedback(...)`。
  - `explainTick(...)` 增加闲时复盘、私有自测、自测反馈稳定的中文解释。
  - 审计曲线新增 `自测把握` 和 `反馈稳定`。

- `apv3test/web/static/phase20_7_workbench.css`
  - 新增四段式生命周期卡片样式。

- `tests/test_phase20_9i_workbench_learning_lifecycle.py`
  - 验证工作台静态契约。
  - 通过真实 API 跑出完整“教学 -> 复盘 -> 自测 -> 反馈稳定”链路。

- `docs/Design_Phase20_9i_WorkbenchLearningLifecycle_20260627.md`
  - 新增本阶段设计稿。

- `docs/Showcase_Phase20_9i_WorkbenchLearningLifecycle_20260627.html`
  - 新增可离线打开的展示页。

同时做了两个验收纠偏:

- `scripts/red_line_check_v14.py`
  - Stage3 红线从只接受历史 `_inject_cstar_virtuals` 调整为接受当前 `_apply_cstar_statepool_feedback`。这是脚本校准, 不改 runtime 认知路径。

- `config/apv3_constants.yaml`
- `runtime/cognitive/state_pool/state_pool.py`
  - 将状态池快照排序中的 `|P|` 权重外提为 `state_pool.snapshot_pressure_weight`。
  - 消除 `runtime/cognitive` 裸数值常量红线。

## 2. 可以证明什么

本轮可以证明:

1. 工作台能展示一个知识点从被教、被闲时复盘、被私有自测, 到自测反馈稳定的跨 tick 过程。
2. 这张视图只读取 `tick_trace` 中的真实字段, 不让 UI 生成学习状态。
3. 自测把握和反馈稳定已经进入审计曲线, 可以连续观察。
4. tick 回放解释能说明“这一步为什么是复盘/自测/反馈稳定”。
5. 红线脚本已经与当前 C* 回灌实现命名一致。
6. 状态池排序权重已经回到常量治理体系。

## 3. 可见效果

工作台入口:

```text
http://127.0.0.1:8776/phase20_7
```

页面可视核验:

```json
{
  "hasPanel": true,
  "panelText": "等待真实教学、复盘、自测和反馈稳定 tick。",
  "headings": [
    "运行状态",
    "学习闭环",
    "学习生命周期验收",
    "本 tick 为什么这样做",
    "Tick 回放",
    "草稿格",
    "短期结构流",
    "本地语音",
    "内心画面",
    "想法云",
    "内心音频",
    "审计曲线"
  ]
}
```

建议人工验收脚本:

```text
1. 输入: phase20.9i lifecycle cue
   教学纠正: phase20.9i lifecycle reply
2. 再输入: phase20.9i lifecycle cue
3. 点闲时 tick: 学习生命周期中出现“闲时复盘”
4. 再点闲时 tick: 出现“私有自测”
5. 再点闲时 tick: 出现“反馈稳定”
```

小白解释:

- 教学/反馈: 用户刚教过 AP。
- 闲时复盘: AP 没有外部输入时, 自己整理刚学到的对应关系。
- 私有自测: AP 自己试着想起来, 但不把这个私有过程发到聊天框。
- 反馈稳定: 想起来就更敢自己说; 想错了就更愿意回脚手架。

## 4. 验收结果

前端语法:

```powershell
node --check apv3test\web\static\phase20_7_workbench.js
```

结果: 通过。

定向测试:

```powershell
python -m pytest tests\test_phase20_9i_workbench_learning_lifecycle.py -q
```

结果: `2 passed in 4.80s`

相邻链路:

```powershell
python -m pytest tests\test_phase20_9i_workbench_learning_lifecycle.py tests\test_phase20_9h_self_test_feedback.py tests\test_phase20_9g_idle_self_test.py tests\test_phase20_9f_idle_learning_review.py tests\test_phase20_9e_learning_loop_carryover.py tests\test_phase20_9d_workbench_learning_loop_panel.py tests\test_phase20_9c_learning_loop_metrics.py tests\test_phase20_9b_learning_protocol_drive_modulation.py tests\test_phase20_9a_learning_protocol_projection.py tests\test_phase20_8m_unclosed_successor_unified_experience_flow.py tests\test_phase20_8k_carryover_ssp_short_structure_flow.py -q
```

结果: `38 passed in 18.82s`

红线脚本:

```powershell
python scripts\red_line_check_v14.py --phase 20.7-stage8
```

结果:

```text
OK: Phase 20.7-stage8 deliverables present
OK: All red line checks pass on runtime/cognitive
```

常量治理:

```powershell
python scripts\check_constant_governance.py
```

结果:

```text
OK: Governance check passed (507 numeric constants)
```

Phase20.7 + Phase20.8 + Phase20.9 全链路:

```powershell
$tests = @(rg --files tests | rg "test_phase20_(7|8|9)")
python -m pytest @tests -q
```

结果: `135 passed in 48.14s`

Release demo:

```powershell
python scripts\verify_phase20_7_release_demo.py
```

结果: `OK: Phase20.7 release demo package verified`

工作台 HTTP:

```powershell
Invoke-WebRequest http://127.0.0.1:8776/phase20_7
```

结果: `200`

## 5. 自审

符合 AP 哲学的点:

- UI 只读取 AP 主流程产生的 tick, 不新增学习实体。
- 生命周期链条不是前端状态机, 而是历史 tick 的白箱投影。
- 私有自测不写聊天回复, 不制造答案候选。
- 自测反馈只调制后继倾向, 不宣称“完全学会”。
- 红线脚本校准到当前 C* 通用回灌路径, 没有为了旧 token 增加假函数。
- `|P|` 排序权重进入常量表, 更符合白箱审计。

仍不能声明:

- 不能声明完整六阶段 runtime 已完成。
- 不能声明 L1/L2/L3 在线嵌入已完成。
- 不能声明完整范式自学习已完成。
- 不能声明数学列竖式已完成。
- 不能声明 object-centric 视觉想象已完成。
- 不能声明 Phase21 视觉教学泛化闭环已完成。

## 6. 下一步

下一步建议进入 Phase20.9j: 让工作台中的学习生命周期验收视图不只展示最近一条链, 而是能按 `alignment_event_id` / `source_text` 选择不同知识点, 对比它们各自的复盘、自测、反馈稳定历史。

这仍然应当只读 RuntimeTickEvent 与经验流, 不新增课程状态表。

