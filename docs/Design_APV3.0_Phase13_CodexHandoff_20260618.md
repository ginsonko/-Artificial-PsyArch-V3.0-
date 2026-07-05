# APV3.0 — 给 Codex 的上下文交接 + Phase 13 启动包

日期: 2026-06-18
目的: 让 Codex 在不读 Claude 14 轮审阅历史的情况下,完整理解 Phase 13 设计目的、用户哲学、最终目标。

---

## 1. 给 Codex 的一句话

**你已经完成 Phase 8-10 共 25 个 phase,质量极高。现在用户希望 Phase 11 完成后启动 Phase 13(认知课程)— 这不是又一个架构 phase,而是开源前的核心内容浸泡阶段。**

详细设计稿: [Design_APV3.0_Phase13_CognitiveCurriculum_v1_20260618.md](Design_APV3.0_Phase13_CognitiveCurriculum_v1_20260618.md)

---

## 2. 用户的最终目标(必读)

### 2.1 用户原话浓缩

用户希望开源时系统具备**幼儿园-小学生水平的中文心智 + 多模态常识**,而不是"婴儿期啥都不会"。

具体要求:
- 3500-5000 常用汉字识字(含偏旁笔画 → 能揣测没见过的字)
- 5000-7000 常用词汇
- 200-300 基本表达范式
- 800-1200 视觉常识对象(**真实图像 + 每对象 ≥ 3 张**)
- 100-200 音频常识
- 100-200 行动反应原型
- 50-100 社交常识

### 2.2 用户希望实现的差异化卖点(开源传播关键)

1. **"你能看到它怎么学的"** — Web 工作台显示 audit trail
2. **"你能教它,而且它真的学"** — RPE + 反例撤销可见影响
3. **"它会想象+会犯人类的错"** — SDPL packet learning 涌现
4. **"它有持续身份和跨天记忆"** — SQLite + cue rehydration
5. **"完全开源+可审计+可定制"** — 课程包社区贡献

### 2.3 4 个应用场景(开源后的主用例)

按用户优先级(待用户确认):
1. 纯文本对话(Web/CLI)
2. 桌宠多模态(SNS)
3. Agent + LLM 协作
4. 具身智能预演

---

## 3. v14 设计哲学不动摇(继承前 14 轮审阅)

Phase 13 严格遵守 v14 UNIFIED 全部红线:

| 红线 | Phase 13 落地方式 |
|---|---|
| ❌ 不许字面量数字 | 全部课程内容在 yaml |
| ❌ 不许 keyword 路由 | 教学走 SDPL HEARSAY proposition 路径 |
| ❌ 不许学生侧 LLM | LLM 只设计时辅助生成 yaml 草稿,**runtime 永不调** |
| ❌ 不许 audit_db 进 cognitive | Phase 8.3 边界保持 |
| ❌ 不许新 SA family | 全部用既有 VocabSA / MarkerSA / EntitySA 等 |

**特别强调**:Phase 13 不引入新公式形态,只是**充分利用 Phase 8-11 已有架构**(SDPL / RPE / trust prior / long_term cold index / 共情等)做大规模教学浸泡。

---

## 4. Phase 13 设计稿核心要点

### 4.1 子阶段(8 个 + 1 验收)

```
Phase 13.1   Curriculum Substrate(课程基础设施 — 必须先做)
Phase 13.2   Character Curriculum(识字 3500-5000 字)
                ↑ 用户特别强调:偏旁部首作为独立 VocabSA 一等公民
                  让 AP 能"揣测没见过的字"
Phase 13.3   Vocabulary Curriculum(词汇 5000-7000)
Phase 13.4   Visual Common Sense Curriculum(视觉 800-1200 对象)
                ↑ 用户特别强调:真实图像 + 每对象 ≥ 3 张(推荐 5-10 张)
                  跨光照/角度/个体提取不变量
Phase 13.5   Audio Common Sense Curriculum(音频 100-200)
Phase 13.6   Expression Paradigm Curriculum(表达 200-300 范式)
Phase 13.7   Action Prototype Curriculum(行动 100-200)
Phase 13.8   Social Common Sense Curriculum(社交 50-100)
Phase 13.9   Four Scenario Validation Suite(四场景 demo)
```

### 4.2 关键技术承诺

1. **课程包 = 6 元组**(Content / Paired / Validation / Modality / Teaching seq / Anti-examples)
2. **教学经 SDPL 路径**(HEARSAY + trust_promoted gate)
3. **trust_promoted 允许绕过 ΔP 显著性**(信任教师加速),**但保留 hold-out 验证**
4. **跨课程一致性 gate**(防教学碎片化)
5. **课程内容物理外化到 `config/curriculum/`**(yaml + 多媒体资产)

### 4.3 偏旁部首机制(用户特别要求,Phase 13.2 核心)

**关键设计**:每个偏旁(如"氵""扌""灬")是**独立 VocabSA 一等公民**。

含此偏旁的字 vocab SA 与偏旁 vocab SA 共现 → 自然涌现"语义场关联":
- "氵" 部 → water 语义场(沙/河/海/湖)
- "扌" 部 → hand action 语义场(打/拿/推/拉)
- "灬" 部 → fire/heat 语义场(热/煮/烹)

教过 50 个常用 "氵" 字后,系统看到从未见过的"湍"字 → 预测"和水有关"
**这是 LLM 没有的真泛化能力**

详见设计稿 §3.2.1-3.2.3。

### 4.4 视觉常识真实图像策略(用户特别要求,Phase 13.4 核心)

**用户原话**:"视觉常识我推荐用真实图像,而且每个常识都建议用复数个图像,这样才能让它明白图像中相似的部分是什么,最终抽象出对应的认知"

**关键设计**:
- 每对象 ≥ 3 张(数学最小)
- 推荐 5-10 张(数学最优)
- 覆盖不同光照 / 角度 / 个体差异
- 公开数据集为主(ImageNet / COCO / Open Images / Freesound)
- 严禁合成图像(SD/GAN)— 会引入伪特征污染 vocab

详见设计稿 §3.4.2-3.4.5。

---

## 5. Phase 11 / 12 与 Phase 13 关系

```
当前位置:Phase 10 完成,Phase 11 设计中
        ↓
Phase 11  8-12 岁元认知(meta/abstract/goal/deliberative/self)
        ↓
Phase 12  Demo Substrate(Web 工作台 polish + 课程加载器)
          ↓ (这是用户希望提前准备的"展示基础设施")
Phase 13  Cognitive Curriculum(本稿) ← 内容浸泡
          ↓
Phase 14  Four Scenario Polish(开源前 demo 拿捏)
          ↓
Phase 15+ 真实硬件 / SNS 桌宠产品 / Agent 工作流
```

---

## 6. 用户和我已确认的几个关键决策

| 项 | 决策 |
|---|---|
| 视觉用真实还是合成图像 | **真实**(用户原话,我同意) |
| 每对象图像张数 | **≥ 3 张,推荐 5-10**(用户原话,我细化) |
| 偏旁是不是一等 SA | **是**(用户灵感,我数学化) |
| 课程包格式 | **yaml + 多媒体资产**(我建议,继承 v14 纪律) |
| 教学是否绕过 SDPL | **绝不绕过**(继承 v14 红线) |
| LLM 在 runtime 角色 | **永不调用**(继承 v14 红线) |

---

## 7. 待用户决策的问题(详见设计稿 §7)

Codex 实施 Phase 13 前应等用户对以下问题表态:

1. 视觉图像版权 / 来源策略(我推荐公开数据集 + 自采)
2. 音频版权策略(我推荐 Freesound CC0 + 自录)
3. 课程包社区贡献接口何时开放(我推荐 alpha 就开)
4. 商业化路径偏好(影响 license 字段设计)
5. 4 场景优先级(影响 Phase 13.7 行动库分配)
6. 教学课程的"声音/人设"(中性 vs 亲切 vs 故事化)
7. 是否做"早期 vs 后期内容"分龄分层(我推荐做)

---

## 8. Codex 实施 Phase 13 时的注意事项

### 8.1 与前序 Phase 的衔接

Phase 13 实施时必须复用:
- Phase 8.3 PERCEIVED / HEARSAY / CORRECTION 三层文本边界
- Phase 8.4 SDPL packet + Q backoff
- Phase 8.5 cognitive_feelings(reality_sense / hearsay_sense 等)
- Phase 8.6 视觉感受器 + 量化桶
- Phase 8.7 视焦点 + saccade
- Phase 8.13 音频 filterbank
- Phase 8.15 long_term cold index + cue rehydration
- Phase 9.2 RPE
- Phase 9.4 attachment(entity_user_sa)
- Phase 9.6 共情
- Phase 10.6 hierarchy SA
- Phase 10.7 trust prior(关键 — Phase 13 教学就是 trust_promoted 加速)

### 8.2 红线脚本扩展

`scripts/red_line_check_v14.py` 加 `--phase 13.X` 支持:
- 13.1 deliverables: curriculum substrate 模块齐全
- 13.2 deliverables: characters/_index.yaml 存在 + 至少 500 char 内容
- 13.3 deliverables: vocabulary/_index.yaml 存在 + 至少 1500 词内容
- ... 依此类推

### 8.3 内容质量 gate(新增)

每个课程包 commit 必经:
1. schema 验证(自动)
2. 完整性验证(自动,反例数 + 视觉张数)
3. 跨课程一致性验证(自动)
4. 人工抽查审校(每 100 条抽 10)
5. AP 试教验证(自动,dev AP 跑课程包并验证 validation 测试)

### 8.4 中文展示页(开源传播关键)

每子 phase 完成时必出中文展示页(类比 Phase 9/10 风格)。最终 Phase 13.9 时合并成开源发布的核心材料。

---

## 9. 总体进度估算(用户问到了)

按 Codex 20 分钟/phase 节奏 + 内容工程量:

- **架构层**:~10 小时 Codex
- **内容层**:**~3-4 周**(视觉图像采集 + 审校是关键瓶颈)
- **总耗时**:**3-4 周到 v1.0 正式版**

**分批发布**:
- 第 1 周末:alpha(500 字 + 1500 词 + 50 范式 + 200 视觉 + 20 行动)
- 第 2 周末:beta
- 第 4 周末:rc
- 第 4-5 周末:v1.0 正式开源

---

## 10. 给 Codex 的最终指令(复述)

1. **设计稿是 v1,可能用户审后还会修订**
2. **Phase 11 完成前不启动 Phase 13**(架构必须先齐)
3. **Phase 13 实施前 7 个用户决策点必须确认**
4. **Phase 13.1 substrate 必须先做**
5. **课程内容分批迭代**(alpha→beta→rc→v1.0)
6. **图像版权严格审查**
7. **跨课程一致性 gate 必跑**
8. **每子 phase 严格 5 段闭环**(设计/审查/落地/验收/报告)
9. **任何超出设计稿范围的提议先停下问 Claude**

---

— 接手线程,2026-06-18

关联文档:
- [v14 UNIFIED 主稿](Design_APV3.0_Humanlike_Multimodal_Foundation_v14_UNIFIED_20260617.md)
- [v14.1 ERRATA](Design_APV3.0_Humanlike_Multimodal_Foundation_v14_1_ERRATA_20260617.md)
- [Phase 8 审计索引](FinalReport_Phase8_AuditTrailIndex_20260617.md)
- [Phase 9 总报告](FinalReport_Phase9_1_to_9_9_MindDepth_20260617.md)
- [Phase 10 总报告](FinalReport_Phase10_1_to_10_8_HierarchicalMind_20260618.md)
- [Phase 13 设计稿(本稿配套)](Design_APV3.0_Phase13_CognitiveCurriculum_v1_20260618.md)
