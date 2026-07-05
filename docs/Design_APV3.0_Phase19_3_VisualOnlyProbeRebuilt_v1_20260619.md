# APV3.0 Phase 19.3 Design — Visual-Only Probe Rebuilt on Enriched Receptors + Human-Like Confidence

Date: 2026-06-19
Author: Claude(架构),银子老师(风格定调与最终签收)
Depends on: Phase 19.0 (visual sensor + R), Phase 19.2 (confidence formula)
Replaces: Codex `Design_APV3.0_Phase18_2_UserRealImageVisualOnlyProbe_v1_20260619.md`(其 visual-only / no-leak / "还不能确认" 设计原封保留,只把感受器从 Phase 18.1 贫血特征替换为 Phase 19.0 9 通道,把决策从余弦相似度替换为 Phase 19.2 把握感公式)
Status: 设计稿,等待 Codex 对抗性审查 + 银子老师签字落地

---

## 0. 这一阶段做什么

把 Phase 18.1 真实照片泛化探测重做一次,**但不修复 Phase 18.1 的结论**(Errata `visual_generalization_valid=false` 保留为历史诚实记录),而是在 Phase 19.0 + 19.2 落地后,**用富感受器 + 拟人把握感**重新做一次同样的探测。

如果这次:
- $\geq 9/12$ 用户图给出 firm 或 soft 决策 → 证明视觉泛化 valid
- 否则 → 真泛化仍未成立,但因为 Phase 19.2 的拟人输出"还不能确认",AP 不会再喊错答案 — 失败也是有尊严的失败

---

## 1. 沿用 Codex 18.2 设计的部分(原封不动)

| 项 | 状态 |
|---|---|
| 三层分离:public/AP layer vs evaluator layer | 保留 |
| Student probe payload 不含 `neutral_label / entry_id / target_class / filename / 中文答案` | 保留 |
| Evaluator sidecar 存 label 但不进 packet builder | 保留 |
| 任何 label 输出需"正确预测 + 置信门"双满足 | 升级为 Phase 19.2 4 档决策 |
| 若 confidence 不够 → 输出 "还不能确认" | 保留并形式化为 Phase 19.2 `tau_ambig` 以下分支 |
| 12 张图作 audit 集,非可分发资产,内部测试用 | 保留 |

---

## 2. Phase 19.3 升级的部分

### 2.1 特征层升级

| Phase 18.1 | Phase 19.3 |
|---|---|
| 贫血 visual_feature(颜色均值 + 粗略形状) | Phase 19.0 9 通道 $\mathbf{f}_x \in \mathbb{R}^{1800}$ |
| 距离 = 单一余弦相似度 | 9 通道分块加权距离 + Shepard 衰减 |
| 类别原型 = 简单均值 | Medoid + Phase 19.0 prototype codebook |

### 2.2 决策层升级

| Phase 18.1 | Phase 19.3 |
|---|---|
| Q 表查最近 → 输出 label(被 Errata 揭露是 label-mediated) | Phase 19.2 `Conf(c|x) = D·C·M·Q·(1-Ω)` 5 因子 |
| 单一阈值通过 / 不通过 | 4 档决策:firm / soft / ambig / no_call |
| 失败时输出 "还不能确认"(临时打补丁) | "还不能确认" 是公式自然结果,对应 `Conf < tau_ambig` |
| 输出文本硬编 | 走 Phase 16 styled corpus 渲染 |

### 2.3 内心画面接入(新增)

每张测试图打分时,**同时**产 `inner_picture::*` SA:
- 用 Phase 19.0 $\mathcal{R}$ 把 $\mathbf{p}_{c^*}$ (top-1 类原型) 渲染成 64×64 PNG
- 该 PNG 就是 AP "脑子里想象的最像类别"
- 落盘 audit-only,展示页可显示"AP 看了这张图,内心浮现的画面是这个"

→ 这让 Phase 19.3 不只产 `decision_tier` 一个数字,而是产**可视化的内心反应**,银子老师和最终用户能直接看出 AP 当下的想法。

---

## 3. 数据流

```
input: 12 张用户真实图(opaque ids, image bytes)
       ↓
Phase 19.0 sensor: 每张图 → f_x ∈ R^1800
       ↓
prototype lookup: 类别原型表 {p_apple, p_banana, p_orange} (Phase 19.3 启动时从 Phase 18.0 clean cards 训练得到)
       ↓
Phase 19.2 confidence: Conf(c|x) for each c
       ↓
decision tier: firm / soft / ambig / no_call
       ↓
inner_picture render: R(p_{c*}) → PNG (audit-only path)
       ↓
output text: 走 Phase 16 styled corpus,从对应 paradigm 池抽
       ↓
StateItem inject: confidence_decomposition + decision_tier + inner_picture_sa
       ↓
evaluator sidecar match: 检查 decision 与真实 label 是否对(audit-only, 不回写到 student state)
       ↓
audit report: 每张图的 (decision_tier, predicted, true, conf, factors) 表
```

---

## 4. 真实 12 张图的预期行为(用作 Phase 19.3 acceptance hypotheses)

| 图 | 期望 decision | 期望文本 | Why |
|---|---|---|---|
| 真实苹果 1-3 | firm | "这是 苹果" | 红色 + 圆形 + 高诊断,无竞争 |
| 真实橙子 1-3 | firm 或 soft | "这是 橙子" / "像是 橙子" | 橙色 + 圆形 + 高诊断 |
| 真实香蕉 1-4 | firm | "这是 香蕉" | 长条 + 黄色 + 弯曲,V6 几何强诊断 |
| 黄绿色苹果 | soft | "像是 苹果" | 颜色非典型但形状/纹理仍是苹果 — $D$ 略低,$M$ 仍高 → soft |
| 绿色橙子 | soft 或 ambig | "像是 橙子" / "可能是 橙子,也可能是 X" | V2 色调与典型橙偏差,但 V6 形状强,$\Omega$ 略高 |

**通过门**:
- 9/12 在 firm/soft 档(允许 3 张 ambig/no_call)
- 黄绿苹果 + 绿橙子**必须不在 firm**(否则说明 $\Omega$ 没起作用,变成假阳性)
- 任意图都**不允许**预测错 label 同时 confidence 在 firm 档(否则说明竞争压制 $M$ 失效)

---

## 5. Deliverable Gates(12 条)

| Gate | 描述 |
|---|---|
| G-19.3-01 | 沿用 Codex 18.2 三层分离原封不动 |
| G-19.3-02 | Student payload 实测无 leak(grep 测试) |
| G-19.3-03 | 12 张图全部通过 Phase 19.0 感受器 + Phase 19.2 公式跑完 |
| G-19.3-04 | $\geq 9/12$ 在 firm/soft 档 |
| G-19.3-05 | 黄绿苹果不在 firm |
| G-19.3-06 | 绿橙子不在 firm |
| G-19.3-07 | 无 (firm + 错预测) 组合 |
| G-19.3-08 | 输出文本全走 Phase 16 styled corpus |
| G-19.3-09 | 每张测试图产对应 inner_picture::* SA |
| G-19.3-10 | inner_picture PNG 落盘 audit-only,不入 SA id |
| G-19.3-11 | 红线全过(继承 Phase 19.0 + 19.2 + Codex 18.2) |
| G-19.3-12 | 全量回归 + Phase 19.3 测试 |

---

## 6. 与 Phase 18.1 Errata 的关系

Phase 18.1 Errata 的最终状态(`visual_generalization_valid=false`,plumbing-only)**保留为历史记录,不修改**。

Phase 19.3 是**重做一次**,在富感受器 + 拟人把握感上重新评估"真实图片泛化" — 它要么独立通过,要么独立失败,不通过修改 18.1 的结论来"假装通过"。

Final Report 要明确写:
> Phase 19.3 是在 Phase 19.0 富感受器 + 19.2 拟人把握感上重做的视觉泛化探测。Phase 18.1 的失败结论保留为 plumbing-only baseline,Phase 19.3 的通过 = 真泛化成立,Phase 19.3 的失败 = 富感受器仍未充分,需要 Phase 19.0/19.1 加通道。

---

## 7. 边界

- 不做听觉泛化(那是后续 Phase 19.4 — 与 19.3 同构)
- 不做多模态融合(那是后续 Phase 19.5)
- 不做对话上下文(对话底座是 Phase 21 起)
- 12 张图不作为开源 release 资产(license / SPDX 不清),只内部 audit
- 不接入用户实时摄像头

---

End of Phase 19.3 Design.
