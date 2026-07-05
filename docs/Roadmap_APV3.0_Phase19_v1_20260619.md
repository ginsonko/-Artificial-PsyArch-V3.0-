# APV3.0 Phase 19 Roadmap — Receptor Enrichment + Reconstruction + Inner Picture/Voice + Human-Like Confidence

Date: 2026-06-19
Author: Claude(架构),银子老师(风格定调与最终签收)
Status: 路线图,Phase 19.0 / 19.1 / 19.2 / 19.3 已起草 v1 设计稿;**v1a Errata 已落** —
        见 [Errata_Phase19_v1a_AnthropomorphicAndEngineeringClosure_20260619.md](Errata_Phase19_v1a_AnthropomorphicAndEngineeringClosure_20260619.md);
        **v1b Micro Errata 已落** —
        见 [Errata_Phase19_v1b_ImplementationSensitiveClosure_20260619.md](Errata_Phase19_v1b_ImplementationSensitiveClosure_20260619.md);
        **v1c Errata 已落(foveated 重建 + canvas 累积 + R_proto 通道合成)** —
        见 [Errata_Phase19_v1c_FoveatedReconstructionAndChannelBasedSynthesis_20260619.md](Errata_Phase19_v1c_FoveatedReconstructionAndChannelBasedSynthesis_20260619.md)
        + [Errata_Phase19_v1c_audio_FoveatedListeningAndChannelBasedSynthesis_20260619.md](Errata_Phase19_v1c_audio_FoveatedListeningAndChannelBasedSynthesis_20260619.md);
        **v1d Errata 已落(三层向量库 + B/C 召回 + 奖惩/认知压学习 + Codex 11 项修订)** —
        见 [Errata_Phase19_v1d_ThreeLayerVectorSubstrateAndRewardSurpriseLearning_20260619.md](Errata_Phase19_v1d_ThreeLayerVectorSubstrateAndRewardSurpriseLearning_20260619.md);
        **v1e Errata 已落(源边界硬化 + eligibility + 存储算术修正 + 冷启动 tentative + 多模态分级)** —
        见 [Errata_Phase19_v1e_SourceDisciplineEligibilityAndStorageReality_20260619.md](Errata_Phase19_v1e_SourceDisciplineEligibilityAndStorageReality_20260619.md)。
        落地时按 **v1 + v1a + v1b + v1c(视觉) + v1c-audio(听觉) + v1d + v1e 七份合读**;v1e 拆 Phase 19.0b 为 19.0b0(schema)/ 19.0b1(写入),总顺序:
        **19.0 (✓) → 19.0b0 (vector schema) → 19.0a (foveated repair) → 19.0b1 (vector write) → 19.2 → 19.3a → 19.3b → 19.1 → 19.1a → 19.4a → 19.4b → 19.5(eligibility+ablation+tentative+多模态) → 19.6(active perception)**
License intent: AGPL-3.0-or-later

---

## 0. Phase 19 的整体定位

把 Phase 18.1 Errata 暴露的两个根本问题一次性解决:

1. **感受器贫血** — 输入端信息不够,后端 Q 表 / SDPL / 原型再聪明也无米下锅
2. **决策过硬** — 余弦相似度 + 单阈值 → 假阳性(label-mediated)或假阴性(全部 no_call)

修法:**输入端做"反向重建"标准化通道集 → 输出端做拟人把握感公式 → 顺手把"内心实时画面 / 内心实时音频"接入底座**。

Phase 19 的成功标准: AP 在看到从未见过的真实照片时,**像人一样**给"这是橙子" / "像是橙子" / "可能是橙子,也可能是 X" / "还不能确认" 四档之一,而且每一档都有数学根据,银子老师能解释给小白听。

---

## 1. 四个子阶段的顺序与依赖

```
Phase 19.0 视觉富感受器 + 反向重建 + 内心画面接入
        │
        ├─→ Phase 19.1 听觉富感受器 + 反向重建 + 内心声音接入(与 19.0 并行可行,但建议串行)
        │
        ├─→ Phase 19.2 拟人把握感公式(数学层,纯函数,依赖 19.0 通道清单)
        │
        └─→ Phase 19.3 visual-only probe 重做(依赖 19.0 + 19.2,沿用 Codex 18.2 框架)
```

**推荐串行**:
1. **Phase 19.0**(视觉富化 + 反向重建)— 立刻动手
2. **Phase 19.2**(把握感公式,纯数学,无 IO)— 19.0 落地后做
3. **Phase 19.3**(visual-only probe 重做)— 19.0 + 19.2 都过后做
4. **Phase 19.1**(听觉富化 + 内心声音)— 视觉链路验证后做,与 Phase 21 对话底座对接顺路

---

## 2. "内心实时画面 / 内心实时音频" 在底座的位置

### 2.1 接入点(继承,不新增机制)

底座已经有以下接口,Phase 19 让它们"长出可视化身体":

| 既有接口 | 既有产出 | Phase 19 让它产出 |
|---|---|---|
| `fast_mapping.reverse_imagine_from_mapping` | `imagined::<target_sa>` SA | 同时产 `inner_picture::*` SA + 64×64 PNG |
| `endogenous.imagined_marker_spawn` | IMAGINED marker | 同上,marker 触发的想象 SA 顺路渲染 |
| `deliberative.conclusion_reify` | 推理结论实化 | 结论包含视觉 vocab → 内心画面;包含听觉 vocab → 内心声音 |
| `narrative.lag_pmi.narrative_candidate` | `VocabSA::narrative::a->b->c` | 链每节点对应一张内心画面 / 一段内心声音,串成内心电影 |
| `cognitive_feelings.epistemic_source_feelings.imagination_sense` | imagination_sense 标量 | 用作内心画面 SA 的 real_energy |

### 2.2 接入的红线

- 内心画面 SA id **不得**编码类别 label / 真名 / 用户原文
- 渲染产物**只**落盘 audit-only 路径,不入 SA id
- 不接外部图像 / 音频生成模型(diffusion / GAN / TTS / Whisper 一律禁止)
- 渲染算子 $\mathcal{R}, \mathcal{R}_{\mathrm{aud}}$ 是 AP-native 的反向算子,纯 numpy / scipy
- 同 tick 渲染数量上限(`inner_picture.max_renders_per_second = 10`,`inner_voice.max_renders_per_second = 2`)避免硬件爆破

### 2.3 双重身份

```
反向重建算子 R / R_aud
  ├── 身份 1: Phase 19.0 / 19.1 的"感受器充分性证明工具"
  │           (SSIM / STOI 门槛 + 人眼/耳可辨度签收)
  │
  └── 身份 2: 底座的"内心实时画面 / 叙事化想法"渲染引擎
              (展示页 / 桌宠 / 调试器订阅实时显示)
```

**同一组算子 + 同一份特征向量** — 不会出现"audit 用的重建"和"内心画面渲染"互相不一致,因为它们就是一个函数。

---

## 3. 与已有 Phase 路线的关系

| Phase | 状态 | 与 Phase 19 关系 |
|---|---|---|
| Phase 13.x 认知课程 | 完成 | Phase 19.3 直接用 13.x 训练过的类别原型 |
| Phase 14.x 中性合成素材 | 完成 | Phase 19.0 reconstruction audit 不依赖,但作为"低难度 baseline" |
| Phase 15.x 课程回放工作台 | 完成 | Phase 19.3 内心画面接入回放,展示 AP 内心反应 |
| Phase 16 styled corpus | 完成 | Phase 19.2 4 档输出文本走 styled corpus 渲染 |
| Phase 17 真实照片白名单 | 完成 | Phase 19.0 audit + Phase 19.3 probe 用 |
| Phase 18.0 干净卡片 | 完成 | Phase 19.3 训练原型用 |
| Phase 18.1 真实泛化探测 + Errata | 已诚实降级 | Phase 19.3 重做,Errata 结论保留为历史 |
| Phase 18.2 visual-only probe(Codex 稿) | 已起草 | **重命名为 Phase 19.3**,沿用 leak gate 设计,升级感受器 + 把握感 |

---

## 4. Phase 19 完成后的整体能力

完成 Phase 19.0 + 19.2 + 19.3 后,AP 拥有:

| 能力 | Phase 19 之前 | Phase 19 之后 |
|---|---|---|
| 看图 | 颜色均值 + 粗略形状 → 给 label | 9 通道富特征 → 4 档把握感输出 |
| 听音 | 能量 + 频带 → 给 vocab | (Phase 19.1) 8 通道富特征 → 4 档把握感输出 |
| 内心 | 状态池里有 `imagined::*` SA,但没渲染 | 每 tick 实时渲染内心画面 / 声音流,可视可听 |
| 决策 | 余弦最近邻 + 单阈值 | 诊断性 × 一致性 × 竞争压制 × 质量门 × OOD 惩罚 |
| 失败 | 假阳性(label-mediated 给错答案)/ 假阴性(全部 no_call) | 失败也"像人",输出"还不能确认"或"像是 X" |
| 充分性证明 | 没有 | 反向重建 + SSIM/STOI + 银子老师签收 |

---

## 5. 与未来阶段的接口

- **Phase 20**(后续)— 类别权重自动学习 + 多模态融合
- **Phase 21**(后续)— 对话底座:把 Phase 19 的把握感 + 内心画面/声音 + Phase 16 styled corpus 串起来,做"看 → 想 → 说"完整链路
- **Phase 22**(后续)— 用户端 alpha:桌宠 + 对话底座 + 内心画面/声音流的展示

---

## 6. 工作流(继承我们一贯流程)

每个 Phase 19.x 严格走:

1. 设计稿(我写,已完成)
2. **对抗性审查**(Codex 做)
3. 数学模型 + 红线 + Gate 锁定后,落地(Codex 做)
4. 严格验收(Codex + 我交叉)
5. Final Report(我写)
6. 展示页(Codex 做,小白可看懂,带真实数据)

---

## 7. 真名与署名

- **原架构设计**:银子老师(笔名)
- **数学模型与设计稿**:Claude (Anthropic) 在银子老师方向下产出
- **实现**:Codex 在审查通过后落地
- **不署**:真名不进任何公开文件

---

## 8. 当前进度

| Phase | 设计稿 | 对抗审查 | 实现 | 验收 | Final Report | 展示页 |
|---|---|---|---|---|---|---|
| 19.0 视觉富感受器 + 反向重建 + 内心画面 | ✓ 已写 | 待 | 待 | 待 | 待 | 待(Codex) |
| 19.1 听觉富感受器 + 内心声音 | ✓ 已写 | 待 | 待 | 待 | 待 | 待(Codex) |
| 19.2 拟人把握感公式 | ✓ 已写 | 待 | 待 | 待 | 待 | 待(Codex) |
| 19.3 visual-only probe 重做 | ✓ 已写 | 待 | 待 | 待 | 待 | 待(Codex) |

设计稿文件:

- [Design_APV3.0_Phase19_0_VisualSensorEnrichmentAndReconstructionAudit_v1_20260619.md](Design_APV3.0_Phase19_0_VisualSensorEnrichmentAndReconstructionAudit_v1_20260619.md)
- [Design_APV3.0_Phase19_1_AudioSensorEnrichmentAndInnerVoice_v1_20260619.md](Design_APV3.0_Phase19_1_AudioSensorEnrichmentAndInnerVoice_v1_20260619.md)
- [Design_APV3.0_Phase19_2_HumanLikeConfidenceFormula_v1_20260619.md](Design_APV3.0_Phase19_2_HumanLikeConfidenceFormula_v1_20260619.md)
- [Design_APV3.0_Phase19_3_VisualOnlyProbeRebuilt_v1_20260619.md](Design_APV3.0_Phase19_3_VisualOnlyProbeRebuilt_v1_20260619.md)

---

End of Phase 19 Roadmap.
