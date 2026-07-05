# APV3.0 Phase 19.1 Design — Audio Sensor Enrichment + Reconstruction Audit + Inner Voice Reify

Date: 2026-06-19
Author: Claude(架构),银子老师(风格定调与最终签收)
Depends on: Phase 19.0 (visual sensor + R operator + inner_picture protocol)
Status: 设计稿,等待 Codex 对抗性审查 + 银子老师签字落地
License intent: AGPL-3.0-or-later + Commercial License separate
Real name handling: 全文件 grep 真名 = 0

---

## 0. 这一阶段做什么(一句话)

把当前贫血的听觉感受器(只输出能量包络 + 简单频带)升级成 **8 通道 AP-native 富感受器**,用**反向重建到 8 kHz / 16-bit WAV**作为充分性证明;同时这条反向重建管线**复用为"内心实时音频(叙事化想法)"通道** — 状态池里的 `narrative.lag_pmi` 链、IMAGINED-audio marker、conclusion_reify 的有声推理结论,都通过同一组算子合成可被人类一耳听懂的内心声音流。

Phase 19.1 与 Phase 19.0 在结构上**同构**(8 通道 vs 9 通道),数学骨架完全平行,审查可一次性走完。

---

## 1. 三个目标

- **G-Receptor 听觉富化**:输入端不再贫血,8 通道并行,纯 numpy/scipy + 仅可选 librosa(@dev_only,不进 runtime,如必须则 inline 重写算子)
- **G-Audit 反向重建**:任意输入音频 $A$,8 通道特征向量 $\mathbf{f}_A$ 必须能通过 $\mathcal{R}_{\mathrm{aud}}$ 合成近似音频 $\hat{A}$,使得 STOI(短时客观可懂度) $\geq \theta_{\mathrm{STOI}}$ 且人耳可辨度 $L \geq L_{\min}$
- **G-Inner 内心实时音频接入**:状态池的 `family in {narrative, inner_voice}` SA 通过 $\mathcal{R}_{\mathrm{aud}}$ 渲染成 WAV,供展示页 / 桌宠界面 / 调试器实时播放

---

## 2. 8 通道感受器清单

输入:单声道 $A \in \mathbb{R}^N$,采样率 $f_s = 16000$ Hz,统一 frame size $N_{\mathrm{frame}} = 512$,hop $= 256$。

每 frame 算 A1..A8。整段音频最终产 $\mathbf{f}_A \in \mathbb{R}^{D_A}$,$D_A$ 由 `audio_sensor.feature_vector_dim` 锁(预估 ≈ 960 / 秒)。

### A1 — Mel-Frequency Cepstral Coefficients (MFCC)
40 mel-band,取前 13 + Δ + ΔΔ = 39 维 / frame。捕音色 / 语音特征。

$$
\mathrm{MFCC}_k = \sum_{m=1}^{40} \log\left(\sum_{n} |X(n)|^2 \cdot H_m(n)\right) \cdot \cos\left(\frac{k(m-0.5)\pi}{40}\right)
$$

### A2 — Chroma(12 半音类)
$$
C_p = \sum_{f \in B_p} |X(f)|, \quad B_p = \{f : \log_2(f/f_0) \mod 1 \in [\frac{p}{12}, \frac{p+1}{12})\}
$$
12 维 / frame,捕音乐 / 音高。

### A3 — Spectral Centroid / Spread / Skewness / Kurtosis(4 维 / frame)
$$
\mu_X = \frac{\sum_f f \cdot |X(f)|}{\sum_f |X(f)|}
$$
等 4 阶矩。捕"亮"vs"闷"vs"窄"vs"宽"。

### A4 — Zero-Crossing Rate(1 维 / frame)
$$
\mathrm{ZCR} = \frac{1}{N_{\mathrm{frame}}} \sum_{n=1}^{N_{\mathrm{frame}}-1} \mathbb{1}[\mathrm{sgn}(A[n]) \neq \mathrm{sgn}(A[n-1])]
$$
区分语音(中 ZCR)/ 音乐(低 ZCR)/ 噪音(高 ZCR)。

### A5 — Onset / Tempo Envelope
谱通量 $\mathrm{flux}(t) = \sum_f \max(0, |X_t(f)| - |X_{t-1}(f)|)$,峰值检测得 onset 序列,自相关估 tempo。8 维 + 1 标量(BPM)。

### A6 — Pitch Contour (F0 via YIN-lite)
基频估计,每 frame 输出 $F_0$ 和 voicing flag。2 维 / frame。捕语调 / 旋律。

### A7 — Energy Envelope(多尺度)
3 个时间尺度的 RMS 包络:25 ms / 100 ms / 500 ms。3 维 / frame。

### A8 — Spectral Contrast(7 band)
每频带峰值与谷值的对比度,捕"清音 vs 浊音 / 和声 vs 纯音"。7 维 / frame。

---

## 3. 反向重建算子 $\mathcal{R}_{\mathrm{aud}}$

### 3.1 形式

$$
\hat{A} = \mathcal{R}_{\mathrm{aud}}(\mathbf{f}_A) : \mathbb{R}^{D_A} \to \mathbb{R}^{N'}
$$

输出 1 秒 8 kHz 单声道 WAV($N' = 8000$,够人耳辨主体音色 / 节奏 / 大致词形)。

### 3.2 5 步管线(与 Phase 19.0 视觉版同构)

**Step 1 — Spectrum skeleton**:MFCC + Chroma 反求 mel 谱 → 反 mel → 线性 STFT 幅值 $|\hat{X}(t,f)|$(用 inverse mel filterbank,纯线代,无神经网)。

**Step 2 — Phase reconstruction**:Griffin-Lim 算法(50 iter,纯 numpy 实现),从 $|\hat{X}|$ 恢复相位。

**Step 3 — Envelope shaping**:用 A7 (RMS 包络) 把整段音频的能量包络对齐(避免重建后全段电平均匀)。

**Step 4 — Pitch overlay**:对有 voicing flag 的 frame,叠加 A6 估计的 $F_0$ 正弦合成,占总幅 30%,与谱重建 70% 加权。

**Step 5 — Onset injection**:在 A5 检测的 onset 时刻注入冲击信号 (高频短脉冲),还原节奏感。

输出 $\hat{A}$ inverse-STFT 回时域。

### 3.3 充分性度量

**STOI 门槛**(短时客观可懂度,文献标准 0..1):
$$
\mathrm{STOI}(A, \hat{A}) \geq \theta_{\mathrm{STOI}} = 0.45 \quad \text{(@structural — "粗略可辨节奏/音色" 经验分界,语音清晰是 0.7+)}
$$

**人耳可辨度门槛**:每段 audit 音频独立标注 $L \in \{1,\dots,5\}$,银子老师签收。

$$
L_{\min} = 3 \quad \text{(@structural — 至少 "能听出是什么类的声音")}
$$

**audit 集**:与 Phase 19.0 同样,先用 12 段公开 CC0 / PD 音频(钢琴音、说话声、雨声、鸟叫、敲门、咳嗽、风、水流、铃铛、口哨、笑声、轻语呼唤),后续银子老师补充。

**通过条件**:$\geq 9/12$ 同时满足 STOI 与 $L_{\min}$。

---

## 4. 内心实时音频(叙事化想法)接入 — 您今天点名的

### 4.1 接入点

| 状态池 SA source | 已有机制 | Phase 19.1 接入 |
|---|---|---|
| `narrative.lag_pmi` 链 | `runtime/cognitive/narrative/lag_pmi.py:44` | 叙事 vocab 链每个节点 → 对应 $\mathbf{f}_{\mathrm{aud}}$ codebook 查 → 整链拼接 → 渲染成一段连续音频 |
| `imagined_marker_spawn` (IMAGINED + audio channel) | 既有 | 触发时,从聚合 audio percept 合成内心声音 |
| `conclusion_reify` | 既有 | 推理结论若含听觉 vocab,合成"内心说出来"的声音 |

### 4.2 内心声音 SA 新族

```
StateItem(
    sa_id=f"inner_voice::{source_sa_id}::{tick}",
    family="inner_voice",
    source="reconstruction_R_audio",
    channel_signature=("audio", "imagined", "reconstruction"),
    real_energy=confidence,
    metadata={
        "rendered_wav_bytes_sha256": <hex>,
        "rendered_wav_path": <path>,
        "narrative_chain_sa_ids": [...],
        "duration_ms": int,
        "is_speech_like": bool,                # A1+A6 联合判断
    }
)
```

### 4.3 "叙事化想法"的实现路径

叙事化想法 = "AP 用内心声音把刚刚推理的链条说出来一遍"。实现:

1. `narrative.lag_pmi` 产 `VocabSA::narrative::...` 链
2. 链每个 vocab id 查"内心声音 codebook"(Phase 19.1 离线构建):
   - 若 vocab 关联 Phase 16 styled corpus 文本 → 用 8 通道 codebook 查最近邻 audio prototype
   - 若 vocab 关联 Phase 14 audio asset → 直接拿 audio prototype 的 $\mathbf{f}_{\mathrm{aud}}$
3. 拼接 $\mathbf{f}_{\mathrm{aud}}^{(1)} \oplus \mathbf{f}_{\mathrm{aud}}^{(2)} \oplus \dots$
4. $\mathcal{R}_{\mathrm{aud}}$ 渲染整段
5. 注入 `inner_voice::*` SA

**红线**:
- 内心声音 codebook 是离线构建的,**不调任何 TTS / LLM / Whisper / 外部 API**
- 渲染产物不入 SA id,只 audit
- 不持久化用户原始音频

### 4.4 与"内心实时画面"的协同

`inner_picture` 流和 `inner_voice` 流可在同 tick 并存(画面 + 配音),供展示页同步播放。这就是您说的"内心实时画面 + 内心实时音频(叙事化想法)"的底座对接 — Phase 19.0/19.1 联合完成后,**展示页可以播放 AP 当时的"内心电影"**:一边是 $\mathcal{R}$ 渲染的画面流,一边是 $\mathcal{R}_{\mathrm{aud}}$ 渲染的声音流,人类一眼看出 AP 在想什么。

---

## 5. 数学骨架(与 19.0 同构)

$$
\begin{aligned}
\mathbf{f}_A &= \mathrm{Concat}_{c=1}^{8} A_c(A) \\
\hat{A} &= \mathcal{R}_{\mathrm{aud}}(\mathbf{f}_A) \\
\mathrm{audit\_pass}(A) &= \mathbb{1}[\mathrm{STOI} \geq \theta_{\mathrm{STOI}}] \wedge \mathbb{1}[L \geq L_{\min}]
\end{aligned}
$$

类别原型 $\mathbf{p}_c^{\mathrm{aud}} = \mathrm{Medoid}(\{\mathbf{f}_{A_i^{(c)}}\})$,打分:

$$
s_{\mathrm{aud}}(A, c) = \exp(-\lambda_{\mathrm{aud}} \cdot d(\mathbf{f}_A, \mathbf{p}_c^{\mathrm{aud}}))
$$

`audio_sensor.shepard_lambda = 2.0` @experimental。

---

## 6. 常量 / 红线 / Gates

### 6.1 新常量

```yaml
audio_sensor:
  sample_rate: 16000                    # @structural
  frame_samples: 512                    # @structural
  hop_samples: 256                      # @structural
  mfcc_n: 13                            # @structural
  mfcc_use_delta_delta_delta: true      # @structural
  chroma_bins: 12                       # @structural
  zcr_dim: 1                            # @structural
  spectral_moment_n: 4                  # @structural
  pitch_method: "yin_lite"              # @structural
  rms_envelope_scales_ms: [25, 100, 500] # @structural
  spectral_contrast_bands: 7            # @structural
  feature_vector_dim: 960               # @structural - per second estimate
  griffin_lim_iters: 50                 # @experimental
  pitch_overlay_weight: 0.3             # @experimental
  spectrum_weight: 0.7                  # @experimental
  reconstruction_duration_ms: 1000      # @structural
  reconstruction_sample_rate: 8000      # @structural
  stoi_threshold: 0.45                  # @structural
  human_legibility_min: 3               # @structural
  batch_pass_ratio_min: 0.75            # @scenario_tuneable
  shepard_lambda: 2.0                   # @experimental

inner_voice:
  max_chain_length_renders: 6           # @scenario_tuneable
  max_renders_per_second: 2             # @structural
  render_format: "wav"                  # @structural
  render_path_root: "data/inner_voice"  # @structural
```

### 6.2 红线

| RL | 描述 |
|---|---|
| RL-19.1-A01 | runtime/cognitive 不得 `import librosa` / `whisper` / `torchaudio` / `tts_*` |
| RL-19.1-A02 | 不调任何在线 API |
| RL-19.1-A03 | `inner_voice::*` SA id 不含真名 / 用户原文 / 文本语义 |
| RL-19.1-A04 | feature vector 不含 filename / class_label |
| RL-19.1-A05 | 渲染 WAV 落盘 audit-only,不入 SA id |
| RL-19.1-A06 | 真名零命中 |

### 6.3 Deliverable Gates(15 条,平行 19.0)

| Gate | 描述 |
|---|---|
| G-19.1-01 | 8 通道感受器每个有独立单测 |
| G-19.1-02 | feature_vector_dim 锁死与 yaml 一致 |
| G-19.1-03 | $\mathcal{R}_{\mathrm{aud}}$ 5 步管线完整 |
| G-19.1-04 | 12 段 audit 音频每段产 $\hat{A}$ |
| G-19.1-05 | $\geq 9/12$ 通过 STOI |
| G-19.1-06 | $\geq 9/12$ 通过人耳可辨度(银子老师签收) |
| G-19.1-07 | 内心声音接入 `narrative.lag_pmi` 链 |
| G-19.1-08 | 内心声音接入 `imagined_marker_spawn` audio 路径 |
| G-19.1-09 | 内心声音接入 `conclusion_reify` |
| G-19.1-10 | `inner_voice::*` SA id 无 leak |
| G-19.1-11 | 6 条红线零命中 |
| G-19.1-12 | 治理通过 |
| G-19.1-13 | 无外部音频库 import |
| G-19.1-14 | 无外部 API |
| G-19.1-15 | 全量回归 ≥ Phase 19.0 完成时基线 + 新增 Phase 19.1 测试 |

---

## 7. 边界

- 不实现 TTS / ASR(仅基于 8 通道特征的 codebook + Griffin-Lim 重建,不识别语义)
- 不调外部预训练音频模型 / LLM
- 不持久化用户原始录音
- 不做实时麦克风采集(纯静态 WAV audit)
- 不实现多语言文本到语音(Phase 19 不做 TTS;若 AP 想"说话",通过 styled corpus 文本 + Phase 19.1 codebook 反向重建,而不是文本→TTS)

---

End of Phase 19.1 Design.
