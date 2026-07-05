# APV3.0 Phase 19 v1b Micro Errata — Implementation-Sensitive Closure

Date: 2026-06-19
Author: Claude(架构),银子老师(风格定调与最终签收)
Status: 设计稿微修订(micro errata),叠加在 v1 + v1a 之上。**这是开工前最后一份**;通过此份后 Codex 可启动 Phase 19.0 实现。
Source: 吸收 [AdversarialReview v1a Final Micro Errata](AdversarialReview_APV3_Phase19_v1a_FinalMicroErrata_20260619.md) 全部 7 条 micro issue + 我自查发现的 3 个衍生隐患
License intent: AGPL-3.0-or-later
Real name handling: 全文件 grep 真名 = 0

---

## 0. 这一份做什么(一句话)

把 v1a 留下的 7 处工程接口缝隙钉死,使得 Codex 可以基于 v1 + v1a + v1b **三份合读** 直接开工 Phase 19.0,不再需要架构级修订。

---

## 1. 全部修订清单(7 收 Codex + 3 自查)

| 修订 ID | 来源 | 内容 |
|---|---|---|
| **C1** | Codex M1 + 我 self-1 | `confidence_score`(数值)与 `decision_tier`(档位)分离 |
| **C2** | Codex M2 | source-aware feedback 在 runtime 用 contribution 自动分摊,evaluator-oracle 仅 audit 模式可用 |
| **C3** | Codex M3 | novelty 拆 `ν_object` / `ν_context`,仅 ν_object 进 tier_map,ν_context 调好奇心 / 再注视 |
| **C4** | Codex M4 | error taxonomy 操作化:blind evaluator 路径 + cue-based audit rule,二选一,**禁**事后主观判定 |
| **C5** | Codex M5 | V0 / A0 拆 `receptor_fast_path` 与 `reconstruction_audit_path`,tick 预算守住 |
| **C6** | Codex M6 | 12 张图 stratified k-fold,禁单次固定 split |
| **C7** | Codex M7 | recall_score 归一化到 `[0,1]`,`learned_cooccurrence` 来源锁死 training_sdpl_only |
| **S1** | 我自查 | μ 收进 raw_confidence 而不是 tier_map 第二参数,统一为单一 numeric 标量 |
| **S2** | 我自查 | §9 feedback gates 改为按 contribution 分摊的统计指标(配合 C2) |
| **S3** | 我自查 | v1a §7 retrieval 公式的 α 常量在 v1b 增加 `_source` 标注与 redline |

---

## 2. C1 + S1 — `confidence_score` 与 `decision_tier` 分离

### 2.1 替换 v1a §4.1 主公式

**v1a 旧版**(混淆):
$$
\mathrm{Conf}(c|x) = \mathrm{TierMap}(\Pi \cdot \Gamma \cdot Q, \mu, \nu)
$$

**v1b 新版**(分离):

$$
\boxed{
\mathrm{raw\_confidence}(c|x) = \Pi(c|x) \cdot \Gamma(c|x) \cdot Q(x) \cdot \mu(c|x)
}
$$

$$
\mathrm{decision\_tier}(c|x) = \mathrm{TierMap}(\mathrm{raw\_confidence}(c|x), \nu_{\mathrm{object}}(x))
$$

### 2.2 状态池 metadata 字段(替换 v1a §2.2)

```python
metadata = {
    "render_mode": "sensory_sketch" | "prototype_imagination",
    "input_trace_hash": <hex>,
    "prototype_trace_hash": <hex or null>,
    "evaluator_label_accessed": False,
    "epistemic_source": "PERCEIVED_SENSORY_SKETCH" | ...,
    "source_confidence": float,
    # 新增 v1b:
    "confidence_score": float,                # raw_confidence ∈ [0,1]
    "decision_tier": "firm" | "soft" | "ambig" | "no_call",
    "confidence_decomposition": {
        "Pi": float, "Gamma": float, "Q": float, "mu": float,
        "nu_object": float, "nu_context": float,
        "active_cues": [str],                 # 通道名 list
        "channel_evidence": {f"V{k}": float for k in range(10)},
    },
}
```

### 2.3 红线扩展

| RL | 描述 |
|---|---|
| RL-19v1b-C1-01 | 任何测试 / 反馈代码不得把 `decision_tier`(字符串)与 `confidence_score`(浮点)互相比较 |
| RL-19v1b-C1-02 | Recall@K / feedback delta / 反馈 source-aware 调整一律用 `confidence_score`,UI / 输出文本一律用 `decision_tier` |

---

## 3. C2 + S2 — Source-Aware Feedback 在 runtime 用 contribution 自动分摊

### 3.1 v1a §9 替换为双模式

**Audit 模式(测试)**:evaluator 显式给 `error_source ∈ {PERCEIVED, IMAGINED, INFERRED, REMEMBERED}` → 走 oracle 路径

**Runtime 模式(自然对话)**:用户只说"不对"或"这是 X",AP 必须按各 source 对决策的贡献自动分摊惩罚。

### 3.2 Contribution 计算

decision 当时贡献的 source 集合 $\mathcal{S}(c^*, x) = \{s : \text{source } s \text{ 参与了 } c^* \text{ 的 } \mathrm{raw\_confidence}\}$。

$$
\mathrm{contribution}(s, c^*, x) = \omega_s \cdot \sigma_s
$$

其中:
- $\omega_s$ — source $s$ 对 raw_confidence 的偏导数近似(数值差分:把 $s$ 路径的证据 mask 掉后 raw_confidence 的下降量)
- $\sigma_s$ — source $s$ 的 `source_confidence`(感知 vs 想象的把握感本身)

归一化:

$$
\mathrm{credit}(s) = \frac{\mathrm{contribution}(s, c^*, x)}{\sum_{s' \in \mathcal{S}} \mathrm{contribution}(s', c^*, x) + \epsilon}
$$

### 3.3 Negative feedback delta(用户说"不对")

$$
\Delta w_s = -\eta \cdot \mathrm{credit}(s) \cdot |\text{error\_signal}|
$$

`vision_sensor.feedback_eta = 0.15` @experimental。

### 3.4 隔离保证(v1a RL-19v1a-S03 升级)

| RL | 描述 |
|---|---|
| RL-19v1b-C2-01 | $\Delta w_s$ 仅对**对决策有贡献**的 source 路径生效,$\mathrm{credit}(s) = 0$ 的 source **不**被削弱 |
| RL-19v1b-C2-02 | Audit 模式 evaluator-oracle 可以**覆盖** contribution 计算,但必须在 metadata 留 `feedback_mode: "audit_oracle"` 痕迹;runtime 模式必为 `feedback_mode: "auto_contribution"` |
| RL-19v1b-C2-03 | 反馈不污染**不同 SA**(隔离),除非该 SA 也在 $\mathcal{S}(c^*, x)$ 内 |

### 3.5 Gate 重写(替换 v1a §9 feedback gates)

| Gate | 描述 |
|---|---|
| G-19v1b-Fb-01 | Audit 模式标 source 后,对应 source 路径权重统计降低(直接复用 v1a 测) |
| G-19v1b-Fb-02 | Runtime 模式 contribution 计算正确性:把某 source 完全 mask 后 raw_confidence 至少下降 $\mathrm{credit}(s) \cdot 0.5$ |
| G-19v1b-Fb-03 | 同图二次输入 → `confidence_score` 严格降低 ≥ 0.1 |
| G-19v1b-Fb-04 | 反馈隔离测试:某 SA 不在 $\mathcal{S}$ 内,其权重不动 |

---

## 4. C3 — Novelty 拆 object / context

### 4.1 替换 v1a §4.7 主因子

**v1a 旧版**:
$$
\nu(x) = 1 - \exp(-\gamma \cdot \min_c d(\mathbf{f}_x, \mathbf{p}_c))
$$

(在 7807 维全空间算 → V0 raw tiles 让背景陌生度污染 object 判断)

**v1b 新版** — 按通道家族分拆:

$$
\nu_{\mathrm{object}}(x) = 1 - \exp\left(-\gamma_{\mathrm{obj}} \cdot \min_c d_{\mathrm{obj}}(\mathbf{f}_x^{\mathrm{obj}}, \mathbf{p}_c^{\mathrm{obj}})\right)
$$

$$
\nu_{\mathrm{context}}(x) = 1 - \exp\left(-\gamma_{\mathrm{ctx}} \cdot \min_c d_{\mathrm{ctx}}(\mathbf{f}_x^{\mathrm{ctx}}, \mathbf{p}_c^{\mathrm{ctx}})\right)
$$

通道分组:
- **object channel set** $\mathcal{C}_{\mathrm{obj}}$ = `{V1 obj_region, V2 obj_region, V3 obj_region, V4 obj_region, V5, V6, V7}`(诊断主体的通道)
- **context channel set** $\mathcal{C}_{\mathrm{ctx}}$ = `{V0 retinal pyramid (除 focus patch), V1/V2/V3 bg_region, V8 layout, V9 fg/bg KL}`

### 4.2 接入 tier_map(替换 v1a §4.7 tier_map)

```
tier_map(raw_conf, nu_object):
    raw_tier =
      "firm"   if raw_conf >= tau_firm
      "soft"   if raw_conf >= tau_soft
      "ambig"  if raw_conf >= tau_ambig
      "no_call" otherwise

    # 只 ν_object 降级
    if nu_object >= novelty_strong:
        tier = downgrade_one(raw_tier)

    if nu_object >= novelty_extreme and Pi < 0.2:
        tier = "no_call"
    return tier
```

### 4.3 ν_context 不进 tier_map,改驱动好奇心 / 再注视

```
attention_pressure_bonus = lambda_curiosity · nu_context
re_fixation_pressure    = lambda_fixation  · nu_context
```

`vision_sensor.lambda_curiosity = 0.4`、`lambda_fixation = 0.3` @experimental。

### 4.4 新常量

```yaml
vision_sensor:
  gamma_object: 1.0                # @experimental
  gamma_context: 0.5               # @experimental
  lambda_curiosity: 0.4            # @experimental
  lambda_fixation: 0.3             # @experimental
```

### 4.5 新 Gate

| Gate | 描述 |
|---|---|
| G-19v1b-C3-01 | 同主体 + 不同背景对(果园苹果 vs 桌面苹果),decision_tier 一致(背景不污染) |
| G-19v1b-C3-02 | OOD object + 常见背景 → tier 降级 |
| G-19v1b-C3-03 | $\nu_{\mathrm{context}}$ 高时 attention_pressure_bonus 抬升(单测) |

---

## 5. C4 — Error Taxonomy 操作化

### 5.1 v1a §8 错误分类必经两路之一(替换主观判定)

**路径 A — Blind external evaluator**:
- evaluator 看图 + AP 输出 + decision_tier + confidence_score
- evaluator **不**看 filename / hidden label / metadata
- evaluator 给出 `human_plausible: bool` 与 `illusion_like: bool`

**路径 B — Cue-based audit rule**(机器化判定):

```
classify_error(sample):
    if evaluator_label_accessed or used_filename or used_metadata:
        return "nonhuman_artifact_error"
    if render_mode_conflict_detected:
        return "source_confusion_error"

    misleading_cue_count = count_strong_cues_supporting_predicted(sample)
    competitor_gap_small = (mu < margin_small_threshold)
    high_novelty         = (nu_object > novelty_strong)

    if decision_tier in {"soft", "ambig"}:
        if misleading_cue_count >= 2 or competitor_gap_small or high_novelty:
            return "human_plausible_soft_error"
        return "uncategorized_soft_error"  # 仍然失败,但不被赦免

    if decision_tier == "firm":
        if misleading_cue_count >= 3 and competitor_gap_small:
            return "human_plausible_illusion_error"
        return "nonhuman_firm_wrong_error"  # 红线 = 0

    if decision_tier == "no_call":
        if competitor_gap_small or high_novelty or misleading_cue_count >= 2:
            return "human_uncertainty"        # 合理
        return "uncertainty_underreach"
```

### 5.2 新常量

```yaml
vision_sensor:
  margin_small_threshold: 0.25         # @structural - mu < 0.25 视为 "竞争紧"
  misleading_cue_strong_h: 0.6         # @structural - 单线索 h >= 0.6 视为 "强"
```

### 5.3 新红线

| RL | 描述 |
|---|---|
| RL-19v1b-C4-01 | `human_plausible_*` 不得仅因预测错就标(必走 §5.1 路径 A 或 B) |
| RL-19v1b-C4-02 | `nonhuman_firm_wrong_error` 与 `nonhuman_artifact_error` / `source_confusion_error` 必为 0(替换 v1a §8 illusion_firm_wrong_max=1 中误绕过的口子) |
| RL-19v1b-C4-03 | Final Report 必须列出每张测试图的 `error_route ∈ {evaluator_A, audit_rule_B}` |

---

## 6. C5 — V0 / A0 Fast Path vs Audit Path

### 6.1 路径分离

```
receptor_fast_path:
  per tick, bounded
  computes:
    - V0 global low-res tiles (8x8 = 192 dim, 1ms 量级)
    - V1 RGB hist on S0/S1 only (72 dim)
    - V4 HOG-lite global only (8 dim)
    - V8 layout summary (5 dim)
  updates compact StateItem.real_energy + minimal channel_signature
  NO rendering

reconstruction_audit_path:
  on demand or replay tick
  computes:
    - full V0 retinal pyramid (4544 dim)
    - all V1..V9 at all S0..S4 scales (3263 dim)
    - calls R_sketch / R_proto on demand
  may queue if budget exhausted
```

### 6.2 Latency gates

```yaml
vision_sensor:
  fast_path_p95_ms: 5                  # @structural - per tick budget
  audit_path_max_concurrent: 4         # @structural - queue size
  audit_path_drop_oldest: true         # @structural - 队满丢最老
```

| Gate | 描述 |
|---|---|
| G-19v1b-C5-01 | 12 张 audit 图 fast_path p95 < 5ms |
| G-19v1b-C5-02 | audit_path 不阻塞 dialogue tick loop(实测) |
| G-19v1b-C5-03 | 队满时 fast_path 仍正常,audit 优雅退化 |

听觉对称:

```yaml
audio_sensor:
  fast_path_p95_ms: 8                  # @structural - 听觉 frame 较密,稍宽
  audit_path_max_concurrent: 2         # @structural
```

### 6.3 红线

| RL | 描述 |
|---|---|
| RL-19v1b-C5-01 | dialogue tick loop / state pool main update **不得**等待 audit_path |
| RL-19v1b-C5-02 | inner_picture 渲染只能走 audit_path,不能阻塞 fast_path |

---

## 7. C6 — 19.3a Stratified K-Fold(替换固定 split)

### 7.1 v1a §5.1 替换

**v1a 旧版**:
| Phase 19.3a | 用户真实照片 train split (~7 张) | held-out (~5 张) |

**v1b 新版** — Stratified Leave-One-Out / k-fold:

设核心类 $\mathcal{C} = \{\text{apple}, \text{orange}, \text{banana}\}$,每类至少 3 张(真实苹果/橙子/香蕉各 3-4 张),变体类(绿橙、黄绿苹果)各 1 张。

```
for each test_image in user_image_set:
    train_set = user_image_set \ {test_image}
    require: each core class still has >= 2 train images
    if not satisfied:
        skip and report degenerate fold
    train prototypes on train_set
    compute decision on test_image
    record decision_tier, confidence_score, error_taxonomy
aggregate across 12 folds → Recall@1 / Recall@3 / per-class accuracy / illusion rate
```

变体类(绿橙、黄绿苹果)作为 leave-one-out 测试时,**变体仍可作 train** — 这才能测出 AP 是否学到"橙子可以是绿的"这种延展。

### 7.2 H0 / λ / diagnosticity 训练集约束

| RL | 描述 |
|---|---|
| RL-19v1b-C6-01 | $h_0^{(k)}$、$\lambda_k$、$\delta_k^{(c)}$ 在每个 fold **只**用 train_set 拟合,**不**用 test_image |
| RL-19v1b-C6-02 | 不允许"在 12 张总集上拟合一次,然后做 LOO" |
| RL-19v1b-C6-03 | Final Report 必须用 "diagnostic" 措辞,不得用 "benchmark" / "validated generalization" |

### 7.3 Gate 重写

| Gate | 描述 |
|---|---|
| G-19.3a-v1b-01 | Stratified LOO 12 折跑完 |
| G-19.3a-v1b-02 | 每折满足 ≥ 2 train per core class,否则标 degenerate |
| G-19.3a-v1b-03 | aggregate Recall@3 ≥ 0.6(允许少量 degenerate fold 扣分) |
| G-19.3a-v1b-04 | nonhuman_firm_wrong_error + nonhuman_artifact_error + source_confusion_error = 0(所有折) |
| G-19.3a-v1b-05 | illusion_firm_wrong ≤ 1(所有折累计) |

19.3b clean-card → real-photo transfer 不变(已固定:train = 18.0 clean cards,test = 12 张全用户图)。

---

## 8. C7 + S3 — Recall Score 归一化 + cooccurrence 来源锁死

### 8.1 v1a §7 公式归一化

**v1a 旧版**(可能超 1):
```
recall_score(c) = Π + α_part·part_overlap + α_shape·shape_overlap + α_cooccur·cooccur - α_conflict·source_conflict
```

**v1b 新版**(归一 [0,1]):

$$
\mathrm{raw\_recall}(c|x) = \mathrm{Pi}(c|x) + \alpha_{\mathrm{part}} \cdot \mathrm{part\_overlap}(c, x) + \alpha_{\mathrm{shape}} \cdot \mathrm{shape\_overlap}(c, x) + \alpha_{\mathrm{cooccur}} \cdot \mathrm{cooccur}(c, x) - \alpha_{\mathrm{conflict}} \cdot \mathrm{source\_conflict}(c, x)
$$

$$
\mathrm{recall\_score}(c|x) = \mathrm{sigmoid}\left(\kappa_{\mathrm{recall}} \cdot (\mathrm{raw\_recall} - \mathrm{recall\_midpoint})\right)
$$

`vision_sensor.kappa_recall = 4.0`、`recall_midpoint = 0.5` @experimental。归一化后 $\in (0,1)$。

权重 α 归一化约束(避免一个权重压死所有信号):

$$
\alpha_{\mathrm{part}} + \alpha_{\mathrm{shape}} + \alpha_{\mathrm{cooccur}} \leq 1, \quad \alpha_{\mathrm{conflict}} \in [0, 0.5]
$$

(满足:0.3 + 0.2 + 0.15 = 0.65 ≤ 1 ✓,conflict 0.4 ≤ 0.5 ✓)

### 8.2 `learned_cooccurrence` 来源锁死

```python
@dataclass(frozen=True)
class CooccurrenceMatrix:
    source: str  # @structural - 必为 "training_sdpl_only"
    matrix: dict[tuple[str, str], float]
    last_updated_tick: int

# 在 cooccurrence_update 路径中:
def update_cooccurrence(c, x, source_tag):
    if source_tag != "training_sdpl_only":
        raise RuntimeError(f"learned_cooccurrence cannot accept source {source_tag}")
    ...
```

### 8.3 新红线

| RL | 描述 |
|---|---|
| RL-19v1b-C7-01 | `learned_cooccurrence` 任何写入必须 `source_tag == "training_sdpl_only"`,否则 raise |
| RL-19v1b-C7-02 | Held-out evaluator sidecar 路径**不得** import / 调用 cooccurrence_update |
| RL-19v1b-C7-03 | Phase 19.3a / 19.3b 测试时 evaluator sidecar 进程 / 模块隔离,通过文件 IO 单向给 audit report |
| RL-19v1b-C7-04 | α 权重和 ≤ 1(运行时常量校验,启动时 assert) |

### 8.4 新 Gate

| Gate | 描述 |
|---|---|
| G-19v1b-C7-01 | recall_score ∈ (0, 1) 在 12 张图全部测试中 |
| G-19v1b-C7-02 | cooccurrence raise 测试:伪 source_tag 调用 raise |
| G-19v1b-C7-03 | evaluator sidecar 路径不写 cooccurrence(import 审计) |
| G-19v1b-C7-04 | 启动时 α 权重和断言通过 |

---

## 9. 修订后 Deliverable Gates 增量表

### Phase 19.0 v1b 增量(在 v1a §10 之上加)

| Gate |
|---|
| G-19.0v1b-15 confidence_score 与 decision_tier 在 SA metadata 分离(RL-19v1b-C1-01 测) |
| G-19.0v1b-16 V0 fast_path / audit_path 拆分,延迟 gate 通过 |
| G-19.0v1b-17 cooccurrence 写入 source_tag 校验 |
| G-19.0v1b-18 retrieval 权重和 ≤ 1 启动断言 |
| G-19.0v1b-19 fast_path p95 < 5 ms on 12 张 audit 图 |

### Phase 19.2 v1b 增量(在 v1a §10 之上加)

| Gate |
|---|
| G-19.2v1b-11 raw_confidence 公式包含 μ,验单测 |
| G-19.2v1b-12 ν_object / ν_context 拆分,通道分组单测 |
| G-19.2v1b-13 tier_map 仅用 ν_object,ν_context 进 attention pressure |
| G-19.2v1b-14 error_route ∈ {evaluator_A, audit_rule_B},每条测试用例标记 |
| G-19.2v1b-15 G-19v1b-Fb-02 自动 contribution 正确性 |

### Phase 19.1 / 19.4 听觉对称增加 fast/audit path + ν_object/ν_context 听觉版

听觉版 ν_object = A0 focus patch + A1+A6 (MFCC+F0) 上的 novelty;ν_context = A0 整段 + A5+A7+A8(背景节奏 / 包络 / 谱对比)。

### Phase 19.3a v1b(替换 v1a §10 19.3a)

(见 §7.3,5 条 Gate)

### Phase 19.5 v1b(替换 v1a §9 gates)

(见 §3.5,4 条 Gate)

---

## 10. 落地次序锁死

```
Phase 19.0 (visual receptors + R_sketch/R_proto + fast/audit path + V0/V1..V9)
        ↓
Phase 19.2 (confidence formula with raw_confidence + decision_tier + nu_object/nu_context)
        ↓
Phase 19.3a (stratified LOO real-photo train/heldout + error taxonomy operationalized)
        ↓
Phase 19.3b (clean-card → real-photo transfer,失败定性为发展阶段限制)
        ↓
Phase 19.1 (audio receptors + R_aud,sketch/proto + fast/audit path + A0/A1..A8)
        ↓
Phase 19.4a (audio stratified LOO real-audio train/heldout)
        ↓
Phase 19.4b (synthetic → real-audio transfer)
        ↓
Phase 19.5 (source-aware feedback runtime contribution gate)
```

---

## 11. 自查 + 红线总结

v1 + v1a + v1b 合读后,Codex 开工前必检清单:

- [ ] feature_vector_dim 视觉 7807 / 听觉 20179 已写入 apv3_constants.yaml
- [ ] V0 fast_path / audit_path 分离实现
- [ ] R_sketch / R_proto 双模式,共享 primitives
- [ ] 每个 inner_picture / inner_voice_sketch SA 携带强制 metadata(epistemic_source / render_mode / input_trace_hash)
- [ ] raw_confidence 与 decision_tier 在 metadata 双存
- [ ] ν 拆 object / context
- [ ] error_route 走 evaluator_A 或 audit_rule_B 之一,无主观判定
- [ ] cooccurrence source_tag 锁 training_sdpl_only,evaluator sidecar 隔离
- [ ] α 权重和 ≤ 1 启动断言
- [ ] 19.3a 走 stratified LOO,h0/λ/δ 每折单独拟合
- [ ] feedback 走 auto_contribution(runtime)或 audit_oracle(测试)
- [ ] fast_path p95 < 5 ms
- [ ] 真名零命中(v1 + v1a + v1b 三份文件全 grep)

---

## 12. 路线图修订(增量)

v1b 落实后,Phase 19 总流程图:

```
v1 (4 设计稿 + roadmap)
    +
v1a Errata (拟人 + 工程闭合)
    +
v1b Micro Errata (实现接口缝隙闭合)
    =
开工就绪
```

总 8 个子阶段:**19.0 → 19.2 → 19.3a → 19.3b → 19.1 → 19.4a → 19.4b → 19.5**。

---

## 13. 边界

- v1b 不替换 v1/v1a,叠加。三份合读为正本。
- v1b 不引入新 marker_kind / 不破坏 v14 marker_kinds cap = 20
- v1b 不接入实时摄像头 / 麦克风 / TTS / LLM
- 12 张图仍为内部诊断集合,LOO 后报告写 "diagnostic" 不写 "benchmark"
- 听觉 audit 集仍待银子老师补充 12 段 CC0/PD 音频

---

## 14. 署名

- 原架构设计:银子老师(笔名)
- 数学修订 + v1b errata:Claude (Anthropic) 在银子老师方向 + 吸收 Codex v1/v2/v1a 全部 14 项审阅点后产出
- 落地实现:Codex 在 v1b 通过最终复核后启动 Phase 19.0

End of Phase 19 v1b Micro Errata.
