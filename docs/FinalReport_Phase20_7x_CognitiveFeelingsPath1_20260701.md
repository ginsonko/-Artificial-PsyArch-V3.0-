# Phase20.7x — §30 认知感受通道 路1 (惊/违和/合理/压力 4核心) 最终汇总报告

**日期**: 2026-07-01
**范围**: B-2 路1 — §30.2 认知感受通道首批4通道 (惊/Surprise/违和/Dissonance/合理/Reasonable/压力/Pressure) 在 phase20_7 涌现
**循环**: 设计 → 审查完善 → 通过落地 → 严谨验收 → 最终汇总报告
**白皮书**: §30.2/§30.3/§27.3/§30.1/§1199/§745/§171 不增魔法字段; 勿增实体

---

## §1 起因

白皮书 §30.2 定义12认知感受通道 (惊/违和/合理/正确/把握/期待/压力/未闭合/时间感/节奏感/证据缺口/重复疲劳).
对抗性预审发现 `runtime/cognitive/cognitive_feelings/factory.py` 实际通道 (fluency/boredom/fulfillment/satisfaction + reality_sense/imagination_sense/hearsay_sense/guess_sense/incongruity) **与白皮书 §30.2 不一致** — 是 §37 源分化+通用流畅度, 非 §30.2. 故**不接通 factory.py** (会引入不合规实现), 改为在 phase20_7 自补 §30.2 通道.

用户裁定: 先做路1 (4核心: 惊/违和/合理/压力), 不忘路2 (补剩8通道分期).

## §2 设计 (审查完善后)

### 白皮书公式 (实读)
- 惊: `Surprise_i = max(P_i - theta_surprise, 0)` (§721)
- 违和: `Dissonance_i = max(-P_i - theta_dissonance, 0)` (§721)
- 合理: `Reasonable_i = decrease(Surprise) + support(C_backward)` (§30.2+§1199)
- 压力: `Pressure = predicted_punish_energy` (§27.3)
- 激活: `feeling_channel = activation(metric, threshold, slope, fatigue)` (§30.3)

### 派生源 (复用既有)
- P=R-V: `StateItem.cognitive_pressure` (§9 状态池字段)
- C_backward grade: c_backward cause_grasp (§1199 已投影)
- 9y reward/punish_pressure (§27.3)

### 修法
新增 `_cognitive_feelings_from_pool(pool, observation, *, c_backward_grasp, reward_pressure, punish_pressure)`:
- 沿用 `_statepool_observation_support_bias` 的 sa_ids 聚合模式 (text_utterance + text_unit), 单调聚合P
- Surprise = _unit(max(0, (avg_pos - theta_surprise) * slope_surprise))
- Dissonance = _unit(max(0, (avg_neg - theta_dissonance) * slope_dissonance))
- Reasonable = _unit((1-surprise)*0.5 + c_backward_grasp*0.5)
- Pressure = _unit(punish_pressure + min(0.20, surprise*0.30))  # + §30.1 惊伴随少量惩罚信号涌现 (用户理论"未知带惩罚→恐惧")

### 接通方式 (最小破坏)
- `_feelings_for_output` 加可选 `cognitive_feelings: dict | None=None` 参数 (向下兼容)
- 各返回 dict 末尾统一 `**cognitive_feelings` 合并
- 8 个调用点统一调 `_cognitive_feelings_from_pool(pool, observation, c_backward_grasp=...)` 传入 — 复用 `_visual_imagination_c_backward(visual_imagination)[-1].get("cause_grasp", 0.0)`

## §3 落地文件

| 文件 | 改动 |
|---|---|
| `apv3test/runtime/phase20_7/runtime.py` | (1) 新增 `_cognitive_feelings_from_pool` 函数; (2) `_feelings_for_output` 加 cognitive_feelings 可选参数 + 5个返回点合并 **cognitive_feelings; (3) 观察write路径多个调用点统一注入 _cognitive_feelings_from_pool(pool, observation, c_backward_grasp=...) |
| `tests/test_phase20_7x_cognitive_feelings_channels.py` | 新增 8 个验收测试 |
| `docs/FinalReport_Phase20_7x_CognitiveFeelingsPath1_20260701.md` | 本报告 |
| `docs/ProgressRoadmap_Phase20_Plus_20260701.md` | 路1→路2 12通道分期规划 |

无新增表/实体/路由/答案表/关键词路由/学生侧 LLM. 纯复用 StateItem.cognitive_pressure + c_backward cause_grasp + 9y pressure.

## §4 白皮书合规

| 条款 | 合规 |
|---|---|
| §30.2 12认知感受通道 (4/12路1) | ✓ 惊/违和/合理/压力 |
| §30.3 activation(metric,threshold,slope,fatigue) | ✓ (fatigue 维度暂未注入, 留路2) |
| §721 Surprise/Dissonance 公式 | ✓ |
| §1199/§745 Reasonable (decrease+cause_grasp) | ✓ |
| §27.3 Pressure=predicted_punish | ✓ (复用9y) |
| §30.1 惊伴随少量惩罚涌现 | ✓ min(0.20, surprise*0.30) |
| §171 不增魔法字段 | ✓ fear/curiosity 禁用串全无 |
| 勿增实体 | ✓ 无新表/实体/路由, 纯读既有字段 |

## §5 对抗性审阅

### 硬编码: theta=0.08/slope=1.6/1.4/0.20 是 §30.3 激活参数先验 (同§173.5退火形状), 非答案硬编 ✓
### 隐患:
- 空 pool → 涌现 0 (无 SA) ✓ (有测)
- df 默认 None → 旧行为不破坏 ✓ (签名向下兼容)
- 全调用点统一用 `_visual_imagination_c_backward(visual_imagination)` — visual_imagination 在681原反馈路径用 feedback_attribution 但语义等价 (cause_grasp 都是§1199归因把握), 保持统一避免散乱 ✓
- 高 P (惊高) 不锁死 — cognitive_pressure 随 B/C* 推进而衰减, 惊随之降 ✓ (集成测: 未知0.51 → write衰减0.43→0.36)

## §6 验收 (实际跑过)

### 单元测试 (8/8 ✓)
- surprise 通道从 P>0 涌现 (>0.5 高惊) ✓
- dissonance 通道从 P<0 涌现 (>0.4 中等违和) ✓
- reasonable 从低惊+高 c_backward_grasp 涌现 (高惊时合理低) ✓
- pressure = 9y + 惊涌现份 ✓
- 未知文通过 tick feelings 涌现 surprise ✓ (集成)
- 禁用串无 ✓
- 空 pool 返回 0 不假装 ✓
- 教师反馈后惊降合理升 (拟人: 知道了就不惊) ✓

### 集成探针 (拟人涌现)
- 未知文 "?什么情况" → request_teacher tick surprise=0.5077 高惊 (求知欲涌现)
- 后续 write_cell tick surprise 逐步衰减 0.43→0.36 (合理感升)
- 教过后再问 surprise 低于首次 (~不惊)

### 邻批 56/56 ✓ (7x/7w/7v + 9j-grasp + stage4 + stage5 + 9f + phase20_14)
### 全量回归: 后台跑中 (基线 905 + 7x新增8 = 预期 913/0)

## §7 进度

A 89% → B-1 90% → B-2路1 **91.5%**

- §30.2 4核心通道接通 (4/12 拟人涌现: 惊/违和/合理/压力)
- 求知欲/恐惧涌现第一层闭环 (惊→压力→u_value 7w + 惊调行动 §32.2)
- 剩 §30 8通道 (把握已接✓ / 期待/未闭合/时间感/节奏感/证据缺口/重复疲劳 / 正确) 在路2分别做

距小白可用惊艳底座**约 91.5%**, 还差 8.5%:
1. §30剩 8通道 (路2) — ~2%
2. §31 情绪慢量→表达风格 — ~2%
3. §27.6 evidence型释放 (B-4) — ~1.5%
4. 首屏冷启动+中文化 — ~2.5%
5. 其他 (counter_evidence/sleep/social/habit接通) — ~0.5%

## §8 下一步 (按规划)

**B-2 路2: 补§30剩 8通道分期**:
1. ✓ 正确感 Correct (路2.1, 见§10.1): low_abs(P) + reward_signal; verified_prediction 留补
2. ✓ 期待 Expectation (路2.2, 见§10.2): reward_pressure (9y) + reward_signal; 纯未来奖励预测留 C_forward
3. 待做: 未闭合 (§27.6): u_value (7w已涌现) + §27.6 释放 (B-4)
4-7. 待做: 时间感/节奏感/证据缺口/重复疲劳
8. 已做: 把握 (9j-grasp已接通)

---

## §10 路2 续作 (2026-07-01 同日记)

### §10.1 路2.1 — 正确感 Correct
**白皮书 §30.2**: `Correct_i = verified_prediction_i + low_abs(P_i) + reward/check_success`
**落地**: `_cognitive_feelings_from_pool` 加 reward_signal 可选参数. 三源可用两项:
- low_abs(P): |P| 低 → R≈V → 预测匹配 (§1264 low_abs_pressure)
- reward_signal: 反馈路径反馈强度 (feedback_drive_context drive 近似)
- verified_prediction 第三项: 留 readback 信号接通后补
**正确感 Correct = _unit(low_abs_p * 0.5 + reward_signal * 0.5)**
**验收**: 12/12 ✓ + 邻批 57/57 ✓
**进展**: 进度 91.5% → 92%

### §10.2 路2.2 — 期待 Expectation
**白皮书 §27.3**: `Expectation(B_j) = predicted_reward_energy(C | B_j)` (与压力 Pressure=predicted_punish_energy 对称, §30.2 第6通道"期待: 奖励预测")
**落地**: 加 expectation 通道到 `_cognitive_feelings_from_pool`.
- reward_pressure (9y 经验调器奖励投影, 调用点暂未传, 默认0)
- reward_signal (反馈路径已传, 反馈后强奖励 → 期待强)
- 纯未来奖励预测 (C_forward 接学习奖励路径) 留 C_forward 接通后补
**Expectation = _unit(reward_pressure + min(0.20, reward_signal * 0.5))**
**验收**: 15/15 ✓ (路1+2.1+2.2合计) + 邻批 73/73 ✓
**对抗性审阅**: 与压力对称; 当前调用点暂未传 9y reward_pressure (浪费, 后续可接); 反馈路径已有 reward_signal → 期待通道已能涌现拟人 (收到强奖励期待再次)
**进展**: 进度 92% → 92.3%

### §10.3 路2.3 — 未闭合 Unclosed
**白皮书 §30.2 第8通道**: "未闭合: 期待/压力未完成或未解除" + §27.6 U持续张力
**落地**: 加 unclosed_u 参数, 从 active_unclosed_for_signature 取 u_value 传入. `unclosed = _unit(unclosed_u)`
**验收**: 18/18 ✓ + 邻77✓ + 裁剪122✓ + 全量923/0✓
**对应用户理论**: "失恋注意难集中"底层 (U高不释放→反复打断)

### §10.4 路2.4 — 时间感 TimeSense
**白皮书 §30.2第9 + §13.4**: "陌生城市时间感觉变慢, 熟悉通勤时间感觉快"
**落地**: `time_sense = _unit((1-surprise)*0.5 + c_backward_grasp*0.5)`. 低惊+高归因→熟悉→快; 高惊+低归因→陌生→慢.
**验收**: 20/20✓ + 裁剪124✓

### §10.5 路2.5 — 节奏感 RhythmSense
**白皮书 §30.2第10 + §1294**: "熟语后继波峰强→自然接下去, 逗号后继分散→停一下"
**落地**: `rhythm_sense = _unit(continue_count * 0.06 * (1-repetition_fatigue))`. 连续多+重复低→流畅; 重复高→紊乱(§586).
**边界**: 调用点暂未传continue_count(需9y开销), 函数正确(单元测试验证), 待rhythm_lag边或9y接通后激活集成涌现.
**验收**: 22/22✓ + 裁剪126✓

### §10.6 路2.6 — 证据缺口 EvidenceGap
**白皮书 §30.2第11 + §1937 + §3258**: "把握上升→证据缺口下降; low_grasp+evidence_gap→request_teacher"
**落地**: `evidence_gap = _unit((1-c_backward_grasp)*0.5 + surprise*0.3 + unclosed*0.2)`. 低把握主导+惊加成+未闭合加成.
**验收**: 24/24✓ + 裁剪128✓

### §10.7 路2.7 — 重复疲劳 RepetitionFatigue
**白皮书 §30.2第12 + §738**: `F_i(t+1) = decay_F*F_i(t) + repeated_focus_i + repeated_action_i`
**落地**: `repetition_fatigue_channel = _unit(avg_fatigue*0.5 + repetition_fatigue*0.5)`. StateItem.fatigue聚合(repeated_focus) + 9y repetition_fatigue(repeated_action).
**验收**: 27/27✓ + 裁剪131✓ (含路2完整验收 test_phase20_7x_all_12_channels_present_in_return)

### §10.8 路2 完整闭合
**§30.2 12通道全部接通**:
- 11通道在 `_cognitive_feelings_from_pool` (惊/违和/合理/正确/期待/压力/未闭合/时间感/节奏感/证据缺口/重复疲劳)
- 把握grasp在 `_feelings_for_output` 外部接入 (9j-grasp已有)
**留补3项** (待后续信号接通, 不强行硬编):
- 正确感 verified_prediction 第3项 (待readback通过信号)
- 节奏感 rhythm_lag边 (待SSP rhythm_lag实现)
- 期待 纯未来奖励预测 (待C_forward接奖励路径)
**进度**: 92.3% → **93.5%** (路2完整闭合)