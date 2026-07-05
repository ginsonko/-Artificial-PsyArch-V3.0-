# Phase20.12c 纯文本输入视觉签名借取泄漏修复设计(已签批)

日期: 2026-06-30
状态: 已通过对抗性审查 + 用户签批,进入落地

## 0. 背景与现象

用户在前端 stage6 工作台实测:教完苹果/香蕉图片后,问纯文本"你是谁?"(无图、从未教过
该文本),系统答"是香蕉"。问"对"/"没错"/"这是?"也都答最近教的物品。白皮书 §269 把这命
名为"最近答案覆盖"——"如果系统总是说最近教过的词,那不是 AP,是最近答案覆盖"。

干净复现(已验证):清空 DB → 教一次"图片香蕉+这是?→是香蕉" → 问纯文本"你是谁?" →
答"是香蕉",B0 support 0.909,t55 触发 visual_imagination_recall。

## 1. 根因(runtime.py:399-407,已坐实)

纯文本输入"你是谁?"本 tick 无图 → `visual_signature = _visual_signature_from_events()`
= None → `_select_backward_attribution` 借历史香蕉窗口的 visual_signature → 赋给当前
observation(line 407)→ `_record_text_observation` 持久化带借来签名的观察 → 下游三路泄漏:

1. `_find_exact_b0` 看到 `observation.visual_signature` 非空 → 走 `_find_visual_exact_b0`
   → 视觉精确命中香蕉记忆 → 输出"是香蕉";
2. `_select_visual_imagination_recall` 触发 `visual_imagination_recall` tick;
3. `_observation_is_visual_reference_family` 返回 True → 绕过 B0 文本匹配门槛。

一处借取导致三重泄漏,根因是 runtime.py:406-407 的无条件借取。

## 2. 白皮书依据

- **§16.1**:「视觉感受器把图像/画布/桌面区域转为视觉 SAOccurrence」——视觉签名只能来自
  本 tick 视觉感受器输入,白皮书从未授权"纯文本观察从历史窗口借视觉签名当当前感知"。
- **§269**:「如果系统总是说最近教过的词,那不是 AP,是最近答案覆盖」——这正是该 bug 的
  白皮书命名。
- **§1210**:「看到苹果图却召回香蕉词,产生违和。C_backward 应从'当前像水果/被问这是
  什么/输出香蕉'这一历史相似现状向前传播,找历史上导致这种现状的前因……如果该解释被
  教师纠正,这条归因关系被惩罚」——C_backward 归因"我可能受刚教香蕉影响"是合理的,但
  归因结果**不应直接变成答案输出**。当前 bug 把归因借来的签名直接喂给 B0,让"最近教的
  香蕉"变成"当前问题的答案"。

## 3. 对抗性自审(关键:一刀切删除会破坏合法视觉指代)

### 3.1 第一次方案(一刀切删除 line 406-407)

**对抗性自审第 5 条"现有测试有没有依赖纯文本借视觉签名"答错**——只 grep 了
`assert.*visual_signature`,漏了两个 stage5 测试通过行为间接依赖借取:

- `test_stage5_text_reference_can_trace_back_to_recent_visual`:纯文本"刚刚图片是啥"教
  "绿色橙子",后续带同一张橙子图问"这个是什么"→期望召回"绿色橙子"。修前 tick2 借了橙子
  签名 → alignment 记录了视觉签名 → tick3 带同图视觉匹配命中。一刀切删除后 tick2 不借
  → alignment 无视觉签名 → tick3 召回失败。
- `test_stage5_idle_visual_focus_follows_latest_visual_imagination_not_last_image`:纯文本
  "苹果"期望触发 visual_imagination_recall 并让 idle 走 idle_visual_focus。

**结论:一刀切删除过宽,破坏了 §1210 合法视觉指代。**

### 3.2 合法与非法借取的区分(实测坐实)

| 场景 | backward source_kind | 查询 vs 视觉记忆输出 overlap | 借取应否 |
|---|---|---|---|
| "刚刚图片是啥"(合法,指代刚才图片) | recent_visual_window | 0.0(指代图片本身,非输出文本) | 应 |
| "苹果"(合法,指代教过的苹果) | recent_text_window | 0.435(>=0.34) | 应 |
| "你是谁?"(非法,最近答案覆盖) | recent_text_window | 0.091(<0.34) | 不应 |

两种合法指代:
1. `recent_visual_window` 命中——查询落到了视觉窗口,如"刚刚图片是啥"指代刚才的图片;
2. 查询与某条带视觉签名的 alignment 输出文本语义重叠 >= 0.34(与
   `_select_visual_imagination_recall` 同阈值),如"苹果"指代教过的苹果视觉记忆。

非法场景两个条件都不满足。

### 3.3 关键发现:_select_visual_imagination_recall 不依赖 observation.visual_signature

实测:`_select_visual_imagination_recall` 在 observation.visual_signature=None 时,
对"苹果"返回 True(overlap 0.435 过阈值),对"你是谁?"返回 False(overlap 0.091 不过)。
它靠 `_semantic_text_overlap_with_units` 工作,不需要借取签名。问题只在
`_find_visual_exact_b0`——它依赖 observation.visual_signature 直接命中。

## 4. 修复方案(勿增实体,用既有结构)

**runtime.py:399-407**:把无条件借取改为条件借取,新增 `_text_query_refers_to_visual_memory`
判据函数(只读取既有 experience_alignment,不新增实体):

```python
if (
    backward_attribution is not None
    and backward_attribution.observation.visual_signature
    and _text_query_refers_to_visual_memory(
        conn, query_text=user_text.strip(), session_id=session_id,
        backward_source_kind=backward_attribution.source_kind,
    )
):
    visual_signature = backward_attribution.observation.visual_signature
```

`_text_query_refers_to_visual_memory`:
- 若 `backward_source_kind == "recent_visual_window"` → True(§1210 视觉窗口指代);
- 否则遍历带 visual_signature 的 experience_alignment,用既有
  `_semantic_text_overlap_with_units`(与 `_select_visual_imagination_recall` 同 0.34 阈值)
  判定查询是否语义指代某视觉记忆;
- 用 visual_signature=None 的临时 observation 调
  `_unified_experience_candidates_for_observation`,避免循环依赖(不能先假设有签名再判定
  是否该借)。

`backward_attribution` 计算无论是否借取都保留,用于 §1160 C_backward 归因行
(`c_backward_rows` 用其自带 recovered observation,与当前 observation 的 visual_signature
解耦)及 ssp_summary 的 backward_reference。

## 5. 对抗性审查

1. **"会不会破坏带图视觉教学?"** — 不会。带 image input 时 `_visual_signature_from_events`
   返回非 None,不进借取分支。
2. **"会不会破坏 §1210 合法视觉指代?"** — 不会。recent_visual_window 命中(刚刚图片是啥)
   或 overlap>=0.34(苹果)时仍借取。两个 stage5 测试通过。
3. **"会不会破坏 §1160 C_backward 归因?"** — 不会。backward_attribution 仍计算;
   c_backward_rows 用 backward_attribution.observation(recovered),不依赖当前 observation
   的 visual_signature。
4. **"会不会破坏 visual_imagination_recall 合法用途?"** — 不会。它不依赖借取签名(实测)。
5. **"会不会 over-claim?"** — 护栏测试断言无完成性字符串。

## 6. 落地清单

- `runtime.py`:line 399-407 条件借取 + 新增 `_text_query_refers_to_visual_memory` 函数;
- `tests/test_phase20_12c_text_input_no_borrowed_visual_signature.py`:5 测试(非法不借/无
  签名/无 imagination 触发/带图不回归/不 over-claim);
- 回归套件 74 测试通过;红线零命中;node --check 通过。

## 7. 验收标准

1. 教香蕉后纯文本"你是谁?"答"我还不太知道怎么说。"(request_teacher),不答"是香蕉"。
2. 纯文本"你是谁?"的 observation 无 visual_signature,无 visual_imagination_recall tick。
3. "刚刚图片是啥"+图教学后的带图召回仍正确(test_stage5_text_reference 通过)。
4. "苹果"指代教过的苹果仍触发 imagination(test_stage5_idle_visual_focus 通过)。
5. 带图视觉教学不回归。
6. 不出现完成性断言(护栏)。
7. 回归套件全绿,红线零命中,node --check 通过。
