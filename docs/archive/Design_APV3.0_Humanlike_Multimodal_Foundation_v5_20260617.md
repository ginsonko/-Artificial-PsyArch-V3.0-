# APV3.0 拟人多模态底座 — 完整设计稿 v5(可证伪最小闭环 + 远景图谱分层)

日期: 2026-06-17
作者: 接手线程
状态: **v4 经 Codex 审阅,5 条核心论点全收,2 条部分收。v5 收束 v4 为"可证伪 AP-native 多模态闭环"作为 Phase 8 实施目标;v4 §20-§28 哺乳类心智机制分层为 Phase 9+ backlog 远景图谱。核心修正:对照课程 + slot 偏好统计涌现 + 稀疏 pairwise + ΔP 作晋升门 + audit_db 严格只渲染 + sensor adapter 边界明确。**

前身:
- v1 (9 blocker)、v2 (修 v1 8 blocker + 3 哲学)、v3 (整合 APV2/SNS 经验)、v4 (修 v3 7 blocker + 哺乳类心智)
- **v5(本稿)**:把 v4 收束为可证伪最小闭环,Codex 5 大 blocker 全部数学化修复

---

## 0. v4 → v5 修正总览(必读)

### 0.1 Codex 审阅 → v5 核心收吸

| Codex 论点 | 严重度 | v5 处理 |
|---|---|---|
| **C-1 黄苹果泛化数学证据不足** | Blocker | §6 重写为**对照课程**(red apple / green apple / yellow banana / yellow cup / red ball / green ball...)+ C1/C2 ablation,无对照课程不构成证据 |
| **C-2 slot.type_preference 是人工 schema** | Blocker | §6.3 改 **slot 偏好从 filler 历史统计自动涌现**;槽偏好不写入,只统计 |
| **C-3 PMI 组合固化爆炸 + 偶然巧合** | Blocker | §2.3 改稀疏 pairwise top-k;**ΔP 是晋升门不是阈值调参信号**;最小曝光 + 时间衰减 + held-out |
| **C-4 audit_db 不能变隐藏完美记忆** | Blocker | §13.7 改严格边界:audit_db 只供 UI 渲染,**AP 认知绝对只读量化桶/通道统计/能量场/范式统计**,raw payload 永不进召回 |
| **C-5 多模态平权 vs 通道工程边界** | Serious | §16.7 明确边界画在 **sensor adapter 之后**:前端允许模态特异,后端 runtime 不再有模态分支 |
| **C-6 §20-§28 推迟到 Phase 9+** | Major | §31 分层:v5 主线 = Phase 8 多模态闭环;**§20-§28 改为 Phase 9+ backlog 远景图谱** |
| **C-7 文本不一句同 tick 注入** | Serious | §16.8 文本按字符微事件流入,每 tick 至多 N 字符,与视觉/音频同步时间网格 |
| **C-8 逐字草稿是行动竞争** | Minor | §16.9 明确 type/reread/replace/commit/stop 都是行动 SA,经 attention selector 竞争 |
| **C-9 APV2 模块需 adapter + 红线** | Serious | §16.10 每复用模块必须有 v3 adapter + 红线扫描脚本 |

### 0.2 v5 整体哲学(必读)

> "Phase 8 阶段不要贪多。最该证明的是:**AP-native 多模态组合学习可证伪闭环**——真实连续 tick、统一 sensor event、组合 SA 固化、slot 偏好自学习、yellow apple 严格泛化、Web 可审计回放。只要这条闭环过了,APV3 就不只是中文短语对话底座,而是开始拥有真正的多模态概念组合学习能力。"

**这是 v5 主线**。v4 §20-§28 的哺乳类心智维度不被砍,而是分层:

- **Phase 8(v5 主线)**:可证伪最小闭环 + 自由对话基础。预期目标 = "类人幼童的多模态概念组合学习能力"
- **Phase 9+(v5 backlog)**:哺乳类心智维度上层化(驱力 / RPE / 受挫 / 依恋 / 共同注意 / 共情 / 痛厌恶 / 重放 / 玩乐)。预期目标 = "类人幼童的心智深度 + 情感反应"

诚实承认:**Phase 8 完成后系统已经是"会学习的拟人对话底座";Phase 9+ 完成后才是"有内心生活的桌宠"**。

### 0.3 v5 → 最终目标可达性的严肃判断

**最终目标**:多模态概念组合及范式实时学习能力的多模态自由对话拟人底座,接近人类幼童的学习能力。

**v5 主线(Phase 8)可达性分析**:

| 幼童能力维度 | v5 Phase 8 落点 | 可达性自评 |
|---|---|---|
| 连续感知不丢失上下文 | §1 时间戳分离 + 短长记忆双层 | 🟢 高 |
| 多模态独立感知 + 跨模态绑定 | §3-§4 通道注册表 + §15.1 双层 align | 🟢 高 |
| 自主发现"概念"(词汇/形状/声音模式) | §2 稀疏 pairwise + ΔP 晋升 + 量化桶 | 🟡 中-高(关键依赖对照课程质量) |
| 组合泛化(没见过黄苹果但能说) | §6 对照课程 + slot 偏好统计涌现 | 🟡 中(需要 Phase 8.8 实测验证) |
| 把不确定/惊/熟悉/无聊感受出来 | §15.2 + v3.1 IntrospectionPrototype | 🟢 高 |
| 持续学习不灾难遗忘 | §1.3 短→长晋升 + §11.7 novelty_residual | 🟢 高 |
| 焦点/注意/习惯化 | §11 数学 + §13 视焦点 + APV2 J-22 | 🟢 高 |
| 逐字/逐词草稿表达 | §16.9 草稿行动竞争 | 🟢 高 |
| 主动表达"我想问/我不懂/我惊讶" | 通过 §15.2 + cognitive feelings 触发 | 🟡 中(emerge,需实测) |
| 主动求知/主动玩乐 | **Phase 9 backlog** (drive::epistemic) | 🟡 Phase 8 弱;Phase 9 高 |
| 共情/对照护者依恋 | **Phase 9 backlog** | ⚪ Phase 8 缺;Phase 9 计划补 |

**最终判断**:**v5 Phase 8 完成后,系统具备幼童的"概念学习+组合泛化+多模态绑定+持续记忆+逐字表达+不确定感受"——这本身就是接近 18-30 月龄幼童的学习能力**。Phase 9+ 完成后,系统才有"心智深度+情感持续+主动性",接近 3-5 岁。

**最大风险**:不在数学链路,在**对照课程是否能持续提供干净数据**。如果教学日志里黄色和苹果偶然同现一次,§6 泛化测试就被污染。**必须有诚实门**(下文 §6.4)。

### 0.4 红线(v5 新强化)

继承 v4 全部,新增:

- **❌ AP 认知决策路径绝对不许 by-id lookup audit_db raw payload**——只供 UI 渲染。`grep "audit_db\." runtime/cognitive/` 必须 0 命中(C-4)
- **❌ slot.type_preference 不许人工写入**——只能从 filler 统计涌现(C-2)
- **❌ ComposedVocabStore 不许枚举 SA 子集**——只能稀疏 pairwise + 链式延展(C-3)
- **❌ 文本不许整句同 tick 注入**——必须按字符/短片段微事件(C-7)
- **❌ "vision/audio/text" runtime 分支只许出现在 sensor adapter 内**——后端只看 channel_signature(C-5)
- **❌ Phase 8 不许实现 §20-§28**——分层为 Phase 9+ backlog(C-6)
- **❌ Phase 8.5 emotion_modulator 4 CFS 补完未验证前不许进 Phase 8.6+**——继承 v4 B-B5

---

## 1. 逻辑 tick runtime(v4 §1 + Codex C-7 修正)

### 1.1 沿用 v4 §1 全部

### 1.2 文本字符微事件(C-7 fix)

**v4 隐含错误**:用户消息整句进 `apply_external_items`,一句 30 字 SA 同 tick 注入 → 视觉/音频的 percept_proto SA 被压过。

**v5 正确做法**:

```python
# Web/CLI 入口接收用户消息 "你好,小桌宠!"
# 不是整句进 state_pool,而是按字符流入 sensor adapter:

text_sensor.queue_user_message("你好,小桌宠!", arrival_wall_ms=now)

# 每 tick 内部:
def text_sensor_step(t, dt_ms):
    chars_per_tick = config.text_chars_per_tick  # 默认 1-2
    for _ in range(chars_per_tick):
        if queue.is_empty():
            break
        char_event = queue.pop()
        emit_sa(
            sa_label=f"text::char::{char_event.char}",
            real_energy=char_R_base,
            arrival_tick=t,
            arrival_wall_ms=char_event.assigned_wall_ms,
            sequence_position=char_event.seq_pos,
        )
```

**关键**:
- `text_chars_per_tick` 默认 1-2,**每个字独占自己的 tick 窗口**
- 同时音频/视觉如果有输入也按各自字符级/帧级速率流入
- 三模态在同一时间网格上**真正并行**,不再"文本压过视觉"

**场景化配置 §1.6 新增**:
| 场景 | text_chars_per_tick | 含义 |
|---|---|---|
| 纯文本对话 | 1 | 标准阅读节奏 |
| 桌宠多模态 | 2 | 略快,但仍按字 |
| 具身连续 | 1 | 严格逐字 |
| Agent | 4 | 处理大文本时加速 |

### 1.3 sleep emerge(继承 v4 §12.5,严格化)

注意 sleep 不能是仅"显式 tick_dilation 行动"——必须 global_fatigue 自动驱动 tick_ms_target 增加,**行动是叠加层不是必经**。否则系统在没学会该行动时永远不睡。

```python
# 默认值
def compute_target_tick_ms(t):
    base = config.scenario.base_tick_ms
    dilation_from_fatigue = sigmoid((global_fatigue - 0.5) * 4) * 10.0  # 0~10x
    learned_dilation = action_parameter_memory.get_learned_tick_dilation(context)
    return base * (1 + dilation_from_fatigue) * (1 + learned_dilation)
```

**emergent**:即使没学会 `tick_frequency_change` 行动,global_fatigue 高时也会自然降频。学到行动后可以叠加更深的休眠。

---

## 2. 通用 SA 组合词汇固化(v4 §2 + Codex C-3 严格化)

### 2.1 沿用 v4 §2.1 哲学(任意 SA 一等公民可组合)

### 2.2 量化桶层(沿用 v4 §2.2)

### 2.3 稀疏 pairwise + ΔP 晋升门(C-3 fix 核心)

**v4 错误**:`ComposedVocabStore` 用多元 PMI 推广,工程上枚举 SA 子集会爆炸,且 PMI 假阳性高。

**v5 正确做法**——四道门关:

**门 1 - 稀疏 pairwise top-k 邻接**:

```python
# 不维护全 SA × SA 共现矩阵,只维护每个 SA 的 top-k 共现伙伴
class SparsePairwiseGraph:
    """每个 SA 只记其 top_k_partners 最强的共现边"""
    partners: dict[SA_id, list[(SA_id, count)]]  # top-K=32 per SA
    
    def observe_cooccurrence(self, sa_a, sa_b):
        # 增量更新 top-k(boundedly bounded heap)
        self._update_top_k(sa_a, sa_b)
        self._update_top_k(sa_b, sa_a)
```

每个 SA 持有的伙伴上限 K=32(可配),内存 O(N · K) 而非 O(N²)。

**门 2 - 最小曝光 + 时间衰减**:

```python
# PMI 用 Bayesian smoothing (沿 v4)
# 但每条边必须满足最小曝光数 + 时间衰减后的有效 count
def edge_is_eligible(edge):
    if edge.exposure_count < θ_min_exposure:    # 默认 5 次
        return False
    if edge.last_seen_age_ticks > age_horizon:  # 默认 1000 tick
        return False
    return edge.smoothed_pmi > θ_pmi_nominate
```

**门 3 - PMI 只能提名,不能晋升**:

```python
def nominate_for_fixation(graph):
    """每 N tick 跑一次,返回候选列表(不直接固化)"""
    candidates = []
    for sa_id, partners in graph.partners.items():
        for partner_id, edge in partners:
            if edge_is_eligible(edge):
                # 还要看是否能成链
                chain = try_extend_chain(sa_id, partner_id, max_length=4)
                candidates.append(chain)
    return candidates
```

**门 4(关键)- ΔP 是晋升门,不是阈值调参信号**:

```python
def evaluate_fixation_with_held_out(candidate, held_out_traces):
    """
    用 held-out 测试数据,模拟"如果固化这个组合 SA,
    在 held-out 上预测压力是否下降"
    """
    P_baseline = compute_total_P(held_out_traces, vocab_set=current_vocab)
    P_with_candidate = compute_total_P(
        held_out_traces, 
        vocab_set=current_vocab | {candidate}
    )
    delta_P = P_baseline - P_with_candidate
    return delta_P

def attempt_promotion(candidate, held_out_traces):
    delta_P = evaluate_fixation_with_held_out(candidate, held_out_traces)
    if delta_P > θ_promote_dP:  # 实测压力降低
        promote_to_vocab_sa(candidate)
        log_promotion_evidence(candidate, delta_P)
    else:
        log_rejection(candidate, delta_P)
```

**为什么这是正确的**:
- PMI 高只是"看起来相关",可能是数据巧合
- 只有当**加入这个组合 SA 真的让系统在新数据上预测更准**,才晋升
- 这是 ML 的标准 generalization gate,迁移到 AP 仍然有效
- θ_promote_dP 由用户配置(可严格可宽松),**不会被反向调到能让任何东西通过**

### 2.4 链式延展(C-3 配套)

```python
def try_extend_chain(seed_a, seed_b, max_length=4):
    """从一对稳定 pairwise 边开始,只向已稳定的邻居延展"""
    chain = [seed_a, seed_b]
    while len(chain) < max_length:
        # 找下一个,要求与 chain 末两个元素都有稳定边
        next_candidate = find_partner(chain[-1])
        if next_candidate is None:
            break
        if not edge_is_eligible(get_edge(chain[-2], next_candidate)):
            break  # 不只与最后一个稳定,要前序也稳定 -> 防巧合
        chain.append(next_candidate)
    return chain if len(chain) >= 2 else None
```

链的整体性靠"每相邻对都稳定 + 隔一对也稳定",数学严谨。

### 2.5 退役(沿用 v4)

### 2.6 v3.1 IntrospectionPrototype 命名空间分离(沿用 v4)

---

## 3-5. 视觉/音频/文本感受器(v4 §3-§5 + Codex C-5 边界明确化)

### 3.1 沿用 v4 §3-§5 全部

### 3.2 模态平权边界明确化(C-5 fix)

新增 §3.0 总图:

```
┌──────────────────────────────────────────────────────┐
│ raw input (image/audio/text)                         │
│           ↓                                          │
│ Modality-specific primitive extractor                │ ← 允许模态分支
│   - vision: HSV/Fourier/optical flow                 │
│   - audio: MFCC/f0/onset                             │
│   - text: char tokenize                              │
│           ↓                                          │
│ Quantization buckets (per-channel VQ codebook)       │
│           ↓                                          │
│ Normalized SA event                                  │ ← 边界线
│   - sa_label, channel_signature, R, V, P, A, F       │
│           ↓                                          │
│ AP-Core runtime                                      │ ← 严禁模态分支
│   - state_pool, attention, recall, draft action      │
└──────────────────────────────────────────────────────┘
```

**红线扫描**:
- `grep "if .*modality" runtime/cognitive/` → **必须 0 命中**
- `grep "if .*modality" runtime/sensor_adapters/` → **允许命中**(模态特异前端)
- `grep "vision\|audio\|text" runtime/cognitive/` → 只允许出现在 `channel_signature` 字段值或 type lattice 配置中

这条边界画在 sensor adapter 之后,**所有 AP-Core 看到的 SA 都是 normalized,运行时只看 channel_signature 是不是数据,不看模态名**。

---

## 6. 黄色苹果泛化的对照课程(v4 §6 + Codex C-1/C-2 重写)

### 6.1 v4 的根本错误

**Codex 论证(我同意)**:只教"红苹果"和"黄色香蕉",数学上以下两种解释完美等价:

| 假设 A(我们想要) | 假设 B(数据完美支持) |
|---|---|
| "苹果" 绑 C1 苹果轮廓 | "苹果" 绑 C1 苹果轮廓 + C2 红色(共定义) |
| "香蕉" 绑 C1 香蕉轮廓 | "香蕉" 绑 C1 香蕉轮廓 + C2 黄色 |
| "黄色" 绑 C2 黄色 | "黄色" 绑 C2 黄色 + C1 香蕉轮廓 |

如果系统学到假设 B,看到黄色苹果时:`C1 苹果轮廓` 但 `C2 黄色`→ 通道冲突,可能输出"红色苹果"(因为"苹果"包含 C2 红色)。**没有任何统计信号区分 A 和 B**。

### 6.2 对照课程的严格设计(C-1 fix)

**课程必须有对照样本让系统看到"苹果"在 C2 上变化、"黄色"在 C1 上变化**:

```yaml
training_curriculum:
  # 苹果跨颜色:让 "苹果" SA 学到只稳绑 C1 (轮廓)
  - red_apple_image    + text "红色苹果"   * 20 次
  - green_apple_image  + text "绿色苹果"   * 20 次
  - yellow_apple_image + text "黄色苹果"   ❌ 测试时再用,训练中绝不出现
  
  # 苹果跨颜色补充
  - red_apple_image    + text "苹果"      * 10 次
  - green_apple_image  + text "苹果"      * 10 次
  
  # 黄色跨形状:让 "黄色" SA 学到只稳绑 C2 (颜色)
  - yellow_banana_image + text "黄色香蕉"  * 20 次
  - yellow_cup_image    + text "黄色杯子"  * 20 次
  - yellow_ball_image   + text "黄色球"   * 20 次
  - yellow_banana_image + text "黄色"     * 10 次
  - yellow_cup_image    + text "黄色"     * 10 次
  
  # 干扰:防止"颜色词=某个物体"
  - red_ball_image    + text "红色球"     * 15 次
  - green_ball_image  + text "绿色球"     * 15 次
  - green_banana_image + text "绿色香蕉"  * 15 次
```

### 6.3 slot 偏好统计涌现(C-2 fix)

**v4 错误**:`slot.type_preference = {C2: 1.0}` 是人工 schema。

**v5 正确做法**:slot 偏好从 filler 历史的通道一致性自动涌现。

**Step 1 - 范式通道发现 slot**:

继承 v2.1 范式通道(slot 发现机制)。slot 是"在表达模板中可被替换的位置"。范式发现"红色 X / 绿色 X / 黄色 X" → 学到模板"颜色 + 物体名",slot1 在"颜色"位,slot2 在"物体名"位。

**Step 2 - 每个 slot 维护 filler 通道签名直方图**:

```python
class Slot:
    slot_id: str
    fillers_history: list[SA_id]  # 历史填入此 slot 的所有 SA
    
    def derive_channel_preference(self) -> dict[ChannelName, float]:
        """从 filler 历史的通道一致性统计涌现"""
        # 对每个通道 c,计算 fillers 在该通道上的标准差(低标准差 = 一致 = 偏好)
        channel_consistency = {}
        for c in all_channels:
            filler_vectors_in_c = [
                quantize(sa.get_channel_payload(c), c) 
                for sa in self.fillers_history
            ]
            # 一致性 = 1 - normalized_entropy(bucket_distribution)
            consistency = 1.0 - normalized_entropy([
                count for bucket, count in Counter(filler_vectors_in_c).items()
            ])
            channel_consistency[c] = consistency
        return softmax(channel_consistency)
```

**Step 3 - slot 填充打分用统计涌现的偏好**:

```python
def fill_score(sa, slot):
    pref = slot.derive_channel_preference()  # 统计涌现的偏好
    signature_match = sum(
        pref[c] * sa.channel_signature.get(c, 0.0) for c in pref
    )
    recall_score = standard_recall_score(sa, current_context)
    return signature_match * recall_score
```

**Step 4 - 数学保证**:

- 教完 §6.2 对照课程后:
  - "颜色 + 物体" slot1 (颜色位) 历史 filler = ["红色", "绿色", "黄色"]
  - 这些 SA 的 C2(颜色)通道桶各不相同但 C1 通道桶变化大(因为它们在不同形状物体上出现)
  - **slot1 的 C2 一致性高(都是颜色类桶),C1 一致性低(跨形状)**
  - → slot1 自然涌现 C2 偏好
- 反之 slot2(物体位)的 filler = ["苹果", "香蕉", "球", "杯子"],它们 C1 一致性高(都是物体轮廓桶),C2 一致性低(跨颜色)→ slot2 自然涌现 C1 偏好

**这是 100% AP-native:slot 偏好是统计结果,不是设计者写入**。

### 6.4 严格泛化测试 + 防作弊验收门(C-1 fix 配套)

```python
def test_yellow_apple_generalization():
    # 1. 必须用真实图像生成器(不手填 percept)
    image = render_realistic_yellow_apple()
    percept = vision_sensor.process(image)
    assert percept.provenance == "vision_sensor.process"
    
    # 2. 教学日志诚实门
    teaching_log = load_teaching_log()
    for tick in teaching_log:
        text = tick.text_tokens
        if "黄色" in text and "苹果" in text:
            assert False, "教学日志含黄苹果同现,泛化测试无效"
    
    # 3. 喂入感知系统(无文本提示)
    state_pool.apply_percept(percept)
    run_tick_loop(N=20, no_text_input=True)
    
    # 4. 触发表达
    state_pool.inject_drive("describe_what_you_see")
    output = run_tick_loop_until_commit()
    
    # 5. 输出必须包含 "黄色" 和 "苹果" 两个 vocab SA(顺序可变)
    assert "黄色" in output.tokens
    assert "苹果" in output.tokens
    
    # 6. 关键:不许出现 "红色"/"绿色"/"香蕉" 之类的污染
    forbidden = {"红色", "绿色", "香蕉", "球", "杯子"}
    assert not (forbidden & set(output.tokens))

def test_yellow_apple_C1_ablation():
    """C1 通道屏蔽 → 系统应只输出 '黄色'(看不到形状)"""
    state_pool.disable_channel("C1")
    output = trigger_describe(yellow_apple_image)
    assert "黄色" in output.tokens
    assert "苹果" not in output.tokens

def test_yellow_apple_C2_ablation():
    """C2 通道屏蔽 → 系统应只输出 '苹果'(看不到颜色)"""
    state_pool.disable_channel("C2")
    output = trigger_describe(yellow_apple_image)
    assert "苹果" in output.tokens
    assert "黄色" not in output.tokens
```

**Ablation 测试是"系统是否真的把'苹果'绑定 C1、'黄色'绑定 C2"的最严格证据**——比单纯看输出更硬。

### 6.5 诚实门(C-1 fix 收尾)

如果 Phase 8.8 泛化测试失败:
- ❌ **不许调通道权重让它过**
- ❌ **不许加 ad-hoc 引导信号**
- ✅ 必须查根因:对照课程数据是否够 diverse?ComposedVocab 是否真把"苹果"固化成 C1 主导?slot 偏好涌现是否充分?
- ✅ 失败也是有价值的数据——汇报清楚 + 暴露真问题

---

## 7-10. 沿用 v4 工程实施 / 白箱审计库(C-4 严格化)

### 7-9. 沿用 v4

### 10. 白箱审计库 — 严格只渲染(C-4 fix)

**v4 错误**:把 audit_db 归入"AP-Core episodic 视觉/音频记忆层",但 §13.7 给出 `lookup_payload(persistent_id)` 接口允许 by-id 完美回忆。这是隐藏完美记忆漏洞。

**v5 严格边界**:

| 访问目的 | 允许? |
|---|---|
| AP runtime 召回打分 | ❌ 绝对禁止 |
| AP runtime emit SA decision | ❌ 绝对禁止 |
| AP runtime learning signal | ❌ 绝对禁止 |
| Web UI 内心画面渲染 | ✅ |
| Web UI 内心音频回放 | ✅ |
| User audit trail review | ✅ |
| LLM 周期清理 | ✅ |

**v3 设计修正**:

```python
class AuditDB:
    """严格只供 UI 与外部审计,绝不参与 AP 认知决策"""
    
    def store_payload(self, persistent_id, payload, modality):
        """从 sensor adapter 写入"""
        # 仅在 audit_db 启用时
        pass
    
    def lookup_for_rendering(self, persistent_id) -> Optional[bytes]:
        """专供 UI 渲染层调用,
        必须在 AP-Core 之外的渲染管道中调用"""
        pass
    
    # ❌ 不存在 lookup_for_recall, lookup_for_decision 等方法
```

**红线扫描脚本**(必跑):

```bash
# AP-Core 任何文件都不许 import audit_db
grep -r "from .* import audit_db\|from .* import AuditDB" runtime/cognitive/
# 必须 0 命中

# UI/render 层可以 import
grep -r "from .* import audit_db" web/render/
# 允许命中
```

**audit_db 失效的后果**:
- UI 内心画面退化为 stylized_blob(从 C1+C2+C4 合成)— 这是 canonical 默认渲染
- AP 认知功能**完全不受影响**(因为它原本就只读量化桶 SA 和通道统计)

**这才是诚实的"audit_db 在 AP-Core 之外"边界**。

---

## 11-15. v3/v4 已修复部分沿用,无大改

### 11. 习惯化稳态推导 + Novelty Trace(沿用 v4 §11)
### 12. 合理感门控 + Sleep emerge(沿用 v4 §12)
### 13. 视焦点 + 变分辨率 + 重建分层(沿用 v4 §13,§13.7 已被 §10 严格化覆盖)
### 14. 视野 P 场(percept-centric WTA) + 持驻焦点(沿用 v4 §14)
### 15. 三个推论机制修复版(沿用 v4 §15)

---

## 16. 工程实施 Phase 重排(v5 收束版)

### 16.1 复用 APV2 模块表(沿用 v4 §16.1)

### 16.2 v5 原创模块清单

- §1.2 文本字符微事件 sensor adapter
- §2.3 SparsePairwiseGraph + ΔP 晋升门
- §3.0 sensor adapter 边界 + 红线扫描
- §6.2 对照课程数据集 + 图像合成器
- §6.3 slot 偏好统计涌现公式 + filler_history 维护
- §6.4 ablation 测试套件
- §10 audit_db 严格只渲染边界 + 红线脚本
- §16.4 cognitive_feelings 补 4 通道(继承 v4)
- §16.7 sensor adapter 总图
- §16.9 草稿行动是行动竞争 SA
- §16.10 APV2 复用 adapter 层

### 16.3 Phase 顺序(v5 收束版)

```
Phase 8.2  连续 tick runtime + 逐字 sensor + draft action runner
            (含 §1.2 文本字符微事件 + §16.9 草稿行动 SA)

Phase 8.3  Sensor Adapter Contract + audit_db 严格只渲染
            (含 §3.0 边界图 + §10 红线脚本)

Phase 8.4  通用 SA 组合词汇 — 稀疏 pairwise + ΔP 晋升门
            (含 §2.3 SparsePairwiseGraph + held-out 验证)

Phase 8.5  cognitive_feelings 补 4 通道 + emotion_modulator 验收
            (B-B5 fix,阻断式前提)

Phase 8.6  玩具视觉感受器(合成 colored shapes)
            (3.1 多通道 + foveated + 量化桶,不上真实摄像头)

Phase 8.7  视焦点 SA + saccade(persisting) + 焦点 overlay

Phase 8.8  严格 yellow apple 泛化验收(对照课程)
            (§6.2 课程 + §6.3 slot 涌现 + §6.4 ablation,核心证伪门)

Phase 8.9  自然纠错/学习下一句话行动范式
            (Codex 提的"你是谁→你好"问题:惩罚后进入"我可能答错了"行动链)

Phase 8.10 习惯化数学验证 + novelty_residual + refocus 行动

Phase 8.11 Web 工作台升级:逐 tick trace 回放 + 内心画面 + Mind/Fairy/Audit 五区

Phase 8.12 音频感受器多通道(合成正弦/谐波,不上真实麦克风)
            (含 §13.5 filterbank 模板)

Phase 8.13 真实多模态端到端验收
            (黄苹果 + 习惯化 + 草稿对话 + 持续记忆)

—— Phase 8 完成,系统具备幼童多模态概念组合学习能力 ——

———————— 以下为 Phase 9+ backlog 远景 ————————

Phase 9.1  §20 驱力 / 内稳态(drive_SA 一等公民)
Phase 9.2  §21 RPE = dopamine analog(已有 P 通道之上)
Phase 9.3  §22 受挫 / 习得性无助(COR 通道扩展)
Phase 9.4  §23 依恋(entity::user SA + OXY 通道)
Phase 9.5  §24 共同注意 / 镜像
Phase 9.6  §25 共情 / 心智化
Phase 9.7  §26 痛持续记忆
Phase 9.8  §27 重放巩固 / 睡眠学习
Phase 9.9  §28 玩乐 / 探索

—— Phase 9 完成,系统具备幼童心智深度 + 情感主动性 ——

Phase 10+  真实摄像头 / 麦克风 / 桌面感受器 + SNS 桌宠产品化
```

### 16.4 cognitive_feelings 补 4 通道(沿用 v4 §16.4)

### 16.5 short_term_buffer 迁移(沿用 v4 §16.5)

### 16.6 (空,v5 删除)

### 16.7 Sensor Adapter 总图(C-5 fix,见 §3.2)

### 16.8 文本字符微事件(C-7 fix,见 §1.2)

### 16.9 草稿行动竞争(C-8 fix)

```python
# 每 tick 内,所有候选草稿行动都是 action SA 进 attention selector
draft_action_candidates = [
    Action("type_token", target=phrase_choice_1, expected_R_change=+0.3),
    Action("type_token", target=phrase_choice_2, expected_R_change=+0.2),
    Action("reread", target=current_draft, expected_R_change=+0.1),
    Action("delete_tail", target=last_n_chars, expected_R_change=-0.1),
    Action("commit", target=current_draft, expected_R_change=+0.5_if_ready_else_-0.2),
    Action("stop", target=None, expected_R_change=+0.4_if_helplessness_else_-0.3),
    Action("noop", target=None, expected_R_change=0.0),
]

# 所有候选经 attention selector 竞争
winning_action = attention_selector.select(draft_action_candidates + other_action_candidates)
# 每 tick 至多 1 个执行
execute(winning_action)
```

**关键**:草稿行动**不是 hardcoded 序列**,与其他行动(saccade / refocus / drive 行动)同等竞争资源。这才是真正"逐字思考"的拟人——思考可以被打断、可以重读、可以放弃、可以静默。

### 16.10 APV2 复用 adapter 层(C-9 fix)

```python
# 每个复用的 APV2 模块都要 wrap 在 adapter:
class APV3EchoBufferAdapter:
    """APV2 ShortTermEchoBuffer 的 v3 adapter"""
    
    def __init__(self):
        self.underlying = APV2.ShortTermEchoBuffer(config=apv3_config)
    
    def observe_sa(self, sa: APV3_SA):
        # 关键:翻译 SA family/channel_signature → APV2 modality enum
        modality = self._derive_modality_for_lifespan(sa.channel_signature)
        apv2_item = APV2.EchoItem(
            label=sa.persistent_id,
            energy=sa.real_energy,
            modality=modality,  # 仅供 echo lifespan 查表用
            origin_tick=sa.arrival_tick,
        )
        self.underlying.observe(apv2_item)
    
    def build_echo_items(self, current_tick) -> list[APV3_SA]:
        apv2_echoes = self.underlying.build_echo_items(current_tick)
        return [self._unwrap_to_v3(item) for item in apv2_echoes]
```

**每个 adapter 跟一个红线扫描**:

```bash
# Echo buffer 不许从 SA 直接读模态名
grep "sa.modality" runtime/cognitive/  # 必须 0 命中
# 只能通过 adapter 的 _derive_modality_for_lifespan
```

---

## 17. v5 完美图景能力清单(分层)

### 17.1 Phase 8 完成后(v5 主线)

**核心多模态认知能力**:
- ✅ 连续逻辑 tick + 真实时间戳分离
- ✅ 多模态独立感知 + 量化桶 + 跨模态 vocab 固化
- ✅ ΔP 验证的稀疏 pairwise 词汇晋升(数学严谨)
- ✅ slot 偏好统计涌现(无人工 schema)
- ✅ 黄苹果对照课程严格泛化通过 + C1/C2 ablation 证据
- ✅ 视焦点 + 变分辨率 + saccade + 持驻
- ✅ 习惯化 emerge + novelty_residual 保证秒级注意
- ✅ 短长记忆双层 + 5 分钟 idle 不丢上下文
- ✅ 逐字草稿行动竞争(type/reread/replace/commit/stop)
- ✅ Web 工作台逐 tick 回放 + 五区(Home/Mind/Fairy/Audit/Settings)
- ✅ cognitive_feelings 完整(7+4=11 个 + factory 模式)
- ✅ 自然纠错行动范式(惩罚 → "我可能错了" → 等教师证据)
- ✅ audit_db 严格只渲染 + AP-Core 不依赖

**对应人类幼童能力(18-30 月龄)**:
- ✅ 多模态感知 + 跨模态绑定("苹果"绑形状不绑颜色)
- ✅ 词汇组合泛化("黄色苹果"没见过也会说)
- ✅ 持续注意 + 习惯化
- ✅ 不确定/惊/熟悉感受表达
- ✅ 逐字表达 + 自纠错
- ❌ 主动求知/玩乐(Phase 9 补)
- ❌ 对照护者依恋(Phase 9 补)
- ❌ 共情他人感受(Phase 9 补)

### 17.2 Phase 9 完成后(backlog)

继承 v4 §20-§28 全部 9 个哺乳类机制 + 对应**3-5 岁幼童的心智深度**:
- ✅ 主动求知/玩乐/探索
- ✅ 老用户/新用户区分 + 依恋
- ✅ 共同注意 + 共情他人
- ✅ 受挫/无助后的"我说啥都被骂干脆不说"
- ✅ 痛持续记忆 + 睡眠学习

### 17.3 Phase 10+ (真实多模态产品化)

真实摄像头/麦克风感受器 + 桌宠 UI(SNS 经验复用)+ 桌面感受器 + Agent 工作流。

---

## 18. v5 最终判断:是否能达成最终预期目标?

### 18.1 最终预期目标(用户原话)

> 多模态概念组合及范式实时学习能力的多模态自由对话拟人底座的实现。让它尽可能接近人类幼童的学习能力。

### 18.2 v5 可达性逐项判定

| 目标维度 | v5 设计是否支持 | 风险点 |
|---|---|---|
| 多模态(视/听/文)感受 | ✅ §3-§5 通道注册表 + sensor adapter | 真实视觉摄像头延后到 Phase 10,Phase 8 用合成图像 |
| 概念组合(词汇=任意 SA 组合) | ✅ §2 SparsePairwiseGraph + ΔP 晋升 | 关键依赖 §6.2 对照课程质量,需 Phase 8.8 实测 |
| 范式实时学习 | ✅ §6.3 slot 偏好统计涌现 + §2.4 链式延展 | 实测前不能保证泛化稳定 |
| 多模态自由对话 | ✅ §16.9 草稿行动竞争 + §1.2 字符微事件 + §11.7 novelty | Phase 8.9 自然纠错决定对话质量 |
| 拟人底座 | ✅ 习惯化 + 不确定/惊/熟悉感受 + 焦点 + 短长记忆 | Phase 9 才补主动性/情感深度 |
| 类人幼童学习能力 | ✅ Phase 8 = 18-30 月龄;Phase 9 = 3-5 岁 | 分层路径清晰 |

### 18.3 关键风险

**最大风险:**

**R1 - 对照课程能否提供干净 disentanglement**

§6.2 的成功依赖训练数据"颜色和形状真正可分"。如果合成图像里红苹果的红色总是有特定的纹理偏好(因为合成器作弊),系统可能学到"颜色=纹理+色调"而非纯颜色。

**缓解**:用 PIL 或 cv2 合成时严格控制颜色通道独立,加 randomize 防伪。每张图独立采样 HSV 值。Phase 8.8 测试时验证 C1/C2 ablation 真的能分离。

**R2 - ΔP 晋升门是否真能阻挡假固化**

如果 held-out 数据集太小或与训练分布太接近,假固化也能让 ΔP > 0。

**缓解**:held-out 严格用未出现过的样本,Phase 8.4 验收门必须包含**故意构造的"看似有 PMI 但无效"**反例(如"红色 + 苹果 + 桌子" 同 tick 大量出现但"桌子"与苹果无任何概念关联)。

**R3 - APV2 模块复用产生隐性偏置**

APV2 各模块写时假设的 SA 语义(episode_id / focus_id / modality)在 v5 新 SA 系统下可能错位。

**缓解**:§16.10 每个 adapter + 红线扫描 + Phase 8.2/8.3 每个 adapter 单独跑回归测试。

**R4 - 自然对话流的"惊不够"**

如果习惯化 emerge 太快,novelty_residual 衰减太快,系统看到新东西只惊一瞬就麻木。

**缓解**:§11.3 novelty_residual 半衰期默认 3 秒 + Phase 8.10 经验验证。

### 18.4 总判断

**v5 设计在数学链路上足够支持最终目标。Phase 8 完成时,系统已经是"会学习的拟人对话底座",具备人类 18-30 月龄幼童的概念组合学习能力**。

Phase 9 完成后,系统具备 3-5 岁幼童的心智深度。

最大不确定性不在数学,**在对照课程的工程质量** + **ΔP 晋升门的反例覆盖度**——这两点必须 Phase 8.8 严格验收。

---

## 19. v5 给 Codex 的最终指令

1. **本稿(v5)取代 v4 作为 Phase 8 实施依据**。v4 §20-§28 移到 Phase 9+ backlog,Phase 8 期间不实施
2. **Phase 8.5 (CFS 补完)是阻断式前提**——继承 v4
3. **Phase 8.8 (对照课程黄苹果) 是核心证伪门**——失败时不许调阈值过
4. **每个 Phase 走完整 5 段闭环**(设计→审查→落地→验收→报告)
5. **任何"新模块/新公式形态"提议必须先停下问 Claude**——v5 承诺全部复用既有底座
6. **审计库红线扫描必须每 Phase 跑**:`grep "audit_db" runtime/cognitive/` 必须 0 命中
7. **slot 偏好红线扫描**:`grep "slot.type_preference\s*=\s*{" runtime/` 必须 0 命中(除测试 fixture)
8. **诚实门**:任何 Phase 验收失败,**不许找 workaround 让它过**,必须找根因 + 提议设计修正

---

## 20-28. 哺乳类心智维度 backlog(沿用 v4 §20-§28)

**整体推迟到 Phase 9+**。v4 §20-§28 全文作为 backlog 远景图谱保留,在 Phase 8 完成后启动。

参见 `Design_APV3.0_Humanlike_Multimodal_Foundation_v4_20260617.md` §20-§28。

---

— 接手线程,2026-06-17

## 附录 A: v5 相对 v3/v4 的删减明细

为避免膨胀,记录哪些被"分层 backlog"而非真删:

| v4 章节 | v5 处理 |
|---|---|
| §11.7 novelty_residual | ✅ 保留主线(Phase 8.10) |
| §12.5 sleep emerge | ✅ 保留主线(Phase 8.10) |
| §13.5 filterbank | ✅ 保留主线(Phase 8.12 音频时) |
| §13.7 audit_db 重定位 | ❌ **被 §10 严格化覆盖**(Codex C-4 fix) |
| §14 percept-centric WTA | ✅ 保留主线 |
| §15.1 双层 align | ✅ 保留主线(Phase 8.13 验收) |
| §15.2 deja_vu | ✅ 保留主线(自然 emerge,Phase 8.13) |
| §15.3 idle 漫游 | ✅ 保留主线(ResidualTracker idle gate) |
| §16.4 CFS 补 4 通道 | ✅ 保留主线(Phase 8.5 阻断前提) |
| §20 驱力 | ⏸ Phase 9.1 backlog |
| §21 RPE | ⏸ Phase 9.2 backlog |
| §22 受挫 | ⏸ Phase 9.3 backlog |
| §23 依恋 | ⏸ Phase 9.4 backlog |
| §24 共同注意 | ⏸ Phase 9.5 backlog |
| §25 共情 | ⏸ Phase 9.6 backlog |
| §26 痛持续 | ⏸ Phase 9.7 backlog |
| §27 重放 | ⏸ Phase 9.8 backlog |
| §28 玩乐 | ⏸ Phase 9.9 backlog |

**总结**:v5 主线 = v4 的多模态认知闭环(全部修复 + Codex 5 大 blocker fix);v4 的 9 个哺乳类心智 → Phase 9+ backlog。**没有真删,只有分层**。

## 附录 B: Codex 5 大 blocker 修复对照表

| Codex 论点 | v5 修复位置 | 验收门 |
|---|---|---|
| C-1 黄苹果数学证据不足 | §6.2 对照课程 | Phase 8.8 + C1/C2 ablation |
| C-2 slot 偏好人工 schema | §6.3 统计涌现公式 | §6.3 grep slot.type_preference |
| C-3 PMI 爆炸 + 巧合 | §2.3 稀疏 pairwise + ΔP held-out | Phase 8.4 反例覆盖 |
| C-4 audit_db 隐藏完美记忆 | §10 严格只渲染 + 红线脚本 | grep audit_db in cognitive/ |
| C-5 模态平权边界 | §3.2 sensor adapter 总图 | grep modality in cognitive/ |
| C-6 §20-§28 推迟 | §16.3 Phase 9+ backlog | Phase 8 实施时不许碰 |
| C-7 文本字符微事件 | §1.2 + §16.8 | Phase 8.2 实测 |
| C-8 草稿行动竞争 | §16.9 | Phase 8.2 行动竞争实测 |
| C-9 APV2 adapter | §16.10 | 每模块独立回归测试 |
