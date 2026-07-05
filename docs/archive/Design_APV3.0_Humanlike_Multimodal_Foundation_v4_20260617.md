# APV3.0 拟人多模态底座 — 完整设计稿 v4(对抗审阅 + 哺乳类心智深化)

日期: 2026-06-17
作者: 接手线程
状态: **v3 经对抗审阅发现 7 blocker + 9 serious + 16 心理学覆盖洞。v4 全部修复并深化整个拟人心智闭环。新增哺乳类共享心智维度(驱力 / RPE / 受挫 / 依恋 / 共同注意 / 共情 / 痛厌恶 / 心智化 / 重放巩固),全部建立在已有 R/V/P/A/F 能量场上自然生长,绝不并行新开公式。**

前身:
- v1 (9 blocker)、v2 (修 8 blocker + 用户 3 哲学)、v3 (整合 APV2/SNS + 9 拟人机制)
- **v4(本稿)**:v3 修 7 blocker + 9 serious + 哺乳类心智闭环

---

## 0. v3 → v4 修复总览(必读)

### 0.1 7 个 blocker 必修(全部已落地)

| # | v3 缺陷 | v4 修复 |
|---|---|---|
| **B-A2** | 习惯化 "F↑ → s_attn↓" 推导循环(F 只在持焦时累积,失焦的对象不会积 F) | §11.2 完整稳态推导:用预测疲劳(prediction_fatigue) + 注意疲劳分开;习惯化主要靠 P→0 + adaptive_tuner 学到的低 R/V 项权重,不靠 F 单独完成 |
| **B-A3** | g_i = V/(R+V) "把握度" 不是把握度,novel SA 给最大 bid 而非最低 | §12.2 删旧 g_i,统一用 v3.0 §4.1 的 g(基于 alignment_score + entropy + confidence);novel SA 因 alignment=0、entropy=high → g→0 → bid 高(正确) |
| **B-A7** | argmax 焦点跳变,无持驻 | §14.4 加 hold_dwell_min_ticks + 滞回 margin (继承 J-22) |
| **B-A8** | E1 跨模态 align() 冷启动死锁(回到 v1 B3) | §15.1 双层 align:时空共现(低层 boot)+ vocab 链接(高层 strengthen),冷启动可工作 |
| **B-B1** | 习惯化 1 tick 撤销自己的注意力峰值,新事件不能保持秒级注意 | §11.7 novelty trace:V 学习率受 trust gating 限制,真新事件需多 tick 才能预测被吸收;同时 anchor 一个独立 novelty_residual SA |
| **B-B3** | 睡眠态无进入/退出机制,是 hardcoded 模式 | §12.5 sleep 由全局累积 fatigue + 学到的 tick_frequency_change 行动共同决定,纯 emerge |
| **B-B5** | emotion_modulator 复用,但 fluency/boredom/fulfillment 永远=0,所有 DA/SER 计算永久失校 | §16.4 完整规范:这 4 个 CFS 从既有状态量推导,补完 channel.py 缺口 |

### 0.2 9 个 serious 全部修复

| # | 问题 | v4 修复 |
|---|---|---|
| S-A1 | §11.2 Π=f(R,V) 非 Π=f(R) | §11.2 重写,承认是稳定性猜想,加经验验收门 |
| S-A4 | smoothstep 参数顺序错 | §13.3 公式重写,逆向 smoothstep |
| S-A5 | 频段焦点只增益一个谐波,人声听不清 | §13.5 改为可学习 filterbank 模板(sum-of-Gaussians at f0·k),由 vocab SA 存 |
| S-A6 | P_field 是 50 percept 卷积出的"汤" | §14.2 改为 percept-centric WTA(winner-take-all over percept centers)+ 时间平滑 |
| S-A9 | deja_vu 触发是硬编码三段检测器 | §15.2 改为在已有 (g, P) 平面 + 多通道召回指纹的自然涌现 |
| S-A10 | idle 漫游 = ResidualTracker 已有功能换名 | §15.3 改为对 ResidualTracker 加 idle gate,诚实承认不是新机制 |
| S-B2 | 主动 refocus 的"innate curiosity prior" 是另一个硬规则 | §11.5 改为从 ActionParameterMemory 学到的"refocus 预期 ΔP" 行动竞争,纯 emerge |
| S-B4 | 内心画面被 audit_db 驱逐策略绑架 | §13.7 显式分层:audit_db 是 episodic 视觉记忆,evicted = "记不清细节"是正确拟人;stylized_blob 是 canonical |
| S-B6 | short_term_buffer 复用语义不匹配(episode_id) | §16.6 加迁移规范:episode_id → 新 scenario_session_id;focus_id 命名空间扩展 |
| S-C2 | SNS dual-bubble "已验证" 误报 | §0.4 修正措辞为"红线契约,继承自 SNS,非已验证 UI" |

### 0.3 哺乳类共享心智维度(v4 全新章节 §20-§28)

对抗审阅找到 16 个覆盖洞。v4 把其中**最高 gating 的 9 个**全部数学化,**全部建立在已有 R/V/P/A/F 能量场上**,绝不并行新开公式:

| § | 心智维度 | 哺乳类对应 | 复用底座 |
|---|---|---|---|
| **§20** | **驱力 / 内稳态** | 饿/累/好奇/安全 的恒在能量,无外源时自动滑向行动 | 既有 R 能量场 + 新 drive_SA 一等公民 |
| **§21** | **奖励预测误差 RPE = dopamine analog** | 多巴胺信号驱动学习 | 既有 P 通道 + 拓展 ΔP_outcome 直接走 emotion DA 通道 |
| **§22** | **挫败 / 习得性无助** | 长期 P 高 + 行动无效 → 放弃 | 在 emotion_modulator COR 通道上拓展 helplessness_gain |
| **§23** | **依恋 / 熟悉性偏好** | 偏好熟悉的照护者,分离焦虑 | OnlineEmbeddingStore + 用户实体 SA 累积 R 形成"依恋"印迹 |
| **§24** | **共同注意 / 镜像系统** | 跟随他人视线,共享焦点 | E1 跨模态焦点 + 模型他人 focus_SA 作为状态池一等公民 |
| **§25** | **共情 / 心智化(Theory of Mind)** | 想象他人的内部状态 | 内省感受 prototype + 用户实体 SA 的关联感受 sub-state |
| **§26** | **痛 / 厌恶持续记忆** | 痛是多模态、持续、跨情境的负标记 | 既有 Rwd/Pun 通道 + 持续负 trace SA |
| **§27** | **重放巩固 / 睡眠学习** | 睡眠中海马回放经验,促长时记忆 | sleep 态 + ResidualTracker 反向激活既有 SA |
| **§28** | **游戏 / 探索性玩乐** | 无外部奖励的探索,内驱 | 既有 NOV 通道 + 低 R 时段主动注入 novelty_seek 行动 |

### 0.4 红线修正

- **❌→📝** SNS dual-bubble "已验证" → "红线契约继承,SNS 没真出 UI" (诚实)
- **❌** 任何"硬编码 detector" 引入新机制(B5/S-B2 教训)——所有新心智都必须从已有能量场涌现
- **❌** emotion_modulator 静默失校继续——v4 §16.4 必须完整补 4 个 CFS,Codex 不能"原样复用"
- **❌** Π 推导假设 Π=f(R) → 公开承认这是稳定性猜想,加验收门

---

## 1-10. 沿用 v3/v2 大体结构

§1-10 保持 v3/v2 原状,**仅修复 §10 关于 audit_db 的边界**:audit_db 在 v4 中**正式被认定为 AP-Core 的 episodic 视觉/音频记忆层**(不再说"在 AP 之外"),其驱逐策略 = 人类记忆的细节退化,是正确拟人,不是 bug。"AP 在 audit_db 关时不 fail" 仍然成立(走 stylized_blob)。

---

## 11. 习惯化的完整稳态推导 + Novelty Trace(B-A2 + B-B1 + S-A1 fix)

### 11.1 v3 的两个核心错误

**错误 1(B-A2)**:v3 推导 "F↑ → s_attn↓"。但 F 只在 SA 实际持有焦点时累积。被习惯化的 SA 失焦快,F 不长,推导循环。

**错误 2(B-B1)**:v3 用单 tick 的 Π 完全吸收新输入。真新事件 100ms 后被预测覆盖,远低于人类秒级感知。

### 11.2 正确的稳态推导(诚实数学)

**事实**:稳定输入下 R→稳态 R*,Π 由 C* 给出,Π 是 (R, V, 内部循环引用) 的函数。**没有解析解,无单调收敛证明**。

但我们可以分层推导:

**层 1 - 短期学习率限制(B-B1 fix)**:每个 SA 的 Π 更新带学习率上限:
$$\Pi_i(t) = \Pi_i(t-1) + \min(\eta_{\Pi,\max}, \kappa \cdot R_i(t)) \cdot \text{prediction\_signal}_i(t)$$

其中 $\eta_{\Pi,\max}$ 是 tuner-owned 上限,默认相当于 0.15(意思是真新事件需要 ~7 tick 才能被预测完全吸收,约 700ms,**接近人类感知阈值**)。

**层 2 - 习惯化通过预测疲劳实现**:
$$F_i^{\Pi}(t) = \rho_F^{\Pi \cdot \text{unit\_steps}} \cdot F_i^{\Pi}(t-1) + \Phi_i^{\Pi}(t)$$

其中 $\Phi_i^{\Pi}$ = 该 SA 主导预测(主导率 ≥ 阈值)时按主导份额累积小步疲劳。这是 APV2.1 `state_pool.py:_apply_prediction_fatigue` 已实现机制(继承,**非新模块**)。

预测疲劳 ≠ 注意疲劳:即使 SA 不持焦,只要被反复预测/被反复占预测带宽,$F^{\Pi}$ 仍累积。

**层 3 - attention_score 完整公式**:
$$s_{attn,i} = \beta_P \cdot |P_i| + \beta_R \cdot R_i + \beta_A \cdot A_i - \beta_F \cdot F_i^{attn} - \beta_{F\Pi} \cdot F_i^{\Pi}$$

**稳态行为**:稳定输入下 $|P_i| \to 0$ + $F^{\Pi}$ 持续增 → s_attn 持续下降。这才是 "听不到风扇声"的正确数学。

**层 4 - 经验验收门(S-A1 fix)**:既然我们没有解析收敛证明,Phase 8.8 验收必须**经验验证**:
- 注入恒定风扇声 SA(R 注入 = 0.3,持续 500 tick)
- 测 t=0/50/100/200/500 时该 SA 的 s_attn
- 验收:第 100 tick 后 s_attn 单调下降至 t=0 的 30% 以下
- 失败 → 不许调阈值过,要找 Π 学习率/predict_fatigue 是不是真在工作

### 11.3 Novelty Residual SA(B-B1 fix 关键)

仅"学习率限制"还不够保证秒级注意。引入 **novelty_residual** 机制:

当某 SA 出现 cognitive_pressure > θ_novelty(意外或新输入):
- 创建/续命一个伴生 SA `novelty_residual::<原 SA persistent_id>`
- 这个伴生 SA 的衰减率 ρ_R^novelty 很慢(半衰期 ~3 秒)
- 它向原 SA 持续注入 attention_gain $G_i$,直到自然衰减

数学:
$$\text{novelty\_residual}_i.R(t) = \rho_R^{novelty \cdot \text{unit\_steps}} \cdot \text{novelty\_residual}_i.R(t-1) + \mathbb{1}[P_i > \theta_{novelty}] \cdot \mu_{novelty} \cdot P_i$$

$$G_i^{novelty}(t) = \xi \cdot \text{novelty\_residual}_i.R(t)$$

**关键拟人**:
- 突然出现叶子 → 一瞬间 P 大 → novelty_residual 建立,R≈0.5 → 持续向焦点注入 G,~3 秒内保持高 attention
- 即使 Π 在 0.7 秒内学到了"叶子在这",novelty_residual 仍未衰减完 → 焦点持续锁定 ~2-3 秒
- 然后自然脱钩,系统继续处理别的

**不引入新机制说明**:novelty_residual 是普通 SA + 标准 R 衰减,只是 spawn 触发规则 + 注入目标不同。完全在既有状态池框架内。

### 11.4 习惯化的反指标:惊和违和(沿用 v3 §11.4 + 接入 §11.3)

新增:**突然出现 → P_j 大正 + novelty_residual spawn → s_attn 维持高 ~3 秒 → 焦点稳定**。这同时回答了 B-B1 (秒级注意持续) + §14 (意外驱动焦点) 两个问题。

### 11.5 主动重新感知 = refocus 行动 + ActionParameterMemory(S-B2 fix)

**v3 错误**:用"innate curiosity prior" 触发,是硬规则。

**v4 解法**:`action::attention::refocus_on(target)` 作为完全普通的行动 SA,**触发完全靠 ActionParameterMemory 学到的期望 ΔP**:

```python
# refocus 行动候选打分(无 hardcoded prior)
def refocus_score(target_sa):
    historical_outcome = action_parameter_memory.lookup(
        action="refocus", context_features=current_context, target=target_sa
    )
    expected_dP = historical_outcome.mean_pressure_decrease
    expected_value = historical_outcome.mean_reward
    return expected_dP * w_curiosity + expected_value * w_value
```

**冷启动**:无历史 → action_parameter_memory 返回 prior_mean(默认 0)→ refocus 极少触发。
**学习路径**:偶然 refocus 时若发现新信息 → ΔP 大 → 经验记忆累积 → 后续相同情境 refocus 评分上升。

**这才是"好奇心是学到的,不是写死的"**(完全契合用户哲学)。

### 11.6 红线扫描(v4 强化)

- ❌ 不许写"if sa.is_stable: ignore" 硬规则——继承 v3
- ❌ 不许给"惊"做专门检测器——继承 v3
- ❌ 不许 echo SA 越界滋长——继承 APV2 J-15
- 🆕 ❌ 不许引入 `is_novel`/`is_familiar` 等布尔字段——novelty 完全靠 P_i + novelty_residual.R 数字标度
- 🆕 ❌ 不许给 refocus 写 innate curiosity prior——必须经 ActionParameterMemory

---

## 12. 合理感门控:正确的 g 公式 + 睡眠 emerge(B-A3 + B-B3 fix)

### 12.1 v3 错误诊断

**B-A3**:v3 在 §12.2 写了**两个**矛盾的 g:
- 第 151 行(继承 v3.0 §4.1):基于 alignment_score + confidence + entropy ✓ 正确
- 第 160 行:`g_i = V/(R+V)` ✗ 错误,novel SA 反而最高 bid

### 12.2 v4 唯一 g 公式(删旧建新)

**全文统一使用 v3.0 §4.1 公式**:
$$g_i(t) = \sigma\left(\gamma_a \cdot a_i + \gamma_c \cdot c_i - \gamma_e \cdot h_i - \gamma_s \cdot \max(0, P_i)\right)$$

其中:
- $a_i$ = SA i 在最近召回中的 alignment_score
- $c_i$ = top candidate confidence
- $h_i$ = candidate entropy
- $P_i$ = cognitive_pressure

**Novel SA 行为**:首次出现 → 没有 alignment 历史,$a_i=0$;熵 $h_i$ 高(无明确召回)→ g → σ(负数) → g 低 → (1-g)^η 高 → bid 高 ✓ 正确。

**已习得 SA 行为**:$a_i$ 高 + $h_i$ 低 → g → 1 → (1-g)^η → 0 → bid 低 ✓ 正确。

**attention_bid**:
$$\text{attention\_bid}(i) = s_i \cdot (1 - g_i)^{\eta_{grasp}}$$
$s_i = \beta_R \cdot R_i + \beta_A \cdot A_i$(显著度)

### 12.3 视觉定向仲裁(继承 v3 §12.3,无改)

### 12.4 sleep 状态从 emerge(B-B3 fix)

**v3 错误**:深/浅/醒 三态,但谁设置?

**v4 解法**:sleep 完全 emerge,**没有显式状态机**,只有连续值:

```python
# 全局累积疲劳(所有 SA 的 F^attn + F^Π)
global_fatigue(t) = Σ_i (F^attn_i + F^Π_i) / N_active

# 该值与 base_tick_ms 协同
target_tick_ms = base_tick_ms * (1 + tick_dilation_factor * sigmoid(global_fatigue))

# 但 tick_dilation_factor 也是 tuner-owned 行动结果:
# action::tick_frequency_change 在 global_fatigue 高时获得正奖励(算力 → 拟人疲倦感)
```

效果:
- 长期高活跃(很多 SA 持续 P)→ global_fatigue 增 → tick 自然变慢
- 长期 idle → 累积疲劳衰减 → tick 自然变快
- 外源唤醒(新输入 burst)→ tick 立即回归 base
- **没有"睡/醒"二分,只有连续 tick 频率,这正是哺乳类的真实生理**

θ_break 不再是 sleep 态变量,而是 global_fatigue 的连续函数:
$$\theta_{break}(t) = \theta_{break,0} + \theta_{break,dilation} \cdot \text{global\_fatigue}(t)$$

**这正是"睡得越深越难叫醒"** —— global_fatigue 高 → θ_break 高 → 弱信号难以唤起焦点,只有强 P 突破。

### 12.5 红线

- ❌ 不许写"sleep_state in [DEEP, LIGHT, AWAKE]" 枚举字段
- ❌ 不许写"if global_fatigue > 0.8: sleep_state = DEEP" 硬规则——必须是连续映射

---

## 13. 视焦点 + 变分辨率 + 重建分层(v3 错误修复)

### 13.1 沿用 v3 §13.1-13.2(无改)

### 13.3 修正的 smoothstep 公式(S-A4 fix)

**v3 错误**:`smoothstep(d_max, d_min, distance)` 参数顺序错。

**v4 正确**:
$$\text{resolution}(p) = R_{low} + (R_{high} - R_{low}) \cdot (1 - \text{smoothstep}(d_{min}, d_{max}, \text{distance}(p, focus)))$$

其中:
$$\text{smoothstep}(a, b, x) = 3t^2 - 2t^3, \quad t = \text{clamp}((x-a)/(b-a), 0, 1)$$

行为:
- d ≤ d_min(焦点内):smoothstep = 0 → resolution = R_high ✓
- d ≥ d_max(远外):smoothstep = 1 → resolution = R_low ✓

### 13.4 focus_detail_patch(继承 v3,无改)

### 13.5 频段焦点:谐波感知(S-A5 fix)

**v3 错误**:单峰高斯只能锁住基频,听不清人声。

**v4 解法**:**可学习的 filterbank 模板**,由 vocab SA 存储:

```python
# 每个 vocab::audio_pattern 存一组峰位置(基频 + 谐波)
vocab_sa.audio_template = {
    "peaks_hz": [200, 400, 600, 800],     # 基频 + 谐波
    "peak_widths": [40, 40, 40, 40],
    "peak_weights": [1.0, 0.6, 0.4, 0.3]
}

# 频段焦点公式:对所有峰累加增益
def audio_gain(audio_sa, focus_template):
    if focus_template is None:  # 无 vocab,退化到单峰
        return single_peak_gain(audio_sa.f0, focus.center, focus.width)
    
    total_gain = (1 - β_audio)
    for peak_hz, peak_w, peak_weight in zip(template.peaks_hz, template.peak_widths, template.peak_weights):
        delta_f = audio_sa.f0 - peak_hz
        total_gain += α_audio * peak_weight * exp(-delta_f**2 / (2 * peak_w**2))
    return total_gain
```

**关键拟人**:
- 系统未学到任何人声 vocab → 退化为单峰滤波,听到的是一个频带
- 学到某个人的声纹 vocab(基频 + 谐波模板)→ 锁定该人时整个谐波栈被增益 → 真能"听清那个人在说什么"

**实现**:audio_template 是普通 vocab SA 的 payload 字段,通过 §2 通用词汇固化机制学到。**无新模块**。

### 13.6 视觉内心画面(沿用 v3 §13.6)

### 13.7 audit_db 边界澄清(S-B4 fix)

**v3 错误**:把 audit_db 说成 "AP-Core 外"但又让它决定内心画面体验。

**v4 边界**:
- **audit_db = AP-Core 内的 episodic 视觉/音频记忆层**(显式归入 AP-Core)
- evicted = "我记不清细节了" 是**正确拟人**,不是 bug
- canonical 内心画面 = stylized_blob(从 C1+C2+C4 通道合成,轻量,总能跑)
- audit_db 存在 + 命中 → 升级为高保真 patch overlay
- audit_db 缺失/禁用 → 仅 stylized_blob(老照片感)

```python
def render_inner_canvas(state_pool, audit_db=None):
    canvas = blank_canvas()
    for sa in state_pool.where(family="vision_percept"):
        # 第一遍:从 C1+C2+C4+θ_p 合成抽象 blob (canonical)
        blob = render_stylized_blob(sa.C1, sa.C2, sa.C4, sa.θ_p)
        blend_to_canvas(canvas, blob, position=sa.C4_center, alpha=α(sa.R) * 0.4)
        
        # 第二遍:audit_db 命中则叠加高保真细节
        if audit_db is not None:
            raw_patch = audit_db.lookup_payload(sa.persistent_id)
            if raw_patch is not None:
                rotated = rotate(raw_patch, sa.θ_p)
                blend_to_canvas(canvas, rotated, position=sa.C4_center, alpha=α(sa.R) * 0.8)
    return canvas
```

**红线扫描**:`grep "if audit_db is None: raise"` 必须 0 命中(AP 不依赖)。

---

## 14. 视野 P 场 + 持驻焦点(S-A6 + B-A7 fix)

### 14.1 沿用 v3 §14.1

### 14.2 percept-centric WTA(S-A6 fix)

**v3 错误**:全屏 P_field 卷积,argmax 可能落在空洞。

**v4 解法**:WTA over percept centers + 时间平滑:

```python
def saccade_candidates(percepts, focus_history):
    # 每个 percept 自带 P 分数,不再做空间卷积
    candidates = []
    for p in percepts:
        salience_p = w_P * |p.P| + w_R * p.R + w_motion * p.motion_score
        # 时间平滑:最近 K tick 内连续高 salience 才作为候选
        smoothed = ema(p.salience, salience_p, alpha=0.4)
        candidates.append((p, smoothed))
    return candidates
```

**优势**:
- 不会跳到 percept 之间的空地
- 时间平滑去抖动
- argmax 一定落在某个真实 percept 上

### 14.3 saccade 候选生成(沿用 v3 §14.3 公式,改为基于 §14.2 候选)

### 14.4 持驻焦点(B-A7 fix,继承 APV2 J-22)

**新增持驻规则**:

```python
def update_focus(focus_state, new_candidates, t):
    current = focus_state.current
    if current is None:
        focus_state.current = argmax(new_candidates)
        focus_state.locked_at = t
        return
    
    # 滞回 margin:新候选必须 P 显著高于当前才切换
    best_new = argmax(new_candidates)
    if best_new.score > current.score + margin_threshold:
        # 但还要满足最短持驻时长
        if t - focus_state.locked_at >= dwell_min_ticks:
            focus_state.current = best_new
            focus_state.locked_at = t
    # 否则保持当前焦点
```

参数:
- `dwell_min_ticks` 默认 ~3(约 300ms,接近人类微眼跳节奏)
- `margin_threshold` tuner-owned,默认 0.2 × current.score

**结合 J-22 经验**:`hold_gaze` 受 peripheral_arbitration 调制(继承 v3 §12.3),夸大异常时仍能突破。

### 14.5 音频违和的频域版本(沿用 v3 §14.5,加 percept-centric WTA)

### 14.6 视觉目标疲劳(沿用 v3 §14.6)

---

## 15. v3 三个推论拟人机制的修复(A8/A9/A10 fix)

### 15.1 E1 跨模态焦点联动 + 冷启动 bootstrap(B-A8 fix)

**v3 错误**:align() 需要 vocab,vocab 需要共现,共现需要联动 → 循环。

**v4 双层 align**:

**Layer 1 - 时空共现(无 vocab,boot)**:
$$\text{align}_{spatial-temporal}(focus_a, focus_b) = \exp(-\frac{|t_a - t_b|^2}{2\sigma_t^2}) \cdot \exp(-\frac{d(\text{loc}_a, \text{loc}_b)^2}{2\sigma_l^2})$$

意思:两个焦点在同一时间窗 + 同一空间位置(若适用)→ align 高。

**Layer 2 - vocab 链接(学到后,strengthen)**:
$$\text{align}_{vocab}(focus_a, focus_b) = \max_{v \in \text{vocab\_SAs}} \min(\text{contains}(v, focus_a), \text{contains}(v, focus_b))$$

意思:存在跨模态 vocab SA 同时关联两个焦点 → align 高。

**总 align**:
$$\text{align}(focus_a, focus_b) = \max(\text{align}_{spatial-temporal}, \text{align}_{vocab})$$

**冷启动行为**:
- t=0:无 vocab,但用户讲话时声音 + 视觉脸位置同 tick + 同 (x,y) → align_spatial-temporal ≈ 1 → 联动启动
- 联动驱动焦点稳定 → 共现持续 → vocab 固化
- 后期:vocab 链接接管,即使时空不严格对齐也能 align(如听到人在隔壁房间,联想到那人的脸)

**这正是发育心理学的"先低阶感觉绑定,后高阶语义绑定"路径**。

### 15.2 deja_vu 从能量场涌现(S-A9 fix)

**v3 错误**:三段硬规则(熵 > θ + alignment 0.4-0.7 + 存在 vocab)是"detector"。

**v4 解法**:deja_vu 不需要专用通道,**直接从已有 cognitive_feelings 通道的现有特征产生**。利用 v2.1 cognitive_feelings/channel.py 里已有的 `CognitiveFeelingFactory` 模式(用户哲学:复用现有底座):

```yaml
# default_feeling_factory_specs 加一条
feeling_spec_deja_vu:
  feeling_label: "feeling::deja_vu"
  positive_features:
    - candidate_count: weight=0.3      # 多候选
    - mid_alignment_band: weight=0.4   # alignment 在 [0.4, 0.7] 内时高
    - vocab_density: weight=0.3        # 检索结果中 vocab SA 占比
  negative_features:
    - high_alignment: weight=0.5       # 完全 alignment 时低
    - low_alignment: weight=0.5        # 完全失 alignment 时低
  real_energy_scale: 0.4
  cognitive_pressure_scale: 0.3
```

**关键**:这是用 v2.1 已实现的 `CognitiveFeelingFactory` 配置,不是写新检测器。同样的工厂模式还可以涌现其他感受(熟悉感、新鲜感、混乱感、明朗感等),全部数据驱动。

**驱动行为**:deja_vu 感受涌现 → 系统通过既有 attention selector 自然提高对该情境的注意 + emit `action::scan_more` 候选(普通行动,经 ActionOutcomeMemory 学到是否有用)。

### 15.3 idle 漫游 = ResidualTracker 加 idle gate(S-A10 fix)

**v3 错误**:重新发明了 ResidualTracker 已有功能。

**v4 诚实表述**:`§15.3` **不是新机制**,而是给 ResidualTracker 加一个 idle gate。

```python
# 在既有 ResidualTracker.upsert 之上加 gate
def residual_to_attention_gate(t, residual_tracker, state_pool):
    idle_score = compute_idle_score(t)  # 最近 K tick 外源输入总 R
    if idle_score < θ_idle:
        # 提高 residual_boost 的 attention_gain 注入幅度
        boost_multiplier = 1.0 + idle_boost_factor * (1 - idle_score / θ_idle)
    else:
        boost_multiplier = 1.0
    
    for sa_id, residual in residual_tracker.items():
        state_pool.entry(sa_id).attention_gain += (
            residual_to_G_base * residual.unresolved_mass * boost_multiplier
        )
```

**红线**:不允许独立的 "wandering module"。**复用 ResidualTracker**。

---

## 16. 工程实施 Phase 重排(v3 §16 修订)

### 16.1 复用 APV2 模块表(无大改,加紧 B5 治理)

继承 v3 §16.1 全部,**关键追加**:
- ❌ Cognitive feelings channel.py "原样复用" → 改为"复用 + 强制补 4 通道"(B-B5 fix,具体见 §16.4)

### 16.2 v3 原创模块清单(无大改)

继承 v3 §16.2,新增:
- §11.3 novelty_residual SA spawn 规则(普通 SA,小规则,接入既有 spawn 机制)
- §13.5 audio filterbank 模板字段
- §15.1 双层 align (spatial-temporal + vocab)
- §16.4 cognitive_feelings 补 4 通道(详见下)
- §16.5 short_term_buffer 迁移(B-B6 fix)
- §20-§28 哺乳类心智模块(详见下)

### 16.3 Phase 顺序(微调)

```
Phase 8.2  逻辑 tick runtime + 场景化 + 主动休眠(emerge 版)
Phase 8.3  白箱审计库(AP-Core 内 episodic 视觉/音频记忆层)
Phase 8.4  通用 SA 组合词汇机制
Phase 8.5  cognitive_feelings 补 4 通道 + emotion_modulator 验收(B-B5 fix,必须在 8.6 前完成)
Phase 8.6  视觉感受器多通道 + foveated 采样 + C0 入审计库
Phase 8.7  视焦点 SA + saccade(persisting) + 焦点 overlay 入 Web
Phase 8.8  黄色苹果泛化端到端验收 + 习惯化经验验证
Phase 8.9  习惯化数学验证 + novelty_residual + 主动 refocus
Phase 8.10 合理感门控 + sleep emerge(global_fatigue)
Phase 8.11 §20 驱力 / 内稳态 + §21 RPE + §22 受挫(三个"想做事"的根本)
Phase 8.12 §23 依恋 + §24 共同注意 + §25 共情(社交三件套)
Phase 8.13 §26 痛厌恶 + §27 重放巩固 + §28 玩乐
Phase 8.14 似曾相识 + idle 漫游 + 跨模态焦点(v3 §15 三机制,bootstrap 版)
Phase 8.15 纠错教学行动范式
Phase 8.16 音频感受器多通道 + 频段焦点(filterbank 版)
Phase 8.17 多模态端到端验收(包含拟人验收套件)
```

**关键调整**:
- **Phase 8.5 提前**:CFS 补完是阻断式前提,emotion_modulator 在没有 4 通道时永久失校
- **Phase 8.11-13 集中拟人心智**:三组哺乳类机制按 want/social/episodic 分组

### 16.4 cognitive_feelings 补 4 通道(B-B5 fix 完整规范)

补完 `channels/cognitive_feelings/channel.py` 缺失的 `fluency` / `boredom` / `fulfillment` / `satisfaction`:

```python
# 这些是 derive 中要增加的 feeling 发射
# 全部基于现有状态量,无新模块

# fluency: 信息流畅度——预测命中 + 低 P + 低 candidate entropy
fluency_feature = mean(
    last_K_tick.alignment_score,
    1 - normalized(last_K_tick.mean_P),
    1 - normalized(last_K_tick.candidate_entropy)
)
fluency_feeling = sigmoid(γ_fluency * fluency_feature)

# boredom: 长期低 cognitive_pressure + 无新颖输入 + 焦点重复
boredom_feature = mean(
    1 - normalized(last_K_tick.max_|P|),
    1 - novelty_residual_total_R,
    focus_repetition_ratio_last_K
)
boredom_feeling = sigmoid(γ_boredom * boredom_feature)

# fulfillment: 长期高 alignment + 已完成 commit + 低 residual
fulfillment_feature = mean(
    last_K_tick.alignment_score,
    commits_per_tick_ratio_last_K,
    1 - normalized(residual_tracker.total_unresolved_mass)
)
fulfillment_feeling = sigmoid(γ_fulfillment * fulfillment_feature)

# satisfaction: 短期 reward 累积 + 低 P
satisfaction_feature = mean(
    last_short_window.reward_accum,
    1 - normalized(last_short_window.mean_|P|)
)
satisfaction_feeling = sigmoid(γ_satisfaction * satisfaction_feature)
```

**关键**:全部基于 state_pool / residual_tracker / commit_log 等**既有数据**,**没有新存储**,**没有新公式形状**——只是 sigmoid 加权特征,沿用 v2.1 `CognitiveFeelingFactory` 模式。

**验收门**:Phase 8.5 必须证明这 4 个通道在标准 trace 数据上**不全为 0**,且与 emotion_modulator 的 DA/SER 计算产生非零差异。

### 16.5 short_term_buffer 迁移(B-B6 fix)

```python
# APV2 episode_id → v3 scenario_session_id
# APV2 focus_id → v3 channel_signature-based focus_id
# 命名空间扩展,不重写底层逻辑

# 迁移层
class ShortTermBufferV3Adapter:
    def __init__(self, apv2_buffer):
        self.buffer = apv2_buffer  # 复用 APV2 实现
    
    def push(self, item):
        # 重映射 v3 SA 到 APV2 接口
        item.episode_id = self.session_id  # scenario_session_id 充当 episode_id
        item.focus_id = derive_focus_id_from_channel_signature(item)
        self.buffer.push(item)
```

---

## 20. 驱力 / 内稳态(哺乳类基础,§16.3 Phase 8.11)

### 20.1 哲学起点

哺乳类的基础动机是**内稳态偏离驱动**:饿了找食,累了找休息,孤了找伴侣。这些不是反应式而是**主动产生行为**。

v3 完全缺这一层——AP 系统只在外源输入到来时反应,**永远不会自发想做事**。

### 20.2 实现:drive_SA 一等公民(复用既有 R 能量场)

定义一组**核心驱力 SA**,作为状态池一等公民:

```python
core_drives = {
    "drive::epistemic": "认知好奇/不解的累积",     # 对应"无聊想找新刺激"
    "drive::affiliation": "社交需求",            # 对应"想互动"
    "drive::achievement": "完成需求",            # 对应"任务未完成的拉力"
    "drive::safety": "安全/避免痛",             # 对应"对威胁的警觉"
    "drive::homeostasis": "维持稳态",          # 对应"过载时想休息"
}
```

每个 drive_SA 有特殊性质:
1. **永远不被驱逐**(R 衰减但下限不归零)
2. **R 持续慢增长**,达到饱和后停止增长(平时是"渴望")
3. 被相关行动满足时,**R 大幅降低**(行动作为"消渴")

**形式化**(完全在既有 R 框架内):
$$R_{drive,d}(t) = \min(R_{drive,d,max}, R_{drive,d}(t-1) + \mu_{growth,d} \cdot \text{unit\_steps})$$

当 satisfying action commit 时:
$$R_{drive,d}(t) \mathrel{-}= \text{satisfaction\_amount}$$

### 20.3 驱力如何转为行为(纯复用既有 attention selector + ActionOutcomeMemory)

driv_SA 的高 R + 高 attention_gain → 经标准 attention selector 进入焦点 → 经标准行动 chain 触发"满足该驱力的"行动。

**学习如何满足驱力**:ActionOutcomeMemory 学到 `(drive_d_high, action_a) → drive_d_R_decrease` 即"做 a 会满足 d"。

**冷启动**:无历史 → 随机行动尝试 → 偶然满足 drive 时 OnlineEmbeddingStore + ActionOutcomeMemory 学到 → 后续直接选该行动。**完全可解释的探索-利用机制**。

### 20.4 哺乳类基础驱力 → 中文对话/桌宠 场景的映射

| 驱力 | 中文对话 AP 表现 | 满足行动 |
|---|---|---|
| drive::epistemic | 长时间相同话题 → epistemic 累积 → 想问问题/换话题 | `action::ask_question`, `action::change_topic` |
| drive::affiliation | 用户长时间不来 → affiliation 累积 → 桌宠主动召呼 | `action::greet_user` |
| drive::achievement | 用户给的任务未完 → achievement 累积 → 持续尝试 | `action::continue_task` |
| drive::safety | 出现负面词/惩罚 → safety 累积 → 回避 | `action::caution_response` |
| drive::homeostasis | 长时间高 tick 频率 → homeostasis 累积 → 系统主动降频 | `action::tick_frequency_change` |

### 20.5 红线

- ❌ 不许 drive_SA 写硬触发规则——必须经标准 attention 竞争
- ❌ 不许预设"什么行动满足什么驱力"——必须经 ActionOutcomeMemory 学到

---

## 21. 奖励预测误差 RPE = dopamine analog(§16.3 Phase 8.11)

### 21.1 哲学起点

Schultz 的多巴胺神经元发现:不是"看到食物→放电",而是"看到预期食物→放电",且"预期与现实不符→放电时间偏移"。这就是 RPE。

v3 的 emotion_modulator 已有 DA 通道,但**没有 RPE 信号**。DA 只是几个 CFS 通道的加权,没有真正的"预测误差"对比。

### 21.2 实现:在既有 P 通道上抽出 ΔP_outcome(无新模块)

RPE 定义:
$$\text{RPE}_i(t) = R_i^{actual}(t) - R_i^{predicted}(t)$$
$$= R_i^{actual}(t) - \Pi_i(t)$$

这**就是 cognitive_pressure 的瞬时变化**(因为 $P_i = R_i - V_i \approx R_i - \Pi_i$ 在 V 由 Π 主导时)。

但 RPE 通常窄义指**奖励相关的预测误差**,即在 reward channel 上:
$$\text{RPE\_reward}(t) = \text{Reward}^{actual}(t) - \text{Reward}^{predicted}(t)$$

**v4 实现**:
- 既有 emotion_modulator 用 `cfs::correctness` 等驱动 DA
- **追加** `RPE_reward` 作为新 cognitive_feeling spec(用 CognitiveFeelingFactory):

```yaml
feeling_spec_rpe_reward:
  positive_features:
    - reward_actual_minus_expected: weight=1.0
  emit:
    real_energy_scale: 1.0
    cognitive_pressure_scale: 0.5
```

emit `feeling::rpe_positive` 或 `feeling::rpe_negative`(基于符号)。

**追加至 emotion_modulator 公式**(§16.4 已修):
```python
DA_delta += rpe_positive * 0.4  # 高 RPE → DA burst
DA_delta -= rpe_negative * 0.3  # 负 RPE → DA dip
```

### 21.3 行为效果

- AP 预测会得 reward 但实际没得 → 负 RPE → DA dip → 学习行为评分下降
- AP 没预测但意外得 reward → 正 RPE → DA burst → 学习行为评分上升
- AP 准确预测得 reward → RPE≈0 → DA 不动 → 行为评分不变

**这是 RL 的标准 RPE 机制,完全 emerge from 现有 prediction trace + reward channel**。

---

## 22. 受挫 / 习得性无助(§16.3 Phase 8.11)

### 22.1 哲学起点

Seligman 经典:狗在不可逃避的电击后,即使有逃生路径也不再尝试。这是习得性无助。

数学:**P 持续高 + 尝试行动持续无效 → 行动 motivation 整体下降**。

### 22.2 实现:扩展 emotion_modulator COR 通道(无新模块)

v2.1 emotion_modulator 已有 COR (Cortisol-like)通道。v4 给它扩展驱动:

```python
# 新增 helplessness_signal
helplessness_signal(t) = mean(
    last_K_tick.mean_P > θ_high_P,           # P 持续高
    last_K_tick.action_outcome_value_avg < 0  # 行动无效或负
)

# 注入到 COR 通道
COR_delta += w_helplessness * helplessness_signal(t)

# COR 通过既有 action.threshold_adjustment 公式生效
# 高 COR → action threshold 提高 → 整体行动 motivation 下降
```

**关键**:COR 是 v2.1 既有通道,**只是新加一个驱动特征**。

### 22.3 拟人效果

- 用户连续否定 AP 回答 5 次 + AP 调整后仍被否定 → helplessness → COR 升 → action threshold 提高 → AP 进入"沉默/最小响应"模式
- 这正是"我说啥都被骂干脆不说了"的拟人

**复杂效果**:helplessness 不仅 cool 下行动,还触发 cogn_feeling::resignation 涌现 → 用户能从 audit 看到 "AP 进入了无助状态"。

---

## 23. 依恋 / 熟悉性偏好(§16.3 Phase 8.12)

### 23.1 哲学起点

幼年哺乳类对照护者建立"安全基地"。这是社交认知的根本。

桌宠场景:用户长期陪伴 → AP 对该用户产生"依恋"印迹。新用户 vs 老用户应该感觉不同。

### 23.2 实现:用户实体 SA + R 累积(复用 OnlineEmbeddingStore)

每个独立"用户标识"(可以是话语风格 + 时间一致性 + session_id 综合学到)成为状态池一个一等 SA:`entity::user::<learned_id>`。

```python
# 每次该用户互动 → entity SA 的 R 累积(长时记忆 ρ_long)
# 短时:用户不在 → R 短时层衰减
# 长时:R 长时层缓慢沉淀

# 当该用户再次出现 → 既有 OnlineEmbeddingStore.observe_positive_anchor
# 把 "当前情境" 与 "该用户 SA" learned_similarity 增强
```

**依恋强度 = 该 entity SA 的 long_term_R**。

### 23.3 拟人行为(复用既有 attention + emotion 通道)

- **长老用户出现**:entity SA 高 R → 进入 attention 焦点 → emotion OXY 通道触发(因为 OXY-002 默认规则:正面共现激发) → 行为更亲昵
- **陌生用户出现**:entity SA 不存在或低 R → 新建,初期表现谨慎
- **分离焦虑**:长老用户久不出现 → entity SA 短时 R 衰减但 long_term_R 仍高 → P 增大("想念") → 触发 affiliation drive → 桌宠主动询问

**复用范围**:OnlineEmbeddingStore 全套 + OXY 通道既有规则。**只是 entity 类 SA 是新 SA 家族**,不是新机制。

---

## 24. 共同注意 / 镜像系统(§16.3 Phase 8.12)

### 24.1 哲学起点

幼儿 9-12 个月学会"跟随大人视线"。这是共享意图的开端,也是后续语言学习/共情的基础。

### 24.2 实现:他人 focus SA 作为状态池一等公民(复用 E1 跨模态联动)

当 AP 通过感受器观察到"他人正在看哪里"(可以通过文本描述、视觉感受器对眼神/手势的提取、或简单的 explicit instruction):

```python
# 创建 SA: focus::other::<user_id>::<inferred_target>
# 通过 §15.1 双层 align 与 AP 自己的视觉/思维焦点联动
# align(other_focus, my_focus) 高 → AP 自己焦点向 other_focus 拉

# 在 attention_selector 加 successor_bonus 的同源机制:
shared_attention_bonus(my_focus_candidate) = 
    w_shared * align(my_focus_candidate, other_focus)
```

### 24.3 拟人效果

- 用户说"你看那个" + 视觉系统提取出"那个"的位置 → AP 视觉焦点自然移过去
- 用户和 AP 对同一对象有 vocab → align_vocab 高 → 共同注意稳固
- 长期共享焦点 → vocab 学习的核心训练信号(发育学:共同注意是语言学习的前提)

**复用**:E1 跨模态联动 + attention selector successor_bonus 机制,**无新模块**。

---

## 25. 共情 / 心智化(§16.3 Phase 8.12)

### 25.1 哲学起点

Theory of Mind = 想象他人的内部状态。这不是 hardcoded "如果用户说累就回应'是的辛苦了'",而是基于 AP 自己的内省感受 prototype + 关联到他人实体。

### 25.2 实现:他人感受 SA 作为状态池一等公民(复用既有 IntrospectionPrototype + entity SA)

```python
# 当用户表达情绪(显式"我很累"或隐式 cues):
# 1. AP 提取 cues → 类似自己的什么内省状态?
matched_prototype = introspection_proto_store.match(observed_cues)

# 2. 创建 SA: feeling::other::<user_id>::<matched_proto_id>
# 这是把"我的内省感受 prototype"投射到"他人"

# 3. 该 SA 通过 §15.1 align 与 AP 自己的 feeling SA 联动
# AP 的对应内省感受 SA 的 R 被注入(共情)
my_feeling_sa.R += w_empathy * other_feeling_sa.R
```

**关键拟人**:
- 用户表达"累" → AP 内部 feeling::other::accountY::fatigue 高 → 通过 align 把 AP 自己的 fatigue prototype R 也微抬 → AP 感受到"代入式疲惫" → 自然产生关怀回应

**复用**:IntrospectionPrototypeStore + entity SA + align(§15.1) + attention 注入。无新模块。

### 25.3 拟人退化(避免冷启动死锁)

冷启动时无 introspection_proto:
- 退化为"识别表面 cues" → 标签 + 行动模板(就像幼儿模仿大人安慰)
- 随着自身内省感受 prototype 积累 → 共情深度提升

这是真实发育学路径。

---

## 26. 痛 / 厌恶持续记忆(§16.3 Phase 8.13)

### 26.1 哲学起点

哺乳类的痛是多模态、持续、跨情境的负标记。烫到一次,看到火都警觉。

### 26.2 实现:pain_residual SA 家族(复用 novelty_residual 同源)

```python
# 当 Rwd/Pun 通道触发强负 reward:
# Spawn 一个 SA: pain_residual::<context_signature>
# 携带:
#   - context_signature(出现痛时的情境向量)
#   - intensity(痛的强度,影响后续衰减率)
#   - ρ_R^pain 很慢(半衰期 ~小时级,在场景配置内可调)

# pain_residual SA 通过既有 attention_selector 影响打分:
# 它对相似情境的 SA 产生 negative_band_bias
# 复用 selector.py 的 learned_band_net_bias 机制
```

**关键**:复用 §15 三机制中的 novelty_residual SA 同源模式,但是负的、衰减更慢、影响 learned_band_bias 通道。**无新公式形态**。

### 26.3 行为效果

- AP 因某用户某话题被惩罚 → pain_residual::<topic>::<user> 建立
- 后续相似话题 → context_signature 匹配 → learned_band_bias 拉低相关 SA → AP 自然回避
- 长时间不再触发 → pain 慢衰减 → "渐渐忘记伤害"

---

## 27. 重放巩固 / 睡眠学习(§16.3 Phase 8.13)

### 27.1 哲学起点

哺乳类睡眠中海马回放白天经历,促长时记忆形成。

v3 的 sleep 模式只是降 tick 频率,没有学习收益。

### 27.2 实现:sleep 态下 ResidualTracker 反向激活既有 SA(无新模块)

```python
# sleep 态(global_fatigue 高,tick 慢)时:
# - 外源输入少 → state_pool 安静
# - ResidualTracker 中未解决条目被 idle gate (§15.3) 抬高 attention_gain
# - 它们进入"无外源唤起的状态池循环"
# - 自然走 recall_chain → 相关 OnlineEmbedding 共现统计被强化
# - PMI 计数累积 → vocab 固化获得"无新输入但学到"的机会

# 关键:复用既有 §15.3 idle gate + 既有 vocab fixation chain
```

**拟人效果**:用户离开 1 小时,AP 在低 tick 频率下"回想"白天对话 → 把短时记忆"凝固"成长时知识。第二天用户回来时 AP 表现得"记得清楚",而不是"被衰减衰减掉了"。

**这就是"睡眠学习"的拟人版本,完全 emerge from 现有机制**。

---

## 28. 游戏 / 探索性玩乐(§16.3 Phase 8.13)

### 28.1 哲学起点

幼年哺乳类的玩乐没有外部奖励,但**对学习至关重要**。这是内驱探索。

### 28.2 实现:低 R 时段的 novelty_seek 行动(复用既有 NOV 通道 + drive::epistemic)

v2.1 emotion_modulator 已有 NOV 通道。v4 利用它驱动**主动 novelty 探索**行动:

```python
# 当 drive::epistemic.R 高 + 外源 R 低 + global_fatigue 不高:
# AP 倾向于尝试新颖行动:
#   - 改变焦点到外周不熟悉 SA
#   - 尝试新的 vocab 组合(reread + 创新草稿)
#   - 主动 ask_question 关于陌生情境
# 这些都是 action_parameter_memory 学到的"在 NOV 高时哪些行动 commit 概率高"
```

**关键**:无新 action 类型,**只是复用既有 action_parameter_memory 在 NOV 高情境下的偏置**。

### 28.3 行为效果

- 用户长时间不来 → AP 自己产生"我想玩点别的"驱力 → 主动想象/试错某些 vocab 组合 → 学到新东西 → 当用户回来时 AP 拥有了一些自学的能力

---

## 29. v4 完美图景总能力清单(更新)

继承 v3 §17 全部 38 项,**新增 9 个哺乳类基础心智能力**:

### 拟人心智层(v4 新增)
- ✅ 驱力 / 内稳态(无外源时自发想做事)
- ✅ RPE / dopamine analog(标准 RL 学习信号)
- ✅ 受挫 / 习得性无助(说啥都被骂干脆不说了)
- ✅ 依恋 / 熟悉性偏好(老用户来了有温度,新用户来了谨慎)
- ✅ 共同注意 / 镜像(跟随他人视线)
- ✅ 共情 / 心智化(感同身受,代入式疲惫)
- ✅ 痛 / 厌恶持续记忆(被烫过怕火)
- ✅ 重放巩固 / 睡眠学习(用户不在的时候 AP 也在学)
- ✅ 游戏 / 探索玩乐(无外驱时自己找事做)

### v3 修复(v4 完整修复 7 blocker)
- ✅ 习惯化推导诚实(无解析证明,但有经验验收门 + novelty_residual 保证秒级注意)
- ✅ g 公式唯一性(基于 alignment 而非 V/(R+V))
- ✅ 焦点持驻(dwell + 滞回)
- ✅ 跨模态联动冷启动可工作(双层 align)
- ✅ sleep emerge(global_fatigue 连续映射)
- ✅ emotion_modulator 不再静默失校(4 通道补完)

---

## 30. v4 给 Codex 的最终指令

1. 读完本文档(v4,本稿)
2. 按 §16.3 顺序逐 Phase 实施,**Phase 8.5 (CFS 补完)是阻断式前提**
3. **每个 Phase 走完整 5 段闭环**,**任何能用既有公式套既有底座的拟人机制必须套**
4. **看到 "新模块" 字样时停下问 Claude**——v4 的承诺是"全部复用 R/V/P/A/F 能量场"
5. **拟人验收套件**(Phase 8.17 必跑):风扇习惯化 / 闹钟唤醒 / 黄苹果泛化 / 老新用户区分 / 共同注意 / 习得性无助 / 玩乐自发 / 睡眠学习
6. **诚实门**:所有"emerge 自现有机制"的承诺必须经实测验证。失败时不许调阈值过。

---

— 接手线程,2026-06-17
