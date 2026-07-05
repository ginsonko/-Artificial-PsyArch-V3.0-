# Phase20.11 L1 在线文本嵌入设计

日期: 2026-06-29

## 1. 目标

Phase20.8e 的只读审计确认了真正的 runtime 缺口:白皮书 §35.3 / §173.3 规定的
L1/L2/L3 在线嵌入完全未实现,`phase20_7_sa_types.vector_l1/l2/l3` 三列自建表以来
一直为空。Phase20.11 的目标是只接入 **L1(receptor-local 文本相似度)**,且严格
不新增认知实体,只把既有 `vector_l1` 列填起来,并让它真实参与 B 召回:

1. 教学反馈后,对受教输出字符的 `text_unit` sa_type 做三元组(triplet)在线更新。
2. 在两个 recall 注入点用 L1 向量余弦作为 `compute_unified_experience_support`
   的一个可叠加项。
3. 索引可由经验日志重放重建,登记为 `rebuildable=1` 的 `l1_vector_index/v1`。
4. L1 delta 作为 `learning_deltas` 的一员进入 tick 审计,但标记为
   `projection_only=True`、`writes_answer_directly=False`。

L2/L3 不在本步范围;本步不声称收敛,不声称 L1/L2/L3 完成。

## 2. 白皮书约束

1. 不新增答案表、不新增关键词/正则路由、不新增隐藏求解器。
2. 不引入外部 LLM 向量作为学生侧语义权威(§19.3b)。L1 向量由 runtime 自身的三元组
   学习产生,初始向量是 `vector_l1` 列的初始化策略,不是新实体。
3. 向量/索引是派生量、可重建,不是真相来源(§24/§132)。真相来源仍是经验流。
4. 三元组不对称(§33.1):异常对象(被教输出字符)被更新,上下文(共现输入字符)
   只作为参考,不共同更新。
5. 退火学习率 `lr_t = lr_0 / sqrt(1 + support_count)`(§173.5),
   默认 `lr_max=0.08, lr_min=0.008, tau=120`。
6. L1 项只调制已有经验候选的 support,不凭空生成 B candidate;unknown / far text
   仍必须请求教师,不得泄漏记忆。
7. 不新增 `l1_converged` / `online_embedding_converged` / `l1_l2_l3_complete`
   之类的完成性断言。

## 3. 数学形式

### 3.1 初始向量(初始化策略,非新实体)

全零锚点 + 全零参考会使 `positive - anchor == 0`,第一步无方向。为此对每个
`sa_type_id` 用其 sha256 派生一个确定性、单位归一、幅度 0.15 的初始向量:

```text
init_vec(sa_type_id) = normalize_0.15( map_to[-1,1]( sha256(sa_type_id) ) )
```

同一 sa_type 永远从同一点起步,不同 sa_types 起步即散开;首个三元组步即有方向,
后续更新很快覆盖初始值。它只是 `vector_l1` 列的初始化策略,不引入新认知实体。

### 3.2 三元组更新(§173.3 / §173.5)

每次教学反馈后,对被教输出的每个字符 sa_type(异常对象/anchor)做一次更新:

```text
positive_centroid = centroid( L1(input_char sa_types) )      # 共现输入为参考
prediction_error  = clamp(0.5 + 0.3*reward + 0.3*punish, 0, 1)
lr_t              = lr_max / sqrt(1 + support_count)         # 退火,§173.5
direction         = normalize(positive_centroid - anchor)     # §33.1 不对称
anchor'           = anchor + lr_t * prediction_error * direction
support_count'    = support_count + 1
```

`negative_centroid` 在本步为 None(L1 只做拉近,不做推远);reward/punish 通过
`prediction_error` 调制步长。`input_char` sa_types 只读不写(参考,非被更新对象)。

### 3.3 B 召回注入

文本相似度用查询文本与记忆文本各自 `text_unit` sa_types 的 L1 质心余弦:

```text
l1_sim(query, memory) = cosine( centroid(L1(query units)),
                                 centroid(L1(memory units)) )
```

在 `compute_unified_experience_support` 中,`l1_vector_similarity` 作为一个
**可叠加项**进入,但**不进入 `primary` max**:

```text
l1_term = unit(l1_sim) * (0.28 if allow_context_bias else 0.0)
support = clamp( sum(weighted_terms) + l1_term, 0, 1 )
```

`allow_context_bias = primary > 0.0` 保持不变。因此当 `l1_vector_similarity`
默认为 0.0(未接线)时,公式输出与原 8e 公式**逐位相同**(向后兼容);
接线后只在已有 primary 的候选上叠加,不凭空抬升零相似候选。

### 3.4 索引重建

`rebuild_phase20_7_indexes` 在 exact_b0 重建之后:清空文本 substrate 的
`vector_l1` -> 按 `created_at` 顺序重放所有 `experience_alignment` 事件的
L1 三元组学习 -> upsert `l1_vector_index/v1` 注册行(`rebuildable=1`,
`config_json` 记录真相来源为经验流)。重建与在线路径同一份
`l1_triplet_update_vector` / `update_sa_type_vector_l1`,保证可复现。

## 4. 审查要点

1. L1 向量只由 runtime 自身的三元组学习产生,不读 teacher answer 文本以外的
   外部语义源,不做关键词/正则答案路由。
2. L1 项只调制已有候选 support,不生成 B candidate;`l1_vector_similarity=0.0`
   时公式逐位退化为 8e。
3. far / unknown 文本仍请求教师,不出现 fake B;L1 不应在无关文本间泄漏相似度。
4. 三元组不对称:只更新输出字符 sa_type,输入字符 sa_type 只读。
5. L1 delta 标记 `projection_only=True`、`writes_answer_directly=False`;
   不直接写 `reply_text`。
6. 不出现 `l1_converged` / `online_embedding_converged` / `l1_l2_l3_complete`
   / `six_stage_learning_complete` 等完成性断言。
7. `vector_l1` 是派生量,可由经验日志重放重建;重建后与在线路径一致。

## 5. 验收标准

1. 一次教学后,被教输出字符 sa_types 的 `vector_l1` 非全零,tick 的
   `learning_deltas` 含 `delta_kind="l1_vector_triplet_update"`。
2. 被教输入/输出对的 L1 余弦 > 无关文本对的 L1 余弦。
3. recall 候选的 `support_terms` 含正向 `l1_vector_similarity`。
4. `l1_vector_index/v1` 可由经验日志重放重建,`rebuildable=1`。
5. far text 仍请求教师,L1 不在无关文本间泄漏(无 fake B)。
6. 不出现任何完成性断言字符串(护栏测试)。
7. Phase20.7/20.8/20.9/20.10 回归链通过,`node --check` 通过,
   `scripts/red_line_check_v14.py` 零命中。
