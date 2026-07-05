# APV3.0 草稿内省感受 + 表达范式共现学习 — 完整设计方案 v2(对抗审阅后)

日期: 2026-06-16
作者: 接手线程
状态: **数学模型 + 伪代码完整,经 3 路对抗审阅(26 条核验,0 misread),所有 blocker/serious 已整合。准备交 Codex Phase 7.3 落地。**
配套: 与 `Design_APV3.0能量本体数学模型_20260615.md`(v3.0)、`Design_持久化中文对话底座_范式通道重构_v2_20260615.md`(v2.1)共同构成 APV3.0 的"输入-感受-表达"完整链路
前身: `Design_APV3.0_DraftIntrospection_ExpressionLearning_v1_20260616.md`(v1,有 9 处真缺陷,本稿全部修正)

---

## v1 → v2 关键修正一览(读这一节就能掌握所有变化)

| # | v1 缺陷(对抗审阅坐实) | v2 修正方向 |
|---|---|---|
| B1 | pattern_hash 在 bin 边界 jitter,雪崩函数把同一感受撕成 N 个 label,学习信号被稀释 | **原型响应度(prototype responsibility)取代 bin 哈希**:在 φ 空间维护原型 μ,label=原型 id,energy=软响应度,无 bin 边界 |
| B2 | intensity(φ, pattern)从未定义,基于"距 bin 中心"在离散码空间数学行不通 | **intensity = 软响应度 r_f(φ) = softmax(-d(φ,μ_f)/τ_f)**,well-defined ∈ [0,1] 且对极端纠结的 φ 给最高响应 |
| S1 | extract_facts 直读 `top_score / runner_up_score`,这些是文本 paradigm 字段,跨模态根本读不到 | **DraftSAEnergyView Protocol**:每个模态必须先经过校准适配器,输出归一化的 `fit_margin / occupancy / commit_readiness` 三个标准量 |
| S2 | self-listening 闭环——commit 的表达喂回来又触发 observe_positive_pair,无新证据但 co_count 单调累加 | **token 加 origin 字段**:`{perception_other, teacher_reply, self_emission}`;`gamma_origin[self_emission]=0` 默认 |
| S3 | reply_pressure 读 `state["recent_external_query_recency"]` 这种 dict scalar,等同于 must_reply=True 改名 | **pressure 输入必须是状态池里真的 SA**(external_query/companion/unfinished_work/silence),按 sa_type 加权求和 |
| S4 | red-line 只 grep 字面量"feeling::undecidable",绕开方式太多(HUMAN_LABELS 字典/测试硬塞 hash) | **三层语义检查**:AST 扫 `feeling::draft::pattern_*` 字面、运行时 label-bijection 不变量、测试不许内联 hash 字符串 |
| S5 | pattern_freq 字典只加不衰退,§6 默认懒淘汰但实际会让 novelty 信号永久失真 | **复用 v3.0 §12.4 半衰期衰减**:每 tick 对所有未触发条目衰减,低于 floor 的清除 |
| S6 | tick_with_introspection 调 `paradigm_fill` 两次,token-per-tick 契约模糊,且 has_undecidable 名字可疑 | **拆 `paradigm_fill_draft` vs `paradigm_rebind_slots`**:前者产 token,后者只改槽;has_undecidable 改为读 `commit_blocked` 结构事实 |
| S7 | §4.5 跨模态测试用根本不存在的 `make_visual_draft_with_shared_after_unresolved()` 是 fixture 串通 | **§4.5 改为 within-text 内容无关性测试**(已落地能验);跨模态延后到 §6 deferred,有第二模态时再开 |

修正后所有 G1–G6 验收目标依然成立,且**每一条都对应可证伪的具体测试**——这是 v1 缺的关键。

---

## 0. 问题陈述与设计目标(沿用 v1,无改)

### 0.1 用户哲学要求

> "我们人类更多的是先产生了一些内在的感受和表达倾向,然后后来根据这些来选取的表达范式来进行语言组织的。"

不能决但又必须有回复时,系统不应该硬编码"说'我不确定'",而应该:
1. **内部先产生一种感受**(纯结构性,由草稿状态派生);
2. **过去观察过别人在类似感受下用某种句式应对**;
3. **下次类似感受出现,联想到该句式,自然组织语言输出**。

### 0.2 当前缺口

Phase 7.2 把 `feeling::undecidable` 写死成字符串、`must_reply` 做成外部 bool、学习用 cue=feeling 教 reply=expression 的直接配对。这三处都不是真正的"感受 → 共现 → 学习"链路。

### 0.3 设计目标(v2 收紧验收依据)

| # | 目标 | 验收依据(v2) |
|---|---|---|
| G1 | feeling SA 标签由系统从草稿结构事实自动派生,不由外部约定 | §4.6 三层语义扫描:AST 扫 hash 字面外泄、label-bijection 不变量、测试不许内联 pattern hash |
| G2 | 同一机制能涌现任意数量的内省感受 | 加新原型只需注入新 φ 向量,机制不变;§4 增加"无名感受"路径测试 |
| G3 | "感受 → 表达范式"的关联完全由共现学习得出 | §4.2 训练 vs 控制对比:训练后 similarity 显著高于训练前(相对增量,不是绝对阈值) |
| G4 | 回复压力从状态池 SA 涌现 | §4.3 通过 ingest 注入 query/companion SA,而非 state["..."]=0.9 |
| G5 | 没学过任何疑惑表达时,感受 SA 仍进池但无表达召回 | §4.4 负例 + 严格 bootstrap 隔离 |
| G6 | 红线干净 | §4.6 + AST 扫描 + bijection 测试 + 内联硬编码扫描 |

---

## 1. 完整数学模型 v2

### 1.1 草稿结构特征空间(模态自适应)

**关键修正(S1 fix)**:特征不再直读 `top_score / occupancy` 这些文本特有字段,改为通过 **DraftSAEnergyView Protocol** 间接读校准量。

#### 1.1.1 DraftSAEnergyView 协议(模态适配契约)

每个模态必须提供 SAEnergyView 适配器,把原生输出归一化成三个标准量:

```python
class DraftSAEnergyView(Protocol):
    @property
    def fit_margin(self) -> float:
        """[0,1]: winning filler 优势 / runner-up,按该模态近期 margin 分布的 EMA(p10-p90) 校准"""
    @property
    def occupancy(self) -> float:
        """[0,1]: 这个 SA 槽位历史经验积累的非新颖性"""
    @property
    def commit_readiness(self) -> float:
        """[0,1]: v2.1 §3.6 已有的草稿自评估"""
```

`extract_facts` **只能读这三个字段 + role**,不许读任何模态原生字段。模态适配器是 tuner-owned EMA 校准,**不是硬编码 scaler**。

#### 1.1.2 特征向量 $\phi(D) \in \mathbb{R}^k$

| 编号 | 特征 | 公式 | 拟人意义 |
|---|---|---|---|
| $\phi_1$ | `has_shared_after_unresolved` | $\mathbb{1}[\exists i: \text{role}_i \in \{anchor, shared\} \land \exists j < i: \text{role}_j = slot \land \text{filler}_j = \emptyset]$ | 前面槽没填后面共享词蹦出来=不能决 |
| $\phi_2$ | `mean_slot_occupancy` | $\frac{1}{N_{slot}} \sum_{i: role_i=slot} \text{view}_i.\text{occupancy}$ | 槽位平均经验充实度 |
| $\phi_3$ | `min_fit_margin` | $\min_{i: role_i=slot} \text{view}_i.\text{fit\_margin}$ | 最弱槽位的纠结度 |
| $\phi_4$ | `paradigm_competition` | 归一化的 top-2 范式 conf 差 | 多个 ParadigmSA 平分秋色 |
| $\phi_5$ | `commit_readiness` | 草稿全局 view.commit_readiness 平均 | 流畅度 |
| $\phi_6$ | `recent_punishment_resemblance` | 草稿向量与近期被惩罚 commit 向量的 cos sim | 心虚 |
| $\phi_7$ | `unresolved_slot_count_norm` | 未填 slot 数 / 总 slot 数 | 总未决度 |

φ 是纯函数(同 D 同 φ),取值都被适配器归一化到 [0,1] 或 {0,1}。**G2 跨模态通用**由适配器契约保证,**不是由字段名长得像通用**(v1 的错)。

### 1.2 涌现 feeling SA 的机制(v2 核心重写)

**v1 错处**:用 bin 量化+blake2b 哈希命名,边界 jitter 会撕碎学习信号(B1);intensity 函数从未定义且基于"距 bin 中心"在离散码空间无定义(B2)。

**v2 解法**:**原型响应度(Prototype Responsibility)**——借用 Phase 2.5 的 PerceptPrototype 框架,无新学习器,无新机制。

#### 1.2.1 内省原型集合

维护 $\Phi$-空间(7 维)里的一组原型:

$$
M = \{\mu_1, \mu_2, ..., \mu_K\}, \quad \mu_f \in \mathbb{R}^7
$$

每个原型 $\mu_f$ 还有**逐坐标尺度** $\tau_f \in \mathbb{R}^7_+$(各特征量纲不同,$\tau_f$ 自动学到白化)。

**原型自然涌现 / 衰减**(完全复用 Phase 2.5 PerceptPrototype 已有规则,**不引入新机制**):
- 来一个新 φ,若离所有现有原型都 > spawn_pressure_threshold → 孵化新原型,$\mu_{K+1} = \phi$,$\tau_{K+1} =$ 初值 from config
- 否则按软分配更新最近原型: $\mu_f \leftarrow \mu_f + \eta \cdot r_f(\phi) \cdot (\phi - \mu_f)$;$\tau_f$ 由 EMA 残差平方更新
- 长时间无激活的原型按 v3.0 §12.4 衰减规则消亡

#### 1.2.2 软响应度(取代 v1 的 intensity)

$$
r_f(\phi) = \frac{\exp\left(-\sum_i (\phi_i - \mu_{f,i})^2 / (2\tau_{f,i}^2)\right)}{\sum_{g \in M} \exp\left(-\sum_i (\phi_i - \mu_{g,i})^2 / (2\tau_{g,i}^2)\right)}
$$

**性质**(对抗审阅 fix 核心):
- $r_f(\phi) \in (0, 1)$:well-defined,且对所有 $f$ 之和 = 1(soft assignment)
- **极端 φ 的处理**:若 φ 离所有原型都远,所有 $r_f$ 都低 → 触发新原型孵化(B2 修正:不会再把"极度纠结"分到错误的低 bin)
- **平滑跨原型**:φ 小幅度漂移 → $r_f$ 连续变化,**无边界 jitter**(B1 修正)
- **白化**:τ 自学坐标尺度,布尔 / [0,1] 浮点 / 计数等不同特征不再因量纲混乱

#### 1.2.3 feeling SA 标签 + 能量

label 由原型 id 派生:

$$
\text{label}_f = \text{"feeling::draft::proto\_"} \oplus \text{stable\_id}(\mu_f)
$$

其中 stable_id 是 tuner-owned 随机但确定的映射(同 μ 同 id),保证 G1。

feeling SA 能量:

$$
R_f = \alpha \cdot r_f(\phi), \quad P_f = \beta \cdot \text{novelty}(f, t)
$$

novelty 由该原型的 EMA 激活频率反比决定:稳定常用的原型 P 低,突然激活的原型 P 高。

#### 1.2.4 反对意见预答(原型不是硬编码)

可能反对:"既然有原型集合,这就是隐藏的预编码模板。"

**答**:
- 原型**完全从经验涌现**——初始集合为空,$M=\emptyset$;第一条 φ 来时孵化第一个原型,自此动态扩展。
- 原型的"含义"系统不知道——它就是 $\mathbb{R}^7$ 里的一个点。
- 这和 Phase 2.5 PerceptPrototype 是同一套机制:外部世界从感知 token 抽出原型,感受世界从 φ 抽出原型——**只是"特征空间"换了**。
- 这才是真正的"语义自下而上涌现"。

### 1.3 共现学习契约(S2 修正:加 token provenance)

#### 1.3.1 触发条件

任意 tick t,若状态池里**同时**存在:

- 至少一个 feeling SA: $f_t \in F_{draft}(t)$
- 至少一个外部表达 token: $e_t^j \in E_t$

**关键 v2 修正**:每个 $e_t^j$ 携带 `origin` 字段:

$$
\text{origin}(e) \in \{\text{perception\_other}, \text{teacher\_reply}, \text{self\_emission}\}
$$

由 ingest 层根据 token 来源端口直接打标,**不是关键词分支**,是结构 metadata(同 role/occupancy 一样)。

#### 1.3.2 学习律(带 provenance 权重)

$$
w(f, e^j) = \text{clip}\left( \frac{R_f}{R_f + \kappa} \cdot \gamma_{co} \cdot \gamma_{\text{origin}}[\text{origin}(e^j)], \; 0, \; w_{max} \right)
$$

其中:
- $\gamma_{\text{origin}}$ 是 tuner-owned 字典:`{perception_other: 1.0, teacher_reply: 1.0, self_emission: 0.0}` 默认
- $R_f = \alpha \cdot r_f(\phi)$,well-defined(B2 修正)
- $\kappa$ 是 tuner-owned 饱和常数

调用:`observe_positive_pair(f.label, e^j, weight=w(f, e^j))`

#### 1.3.3 self_emission 默认为 0 的理由

- 防止 commit 出去的表达**通过自听**自我强化(S2 闭环)
- 但保留 `gamma_origin[self_emission]` 作为 config 字段,**未来若有证据表明自言自语有价值**(比如 commit 后获得正向反馈),可以由 tuner 慢慢学到一个正值
- **这不是硬编码** 0 — 是默认值 0 + 可学习权重

### 1.4 召回链路(v2:加双阶段索引,fix S3-M1 性能)

#### 1.4.1 两阶段召回

```python
# Stage 1: 快索引(O(K) where K << |paradigms|)
candidates = embed.nearest_by_label(feeling_labels, top_k=K_fast)
# Stage 2: 精排(O(K_fast × |feelings|))
scored = []
for p in candidates:
    score = sum(f.R * embed.learned_similarity([f.label], list(p.cue_tokens)) for f in F_t)
    scored.append((p, score))
```

`nearest_by_label` 是既有接口(若没有则一行加在 OnlineEmbeddingStore)。这是 v3.0 §3.6 标准范式召回的标准模式,**复用**。

#### 1.4.2 涌现的回复压力(S3 修正)

**v1 错处**:`state.get("recent_external_query_recency", 0.0)` 等四个 dict scalar 读,等于 must_reply=True 改名(S3)。

**v2 解法**:**所有 pressure 输入必须是状态池里真的 SA**,通过 sa_type 过滤+加权求和。

```python
def derive_reply_pressure_sa(state: dict, config: IntrospectionConfig) -> ReplyPressureSA:
    items = state.get("state_field_items", [])
    raw = 0.0
    for sa in items:
        sa_type = sa.get("sa_type", "")
        weight = config.pressure_type_weights.get(sa_type, 0.0)  # tuner-owned dict
        if weight != 0:
            raw += weight * sa.get("real_energy", 0.0)
    pressure_level = 1.0 / (1.0 + math.exp(-raw))
    return ReplyPressureSA(
        sa_label="feeling::reply_pressure",
        sa_type="reply_pressure",
        real_energy=pressure_level,
        cognitive_pressure=max(0.0, pressure_level - config.reply_pressure_neutral),
    )
```

`pressure_type_weights` 配置示例:
```yaml
pressure_type_weights:
  external_query: +1.0     # 外部询问 SA → 抬压力
  companion: +0.5          # 同伴在场 SA → 抬
  teacher_present: +0.8    # 老师在场 → 抬
  unfinished_work: +0.7    # 工作记忆未闭合 → 抬
  silence: +0.3            # 沉默时长 SA → 抬
  recent_commit: -1.2      # 刚 commit 过 → 压低
```

**关键**:这些 sa_type 必须是状态池里**真存在的 SA 类型**,由相应的 ingest/产生模块写入:
- `external_query` SA:由 ingest 模块在收到外部话语时铸造,real_energy 随 tick 衰减
- `companion` SA:已是 v2.1 状态池一等公民,直接读
- `unfinished_work` SA:Phase 5.7/5.9 已有
- `silence` SA:由心跳模块产生,real_energy = sigmoid((tick - last_commit) / τ)
- `recent_commit` SA:commit 后产生的瞬态 SA,real_energy 随 tick 衰减

**测试必须通过 ingest 注入 SA**,不许 `state["..."]=0.9`。这是 G4 的硬验收。

### 1.5 自言自语回路(minor P10,有界)

补 v1 漏的"内化路径":若上一 tick commit 出 expression,且本 tick 未受惩罚,把它作为带 `origin=self_emission` 的 token 喂回 §1.3。默认 `gamma_origin[self_emission]=0`,所以这条路径默认不学;但 config 可以开。这把决策留给 tuner。

---

## 2. 伪代码 v2

### 2.1 草稿结构特征抽取器(模态适配)

```python
# APV3.0test/apv3test/runtime/draft_introspection.py
from dataclasses import dataclass
from typing import Protocol, Sequence

class DraftSAEnergyView(Protocol):
    fit_margin: float       # [0,1] 该模态自校准
    occupancy: float        # [0,1]
    commit_readiness: float # [0,1] v2.1 §3.6
    role: str               # "slot" | "fixed_anchor" | "shared_fragment"
    filler: str | None      # 已填的 token,None 表示未填

@dataclass(frozen=True)
class DraftStructuralFacts:
    has_shared_after_unresolved: bool
    mean_slot_occupancy: float
    min_fit_margin: float
    paradigm_competition: float
    commit_readiness: float
    recent_punishment_resemblance: float
    unresolved_slot_count_norm: float
    commit_blocked: bool  # 派生事实,用于 §2.7 gate

def extract_facts(
    views: Sequence[DraftSAEnergyView],
    active_paradigms,
    recent_punished_commits,
    embed,
    config,
) -> DraftStructuralFacts:
    # CI 检查:此函数禁止读 views[i] 上不在 DraftSAEnergyView 协议里的字段
    # 红线扫描 grep -rn 'd\.top_score\|d\.runner_up_score' 必须为空
    n_slot = sum(1 for v in views if v.role == "slot")
    has_shared = any(
        v.role in {"fixed_anchor", "shared_fragment"}
        and any(prev.role == "slot" and prev.filler is None for prev in views[:i])
        for i, v in enumerate(views)
    )
    mean_occ = sum(v.occupancy for v in views if v.role == "slot") / max(1, n_slot)
    margins = [v.fit_margin for v in views if v.role == "slot"]
    min_margin = min(margins) if margins else 1.0
    # ... 其余特征
    commit_blocked = (
        sum(v.commit_readiness for v in views) / max(1, len(views)) < config.ready_floor
        or min_margin < config.margin_floor
    )
    return DraftStructuralFacts(...)
```

### 2.2 原型响应度命名 + 能量(取代 pattern_hash)

```python
# 复用 Phase 2.5 PerceptPrototype 框架,无新机制
class IntrospectionPrototypeStore:
    def __init__(self, config):
        self.prototypes: list[Prototype] = []  # 起始为空
        self.config = config

    def respond_or_spawn(self, phi: np.ndarray) -> tuple[Prototype, float]:
        if not self.prototypes:
            new_p = self._spawn(phi)
            return new_p, 1.0
        responsibilities = self._compute_softmax_responsibilities(phi)
        best_f, best_r = max(responsibilities.items(), key=lambda x: x[1])
        # 极端 φ 离所有原型都远 → 孵化新
        max_distance = max(self._distance(phi, p) for p in self.prototypes)
        if best_r < self.config.spawn_responsibility_floor and max_distance > self.config.spawn_distance_threshold:
            new_p = self._spawn(phi)
            return new_p, 1.0
        # 否则按软分配更新所有原型
        for p, r in responsibilities.items():
            self._update_prototype(p, phi, r)
        return best_f, best_r

    def _compute_softmax_responsibilities(self, phi) -> dict[Prototype, float]:
        logits = {p: -np.sum((phi - p.mu)**2 / (2 * p.tau**2)) for p in self.prototypes}
        max_l = max(logits.values())
        exp_l = {p: math.exp(l - max_l) for p, l in logits.items()}
        z = sum(exp_l.values())
        return {p: v / z for p, v in exp_l.items()}

    def _spawn(self, phi) -> Prototype:
        p = Prototype(
            id=self._next_stable_id(),
            mu=phi.copy(),
            tau=np.full_like(phi, self.config.tau_init),
            last_activated_tick=self._current_tick,
        )
        self.prototypes.append(p)
        return p

    def decay_unactivated(self, current_tick: int) -> None:
        # 复用 v3.0 §12.4 半衰期衰减
        decayed = []
        for p in self.prototypes:
            age = current_tick - p.last_activated_tick
            p.activation_ema *= self.config.half_life_decay ** age
            if p.activation_ema > self.config.eviction_floor:
                decayed.append(p)
        self.prototypes = decayed
```

### 2.3 feeling SA 涌现 v2

```python
def emit_draft_introspection_feelings(
    views, state, embed, store: IntrospectionPrototypeStore, config
) -> list[FeelingSA]:
    if not views:
        return []
    facts = extract_facts(views, state.get("paradigms", []),
                          state.get("recent_punished_commits", []), embed, config)
    phi = np.array([
        float(facts.has_shared_after_unresolved),
        facts.mean_slot_occupancy,
        facts.min_fit_margin,
        facts.paradigm_competition,
        facts.commit_readiness,
        facts.recent_punishment_resemblance,
        facts.unresolved_slot_count_norm,
    ])
    proto, r = store.respond_or_spawn(phi)

    feeling = FeelingSA(
        sa_label=f"feeling::draft::proto_{proto.id}",
        sa_type="draft_introspection_feeling",
        real_energy=config.alpha * r,
        cognitive_pressure=config.beta * (1.0 / (1.0 + proto.activation_ema)),
        prototype_id=proto.id,
        facts=facts,
        tick=state.get("tick", 0),
    )
    # 写入状态池 state_field_items(同 work_memory_unfinished 同模式)
    state.setdefault("state_field_items", []).append(feeling.to_dict())
    proto.last_activated_tick = state.get("tick", 0)
    proto.activation_ema = proto.activation_ema * config.half_life_decay + 1.0
    # 把 commit_blocked 挂上 state,供 §2.7 gate 用
    state["draft_commit_blocked"] = facts.commit_blocked
    return [feeling]
```

### 2.4 共现学习契约 v2(带 provenance)

```python
@dataclass(frozen=True)
class ExternalExpressionToken:
    token: str
    origin: str  # "perception_other" | "teacher_reply" | "self_emission"

def observe_feeling_expression_cooccurrence(
    feelings: Sequence[FeelingSA],
    external_tokens: Sequence[ExternalExpressionToken],
    embed,
    config,
) -> None:
    if not feelings or not external_tokens:
        return
    for f in feelings:
        for e in external_tokens:
            gamma_origin = config.gamma_origin.get(e.origin, 0.0)
            if gamma_origin <= 0:
                continue
            w_f = (f.real_energy / (f.real_energy + config.cooccurrence_saturation)
                   ) * config.cooccurrence_lr * gamma_origin
            w_f = min(w_f, config.cooccurrence_max_weight)
            if w_f <= 0:
                continue
            embed.observe_positive_pair(f.sa_label, e.token, weight=w_f)
```

### 2.5 双阶段召回(fix S3-M1)

```python
def recall_expression_paradigms_for_feelings(
    feelings, embed, config
) -> list[tuple[ParadigmSA, float]]:
    # Stage 1: 快索引(K_fast << |paradigms|)
    feeling_labels = [f.sa_label for f in feelings]
    candidate_paradigm_ids = embed.nearest_paradigm_cues_by_labels(
        feeling_labels, top_k=config.K_fast
    )
    # Stage 2: 精排
    scored = []
    for pid in candidate_paradigm_ids:
        p = lookup_paradigm(pid)
        if not p:
            continue
        total = sum(
            f.real_energy * embed.learned_similarity([f.sa_label], list(p.cue_tokens)).get("score", 0.0)
            for f in feelings
        )
        if total > 0:
            scored.append((p, total))
    scored.sort(key=lambda x: -x[1])
    return scored
```

### 2.6 涌现回复压力 v2(S3 修正)

```python
def derive_reply_pressure_sa(state, config) -> ReplyPressureSA:
    raw = 0.0
    sources = []
    for sa in state.get("state_field_items", []):
        sa_type = sa.get("sa_type", "")
        weight = config.pressure_type_weights.get(sa_type, 0.0)
        if weight != 0:
            contribution = weight * float(sa.get("real_energy", 0.0))
            raw += contribution
            sources.append((sa_type, sa.get("sa_label", ""), contribution))
    pressure_level = 1.0 / (1.0 + math.exp(-raw))
    return ReplyPressureSA(
        sa_label="feeling::reply_pressure",
        sa_type="reply_pressure",
        real_energy=pressure_level,
        cognitive_pressure=max(0.0, pressure_level - config.reply_pressure_neutral),
        provenance=sources,  # trace 用,白箱可审计
    )
```

### 2.7 tick 编排 v2(S6 修正:拆 fill/rebind)

```python
def tick_with_introspection(state, input):
    # Phase 0: ingest 外部输入 → 铸造对应 SA 入池(包括 external_query/companion/silence 等)
    ingest(input, state)

    # Phase 1: 既有 recall + 草稿
    paradigm_candidates = recall_paradigm(state, input)
    drafts = paradigm_fill_draft(paradigm_candidates, state)  # 每 tick 最多 emit 1 token

    # Phase 2: 涌现内省感受
    views = wrap_drafts_with_energy_view(drafts, state)  # 模态适配器在这里
    feelings = emit_draft_introspection_feelings(views, state, embed, prototype_store, config)

    # Phase 3: 共现学习(外部表达 token 必须带 origin)
    external_tokens = extract_external_expression_tokens(input, state)
    observe_feeling_expression_cooccurrence(feelings, external_tokens, embed, config)

    # Phase 4: 涌现回复压力
    reply_pressure = derive_reply_pressure_sa(state, config)
    state["state_field_items"].append(reply_pressure.to_dict())

    # Phase 5: 是否触发表达召回(注意:删除 has_undecidable;改读 commit_blocked 结构事实)
    if (reply_pressure.real_energy > config.must_reply_threshold
            and state.get("draft_commit_blocked", False)):
        expr_candidates = recall_expression_paradigms_for_feelings(feelings, embed, config)
        if expr_candidates:
            best_paradigm, _ = expr_candidates[0]
            # 关键:rebind_slots 不 emit token,只改已有草稿的槽位
            drafts = paradigm_rebind_slots(drafts, best_paradigm, focus_tokens=high_grasp_fragments(drafts))
            # 重新算 feeling(stale-feeling 修正)
            views2 = wrap_drafts_with_energy_view(drafts, state)
            feelings2 = emit_draft_introspection_feelings(views2, state, embed, prototype_store, config)
            # 至少一个新 feeling 仍 endorse 这个 paradigm 才允许 commit
            endorses = any(
                embed.learned_similarity([f.sa_label], list(best_paradigm.cue_tokens)).get("score", 0.0)
                > config.endorse_threshold
                for f in feelings2
            )
            if not endorses:
                drafts = mark_as_blocked(drafts)

    # Phase 6: commit gate(若草稿可 commit 且未被 block)
    return commit_or_keep_drafting(drafts, state)
```

**关键:整个 tick 最多 emit 1 token**(由 `paradigm_fill_draft` 保证),`paradigm_rebind_slots` 只改已有草稿的 slot filler,不 emit。**这是 §3 红线表新增的"single externally-visible emission per tick"不变量**。

---

## 3. 红线核对(v2 扩展)

| v3.1 红线 | 本设计是否合规 | 说明 |
|---|---|---|
| 不新增关键词 if-else | ✅ | 无 if feeling.label.startswith(...) |
| 不新增答案表 | ✅ | 表达范式是普通 ParadigmSA,共现学到 |
| 不新增整句宏 | ✅ | 每 tick 单 token emit |
| 不用学生侧 LLM | ✅ | 完全无 LLM 调用 |
| 不让自生成草稿增正向 support | ✅ | gamma_origin[self_emission]=0 默认 |
| **不让自 commit 表达通过自听抬 OnlineEmbedding co_counts** | ✅(v2 新增 S2 fix) | provenance 字段 + gamma_origin gating |
| 阈值是 config/tuner 字段 | ✅ | 所有 spawn 阈、半衰期、γ、bin、τ 都 tuner |
| 每输出 token 可回溯证据链 | ✅ | trace: facts → prototype id → feeling SA → recalled expression → emit |
| 不出现 if vision/if text | ✅ | DraftSAEnergyView 适配器是 v2 修正,无 if branch |
| **每 tick 最多 1 个外部 emit** | ✅(v2 新增 S6 fix) | paradigm_fill_draft vs paradigm_rebind_slots 拆分 |
| **pressure 输入必须是状态池 SA 而非 dict scalar** | ✅(v2 新增 S3 fix) | iterate state_field_items + sa_type 过滤 |

---

## 4. 验收门 v2(每条对应已修正的 blocker/serious)

### 4.1 内省感受无教学自涌现

```python
def test_introspection_feeling_emerges_without_teaching():
    state, store = bootstrap_empty()
    draft_with_undecidable = make_canonical_unresolved_draft_through_text_pipeline()
    state = tick_with_introspection(state, TickInput(draft=draft_with_undecidable))
    feelings = [sa for sa in state["state_field_items"]
                if sa["sa_type"] == "draft_introspection_feeling"]
    assert len(feelings) >= 1
    assert feelings[0]["sa_label"].startswith("feeling::draft::proto_")
    # 没教过任何表达范式,所以没有 expression recall
    assert not state.get("recalled_expression_paradigms")
```

### 4.2 共现学习相对增量测试(S3-M2 修正)

**不再硬编码 0.3 阈值**,改用相对增量:

```python
def test_cooccurrence_learning_increment():
    state, store, embed = bootstrap_empty()
    # 用随机 token 名,测试方不"知道"它是什么
    expression_token = f"expr::{random.random_id(8)}"
    distractor_token = f"expr::{random.random_id(8)}"

    # 训练前测相似度
    feeling_label_pre = peek_first_feeling_label(state, store)
    sim_before = embed.learned_similarity([feeling_label_pre], [expression_token]).get("score", 0)

    for _ in range(50):
        state = tick_with_introspection(state, TickInput(
            draft=make_canonical_unresolved_draft_through_text_pipeline(),
            external_tokens=[ExternalExpressionToken(expression_token, "teacher_reply"),
                             ExternalExpressionToken(distractor_token, "perception_other")],
        ))

    feeling_label_post = peek_first_feeling_label(state, store)
    sim_after = embed.learned_similarity([feeling_label_post], [expression_token]).get("score", 0)
    sim_distractor_after = embed.learned_similarity([feeling_label_post], [distractor_token]).get("score", 0)

    # 相对增量,而非绝对阈值
    assert sim_after - sim_before > config.test_learning_delta_min
    # 训练 token 涨,但任意控制 token 不该涨这么多
    untrained_token = f"expr::{random.random_id(8)}"
    sim_untrained = embed.learned_similarity([feeling_label_post], [untrained_token]).get("score", 0)
    assert sim_after > sim_untrained + config.test_learning_separation_min
```

### 4.3 reply_pressure 通过 ingest 注入,不许 dict scalar(G4 修正)

```python
def test_reply_pressure_emerges_from_sa_ingestion():
    state, store, embed = bootstrap_empty()
    # 训练共现关联
    state = train_cooccurrence_learning(state, n=50)
    # 通过 ingest 注入 external_query SA(而不是 state["..."]=0.9)
    state = tick_with_introspection(state, TickInput(
        incoming_external_query="something_uncertain"
    ))
    # 检查状态池里出现了 external_query SA
    assert any(sa["sa_type"] == "external_query"
               for sa in state.get("state_field_items", []))
    # 检查 reply_pressure SA 涌现且 real_energy 高
    reply_p = next(sa for sa in state["state_field_items"]
                   if sa["sa_type"] == "reply_pressure")
    assert reply_p["real_energy"] > config.must_reply_threshold
    # 触发表达召回
    state = tick_with_introspection(state, TickInput(
        draft=make_canonical_unresolved_draft_through_text_pipeline()
    ))
    assert state.get("recalled_expression_paradigms")
```

### 4.4 负例:没学过就不该有表达,严格 bootstrap 隔离

```python
def test_no_expression_when_not_learned():
    state, store, embed = bootstrap_truly_empty()  # 严格隔离,新 OnlineEmbeddingStore 实例
    state = tick_with_introspection(state, TickInput(
        incoming_external_query="urgent",
        draft=make_canonical_unresolved_draft_through_text_pipeline()
    ))
    assert not state.get("recalled_expression_paradigms")
    assert not state.get("commit_text")
```

### 4.5 内容无关性(within text,S7 修正)

**v1 错处:`make_visual_draft_with_shared_after_unresolved` 不存在,跨模态测试是 fixture 串通。**

**v2:改成 within-text 内容无关性测试,有真实可验。**

```python
def test_content_independence_within_text():
    state1, store, embed = bootstrap_empty()
    draft_apple_color = make_text_draft_through_real_pipeline(
        cue=("苹果",), slot_tokens=("颜色",))
    state1 = tick_with_introspection(state1, TickInput(draft=draft_apple_color))
    feeling_apple = peek_first_feeling_label(state1, store)

    state2, _, _ = bootstrap_empty()
    draft_snowflake_shape = make_text_draft_through_real_pipeline(
        cue=("雪花",), slot_tokens=("形状",))
    state2 = tick_with_introspection(state2, TickInput(draft=draft_snowflake_shape))
    feeling_snowflake = peek_first_feeling_label(state2, store)

    # 不同内容但同结构事实 → 同 prototype → 同 label
    # (因为 prototype 是φ空间里的点,φ 不读 token 内容)
    assert feeling_apple == feeling_snowflake
```

### 4.5b 跨模态(deferred)

待第二模态(如 glyph token / 简单视觉)pipeline 落地后,通过 DraftSAEnergyView Protocol 适配器构造视觉 draft,做真正跨模态测试。**当前以 PROTOCOL 契约保证可扩展,以测试推迟保证不撒谎**。

### 4.6 红线扫描三层(S4 修正)

**v1 错处:只 grep 字面量"feeling::undecidable"等,绕开方式太多。**

**v2 三层语义检查**:

#### 4.6.1 AST 级扫描
```python
# 扫所有 runtime 源文件
def test_no_pattern_label_string_literals_in_runtime():
    import ast
    for py_file in iter_runtime_py_files():
        tree = ast.parse(py_file.read_text())
        for node in ast.walk(tree):
            # 检查所有字符串字面量
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                # 禁止 "feeling::draft::proto_*" 这种 prototype id 字面外泄
                assert not re.match(r"feeling::draft::proto_[a-f0-9]+", node.value), \
                    f"硬编码 prototype label: {node.value} @ {py_file}:{node.lineno}"
            # 检查所有 Compare/In 节点,RHS 是字符串字面 + LHS 含 sa_label
            if isinstance(node, ast.Compare):
                for comparator in node.comparators:
                    if isinstance(comparator, ast.Constant) and isinstance(comparator.value, str):
                        if "label" in ast.dump(node.left):
                            assert "feeling::" not in comparator.value, \
                                f"label 字符串硬编码比较 @ {py_file}:{node.lineno}"
```

#### 4.6.2 Label-Bijection 不变量测试
```python
def test_label_opacity_via_random_bijection():
    """如果有任何代码读 label 语义内容,这个测试会暴露它。"""
    state, store, embed = bootstrap_empty()
    state = train_cooccurrence_learning(state, n=50)

    # 跑一次 tick,记录所有 emit token + recall scores
    result_normal = tick_with_introspection(state, TickInput(...))

    # 应用随机 bijection 把所有 sa_label 映射到随机 token
    # (在 OnlineEmbeddingStore 内部 key 一并替换)
    state_mapped, embed_mapped = apply_label_bijection(state, embed, random_bijection)
    result_mapped = tick_with_introspection(state_mapped, TickInput(...))

    # 因为 label 应该是 opaque key,bijection 不该改变行为
    assert result_normal.recalled_paradigm_ids == result_mapped.recalled_paradigm_ids
    assert abs(result_normal.commit_pressure - result_mapped.commit_pressure) < 1e-6
```

#### 4.6.3 测试端禁止内联 hash 字面
```python
# CI 扫所有 tests/
def test_no_inline_prototype_ids_in_test_files():
    for test_file in iter_test_py_files():
        content = test_file.read_text()
        # 禁止 "feeling::draft::proto_<hex>" 字面出现在测试
        # 测试应该通过 store.respond_or_spawn(make_facts(...)) 派生
        assert not re.findall(r"feeling::draft::proto_[a-f0-9]{6,}", content), \
            f"测试内联 prototype id:{test_file}"
```

### 4.7 self-listening 隔离(S2 修正)

```python
def test_self_emission_does_not_inflate_cooccurrence():
    state, store, embed = bootstrap_empty()
    state = train_cooccurrence_learning(state, n=50, expression_token="expr::test")

    # 测训练后的 co_count
    sim_before_self = embed.learned_similarity([first_feeling_label(state)], ["expr::test"]).get("score")

    # 让系统自己 commit 出 "expr::test" 然后通过 self_emission 重新进入
    for _ in range(50):
        state = tick_with_introspection(state, TickInput(
            draft=make_canonical_unresolved_draft_through_text_pipeline(),
            # 通过 self_emission 路径喂回自己 commit 的 token
            external_tokens=[ExternalExpressionToken("expr::test", "self_emission")],
        ))

    sim_after_self = embed.learned_similarity([first_feeling_label(state)], ["expr::test"]).get("score")

    # 默认 gamma_origin[self_emission]=0,所以 co_count 不该变
    assert abs(sim_after_self - sim_before_self) < 1e-4
```

### 4.8 jitter 鲁棒性(B1 修正)

```python
def test_prototype_responds_smoothly_to_feature_drift():
    state, store, _ = bootstrap_empty()
    # 喂 20 个连续 tick,只让 min_fit_margin 从 0.30 平滑漂到 0.40
    feelings_traces = []
    for i in range(20):
        phi = make_phi_with_margin_at(0.30 + i * 0.005)
        proto, r = store.respond_or_spawn(phi)
        feelings_traces.append(proto.id)
    # 平滑漂移不该让 prototype id 翻转多次
    unique_protos = set(feelings_traces)
    assert len(unique_protos) <= 2, \
        f"平滑漂移产生了 {len(unique_protos)} 个原型,bin jitter 没修干净"
```

### 4.9 pattern_freq 衰减(S5 修正)

```python
def test_pattern_freq_decays_unactivated_patterns():
    state, store, _ = bootstrap_empty()
    # 触发原型 A
    state = tick_with_introspection(state, TickInput(draft=draft_A))
    # 跑 1000 ticks 不再激活 A
    for _ in range(1000):
        state = tick_with_introspection(state, TickInput(draft=draft_B))
    # 原型 A 应该已被衰减驱逐
    proto_a_id = first_proto_id_for_draft(draft_A, store)
    assert proto_a_id not in [p.id for p in store.prototypes], \
        "未触发原型未按 v3.0 §12.4 衰减驱逐"
    # 重新喂 A,novelty 应当 ≈ 第一次的水平(不被残留 freq 抑制)
    proto_a_new, _ = store.respond_or_spawn(make_phi_for_draft(draft_A))
    assert proto_a_new.activation_ema < 0.1
```

---

## 5. 工程落地步骤(给 Codex)

1. **新增 `APV3.0test/apv3test/runtime/draft_introspection.py`**(~200 行):
   - `DraftSAEnergyView` Protocol
   - `extract_facts` 函数(仅读 Protocol 字段)
   - `IntrospectionPrototypeStore` 类(复用 PerceptPrototype 风格)
   - `emit_draft_introspection_feelings` 函数

2. **新增 `APV3.0test/apv3test/runtime/cooccurrence_learning.py`**(~80 行):
   - `ExternalExpressionToken` dataclass(带 origin)
   - `observe_feeling_expression_cooccurrence` 函数

3. **新增 `APV3.0test/apv3test/runtime/reply_pressure.py`**(~60 行):
   - `derive_reply_pressure_sa` 函数(读状态池 SA,不读 dict scalar)
   - 配套:`external_query` / `silence` / `recent_commit` SA 类型注册

4. **修改 `incremental_tick_runtime.py`**:
   - 删除 `undecidable_feeling_tokens` 和 `must_reply: bool` 参数
   - ingest 阶段铸造 `external_query` 等 SA 入池
   - tick 编排按 §2.7 v2 重写(拆 fill/rebind)

5. **修改 `paradigm_fill.py`**:拆分 `paradigm_fill_draft` 和 `paradigm_rebind_slots`

6. **新增 `APV3.0test/apv3test/config/introspection_config.py`**:
   - 原型 spawn/decay 参数
   - bin/τ 初值
   - `gamma_origin` dict
   - `pressure_type_weights` dict
   - 各阈值(must_reply / endorse / spawn 等)

7. **新增模态适配器骨架** `APV3.0test/apv3test/runtime/modality_adapters.py`:
   - text adapter(实现 DraftSAEnergyView)
   - 留 vision adapter stub(deferred)

8. **新增测试** `test_phase7_3_*`:§4 的 9 个验收门 + 4.6.1/4.6.2/4.6.3 三层扫描

---

## 6. 未决问题(诚实 v2)

1. **原型集合可能过度增长**:虽然有 §12.4 衰减,但短期内涌现速率 vs 衰减速率的平衡需 tuner 调。建议加 `max_prototypes` 软上限(不是硬钳,超了启动 aggressive 衰减)。

2. **跨模态适配器尚无第二模态可验**:DraftSAEnergyView Protocol 是契约,但只有 text 实现。等 vision/audio 阶段到了再验,届时 §4.5b 解锁。

3. **τ_f 学习速率**:坐标尺度自学是新机制,初值和学习率需要 tuner 标定。可能需要几个 phase 才能稳定。

4. **gamma_origin[self_emission] 是否该学习**:默认 0 防自循环,但人类自言自语确实有学习价值。是否给一个小正值由 tuner 决定。

5. **多 feeling 同时活跃时的注意力分配**:当前 §2.5 用线性加权,可能某 feeling 主导。是否需要 softmax 或注意力机制需测试观察。

6. **EMA 校准在适配器内的初始化**:第一条 draft 来时无 EMA 历史,模态适配器需要 graceful default(可能用配置 prior 平滑过渡)。

---

## 7. 哲学总判 v2

本设计 v2 实现了用户的核心要求,并修正了 v1 的所有数学/工程缺陷:

> **"我们人类更多的是先产生了一些内在的感受和表达倾向,然后后来根据这些来选取的表达范式来进行语言组织的。"**

- **内在感受**:从草稿结构事实派生 φ → 软响应度 → 原型 id 命名的 feeling SA
- **可证伪标签 opacity**:label-bijection 测试保证任何代码都不能依赖 label 内容做分支
- **表达倾向**:reply_pressure 由真实状态池 SA(query/companion/silence/unfinished)能量加权涌现
- **选取表达范式**:learned_similarity 召回 + 双阶段索引(性能可扩展)
- **后天学到**:provenance gating 防自循环,默认只学外部教师/同伴的表达
- **通用扩展**:加新原型只需让 φ 进新区域;加新模态只需实现 DraftSAEnergyView 适配器
- **数学严密**:原型响应度 well-defined,无 bin 边界 jitter,白化坐标尺度

**最关键:经 3 路独立对抗审阅 26 条核验,所有 blocker/serious 已落实修正。这次不是纸上谈兵的设计,是经得起反复盘问的设计。**
