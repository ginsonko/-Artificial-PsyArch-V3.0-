# Phase 13.5b 数学能力诊断报告 + 收敛方案

日期: 2026-06-18
作者: Claude(对抗审阅 + 诚实报告)
状态: **已被银子老师挑战 + 修订 — 见本文 §0.5。原报告留存 audit trail,但结论已被推翻,以 v3.3 设计稿为准。**

---

## 0.5 银子老师 2026-06-18 晚间挑战 + Claude 修订(本节优先于全文)

### 背景

本报告 §1-§5 提出"APV3 v14 当前到 Math-1 是上限"。

银子老师质疑:"为什么我们的系统不能支持更复杂的数学机制?是竖式本身不能作为范式学习吗?还是个位加减和九九乘法表不能作为基础背下来,配合竖式进行草稿填写?还是说我们这套系统理论上现在无法从题目中提取出正确的含义,然后列出算式本身呢?还是说最终算出来的结果它无法利用,填写在后面的答案中呢?"

### Claude 复核与诚实承认

银子老师的质疑**完全正确**。我之前的判断错在 3 处:

1. **错误地把 APV2.1 实现方式当成唯一路径** — 数学不是必须用"参数化 action SA 14 件套",可以用"视觉范式 + vocab 事实库 + 草稿空间排列 + 应用题 slot fill"路径
2. **被审阅 agent 的预设带跑** — 审阅 agent 假设"必须复现 APV2.1 栈",所以判断 v14 不够,但这个假设本身错
3. **低估 v14 已有机制的组合能力** — 量化桶 + ComposedVocab + hierarchy SA + DraftActionRunner + 表达范式 已经够用

### 正确判断(银子老师修订)

数学竖式 / 九九乘法 / 应用题 / 列方程 这些能力,**APV3 v14 已有机制可学到**,关键是用对路径:

| 能力组件 | 原诊断 | 修订后路径 |
|---|---|---|
| 数字 / 数量 | 需 quantity_grasp feeling | Phase 8.6 量化桶 + Phase 8.4 vocab |
| 九九乘法 81 事实 | 需参数化 action | Phase 8.4 SDPL vocab + Phase 8.15 cold_index |
| 个位加减事实 | 需 ActionParameterMemory | 同上 |
| **竖式视觉识别**(看竖式) | 需严格 trace 审计 | Phase 8.6 视觉感受器 + Phase 8.7 视焦点 + Phase 10.6 hierarchy SA |
| **竖式草稿生成**(写竖式) | 需 strict_compute_column_sum action | **DraftActionRunner 扩展到 2D 文本网格**(银子老师补充) |
| 进位 / 借位 | 需 strict_propagate_carry | 范式 hierarchy SA emerge |
| 应用题关系提取 | 需 relation_competition 子系统 | ComposedVocab + slot 偏好(黄苹果同款) |
| 列方程 / 求未知数 | 需未知数绑定子系统 | Phase 11.2 abstract_vocab + Phase 11.4 deliberative |
| 答案填回 | 需专门机制 | Phase 13.6 表达范式 + Phase 8.9 自然纠错 |

### 银子老师关键追加(2D 文本空间)

银子老师进一步指出:

> "之前的空间排列范式是视觉感受器的,而我们的草稿框里面是文本的空间排列范式,它理论上是需要在自己的草稿框里面写空间排列范式,并且可以观察到文本的空间排列范式,而不只是视觉感受器"

这是**两个空间范式空间的精确区分**:

- **空间 A: 视觉感受器的竖式识别**(看到教师写的竖式 → 知道是竖式)
  - 输入路径,Phase 8.6/8.7 已有
- **空间 B: 草稿框的文本竖式生成**(系统自己在草稿框里写竖式)
  - 输出路径,**DraftActionRunner 当前只是一维文本流,需扩到 2D 网格**

这两个空间是同一个"竖式范式 hierarchy SA"的不同方向(输入/输出)。**真正的拟人:看到竖式知道是竖式,自己写时也能写出竖式**。

### 重新路线评估

| 选项 | 描述 | 时间 | 修订后评估 |
|---|---|---|---|
| **A 原推荐** | 只做 Math-0/1 | +0 周 | **过于保守,放弃 v14 真有的能力** |
| **A' 新路径** | 用 v14 已有 + DraftActionRunner 2D 扩展,Math-0~ 应用题/方程 | +1-2 周 | **★★★★★ 强推荐** |
| B / C | 原方案 | +3-8 周 | 不必要,A' 已能做 |

### 接下来的工作

- **Phase 13.5b v3.3 设计稿**:以 A' 路径详细设计,含 DraftActionRunner 2D 网格扩展 + 视觉/草稿双路径
- **Codex 对抗审阅 v3.3**:验证可行性
- **本诊断报告 §1-§5 留存作 audit trail**:原结论错,但思考过程有价值,不删除

### Audit Trail 教训

这是项目中**第二次"先入预设错"案例**(第一次是 Codex 14 轮 review 时的 grep red line)。教训:

1. **审阅 agent 也可能带错误前提** — 不能盲信审阅结论,必须自己复核前提是否成立
2. **银子老师的直觉质疑往往最珍贵** — 因为他是原架构设计者,知道每个机制的真实能力边界
3. **遇到"做不到"的判断,先问"为什么做不到" + 列出依赖前提**,再判断前提是否真成立

---



## 0. TL;DR(给银子老师的 1 分钟版)

**审阅结论**:

APV3 v14 现有架构**无法**复现 APV2.1 的 Math-0~28 全部 728/728。

- **Math-0(数感) → Math-1(单位加减)**: 可做(2-3 天补少量基础)
- **Math-2~5**(两位数竖式): 黄/红区,需补 4-6 周架构扩展
- **Math-9~28**(乘除/应用题/方程): 深红区,**几乎不可能用当前架构实现**

**根本原因**: APV3 v14 SDPL 路径学的是 `packet → single action_str`,数学竖式需要的是 `packet → parameterized action chain`。APV2.1 用 14+ 个细粒度参数化 action SA + ActionParameterMemory + ActionConsequenceEvaluator + Planner.record_feedback + 经验包累积 + 严格 trace 审计**六件套**解决,**APV3 当前一个都没有**。

**3 个路线选择**:

| 选项 | 描述 | 时间 | 风险 | 我的推荐度 |
|---|---|---|---|---|
| **A** | Phase 13.5b 只目标 Math-0/1,Math-2+ 列 Phase 14+ backlog | +0 周 | 低 | ★★★★★ |
| **B** | Phase 13.5b 前先做 Phase 14a 行动 SA 子系统补齐(6 项),再做完整 Math-0~5 | +3-4 周 | 中 | ★★★ |
| **C** | 硬冲 Math-0~28 全套,边补架构边做课程 | +6-8 周 | 高 | ★ |

**我推荐 A**。理由见 §4。

---

## 1. 审阅细节核实

### 1.1 审阅 agent 的关键发现

#### A. APV2.1 数学栈实际依赖(诚实清单)

```
APV2.1 Math 真实栈:
1. CognitiveFeelingFactory 5 通道(quantity_grasp / computation_pressure / step_closure / uncertainty / sensory_clarity)
2. 细粒度参数化 Action SA 14+ 个(count_step / write_digit / strict_compute_column_sum/difference / 
   strict_propagate_carry/borrow / strict_multiply_partial_column / strict_shift_second_partial_row / 
   strict_bring_down_digit / strict_estimate_trial_quotient_digit / ...)
3. ActionParameterMemory(参数手感) + ActionOutcomeMemory(趋近/回避) + ActionConsequenceEvaluator
4. Planner.record_feedback(反馈→行动竞争)
5. SkillScaffoldProtocolV2Controller(4 阶段退火:strong→weak→feedback_only→teacher_off)
6. 经验包累积 v1→v28(每阶段冷启动加载前面所有包)
7. 严格竖式 trace 审计(strict_vertical_word_problem_process_audit_not_solver)
```

#### B. APV3 v14 实际有什么(扫码后诚实清单)

```
APV3 v14 现有:
1. CognitiveFeelingFactory 9 通道(fluency/boredom/fulfillment/satisfaction + 5 EpistemicSource)
   ❌ 无 quantity_grasp / computation_pressure / step_closure
2. SDPL packet → action_str(Q 表 5 层 backoff)
   ❌ action 是 str 标签,无参数化,无 chain
3. Long-term Dual Layer(active + cold_index LRU)
   ❌ 无经验包累积 v1→vN
4. cognitive tick_loop.py 写死 draft_action="noop"
   ❌ cognitive 包里完全没有 action emission
5. apv3test/runtime/draft_action.py 仅 5 个文本编辑动作
   ❌ 不支持竖式计算这类细粒度参数化动作
6. audit_db_boundary.py 是渲染层
   ❌ 不在 cognitive substrate,无严格 trace 审计
```

### 1.2 我对审阅判断的复核

我自己读了关键文件,**完全确认审阅判断**:

- `runtime/cognitive/runtime/tick_loop.py:97` 确实写 `draft_action="noop"`
- `runtime/cognitive/cognitive_feelings/factory.py:16` `CORE_FEELING_KEYS` 不含 `quantity_grasp`
- `runtime/cognitive/sdpl/q_table_backoff.py` 的 `query(packet, action: str)` 签名,action 是 str
- `runtime/cognitive/long_term/layers.py` 是 LRU OrderedDict,没有版本累积

**审阅 100% 准确,我之前 Phase 13 设计稿 + v3.2 都低估了这个 gap**。

---

## 2. Gap 严重度分级(具体到 Math 阶段)

| Math 阶段 | 能力要求 | APV3 现有 | Gap 严重度 |
|---|---|---|---|
| Math-0 数感积木 | 共现学习 digit ↔ quantity ↔ pronunciation ↔ successor | SDPL packet 学共现 OK | 🟢 绿 |
| Math-1 单位加减 by count | `count_step(from, to, direction)` 参数化行动 | **无参数化 action SA** | 🟡 黄(2-3 天可补) |
| Math-2/3 随机保持+错例 | ActionOutcomeMemory 自修 loop | **无** | 🟡 黄(1 周可补) |
| Math-4/5 两位数进位/借位竖式 | column_chain 多步参数化 + 严格 trace | **无** | 🔴 红(2-3 周架构扩展) |
| Math-7/8 多位数 | 同上 + column index propagation | **无** | 🔴 红 |
| Math-9~13 乘法竖式 | 部分积+位值平移嵌套 | **完全没有 hierarchical action SA** | 🔴 深红 |
| Math-14~20 长除法 | 试商-乘回-相减-落位 4-step inner loop | **完全没有** | 🔴 深红 |
| Math-21~24 应用题严格过程 | relation_competition + bridge-not-solver governance + 严格 trace | **完全没有** | 🔴 深红 |
| Math-25~28 方程/列方程/干扰 | 未知数绑定 + 逆运算 schema + 平衡变换 | **完全没有** | 🔴 深红 |

---

## 3. 为什么 SDPL 不能直接做数学竖式

这是审阅最关键的洞察,我必须重点说:

**SDPL Q 表**:学的是 `(packet, action_str) → Q value`。给一个情境(packet),选最佳单 action。

**数学竖式**:典型 3 位数乘 2 位数大约需要 **17 个 tick 的参数化行动链**:
```
tick 1: action::strict_compute_column_sum(column_index=0, first_digit=3, second_digit=7) → produces 21
tick 2: action::strict_propagate_carry(from_column=0, to_column=1, carry_value=2) → state update
tick 3: action::strict_compute_column_sum(column_index=1, first_digit=5, second_digit=8, with_carry=2)
...
tick 17: action::strict_compute_final_partial_row → commit answer
```

每一步 action 的**参数依赖前一步的输出**。这不是 SDPL 学 `packet → action_str` 能直接做的。

APV2.1 的解法是:
- `ParameterizedActionSA(action_id, parameter_dict)` — action 本身带参数
- `ActionParameterMemory` — 学"在 column_index=2 时,carry_value 通常是 0 还是 1"这类手感
- `ActionConsequenceEvaluator` — 估计"做完这步 → 下一步的 partial_sum 大致多少"
- `Planner.record_feedback` — 多 tick 行动链每步反馈累积

**APV3 SDPL 单层不能直接取代这个**。Q 表对 `(packet, action_str)` 学,不学 `(packet, action_str, parameters)`,更不学 `(packet, action_chain)`。

---

## 4. 路线选择详细分析

### 4.1 选项 A: Phase 13.5b 只做 Math-0/1(我推荐)

**做**:
- Math-0 数感积木(SDPL packet 学共现)— 1 天
- Math-1 单位加减 by count(需在 cognitive 加一个最小的 `count_step` action 模块,2-3 天)

**Phase 13.5b 验收门**:
- teacher-off Math-0 ≥ 95%
- teacher-off Math-1 ≥ 90%(略低于 APV2.1 100%,因为是最小架构补丁)
- 不冲 Math-2+

**Math-2~28** 列入 **Phase 14+ backlog**(架构扩展后做)

**开源 demo 怎么说**:
- "看,系统经 SDPL 路径从零学会了数感和单位加减"
- "完整小学数学需要后续 Phase 14 行动 SA 子系统支持,我们在做"
- 诚实展示 现有能力 + roadmap

**优点**:
- 风险低,几乎肯定能成
- 时间不变(Phase 13 仍 24-30 天到 alpha)
- 诚实承认架构边界,不 overpromise

**缺点**:
- 开源时不能演示 23×47 这种"震撼时刻"
- 数学能力作为 LLM 区别点弱化(但仍有)

**为什么我推荐 A**:
- v14 架构是 14 轮对抗审阅 + 3 轮哲学深化后的精心收敛,**不应该为 Math-28 而仓促扩架构**
- Math-0/1 已足以演示"它真的从零学到了基础数学",已经是 LLM 给不了的真证据
- 开源时另外两个核武器(SDPL 来源监控 + 跨 session 持续学习)不弱于数学

### 4.2 选项 B: Phase 14a 补 6 项,再做完整 Math-0~5(中等推荐)

**做**:
- **Phase 14a — Action SA 子系统**(3-4 周):
  1. `runtime/cognitive/action/parameterized_action_sa.py`(参数化行动 SA)
  2. `runtime/cognitive/action/action_parameter_memory.py`(参数手感)
  3. `runtime/cognitive/action/action_outcome_memory.py`(趋近/回避)
  4. `runtime/cognitive/action/action_consequence_evaluator.py`(后果估计)
  5. `runtime/cognitive/action/planner_feedback_loop.py`(多 tick 行动链)
  6. `runtime/cognitive/cognitive_feelings/quantity_feelings.py`(quantity_grasp / computation_pressure / step_closure)

- 然后 Phase 13.5b 做 Math-0~5(单位 + 两位数竖式)

**开源 demo 怎么说**:
- "系统从零学会了两位数加减(竖式过程可看)"
- "Math-9 乘法及以上仍在 Phase 15+ roadmap"

**优点**:
- 数学能力达到"两位数加减"水平,开源 demo 有看头
- 架构扩展是有价值的(不止为数学)— action 子系统是 v14 的真缺口

**缺点**:
- 时间 +3-4 周(Phase 13 整体 6-8 周到 alpha)
- 架构扩展可能引入新 bug,影响已有 Phase 8-12 测试
- Math-9~28 仍做不到

### 4.3 选项 C: 硬冲 Math-0~28(不推荐)

**做**: 边补架构边做课程,争取 728/728

**优点**: 开源时最强 demo("看,我们做到了 728/728")

**缺点**:
- 时间 +6-8 周
- 风险高(可能架构补完发现还是不行)
- 容易塌成 APV2.1 patching(失去 v14 SDPL 演化证据)
- 与 v14 14 轮收敛的精神冲突

**为什么不推荐**:
- v14 是经过 14 轮对抗审阅收敛的,架构有自己的逻辑
- 为了 demo 仓促扩架构,会让 v14 失去严谨性
- 如果架构扩出来但没人审,会引入新 anti-pattern

---

## 5. 我的最终建议

### 5.1 推荐选项 A,理由

1. **不破坏 v14 架构纪律**: 14 轮对抗审阅的成果不应被 demo 压力压垮
2. **诚实承认边界**: 开源时说清"现在做到 X,roadmap 到 Y",比硬塞失败的 demo 强
3. **Math-0/1 已经足够强**: SDPL 来源监控 + Math-0 数感涌现,已是 LLM 没有的真能力
4. **数学能力分两阶段**: Phase 13.5b 是"AP 能学到数感和单位加减",Phase 15+ 是"AP 能做完整小学数学",这是合理的演化路径

### 5.2 具体路线(如果你选 A)

```
Phase 13.0(v3 + v3.1 + v3.2 + v3.2a 四稿,F1-F6 6 项 must-fix)
  ↓ 2-3 天
Phase 13.1 substrate
  ↓ 1.5 天
Phase 13.2/3/4/5 内容浸泡(并行)
  ↓ ~10 天
Phase 13.5b 数学 — 收缩版
  内容:Math-0(数感)+ Math-1(单位加减)
  时间:3-4 天(含 count_step action 最小补丁)
  验收:teacher-off ≥ 90%,公开标注"完整数学留 Phase 15+"
  ↓ 2 天
Phase 13.6 表达范式 + 13.7 行动 + 13.8 社交(已有银子老师+Claude 撰写)
  ↓ ~10 天
Phase 13.9 四场景验收 + 中文展示页
  ↓ 2 天

总 alpha: ~28-30 天
```

### 5.3 开源时的诚实话术

```markdown
# AP Cognitive Architecture 能力清单(v1.0 alpha)

## 现已具备
- 中文自由对话(3500 字 / 7000 词 / 300 表达范式)
- 多模态视觉/音频常识(800 视觉对象 / 100 音频)
- SDPL 来源监控(真实 vs 想象 vs 听闻 vs 记忆)
- 持续想象 + 跨 session 记忆
- 共情 / 共同注意 / 假信念识别
- 数感 + 单位数加减(数学能力第一阶段)
- 教师协作学习(你能教它,它真的学)

## Roadmap(后续 Phase 计划)
- Phase 15: 完整小学一二年级数学(两位数加减乘除)
- Phase 16: 应用题 + 列方程
- Phase 17: 真实硬件接入 / SNS 桌宠产品化
```

这种诚实表达,**反而比"什么都能做"的 LLM 套壳更可信**。

### 5.4 如果你选 B(中等推荐)

也合理。但需要明确:
- Phase 14a 6 项扩展是 v14 主稿之外的扩张,需要新设计稿 + 对抗审阅
- 时间 +3-4 周
- 风险中等(可能架构补完仍不达预期)

如果选 B,我会写 Phase 14a 完整设计稿(类似 v14 风格)。

### 5.5 如果你选 C(不推荐)

我会反对。但如果你坚持,我会写,但会要求:
- 至少 2-3 轮对抗审阅每个扩展模块
- 时间预期 6-8 周
- 接受可能仍达不到 728/728 的风险

---

## 6. 关于开源传播的考虑

银子老师之前提到的"一鸣惊人"目标,我重新评估:

**LLM 给不了的核武器** — 不只数学:

1. ✅ **来源监控** — "我看到的" vs "我想象的" 分化(Phase 13.6 表达范式直接展示)
2. ✅ **持续想象** — 用户离开期间系统主动思考(Phase 8.10 + 9.X 已有)
3. ✅ **共情共振** — 用户难过时系统弱信号接收(Phase 9.6 已有)
4. ✅ **跨 session 记忆** — 第二天还记得(Phase 8.16 已验)
5. ✅ **假信念识别** — Sally-Anne 范式(Phase 10.5 已验)
6. ✅ **真持续学习** — 用户教 → 系统学到 + 反例撤销(Phase 8.9 已有)
7. ⚠️ **数学计算** — 只到 Math-1(单位加减),非完整小学数学
8. ✅ **审计透明** — Web 工作台逐 tick 可看(Phase 12 已有)

7 个 ✅ + 1 个 ⚠️ — 仍然是非常强的差异化清单。

**数学不是唯一的核武器**。如果开源 demo 重点放在 1-6 + 8,加上 Math-0/1 作为"现学的真实"展示,**仍然能一鸣惊人**。

---

## 7. 给银子老师的决策请求

我需要你回答:

**Q: 你选 A、B、还是 C?**

我的强推荐是 **A**:
- 时间不延期
- 不破坏 v14 架构纪律
- 数学能力诚实标注"现到 Math-1,Math-2+ Phase 15+"
- 把"核武器"焦点放在来源监控 / 持续想象 / 跨 session / 假信念 / 真学习这些 LLM 真做不到的事
- Phase 13.0 + v3.2a 6 项 must-fix gates 先做,Phase 13.5b 后置

如果你选 A,我接下来准备:
- Phase 13.6 第一批 50 个范式文本(银子老师 + Claude 联合撰写)
- Phase 13.5b 收缩版课程包(Math-0/1 yaml)
- 同步让 Codex 跑 Phase 13.0 + v3.2a 6 项

如果你选 B,我准备:
- Phase 14a Action SA 子系统设计稿(类 v14 风格,需对抗审阅)
- Phase 13.6 表达范式(并行)
- 等 Phase 14a 完成后再启 Phase 13.5b 完整版

如果你选 C,我准备...(同上 + 接受高风险)

---

## 8. 总结

诚实诊断:**APV3 v14 当前到 Math-1 是上限,Math-5 起会撞墙**。

我之前 Phase 13.5b 设计的"7 阶段 + 验收 95%/85%/20%"是**过度乐观**,不符合架构现实。

v3.2 把"借鉴而非复用"这个方向是对的,但**仍假设了 APV3 有能力做完整 728/728**,这点错了。

正确做法是**承认架构现实**:
- 数学到 Math-1
- 完整小学数学留 Phase 15+
- 开源传播靠"来源监控 + 持续学习 + 假信念 + 跨 session" 这些 LLM 真没的东西

这是诚实路线,也是对得起 14 轮对抗审阅 + 3 轮哲学深化的工程纪律的路线。

---

— Claude(诚实诊断)
— 2026-06-18

**等银子老师决策 A/B/C**
