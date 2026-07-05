# APV3.0 Phase 19.7 Design — Diagnostic-First Recognition: Three-Layer Vector Wired, Channel-Weighted Voting, Foreground Subject Isolation, Multi-Fixation Subject Probe

Date: 2026-06-19
Author: Claude(架构),银子老师(风格定调与最终签收)
Status: 设计稿(全新 Phase 19.7,Phase 19 之后的根治补丁),叠加在 v1 / v1a / v1b / v1c / v1c-audio / v1d / v1e 上
Trigger:
1. 银子老师亲手测 Codex Phase 19 落地的泛化效果 — 12 张真实图 9 正 3 错,但**所有 top score 0.82-0.965,margin 0.003-0.063,全 ambig**,说明系统在"猜",没有真诊断性
2. Codex 自己识别"Phase 19.7 真实照片主体诊断性修复"方向对,但**没说到根本** — 根因是 19.3 探测脚本走全维 cosine,**绕开了 v1d 设计的三层向量库 + 拟人 Conf 公式**,而 v1d RL-19v1d-Recog-01 明令禁止全维 cosine
3. 银子老师要"近乎 100% 拟人 + 真实泛化",当前架构已就绪,只缺**真正接通**的诊断性识别管线
License intent: AGPL-3.0-or-later
Real name handling: 全文件 grep 真名 = 0

---

## 0. 这一份做什么(一句话)

**根因修复**:Phase 19 v1-v1e 设计了完美的三层向量库 + 拟人 Conf 架构,但 Codex 实现的 19.3 视觉 probe **绕开了它**,直接走 27842 维 cosine。Phase 19.7 把识别管线**真正接通** v1d 设计的 C 召回 → B 召回 → 通道加权诊断打分 → 拟人 Conf 公式 → 4 档输出,并补 Codex 19.7 提的前景主体分离 + 多 fixation 主体扫描 + 通道 ablation 审计,从根本解决"score 都很高但 margin 极小"的非诊断问题。

---

## 1. 根因诊断(数据驱动,不只是审阅)

### 1.1 银子老师 12 张实测原始数据

```
真实苹果1.jpeg → banana 0.820 / apple 0.815  (margin 0.005, ambig, 错)
真实苹果2.jpg  → apple 0.949 / orange 0.941  (margin 0.008, ambig, 对)
真实苹果3.jpeg → apple 0.954 / orange 0.952  (margin 0.003, ambig, 对)
真实香蕉1.webp → banana 0.946 / orange 0.914  (margin 0.032, ambig, 对)
真实香蕉2.webp → banana 0.843 / orange 0.830  (margin 0.013, ambig, 对)
真实香蕉3.webp → banana 0.879 / orange 0.816  (margin 0.063, soft,  对) ← 唯一 soft
真实香蕉4.webp → banana 0.965 / orange 0.953  (margin 0.012, ambig, 对)
真实橙子1.webp → orange 0.937 / apple 0.927   (margin 0.010, ambig, 对)
真实橙子2.webp → orange 0.855 / apple 0.836   (margin 0.019, ambig, 对)
真实橙子3.jpeg → orange 0.923 / apple 0.913   (margin 0.009, ambig, 对)
绿色橙子1.webp → banana 0.833 / orange 0.822  (margin 0.011, ambig, 错)
黄绿苹果1.jpg  → orange 0.896 / banana 0.877  (margin 0.019, ambig, 错)
```

### 1.2 数据告诉我

| 现象 | 含义 |
|---|---|
| 全部 score 0.82-0.965 | 27842 维 cosine 对水果照片**几乎饱和** — 任何两张水果照片相似度都 > 0.8 |
| Margin 0.003-0.063 | top-1 与 top-2 几乎**重合** — 系统在"五五开里偶尔猜对" |
| 9 正 3 错也只是 margin 平均略偏 0.014 | 与噪音同量级 — 9 张"对"和 3 张"错" **统计意义上是同一分布** |
| 全 ambig + 0 firm | 拟人公式在压制错答案(达成 v1a G-19.3a-04)但**视觉通道本身几乎无诊断性** |
| 唯一 soft(真香蕉 3)margin 0.063 | 这是这套系统目前能"敢说像是"的真正水位 |

### 1.3 探测脚本的代码层根因(直接读 [scripts/reports/render_phase19_generalization_effect_probe.py:60](scripts/reports/render_phase19_generalization_effect_probe.py#L60))

```python
score = cosine_similarity(q_vec, train_vec)        # ← 全 27842 维 cosine
if score > label_scores.get(label, -1.0):
    label_scores[label] = score                     # ← 同类取 max(不是 noisy-OR)
ranked = sorted(label_scores.items(), ...)
top, top_score = ranked[0]                          # ← 直接 argmax
```

**违反 v1d RL-19v1d-Recog-01**:"recognize() 不允许 numpy.linalg.norm... 只允许 channel-wise distance + noisy-OR + B 召回的 K × N 拟人 Conf"。

也就是说,Phase 19 substrate / foveated / 三层库 schema 都落了,但**识别管线没真正接通**,探测脚本走了快捷方式。这不是设计错,是**实现断层**。

### 1.4 Codex 19.7 方向 vs 我的判断

| Codex 19.7 提议 | 我的裁定 |
|---|---|
| 前景主体分离 | **对,必须**(但需要数学化,不能空说) |
| 多 fixation 主体扫描 | **对,但要绑死 saccade 路径** |
| 部件/纹理/轮廓分通道投票 | **对,这是核心** — 但**不止投票**,要走真正的诊断性公式 |
| Channel ablation 审计 | **对,但要分清"调试 ablation" vs "决策 ablation"** |

Codex 没说到的根本:**三层向量库已经设计好了但 19.3 探测脚本没用**。Phase 19.7 必须从把识别管线接通开始,不是加新组件。

---

## 2. Phase 19.7 五件事(按必要性排序)

### A. **接通**:把 v1d 三层库识别管线**真正用进**视觉 probe
### B. **公式根治**:channel-weighted diagnostic noisy-OR(替全维 cosine)
### C. **主体分离**:前景主体掩码 + 主体 vs 背景区分通道
### D. **多 fixation 主体扫描**:6 fixation 在主体内部 + 1 fixation 比较背景
### E. **通道 ablation 审计**:每张测试图产 9 通道贡献分解表

---

## 3. A. 接通 — 三层库识别管线接进视觉 probe

### 3.1 新识别函数(替换 19.3 探测脚本的 cosine 直查)

```python
def visual_recognize_v1_7(query_image_path: Path, *,
                           layer1: Layer1PerceptVectorStore,
                           layer2: Layer2PartPrototypeStore,
                           layer3: Layer3ConceptPrototypeStore,
                           ) -> RecognitionResult:
    """
    Phase 19.7 正式识别管线(完全按 v1d §5 设计)。
    禁止全维 cosine,禁止全维 L2。
    """
    # 1. 富感受器 + foveated 多 fixation 累积
    canvas = SensoryCanvas.empty()
    for fix_idx in range(N_fixations):
        fix_xy = choose_next_fixation(canvas, mask_hypotheses=...)
        trace  = extract_visual_audit_path_v2(query_image_path, focus_xy=fix_xy)
        canvas = update_sensory_canvas(canvas, trace, tick=fix_idx)

    # 2. C 召回 — Layer-2 part 倒排查
    query_signature_256 = pca_quantize_signature(canvas.summary_feature)
    candidate_parts = layer2.match_parts(query_signature_256, top_k_per_channel=8)
    candidate_concepts = layer3.lookup_by_parts(candidate_parts, top_k_concept=5)

    if not candidate_concepts:
        # 冷启动:spawn tentative concept (v1e §7)
        tentative = layer3.spawn_tentative_concept(initial_part_associations=candidate_parts)
        return RecognitionResult(top_concept=tentative,
                                 decision_tier="ambig",
                                 raw_confidence=0.4,
                                 source="tentative_concept",
                                 output_text=styled_corpus_render("像是某种" + parts_to_descriptor(candidate_parts)))

    # 3. B 召回 — 在 candidate concepts 的 Layer-1 episodics 上算分场拟人 Conf
    concept_scores = []
    for concept in candidate_concepts:
        episodics = layer1.episodics_for(concept, top_k=10)
        # 对每个 candidate concept 算 §4 的通道加权诊断 noisy-OR Conf
        c_conf = compute_channel_diagnostic_confidence(canvas, concept, episodics)
        concept_scores.append((concept, c_conf))

    # 4. 拟人 Conf 公式 + tier_map (v1d §5.2 + v1b §2.1)
    ranked = sorted(concept_scores, key=lambda x: x[1].raw_confidence, reverse=True)
    top, top_conf = ranked[0]
    second_conf = ranked[1][1].raw_confidence if len(ranked) > 1 else 0.0

    raw_confidence = top_conf.raw_confidence  # 已含 Π·Γ·Q·μ
    decision_tier  = tier_map(raw_confidence, nu_object=top_conf.nu_object)

    return RecognitionResult(
        top_concept=top,
        decision_tier=decision_tier,
        raw_confidence=raw_confidence,
        all_concept_scores=ranked,
        channel_ablation_table=top_conf.channel_ablation,
        source="three_layer_recognition",
        output_text=styled_corpus_render(decision_tier, top.label),
    )
```

### 3.2 红线

```
RL-19.7-A01: visual_recognize_v1_7 不调用 cosine_similarity(grep test)
RL-19.7-A02: 不调用 numpy.linalg.norm 在 query_feature_full vs prototype_feature_full
RL-19.7-A03: 必须经过 C 召回 → B 召回两阶段,直接 ranked.argmax 是 fail
RL-19.7-A04: candidate_concepts 为空时必须 spawn tentative,不允许 raise / return None
```

---

## 4. B. 公式根治 — Channel-Weighted Diagnostic Noisy-OR

### 4.1 替换全维 cosine 为 9 通道分块诊断打分

把单一标量 score 改成 9 通道(V1..V9,V0 用于 source_quality 不进诊断)分块的诊断证据向量:

$$
\mathbf{e}^{(c)}(x) = (e_1^{(c)}, e_2^{(c)}, \dots, e_9^{(c)})
$$

每通道证据:

$$
e_k^{(c)}(x) = \max\left(0, \delta_k^{(c)} \cdot (\mathrm{sim}_k^{(c)}(x) - h_0^{(k)})\right)
$$

其中:
- $\mathrm{sim}_k^{(c)}(x)$ — **该通道**上 query 与 concept 原型的相似度
  - V1 RGB hist: $1 - \chi^2$ 距离
  - V2 HSV hist: $1 - \chi^2$ 距离
  - V3 LBP: $1 - \chi^2$ 距离 / 30 维
  - V4 HOG: cosine on 8-dim per region,平均
  - V5 radial gradient: cosine on 16-dim
  - V6 shape geometry: 1 - normalized euclidean on 5-dim
  - V7 part overlap: Jaccard on part_uuids
  - V8 spatial layout: 1 - normalized euclidean on 5-dim
  - V9 fg/bg KL: 1 - normalized euclidean on 3-dim
- $\delta_k^{(c)}$ — nearest-negative 诊断系数(v1a §4.2 + v1e B5)
- $h_0^{(k)}$ — 通道 $k$ 的 baseline,**离线**在训练集上估(每通道独立)

### 4.2 Thresholded top-m noisy-OR

$$
\Pi(c|x) = 1 - \prod_{k \in \mathrm{TopM}(e^{(c)})} (1 - e_k^{(c)}(x))
$$

`vision_sensor.recognition_top_m = 4` @structural — 只取每 concept 上证据最强的 4 个通道,**避免**所有 9 通道弱证据堆出假高 score。

### 4.3 关键性质 — 解决"score 都 0.9+ 但 margin 0.005"

| 场景 | 旧全维 cosine | 新通道诊断 |
|---|---|---|
| 真苹果 vs 苹果原型 | 0.949(高,因为全图统计相似) | $\Pi$ 高,因为 V2 红色诊断 + V6 圆度诊断都强 |
| 真苹果 vs 香蕉原型 | 0.941(也高,因为水果背景相似) | $\Pi$ 低,因为 V6 形状诊断、V4 边缘诊断不命中 |
| Margin | 0.008(基本不可区分) | 显著拉开(预期 0.3-0.5) |

通道分块的本质:**让"全图相似但部件不同"两张图在 score 上区分开**,这正是 v1d 的设计意图。

### 4.4 Coherence + Margin + Quality + Novelty(继续按 v1d §5.2)

$$
\mathrm{raw\_confidence}(c|x) = \Pi(c|x) \cdot \Gamma(c|x) \cdot Q(x) \cdot \mu(c|x)
$$

各项:见 v1a §4.4 (active-cue Coherence) + v1a §4.6 (shifted margin) + v1a §4.5 (Source quality) + v1d §5.2(整合)。

### 4.5 红线

```
RL-19.7-B01: 识别函数返回的 raw_confidence 必须可逐通道分解(audit 表)
RL-19.7-B02: top_m noisy-OR 必须取 top-4,不允许全 9 通道直接 AND
RL-19.7-B03: 同 concept 在 12 张测试图上 $\delta_k^{(c)}$ 必须一致(离线表)
```

---

## 5. C. Foreground Subject Isolation

### 5.1 复用 v1a §3.3 multi-hypothesis mask

Phase 19 v1a 已经数学化了 multi-hypothesis mask(4 假设 + segmentation_confidence)。Phase 19.7 把它**真正接进**通道计算:

```python
def extract_channel_for_subject_only(rgb, edge, channel_kind, mask_hypotheses):
    """
    每通道分两个版本:
      V1_subject = V1 在主体掩码内的 hist
      V1_background = V1 在主体外的 hist
      
    诊断打分时,V1_subject 主用,V1_background 仅用于 V9 fg/bg KL
    """
    best_mask = max(mask_hypotheses, key=lambda m: m.segmentation_confidence)
    subject_pixels = rgb[best_mask.foreground]
    background_pixels = rgb[best_mask.background]
    ...
```

### 5.2 主体加权 vs 背景加权

```yaml
recognition:
  subject_weight: 0.85          # @experimental - 主体通道证据权重 85%
  background_weight: 0.15       # @experimental - 背景通道证据权重 15%
  use_subject_only_threshold: 0.6   # @experimental - segmentation_confidence > 0.6 才用 subject-only
                                    # 否则降级用全图(rejection-resilient)
```

### 5.3 关键效果

苹果照片背景是桌面 / 树叶 / 木板等(差异极大),如果主体分离前算 V1 RGB hist,背景颜色会盖过苹果本身的红色诊断。主体分离后,V1 主要算红色 → 与香蕉(黄)、橙子(橙)显著分开。

### 5.4 与 Codex 19.7 提议的"前景主体分离"接齐

Codex 提议对的,但没说"用 v1a multi-hypothesis 已有结果"。这里明确接通。

---

## 6. D. Multi-Fixation Subject Probe

### 6.1 6 + 1 fixation 策略

- **6 fixation 在主体内**(从主体掩码中按 saliency × uncertainty 选,IOR 已注视位置压制)
- **1 fixation 在背景**(对比 V9 fg/bg KL 提升诊断)
- 7 fixation 后,SensoryCanvas 累积形成 query feature

继承 v1c §5.1 saccadic scanning,但显式偏向主体。

```yaml
recognition:
  fixations_in_subject: 6       # @structural
  fixations_in_background: 1    # @structural
  fixation_subject_bias: 0.85   # @experimental - 落在主体内概率
```

### 6.2 为什么 6 fixation 在主体

人类看苹果时,眼睛会扫:整体 → 顶部(看果柄)→ 底部(看果蒂)→ 中部颜色 → 表面纹理 → 边缘形状 → 偶尔扫一眼周围。这是拟人多 fixation 主体扫描的根据。

### 6.3 多 fixation 后特征聚合

聚合方式 = SensoryCanvas 累积公式(v1c §4)— 通过 confidence-weighted Bayesian blending,而不是简单平均。

### 6.4 红线

```
RL-19.7-D01: 7 fixation 计划在调度日志中必须可审计(每 fixation 的 saliency / uncertainty / chosen_xy)
RL-19.7-D02: 至少 5 个 fixation 必须落在主体掩码内(否则探测无效)
```

---

## 7. E. Channel Ablation Audit

### 7.1 每张测试图产 9 通道贡献分解表

对每张测试图,识别完成后产以下 audit 行(写入 RecognitionResult):

```python
@dataclass
class ChannelAblationRow:
    concept_uuid: str
    label: str
    raw_confidence_full: float            # 全部通道
    channel_contribution: dict[str, float]  # 移除某通道后 raw_confidence 的下降幅度
    # e.g. {"V1": 0.05, "V2": 0.15, "V3": 0.02, "V6": 0.20, "V7": 0.10, ...}
    most_diagnostic_channels: list[str]   # 排序后 top-3
    least_diagnostic_channels: list[str]  # 排序后 bottom-3
```

`channel_contribution[k]` 通过 v1e B5 的 local ablation 算:

$$
\mathrm{contribution}_k = \mathrm{raw\_confidence}(c|x; \text{all channels}) - \mathrm{raw\_confidence}(c|x; \text{without channel } k)
$$

### 7.2 关键诊断 gate

**Gate 19.7-E01**:对 12 张测试图,top-3 most_diagnostic_channels 必须**与人类视觉直觉一致** —
- 苹果 → V2 (HSV 红色) + V6 (圆度) + V7 (果柄部件)
- 香蕉 → V6 (长条形) + V2 (黄色) + V4 (弯曲边缘)
- 橙子 → V2 (橙色) + V6 (圆度) + V3 (纹理)

如果 top-3 是 V0 全图 + V8 layout + V9 fg-bg,说明系统在用"位置 + 背景"判断,不是部件,需要回 Phase 19.0a 修。

### 7.3 区分调试 ablation 与决策 ablation

**调试 ablation**(audit only):用于 Final Report 展示 — 9 通道哪个贡献大,人能看懂
**决策 ablation**(继承 v1e §5):用于 Phase 19.5 学习信号 local_error — 计算 $L_i$,top-K=16 限算

不能混。

### 7.4 红线

```
RL-19.7-E01: channel_contribution 表必须为每张测试图产出
RL-19.7-E02: top-3 most_diagnostic 与人类直觉对照表(Phase 19.7 完成时银子老师签收)
RL-19.7-E03: 调试 ablation 不允许写回 Layer-3 weights,只 audit
```

---

## 8. 期待效果(给 Phase 19.7 落地后的预期)

跑同样 12 张测试图,期待:

| 测试图 | top-1 (期待) | raw_conf (期待) | margin (期待) | tier (期待) |
|---|---|---:|---:|---|
| 真实苹果 1-3 | apple | 0.60-0.75 | 0.25-0.40 | soft 或 firm |
| 真实橙子 1-3 | orange | 0.55-0.70 | 0.20-0.35 | soft 或 firm |
| 真实香蕉 1-4 | banana | 0.65-0.80 | 0.30-0.45 | soft 或 firm(V6 形状强诊断) |
| 绿色橙子 1 | orange | 0.40-0.55 | 0.10-0.20 | soft (拟人,变体) |
| 黄绿苹果 1 | apple | 0.40-0.55 | 0.10-0.20 | soft (拟人,变体) |

**核心 gate 改写**:
- $\geq 10/12$ 正确(从 9/12 提升)
- $\geq 6/12$ 进入 soft 或 firm(从 1/12 soft 提升)
- 错的 ≤ 2 张,且全部 ambig 不进 firm(继承 v1a G-19.3a-04)
- Margin 平均 ≥ 0.20(从 0.014 提升,提升 ~14×)
- 通道 ablation top-3 与人类直觉对照表 ≥ 9/12 一致

---

## 9. Deliverable Gates (Phase 19.7 — 18 条)

| Gate |
|---|
| G-19.7-01 visual_recognize_v1_7 实现并接进 19.3 视觉 probe |
| G-19.7-02 cosine_similarity / numpy.linalg.norm grep 测在新 probe 路径不命中 |
| G-19.7-03 9 通道分块诊断 noisy-OR 实现 |
| G-19.7-04 $\delta_k^{(c)}$ 离线表 + $h_0^{(k)}$ baseline 表生成 |
| G-19.7-05 前景主体分离接进 9 通道计算(subject_weight 0.85) |
| G-19.7-06 6 + 1 多 fixation 主体扫描实现,日志可审计 |
| G-19.7-07 每张测试图产 channel_contribution audit 行 |
| G-19.7-08 top-3 most_diagnostic 与人类直觉对照表 ≥ 9/12 一致(银子老师签收) |
| G-19.7-09 重跑 12 张图,$\geq 10/12$ top-1 正确 |
| G-19.7-10 $\geq 6/12$ 在 soft / firm 档 |
| G-19.7-11 错预测全部 ambig 不进 firm |
| G-19.7-12 Margin 平均 ≥ 0.20 |
| G-19.7-13 绿橙 / 黄绿苹果输出 soft 不 firm,不 no_call |
| G-19.7-14 tentative concept 在 candidate_concepts 为空时 spawn 测试通过 |
| G-19.7-15 RL-19.7-A01..E03 红线全过 |
| G-19.7-16 治理通过 |
| G-19.7-17 真名 0 命中 |
| G-19.7-18 全量回归 ≥ 561 + Phase 19.7 新测试 |

---

## 10. 与 Codex 19.7 提议的对齐

| Codex 提议 | Phase 19.7 § | 增强 |
|---|---|---|
| 前景主体分离 | §5 | 接通 v1a multi-hypothesis,subject_weight 量化 |
| 多 fixation 主体扫描 | §6 | 6+1 策略 + saliency × uncertainty × IOR 显式公式 |
| 部件/纹理/轮廓分通道投票 | §4 | 9 通道分块 noisy-OR + diagnosticity 加权(不只投票) |
| Channel ablation 审计 | §7 | audit 行 + top-3 与人类直觉对照 gate |

Codex 没明说但我加的:
- **§3 把识别管线真正接通 v1d 三层架构**(根因修复)
- **§4 公式根治**(从全维 cosine 改 9 通道诊断 noisy-OR)
- **§8 预期效果数字** + **§9 Gate 18 条**(可验证)

---

## 11. 边界

- Phase 19.7 不改感受器(V0..V9 + A0..A8 都不动)
- Phase 19.7 不改三层向量库 schema(继续 v1d / v1e)
- Phase 19.7 不改拟人 Conf 公式 $\Pi \cdot \Gamma \cdot Q \cdot \mu$(继续 v1a/v1b/v1d)
- Phase 19.7 只补**接通 + 公式真用 + 主体分离 + 多 fixation + audit**五件事
- 不接入实时摄像头
- 12 张图仍诊断,不证全宇宙泛化
- 不调外部 ML / API

---

## 12. 落地顺序

```
当前: Phase 19 全部 ✓(substrate + 三层库 + foveated + 拟人 Conf + probe + feedback + active 都有)
   ↓
Phase 19.7 接通修复(本设计)
   ↓
重跑 12 张图 → 期待 10/12 正确 + 6/12 soft/firm + Margin 平均 0.20+
   ↓
继续推进对话底座 / SNS 接入
```

---

## 13. 给 Codex 的实现优先级

```
Day 1: §4 9 通道分块 noisy-OR + δ_k 离线表 + h_0 baseline 表
Day 2: §5 前景主体分离接进 9 通道
Day 3: §6 6+1 多 fixation
Day 4: §3 visual_recognize_v1_7 总入口 + 替换 19.3 probe
Day 5: §7 channel ablation audit + Final Report
Day 6: 12 张图重跑 + 与银子老师对照人类直觉 + 银子老师签收
```

---

## 14. 给 Codex 的对抗审查指引

如果你拿到这份设计稿,请重点查:

1. §4 9 通道分块公式是否真的能拉开 margin(用 12 张图数据自己跑下心算/模拟)
2. §5 主体分离 segmentation_confidence < 0.6 时降级用全图,是否会让背景污染回来
3. §6 6+1 fixation 是否会过度采样主体内一个小区域(导致单一部件主导)
4. §7 top-3 diagnostic 对照表是否真能反映"人类用哪些线索"
5. §3 接通后是否仍有任何代码绕过(grep test)
6. v1e §10.3 object-arbitration 是否在跨 modality 情况下与 §4 单 modality recognition 协调

---

## 15. 署名

- 原架构设计:银子老师(笔名)
- v19.7 根因诊断 + 修复设计:Claude (Anthropic) 在银子老师 12 张实测 + Codex 19.7 方向提议基础上产出
- 落地:Codex 在 19.7 通过最终审查后实施

End of Phase 19.7 Design.
