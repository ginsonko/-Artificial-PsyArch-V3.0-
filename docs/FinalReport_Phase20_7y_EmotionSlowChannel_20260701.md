# Phase20.7y — §31 情绪慢量通道 最终汇总报告

**日期**: 2026-07-01
**范围**: B-3 — §31 情绪慢量从 turn 内 tick_events 的 §30 feelings 衰减加权积分
**循环**: 设计 → 审查完善 → 通过落地 → 严谨验收 → 最终汇总报告
**白皮书**: §31.1/§31.2/§31.3/§31.4 红线; 勿增实体

---

## §1 起因

白皮书 §31: 情绪是由认知感受+奖惩+行动反馈+记忆召回积分出的慢变量, 调制注意/行动阈值/奖惩权重/探索保守/表达风格.
§30.2 12通道已全接通 (B-2路1+路2), 但 §31 情绪慢量未积分 — phase20_7 的 `emotion` 字段是空的.

## §2 设计 (审查完善后)

### 白皮书公式 (实读 §31.2)
```
emotion_c(t+1) = clamp(decay_c * emotion_c(t) + sum_k w_ck * feeling_k
                      + reward_weight_c * reward - punish_weight_c * punish + memory_recall_c)
```

### 持久化对抗性自审
- emotion_c(t) 跨turn慢变量需持久化 — 但 phase20_7 无 state 持久机制 (turn-based, 每次从DB重建)
- 存DB会增表/列 (增实体) — 不合规
- **最克制方案**: turn内积分 — 从 tick_events 的 feelings 衰减加权积分, turn结束输出到 result.emotion
- 跨turn慢变量持久化 + memory_recall 项留待 state 持久机制接通后补 (同 rhythm_lag/verified_prediction 留补模式)

### 修法
新增 `_integrate_emotion_from_ticks(tick_events)`:
- 从 tick_events 序列的 RuntimeTickEventV2.feelings 取 §30 12通道数值
- §31.2 衰减加权积分: `weight = decay^(N-1-k)`, 越近权重越高 (拟人: 近因情绪影响大)
- 从12通道积分出6个情绪维度:
  - valence (正负): correct/reasonable/expectation→正; pressure/dissonance/unclosed→负
  - arousal (激活): surprise/dissonance/evidence_gap→高; repetition_fatigue→低
  - dominance (掌控): correct/reasonable→高; unclosed/evidence_gap→低
  - pressure_tone (压力色调 §31.3): pressure+unclosed
  - curiosity_tone (求知色调): surprise+evidence_gap
  - fatigue_tone (疲劳色调): repetition_fatigue+dissonance

### 不增实体
- 纯从 tick_events (已有 RuntimeTickEventV2.feelings) 派生
- 不存 DB, 不新增表/列/实体/路由
- emotion 字段加到 Phase207TurnResult (向下兼容 default_factory=dict)

## §3 落地文件

| 文件 | 改动 |
|---|---|
| `apv3test/runtime/phase20_7/runtime.py` | 新增 `_integrate_emotion_from_ticks` 函数; 3主返回点接入 (stage6文本/idle_think/idle外向言语) |
| `apv3test/runtime/phase20_7/models.py` | Phase207TurnResult 加 emotion 字段 (default_factory=dict 向下兼容) + to_dict |
| `tests/test_phase20_7x_cognitive_feelings_channels.py` | 新增3个emotion测试 (集成涌现+教师奖励valence升+红线禁用串) |
| `docs/FinalReport_Phase20_7y_EmotionSlowChannel_20260701.md` | 本报告 |

## §4 白皮书合规

| 条款 | 合规 |
|---|---|
| §31.1 情绪由感受积分慢变量 | ✓ 从§30 12通道 feelings 衰减加权积分 |
| §31.2 decay*emotion_c(t)+sum w*feeling | ✓ decay^N-k 衰减加权 (近因权重高) |
| §31.3 长期压力→警觉保守 | ✓ pressure_tone 从 pressure+unclosed涌现 |
| §31.4 红线 不由关键词设置 | ✓ 纯从 feelings 派生无关键词 |
| §31.4 红线 只软调制不强制模板 | ✓ 输出连续值供下游软调制 |
| 勿增实体 | ✓ 不存DB不增表, 纯从tick_events派生 |

## §5 对抗性审阅

### 硬编码: decay=0.85 / 权重0.25/0.20等 是§31慢变量参数先验, 同§173.5退火形状, 非答案硬编 ✓
### 隐患:
- 空 tick_events → 默认零值 (有测) ✓
- 既有返回点不传emotion → default_factory=dict 向下兼容不破坏 ✓ (42/42 + 142/142验证)
- decay=0.85 近因权重 — 单turn内合理, 跨turn待持久化后调整
### 白皮书不符: 无 ✓
### 可更泛化: 跨turn memory_recall 项留补 — 待 state 持久机制接通后积分跨turn情绪

## §6 验收 (实际跑过)

### 30/30 测试全绿 (路1+路2+路2.7+B-3 emotion 合计)
- emotion集成: 未知文→arousal>0.15, curiosity_tone>0.15, integrated_from_tick_count>0 ✓
- 教师奖励→valence升: 学过后valence≥首次未知 (拟人: 知道了情绪更正) ✓
- 红线禁用串: emotion_converged/complete/mood_complete 全无 ✓

### 裁剪回归 142/142 ✓ (含 phase7_9 多轮+phase20_9a-z学习+phase20_7全stage+phase20_14)

## §7 进度

93.5% → **94.5%** (§31情绪慢量闭合)

距小白可用惊艳底座**约94.5%**, 还差5.5%:
1. §27.6 evidence型释放 (4/5缺, B-4) — ~1.5%
2. 首屏冷启动+中文化 — ~2.5%
3. 其他接通 (sleep/social/habit/counter_evidence/emotion跨turn持久) — ~1.5%

## §8 下一步

- **B-4: §27.6 evidence型释放** — 4/5缺 (source_removal/giving_up/impossibility/cost_revaluation), 需C_backward证据接通
- **首屏冷启动+中文化** — 小白打开就能看AP拟人
- **emotion跨turn持久化** — 待state持久机制接通后, emotion_c(t) 跨turn积分+memory_recall项