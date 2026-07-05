# Phase20.7w — 未闭合压力认知涌现 (求知欲/恐惧底层) 最终汇总报告

**日期**: 2026-07-01
**范围**: B-1.1 — §27.1 未闭合期待/压力的认知涌现项 (用户理论引出: 未知带惩罚→恐惧/求知欲)
**循环**: 设计 → 审查完善 → 通过落地 → 严谨验收 → 最终汇总报告
**白皮书**: §27.1/§27.3/§27.6/§30.1/§30.2/§171 不增魔法字段; 勿增实体

---

## §1 起因

用户理论 (与白皮书一致): "恐惧=对惩罚信号的预测; 未知本身就有惩罚信号, 导致压力和恐惧;
求知欲=降低认知压的奖励信号; 认知压高伴随惩罚信号, 降低伴随奖励信号".

白皮书 §27.1: "预测会带来惩罚, 形成压力". §27.3: `Pressure=predicted_punish_energy`.
但当前 phase20_7 的 `upsert_unclosed_item` 的 u_delta **只由 output_intent 硬触发**
(request_teacher=0.46 / maintain_unclosed=0.18), **认知压(P=R-V)不涌现为压力** ——
这正是"未知带惩罚→恐惧/求知欲涌现"链条断裂之处.

## §2 设计 (审查完善后)

### 现状断裂
- §27.6 五种释放机制只 closure (1/5) 落地 (resolve_unclosed_items)
- §27.3 decay_U * U(t) 已在 `_decay_unclosed_for_idle` 实现 (decay=0.88/0.72)
- 但 §27.6 第4项 impossibility 需 C_backward 召回说明任务前提不成立 — 当前 idle tick 无此信号
- 强行加 impossibility 释放会变硬规则, 违反白皮书"需要 evidence"精神, **不在本轮单步范围**

### 可合规落地的唯一一项: 认知压涌现 u_value
复用既有 `_statepool_observation_support_bias` 的 sa_ids 聚合模式 (text_utterance + text_unit),
新函数 `_statepool_unresolved_pressure` 从 pool 取认知压 P=R-V:
- P>0 (惊/预测不足) → pressure_emergent (惩罚预测涌现 → 求知/恐惧)
- P<0 (违和/期待落空) → dissonance_emergent (期待失望压力涌现)
- 返回连续值, 不增表/实体/路由, 纯读 `StateItem.cognitive_pressure` (§9 既有字段)

u_delta 公式:
```
_base_delta = 0.46 if request_teacher else 0.18  # 保留 §27.1 行动增益先天分量
_cognitive_pressure_emergent = min(0.30, pressure_emergent*0.22 + dissonance_emergent*0.14)
u_delta = _base_delta + _cognitive_pressure_emergent
```
- 0.30 上限防涌现压过行动分量 (不让自然涌现 hijack 主竞争)
- 涌现项叠在行动分量上而非取代 (保留 §27.1 affordance*predicted_reward 语义)

## §3 落地文件

| 文件 | 改动 |
|---|---|
| `apv3test/runtime/phase20_7/runtime.py` | (1) 新增 `_statepool_unresolved_pressure` 函数; (2) 修改 `_run_turn` 内 `upsert_unclosed_item` 调用点, u_delta 含认知压涌现, reason 记录各涌现分量 |
| `tests/test_phase20_7w_unclosed_pressure_emergent.py` | 新增 5 个验收测试 |
| `docs/HumanPsychology_AP_Mapping_20260701.md` | (前序) 全人类心理机制↔AP对照清单 |
| `docs/FinalReport_Phase20_7w_UnclosedPressureEmergent_20260701.md` | 本报告 |

### B-1.2 诚实边界交代
单做 §27.6 impossibility 释放需 C_backward 召回提供"任务前提不成立"证据, 当前 idle tick 无此信号;
强行规则化衰减会变硬规则 (违反白皮书 §27.6 "需要 evidence" 明文).
**已在报告显式标注 _decay_unclosed_for_idle 当前已是合规 §27.3 decay_U 时间衰减**,
真正缺的 §27.6 第2/3/4/5 项"证据型释放"留作后续循环 (B-3 等, 待 C_backward 信号接通).

## §4 白皮书合规

| 条款 | 合规 |
|---|---|
| §27.1 未知形成压力 | ✓ 认知压 P=R-V 自动涌现 u_value 增长 |
| §27.3 Pressure=predicted_punish_energy | ✓ 正 P 涌现 pressure_emergent |
| §27.6 new_evidence 项 | ✓ 涌现项是 U(t+1) 的 new_evidence |
| §30.1 惊/违和通道涌现 | ✓ P>0→惊, P<0→违和 分别涌现 |
| §171 不增魔法字段 | ✓ fear/curiosity 等禁用串全无, 连续软投影 |
| 勿增实体 | ✓ 无新表/实体/路由, 纯读 StateItem.cognitive_pressure |

## §5 对抗性审阅

### 硬编码检查
- 0.22/0.14 是与既有 9y boldness/caution 同量级的连续调制系数, 非答案硬编 ✓
- 0.30 上限是防涌现 hijack 的边界, 不是阈值断言 ✓

### 隐患检查
- 空 pool → 涌现 0 (无 SA → 无认知压) ✓ (有测)
- 涌现权重过高会让 u_value 永远高? — 不会, min(0.30,...)+_decay_unclosed(0.88 decay) 平衡 ✓
- 缺数据时 (P=0 全场) → 涌现 0, u_delta 退回 _base_delta (安全) ✓

### 白皮书不符检查: 无 ✓
### 可更泛化检查: 0.22/0.14 写死是合理先验, 未来可调参器调解 (Leave for §33 adapter)

## §6 验收

- 5/5 新测试 ✓ (单元涌现+集成未知文涌现+教师反馈不破坏+红线非路由+禁用串)
- 邻批 45/45 ✓ (stage4 unclosed + 9f/9e idle + 8m successor + 7v视觉 + 9j-grasp)
- 全量回归: 后台跑中, 待补

## §7 进度

A 后 89% → B-1.1 后 **90%**
- §27.1 认知压涌现压力 ✓ (求知/恐惧底层接通第一层)
- §27.6 完整释放机制仍 1/5 + decay_U 时间衰减 (4/5 evidence型释放未做, 留 C_backward 接通)
- §30 12认知感受通道 11/12 仍与 phase20_7 断 (留 B-2 后续)

距小白可用惊艳底座**约 90%**, 还差 10%, 集中在:
1. §30 认知感受通道接通 phase20_7 (11/12 断, P0) — 约 4%
2. §31 情绪慢量积分→表达风格 (断, P1) — 约 2%
3. §27.6 evidence 型释放 (4/5缺, P1, 需 C_backward) — 约 1.5%
4. 首屏冷启动体验 + 中文化 — 约 2.5%

## §8 下一步 (B 阶段后续)

1. **B-2: §30 认知感受通道接通 phase20_7** (P0 大缺口 4%) — 把 runtime/cognitive/cognitive_feelings/factory.py 的 build_cognitive_feelings 接入 phase20_7 tick, 让惊/违和/合理/正确等通道在对话里涌现并调制行动竞争
2. **B-3: §31 情绪慢量积分→表达风格** (P1) — emotion_c 积分慢调制 expression_style
3. **B-4: §2363 counter_evidence 5项完整** (视错觉不可逆 / 创伤松动) — 中优先级
4. **C: codex 外审偏硬点** — 低优先级
5. **§27.6 evidence型释放** — 待 C_backward 接通后做