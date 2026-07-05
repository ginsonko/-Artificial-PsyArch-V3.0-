# Phase20.9j-grasp — 泛化驱动结果锚定把握感门控 最终汇总报告

**日期**: 2026-06-30
**触发**: codex 外审反馈核实 + 修复 (独立核实, 择其成立部分, 拒其误判部分)
**白皮书依据**: §173.5 退火后验把握感 / §24 §132 派生可重建 / §19.3b 无外部语义权威 / 勿增实体
**编号说明**: 本修复是 Phase20.9j (structural generalization) 的深化子修复, 复用 9j 既有
`PHASE20_9J_STRUCTURAL_GENERALIZATION_ID` (不新建 formula_id 常量, 勿增实体). 编号用
`9j_grasp` 后缀以区别于 9j 主体, 并避开已被 `PHASE20_9K_OUTWARD_SPEECH_ID` 占用的 9k.

---

## §1 做了什么

修复 codex 外审中**经独立核实成立**的一条真问题: 泛化路径 (structural_bccstar) 的 write drive
由**结构相似度先验主导**, 而精确回忆路径 (exact_b0) 的 support 走**结果锚定的把握感**
(`_support_from_reward_punish`). 两条回忆路径的置信度锚定不一致, 导致**泛化比精确回忆还自信**
(倒置) —— 无奖励证据时仍敢泛化出答案.

修法 (AP 闭环, 勿增实体): 在 structural_b 构造处用**既有** `_support_from_reward_punish` +
`_alignment_support_count` 算出"结果把握感 grasp"存入 audit_slot; 在 `_write_drive_from_recall_state`
用 grasp **乘性门控** support 斜率:

```
drive = _unit(0.22 + support * 0.58 * grasp + reward_delta - punish_delta - residual_delta)
```

- 复用 exact_b0 同一条把握感通道 → 统一两条回忆路径的置信度锚定
- 结果→把握感→驱动门控 形成闭环 (AP 主流, 不新增实体)
- "敢泛化"成为**经验结果**, 而非结构先验默认冲动

---

## §2 落地文件

| 文件 | 改动 |
|---|---|
| `apv3test/runtime/phase20_7/runtime.py` | 3 处编辑: (1) structural_b 构造处算 generalization_grasp; (2) audit_slot 存 grasp; (3) `_write_drive_from_recall_state` 用 grasp 门控 support 斜率 |
| `tests/test_phase20_9j_grasp_gating.py` | 新增 5 个验收测试 |
| `docs/FinalReport_Phase20_9j_GeneralizationGraspGating_20260630.md` | 本报告 |

无新增表 / 实体 / 路由 / 答案表 / 关键词路由 / 学生侧 LLM. `_support_from_reward_punish` 与
`_alignment_support_count` 均已在 runtime.py 顶部导入, 无新增依赖.

---

## §3 codex 外审核实结论 (独立验证, 不盲信)

### 成立的部分 (1 条真问题, 已修复)
- `_write_drive_from_recall_state` 的 structural_bccstar 分支: 实跑探针确认 reward=0 (零结果证据)
  时仍泛化出"谢谢", write_cell drive=0.7974 碾压 request_teacher 0.1599; write_trace 里 support
  先验贡献 68%, reward_delta 仅 6%. 根因: 泛化路径 support 走结构相似度先验, 精确回忆路径 support
  走结果锚定 grasp —— 两路径置信度锚定不一致, 泛化比精确回忆还自信 (倒置).

### codex 判错的部分 (不予采纳)
1. **奖励泛化 (reward=1.0→"谢谢") 是 bug** —— 误判. 9j 测试明断言 `can_generalize_without_answer_table`,
   这是 AP 替代答案表的核心机制, 合规设计特性, 不是 bug.
2. **"先别上 L3"** —— 认知滞后. 13b/13c 已闭合验收 (876/4 零新增回归).
3. **"_support_from_reward_punish 是手调先验不是 posterior"** —— 误判. 退火形状参数是先验, 但
   support_count 锚定使其已是学习 posterior; 改它要改白皮书 §173.5 退火公式, 不在范围且会破坏 13b/9j.
4. **"lifecycle no_database_context 是 bug"** —— 误判. 是 conn=None 时的安全退化 (runtime.py:9168),
   非缺陷.
5. **"硬常数 STRUCTURAL_B_THRESHOLD / _bounded_multiplier 是硬编码"** —— 误判. 阈值/边界是
   §1742 有界非零要求, 不是答案硬编.

---

## §4 白皮书合规 (逐条)

| 条款 | 合规 |
|---|---|
| §173.5 退火后验把握感 | ✓ 直接复用 `_support_from_reward_punish`, 不新公式 |
| §24 / §132 派生可重建 | ✓ `_alignment_support_count` 派生自 append-only 经验流, 可由 rebuild 重建 |
| §19.3b 无外部 LLM 语义权威 | ✓ 无引入 |
| §35.4 红线 1 在线嵌入不替显式通道 | ✓ 未触碰 |
| §1742 有界非零 [0.7,1.3] | ✓ 未触碰 (本修复在 write drive, 非动作调制乘子) |
| 勿增实体 | ✓ 无新表/实体/路由, 复用既有函数与 audit_slot 通道 |
| 不声称学成 | ✓ grasp 是连续值 [0.18,0.96], 无布尔断言; 禁用串全无 |

---

## §5 对抗性审阅 (写后做)

### 硬编码检查
- 所有值 (reward_value, punish_value, support_count, grasp) 运行时派生, 无答案硬编 ✓

### 隐患检查
- grasp 缺省 0.0 → drive 退到 0.22 base (安全方向: 缺数据退缩, 不假装知道) ✓
- conn / payload 在 structural_b 构造上下文已可用 (同函数已调 `_value_signal_for_unified_candidate(conn,...)`) ✓
- 空串防御: `if _src_input_signature else 0` → support_count=0 → 底噪分支 ✓

### 白皮书不符检查
- 无 ✓ (见 §4)

### 可更泛化 / 优雅检查
- 通过 audit_slot 传递 grasp 是现有设计 (candidate_audit_slots 本就是给下游门控用), 无需改 dataclass ✓
- 保留两路径语义差异 (精确回忆把握=grasp 本身; 泛化把握=相似度×结果把握感), 更符合 AP 哲学 ✓
- exact_b0 无需再改 (其 support 本身就是 grasp 派生, drive 已隐含门控) ✓

---

## §6 验收结果 (实际跑过)

### 探针 (4 场景)
| 场景 | 修复前 | 修复后 |
|---|---|---|
| reward=1.0 泛化 | write drive 0.83, reply="谢谢" | write drive 0.67, reply="谢谢" (仍泛化, 9j 不破坏) ✓ |
| reward=0 泛化 | write drive 0.73, reply="谢谢" (太敢写) | write drive 0.39, write_cell drive 0.46 (软化) ✓ |
| 退火 (sc 0→50) | — | grasp 0.73→0.43 趋稳 ✓ |
| 奖惩等时不偏 | — | r=1,p=1 → grasp=0.34=底噪 (净位移=0) ✓ |
| 纯惩保守 | — | r=0,p=1 → grasp=0.18 < 底噪 0.34 ✓ |

### 测试
- 9j 原测试 4/4 通过 ✓ (奖励泛化不破坏)
- 新增 9k 测试 5/5 通过 ✓ (锁定: 奖励仍泛化 / 无奖励软化 / grasp 结果锚定非结构先验 / 惩罚保守 / 红线无收敛断言)
- 大邻批 54/54 通过 ✓ (structural_b + ladder + L3 + cold_retest + memory_rhythm + L1 全下游)
- 全量回归: 见 §7 (后台运行中, 待填权威数字)

---

## §7 全量回归

**890 passed / 0 failed (890 tests, 1066s) ✓** — 全绿, 零新增回归. 含 9j-grasp 新增 5 测试 +
既有 9j/9k OutwardSpeech/13b/13c/14 全套. 此前 13c 基线 876/4, 经 (a) 4 既存失败独立清理
(PreexistFailures_Cleanup) + (b) Phase20.14 场景学成判据 + (c) 本 9j-grasp 门控, 现已达 890/0 全绿.

---

## §8 边界

- 本修复只动 structural_bccstar 的 write drive 公式, 不动 exact_b0 / 动作调制乘子 / L3 / 阶梯投影
- grasp 是连续投影, 不声称学成; 退火形状参数 (lr_min/lr_max/tau/base) 未改, 维持 13b/9j 既有边界
- 4 个既存失败已在 `FinalReport_Phase20_PreexistFailures_Cleanup_20260630.md` 独立清理完毕 (phase7_9
  删 phrase_kind 路由走 phrase_id 命名空间 / phase8×2 陈旧断言更新 / sqlite 加两表键), 全量已达 890/0
- Phase20.14 场景学成判据已在 `FinalReport_Phase20_14_SceneLearnedProjection_20260630.md` 落地

---

## §9 下一步

- 4 既存失败清理 ✓ / Phase20.14 场景学成判据 ✓ / 9j-grasp 门控 ✓ 均已完成, 全量 890/0 全绿
- 下一步候选 (待用户授权): 继续深化拟人开放对话底座, 例如对象中心文本驱动组合式视觉想象、
  泛化胆量/谨慎的连续可自举 AP-native posterior、或 codex 外审其余可成立项的逐条核实
