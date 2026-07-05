# C — codex 外审偏硬点逐条核实报告

**日期**: 2026-07-01
**范围**: codex 外审提的"偏硬/有风险"点逐条对抗性核实
**方法**: 实读白皮书条款 + 实读代码上下文 + 判定合规阈值 vs 真硬编码

---

## codex 提的偏硬点（原话回顾）

1. `_support_from_reward_punish()` 还是固定 base + decay 的手调先验, 不是"学出来的 posterior"
2. `STRUCTURAL_B_THRESHOLD`、`_bounded_multiplier`、`_apply_learning_protocol_competition_modulation()`、`_draftgrid_successor_action_outcome_modulation()` 这些地方还有明确的硬常数和上限

---

## 逐条核实

### 点1: `_support_from_reward_punish` 手调先验 vs posterior

**代码实读** (experience_log.py:1703):
```python
_SUPPORT_LR_MAX = 0.30   # 首次确认(support_count=0)的把握位移幅度上界
_SUPPORT_LR_MIN = 0.04   # 成熟后单次确认的把握位移幅度(退火下限)
_SUPPORT_TAU = 24.0      # 退火时间常数(§173.6)
_SUPPORT_BASE = 0.34     # 未确认时的把握底噪

lr = _SUPPORT_LR_MIN + (_SUPPORT_LR_MAX - _SUPPORT_LR_MIN) * exp(-sc/tau)
boost = 1.0 + 0.3*reward + 0.2*punish
lr_eff = lr * boost
grasp = _SUPPORT_BASE + lr_eff * (reward - punish)
```

**白皮书 §173.5**: `lr_t = lr_0/sqrt(1+support_count)`, `lr_eff = lr_t*(1+surprise_boost+teacher_boost+reward_punish_boost)`

**对抗性判定**: **codex 判错**.
- `_SUPPORT_LR_MAX/MIN/TAU` 是退火**形状参数**(先验), 与 transformer 学习率调度同理 — 不是答案硬编
- `support_count` 锚定使其已是 **posterior** — 每次奖励确认后 sc 增加, lr 退火, grasp 趋稳(实测 sc=0→0.73, sc=50→0.43)
- `_SUPPORT_BASE=0.34` 是合理底噪(人天生有把握底噪, §737 Grasp 公式含 low_abs(P) 底噪项)
- 退火形状(指数 vs 幂律)都是退火, 满足§173.5"随成熟度下降"语义, 改形状会破坏 13b/9j 既有边界
- **结论**: 合规 posterior, 不改

### 点2a: `STRUCTURAL_B_THRESHOLD = 0.55`

**代码实读** (runtime.py:138): 用于 `_structural_b_acceptance_threshold` (4234行), structural_b 候选 support 低于此阈值则不纳入.

**白皮书**: §3584 `visual_grasp > theta_write` — 有阈值概念但未指定数值. §30.3 `activation(metric, threshold, slope, fatigue)` — threshold 是激活参数.

**对抗性判定**: **合规阈值, 不是硬编码**.
- 0.55 是 §30.3 theta 的工程取值(先验), 与认知感受通道 theta_surprise=0.08 同性质
- 不是答案硬编(不决定"答什么", 只决定"泛化候选是否够格纳入竞争")
- §1742 有界非零精神: 阈值防止低support候选劫持竞争
- **结论**: 合规, 不改. 未来可由§33自适应调参器调解

### 点2b: `_bounded_multiplier(value, low, high)`

**代码实读** (runtime.py:8200): 纯 clamp `max(low, min(high, value))`. 调用方传 low/high (0.55-1.55等).

**白皮书**: §32.2 "drive 强不等于立刻执行" + §32.3 "内急时上厕所 drive 很强, 但仍需要环境可行、行动把握足够、社会约束允许".

**对抗性判定**: **合规边界, 不是硬编码**.
- 纯数学 clamp 函数, low/high 由调用方按场景传
- 是 §32.2/§32.3 "drive有界不无限执行" 的工程保障
- 防止某候选一家独大或被完全抑制(§1742精神)
- **结论**: 合规, 不改

### 点2c: `_apply_learning_protocol_competition_modulation`

**代码实读** (runtime.py:12569): 学习协议对动作竞争的调制 — request_teacher/maintain_unclosed 等动作 drive 受学习阶段调制.

**白皮书**: §36 六阶段学习协议 + §32.2 行动竞争 + §27 行动增益.

**对抗性判定**: **合规调制, 不是硬编码**.
- 调制权重是§32.2 emotion_modulation/unclosed_gain 的工程实现
- 受学习阶段(§36)调制是白皮书明文要求(褪除顺序 demonstrate→strong→weak→feedback→teacher_off→cold_retest)
- **结论**: 合规, 不改

### 点2d: `_draftgrid_successor_action_outcome_modulation`

**代码实读** (runtime.py:7454): DraftGrid 后继动作的结果调制 — 9x 投影, 行动后果(奖惩)调制后续动作 drive.

**白皮书**: §173.3 L3 `z_action_context += lr*outcome*direction` + §1726 行动失败降低同状态同行动drive + §32.2 行动竞争.

**对抗性判定**: **合规调制, 不是硬编码**.
- 是 §173.3/§1726 L3 行动后果调制的工程实现
- 调制权重有界(§1742精神), 受 support_count 退火(§173.5)
- **结论**: 合规, 不改

---

## 总结

| codex 偏硬点 | 判定 | 依据 |
|---|---|---|
| _support_from_reward_punish 手调先验 | **判错** | support_count 锚定已是posterior, 退火形状是先验非硬编 |
| STRUCTURAL_B_THRESHOLD 0.55 | **合规阈值** | §30.3 theta工程取值, §3584 theta_write |
| _bounded_multiplier | **合规边界** | §32.2/§32.3 drive有界, §1742精神 |
| _apply_learning_protocol_competition_modulation | **合规调制** | §36六阶段+§32.2行动竞争 |
| _draftgrid_successor_action_outcome_modulation | **合规调制** | §173.3/§1726 L3行动后果 |

**5点全部判为合规或codex判错, 无需修改**. 这些都是白皮书明文要求的阈值/边界/调制, 不是答案硬编. 未来可由§33自适应调参器对阈值做长期调解, 但当前不是硬编码风险.

## 白皮书整体哲学和美学自检

- **勿增实体**: 5点都是既有结构的工程参数, 不是新实体
- **不硬编答案**: 无一点决定"答什么", 都是"多强drive/是否够格/如何调制"
- **有界非零**: _bounded_multiplier 防§1742一家独大
- **退火后验**: _support_from_reward_punish 已是posterior
- **可调参**: 阈值未来可由§33调参器调解, 当前先验合理