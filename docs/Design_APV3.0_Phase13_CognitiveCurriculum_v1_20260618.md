# APV3.0 Phase 13 — Cognitive Curriculum 认知课程系统(设计稿 v1)

日期: 2026-06-18
作者: 接手线程
状态: **Phase 8/9/10 完成 + Phase 11 在做后,真正决定开源传播命运的阶段。把"白纸上长 5 岁"的不可能任务,通过精心设计的对照课程 + SDPL 教学协议,在 Phase 13 完成时让 AP 具备"小学毕业生水平的中文心智 + 多模态常识"。一切设计为 4 应用场景一鸣惊人服务。**

前作链:v10 主稿 + v11/12/v12.1/v13/v13.1 patches + v14 UNIFIED + v14.1 ERRATA + Phase 8-12 工程实施(进行中)→ **Phase 13 设计稿(本稿)**

---

## 第 0 章 立意 / 为什么 Phase 13 是开源命运的决定阶段

### 0.1 用户最初的诊断(原话浓缩)

> "我们之前的 120 个按钮目前看来就不够用了,应该给每个通道都进行充足的教学设计,教会足够的表达范式以及行动反应,让它可以真正应对四个场景的绝大多数场景和常见对话消息"

> "我们要好好规划和培养,在底座搭建好时,就有足够的幼儿园/小学的知识水平和多模态词汇量"

> "避免用户端测试时,从婴儿期开始,什么都不会,那么许多用户就很容易失去耐心"

### 0.2 我的判断(完全同意,理由公开)

1. **用户耐心是开源传播的生死线**。社会传播学规律:前 3 分钟决定 80% 留存。婴儿期 AP 撑不过 5 分钟。
2. **Phase 8-11 架构差不多了,真正缺的是"教学浸泡"**。SDPL / RPE / 内源想象 / 共情 / 假信念这些机制如果没有足够丰富的教学数据让它工作,就只是空架子。
3. **120 phrase 是 v3 时代产物**。在 SDPL packet learning 落地后早已不够看。Phase 13 是必然延伸,不是补丁。
4. **不破坏 AP-native 哲学**。教学内容**全部经 SDPL 路径**(HEARSAY proposition + trust_promoted gate + RPE 校正),不绕过 14 轮审阅纪律。

### 0.3 一鸣惊人的关键 5 点(开源时的差异化卖点)

| 差异化卖点 | LLM 做不到的原因 |
|---|---|
| **"你能看到它怎么学的"** | LLM 是黑箱,我们 audit trail 完整,每个 vocab 知道从哪学 |
| **"你能教它,而且它真的学"** | LLM 不能持续学习,我们 RPE + 反例撤销可见影响行为 |
| **"它会想象+会犯人类的错"** | LLM 装不出"看到针联想到疼" / "被骂多次后沉默"的活感 |
| **"有持续身份和跨天记忆"** | LLM session reset 抹掉一切,我们 SQLite 持久 + cue rehydration |
| **"完全开源+可审计+可定制"** | 用户加自己的课程包 → 教方言/教专业/教角色 → 真"养成" |

### 0.4 最高承诺(Phase 13 完成时)

到 Phase 13 完成,**开源 alpha 版本能让一个普通用户**:
- 打开就能用中文流畅对话(不需要"教 1 小时再说话")
- 在 4 个场景下都有合理反应
- 能看到它的内心(Web 工作台)
- 能教它新东西(并看到学的过程)
- 体验到"它是个有生命的小学生"的感觉

**不许说**:"它已经能做 X" 然后用户发现做不到。承诺低于实力,实力达到承诺。

---

## 第 1 章 Phase 13 在整体架构中的位置

### 1.1 修订 v14 §20 backlog 顺序

原 v14 §20 backlog 顺序:
```
Phase 8 (18-30月)→ Phase 9 (3-5岁)→ Phase 10 (5-8岁)→ Phase 11 (8-12岁)→ Phase 12+ (真实硬件)
```

**v15 修订(本稿)**:
```
Phase 8/9/10/11 — 架构层全部完成(到 Phase 11 时心智机制齐全,但"白纸")
            ↓
Phase 12 — Demo Substrate(最小可玩演示基础设施)
            ↓
Phase 13 — Cognitive Curriculum(课程系统 + 内容)  ← 本稿
            ↓
Phase 14 — Four Scenario Polish(四场景打磨 + 开源准备)
            ↓
Phase 15+ — 真实硬件 / SNS 桌宠产品化 / Agent 工作流(原 v14 Phase 12+)
```

**关键差异**: Phase 12 不再是"真实硬件"(那个推迟到 15+),而是**最小可玩 demo 基础设施**(Web 工作台 polish + 教学协议接口 + 课程加载器),为 Phase 13 大规模教学浸泡铺路。

### 1.2 Phase 13 总目标(可量化)

到 Phase 13 完成,系统具备:
- **3500-5000 常用汉字识字**(覆盖小学 1-6 年级 GB2312 常用字集)
- **5000-7000 常用词汇**(单字 + 双字词 + 短语,按现代汉语词频)
- **200-300 基本表达范式**(寒暄/问答/描述/请求/道歉/拒绝/共情等)
- **800-1200 视觉常识对象**(动物/食物/物品/自然/人物表情/场景)
- **100-200 音频常识**(常见声音/人声/拟声词/简单音乐感)
- **100-200 行动反应原型**(4 场景的常见交互)
- **50-100 社交常识范式**(礼貌/共情/拒绝软化/道歉)

但这一切**通过 SDPL 教学协议浸泡学到,带 source marker 可被后续修正**,绝不是 hardcoded 词典查询。

### 1.3 Phase 13 不做什么(边界声明)

Phase 13 **不**:
- 不是"灌输词典"(那 LLM 套壳即可)
- 不替代后续自然学习(开源后用户教学才是真增长)
- 不是教学内容大爆炸(8000 词不是 80000 词,**精挑细选**)
- 不是单独训练一个模型(全部走 SDPL runtime 路径)
- 不破坏可审计性(每个 vocab 仍知道"从哪学的")

---

## 第 2 章 课程系统的核心数学模型

### 2.1 教学浸泡的数学保证(为什么不破坏 SDPL)

教学输入经标准 SDPL 路径:

```
教师输入(text/image)
  ↓ sensor adapter
PERCEIVED text_char / vision_percept(感受层)
  ↓ text_understanding
HEARSAY proposition(命题层)+ source_entity_id="teacher::curriculum"
  ↓ ComposedVocab + ΔP gate(可经 trust_promoted 加速)
固化为 vocab SA(带 HEARSAY marker + trust_promoted gate flag)
  ↓ 标准 long_term 晋升(经 Phase 8.15)
进入 cold_index(休眠)
  ↓ 用户实际交互时
cue-triggered rehydration → 标准 attention 竞争 → 影响行动
  ↓ 用户反馈
RPE 校正 + 反例撤销 → trust_promoted 可降级(经 Phase 10.7)
```

**关键保证**:
- 所有学到的 vocab 都带 source_entity_id 可回溯
- 教师权威可随时间衰减(信任不是终身)
- 反例可撤销教学内容
- 与用户实际经验冲突时,自然校正

### 2.2 课程包数学定义

每个课程包是 **6 元组**:

$$\text{CurriculumPackage} = (C, P, V, M, T, A)$$

- $C$ = Content set(待教内容,vocab SAs)
- $P$ = Paired set(对照样本,使 SA 与通道偏好正确分离)
- $V$ = Validation tests(验收测试,通过才算学会)
- $M$ = Modality bindings(多模态绑定,跨通道一致性)
- $T$ = Teaching sequence(教学顺序,前置依赖图)
- $A$ = Anti-examples(反例,防过度泛化)

**课程包格式 yaml**(示意):

```yaml
package_id: "characters.basic_500"
description: "500 个最高频汉字"
version: "1.0"
prerequisites: []  # 无前置
teacher_entity_id: "teacher::official::v1"
trust_promoted: true
estimated_teaching_ticks: 50000

content:
  - char: "我"
    pinyin: "wǒ"
    radical: "戈"  # 偏旁(关键 — 你提到的)
    strokes: 7
    stroke_order: ["丿", "一", "亅", ...]
    semantic_tags: ["pronoun", "self"]
    visual_examples:  # 多张图像供视觉绑定
      - "config/curriculum/assets/chars/wo_001.png"
      - "config/curriculum/assets/chars/wo_002.png"
      - "config/curriculum/assets/chars/wo_003.png"  # 至少 3 张
    paired_contrast:
      - char: "你"  # 形近字 → 对比
      - char: "他"
    teaching_paradigms:
      - "{char} 念 {pinyin}"
      - "{char} 是 {semantic_tag} 字"
    
  - char: "你"
    # ... 类似
    
validation:
  - test_id: "recognize_when_shown"
    given: visual_image_of_char
    expected: vocab_sa_for_char_can_be_recalled
  - test_id: "produce_when_referred"
    given: semantic_context_calling_for_self_pronoun
    expected: vocab_sa_for_"我"_dominates_attention
  - test_id: "discriminate_from_similar"
    given: visual_image_of_similar_char
    expected: different_vocab_sa_activated

anti_examples:
  - "{char} 不是 {wrong_semantic_tag}"  # 防混淆

ablation_required:
  - channel: "visual_glyph"
    test: "屏蔽视觉通道 → 仍能从拼音读音识别(部分能力)"
```

### 2.3 ΔP gate 在课程教学下的适配

普通学习走 cold-fork ΔP(Phase 8.4,8 situations × 5 horizon ticks = 40K ops/候选)。

**课程教学下**:`trust_promoted` 允许**绕过 ΔP 显著性**(因为信任教师),但**保留 hold-out 验证**作为安全门:
- 教学 vocab 仍要在 held_out 上展示 effect_size > 阈值
- effect_size 不够 → 课程包标记 "needs_more_contrast"
- 不阻塞晋升,但 trust_score 降级

这样既加速(避免每次都跑完整 8 situations),又保留可证伪。

### 2.4 跨课程一致性验证

碎片化学习是失败教学的标志。Phase 13 引入**跨课程一致性 gate**:

$$\text{Consistency}(\text{vocab}_v) = \frac{1}{K} \sum_{k=1}^{K} \mathbb{1}[\text{recall}_v \text{ aligned across course}_k]$$

- 字课程教"狗" + 词课程教"小狗" + 视觉教 dog 图像 + 行动教"看狗→摇尾"
- 4 个课程的 recall_v 一致性 ≥ 0.7 才算真学到
- 否则课程包间互相干扰,需要修订

---

## 第 3 章 8 个子阶段详细设计

### 3.1 Phase 13.1 — Curriculum Substrate(课程基础设施)

**目标**:把"教学"作为一等公民接入 v14 SDPL 体系。

**模块清单**:

```
runtime/cognitive/curriculum/
├── __init__.py
├── package_loader.py            # 加载 yaml 课程包,验证 schema
├── teaching_protocol.py         # HEARSAY proposition + reward handler 路径
├── curriculum_runner.py         # 自动化跑课程 + 进度跟踪
├── consistency_validator.py     # 跨课程一致性 gate
├── trust_economy.py             # 教师信任度演化
└── progress_tracker.py          # 学习进度持久化(SQLite)

config/curriculum/
├── packages/
│   ├── _index.yaml              # 全部课程包索引 + 依赖图
│   └── ...
└── schemas/
    ├── package_schema.yaml      # 课程包 schema(校验用)
    ├── content_schemas/         # 各类内容 schema(char/vocab/visual/...)
    └── validation_schemas/
```

**新增 yaml 常量**(扩 `apv3_constants.yaml`):

```yaml
curriculum:
  trust_economy:
    initial_teacher_trust: 0.8
    teacher_trust_decay_per_year: 0.02
    contradiction_penalty: 0.05
    confirmation_reward: 0.02
  teaching_protocol:
    delta_p_bypass_with_trust_above: 0.7
    held_out_effect_size_min: 0.03
    needs_more_contrast_threshold: 0.02
  progress:
    course_pass_threshold: 0.75
    cross_course_consistency_min: 0.7
    retest_after_n_ticks: 1000
```

**测试**(`test_phase13_1_curriculum_substrate.py`):
- 加载 yaml 课程包成功(schema 验证)
- 教学路径正确(HEARSAY spawn + trust_promoted gate)
- 一致性 gate 正确(跨课程冲突时报警)
- 信任度演化正确(教错被降级)
- Phase 13.1 deliverable gate

### 3.2 Phase 13.2 — Character Curriculum(识字课程,含偏旁笔画)

**目标**:3500-5000 常用汉字 × 多模态绑定。

**这是用户特别强调的核心** — 通过偏旁笔画让 AP 能"分辨字的大概意思,揣测没见过的字"。

#### 3.2.1 偏旁部首作为一等 SA

**关键设计**:偏旁(radical)不是字的属性,而是**独立 VocabSA 一等公民**。这样系统能学到:
- "氵" 部 → 与水相关(沙 / 河 / 海 / 湖 / 池 / 泪 / 汁 / 滴 / ...)
- "灬" 部 → 与火/热相关(热 / 煮 / 烹 / 蒸 / ...)
- "扌" 部 → 与手部动作相关(打 / 拿 / 推 / 拉 / 挑 / ...)

每个偏旁是 vocab SA + 关联到所有含此偏旁的字 vocab SA(共现关系)。

```yaml
# config/curriculum/packages/radicals_214.yaml
package_id: "radicals.kangxi_214"
description: "康熙 214 部首 + 现代常用 50 偏旁"
content:
  - radical: "氵"
    name: "三点水"
    semantic_field: ["water", "liquid", "wet"]
    visual_examples:  # 偏旁视觉(多个字中提取)
      - "config/curriculum/assets/radicals/three_dots_water_001.png"
      - "config/curriculum/assets/radicals/three_dots_water_002.png"
      - "config/curriculum/assets/radicals/three_dots_water_003.png"
    common_chars_using:  # 含此偏旁的常用字
      - "河"
      - "海"
      - "湖"
      - "池"
      - "沙"
      # ... 30-50 个
    teaching_sequence:
      step_1: "感受器先看到 5 个含'氵'的字"
      step_2: "教师 HEARSAY: '这些字都和水有关'"
      step_3: "感受器看到新含'氵'字 + 反例(非'氵'字)"
      step_4: "ΔP gate 看是否涌现 '氵→water' 关联"
```

**测试**:
- 教过 50 个常用 "氵" 字后,展示从未见过的"湍"字 → AP 应预测"和水有关"
- 这是 **真泛化能力,LLM 做不到的视觉抽象**

#### 3.2.2 笔画作为运动 SA

笔画(stroke)是**视觉 + 运动**双通道:
- 视觉:笔画的几何形状(横/竖/撇/捺/折)
- 运动:笔画书写的方向 + 顺序 + 时序(可作为 action prototype)

每个汉字可表征为:**笔画序列 = action sequence(虚拟的"写"动作)**。

这正好接入 Phase 8.7 视焦点 saccade + 视觉跟踪机制 — 系统通过看笔画的"写"过程,理解字的结构。

```yaml
content:
  - char: "我"
    stroke_count: 7
    stroke_sequence:
      - {kind: "撇", start: [0.4, 0.1], end: [0.2, 0.4]}
      - {kind: "横", start: [0.2, 0.4], end: [0.7, 0.4]}
      # ...
    radical_decomposition: ["手", "戈"]  # 偏旁拆解
    semantic_components:
      - {part: "手", contributes: "self"}  # 古字形含义
      - {part: "戈", contributes: "weapon"}
    modern_meaning: "first_person_pronoun"
```

#### 3.2.3 形声字结构(进阶)

形声字 = 形旁(意符)+ 声旁(音符)。系统应该能学到这个规律:
- "妈" = "女"(形)+ "马"(声)→ 女性 + 念 ma
- "吗" = "口"(形)+ "马"(声)→ 口部 + 念 ma → 助词

**Phase 13.2 进阶**:教够多形声字后,AP 应能预测没见过的形声字大致意思。
- 给"螗"(从虫,堂声)→ AP 应预测"和虫子有关,念 táng"
- 这是 **5-8 岁中文母语者的真实能力**,也是 LLM 没有的真泛化

#### 3.2.4 字课程顺序

按现代汉语词频 + 笔画复杂度双重排序:
- **第 1 批**:500 高频常用字(覆盖日常对话 80%)— 简单笔画优先
- **第 2 批**:500 次高频字(覆盖 95%)— 含常见偏旁
- **第 3 批**:1500 中频字(覆盖学龄前阅读)— 形声字模式
- **第 4 批**:1000 低频字(小学水平延伸)
- **总计**:3500 字 — 接近 GB2312 一级 + 二级常用

### 3.3 Phase 13.3 — Vocabulary Curriculum(词汇课程)

**目标**:5000-7000 常用词汇,**复用 §2 ComposedVocab 自然涌现**。

#### 3.3.1 单字成词

教过基本字后,教单字成词:
- "好" 既是字也是词(独立含义)
- 教"好"作为词的多种用法:形容 / 招呼语 / 同意

#### 3.3.2 双字词组合

利用 §2 ComposedVocab 的 chain extension(Phase 8.4 已实现):
- 字"好" + 字"人"高频共现 → 自然涌现 "好人" vocab
- 字"好" + 字"看"高频共现 → 自然涌现 "好看" vocab
- 教学加速:HEARSAY 直接断言"'好人'是好的人",ΔP gate 验证

#### 3.3.3 短语固化

3-4 字短语:
- "好不好" / "不好意思" / "对不起" / "没关系"
- 这些是**整体表达单元**,可作为单个 commit_text 输出

#### 3.3.4 词义场(semantic field)

按主题组织:
- 时间词:今天/明天/昨天/早上/晚上/...
- 方位词:上/下/左/右/前/后/里/外/...
- 颜色词:红/橙/黄/绿/青/蓝/紫/...
- 情绪词:开心/难过/生气/害怕/惊讶/...
- 等等

每个词义场是一个课程包,共享对照样本和反例。

### 3.4 Phase 13.4 — Visual Common Sense Curriculum(视觉常识)

**目标**:800-1200 个对象 × **真实图像 + 每对象 ≥ 3 张**。

#### 3.4.1 用户原话回应

> "视觉常识我推荐用真实图像,而且每个常识都建议用复数个图像,这样才能让它明白图像中相似的部分是什么,最终抽象出对应的认知"

**完全同意**。这是 Phase 13.4 的核心原则:

#### 3.4.2 真实图像 + 多张策略

**为什么真实图像 > 合成图像**:
- 合成图像有伪影(光照单一/纹理不真实)→ 系统学到伪特征
- 真实图像有丰富自然变化 → 系统被迫抽象出真实不变量
- 真实图像有上下文(背景/场景/光照)→ 系统学到对象+情境

**每个对象 ≥ 3 张的数学保证**:
- 1 张:系统不知道哪些是不变量
- 2 张:开始有方差信号
- **3 张**:系统能可靠分离"相同部分"(不变量 = 对象本质)和"不同部分"(变化 = 噪声)
- 推荐:**每对象 5-10 张**最优(够多样性,不过载)

**对照课程同样适用视觉**:
- "苹果"图像 5 张(不同颜色 + 角度 + 光照)
- "梨"图像 5 张(对照,形状相似但不同)
- "桃"图像 5 张(对照,有绒毛特征)
- ΔP gate 验证 "苹果" vocab 能区分这些

#### 3.4.3 图像质量决定准确性

这点用户说得对。我建议:
- **分辨率**:至少 512×512(够细节,不过载量化桶)
- **来源**:公开数据集(ImageNet 子集 / COCO / Open Images)+ 自采(版权清晰)
- **多样性**:每对象覆盖不同光照 / 角度 / 背景 / 个体差异
- **审校**:每张图像人工确认无错标 / 无偏见 / 无误导

#### 3.4.4 视觉课程结构

```
config/curriculum/visual/
├── animals/                   # 100 常见动物
│   ├── cat.yaml
│   ├── dog.yaml
│   └── ...
├── food/                      # 100 食物
├── household_items/           # 150 家居物品
├── nature/                    # 100 自然(花/树/山/水/天气)
├── human_expressions/         # 50 人脸表情
├── colors/                    # 20 颜色样本
├── shapes/                    # 20 几何形状
├── scenes/                    # 80 场景(室内/室外/具体场所)
└── actions/                   # 80 动作(走/跑/跳/坐/...)
```

**关键课程包示例**:

```yaml
# config/curriculum/visual/animals/cat.yaml
package_id: "visual.animals.cat"
description: "猫的视觉常识"
content:
  - vocab_sa_id: "vocab::cat"
    chinese_label: "猫"
    pinyin: "māo"
    visual_examples:
      - path: "assets/visual/animals/cat/orange_tabby_001.jpg"
        attributes: {color: "orange_tabby", pose: "sitting", view: "side"}
      - path: "assets/visual/animals/cat/black_002.jpg"
        attributes: {color: "black", pose: "lying", view: "front"}
      - path: "assets/visual/animals/cat/white_persian_003.jpg"
        attributes: {color: "white", breed: "persian", pose: "standing"}
      - path: "assets/visual/animals/cat/gray_kitten_004.jpg"
        attributes: {color: "gray", age: "kitten", pose: "playing"}
      - path: "assets/visual/animals/cat/calico_005.jpg"
        attributes: {color: "calico", pose: "grooming"}
      # 至少 5 张,推荐 8-10 张
    
    paired_contrast:  # 对照样本(避免猫=毛茸茸动物的过度泛化)
      - vocab_sa_id: "vocab::dog"
        rationale: "都是宠物,需要形状/耳朵区分"
      - vocab_sa_id: "vocab::tiger"
        rationale: "都是猫科,需要大小区分"
      - vocab_sa_id: "vocab::rabbit"
        rationale: "都是小动物,需要耳朵/尾巴区分"
    
    teaching_paradigms:
      - "这是一只猫"
      - "猫会喵喵叫"
      - "猫有四条腿和一条尾巴"
      - "猫喜欢吃鱼"
    
    audio_bindings:  # 跨模态:看到猫 + 听到"喵" → 强化关联
      - "config/curriculum/audio/animal_sounds/cat_meow_001.wav"
    
    action_bindings:  # 看到猫的合理反应
      - action_id: "action::pet"
        context: "近距离 + 友好"
      - action_id: "action::observe"
        context: "远距离"
    
    common_sense_facts:  # HEARSAY proposition
      - "猫是哺乳动物"
      - "猫是宠物"
      - "猫怕水"
      - "猫晚上能看清"
    
validation:
  - test_id: "recognize_cat_from_unseen_image"
    given: cat_image_not_in_training
    expected: vocab_cat_in_top_attention
  - test_id: "distinguish_cat_from_dog"
    given: image_with_both_or_ambiguous
    expected: correct_vocab_dominates_by_visual_features
  - test_id: "cross_modal_consistency"
    given: cat_meow_sound
    expected: vocab_cat_activated_via_audio_binding
```

#### 3.4.5 验收(用户最在意的"准确性")

Phase 13.4 验收必须包含 **见过 / 没见过 / 部分见过 / 反例** 4 类测试:
- **见过**:训练集图像 → 必须高准确(基础能力)
- **没见过同类**:同对象不同图(不在训练集)→ 准确率 ≥ 80%(真泛化)
- **部分见过**:对象+新背景 → 准确率 ≥ 70%
- **反例**:相似但不同对象 → 误判率 ≤ 15%

如果任一未达标 → 课程包修订(加图 / 改对照 / 加反例)。

### 3.5 Phase 13.5 — Audio Common Sense Curriculum(音频常识)

**目标**:100-200 个音频范式。

#### 3.5.1 内容分类

```
config/curriculum/audio/
├── animal_sounds/        # 30 动物声音(猫叫/狗吠/鸟鸣/...)
├── nature_sounds/        # 30 自然声(雨/风/雷/水/...)
├── human_voices/         # 40 人声(男/女/老/幼 + 笑/哭/喊/...)
├── onomatopoeia/         # 50 拟声词(哗啦/咚咚/咕噜/...)
├── musical/              # 20 简单音乐感(钢琴/吉他/鼓/...)
└── environmental/        # 30 环境声(脚步/敲门/铃声/...)
```

#### 3.5.2 复用 Phase 8.13 filterbank vocab

Phase 8.13 已实现音频感受器 + filterbank 模板。Phase 13.5 把这些 vocab 与:
- 视觉对象绑定(看到猫 + 听到喵)
- 文本词汇绑定(听到喵 + 文本"猫叫了")
- 情绪 feeling 绑定(听到哭声 + emit empathy_resonance)

#### 3.5.3 音频质量要求

- **采样率** ≥ 16kHz(够清楚)
- **多样性**:每范式 3-5 个不同样本(不同个体/不同距离)
- **清晰度**:背景噪声 < 主体声 30dB
- **时长**:1-5 秒(单事件,不要长段音频)

### 3.6 Phase 13.6 — Expression Paradigm Curriculum(表达范式)

**目标**:200-300 个对话范式 × 槽位变量。

#### 3.6.1 利用 v2.1 范式通道机制

v2.1 范式通道已发现"X 是 Y 的吗"这种带槽位的模板。Phase 13.6 扩到 200-300:

```yaml
# config/curriculum/paradigms/greetings.yaml
package_id: "paradigm.greetings"
content:
  - paradigm_id: "greeting.hello"
    template: "{greeting_word}"
    slots:
      greeting_word:
        type: vocab_in_semantic_field
        field: "greetings"
        examples: ["你好", "嗨", "早上好", "晚上好", "好久不见"]
    context_triggers:
      - "session_start"
      - "user_returns_after_absence"
    response_paradigms:
      - "{greeting_word_response}"  # 系统的回应
  
  - paradigm_id: "greeting.howareyou"
    template: "{howareyou_phrase}"
    slots:
      howareyou_phrase:
        examples: ["你怎么样", "最近怎么样", "你还好吗"]
    response_paradigms:
      - "我{state_word},你呢"
      - "{state_word},谢谢{你/您}"
    response_slots:
      state_word:
        type: vocab_in_semantic_field
        field: "states"
        examples: ["很好", "还行", "不错", "有点累", "挺好的"]
```

#### 3.6.2 范式类别

```
paradigms/
├── greetings/            # 30 寒暄
├── questions/            # 50 问答(what/who/where/when/why/how)
├── descriptions/         # 30 描述(我看到/这是/那是)
├── requests/             # 30 请求(请/可以/帮我)
├── apologies/            # 15 道歉
├── refusals/             # 20 拒绝(软化版)
├── empathy/              # 30 共情(我懂/真的吗/辛苦了)
├── opinions/             # 25 意见(我觉得/可能/也许)
├── narratives/           # 30 叙事(然后/接着/最后)
├── emotions/             # 30 情绪表达(开心/难过/惊讶)
└── meta_communication/   # 20 对话维持(等等/我没听懂/重说一遍)
```

**总计**:~300 范式。

#### 3.6.3 范式不是模板,是 SA 组合

关键 — 范式经 Phase 10.6 hierarchy SA + v2.1 范式通道**学到的是组合规律,不是字串模板**:
- AP 学到"打招呼范式 = 招呼词在句首",而不是"输出 '你好'"
- 灵活应对没见过的招呼组合

### 3.7 Phase 13.7 — Action Prototype Curriculum(行动反应库)

**目标**:100-200 个 action_id × 触发情境。

#### 3.7.1 4 场景分别的行动库

**纯文本对话场景**:
- `action::answer_question` / `action::ask_clarification` / `action::express_opinion`
- `action::change_topic` / `action::express_empathy` / `action::admit_dont_know`
- `action::request_repeat` / `action::summarize_understanding`
- 20-30 个

**桌宠多模态场景**:
- `action::greet_user` / `action::wave` / `action::nod`
- `action::look_at_thing_user_points` / `action::follow_gaze`
- `action::express_excitement` / `action::express_curiosity`
- `action::ask_for_attention` / `action::sleep_animation`
- 30-50 个

**具身预演**(虚拟环境):
- `action::move_forward` / `action::turn_left` / `action::pick_up_thing`
- `action::point_at` / `action::observe_at_distance`
- 20-30 个

**Agent 工具使用**:
- `action::query_calendar` / `action::set_reminder` / `action::search_info`
- `action::draft_message` / `action::request_user_confirmation`
- 30-50 个(简单工具,Phase 15+ 扩展)

#### 3.7.2 通过 RPE + Q 表 backoff 学行动后果

不是 hardcoded if-then,而是:
- 教学课程提供"情境 → 合适行动"对照样本
- 系统经 Phase 9.2 RPE + Phase 8.4 SDPL Q backoff 学到 Q(packet, action)
- 多次曝光后 Q 收敛 → 自然涌现合适反应

#### 3.7.3 行动课程包格式

```yaml
package_id: "action.desktop_pet.greet"
content:
  - action_id: "action::greet_user"
    description: "用户打开桌宠/长时间不见后再次出现"
    trigger_packet_patterns:
      - source_marker: "PERCEIVED"
        content_sa_includes: ["entity::user", "event::session_start"]
        feeling_sa_includes: ["feeling::affiliation_drive_high"]
    action_payload:
      visual: "wave_animation"
      audio_optional: "greeting_sound"
      text: "{greeting_word},好久不见"
    outcome_examples:
      - {situation: "user_just_opened_app", expected_reward: 0.8}
      - {situation: "user_returned_after_hour", expected_reward: 0.9}
      - {situation: "user_already_greeted", expected_reward: -0.3}  # 重复打招呼负反馈
```

### 3.8 Phase 13.8 — Social Common Sense Curriculum(社交常识)

**目标**:50-100 个社交范式。

#### 3.8.1 礼貌表达

- 何时用"您" vs "你"
- 何时加"请" / "麻烦您" / "不好意思"
- 何时该道歉(打断 / 没听清 / 表错意)
- 何时该感谢

#### 3.8.2 共情回应

复用 Phase 9.6 EMPATHY_RESONANCE marker:
- 看到用户 PAIN marker → 触发 empathy → 选择"理解"类回应
- 看到用户 frustrated → 选择"安慰"类回应
- 看到用户 excited → 选择"分享喜悦"类回应

```yaml
package_id: "social.empathy.user_sad"
content:
  - paradigm_id: "respond_to_user_sadness"
    trigger:
      user_feeling_inferred: "sadness"
      empathy_resonance_active: true
    candidate_responses:
      - "怎么了"  # 询问
      - "我能听你说说吗"  # 邀请倾诉
      - "辛苦了"  # 共情
      - "我陪着你"  # 陪伴
    avoid:
      - "别想了"  # 否定情绪
      - "这有什么"  # 轻视
```

#### 3.8.3 拒绝软化

直接拒绝伤情绪,要软化:
- 不是"我不能" → 而是"这个我可能做不到,但是..."
- 不是"不知道" → 而是"我也不太确定,要不我们一起想想"

### 3.9 Phase 13.9 — Four Scenario Validation Suite(四场景验收套件)

**目标**:端到端验收 + demo 准备。

#### 3.9.1 纯文本对话场景验收

50 个标准对话场景全跑通:
- 基础问候 / 简单问答 / 描述事物 / 表达情绪 / ...
- 测试维度:流畅度 / 相关性 / 情绪适配 / 一致性

#### 3.9.2 桌宠多模态场景验收

30 个交互情境:
- 用户长时间不来 → 桌宠主动呼唤
- 用户摸头 → 桌宠表达喜悦
- 用户说"看那个" + 指 → 桌宠跟随视线
- 用户哭 → 桌宠表达关心
- ...

#### 3.9.3 具身预演验收(虚拟环境)

20 个简单动作:
- 找路 / 拿东西 / 指物 / 跟随 / ...

#### 3.9.4 Agent 工具使用验收

20 个简单工具调用:
- 提醒事项 / 简单搜索 / 草稿邮件 / ...

#### 3.9.5 中文展示页 + Demo 视频

- 4 个场景各录 3-5 分钟 demo
- 中文展示页含每场景能力清单 + 学习曲线 + audit trail
- 开源前的最终包装

---

## 第 4 章 用户体验设计(关键 — 一鸣惊人的关键)

### 4.1 第一次打开体验(前 3 分钟)

**Goal**: 让用户在 30 秒内"哇",3 分钟内确定"这值得继续玩"。

#### 4.1.1 启动序列

```
用户首次启动
  ↓
0-3 秒:Web 工作台加载,显示"嗨,我刚醒来"+ 简短动画
  ↓
3-10 秒:展示"我已经学过这些"  
  - "我认识 3500 个汉字 / 5000 个词 / 800 个常见对象"
  - "我有点像 5-8 岁的小学生,会说话会想"
  - 进度条:展示已掌握课程包(让用户看到丰富度)
  ↓
10-30 秒:首句对话
  - 系统主动:"你好,你叫什么名字" (entity_user_sa 初始化)
  - 等待用户回应
  ↓
30 秒-3 分钟:自然对话
  - 用户问什么都能回应(因为 5000 词足够)
  - Web 工作台同步展示内心(ledger / feelings / 焦点对象)
  ↓
3-10 分钟:用户开始"教"
  - 用户教新词 / 纠正错误 / 表达情绪
  - 系统 visible 学习(audit trail 显示新 vocab 加入)
  ↓
10+ 分钟:养成开始
  - 系统记住用户偏好
  - 跨天还记得("昨天你说...")
```

### 4.2 Web 工作台展示设计

#### 4.2.1 主对话区(中)

- 多 tick 逐字气泡动画(每 tick 渲染一字)
- 用户消息气泡(可点击👍/👎/教学按钮)
- 系统回复气泡(显示风格 tier 颜色提示)
- **关键**:显示系统**正在想**的状态(而不是 LLM 黑箱式瞬间出结果)

#### 4.2.2 Mind 区(右)

5 个子面板:
- **想法云**:状态池 top 20 SA,字号 ∝ R+A
- **内心画面**(Phase 8.6+):状态池视觉 SA 叠加渲染
- **当前焦点**:视/音频/思维三类注意力
- **感受**:reality_sense / imagination_sense / empathy / 等(可视化为雷达图)
- **驱力**:5 类 drive 的实时压力(柱状图)

#### 4.2.3 Audit 区(下/抽屉)

- 逐 tick trace 时间轴(可拖动)
- 当前 packet 详情(content / source / feeling)
- 学习事件(新 vocab spawn / Q 更新 / 反例撤销)
- 教学历史(每个 vocab 知道从哪学的)

#### 4.2.4 Ledger 饼图(右上小窗)

- 当前焦点 SA 的 attention_gain 8 维账本
- 实时展示"它现在的注意力来自哪"
- 用户看到 "external 70% + imagination 20% + replay 10%" → 一目了然

#### 4.2.5 Replay 控制(顶部)

- 速度:0.25x / 1x / 4x / 16x
- 单步前进/后退
- 跳到关键 tick(惊涌现 / commit / 学习事件)
- **这是用户能"重看它思考过程"的关键 — LLM 给不了**

### 4.3 用户教学接口

#### 4.3.1 即时反馈按钮

- 👍 / 👎(每条系统回复)
- 经 reward handler → RPE → 系统学到此 packet 下该 action 好坏

#### 4.3.2 显式纠错

- "其实是 X"(改正最后一句)
- 系统经 CORRECTION marker + 自然纠错(Phase 8.9)学到

#### 4.3.3 教学新词

- 用户:"X 是 Y"(陈述)
- 系统经 HEARSAY proposition + trust_promoted(用户被自动设为高信任)→ 学到
- audit trail 显示"用户教了我 X"

#### 4.3.4 课程包加载

- 用户可上传自定义课程包(yaml)
- 商店式课程市场(未来):方言包 / 专业知识 / 角色设定

### 4.4 跨场景一致性体验

无论用户在哪个场景接入,系统人格一致:
- entity::self SA 是全局的
- 用户身份(entity_user_sa)跨场景识别
- 学到的偏好跨场景生效
- "桌宠模式下教的东西,文本对话模式也记得"

### 4.5 失败场景处理(用户最容易失去耐心的点)

**场景 A**:用户问超纲问题(系统不会)
- ❌ 不要:"抱歉我不知道"(冷冰冰)
- ✅ 应该:"这个我还不太懂,你能给我讲讲吗"(显示求知欲 + 教学接口)
- 经 Phase 9.1 drive::epistemic + KNOWLEDGE_GAP marker emerge

**场景 B**:用户测试边界(故意问怪问题)
- ❌ 不要:报错或重复输出
- ✅ 应该:显示惊讶 / 困惑 feeling,询问澄清
- 经 §10.2 incongruity feeling 自然涌现

**场景 C**:用户长时间冷场(看系统会不会"死")
- ❌ 不要:静默无反应
- ✅ 应该:Phase 9.1 drive 积累 → 主动发起话题
- "你在想什么呢" / "我刚才在想..."

**场景 D**:用户打错字 / 输入混乱
- ❌ 不要:理解失败报错
- ✅ 应该:猜测意图 + 用 incongruity feeling 表达"有点没懂"
- "你是说...吗"(澄清询问)

---

## 第 5 章 课程内容生成策略(工程量管理)

### 5.1 课程内容的来源

| 内容类型 | 主来源 | 辅来源 | 审校 |
|---|---|---|---|
| 汉字 | GB2312 + 现代汉语词频表 | 字典数据 | 必须人工审校 |
| 偏旁部首 | 康熙 214 部首 + 简化字偏旁 | 字源学 | 必须人工审校 |
| 笔画 | 国标 | 字典 | 抽查审校 |
| 词汇 | 现代汉语词频表 + 北京语料库 | 字典 | 抽查审校 |
| 短语 | 北大语料库 + 教科书 | LLM 辅助生成 | 必须人工审校 |
| 视觉对象 | ImageNet / Open Images(图像) | 自采 | **必须人工审校** |
| 音频范式 | Freesound + 公开数据集 | 自采 | 必须人工审校 |
| 表达范式 | 中文母语者直觉 + 语料库 | LLM 辅助生成 | 必须人工审校 |
| 行动反应 | 4 场景设计师 | LLM 辅助生成 | 必须人工审校 |
| 社交常识 | 中文文化典型 + 礼仪手册 | LLM 辅助生成 | 必须人工审校 |

### 5.2 LLM 辅助生成的关键限制

**LLM 永远不进 runtime**,只在课程设计时辅助生成草稿:

```
设计时(允许)                 runtime(禁止)
LLM 生成 yaml 草稿              ❌
  ↓
人工审校 + 修订                 ❌
  ↓
commit 到 config/curriculum/    ✅(只 yaml,不调 LLM)
  ↓
Phase 13 课程跑器加载            ✅
  ↓
SDPL 教学路径学习                ✅
```

### 5.3 课程包审校工作流

每个课程包 commit 前必经:
1. **schema 验证**(自动) — 格式正确
2. **完整性验证**(自动) — 必填字段 / 反例数量 / 视觉张数
3. **跨课程一致性验证**(自动) — 与已有课程不冲突
4. **人工抽查审校**(每 100 条抽 10 条人工看) — 内容质量
5. **AP 试教验证**(自动) — 一台 dev AP 跑一遍,通过 validation 测试

### 5.4 分批迭代(关键 — 不要等全做完才发布)

| 批次 | 时间 | 内容 | 发布版本 |
|---|---|---|---|
| 批 1 | 1 周 | 500 字 + 1500 词 + 50 范式 + 200 视觉 + 20 行动 | **alpha**(内测) |
| 批 2 | 再 1 周 | 扩到 2000 字 + 3500 词 + 150 范式 + 500 视觉 + 80 行动 | **beta**(小范围公测) |
| 批 3 | 再 2 周 | 扩到 3500 字 + 5500 词 + 250 范式 + 800 视觉 + 150 行动 | **rc**(开源候选) |
| 批 4 | 再 1 周 | 全量到 3500-5000 字 + 7000 词 + 300 范式 + 1200 视觉 + 200 行动 | **v1.0** 正式开源 |

**alpha 出来时就有内容可玩**,不需要等所有 done。

---

## 第 6 章 与 14 轮设计审阅 + 用户哲学的对齐

### 6.1 v14 红线全部继承

Phase 13 严格遵守:
- ❌ 不许字面量(全部课程内容 + 阈值进 yaml)
- ❌ 不许 keyword 路由(教学经 SDPL,不 hardcode)
- ❌ 不许学生侧 LLM(LLM 只设计时辅助)
- ❌ 不许 audit_db 进 cognitive 路径
- ❌ 不许新 SA family(全部走 VocabSA / EntitySA / 等既有 type)

### 6.2 SDPL 哲学完整保留

教学 vocab **绝不是 hardcoded** :
- 带 source_entity_id(可追溯)
- 经 trust_promoted gate(可降级)
- 经 RPE + 反例撤销(可修正)
- 在 packet_key 中 source 维度仍能区分(用户实际经验 vs 教学陈述)

### 6.3 用户哲学 3 轮升级全部生效

- **拟人 > 准确**:教学允许"不完美",经实际交互校正
- **想象可学**:教学的视觉抽象进入 IMAGINED packet 路径
- **源可分**:教师陈述 = HEARSAY,与亲历 PERCEIVED 自然分化

### 6.4 14 轮审阅纪律延续

Phase 13 每子阶段必须:
- 设计稿(本稿是总图,子稿可补)
- 审查完善(对抗审阅每个课程包)
- 通过落地(模块 + 测试 + 报告)
- 严谨验收测试(每子 phase 至少 4 个 gate)
- 最终汇总报告(总报告 + 中文展示页)

---

## 第 7 章 不确定问题(需要你拍板)

### 7.1 视觉图像版权 / 来源

**选项 A**:全用公开数据集(ImageNet / COCO / Open Images)
- 优点:零成本 / 法律安全
- 缺点:有些类别图像质量/数量不足

**选项 B**:公开数据集 + 自采 + 用户贡献
- 优点:更全 / 更新
- 缺点:版权审查成本高

**选项 C**:公开数据集 + 合成图像辅助(用 SD 生成补缺)
- 优点:成本低 / 数量足
- 缺点:可能引入伪特征(违反"真实图像优先"原则)

**我推荐**:A 为主 + B 选补 + 严格不用 C。
**问题**:你怎么看?有没有你能提供的资源(比如自有图库)?

### 7.2 音频版权

类似问题。
**我推荐**:Freesound (CC0 / CC-BY) + 自录。

### 7.3 课程包社区贡献接口

**选项 A**:发布时就提供贡献接口(CONTRIBUTING.md + PR review)
**选项 B**:正式版后再开放
**我推荐**:从 alpha 就开放(小社区 → 大社区,养社区)。

### 7.4 商业化路径预留

**选项 A**:全免费(纯开源)
**选项 B**:基础课程包免费 + 专业课程包收费(方言 / 角色设定 / 专业知识)
**选项 C**:框架免费 + SaaS 服务收费(托管 / 定制 / 高级 audit)

**问题**:你的商业化偏好?这影响课程包 yaml 格式设计(要不要预留 license 字段)。

### 7.5 4 个场景的优先级

我倾向:**纯文本对话 = 桌宠多模态 > Agent 工具 > 具身**
**问题**:你的优先级?(影响 Phase 13.7 行动库分配)

### 7.6 教学课程的"声音" / "人设"

教学内容用什么语气?
- 中性书面("猫是哺乳动物")
- 亲切口语("你看,这就是小猫咪")
- 故事化("从前有只小猫...")

不同语气会影响 AP 学到的表达风格。
**问题**:你想要什么风格?

### 7.7 早期 vs 后期内容

是否需要"早期内容"(给完全萌新用户) vs "后期内容"(给老用户):
- 早期:基础识字 / 简单对话 / 显式教学指引
- 后期:复杂叙事 / 抽象概念 / 用户主导学习
- 系统通过 entity_user_sa 累积时长判断

**我推荐**:做(分龄分层是教育产品标配)。
**问题**:你同意吗?

---

## 第 8 章 时间估算(基于 Codex 20分钟/phase 节奏)

| 阶段 | Codex 工程量 | 内容工程量 | 总耗时 |
|---|---|---|---|
| Phase 13.1 substrate | 1-2 小时 | - | 半天 |
| Phase 13.2 字课程架构 | 1 小时 | **3-5 天**(500 字内容) | 1 周(批 1) |
| Phase 13.3 词课程架构 | 1 小时 | 3-5 天 | 与上同时 |
| Phase 13.4 视觉课程架构 | 1 小时 | **1-2 周**(图像采集+审校) | 2 周(关键瓶颈) |
| Phase 13.5 音频课程架构 | 1 小时 | 3-5 天 | 1 周 |
| Phase 13.6 表达范式架构 | 1 小时 | 3-5 天 | 1 周 |
| Phase 13.7 行动课程架构 | 1-2 小时 | 1 周 | 1 周 |
| Phase 13.8 社交课程架构 | 1 小时 | 3-5 天 | 1 周 |
| Phase 13.9 四场景验收 | 半天 | 3-5 天 | 1 周 |
| **总计** | **~10 小时 Codex** | **~3-4 周内容** | **3-4 周到正式版** |
| 分批 alpha | - | - | **第 1 周末** |

**关键瓶颈是视觉常识图像采集** — 这是无法压缩的部分,需要真人做。

---

## 第 9 章 总判断 — Phase 13 能否一鸣惊人

### 9.1 数学+架构可行性:**完全可行**

v14 SDPL 路径 + 既有 Phase 8-11 机制 + 课程包 yaml 化,所有需要的钩子都准备好了。Phase 13 不引入新公式,只是充分利用已有能力。

### 9.2 工程可行性:**关键看内容质量**

- 架构层:Codex 几小时完成
- 内容层:**~3-4 周高质量内容采集 + 审校**
- 测试层:每子 phase 验收 gate 严格

### 9.3 一鸣惊人可能性:**高,但取决于 3 件事**

| 关键 | 概率 |
|---|---|
| **课程质量**(对照设计严谨度) | 80% — Phase 8.8 黄苹果验过,可迁移 |
| **Web 工作台可视化**(让用户能看到内心) | 70% — Phase 8.11 基础有,要 polish |
| **4 场景 demo 拿捏**(精打磨而非贪多) | 60% — 取决于 demo 视频质量 |

**综合概率:60-70% 一鸣惊人**,这在开源产品中已经是非常高的预期。

### 9.4 风险点

| 风险 | 缓解 |
|---|---|
| 课程包冲突(教学碎片) | 跨课程一致性 gate 自动检测 |
| 用户教错(恶意/错误) | 反例撤销 + 信任度演化 |
| 视觉图像质量参差 | 人工审校 + 抽查 + 数据集白名单 |
| 性能瓶颈(5000 vocab) | Phase 8.15 cold_index 双层已规划 |
| 用户期望过高(以为 LLM) | 文档明确边界 + demo 显示"现学" |

### 9.5 如果做得好,能超出"幼儿园-小学生"水平吗?

可能。**因为 AP 有 LLM 没有的两个东西**:
- 真实持续记忆(跨天跨周)
- 真实学习能力(用户教 = 真改变)

理论上,**长期使用的 AP 会比初始版本聪明很多**(用户教多了 → 用户专属知识库 → 比预设课程包更适合该用户)。
这反过来成为 alpha → beta → 正式版的 "用户积累 = 系统价值积累" 飞轮。

---

## 第 10 章 给 Codex 的最终指令(Phase 13)

1. **本稿(Phase 13 v1)+ v14 UNIFIED + v14.1 ERRATA + Phase 8-12 成果 = 实施依据**
2. **Phase 13.1 substrate 必须先做**(课程系统基础)
3. **每子 phase 严格 5 段闭环**(设计/审查/落地/验收/报告)
4. **课程内容分批迭代**,不要等全做完才发布
5. **图像 + 音频版权严格审查**(从公开数据集 + 自采,绝不偷)
6. **trust_promoted gate 必须实施**(教学加速但不破坏可证伪)
7. **跨课程一致性 gate 必须实施**(防教学碎片化)
8. **Web 工作台同步升级**(Phase 12 完成后,Phase 13 期间持续 polish)
9. **每子 phase 中文展示页**(到 Phase 13.9 时合并成开源材料)
10. **任何"超出本稿范围"的设计提议必须先停下问 Claude**(继承 14 轮审阅纪律)

---

## 附录 A:与 v14 UNIFIED + 4 应用场景的最终对接

到 Phase 13.9 完成 + Phase 12 配套 demo 基础设施 + Phase 14 polish 完成,**系统具备**:

- v14 设计的全部架构(Phase 8-11)
- Phase 9 主动心智深度(driver/RPE/共情/etc.)
- Phase 10 5-8 岁层级心智(narrative/causal/ToM/etc.)
- Phase 11 8-12 岁元认知(meta/abstract/goal/deliberative/self)
- Phase 13 小学水平知识浸泡(3500 字/7000 词/800 视觉/300 范式/200 行动)
- Phase 12+ Web 工作台 polish + 4 场景 demo

**预期开源效果**:
- 普通用户 30 秒内"哇"
- 3 分钟确定"值得继续玩"
- 10 分钟开始教它新东西
- 第二天还记得用户

**这是 14 轮设计审阅 + 用户 3 轮哲学深化 + 工程实施严谨纪律的终极产出**。

---

— 接手线程,2026-06-18

附:本设计稿要点已与 Phase 8-10 实测能力对齐,Phase 11 完成后立即可启动 Phase 12 → Phase 13 → Phase 14。
