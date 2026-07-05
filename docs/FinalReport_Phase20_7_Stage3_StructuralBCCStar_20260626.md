# Phase20.7 Stage 3 Structural B/C/C* 验收报告

日期: 2026-06-26  
范围: 结构相似 B 召回、C_forward 预测、C_backward 解释、C* 虚能量回灌。

---

## 1. 本阶段目标

Stage 3 的目标是在 Stage 1 exact B0 和 Stage 2 可重建索引基础上, 实现第一版 AP-native B/C/C*:

1. B: 当前 SSP query 与历史结构相似匹配后形成当前认知。
2. C_forward: 沿历史 alignment 向后传播, 形成预测认知。
3. C_backward: 引用历史输入结构, 形成解释认知。
4. C*: 将 B/C 的把握感与预测虚能量回灌 StatePool。
5. C* 不直接写答案, 输出仍必须经过 action competition 与 DraftGrid。

---

## 2. 已落地内容

`runtime.py` 新增:

1. `PHASE20_7_STAGE3_SCHEMA_ID`
2. `STRUCTURAL_B_THRESHOLD`
3. `_StructuralB`
4. `_find_structural_b(...)`
5. `_structural_similarity(...)`
6. `_inject_cstar_virtuals(...)`

### 2.1 结构相似度

当前 Stage 3 的结构相似度由三部分组成:

```text
similarity =
  positional_score * 0.48
  + bigram_score * 0.34
  + prefix_score * 0.18
```

门槛为 `0.55`。  
这让“你好啊”与“你好呀”可以形成近似结构召回, 而“你是谁”只共享一个字, 不会过门槛。

### 2.2 B/C/C* trace

RuntimeTickEvent v2 中新增真实字段填充:

1. `b_candidates`: `kind=structural_b`
2. `c_forward`: `sequence_forward_prediction`
3. `c_backward`: `source_structure_explanation`
4. `cstar_packet`: `bccstar_stage3_packet`
5. StatePool: `memory_prediction` 项带有虚能量 `V`

### 2.3 行动边界

C* 只提供虚能量、把握感和解释痕迹, 不直接输出。  
最终文本仍由 `write_cell` 逐 tick 写入 DraftGrid, 再由 `commit_reply` 提交。

---

## 3. 当前可展示效果

```text
用户: 你好啊
教师反馈: 你也好
AP: 嗯,记下了。

用户: 你好呀
AP: 你也好

tick trace:
B: structural_b, support >= 0.55
C_forward: 预测输出序列长度 3
C_backward: 来源结构解释, 共享单位为 “你 / 好”
C*: 写入 memory_prediction 虚能量
DraftGrid: 你 -> 你也 -> 你也好
```

而:

```text
用户: 你是谁
AP: 我还不太知道怎么说。
```

不会召回“你也好”。

---

## 4. 本阶段能证明什么

Stage 3 可以证明:

1. Phase20.7 不只会 exact 记忆, 已具备受控结构类比。
2. B/C/C* trace 来自 RuntimeTickEvent, 不是 UI 演示流程。
3. C_forward/C_backward 已分开记录预测和解释。
4. C* 能将预测虚能量回灌 StatePool。
5. 相似召回仍受门槛控制, 不会把任意输入串到最近教学。
6. exact B0 优先级高于 structural B。

---

## 5. 本阶段尚未证明什么

Stage 3 还不证明:

1. 长程因果解释。
2. 反例驱动的信念松动数学闭环。
3. 未闭合感与 idle_think。
4. 在线嵌入 L1/L2/L3。
5. 多模态视觉/听觉结构召回。

这些进入 Stage 4-6。

---

## 6. 验收命令

### 6.1 Stage 0-3 单测

```powershell
python -m pytest .\tests\test_phase20_7_stage0_runtime_boundary.py .\tests\test_phase20_7_stage1_text_closed_loop.py .\tests\test_phase20_7_stage2_experience_memory_indexes.py .\tests\test_phase20_7_stage3_structural_bccstar.py -q
```

结果: `18 passed`。

### 6.2 Stage 3 红线扫描

```powershell
python .\scripts\red_line_check_v14.py --phase 20.7-stage3
```

结果: 见最终运行记录。

---

## 7. 下一阶段入口

Stage 4 应实现:

1. 未闭合感 U 的 AP-native 来源。
2. idle_think 低频调度。
3. request_teacher 的不烦不傻触发。
4. 放弃/来源移除/教师释放等让 U 下降的路径。
5. 闲时思考写入经验流, 但不直接打扰用户。

