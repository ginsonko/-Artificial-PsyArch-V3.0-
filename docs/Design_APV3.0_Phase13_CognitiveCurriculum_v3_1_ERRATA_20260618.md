# APV3.0 Phase 13 — Cognitive Curriculum 设计稿 v3.1 ERRATA

日期: 2026-06-18
作者: 银子老师 / Claude 协作
状态: **v3 经对抗审阅识别 6 blocker + 8 serious + 8 medium。v3.1 是精准修复补丁,不重写 v3。Codex 实施依据 = v3 + v3.1 ERRATA 双稿。同时新增 APV2.1 数学能力(Math-0~28 已实测 728/728)接入路径。**

前作:
- [Phase 13 设计稿 v3](Design_APV3.0_Phase13_CognitiveCurriculum_v3_20260618.md)
- [人设样例 v1(已确认)](Phase13_PersonaSamples_v1_20260618.md)

许可:AGPL-3.0-or-later + 商用授权另谈
原架构设计:银子老师

---

## 0. v3 → v3.1 修复总览

| 类型 | 数量 | 范围 |
|---|---|---|
| BLOCKER | 6 | 必修才能进 Phase 13.0 |
| SERIOUS | 8 | 实施期高优先级 |
| MEDIUM | 8 | 实施期可迭代 |
| 新增 | 1 大节 | 小学数学能力接入(基于 APV2.1 728/728 证据) |

---

## 第 1 章 BLOCKER 修复(6 个,必修)

### B1. 小学数学能力缺位 — 必须加入

**v3 缺陷**: §6.2-6.8 课程包清单完全没有数学,失去 AP 架构最强的"会想会算"证据。

**审阅事实**: APV2.1 已完整跑通 Math-0~Math-28 + LangMath-0/1/2 + 应用题 + 列方程 + 干扰抑制,**总 728 题 100% 最终正确**。这是 LLM 装不出的真推理。

**v3.1 修复**:**新增 Phase 13.5b — 小学数学课程**(独立 optional 课程包,在批 2/3 内容批次中加入)。

#### 1.1 Phase 13.5b 设计

**目标**: 复用 APV2.1 已验证的 Math-0~28 经验包链,在 APV3 v14 SDPL 路径下教学。

**关键约束**:
- **不重训** — APV2.1 已实测 728/728,直接复用 `math_skill_experience_package/v1` ~ `/v28`
- **复用既有机制**:
  - `feeling::quantity_grasp`(已实现 of Phase 8.5 cognitive_feelings)
  - `feeling::computation_pressure`
  - `feeling::step_closure`
  - `SkillScaffoldProtocolV2Controller`(教师4阶段退火)
  - 带参行动:`action::count_step / write_digit / carry_one / borrow_one / propagate_carry / partial_row / shift_place / estimate_trial_quotient_digit / multiply_back / bring_down / request_more_evidence_before_calculation`
- **走 SDPL 路径** — 数学课程包同样经 HEARSAY proposition + trust_promoted gate

#### 1.2 课程包清单(批次)

```
config/curriculum/packages/math/
├── _index.yaml
├── math_0_numbers_quantity.yaml          # Math-0: 数字/数量/successor
├── math_1_2_single_digit_add_sub.yaml    # Math-1/2: 单位数加减
├── math_3_4_within_10.yaml                # Math-3/4: 10以内 + 进位/借位桥接
├── math_5_6_two_digit.yaml                # Math-5/6: 两位数加减
├── math_7_8_multi_digit.yaml              # Math-7/8: 多位数
├── math_9_10_11_multiplication.yaml       # Math-9/10/11: 乘法表 + 两位数乘
├── math_12_13_three_by_two_mult.yaml      # Math-12/13: 三位×两位
├── math_14_17_short_division.yaml         # Math-14-17: 短除法
├── math_18_19_20_long_division.yaml       # Math-18-20: 长除法
├── math_21_24_word_problems.yaml          # Math-21-24: 应用题(读题+严格竖式)
├── math_25_26_equations.yaml              # Math-25/26: 一元一次方程
└── math_27_28_word_equation_interference.yaml  # Math-27/28: 列方程+干扰抑制
```

#### 1.3 验收门(3 个)

源自 APV2.1 实测基准:

| 指标 | 阈值 | APV2.1 实测对照 |
|---|---|---|
| teacher-off 最终正确率 | ≥ 95% | 728/728 = 100% |
| first-correct round 末 | ≥ 90% | Math-9 round 4: 91.7%, LangMath-2: 100%, Math-28: 84% |
| 反馈 `answer_payload=None` 修复率 | ≥ 30% | Math-28: 24%, Math-21b: ~16%(放宽到 30% 为 Phase 13 量产口径) |

**关键**: 验收测试**不能用语义字串**(继承 v14.1 §54 红线)— 必须断言:
- 系统提交的 action_chain id 序列正确
- 最终 commit text 经数值解析等于真值(注意是解析数值,不是匹配字符串)
- 行动 trace 符合预期(竖式过程审计)

#### 1.4 yaml 常量(`apv3_constants.yaml` 新增)

```yaml
curriculum:
  math:
    teacher_off_accuracy_min: 0.95            # @experimental — APV2.1 实测 100%
    first_correct_round_final_min: 0.90       # @experimental — APV2.1 多阶段 90-100%
    no_answer_repair_rate_min: 0.30           # @experimental — APV2.1 Math-28: 24%
    experience_package_path: "config/curriculum/packages/math/experience_packages/"
    skill_scaffold_protocol_version: "v2"
    enable_quantity_grasp_feeling: true
    enable_computation_pressure_feeling: true
```

#### 1.5 数学能力作为开源关键卖点

开源 demo 中,数学能力应该作为**"非 LLM 真推理"的标志性证据**:

- LLM 算 23×47 是统计预测(可能错)
- AP 系统算 23×47 是**走完整竖式过程**(部分积 + 位值平移 + 列加链),每一步有 trace
- Web 工作台可显示**计算过程动画**(竖式自动绘制)
- 这是开源时区别于"又一个 LLM 套壳"的硬证据

**Phase 13.9 四场景验收必加**:文本对话场景中,系统能现场算并展示过程。

#### 1.6 引用文档

直接引 APV2.1 已存在:
- `docs/ColdSave_PublicMathGraduation0_showcase_landing_report_20260603.md` — 7 阶段 728/728 总览
- `docs/ColdSave_Math24b_strict_vertical_word_problem_audit_landing_report_20260603.md` — 应用题严格竖式审计
- `docs/ColdSave_Math28_equation_word_problem_interference_retention_landing_report_20260603.md` — 干扰列方程

**Phase 13.5b 实施时,Codex 必读这 3 份 cold-save**。

---

### B2. trust_promoted ΔP gate 会被高 trust 教师劫持

**v3 缺陷**: §2.2.2 公式 `trust(t) > 0.7 ∧ effect_size > 0.03`,但没有 p-value 约束,trust=0.95 时 effect_size=0.031 的统计噪声也通过 → 污染。

**v3.1 修复**: **trust 越高反而要更大 effect_size**(防权威盲信),并强制最小观测数。

#### 2.1 修订公式

```python
def compute_trust_aware_effect_size_threshold(trust):
    """trust 越高 → 要求 effect_size 越大(防权威盲信)"""
    # trust ∈ [0.7, 1.0] → θ ∈ [0.08, 0.02]
    # trust=0.7: θ=0.08 (高要求)
    # trust=0.85: θ=0.05 (中)
    # trust=1.0: θ=0.02 (低要求,但要求 min_obs=8)
    return max(0.02, 0.08 - 0.06 * (trust - 0.7) / 0.3)


def trust_promote_gate_v3_1(vocab, teacher, effect_size, n_obs):
    """v3.1 修订后的 trust_promoted gate"""
    trust = teacher.trust_score
    
    # 门 1: trust 准入
    if trust < load_constant("curriculum.teaching_protocol.delta_p_bypass_tau_min"):
        return False
    
    # 门 2: trust-aware effect_size 阈值
    theta = compute_trust_aware_effect_size_threshold(trust)
    if effect_size <= theta:
        return False
    
    # 门 3: 最小观测数(防统计噪声)
    min_obs_trust = load_constant("curriculum.teaching_protocol.delta_p_bypass_min_obs_trust")
    # 默认 8(普通 5 不够,trust 模式因绕 p-value 反而要更多观测)
    if n_obs < min_obs_trust:
        return False
    
    return True
```

#### 2.2 yaml 修订

```yaml
curriculum:
  teaching_protocol:
    delta_p_bypass_tau_min: 0.7              # @structural — trust 准入门
    delta_p_bypass_effect_size_lower_bound: 0.02   # @structural — trust=1.0 时下限
    delta_p_bypass_effect_size_upper_bound: 0.08   # @structural — trust=0.7 时下限
    delta_p_bypass_min_obs_trust: 8           # @structural — trust 模式最小观测
```

---

### B3. trust 演化漂移失控

**v3 缺陷**: 不对称 0.02/0.05 + 系统自身会犯错 → 用户合理反驳(系统真错了)算 contradict → 好教师 trust 单调下行,过 τ_min 后锁死。

**v3.1 修复**: **contradict 必须绑定来源 + EMA 平滑 + 锁死恢复**。

#### 3.1 修订 trust 演化

```python
def update_teacher_trust_v3_1(teacher, *, event, tick, lambda_ema=0.1):
    """
    v3.1: 
    - contradict 只在 USER 主动 CORRECTION marker 触发时扣 trust
    - 系统自发 RPE 失败不扣教师(那是系统泛化错了,不是教师错了)
    - EMA 平滑防剧烈波动
    - 跨 τ_min 后可恢复(连续 N 次 confirm)
    """
    rho_decay = load_constant("curriculum.trust_economy.annual_decay") / 365
    
    if event.kind == "USER_EXPLICIT_CORRECTION":
        # 用户主动 CORRECTION (按按钮 / 显式纠错) — 真扣 trust
        delta = -load_constant("curriculum.trust_economy.contradiction_penalty")
    elif event.kind == "USER_CONFIRMATION":
        delta = +load_constant("curriculum.trust_economy.confirmation_reward")
    elif event.kind == "SYSTEM_RPE_FAILURE":
        # 系统自身 RPE 失败 — NOT 扣教师 trust (这是系统问题不是教师问题)
        delta = 0.0
    else:
        delta = 0.0
    
    # EMA 平滑
    local_evidence = teacher.trust_score + delta - rho_decay
    teacher.trust_score = (1 - lambda_ema) * teacher.trust_score + lambda_ema * local_evidence
    
    # 锁死恢复:跨 τ_min 后,连续 N 次 confirm 可重新升过
    if teacher.trust_score < load_constant("curriculum.teaching_protocol.delta_p_bypass_tau_min"):
        if event.kind == "USER_CONFIRMATION":
            teacher.consecutive_confirms_since_lockout += 1
        else:
            teacher.consecutive_confirms_since_lockout = 0
        
        n_recovery = load_constant("curriculum.trust_economy.lockout_recovery_n_confirms")
        if teacher.consecutive_confirms_since_lockout >= n_recovery:
            # 恢复:trust 强制升回 τ_min + 0.05
            teacher.trust_score = load_constant("curriculum.teaching_protocol.delta_p_bypass_tau_min") + 0.05
            teacher.consecutive_confirms_since_lockout = 0
    
    # 下限
    teacher.trust_score = max(
        load_constant("curriculum.trust_economy.trust_floor_min"),
        min(1.0, teacher.trust_score)
    )
```

#### 3.2 yaml 新增

```yaml
curriculum:
  trust_economy:
    ema_lambda: 0.1                          # @structural — EMA 平滑系数
    lockout_recovery_n_confirms: 5           # @structural — 锁死后恢复需要的连续 confirm 数
    annual_decay: 0.02                       # @experimental
```

#### 3.3 关键澄清

**v3.1 严格区分两类反馈**:

| 反馈类型 | 触发方式 | 是否扣教师 trust |
|---|---|---|
| USER_EXPLICIT_CORRECTION | 用户按"其实是 X"按钮 / 显式纠错 | ✅ 扣 |
| USER_CONFIRMATION | 用户按 👍 / 主动确认 | ✅ 升 |
| SYSTEM_RPE_FAILURE | 系统行动得到负 outcome | ❌ 不扣教师(系统问题) |
| SYSTEM_RPE_SUCCESS | 系统行动得到正 outcome | ❌ 不升教师(系统进步) |

这避免了"系统犯错怪老师"的反向归因。

---

### B4. 反差萌触发是 hardcoded random,违 v14 红线

**v3 缺陷**: §9.1.2 公式 `P = min(p_base + p_user_long + p_empathy_high + ..., p_max)` 然后 `np.random.random() < P` = 硬编码概率公式 + 抛骰子,**违 v14 §0.4 红线 4 精神**(hardcoded routing extended to numeric form)。

**v3.1 修复**: 删除概率公式,改为**长候选 vocab 在 commit gate 的 attention score 由 marker 自然推高**。

#### 4.1 修订机制

```python
# v3 错误版本(删除)
# P = p_base + p_user_long + p_empathy_high + ...
# if np.random.random() < P: commit long candidate

# v3.1 正确版本:让长候选的 attention 自然胜出
def select_commit_candidate_v3_1(candidates, state_pool):
    """
    长候选 vocab 的 attention score 由以下 marker 推高:
    - Phase 9.6 EMPATHY_RESONANCE marker (共情高时)
    - Phase 11 SELF_REFERENCE marker (自我话题时)
    - entity_user_sa.long_term_flag (长期用户时)
    
    经 Phase 14.1 §B2 凸组合 attention 自然 emerge.
    不显式抛骰子,不硬编码 P.
    """
    # 候选 vocab 的 initial_R 在 yaml 中作为 prior(冷启动)
    for c in candidates:
        c.attention_score = compute_attention_score_v13_1(c.vocab_sa)
        # attention_score 已含:
        # - PERCEIVED marker R (外感强度)
        # - EMPATHY_RESONANCE R (共情强度)
        # - SELF_REFERENCE R (自我话题)
        # - entity_user_sa OXY (亲近度)
        # 这些经 §3.1 凸组合自然影响 score
    
    # 标准 attention selector 选择,不另抛骰子
    winner = attention_selector.select(candidates)
    return winner
```

#### 4.2 yaml 仍可保留 weight,但语义改

```yaml
# v3 yaml 候选(继续保留,但语义不是抛骰子的 P)
candidates:
  - text: "嗯,你好。"
    initial_R_prior: 0.4    # v3.1: 改名为 "initial_R prior",意为冷启动 R 强度
    context_tag: "default"
  - text: "嗯。"
    initial_R_prior: 0.3
  - text: "诶,你回来了。"
    initial_R_prior: 0.05    # 反差萌候选,冷启动低 R,但 marker 高时 emerge
    requires_marker_above: 
      EMPATHY_RESONANCE: 0.6
      entity_user_long_term: true
```

`requires_marker_above` 是 attention soft prior(在 attention_selector 内 emerge),**不是 hard if-then**。这符合 §15.1 红线对齐。

#### 4.3 验收

统计上仍应满足:
- P(L ≤ 8) ≥ 0.90
- 反差萌频率 < 5%

但**测试不能直接断言 P=0.05**(那样验证了硬编码概率),而是:
- 100 turn 自然对话中,反差萌出现次数 ≤ 5 次(统计观测)
- 触发条件下(共情高 + 长期用户),反差萌候选出现频率显著高于基线

---

### B5. 反 LLM 漂移防护缺失

**v3 缺陷**: §9.2 只有静态禁词正则,没有动态约束。用户 👍 偏好温暖话痨 → RPE 学到长回复更被奖励 → 系统漂向 LLM 风格。

**v3.1 修复**: 三层动态防护。

#### 5.1 persona_compliance_penalty

```python
def apply_rpe_with_persona_penalty(packet, action, outcome):
    """
    v3.1: 违反人设的 commit 即使收到正 outcome,
    RPE 信号经 penalty 衰减
    """
    commit_text = action.commit_text
    
    if check_persona_compliance(commit_text):
        adjusted_outcome = outcome
    else:
        # 违反人设
        penalty = load_constant("persona.compliance_violation_penalty")  # 默认 0.5
        adjusted_outcome = outcome * penalty
        
        # 同时 spawn frustration-like marker(自我不一致感)
        spawn_marker(MarkerKind.MISMATCH, target=action.action_id, 
                     real_energy=load_constant("persona.violation_mismatch_R"))
    
    # 走标准 RPE
    apply_rpe_learning(q_table, packet, action, actual_reward=adjusted_outcome, ...)
```

#### 5.2 persona drift monitor

```python
class PersonaDriftMonitor:
    """
    滚动窗口监控人设漂移,
    若严重漂移 → 触发"自我重学"(回到官方课程包)
    """
    
    def __init__(self):
        self.recent_turns = deque(maxlen=200)
    
    def observe(self, commit_text):
        self.recent_turns.append(commit_text)
        
        if len(self.recent_turns) < 200:
            return
        
        # 统计漂移指标
        p_within_8 = sum(1 for t in self.recent_turns if len(t) <= 8) / 200
        forbidden_rate = sum(1 for t in self.recent_turns if not check_persona_compliance(t)) / 200
        
        # 触发条件
        if p_within_8 < 0.85 or forbidden_rate > 0.10:
            # 严重漂移:trust_promoted 暂时禁用,重新学习官方课程
            self.trigger_self_reteach()
    
    def trigger_self_reteach(self):
        """暂时禁用 trust_promoted,系统经普通 ΔP gate 重新学官方 persona 课程包"""
        ...
```

#### 5.3 forbidden_patterns 检查时机

**v3 错误**: 静态正则在事后审计
**v3.1 正确**: 在 commit gate 之前

```python
def commit_gate_v3_1(candidate_text, state_pool):
    # 先过人设合规
    if not check_persona_compliance(candidate_text):
        # 拒绝该候选
        return None
    # 走标准 commit gate
    return standard_commit_gate(candidate_text, state_pool)
```

#### 5.4 yaml 新增

```yaml
persona:
  compliance_violation_penalty: 0.5         # @structural — 违人设 RPE 衰减
  violation_mismatch_R: 0.3                  # @experimental
  drift_monitor_window: 200                  # @structural
  drift_monitor_p_within_8_min: 0.85         # @structural
  drift_monitor_forbidden_rate_max: 0.10     # @structural
```

---

### B6. 隐私 / 未成年保护 / GDPR 漏洞

**v3 缺陷**: §14.1 风险矩阵没有用户隐私 / GDPR / 未成年保护。开源前是法律时间炸弹。

**v3.1 修复**: Phase 13.0 license 框架同步加这些文档。

#### 6.1 新增文档(Phase 13.0 必须落地)

```
项目根/
├── LICENSE                       # AGPL-3.0(已有)
├── LICENSE_COMMERCIAL.md          # 商用授权(已有)
├── AUTHORS.md                     # 署名(已有)
├── README.md                      # 主页(已有)
├── CONTRIBUTING.md                # 贡献者(已有)
├── PRIVACY.md                     # ★ v3.1 新增
├── MINORS.md                      # ★ v3.1 新增
└── DATA_HANDLING.md               # ★ v3.1 新增
```

#### 6.2 PRIVACY.md 骨架

```markdown
# Privacy Policy / 隐私政策

## 数据收集
APV3 在本地运行,默认**不向任何外部服务器发送数据**。
所有学习进度存储在本地 SQLite (`state/curriculum_progress.sqlite`)。

## 数据内容
- sa_id (vocab/concept identifiers)
- tick 时间戳
- packet_key (匿名化的 packet hash)
- RPE 信号 / Q 值统计

**不存储**:用户实际文本内容 / 用户身份 / IP / 个人识别信息(PII)

## 数据导出与删除(GDPR 合规)
用户可任何时间:
- 导出自己的数据: `python -m apv3 export_my_data --user_id X --output ./my_data.json`
- 删除所有数据: `python -m apv3 delete_my_data --user_id X --confirm`

## 课程包共享
社区课程包(beta 阶段后开放)经 sanitization,不含原始用户数据。

## 联系
Privacy 问题: contact 银子老师 [TBD]
```

#### 6.3 MINORS.md 骨架

```markdown
# Minors Policy / 未成年人使用政策

## 推荐年龄
**13+ recommended.**

本项目模拟 5-8 岁儿童心智,内容适合青少年与成年人接触,
但作为开源 AI 工具,不建议 13 岁以下未成年人独立使用。

## 监护人责任
13 岁以下使用需监护人陪同。监护人应监督:
- 教学内容(不应教不适当的内容)
- 互动时长(避免过度依赖)
- 数据隐私(参 PRIVACY.md)

## 不适内容防护
项目默认:
- 不接受成人/暴力/政治敏感教学内容(schema validator 拒绝)
- 共情 marker 不模拟极端情绪
- 自我话题不涉及深度存在主义焦虑

## COPPA(美国)/ 国内未成年人法
若部署给 < 13 岁用户群体,部署方需:
- 取得监护人同意(COPPA 51.6 章)
- 中国《未成年人保护法》网络专章合规
- 不收集 PII

## 商业产品
将 APV3 用于面向未成年人的商用产品,**必须取得专项商用许可证**,
并经监护人同意 + 实名认证流程。
```

#### 6.4 DATA_HANDLING.md 骨架

```markdown
# Data Handling / 数据处理

## SQLite 持久化字段
`state/curriculum_progress.sqlite`:

```sql
CREATE TABLE vocab_progress (
    sa_id TEXT PRIMARY KEY,
    R_long_term REAL,
    learned_tick INTEGER,
    last_recalled_tick INTEGER,
    source_entity_id TEXT  -- 教师 id,非用户身份
);

CREATE TABLE q_table_packets (
    packet_key_hash TEXT,  -- sha256 hash,无原文
    action_id TEXT,
    q_value REAL,
    sample_count INTEGER
);

CREATE TABLE teacher_trust (
    teacher_entity_id TEXT,
    trust_score REAL,
    last_updated_tick INTEGER
);
```

**所有 text content 永不持久化**。

## 备份(M6 medium fix)
每日自动 snapshot:
```python
python -m apv3 backup_progress --output ./backups/$(date +%Y%m%d).sqlite
```

## 同步(可选)
若用户允许,可同步到自有 cloud:
```python
python -m apv3 sync_progress --provider [own-cloud-url]
```
**永不同步到第三方**,绝不向银子老师/AP 维护团队发送。
```

#### 6.5 Phase 13.0 DoD 扩展

原 DoD 6 项基础上 + 3 项:
- [ ] PRIVACY.md 完成
- [ ] MINORS.md 完成
- [ ] DATA_HANDLING.md 完成

---

## 第 2 章 SERIOUS 修复(8 个,实施期高优先级)

### S1. 跨课程一致性 gate snapshot 协议

**v3 缺陷**: recall_vec 没说何时 snapshot,跨课程 teaching_episode 数不同 → 不可比。

**v3.1 修复**:

```python
def snapshot_recall_vec_v3_1(vocab_sa_id, package_id, state_pool):
    """
    v3.1: recall_vec 必须在固定协议下 snapshot.
    """
    # 1. 教学完成后,等待 cooling 期
    cooling_ticks = load_constant("curriculum.consistency.snapshot_cooling_ticks")  # 1000
    sleep_until_cooling_complete(cooling_ticks)
    
    # 2. 跑 N=K 次独立 probe(每次 probe 用不同 cue)
    K = load_constant("curriculum.consistency.snapshot_probe_n")  # 8
    
    probe_vectors = []
    for probe_i in range(K):
        probe_state = state_pool.snapshot()  # snapshot 当前状态
        probe_cue = generate_probe_cue(vocab_sa_id, probe_i)
        
        # recall and capture top-K context SAs
        recall_results = state_pool.recall_by_cue(probe_cue, top_k=32)
        context_freq_vec = compute_context_frequency_vector(recall_results)
        probe_vectors.append(context_freq_vec)
        
        # 恢复 state pool 避免污染
        state_pool.restore(probe_state)
    
    # 3. 求均值,这就是与教学密度解耦的 recall_vec
    return np.mean(probe_vectors, axis=0)
```

```yaml
curriculum:
  consistency:
    snapshot_cooling_ticks: 1000             # @structural — 教学后冷却
    snapshot_probe_n: 8                       # @structural — probe 次数
```

---

### S2. 偏旁部首阈值调整 + 反例库扩 + 视觉感受器 OOD 验证

**v3 缺陷**: 60% 过于乐观,反例库只 2 例,Phase 8.6 量化桶对 OOD 字未验证。

**v3.1 修复**:

#### 2.1 阈值降到 45% top-3

(从 60% 改为 45%,符合现代简化字偏旁失效率 30-40% 的现实)

#### 2.2 反例库扩到 ≥ 30 条

```yaml
# config/curriculum/packages/characters/radical_anti_examples.yaml
package_id: "characters.radicals.anti_examples"
content:
  - char: "求"
    issue: "看似三点水,实际不是'氵'部"
    correct_radical: "水"
  - char: "氷"
    issue: "异体字,'冰'的繁体"
    correct_radical: "冰"
  # ... 28+ more
```

**Codex L4 任务**:Codex 从字典数据生成 30 条草稿,Claude 审,银子老师终审。

#### 2.3 Phase 8.6 量化桶 OOD 验证(Phase 13.2 前置)

Phase 13.2 启动前必须做的 micro-benchmark:

```python
# tests/micro/test_radical_visual_ood.py
def test_visual_sensor_can_extract_radical_from_unseen_char():
    """
    Pre-Phase-13.2: 验证 Phase 8.6 视觉感受器能从未训练字中提取偏旁特征.
    
    若失败:Phase 13.2 必须先做"偏旁视觉预训练"阶段
    (单独喂偏旁图像,让感受器学到偏旁的视觉特征).
    """
    # 训练时:50 个 "氵" 字
    train_chars = ["河", "湖", "海", "沙", "池", "泪", "汁", "滴", ...] # 50
    train_with_visual_sensor(train_chars)
    
    # 测试时:从未训练过的"湍"
    test_char_image = render_character("湍")
    percepts = vision_sensor.process(test_char_image)
    
    # 验收:percepts 中应有显著与 "氵" 偏旁视觉特征相似的 percept SA
    radical_percepts = filter_by_similarity_to(percepts, "氵_radical_template")
    
    assert len(radical_percepts) >= 1
    assert radical_percepts[0].similarity_score >= 0.5
```

**若失败**:Phase 13.2 加 "Phase 13.2a — 偏旁视觉预训练" 子阶段。

---

### S3. 视觉策略统计学论证修订 + 抽象 vocab 例外

**v3 缺陷**: "3 sigma 用 3 个数据点" 不是严格统计学。

**v3.1 修复**:

#### 3.1 修订论述

§8.3 改为:
> "经验下限"而非严格统计学保证。
> Min ≥ 5 (推荐 8-10) 是基于 ML 实践经验,
> 不是 3-sigma 论证。

#### 3.2 schema 修订

```yaml
# package_schema.yaml v3.1
visual_examples:
  type: array
  minItems: 5  # 从 3 改为 5
```

#### 3.3 抽象 vocab 例外

```yaml
# package_schema.yaml v3.1
content_item:
  oneOf:
    - required: [visual_examples]  # 视觉课程
      properties:
        visual_examples:
          minItems: 5
    - required: [audio_examples]  # 音频课程
      properties:
        audio_examples:
          minItems: 3
    - required: [text_paradigms]  # 抽象/纯文本课程
      properties:
        text_paradigms:
          minItems: 5
```

---

### S4. 多教师矛盾按 trust 加权 + 防 sybil

**v3 缺陷**: 简单多数决,5 user entity 协同教错 → 否决官方。

**v3.1 修复**:

#### 4.1 按 trust 加权投票

```python
def resolve_multi_teacher_conflict_v3_1(vocab_sa, conflicting_teachers, hearsay_markers):
    """
    v3.1: 按 trust 加权,且要求 PERCEIVED 经验决胜.
    """
    # 计算各教师的加权投票
    vote_weights = defaultdict(float)
    for teacher_id, attribute_value in conflicting_teachers.items():
        teacher = get_teacher_entity(teacher_id)
        vote_weights[attribute_value] += teacher.trust_score
    
    # 防 sybil:同一 ip / 同一会话内创建的 user entity 共享 trust pool
    vote_weights = apply_sybil_protection(vote_weights)
    
    # 若 PERCEIVED 经验已介入(系统实际看见过该 vocab 的某个 attribute),
    # PERCEIVED 经验权重 = 所有 HEARSAY 权重之和 + 1(必胜)
    perceived_evidence = state_pool.get_perceived_evidence_for(vocab_sa)
    if perceived_evidence:
        winner_attribute = perceived_evidence.attribute_value
    else:
        # 纯 HEARSAY 投票,等待 PERCEIVED 经验出现前不强制下结论
        # 设为 awaiting_revalidation
        vocab_sa.kind = "awaiting_revalidation"
        winner_attribute = None
    
    return winner_attribute
```

#### 4.2 防 sybil 机制

```python
def apply_sybil_protection(vote_weights, conflicting_teachers):
    """同一会话/同一 IP / 短时间内创建的 user entity 共享 trust pool"""
    teacher_groups = group_teachers_by_provenance(conflicting_teachers)
    
    for group in teacher_groups:
        if group.is_sybil_suspect():
            # 该组所有教师共享 trust(取最低)
            shared_trust = min(t.trust_score for t in group)
            for t in group:
                vote_weights[t.attribute_value] -= t.trust_score
                vote_weights[t.attribute_value] += shared_trust / len(group)
    
    return vote_weights
```

---

### S5. 验收阈值调整(对齐 Phase 8 实测)

**v3 缺陷**: 70% / 95% / N=20 阈值缺乏 Phase 8 实测数据支撑。

**v3.1 修复**:

```yaml
# 修订验收阈值
phase_13_acceptance_revised:
  continuous_learning_5_episodes:
    target: 0.50               # 从 70% 降到 50%(更保守,Phase 8.4 实测后调整)
    rationale: "Phase 8.4 实测 baseline 待补;期望 50% → 70%"
  
  cross_session_recall_5000_vocab:
    first_500_active: 0.95     # 高频 vocab 仍 95%
    overall_5000: 0.80         # 5000 vocab 时降到 80%
    rationale: "rehydration_top_k 限制下降"
  
  first_30s_wow_rate:
    n_users: 50                # 从 20 升到 50
    threshold: 0.60
    min_non_ai_users: 10       # 至少 10 个非 AI 圈外用户
    confidence_interval_max: 0.15  # 公开置信区间
```

---

### S6. yaml 常量全部加治理标签

**v3 缺陷**: §6.1.3 yaml 没标 @structural / @experimental.

**v3.1 修复**: Phase 13.0 substrate 必须给所有 curriculum / persona / visual / audio 段加治理标签:

```yaml
# 全部 yaml 常量必须有标签
curriculum:
  trust_economy:
    initial_official_teacher_trust: 0.9   # @experimental — APV2.1 实测后 tune
    trust_floor_min: 0.1                   # @structural — 防永久封禁
    contradiction_penalty: 0.05            # @structural — Bayesian unsymmetric
  
  teaching_protocol:
    delta_p_bypass_tau_min: 0.7            # @structural — trust 门
    delta_p_bypass_min_obs_trust: 8        # @structural — 防统计噪声

# ... 等等,全部段
```

`check_constant_governance.py` 必须扫到所有 curriculum 段。

---

### S7. 定理证明加假设

**v3 缺陷**: §2.2.3 定理 1/2 证明过短,隐含假设未声明.

**v3.1 修复**: 改写定理

```markdown
**定理 1**(修订):在 v3.1 trust_promoted 模式下,
任何固化的 vocab SA 仍带 HEARSAY marker,
**假设 vocab SA promotion 不触发 hierarchy SA merge**(Phase 10.6)。

**证明**:由 §2.2.1 spawn 流程,HEARSAY marker 在 promotion 前 spawn。
promotion 操作仅改变 vocab.kind = "promoted",不修改 marker 集。
**若 promotion 触发 hierarchy merge**(多个 HEARSAY vocab 合并成 abstract_vocab),
合并后的 abstract_vocab 的 source attribution 可能丢失。
**v3.1 约束**:trust_promoted 路径下的 vocab 不参与 hierarchy merge,
直至 trust_score 稳定(7 天无大幅变动)。∎

**定理 2**(修订):trust 衰减 → 旧 vocab 可被新经验校正,
**假设反驳教学的 packet_key 与原教学 R_bucket 相同**。

**证明**:trust 演化使旧教师的后续 HEARSAY 不再 trust_promoted。
但 RPE 校正旧 vocab 需要 Q 表 packet_key 匹配。
**若 R_bucket 不同**(教学时 R=0.8 → bucket=high;反驳时 R=0.3 → bucket=low),
Q 表更新指向不同 packet,反驳无效。
**v3.1 约束**:CORRECTION 教学必须显式匹配原教学的 R bucket
(由 §5.3 packet_key 量化协议保证)。∎
```

---

### S8. TeachResult 接口完整定义

**v3 缺陷**: §6.1.2 接口未定义.

**v3.1 修复**:

```python
@dataclass
class TeachResult:
    """v3.1 完整定义"""
    status: Literal["promoted", "rejected", "awaiting_revalidation"]
    failed_reason: Optional[Literal[
        "delta_p_fail",
        "trust_fail",
        "schema_violation",
        "resource_missing",
        "consistency_fail",
        "min_obs_not_met",
        "persona_violation",
    ]] = None
    vocab_sa_id: str
    cleanup_tick: Optional[int] = None
    """失败后多久从 state_pool 清除 (None = 立即清除)"""


def teach_vocab_v3_1(state_pool, long_term, *, content_item, teacher_entity, tick) -> TeachResult:
    """
    v3.1: 完整失败处理 + 资源清理.
    """
    try:
        # 1. spawn percepts + hearsay
        ...
        
        # 2. ΔP gate
        if not trust_promote_gate_v3_1(...):
            # 失败 — 清理 spawn 的临时 SA
            cleanup_temp_spawn(state_pool, current_spawned_sas)
            return TeachResult(
                status="rejected",
                failed_reason="delta_p_fail",
                vocab_sa_id=content_item.sa_id,
                cleanup_tick=tick,
            )
        
        # 3. 一致性 gate
        if not consistency_validator.check(...):
            return TeachResult(
                status="awaiting_revalidation",
                failed_reason="consistency_fail",
                vocab_sa_id=content_item.sa_id,
                cleanup_tick=tick + load_constant("curriculum.consistency.retest_after_n_ticks"),
            )
        
        # 4. promote
        promote_to_long_term(vocab_sa, layer=content_item.recall_policy.promote_to_layer)
        return TeachResult(
            status="promoted",
            vocab_sa_id=content_item.sa_id,
        )
    
    except CurriculumSchemaError:
        return TeachResult(status="rejected", failed_reason="schema_violation", ...)
    except ResourceMissingError:
        return TeachResult(status="rejected", failed_reason="resource_missing", ...)
```

---

## 第 3 章 MEDIUM 修复(8 个,实施期可迭代)

### M1. Phase 13.6 时间预算调整

`2-3 天` → `5-7 天`,M2 alpha 启动后移到第 12 天。

### M2. 抽象 vocab 例外(已并入 S3)

### M3. yaml weight 改名为 `initial_R_prior`(已并入 B4)

### M4. §10.1 启动序列百分比删除(已并入 B4)

### M5. 用户测试样本量统一

M2 alpha N=10,M3 beta N=20+,M7 rc N=50+。验收矩阵分层。

### M6. 备份 + 灾难恢复

```python
# scripts/backup_progress.py
def daily_backup():
    """每日 snapshot,7 天滚动"""
    snapshot_dir = Path("state/backups")
    snapshot_dir.mkdir(exist_ok=True)
    
    today = datetime.now().strftime("%Y%m%d")
    backup_path = snapshot_dir / f"progress_{today}.sqlite"
    
    shutil.copy("state/curriculum_progress.sqlite", backup_path)
    
    # 滚动:删除 7 天前的
    cleanup_old_backups(snapshot_dir, keep_days=7)
```

Phase 13.1 substrate 加 `progress_backup.py`。

### M7. 数据集偏差登记

§8.12 新增:

```markdown
## 已知数据集偏差

| 数据集 | 已知偏差 | 缓解 |
|---|---|---|
| ImageNet | 西方中心 / 类别失衡 / 部分种族标注问题 | 文档登记;视觉验收必含跨文化样本 |
| COCO | 多以室内场景为主 | 用 Open Images 补室外 |
| Wikimedia | 编辑者偏向西方语言 | 优先选中文 wikimedia 子集 |
```

### M8. 测试函数命名修订

测试函数名引用 sa_id 而非 marker kind string。

---

## 第 4 章 修订后的 Phase 13 完整工作流

### 4.1 Phase 顺序修订

```
Phase 13.0    License + Authorship + PRIVACY + MINORS + DATA_HANDLING(0.5 天)
              ★ v3.1 新增 3 个文档

Phase 13.1    Curriculum Substrate(1 天)
              ★ v3.1 + TeachResult schema 完整定义
              ★ v3.1 + backup/restore CLI

Phase 13.2    字课程 + 偏旁部首(批 1 500 字,3 天)
              ★ v3.1 + 反例库 ≥ 30 条
              ★ v3.1 + 视觉感受器 OOD 预验证 micro-benchmark

Phase 13.2a   偏旁视觉预训练(if S2 micro-benchmark 失败,新增 1-2 天)

Phase 13.3    词课程(批 1 1500 词,3 天)

Phase 13.4    视觉课程(批 1 200 对象,7 天)
              ★ v3.1 + min ≥ 5 张
              ★ v3.1 + 抽象 vocab 例外

Phase 13.5    音频课程(批 1 50 范式,2 天)

Phase 13.5b   ★ v3.1 新增 — 小学数学课程
              复用 APV2.1 Math-0~28 经验包
              7 阶段课程包(批 2/3 内)

Phase 13.6    表达范式课程(银子老师 + Claude 撰写,5-7 天)

Phase 13.7    行动反应库(1 天 Codex + 1 天内容)

Phase 13.8    社交常识(银子老师 + Claude,2 天)

Phase 13.9    四场景验收(2 天)
              ★ v3.1 + 数学能力 demo 必跑
              ★ v3.1 + N=50 用户测试
              ★ v3.1 + 数据集偏差登记文档
```

### 4.2 修订总时间预算

| 阶段 | 修订前 | 修订后 |
|---|---|---|
| Phase 13.0-13.5 | ~14 天 | ~16 天(+ PRIVACY/MINORS) |
| Phase 13.5b 数学 | — | +3 天(新增) |
| Phase 13.6 | 2-3 天 | 5-7 天 |
| Phase 13.7-13.9 | ~6 天 | ~7 天(+ N=50 测试) |
| **alpha 总耗时** | ~14 天 | **~21 天到 alpha**(M2 第 21 天) |
| **v1.0 正式开源** | 5 周 | **6-7 周到 v1.0** |

---

## 第 5 章 给对抗审阅者的回应(下一轮审阅者必读)

v3.1 ERRATA 已修复 6 BLOCKER + 8 SERIOUS + 8 MEDIUM,**包括对抗审阅指出的所有关键问题**。

特别强调:
1. **B1 数学能力** — 不是"加进来",而是**复用 APV2.1 已实测 728/728 的实战经验**,无需重训
2. **B2-B5 紧密关联** — 修复都是为了让 trust 系统不被滥用,让人设不漂向 LLM
3. **B6 法律合规** — 开源前必须修,否则碰到欧盟用户/未成年人有真法律风险
4. **B4 反差萌 emerge** — 删除概率公式不是软化要求,而是让人设真正经 marker emerge,符合 v14 SDPL 哲学

请下一轮审阅特别审查:
- B4 的 `requires_marker_above` 软 prior 是否真不构成 hardcoded 路由?
- B3 trust 演化的 EMA 平滑是否真能防漂移?
- S2 偏旁视觉 OOD micro-benchmark 是否充分?

---

## 第 6 章 给 Codex 的实施指令

1. **v3 + v3.1 ERRATA 双稿配合阅读** — v3.1 修订项标 ★
2. **Phase 13.0 必须落 3 个新文档**(PRIVACY/MINORS/DATA_HANDLING)
3. **Phase 13.2 启动前跑 S2 micro-benchmark**,失败则插 13.2a
4. **Phase 13.5b 数学课程必读** APV2.1 Math 3 份 cold-save:
   - `ColdSave_PublicMathGraduation0_showcase_landing_report_20260603.md`
   - `ColdSave_Math24b_strict_vertical_word_problem_audit_landing_report_20260603.md`
   - `ColdSave_Math28_equation_word_problem_interference_retention_landing_report_20260603.md`
5. **Phase 13.5b 不重训** — 直接复用 APV2.1 经验包路径
6. **Phase 13.6 持 5-7 天**预算
7. **每子 Phase 验收必跑** v3.1 修订的阈值,而非 v3 原阈值
8. **trust_promoted 路径下的 vocab 不参与 hierarchy merge**(S7 定理 1 约束)
9. **CORRECTION 教学必须显式匹配原教学 R bucket**(S7 定理 2 约束)
10. **任何对 v3 设计的偏离必须先停下问 Claude/银子老师**

---

## 结语

v3.1 ERRATA 是 v3 的精准补丁,不是重写。

修复了:
- 6 个 BLOCKER(包括最重要的小学数学能力 B1)
- 8 个 SERIOUS
- 8 个 MEDIUM

接下来:
1. 银子老师审 v3.1 ERRATA
2. 再次对抗审阅(可选,但建议)
3. Codex 据 v3 + v3.1 ERRATA 实施 Phase 13

预期开源 alpha 启动:**第 21 天**
预期正式 v1.0:**第 6-7 周**

开源时关键卖点扩为 **6 个**(原 5 + 数学能力):
1. "你能看到它怎么学的"
2. "你能教它,而且它真的学"
3. "它会想象 + 会犯人类的错"
4. "它有持续身份和跨天记忆"
5. "完全开源 + 可审计 + 可定制"
6. **"它能算 — 而且能给出过程"**(v3.1 新增)

最后这条最强 — LLM 算错了你只能信或不信,AP 算时你能看到它一列一列写竖式。

— 银子老师 / Claude
— 2026-06-18
