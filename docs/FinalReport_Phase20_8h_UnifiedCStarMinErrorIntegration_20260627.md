# Phase20.8h 统一 C* 最小误差整合落地报告

日期: 2026-06-27

## 一、设计

设计文件:

- `docs/Design_Phase20_8h_UnifiedCStarMinErrorIntegration_20260627.md`

本阶段目标:

```text
B evidence
C_forward prediction
C_backward attribution
UnifiedExperienceCandidate statistics
Action competition
        -> C* min-error integration
        -> cstar_packet
```

这不是新增认知实体, 也不是新增回答模块。它只把每 tick 已经存在的 B/C/行动竞争/统一候选统计, 按同一套最小误差公式归一化成 C* 审计字段。

## 二、审查完善

审查发现:

1. Phase20.8g 之前的 C* 仍偏展示层:
   - default C* 写出 `grasp`、`e_forward`、`e_backward`。
   - 已有 `bccstar_stage3_packet` 只保留自身字段。
   - 两类 packet 没有统一 `E_total`。
2. 已有 C* packet 会被 `complete_every_tick_cognitive_cycle(...)` 保留, 但没有经过统一 C* 最小误差整合。
3. 统一候选统计已进入 C*, 但还没有参与 `grasp` 与误差计算。

白皮书约束:

1. C* 是 C_forward 与 C_backward 叠加、裁剪、归一化后的唯一回灌包。
2. B 只作为现状认知波和证据来源, 不直接当回灌。
3. 每 tick 都应有预测和归因。
4. 索引与候选统计不是真相源。
5. 不新增 keyword/regex/answer table/hidden solver/student-side LLM。

修正方向:

- 新增纯函数 `_integrate_cstar_packet(...)`。
- 对 default C* 和已有 `bccstar_stage3_packet` 都执行同一整合公式。
- 保留旧 packet 的 `kind`、`support_formula` 等字段, 避免破坏前阶段审计语义。
- 新增 `cstar_formula_id`、`cstar_model`、`cstar_min_error_integration`、`e_total`、`cstar_virtual_energy`、`alpha_forward`、`alpha_backward`。

## 三、通过落地

修改:

- `apv3test/runtime/phase20_7/cognitive_cycle.py`

新增:

- `tests/test_phase20_8h_unified_cstar_min_error_integration.py`

核心公式:

```text
S_b      = support(B or weak_tick_evidence_B)
S_f      = max support(C_forward)
S_bwd    = max grasp(C_backward)
S_u      = max support(UnifiedExperienceCandidate slots)
D_action = selected_action_drive
H_conf   = action_competition_entropy

E_forward  = 1 - S_f
E_backward = 1 - S_bwd
E_b        = 1 - max(S_b, S_u)
E_action   = 1 - D_action
E_conflict = H_conf

E_total =
  0.30 * E_forward
+ 0.30 * E_backward
+ 0.18 * E_b
+ 0.12 * E_conflict
+ 0.10 * E_action

grasp = 1 - E_total
```

C* 虚能量审计:

```text
Cstar_virtual_energy =
  max(S_f, S_bwd, S_u, S_b) * (1 - 0.35 * H_conf)
```

方向权重:

```text
alpha_forward  = S_f   / (S_f + S_bwd + eps)
alpha_backward = S_bwd / (S_f + S_bwd + eps)
```

## 四、严谨验收测试

编译:

```powershell
python -m py_compile apv3test\runtime\phase20_7\cognitive_cycle.py tests\test_phase20_8h_unified_cstar_min_error_integration.py
```

结果:

```text
通过
```

专项测试:

```powershell
python -m pytest tests\test_phase20_8h_unified_cstar_min_error_integration.py -q
```

结果:

```text
4 passed in 2.05s
```

相关回归:

```powershell
python -m pytest tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8f_unified_candidate_driven_b_recall.py tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py tests\test_phase20_8h_unified_cstar_min_error_integration.py -q
```

结果:

```text
12 passed in 3.53s
```

Phase20.7/20.8 指定回归链:

```powershell
python -m pytest tests\test_phase20_7_stage0_runtime_boundary.py tests\test_phase20_7_stage1_text_closed_loop.py tests\test_phase20_7_stage2_experience_memory_indexes.py tests\test_phase20_7_stage3_structural_bccstar.py tests\test_phase20_7_stage4_unclosed_idle.py tests\test_phase20_7_stage5_visual_patch_reconstruction.py tests\test_phase20_7_stage6_audio_tts.py tests\test_phase20_7_stage7_api_workbench.py tests\test_phase20_7_stage8_release_demo.py tests\test_phase20_8b_every_tick_cognitive_cycle.py tests\test_phase20_8c_unified_experience_recall.py tests\test_phase20_8d_unified_structure_flow.py tests\test_phase20_8e_code_audit_and_unified_candidate.py tests\test_phase20_8f_unified_candidate_driven_b_recall.py tests\test_phase20_8g_exact_b0_and_weak_cycle_unified_stats.py tests\test_phase20_8h_unified_cstar_min_error_integration.py -q
```

结果:

```text
68 passed in 49.05s
```

红线扫描:

```powershell
rg -n "raw_source_asset_used_for_render.*True|visual_environment_frame_payload|environment_frame|environment_payload_ref|label_map|image_label_map|taught_answer|direct_reply|reply_text\s*=\s*taught|answer_table|hidden_solver|student_side_llm|enumerate_objects_in_image" apv3test\runtime\phase20_7 tests\test_phase20_8h_unified_cstar_min_error_integration.py -g "*.py"
```

结果:

```text
无命中
```

说明:

- 本轮没有重新跑全仓库 `python -m pytest -q`。上一轮全量命令 240 秒超时, 本轮继续以 Phase20.7/20.8 指定回归链作为验收证据。

## 五、可以证明什么

本阶段可以证明:

1. 非 Stage0 cognitive tick 的 C* packet 已进入统一最小误差整合公式。
2. default C* 与已有 `bccstar_stage3_packet` 都会补入 `cstar_formula_id = apv3_phase20_8h_cstar_min_error/v1`。
3. `B`、`C_forward`、`C_backward`、`UnifiedExperienceCandidate statistics`、`action_competition_entropy` 已经进入同一个 `E_total`。
4. unknown/default weak tick 仍不伪造 `b_candidates`, 但会有 C* 误差审计。
5. exact B0 与 structural B 旧审计字段没有被破坏。

## 六、仍不能声称什么

本阶段仍不能声称:

1. 所有 B/C/C* 召回来源已经完全由唯一心脏驱动。
2. C* 已经真实按 SA 粒度回灌 StatePool 的 `V_i(t+1)`。
3. L1/L2/L3 在线嵌入已经由 `E_total` 训练。
4. 六阶段学习协议已经贯通 runtime。
5. 完整范式自学习、数学列竖式、任意模态远距离归因、画板行动范式已经完成。
6. 全仓库 pytest 已通过。

## 七、下一步

Phase20.8i 建议继续:

1. 把 C* 整合结果从审计字段推进到真实 StatePool 虚能量回灌, 但必须按 SA/occurrence 粒度, 不可直接改回复文本。
2. 将 `E_total`、`E_forward`、`E_backward` 作为后续 L1/L2/L3 在线嵌入学习信号的输入, 先做可验审计, 再做参数更新。
3. 继续收束剩余 helper, 让 B/C/C* 的候选来源逐步只剩 SSP/ExperienceFlow 统一接口。
4. 在这之后再进入六阶段学习协议 runtime 状态机最小闭环。
