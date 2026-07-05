# APV3.0 Phase 19 v1c-Audio Errata — Foveated Listening, Multi-Tick Auditory Canvas, Saccadic Listening, and Channel-Based Sound Prototype Synthesis

Date: 2026-06-19
Author: Claude(架构),银子老师(风格定调与最终签收)
Status: 设计稿微修订(v1c errata 听觉对偶),叠加在 v1/v1a/v1b 之上。**Phase 19.1a 子阶段的设计正本**。
Trigger: 银子老师明确"音频也是,级别都比我想象中低" + "效果第一,先不要管性能"
Principle: 与 v1c 视觉对称 — **听觉焦点不从压缩波形采**,直接从原采样率原始波形采;其他时间段允许逐层降时间/频率分辨率
License intent: AGPL-3.0-or-later

---

## 0. 这一份做什么(一句话)

把听觉感受器升级到与视觉 v1c 同等深度 — **听觉焦点直采原采样率波形**,周边按时间/频率轴 dyadic 降分辨率;**ClarityField_aud** 在时频平面上分布;**AuditoryCanvas** 多 tick 累积让"听久了更清晰";**Saccadic Listening** 听觉焦点移动后拼出全段;**R_proto_aud** 严格用 A1..A8 全部 8 通道合成原型想象声音(不再只是 Griffin-Lim 出一个雾里的相)。

---

## 1. 听觉与视觉的同构映射

| 视觉 v1c | 听觉 v1c-Audio |
|---|---|
| 像素坐标 $(x,y)$ | 时频坐标 $(t, f)$(时间-频率平面) |
| 视焦点 $\mathbf{c}_t$ | 听焦点 $\mathbf{c}_t^{\mathrm{aud}} = (t_c, f_c)$ |
| 像素分辨率 $\rho$ | 时间分辨率 $\Delta t$ + 频率分辨率 $\Delta f$ |
| Foveated radial pyramid | Foveated time-frequency pyramid |
| ClarityField $\phi(x,y)$ | AudibilityField $\phi^{\mathrm{aud}}(t,f)$ |
| SensoryCanvas | AuditoryCanvas |
| Saccadic stitching | Saccadic listening |
| R_proto with V3-V9 | R_proto_aud with A1-A8 |

---

## 2. Native Foveated Time-Frequency Sampling(从原采样率直采)

### 2.1 核心原则

**不允许**先把原音频 down-sample 到固定采样率(如 8 kHz),再从 down-sample 后取听焦点。听焦点的时频窗口必须**直接从原采样率 16 kHz 波形 + 高频分辨率 STFT** 取;周边时频区才允许降分辨率。

### 2.2 时间金字塔 + 频率金字塔(双轴 dyadic)

对原波形 $A \in \mathbb{R}^{N_s}$($N_s = 16000$ samples/sec, 时长可变):

定义**时间锚** $t_c$(听焦点的时间位置,以 frame 计)+ **频率锚** $f_c$(听焦点的频率位置,以 mel/Hz 计)。

#### 2.2.1 时间金字塔(沿时间轴)

$$
\mathcal{T}_n = \{t : 2^{n-1} \cdot \Delta t_0 \leq |t - t_c| < 2^n \cdot \Delta t_0\}, \quad n = 0, 1, \dots, L_t - 1
$$

- $\Delta t_0 = $ `audio_sensor.foveal_base_time_ms` = 50 ms(@structural)
- $L_t = $ `audio_sensor.foveal_time_layer_count` = 5(@structural)
- 层 0:听焦点 ±50 ms 共 100 ms,用**原始 16 kHz 采样率 + hop 64 STFT 高时间分辨率**(每 4 ms 1 frame)
- 层 1:扩展环 50-100 ms,降 hop 128(每 8 ms 1 frame)
- 层 4:扩展到 800 ms 外,hop 1024(每 64 ms 1 frame)

#### 2.2.2 频率金字塔(沿频率轴)

$$
\mathcal{F}_m = \{f : 2^{m-1} \cdot \Delta f_0 \leq |f - f_c| < 2^m \cdot \Delta f_0\}, \quad m = 0, 1, \dots, L_f - 1
$$

- $\Delta f_0 = $ `audio_sensor.foveal_base_freq_hz` = 30 Hz(@structural)
- $L_f = $ `audio_sensor.foveal_freq_layer_count` = 5(@structural)
- 层 0:听焦点 ±30 Hz,密集分辨率 1 mel/bin
- 层 4:扩展到 480 Hz 外,粗 16 mel/bin

#### 2.2.3 时频金字塔联合

$\mathcal{TF}_{n,m} = \mathcal{T}_n \cap \mathcal{F}_m$,共 $L_t \times L_f = 25$ 个 tile。每 tile 给出:

$$
\mathrm{TF\_tile}_{n,m} = \{\mathrm{STFT}_{n,m}(t, f) : (t,f) \in \mathcal{TF}_{n,m}\}
$$

### 2.3 A0 升级:Native Foveated Time-Frequency Pyramid

替换 v1a §6.1 的 A0(原 v1a 是固定 Gammatone + STFT bank,均匀分辨率)。

| Tile | 来源 | 维度 |
|---|---|---|
| 25 个 (time, freq) tiles,每 tile 32×32 mag bin | 25 tiles × 32 × 32 | 25600 |
| 每 tile 一份 phase summary(平均 phase + 标准差) | 25 × 2 | 50 |
| 整段全局 onset salience 高时间分辨率 | 4 ms × 1000 ms / max_duration_sec | 250 |
| 整段全局 F0 高分辨率轨迹 | per frame F0 + voicing | 500 |
| Time-frequency cross-layer correlation matrix | 25×25 / 2 = 300 | 300 |

A0 子总 = **26700**(比 v1a 旧版 16378 多)。

新常量:

```yaml
audio_sensor:
  foveal_base_time_ms: 50              # @structural
  foveal_base_freq_hz: 30              # @structural
  foveal_time_layer_count: 5           # @structural
  foveal_freq_layer_count: 5           # @structural
  a0_tile_size: 32                     # @structural
  feature_vector_dim: 30501            # @structural - 20179 - 16378 + 26700 (+ canvas state)
```

---

## 3. AudibilityField — 时频清晰度连续场

### 3.1 数学定义

听焦点 $(t_c, f_c)$ 在 tick $t$ 的 AudibilityField:

$$
\boxed{
\phi^{\mathrm{aud}}_t(t, f) = \exp\left(-\frac{(t - t_c)^2}{2 \sigma_t^2} - \frac{(f - f_c)^2}{2 \sigma_f^2}\right) + \phi_{\min}^{\mathrm{aud}}
}
$$

- $\sigma_t = $ `audio_sensor.clarity_time_sigma_ms` = 80(@experimental)
- $\sigma_f = $ `audio_sensor.clarity_freq_sigma_hz` = 50(@experimental)
- $\phi_{\min}^{\mathrm{aud}} = $ `audio_sensor.clarity_floor_aud` = 0.08(@structural)

### 3.2 多 fixation 累积

与 v1c §3.2 同构:

$$
\phi^{\mathrm{aud}}_{\mathrm{multi}}(t, f) = \max_{i \in \{1,\dots,k\}}\left[\phi^{\mathrm{aud}}_{t_i}(t, f) \cdot \exp\left(-\frac{t_{\mathrm{now}} - t_i}{\tau_{\mathrm{aud,memory}}}\right)\right] + \phi_{\min}^{\mathrm{aud}}
$$

`audio_sensor.sensory_memory_tau_aud_ticks = 40` @experimental(听觉记忆比视觉略长,符合心理学 echoic memory 4 秒原则,4s × 0.1s/tick = 40 tick)。

### 3.3 应用 — 时频像素从哪层金字塔取

$$
(n^*, m^*)(t, f) = \arg\min_{n,m} \left| \phi^{\mathrm{aud}}(t, f) - 2^{-(n+m)} \right|
$$

焦点 $\phi \approx 1$ → $(0, 0)$(最高时间 + 最高频率分辨率)
$\phi \approx 0.25$ → $(1, 1)$ 或 $(0, 2)$ 或 $(2, 0)$
$\phi$ 极低 → 远层

---

## 4. AuditoryCanvas — 多 tick 累积模型

### 4.1 状态

```python
@dataclass
class AuditoryCanvas:
    canvas_mag: np.ndarray              # T_c × F_c, float [0,1], 累积 mag spectrogram
    canvas_phase_mean: np.ndarray       # T_c × F_c, float [-π,π], phase 平均
    canvas_clarity: np.ndarray          # T_c × F_c, float [0,1]
    canvas_confidence: np.ndarray       # T_c × F_c, float [0,1]
    canvas_freshness: np.ndarray        # T_c × F_c
    last_fixation_tf: tuple[float, float]
    tick: int
    # 关键:Canvas 时频分辨率 = 原音频 STFT 在 16 kHz / hop=64 下的网格
```

`audio_sensor.canvas_match_native = true` @structural。

### 4.2 PatchFusion(同 §v1c §4.3 Bayesian blending,改成 mag + phase 分别融合)

$$
\mathrm{canvas\_mag}'(t,f) = \frac{w_{\mathrm{old}} \cdot \mathrm{canvas\_mag}(t,f) + w_{\mathrm{new}} \cdot \mathrm{patch\_mag}(t,f)}{w_{\mathrm{old}} + w_{\mathrm{new}} + \epsilon}
$$

Phase 用**circular mean**(防 ±π 边界跳变):

$$
\mathrm{canvas\_phase}'(t,f) = \mathrm{atan2}\left(w_{\mathrm{old}} \sin(\mathrm{old}) + w_{\mathrm{new}} \sin(\mathrm{new}),\; w_{\mathrm{old}} \cos(\mathrm{old}) + w_{\mathrm{new}} \cos(\mathrm{new})\right)
$$

### 4.3 多 tick 重建质量 gate

定义 STOI / mel-spec correlation / pitch contour correlation 在 AuditoryCanvas 上算(随声音家族):

**Gate 19.1a-MT-01**(单调):family-specific 指标 tick 间至多回退 0.03
**Gate 19.1a-MT-02**(累积):10 tick 后,指标至少提升 0.15

---

## 5. Saccadic Listening — 听焦点移动

### 5.1 移动策略

每 tick 由 attention 选下个 $(t_{c}, f_{c})$。Phase 19.1a 用确定性扫描:

```
1. 在 AuditoryCanvas 找 confidence 最低 + canvas_mag 高的时频区(最重要但听得最不清楚的部分)
2. 跳过那里做听焦点
3. 若整体覆盖率 > 0.7,以 30% 概率到 onset salience 高的位置(对应"哪里出现新声音"的拟人 startle 响应)
```

### 5.2 听焦点路径示例(口语片段)

对一段"你好"的录音:
- tick 1: 听焦点在第一个音节起始(辅音 "ni")— 取得高频高时间分辨率细节
- tick 2: 听焦点跳到尾音元音 "i" — 取得高频低分辨率
- tick 3: 听焦点跳到 "ha"
- tick 4: 听焦点跳到 "ao"
- tick 5: 听焦点回到整段中间最不清楚的过渡

多 fixation 后,AuditoryCanvas 的高 clarity 区覆盖了整段(saccadic listening = "我把整段听了一遍")。

### 5.3 Stitching gate

**Gate 19.1a-Stitch-01**:5 个不同 (t,f) fixation 后,高清区 $\{\phi > 0.5\}$ 覆盖比例 ≥ $2.5 \times$ 单 fixation。
**Gate 19.1a-Stitch-02**:5 fixation 后,family-specific 指标 ≥ 0.75(语音 STOI / 音乐 chroma cos / 自然 mel corr / 冲击 onset F1)。

---

## 6. Channel-Based Sound Prototype Synthesis(R_proto_aud 用 A1..A8 全部)

### 6.1 6 步算子(与视觉 §6 对偶)

```
Step 1: Spectral skeleton (用 A1 MFCC + A2 Chroma)
Step 2: Temporal envelope shaping (用 A5 Onset + A7 RMS multi-scale)
Step 3: Pitch overlay (用 A6 F0 + voicing)
Step 4: Texture / timbre overlay (用 A3 spectral moments + A8 spectral contrast)
Step 5: Sound part stamping (用 onset codebook,类似 V7 part stamping)
Step 6: Speech-noise contrast (用 A4 ZCR + A6 voicing)
```

### 6.2 Step 1 — Spectral Skeleton

由 A1 MFCC + A2 Chroma 反求 mel 谱 → 反 mel → STFT mag。

```python
mel_spec_estimate = inverse_dct(MFCC_delta_deltadelta)  # 已含动态
chroma_to_pitch  = chroma_to_pitch_class_distribution(A2)
spec_combined    = blend(mel_spec_estimate, chroma_to_pitch, weight_chroma=0.3)
```

### 6.3 Step 2 — Temporal Envelope Shaping(关键解决重建后能量包络均匀)

用 A7 多尺度 RMS 包络分别在 25 ms / 100 ms / 500 ms 时间尺度对 mag 谱施加调制:

```python
for scale_ms in [25, 100, 500]:
    envelope = A7_rms_envelope[scale_ms]
    spec_combined *= upsample(envelope, scale_ms / 4ms_per_frame)
```

A5 onset 序列在 onset 时刻 boost 5-8 kHz 高频(对应辅音 / 冲击):

```python
for onset_t in A5_onsets:
    spec_combined[onset_t - 4 : onset_t + 8, freq_5kHz:freq_8kHz] *= onset_boost
```

`audio_sensor.onset_boost = 1.5` @experimental

### 6.4 Step 3 — Pitch Overlay

A6 F0 + voicing 给出有声帧。对每 voiced frame 叠加 F0 及其 1-5 倍谐波:

```python
for frame_idx, (f0, voiced) in enumerate(A6_F0_traj):
    if voiced:
        for harmonic in [1, 2, 3, 4, 5]:
            freq_idx = round_to_bin(f0 * harmonic)
            spec_combined[frame_idx, freq_idx] += harmonic_amplitude(harmonic) * pitch_overlay_weight
```

`audio_sensor.pitch_overlay_weight = 0.35` @experimental

### 6.5 Step 4 — Texture / Timbre Overlay

A3 谱矩(centroid / spread / skewness / kurtosis)调整每 frame 的谱形状:

```python
for frame_idx in range(frames):
    centroid, spread, skew, kurt = A3[frame_idx]
    # 通过 centroid 决定主能量频段,通过 spread 决定带宽,
    # 通过 skewness 决定高频偏移,通过 kurtosis 决定峰锐度
    spec_combined[frame_idx] = apply_moment_shaping(spec_combined[frame_idx],
                                                     centroid, spread, skew, kurt)
```

A8 spectral contrast 给出 7 频带 peak-vs-valley 对比,boost 各频带 peak:

```python
for band_idx, contrast in enumerate(A8_spectral_contrast):
    band_range = band_idx_to_freq_range(band_idx)
    spec_combined[:, band_range] *= (1.0 + contrast_boost * contrast)
```

`audio_sensor.contrast_boost = 0.3` @experimental

### 6.6 Step 5 — Sound Part Stamping

类比视觉 V7 part stamping,听觉 part 用 onset 周边的小 patch codebook(类似"咔哒"声、"嗡"声、"嘶"声等可重复的声学事件)。

```python
sound_part_codebook = load_offline_npz("data/aud_part_codebook_v1.npz")  # 小 patch 库
for part in top_k_sound_parts:
    stamp_t, stamp_f = part_position_in_canvas(part)
    stamp_patch = sound_part_codebook[part.id]   # 16 frame × 32 freq 小 patch
    spec_combined = alpha_blend_tf(spec_combined, stamp_patch, (stamp_t, stamp_f), part.alpha)
```

`audio_sensor.aud_part_codebook_path = "data/aud_part_codebook_v1.npz"` @structural

### 6.7 Step 6 — Speech-Noise Contrast

A4 ZCR + A6 voicing 判断是否语音,对语音段做 formant 突出 / 噪音段做 hiss-floor 填充:

```python
for frame_idx in range(frames):
    is_speech = A4[frame_idx] < zcr_speech_max AND A6_voicing[frame_idx]
    if is_speech:
        spec_combined[frame_idx] = enhance_formants(spec_combined[frame_idx])
    else:
        spec_combined[frame_idx] = add_noise_floor(spec_combined[frame_idx], noise_level)
```

### 6.8 最终重建

```python
def R_proto_aud(prototype_aud_features: PrototypeAudFeatures, duration_ms: int = 1000) -> AudioWaveform:
    spec = step1_spectral_skeleton(features.A1, features.A2)
    spec = step2_temporal_shaping(spec, features.A5, features.A7)
    spec = step3_pitch_overlay(spec, features.A6)
    spec = step4_texture_overlay(spec, features.A3, features.A8)
    spec = step5_part_stamping(spec, features.onset_parts)
    spec = step6_speech_noise_contrast(spec, features.A4, features.A6)
    # 最后 Griffin-Lim 反相
    waveform = griffin_lim(spec, n_iter=50)
    return waveform
```

**这才是真正的"内心声音想象"** — 谱形 + 包络 + 音高 + 音色 + 声学部件 + 语音/噪音对比,8 通道全用到。

---

## 7. 频率分场 Audibility Gate(替换 v1a §6.4 单一指标)

| 区 | 定义 | 门槛 |
|---|---|---|
| Foveal(听焦点核心) | $\|(t,f) - (t_c, f_c)\| < \Delta t_0 + \Delta f_0$ | $\mathrm{metric}_{\mathrm{focal}} \geq 0.75$ |
| Near | 中环 | $\mathrm{metric}_{\mathrm{near}} \geq 0.50$ |
| Far | 远环 | $\mathrm{metric}_{\mathrm{far}} \geq 0.30$ |

`metric` 按家族选(同 v1a §6.4):语音 STOI / 音乐 chroma / 自然 mel / 冲击 onset。

单调约束:$\mathrm{metric}_{\mathrm{focal}} > \mathrm{metric}_{\mathrm{near}} > \mathrm{metric}_{\mathrm{far}}$。

---

## 8. 状态池注入

```python
StateItem(
    sa_id=f"auditory_canvas::<canvas_state_hash>::{tick}",
    family="auditory_canvas",
    source="canvas_update_aud",
    metadata={
        "fixation_tf": (tc, fc),
        "patch_size_ms_hz": (50, 30),
        "patch_native_resolution": True,
        "clarity_mean": float,
        ...
    },
)

StateItem(
    sa_id=f"inner_voice_sketch::sensory::<input_trace_hash>::{tick}",
    family="inner_voice_sketch",
    source="reconstruction_R_aud_sketch",
    metadata={
        ...,
        "canvas_state_hash": <hex>,
        "metric_focal": float,
        "metric_near": float,
        "metric_far": float,
        "family": "speech" | "music" | "nature" | "impact",
    },
)
```

---

## 9. 红线扩展(听觉)

| RL | 描述 |
|---|---|
| RL-19v1c-aud-A01 | 听焦点 STFT **必须**用 hop=64 高时间分辨率(layer 0),不允许先 down-sample 到 8 kHz 再算 |
| RL-19v1c-aud-A02 | 周边层降时间分辨率只通过 box average 时间池化 + Mel 频带聚合,不调外部库 |
| RL-19v1c-aud-A03 | R_aud_sketch / R_aud_proto 不共享主函数 |
| RL-19v1c-aud-A04 | onset / part / LBP-equivalent 听觉 codebook 离线 deterministic |
| RL-19v1c-aud-A05 | metric_focal > metric_near > metric_far 单调必为硬 gate |
| RL-19v1c-aud-A06 | 多 tick 累积 metric 单调上升 |

---

## 10. Phase 19.1a Deliverable Gates(20 条,与 19.0a 平行)

| Gate |
|---|
| G-19.1a-01 双轴时频金字塔 5×5 = 25 tiles,层 0 = 16 kHz / hop=64 |
| G-19.1a-02 feature_vector_dim = 30501 闭合 |
| G-19.1a-03 AudibilityField 焦点 ≈ 1,远端 ≈ 0.08 |
| G-19.1a-04 AuditoryCanvas 时频网格 = 原 STFT 网格 |
| G-19.1a-05 mag + phase 双 PatchFusion 单测(circular mean) |
| G-19.1a-06 10 tick 累积 family metric 上升 ≥ 0.15 |
| G-19.1a-07 单 tick → tick+1 metric 至多回退 0.03 |
| G-19.1a-08 Saccadic listening 5 fixation 后高清区 ≥ 2.5× 单 fixation |
| G-19.1a-09 metric_focal ≥ 0.75 / near ≥ 0.50 / far ≥ 0.30 在 12 段 audit |
| G-19.1a-10 metric_focal > near > far 单调 |
| G-19.1a-11 R_proto_aud 6 步全实现 |
| G-19.1a-12 R_proto_aud 6 个 ablation gate(去除任意 step,对应特性消失) |
| G-19.1a-13 sound part / onset codebook 离线 npz 存在 |
| G-19.1a-14 R_aud_sketch / R_aud_proto 不共享主函数 |
| G-19.1a-15 auditory_canvas SA 注入 + inner_voice_sketch SA 含分场 metric |
| G-19.1a-16 红线 RL-19v1c-aud 全过 |
| G-19.1a-17 治理通过 |
| G-19.1a-18 真名零命中 |
| G-19.1a-19 全量回归 + Phase 19.1a 新测试 |
| G-19.1a-20 展示页含原音频 / 单 tick canvas / 5 tick canvas / 10 tick canvas / R_proto_aud 输出 — 同视觉 5 列对比 |

---

## 11. 落地顺序(配 v1c 视觉)

总顺序更新为:

```
19.0 (substrate, ✓) → 19.0a (foveated visual repair)
                            ↓
                          19.2 (confidence)
                            ↓
                       19.3a → 19.3b
                            ↓
                       19.1 (audio substrate)
                            ↓
                       19.1a (foveated audio repair)
                            ↓
                       19.4a → 19.4b → 19.5
```

19.1 现在变成"听觉 substrate(平 v1 + v1a 的版本)",然后必须做 19.1a 才能宣称"听觉重建效果合格"。

---

## 12. 署名

- 原架构设计:银子老师(笔名)
- v1c-Audio 数学修订:Claude (Anthropic) 在银子老师"音频也是,级别都比我想象中低"的反馈下,与 v1c 视觉对偶产出
- 落地:Codex 实施

End of Phase 19 v1c-Audio Errata.
