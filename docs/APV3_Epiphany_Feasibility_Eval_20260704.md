# AP "灵光一现" 可行性评估

> 评估对象：用户提的灵光一现假设——"瞎想时两件事同时进入短期结构流 → 泛化召回出同时关联到这两件事的事 → 灵光一现的创新"。
> 评估基准：当前 `apv3test/runtime/phase20_7/runtime.py` 引擎实现（20260704）。
> 评估结论：**理论上演得通，引擎上做不到。**

---

## 0. 用户的假设（按 AP 理论复述）

```
瞎想（idle / 回味 9f）
   ├─→ 主题 A 进入短期结构池 SSP
   └─→ 主题 B 进入短期结构池 SSP
            ↓
        状态池针对 A∪B 联合签名做泛化召回（B/C/C*）
            ↓
        召回到的是"既沾 A 也沾 B"的第三件事 ←【这就是灵光一现】
            ↓
        新剧情/新类比/新解法被写入经验流 → 创新
```

这条链路要成立，必须有四个工程前提：

1. **并发多主题**：idle 状态下 SSP 里能同时有 ≥ 2 个不同回味主题活着；
2. **联合签名召回**：状态池的 c_forward/c_backward 拿到的不是单一主题签名，而是 A∪B 联合签名；
3. **跨域泛化**：召回函数对"同时沾两域"的事件给增量支持（这就是"既像 A 又像 B"才被选中的机制）；
4. **创新写入**：选中的"既沾 A 又沾 B"的事件被作为新经验写回，后续 turn 才能把它说出口。

---

## 1. 评估——逐条对应当前实现

### 1.1 多主题并发 SSP — **做不到**

`_short_structure_flow_attention_bias`（runtime.py:9085）只取 **最新一条** SSP 出现：

```python
latest = _latest_short_structure_flow_occurrence(...)
if latest is None:
    return {"active": False, ...}  # 历史 0 时直接停机
```

返回的 `attention_bias` 单调来自 `latest` 这一条——它的 `active` 标志、`source_kind` 都只有那一个值。9f 回味（`_run_idle_learning_review_tick` runtime.py:3424）只把单条 `review = dict(learning_loop_carryover.get("idle_learning_review", {}))` 写进这一条 SSP——`narrative_text` 是**单主题**叙事。

未闭合张力（unclosed）这条更狠：第 2871-2876 行直接 `ORDER BY u_value DESC LIMIT 1` 取最大那一个；`unclosed_drive` 当前还被硬编成 `0.0`（M4-3 尚未激活，见 runtime.py:4023 注释）。

→ **结论：idle 时只有一个主题在 SSP 里。** 没有第二股 STREAM 跟它同框。

### 1.2 联合签名召回 — **做不到**

`_idle_learning_review_c_forward`（runtime.py:11042）写出来的 c_forward 是单元的：

```python
target_text = str(review.get("target_text") or "").strip()
return ({
    "kind": "idle_learning_review_continuation",
    "predicted_text": target_text,
    "support": max(...readiness...),
    ...
},)
```

签名 = 单一回味主题的 target_text。下一 tick 的 B/C/C* 召回就是拿这单一签名去匹配经验流——不会出现"主题 A  OR  主题 B"那种宽泛捕捉，更不会出现"A∩B"那种二阶联合匹配。

### 1.3 跨域泛化召回 — **部分能做**

`_semantic_text_overlap_with_units`（runtime.py:2745 起）确实是单元覆盖度打分，**单个** query 落到多个 alignment_event 上时，`selected` 最多取到 3 个候选（runtime.py:2784 `if len(selected) >= 3`），并累计 `covered_units`——这是泛化召回的雏形。

但这条机制是给**单一 query** 找多命中，而 query 的来源是上面 1.2 那个单一 target_text。它泛化召回的对象是"在文本单元上跟 A 重合的经验"。**没有一处地方把 A∪B 当成 query**，所以"既沾 A 又沾 B"的第三件事根本进不了候选池。

### 1.4 创新写入 — **机制在，但喂不进真信号**

写回经验流的事件（`_observe_pool`、SSP `idle_flow`、`insert_experience_event`）路径本身 OK——只要 1.3 能选出"泛化来的新事件"，是写得回去的。问题只出在上游喂不进信号。

最后再补一刀：`_idle_learning_self_test_from_short_structure_flow`（runtime.py:11086-11089）:

```python
if current_alignment and previous_alignment and current_alignment != previous_alignment:
    return {}  # 当前/上一回想不是同一对齐事件就完全放弃自我测试
```

这条更显式：**变动主题就直接 short-circuit**——架构是有意把 SSP 拉成单焦流。

---

## 2. 缺口清单

| # | 缺口 | 当前在哪儿 | 应该改成什么 |
|---|------|------------|------------|
| G1 | SSP attention 只看 1 条 latest | `_short_structure_flow_attention_bias` runtime.py:9091 | 改成把最近 N 条 SSP 合取地叠在 bias 上；或至少在 `idle_think_drive_delta` 上让 theme-A 的 review 和 theme-B 的 review 同时贡献 |
| G2 | 9f review 单主题 carryover | `idle_learning_review` 单 dict（runtime.py:3438） | 改成 `idle_learning_reviews: [A, B]`，每个 tick 推一个主题，让 carryover 留两条活过 |
| G3 | c_forward 是单一签名 | `_idle_learning_review_c_forward` runtime.py:11042 | 增加一种 `idle_learning_review_joint_continuation`，把两个 target_text 拼成联合 query，喂给 `_semantic_text_overlap_with_units` |
| G4 | 召回无联合支持增量 | runtime.py:2757 `coverage_ratio` 公式 | 增一条 "joint_overlap_bonus"——同一候选事件对 A、B 两个 query 都被覆盖时，`support += 奖励`（这就是"既像 A 又像 B"被压高） |
| G5 | 9g 拒绝跨主题 | runtime.py:11086 早返 | allow 9g 在 idle 跨主题时改为做"联合自测"——对 A、B 联合找一个事件估把握，不必非得当前回流同主题 |
| G6 | M4-3 unclosed 硬编 0.0 | runtime.py:2975、3002，注释见 4023 | 这是另一条独立 subject-agency 通路，激活它之后"瞎想"里那种"还没解决的问题自动冒出来"才有力——但这条与"灵光一现是双主题汇合"是平行的，激活了也未必能让 A∪B 同时出现 |
| G7 | 没有"复合主题产物"显式标识 | 现有的 `source_kind="learning_review"` 单分类 | 加 `source_kind="epiphany_joint_review"`，让 UI/经验流能识别"这是创新"，并给一道独立认知感受通道奖励（创新=发现新的关联） |

---

## 3. 评估结论

**理论上：可以实现。** 假设链路（A+B → 联合泛化召回 → 既沾 A 又沾 B 的第三件事）确实是 AP 架构"瞎想"产生本质新意的合理来源。这也是白皮书里"短结构池印象回环 + 视觉想象 + 认知感受"那套机制的自然引申。

**引擎上：现在还做不到。** 三个关键前提全部不满足：

1. idle 没**多主题同时活**在 SSP 里（架构就用 LIMIT 1 把它压成单焦流）；
2. c_forward 拿的是**单签名**（target_text 单字符串），从未构过 A∪B 联合 query；
3. 召回路径里**没有 join 支持增量**——同一事件被 A、B 都沾时不会得到奖励，没法把它从候选池抬出来当"灵光"。

```
得分卡：
  理论可行度     ████████████████████  95/100  ← 与白皮书一致
  工程实现度     ████                  20/100  ← 现在 G1+G2+G3 缺口都在
  演示可看度     █                     10/100  ← 上面 idle 演示能看到单主题回味，看不到双主题汇合
```

---

## 4. 要做出"灵光一现"应做的最小补丁

1. **G1 改双活 SSP**：让 `_short_structure_flow_attention_bias` 取最近 2 条 `learning_review` 出现，把它俩的 `support*recency` 都算进 attention（叠加，不取最大）；
2. **G2 改双主题 carryover**：`learning_loop_carryover.idle_learning_review` 改成数组（或加平行字段 `idle_learning_review_alt`），carrying 每条活过格衰减；
3. **G3 联合 c_forward**：见 runoff 一条 `kind="epiphany_joint_continuation"`，签名为 `target_text_A + " " + target_text_B`；
4. **G4 联合召回奖励**：在 `_semantic_text_overlap_with_units` 后插一个"双 query 都覆盖该候选就 +0.18"的小补丁；这是创新识别的最少代码量；
5. **G7 标创新**：被联合召回 + 双 query 都沾的事件，写回时打 `is_epiphany=true` 标志，前端"详情"页给一道"灵光"高亮。

补完上五条以后，再按 9f → idle 几十轮 → 看会不会冒一句"既像 A 又像 B"的话。这才是真"灵光一现"。

---

## 5. 与当前前端演示的关系

目前的"看它回味示例" `runReminisceDemo` 只能演示**单主题回味**——给一个 Teaching 门、挂机几轮、看 9f 重提它。这是诚实呈现。**需要等 G1-G4 引擎补完，再做"看它灵光一现示例"按钮**（先同时教 A、B 两件不相干的事、挂机足够多 idle、看会不会冒同时沾两件事的复合句）——否则就是骗用户。

> 本评估与当前前端代码（phase20_7_workbench.js / HTML）一致：现阶段在 UI 里没承诺"灵光一现"，引导卡 5 已诚实标注到 9f/9g 两机制 + 找新等环境接口待接。这条评估是下一步引擎补丁的 spec 输入。
