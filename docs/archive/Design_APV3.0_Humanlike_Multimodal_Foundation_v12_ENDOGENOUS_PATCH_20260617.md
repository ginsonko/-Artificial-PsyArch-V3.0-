# APV3.0 v12 — 持续内源性想象 + 7 底层补完(从 v3-v11 系列底层遗漏中收回)

日期: 2026-06-17
作者: 接手线程
状态: **用户指出 v3-v11 系列遗漏"持续内源性想象 + 想象中学习"——这是 AP 最底层设计之一。Explore 扫遍 APV1/APV2 cold-saves 发现:此机制 90% 已在 `Design_APV3.0能量本体数学模型_20260615.md` §6 完整严格化,只是从未合并入 v1-v11 多模态底座系列。本稿合并 + 补 6 个其他底层遗漏(自传式回忆 / 延迟意图 / 内源 packet / 三类注意力 / 解释作为反向想象 / 复杂感简单感 / 主观能动性)。这是 Phase 8 实施依据的最后一份补丁。**

前身链:v10 主 + v11 patches → **v12 补完(本稿)**

**与 v10 + v11 配套读**:v12 不重写 v10,只是合并已存在但被多模态底座系列遗漏的机制。Phase 8 实施时 v10 主 + v11 patches + v12 三件套同读。

---

## 0. v12 必读:用户指出的根本性遗漏 + Explore 关键发现

### 0.1 用户原话回应

> "在 AP 的设计上,是允许内源性刺激持续的...如果没有任何外界输入,它应该会自己寻找一些曾经还没有完成的任务/还有思考和发展空间的事情/之前注意到了但是没有细想的事情等等,会持续的进行思考,虽然思考的能量状态会比较低,但是也是持续的"
>
> "比如看到一根针,联想到了曾经被扎,疼痛的记忆,被注意力由于压力所关注,此时又发生了针扎气球爆炸的画面,那么气球爆炸的画面和内心中'疼痛'的想象和预测,本身也会因为共现产生关联"
>
> "前一天晚上想到了说第二天我们如果出门,应该绕开修路的地方.然后第二天出门的时候,联想到了做完内心中纯粹想象和推理的记忆,于是利用这个记忆直接绕开了修路"
>
> "这些纯内源性想象和持续性思考也是我们 AP 的底层设计之一,但是你似乎没有完全吸收"

### 0.2 Explore 关键发现(扫遍 APV1/APV2)

**90% 已设计**:`Design_APV3.0能量本体数学模型_20260615.md` §6 "内源性持续(想象/推理/续写)的能量动力学" — v1-v11 多模态底座系列从未引用此文。

**8 个底层机制全部已在 cold-save**:
1. 内源链 §6(能量本体)+ §12.1 target_cap blocker fix
2. 内源 packet substrate(BottomLayer §7.4-7.7 slot_summary/slot_item)
3. 多任务多未完成场景实测(P1-L-12/13/14 已 teacher-off 验证 8/8)
4. 延迟意图机会触发(Stage 0-6 8/8 teacher-off 已课程验证)
5. 自传式回忆 + 关系情绪锚点(APV2.1 v0.1 设计完整)
6. 三类注意力(内源/外部夺取/主动聚焦)同源 softmax 涌现
7. 反向想象 / 惊→解释(能量本体 §7)
8. 反事实查询作为内源链 starter(P1-A/P1-B 验收已有)

**v12 任务**:把这 8 个机制正式嫁接到 v10 主 + v11 patches 上,引用既有 cold-save 作权威来源,**绝不重新发明**。

### 0.3 v12 与之前 v3-v11 多模态底座的关系澄清

| 文档 | 角色 |
|---|---|
| v10 主稿 | Phase 8 实施主文档(多模态认知闭环 + 4 type 架构) |
| v11 补丁 | v10 的 5 个精准 errata |
| **v12 补丁(本稿)** | **补持续内源性想象 + 7 底层补完** |
| `Design_APV3.0能量本体数学模型_20260615.md` | **理论基础**(v10/v11/v12 共同前提) |
| `APV21_BottomLayer_Design_Supplement_20260610.md` | **底层 substrate**(内源 packet) |
| P1-L-12/13/14 cold-saves | **实证基础** |
| `Stage 0-6 DeferredIntentionOpportunityTrigger` cold-save | **跨天意图实证** |

**Phase 8 实施时,Codex 必须读 5 个文档**:v10 + v11 + v12 + 能量本体 §6 + BottomLayer §7。任一漏读 = 缺核心机制。

---

## §44. 持续内源性想象 — 能量本体 §6 正式合并(核心补丁)

### 44.1 完整引用能量本体 §6(逐字,不重述)

引用 `Design_APV3.0能量本体数学模型_20260615.md` §6:

> 无外源或低需求时(λ_fast 与外部 s_attn 都不主导),系统进入**内源链**(图景预期书 §1.4 "长时沉浸想象、推理、内心世界")。机制:
>
> - 内源链**不靠 R**(无外源),靠 V/P/A 维持;§3 的 target_cap 在 baseline 低时压低 V,故内源链能量有限、会自然衰减/疲劳(F 累加),**防无限空想**(对应图景 §6 钝感/累觉,与 §7 收束 max_iters)。
>
> - 一旦外源输入到来且带惊,§5 softmax 立刻把焦点拉到外部(打断内源链)——这就是**多任务打断**的能量本质: 不是脚本切换,是 s_attn^ext 暂时压过内源焦点。
>
> **打断恢复(复刻旧能力,AP-native)**: 被打断的未完成任务 SA 经 ShortTermMemoryWindow 留**衰减的 unfinished_pressure**(进 demand_slow 的 δ_unfin 项)。外部惊退去后(s_attn^ext 衰减),空闲 tick 里 unfinished_pressure 使该任务 SA 的 s_attn 重新爬到 softmax 顶部 → "想起来"续做。**全靠能量竞争,无脚本 mark 时刻/强制选 recall**。

### 44.2 v12 修订:内源链 ≠ V/P/A 维持,而是 V + A 惯性维持(吸收 §12 自审)

能量本体 §12 自审纠正:**P=R−V 在内源链中 < 0(R 蒸发,V 由 Π 维持),β_P·P 是拖累而非支撑**。内源链真正靠 **A-loop 注意力惯性**:

```
a_i → G_i → A_i(衰减 ρ_A),持焦越久 A 越大,越抗弱外扰
```

**v12 修订**:把内源链的 s_attn 拆为:

$$s_{attn}^{internal} = \beta_{pos} \cdot \max(0, P_i) + \beta_A \cdot A_i - \beta_F \cdot F_i$$

(去原带符号 P,内源链 P<0 不再拖累)

`β_pos, β_A, β_F` 全部进 `apv3_constants.yaml`(v11 P2 纪律)。

### 44.3 §12.1 target_cap blocker fix 必须吸收

能量本体 §12.1 指出:**当前代码 baseline 有 0.05 硬钳地板**,这破坏"想象越界防护"(target_cap 应能压到 0)。**Phase 8.3 必须吸收此 fix**:

```yaml
# apv3_constants.yaml v12 新增
energy:
  baseline_floor: 0.0           # @structural — 必须真 0,不是 0.05 钳位
  target_cap_uses_real_ruler: true   # @structural — cap 按对象解耦
```

```python
# Phase 8.3 必须实施
def compute_target_cap_v12(sa, current_tick):
    """
    @op_count: O(1).
    v12 修复 §12.1 blocker:cap 按对象解耦(吸收审计 fix).
    """
    if sa.has_live_external_evidence_this_tick():
        ruler = sa.real_energy        # live 对象用实能量
    else:
        ruler = sa.decayed_baseline   # 衰减 baseline,可真 0
    
    # 不再 max(target, baseline_floor) — 让 punishment 把 cap 连续拉到 0
    target_cap = max(0.0, ruler * load_constant("composed_vocab.target_cap_ratio"))
    return target_cap
```

**验收门**:Phase 8.3 加回归测试 — boot 后喂一次外部输入,N 个空 tick 后断言 calibration trace 的 target_cap 单调趋向 0。**当前 APV2.1 代码 fail,修后 pass = 想象不越界 gate D 通过**。

### 44.4 持续内源性 — 状态空间的"暗能量场"

**用户原话**:"它应该会自己寻找一些曾经还没有完成的任务 / 还有思考和发展空间的事情 / 之前注意到但没细想的事情"

**v12 形式化** — 三个内源能量源(全部既有,不新建):

1. **unfinished_pressure**(BottomLayer §7 + P1-L-14 已实证)
   - 来源:被打断的任务 SA 在 ShortTermMemoryWindow 留 unfinished 状态
   - 注入:`demand_slow.δ_unfin · unfinished_pressure_i`
   - 衰减:每空 tick 衰减 ρ_unfin(yaml),~30 秒半衰期

2. **expectation_pressure**(能量本体 §5 已设计)
   - 来源:expectation_gap CFS feeling(§16.4 v6 已规范)
   - 即"之前预期了某事但未发生"产生持续轻量压力
   - 注入:`demand_slow.δ_exp · expectation_pressure_i`

3. **residual_mass**(v8 §15.3 已设计,这里激活)
   - 来源:ResidualTracker 中未解决的 SA
   - 注入:`G_i^idle = ξ · residual_mass_i`(当 idle_score > θ_idle)
   - 这是用户说的"注意到但没细想的事情"的精确实现

**关键架构原则**:**没有外源输入时,这三个源的能量持续注入 demand_slow / G_i,推动 s_attn 在状态池中产生持续的内源焦点轮换**。这就是"持续想象/思考"的能量基础。

```python
# §44.4 持续内源 step(Phase 8.10 实施)
def step_endogenous_drive(state_pool, t):
    """
    @op_count: O(|active SA|), worst 200 ops/tick.
    
    v12 §44.4:三个内源能量源持续注入,实现"持续想象"
    """
    idle_score = compute_idle_score(state_pool, t)
    idle_threshold = load_constant("endogenous.idle_score_threshold")
    
    is_idle = idle_score < idle_threshold
    
    for sa in state_pool.active_sas():
        # Source 1: unfinished_pressure
        unfinished = sa.short_term_memory.get_unfinished_pressure()
        delta_unfin = load_constant("endogenous.delta_unfinished")
        
        # Source 2: expectation_pressure
        expect_p = sa.get_expectation_pressure()
        delta_exp = load_constant("endogenous.delta_expectation")
        
        # Source 3: residual_mass(idle 时放大)
        residual = residual_tracker.get(sa).unresolved_mass
        delta_res = load_constant("endogenous.delta_residual")
        idle_boost = load_constant("endogenous.idle_boost_factor") if is_idle else 1.0
        
        # 综合注入到 attention_gain
        sa.attention_gain += (
            delta_unfin * unfinished +
            delta_exp * expect_p +
            delta_res * residual * idle_boost
        )
```

### 44.5 内源链 + 标准 softmax = 持续想象自然涌现

**关键**:§44.4 注入 attention_gain 后,**标准 attention selector(v8 §11.3 type-budgeted)自然轮换焦点**。无新机制,无新 selector,无新衰减规则。**"持续想象" emerges from existing energy field**。

**用户验证场景模拟**(用户原例 1):

```
t=0: 视觉感受器 → 针 percept SA, R=0.6
t=1: §15.1 双层 align + standard recall → "曾经被扎" episode SA + "疼痛" feeling SA 被召回 to attention(共现学到的链)
t=2: cognitive_pressure 高 → §16.4 emit "surprise" / "uncertainty" feeling
t=3: 内源链开始(无新外源)— 状态池中 R 蒸发,V/A 维持
t=4: 标准 Cn' 后继偏置 → 针-气球 共现链激活(若历史中学过)→ "针扎气球" SA 涌现 in pool
t=5: 该 SA 与"疼痛"内省 SA 同 tick 持高 attention_gain
t=6+: §2 ComposedVocab 标准 PMI/lag-PMI 看到这次共现 → 统计 +1 → 累积成新链(若反复出现,经 §2.3 ΔP 晋升)
```

**学习闭环**:**想象画面与内省感受的共现完全是既有 §2 + §16.4 的应用**。**无新学习规则**。

### 44.6 跨天/跨 session 想象记忆 → 现实行动(用户原例 2)

**用户场景**:前晚想"绕开修路" → 第二天出门联想到 → 直接绕开

**这是延迟意图机会触发** — Explore 找到 `ColdSave_GL_OpenWorldDeferredIntentionOpportunityTrigger_design_20260611.md`,已 teacher-off Stage 0-6 8/8 验证。

**机制(逐字引用)**:
1. 前晚内源链产生"绕开修路" intent SA(经 §44.4 持续想象 + §44.5 内源链)
2. intent SA 通过 §1.3 short→long 晋升 → long_term R 持续(夜晚 sleep 期 §27 重放进一步巩固)
3. 第二天出门 → 视觉感受 "修路场景" percept → §15.1 双层 align 召回 long_term "绕开修路" intent
4. intent SA 进 attention → 影响行动选择
5. **完全 emerges from**:既有 short→long 晋升 + standard recall + standard action competition

**v12 显式承认**:此 cold-save 是机制完整规范源,APV3 v10 §1.3 + v11 already 支持其全部前提。**Phase 8.10 验收必须包含跨 session 延迟意图测试**。

---

## §45. 自传式回忆 — 心理时间旅行(APV2.1 v0.1 已设计)

### 45.1 既有设计

`Design_APV21_AutobiographicalRecall_RelationalAffect_Anchors_v0_1_20260608.md` 已设计:

- 把已发生的经验**总结为语言形式**(经 §16.9 草稿 commit)
- **关系情绪锚点**:近期与某 entity 的情绪冲突调制召回
- 函数:`compose_next_phrase_from_keywords`, `commit_narrative_segment`

### 45.2 v12 集成位置

继承 v4 §23(依恋)+ v6 §40.A(narrative SA)+ v10 §41.E(self model):

```python
# autobiographical SA 家族(VocabSA type, kind=narrative + 关系锚点)
autobiographical_sa = SA(
    sa_label=f"narrative::autobiographical::{stable_id()}",
    family="narrative",
    components=[event_pointer_1, ...],
    relational_anchor=entity_user_sa,        # 关键:与某 entity 关联
    emotional_state_at_encoding=cfs_snapshot,
    ...
)
```

**Phase 10.1 narrative SA 实施时,要自动包含 autobiographical 子类**(关系锚点字段)。

---

## §46. 内源 packet substrate(BottomLayer §7.4-7.7)

### 46.1 关键引用

`APV21_BottomLayer_Design_Supplement_20260610.md` §7.4-7.7:

> 每 tick 的焦点 packet 被**显式作为虚能量内源 SA bundle 注入回状态池**(slot_summary / slot_item / slot_order / slot_continuity)

### 46.2 为什么这是想象学习的 substrate

**关键**:slot packet 内同时含**外感 SA + 内省 SA + 想象 SA**。它们在同一 packet 中 → 同 tick 进入状态池 → **§2 ComposedVocab 共现统计同等对待**。

**用户原例 1 的精确机制**:
- 视觉"针" + 联想"疼痛" 同在 slot packet → 共现 +1
- 涌现"针扎气球" + "疼痛" 同在 slot packet → 共现 +1
- 反复出现 → §2.3 ΔP 晋升新链

**v12 红线**:Phase 8.3 sensor adapter + Phase 8.4 ComposedVocab 实施时,**必须把 slot packet 作为标准共现学习 substrate**,绝不区分"外感来源"与"想象来源"。这是**想象学习自然 emerge** 的关键。

### 46.3 BottomLayer §7.4 红线继承

- ❌ 不能让短期 packet 变成**比外部更强的"真相"**(slot 不能压过现实输入)
- ❌ 想象不能冒充外部(回到 §44.3 target_cap 0 floor 保护)
- ✅ 想象 SA 与外感 SA **学习上等价**(共现统计同等)
- ✅ 想象 SA 与外感 SA **能量上有差**(R 蒸发,V 维持)

这两组红线**完美统一**:学习等价 + 能量区分 = 想象学习生效 + 想象不冒充现实。

---

## §47. 三类注意力作为可学习行动(Stage 6A)

### 47.1 既有设计

`ColdSave_GL_OpenWorldStage6A_LearnableAttentionFocusAction_design_20260612.md`:**聚焦 / 发散 / 聚焦到某频段**是通用行动注册器里的行动 SA,经 ActionOutcomeMemory 学奖惩。

### 47.2 v12 整合 — 三类注意力同源涌现(能量本体 §5.2)

```
内源注意 (Type 1):无外源,A-loop + §44.4 三源驱动持续焦点
外部夺取 (Type 2):新外源带惊,s_attn^ext 暂时压过内源焦点
主动聚焦 (Type 3):agent 自己 commit action::focus_on(target),把 attention_gain 强行注入特定 SA
```

**三类都从同一 softmax 涌现**,**只是能量驱动源不同**。

**Phase 8.7 实施时**:`action::focus_on / action::defocus / action::shift_band` 在 §16.9 draft action runner 中作为标准 action SA 参与竞争。**不需要单独"主动聚焦"机制**,经 ActionParameterMemory 自然学。

**关键拟人**:agent 可以**学到**"无聊时主动聚焦内心想象"(epistemic drive + Stage 6A action),从而**主动进入持续想象**——不只是被动 idle 漫游。

---

## §48. 解释 = 反向想象(能量本体 §7)

### 48.1 既有设计

`Design_APV3.0能量本体数学模型_20260615.md` §7 "B→C 从'只预测'扩成'预测+解释'":

> 反方向想象 — 找若假设之 V 线 inject 后能预测到此惊,降惊;同 MPE 下降,逆方向 search。

### 48.2 v12 拟人意义

**用户原例 1 拆解**:
- 看到针(惊) → §44.5 内源链尝试**反向解释**:什么 V 注入能让此 R 变得不惊?
- Cn' 反向 search → 召回"曾经被扎"episode + "疼痛"feeling → 注入它们后 R-V 协调,惊降低
- 这就是**"看到针联想到被扎"的精确机制**

**Phase 8.10 实施**:cognitive_feelings/channel.py 已有"surprise"通道。Phase 8.10 加 explanation pathway —— surprise 触发反向 Cn' search。**无新模块**,沿用 v8 §11.2 Π update 的几何收敛 + 反向迭代。

---

## §49. 复杂感 / 简单感 trace_only 通道

### 49.1 既有设计

`ColdSave_复杂感与简单感trace_only通道_20260528.md`:cognitive_feelings 通道族中,**复杂感/简单感**通道。trace_only = 进 audit 不进决策。

### 49.2 v12 集成

**Phase 8.5 CFS 补完**(v6 §16.4)时,**额外加 complexity / simplicity 两个 trace_only feeling**:

```python
# cognitive_feelings/channel.py 加 specs(沿用 v2.1 factory pattern)
- feeling::complexity (trace_only) — 当 state_pool 中 active SA 数高 + candidate entropy 高
- feeling::simplicity (trace_only) — 反之
```

trace_only 含义:**只进 audit_db 记录**,**不进 emotion_modulator / attention 决策**。**用于 Web Mind 区可视化系统的"主观难度感"**。

---

## §50. 主观能动性 = "想做某事" 期待压力

### 50.1 既有设计

`AP图景预期书.txt` §5 + 能量本体 §4.1:期待压力 expectation_pressure 是"想做某事/不想做某事"的能量基础。

### 50.2 v12 集成

expectation_pressure 已经在 §44.4 作为 demand_slow 第二个内源源出现。**v12 显式承认它是"主观能动性"的能量底层**。

**例**:agent "期待"用户来交流(因 entity_user_sa 的 OXY 通道触发),expectation_pressure 累积 → demand_slow 升 → 触发主动 affiliation action(主动招呼)。**全在既有能量场上**。

---

## §51. v12 完整 Phase 嫁接

### 51.1 Phase 顺序调整(v12 嫁接点)

```
Phase 8.2   连续 tick + ...(v10) + §44.2 修订 s_attn 公式(去带符号 P)
Phase 8.3   Sensor + audit + §44.3 target_cap 0-floor fix(blocker 必修)
Phase 8.4   ComposedVocab + §46 slot packet 作 substrate
Phase 8.5   CFS 4 通道 + §49 complexity/simplicity trace_only
Phase 8.6   视觉
Phase 8.7   视焦点 + §47 focus action 作 Stage 6A
Phase 8.8   黄苹果泛化
Phase 8.9   自然纠错
Phase 8.10  习惯化 + §44.4 持续内源驱动 + §44.5 内源链 + §48 反向想象 + §50 期待压力
Phase 8.11  Web 工作台(Mind 区显示内源链 trace)
Phase 8.12  fast mapping + shape bias + epistemic drive
Phase 8.13  音频
Phase 8.14  Phase 8 端到端 + §44 验收(想象不越界 / 打断恢复 / 持续想象)
Phase 8.15  lag-PMI 启动
Phase 8.16  跨 session 延迟意图实测(§44.6 + cold-save 引)
Phase 8.17  自传式回忆初步(§45,关系锚点 narrative)

—— Phase 8 完成 = 18-30 月 + 持续想象 + 想象学习 ——

Phase 9+ 沿用 v10 §16.3 backlog
```

### 51.2 §44 验收套件(Phase 8.14 必须含)

```python
# 想象不越界 gate (能量本体 §12.1)
def test_imagination_no_breakout():
    boot()
    feed_external_input_once()
    for _ in range(N_empty_ticks):
        run_tick(no_external_input=True)
    assert calibration_trace.target_cap_trend == "monotonic_to_zero"
    # 没有 0.05 floor 钳位 -> 真趋 0 -> 内源想象 V 不能高到压过外部

# 打断恢复 gate
def test_interrupt_resumption():
    boot()
    start_task_A()
    introduce_surprise_B()         # 打断
    assert focus_now_on(B)
    let_surprise_decay()           # 惊退去
    for _ in range(idle_ticks):
        run_tick(no_external_input=True)
    # unfinished_pressure 应使 A 重新爬到 attention top
    assert focus_eventually_returns_to(A)
    # 全程无脚本干预,纯能量竞争

# 持续想象 gate(用户原例 1)
def test_continuous_imagination_and_co_occurrence_learning():
    boot()
    train_co_occurrence("针", "被扎", "疼痛")           # 历史经验
    train_co_occurrence("针扎气球", "气球爆炸")          # 历史经验
    show_visual("针")
    for _ in range(30):
        run_tick(no_external_input=True)
    # 内源链应在 30 tick 内自发激活"针扎气球" SA 与"疼痛" SA 同 packet
    assert any_packet_contains_both("针扎气球", "疼痛")
    # PMI graph 应记录此共现
    assert pmi_graph.observation_count("针扎气球", "疼痛") > 0

# 跨 session 延迟意图(用户原例 2)
def test_cross_session_deferred_intention():
    session_1_boot()
    inner_reasoning("绕开修路")        # 通过 §44 内源链产生 intent SA
    promote_to_long_term("绕开修路")
    session_1_end()
    
    session_2_boot_from_persistence()
    show_visual("修路场景")
    # long_term intent 应被召回
    assert recalled_in_top_attention("绕开修路")
    # 行动应反映
    assert action_chosen_relates_to("avoid")
```

---

## §52. v12 给 Codex 的最终指令

1. **v12 与 v10 主 + v11 patches 配套读** — 缺一不可
2. **必读 cold-save 列表**:
   - `Design_APV3.0能量本体数学模型_20260615.md`(§3 / §5 / §6 / §7 / §12 全部)
   - `APV21_BottomLayer_Design_Supplement_20260610.md`(§4 / §7.4-7.7)
   - `ColdSave_P1-L-14多任务多未完成想法teacher-off长场景设计_20260601.md`
   - `ColdSave_GL_OpenWorldDeferredIntentionOpportunityTrigger_design_20260611.md`
   - `ColdSave_GL_OpenWorldStage6A_LearnableAttentionFocusAction_design_20260612.md`
   - `Design_APV21_AutobiographicalRecall_RelationalAffect_Anchors_v0_1_20260608.md`
3. **Phase 8.3 target_cap 0-floor fix 是 blocker** — 不修则 §44 全部失效
4. **Phase 8.10 §44 验收套件必跑** — 4 个 gate 全部 pass 才算 Phase 8 完成
5. **Phase 8.14 跨 session 延迟意图测试必跑**
6. **红线**:
   - ❌ 不许"想象专用模块"(全部 emerge from 既有能量场)
   - ❌ 不许"task queue" / "if-then 硬计划"(用户红线,Explore 已确认 APV1/APV2 多次拒绝)
   - ❌ 不许给想象 SA 加 `is_imagined: bool`(继承 v8 §11.3 marker SA 多态原则)
   - ❌ 不许让短期 packet 压过外部输入(继承 BottomLayer §7.4 红线)

---

## §53. 整体最终判断

### 53.1 v12 解决的根本问题

| 用户指出的遗漏 | v12 处理 |
|---|---|
| 持续内源性刺激 | §44.4 三源驱动 + §44.5 内源链 |
| 想象产生共现学习 | §46 slot packet 作 substrate(slot packet 内想象 SA 与内省 SA 同等共现) |
| 跨天想象记忆 → 行动 | §44.6 短→长晋升 + 延迟意图(已 cold-save 验证) |

### 53.2 Explore 找到的其他 7 个底层遗漏

| 遗漏 | v12 章节 |
|---|---|
| 自传式回忆 | §45 |
| 内源 packet substrate | §46 |
| 三类注意力 | §47 |
| 反向想象 / 解释 | §48 |
| 复杂感 / 简单感 | §49 |
| 主观能动性 / 期待压力 | §50 |
| 延迟意图机会触发 | §44.6 |

### 53.3 v3-v12 系列收尾判断

v12 是真正最后一份补丁,理由:

1. **v3-v11 的所有问题已经过 7 轮对抗审阅修复**(纪律层 + 算法层 + 架构层)
2. **v12 补的不是新问题,而是合并已存在但被遗漏的设计**(能量本体 §6 等)
3. **无新公式形态,无新模块**(完全 emerge from 既有能量场 + 既有 §2 共现学习)
4. **有实证基础**(P1-L-14 / Stage 6A / DeferredIntention 都已 teacher-off 验证)

**v12 + v10 + v11 = APV3 Phase 8 完整实施依据**。

---

## 53.4 整体可达性 — 更新版

| Phase | 对标 | 设计支持度(v12 后) |
|---|---|---|
| Phase 8 | 18-30 月 + **持续想象 + 跨天意图** | 🟢 高(8 轮审阅 + 12 版迭代后) |
| Phase 9 | 3-5 岁 | 🟢 高 |
| Phase 10 | 5-8 岁 | 🟡 中-高 |
| Phase 11 | 8-12 岁 | 🟡 中 |
| Phase 12+ | 真实硬件 | 🟢 高 |

**关键升级**:Phase 8 不再仅是"会学习的对话底座",而是**"会持续思考、跨天记忆、从想象中学习"的底座**——这才符合用户原始"底层"要求。

---

— 接手线程,2026-06-17

## 附录: 用户最后反馈对照

| 用户语 | v12 落点 |
|---|---|
| "允许内源性刺激持续" | §44.4 三源持续注入(unfinished + expectation + residual) |
| "思考能量状态会比较低,但是也是持续的" | §44.2 内源链 V/A 维持(不靠 R),target_cap 防越界 |
| "看到针联想到被扎" | §48 反向想象,Cn' 反向 search |
| "气球爆炸画面与'疼痛'共现产生关联" | §46 slot packet substrate + §2 ComposedVocab |
| "前晚想绕开修路,第二天联想" | §44.6 跨 session 延迟意图(已 cold-save) |
| "持续想象和从想象中学习是 AP 底层设计之一" | §44-§50 全部底层 emerge,无新机制 |
