# Phase20.12 L2 时序/边在线嵌入设计(已签批)

日期: 2026-06-29
状态: 已通过对抗性审查 + 用户签批,进入落地

## 0. 背景与上一报告措辞纠正

Phase20.11 最终报告把下一步写成"L2 跨模态共现在线嵌入"。**这是措辞不精确,本次审计纠正**。

白皮书原文(§35.2 / §173.2 / §173.3)规定:

- L1 = 现状召回准确性层,用认知压训练对象软相似,**帮 B 召回**(Phase20.11 已落地)。
- L2 = **时序/空间/因果层**,学顺序、运动、空间趋势、因果候选,**帮 C_forward/C_backward**。
- L3 = 行动后果层,学场景-行动-奖惩后果,**帮 action competition**。

L2 的被更新对象是**边** `e=(a relation b)`,不是单个对象;其数学形式(§173.3):

```
z_relation_context = compose(z_a, relation_type, z_b)
z_edge <- z_edge + lr_L2 * structure_support * (z_relation_context - z_edge)
顺序非对称: z_next(a->b) != z_next(b->a)
```

验收锚点(§173.8):"狗咬我/我咬狗"顺序不同;重启后向量索引可由经验流重建。

## 1. 只读审计结论(设计依据)

### 1.1 runtime 事实

- `phase20_7_sa_types` 表已含 `vector_l2 BLOB` 列(白皮书与 schema 早已规定),目前全空。表按 `sa_type_id` 键化。
- 现有 sa_type 命名空间:`text_unit::<hash>`、`cognitive`、`SELF_DRAFT_GRID`。**无"边类型" sa_type**,但 `upsert_sa_type` 是通用接口,接受任意 `sa_type_id` 字符串 + `substrate`/`modality`/`canonical_hint`,新 substrate 不改表、不加表。
- `phase20_7_structure_edges` 表按 `edge_id` 键化,存 `src/dst_occurrence_id + edge_type + weight + learned_weight`,**不挂 vector 列**。
- `phase20_7_occurrences` 表存 `sa_type_id`,因此边经 src/dst occurrence 可 join 回两端 sa_type 的 L1 向量。
- 已有边类型字面量:`linear_next`、`linear_contains`、`feedback_linear_next`、`feedback_alignment_edge`、`short_structure_next` 等(白皮书规定的顺序/结构边,非新增)。
- C_forward/C_backward 行构造**分散**(visual_imagination / feedback_attribution / idle_self_test / short_structure_flow / cstar_carryover 各有独立构造器,10+ 调用点),但最终在 `_emit_runtime_tick_event`(runtime.py:10686+)的 `c_forward_rows`/`c_backward_rows`(10739/10740)**汇聚**。

### 1.2 SSP 与 L2 的分层(用户质疑后核对白皮书坐实)

用户挑战:L2 是否在重复造 SSP 已有的顺序/空间/三维结构边?核对白皮书后**确认是两个不同层次**:

- **SSP(§10)**:白箱显式结构图 `G_t=(O_t, E_t)`,`E_t` 已含 `next/spatial_left_of/causal_candidate/rhythm_lag` 等边(§10.3)。表达"此刻在场"的精确结构,每个 occurrence 保留位置/顺序/能量。runtime 已用 `phase20_7_structure_edges` 表 + `linear_next` 等边类型实现。
- **L2 在线嵌入(§35.3/§173)**:从 AP 自身的预测误差、结构共现、奖惩中**学习**出的边 `z_edge` 的**软相似向量层**,用于**跨经验召回**——当新现状的顺序结构 (a->b) 与历史某条边**相似但 token 不完全相同**时,凭**相似度**召回那条后继/前因。

§35.4 红线第 1 条:"在线嵌入**不替代**白箱显式通道"——正是 SSP 与 L2 的分工红线。

### 1.3 runtime 后继召回现状(证明 L2 填的是真缺口)

读 `_short_structure_next_candidates`(experience_flow.py:130-298):

- `WHERE edge_type='short_structure_next' AND dst.sa_type_id LIKE 'short_structure_flow::%'`——按 edge_type 字面量 + sa_type_id 前缀**精确过滤**。
- support 只来自 `edge.weight*0.45 + learned_weight*0.25 + 能量 + recency`,**没有任何边与边之间的软相似度**。
- 只能召回"曾经**完全一样**写过的边",跨不过"相似但不相同"那一截。

**结论:L2 在当前 runtime 填的是真缺口**——给类型对边一个学出来的软相似向量,使新现状顺序结构与历史边相似但 token 不同时也能召回后继(§173.2 "L2 帮 C_forward/C_backward"的真意)。

### 1.4 勿增实体判断(已签批)

用户已裁定:类型对键 `sa_type_id="text_edge::linear_next::<hash(a_type)>-><hash(b_type)>"`,写进既有 `sa_types` 表的既有 `vector_l2` 列。**不算新增实体**,理由:

1. `sa_types` 表与 `vector_l2` 列白皮书与 schema 早已规定,本步只填它,与 L1 填 `vector_l1` 同构。
2. `upsert_sa_type` 已是通用接口,新 substrate 不改表、不加表、不加列。
3. L2 不复制 SSP 的 occurrence 级精确边,只给**类型对**加一层学习软相似;occurrence 级精确结构仍在 SSP。
4. 边向量 `compose(z_a, relation, z_b)` 由两端已学 L1 向量与关系类型派生,可由经验流重放重建,是派生量非真相源(§24/§132)。

否决的备选:给 `structure_edges` 表加 vector_l2 列(occurrence 级)——与白皮书"类型对跨经验泛化"相悖,不同 tick 的"你->好"会变成不同 edge_id,无法共享 z_edge,失去 L2 跨经验相似召回意义。

## 2. 设计(草案)

### 2.1 边类型 sa_type 投影

对每条 `linear_next` / `feedback_linear_next` 顺序边 `(a -next-> b)`:

```
edge_sa_type_id = f"text_edge::linear_next::{hash(a_sa_type)}->{hash(b_sa_type)}"
substrate = "text_edge"
modality = "structure"
canonical_hint = f"{label(a)} -> {label(b)}"   # 如 "你 -> 好"
```

`linear_contains` 是包含关系(utterance 含 char),非顺序,本步**不**纳入 L2(避免把"包含"误当"顺序",符合白皮书"顺序非对称"重点)。`feedback_alignment_edge` 是输入-输出对齐边,性质不同,本步也**不**纳入。**本步只处理顺序边**(`linear_next` + `feedback_linear_next`),这是 §173.8"顺序不同"验收的最小充分集。

### 2.2 边向量更新(§173.3 L2 结构更新)

教学反馈后,对受教输出序列产生的顺序边做三元组式更新:

```
z_a = L1(a_sa_type)            # 读两端已学 L1 向量(已落地)
z_b = L1(b_sa_type)
relation_type = "linear_next"
z_relation_context = compose(z_a, relation_type, z_b)   # 拼接+关系编码
structure_support = clamp(0.5 + 0.3*reward + 0.2*|prediction_error-0.5|, 0, 1)
lr_L2 = lr_max_L2 / sqrt(1 + support_count)             # 退火 §173.5
z_edge_new = normalize(z_edge + lr_L2 * structure_support * (z_relation_context - z_edge))
support_count += 1
```

- `compose`:把 `z_a`(24维)、关系编码(24维,由 relation_type 哈希派生,同 L1 初始向量的确定性策略)、`z_b`(24维)投影到 24 维(取 a 段前 12 + b 段后 12,或加权拼接后归一),保证**顺序非对称**:`compose(a,b) != compose(b,a)`。
- 初始 `z_edge` 用与 L1 同构的确定性 content-addressed 初始向量(基于 edge_sa_type_id 哈希),非新实体,只是初始化策略。
- 只更新顺序边对应的 edge sa_type;不更新两端 a/b 的 L1(它们各自由 L1 学习)。

### 2.3 注入点(汇聚式,避免横切)

**只在 `_tick_event` 的 `c_forward_rows` 汇聚点叠加一行 L2 后继预测**:

```
c_forward_rows = (c_forward or ()) + _cstar_carryover_c_forward(cstar_carryover)
               + _l2_successor_prediction(conn, observation=observation)
```

`_l2_successor_prediction` 的预测语义(落地版,经实测调整):

1. 取当前观察序列最后一个有义字符为源 sa_type `a'`。
2. `LIKE` 前缀 `text_edge::linear_next::<hash(a'_sa_id)>->%` 找出所有以 `a'` 为源、已学(非空 vector_l2)的顺序边。
3. 候选边按**边的已学 support_count** 排序(score = clamp(0.4 + 0.12*support_count, 0, 1)),取 top-1。
4. 该边的 dst 端点 sa_type_id(从 `canonical_hint` "src -> dst" 解码)即预测的后继;`predicted_dst_sa_type_id` 写入行。

**分层正确性**:L1 端点相似度层负责"哪个历史边的源与我当前源相似",L2 边的 support_count 负责"这条后继关系被强化过几次"。本步因 LIKE 前缀已把源精确钉为 `a'`,所有候选共享源,score 取决于边的强化次数;未来若放开前缀做"相似但非同一 token"的源泛化,L1 端点余弦即接管源匹配信号。两层各司其职,互不替代(§35.4 红线 1)。

`l2_edge_sa_type_id` 把端点编码为 `_hash_text(src_sa_type_id)`(即对完整 `"text_unit::<hash>"` 字符串再哈希),所以 `LIKE` 前缀必须用 `_hash_text(src_sa_id)`,**不是**原始 char 哈希——这是实测中发现并修正的编码一致性要点。

**不**改散落各处的 visual_imagination / feedback_attribution / idle_self_test 构造器。L2 只在这个汇聚点叠加,作为 C_forward 的一个可叠加行,**不替代**任何已有 C_forward 行。L2 行标记 `kind="l2_temporal_edge_prediction"`、`projection_only=True`、`writes_answer_directly=False`。

L2 也可在 `c_backward_rows`(10740)叠加一行顺序前驱归因,但**本步先只做 C_forward 一侧**,把范围控制到最小可验收;C_backward 侧留到确认 C_forward 注入无误后再加(避免一次铺太大)。

### 2.4 索引重建

`rebuild_phase20_7_indexes`:在 L1 重建之后,

1. 清空 `substrate='text_edge'` 的 sa_types 的 `vector_l2`;
2. 重放所有 `experience_alignment` 事件,对受教输出序列重建顺序边 sa_type 并重放 L2 更新;
3. upsert `l2_vector_index/v1` 注册行(`rebuildable=1`,`config_json` 记录真相来源为经验流)。

### 2.5 delta 审计

L2 更新作为 `learning_deltas` 一员:`delta_kind="l2_temporal_edge_update"`、`projection_only=True`、`writes_answer_directly=False`、含 `edge_sa_type_id`、`structure_support`、`lr_L2`、`support_count`。不出现 `l2_converged` / `online_embedding_converged` / `l1_l2_l3_complete` 等完成性断言。

### 2.6 范围控制(本步不做)

- 不做空间边(视觉 patch 位置)——视觉 substrate 未在本 runtime 落地,留到 Phase21。
- 不做因果候选边——因果是 C_backward 的高阶,本步只做顺序。
- 不做 L3。
- 不接入 B 召回(L2 帮 C_forward,不是帮 B)。

## 3. 对抗性审查(待用户复核)

### 3.1 "L2 是否重复造 SSP 已有的边结构?"(用户质疑,已核对白皮书)

**结论:不重复,因 SSP 与 L2 是显式/学习两层(§1.2)。**

- 用户挑战:SSP 已有顺序/空间/三维结构边,L2 再做顺序边是否重复?
- 核对白皮书:SSP(§10)是此刻在场的精确显式图;L2(§35.3/§173)是从预测误差/共现/奖惩学的边**软相似向量层**,用于跨经验"相似但不相同"召回。§35.4 红线第 1 条"在线嵌入不替代白箱显式通道"即此分工。
- runtime 现状(§1.3)证明 L2 填真缺口:后继召回是精确边匹配,无软相似。
- 已签批:类型对键 + 既有 vector_l2 列;L2 不复制 SSP occurrence 级精确边。

### 3.2 "L2 行叠加在 C_forward 汇聚点,是否滑向横切模块?"

**结论:不滑,因为单点注入。**

- 反方:在 `_emit_runtime_tick_event` 改 c_forward_rows 是改核心 tick 构造。
- 正方:只在最终汇聚点**叠加一行**,不改任何已有 C_forward 行的构造逻辑,不改散落构造器。与 Phase20.8j carryover 在同一点叠加 `_cstar_carryover_c_forward` 同构(已被审查通过)。

### 3.3 "顺序非对称如何被验收坐实?"

- 测试构造:教 "你->好" 与 "好->你" 两个不同顺序,断言 `l2_cosine(edge(你->好), edge(你->好))` 高,`l2_cosine(edge(你->好), edge(好->你))` 显著低于前者。这直接对应 §173.8"狗咬我/我咬狗"。

### 3.4 "会不会在 far text 泄漏 / 生成 fake 后继?"

- L2 行是 `projection_only=True` 的叠加行,不生成 B candidate,不写 reply_text。far text 仍由现有逻辑请求教师。护栏测试断言 far text tick 的 c_forward 不含 L2 行,或含但 selected_action 仍为 request_teacher。

### 3.5 "会不会 over-claim?"

- 护栏:`l2_converged` / `online_embedding_converged` / `l1_l2_l3_complete` / `six_stage_learning_complete` 不得出现。更新 8e 护栏测试加禁串。

## 4. 落地清单(签批后才做)

- `experience_log.py`:L2 向量序列化(update/load)、`l2_compose`、`l2_triplet_update_vector`、rebuild 重放 L2、`l2_vector_index/v2` 注册行。
- `__init__.py`:导出 L2 helper。
- `runtime.py`:`_l2_successor_prediction`、`_apply_l2_temporal_edge_update`、接入 `_record_teacher_feedback`、接入 `_emit_runtime_tick_event` 的 c_forward_rows 汇聚点、L2 delta 入 learning_deltas。
- 测试:`tests/test_phase20_12_l2_temporal_edge_embedding.py`(顺序非对称、L2 行叠加、可重建、far text 不泄漏、不 over-claim)。
- 8e 护栏加 `l2_converged` 禁串。

## 5. 验收标准

1. 一次教学后,受教输出顺序边 sa_types 的 `vector_l2` 非全零,tick learning_deltas 含 `l2_temporal_edge_update`。
2. "你->好" 与 "好->你" 的 L2 余弦显著不同(顺序非对称,§173.8)。
3. c_forward_rows 含 `l2_temporal_edge_prediction` 行,`projection_only=True`。
4. `l2_vector_index/v2` 可由经验流重放重建,`rebuildable=1`。
5. far text 不出现 fake 后继/不改变 request_teacher。
6. 不出现完成性断言(护栏)。
7. Phase20.7/8/9/10/11 回归链通过,红线零命中,node --check 通过。
