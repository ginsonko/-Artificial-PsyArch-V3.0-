# APV3.0 拟人多模态底座 — 完整数学模型设计稿 v1

日期: 2026-06-17
作者: 接手线程
状态: **完整数学模型 + 工程实施步骤,经用户三个关键口味决定(逻辑 tick / 三模态同步落地 / 多通道主驱黄苹果反驱)校准。**

---

## 0. 顶层设计哲学(必读,所有后续设计的判据)

### 0.1 用户三个关键决定

| 维度 | 决定 |
|---|---|
| tick 机制 | **逻辑 tick** — 软件内部推进,可回放,可加速,不绑真实墙钟 |
| 模态优先级 | **三模态同步落地** — 文本/视觉/听觉一起做 |
| **自主词汇发现** | **用户最重要的哲学升级:不是文本专属,而是"任意 SA 一等公民可组合成固化链条"的通用机制。词汇=固化组合=链条** |
| 黄苹果路径 | **多通道主驱,黄苹果反驱设计** — 多通道是底层一等机制,黄苹果只是验收场景 |

### 0.2 用户提出的核心哲学(直接引述)

> "理论上应该可以'自主发现'新的'词汇',比如三顾的例子中的'庐',就可以说它根据共现抽象来的新的词汇 sa 对象。"

> "这个'词汇'也不仅是词,而是类似于一种固化的'组合'或者'链条'。"

> "这不是一个专属于文本感受器的机制,而应该是以任意 SA 一等公民为基础的通用机制,包括多模态、认知感受,甚至行动节点,都可以组合和构成更高的多模态'词汇'的一部分。"

### 0.3 我对这个哲学升级的翻译

**"词汇"= 任意 SA 序列(或任意 SA 集合)经过共现统计稳定形成的固化对象,本身也是一个 SA**。这是个**递归定义**:
- 一级词汇:单个原子 SA(文本字、像素 patch、音频 token、动作 token)
- 二级词汇:多个一级 SA 高频共现/共序 → 固化为一个新 SA(如"庐"、"苹果"、"颜色::红")
- 三级及以上:递归向上

所有模态、认知感受、行动节点全部**走同一套词汇固化机制**——这就是后面 §3 的"通用组合词汇机制"。这取代了传统 NLP 的 tokenization,也取代了视觉的 feature engineering。

### 0.4 红线(所有后续设计必守)

- **❌ 不许把"词汇发现"做成文本专用**——任何分支 `if modality == "text"` 直接 fail。
- **❌ 不许预设词汇库**——所有词汇都是后天学到的(seed phrase 库是表达层风格约束,不是词汇层)。
- **❌ 不许跨模态融合用"加法"**——每个通道独立打分独立召回,融合发生在范式槽层。
- **❌ 不许把视觉/听觉做成"调用现有 lib"**——必须有自己的数学模型,且各通道可独立向量化、可独立召回。
- **❌ 不许真时间钩 0.1s 实墙钟**——逻辑 tick,可加速可回放。

---

## 1. 逻辑 tick runtime 完整数学模型

### 1.1 核心定义

**逻辑 tick** = 系统内部"思考节拍",由感受器队列驱动 + 主动 step 推进。不绑墙钟,但默认 1 tick 名义对应 0.1s。

```
tick(t) → tick(t+1):
    sources_input(t)       # 来自各感受器队列的本 tick 输入(可空)
    state_pool(t)         # 状态池能量演化(R/V/P/A/F)
    recall_chain(t)        # Bn → Cn → 范式召回
    draft_action(t)        # 草稿编辑动作(type/reread/replace/commit)
    feedback(t)            # 反馈回流
```

### 1.2 idle tick 能量动力学

**关键问题**:空 tick 时系统应该怎样"无聊地等待"?

**v3.0 §2.1 已有的能量演化律(沿用)**:
```
R_i(t) = ρ_R · R_i(t-1) + Inj_i^ext(t) + Inj_i^fb(t)
V_i(t) = ρ_V · V_i(t-1) + Π_i(t)
A_i(t) = ρ_A · A_i(t-1) + G_i(t)
F_i(t) = ρ_F · F_i(t-1) + Φ_i(t)
P_i(t) = R_i(t) - V_i(t)
```

**idle tick 的特殊性**:`Inj_i^ext = 0`,所有 SA 的 R 单调衰减。这正确——idle 时短期记忆**真的应该淡化**。

**但要解决用户提的"几秒没回复就忘了上下文"问题**:

新增**长时短记忆双层结构**:
```
short_term_R(t) = ρ_R^short · short_term_R(t-1) + Inj^ext   # ρ_R^short ≈ 0.95,几秒衰减明显
long_term_R(t) = ρ_R^long · long_term_R(t-1) + Inj^promote  # ρ_R^long ≈ 0.999,几十 tick 还在

# 关键:当 short_term_R 在 N 个 tick 内被多次激活,触发 promotion 到 long_term
if short_term_R_activation_count_in_window(N) >= θ_promote:
    long_term_R += promote_amount * current_short_term_R
```

这相当于**人类的瞬时记忆 → 短时工作记忆 → 长时记忆**的三级模型在 AP 里的最小数学实现。

### 1.3 输入到来的"惊"机制(已有 §5 收束 pass 真正接通)

感受器输入到来时 → 高 R 低 V 的 SA 进池 → 大正认知压 → §7 收束触发。这已经是 v3.0 §5/§7 的设计,但 Phase 8 没真接到 Web 感受器流。

**Phase 8.2 必须做**:把 Web/CLI 入口的输入流真接到 `Inj_i^ext`,让 v3.0 §5 收束 pass 真正运转。

### 1.4 逐字草稿输出的数学约束

用户提的"逐字/逐词输出"在 v2.1 已经设计过(`text_actuator.py` 的 type/reread/replace/commit)。Phase 8 没接是 Codex 偷工。

**约束**:
- 每个 tick **最多执行 1 个草稿动作**(已是 v3.1 §S6 单 emit-per-tick 红线)
- type token 来自 7.7 的 phrase_id → tokens 序列
- 当 `commit_blocked = False` 且 `reply_pressure > θ` 时,触发 commit
- **如果在 K 个 tick 内仍 commit_blocked**,fallback 到 tier-0 诚实表达(不知道)或保持沉默

### 1.5 Web 回放需要的 tick trace

每个 tick 必须暴露的 trace 字段:
```
tick_trace = {
    "t": int,                            # tick 序号
    "inputs": [...],                     # 本 tick 各感受器输入
    "state_pool_top": [...],             # top 20 SA 的 (R,V,P,A,F)
    "recall_focus": str,                 # 慢系统焦点 label
    "draft_action": str,                 # type / reread / replace / commit / noop
    "draft_buffer": str,                 # 草稿缓冲区当前内容
    "reply_pressure": float,
    "commit_blocked": bool,
    "promotions_to_long_term": [...]     # 本 tick 哪些 SA 被晋升到长时记忆
}
```

Web 回放界面遍历这些 trace,**逐 tick 重现内部发生了什么**。这是用户最想要的体验。

---

## 2. 通用 SA 组合词汇固化机制(本设计稿的灵魂)

### 2.1 哲学起点

> "这个'词汇'也不仅是词,而是类似于一种固化的'组合'或者'链条'。"
> "任意 SA 一等公民为基础的通用机制,包括多模态、认知感受、行动节点,都可以组合。"

**形式化**:任何 SA 集合或序列经过共现统计,如果稳定度超过阈值,就**固化为一个新 SA**。这个新 SA 本身也是一等公民,可以继续被组合。

### 2.2 数学定义

设状态池里的 SA 集合为 $S$。对任意子集合或子序列 $\sigma \subseteq S$(或 $\sigma$ 是 $S$ 的一个有序序列),定义:

**共现/共序强度**:
$$
\text{coh}(\sigma) = \frac{f(\sigma)}{\prod_{i} f(\sigma_i) / N}
$$

其中 $f(\sigma)$ = $\sigma$ 整体出现的次数,$f(\sigma_i)$ = 各组件单独出现的次数,$N$ = 总观察数。这是**点对互信息(PMI)的多元推广**。高 coh = "这些 SA 在一起出现的频率远超偶然"。

**稳定性**:
$$
\text{stab}(\sigma, t) = \frac{f(\sigma)}{T_{\text{decay}}(t)}
$$

考虑时间衰减(老观察权重低)。

**固化条件**:当 $\text{coh}(\sigma) > \theta_{\text{coh}}$ AND $\text{stab}(\sigma) > \theta_{\text{stab}}$ AND $f(\sigma) > \theta_{\text{min\_count}}$,**固化为新 SA**:

```
new_sa = SA(
    sa_type = "composed_vocab",
    sa_label = f"vocab::level_{level}::{stable_id()}",
    components = σ,
    components_kind = "set" | "sequence",
    level = max(level(σ_i)) + 1,        # 递归层级
    cumulative_coh = ...,
    persistent_id = stable_id(),         # 沿用 v3.1 B2 持久 id 模式
)
```

固化后这个 SA 进入状态池,**未来可以作为更高层组合的组件**。这就是递归。

### 2.3 跨模态组合

**关键**:$\sigma$ 的组件**不必同模态**。`{vision::contour::shape_3, text::苹果}` 高共现 → 固化为 `vocab::level_2::xx` SA。

这个固化 SA **就是"苹果"概念的真正涌现**——它既不是文本"苹果"也不是视觉"苹果轮廓",而是**两者的固化绑定**。

### 2.4 与 v2.1 范式通道的关系

v2.1 §3 的范式通道做的是**槽位结构发现**(哪些位置固定哪些可替换)。本机制做的是**组合实体发现**(哪些 SA 应该被打包成一个新 SA)。

两者关系:
- 词汇固化 = 发现"积木块"
- 范式通道 = 发现"积木如何拼"

词汇固化先于范式通道——必须先有"庐"这个新 SA,范式通道才能发现"三顾 X 庐"的槽位结构。

### 2.5 工程实现要点

新增 `ComposedVocabStore` 模块:
- 共现 / 共序统计窗口(用 v3.1 §B3 同模式 SQLite)
- 固化判定 + 创建新 SA(走 v3.1 §B2 persistent_id 模式)
- 退役机制:固化 SA 长期不被复用 → 衰减 → 驱逐(配 §B2 的 retire 钩子)
- 红线扫描:`if vocab.modality == ...` 必须 0 命中(全模态平权)

---

## 3. 视觉感受器多通道数学模型

### 3.1 总原则

每个视觉感知对象(percept_proto)在**多个通道上独立向量化**,每通道独立可召回。**不允许把多通道压成一个总向量**——那会失去"轮廓像苹果颜色像香蕉"的能力。

### 3.2 7 个独立通道

每个通道独立维护向量空间 + 独立 OnlineEmbeddingStore-style 共现学习:

| 通道 | 数学定义 | 维度 | 拟人意义 |
|---|---|---|---|
| **C1 轮廓** | Fourier 描述子(沿轮廓采样的 N 点 → FFT 前 K 个谐波) | 32 | 形状,旋转/平移/缩放不变 |
| **C2 颜色** | HSV 加权直方图 + 主色聚类中心 | 16 | 主要颜色基调 |
| **C3 大小** | log(面积 / 视场总面积) + 长宽比 + 紧凑度 | 4 | 物理尺寸感 |
| **C4 空间方位** | 中心点 (x,y) / 视场,极坐标 (r,θ),距视焦距离 | 6 | 在哪里 |
| **C5 运动趋势** | 相邻 tick 同 id 轮廓中心位移向量 (dx,dy,d²x,d²y) | 4 | 动还是静,加速还是匀速 |
| **C6 纹理** | LBP / Gabor 滤波器响应 | 24 | 表面质感(粗糙/光滑) |
| **C7 持续性** | 在最近 N tick 中出现频率 + 平均持续时间 | 4 | 是否稳定存在 |

总维度:32+16+4+6+4+24+4 = 90 维 per percept,**但分 7 个独立子空间**。

### 3.3 跨 tick 轮廓追踪(关键)

**问题**:同一个物体在不同 tick 怎么知道是"同一个"?

**解法**:跨 tick 匹配 = 综合各通道相似度的最近邻:

$$
\text{match}(p_t^i, p_{t-1}^j) = \sum_k w_k \cdot \text{cos\_sim}(\text{ch}_k(p_t^i), \text{ch}_k(p_{t-1}^j))
$$

`w_k` 是 tuner-owned,初值偏 C1+C2+C4(轮廓+颜色+位置最稳定)。匹配阈值过则**复用 percept_id**,否则**新建 percept_proto**。

复用 percept_id 时 C5(运动)通道**自动更新**:`dx_t = x_t - x_{t-1}`。

### 3.4 视焦点作为可学习行动

**视焦点 SA** `attention::vision::focus`:
- 状态:`(focus_x, focus_y, focus_radius) ∈ R³`
- 影响:在 focus_radius 内的 percept 的 R_inj 系数高(乘子 > 1),外的低(乘子 < 1)
- 是一等**行动 SA**,可以被学习触发(像 v3.1 的 attention focus action)

更新律:
$$
R_{\text{inj}}(p) = R_{\text{base}}(p) \cdot g_{\text{focus}}(\text{dist}(p, \text{focus}))
$$
$$
g_{\text{focus}}(d) = 1 + \alpha \cdot \exp(-d^2 / (2 \cdot \text{focus\_radius}^2)) - \beta
$$

`α` 是焦点增益,`β` 是焦外抑制,都 tuner-owned。

### 3.5 内心画面可重建

**重建函数**:给定状态池里的 percept SA 集合 + 各自能量,在画布上叠加绘制。

$$
\text{canvas}_{x,y} = \sum_{p \in \text{state\_pool}} \alpha(R_p) \cdot \text{render}(p, x, y)
$$

`α(R)` 是 R-到-不透明度映射,高 R = 高不透明度。`render(p, x, y)` 是把 percept 在画布上绘制的函数,用其 C1 轮廓 + C2 颜色 + C4 位置参数化。

**这是"内心画面 = 状态池能量的 2D 投影"的物理实现**。Web 界面可以直接渲染这个 canvas。

---

## 4. 音频感受器多通道数学模型

### 4.1 6 个独立通道

| 通道 | 数学定义 | 维度 |
|---|---|---|
| **A1 音色** | MFCC 前 13 系数 + delta + delta-delta | 39 |
| **A2 音调** | f0 (基频) + harmonic-to-noise ratio | 4 |
| **A3 节奏** | onset density + 间隔 IOI 直方图 | 16 |
| **A4 响度** | RMS / log-energy + 包络 attack/decay 时间 | 6 |
| **A5 空间方位** | ITD (耳间时差) + ILD (耳间响度差) | 4 |
| **A6 音频含义** | 跨 tick 共现稳定后的"语音对象"嵌入 | 64 (后天学到) |

总维度:39+4+16+6+4+64 = 133 维 per audio_proto。

### 4.2 频段焦点(对应视焦点)

**音频焦段 SA** `attention::audio::band`:
- 状态:`(center_freq, band_width)`
- 在 band 内的音频对象 R_inj 增强
- 是一等行动 SA

### 4.3 跨 tick 连续性

**关键问题**:几秒内一个完整词(如"妈—妈—"中两个"妈")需要被识别为一个对象。

**解法**:`A1 音色`通道的相似度 + `A2 音调`接近 + 时间窗口(N tick 内)→ 同一 audio_proto。

跨 tick 累计的音频内容由 `audio_proto.payload` 累积存储(类似视频里的 frame 序列)。

### 4.4 内心音频可重建

类似视觉:状态池里的 audio_proto 按 R 加权合成。
$$
\text{audio\_signal}(t) = \sum_{a \in \text{state\_pool}} \alpha(R_a) \cdot \text{synthesize}(a, t)
$$

`synthesize(a, t)` 用 audio_proto 的各通道参数重建音频片段。Web 界面可以播放这个合成结果。

---

## 5. 文本感受器多通道数学模型

### 5.1 4 个独立通道

| 通道 | 数学定义 | 维度 |
|---|---|---|
| **T1 字符身份** | one-hot / 嵌入 | 64 |
| **T2 子词组合** | 字 2-gram / 3-gram(用 §2 通用组合机制涌现) | 动态 |
| **T3 文本顺序** | transition_counts(字 → 下一字)+ 位置编码 | 128 |
| **T4 句法位置** | 标点边界 / 段落边界 / 句中位置归一化 | 8 |

### 5.2 自主词汇发现(用户最强调的)

走 §2 的通用组合机制。例:
- 字"庐"在"三顾茅庐"和"三顾臣于草庐之中"中**高 PMI 出现** → 触发固化
- 新建 `vocab::level_1::庐_<hash>` SA
- 这个 SA 进状态池,后续可以参与"三顾→[槽]→庐"这种范式结构发现

### 5.3 跨模态文本词汇

如 §2.3 所述,文本 SA 可以与视觉/听觉 SA 共组合。例:
- 文本"苹果" + 视觉 `contour_shape_3` + 视觉 `color_red` 高共现 → 固化 `vocab::level_2::苹果_<hash>`
- 这是真正的概念绑定

### 5.4 与 7.8 phrase memory 的关系

**关键澄清**:
- 7.8 的 `ExpressionPhraseMemory` 是**表达层**——系统**说**什么短语
- §2 的 `ComposedVocabStore` 是**感知层**——系统**理解到**什么概念

两者不同层:理解层可以涌现"庐"这种词汇 SA,而表达层仍受 120 phrase 约束(风格守恒)。

---

## 6. 黄色苹果泛化的完整数学链路(多通道主驱,反驱验收)

### 6.1 教学阶段

**Step 1**:展示 红色苹果图片 + 同 tick 文本"红色苹果"
- 视觉提取:`percept_1 = {C1: 苹果轮廓, C2: 红色, C3: 中等大小}`
- 文本提取:tokens `["红", "色", "苹", "果"]`
- 经 §2 词汇固化:涌现 `vocab::苹果` SA(绑定 C1 苹果轮廓 + 文本"苹果")
- 涌现 `vocab::红色` SA(绑定 C2 红色 + 文本"红色")
- 涌现范式 `颜色::[槽] 对象::[槽]`(用 v2.1 范式通道)

**Step 2**:展示 黄色香蕉图片 + 同 tick 文本"黄色香蕉"
- 类似涌现 `vocab::香蕉`(C1 香蕉轮廓 + 文本"香蕉")
- 涌现 `vocab::黄色`(C2 黄色 + 文本"黄色")
- 范式 `颜色::[槽] 对象::[槽]` 被进一步强化

### 6.2 泛化测试阶段(从未见过的黄色苹果图片)

**给系统输入:黄色苹果图片**(单图,无文本)

**多通道独立召回**:

C1 轮廓通道:
- 当前 percept 的 C1 向量 ≈ 苹果轮廓
- learned_similarity 召回 → `vocab::苹果` 高分,`vocab::香蕉` 低分

C2 颜色通道:
- 当前 percept 的 C2 向量 ≈ 黄色
- learned_similarity 召回 → `vocab::黄色` 高分,`vocab::红色` 低分

**范式槽竞争**:
- 已学的范式 `颜色::[槽] 对象::[槽]` 被触发
- 颜色槽的候选填充物:`vocab::黄色`(C2 召回得分高)→ 胜出
- 对象槽的候选填充物:`vocab::苹果`(C1 召回得分高)→ 胜出

**输出**:文本表达走 v2.1 范式通道 → "黄色 苹果"

### 6.3 关键数学保证

**为什么这能 work**(不是手挥):

1. **通道独立性**:C1 和 C2 是两个独立向量空间,各自的相似度计算互不干扰
2. **范式槽对类型的限制**:颜色槽只接受 C2 类 SA,对象槽只接受 C1 类 SA(通过 SA 的 `dominant_channel` 字段实现,**不是关键词分支**)
3. **竞争的可解释性**:每个槽的胜出可以**完全溯源**到具体通道的相似度分数

### 6.4 防作弊保证

- 测试图片必须是**真实生成的黄色苹果**(用图像合成工具生成,不是手工构造 percept 字段)
- 系统**之前没见过任何黄色+苹果的同 tick 输入**(从训练日志可证)
- 输出**完全来自范式槽填充链路**,不来自任何 hardcoded 映射

---

## 7. 工程实施步骤(给 Codex 看,分 5 个 Phase)

### Phase 8.2 — 逻辑 tick runtime + 真感受器输入流

**核心模块**:
- `core/runtime/logical_tick_loop.py`:tick 主循环 + 短时/长时记忆双层
- `sensors/text/text_sensor.py`:接 Web 入口,产 SA 流
- `sensors/vision/stub_sensor.py`:暂留 stub,接口预留
- `sensors/audio/stub_sensor.py`:同上
- `core/short_term_memory/promotion_layer.py`:短→长记忆晋升

**验收**:
- 5 分钟空 tick + 偶尔输入,系统不忘记上下文
- Web 能回放每个 tick 的 trace
- 逐字草稿输出(每 tick 一个 token)
- 全量 7.0-7.11 测试通过

### Phase 8.3 — 通用 SA 组合词汇机制(§2)

**核心模块**:
- `runtime/composed_vocab_store.py`:共现/共序统计 + 固化判定 + SA 创建
- 配 SQLite parity(沿 v3.1 §B3)

**验收**:
- 文本场景:教过"三顾茅庐"和"三顾臣于草庐之中"50 次后,"庐"被固化成 SA
- 跨模态:文本"苹果" + 任意 vision_proto 共现 30 次后,固化 `vocab::苹果`
- 红线:扫 `if vocab.modality == ...` 必须 0 命中

### Phase 8.4 — 视觉感受器多通道(§3)

**核心模块**:
- `sensors/vision/contour_channel.py`(C1)
- `sensors/vision/color_channel.py`(C2)
- `sensors/vision/spatial_channel.py`(C4)
- `sensors/vision/motion_channel.py`(C5)
- 其余 C3/C6/C7 占位实现
- `sensors/vision/attention_focus.py`:视焦点行动 SA
- `runtime/inner_canvas_renderer.py`:内心画面重建

**验收**:
- 单色块图片 → 提取出对应 percept,各通道向量正确
- 同物体在画布上移动 → 跨 tick 复用同 percept_id,C5 通道有非零运动向量
- 内心画面可在 Web 上渲染显示

### Phase 8.5 — 音频感受器多通道(§4)

**核心模块**:类比 §8.4 的 audio 版本

**验收**:
- 单频正弦波 → 提取 A2 音调,持续 N tick 仍是同 audio_proto
- 内心音频可在 Web 上播放

### Phase 8.6 — 黄色苹果泛化端到端验收(§6)

**关键测试**:
- 教学:红色苹果图 + 文本 30 次,黄色香蕉图 + 文本 30 次
- 测试:输入从未见过的黄色苹果图(单独,无文本)
- 断言:输出 = "黄色 苹果"(顺序可能不固定,但 token 集合必须是这两个)
- **关键诚实门**:如果失败,**不许调通道权重让它过**——这暴露真问题,要找根因

---

## 8. Phase 8.2 之前还要做的两件 immediate 工作

### 8.0 — 测试探针清理(Codex 已完成)
### 8.1 — Web 工作台(Codex 已完成,但还是单 turn,不是 tick loop)

### **8.1.5 — 修复 Codex 自己提的两个体验问题**

(我同意 Codex 自己列的 8.2-8.4,但顺序要调:**先做 tick runtime,再做纠错教学**,因为纠错教学必须建立在 tick runtime 之上)

修正顺序:
1. **Phase 8.2(本设计稿) — 逻辑 tick runtime + 真感受器输入流**
2. **Phase 8.3 — 通用 SA 组合词汇机制**
3. **Phase 8.4 — Codex 的纠错教学行动范式**(在 tick runtime 上做)
4. **Phase 8.5 — 视觉感受器多通道**
5. **Phase 8.6 — 音频感受器多通道**
6. **Phase 8.7 — 黄色苹果泛化端到端验收**
7. **Phase 8.8 — Web 工作台升级:内心画面 / 内心音频 / 想法云 / 多通道审计折线图**

---

## 9. Phase 8.8 Web 工作台升级清单(给 Codex 实施时直接照做)

用户提的"美观、方便的前端对话接口"具体落点:

### 9.1 主对话区(替换现有简陋区)
- 多 tick 逐字气泡动画(每 tick 渲染一字)
- 用户消息气泡(点击可标记奖励/惩罚)
- 系统回复气泡(显示 commit_text + 风格 tier 颜色提示)

### 9.2 内心画面面板(Phase 8.4 之后)
- Canvas 渲染状态池里的视觉 SA 叠加
- 高 R 对象不透明度高
- 视焦点高亮显示

### 9.3 内心音频面板(Phase 8.5 之后)
- 频谱图显示当前状态池音频 SA 合成结果
- 音频焦段高亮

### 9.4 想法云
- 状态池 top 20 SA 的 label,字体大小 ∝ R+A
- 颜色编码:文本/视觉/听觉/认知感受/行动 各不同色

### 9.5 行动审计
- 当前 tick 的 draft action 类型(type/reread/replace/commit)
- 草稿缓冲区当前内容
- candidate phrase 列表 + 得分

### 9.6 多通道折线图(实时)
- reply_pressure 折线
- candidate count 折线
- draft length 折线
- commit_readiness 折线
- 各通道独立词汇固化数折线
- 短时 → 长时记忆晋升次数折线

### 9.7 tick 回放控制
- 回放速度:0.25x / 1x / 4x / 16x
- 单步前进/后退
- 跳到关键 tick(惊涌现 / commit / 学习事件)

---

## 10. 给 Codex 的总指令格式

完成本设计稿后,Codex 应该:

1. 读完本文档
2. 按 §7 顺序逐 Phase 实施
3. **每个 Phase 走完整 5 段闭环**(设计→审查→落地→验收→报告)
4. 每 Phase 完成后冷保存 + 出 trace 给我评估
5. **任何"看起来通过但不该通过"的情况立即停下问我**

---

— 接手线程,2026-06-17
