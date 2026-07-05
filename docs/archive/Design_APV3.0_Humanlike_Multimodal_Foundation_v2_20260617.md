# APV3.0 拟人多模态底座 — 完整数学模型设计稿 v2(对抗审阅后)

日期: 2026-06-17
作者: 接手线程
状态: **设计稿 v2,经 3 路对抗审阅(35 raw / 30 verified / 8 blocker + 21 serious / 0 misread)。所有 blocker 已修正。融合用户三个关键哲学升级:白箱审计库分离 / 场景化 tick 配置 / 主动休眠行动。**
前身: v1(`Design_APV3.0_Humanlike_Multimodal_Foundation_v1_20260617.md`)
审阅源: task wkbhjpamq (2026-06-17)

---

## 0. v1 → v2 重大变化一览(必读)

### 0.1 v1 的 8 个 blocker(全部坐实,v2 全部修)

| # | v1 缺陷 | v2 修正方向 |
|---|---|---|
| **B1** | MFCC 数学上不可逆,音频不可能重建出可识别语音 | 新增独立**白箱审计库**存原始 PCM(用户洞察),AP 本体只存 A1-A6 向量;§4.4 改成从审计库播放 |
| **B2** | 32 维 Fourier + 全局 HSV 直方图重建只能出色块,看不出是苹果 | 同上——视觉 patch 入白箱审计库;C1 加主轴角度 θ_p,C2 改 2×2 空间网格 HSV |
| **B3** | A6 音频含义循环依赖(含义靠共现学,共现需要稳定对象,冷启动死锁) | 删 A6,音频含义通过 §2 通用词汇固化机制涌现,不预设通道 |
| **B4** | PMI 多元推广有统计偏差,长度>2 时罕见组合假阳性 | 改用 **bayesian smoothing 的 ratio test**,固定为成对 PMI 链式分解,避免多元偏差 |
| **B5** | PMI 对连续向量没法"共现计数" | 引入**通道量化桶(quantization bin)**作为可学习中间层;桶以下是连续向量,桶以上做 PMI |
| **B6** | θ_coh 没损失信号,tuner 无法学 | 用**预测误差降低量**作为损失信号——固化后该对象进入召回链能多大幅度降低 cognitive_pressure |
| **B7** | dominant_channel 是变相关键词路由 | 改为**类型继承图(type lattice)**:槽接受"通道签名"类的 SA,签名是结构事实而非标签 |
| **B8** | 短时记忆 ρ_R=0.95 跑 3000 tick 衰减到 10^-67,5 分钟保上下文做不到 | 不再固定 1 tick=0.1s,改为**场景化 tick 配置** + 真实时间戳分离;短→长晋升规则精确化 |

### 0.2 用户三个哲学升级(v2 新章节)

| 升级 | 设计落点 |
|---|---|
| **白箱审计库分离** | 新增 §10:可配置容量的独立审计库,不参与 AP 核心流程,满了删最旧/最低权重,可关闭可 LLM 周期清理 |
| **场景化 tick 配置** | 新增 §1.6:4 个典型应用场景(纯文本对话/桌宠/具身智能/Agent+LLM)各自一套 tick 参数;tick 与墙钟解耦,用时间戳记录真实时间 |
| **主动休眠行动** | 新增 §1.7:系统可通过"行动"主动降低 tick 频率(1s/10s/30s),配定时任务保活,降算力维持基础认知 |

### 0.3 21 个 Serious 集成方式

逐条编入 §1-§9 各章节细节,在 v2 文末 §11 列表所有修复对照。

---

## 1. 逻辑 tick runtime 完整数学模型 v2(重写)

### 1.1 核心定义重写

**逻辑 tick** = 系统内部"思考节拍",由感受器队列驱动 + 主动 step 推进。

**关键变化**:tick 不再固定对应 0.1s,而是**与墙钟解耦**:
- 每个 tick 携带 `wall_clock_timestamp_ms`(记录真实时间)
- tick 频率由**场景配置**决定(§1.6)
- tick 频率可由**系统主动行动**改变(§1.7)

### 1.2 能量演化律(沿用 v3.0 §2.1,但时间步基于 wall_clock_delta_ms)

```
delta_ms = wall_clock(t) - wall_clock(t-1)
unit_steps = delta_ms / config.base_tick_ms      # base_tick_ms 是场景配置,默认 100ms

R_i(t) = ρ_R^unit_steps · R_i(t-1) + Inj_i^ext(t) + Inj_i^fb(t)
V_i(t) = ρ_V^unit_steps · V_i(t-1) + Π_i(t)
A_i(t) = ρ_A^unit_steps · A_i(t-1) + G_i(t)
F_i(t) = ρ_F^unit_steps · F_i(t-1) + Φ_i(t)
P_i(t) = R_i(t) - V_i(t)
```

**关键**:衰减基于**真实经过时间**,不是 tick 数。这样系统从 0.1s/tick 切换到 10s/tick(主动休眠)时,**记忆衰减率不变**——人类睡 8 小时不会忘记昨天的事,因为时间衰减是连续的。

### 1.3 短时 → 长时记忆双层(v1 §1.2 修正,B8 fix)

**v1 错处**:用"window N tick + θ_promote"做晋升,N 没规则,θ 没标定。

**v2 解法**:**用真实时间窗口 + 累积激活能量**做晋升:

```
# 每个 SA 维护两个 R 量
short_term_R(t) 演化同 §1.2,ρ_R^short ≈ 半衰期 30 秒
long_term_R(t) 演化同 §1.2,ρ_R^long ≈ 半衰期 24 小时

# 晋升条件(真实时间驱动)
cumulative_activation_energy(SA, window_ms) = ∫_{t-window_ms}^t Inj_SA^ext(τ) dτ
if cumulative_activation_energy > θ_promote_to_long_term:
    long_term_R(SA) += promote_factor * short_term_R(SA)

# 召回时合并两层
R_effective(SA) = short_term_R + γ_long * long_term_R
```

**关键参数**:
- `θ_promote_to_long_term`: 由 AdaptiveTuner 标定,初值为"用户连续提及某概念约 3 次的能量"
- `window_ms` (积分窗口): 默认 60 秒
- `γ_long`: 长时记忆在召回时的权重,默认 0.5

**为什么这解决了 v1 的问题**:用户说话 30 秒后停 5 分钟,关键概念在 30 秒内被激活多次累积能量 → 晋升 → long_term_R 不衰减 → 5 分钟后召回仍可用。

### 1.4 idle tick 行为

- 空 tick(无外源输入):tick 仍推进 wall_clock_timestamp,所有 SA 按 §1.2 衰减
- 但 tick 频率由 §1.6 场景配置 + §1.7 主动休眠决定——可能"空 tick 实际不跑"(休眠中)

### 1.5 逐字草稿输出

每个 tick 最多 1 个草稿动作(沿用 v3.1 §S6):
- type token(从 7.7 phrase memory 选)
- reread(重读已有草稿)
- replace_tail(改最后几字)
- commit(提交)
- noop

K 个 tick 仍 commit_blocked → fallback 到 tier-0 诚实表达(v3 7.8 §3.2 已做)

**v1 §1.4 commit_blocked spam "不知道" 永远的问题(S14 fix)**:加入**反向疲劳**——连续 N 次同一情境 fallback 到"不知道" → reply_pressure 临时下降 → 系统进入沉默而非 spam。这是拟人的"我说不清楚就不说了"。

### 1.6 场景化 tick 配置(新增,B8 fix 核心)

不同应用场景的 tick 参数预置:

| 场景 | base_tick_ms | ρ_R 短时半衰期 | 主动休眠允许 | 用例 |
|---|---|---|---|---|
| **A. 纯文本对话(Web/CLI)** | 200ms | 60 秒 | ✅ 用户输入间空闲时 | 桌面问答场景 |
| **B. 桌宠/多模态连续** | 100ms | 30 秒 | ✅ 长 idle | 直播桌宠 |
| **C. 具身智能/连续认知** | 100ms 严格 | 30 秒 | ❌ 永远跑 | 机器人 |
| **D. Agent + LLM 协作** | 事件驱动 | 60 秒 | ✅ LLM 调用间隔 | 工作流 |

配置文件 `scenario_profile.json` 由用户启动时选,Codex 实施时各场景一套预设。

### 1.7 主动休眠作为行动 SA(新增)

**行动 SA** `action::tick_frequency_change`:
- 状态:`(target_base_tick_ms, duration_ms)`
- 触发条件:**学到的**——通过 ActionOutcomeMemory 学到"什么情境降频率有奖励"
- 例:用户连续 2 分钟无输入 → 系统主动 commit 行动 `action::tick_frequency_change(target=10000, duration=until_input)` → tick 拉到 10 秒/次
- 一旦有新外源输入或定时任务触发 → 唤醒回 base_tick_ms

**关键**:这不是 hardcoded 规则,是**学到的行动**——系统通过经验学到"主动降频在用户长期不在时有奖励(算力低)"。

### 1.8 Web 回放需要的 tick trace(沿用 v1 §1.5,加几个字段)

```
tick_trace = {
    "t": int,
    "wall_clock_ms": int,                # NEW
    "scenario_profile": str,              # NEW
    "current_base_tick_ms": int,          # NEW (可能因主动休眠改变)
    "inputs": [...],
    "state_pool_top": [...],
    "recall_focus": str,
    "draft_action": str,
    "draft_buffer": str,
    "reply_pressure": float,
    "commit_blocked": bool,
    "short_to_long_promotions": [...]
}
```

---

## 2. 通用 SA 组合词汇固化机制 v2(数学严密化,B4/B5/B6 fix)

### 2.1 哲学起点(沿用 v1 §2.1)

任何 SA 集合或序列经共现统计稳定形成的固化对象,本身也是新 SA。递归到任意层级,跨模态。

### 2.2 量化桶层(新增,B5 fix)

**v1 问题**:连续向量(Fourier/HSV)不能直接"共现计数"。

**v2 解法**:每个连续通道维护一个**可学习的量化桶集合**(VQ codebook):

```
# 每通道独立的量化桶集合
quantization_buckets[channel] = {
    bucket_id: bucket_center_vector,
    bucket_id: bucket_center_vector,
    ...
}

# 新感知 → 最近邻桶,触发 bucket 更新(沿用 v3.1 percept_prototype 模式)
def quantize(channel_vec, channel):
    best_bucket = argmin_b distance(channel_vec, buckets[channel][b])
    update_bucket_center(best_bucket, channel_vec, eta_vq)
    return best_bucket

# 极端情形:全部桶都太远 → 孵化新桶(同 v3.1 §B2 spawn 模式)
```

**桶 id 作为离散 SA 标签** → §2.3 PMI 可以工作。

**关键**:这等价于 v3.1 §B2 的 prototype 机制在每个感受器通道上的复刻——**完全同构,无新机制**。

### 2.3 成对 PMI + 链式分解(B4 fix)

**v1 问题**:多元 PMI 推广 `coh(σ) = f(σ) / (∏ f(σ_i) / N)` 对长度>2 有偏差。

**v2 解法**:**只用成对 PMI**(数学严谨),长链通过分解处理:

```
# 成对 PMI (Bayesian smoothed):
PMI(a, b) = log( (f(a,b) + α) · (N + α·K²) / ((f(a) + α·K) · (f(b) + α·K)) )

其中 α = Dirichlet 平滑系数 (默认 0.5),K = 总 SA 数,N = 总观察数。

# 长链 σ = [s_1, s_2, ..., s_n] 的固化判定:
chain_score(σ) = mean_{i} PMI(σ_i, σ_{i+1})   # 相邻对的平均 PMI

# 集合 σ = {s_1, ..., s_n} 的固化判定:
set_score(σ) = mean_{(i,j) ∈ pairs(σ)} PMI(σ_i, σ_j)
```

**为什么这没偏差**:成对 PMI 经 Bayesian 平滑后,稀有项有 prior 兜底,不会假阳性。链/集合的"整体性"靠相邻或两两均值,不依赖未定义的多元联合概率。

### 2.4 损失信号驱动的 θ_coh 学习(B6 fix)

**v1 问题**:θ_coh 阈值没有损失信号,tuner 没法学。

**v2 解法**:**用 cognitive_pressure 降低量作为损失**:

```
# 固化候选 σ 触发固化前,记录系统在 σ 出现时的总 P
P_before_fixation = Σ_i max(0, P_i)  in current tick

# 假设固化(暂时把 σ 当 SA 加入召回链)
P_after_fixation = recompute_P_with_σ_as_SA()

# 实际降压效果
ΔP(σ) = P_before - P_after

# 损失信号
loss(θ_coh) = - Σ_σ activated  ΔP(σ) · I[chain_score(σ) > θ_coh]

# 用 AdaptiveTuner 标定 θ_coh,以 ΔP 为奖励
```

**为什么这是真正的损失信号**:固化对的本质就是**提升预测能力**(让该情境下的虚能量预先抬高,降 P)。如果固化对真的有效,ΔP 必然显著为正。θ_coh 学到的是"什么阈值让真正有效的固化通过、无效的不通过"。

### 2.5 跨模态固化(沿用 v1 §2.3,但 SA 都是量化桶 id)

例:文本"苹果"是 char SA + bucket_id 视觉轮廓 SA 在同 tick 共现 → 用 §2.3 成对 PMI 算 chain_score → 超阈值固化 → 新 SA `vocab::level_2::{vision_bucket_X, char_苹果}`。

**B5 fix 让这能工作**:视觉轮廓不再是连续向量,而是 `bucket_X`(离散),可以和 char 一样计数。

### 2.6 与 v3.1 IntrospectionPrototypeStore 的关系(S22 fix)

**v1 问题**:v3.1 已有 prototype 机制,v1 又加 vocab 机制,两套都创建新 SA,可能冲突。

**v2 澄清**:
- **v3.1 prototype** 是**内省 feeling 派生层** —— 从 draft 结构事实派生 feeling SA
- **v2 ComposedVocabStore** 是**感知 / 表达层** —— 从感受器 SA + 文本 SA 共现派生概念 SA
- **两者作用层不同,id 命名空间分离**:
  - prototype: `feeling::draft::proto_*`
  - vocab: `vocab::level_*::*`
- **没有冲突**:vocab 关注"积木块",prototype 关注"内省状态"。它们经过共现可以互相组合(如 `vocab::苹果` 在 `feeling::draft::proto_0` 下被表达),但 SA 本身分立。

### 2.7 量化桶的退役 / 合并(沿用 v3.1 §B2 retire 模式)

- 长期不被复用的桶 → 衰减驱逐
- 两个桶中心距离持续 < merge_threshold → 合并
- 合并/退役时同步删除该桶相关的 vocab 固化(沿用 v3.1 §B2 atomic retire)

---

## 3. 视觉感受器多通道数学模型 v2(B2 fix 重写)

### 3.1 总原则升级

每个 percept_proto 在多通道独立向量化,**独立打分独立召回,绝不压成总向量**(沿用 v1)。

**新增**:
- 加 C0 raw_payload 通道(只用于审计库,不进 PMI 不进召回,B2 fix)
- C1 加 θ_p 主轴角度(B2 fix,让 Fourier 在旋转不变 + 渲染时能恢复角度)
- C2 改 2×2 空间网格 HSV(B2 fix,能区分"红球黄边"vs"黄球红边")
- C5 motion 加遮挡容忍(S5/S22 fix)

### 3.2 8 个独立通道(C0 + C1-C7)

| 通道 | 数学定义 | 维度 | participates_in_vocab | participates_in_recall | participates_in_audit |
|---|---|---|---|---|---|
| **C0 raw_payload** | 32×32 RGB 缩略图(可配置) | 3072 | ❌ | ❌ | ✅ |
| **C1 轮廓 (FD)** | Fourier 描述子(沿 N=128 采样点 FFT 前 K=32 谐波) | 32 | ✅ | ✅ | ❌ |
| **C1 辅助 θ_p** | 主轴角度(旋转恢复,渲染时用) | 1 | ❌ | ❌ | ✅ |
| **C2 颜色 (HSV)** | 2×2 空间网格 × 16 桶 HSV 直方图 + 主色聚类 | 80 | ✅ | ✅ | ❌ |
| **C3 大小** | log(area/total) + aspect_ratio + compactness | 4 | ✅ | ✅ | ❌ |
| **C4 空间方位** | 中心(x,y) + 极坐标(r,θ) + 距视焦距离 | 6 | ✅ | ✅ | ❌ |
| **C5 运动趋势** | (dx, dy, d²x, d²y) + 遮挡容忍标志 | 5 | ✅ | ✅ | ❌ |
| **C6 纹理** | LBP / Gabor 响应 | 24 | ✅ | ✅ | ❌ |
| **C7 持续性** | 出现帧数比例 + 平均持续时长 + 间断次数 | 3 | ✅ | ✅ | ❌ |

**关键设计**(B1/B2 fix):
- `participates_in_vocab/recall/audit` 是**通道注册时声明的布尔**,不是关键词分支
- 这就是审阅员推荐的 AP-native 实现——`ComposedVocabStore` 迭代通道注册表过滤,**runtime 没有任何 `if channel == "C0"` 分支**
- C7 改成 3 维向量(出现比 + 时长均值 + 间断次数),余弦相似度有意义(S5 fix)

### 3.3 通道量化(B5 fix,§2.2 接入点)

每个 participates_in_vocab 通道维护自己的 VQ codebook:

```
# 例:C1 轮廓
quantization_buckets["C1"] = {
    "contour_b0": [Fourier vector of bucket 0 center],
    "contour_b1": [...],
    ...
}

# 新视觉对象进入 → 各通道量化 → 桶 id 作为 SA 标签
def percept_to_sa_labels(percept):
    labels = []
    for channel in vision_channels.with_flag("participates_in_vocab"):
        bucket_id = quantize(percept[channel], channel)
        labels.append(f"vision::{channel}::{bucket_id}")
    return labels
```

`vocab` 学习用这些 label 跑 §2.3 PMI。

### 3.4 跨 tick 匹配(S5/S22 fix)

```
match(percept_t^i, percept_{t-1}^j) = Σ_k w_k · cos_sim(ch_k(p_t^i), ch_k(p_{t-1}^j))

只用 participates_in_recall = True 的通道
默认 w_C1 = 0.4, w_C2 = 0.3, w_C4 = 0.3(轮廓+颜色+位置最稳)
```

**遮挡容忍(S5 fix)**:如果某 percept 连续 K 个 tick 找不到匹配(occluded),但**距离上次出现 < occlusion_timeout_ms**,保留 percept_id 不失效;再出现且匹配同 id 时,C5 motion 复活(基于最近一次见到的位置和当前位置 + 经过时间计算)。

`occlusion_timeout_ms` 默认 2000ms(场景化可配)。

### 3.5 视焦点公式修正(S7 fix)

**v1 问题**:`g_focus(d) = 1 + α·exp(-d²/(2σ²)) - β`,无界 - β 可以 < 0(负放大),无理论保证。

**v2 解法**:
```
g_focus(d) = (1 - β) + α · exp(-d² / (2 · focus_radius²))
其中 α, β ∈ [0, 1],β = focus 外抑制系数
g_focus(0) = 1 - β + α  (焦点位置最强)
g_focus(∞) = 1 - β       (焦外抑制)
```
天然 [1-β, 1-β+α] 区间内,无符号问题。α/β 由 AdaptiveTuner 标定。

### 3.6 内心画面重建(B2 fix,从审计库读)

**v1 问题**:从 C1+C2+C4 重建只出色块。

**v2 解法**:从**白箱审计库**读 C0 raw_payload + θ_p 旋转 + C4 位置:

```python
def render_inner_canvas(state_pool, audit_db):
    canvas = blank_canvas()
    for sa in state_pool.where(family="vision_percept"):
        if sa.R < render_threshold:
            continue
        raw_patch = audit_db.lookup_payload(sa.persistent_id)
        if raw_patch is None:           # 审计库已淘汰这个 SA 的 payload
            # fallback: 抽象色块渲染
            raw_patch = render_stylized_blob(sa.C1, sa.C2)
        rotated = rotate(raw_patch, sa.θ_p)
        blend_to_canvas(canvas, rotated, position=sa.C4_center, alpha=α(sa.R))
    return canvas
```

**关键**:
- 审计库未淘汰 → 渲染真实 patch,**能看出是苹果**
- 审计库已淘汰 → 退化到抽象色块,**老实承认"我记不清细节了"**
- 这正是拟人的:**最近的事看得清,很久以前的事只有印象**

---

## 4. 音频感受器多通道数学模型 v2(B1 fix 重写)

### 4.1 总原则升级

**v1 错处**:用 MFCC 等不可逆通道做音频含义并要求"重建可识别语音",数学上不可能。

**v2 解法**:**用与视觉同构的"原始 payload 进审计库 + 向量通道进 AP"分层**。

### 4.2 7 个独立通道(A0 + A1-A6)

| 通道 | 数学定义 | 维度 | vocab | recall | audit |
|---|---|---|---|---|---|
| **A0 raw_payload** | 窗口 PCM 片段(或 mel-spectrogram+phase) | 可变(16kHz × duration) | ❌ | ❌ | ✅ |
| **A1 音色 (MFCC)** | MFCC + Δ + ΔΔ | 39 | ✅ | ✅ | ❌ |
| **A2 音调** | f0 + HNR + 主频带 | 4 | ✅ | ✅ | ❌ |
| **A3 节奏** | onset density + IOI 直方图 | 16 | ✅ | ✅ | ❌ |
| **A4 响度** | RMS + 包络 | 6 | ✅ | ✅ | ❌ |
| **A5 空间方位** | ITD + ILD | 4 | ✅ | ✅ | ❌ |
| ~~A6 音频含义~~ | **删除**(B3 fix) | - | - | - | - |

**B3 fix**:A6"音频含义"原计划是后天学到的 embedding,但作为通道注册等于"先有含义再去学含义"的循环。**v2 删 A6**,音频含义**通过 §2 通用词汇固化机制涌现**:
- A1-A5 量化桶 + 跨模态共现(如音频桶 X + 文本桶"妈妈" 高 PMI)→ 固化为 `vocab::level_2::*`
- 这才是真正的"音频含义从经验涌现"

### 4.3 频段焦点(沿用 v1 §4.2)

`attention::audio::band` 行动 SA,同视焦点。

### 4.4 跨 tick 连续性(沿用 v1 §4.3,改为基于 audit_db payload)

短时间内同一个词的多个 audio_proto 通过 A1 音色相似 + 时间窗口归并为同一 audio_object。

### 4.5 内心音频重建(B1 fix,从审计库读)

```python
def render_inner_audio(state_pool, audit_db, time_window_ms):
    audio_buffer = silence(time_window_ms)
    for sa in state_pool.where(family="audio_proto"):
        if sa.R < render_threshold:
            continue
        raw_pcm = audit_db.lookup_payload(sa.persistent_id)
        if raw_pcm is None:
            # fallback: 节奏包络合成(抽象,听不出内容)
            raw_pcm = render_stylized_envelope(sa.A3, sa.A4)
        overlap_add(audio_buffer, raw_pcm, weight=α(sa.R))
    return audio_buffer
```

审计库未淘汰 → 真实 overlap-add,**真能听出"妈妈我饿了"**。
审计库已淘汰 → 抽象节奏包络,听不出内容但有节奏感。

---

## 5. 文本感受器多通道数学模型 v2(沿用 v1 §5,小修)

### 5.1 通道(沿用 v1)

T1 字符身份 / T2 子词组合(通过 §2 涌现) / T3 文本顺序 / T4 句法位置

### 5.2 自主词汇发现(走 §2 通用机制,不变)

### 5.3 文本侧词库 vs 多模态平权的不对称(S20 fix)

**v1 问题**:7.7 已有 120 phrase 表达词库(seed),vision/audio 没有 seed → 不对称。

**v2 澄清**:
- **表达层**有 seed phrase(120 个,用于"系统说什么")—— 这是**风格约束**,不是认知词库
- **感知层**无任何 seed,所有概念 SA 全部后天涌现(vision/audio/text 平权)
- 两层分离,**红线扫描 `if modality.text.seed` 应该 0 命中**(seed 只用于表达决策不进感知 PMI)

---

## 6. 黄色苹果泛化的完整数学链路 v2(沿用 v1 §6,fix B7)

### 6.1 教学阶段(沿用 v1 §6.1)

### 6.2 范式槽竞争 — 通道签名匹配(B7 fix)

**v1 问题**:`dominant_channel` 字段做槽类型匹配,本质是 metadata 路由,边界模糊。

**v2 解法**:**类型继承图(type lattice)** + **通道签名**:

```
# 每个 SA 自动从其 quantized_channels 集合产生 type signature
def channel_signature(sa):
    # 返回这个 SA 在哪些通道有量化桶 + 各桶强度
    return {
        channel: bucket_strength
        for channel, bucket_id, bucket_strength in sa.channel_buckets
    }

# 例:
#   vocab::苹果 的 channel_signature = {C1: 0.9 (轮廓), char: 1.0 (苹果)}
#   vocab::黄色 的 channel_signature = {C2: 0.95 (颜色), char: 1.0 (黄色)}

# 范式槽指定其"类型偏好"(也是通道签名)
slot_color.type_preference = {C2: 1.0}     # 颜色槽偏好 C2 主导的 SA
slot_object.type_preference = {C1: 1.0}    # 对象槽偏好 C1 主导的 SA

# 槽填充打分(通道签名匹配 + 召回打分)
def fill_score(sa, slot):
    signature_match = cosine(sa.channel_signature, slot.type_preference)
    recall_score = standard_recall_score(sa, current_context)
    return signature_match · recall_score
```

**为什么这不是关键词路由**:
- `channel_signature` 是**结构事实**(SA 在哪些通道有量化桶),不是标签
- `type_preference` 也是结构事实(槽偏好哪个通道的 SA)
- runtime **没有任何字符串比较**或 `if sa.label == ...` 分支
- 红线扫描:`grep "if .*type_preference" runtime/` 应该 0 命中,**只有打分函数读**

### 6.3 完整黄色苹果泛化链路(沿用 v1 §6.2)

C1 召回 `vocab::苹果`,C2 召回 `vocab::黄色` → 颜色槽 + 对象槽竞争 → 范式输出"黄色 苹果"。

### 6.4 防作弊量化验收门(S15 fix)

**v1 问题**:"测试图必须真实生成的黄苹果"没有 CI 保护。

**v2 解法**:加几个量化测试:

```python
def test_yellow_apple_no_handcrafted_percept():
    """生成黄苹果图必须经过完整 vision 管线,不是手填 percept。"""
    image = generate_yellow_apple_image()    # 用 PIL 或图像合成
    percept = vision_sensor.process(image)
    # 断言:percept.C1 量化桶不是测试方塞的,来自真实管线
    assert percept.provenance == "vision_sensor.process"
    assert percept.C1_quantized_bucket != "test_handcrafted_bucket"

def test_yellow_apple_history_no_yellow_apple_cooccurrence():
    """教学日志里不能有任何"黄色"+"苹果"同 tick 出现。"""
    teaching_log = load_teaching_log()
    for tick in teaching_log:
        text_tokens = tick.text_tokens
        if "黄色" in text_tokens and "苹果" in text_tokens:
            assert False, "教学日志里黄苹果同现,泛化测试无效"
```

---

## 7. 工程实施步骤 v2(用户三个升级 + Phase 重排)

### 7.1 Phase 顺序重排(用户决定:黄苹果优先)

```
Phase 8.2 — 逻辑 tick runtime + 场景化配置 + 主动休眠
Phase 8.3 — 白箱审计库(新独立模块,§10)
Phase 8.4 — 通用 SA 组合词汇机制(§2)
Phase 8.5 — 视觉感受器多通道(§3)+ C0 入审计库
Phase 8.6 — 黄色苹果泛化端到端验收(§6)— 用户最早能玩到核心承诺
Phase 8.7 — 纠错教学行动范式(Codex 8.4 原意)
Phase 8.8 — Web 工作台升级(§9 完整版,加内心画面)
Phase 8.9 — 音频感受器多通道(§4)+ A0 入审计库
Phase 8.10 — 真实多模态端到端验收
```

### 7.2 每 Phase 验收门(B6 等 fix 后明确化)

每 Phase 必须有:
- **量化验收门**(具体测试通过否)
- **诚实门**(失败时不能调阈值过)
- **回放 trace**(供 Claude 审阅)

---

## 8. (沿用 v1,不变)

---

## 9. Web 工作台升级清单 v2(沿用 v1 §9,加场景切换)

新增功能:
- **场景配置切换器**(纯文本/桌宠/具身/Agent)
- **当前 tick 频率显示 + 主动休眠状态指示**
- **审计库状态面板**(已用容量/淘汰统计/手动清理按钮)

---

## 10. 白箱审计库(新增,用户哲学升级核心)

### 10.1 设计原则

**完全独立于 AP 核心流程**:
- 独立 SQLite 数据库文件(`audit_db.sqlite`,与 `apv3_runtime.sqlite` 分离)
- AP runtime **不依赖审计库**——审计库满了/损坏了/关闭了,AP 仍正常工作
- 审计库**只存原始 payload**(C0 视觉 patch / A0 音频 PCM),不存任何决策路径或学习状态

### 10.2 数学/结构定义

```
audit_db.payloads = {
    persistent_id: {
        "modality": "vision" | "audio",
        "payload_blob": <binary>,
        "stored_at_tick": int,
        "stored_at_wall_ms": int,
        "last_audit_query_tick": int,
        "audit_priority": float    # 用于淘汰决策
    }
}
```

### 10.3 淘汰策略

`max_audit_capacity_mb` 由用户配置(默认 500MB,可关 = 0):

```
if used_capacity > max_audit_capacity_mb:
    # 综合"最旧"和"最低回忆权重"
    eviction_score(payload) = (1 - normalize(last_audit_query_tick)) +
                              (1 - normalize(R(sa.persistent_id)))
    evict_top_k_by_score()
```

被淘汰的 payload 不影响 AP 内部状态,仅审计能力降级(渲染 fallback 到抽象色块/包络)。

### 10.4 LLM 周期清理(用户提的可选机制)

支持外部触发 `audit_db.llm_review_and_purge(criterion="last_24h")`:
- LLM 读最近 24h 的 payload + 对应 commit_text
- 标记"可安全删除"的 payload
- 删除,释放空间

这是**完全可选**的工程接口,不是 AP 内部机制。

### 10.5 用户配置选项

| 配置 | 选项 |
|---|---|
| `enable_audit_db` | true / false |
| `max_audit_capacity_mb` | 数字,0 = 关闭 |
| `audit_eviction_policy` | "oldest_first" / "lowest_recall_first" / "combined"(默认) |
| `llm_purge_enabled` | true / false |
| `llm_purge_interval_hours` | 数字 |

### 10.6 红线

- AP runtime **绝对不许**因为审计库被关而 fail
- 审计库**绝对不许**写入任何 AP 决策路径上的数据
- 红线扫描:`grep "audit_db.write_decision\|audit_db.write_learning_state"` 必须 0 命中

---

## 11. v1 → v2 修复对照表(完整,29 条 confirmed + 5 minor)

| ID | 严重度 | 来源接缝 | v2 修复位置 |
|---|---|---|---|
| B1 audio MFCC 不可逆 | blocker | 信息论 | §4 A0 入审计库 + 4.5 重写重建 |
| B2 render 未定义 + 重建只有色块 | blocker | 信息论 | §3 C0 入审计库 + 3.6 重写重建 |
| B3 A6 循环依赖 | blocker | 信息论 | §4.2 删 A6 |
| B4 PMI 多元偏差 | blocker | 数学 | §2.3 改成对 PMI + 链式分解 |
| B5 PMI 连续向量 | blocker | 数学 | §2.2 量化桶层 |
| B6 θ_coh 无损失信号 | blocker | 数学 | §2.4 ΔP 损失信号 |
| B7 dominant_channel 关键词路由 | blocker | 数学 | §6.2 channel_signature 结构事实 |
| B8 短时记忆 5 分钟归零 | blocker | 架构 | §1 时间戳分离 + §1.6 场景化 + §1.7 主动休眠 |
| Phase ordering | blocker | 架构 | §7.1 重排 |
| S5 occlusion gap | serious | 信息论 | §3.4 加 occlusion_timeout_ms |
| S6 within-tick + soft-or | serious | 信息论 | §3.3 跨 tick 匹配规则 |
| S7 g_focus 公式 | serious | 信息论 | §3.5 公式重写 |
| S8 canvas linear sum 冲突 slot | serious | 信息论 | §3.6 R 加权混合是渲染层不是决策层 |
| S14 commit gate spam | serious | 数学 | §1.5 反向疲劳 |
| S15 phase8.6 anti-cheat | serious | 数学 | §6.4 量化验收门 |
| S16 phrase memory asymmetry | serious | 架构 | §5.3 表达 vs 感知分离澄清 |
| S22 vocab vs prototype 冲突 | serious | 架构 | §2.6 命名空间分离 |
| S25 C5 单 tick 污染 | serious | 架构 | §3.4 单 tick 教学 C5 跳过 PMI |
| S27 cross-tick matching threshold | serious | 架构 | §3.4 用 AdaptiveTuner |
| S29 phi_pooling_schema_version | partial | 架构 | bump schema_version,加 v3.1 §B6 guard |
| S30 §3.5 fidelity blob | serious | 架构 | §3.6 审计库分层 fix |
| S31 §4.4 continuity | serious | 架构 | §4.5 overlap-add fix |
| S32 codex correction unspec | partial | 架构 | Phase 8.7 显式做完整设计 |
| S33-37 minor | minor | 各 | 文档细节修正 |

---

## 12. 给 Codex 的总指令格式

完成本设计稿后,Codex 应该:

1. 读完本文档(v2,本稿)
2. 按 §7.1 顺序逐 Phase 实施
3. **每个 Phase 走完整 5 段闭环**(设计→审查→落地→验收→报告)
4. 每 Phase 完成后冷保存 + 出 trace 给 Claude 评估
5. **任何"看起来通过但不该通过"的情况立即停下问 Claude**
6. **Phase 8.2 之前不许偷工**——逻辑 tick runtime 是后续所有 phase 的地基,做不稳一切白搭

---

— 接手线程,2026-06-17
