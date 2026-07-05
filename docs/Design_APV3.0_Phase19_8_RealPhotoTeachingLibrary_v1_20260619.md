# APV3.0 Phase 19.8 Design — Real Photo Teaching Library Construction (Codex Auto-Download + 银子老师 Human Curation)

Date: 2026-06-19
Author: Claude(架构),银子老师(风格定调与最终签收)
Status: 设计稿(基于 v1h 实测数据 + 银子老师亲手实测 Q1/Q2/Q3 确认根因后的工作流方案)
Trigger:
1. v1h 实测显示 V7/V10/V11 三个局部通道**有诊断性**(+58% / +103% / +82% 拉开比)
2. 但跨域(clean cards → real photos)只能 4/6
3. **决定性实验**(我亲手实测):
   - Q1: Clean cards 同类聚集完美(V7 +9887%)→ 通道实现没问题
   - Q2: 真实图 LOO 用 2 张/类作 train → 4/4 正确,margin 0.047-0.398
   - Q3: 真实图 LOO 用 11 张 real + 9 张 clean 作 train → **10/10 全对**,margin 平均 0.13
4. 银子老师确认根因:**clean cards 跟真实图差距太大 + train 集每概念只 3 张 → 跨域不行**
5. 银子老师同意"自己手工筛选(看后删不好的)" → Codex 写下载脚本,银子老师做 yes/no 决策
License intent: AGPL-3.0-or-later
Real name handling: 全文件 grep 真名 = 0

---

## 0. 这一份做什么(一句话)

把 Phase 19 卡死的"clean cards 跨域识别失败"问题用**真实图教学库**根治 — Codex 写**自动下载脚本**(从 CC-BY/CC0 公开图库批量下载),银子老师**人工筛选保留清晰且代表性好的**,Codex 再把保留的图按 Phase 19.0a foveated + V7/V10/V11 通道入库到 Layer-1/2/3,完成后系统在真实图上识别能力立刻从 7/12 → 接近 10/12。

---

## 1. 数据驱动的工作流总览

```
银子老师指定概念清单(20-30 个)
        ↓
Codex 写自动下载脚本(从 CC0/CC-BY 公开源)
        ↓
每概念下载 30 张候选 → 总 600-900 张
        ↓
Codex 把每概念 30 张排在一个简洁审阅网页上(thumbnails grid)
        ↓
银子老师**只**做 yes/no 决策(点击保留/删除)
目标:每概念保留 8-12 张清晰、主体明确、背景多样的
        ↓
Codex 自动入库:
  - 文件搬到 config/curriculum/assets/visual/real_teaching/<concept>/
  - 生成 manifest 含 SPDX license_id + source_url + 概念 label + train/held_out 拆分
  - 走 v1h 感受器抽 V0..V12 入 Layer-1
  - 触发 Layer-2 k-medoids 增量更新(part codebook 扩充)
  - 教师标注 → Layer-3 ConceptPrototype association 更新
        ↓
重跑 12 张图泛化探测,期待 ≥10/12 正确,≥6/12 进 soft/firm
```

---

## 2. 概念清单(银子老师签收)

第一批做 **20 个核心概念**(够开放对话底座的 alpha):

### 2.1 水果类(5)
苹果 / 香蕉 / 橙子 / 草莓 / 葡萄

### 2.2 常见物体(7)
书 / 杯子 / 椅子 / 桌子 / 钥匙 / 手机 / 电脑

### 2.3 动物(4)
猫 / 狗 / 鸟 / 鱼

### 2.4 食物(4)
面包 / 米饭 / 鸡蛋 / 蛋糕

**银子老师可以增删** — 这只是建议。

---

## 3. 下载源选择(全部 CC-BY/CC0/Public Domain)

**只**用以下源,有明确 license:

| 源 | License | API | 优先级 |
|---|---|---|---|
| **Wikimedia Commons** | CC0/CC-BY/PDM | Wikimedia REST API | P0 (优先) |
| **Pexels** | Pexels License (CC0 等价) | Pexels API (需注册免费 token) | P1 |
| **Pixabay** | Pixabay License (CC0 等价) | Pixabay API (需注册免费 token) | P1 |
| **Unsplash** | Unsplash License (CC0 等价) | Unsplash API (需注册免费 token) | P1 |
| **Openverse** | CC0/CC-BY 聚合 | Openverse API (无需 token) | P2 |

**严禁**:
- Google Images / 百度图片 (license 不明)
- 商业图库 (Shutterstock 等)
- 任何 CC-BY-SA(避免 viral copyleft 影响开源 alpha)
- 任何无明确 license 标注的源

### 3.1 银子老师手工补充路径

若 Codex 自动下载某概念不够 8 张清晰图,银子老师可手动从 Wikimedia 找补充(必须 CC0/CC-BY/PDM)。

---

## 4. Codex 下载脚本规约(精确)

### 4.1 入口

```python
scripts/curriculum/download_real_teaching_photos.py
  --concepts apple banana orange ...   # 概念清单
  --per-concept 30                      # 每概念下载候选数
  --license-allow CC0,CC-BY-3.0,CC-BY-4.0,PDM-1.0
  --license-block CC-BY-SA,All-Rights-Reserved,Unknown
  --output-dir config/curriculum/assets/visual/real_teaching_candidates/
  --max-file-size-mb 5
  --min-resolution 320x320              # 太低分辨率不要
  --max-resolution 4096x4096            # 太高分辨率压力大
```

### 4.2 下载流程

```
for concept in concepts:
    candidates = []
    for source in [WikimediaCommons, Pexels, Pixabay, Unsplash, Openverse]:
        results = source.search(concept, per_page=10)
        for r in results:
            if r.license not in licenses_allowed: continue
            if r.size_bytes > max_file_size: continue
            if r.width < min_w or r.height < min_h: continue
            # 下载到临时目录
            local_path = download(r.url, ...)
            # 生成 sidecar metadata
            sidecar = {
                "candidate_id": opaque_uuid,
                "concept": concept,
                "source": source.name,
                "source_url": r.url,
                "license_id": r.license,
                "author": r.author,
                "downloaded_at": "2026-06-19",
                "sha256": compute_sha256(local_path),
            }
            candidates.append((local_path, sidecar))
            if len(candidates) >= 30: break
        if len(candidates) >= 30: break
    save_candidate_set(concept, candidates)
```

### 4.3 输出结构

```
config/curriculum/assets/visual/real_teaching_candidates/
├── apple/
│   ├── cand_a3f9b1.jpg
│   ├── cand_a3f9b1.json   # sidecar metadata
│   ├── cand_8c2e44.jpg
│   ├── cand_8c2e44.json
│   ├── ... (30 张)
├── banana/
│   └── ... (30 张)
└── ... (20 概念 × 30 张 = 600 张)
```

### 4.4 红线

```
RL-19.8-Dl-01: license_id 必须在白名单内,缺失 license 跳过
RL-19.8-Dl-02: 真名("银子老师本名"/拼音)零命中(metadata 内)
RL-19.8-Dl-03: 不下载任何含人脸/可识别个人特征的图(简单检测:面部检测器跳过有面部的)
RL-19.8-Dl-04: 下载并发不超过 8(避免被源 ban)
RL-19.8-Dl-05: 失败重试 3 次,仍失败标记 skipped
```

---

## 5. 银子老师审阅页(关键 — 让筛选最快)

### 5.1 网页设计原则

**银子老师只需要做 yes/no** — 设计必须**减少决策疲劳**:

```
http://127.0.0.1:8767/real_curation.html
+-----------------------------------------------+
|  概念: 苹果  (1/20)                            |
|  保留: 0 / 目标 8-12 张                         |
+-----------------------------------------------+
|  [图1]   [图2]   [图3]   [图4]   [图5]         |
|  保留    保留    删除    保留    保留           |
|                                                 |
|  [图6]   [图7]   [图8]   [图9]   [图10]        |
|  保留    保留    保留    删除    保留           |
|                                                 |
|  ... (30 张,缩略图 200×200)                    |
+-----------------------------------------------+
|  [上一概念]    [下一概念]   [保存当前]         |
+-----------------------------------------------+
```

### 5.2 操作约定

- 默认状态:**所有图都"保留"**(银子老师**只**点击坏的标"删除")
- 单击图片 → 切换 保留/删除 状态
- 双击图片 → 大图预览(更清楚看主体)
- 键盘快捷键:`空格` = 下一张 / `D` = 标删除 / `S` = 保留 / `→` = 下一概念

### 5.3 筛选标准(银子老师指引)

**保留**:
- 主体清晰,占画面 ≥ 15%
- 主体颜色饱和(不严重退色)
- 背景与主体能区分
- 无文字/水印遮挡主体
- 拍摄角度自然(俯拍 / 侧拍 / 正拍都行)

**删除**:
- 主体被严重遮挡 / 切边
- 主体颜色异常(过曝/过暗)
- 多个不同概念混在一张图(如苹果+橙子同时)
- 图片质量差(模糊/噪点/低分辨率)
- 卡通/手绘/插画(我们要真实照片)

### 5.4 目标产出

每概念 **8-12 张**(若候选不够 8 张,银子老师补一些手动从 Wikimedia 找)。

---

## 6. Codex 入库脚本(银子老师筛完后跑)

### 6.1 入口

```python
scripts/curriculum/ingest_real_teaching_photos.py
  --curated-dir config/curriculum/assets/visual/real_teaching/
  --train-ratio 0.7        # 70% train, 30% held_out
  --rebuild-codebook       # 重建 Layer-2 V7 codebook
  --update-layer3          # 教师标注 → Layer-3 association
```

### 6.2 入库流程

```
for concept_dir in curated_dir.iterdir():
    photos = list(concept_dir.glob("*.jpg/png/webp"))
    # 拆 train / held_out (按 sha256 hash 决定,deterministic)
    train_photos, held_out_photos = split_by_hash(photos, train_ratio=0.7)
    
    # 入 Layer-1 PerceptVector
    for photo in train_photos:
        trace = extract_visual_audit_path_v2(photo)
        Layer1.insert(
            uuid=opaque_uuid_from(photo.sha256),
            signature=quantize_pca(trace.feature_vector),  # 256 uint8
            full_vec=trace.feature_vector,
            metadata={
                "concept": concept_dir.name,
                "split": "train",
                "license_id": photo.sidecar.license_id,
                "source_url": photo.sidecar.source_url,
                "epistemic_source": "PERCEIVED_TEACHING",
                "receptor_version": "phase19_0a_foveated",
            }
        )
    
    # 同样 held_out_photos 入 Layer-1,但标 split=held_out
    
    # 增量更新 Layer-2 V7 codebook
    for photo in train_photos:
        rgb = load_rgb(photo)
        mask = solve_subject_mask(rgb)
        sp_features = slic_part_features(rgb, mask, n=200)
        for sp_feat in sp_features:
            Layer2.online_kmedoids_update("V7", sp_feat, exemplar_id=opaque_uuid_from(photo.sha256))
    
    # 教师标注 → Layer-3 ConceptPrototype
    concept_uuid = Layer3.get_or_create_concept(
        label_external=concept_dir.name,  # audit only
        opaque_uuid=hash(concept_dir.name)
    )
    for photo in train_photos:
        Layer3.add_episodic_association(
            concept_uuid=concept_uuid,
            episodic_uuid=opaque_uuid_from(photo.sha256),
            source="teacher_labeled",
            tick=current_tick,
        )
    
    # 同 train_photos 在 V7 part_coverage 上聚合,赋 part_weights
    Layer3.update_part_weights(concept_uuid, derived_from=train_photos)
```

### 6.3 红线

```
RL-19.8-Ing-01: photos 必须来自 curated_dir(银子老师筛过),不允许直接从 candidates 入库
RL-19.8-Ing-02: split 必须 deterministic (sha256 % 10 < 7 → train),
                同一文件下次重跑产生同样 split
RL-19.8-Ing-03: Layer-3 association 入库时,概念名(audit only)不入 SA id / packet_key
                opaque_uuid 即可
RL-19.8-Ing-04: held_out photos 不参与 Layer-2 codebook 增量
RL-19.8-Ing-05: ingest 完成后立即跑 12 张图泛化探测,验证 ≥10/12
```

---

## 7. 期待效果(基于 Q3 实测)

我已经实测过用 11 张真实 + 9 张 clean cards LOO → **10/10 100%,margin 平均 0.13**。

Phase 19.8 完成后,**20 概念 × ~10 张真实 + 现有 clean cards** 作 train,12 张原图作 test:

| 指标 | Phase 19.7h 现在 | Phase 19.8 预期 |
|---|---:|---:|
| 正确率 | 7/12 (58%) | **≥ 10/12 (83%+)** |
| Soft / firm 档 | 0/12 | **≥ 6/12** |
| 错预测进 firm | 0 ✓ | 0 ✓ |
| margin 平均 | < 0.05 | **≥ 0.10** |

不再宣称"近 100% 拟人",但**从根本上突破跨域瓶颈**,产生真实可用泛化能力。

---

## 8. Deliverable Gates(15 条)

| Gate |
|---|
| G-19.8-01 download_real_teaching_photos.py 实现且单测过 |
| G-19.8-02 20 概念候选下载完成 ≥ 600 张 |
| G-19.8-03 license_id 必须在白名单内(零命中 unknown/CC-BY-SA) |
| G-19.8-04 每张图 sidecar JSON 完整(source_url + author + license + sha256) |
| G-19.8-05 银子老师审阅页(real_curation.html)可访问 |
| G-19.8-06 银子老师筛完每概念 8-12 张 |
| G-19.8-07 ingest_real_teaching_photos.py 实现 |
| G-19.8-08 Layer-1 入库 train + held_out 拆分 deterministic |
| G-19.8-09 Layer-2 V7 codebook 增量更新成功 |
| G-19.8-10 Layer-3 教师标注 association 完成 |
| G-19.8-11 12 张图重跑,正确率 ≥ 10/12 |
| G-19.8-12 ≥ 6/12 进 soft / firm |
| G-19.8-13 错预测全部 ambig,不进 firm |
| G-19.8-14 红线 RL-19.8-Dl-01..05 + Ing-01..05 全过 |
| G-19.8-15 真名零命中(全 metadata + 全 manifest + 全 audit 文件) |

---

## 9. 时间估算

| 阶段 | 时间 | 谁 |
|---|---|---|
| Codex 写下载脚本 + 审阅页 | 半天 | Codex |
| Codex 跑下载(600 张) | 1-2 小时 | Codex(自动) |
| 银子老师筛选(20 概念 × 30 候选 = 600 张) | 30-60 分钟 | 银子老师(决策疲劳低) |
| Codex 写 ingest 脚本 | 半天 | Codex |
| Codex 跑入库 + 重跑泛化探测 | 1 小时 | Codex |
| 验收 + Final Report | 半天 | Claude + Codex |

**总:** 1-2 天工作量,**banner 是银子老师筛选 1 小时**。

---

## 10. 边界

- 第一批 20 概念,不要 100 概念(MVP 优先)
- 单概念 8-12 张,不要 50 张(质量 > 数量)
- 不调外部 ML / GAN augmentation,纯真实图
- 不接入实时网络爬虫,只用 API + 一次性脚本
- 银子老师手工筛选不可由 Codex 替代(避免选择偏差)
- 第一批不做 alpha 公测,只内部验证

---

## 11. 后续路线(Phase 19.8 完成后)

完成 19.8 → 真实图教学库就绪 → 可以做:

1. **Phase 19.9** 把已学概念接入开放对话工作台,让用户语音 / 文字 / 图片输入触发识别
2. **Phase 19.10** 用户教学反馈循环(用户说"对/不对" → 触发 v1e §5 eligibility-based learning)
3. **Phase 19.11** 扩展到 50 概念
4. **Phase 20** 开始多模态绑定(图 + 语音 + 文字)

---

## 12. 银子老师当下要做的事

1. **确认 §2 概念清单**(我建议的 20 个,您可增删)
2. **批准 Codex 写下载脚本**
3. **等 Codex 下载完后,登录 real_curation.html,30-60 分钟筛选**
4. **Codex 入库 + 重跑 → Claude 出 Final Report**

---

## 13. 署名

- 原架构设计:银子老师(笔名)
- v19.8 工作流方案:Claude (Anthropic) 在亲手实测 12 张图 LOO Q1/Q2/Q3 + 银子老师同意"自己手工筛选可以"后产出
- 落地:Codex 写下载脚本 + 审阅页 + 入库脚本

End of Phase 19.8 Design.
