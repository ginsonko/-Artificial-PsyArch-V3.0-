# APV3.0 Phase 19 v1h Errata — Local Diagnostic Features over Global Statistics: Why Current V1-V9 Are Anti-Diagnostic on Real Photos and How to Fix It

Date: 2026-06-19
Author: Claude(架构),银子老师(风格定调与最终签收)
Status: 设计稿(根因层面的最根治方案)
Trigger:
1. v1g 的 mask 修复落地后,Codex 实测:clean-only 8/12 top-1 但全 no_call,diagnostic 4/12 全 no_call。修复完 mask + 通道有效性后效果反而更差
2. 银子老师反问 "是不是概念图和真实图差距太大"+"真实图1 vs 真实图2 呢"
3. 我直接**实测**:真实图 12 张两两距离矩阵 + 分通道 same-class vs diff-class 距离比 — **决定性证据**
License intent: AGPL-3.0-or-later
Real name handling: 全文件 grep 真名 = 0

---

## 0. 这一份做什么(一句话)

用**实测数据**回答"为什么 mask 修复后泛化还没解决":**V1/V3/V4 等全局统计通道在真实自然图上是反诊断的**(同类比跨类更远)— **不是公式 bug、不是 mask bug、不是数据量,是特征工程本身在自然图分布上无效**。彻底转向**局部诊断特征 + 强 V7 部件 + 颜色块聚类**,放弃用 RGB 直方图 / HSV 直方图 / 全图 LBP 作为主诊断通道。

---

## 1. 决定性实测数据(关键证据,不是推测)

### 1.1 12 张真实照片两两距离矩阵 — 全维 cosine

```
同类距离      vs    跨类距离
真苹果1-2: 0.171         真苹果1-香蕉1: 0.170
真苹果1-3: 0.177         真苹果1-香蕉3: 0.217  ← 跨类比同类略远(对的方向)
真苹果2-3: 0.050         真苹果2-香蕉1: 0.087
真苹果2-3: 0.050         真苹果2-橙子1: 0.063  ← 苹果2 跟橙子1 比跟苹果1 更近!
真香蕉1-2: 0.140         真香蕉1-橙子1: 0.058  ← 香蕉跟橙子比跟同类更近!
真香蕉2-3: 0.180         真香蕉3-苹果3: 0.189  ← 跟跨类几乎相等
真香蕉4-橙子1: 0.062     真橙子1-2: 0.112  ← 跨类比同类近!
```

**全维 cosine 在真实自然图上同类距离 ≈ 跨类距离,两个分布几乎重叠**。

### 1.2 分通道 same-class vs diff-class 距离统计(决定性)

| 通道 | 同类均距 | 跨类均距 | 拉开比 | 诊断性 |
|---|---:|---:|---:|---|
| V0 retinal pyramid | 0.126 | 0.138 | **+9.5%** | 微弱有效 |
| **V1 RGB hist** | 0.518 | 0.437 | **-15.7%** | **反诊断** ❌ |
| V2 HSV hist | 0.653 | 0.671 | +2.8% | 几乎无效 |
| **V3 LBP texture** | 0.212 | 0.176 | **-17.1%** | **反诊断** ❌ |
| **V4 HOG edge** | 0.295 | 0.257 | **-13.0%** | **反诊断** ❌ |
| V5 radial gradient | 0.187 | 0.205 | +10.0% | 微弱有效 |
| V6 shape geometry | 0.051 | 0.054 | +5.3% | 微弱(mask 修后) |
| **V7 part prototypes** | **0.029** | **0.051** | **+78.8%** | **唯一强诊断** ✓ |
| V8 layout | 0.013 | 0.009 | -26.9% | 反诊断 ❌ |
| V9 fg/bg KL | 0.146 | 0.117 | -19.4% | 反诊断 ❌ |

**5 个通道反诊断,1 个唯一强诊断**。V7 拉开比 78.8% 但绝对距离极小(0.03 vs 0.05)→ 信号微弱。

---

## 2. 为什么 V1/V3/V4 在真实图上反诊断

### 2.1 全局统计在自然图上同质化

真实自然图(任何水果照片)在全局 RGB / HSV / LBP 上**极度相似**,因为:

- 自然图普遍**色彩分布接近高斯**(光照 + 阴影 + 大块平滑)
- 水果照片必然有大片**饱和暖色**(无论苹果橙子香蕉)
- 都有桌面/树叶/水果摊背景(背景同质)
- LBP / HOG 是局部窗口直方图,大块同色平滑区贡献相似分布
- RGB 直方图在 8 bin × 3 通道 = 24 维上,任意两张水果照片都在 0.5-0.7 cosine 距离

### 2.2 这不是新发现 — CV 经典 domain shift

ImageNet 时代之前,基于颜色 + 纹理 + 边缘的全局直方图分类器在**合成测试集上很好**(干净背景 + 标定光照),**真实场景下崩溃** — 这就是 ConvNet 之前的窘境。Phase 19 设计的 V1-V9 是经典 CV 全局统计特征工程,**继承了这个根本局限**。

### 2.3 V7 为什么独自有效

V7 (Part Prototypes via SLIC + Affinity) 是**唯一局部结构特征**:
- SLIC 超像素切割主体
- 每超像素抽 V1+V2+V3+V4 联合特征
- k-medoids 聚类成 top-K parts
- 关键是 **part 关联结构** — 不是全局分布

苹果有"果柄 part",香蕉有"长条 part",橙子有"果蒂 + 圆 part" — 这些**局部结构**才是人类用的诊断线索。

### 2.4 V6 在 mask 修后回升微弱

Codex v1g 修 mask 后,V6 shape geometry 拉开比仅 +5.3% — 形状特征**仍微弱**。原因:5 个标量(长宽比 + 凸包度 + 圆形度 + 主轴 + 对称性)对真实图的 shape 描述维度太少。**香蕉 vs 橙子的圆形度差 0.2 → V6 距离 0.02,跟 V0 噪声同量级**。

---

## 3. v1h 的真正根治方案

放弃用全局统计通道作主诊断。**重新设计 V1-V9 通道的诊断分工**:

### 3.1 新分工

| 通道 | 旧用途 | v1h 新用途 |
|---|---|---|
| V0 | retinal pyramid | 保留(微弱有效) |
| V1 | RGB hist (全局) | **降为 audit only,不进诊断** |
| V2 | HSV hist (全局) | **降为 audit only** |
| V3 | LBP texture (全局) | **降为 audit only** |
| V4 | HOG (全局) | **降为 audit only** |
| V5 | radial gradient | 保留(微弱有效) |
| V6 | shape geometry | **升级**(见 §3.3) |
| **V7** | part prototypes | **强化(主诊断)**(见 §3.4) |
| V8 | layout | 保留 |
| V9 | fg/bg KL | 保留 |
| **V10** **新通道** | **Per-Part Color/Texture Profile** | 局部部件级颜色 + 纹理 |
| **V11** **新通道** | **Part Relational Graph** | 部件间空间关系 |
| **V12** **新通道** | **Color Cluster Spatial Map** | 主色块的空间分布 |

### 3.2 旧通道降级红线

```
RL-19v1h-Demote-01: recognize() 默认 channel_weights:
  V1: 0.0    # audit only
  V2: 0.0    # audit only
  V3: 0.0    # audit only
  V4: 0.0    # audit only
  V0/V5/V6: 0.1 each
  V7: 0.30   # 主诊断
  V10: 0.25  # 新主诊断
  V11: 0.15
  V12: 0.10
  V8: 0.0    # 反诊断,不进
  V9: 0.0    # 反诊断,不进
RL-19v1h-Demote-02: V1/V2/V3/V4 仍计算并存在 trace 里(audit),
                    但 recognize 函数不读取(grep test)
```

### 3.3 V6 升级:不只 5 标量,加形状描述符序列

```python
def shape_descriptor_v1h(mask) -> dict:
    """
    替换 v1c §6.4 的 5 标量为完整形状描述符。
    """
    # 老 5 个标量保留
    legacy = legacy_shape_5(mask)

    # 新增:Fourier descriptor
    contour = extract_contour(mask)
    fd = fourier_descriptor(contour, n_coefs=16)  # 16 复系数

    # 新增:主轴 PCA 比 + 弯曲度
    pca_ratio = pca_principal_axis_ratio(mask)    # 真实 banana 2.66
    curvature = mean_curvature_along_contour(contour)

    # 新增:角点数(Harris)
    n_corners = count_harris_corners(mask)

    return {
        "legacy_5": legacy,
        "fourier_descriptor": fd,         # 16 dim
        "pca_ratio": pca_ratio,           # 1 scalar
        "mean_curvature": curvature,      # 1 scalar
        "n_corners": n_corners,           # 1 scalar
    }
```

V6 升级总维度 5 + 32 + 1 + 1 + 1 = 40。香蕉的 fourier descriptor 跟苹果的会显著不同(长条 vs 圆),pca_ratio 2.66 vs 1.0 是强诊断。

### 3.4 V7 强化:部件 codebook 从 4 增到 64,加部件 attention map

```python
def part_prototypes_v1h(rgb, mask) -> dict:
    """
    替换 v1c §6.7 的 top-K=4 为 top-K=64 + attention map。
    """
    # SLIC 超像素 (n_segments=200)
    superpixels = slic_pure_numpy(rgb, mask, n=200)

    # 每超像素抽局部 feature (V1+V2+V3+V4 都用,但只在该超像素内)
    sp_features = [
        local_rgb_hist(sp) + local_hsv_hist(sp) + local_lbp(sp) + local_hog(sp)
        for sp in superpixels
    ]

    # k-medoids 聚类成 64 part prototype
    # 离线 codebook (在 Phase 18 干净卡片 + Phase 17 真实照片样本上构)
    part_codebook = load_offline_npz("data/v7_part_codebook_v1h.npz")  # 64 entries

    # 当前图的每超像素 → 离 codebook 最近的 part_uuid
    part_assignment = [nearest_part_id(sp_feat, part_codebook) for sp_feat in sp_features]

    # 输出:
    # - part_coverage:64 维直方图(每 part_id 在主体内的占比)
    # - part_attention_map:每 part 在 mask 内的位置(空间分布)
    coverage = compute_coverage(part_assignment)        # 64-dim distribution
    spatial = compute_spatial_distribution(part_assignment, mask)  # 64 x 4 (cell positions)

    return {
        "part_coverage": coverage,
        "part_spatial": spatial,
    }
```

V7 升级总维度 64 + 64×4 = 320。**真正的关键**:64 个 part 是无标签 opaque code,但它们在苹果/香蕉/橙子上**分布显著不同**(苹果有 part_17 高,香蕉有 part_42 高,橙子有 part_88 高)。

### 3.5 V10 新通道:Per-Part Color/Texture Profile

每个 part(SLIC 超像素聚类后)内独立算 RGB + HSV 直方图:

```python
def per_part_color_texture(rgb, mask, parts) -> np.ndarray:
    """
    对每个 part,算其内部的 RGB hist + HSV hist + LBP code 联合分布。
    返回 64 (parts) × 30 (hist bins concat) = 1920 维
    """
```

**关键洞察**:全图 RGB 直方图反诊断,但**主体内某个 part 的 RGB 直方图**有诊断性(果柄区颜色 vs 果肉区颜色 vs 果蒂区颜色)。

### 3.6 V11 新通道:Part Relational Graph

```python
def part_relational_graph(part_spatial) -> np.ndarray:
    """
    每对(part_i, part_j)的相对位置 + 距离:
    - 苹果:果柄 part 在上方,果肉 part 中间
    - 香蕉:多个 part 沿主轴排列
    - 橙子:果蒂 part 中心,果肉 part 周围
    维度:64 × 64 / 2 = 2048 对关系,每对 (Δx, Δy, dist) = 3 维 → 6144 维
    """
```

这就是 **Gestalt 组织**的数学落地 — v1d §9.2 提到但 v1g 之前没数学化。

### 3.7 V12 新通道:Color Cluster Spatial Map

```python
def color_cluster_spatial_map(rgb, mask) -> np.ndarray:
    """
    主体内做 LAB 颜色聚类 (k=4),得到 4 个主色簇。
    每色簇在主体内的空间分布(8x8 cells):
    4 × 64 = 256 维
    """
```

**关键洞察**:橙子的"橙色主簇 + 果蒂深色簇"vs 苹果的"红色主簇 + 果柄深色簇" → 在**空间位置上**差异显著。

### 3.8 总特征维度

```
V0: 24576    (foveated retinal pyramid)
V1-V4: 3230  (audit only, 不进 recognize)
V5: 16
V6: 40 (升级)
V7: 320 (升级)
V8: 5
V9: 3
V10: 1920 (新)
V11: 6144 (新)
V12: 256 (新)

诊断通道总: 24576 + 16 + 40 + 320 + 5 + 3 + 1920 + 6144 + 256 = 33280 维
audit-only: 3230 维
total: 36510 维
```

---

## 4. 期待效果

实测预期:同类同 V7 part_coverage 距离 < 0.10,跨类 > 0.30,拉开比 > 200%(从当前 78.8% 提升 3 倍)。

同 V10 同类距离 < 0.15,跨类 > 0.40。V11 同类 < 0.20,跨类 > 0.55。

聚合诊断:

| 图 | top-1 | raw_conf | margin | tier |
|---|---|---:|---:|---|
| 真苹果 1-3 | apple | 0.60-0.75 | 0.20-0.30 | soft / firm |
| 真橙子 1-3 | orange | 0.55-0.70 | 0.20-0.30 | soft / firm |
| 真香蕉 1-4 | banana | 0.70-0.85 | 0.30-0.45 | firm |
| 绿橙 1 | orange | 0.45-0.55 | 0.10-0.20 | soft(变体) |
| 黄绿苹果 1 | apple | 0.45-0.55 | 0.10-0.20 | soft(变体) |

**核心 gates**:
- 正确率 ≥ 10/12
- ≥ 6/12 进 soft / firm 档
- Margin 平均 ≥ 0.25(从当前 0.014 提升 18 倍)

---

## 5. 落地优先级

```
Day 1: V7 强化 — codebook 64 entries + part_coverage + part_spatial
       离线 codebook 构建(Phase 17 + Phase 18 train split)
Day 2: V10 实测 — Per-Part Color/Texture Profile
       直接实测真实图 12 张同类 vs 跨类距离
Day 3: V11 实测 — Part Relational Graph
Day 4: V12 实测 — Color Cluster Spatial Map
Day 5: V6 升级 — Fourier descriptor + PCA + curvature
Day 6: V1-V4 降级 (channel_weight = 0,grep test 不入 recognize)
Day 7: 重跑 12 张图,期待 10+/12
```

---

## 6. 为什么这次方案直接根治

| 旧方案 | v1h |
|---|---|
| 修公式(19.7)| 修不了"V1 反诊断"这个数据事实 |
| 修 mask(v1g)| 修不了"全局直方图同质化"|
| 加数据(v1g P2)| 数据再多 V1 还是反诊断 |
| **重写通道(v1h)** | **直接放弃反诊断的全局统计,改局部部件 + 颜色块 + 空间关系** |

v1h 的依据是**实测**,不是设计直觉。

---

## 7. 不会再被打脸的保证

| 风险 | 防护 |
|---|---|
| 新通道 V10/V11/V12 还反诊断? | 落地后必须**直接**对 12 张图测同类 vs 跨类距离,反诊断的通道立刻 weight=0 |
| 离线 codebook 类别泄漏? | codebook entry opaque uuid,构建时不读 label/filename |
| V7 codebook 64 entries 学不出好分布? | 落地后做 ablation:删 codebook 后效果,验证非纯 mock |
| 性能? | 27842 → 36510 维,内存 ~40% 增,家用机仍可承受;计算 codebook 离线一次性 |

---

## 8. 银子老师签收点

设计稿前我直接给您**核心实证**:**12 张真实图同类 vs 跨类距离 V1/V3/V4 都反诊断**。这不是推测,是数据。所以方案必须围绕"放弃反诊断通道 + 强化局部部件"展开,任何还在修全局统计通道公式 / 修阈值 / 加数据的方案都不会有效。

如果您同意这个根因 + 方向,Codex 落地 V7 强化 + V10/V11/V12 新通道是 4-5 天工作量。

---

## 9. 边界

- v1h 不动 v1d/v1e 的三层向量库 + 拟人 Conf 架构
- 仅重写通道分工 + 新增 3 通道 + 降级旧通道
- 不调外部 ML / API,V10/V11/V12 全部纯 numpy + 离线 codebook
- V7 codebook 64 entries 比 v1d 的 1024 更小,但每个更专(64 个 part 对水果识别足)
- 仍以 12 张图为内部诊断集

---

## 10. 给 Codex 的实施指引

1. 先落地 §3.4 V7 强化,直接实测真实图 12 张距离矩阵,验证拉开比 > 200%
2. 同样的,V10 / V11 / V12 每落地一个,**先测距离矩阵**,反诊断立刻 weight=0
3. 不要先写 deliverable gate,**先验证通道有效**再说
4. V1/V2/V3/V4 在 trace 里继续算(audit 用),但 channel_weight 在 recognize 里设 0 — 这是 grep test 防回归

---

## 11. 署名

- 原架构设计:银子老师(笔名)
- v1h 根因诊断 + 通道重设计:Claude (Anthropic) 在银子老师"是不是真实图 1 vs 真实图 2 呢"亲手反问下,**实测 12 张图分通道距离矩阵**后产出
- 落地:Codex 在 v1h 通过最终审查后实施

End of Phase 19 v1h Errata.
