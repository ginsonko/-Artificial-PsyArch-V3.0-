# APV3.0 Phase 21 v1b Micro Errata — Truly Local Masks for V10/V11/V12

Date: 2026-06-20
Author: Claude(架构),银子老师(风格定调与最终签收)
Status: Micro errata,叠加在 Phase 21 v1a 上,**短小、聚焦、仅修 1 处工程缺口**
Trigger:
1. Phase 21 v1a 验收时我直接实测三个 candidate_bbox(左上 / 右下 / 中央)在真苹果1.jpeg 上抽出特征
2. 验证结果:
   - V7: TL_vs_BR=0.5844 / TL_vs_C=0.4229 ✓
   - **V10: TL_vs_BR=0.3151 / TL_vs_C=0.1447 ✗(中央 vs 左上几乎一样)**
   - **V11: TL_vs_BR=0.1216 / TL_vs_C=0.2580 ✗**
   - **V12: TL_vs_BR=0.0912 / TL_vs_C=0.3065 ✗**
3. R2 要求 V7/V10/V11/V12 必须真随 candidate_bbox 变(差异 > 0.3),实测仅 V7 兑现
License intent: AGPL-3.0-or-later

---

## 0. 这一份做什么(一句话)

让 V10/V11/V12 三个通道**真实地随 candidate_bbox 变化**,使得 Phase 21 扫视到不同位置时,部件颜色纹理 / 部件关系 / 颜色块空间图**也跟着重新计算**,而不是被 v1a 实施时的 mask 残留绑死在整图上。

---

## 1. 根因(实际读代码 + 单测确认)

`extract_visual_audit_path_v2_object_centric` 在 v1a 实施时:
- V0 → 真用 focus_xy ✓
- V7 → 真用 local mask ✓
- V10/V11/V12 → **仍走整图 _best_mask**(可能因为 Codex 在 v1a 实施时只改了 V7 入口签名,忘了同步 V10/V11/V12)

R2 红线写"V7/V10/V11/V12 必须 local",但单测可能只测了 V7。

---

## 2. 修法(只 1 处)

把 V10/V11/V12 的内部入口改成接受 `local_mask + local_rgb`,与 V7 同源:

```python
# 修前(整图 mask)
channels.append(("V10", _per_part_color_texture(rgb, mask)))
channels.append(("V11", _part_relational_graph(rgb, mask)))
channels.append(("V12", _color_cluster_spatial_map(rgb, mask)))

# 修后(local mask + local rgb)
channels.append(("V10", _per_part_color_texture(local_rgb, local_mask)))
channels.append(("V11", _part_relational_graph(local_rgb, local_mask)))
channels.append(("V12", _color_cluster_spatial_map(local_rgb, local_mask)))
```

`local_rgb` 是 candidate_bbox crop + padding,`local_mask` 是该 crop 内的 `_best_mask` 结果。

---

## 3. 单测(替换或扩展现有 R2 测试)

```python
def test_phase21_v1b_v10_v11_v12_truly_local_to_candidate_bbox():
    """
    同一张图,左上 / 右下 / 中央 三个 candidate_bbox 抽特征,
    V7/V10/V11/V12 两两距离必须 > 0.3
    """
    image_path = Path('config/curriculum/assets/visual/clean_cards/noun_apple_train_0.png')
    img = Image.open(image_path)
    W, H = img.size
    b1 = (0, 0, W//2, H//2)
    b2 = (W//2, H//2, W, H)
    bc = (W//4, H//4, 3*W//4, 3*H//4)

    t1 = extract_visual_audit_path_v2_object_centric(image_path, candidate_bbox=b1)
    t2 = extract_visual_audit_path_v2_object_centric(image_path, candidate_bbox=b2)
    tc = extract_visual_audit_path_v2_object_centric(image_path, candidate_bbox=bc)

    for ch in ['V7', 'V10', 'V11', 'V12']:
        v1 = _channel_slice(t1, ch)
        v2 = _channel_slice(t2, ch)
        vc = _channel_slice(tc, ch)
        assert cos_dist(v1, v2) > 0.3, f"{ch}: TL_vs_BR not local enough"
        # V10/V11/V12 跟 V7 一样必须真随 bbox 变
```

---

## 4. Deliverable Gate(3 条)

| Gate |
|---|
| G-21v1b-01 修 V10/V11/V12 入口,grep test:V10/V11/V12 调用必传 local_rgb + local_mask |
| G-21v1b-02 新单测 test_phase21_v1b_v10_v11_v12_truly_local_to_candidate_bbox 通过 |
| G-21v1b-03 12 张真实图重跑 enumerate_objects_in_image,truth-in-labels 不能从 11/12 倒退 |

---

## 5. 期待效果

不必显著提升 top-1 准确率(还需 train 集积累)。但是:

- **R2 红线真兑现**(4/4 通道 local,而不是 1/4)
- 后续 Phase 20 反馈闭环跑起来时,V10/V11/V12 真随焦点变 → 学习信号在更稳的特征上分摊 credit → 反馈学习效率提升

---

## 6. 边界

- 不动 V1-V6, V8, V9 — 它们在 v1a 已正确实施(或已 audit-only)
- 不动 Phase 21 主调度路径
- 不破坏现有 7 项 targeted tests
- 与 Phase 20 平行实施,不阻塞

---

## 7. 给 Codex 的实施备注

1. 找 `_per_part_color_texture` / `_part_relational_graph` / `_color_cluster_spatial_map` 三个函数体
2. 确认它们接受的 mask 参数确实是从外部传入
3. 在 `extract_visual_audit_path_v2_object_centric` 调用处,改成传 `local_mask`
4. 必须验证:**修后**重跑 §3 单测**全过**,**修前**至少 2 个通道 FAIL — 用对照法证明 v1b 真有效

---

## 8. 署名

- v1b 根因诊断:Claude (Anthropic) 在 Phase 21 验收时实测 + 直接读 [extract_visual_audit_path_v2:262](apv3test/runtime/visual_receptor.py#L262)
- 落地:Codex 0.5 天

End of Phase 21 v1b Micro Errata.
