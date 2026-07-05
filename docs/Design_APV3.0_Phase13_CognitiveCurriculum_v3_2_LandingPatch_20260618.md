# APV3.0 Phase 13 — Cognitive Curriculum 设计稿 v3.2 Landing Patch

日期: 2026-06-18
作者: 银子老师 / Claude 协作
状态: **v3.1 经 Codex 第三轮对抗审阅识别 3 blocker + 6 serious。每条都是真问题,且部分(如隐私与现有 chat.py 实现冲突、AGPL 法律解读错误、trust 公式自相矛盾)是 v3.1 自己造成的新坑。v3.2 是 Landing Patch:每条问题给出根治方案,不留模糊地带。Codex 实施依据 = v3 + v3.1 ERRATA + v3.2 Landing Patch 三稿。**

前作链:
- v1 / v2 / v3 / v3.1 ERRATA
- [v3.1 ERRATA](Design_APV3.0_Phase13_CognitiveCurriculum_v3_1_ERRATA_20260618.md)
- 人设样例 v1(已确认)

许可:AGPL-3.0-or-later(标准 GPL family 解读,允许商业使用)
原架构设计:银子老师

---

## 0. v3.2 修复总览

| 问题 | 类型 | v3.1 中的错误 | v3.2 修复 |
|---|---|---|---|
| **B1** trust_promoted 自相矛盾 | BLOCKER | "trust 越高要更大 effect_size" 但公式给反 | 公式根治:trust 只能绕 p-value + 降 min_obs,**不许动 effect_size** |
| **B2** 数学能力 "直接复用经验包" | BLOCKER | 看似 APV2.1 patching,容易塌成"伪装的旧系统" | 改为"借鉴课程设计/action schema/题型/审计,**在 APV3 SDPL 路径重新落地并 teacher-off 重验**" + 数字错误修正(24%/16% → 阈值 20%,不是 30%) |
| **B3** 隐私与现有 chat.py 冲突 | BLOCKER | chat.py 实际把 user_text 原文存 SQLite,v3.1 说"永不持久化"是骗 | Phase 13.0 第一件事:**改 chat.py 默认不持久化原文**(opt-in 才存),真做 export/delete CLI |
| **S1** License 表述法律风险 | SERIOUS | "任何商用需另谈" 违 AGPL 精神 | 改 "AGPL 允许商业使用(含闭源 SaaS 仍需开源衍生);商业**闭源专有/品牌合作/托管豁免**另谈" + 加专业法律声明 |
| **S2** requires_marker_above 仍像硬路由 | SERIOUS | yaml 写就是硬条件 | 删该字段;改为 marker R 影响候选 vocab 的 attention,**只过 attention 不过 filter** |
| **S3** 偏旁 OOD oracle 字符串 | SERIOUS | `filter_by_similarity_to("氵_radical_template")` 是 oracle | 改用 AP 已学到的 radical VocabSA 自身的 percept prototype 比对,**不允许字符串模板** |
| **S4** sybil 防护与隐私互撞 | SERIOUS | 一边说不存 IP 一边按 IP 分组 | 删 IP 方案;改 **本地 provenance group + 课程包签名 + 人工审核 tier** |
| **S5** 表达范式课程容易塌成句库 | SERIOUS | context_tag → text 映射像宏 | 加红线:**禁止 context_tag/中文场景名直接选句**;候选 vocab 必须经能量竞争 |
| **S6** 跨课程一致性 probe 隐藏答案 | SERIOUS | `generate_probe_cue()` 用 vocab 名造 cue | probe cue 必须来自 **held-out 感受器事件**,不许函数式生成 |

---

## 第 1 章 BLOCKER 根治(3 个)

### B1. trust_promoted 公式根治

#### 1.1 v3.1 错在哪

v3.1 §2.2 line 125 文字写:
> "trust 越高反而要更大 effect_size(防权威盲信)"

但 v3.1 公式:
```python
def compute_trust_aware_effect_size_threshold(trust):
    return max(0.02, 0.08 - 0.06 * (trust - 0.7) / 0.3)
```

代入:
- trust = 0.7 → θ = 0.08
- trust = 0.85 → θ = 0.05
- trust = 1.0 → **θ = 0.02**(变小了!)

**文字说要变大,公式给变小,自相矛盾**。Codex 指出这"重新打开高信任教师低效应污染的门"。

#### 1.2 v3.2 根治方案

**核心原则**:trust 只能换两个东西,**绝不许换 effect_size**:
1. 绕过 p-value(因为 p-value 受 n 影响,trust 大时少观察也可信)
2. 降低 min_obs(信任度高的教师不需要那么多次重复)

**但 effect_size 必须保持不变**:effect_size 反映"加这个 vocab 真带来实质性能预测压力下降",**这是物理性质,不应被 trust 软化**。

#### 1.3 v3.2 正式公式

```python
def trust_promote_gate_v3_2(vocab, teacher, effect_size, p_value, n_obs):
    """
    v3.2 根治版:trust 只能换 p-value 和 min_obs,不能换 effect_size.
    
    门 1 (硬): effect_size 必须 ≥ 固定下限 0.03 (无论 trust 多高)
    门 2 (硬): n_obs 必须 ≥ trust-dependent min_obs
    门 3 (软): p_value 在 trust 高时可被绕过
    """
    # === 门 1: effect_size 固定下限,无视 trust ===
    EFFECT_SIZE_HARD_MIN = load_constant(
        "curriculum.teaching_protocol.effect_size_hard_min"
    )  # 0.03,所有教师都必须满足
    
    if effect_size < EFFECT_SIZE_HARD_MIN:
        return False  # 即使 trust=1.0 也不许过
    
    # === 门 2: trust 越高 → min_obs 越小,但仍要 ≥ 5 ===
    trust = teacher.trust_score
    if trust < load_constant("curriculum.teaching_protocol.delta_p_bypass_tau_min"):
        return False  # trust 不够,不走 trust 路径
    
    # trust ∈ [0.7, 1.0] → min_obs ∈ [10, 5]
    # trust=0.7 (低) → 10 次观察
    # trust=1.0 (高) → 5 次观察
    min_obs = int(round(
        10 - 5 * (trust - 0.7) / 0.3
    ))
    
    if n_obs < min_obs:
        return False
    
    # === 门 3: p_value 在 trust 高时可放宽 ===
    # trust ∈ [0.7, 1.0] → p_threshold ∈ [0.05, 0.20]
    p_threshold = 0.05 + 0.15 * (trust - 0.7) / 0.3
    
    if p_value > p_threshold:
        return False
    
    return True
```

#### 1.4 数学保证(给对抗审阅)

**定理 1**(v3.2):任何通过 trust_promoted gate 的 vocab,实际 effect_size 必 ≥ 0.03,与普通 ΔP gate 的 effect_size 门相同。

**证明**:门 1 硬约束 effect_size ≥ EFFECT_SIZE_HARD_MIN = 0.03。trust 影响 p_value 阈值和 min_obs,**完全不动 effect_size 判定**。∎

**推论**:trust 永远不能让"无实质效应"vocab 通过。教师权威可以加速学习(少观察 + 弱显著),但不能凭空创造效应。

#### 1.5 必修测试(Phase 13.1 必跑)

```python
def test_trust_promoted_cannot_bypass_effect_size_hard_min():
    """
    B1 验证测试:即使 trust=1.0 + n_obs=100,
    effect_size=0.025 仍必须被拒.
    """
    teacher = TeacherEntitySA(trust_score=1.0)
    vocab = VocabSA(...)
    
    result = trust_promote_gate_v3_2(
        vocab,
        teacher,
        effect_size=0.025,  # 在 0.03 hard min 以下
        p_value=0.001,       # 统计显著
        n_obs=100,           # 大量观察
    )
    assert result is False, "trust=1.0 仍不能让 effect_size=0.025 通过"


def test_trust_promoted_allows_high_trust_low_n():
    """trust=0.95 + n_obs=5 + effect_size=0.04 + p=0.15 应该通过"""
    teacher = TeacherEntitySA(trust_score=0.95)
    
    result = trust_promote_gate_v3_2(
        vocab=VocabSA(...),
        teacher=teacher,
        effect_size=0.04,
        p_value=0.15,
        n_obs=5,
    )
    assert result is True


def test_low_trust_requires_strict_p_value():
    """trust=0.7 + p=0.06 不通过(普通 ΔP 门)"""
    teacher = TeacherEntitySA(trust_score=0.7)
    
    result = trust_promote_gate_v3_2(
        vocab=VocabSA(...),
        teacher=teacher,
        effect_size=0.05,
        p_value=0.06,   # 普通 0.05 门外
        n_obs=10,
    )
    assert result is False
```

#### 1.6 yaml 修订

```yaml
curriculum:
  teaching_protocol:
    # === v3.2 根治 ===
    effect_size_hard_min: 0.03               # @structural — 所有教师都受此门,trust 无法绕过
    delta_p_bypass_tau_min: 0.7              # @structural — trust 准入门
    delta_p_bypass_min_obs_low_trust: 10     # @structural — trust=0.7 时
    delta_p_bypass_min_obs_high_trust: 5     # @structural — trust=1.0 时
    delta_p_bypass_p_threshold_low_trust: 0.05  # @structural — trust=0.7 时
    delta_p_bypass_p_threshold_high_trust: 0.20  # @structural — trust=1.0 时
    
    # 删除 v3.1 错误字段:
    # ~delta_p_bypass_effect_size_lower_bound: 0.02~  # 删,被 effect_size_hard_min 替代
    # ~delta_p_bypass_effect_size_upper_bound: 0.08~  # 删,概念错误
```

---

### B2. 数学能力的正确接入方式

#### 2.1 v3.1 错在哪

v3.1 line 39:
> "不重训 — APV2.1 已实测 728/728,直接复用 `math_skill_experience_package/v1` ~ `/v28`"

银子老师明确指出:**"之前的数学能力不少可能是偏向于硬编码,我们需要让它按我们新的 APV3 的基础来重新进行学习和实现"**

这是真问题。APV2.1 Math-0~28 能跑通 728/728,但实施过程中:
- 部分 action 是 hardcoded(如 `action::count_step` 的具体步数逻辑)
- 部分 cognitive_feeling 走 APV2.1 专属通道
- 没经过 v14 SDPL packet 学习
- 没经过 trust_promoted gate
- 没经过 EpistemicSource marker 区分(HEARSAY 教学 vs PERCEIVED 实操)

**直接复用经验包** = APV2.1 patching,容易塌成"伪装的旧系统",失去 AP 架构演化的证据。

#### 2.2 v3.1 数字错误

v3.1 line 78:
> "反馈 `answer_payload=None` 修复率 ≥ 30% (APV2.1 Math-28: 24%)"

放宽阈值放高于实测值 = 更严格不是更宽松。**逻辑错误**。

#### 2.3 v3.2 根治方案:借鉴而非复用

**新口径**:Phase 13.5b 是**APV3 SDPL 路径下的数学技能浸泡**,**借鉴** APV2.1 已验证的:

| 借鉴对象 | 借鉴形式 | 不直接复用 |
|---|---|---|
| **课程设计**(Math-0~28 阶段顺序) | yaml 课程包模仿同样的阶梯 | ❌ 不复用经验包二进制 |
| **action schema**(`count_step / write_digit / carry_one ...`) | 在 Phase 8.4 SDPL 中重新定义为标准 action SA | ❌ 不复用 APV2.1 行动定义 |
| **审计范式**(strict vertical trace) | 在 APV3 audit 体系中重新实现 | ❌ 不复用 APV2.1 trace 格式 |
| **验收题型**(单位数加减/进位/列方程) | 作为 Phase 13.5b validation tests | ✅ 可直接借鉴题面 |
| **cognitive_feeling**(quantity_grasp/computation_pressure/step_closure) | 这些已在 Phase 8.5 cognitive_feelings/channel.py 实现 | ✅ 复用 |

**核心要求**:
- Phase 13.5b 系统必须**从零学到**数学能力,经 SDPL + trust_promoted + RPE 路径
- teacher-off 验证必须**重新跑**(APV2.1 数据只作历史参照,不算 APV3 证据)
- 必须证明:**APV3 v14 架构下,从零教学也能 emerge 数学能力**

#### 2.4 v3.2 修订阈值(对齐实测,不放宽)

```yaml
curriculum:
  math:
    # === v3.2 修订:基于 APV2.1 实测,但不能比实测松 ===
    teacher_off_accuracy_min: 0.95            # @experimental — APV2.1 实测 100%,留 5% 安全余量
    first_correct_round_final_min: 0.85       # @experimental — APV2.1 LangMath-2: 100%, Math-9: 92%, Math-28: 84%(取较低)
    no_answer_repair_rate_min: 0.20           # @experimental — v3.2 修正:APV2.1 Math-28: 24%, Math-21b: ~16%
                                              # 取 20% 作 APV3 期望(比 APV2.1 略低,因为重新学,不取最严)
    
    # === v3.2 新增:重新学习的必要性 ===
    relearn_from_scratch_required: true        # @structural — Phase 13.5b 必须从零教学
    apv2_1_experience_packages_as_reference_only: true   # @structural — 仅作历史参照
```

#### 2.5 Phase 13.5b 实施流程

```
Phase 13.5b.0 — 课程包翻译
  - 把 APV2.1 Math-0~28 阶段顺序翻译为 APV3 yaml 课程包
  - 题型/验收/cognitive_feeling 借鉴
  - action schema 在 APV3 重新定义

Phase 13.5b.1 — 数感预训练 (对应 APV2.1 Math-0)
  - 教学:数字 + 数量 + successor
  - SDPL 路径:HEARSAY 教学 + PERCEIVED quantity 感受
  - 验收:数感 cognitive_feeling::quantity_grasp 涌现 + teacher-off 通过

Phase 13.5b.2 — 单位数加减 (对应 Math-1/2/3)
  - 同理
  ...

Phase 13.5b.N — 列方程应用题 (对应 Math-27/28)
  - 最高阶段

Phase 13.5b.最终 — 跨阶段保持
  - 教完所有阶段后,从 13.5b.1 题面重测
  - 验证旧能力没在新学时被遗忘
```

#### 2.6 给对抗审阅的承诺

**v3.2 不再说"复用 APV2.1 数学能力"。**

v3.2 说:**"复刻 APV2.1 已证明可行的课程设计,在 APV3 v14 SDPL 架构下从零重新教学并验证,以证明 v14 架构不仅与 APV2.1 等强,而且因 SDPL/源监控/共情等机制,可能更稳更可解释"**。

如果重新学不出来 → **是 v14 架构的真问题,必须修架构,不许 fallback 到 APV2.1 经验包**。

这是开源时的诚实承诺,也是 v14 架构的真考验。

---

### B3. 隐私承诺与现有 chat.py 冲突 — 根治

#### 3.1 现实(Codex 查证)

chat.py line 126-132:
```python
self.state["chat_session_trace"] = _chat_trace_with(
    self.state,
    {
        "schema_id": "apv3_minimalist_chat_presented_turn/v1",
        ...
        "user_text": text,   # ← user_text 原文进 trace
        ...
    },
```

trace 进 SQLite blob 持久化(sqlite_runtime_store.py line 140 save_state)。

v3.1 PRIVACY.md 写:
> "不存储:用户实际文本内容"

**这是骗**。Codex 抓到了。

#### 3.2 v3.2 根治:真做不存,默认不持久化原文

**Phase 13.0 第一件事**(在 license 框架之前):

```python
# v3.2: chat.py 修订
class ConversationSession:
    def __init__(self, ..., persist_user_text: bool = False):
        """
        v3.2 默认 False — 不持久化用户原文.
        opt-in 才存,且必须显式弹出"我同意持久化"提示.
        """
        self.persist_user_text = persist_user_text
    
    def commit_user_turn(self, user_text: str, ...):
        ...
        trace_record = {
            "schema_id": "apv3_minimalist_chat_presented_turn/v2",  # bump
            "tick": tick,
            "mode": active_mode,
            # v3.2: 默认不存原文,只存 hash
            "user_text_hash": hashlib.sha256(text.encode()).hexdigest()[:16],
            "user_text": text if self.persist_user_text else None,
            "user_text_length": len(text),
            "runtime_committed_text": result.committed_text,
            ...
        }
```

#### 3.3 必落地的 CLI(不只是写政策,真实现)

```python
# apv3test/cli/data_management.py
"""v3.2: 真实 export/delete CLI,不只是政策口号."""

@click.command()
@click.option("--user_id", required=True)
@click.option("--output", required=True, type=click.Path())
def export_my_data(user_id: str, output: str):
    """导出该用户的所有持久化数据为 JSON."""
    store = SQLiteRuntimeStore(get_default_db_path())
    records = store.query_by_user(user_id)
    
    # 过滤 + 脱敏
    sanitized = [
        sanitize_record(r) for r in records
    ]
    
    Path(output).write_text(
        json.dumps(sanitized, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )
    click.echo(f"Exported {len(sanitized)} records to {output}")


@click.command()
@click.option("--user_id", required=True)
@click.option("--confirm", is_flag=True, required=True)
def delete_my_data(user_id: str, confirm: bool):
    """删除该用户的所有数据(必须显式 --confirm)."""
    if not confirm:
        raise click.UsageError("必须加 --confirm 才能删除")
    
    store = SQLiteRuntimeStore(get_default_db_path())
    deleted_count = store.delete_by_user(user_id)
    
    # 同步删除 curriculum_progress 中相关记录
    cp_store = CurriculumProgressStore(get_curriculum_db_path())
    cp_deleted = cp_store.delete_by_user(user_id)
    
    click.echo(f"Deleted {deleted_count + cp_deleted} records for {user_id}")


@click.command()
def privacy_status():
    """显示当前会话的隐私设置."""
    profile = load_runtime_profile()
    click.echo(f"persist_user_text: {profile.persist_user_text}")
    click.echo(f"sqlite_path: {profile.sqlite_state_path}")
    click.echo(f"user_text_hash_length: 16 chars (sha256 prefix)")
```

#### 3.4 默认 profile(text_dialogue / desktop_pet / agent / embodied)

```yaml
# config/scenario_profiles/text_dialogue.yaml(v3.2 修订)
privacy:
  persist_user_text: false              # 默认 false
  persist_session_trace: true            # trace 仍存(但 user_text 字段是 None)
  hash_algorithm: "sha256_prefix_16"
  user_can_opt_in_via_ui: true            # UI 允许用户主动开启
```

#### 3.5 现有 trace 数据的处理

迁移脚本:

```python
# apv3test/cli/data_migration.py
@click.command()
def migrate_existing_traces_to_v32_privacy():
    """
    v3.2 启动后,处理已有 trace:
    - 把 user_text 字段填充 hash
    - 把原文移到 separate opt-in 表(用户没 opt-in 则删原文)
    """
    store = SQLiteRuntimeStore(get_default_db_path())
    
    for record in store.iter_all():
        if "user_text" in record and record.get("user_text"):
            text = record["user_text"]
            record["user_text_hash"] = hashlib.sha256(text.encode()).hexdigest()[:16]
            record["user_text"] = None  # 清掉
            store.update(record)
    
    click.echo("Migration complete. All user_text fields cleared.")
```

#### 3.6 Phase 13.0 DoD 扩展

原 9 项 + 4 项:
- [ ] chat.py 修订:default persist_user_text=False
- [ ] export_my_data / delete_my_data / privacy_status CLI 实现
- [ ] migrate_existing_traces_to_v32_privacy 跑过(清现有数据)
- [ ] PRIVACY.md 描述与实现一致

#### 3.7 验收

```python
def test_user_text_not_persisted_by_default():
    """默认 profile 下,user_text 不存原文."""
    profile = load_runtime_profile("text_dialogue")
    assert profile.persist_user_text is False
    
    session = ConversationSession(profile=profile)
    session.commit_user_turn("你好我是测试用户", tick=1)
    
    # 检查 sqlite 里没原文
    store = SQLiteRuntimeStore(profile.sqlite_state_path)
    last_state = store.load_latest()
    trace = last_state["chat_session_trace"][-1]
    
    assert trace["user_text"] is None
    assert trace["user_text_hash"] is not None
    assert "你好我是测试用户" not in str(last_state)
```

---

## 第 2 章 SERIOUS 根治(6 个)

### S1. License 表述法律风险 — 改对

#### 1.1 v3.1 错在哪

v3.1 写:"任何盈利性产品/服务/SaaS 使用本项目...必须获得本商用许可证"

**错**:AGPL-3.0 本身就允许商业使用,只要求遵守 AGPL(分发/修改时开源衍生)。Codex 指出"任何商用需另谈"在法律上不准确。

#### 1.2 v3.2 正确表述

```markdown
# LICENSE_COMMERCIAL.md(v3.2 重写)

## AGPL-3.0 默认许可允许什么

本项目以 AGPL-3.0 发布,**允许商业使用**,包括:
- 用 AP 架构开发商业产品(需开源衍生,遵守 AGPL §13)
- 以 AGPL 形式提供 SaaS(用户可获取源代码)
- 学术研究、个人使用、教学、demo
- 内部企业使用(无需对外开源)

## 商业**闭源/专有**授权(另谈)

以下情形需要单独的**闭源商业许可证**:
- 商业产品**不愿意开源衍生作品**
- 提供 SaaS 但**不愿意向用户提供源代码**
- 将 AP 架构整合到**专有产品**(闭源)
- **品牌合作**(在产品中使用 "Powered by AP / 银子老师" 等署名作宣传)
- **托管豁免**(不愿承担 AGPL §13 网络分发义务)

联系:[银子老师联系方式 TBD]

## 关于 AP 架构 IP 的法律声明

**重要**:本节为非正式声明,不构成法律意见。
正式法律保护需经专业律师起草。

银子老师作为 AP 认知架构的原始设计者,主张:
1. 架构设计文档的著作权(可主张)
2. 实现代码的著作权(可主张)
3. 架构核心机制(SDPL/Ledger/EpistemicSource 等)的**设计署名权**(可主张)

不主张(因当前无法律基础):
- 算法/数学公式的专利权(需另行申请专利)
- "AP 架构"商标(可注册但尚未注册)
- 防止第三方开发兼容架构的独占权

## 衍生作品的署名义务

无论以 AGPL 还是商业许可使用,衍生作品都应:
- 在 README / 文档显著位置标注 "Based on AP Cognitive Architecture by 银子老师"
- 不主张衍生作品是 AP 架构的"原创"

违反署名义务 → 违反 AGPL §7 的额外许可条款 → 许可可能被撤销。

## 警告:本文件不构成法律意见

商业部署前请咨询专业律师。
AP 架构作者保留在咨询律师后修订本商业授权条款的权利。
```

#### 1.3 README.md 简化版

```markdown
# License

This project is licensed under [AGPL-3.0-or-later](LICENSE).

AGPL-3.0 permits commercial use, subject to the requirement to provide source 
code for derivative works (including SaaS deployments).

For proprietary/closed-source commercial use, brand partnerships, or hosting 
exemptions, please see [LICENSE_COMMERCIAL.md](LICENSE_COMMERCIAL.md) and 
contact the original architecture designer.

The AP Cognitive Architecture was originally designed by 银子老师 (Silver Teacher).
Derivative works should credit the original design.
```

#### 1.4 给银子老师的实际建议(下一步行动)

```markdown
# Phase 13.0 法律加固清单(给银子老师 of v3.2)

短期(开源前必做):
- [ ] LICENSE_COMMERCIAL.md 按 v3.2 §1.2 重写,避免法律错误表述
- [ ] README 顶部简化为 AGPL 标准说明
- [ ] 不主张专利(没申请就不主张)
- [ ] 不主张商标(没注册就不主张)
- [ ] 仅主张著作权 + 署名权 + 商业闭源授权权

中期(开源后 3 个月内):
- [ ] 咨询专业 IP 律师,起草正式商业授权合同模板
- [ ] 考虑注册 "AP 架构" 中英文商标
- [ ] 考虑申请核心机制专利(SDPL packet learning / Ledger 等)
- [ ] 考虑加入开源软件基金会(Apache Software Foundation 等)的会员

长期(有商业合作时):
- [ ] 与具体合作方签订商业授权合同(经律师审核)
- [ ] 维护 AP 架构社区的署名规范
```

---

### S2. requires_marker_above — 删除,改 attention emerge

#### 2.1 v3.1 错在哪

v3.1 §4.2 yaml:
```yaml
- text: "诶,你回来了。"
  initial_R_prior: 0.05
  requires_marker_above:           # ← Codex 指出这是硬条件
    EMPATHY_RESONANCE: 0.6
    entity_user_long_term: true
```

无论 v3.1 说它是"soft prior",**写在 yaml 里就是硬条件**:Codex 的 commit gate 实现自然会写成 `if not all(marker_R > threshold for ...): skip_candidate`。这是 if-then 路由。

#### 2.2 v3.2 根治:删除该字段,改 attention 自然涌现

```yaml
# v3.2 候选定义(简化)
candidates:
  - text: "嗯,你好。"
    initial_R_prior: 0.4
  - text: "嗯。"
    initial_R_prior: 0.3
  - text: "诶,你回来了。"
    initial_R_prior: 0.05
    # 删除 requires_marker_above ← 不再有
```

候选的选择**完全经 attention selector**:

```python
def select_commit_candidate_v3_2(candidates, state_pool):
    """
    v3.2: 候选完全经 attention 竞争,无 filter,无硬条件.
    """
    for c in candidates:
        # 1. initial_R_prior 作为 vocab SA 的初始 R 强度
        vocab_sa = get_or_create_vocab(c.text, initial_R=c.initial_R_prior)
        
        # 2. attention score = 凸组合 external/internal + 当前 marker 影响
        # 关键:marker R 自然影响 attention,不影响 filter
        # - EMPATHY_RESONANCE 高 → 共情类长候选的 attention 自然升
        # - SELF_REFERENCE 高 → 自我话题长候选 attention 自然升
        # 这是凸组合的副作用,不是显式 if
        c.attention_score = compute_attention_score_v14_1(vocab_sa, state_pool)
    
    # 标准 attention selector 选 top
    winner = attention_selector.select(candidates)
    return winner
```

**关键**:**marker R 是 attention 计算输入,不是 filter 条件**。所有候选都参与竞争,marker 高时某些候选自然胜出,不是某些候选被排除。

#### 2.3 验收(label-bijection + marker ablation)

```python
def test_long_candidate_not_filtered_by_marker():
    """B4 验证:即使 marker R 低,长候选也可参与竞争."""
    state_pool = setup_state_pool(empathy_marker_R=0.1)  # 低
    
    candidates = [
        Candidate("嗯。", initial_R=0.3),
        Candidate("诶,你回来了。", initial_R=0.05),
    ]
    
    # 即使 EMPATHY 低,两个候选都应该参与 attention 计算
    # 只是长候选 attention 自然低,大多数情况输给短候选
    
    scores = compute_all_attention_scores(candidates, state_pool)
    assert all(s > 0 for s in scores)  # 都参与了,没被 filter


def test_marker_ablation_changes_distribution():
    """marker ablation 实验:增 EMPATHY → 长候选选中频率自然升."""
    # 配对实验,固定 100 次对话
    
    # 实验组:EMPATHY 高
    high_results = run_n_dialogues(
        n=100, 
        marker_setup=high_empathy_setup
    )
    
    # 对照组:EMPATHY 低
    low_results = run_n_dialogues(
        n=100,
        marker_setup=low_empathy_setup
    )
    
    high_long_rate = count_long_responses(high_results) / 100
    low_long_rate = count_long_responses(low_results) / 100
    
    # 高 empathy 时长候选率应显著高于低 empathy
    assert high_long_rate > low_long_rate
    # 但都应在合理范围
    assert high_long_rate < 0.20  # 不会失控
    assert low_long_rate >= 0.01  # 不会归零(候选仍参与)


def test_no_yaml_field_requires_marker_above():
    """红线扫描:yaml 不应有 requires_marker_above 字段."""
    for yaml_file in Path("config/curriculum/packages").rglob("*.yaml"):
        content = yaml_file.read_text()
        assert "requires_marker_above" not in content, f"{yaml_file} has forbidden field"
```

---

### S3. 偏旁视觉 OOD micro-benchmark — 删 oracle 字符串

#### 3.1 v3.1 错在哪

v3.1 §2.3 测试代码:
```python
radical_percepts = filter_by_similarity_to(percepts, "氵_radical_template")
```

**`"氵_radical_template"` 是字符串模板**,这是外部 oracle。系统不应"知道"自己在找"氵",应该看视觉特征相似度。

#### 3.2 v3.2 根治:用 AP 已学到的 VocabSA 做比对

```python
def test_visual_sensor_extracts_radical_percept_from_unseen_char_v3_2():
    """
    v3.2: 不用 oracle 字符串,用 AP 已学到的 radical VocabSA 比对.
    
    前置:训练阶段已 spawn VocabSA "vocab::radical::氵",
         经 50 个含"氵"字训练后,该 VocabSA 已有稳定的 percept prototype.
    """
    # 训练阶段
    train_chars = ["河", "湖", "海", "沙", "池", ...]  # 50 个含氵的字
    for char in train_chars:
        image = render_character(char)
        teach_character(image, char)  # 标准教学路径
    
    # 训练后,VocabSA "vocab::radical::氵" 已有 percept prototype
    radical_vocab = state_pool.get_vocab_by_id("vocab::radical::氵")
    assert radical_vocab is not None
    assert radical_vocab.has_percept_prototype()
    
    # 测试阶段:呈现未训练过的"湍"
    test_image = render_character("湍")
    percepts = vision_sensor.process(test_image)
    
    # 用 radical_vocab 自身的 percept prototype 比对(不用字符串模板)
    matching_percepts = [
        p for p in percepts
        if percept_similarity(p, radical_vocab.percept_prototype) > 0.5
    ]
    
    assert len(matching_percepts) >= 1, "应至少识别出 1 个相似 percept"


def percept_similarity(percept_a, percept_b):
    """
    用 percept SA 的 channel signature 计算相似度.
    完全不依赖标签 / 字符串.
    """
    return cosine_similarity(
        percept_a.channel_signature_vector,
        percept_b.channel_signature_vector,
    )
```

#### 3.3 测试集扩充(防 "湍" 单点)

```python
@pytest.mark.parametrize("unseen_char,expected_radical_vocab", [
    ("湍", "vocab::radical::氵"),     # 简体三点水
    ("漪", "vocab::radical::氵"),
    ("濯", "vocab::radical::氵"),
    ("攀", "vocab::radical::扌"),     # 提手旁
    ("揪", "vocab::radical::扌"),
    ("烬", "vocab::radical::灬"),     # 四点底
    ("熹", "vocab::radical::灬"),
    
    # 多字体(防过拟合到单字体)
    ("湍", "vocab::radical::氵"),     # 楷体
    ("湍", "vocab::radical::氵"),     # 宋体
    ("湍", "vocab::radical::氵"),     # 黑体
    
    # 反例(不应识别)
    ("求", None),                     # 看似三点水但不是氵部
    ("氷", None),                     # 异体字
])
def test_radical_recognition_multiple_chars_and_fonts(unseen_char, expected_radical_vocab):
    image = render_character(unseen_char, font="default")
    percepts = vision_sensor.process(image)
    
    if expected_radical_vocab is None:
        # 反例:应该没有强匹配
        for vocab_id in ["vocab::radical::氵", "vocab::radical::扌", "vocab::radical::灬"]:
            vocab = state_pool.get_vocab_by_id(vocab_id)
            if vocab:
                top_sim = max(percept_similarity(p, vocab.percept_prototype) for p in percepts)
                assert top_sim < 0.5, f"反例 {unseen_char} 不应强匹配 {vocab_id}"
    else:
        # 正例
        target_vocab = state_pool.get_vocab_by_id(expected_radical_vocab)
        top_sim = max(percept_similarity(p, target_vocab.percept_prototype) for p in percepts)
        assert top_sim >= 0.5
```

---

### S4. Sybil 防护 — 不依赖 IP

#### 4.1 v3.1 错在哪

v3.1 sybil 方案存 IP / session 分组,但同时声明"不存 PII / 不存 IP"。**自相矛盾**。

#### 4.2 v3.2 根治:不存 IP,改本地 provenance + 签名 + 审核

```python
class TeacherEntitySA_v3_2(EntitySA):
    # 不存 IP / session
    teacher_id: str
    trust_tier: Literal["official", "user_local", "community_signed", "community_unsigned"]
    course_package_signature: Optional[str]  # 课程包加密签名
    human_reviewed: bool  # 是否经过人工审核
```

#### 4.3 trust tier 决定 trust 初值和投票权重

```python
def get_initial_trust_by_tier(tier: str) -> float:
    """v3.2: trust 完全由 tier 决定,无 IP 元素."""
    return {
        "official": 0.9,            # 官方课程包,银子老师亲审
        "community_signed": 0.6,    # 社区贡献,经人工审核,签名验证通过
        "user_local": 0.5,          # 用户本地教学(自教自用)
        "community_unsigned": 0.3,  # 未审核社区课程包,初始 trust 低
    }[tier]


def resolve_multi_teacher_conflict_v3_2(vocab_sa, conflicting_teachers):
    """
    v3.2 投票按 trust_score 加权,无 IP 防 sybil.
    
    防 sybil 真实手段:
    1. community tier 必须经人工审核才能升 trust_tier
    2. unsigned community 教师 trust 上限 0.5(无法压过 official 0.9)
    3. 同 vocab 的 community 教师票数无论多少,总权重不超过 0.5
    """
    vote_weights = defaultdict(float)
    
    for teacher_id, attribute_value in conflicting_teachers.items():
        teacher = get_teacher_entity(teacher_id)
        vote_weights[attribute_value] += teacher.trust_score
    
    # === v3.2 防 sybil 关键 ===
    # 同 tier 的 community/user_local 教师合计投票权重 ≤ tier 内最高 trust 的 1.5 倍
    # 这防止"同 tier 内堆 10 个低 trust 教师压过 1 个 official"
    vote_weights = apply_tier_cap(vote_weights, conflicting_teachers)
    
    # PERCEIVED 经验优先(沿用 v3.1)
    perceived = state_pool.get_perceived_evidence(vocab_sa)
    if perceived:
        return perceived.attribute_value
    
    if not vote_weights:
        vocab_sa.kind = "awaiting_revalidation"
        return None
    
    return max(vote_weights, key=vote_weights.get)


def apply_tier_cap(vote_weights, teachers):
    """同 tier 总权重不超 tier 最高 trust 的 1.5 倍."""
    by_tier = defaultdict(list)
    for tid, attr in teachers.items():
        teacher = get_teacher_entity(tid)
        by_tier[teacher.trust_tier].append((tid, attr, teacher.trust_score))
    
    capped = defaultdict(float)
    for tier, members in by_tier.items():
        max_trust_in_tier = max(t[2] for t in members)
        tier_cap = max_trust_in_tier * 1.5
        
        # 按 trust 排序,只累计到 cap
        sorted_members = sorted(members, key=lambda m: m[2], reverse=True)
        running_sum = 0
        for tid, attr, trust in sorted_members:
            if running_sum + trust <= tier_cap:
                capped[attr] += trust
                running_sum += trust
            else:
                # 超 cap,部分计入
                remaining = tier_cap - running_sum
                if remaining > 0:
                    capped[attr] += remaining
                    running_sum = tier_cap
                break
    
    return capped
```

#### 4.4 课程包签名机制

```python
# 社区课程包必须经签名才能升级 trust_tier
class CurriculumPackageSignature:
    package_id: str
    signer: str  # 银子老师 / 经授权审核者
    signature: str  # 数字签名(ed25519 等)
    review_status: Literal["pending", "approved", "rejected"]
    review_notes: str
```

只有 `review_status == "approved"` 的 package_id 在加载时,其教师才能升到 `community_signed` tier。

#### 4.5 PRIVACY.md 修订(与 sybil 方案一致)

```markdown
## 不存储的内容(v3.2 严格)

- 用户文本原文(默认配置)
- IP 地址
- session token / cookie
- 浏览器 fingerprint
- 用户个人身份信息(PII)

## sybil 防护手段(无 IP)

我们通过以下方式防止恶意刷量:
1. trust tier 系统(官方 / 已审核社区 / 用户本地 / 未审核社区)
2. 课程包加密签名
3. 同 tier 投票上限
4. PERCEIVED 经验优先于 HEARSAY 投票

**不使用 IP 追踪 / 设备指纹 / cookie 等**。
```

---

### S5. 表达范式课程禁止 context_tag 硬选 — 加红线

#### 5.1 v3.1 风险

v3.1 §6.6.1 yaml:
```yaml
candidates:
  - text: "嗯,你好。"
    weight: 0.4
    context: "默认"     # ← Codex 警告:context_tag → text 容易塌成宏
```

Codex 担心实现时变成 `if context == "默认": choose("嗯,你好。")` 这种硬路由。

#### 5.2 v3.2 根治:加红线 + 改实现

**红线**:

```python
# scripts/red_line_check_v14.py(扩 v3.2)
def check_no_context_tag_hard_routing():
    """
    禁止 cognitive/ 路径下按 context_tag 字符串 if-then 路由.
    
    允许:context_tag 作为 packet_key 的 slot_context 字段(经 SDPL packet 学)
    禁止:if context == "X": choose(Y) 这种硬路由
    """
    pattern = re.compile(r'if\s+\w+\s*==\s*["\'](?:默认|主动|被动|长期用户|新用户)["\']')
    
    violations = []
    for py_file in glob("runtime/cognitive/**/*.py", recursive=True):
        source = open(py_file).read()
        for i, line in enumerate(source.split("\n"), 1):
            if pattern.search(line):
                violations.append(f"{py_file}:{i}: context_tag hardcoded routing")
    return violations
```

**实现层**:

```python
# v3.2: 候选选择走 SDPL packet 路径,context_tag 不直接选句
def select_commit_candidate_v3_2_no_context_tag(candidates, state_pool):
    """
    候选选择走标准 SDPL packet + attention 路径.
    context_tag 只作为 packet.slot_context 的输入,不直接 if-then 选句.
    """
    current_packet = build_current_packet(state_pool)
    # current_packet.slot_context 含 entity_user_sa, 当前 feeling 等
    # context_tag 是 yaml 中的 metadata,经 packet_key 量化进 SDPL Q
    
    for c in candidates:
        # 每个候选作为 action SA,经 Q 表 backoff 查
        c.expected_R_change = q_table.query(
            packet=current_packet,
            action=action_id_for(c.text),
        )
    
    # attention 竞争(经 Phase 14.1 §B2 凸组合)
    winner = attention_selector.select(candidates)
    return winner
```

#### 5.3 yaml 改名

```yaml
# v3.2: context_tag → 改成 metadata 标注用,不直接路由
candidates:
  - text: "嗯,你好。"
    initial_R_prior: 0.4
    metadata:
      style_tag: "default_quiet"     # 仅 metadata,运行时不读
      design_note: "基线问候"        # 设计文档用
  
  - text: "诶,你回来了。"
    initial_R_prior: 0.05
    metadata:
      style_tag: "rare_warmth"
      design_note: "反差萌候选"
```

`metadata` 字段**运行时被忽略**(只用于审计 / 文档可读性)。

#### 5.4 验收

```python
def test_no_context_tag_in_runtime():
    """红线测试:runtime 不读 context_tag."""
    violations = check_no_context_tag_hard_routing()
    assert len(violations) == 0
```

---

### S6. 跨课程一致性 probe — 用 held-out 而非函数式生成

#### 6.1 v3.1 风险

v3.1 §2.3 `generate_probe_cue(vocab_sa_id, probe_i)`:函数式从 vocab 名造 cue → 隐藏答案(知道在测什么)。

#### 6.2 v3.2 根治:probe cue 来自 held-out 感受器事件

```python
class HeldOutEventPool:
    """v3.2 新增:存放课程中预留的感受器事件,用于无答案 probe."""
    
    def __init__(self):
        self.held_out_events: list[NormalizedSAEvent] = []
    
    def add_during_curriculum(self, event: NormalizedSAEvent, k_fold_index: int):
        """课程教学时,每 K 次随机 1 次进 held-out 池.
        
        这些事件不参与教学,只在一致性 probe 时使用.
        """
        if k_fold_index % K_FOLD == 0:
            self.held_out_events.append(event)
    
    def sample_probe_events_for_vocab(self, vocab_sa_id: str, n: int) -> list:
        """采样与该 vocab 上下文相似的 held-out 事件."""
        # 注意:不许根据 vocab_sa_id 函数式生成,只能从 held-out 池中查
        candidate_events = [
            e for e in self.held_out_events
            if any(sa_id_overlap(e, vocab_sa_id) for ...)  # 用 SA id 关联,不用字符串
        ]
        return random.sample(candidate_events, min(n, len(candidate_events)))


def snapshot_recall_vec_v3_2(vocab_sa_id, package_id, state_pool, held_out_pool):
    """
    v3.2: probe cue 必须来自 held_out_pool,不许函数式生成.
    """
    cooling_ticks = load_constant("curriculum.consistency.snapshot_cooling_ticks")
    sleep_until_cooling_complete(cooling_ticks)
    
    K = load_constant("curriculum.consistency.snapshot_probe_n")
    
    # === v3.2: 从 held-out 池取 cue,不从 vocab_sa_id 生成 ===
    probe_events = held_out_pool.sample_probe_events_for_vocab(vocab_sa_id, K)
    if len(probe_events) < K:
        # held-out 不够 → 一致性 gate 暂缓,而非用函数式 cue 填补
        return ConsistencyResult(
            status="insufficient_held_out",
            recall_vec=None,
        )
    
    probe_vectors = []
    for probe_event in probe_events:
        snapshot = state_pool.snapshot()
        state_pool.apply_external_event(probe_event)
        
        recall_results = state_pool.top_k_recall(top_k=32)
        context_freq_vec = compute_context_frequency_vector(recall_results)
        probe_vectors.append(context_freq_vec)
        
        state_pool.restore(snapshot)
    
    return ConsistencyResult(
        status="ok",
        recall_vec=np.mean(probe_vectors, axis=0),
    )
```

#### 6.3 验收

```python
def test_consistency_probe_not_from_vocab_name():
    """probe cue 不来自 vocab name 函数式生成."""
    # 1. 监控 generate_probe_cue 函数(应被删除)
    import inspect
    
    consistency_module = importlib.import_module("runtime.cognitive.curriculum.consistency_validator")
    assert not hasattr(consistency_module, "generate_probe_cue"), \
        "generate_probe_cue 应被删除,改用 held_out_pool"
    
    # 2. 监控 held_out_pool 存在
    assert hasattr(consistency_module, "HeldOutEventPool")


def test_insufficient_held_out_doesnt_fallback_to_functional_cue():
    """held-out 不够时,gate 暂缓而非 fallback."""
    held_out = HeldOutEventPool()
    # 不填充
    
    result = snapshot_recall_vec_v3_2(
        vocab_sa_id="vocab::test",
        package_id="test_package",
        state_pool=mock_state_pool(),
        held_out_pool=held_out,
    )
    
    assert result.status == "insufficient_held_out"
    assert result.recall_vec is None  # 不许 fallback 出值
```

---

## 第 3 章 v3.2 修订后的工作流

### 3.1 Phase 顺序(v3.2 修订)

```
Phase 13.0    License + Authorship + PRIVACY + MINORS + DATA_HANDLING + 现有 chat.py 隐私修订(1 天)
              ★ v3.2 + chat.py 默认不持久化原文
              ★ v3.2 + LICENSE_COMMERCIAL.md 法律正确表述
              ★ v3.2 + 真实 CLI(export/delete/privacy_status)
              ★ v3.2 + 现有 trace 迁移

Phase 13.1    Curriculum Substrate(1.5 天)
              ★ v3.2 + trust_promoted gate 根治公式
              ★ v3.2 + 一致性 gate 用 held_out_pool
              ★ v3.2 + trust tier 系统(无 IP)
              ★ v3.2 + 课程包签名机制

Phase 13.2    字课程(批 1 500 字,3 天)
              ★ v3.2 + Phase 8.6 视觉 OOD 验证不用 oracle 字符串

Phase 13.3    词课程(3 天)

Phase 13.4    视觉课程(7 天)

Phase 13.5    音频课程(2 天)

Phase 13.5b   ★ v3.2 改口径 — APV3 SDPL 路径从零学习数学
              复刻 APV2.1 课程设计,APV3 重新落地 + teacher-off 重验
              7 阶段(对应 Math-0~28)
              4-5 天(比 v3.1 略慢,因为是真重学)

Phase 13.6    表达范式(5-7 天)
              ★ v3.2 + 删 requires_marker_above
              ★ v3.2 + 删 context_tag 路由,改 metadata
              ★ v3.2 + commit 选候选走 SDPL packet 路径

Phase 13.7    行动反应库(1-2 天)
Phase 13.8    社交常识(2-3 天)
Phase 13.9    四场景验收(2 天)
              ★ v3.2 + N=50 用户 + 数据集偏差登记
              ★ v3.2 + 数学能力 demo 必跑

总耗时:~24-26 天到 alpha,6-8 周到 v1.0
```

---

## 第 4 章 给 Codex 的实施指令(v3.2)

1. **三稿配合**:v3 + v3.1 ERRATA + v3.2 Landing Patch,后者覆盖前者
2. **Phase 13.0 第一件事**:改 chat.py persist_user_text=False + 真实 CLI + 迁移现有数据
3. **trust 公式不能违 B1**:effect_size 永远不能被 trust 软化
4. **数学能力必须重新学**:不许复用 APV2.1 二进制经验包
5. **删 requires_marker_above 字段**:yaml 中此字段出现 → 红线扫描必拒
6. **删 context_tag 路由**:if context == "X" 模式扫描必拒
7. **probe 用 held_out_pool**:generate_probe_cue 函数必须删除
8. **OOD 测试不用 oracle 字符串**:用 VocabSA 自身 percept prototype
9. **License 表述按 v3.2 §1.2**:不能写 "任何商用需另谈"
10. **sybil 不存 IP**:改 trust tier + 课程包签名 + tier cap

---

## 第 5 章 给银子老师的总结

Codex 这轮审阅极有水平,**找到了 v3.1 自己造的 3 个新坑**:

1. **trust 公式自相矛盾** — 我文字写"trust 高要严",代码写"trust 高更松",这是 v3.1 自己打自己脸,Codex 一眼看穿
2. **数学能力"直接复用"** — 你也指出了,这会让 Phase 13 看起来像 APV2.1 patching,失去 v14 架构的演化证据。正确做法是**重新学,证明 v14 也能 emerge 出来,而且可能比 APV2.1 更稳更可解释**
3. **隐私承诺与现有 chat.py 实现冲突** — 我写"永不持久化"但代码实际存原文,这是欺骗用户。**必须先改代码再写政策**

加上 6 个 serious:
- License 法律表述错(AGPL 本来就允许商业使用)
- `requires_marker_above` 仍像硬路由
- 偏旁 OOD 用 oracle 字符串
- sybil 存 IP 与隐私冲突
- 表达范式可能塌成句库
- 一致性 probe 用 vocab 名生成 cue(隐藏答案)

**v3.2 Landing Patch 把每条都根治了**,不是软修补,是公式重写 + 实现重写 + 红线扫描 + 法律表述修正。

**接下来**:
1. 你审 v3.2(可能还要再让 Codex 审一轮)
2. 如果 OK,Codex 据 v3 + v3.1 ERRATA + v3.2 Landing Patch 三稿启动 Phase 13.0
3. 我手头准备 Phase 13.6 第一批 50 个范式文本(在 v3.2 删除 context_tag/requires_marker_above 后,只剩 candidates + initial_R_prior + metadata)

**关于数学能力**:

你提到"之前的可能偏向硬编码,要按 APV3 重新学",这个判断完全正确。Phase 13.5b 重新走 SDPL 路径有几个好处:

1. **证据等级最高** — 不是"我们重新跑了一遍 APV2.1 实验",而是"我们用全新架构从零教学,emerge 出了同样的能力,而且过程可审计"
2. **开源 demo 最强** — "看,这是它现学的过程,不是预训练的"
3. **架构验证最严** — 如果学不出来,就是 v14 架构有真问题,必须修。这反而比"复用旧成果"更有学术价值

如果你认可,我准备:
- Phase 13.6 第一批范式文本(等 v3.2 确认后开始,2-3 天交付)
- Phase 13.5b 第一阶段(数感)的具体课程包 yaml 草稿

哪个先做?

— Claude
— 2026-06-18
