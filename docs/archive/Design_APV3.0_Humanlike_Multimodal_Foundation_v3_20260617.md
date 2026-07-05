# APV3.0 拟人多模态底座 — 完整设计稿 v3(立意最高图景)

日期: 2026-06-17
作者: 接手线程
状态: **完整 v3 设计稿。融合 APV2 P1-J 已验证机制 + SNS 桌宠产品壳 + APV2.1 AP-Core 干净模块 + 用户 6 个哲学升级 + 3 个推论拟人机制。这是"理想图景"——能想到的拟人效果全列出,再看怎么落地。**
前身:
- v1: `Design_APV3.0_Humanlike_Multimodal_Foundation_v1_20260617.md`(9 blocker 待修)
- v2: `Design_APV3.0_Humanlike_Multimodal_Foundation_v2_20260617.md`(8 blocker 修后 + 用户 3 哲学升级)
- **v3(本稿)**: v2 基础 + APV2/SNS 已验证经验整合 + 6 + 3 = 9 个新拟人机制完整数学化

---

## 0. 顶层设计哲学(读懂这章再读其他)

### 0.1 v3 相对 v2 的三个根本提升

| 维度 | v2 | v3 |
|---|---|---|
| **数据来源** | 凭空设计 | **整合 APV2 P1-J 系列已实测验证的 11 条经验**(J-2 到 J-22)+ SNS 桌宠产品契约(dual-bubble / focus overlay / bounded tick loop)+ APV2.1 AP-Core 干净模块 |
| **拟人范围** | 5 个主要机制 | **9 个机制**(用户 6 个 + 我推论 3 个)。覆盖看/听/注意力过滤/视焦点/惊/想象/合理感/漫游/似曾相识/多模态联动 |
| **复用 vs 重写边界** | 模糊 | **明确**:APV2 已验证组件**按接口复用**,只做必要重命名;v2 新增数学模型(白箱审计库/场景化 tick/通用词汇)是真正的新工作 |

### 0.2 用户 6 个核心哲学升级(本稿全部数学化)

| # | 用户语 | 设计落点 |
|---|---|---|
| U1 | "持续稳定输入 → 注意力本能过滤,听不到风扇声" | §11 习惯化数学模型,基于 v3.0 能量动力学的自然推论 |
| U2 | "主动注意力可以重新感知已习惯化的对象" | §11.5 attention focus action 复活习惯化 SA |
| U3 | "合理感强(预测准)的事件不抢注意力,睡觉时风扇声不吵醒;少见声音吵醒" | §12 合理感门控公式 grasp × salience |
| U4 | "视焦点 + 焦点处高保真采样 + 内心画面实时显示焦点位置" | §13 视焦点 + 变分辨率 + 实时可视化(继承 APV2 P1-J-5/J-6) |
| U5 | "意外/违和驱动焦点移动,本能但可被后天对抗" | §14 2D 视野 P 场 + ActionParameterMemory 学习覆盖本能 |
| U6 | "音频频段焦点同构(1D 版视焦点)" | §13.5 频段焦点完整数学(APV2 没完整做,v3 补) |

### 0.3 我推论出的 3 个额外拟人机制(v3 新增)

| # | 机制 | 拟人现象 | 数学落点 |
|---|---|---|---|
| **E1** | **多模态焦点联动** | 听某人讲话时眼睛本能看向那人;看某物时听觉过滤增强 | §15.1 跨模态焦点能量耦合 |
| **E2** | **似曾相识感受** | 场景熟悉但细节不同 → "有点眼熟但说不上来" | §15.2 多候选高熵 → 涌现 `feeling::deja_vu` |
| **E3** | **注意力惯性 / 漫游** | idle 时眼神/思维漫游,不死钉一处 | §15.3 无外源时 attention_gain 自然漂移 |

### 0.4 总红线(必守)

继承 v2 §0.4 全部,加 SNS 产品壳红线:

- **❌ AP-native vs Fairy/LLM 言说必须 dual-bubble**:绝不合并气泡,LLM 不写最终答,只判断/给偏置/做教学规划
- **❌ tick 无限后台跑**:必须 `max_ticks` + 主动 sleep + 外源唤醒(继承 SNS J-J-J 经验)
- **❌ 桌面真实控制必须用户当场确认**:对应 SNS 红线
- **❌ 不许 raw asset replay** 做内心音频/画面:必须从状态池能量合成
- **❌ 不许把 GL/Fairy/产品壳能力当作 AP-Core 能力**

---

## 1-10. 沿用 v2 大体结构(§1-10 含逻辑 tick / 通用词汇 / 视觉 7 通道 / 音频 6 通道 / 文本 / 黄苹果 / 工程顺序 / Web / 白箱审计库)

**v2 已修 8 个 blocker 全部继承**。本稿不重复 v2 内容,只在以下新增章节扩展。

---

## 11. 习惯化与注意力过滤的统一能量模型(U1 数学化,继承 APV2 P1-J-13/15/22)

### 11.1 用户原话回应

> "如果音频中持续的有稳定的杂音,比如风扇声,人类除了一开始能认知到,后面就和'仿佛听不到了'一样,会被注意力过滤。"
>
> "这种对不变输入的注意力过滤能力似乎每个模态都有。"

**关键洞察**:习惯化不是新机制,而是 v3.0 能量动力学的**自然产物**。如果 v3.0 数学对,习惯化自动涌现。如果习惯化不涌现,说明 v3.0 数学有问题——这给了一个**反向验收门**。

### 11.2 数学推导(为什么稳定输入自动被过滤)

设某 SA(如"风扇声")在每个 tick 都有稳定外源注入 $\text{Inj}^{ext}_i(t) = I$(常数)。

由 v3.0 §2.1 能量演化律:
$$R_i(t) = \rho_R \cdot R_i(t-1) + I \to R_i^* = \frac{I}{1 - \rho_R}$$(稳态)

由 C* 预测机制:**反复出现的输入 → Cn 学到稳定后继预测 → 每 tick 给 $V_i$ 注入 $\Pi_i$**。设稳定后:
$$V_i(t) = \rho_V \cdot V_i(t-1) + \Pi_i \to V_i^* = \frac{\Pi_i}{1 - \rho_V}$$

由 §3 最小预测误差校准:**$\Pi_i$ 趋向 $R_i^*$**(target_cap = real_energy ruler)。所以稳态:
$$R_i^* \approx V_i^* \implies P_i^* = R_i^* - V_i^* \to 0$$

由 §4 attention_score 公式:
$$s_{attn} = \beta_P \cdot P + \beta_R \cdot R + \beta_A \cdot A + \beta_V \cdot V - \beta_F \cdot F$$

稳态时 $P \to 0$,而 fatigue $F$ 因反复占焦点而累积升高(v3.0 §3.7 范式疲劳)。所以:
$$s_{attn}^* = \beta_R \cdot R^* + \beta_V \cdot V^* - \beta_F \cdot F^* \xrightarrow{F \uparrow} \text{very low}$$

**结论:稳定输入数学上必然走向低 attention_score,系统"听不到"它**。这正是习惯化。

### 11.3 短期残响层精化(继承 APV2 P1-J-13/15)

APV2 P1-J-13/15 已验证的**per-modality 残响衰减**:

| 模态 | max_age | decay | max_echo_energy | 拟人意义 |
|---|---|---|---|---|
| 视觉 | 4 tick | 0.42 | 0.16 | 看一眼后印象很快淡 |
| 音频 | 24 tick | 0.82 | 0.22 | 听到的声音余音持续几秒 |
| 文本 | 10 tick | 0.72 | 0.18 | 字句过目印象中等 |
| 想法 | 14 tick | 0.76 | 0.20 | 想法在意识里飘几秒 |

**echo 公式**(APV2 已验):
$$\text{echo\_energy}(t) = \text{original\_energy} \cdot \text{gain} \cdot \text{decay}^{age}$$
上限 `max_echo_energy`,逾 `max_age` 即清除。

**关键工程规则**(APV2 J-15 教训,必继承):
- 想法 echo 不携带视觉 reconstruction_payload(否则视觉鬼影自我续命)
- 每模态独立 quota,单一模态不能压垮其他模态
- echo SA 携带 `not_new_external_input=true`,不应被当成新感受输入

### 11.4 习惯化的"反指标"——惊和违和反而显眼

由同样的能量公式:**突然出现的对象** $R_j$ 暴涨 + $V_j \approx 0$(预测未学到)→ $P_j$ 大正 → $s_{attn,j}$ 暴涨 → 必抢焦点。**这正是 §14 意外驱动焦点移动的同源数学**。

### 11.5 主动重新感知(U2 落地)

用户:"当人类想要注意它时,也可以通过主动的注意力聚焦来让自己再次分辨/判断有没有这个输入对象"

**机制**:增加 `action::attention::refocus_on(target_band|target_region|target_sa)`:
- 这是个普通 action SA,经 ActionOutcomeMemory 学奖惩
- 触发条件 1:**先天好奇心**(default_rules 里有低强度 prior)
- 触发条件 2:**后天学到的好处**(主动注意发现过有价值信息 → drive_bias 增)
- 执行效果:对目标 SA **强行注入 $G_i$**(attention_gain 增益),临时压过疲劳

数学:
$$G_i(t) = G_{i,base}(t) + \delta_{refocus} \cdot \mathbb{1}[\text{refocus\_action targets } i]$$

其中 $\delta_{refocus}$ 是 tuner-owned 常数,默认相当于 0.6 倍 attention_score 阈值。

**关键拟人**:`refocus` 可以"复活"被习惯化的对象。用户想听风扇声 → refocus 到风扇频段 → 风扇 SA 的 $A$ 暂时高 → $s_{attn}$ 重新超过阈值 → 焦点回到风扇 → 系统重新"听到"。

### 11.6 红线扫描

- ❌ 不许写"if sa.is_stable: ignore" 这种硬规则——习惯化必须从能量数学涌现
- ❌ 不许给"惊"做专门的检测器——必须经 cognitive_pressure 通道
- ❌ 不许让 echo SA 越界滋长(继承 APV2 J-15 经验)

---

## 12. 合理感门控:把握度 × 显著度的注意力分配(U3 数学化,继承 APV2 P1-J-22)

### 12.1 用户原话回应

> "这方面我建议通过能量/预测模型的角度来试着解决"
>
> "当一件事发生,但是合理感很强时,也不太容易被注意到"

### 12.2 数学:把握度 g 与显著度 s 的乘积门控

继承 v3.0 §4.1 的把握度定义:
$$g(t) = \sigma\left(\gamma_a \cdot \text{alignment\_score}(t) + \gamma_c \cdot \text{top\_candidate\_conf}(t) - \gamma_e \cdot \text{candidate\_entropy}(t) - \gamma_s \cdot \max(0, P_{focus}(t))\right)$$

引入显著度:
$$s_i = \beta_R \cdot R_i + \beta_A \cdot A_i$$(纯"在场强度")

**注意力分配门控函数**:
$$\text{attention\_bid}(i, t) = s_i \cdot (1 - g_i)^{\eta_{grasp}}$$

其中 $g_i$ 是该 SA 在状态池的"局部把握度":
$$g_i = \frac{V_i + \epsilon}{R_i + V_i + \epsilon}$$(预测多接近实际)

含义:
- **把握度高(g→1)且显著度高(s 大)**:风扇声——bid 低,**不抢焦点** ✅
- **把握度低(g→0)且显著度高(s 大)**:闹钟——bid 高,**抢焦点** ✅
- **把握度高且显著度低**:背景静默物体——bid 低 ✅
- **把握度低且显著度低**:微弱新奇刺激——bid 中等,**取决于其他因素**

### 12.3 视觉定向仲裁(继承 APV2 P1-J-22 教训)

APV2 P1-J-22 验证:`hold_gaze` 的 outcome_bias 原本太强,**让习惯化吃掉了真异常**。修正:
$$\text{hold\_gaze\_score} = \text{outcome\_bias} \cdot \max(0, 1 - \frac{\text{peripheral\_arbitration}}{\theta_{break}})$$

其中:
$$\text{peripheral\_arbitration} = w_p \cdot \text{peripheral\_need} + w_m \cdot \text{motion} + w_{|P|} \cdot |P_{peripheral}| + w_s \cdot \text{salience}_{peripheral}$$

当外周信号超过 $\theta_{break}$,`hold_gaze` 失效,焦点移走。这是 J-22 的**关键工程经验**,必须继承。

### 12.4 睡眠态门控(SNS 桌宠 J-J-J 经验)

继承 SNS `true_sleep / low_frequency_poll(60s) / fast_spinner / slow_spinner` 状态机:
- 深度睡眠态:$\theta_{break}$ 升高,**只有极强信号能唤醒**(闹钟 ✓,风扇声 ✗)
- 浅睡眠态:$\theta_{break}$ 中等
- 清醒态:$\theta_{break}$ 标准

这正是"睡觉时风扇不吵醒,闹钟吵醒"的数学。

---

## 13. 视焦点 + 变分辨率 + 实时可视化(U4 数学化,继承 APV2 P1-J-5/6)

### 13.1 用户原话回应

> "希望也能实时在画面中展示它对应 tick 的视焦点位置"
>
> "理论上视焦点附近的信息它采集的保真度更高,这样可以允许它在需要某个信息但是直接采集分辨率不够时,移动视焦点到对应位置"

### 13.2 视焦点作为一等 SA(继承 APV2)

**SA**:`attention::vision::focus`
- 状态:`(focus_x, focus_y, focus_radius) ∈ R³`(屏幕归一化坐标)
- 是状态池一等公民,有 R/V/P/A/F
- 通过 v3.0 §5 attention softmax 与其他 SA 竞争资源

### 13.3 连续 foveated 采样(APV2 J-5 已验证)

每个 percept_proto 的采样分辨率由距焦点距离决定:
$$\text{resolution}(p) = \text{smoothstep}(d_{\max}, d_{\min}, \text{distance}(p, \text{focus})) \cdot (R_{high} - R_{low}) + R_{low}$$

其中 smoothstep:
$$\text{smoothstep}(a, b, x) = 3t^2 - 2t^3, \quad t = \text{clamp}((x-a)/(b-a), 0, 1)$$

继承 APV2:`R_high ≈ 20×20×3`,`R_low ≈ 8×8×3`,`focus_radius ≈ 0.15`(归一化).

### 13.4 focus_detail_patch(继承 APV2 J-5)

只对**焦点附近高分对象**额外生成小型近原图剪裁:
$$\text{generate\_focus\_detail\_patch}(p) \iff \text{distance}(p, \text{focus}) < \text{detail\_threshold} \land R_p > \text{R\_threshold}$$

patch 大小:32×32×3(可配),存入 §10 白箱审计库的 C0 通道。

**关键**:这是采样精度提升,**但不全图都高精度**——避免空间爆炸,只保证用户最在意的那个对象高清晰。这正是中心凹的生物学原理。

### 13.5 音频频段焦点(U6 落地,补 APV2 缺口)

**APV2 没完整做的部分**:`lock_audio_band` 草稿存在但没有完整疲劳 + 参数学习。v3 补完:

**SA**:`attention::audio::band`
- 状态:`(center_hz, band_width_hz) ∈ R²`
- 一等 SA,行动 SA 可改变其位置:`action::audio::shift_band(target_hz)` / `widen_band(factor)`

**频段内的音频对象 R 增益**:
$$\text{gain}(audio\_sa) = (1 - \beta_{audio}) + \alpha_{audio} \cdot \exp\left(-\frac{(f_{sa} - f_{focus})^2}{2 \cdot \text{band\_width}^2}\right)$$

完全镜像视觉焦点公式,只是 1D 版。

### 13.6 内心画面实时显示焦点位置(U4 关键落地)

继承 SNS `ap_desktop_focus_overlay_bridge.py` 的 overlay 机制 + APV2 J-3 `inner_vision_reconstruction.focus_overlay`:

```python
def render_inner_canvas(state_pool, audit_db):
    canvas = blank_canvas()
    # 1. 渲染所有视觉 SA(从审计库读 C0 patch)
    for sa in state_pool.where(family="vision_percept"):
        raw_patch = audit_db.lookup_payload(sa.persistent_id)
        blend_to_canvas(canvas, raw_patch, position=sa.C4_center, alpha=α(sa.R))
    
    # 2. NEW v3: 实时叠加焦点圆/方框 + 焦点附近高精度采样区域
    focus_sa = state_pool.get("attention::vision::focus")
    if focus_sa and focus_sa.R > render_threshold:
        draw_focus_indicator(canvas, focus_sa.x, focus_sa.y, focus_sa.radius,
                             color="cyan", alpha=0.7)
        # 焦点处采样精度可视化
        for p in state_pool.where(family="vision_percept"):
            if has_focus_detail_patch(p):
                draw_high_res_marker(canvas, p.position, marker="✨")
    
    return canvas
```

**Web 工作台显示**:用户能直接看到当前 tick AP 在看哪里、哪些对象是高清采样的。这正是 SNS focus overlay 在 inner canvas 上的版本。

---

## 14. 意外/违和驱动焦点移动 + 本能/后天可学(U5 数学化,继承 APV2 P1-J-6)

### 14.1 用户原话回应

> "它的'本能'中应该也有拟人原则类似的'有意外输入/违和感对象'时,视焦点本能的移动到对应位置的设计"
>
> "比如之前的苹果上面没有叶子,这次加了个叶子,那它就会觉得很意外,视角会本能的有一种查看它和预期不符地方的感觉"
>
> "这个本能也不是写死的,它也是一种可以被后天学习来对抗的行动范式"

### 14.2 2D 视野的 P 场(违和热力图)

视觉感受器每 tick 产生**逐区域的认知压力场**:
$$P_{field}(x, y, t) = \sum_{p \in \text{vision\_percepts}} P_p \cdot K(\text{distance}((x,y), p_{center}))$$

其中 $K$ 是高斯核(影响范围)。

**违和区域** = $P_{field}(x,y) > \theta_{anomaly}$ 的区域。

### 14.3 saccade 行动候选生成(继承 APV2 J-6 闭环)

每 tick 由 P_field 自动生成 `move_gaze_to` 候选:
$$\text{move\_gaze\_score}(x, y) = w_P \cdot P_{field}(x,y) + w_R \cdot \text{salience}_{field}(x,y) + w_m \cdot \text{motion}_{field}(x,y) - w_f \cdot \text{fatigue}_{field}(x,y)$$

**关键工程红线(继承 APV2 J-20)**:`move_gaze_to` **必须带真实 (x, y) 或 bbox_norm**——绝不允许 label hash 当假坐标。

### 14.4 先天 → 后天可覆盖(U5 关键落地)

**本能(先天)**:`default_rules.py` 加 AT-NEW 规则:
```
AT-NEW-saccade: 
  trigger: P_field > θ_innate
  emit: action::move_gaze_to(argmax_xy P_field) bias=0.5
```

**后天覆盖**:同 SA 经 `ActionParameterMemory` 学到 `(context, gaze_delta) → utility`。
- 经验显示某情境下"不要看异常"有奖励(如训练系统忽略分散注意力的元素)→ utility 累积负值 → `drive_bias` 抵消本能
- 这正是 ActionParameterMemory 的**软偏置覆盖**模式

**关键**:本能不是 hardcode,是**强初值的可学习参数**。

### 14.5 音频违和的频域版本(U6 + U5 结合)

完全对应,只是 1D:
$$P_{audio\_spectrum}(f, t) = \sum_{a \in \text{audio\_percepts}} P_a \cdot K(|f - f_a|)$$

行动 `action::audio::shift_band_to(target_hz)` 由 spectrum 上的 P 峰驱动。

### 14.6 视觉目标疲劳(继承 APV2 J-8)

防止焦点反复看同一异常:
$$\text{fatigue}_{field}(x, y) = \sum_{t' \in \text{recent}} \text{decay}^{(t-t')} \cdot \mathbb{1}[\text{looked\_at}((x,y), t')]$$

继承 APV2 J-8 的 ActionParameterMemory 接口,**软抑制不硬排除**。

---

## 15. 我推论的 3 个额外拟人机制(v3 新增)

### 15.1 E1 - 多模态焦点联动(注意力的看-听-想协同)

**拟人现象**:专注听某人讲话 → 眼睛本能看那人 / 看某物时听觉过滤增强 / 想问题时眼神发呆(视觉退化)。

**机制**:状态池中各模态焦点 SA 通过 cognitive_pressure 通道**互相耦合**:

$$P_{focus,vision}(t) = \alpha \cdot \text{align}(\text{focus}_{vision}, \text{focus}_{audio}) + \beta \cdot \text{align}(\text{focus}_{vision}, \text{focus}_{thought})$$

`align` 是"两个焦点对应同一对象/同一概念"的相似度,经 §2 通用词汇固化产生的跨模态 SA 链接判定。

**结果**:
- 看到人(视觉焦点)+ 听到声(音频焦点) + 两者属同一 vocab SA → P_focus,vision 和 P_focus,audio 互相加强 → 注意力锁定该人,其他干扰被自然过滤
- 思考某概念(慢系统焦点)+ 视觉漫游 → 视觉焦点 P 弱 → 视觉退化("看不见")

**实现**:`align` 函数走既有 learned_similarity,不引入新机制。

### 15.2 E2 - 似曾相识感受(高熵 Bn 召回 → 模糊感)

**拟人现象**:场景熟悉但细节不同 → "有点眼熟但说不清"。既不是惊也不是合理。

**机制**:cognitive_feelings 通道新增 spec:
```
feeling::deja_vu
  trigger features:
    - Bn 召回 top-K 候选熵 > θ_entropy(多候选分数接近)
    - top-1 候选 alignment_score 中等(0.4-0.7)
    - 至少 1 个候选有 promoted vocab SA 关联
  emit:
    real_energy = entropy * mid_alignment * 0.6
    cognitive_pressure = 0.3
    驱动: action::scan_more / action::reread / action::ask_clarify
```

**关键**:似曾相识感受 **驱动主动探索**(scan more / re-read / ask),不只是个标记。

### 15.3 E3 - 注意力惯性 / 漫游(idle 内源探索)

**拟人现象**:长时间无外源 → 眼神漫游 / 思维飘走,不死钉一处。

**机制**:无外源时,attention_gain $A_i$ 的自然漂移:

$$G_i(t) = \rho_A \cdot G_i(t-1) + \text{idle\_perturbation}_i(t)$$

其中:
$$\text{idle\_perturbation}_i(t) = \mathbb{1}[\text{idle\_score}(t) > \theta_{idle}] \cdot \eta_{wander} \cdot \text{residual\_mass}_i$$

`idle_score` = 最近 K tick 外源输入总能量为零;`residual_mass` 是 ResidualTracker 里那 SA 未解决的能量。

**结果**:idle 时 ResidualTracker 里的未解决问题逐渐获得 attention_gain → 焦点漫游到它们 → 自发"想起"未完成的事或未解决的疑问。**这是 v3.0 §6 内源链的具体落地**,补 APV2 缺失。

---

## 16. 工程实施 Phase 重排(基于 APV2 复用 + v3 新增)

### 16.1 重大调整:大量复用 APV2 已验证模块

| 模块 | APV2 路径 | v3 处理 |
|---|---|---|
| 短期残响 echo_buffer | `memory/short_term/echo_buffer.py` | **原样搬入**(只改 import) |
| 视觉焦点感受器 | `sensors/vision/numeric_sensor.py` 中 `_smoothstep` / `_focus_gain_for_box` 等 | **按接口搬**(配 v3 通道注册表) |
| 音频焦点感受器 | `sensors/audio/numeric_sensor.py` | **按接口搬**(补完 lock_audio_band 完整逻辑) |
| ActionParameterMemory | `core/action/parameter_memory.py` | **原样搬入** |
| VisualGazeActuator | `core/action/focus_actuators.py` | **原样搬入** |
| Focus overlay bridge | `StrongestNurturingSystem/scripts/ap_desktop_focus_overlay_bridge.py` | **改造**为 Web 工作台版本 |
| Inner canvas reconstruction | APV2 J-2/J-3 设计 + 实现 | **重构入 v3 §13.6** |
| Visual orientation arbitration | APV2 planner `_apply_visual_orientation_arbitration` | **按接口搬** |
| Cognitive feelings | `channels/cognitive_feelings/channel.py` | **复用 + 补缺**(填 fluency/boredom/fulfillment) |
| Emotion modulator | `core/emotion/emotion_modulator.py` | **原样复用** |
| Attention selector | `core/attention/selector.py` | **原样复用** |
| AdaptiveTuner | `core/tuner/adaptive_tuner.py` | **原样复用** |
| ResidualTracker | `core/state_pool/residual_tracker.py` | **原样复用** |
| OnlineEmbeddingStore | `memory/embedding/online_store.py` | **原样复用** |
| Short-term buffer 全套 | `memory/short_term/*` | **原样复用** |
| Persistence schema | `memory/persistence/sqlite_store.py` | **复用 schema** |
| SNS desktop pet | `StrongestNurturingSystem/scripts/desktop_pet.py` 等 | **可选未来**:作为 v3 Web 工作台之外的另一个表达层 |

### 16.2 真正需要 Codex 新写的(v3 原创)

- **§2 ComposedVocabStore**(通用 SA 组合词汇,跨模态)
- **§10 白箱审计库**(独立 SQLite,可配置)
- **§11.5 attention::refocus action**(主动复活习惯化对象)
- **§12 合理感门控** + 睡眠态阈值切换
- **§13.6 焦点 overlay 入 Web 工作台**(继承 SNS focus overlay)
- **§14.2 P_field 2D 异常热力图**(逐区域 cognitive_pressure)
- **§15 三个新拟人机制**(E1 跨模态焦点 / E2 deja_vu / E3 漫游)
- **§1.6 场景化 tick 配置**(纯文本/桌宠/具身/Agent 4 套预设)
- **§1.7 主动休眠行动**

### 16.3 Phase 顺序(以可见进展优先)

```
Phase 8.2  逻辑 tick runtime + 场景化 + 主动休眠
Phase 8.3  白箱审计库
Phase 8.4  通用 SA 组合词汇机制
Phase 8.5  视觉感受器多通道 + foveated 采样 + C0 入审计库(从 APV2 按接口搬)
Phase 8.6  视焦点 SA + saccade 行动 + 焦点 overlay 入 Web(继承 APV2 J-6)
Phase 8.7  黄色苹果泛化端到端验收(用户最早看到核心承诺)
Phase 8.8  习惯化数学验证 + 主动 refocus 行动(§11)
Phase 8.9  合理感门控 + 睡眠态阈值(§12)
Phase 8.10 似曾相识感受 + idle 漫游 + 跨模态焦点联动(§15 三机制)
Phase 8.11 纠错教学行动范式(Codex 8.4 原意)
Phase 8.12 Web 工作台升级(完整版,inner canvas + audit + dual-bubble)
Phase 8.13 音频感受器多通道 + 频段焦点(完整版,§13.5)
Phase 8.14 多模态端到端验收
```

**关键调整**:把"习惯化/合理感/三机制"集中在 8.8-8.10——这些都建立在视觉焦点 + 通用词汇上,**早做反而验证不了**。

---

## 17. 完美图景的拟人能力清单(v3 全部覆盖)

按你的"立意最高"要求,这里把 v3 完成后系统拥有的所有拟人能力枚举出来。**全部都有数学落点**,不是 vapor:

### 感知层
- ✅ 多通道独立向量化(视觉 7 通道 / 音频 6 通道 / 文本 4 通道)
- ✅ 焦点附近高保真采样,外周低分辨率(变分辨率)
- ✅ 焦点位置实时显示(Web inner canvas)
- ✅ 跨模态焦点联动(看人时听该人声音,听人时看该人)

### 注意力层
- ✅ 稳定输入习惯化(听不到风扇声)
- ✅ 主动 refocus 可重新感知(想听就能听到风扇声)
- ✅ 合理感门控(预期内的不抢,意外的抢)
- ✅ 睡眠态阈值变化(只有强信号能唤醒)
- ✅ 视觉/音频违和驱动焦点移动(意外位置/频段本能查看)
- ✅ 本能可被后天学习覆盖(ActionParameterMemory)
- ✅ 注意力漫游(idle 时焦点不死钉)
- ✅ 目标疲劳(反复看同一对象会"看烦")

### 学习层
- ✅ 通用 SA 组合词汇固化(跨模态)
- ✅ 似曾相识感受(高熵召回 → 模糊感 → 驱动探索)
- ✅ 范式槽位 + 通道签名(黄苹果泛化)
- ✅ Phrase memory 风格守恒(无口少女表达)
- ✅ 用户风格 mirroring(共现学到的口味)
- ✅ 教学协议同构(自然 vs LLM 等价)
- ✅ 纠错教学行动范式

### 内省层
- ✅ 草稿内省感受涌现 + 与外部表达共现学习
- ✅ 内心画面可重建(从审计库读 C0 patch)
- ✅ 内心音频可重建(从审计库读 A0 PCM)
- ✅ 想法云(状态池 top SA 可视化)
- ✅ 焦点 overlay(实时 AP 在看哪)
- ✅ 行动审计(逐 tick 草稿动作)
- ✅ Echo 短期残响(感觉余韵)

### 运行时层
- ✅ 逻辑 tick(可回放可加速)
- ✅ 场景化配置(纯文本/桌宠/具身/Agent 4 模式)
- ✅ 主动休眠(系统自己降频率)
- ✅ 真实时间戳与 tick 解耦
- ✅ 短时→长时记忆晋升(几分钟保上下文)
- ✅ SQLite 持久化 + warm-load parity
- ✅ 白箱审计库分离(可配置/可关/LLM 周期清理)
- ✅ Bounded tick loop(永不无限后台跑)

### 表达层
- ✅ 120 phrase 风格库(可后期扩)
- ✅ 风格守恒红线(无口少女 / 极简 / 诚实)
- ✅ Dual-bubble 言说(AP-native vs LLM 严格分)
- ✅ 多轮对话流(惩罚改变下次召回 / 话题切换隔离)

### 系统层
- ✅ AP-native vs LLM 严格边界
- ✅ 永不 raw asset replay(内心音频/画面必须状态池合成)
- ✅ Conflict-domain 并行行动(看 + 想 + 持姿)
- ✅ 桌面控制安全门(必须用户确认)

---

## 18. 给 Codex 的总指令格式

1. 读完本文档(v3,本稿)
2. 按 §16.3 顺序逐 Phase 实施
3. **每个 Phase 走完整 5 段闭环**
4. **APV2 复用模块**:看 §16.1,按接口搬入,不要重写
5. **v3 原创模块**:看 §16.2,按各章节详细设计实现
6. **任何"看起来通过但不该通过"立即停下问 Claude**
7. **特别注意**: SNS 桌宠相关红线(dual-bubble / focus overlay TTL / bounded loop / 桌面控制安全门)必须继承

---

— 接手线程,2026-06-17
