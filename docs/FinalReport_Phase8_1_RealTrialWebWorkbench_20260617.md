# APV3 Phase8.1 真实试玩观察与 Web 工作台最终报告
日期: 2026-06-17
阶段: Phase8.1
状态: 通过

## 1. 设计

Phase8.1 的目标是从“CLI 可运行”推进到“真实体验可观察”:

- 代替用户做一轮真实试玩，记录好用和不好用的地方。
- 对暴露出的体验问题做小步产品化修复。
- 新增本地 Web 对话工作台，把对话、奖励/惩罚、tick 回放、top phrase、内省 feeling、审计 trace 和趋势图放到同一界面。

本阶段仍然保持 APV3 边界:

- 不加关键词回答。
- 不加答案表。
- 不接学生侧 LLM。
- 不允许用户输入动态扩词。
- UI 只是体验和审计壳，不把 UI 行为伪装成 AP-native 能力。

## 2. 审查完善

真实试玩先暴露了两个问题。

### 问题 A: 纯词库外冷启动会空回复

复现:

```text
输入: 这是什么情况
底层 committed_text: ""
可见回复: ""
```

原因:

- 底层 runtime 在没有 learned phrase candidate 时保持空提交，这是 7.x teacher-off 探针需要保留的诚实语义。
- 但用户体验入口是“必须有反馈”的交互壳，空回复会显得像系统坏了。

修复:

- 不改 7.x 核心 teacher-off 语义。
- 只在 `APV3MinimalistChatSession` 的呈现层使用 `HONEST_FALLBACK_TOKENS=("不知道",)`。
- trace 中同时保留 `runtime_committed_text=""` 和 `used_honest_fallback=true`。

修复后:

```text
输入: 这是什么情况
底层 committed_text: ""
可见回复: 不知道
trace: used_honest_fallback=true
```

### 问题 B: flow/request/corrective 结构态坍缩

复现:

```text
输入 嗯(uncertain) -> 嗯
输入 好(flow) -> 好
输入 教教(request) -> 好
输入 不对(corrective) -> 不对
再输入 普通输入(flow) -> 不对
```

原因:

- CLI 的 `flow/request/corrective` 视图在 draft introspection 的结构特征上太接近。
- `request` 和 `corrective` 会落到同一个 prototype，导致不同场景短语混进同一个 feeling。

修复:

- 仍然不按词分支。
- 通过 AP-native 结构视图区分不同状态:
  - `request`: 未填 slot，低 readiness。
  - `corrective`: 已填但 fit margin 很低。
  - `flow`: 已填且高 readiness。
  - `uncertain`: 未填 slot 后跟 shared fragment。

修复后:

```text
uncertain -> feeling::draft::proto_0
flow      -> feeling::draft::proto_1
request   -> feeling::draft::proto_2
corrective-> feeling::draft::proto_3
```

并且:

```text
输入 教教(request) -> 教教
输入 不对(corrective) -> 不对
再输入 普通输入(flow) -> 好
```

## 3. 通过落地

新增:

- `apv3test/web_chat.py`
- `apv3test/web/static/index.html`
- `apv3test/web/static/styles.css`
- `apv3test/web/static/app.js`
- `tests/test_phase8_1_real_trial_and_web_chat.py`
- `docs/FinalReport_Phase8_1_RealTrialWebWorkbench_20260617.md`
- `reports/APV3_Phase8_1_RealTrialWebWorkbench_Showcase_20260617.html`

更新:

- `apv3test/chat.py`

Web 工作台能力:

- 左侧: 对话流。
- 顶部: 结构态切换。
- 输入区: 发送、奖励、惩罚。
- 中间: tick 回放、趋势图、指标卡。
- 右侧: top phrase、想法云、审计 trace、内心画面/音频占位视图。
- API: `/api/message`, `/api/feedback`, `/api/mode`, `/api/state`, `/api/replay`。

启动:

```text
python -m apv3test.web_chat --host 127.0.0.1 --port 8765
```

## 4. 严谨验收测试

已执行:

```text
python -m pytest tests\test_phase8_0a_runtime_profile.py tests\test_phase8_0b_minimal_cli_entry.py tests\test_phase8_1_real_trial_and_web_chat.py -q
python -m pytest tests\test_phase7_8_minimalist_expression_corpus.py tests\test_phase7_9_minimalist_multiturn_dialogue_flow.py tests\test_phase7_10_longrun_stability.py tests\test_phase7_11_user_style_mirroring.py tests\test_phase8_0a_runtime_profile.py tests\test_phase8_0b_minimal_cli_entry.py tests\test_phase8_1_real_trial_and_web_chat.py -q
python -m pytest tests -q
python -m compileall apv3test tests -q
```

结果:

- Phase8.0-8.1 targeted: `12 passed`
- Phase7.8-8.1 combined: `37 passed`
- Full suite: `267 passed`
- Compileall: passed
- Redline scan: no matches

浏览器验证:

- 打开 `http://127.0.0.1:8766/` 成功。
- 输入 `这是什么情况`，页面显示 `不知道`，fallback 指标为 1。
- 输入 `嗯`，页面显示 `嗯`，top phrase 出现 `p:ack:yes`。
- 点击奖励按钮后生成 tick 3，审计 trace 记录 `reward_delta=0.1`，support 从 `1.7001` 升到 `1.783099`。

## 5. 最终汇总

Phase8.1 证明:

- 真实试玩可以发现测试报告里不明显的体验问题。
- 冷启动未知输入现在能以“不能决”的简洁方式回应，同时保留底层空提交证据。
- 结构态可以通过 AP-native 结构视图分化，而不是通过关键词或答案表分化。
- 本地 Web 工作台已经能支持连续对话、奖励/惩罚、tick 回放、趋势图和审计查看。

仍然不能宣称:

- 这不是完整 Web 产品。
- 内心画面/音频目前是结构态审计视图，不是跨模态生成。
- 当前表达仍受 120 seed phrase 限制，不能学习词库外新短语。
- 还没有真实用户长时间试玩统计。

下一步建议:

- Phase8.2: 用 Web 工作台做 30-60 分钟真实试玩记录，按问题类型分为体验节奏、表达丰富度、审计可读性、状态持久化和长程污染风险。
- Phase8.3: 在保持固定词库安全边界的前提下扩展 seed corpus 到 300-500 个短表达。
