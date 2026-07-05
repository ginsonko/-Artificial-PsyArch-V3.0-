# APV3.0 Phase 19 v1d Errata — Three-Layer Vector Substrate, B/C Recall, Online Embedding by Reward-Surprise, and Codex Closure

Date: 2026-06-19
Author: Claude(架构),银子老师(风格定调与最终签收)
Status: 设计稿修订,叠加在 v1 / v1a / v1b / v1c / v1c-audio 之上 — 六份合读。
        **新增 Phase 19.0b 子阶段** — 必须在 Phase 19.0a 之前落地,作为 19.0a 的存储底座。
Trigger:
1. Codex v1c 对抗审阅给出 5 Blocker + 6 Serious + 多模态/Gestalt/恒常性"还缺特性"
2. 银子老师明确"我们要做近乎 100% 拟人"+"不应该要简化方案"+"性能允许的话能做到吗" + 引入 B/C 召回 + 本地在线嵌入学习
3. 银子老师明确修正学习信号: **由奖惩信号(外部用户 + 内部违和感/期待压力)+ 最小化预测误差(认知压)驱动**,不是用户反馈直接改 weights
License intent: AGPL-3.0-or-later
Real name handling: 全文件 grep 真名 = 0

---

## 0. 这一份做什么(一句话)

把"感受器 → 直接打分"的扁平架构升级为"感受器 → 三层 AP-native 向量库 → 拟人 Conf → 输出 + 反向(R_sketch/R_proto/识别共用底座)" 的**正确拟人架构**;Layer-3 在线嵌入学习由**奖惩信号(外源 + 内源)+ 认知压最小化**驱动 — 不是用户反馈直接覆盖权重。这一份同时吸收 Codex v1c 审阅的全部 11 项修订(5 Blocker + 6 Serious),并把"周边视觉特性 / Gestalt / 恒常性 / 多模态绑定 / McGurk"等之前提的拟人扩展全部落到这个三层架构里。

---

## 1. 全部修订清单

### 1.1 吸收 Codex v1c 审阅 11 项

| ID | Codex | 我的处理 |
|---|---|---|
| **B1** 维度不闭合 | feature_dim 与 canvas_state_dim 混 | §2.1 Layer-1 锁 27838 维感受;canvas_state 独立 4 维;packet 三分(sensory / canvas / render_audit) |
| **B2** ClarityField floor 加两次 | 远处 floor 残留 | §2.2 公式改 $\phi = \mathrm{clip}(\phi_{\min} + (1-\phi_{\min}) \cdot \max_i[\dots], 0, 1)$ |
| **B3** SSIM 单调 gate 过硬 | 不允许新发现细节时短暂回退 | §2.3 改 normalized gain + coverage gain + clarity-weighted SSIM |
| **B4** sketch canvas 被识别信心污染 | top-down 写入 PERCEIVED | §3.4 sketch canvas 只由 PERCEIVED + clarity + source_reliability 更新;识别信心走单独 prediction_overlay,source=INFERRED |
| **B5** R_proto codebook 类别模板泄漏 | codebook 变"苹果模板库" | §4.3 Layer-2 codebook 严格 opaque id;Layer-3 association 才承载"苹果是哪些 parts 经常共现" |
| **S1** 32×32 焦点不具尺度拟人性 | 固定像素 | §2.4 改 viewport 归一化 $r_0 = \mathrm{clamp}(k \cdot \min(W,H), r_{\min}, r_{\max})$ |
| **S2** SSIM_focus > near > far 对自然图过硬 | 远处纯白会 SSIM 高 | §2.5 合成 checkerboard 测分辨率单调;自然图测统计趋势 + MTF/高频保留率 |
| **S3** 重建≠识别泛化 | 全维 L2 不拟人 | §5 完全靠 C+B 召回 + Layer-3 ConceptPrototype 的拟人 Conf,不用全维相似度 |
| **S4** 扫视太机械 | "找最低 clarity"过于呆板 | §6 next_fixation = saliency + uncertainty + task + surprise - IOR |
| **S5** 听觉不能像看图那样扫 | echoic memory 4 秒边界 | §7.1 echoic buffer 4 秒硬墙,超出只能 REMEMBERED/IMAGINED |
| **S6** phase 融合不稳 | circular mean 制造伪影 | §7.2 phase 降为 audit;核心认知 = mag/envelope/pitch/onset/timbre |

### 1.2 银子老师指定的架构扩展

| ID | 修订 | §X |
|---|---|---|
| **A1** 三层 AP-native 向量库 | Layer-1 PerceptVector / Layer-2 PartPrototype / Layer-3 ConceptPrototype | §3 |
| **A2** B 召回 / C 召回 | 复用 APV2.1 已验证的双速召回路径 | §3.2 + §5 |
| **A3** 本地在线嵌入学习 | k-medoids 增量 + SDPL contribution,**由奖惩 + 认知压驱动** | §4 + §8 |
| **A4** Layer-3 学习信号 | **奖惩信号(外源用户 + 内源违和感/期待压力)+ 最小化预测误差(认知压)** | §8 |

### 1.3 之前提到但还没落到设计稿的"拟人扩展特性"

| ID | 特性 | 在三层架构里的位置 |
|---|---|---|
| **X1** 周边视觉颜色/对比/运动/边缘衰减曲线不同 | Layer-1 V0 各通道独立衰减常量 | §9.1 |
| **X2** Gestalt 组织(接近 / 连续 / 闭合 / 相似) | Layer-2 PartPrototype 的 association 边 | §9.2 |
| **X3** Figure-ground 分离 | Layer-1 内置(v1c §3.3 multi-hypothesis mask)+ Layer-2 part 关联背景 | §9.3 |
| **X4** 颜色/大小/形状恒常性 | Layer-3 ConceptPrototype 记录"变体范围"(orange 包括绿橙) | §9.4 |
| **X5** 物体持存 | Layer-1 PerceptVector 跨 tick 持久(衰减)+ Layer-3 object_id binding | §9.5 |
| **X6** 预测编码(source-separated) | Phase 19.5 的 prediction_overlay,source=INFERRED | §9.6 |
| **X7** change blindness / inattentional blindness | 周边低 clarity 区不更新 PerceptVector | §9.7 |
| **X8** 听觉 masking / 等响曲线 / 双耳定位 | Layer-1 A0 编码内置 | §9.8 |
| **X9** 多模态时间同步绑定 | Layer-3 ConceptPrototype 跨模态 association | §9.9 |
| **X10** McGurk 冲突(视听不一致) | Layer-3 reliability-weighted cue integration | §9.10 |

---

## 2. Codex Blocker / Serious 11 项落地(快速通过)

### 2.1 B1 — 维度拆分

```
Layer-1 PerceptVector dim:
  visual_feature_dim   = 27838    (V0..V9)
  audio_feature_dim    = 30497    (A0..A8)

Layer-1 CanvasState dim (独立):
  visual_canvas_state_dim = 4    (clarity_mean, confidence_mean, freshness_mean, fixation_count)
  audio_canvas_state_dim  = 4    (同语义,时频版)

Layer-1 RenderAudit dim (独立):
  visual_render_audit_dim = 8    (ssim_focus, ssim_near, ssim_far, coverage, ...)
  audio_render_audit_dim  = 8    (同语义)

SDPL packet 显式三分: sensory_feature_block / canvas_state_block / render_audit_block
红线 RL-19v1d-B1-01: packet_key 只依赖 sensory_feature_block,canvas/render 仅 audit
```

### 2.2 B2 — ClarityField floor 修正

**v1c 原版**(错):
$$
\phi_t(x, y) = \exp(\dots) + \phi_{\min}, \quad \phi_{\mathrm{multi}} = \max_i[\dots] + \phi_{\min}
$$

**v1d 修正**:

$$
\boxed{
\phi_{\mathrm{multi}}(x, y) = \mathrm{clip}\left(\phi_{\min} + (1 - \phi_{\min}) \cdot \max_i\left[\exp\left(-\frac{\|p-c_i\|^2}{2\sigma^2}\right) \cdot \exp\left(-\frac{t - t_i}{\tau_{\mathrm{memory}}}\right)\right],\; 0,\; 1\right)
}
$$

floor 只加一次,自然在 $[\phi_{\min}, 1]$ 区间。听觉同理。

### 2.3 B3 — SSIM gate 改 normalized gain + coverage(允许人类式短暂回退)

**v1c 原版 gate** "10 tick SSIM 至少 +0.15 且每 tick 不能回退 > 0.02" → 不拟人(人会瞥到细节短暂困惑)

**v1d 修正**:

```yaml
normalized_gain := (SSIM_T - SSIM_0) / max(1 - SSIM_0, eps)
coverage_gain  := (cov_T - cov_0)                # clarity > 0.5 像素覆盖率
clarity_weighted_ssim_gain := ...                # 按每像素 clarity 加权

Gate 重写(any 满足即过):
  G-19.0a-MT-01a: normalized_gain >= 0.20
  G-19.0a-MT-01b: coverage_gain   >= 0.30
  G-19.0a-MT-01c: clarity_weighted_ssim_gain >= 0.15

并且禁掉硬 per-tick 单调约束,改为:
  G-19.0a-MT-02: 任意 5 连续 tick 滑动窗口内,上述三个 gain 至少有一个 > 0
```

允许"看到边缘短暂困惑、整体 SSIM 回退一下" 这种拟人现象,只要 5 tick 滑动窗口里有信息增益。

### 2.4 B4 — Sketch canvas 不被识别信心污染

**红线**:

```
RL-19v1d-B4-01: SensoryCanvas 更新公式只允许:
                fuse(canvas, patch_value, w_old=canvas_confidence, w_new=phi_new * source_reliability)
                source_reliability 仅取自:
                  - 视觉传感器物理可信度(模糊度 / 噪声估计)
                  - epistemic_source ∈ {PERCEIVED_SENSORY_SKETCH}
                禁止取自 Layer-3 ConceptPrototype 的识别 Conf

RL-19v1d-B4-02: 识别信心写入独立 prediction_overlay canvas:
                family="prediction_overlay"
                source="INFERRED" 或 "IMAGINED"
                展示页可叠加显示,audit 必须能拆开
```

### 2.5 B5 — Codebook 防类别泄漏

```
Layer-2 PartPrototype Store 红线:
  RL-19v1d-B5-01: codebook entry 是 opaque uuid,不含类别 / 文件名 / 中文 / 标签
  RL-19v1d-B5-02: 构建时不读取类别名 / 文件名 / held-out 分组
  RL-19v1d-B5-03: 只用 Phase 17/18 train split 样本,held-out 一切隔离
  RL-19v1d-B5-04: R_proto 选择部件来自 Layer-3 ConceptPrototype 的 association,
                  不是 Layer-2 直接按类别检索

Layer-3 ConceptPrototype 才知道 "apple_concept_uuid 关联 [part_4f2a, part_8b21, part_3c19]"
删除 Layer-3,Layer-2 仍能产生 opaque parts,但无法复刻"苹果"
```

### 2.6 S1 — 焦点半径 viewport 归一化

$$
r_0^{\mathrm{px}} = \mathrm{clamp}\left(k \cdot \min(W, H),\; r_{\min},\; r_{\max}\right)
$$

```yaml
vision_sensor:
  foveal_radius_ratio_k: 0.025        # @experimental - 占画面短边的 2.5%
  foveal_radius_min_px: 16            # @structural - 最小焦点核心半径
  foveal_radius_max_px: 96            # @structural - 最大焦点核心半径
```

1024 px 短边 → $r_0 = 25.6$,clamp 到 $[16, 96]$ → 26 px;64 px 测试图 → clamp 下界 → 16 px。
这就让"同一图缩放后看见能力稳定"。

### 2.7 S2 — SSIM 分场 gate 区分合成图 vs 自然图

```
合成 checkerboard / 高频细纹理图 (内部硬测):
  SSIM_focus > SSIM_near > SSIM_far 单调必须严格成立(分辨率证明)
  MTF / 高频保留率必须随 layer level 单调下降

自然图(用户 12 张 + 真实 audit 集):
  统计趋势(12 张平均):
    mean(SSIM_focus) > mean(SSIM_near) > mean(SSIM_far)
  单张允许例外(远处纯背景),不强制每张单调
  补充指标:
    edge_sharpness_focus > edge_sharpness_periphery
    high_freq_energy_focus > high_freq_energy_periphery
```

### 2.8 S3 — 识别走 C+B 召回 + 拟人 Conf,不全维 L2

完全交给 §3 + §5 的三层向量库 + 拟人 Conf 公式。

### 2.9 S4 — 扫视策略 saliency + uncertainty + task + surprise - IOR

```
next_fixation_score(p) =
    w_sal       * saliency(p)
  + w_unc       * uncertainty(p)            # 1 - canvas_confidence(p)
  + w_task      * task_drive(p)             # 由当前 attention goal 决定
  + w_surprise  * |prediction_error(p)|     # prediction_overlay - sensory_sketch 差
  - w_ior       * recent_fixation_mask(p)   # inhibition of return,30 tick 内已注视的位置压制

next_fixation = argmax_p next_fixation_score(p)
```

```yaml
vision_sensor:
  saccade_w_saliency: 0.30           # @experimental
  saccade_w_uncertainty: 0.30        # @experimental
  saccade_w_task: 0.20               # @experimental
  saccade_w_surprise: 0.20           # @experimental
  saccade_w_ior: 0.50                # @experimental
  ior_decay_ticks: 30                # @experimental
```

Phase 19.0a 实现 saliency + uncertainty 两项;task/surprise/IOR 在 Phase 19.0b 完成 Layer-3 后开启;留接口位 + 早期 stub 返回 0。

### 2.10 S5 — 听觉 echoic 4 秒硬墙

```
auditory_focus_constraint:
  - 当前输入流任意时间位置可作为听焦点
  - 过去 ≤ 4 秒(echoic_buffer)的位置可作为听焦点,标记 epistemic_source="REMEMBERED_RECENT"
  - 过去 > 4 秒的位置不能直接听焦点
  - 想"回放"必须走 R_proto_aud,标记 epistemic_source="IMAGINED_PROTOTYPE_SKETCH"

红线 RL-19v1d-S5-01: 听焦点时间坐标 t_focus 必须满足 t_now - t_focus <= 4 sec
                     否则 raise InvalidAuditoryFocus
```

```yaml
audio_sensor:
  echoic_buffer_seconds: 4.0          # @structural - 心理学 echoic memory 经验值
```

### 2.11 S6 — Phase 融合降级为 audit

```
AuditoryCanvas 核心字段:
  canvas_mag                # magnitude spectrogram, 主认知证据
  canvas_envelope           # RMS 包络
  canvas_pitch              # F0 traj
  canvas_onset_salience     # onset 序列
  canvas_timbre             # spectral moments + contrast
  canvas_phase              # 仅 audit, 不参与认知决策

红线 RL-19v1d-S6-01: SDPL packet 不读取 canvas_phase
                    Layer-2/3 向量库不存 phase 信息
                    canvas_phase 只用于 Griffin-Lim 重建展示
```

R_proto_aud Step 6 改用 envelope + onset + pitch 主导,phase 留作 Griffin-Lim 的最后展示步,**不进认知证据流**。

---

## 3. 三层 AP-Native 向量库(架构核心)

### 3.1 总览

```
┌─────────────────────────────────────────────────────────────────┐
│ Layer-1 PerceptVector Store (episodic 记忆)                   │
│   - 每张图经感受器后的 opaque (V0..V9) vec,27838 维           │
│   - 同时存 canvas_state_block (4 维) 与 render_audit_block (8 维)│
│   - 来源 marker (epistemic_source / source_confidence)        │
│   - 累积上限: 100 k 实例 (LRU + 重要性加权)                    │
│   - 持久化: vector_db_disk("data/percept_vectors/")             │
│   入口: B 召回                                                  │
└─────────────────────────────────────────────────────────────────┘
            ↑                              ↓
       存进新感受             召回(高精度,慢,~5 ms × K)
            ↑                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Layer-2 PartPrototype Store (无语义视觉/听觉碎片)            │
│   - V3 LBP code patches (~512 entries)                          │
│   - V7 part prototypes (~1024 entries)                          │
│   - V6 shape codes (~128 entries)                               │
│   - A1 timbre codes (~512), A5 onset codes (~256) etc.          │
│   - 每 entry: opaque uuid + patch_vec + activation count       │
│   - 离线 + 在线 k-medoids 增量                                  │
│   入口: C 召回                                                  │
└─────────────────────────────────────────────────────────────────┘
            ↑                              ↓
   在线 k-medoids 增量            召回(快,~200 μs)
            ↑                              ↓
┌─────────────────────────────────────────────────────────────────┐
│ Layer-3 ConceptPrototype Store (习得 association)            │
│   - concept_uuid (opaque, 例 c_3f1a9b)                          │
│   - 关联 Layer-2 part_uuids 的 noisy-OR 权重 w_part            │
│   - 关联 Layer-1 episodic uuids 的 retrieval keys              │
│   - 跨模态绑定 (vision_uuid, audio_uuid, text_uuid)            │
│   - source-aware contribution weights w_source                 │
│   - 学习信号: 奖惩 (外+内) + 认知压最小化 (见 §8)              │
│                                                                 │
│   重要: Layer-3 知道 "c_3f1a9b 关联 part_4f2a + part_8b21",   │
│         但 Layer-3 自己不存 "apple" 这个名字 — 名字是另存       │
│         的 vocab SA 与 c_3f1a9b 的 association                  │
│                                                                 │
│   红线 RL-19v1d-L3-01: concept_uuid 不含类别名;名字关联存外    │
└─────────────────────────────────────────────────────────────────┘
            ↓
       识别 / R_proto / 内心画面 / 输出
```

### 3.2 B 召回 / C 召回(继承 APV2.1 双速召回经验)

**C 召回 — Layer-2 直查**(快,~200 μs):

```
def C_recall_visual(query_feature: V0_V9_vector) -> list[concept_uuid]:
    """
    1. 从 query 提取 V3 LBP codes + V7 part hashes + V6 shape code
    2. 在 Layer-2 codebooks 查最近邻 part_uuids (top-K_C per channel)
    3. 在 Layer-3 association 表查这些 part_uuids 共同覆盖到的 concept_uuids
    4. 返回 top-K_concept candidates with rough activation scores
    """
```

`vision_sensor.c_recall_top_k_per_channel = 8` @experimental
`vision_sensor.c_recall_top_k_concept = 5` @experimental

**B 召回 — Layer-1 精算**(慢,~5 ms × K):

```
def B_recall_visual(query_feature: V0_V9_vector, candidate_concepts: list[concept_uuid]) -> list[ConceptScore]:
    """
    对 C 召回返回的每个 candidate concept:
      1. 从 Layer-3 取该 concept 的 episodic_keys (Layer-1 中代表 instances)
      2. 在 Layer-1 上取这些 instances 的精确 V0..V9 vectors
      3. 用 Phase 19.2 拟人 Conf 公式 在 query × instances 上算分场把握感
      4. 加 Layer-3 source-aware weighting
      5. 返回 K × N 实例级 ConceptScore
    """
```

`vision_sensor.b_recall_episodic_per_concept = 10` @experimental
**总打分量** = K_concept × N_episodic = 5 × 10 = 50 实例,远小于全 Layer-1 暴力。

### 3.3 Layer-1 PerceptVector 增量与衰减

```
Layer-1 容量管理:
  capacity = 100000 (vision) + 50000 (audio)  @scenario_tuneable
  插入规则: 新 PerceptVector 写入,带 importance_score
  importance_score = surprise + reward_magnitude + Conf_at_acquisition
  LRU + importance-weighted: 容量满时,丢 importance × recency 最低
  红线 RL-19v1d-L1-01: held-out 标记的 PerceptVector 永不进 Layer-3 association 学习
```

### 3.4 Layer-2 在线 k-medoids 增量

```
def online_kmedoids_update(layer2_codebook, new_feature_vec, channel):
    """
    每 N 张图触发一次 (N=100 默认)
    1. 找最近 medoid
    2. 若距离 > theta_new_medoid → 提议新 medoid (容量未满则接受;满则需替换最弱的)
    3. 否则: 该 medoid 的 patch_vec 增量平均更新(指数移动平均)
    """
    pass
```

`vision_sensor.layer2_update_every_n_obs = 100` @scenario_tuneable
`vision_sensor.layer2_new_medoid_threshold = 0.4` @experimental
`vision_sensor.layer2_ema_alpha = 0.05` @experimental(每次更新只动 5%)

---

## 4. R_proto / R_sketch 重写 — 走三层向量库

### 4.1 R_sketch 重写(对接 Layer-1)

```python
def R_sketch(query_input_trace_hash, canvas: SensoryCanvas, target_size):
    """
    sensory_sketch 模式:
    - 主要从 SensoryCanvas (来自当前输入感受) 取像素
    - 可选叠加 Layer-1 召回的相似 episodic vectors 的 canvas
      但叠加权重严格按 source_reliability(同图反复看过的相似实例可加大置信)
    - 不调用 Layer-3 ConceptPrototype
    红线 RL-19v1d-Rsketch-01: 禁止读取 Layer-3 — sketch 是感知不是想象
    """
```

### 4.2 R_proto 重写(对接 Layer-3)

```python
def R_proto(concept_uuid, target_size):
    """
    prototype_imagination 模式:
    1. 从 Layer-3 取 concept 的 part_uuid associations + 权重 w_part
    2. 对每个 part_uuid:
       - 从 Layer-2 取其 patch_vec
       - 按 w_part * activation_strength 决定 stamp 强度
    3. 用 v1c §6 的 6 步算子合成 64×64 内心想象图:
       Step 1 颜色: 从 concept 关联的 V1/V2 prototype 取主色
       Step 2 形状: 从关联的 V6 shape code 取参数
       Step 3 边缘: 从关联的 V4 HOG profile 反求
       Step 4 纹理: 按 w_part 比例 stamp Layer-2 LBP codes
       Step 5 部件: 按 w_part 比例 stamp Layer-2 V7 parts
       Step 6 fg/bg: 从 concept 的 V9 KL profile 反求
    4. 输出 R_proto image, source=IMAGINED_PROTOTYPE_SKETCH
    红线 RL-19v1d-Rproto-01: 不调用 Layer-1 episodic instances(否则就在复刻某张训练图)
    红线 RL-19v1d-Rproto-02: 不读取 evaluator label / filename
    """
```

### 4.3 这样自然避免 Codex B5 模板泄漏

- Layer-2 是无标签 opaque codes
- Layer-3 是习得 association
- R_proto 通过 association 合成,**不**直接按类别检索 codebook
- 删除 Layer-3 → R_proto 不能产生"苹果",只能产生"随机部件堆"
- 删除 Layer-1 → R_sketch 失效但 R_proto 仍能从 Layer-3 + Layer-2 合成想象

---

## 5. 识别走 C+B 召回 + 拟人 Conf(替换全维 L2)

### 5.1 总流程

```python
def recognize(query_input):
    # 1. 感受器
    feature_vec = visual_receptor(query_input)  # 27838 维
    canvas      = update_sensory_canvas(canvas, feature_vec)

    # 2. C 召回 (Layer-2 → Layer-3)
    candidate_concepts = C_recall_visual(feature_vec)  # ~5 candidates, 200 μs

    # 3. B 召回 (Layer-3 → Layer-1 精算)
    concept_scores = B_recall_visual(feature_vec, candidate_concepts)  # ~50 instances, 25 ms

    # 4. 拟人 Conf 公式(v1a §4 + v1b raw_confidence/decision_tier 分离 + v1b ν_object/ν_context)
    raw_conf_per_concept = compute_human_like_confidence(feature_vec, concept_scores)
    decision_tier        = TierMap(raw_conf_per_concept, nu_object, nu_context)

    # 5. 输出
    output_text = pick_styled_response(decision_tier, top_concepts)  # Phase 16 styled corpus
    return decision_tier, output_text, concept_scores
```

### 5.2 拟人 Conf 公式接入 Layer-3 source-aware

```
raw_confidence(c | query) =
    prototype_pull(c | query)         # noisy-OR over active diagnostic cues
  × coherence(c | query)               # 跨通道一致
  × source_quality(query)              # focus + segmentation + occlusion + freshness
  × margin_against_nearest_negative(c) # 最近竞争类的 margin
  × layer3_source_weight(c)            # Layer-3 SDPL contribution × source reliability
```

`vision_sensor.layer3_weight_floor = 0.3` @experimental — 即使 Layer-3 weight 低,raw_confidence 也不会被压成 0(避免新概念被冷启动锁死)。

### 5.3 完全不走全维 L2

红线:

```
RL-19v1d-Recog-01: recognize() 不允许 numpy.linalg.norm(query_feature_full - any_prototype_feature_full)
                   只允许 channel-wise distance + noisy-OR + B 召回的 K × N 拟人 Conf
```

---

## 6. 扫视策略(吸收 Codex S4)

完整 v1d 公式:

$$
\mathrm{score}(p) = w_{\mathrm{sal}} \cdot \mathrm{saliency}(p) + w_{\mathrm{unc}} \cdot \mathrm{uncertainty}(p) + w_{\mathrm{task}} \cdot \mathrm{task\_drive}(p) + w_{\mathrm{surp}} \cdot |\Delta_{\mathrm{pred}}(p)| - w_{\mathrm{ior}} \cdot \mathrm{recent\_fixation\_mask}(p)
$$

其中各项:

- **saliency**: V0 边缘强度 + V1 颜色对比度 + (运动通道留 Phase 19.6,Phase 19.0a 设 0)
- **uncertainty**: $1 - \mathrm{canvas\_confidence}(p)$
- **task_drive**: 当前 attention goal vector(来自上层 deliberative;Phase 19.0a 默认 = 主体掩码内为 1,外为 0.3)
- **surprise**: $|\mathrm{prediction\_overlay}(p) - \mathrm{sensory\_canvas}(p)|$(B4 已分离的两个 canvas 之差)
- **IOR**: 30 tick 衰减的最近注视位置 mask

Phase 19.0a 仅实现 saliency + uncertainty(简化版);task_drive / surprise / IOR 等 Phase 19.0b 三层向量库就绪后开启。

---

## 7. 听觉对应修正(吸收 Codex S5/S6)

已分别落到 §2.10(echoic 硬墙)+ §2.11(phase 降 audit)。Layer-1/2/3 听觉版完全对偶视觉版,术语对应:

| 视觉 | 听觉 |
|---|---|
| PerceptVector (V0..V9) | AudPerceptVector (A0..A8) |
| Part codes (V3 LBP, V7 parts, V6 shape) | Aud codes (A1 timbre, A5 onset, A6 pitch tags) |
| ConceptPrototype | ConceptPrototype(跨模态共享 concept_uuid,见 §9.9) |

---

## 8. 学习信号 — 奖惩 + 认知压(银子老师明确修正)

### 8.1 总公式

Layer-3 的 SDPL contribution weights $w_{\mathrm{source}}(s, c)$ 和 association weights $w_{\mathrm{part}}(p, c)$ 的增量更新由两个**完全 AP-native** 信号驱动 — **不是用户反馈直接覆盖**:

$$
\boxed{
\Delta w = \eta \cdot \left[\underbrace{\alpha_R \cdot R_{\mathrm{net}}}_{\text{奖惩信号(外+内汇合)}} - \underbrace{\alpha_E \cdot \nabla_w \mathcal{E}_{\mathrm{cog}}}_{\text{认知压最小化}}\right]
}
$$

### 8.2 奖惩信号 $R_{\mathrm{net}}$

**外源奖惩** $R_{\mathrm{ext}}$:
- 用户说"对"→ $R_{\mathrm{ext}} = +1$
- 用户说"不对"→ $R_{\mathrm{ext}} = -1$
- 用户无反馈 → $R_{\mathrm{ext}} = 0$

**内源奖惩** $R_{\mathrm{int}}$(AP 自己产生):
- 期待与实际匹配("我以为是橙子,看清楚后确实是橙子") → $R_{\mathrm{int}} = +\rho_{\mathrm{match}}$
- 违和感("我以为是苹果,看清楚后形状像香蕉") → $R_{\mathrm{int}} = -\rho_{\mathrm{conflict}}$
- 期待压力释放("一直猜不出,终于看清是橙子") → $R_{\mathrm{int}} = +\rho_{\mathrm{release}}$
- 未消解的违和感累积 → $R_{\mathrm{int}}$ 持续负值

汇合:

$$
R_{\mathrm{net}} = \gamma_{\mathrm{ext}} \cdot R_{\mathrm{ext}} + \gamma_{\mathrm{int}} \cdot R_{\mathrm{int}}
$$

`vision_sensor.gamma_ext = 0.6` @experimental(外源略大)
`vision_sensor.gamma_int = 0.4` @experimental
`vision_sensor.rho_match = 0.3, rho_conflict = 0.5, rho_release = 0.4` @experimental

### 8.3 认知压 $\mathcal{E}_{\mathrm{cog}}$

最小化的预测误差(free energy / surprise 量):

$$
\mathcal{E}_{\mathrm{cog}} = \sum_{c \in \mathrm{active\_concepts}} \mathrm{Conf}(c) \cdot \|\mathrm{prediction\_overlay}_c - \mathrm{sensory\_canvas}\|_{\mathrm{channel-wise}}^2
$$

也就是:对每个当前活跃的 concept,它的预测画面与实际感知画面的差距,按 Conf 加权求和。

性质:
- 高 Conf 但预测错得离谱 → $\mathcal{E}_{\mathrm{cog}}$ 大 → 强烈推动 $w$ 调整
- 低 Conf 且预测错 → $\mathcal{E}_{\mathrm{cog}}$ 小(系统知道自己不确定,不用大调)
- 高 Conf 且预测对 → $\mathcal{E}_{\mathrm{cog}}$ 接近 0,系统不变

### 8.4 source 分摊(配合 v1b §3)

奖惩 + 认知压算出 $\Delta w$ 后,按 source contribution 自动分摊到不同 source 路径:

$$
\Delta w_{\mathrm{source}}(s) = \mathrm{credit}(s) \cdot \Delta w
$$

$$
\mathrm{credit}(s) = \omega_s \cdot \sigma_s / \sum_{s'} \omega_{s'} \sigma_{s'}
$$

(继承 v1b §3.2,$\omega_s$ 是数值差分贡献,$\sigma_s$ 是 source confidence)

### 8.5 关键约束

```
RL-19v1d-Learn-01: 用户反馈不允许直接覆盖 Layer-3 weights
                   必须经过 §8.1 公式,作为 R_ext 输入

RL-19v1d-Learn-02: 内源奖惩 R_int 由认知压 + Phase 9.6 共情 + Phase 8 marker 系统产生
                   不允许凭空注入

RL-19v1d-Learn-03: 高 Conf + 持续预测错 必须触发 R_int 负值(违和感)
                   否则系统会陷入"自信地一直错"

RL-19v1d-Learn-04: held-out PerceptVector 不参与认知压计算
                   不污染训练集学习
```

### 8.6 Phase 9.6 / Phase 8.5 既有机制对接

| AP 既有 | Phase 19 学习信号中的角色 |
|---|---|
| Phase 8.5 cognitive_pressure | 直接对应 $\mathcal{E}_{\mathrm{cog}}$ 的实化形式 |
| Phase 8.10 EMPATHY_RESONANCE | 用户语气 + 反馈强度 → 调 $\gamma_{\mathrm{ext}}$ |
| Phase 9.6 共情 trust_promoted | 提高 $R_{\mathrm{ext}}$ 的强度 |
| Phase 11.4 deliberative | 期待压力的来源 |
| MISMATCH marker | 触发 $R_{\mathrm{int}}$ 的违和感 |
| NOVELTY marker | 触发 $\nu_{\mathrm{object}}$ 升高 + uncertainty 升高 |

也就是说,$R_{\mathrm{net}}$ 和 $\mathcal{E}_{\mathrm{cog}}$ **不是新机制**,是把已有的 marker / pressure / 共情 / deliberative 机制汇成 Layer-3 学习信号的统一接口。

---

## 9. 拟人扩展特性的三层架构定位

### 9.1 X1 周边视觉颜色/对比/运动/边缘衰减曲线不同

V0 每通道独立衰减常量(替代 v1c 的统一 ClarityField):

```yaml
vision_sensor:
  clarity_sigma_color_px: 32           # @experimental - 颜色周边可见性较强
  clarity_sigma_contrast_px: 28        # @experimental
  clarity_sigma_motion_px: 48          # @experimental - 周边运动敏感(Phase 19.6 才用)
  clarity_sigma_edge_px: 20            # @experimental - 边缘焦点窄
```

每通道独立 sigma → 拟人化各通道周边敏感度不同。

### 9.2 X2 Gestalt 组织

Layer-2 PartPrototype 之间维护**关联图**:

```
gestalt_edges = {
    (part_a, part_b): {
        "proximity_score": float,        # 共现时距离常一致
        "continuity_score": float,       # 共现时方向连续
        "closure_score": float,          # 共现时形成闭合
        "similarity_score": float,       # 视觉特征相似
    }
}
```

构建方式:Layer-1 PerceptVector 在线 mining。

### 9.3 X3 Figure-ground 分离

继承 v1c §3.3 multi-hypothesis mask + Layer-2 part 关联是否在 fg/bg:

```
part.associated_zone ∈ {"fg", "bg", "edge"}
```

### 9.4 X4 颜色/大小/形状恒常性

Layer-3 ConceptPrototype 内存"变体范围":

```
concept_uuid = "c_3f1a9b"   # 比如代表 "橙子"
shape_range: (gamma_min=0.7, gamma_max=1.0)        # 圆形度范围
color_range_hsv:
    h: (0.05, 0.20)                                 # 橙色主区
    h_extended: (0.20, 0.35)                        # 绿橙也接受(扩展)
size_range_normalized: (0.05, 0.4)                  # 占画面比例范围
```

绿橙子的 H 落在 extended 区 → Conf 略降但仍归到 c_3f1a9b → 输出"像是橙子"。

### 9.5 X5 物体持存

Layer-1 PerceptVector 跨 tick 持久:

```
PerceptVector lifecycle:
  - 生成: 感受器输出
  - 衰减: real_energy *= exp(-1/tau)
  - 重激活: 同 input_trace_hash 再来时重置 real_energy
  - 物体 ID binding: Layer-3 维护 object_uuid → list of PerceptVector_uuids
  - 即使物体被遮挡(看不到几 tick),object_uuid 仍在 Layer-3 维持低权重活跃
```

### 9.6 X6 预测编码(source-separated)

继承 B4 修正:

```
prediction_overlay = R_proto(top concept from Layer-3 expected)
                   source = "INFERRED"
sensory_sketch     = R_sketch(canvas)
                   source = "PERCEIVED_SENSORY_SKETCH"
visualizer 可叠加显示,audit 必能拆开
surprise = prediction_overlay - sensory_sketch  → Phase 19.0b 扫视项之一
```

### 9.7 X7 change blindness / inattentional blindness

```
仅 clarity > clarity_min_for_update 的像素才更新 PerceptVector / Layer-1
周边低 clarity 区不进入 Layer-1
红线 RL-19v1d-X7-01: 周边变化无更新 SA 注入 → 实现拟人 inattentional blindness
```

`vision_sensor.clarity_min_for_update = 0.3` @experimental

### 9.8 X8 听觉 masking / 等响曲线 / 双耳定位

A0 编码内置:

```yaml
audio_sensor:
  masking_filter_enabled: true           # @structural - 时频 masking 模型
  equal_loudness_contour: "iso226"       # @structural - ISO 226 等响曲线
  binaural_stereo_support: true          # @structural - 双声道时定位
  binaural_itd_max_us: 660               # @structural - 双耳时间差最大值
```

Phase 19.1a 必落地。

### 9.9 X9 多模态时间同步绑定

Layer-3 跨模态 association(关键):

```
ConceptPrototype c_3f1a9b 同时关联:
    vision_episodics:  [pv_v_3a9, pv_v_8b1, ...]
    audio_episodics:   [pv_a_2f1, pv_a_9c4, ...]
    text_vocab_sa_ids: [sa_vocab_orange_3, ...]

时间同步绑定:
    若 vision PerceptVector 在 tick t 入,audio 在 tick t+Δt 入,Δt < binding_window_ticks
    且两者激活了同 concept → association 加强
    否则 → 各模态独立
```

`multimodal.binding_window_ticks = 6` @experimental(0.6 秒,接近人类多模态同步窗口)

### 9.10 X10 McGurk 冲突

reliability-weighted cue integration:

$$
\mathrm{Conf}(c \mid x_{\mathrm{vis}}, x_{\mathrm{aud}}) = \frac{r_{\mathrm{vis}} \cdot \mathrm{Conf}(c \mid x_{\mathrm{vis}}) + r_{\mathrm{aud}} \cdot \mathrm{Conf}(c \mid x_{\mathrm{aud}})}{r_{\mathrm{vis}} + r_{\mathrm{aud}}}
$$

$r_{\mathrm{vis}}, r_{\mathrm{aud}}$ = 各模态当前可信度。视听冲突时,可信度高的占主。这就**自然**产生 McGurk 式拟人错觉。

---

## 10. 新的 Phase 19 子阶段顺序

```
Phase 19.0  (substrate ✓)                  — 已落地
Phase 19.0b (三层向量库 substrate)         — v1d 新增,必须先做
Phase 19.0a (foveated visual repair)       — 基于 19.0b 上做
Phase 19.2  (拟人 Conf 接入三层)
Phase 19.3a / 19.3b (视觉 probe)
Phase 19.1  (audio substrate + Layer-1/2 听觉版)
Phase 19.1a (foveated audio repair)
Phase 19.4a / 19.4b (听觉 probe)
Phase 19.5  (source-aware feedback + 奖惩 + 认知压学习)
Phase 19.6  (active perception 扫视升级,Layer-3 task_drive)
```

总顺序:
**19.0 ✓ → 19.0b → 19.0a → 19.2 → 19.3a → 19.3b → 19.1 → 19.1a → 19.4a → 19.4b → 19.5 → 19.6**

---

## 11. 新增 Deliverable Gates

### Phase 19.0b 三层向量库(15 条)

| Gate |
|---|
| G-19.0b-01 Layer-1 PerceptVector store 实现,可读写,持久化到磁盘 |
| G-19.0b-02 Layer-2 PartPrototype store 实现,opaque uuid,无标签 |
| G-19.0b-03 Layer-3 ConceptPrototype store 实现 |
| G-19.0b-04 C 召回 200 μs p95 |
| G-19.0b-05 B 召回 5 ms × K p95 |
| G-19.0b-06 在线 k-medoids 增量算法实现(每 100 obs 触发) |
| G-19.0b-07 Layer-1 LRU + importance 容量管理 |
| G-19.0b-08 Layer-2 codebook 严格无标签(grep 测) |
| G-19.0b-09 删除 Layer-3 后 R_proto 不能产生 "苹果" 但仍能产生 part heap(消融测) |
| G-19.0b-10 held-out PerceptVector 标记不进 Layer-3 学习(grep + 流程测) |
| G-19.0b-11 跨模态 ConceptPrototype 实现(vision + audio + text vocab 三向绑定) |
| G-19.0b-12 持久化到 data/percept_vectors / data/part_codes / data/concept_prototypes |
| G-19.0b-13 红线 RL-19v1d-B1/B5/L1/L3/Rsketch/Rproto/Recog 全过 |
| G-19.0b-14 治理通过 |
| G-19.0b-15 真名零命中 |

### Phase 19.0a v1d 增量(在 v1c §11 基础上加)

| Gate |
|---|
| G-19.0a-v1d-21 R_sketch 不读 Layer-3(grep) |
| G-19.0a-v1d-22 R_proto 不读 Layer-1 episodic(grep) |
| G-19.0a-v1d-23 prediction_overlay 与 sensory_sketch 在 audit 可拆开 |
| G-19.0a-v1d-24 焦点半径 viewport 归一化测试(64/256/1024 px 图,r0 各不同) |
| G-19.0a-v1d-25 ClarityField floor 不重复加(单测) |
| G-19.0a-v1d-26 multi-tick gate 改 normalized_gain / coverage_gain / clarity-weighted SSIM 三选一 |
| G-19.0a-v1d-27 saliency + uncertainty 扫视项实现(task/surprise/IOR 留 stub) |
| G-19.0a-v1d-28 周边视觉各通道独立 clarity_sigma 测 |
| G-19.0a-v1d-29 clarity < 0.3 区不更新 PerceptVector(change blindness 测) |

### Phase 19.5 v1d 重写(奖惩 + 认知压学习)

| Gate |
|---|
| G-19.5-v1d-01 R_net = γ_ext · R_ext + γ_int · R_int 公式实现 |
| G-19.5-v1d-02 R_int 由 MISMATCH marker / cognitive_pressure / Phase 9.6 共情产生(无凭空注入) |
| G-19.5-v1d-03 E_cog 按 Conf 加权 channel-wise 距离平方 |
| G-19.5-v1d-04 Δw 按 §8.4 source 分摊 |
| G-19.5-v1d-05 用户反馈不直接覆盖 Layer-3 weights(red line + 流程测) |
| G-19.5-v1d-06 高 Conf + 持续预测错 → R_int 持续负值,Δw 持续修正,5 tick 内 Conf 下降 |
| G-19.5-v1d-07 held-out PerceptVector 不参与 E_cog |
| G-19.5-v1d-08 反馈隔离测试(继承 v1b §3.5 G-19v1b-Fb-04)|

---

## 12. 算力 / 内存核算(家用机可行性)

按 §0 数学,单 turn 完整看图 + 识别 + 输出:

| 项 | 时间 | 内存峰值 |
|---|---|---|
| 感受器 (V0..V9) 27838 维 | 150 ms | 30 MB |
| Sensory Canvas update | 10 ms | 4 MB (canvas 持续) |
| R_sketch | 5 ms | 1 MB |
| C 召回 (Layer-2) | 200 μs | 10 MB (codebook 常驻) |
| B 召回 (Layer-1 K×N) | 25 ms | 5 MB (本次 working set) |
| 拟人 Conf (Phase 19.2) | 1 ms | < 1 MB |
| Layer-3 association 查找 | 5 ms | 10 MB (常驻) |
| R_proto (从 Layer-3 反向合成) | 50 ms | 1 MB |
| 输出 styled corpus 选择 | 1 ms | < 1 MB |
| **总单 turn** | **≈ 250 ms** | **+ 24 MB 临时 / 60 MB 常驻** |

持续运行:
- Layer-1 持久存储:1 万实例 × 30 MB = 300 MB (磁盘)
- Layer-2 codebook 常驻:10 MB
- Layer-3 association 常驻:50 MB
- SensoryCanvas 常驻:4 MB
- 工作内存峰值:< 100 MB

**家用机** (16 GB RAM, 4 核 CPU, SSD) 完全跑得动。10 tick 看清一张图 = 2.5 秒,符合您"看几秒"的预期。

---

## 13. 边界

- Phase 19.0b 是 substrate,**只**搭三层向量库 + B/C 召回 + 在线 k-medoids;不调任何外部库
- Layer-1/2/3 持久化用 numpy npz + json,不用 FAISS / Annoy / Milvus(外部依赖)
- 在线 k-medoids 用纯 numpy 增量实现,不调 sklearn
- 跨模态绑定 Phase 19.0b 实现接口,Phase 19.4 完成听觉 Layer-1/2 后才真正使用
- McGurk 等多模态拟人错觉测在 Phase 19.4b 之后做
- "近乎 100% 拟人"是目标不是当 phase 验收门槛 — Phase 19 完成意味着拟人**底座**就绪,**alpha 公测**前会按用户感受继续 tune

---

## 14. 落地优先级建议(给 Codex)

```
Week 1: Phase 19.0b
  Day 1-2: Layer-1 PerceptVector store + 持久化
  Day 3:   Layer-2 PartPrototype store + 在线 k-medoids
  Day 4:   Layer-3 ConceptPrototype + association
  Day 5:   B 召回 / C 召回 + 跨模态绑定接口
  Day 6:   持久化 + 容量管理 + 红线测试
  Day 7:   全量回归 + Final Report

Week 2: Phase 19.0a v1d
  按 v1c + v1d 合读
  R_sketch / R_proto 走 §4 重写
  saccade 用 saliency + uncertainty 简化版
  Codex Blocker/Serious 11 项落地

Week 3: Phase 19.2
  拟人 Conf 公式接 Layer-3 + source-aware

Week 4: Phase 19.3a/b
  Stratified LOO 12 张图,识别管线打通

Month 2: 19.1, 19.1a, 19.4a/b
Month 3: 19.5, 19.6
```

效果优先,性能次之 — 但底座算下来 250 ms / turn 已经在家用机舒适区。

---

## 15. 给 Codex 的对抗审查指引

请重点查:

1. §3 三层架构边界是否清晰(Layer-1 episodic vs Layer-3 concept 不能模糊)
2. §4 R_sketch / R_proto 数据流是否真分离(grep 测)
3. §5 拟人 Conf 是否真不走全维 L2(grep test)
4. §8 奖惩 + 认知压公式是否真在动 Layer-3,不通过用户反馈直接 patch(流程测)
5. §9 拟人扩展特性是否落到合理的层(不要把 Gestalt 放到 Layer-1 感受器)
6. §12 算力核算是否乐观(若有实测偏差,告诉我)
7. 维度核对:Layer-1 v1d 是 27838(B1 修)+ canvas_state_dim 4 独立

---

## 16. 署名

- 原架构设计:银子老师(笔名)
- v1d 数学修订与三层架构:Claude (Anthropic) 在银子老师明确的"近乎 100% 拟人 + B/C 召回 + 本地在线嵌入 + 奖惩 / 认知压学习"反馈下产出
- 落地:Codex 在 v1d 通过对抗审查后实施

End of Phase 19 v1d Errata.
