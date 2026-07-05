# 最终汇总报告 — Phase20.13a support 退火化

日期: 2026-06-30
子项目: APV3.0test
白皮书依据: §173.5 退火曲线 / §737 把握感 Grasp / §173.6 人类类比 / §24·§132 真相源 / §1640 tombstone / §3351 红线
设计文档: docs/Design_Phase20_13a_SupportAnnealing_20260630.md

## 1. 问题

### 1.1 codex 上一轮"软化"的三个错误（对抗性验收发现）
1. **`_support_from_reward_punish` 新公式违背 §173.5 退火**：codex 把 support 从 `0.7+reward*0.2-punish*0.2` 改成 `0.52+reward*0.18-punish*0.16`，是**另一条无 support_count 的平坦线性先验**，0.52/0.18/0.16 三个魔数在白皮书无依据。白皮书 §173.5 明确要求 `lr_t = lr_0/√(1+support_count)` 退火后验，§737 定义 `Grasp = f(..., support_count, ...)`——support_count 是输入变量。讽刺的是同仓库 L1(line 362)、L2(line 593) 已正确实现退火范式。
2. **runtime.py:2016 内联复制了同款错误公式**，没调函数，存在公式漂移风险。
3. **`experience_log.py:1030` `support_0.350` 是硬编码字符串伪装成学习结果**（§3351 红线"不可调成捷径"第3条）。

### 1.2 codex 的"??"诊断是错的
codex 12:19/12:28 报告"教过 你好聪明 后问仍回 ??"，据此反复调低 `_write_drive_from_recall_state` 的 structural_b 写驱动力。实测 `data/phase20_7_workbench.sqlite`：4 条 `experience_alignment` output 是纯 `???`，**对应输入文本本身就是 `????`**（PowerShell 跑中文探针时编码被吞成 `?`，runtime 忠实存下）。在**全新 DB** 上 `你好聪明 → 谢谢` 泛化完全正常。codex 整条修复链基于污染数据。

## 2. 白皮书依据

- **§173.5 退火曲线**：`lr_t = lr_0/√(1+support_count)`，`lr_eff = lr_t*(1+surprise_boost+teacher_boost+reward_punish_boost)`——support 是随成熟度退火的学习后验，不是平坦先验。
- **§737 把握感**：`Grasp = f(max_similarity(B), margin(B), support_count, low_conflict, low_abs(P))`——support_count 是 Grasp 的输入变量。
- **§173.6 人类类比**：初学易被一次经验影响（sc=0 时 lr=lr_max），熟练后更稳定（sc 增大 lr 退火）。
- **§24/§132 真相源**：经验流是真相源，索引/向量是派生可重建——故 support_count 派生自查、不建表/列。
- **§3351 红线**：不可调成捷径，包括"强行提高/固定某个答案候选"。

## 3. 对抗性自审（设计阶段，coding 前）

1. **退火公式边界值验证**：用脚本跑全部边界——首教 r=1.0 → 0.73（够高，exact 召回的 write_drive 赢竞争）、无奖无惩 → 0.34（底噪）、纯惩 → 0.18、奖惩等 → 0.34、成熟 sc=10→0.61/sc=50→0.43（趋稳）。
2. **发现并修正初版两个缺陷**：
   - (a) 初版用 `sign*lr_eff`，导致无奖无惩(r=p=0)时仍上推到 0.64（误判为有把握）。终版改为单一 boost 乘子 × 净奖惩量 `(reward-punish)`，奖惩等时净位移=0。
   - (b) TAU=80 退火过慢，sc=10 仍 0.69。终版 TAU=24，sc=10→0.61 趋稳明显。
3. **support_count 时序安全**：alignment 事件在 runtime.py:1972 先 insert，再在 2010 upsert exact_b0，故 `_alignment_support_count` 查询能含本次。首教 sc=1 时 grasp=0.716 仍 > 0.52，exact 召回不丢。
4. **不回退 codex 的 write_drive 系数**：无 git 历史、干净 DB 泛化正常、无测试断言具体值、属 §370 合法调制——盲目回退有破坏风险。交 L3 学出来。
5. **勿增实体**：support_count 派生自查（零新表/列），与 L1/L2 已有范式一致。

## 4. 修复

### 4.1 `_support_from_reward_punish` 退火化（experience_log.py）
新增常量 `_SUPPORT_LR_MAX=0.30 / _SUPPORT_LR_MIN=0.04 / _SUPPORT_TAU=24.0 / _SUPPORT_BASE=0.34`，函数改为：
```python
def _support_from_reward_punish(reward, punish, *, support_count=0):
    lr = _SUPPORT_LR_MIN + (_SUPPORT_LR_MAX - _SUPPORT_LR_MIN) * math.exp(-max(0,int(support_count))/_SUPPORT_TAU)
    boost = 1.0 + 0.3*min(1,reward) + 0.2*min(1,punish)
    lr_eff = lr * boost
    net_strength = min(1,reward) - min(1,punish)
    grasp = _SUPPORT_BASE + lr_eff * net_strength
    return max(0.18, min(0.96, grasp))
```
与 L1(line 362) `lr_min+(lr_max-lr_min)*exp(-support_count/tau)` **同范式**，作用在把握感标量。

### 4.2 新增 `_alignment_support_count`（experience_log.py）
派生计数：同 `input_signature` 下 `experience_alignment` 事件中 reward>0 的累计确认次数。只读既有表，不建表/列，可由 rebuild 重建。

### 4.3 三个调用点同步（消除内联复制 + 传 support_count）
- `experience_log.py:780` rebuild 路径：按 input_signature 维护运行计数器，模拟运行时按时间序累计。
- `experience_log.py:1004` 记忆视图：调 `_alignment_support_count` 派生。
- `runtime.py:2023` 内联复制 → 改为调用 `_support_from_reward_punish(..., support_count=_alignment_support_count(...))`。

### 4.4 修复 `support_0.350` 硬编码（experience_log.py:1039）
text_receptor_observation 是未学习输入观察，改为 `processing_tendency="support_prior_observation"`、`support=_SUPPORT_BASE`（0.34），明确标注为先验底噪而非学习结果。

### 4.5 修正测试魔数（test_phase20_7_stage2）
codex 把 `0.52` 写进断言边界。改为断言真正的不变量：教过 alignment support > 0.52（退火公式推出 0.72）；未学习观察 support ≤ 0.40（底噪 0.34）。

### 4.6 不动 write_drive 系数
codex 基于污染数据调的 `_write_drive_from_recall_state` 系数不回退（见 §3.4），交 L3。

## 5. 验收（实际检查）

| 检查 | 结果 |
|---|---|
| byte-compile (3 文件) | OK |
| node --check workbench.js | OK |
| red_line_check_v14 main gate | OK (runtime/cognitive 零违规) |
| over-claim 字符串扫描 | 零命中 |
| 残留 `0.52+reward*0.18` 内联公式 | 已清除（仅剩无关的 feedback_only readiness） |
| 残留 `support_0.350` 硬编码 | 已清除 |
| `_support_from_reward_punish` 调用点 | 3 处全部传 support_count |
| **三组样本(干净DB)** | 组1 你好聪明→**谢谢** ✓ / 组2 天气怎么样→**我还不太知道怎么说。** ✓ / 组3 苹果→**是红色苹果** ✓ |
| support 退火验证 | alignment=0.716(>0.52) ✓ observation=0.34(≤0.40) ✓ |
| 退火边界值 | 全部符合设计（0.73/0.34/0.18/0.34/0.61/0.43） |
| **污染DB rebuild** | 41 行索引成功，不崩 |
| **污染DB 跑 turn** | 正常回复，不崩 |
| **全套回归 phase20.1-20.12** | **235 passed, 0 failed**（远超 codex 声称的 74） |

回归明细：20.7+20.8 核心 66 / 20.10-20.12 学习生命周期+L1/L2 42 / 20.1-20.6 早期 51 / 20.9 action+DraftGrid 76。

## 6. 边界与未做

- **不删 `?` 污染行**：append-only 经验流不可变（§1049）。污染清理用 tombstone 标记 inactive（§1640），另列待办，不在本步。
- **不动 `_competition`/`_write_drive_from_recall_state` 魔数系数**（0.42/0.48/0.22/0.58）：属 §370 合法调制，应由 L3 行动后果学习学出来（§173.7.3），不手调。
- **red_line_check_v14 的 `check_phase20_7_stage2_redlines` 是 dead code**（main 未调用），其 required token 含 `fast_tendency`/`slow_trace` 但实际未 gate。codex 删这两个标签未触发违规，但这是潜在 gate 缺口，记入待办。
- **support 退火是连续后验了，但还不是完整 learned posterior**：当前 support_count 只计 alignment 确认次数，未接 prediction_error/surprise 的 full §737 Grasp（max_similarity(B)/margin(B)/low_conflict/low_abs(P)）。这是 L3 行动后果学习的自然延伸。

## 7. 下一步

**Phase20.13b 或直接 L3**：support 退火这一前置依赖已做对，现在可以进 **L3 行动后果在线嵌入**（§1657/§173.7.3/§1726）：
- 填既有 `vector_l3` 列（不新增表/列）
- triplet/退火更新由行动结局（reward/punish/failed_action）驱动
- 注入为 `action_competition` 的调制（§173.7"最后实现 L3，接 action competition"；§1726"行动失败降低同状态同行动 drive"）
- 把 `_competition`/`_write_drive_from_recall_state` 的手调魔数系数逐步替换为 L3 学出来的 drive 调制
- 可重建 `l3_vector_index/v1`，同 L1/L2 的 far-text no-leak / no-completion guardrails

L3 完成后，三层在线嵌入（L1/L2/L3）全部闭合，再进六阶段学习协议完整闭合（§36）。
