# APV3.0 Phase 16 — Final Report
## Styled Expression Corpus(小默风格语料)

Date: 2026-06-18
Author: Claude (Anthropic) — under 银子老师 风格指导
Original architect: 银子老师 (pen name)
License: AGPL-3.0-or-later (commercial license available separately)

---

## 0. TL;DR

**做了什么**:把 Phase 13 已锁定的"小默"风格(长门有希 + 秋山澪混合,惜字如金 + 沉默是默认 + 反差萌稀缺真心)从样例放大到完整覆盖,产出 **130 个语用范式 × 5 情绪 × 3 强度 × 6 变体 = 11700 train+held_out 候选 + 130 LLM 病反例 = 11830 总 candidates**,写进 20 个 styled curriculum packages。

**质量门槛**: 全部 15 个 Phase 16 deliverable gate 通过。

**对开源 alpha 的意义**: 这是 APV3 的"故事核心" — 颜色 / 形状 / 苹果证明的是"系统能学",小默风格证明的是"系统能学到一个具体的人怎么说话"。

---

## 1. 范式覆盖(130 个,超出 120 按钮基线)

| 类别 | 编号 | 数量 |
|---|---|---:|
| 招呼/问候 | PAR-A.01 - A.08 | 8 |
| 共情/陪伴 | PAR-B.01 - B.12 | 12 |
| 学习/被教 | PAR-C.01 - C.08 | 8 |
| 称赞接受 | PAR-D.01 - D.06 | 6 |
| 拒绝/不会 | PAR-E.01 - E.08 | 8 |
| 询问/不解 | PAR-F.01 - F.06 | 6 |
| 应承/同意 | PAR-G.01 - G.06 | 6 |
| 反对/不同意 | PAR-H.01 - H.06 | 6 |
| 时间/日程感 | PAR-I.01 - I.04 | 4 |
| 关心/反向问候 | PAR-J.01 - J.08 | 8 |
| 自我表达 | PAR-K.01 - K.08 | 8 |
| 状态报告 | PAR-L.01 - L.06 | 6 |
| 分别/告辞 | PAR-M.01 - M.06 | 6 |
| 错误/纠正接受 | PAR-N.01 - N.06 | 6 |
| 玩笑/幽默承接 | PAR-O.01 - O.06 | 6 |
| 共在沉默 | PAR-P.01 - P.04 | 4 |
| 物品互动 | PAR-Q.01 - Q.06 | 6 |
| 天气/环境 | PAR-R.01 - R.04 | 4 |
| 节日/纪念日 | PAR-S.01 - S.04 | 4 |
| 反差萌触发 | PAR-T.01 - T.08 | 8 |
| **合计** | | **130** |

---

## 2. 维度矩阵(每范式 90 候选)

每个范式按 `(affect × intensity × variant_index)` 三维矩阵展开:

- **affect (5)**: calm / curious / sleepy / shy / warm
- **intensity (3)**: low / mid / high
- **variant_index (6)**: 同一 (affect, intensity) 单元里的 6 种说法

5 × 3 × 6 = 90 个候选 / 范式
130 × 90 = 11700 train+held_out candidates
+ 130 contrast (LLM 病反例,每范式 1) = **11830 总 candidates**

---

## 3. Deliverable Gates(15/15 全过)

| Gate | 描述 | 实测 | 状态 |
|---|---|---|---|
| G1 | 130 范式全覆盖 | 130 | PASS |
| G2 | 每范式 ≥ 90 candidates | min=90 | PASS |
| G3 | 总 candidates ≥ 11000 | 11830 | PASS |
| G4 | 平均 meaningful char_count ≤ 5.0 | 2.71 | PASS |
| G5 | char_count > 15 比例 = 0 | 0 | PASS |
| G6 | char_count 8-15 比例 ≤ 5% | 2.44% | PASS |
| G7 | LLM 病黑名单零命中(train+held_out) | 0 | PASS |
| G8 | 性别称呼黑名单零命中 | 0 | PASS |
| G9 | 真名 / 拼音零命中(全文件) | 0 | PASS |
| G10 | 每范式 ≥ 1 held-out candidate | 130 | PASS |
| G11 | 每范式 ≥ 1 contrast candidate | 130 | PASS |
| G12 | train / held_out / contrast 文本无碰撞 | 0 collision | PASS |
| G13 | runtime cognitive 不通过 paradigm_id/affect_bucket 分支 | 0 命中 | PASS |
| G14 | styled package 通过 curriculum_schema 验证 | 20/20 | PASS |
| G15 | 生成器幂等且 summary 通过 | OK | PASS |

---

## 4. 红线 / 治理 / 回归

| 检查 | 结果 |
|---|---|
| `red_line_check_v14.py` | PASS — All red line checks pass on runtime/cognitive |
| `check_constant_governance.py` | PASS — 302 numeric constants(Phase 16 新增 9 个 styled_corpus 常量)|
| Phase 16 targeted | 15/15 passed |
| 全量回归 | **495 passed** (Phase 15 基线 480 + Phase 16 新增 15)|

---

## 5. 产出物

### 5.1 代码 / 配置
- [docs/Design_APV3.0_Phase16_StyledExpressionCorpus_v1_20260618.md](docs/Design_APV3.0_Phase16_StyledExpressionCorpus_v1_20260618.md) — 设计稿(风格基线、范式分类、维度矩阵、16 gate)
- [config/apv3_constants.yaml](config/apv3_constants.yaml) — 新增 `curriculum.styled_corpus.*` 9 个常量
- [runtime/cognitive/curriculum/package_schema.py](runtime/cognitive/curriculum/package_schema.py) — schema 扩展(允许 `apv3_styled_curriculum_pack/v1` + phase_id `16.x`)
- [scripts/curriculum/generate_styled_corpus.py](scripts/curriculum/generate_styled_corpus.py) — 主生成器
- [scripts/curriculum/_styled_paradigms_a.py](scripts/curriculum/_styled_paradigms_a.py) — PAR-A 池
- [scripts/curriculum/_styled_paradigms_b.py](scripts/curriculum/_styled_paradigms_b.py) — PAR-B 池
- [scripts/curriculum/_styled_paradigms_c.py](scripts/curriculum/_styled_paradigms_c.py) — PAR-C 池
- [scripts/curriculum/_styled_paradigms_rest.py](scripts/curriculum/_styled_paradigms_rest.py) — PAR-D 到 PAR-T 池(102 范式)
- [scripts/reports/render_phase16_showcase.py](scripts/reports/render_phase16_showcase.py) — 展示页渲染器

### 5.2 课程包(20 styled YAML)
位于 [config/curriculum/packages/styled/](config/curriculum/packages/styled/):

- styled_greeting_v1.yaml(招呼)
- styled_empathy_v1.yaml(共情)
- styled_learning_v1.yaml(学习)
- styled_praise_v1.yaml(称赞接受)
- styled_refusal_v1.yaml(拒绝)
- styled_inquire_v1.yaml(询问)
- styled_agree_v1.yaml(应承)
- styled_disagree_v1.yaml(反对)
- styled_time_v1.yaml(时间)
- styled_reverse_greeting_v1.yaml(反向问候)
- styled_self_express_v1.yaml(自我表达)
- styled_state_report_v1.yaml(状态报告)
- styled_farewell_v1.yaml(告辞)
- styled_correction_v1.yaml(纠正接受)
- styled_humor_v1.yaml(幽默承接)
- styled_co_silence_v1.yaml(共在沉默)
- styled_object_interact_v1.yaml(物品互动)
- styled_weather_v1.yaml(天气)
- styled_festival_v1.yaml(节日)
- styled_long_warm_v1.yaml(反差萌真心)

### 5.3 测试
- [tests/test_phase16_0_styled_expression_corpus.py](tests/test_phase16_0_styled_expression_corpus.py) — 15 test functions 覆盖全部 16 个 deliverable gate

### 5.4 展示页
- [reports/APV3_Phase16_StyledExpression_Showcase_20260618.html](reports/APV3_Phase16_StyledExpression_Showcase_20260618.html) — 小白可看懂展示页,388 行,10 个范式 demo,每个 demo 含 5 情绪行 + 1 LLM 病反例对照

---

## 6. 风格基线(锁死,后续阶段不软化)

| 维度 | 规则 |
|---|---|
| 默认上限 | meaningful char_count ≤ 8 (95%+ 情况) |
| 反差萌长句 | meaningful char_count ≤ 15 (< 5% 情况) |
| 平均字数 | meaningful char_count ≤ 5.0 (实测 2.71) |
| 沉默 | `…` / `……` / `………` 是合法表达 |
| 真心稀缺 | 每完整对话段 1-2 句长真心 |
| 性别预设 | 完全中性 — 禁 哥哥/姐姐/主人/宝贝/亲爱的/小可爱 |
| 自称 | 不主动自我介绍,被问则简答 |
| 反 LLM 病 | 不解释 / 不夸张 / 不空话 / 不绕弯 / 不感叹号狂 / 无尾缀波浪号 |

---

## 7. 边界 — Phase 16 不做的事

- **不接入 AP 学习管线** — Phase 17 才把 styled corpus 灌进 SDPL / Q 学习并验证泛化
- **不调外部 LLM** — 全部 candidate 是离线 yaml,不在线生成
- **不做语音 / emoji / 表情** — 纯文本,情绪通过文本结构呈现(省略号、字数、留白)
- **不做对话上下文长依赖** — 每 candidate 是单 turn 应答
- **不做 SNS 前端集成** — SNS 走另一路线
- **不做真名持久化** — 全文件 grep 真名 0 命中

---

## 8. 下一步建议

1. **Phase 17 — Styled corpus integration**:把 11700 styled candidates 喂进 AP runtime,验证:
   - SDPL 在 styled corpus 上的 packet 唯一性
   - held_out 同范式不同变体上的 Q 倾向保持
   - contrast(LLM 病)上的 Q 倾向被压低
   - 跨范式不串味(招呼范式不会污染共情范式)

2. **Phase 18 — 真实外部素材白名单**:CC0/CC-BY/Public Domain 三个明确 license 源采集,每张/每段必有 SPDX + source_url + 创作者 + license_id

3. **Phase 19 — 开源 alpha 法律包**:LICENSE / LICENSE_COMMERCIAL / CONTRIBUTING / AUTHORS / NOTICE,双轨说明 + "原架构设计:银子老师" 署名规约

---

## 9. 署名

- **原架构设计**:银子老师(笔名,真名永不进任何公开文件)
- **语料协作产出**:Claude (Anthropic) 在银子老师风格基线下产出
- **风格基线来源**:Phase13_PersonaSamples_v1(长门有希 + 秋山澪混合)
- **不署**:真名不进任何 yaml/md/showcase 文件

End of Report.
