# Phase20.12b L2 C_backward 顺序前驱归因设计(已签批)

日期: 2026-06-29
状态: 已通过对抗性审查 + 用户签批,进入落地

## 0. 背景与上一步收尾

Phase20.12 落地了 L2 时序/边在线嵌入的 **C_forward 一侧**:受教输出序列的相邻字符形成
`linear_next` 类型对边,写进既有 `vector_l2` 列,并在 `c_forward_rows` 汇聚点叠加一行
`l2_temporal_edge_prediction` 后继预测(投影式,不写答)。Phase20.12 设计文档 §2.3 末段
明确把 C_backward 侧留到"C_forward 注入无误后再加,避免一次铺太大"。

Phase20.12 验收已通过(6/6 新测试 + 45 回归 + 红线零命中 + node --check)。本步
Phase20.12b 即那个被刻意控制范围、推迟到现在的 **C_backward 镜像切口**,把 L2 的
"帮 C_forward/C_backward"补齐后一半,然后才进 L3。

白皮书依据不变(§35.2 / §173.2 / §173.3 / §173.8),且新增 C_backward 的定义依据:

- **§1160**:"C_backward 是从 B 命中的历史相似现状沿时间/结构/因果候选/证据边向前传播
  得到的追溯认知。它回答'历史上这种现状之前通常有什么条件',并把这些历史前因作为虚能量
  投向当前短期结构池。"
- **§173.2**:"L2 时序/空间/因果层……帮 C_forward/C_backward。"

L2 的被更新对象仍是**边** `e=(a relation b)`,数学形式(§173.3)与 Phase20.12 完全一致;
本步**不新增任何边向量更新**,只新增一个**读取已学边向量、做前驱归因**的 C_backward 叠加行。

## 1. 只读审计结论(设计依据)

### 1.1 runtime 事实

- `vector_l2` 列已由 Phase20.12 填充:`text_edge::linear_next::<hash(a)>-><hash(b)>` 类型对
  边 sa_type 上有非零 24 维向量 + support_count。本步**只读**这些已学边,不再写新向量。
- C_backward 行构造**分散**(visual_imagination / feedback_attribution / idle_self_test /
  short_structure_flow / cstar_carryover 各有独立构造器),但最终在 `_tick_event` 的
  `c_backward_rows`(runtime.py:11112)**汇聚**。Phase20.12 的 C_forward 切口已在
  `c_forward_rows`(11107)单点叠加 `_l2_successor_prediction`,本步在同构的
  `c_backward_rows` 单点叠加其镜像。

### 1.2 C_backward 现状(证明 L2 前驱归因填的是真缺口)

读 `_short_structure_flow_query_c_backward`(runtime.py:5950):

- 调 `query_recent_experience_flow_candidates`,**只保留** `candidate_kind ==
  "short_structure_flow_next"` 的候选,取 support 最大者为 best。
- support 来自 `edge.weight*0.45 + learned_weight*0.25 + 能量 + recency`,
  **没有任何边与边之间的软相似度**,且只看 `short_structure_flow::` 这一类 occurrence。
- 它只能归因"曾经**完全一样**写过的 short_structure_flow 边",跨不过"相似但 token 不相同"
  那一截,也覆盖不到 `linear_next` 类型对边的跨经验前因。

`_cstar_carryover_c_backward` 则是 C* 残留压力的 carryover,与 L2 的"学出来的边前因"是
不同来源。**结论:L2 前驱归因在当前 runtime 填的是真缺口**——给已学 `linear_next` 类型对边
一个反向查询(以当前末字符为 dst,找 ENDING at 它的边),凭边的 support_count 召回历史前因
(§1160"历史上这种现状之前通常有什么条件"的真意)。

### 1.3 与 C_forward 切口的同构(顺序非对称自洽)

§173.3 顺序非对称 `z_next(a->b) != z_next(b->a)` 在本步体现为**查询方向相反**:

- **C_forward**(Phase20.12):取当前末字符为**源** `a'`,`LIKE` 前缀
  `text_edge::linear_next::<hash(a'_sa_id)>->%` 找**以 a' 为源**的边 → 预测后继 dst。
- **C_backward**(本步):取当前末字符为**dst** `b'`,`LIKE` 后缀
  `text_edge::linear_next::%-><hash(b'_sa_id)>` 找**以 b' 为终点**的边 → 归因前因 src。

同一批已学边向量,相反查询方向。这正是 §173.8"狗咬我/我咬狗顺序不同"在 C_backward 上的
落点:问"好之前通常有什么"与问"好之后通常有什么"查的是不同方向的边。

### 1.4 勿增实体判断(已签批)

本步**不新增任何实体**:

1. 不新增表/列/substrate——只读 Phase20.12 已填的 `vector_l2`。
2. 不新增认知实体——`_l2_predecessor_attribution` 是 `_l2_successor_prediction` 的镜像
   函数,与 `_cstar_carryover_c_backward` / `_short_structure_flow_query_c_backward` 同级,
   都是 C_backward 汇聚点的一个可叠加行。
3. 不复制 SSP 的 occurrence 级精确边——只对已学 `linear_next` 类型对边做反向查询。
4. 不引入外部 LLM 向量——前因 sa_type_id 由 `canonical_hint` "src -> dst" 解码得到,
   是 AP 自身结构学习的派生量(§24/§132)。

## 2. 设计(草案)

### 2.1 前驱归因行构造

```
def _l2_predecessor_attribution(conn, *, observation):
    chars = <observation 的有义字符>
    if not chars: return ()
    dst_sa_id = f"text_unit::{hash(chars[-1])}"
    dst_edge_hash = _hash_text(dst_sa_id)      # 与 C_forward 前缀同编码规则
    suffix = f"%->{dst_edge_hash}"
    pattern = f"text_edge::linear_next::{suffix}"
    rows = SELECT sa_type_id, vector_l2, canonical_hint, updated_tick
           FROM phase20_7_sa_types
           WHERE sa_type_id LIKE ? AND vector_l2 IS NOT NULL
           ORDER BY updated_tick DESC LIMIT 24
    # 候选边按已学 support_count 排序(与 C_forward 同评分,两方向可比)
    for edge in rows:
        support_count, edge_vec = bytes_to_l2_vector(raw)
        if edge_vec 全零: continue
        src_sa_id = _l2_src_sa_type_from_hint(hint)   # "src -> dst" 取 src
        if not src_sa_id: continue
        score = clamp(0.4 + 0.12*support_count, 0, 1)
        取 score 最大者为 best_edge
    if best_edge is None: return ()
    return ({
        "kind": "l2_temporal_edge_predecessor",
        "model": PHASE20_12_L2_STRUCTURE_UPDATE_ID,
        "source_edge_sa_type_id": edge_sa_id,
        "edge_kind": L2_RELATION_LINEAR_NEXT,
        "current_dst_sa_type_id": dst_sa_id,
        "attributed_cause_sa_type_id": src_sa_id,
        "edge_hint": hint,
        "l2_edge_support": score,
        "cause_grasp": _unit(score),
        "e_backward": 1.0 - _unit(score),
        "edge_support_count": support_count,
        "cause_slots": ({ "slot_kind": "l2_temporal_edge_predecessor_slot", ... },),
        "neutralized_occurrences": (),
        "subjective": True,
        "may_be_wrong": True,
        "projection_only": True,
        "writes_answer_directly": False,
    },)
```

`_l2_src_sa_type_from_hint` 是 `_l2_dst_sa_type_from_hint` 的镜像:从 "src -> dst" 取 src
端 sa_type_id(前因)。`l2_edge_sa_type_id` 把端点编码为 `_hash_text(<full sa_type_id>)`,
所以 LIKE 后缀必须用 `_hash_text(dst_sa_id)`,**不是**原始 char 哈希——与 C_forward 前缀
同编码一致性要点(Phase20.12 实测中已修正过一次)。

### 2.2 注入点(汇聚式,与 C_forward 切口同构)

**只在 `_tick_event` 的 `c_backward_rows` 汇聚点叠加一行**:

```
c_backward_rows = (c_backward or ())
    + _cstar_carryover_c_backward(cstar_carryover)
    + _short_structure_flow_query_c_backward(conn, session_id=session_id)
    + _l2_predecessor_attribution(conn, observation=observation)
```

与 C_forward 切口(`c_forward_rows` 叠加 `_l2_successor_prediction`)严格同构:单点注入,
不改任何已有 C_backward 行的构造逻辑,不改散落构造器。L2 行标记
`kind="l2_temporal_edge_predecessor"`、`projection_only=True`、`writes_answer_directly=False`、
`may_be_wrong=True`(C_backward 是追溯归因,本质可错,与 `_cstar_carryover_c_backward` 一致)。

### 2.3 范围控制(本步不做)

- 不做空间边前驱、因果候选前驱——视觉 substrate 未落地,因果是 C_backward 高阶,本步只做顺序。
- 不新增边向量更新——只读 Phase20.12 已学的 `linear_next` 边。
- 不接入 B 召回——L2 帮 C_backward,不是帮 B。
- 不做 L3。

## 3. 对抗性审查

### 3.1 "C_backward 是否重复 _short_structure_flow_query_c_backward?"

**结论:不重复。**

- `_short_structure_flow_query_c_backward` 只看 `short_structure_flow::` occurrence 的精确
  边匹配,support 来自 edge 权重/能量/recency,无类型对边软相似,也覆盖不到 `linear_next`
  类型对边的跨经验前因。
- L2 前驱归因查的是已学 `linear_next` 类型对边(以当前末字符为 dst),凭边的 support_count
  归因前因。两者来源、覆盖范围、信号都不同,与 Phase20.12 §1.3 同理。

### 3.2 "前驱归因是否滑向横切模块?"

**结论:不滑,因为单点注入。**

- 反方:在 `_tick_event` 改 c_backward_rows 是改核心 tick 构造。
- 正方:只在最终汇聚点**叠加一行**,不改任何已有 C_backward 行构造,不改散落构造器。与
  Phase20.12 C_forward 切口、`_cstar_carryover_c_backward` 在同一点叠加同构(已被审查通过)。

### 3.3 "顺序非对称如何被验收坐实?"

- C_forward 查 SRC=当前末字符的边(预测后继);C_backward 查 DST=当前末字符的边(归因前因)。
  同一批已学边向量,相反查询方向。测试构造:教 "你也好" 后,查以"好"结尾的观察应归因"也"
  为前因(也->好 边),查以"也"结尾的观察应归因"你"为前因(你->也 边)——不同 dst 归因出
  不同前因,且与 C_forward 的后继预测用相反边方向。这直接对应 §173.8。

### 3.4 "会不会在 far text 泄漏 / 生成 fake 前因?"

- LIKE 后缀把 dst 精确钉为当前末字符的 sa_type;far text 末字符从未被教过 → 没有边以它为
  终点 → 无前驱行。L2 行是 `projection_only=True` 的叠加行,不生成 B candidate,不写
  reply_text。far text 仍由现有逻辑请求教师。护栏测试断言 far text tick 的 c_backward 不含
  L2 前驱行,或含但 selected_action 仍为 request_teacher。

### 3.5 "会不会 over-claim?"

- 护栏:`l2_converged` / `online_embedding_converged` / `l1_l2_l3_complete` /
  `six_stage_learning_complete` / `l2_vector_converged` 不得出现。8e 护栏测试已在
  Phase20.12 加 `l2_vector_converged` 禁串,本步继承。

## 4. 落地清单

- `runtime.py`:新增 `_l2_src_sa_type_from_hint`(src 解码镜像)、`_l2_predecessor_attribution`
  (前驱归因行),接入 `_tick_event` 的 `c_backward_rows` 汇聚点(11116)。
- 测试:`tests/test_phase20_12b_l2_c_backward.py`(末字符归因前因、不同 dst 归因不同前因、
  C_forward/C_backward 用相反边方向、far text 不泄漏、前驱可重建、不 over-claim)。
- 8e 护栏继承 Phase20.12 的 `l2_vector_converged` 禁串。

## 5. 验收标准

1. 一次教学后,查以受教边终点结尾的观察,`c_backward_rows` 含
   `l2_temporal_edge_predecessor` 行,`attributed_cause_sa_type_id` = 该边的 src 端点,
   `projection_only=True`。
2. 不同 dst 归因出不同前因(也->好 归因也,你->也 归因你)。
3. C_forward 后继预测与 C_backward 前驱归因用相反边方向(同一批边,相反查询)。
4. far text(末字符未被教过)不出现 fake 前因 / 不改变 request_teacher。
5. 前驱归因在 rebuild 后仍存活(边向量可由经验流重建)。
6. 不出现完成性断言(护栏)。
7. Phase20.7/8/9/10/11/12 回归链通过,红线零命中,node --check 通过。
