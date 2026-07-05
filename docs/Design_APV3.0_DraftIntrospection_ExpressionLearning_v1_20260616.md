# APV3.0 草稿内省感受 + 表达范式共现学习 — 完整设计方案

日期: 2026-06-16
作者: 接手线程(对抗审阅前 v1)
状态: **数学模型 + 伪代码完整,对抗审阅前,待 Codex Phase 7.3 落地**
配套: 与 `Design_APV3.0能量本体数学模型_20260615.md`(v3.0)、`Design_持久化中文对话底座_范式通道重构_v2_20260615.md`(v2.1)共同构成 APV3.0 的"输入-感受-表达"完整链路
范围: 仅 `APV3.0test/` 目录,旧 core/memory 不改

---

## 0. 问题陈述与设计目标

### 0.1 用户哲学要求(必须满足)

> "我们人类更多的是先产生了一些内在的感受和表达倾向,然后后来根据这些来选取的表达范式来进行语言组织的。"
>
> "面对各种意外输入情况,它都能产生和人类类似的反应,以正确的范式应对。不要求它天然什么都会,但是可以在面对不会、面对只有一些不能决定的问题等情况时,可以以正确的范式进行应对和处理。"
>
> 不能决但又必须有回复时,系统不应该硬编码"说'我不确定'",而应该:
> 1. **内部先产生一种感受**(纯结构性,由草稿状态派生);
> 2. **过去观察过别人在类似感受下用某种句式应对**;
> 3. **下次类似感受出现,联想到该句式,自然组织语言输出**。

这是真正意义上的拟人——**感受先行,表达后选,且选取是后天学到的关联,不是预编程映射**。

### 0.2 当前缺口(Codex Phase 7.2 实现已暴露)

`undecidable_feeling_tokens=("feeling::undecidable",)`:外部硬塞的字符串标签。
`must_reply: bool`:外部硬塞的回复压力开关。
学习契约:`cue=feeling::undecidable → reply=expr::uncertain` 的直接配对(等于"看到 feeling 说这句话"的硬编码映射)。

三处都不是真正的"感受 → 共现 → 学习"链路。

### 0.3 设计目标(必须全部达成)

| # | 目标 | 验收依据 |
|---|---|---|
| G1 | feeling SA 标签由系统从草稿结构事实自动派生,不由外部约定 | grep 不到"feeling::undecidable"字面量出现在 runtime 或测试参数 |
| G2 | 同一机制能涌现任意数量的内省感受(不能决/纠结/心虚/流畅/...) | 加新 feeling 只需加结构特征定义,不改 runtime 代码 |
| G3 | "感受 → 表达范式"的关联完全由 OnlineEmbeddingStore 的共现学习得出 | 教学时 cue ≠ feeling token、reply ≠ expression token,二者只是**同一 tick 共现** |
| G4 | 回复压力(must_reply)从状态池能量涌现,非外部 bool | 测试入口不直接传 must_reply=True,而是塞入对话压力 SA |
| G5 | 没学过任何疑惑表达时,感受 SA 仍进池但无表达召回 | 负例测试:有感受、无关联,系统沉默 |
| G6 | 红线干净:无 if feeling、无 case_name 分支、无 modality 特例 | 红线扫描全程干净 |

---

## 1. 完整数学模型

### 1.1 草稿结构特征空间

定义:在任一 tick t,草稿状态 $D(t)$ 由有序 token 序列组成,每个 token 自带元数据 $(role, occupancy, filler\_margin, support, slot\_position, paradigm\_conf, ...)$。

**草稿结构特征向量** $\phi(D) \in \mathbb{R}^k$ 由若干**纯函数**抽取:

$$
\phi(D) = (\phi_1, \phi_2, ..., \phi_k)
$$

每个 $\phi_i$ 必须:
1. 是 $D$ 上的纯函数(同 D 同 $\phi_i$)
2. 不依赖具体 token 内容(否则违反 G1/G2)
3. 取值在 [0, 1] 或 {0, 1}(便于阈值化)
4. 可由 tuner 调节但本身不可学习(它是事实抽取)

**初始最小特征集 $\Phi^{(0)}$**(可扩展):

| 编号 | 特征名 | 计算公式 | 拟人意义 |
|---|---|---|---|
| $\phi_1$ | `has_shared_after_unresolved` | $\mathbb{1}[\exists i: \text{role}_i \in \{anchor, shared\} \land \exists j < i: \text{role}_j = slot \land \text{filler}_j = \emptyset]$ | "前面槽没填,后面共享词蹦出来"=不能决 |
| $\phi_2$ | `mean_slot_occupancy` | $\frac{1}{N_{slot}} \sum_{i: role_i=slot} \text{occupancy}_i$ | 槽位平均经验充实度 |
| $\phi_3$ | `min_filler_margin` | $\min_{i: role_i=slot} (\text{top}_i - \text{runner\_up}_i)$ | 最弱槽位的纠结度(margin 越小越纠结) |
| $\phi_4$ | `paradigm_competition` | $1 - \text{conf}_{\text{top}} + \text{conf}_{\text{2nd}}$(归一化到 [0,1]) | 多个 ParadigmSA 平分秋色 |
| $\phi_5$ | `commit_readiness` | 草稿 self-evaluation 分数(已有,来自 v2.1 §3.6) | 流畅度 |
| $\phi_6$ | `recent_punishment_resemblance` | learned_similarity(草稿向量, 近期被惩罚的 commit 向量) | 心虚("这句话上次说错了") |
| $\phi_7$ | `unresolved_slot_count` | $|\{i: role_i = slot, \text{filler}_i = \emptyset\}|$ 归一化 | 总未决度 |

注意:$\phi_1$ 已经在 Codex 当前实现里有了(`undecidable_fragment`)。$\phi_5$ 在 v2.1 也有了。$\phi_2, \phi_3, \phi_7$ 是新加,但只需读草稿元数据,工程量极小。$\phi_4, \phi_6$ 需要少量召回/相似度调用,但接口都已存在。

### 1.2 涌现 feeling SA 的机制(关键)

**问题**:从 $\phi(D)$ 怎么生成 feeling SA?如果用 `if φ1 > 0.5: emit("feeling::undecidable")` 就是硬编码。

**解法**:**让 feeling SA 的标签**由特征向量本身的离散化结果直接命名,不由人类语义命名。

#### 1.2.1 特征模式哈希命名(Pattern-Hashed Naming)

把每个特征 $\phi_i$ 量化到少量 bin(2-4 个,如 low/mid/high),则整个特征向量量化成一个**模式码** $\text{pattern}(D) \in \mathcal{P}$,$|\mathcal{P}| \leq 4^k$(实际远小于,稀疏)。

feeling SA 标签:

$$
\text{label}(D) = \text{"feeling::draft::pattern\_"} \oplus h(\text{pattern}(D))
$$

其中 $h$ 是稳定哈希(同 pattern 同 label)。**系统不知道这个 label 在人类语义里叫什么**(可能叫 "undecidable"、"hesitant"、"awkward",都行),它只知道**"草稿处于这个特征模式"是个可被状态池记录的事实**。

#### 1.2.2 特征模式 SA 的能量

每个涌现的 feeling SA 写入状态池作为一等 PoolEntry,带:

- `sa_label = "feeling::draft::pattern_<hash>"`
- `sa_type = "draft_introspection_feeling"`
- `real_energy` $= \alpha \cdot \text{intensity}(\phi(D), \text{pattern})$,其中 $\text{intensity}$ 衡量特征向量在该 pattern 中心的接近度(越接近能量越高)
- `cognitive_pressure`:由模式的"违和度"派生——一个稳定常出现的模式压力低,一个突然出现的反常模式压力高(用 EMA 计算模式出现频率,反比例转 pressure)
- `attention_gain`:由 v3.0 能量本体的 $\beta_P \cdot P + \beta_R \cdot R + ...$ 计算

**关键**:模式哈希 + 能量计算**全部是纯函数**,不依赖 token 内容,不依赖模态。同样的 $\phi(D)$ 在文本/视觉/听觉 draft 上**都派生同名 feeling**,实现 G2 跨模态通用。

#### 1.2.3 反对意见预答(为什么 hash 命名不是硬编码)

可能的反对:"hash 命名只是把硬编码字符串换了形式,本质没区别。"

**答**:
- 硬编码字符串("feeling::undecidable")依赖人类对这个状态的命名共识——系统**无法学到**"我现在叫 undecidable",必须靠外部告诉它。
- hash 命名是**结构事实的稳定标识符**——系统不需要任何外部介入就能产生它,且两次相同的结构事实保证产生相同的 label。
- 外部教师/老师可以**学习到**"系统在 pattern_<hash_X> 状态下说某句话"这个事实,不必给它人类名字。
- 这是"语义自下而上涌现"vs"语义自上而下注入"的本质区别。

### 1.3 共现学习契约(核心)

#### 1.3.1 触发条件

任意 tick t,若状态池里**同时**存在:

- 至少一个 feeling SA: $f_t \in F_{draft}(t)$
- 至少一个外部表达 token 序列(来自感受器或教师 reply 流): $e_t = (e_t^1, e_t^2, ..., e_t^m)$

则进入"感受-表达共现学习"。

#### 1.3.2 学习律

对所有 $(f, e^j)$ 对,以**有界、按 feeling 能量加权**的方式调用既有 `OnlineEmbeddingStore.observe_positive_pair`:

$$
w(f, e^j) = \text{clip}\left( \frac{R_f}{R_f + \kappa} \cdot \gamma_{co}, \; 0, \; w_{max} \right)
$$

其中:
- $R_f$ = feeling SA 的 real_energy(越显著越值得学)
- $\kappa$ 是 tuner-owned 饱和常数(沿用 v3.0 §12.4 的半衰期形)
- $\gamma_{co}$ 是 tuner-owned 共现学习率
- $w_{max}$ 是 tuner-owned 上界

调用:`observe_positive_pair(f.label, e^j, weight=w(f, e^j))`

这一步**只用现有接口,无新机制**。

#### 1.3.3 为什么这是真正的"共现"而不是"配对"

| 配对学习(Codex 当前 Phase 7.2 等价) | 共现学习(本设计) |
|---|---|
| 测试方知道"undecidable feeling 应该对应不确定句式" | 测试方只往状态池塞外部表达流,不指定它配什么 feeling |
| 直接 cue=feeling、reply=expression | feeling 由草稿自发涌现,表达由外界自然存在 |
| 学到的是"if feeling then expression"映射 | 学到的是"feeling 向量和 expression 向量在嵌入空间靠近" |
| 一次教学一对 | 一次 tick 多 feeling × 多 expression,所有相关对都被学习 |

**关键**:在共现学习契约里,**老师不需要知道系统当前的 feeling label 是什么**——它只需要在系统处于困惑/纠结/心虚等状态时,**自然地用对应句式回应**;OnlineEmbeddingStore 自然把两者在向量空间拉近。

#### 1.3.4 多 feeling 同时活跃的处理

一个 tick 内可能同时活跃多个 feeling(如同时有"纠结"和"心虚")。每个 feeling 都独立按 $w(f_i, e^j)$ 学习,**不互相影响**(observe_positive_pair 本身是按对独立累加 co_counts 的)。

这保证一种表达可能同时和多种 feeling 关联("我不太确定" 可能既关联 undecidable 也关联 ambiguous_competition),日后召回时按当下 feeling 组合软选择。

### 1.4 召回链路(感受 → 表达)

#### 1.4.1 召回输入

当下 tick t,假设草稿涌现了 feeling 集合 $F_t = \{f_1, ..., f_n\}$,要从已学的表达范式池中召回候选。

#### 1.4.2 召回算法

对每个候选表达 ParadigmSA $p$(它是普通 ParadigmSA,只是恰好在过去学习中与 feeling 共现过):

$$
\text{score}(p \mid F_t) = \sum_{f \in F_t} R_f \cdot \text{learned\_similarity}(f.\text{label}, p.\text{cue\_tokens})
$$

其中 `learned_similarity` 是既有接口(memory/embedding/online_store.py:190),返回向量空间相似度。

这就是 v2.1 §3.6 的 paradigm recall 链路的纯应用——**没有任何新机制**。表达范式和普通范式走同一条召回管线。

#### 1.4.3 触发门控(must_reply 涌现)

不直接传 `must_reply=True`。改为:

定义 **reply_pressure SA**(`feeling::reply_pressure`),由以下信号涌现进池(都是状态池已有的或可派生的):

- `external_query_recency`: 最近收到外部查询的时间近因(EMA)
- `social_expectation`: 对话角色压力(老师在场、对话伙伴注视等)
- `task_unfinished_pressure`: 工作记忆未闭合压力(work_memory 已有)
- `silence_duration`: 自上次 commit 后的沉默时长

具体公式(全部 tuner-owned):

$$
R_{reply\_pressure} = \sigma\left( w_q \cdot \text{external\_query} + w_s \cdot \text{social} + w_u \cdot \text{unfinished} + w_d \cdot \text{silence} - w_c \cdot \text{recent\_commit} \right)
$$

**must_reply 判定**:`reply_pressure SA 的 attention_score > θ_reply`,θ_reply 是 tuner-owned。

这就实现了 G4:must_reply 从能量涌现,不是外部 bool。

#### 1.4.4 完整链路

```
草稿状态 D(t)
    ↓ φ(D) 特征抽取(纯函数)
特征向量
    ↓ pattern_hash 量化命名
feeling SA(进状态池)
    ↓ learned_similarity 召回(经 OnlineEmbeddingStore)
表达范式候选 ParadigmSA
    ↓ 普通范式召回 + 注意力竞争
胜出表达范式
    ↓ 填槽(由当前高能 SA 填,如 candidate fragments)
草稿候选
    ↓ commit gate(若 reply_pressure 高且草稿可 commit)
输出
```

这条链路里**没有一个新机制是凭空发明的**——全部接 v2.1/v3.0 已有的 SA、感受工厂、范式召回、能量驱动。

---

## 2. 伪代码

### 2.1 草稿内省特征抽取器

```python
# APV3.0test/apv3test/runtime/draft_introspection.py
from dataclasses import dataclass
from typing import Sequence

@dataclass(frozen=True)
class DraftStructuralFacts:
    """Pure-function facts computed from a draft sequence."""
    has_shared_after_unresolved: bool
    mean_slot_occupancy: float
    min_filler_margin: float
    paradigm_competition: float
    commit_readiness: float
    recent_punishment_resemblance: float
    unresolved_slot_count_norm: float

def extract_facts(drafts: Sequence[DraftCandidate],
                  active_paradigms: Sequence[Paradigm],
                  recent_punished_commits: Sequence[CommitTrace],
                  embed: OnlineEmbeddingStore) -> DraftStructuralFacts:
    # 纯函数,不依赖 token 内容
    n_slot = sum(1 for d in drafts if d.role == "slot")
    has_shared = any(
        d.role in {"fixed_anchor", "shared_fragment"}
        and any(prev.role == "slot" and not prev.filler for prev in drafts[:i])
        for i, d in enumerate(drafts)
    )
    mean_occ = sum(d.occupancy for d in drafts if d.role == "slot") / max(1, n_slot)
    margins = [d.top_score - d.runner_up_score for d in drafts if d.role == "slot"]
    min_margin = min(margins) if margins else 1.0
    # ... 其余特征
    return DraftStructuralFacts(...)
```

**注意**:整个抽取器**不读任何具体 token 内容**——它只读 `role`、`occupancy`、`top_score` 这些**结构事实**。这是 G2(跨模态通用)的根基。

### 2.2 模式哈希命名

```python
def pattern_hash(facts: DraftStructuralFacts, config: IntrospectionConfig) -> str:
    """Quantize facts into a stable pattern label."""
    bins = (
        _bin(facts.has_shared_after_unresolved, [0.5]),         # 二值
        _bin(facts.mean_slot_occupancy, config.occ_bins),        # 3 档
        _bin(facts.min_filler_margin, config.margin_bins),       # 3 档
        _bin(facts.paradigm_competition, config.comp_bins),      # 3 档
        _bin(facts.commit_readiness, config.ready_bins),         # 3 档
        _bin(facts.recent_punishment_resemblance, [0.3]),       # 二值
        _bin(facts.unresolved_slot_count_norm, [0.0, 0.5]),     # 3 档
    )
    digest = hashlib.blake2b("|".join(str(b) for b in bins).encode(), digest_size=6).hexdigest()
    return f"feeling::draft::pattern_{digest}"

def _bin(value: float, edges: list[float]) -> int:
    for i, edge in enumerate(edges):
        if value < edge:
            return i
    return len(edges)
```

**关键**:bin 边界是 config(tuner-owned),不是字面量。同一组 facts → 同一 label,确定性。

### 2.3 feeling SA 涌现

```python
def emit_draft_introspection_feelings(
    drafts: Sequence[DraftCandidate],
    state: dict,
    embed: OnlineEmbeddingStore,
    config: IntrospectionConfig,
) -> list[DraftIntrospectionFeelingSA]:
    if not drafts:
        return []
    facts = extract_facts(drafts, state.get("paradigms", []),
                          state.get("recent_punished_commits", []), embed)
    label = pattern_hash(facts, config)

    # 模式频率统计(用于 pressure)
    pattern_freq = state.setdefault("draft_pattern_freq", {})
    freq = pattern_freq.get(label, 0.0)
    pattern_freq[label] = freq * config.pattern_freq_decay + 1.0

    # 能量计算
    intensity = _intensity_from_facts(facts, label, config)
    novelty = 1.0 / (1.0 + freq)  # 越罕见越压力
    pressure = config.pattern_pressure_weight * novelty * intensity

    feeling = DraftIntrospectionFeelingSA(
        sa_label=label,
        sa_type="draft_introspection_feeling",
        real_energy=intensity,
        cognitive_pressure=pressure,
        facts=facts,
        tick=state.get("tick", 0),
    )
    _write_to_state_field(state, feeling)
    return [feeling]
```

### 2.4 共现学习契约

```python
def observe_feeling_expression_cooccurrence(
    feelings: Sequence[DraftIntrospectionFeelingSA],
    external_expression_tokens: Sequence[str],
    embed: OnlineEmbeddingStore,
    config: IntrospectionConfig,
) -> None:
    """每个 feeling SA 与同 tick 的外部表达 token 做 positive_pair 学习。"""
    if not feelings or not external_expression_tokens:
        return
    for f in feelings:
        w_f = (f.real_energy / (f.real_energy + config.cooccurrence_saturation)) * config.cooccurrence_lr
        w_f = min(w_f, config.cooccurrence_max_weight)
        if w_f <= 0:
            continue
        for token in external_expression_tokens:
            embed.observe_positive_pair(f.sa_label, token, weight=w_f)
```

**关键**:`observe_positive_pair` 是既有接口,我**完全不引入新学习器**。

### 2.5 表达范式召回

```python
def recall_expression_paradigms_for_feelings(
    feelings: Sequence[DraftIntrospectionFeelingSA],
    paradigm_candidates: Sequence[ParadigmSA],
    embed: OnlineEmbeddingStore,
) -> list[tuple[ParadigmSA, float]]:
    """对每个 feeling 用 learned_similarity 召回候选表达范式,按能量加权汇总。"""
    scored = []
    for p in paradigm_candidates:
        total = 0.0
        for f in feelings:
            sim = embed.learned_similarity(
                [f.sa_label], list(p.cue_tokens)
            ).get("score", 0.0)
            total += f.real_energy * sim
        if total > 0:
            scored.append((p, total))
    scored.sort(key=lambda x: -x[1])
    return scored
```

**关键**:同样,`learned_similarity` 是既有接口。**表达范式和普通范式没有结构区别**——它只是"恰好和某些 feeling 在嵌入空间近邻"的范式。

### 2.6 涌现的回复压力(取代 must_reply: bool)

```python
def derive_reply_pressure(state: dict, config: IntrospectionConfig) -> ReplyPressureSA:
    external_query = state.get("recent_external_query_recency", 0.0)
    social = state.get("social_expectation_pressure", 0.0)
    unfinished = state.get("work_memory_unfinished_pressure", 0.0)
    silence = min(1.0, state.get("ticks_since_last_commit", 0) / config.silence_normalizer)
    recent_commit = state.get("recent_commit_recency", 0.0)
    raw = (
        config.w_query * external_query
        + config.w_social * social
        + config.w_unfin * unfinished
        + config.w_silence * silence
        - config.w_commit * recent_commit
    )
    pressure_level = 1.0 / (1.0 + math.exp(-raw))  # sigmoid
    return ReplyPressureSA(
        sa_label="feeling::reply_pressure",
        sa_type="reply_pressure",
        real_energy=pressure_level,
        cognitive_pressure=max(0.0, pressure_level - config.reply_pressure_neutral),
    )
```

**关键**:所有 `w_*` 都是 tuner-owned 系数,初值由 golden trace 锁定;`pressure_level` 是 0-1 连续量。must_reply 判定改成:

```python
must_reply = reply_pressure.real_energy > config.must_reply_threshold
```

这一改之后,`must_reply` 不再是外部入参,而是状态池能量的派生。测试塞入"外部查询"或"社交期待"SA 自然抬高 pressure,而不是直接说 `must_reply=True`。

### 2.7 tick 编排

```python
def tick_with_introspection(state: dict, input: TickInput) -> TickResult:
    # ... 既有 ingest / recall / draft 阶段
    drafts = paradigm_fill(...)

    # 新增:涌现内省感受
    feelings = emit_draft_introspection_feelings(drafts, state, embed, config)

    # 新增:观察外部表达 token(来自 input 或感受器流)
    external_expressions = extract_external_expression_tokens(input, state)
    observe_feeling_expression_cooccurrence(feelings, external_expressions, embed, config)

    # 新增:涌现回复压力
    reply_pressure = derive_reply_pressure(state, config)

    # 若 reply_pressure 高且草稿不能 commit,尝试用 feeling 召回表达范式
    if reply_pressure.real_energy > config.must_reply_threshold and has_undecidable(drafts):
        expression_candidates = recall_expression_paradigms_for_feelings(
            feelings, state.get("paradigms", []), embed)
        if expression_candidates:
            best_paradigm, _ = expression_candidates[0]
            drafts = paradigm_fill(best_paradigm, focus_tokens=high_grasp_fragments(drafts))

    # ... 既有 commit gate / 输出
```

---

## 3. 红线核对(对照 v3.1 §13)

| v3.1 红线 | 本设计是否合规 | 说明 |
|---|---|---|
| 不新增关键词 if-else | ✅ | 全程无 if feeling.label.startswith("undecidable") |
| 不新增答案表 | ✅ | 表达范式是普通 ParadigmSA,通过共现学到 |
| 不新增整句宏 | ✅ | 输出仍走逐 token 草稿 |
| 不用学生侧 LLM | ✅ | 完全无 LLM 调用 |
| 不让自生成草稿增正向 support | ✅ | feeling SA 是内省事实,不抬 support;表达范式 support 仍需外部 commit/feedback |
| 阈值是 config/tuner 字段 | ✅ | 所有 bin 边界、权重、阈值均 tuner-owned |
| 每输出 token 可回溯证据链 | ✅ | trace 含 facts → pattern → feeling → recalled expression → filled draft → commit |
| 不出现 if vision/if text | ✅ | 整个机制只读 role/occupancy 等结构事实 |
| 索引不直接决定行动 | ✅ | feeling 是 cue,召回结果仍要过竞争和 commit gate |
| 教师协议无独有字段 | ✅ | 教学时只塞外部表达 token,不带 feeling 标签 |

---

## 4. 验收门(端到端测试设计)

### 4.1 测试 1:无教学时 feeling 仍涌现,但无表达

```python
def test_introspection_feeling_emerges_without_teaching():
    state = bootstrap_empty_state()
    draft_with_undecidable = make_draft_with_shared_after_unresolved()
    state = tick_with_introspection(state, TickInput(draft=draft_with_undecidable))
    feelings = [sa for sa in state["state_field_items"] if sa["sa_type"] == "draft_introspection_feeling"]
    assert len(feelings) >= 1
    assert feelings[0]["sa_label"].startswith("feeling::draft::pattern_")
    # 没教过任何表达范式,所以没有 expression recall
    assert state.get("recalled_expression_paradigms", []) == []
```

### 4.2 测试 2:共现教学(关键)

```python
def test_cooccurrence_learning_feeling_to_expression():
    # 训练阶段:让系统产生 undecidable 草稿,同时塞外部"我不确定"句式
    state = bootstrap_empty_state()
    for _ in range(50):
        state = tick_with_introspection(state, TickInput(
            draft=make_draft_with_shared_after_unresolved(),
            external_expression_tokens=("expr::uncertain", "candidate_1", "candidate_2"),
            # 注意:测试方完全不知道 feeling 叫什么 label
        ))
    # 学完后,验证 OnlineEmbeddingStore 里有 feeling.label → expression token 的关联
    embed = state["online_embedding_store"]
    feeling_labels = [sa["sa_label"] for sa in state["state_field_items"]
                      if sa["sa_type"] == "draft_introspection_feeling"]
    assert any(
        embed.learned_similarity([fl], ["expr::uncertain"]).get("score", 0) > 0.3
        for fl in feeling_labels
    )
```

### 4.3 测试 3:学过后 must_reply 时自然召回表达

```python
def test_must_reply_recalls_learned_expression():
    state = train_for_uncertainty_expression(state)  # 用测试2的训练流程
    # 推 reply_pressure 升高(塞入外部查询 SA)
    state["recent_external_query_recency"] = 0.9
    # 触发不能决草稿
    state = tick_with_introspection(state, TickInput(
        draft=make_draft_with_shared_after_unresolved()
    ))
    # 应该看到表达范式被召回并填入草稿
    drafts = state.get("current_drafts", [])
    assert any("expr::uncertain" in str(d.label) for d in drafts) or \
           state.get("recalled_expression_paradigms", [])
```

### 4.4 测试 4:负例(关键防硬编码)

```python
def test_no_expression_when_not_learned():
    state = bootstrap_empty_state()
    state["recent_external_query_recency"] = 0.9  # 高 reply_pressure
    state = tick_with_introspection(state, TickInput(
        draft=make_draft_with_shared_after_unresolved()
    ))
    # 没教过任何表达范式,即使 must_reply 也不该凭空生成
    assert state.get("recalled_expression_paradigms", []) == []
    assert not state.get("commit_text", "")
```

### 4.5 测试 5:跨模态通用(关键防模态特例)

```python
def test_introspection_works_on_visual_draft():
    state = bootstrap_empty_state()
    visual_draft = make_visual_draft_with_shared_after_unresolved()
    state = tick_with_introspection(state, TickInput(draft=visual_draft))
    feelings = [sa for sa in state["state_field_items"] if sa["sa_type"] == "draft_introspection_feeling"]
    # 视觉草稿应该派生出和文本草稿同名的 pattern label(同一结构事实)
    assert len(feelings) >= 1
    text_feeling = run_text_version_and_get_feeling_label()
    assert feelings[0]["sa_label"] == text_feeling  # 跨模态同 pattern
```

### 4.6 测试 6:红线扫描

```bash
# 任何引入新硬编码会立刻被这条扫描抓出
grep -rn 'feeling::undecidable\|feeling::ambiguous\|feeling::hesitant' APV3.0test/apv3test/
# 应该一条都没有(都是 hash 命名)
grep -rn 'if.*feeling.*label' APV3.0test/apv3test/
# runtime 不应该有 if 读 feeling 内容做分支
```

---

## 5. 工程落地步骤(给 Codex)

1. **新增 `APV3.0test/apv3test/runtime/draft_introspection.py`**(~150 行):特征抽取 + 模式哈希 + feeling SA 涌现。
2. **新增 `APV3.0test/apv3test/runtime/cooccurrence_learning.py`**(~50 行):共现学习契约。
3. **新增 `APV3.0test/apv3test/runtime/reply_pressure.py`**(~50 行):涌现的回复压力。
4. **修改 `incremental_tick_runtime.py`**:
   - 删除 `undecidable_feeling_tokens` 和 `must_reply: bool` 参数。
   - 增加 `external_expression_tokens` 参数(可选,接外部表达流)。
   - 在 tick 编排里嵌入 §2.7 的流程。
5. **新增 `APV3.0test/apv3test/config/introspection_config.py`**:所有 bin 边界、权重、阈值。
6. **新增测试 `test_phase7_3_*`**:§4 的 6 个验收门。
7. **golden trace lock**:同输入 → 同 feeling label、同 pressure(确定性 check)。

---

## 6. 未决问题(诚实)

1. **bin 边界初值如何设?** 初版用 `[0.33, 0.67]` 三档,由 tuner 后续优化。可能存在"边界附近抖动"问题,需要 hysteresis。
2. **特征模式过多怎么办?** 7 个特征 × 平均 3 档 ≈ 2187 个可能 pattern,实际激活的会远少。但若长期积累,需要懒淘汰(用模式频率衰减 → 低频模式 GC)。
3. **共现学习什么时候停?** 当 OnlineEmbeddingStore 的相应关联已经稳定(变化率低于阈值)时,可以降低学习率。这是 v3.1 §13.2 "自然衰减"原则的延伸。
4. **多 feeling 联合召回时怎么避免互相干扰?** 当前用线性加权,可能某 feeling 主导。需测试是否需要 softmax 或注意力分配机制。

这些都是落地时需要 tuner 标定 / 后续观察才能定的,不影响数学模型本身的正确性。

---

## 7. 哲学总判

本设计实现了用户的核心要求:

> **"我们人类更多的是先产生了一些内在的感受和表达倾向,然后后来根据这些来选取的表达范式来进行语言组织的。"**

- **内在感受**:由草稿结构事实自动派生的 feeling SA,标签由 pattern hash 命名,系统不"知道"它叫什么人类语义。
- **表达倾向**:reply_pressure 由社交/任务压力涌现,不是外部 bool。
- **选取表达范式**:通过 OnlineEmbeddingStore 学到的 feeling-expression 关联召回,完全由共现统计驱动。
- **后天学到**:无任何预编程映射,所有"什么 feeling 配什么表达"都是经验积累。
- **通用扩展**:加新感受只需加新结构特征,机制不变;同一机制适用于不能决/纠结/心虚/流畅/...任意状态。

最关键的是:**没有任何代码读 feeling 的语义内容做分支**——所有判断都是结构事实 + 嵌入相似度 + 能量竞争。这是 APV3.0 哲学的真正胜利。
