# APV3.0 Phase 19 v1g Errata — Mask-Driven Subject Recovery, Channel Validity Gates, and Diagnostic-Library Construction

Date: 2026-06-19
Author: Claude(架构),银子老师(风格定调与最终签收)
Status: 设计稿(根治补丁,优先级最高),叠加在 v1 + v1a + v1b + v1c + v1c-audio + v1d + v1e + 19.7 上
Trigger:
1. 银子老师让我重新查泛化失败的根因(Codex 19.7 实测 9→4→6 反降)
2. 我读 visual_receptor.py 直接读到 `_quick_mask` 算法:`mask = score >= score.mean()`,**数学上**就是"取高于均值的 20-50% 像素",bbox 几乎总是 1:1 — 不反映主体真实形状
3. 实测验证:banana clean card 真实 PCA 主轴比 2.66:1,但 `_quick_mask` 给的 bbox 1:1 → V6 形状几何**零诊断性**
4. V6/V7/V8/V9 都依赖 mask → **4 个通道集体失效**;V1/V2/V3 颜色/纹理通道独立工作,所以全维 cosine 还能侥幸 9/12,但 19.7 通道 noisy-OR 把废通道公平加入 → 反而暴露隐藏 bug → 9 降到 4
5. Codex 提的"加多样化数据"是治标:即使加 100 张真照,只要 mask 还是 1:1,V6 还是废
License intent: AGPL-3.0-or-later
Real name handling: 全文件 grep 真名 = 0

---

## 0. 这一份做什么(一句话)

**根治 Phase 19 视觉泛化的 mask 算法 bug** — 重写 `_quick_mask` 为真正能反映主体形状的多策略 mask 求解器,加 **channel validity gates**(每通道在使用前必须自证非废),并补 Codex 提的 **diagnostic library construction**(干净卡片之外加真实教学样本 + 主体 descriptor 质量门)。三件事一起做才能从根本上让 9/12 → 11-12/12。

---

## 1. 三层根因诊断(完整证据链)

### 1.1 Layer 1 (公式层)
- 旧探测脚本走 27842 维 cosine + 直接 argmax
- 这是 Codex 19.7 已经修了的,但实测反降。说明这只是**表层**

### 1.2 Layer 2 (原型数据层)
- V6 / V7 / V8 / V9 在 clean cards 上接近无差异
- Codex 这次提的:多样化训练样本 + 真实教学样本

### 1.3 Layer 3 (**我刚找到的隐藏 mask bug 层**)

`apv3test/runtime/visual_receptor.py:988` 的 `_quick_mask` 实现:

```python
def _quick_mask(rgb, edge):
    luma = _luma(rgb)
    center = _center_prior(rgb.shape[0], rgb.shape[1])
    score = np.abs(luma - float(np.median(luma))) + edge * 0.25 + center * 0.10
    mask = score >= float(score.mean())   # ← 这是 bug
    if float(mask.mean()) <= 0.01:
        return center >= 0.35
    return mask
```

**数学问题**:`score >= score.mean()` 在任意分布上**永远**返回约 30-50% 像素(高斯分布严格 50%,实际加边缘后偏 30%)。这对 banana 来说:

- 香蕉黄色像素 ≈ 15% 真实主体
- 但 score >= mean 提出了 ≈ 25% 像素 → 把背景白色边缘也提进 mask
- 提出来的 mask bbox 接近正方 ≈ 1:1
- **V6 长宽比、V6 主轴方向、V6 凸包度全部失效**
- V7 SLIC 部件基于错 mask → 错部件
- V8 主体重心 + 占比 → 错位置/错面积
- V9 fg/bg KL → 用错 fg/bg → 错对比

我实测验证:

```
apple clean train_0: mask coverage 20.7%, bbox ratio 1.00
banana clean train_0: mask coverage 24.5%, bbox ratio 1.00  ← 应该 ~2.66:1!
orange clean train_0: mask coverage 24.2%, bbox ratio 1.00
真香蕉 1: mask coverage 32.3%, bbox ratio 1.22 ← 真照片只能挽回少许
真苹果 1: mask coverage 37.6%, bbox ratio 1.00
绿橙子 1: mask coverage 37.1%, bbox ratio 1.04
```

### 1.4 为什么 19.7 实测反降到 4/12

旧全维 cosine 走 27842 维大池,V0-V9 共存。V1+V2+V3 颜色/纹理通道独立工作,**侥幸覆盖了** V6/V7/V8/V9 废通道的污染 → 9/12。

19.7 改通道分块 noisy-OR + top-m=4,**让 V6/V7 这些废通道**公平进入候选(它们 score 极接近,top-m 选不出强诊断通道)→ 通道证据相互打架 → margin 反而更小 → 4/12。

加 V0 高带宽 sketch 后,V0 包含原图直采(不依赖 mask),回升到 6/12。

**结论**:Layer 3 的 mask bug 是这次"19.7 实测降"的真正解释,**不只是 Codex 说的"原型诊断性不足"**。

---

## 2. v1g 修复三件事(按优先级)

| 优先级 | 内容 | 解决什么 |
|---|---|---|
| **P0 必修** | 重写 `_quick_mask` → `solve_subject_mask`,**多策略 + iterative refinement** | Layer 3 mask bug,V6/V7/V8/V9 失效 |
| **P1 必修** | Channel validity gates,每通道在使用前必须自证非废 | 防今后再有隐藏废通道偷偷生效 |
| **P2 必修** | Diagnostic Library: clean cards + 真实教学样本 + 主体 descriptor 质量门 | Codex Layer 2 方向,补数据多样性 |

---

## 3. P0 — 主体 Mask 求解器重写

### 3.1 设计目标

mask 必须满足三条数学性质:

1. **形状保持** — banana mask bbox ratio 必须 ≥ 2.0(真实 2.66:1 至少保住 75%)
2. **覆盖合理** — coverage 在 5%-50% 之间(不可能整图 = 主体,也不能 < 5% = 抓不到)
3. **跨样本一致** — 同概念多张训练样本,mask 形状指标(ratio, circularity)的标准差 / 均值 < 0.3

### 3.2 多策略 mask 求解(替换 score >= mean)

```python
def solve_subject_mask(rgb, edge, *, return_hypotheses=False) -> Mask | list[Mask]:
    """
    多策略 mask 求解,加 iterative refinement.
    继承 v1a §3.3 multi-hypothesis 但显式实现(v1a 只写了 prose).
    """
    hypotheses = []

    # H1: Color-cluster mask
    # 用 k-means(k=3-5)在 LAB 颜色空间聚类,选"最像主体"的簇:
    #   - center prior 高,
    #   - 与背景色显著不同(LAB ΔE > threshold),
    #   - cluster 面积 5%-50%
    h1 = mask_color_cluster(rgb, k=4)
    hypotheses.append(h1)

    # H2: Edge-closure mask
    # Canny + 形态学闭运算 → 连通区域 → 选最大且占 5%-50% 的连通块
    h2 = mask_edge_closure(rgb, edge)
    hypotheses.append(h2)

    # H3: Saturation-prior mask (LAB ΔE from white background)
    # 计算每像素到白色背景的 LAB ΔE 距离,取 ΔE > threshold 的连通块
    h3 = mask_saturation_prior(rgb)
    hypotheses.append(h3)

    # H4: Iterative GrabCut-lite (纯 numpy)
    # 用 center prior 作 trimap 初值,迭代 5 次 LAB 颜色 GMM
    h4 = mask_grabcut_lite(rgb, n_iter=5)
    hypotheses.append(h4)

    # 每 hypothesis 算 segmentation_confidence
    for h in hypotheses:
        h.segmentation_confidence = compute_seg_conf(h)
        # = coverage_in_5_50_range × edge_alignment × center_prior_match × inner_homogeneity

    if return_hypotheses:
        return hypotheses

    # 单 mask 模式:加权融合 top-K hypothesis
    return weighted_blend(hypotheses, top_k=3)


def compute_seg_conf(mask: Mask) -> float:
    """
    segmentation_confidence ∈ [0, 1]
    """
    coverage = mask.pixel_count / mask.total_pixels
    # 性质 1: coverage 在 5%-50% 之间
    coverage_score = piecewise_score(coverage, 0.05, 0.50)

    # 性质 2: 边缘对齐 — mask 边界处 edge 强度高
    boundary = mask_boundary(mask)
    edge_alignment = edge_intensity_at(boundary).mean()

    # 性质 3: 内部均匀 — mask 内部色彩方差低(同主体)
    inner_homogeneity = 1.0 - color_std_inside(mask)

    # 性质 4: 中心先验 — mask 重心接近图心
    center_match = 1.0 - center_offset(mask)

    return coverage_score × edge_alignment × inner_homogeneity × center_match
```

### 3.3 关键修正:不再用 `score >= mean`

**禁止任何形式的"取超过均值像素"作为 mask**。红线:

```
RL-19v1g-Mask-01: grep test 检 visual_receptor.py: `mask = score >= score.mean()` 必须为 0
                  类似 `>= np.median(score)` 也禁
RL-19v1g-Mask-02: 任意 mask 在使用前必须经过 compute_seg_conf,segmentation_confidence ≥ 0.4 才用
RL-19v1g-Mask-03: 若 segmentation_confidence < 0.4,V6/V7/V8/V9 通道**降级**:
                  - V6 shape 输出零向量
                  - V7 part 用 SLIC 全图无主体偏置
                  - V8 layout 用整图中心 + 全图面积
                  - V9 fg/bg KL 退化为 0(无对比)
                  减少废通道干扰但不参与诊断
```

### 3.4 Hypothesis 投票模式(v1a 既有但没实施)

每 hypothesis 独立产 V6/V7/V8/V9 → 加权 / 投票:

```python
def extract_subject_channels(rgb, edge):
    hyps = solve_subject_mask(rgb, edge, return_hypotheses=True)
    valid_hyps = [h for h in hyps if h.segmentation_confidence >= 0.4]

    if not valid_hyps:
        # 全废,降级
        return _degenerate_channels()

    # 每 hypothesis 给出 V6/V7/V8/V9
    channel_estimates = []
    for h in valid_hyps:
        channel_estimates.append({
            "V6": shape_geometry(h.mask),
            "V7": part_prototypes(rgb, h.mask),
            "V8": layout_summary(h.mask),
            "V9": fg_bg_kl(rgb, h.mask),
            "weight": h.segmentation_confidence,
        })

    # 加权融合
    return weighted_average(channel_estimates)
```

### 3.5 Gate

| Gate |
|---|
| G-19v1g-P0-01 banana clean cards 三张 mask bbox ratio ≥ 2.0(实测 PCA 2.66) |
| G-19v1g-P0-02 苹果 mask circularity ≥ 0.75(真圆) |
| G-19v1g-P0-03 香蕉 mask circularity ≤ 0.55(长条且弯曲) |
| G-19v1g-P0-04 12 张真实照片每张 segmentation_confidence ≥ 0.4(否则降级) |
| G-19v1g-P0-05 同概念 3 张训练样本,mask 形状指标 std/mean < 0.3 |
| G-19v1g-P0-06 grep test 旧 `mask = score >= score.mean()` 不命中(已删) |

---

## 4. P1 — Channel Validity Gates

### 4.1 设计目标

防止今后再有隐藏废通道偷偷生效。每通道在 recognize() 阶段使用前,必须自证非废:

```python
def channel_validity_check(channel_evidence, channel_name) -> bool:
    """
    一个通道在某 concept 上的诊断系数 δ_k^(c) 必须 ≥ delta_min_valid
    且 在 train 集上 各类间方差 / 类内方差 ≥ between_within_ratio_min
    """
    if channel_evidence.delta_k < float(load_constant("phase19.channel.delta_min_valid")):
        return False

    if channel_evidence.between_within_ratio < float(load_constant("phase19.channel.between_within_ratio_min")):
        return False

    return True
```

```yaml
phase19:
  channel:
    delta_min_valid: 0.30                # @structural - 最近负例 nearest-negative 诊断系数下限
    between_within_ratio_min: 1.5        # @experimental - F-statistic 类间方差 / 类内方差
    invalid_channel_penalty: 0.0         # @structural - 失效通道证据置零
```

### 4.2 Recognize 时只用 valid channels

```python
def visual_recognize_v1g(query, ...):
    # 先 mask + V0..V9 抽
    canvas = build_sensory_canvas(query)
    # 对每通道做 validity check
    valid_channels = []
    for k in ("V1", "V2", ..., "V9"):
        if channel_validity_check(channel_evidence[k], k):
            valid_channels.append(k)
        else:
            log_audit(f"channel {k} dropped: invalid")

    if len(valid_channels) < 3:
        # 不足 3 个 valid 通道 → 输出 no_call (拟人:看不清就别说)
        return RecognitionResult(decision_tier="no_call", reason="insufficient_valid_channels")

    # 通道 noisy-OR 只在 valid channels 上做
    Pi = thresholded_noisy_or(query, concept, valid_channels)
    ...
```

### 4.3 Audit 表

每张测试图的 audit 行加 `valid_channels: list[str]` + `dropped_channels: list[tuple[str, reason]]`,可显式看到 V6 V7 是不是被 drop 了。

### 4.4 Gate

| Gate |
|---|
| G-19v1g-P1-01 每通道独立 validity check 单测 |
| G-19v1g-P1-02 12 张图 audit 行含 valid_channels / dropped_channels |
| G-19v1g-P1-03 修 mask 后,V6/V7/V8/V9 应该重新 valid(否则说明 mask 还没修对) |
| G-19v1g-P1-04 valid_channels < 3 时输出 no_call |

---

## 5. P2 — Diagnostic Library Construction

### 5.1 现有 clean card 套件不够 — 给 Codex P2 方向

每概念目前只有:
- 3 train + 1 held_out + 1 contrast = 5 张
- 全是合成,基本无尺度 / 角度 / 颜色变化
- contrast 只是其他类的样本,不是同类变体

补充:

```
每概念至少 8 train + 4 held_out:
  3 generic clean cards (现有)
  3 多样化 clean cards (尺度、位置、颜色饱和度变化)
  2 真实简单照片 (单果实、白背景)(可从用户 12 张里取部分作 train,LOO 不重叠的)
held_out:
  2 generic (现有)
  1 颜色变体 (绿橙、黄绿苹果作 hard case)
  1 角度 / 部分遮挡 (challenge case)
```

注意:用户 12 张全是 audit 集,**不能直接挪到 train** — 必须用 LOO(留 1 测 11)或新找额外样本。

### 5.2 主体 Descriptor 质量门(Codex 提的)

每张训练样本入库前,先经过 mask + V6/V7 抽取 → descriptor 质量评分:

```python
def descriptor_quality_score(example) -> float:
    """
    一个训练样本对该概念的诊断贡献,需满足:
    - 主体清晰可分割
    - 颜色饱和度足够
    - 形状代表性(不在 ± 30% 偏离原型)
    """
    seg_conf = example.segmentation_confidence
    color_saturation = compute_avg_saturation(example.mask)
    shape_distance_to_prototype = compute_shape_distance(example, all_train_for_concept)

    return seg_conf × color_saturation × (1.0 - shape_distance_to_prototype)
```

低于 `phase19.train.descriptor_quality_min = 0.5` 的不入 Layer-3 训练。

### 5.3 Gate

| Gate |
|---|
| G-19v1g-P2-01 每概念 ≥ 8 train + ≥ 4 held_out |
| G-19v1g-P2-02 每入库训练样本 descriptor_quality ≥ 0.5 |
| G-19v1g-P2-03 真实教学样本不重叠 audit 12 张 |

---

## 6. 期待效果

修完 P0 + P1 + P2 后,**重跑同样 12 张**:

| 测试图 | 预期 top-1 | 预期 raw_conf | 预期 margin | 预期 tier |
|---|---|---:|---:|---|
| 真实苹果 1-3 | apple | 0.55-0.70 | 0.20-0.35 | soft / firm |
| 真实橙子 1-3 | orange | 0.55-0.70 | 0.20-0.35 | soft / firm |
| 真实香蕉 1-4 | banana | 0.65-0.80 | 0.30-0.45 | firm(V6 形状现在有诊断了) |
| 绿橙 1 | orange | 0.40-0.55 | 0.10-0.20 | soft(拟人变体) |
| 黄绿苹果 1 | apple | 0.40-0.55 | 0.10-0.20 | soft(拟人变体) |

**核心 gates**:
- 正确率 ≥ 10/12(Codex 19.7 实测 4-6 → v1g 预期 10-12)
- 至少 5 张进入 soft 或 firm 档
- 错预测 ≤ 2 张且全在 ambig
- Margin 平均 ≥ 0.20

---

## 7. 落地优先级(给 Codex)

```
Day 1: P0 — solve_subject_mask 多策略 + iterative refinement + compute_seg_conf
       验证:banana mask bbox ratio ≥ 2.0
Day 2: P0 — extract_subject_channels 通过 hypothesis 投票
       验证:V6/V7/V8/V9 在 banana 上重新有诊断性
Day 3: P1 — channel_validity_check + audit 表
       验证:废通道自动 drop
Day 4: P2 — 加 5 张多样化 clean cards/concept + 2 张真实教学(从 12 张里 LOO 留 1)
       注意:LOO 留 1 是 train 时 11 张训练,测试时 1 张测,12 个 fold 跑一遍
Day 5: 重跑 12 张图 → 与 Codex 之前 4/12 / 6/12 / 9/12 直接对比
Day 6: Final Report + 展示页(由 Codex)
```

---

## 8. 红线汇总

| RL | 描述 |
|---|---|
| RL-19v1g-Mask-01 | grep `mask = score >= score.mean()` 命中 = fail |
| RL-19v1g-Mask-02 | 任意 mask 用前 seg_conf ≥ 0.4 |
| RL-19v1g-Mask-03 | seg_conf < 0.4 时 V6/V7/V8/V9 降级到 0 不参与诊断 |
| RL-19v1g-Channel-01 | 每通道 validity check 必经过 |
| RL-19v1g-Channel-02 | valid_channels < 3 时强制 no_call |
| RL-19v1g-Train-01 | descriptor_quality < 0.5 的样本不入 Layer-3 |
| RL-19v1g-LOO-01 | 用户 12 张图不允许直接进 train,只能 LOO |

---

## 9. 边界

- v1g 修 mask + channel validity + diagnostic library 三件事,不动其他架构
- 不调外部 segmentation 库(GrabCut-lite 纯 numpy 实现)
- 不调外部 superpixel 库(SLIC 纯 numpy)
- 12 张用户图仍为 audit 集,LOO 跑 12 fold
- 不接入实时摄像头 / 大量真实图采集 — 单次 LOO + 8 train/concept 就够了
- 不宣称真泛化,Phase 19.7 + v1g 完成后只能宣称"诊断管线 + mask + channel validity + library 都到位,在 12 张内部诊断 + LOO 上取得 10+/12"

---

## 10. 为什么这次不会再被实测打脸

| 问 | 答 |
|---|---|
| 还会有隐藏 bug 让通道失效吗? | P1 channel validity gate 自动检测,不能再静默废 |
| mask 算法还会出错吗? | P0 多 hypothesis + seg_conf 门 + 直接 grep 旧 `score >= mean` |
| 训练数据还会不够吗? | P2 加 5 多样化卡 + 2 真实教学,LOO 验证够用 |
| 拟人 Conf 公式还能再被打脸吗? | v1d/v1e/19.7 已经做了 Π·Γ·μ·Q,纯数学,不会再变 |

诊断证据已经在数据里(banana mask bbox 1.00 vs PCA 2.66)— v1g 不再是凭空设计。

---

## 11. 致 Codex 的对抗审查指引

如果你拿到这份设计稿,重点查:

1. solve_subject_mask 的 4 个 hypothesis 是否在 banana clean card 上能给出 ratio ≥ 2.0(实测,不只是设计)
2. compute_seg_conf 在低对比 / 高遮挡情况下会不会失稳
3. channel_validity 的 between_within_ratio = 1.5 是否对 3 个概念 + 8 train 够稳定
4. LOO 12 fold 是否会让 held_out 信息隐式回流(继承 v1b §7 RL-19v1b-C6-01)
5. 是否有 v1g 没覆盖的其它通道实现 bug(预测:可能在 V4 HOG 的方向分桶上)

---

## 12. 署名

- 原架构设计:银子老师(笔名)
- 根因诊断 + v1g 修法:Claude (Anthropic) 在银子老师亲手实测 Codex 19.7 后,**实际读 visual_receptor.py 找到 `_quick_mask` bug** 而出
- 落地:Codex 在 v1g 通过最终审查后启动

End of Phase 19 v1g Errata.
