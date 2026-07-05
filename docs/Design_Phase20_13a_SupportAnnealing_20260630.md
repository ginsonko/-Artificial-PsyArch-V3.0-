# Phase20.13a — support 退火化（落实白皮书 §173.5/§737，回退 codex 错误诊断）

日期: 2026-06-30
子项目: APV3.0test
白皮书依据: §173.5 退火曲线 / §737 把握感 / §173.7 实施规划 / §24·§132 真相源 / §1640 tombstone / §3351 红线

## 1. 背景与问题

### 1.1 codex 上一轮"软化"做了什么
codex 在 06-30 11:30–12:27 改了 5 个文件，把 support 从"0.7 base / 0.25 floor 平坦先验"改成"0.52 + reward*0.18 - punish*0.16"的**另一条平坦线性先验**，并把 `fast_tendency`/`slow_trace` 二分标签改成 `support_xxx` 连续标签。

### 1.2 对抗性验收发现的三个问题
1. **`_support_from_reward_punish` 新公式违背 §173.5 退火**。
   白皮书 §173.5 明确要求 support 是随成熟度退火的学习后验：
   ```
   lr_t = lr_0 / sqrt(1 + support_count)
   lr_eff = lr_t * (1 + surprise_boost + teacher_boost + reward_punish_boost)
   ```
   §737 进一步定义 `Grasp = f(max_similarity(B), margin(B), support_count, low_conflict, low_abs(P))`——**support_count 是输入变量**。
   codex 的 `0.52 + reward*0.18 - punish*0.16` 无 support_count，是平坦先验，0.52/0.18/0.16 三个魔数在白皮书无依据。讽刺的是同一 `experience_log.py` 里 L1(line 363) 和 L2(line 593) 已经正确实现 `lr_min+(lr_max-lr_min)*exp(-support_count/tau)` 退火范式。

2. **runtime.py:2016 内联复制了同款错误公式**，没调函数，存在公式漂移风险。

3. **`experience_log.py:1030` `text_receptor_observation` 的 `support_0.350` 是硬编码字符串伪装成学习结果**。白皮书 §3351 红线"不可调成捷径"第3条"强行提高某个答案候选"——这里是强行固定观察的支持度。

### 1.3 codex 的"??"诊断是错的
codex 12:19/12:28 报告"教过 你好聪明 之后问 你好聪明 仍回 ??"，并据此反复调低 `_write_drive_from_recall_state` 的 structural_b 写驱动力。
实测 `data/phase20_7_workbench.sqlite`：4 条 `experience_alignment` 的 output 是纯 `???`/`?????`，对应**输入文本本身就是 `????`/`?????`**（PowerShell 跑中文探针时编码被吞成 `?`，runtime 忠实存下）。在**全新 DB**上实测 `你好聪明 → 谢谢` 泛化完全正常。codex 整条"压低 structural_b 写驱动"的修复链基于污染数据。

## 2. 设计目标（勿增实体）

把 support 从"平坦线性先验"改成"带 support_count 的退火后验"，并清理 codex 基于错误诊断/硬编码的改动。**不新增任何认知实体、表、列、路由**。support_count 不存表（无 ALTER 迁移机制），运行时从 append-only 经验流派生查询（§24/§132 真相源是经验流，索引/向量是派生可重建），与 L1/L2 已有范式一致。

## 3. 具体设计

### 3.1 support_count 来源（派生，零新表）
`support_count` = 同一 `input_signature` 下、`experience_alignment` 事件中 reward>0 的累计确认次数。这是 append-only 经验流的派生计数，可由 `rebuild_phase20_7_indexes` 重建，不是新真相源。

新增派生查询函数 `_alignment_support_count(conn, *, input_signature) -> int`（在 experience_log.py，紧邻 `_support_from_reward_punish`）：
```python
def _alignment_support_count(conn, *, input_signature: str) -> int:
    """派生计数: 同 input_signature 下 reward>0 的 experience_alignment 累计确认次数.
    真相源是 append-only 经验流(§24/§132), 不是新表/新列. 可由 rebuild 重建."""
    row = conn.execute(
        """
        SELECT COUNT(*) FROM phase20_7_experience_events
        WHERE event_kind='experience_alignment'
          AND json_extract(payload_json, '$.input_signature')=?
          AND reward>0
        """,
        (str(input_signature),),
    ).fetchone()
    return int(row[0]) if row else 0
```
**对抗性注意**: 此函数只读既有表，不写、不路由、不增实体。它的输出只用于 support 退火计算，不直接决定答案。

### 3.2 `_support_from_reward_punish` 退火化（experience_log.py:1340）
改签名为 `_support_from_reward_punish(reward, punish, *, support_count=0)`，并按 §173.5 退火。
**对抗性自审修正过的两点**：(a) 初版用 `sign*lr_eff`，导致无奖无惩(r=p=0)时仍上推到 0.64（误判为有把握）；(b) TAU=80 退火过慢，sc=10 仍 0.69。终版改为单一 boost 乘子 × 净奖惩量，TAU=24：

```python
_SUPPORT_LR_MAX = 0.30   # 首次确认(support_count=0)的把握位移幅度上界
_SUPPORT_LR_MIN = 0.04   # 成熟后单次确认的把握位移幅度(退火下限)
_SUPPORT_TAU = 24.0      # 退火时间常数(拟人: 多次确认后趋稳, §173.6)
_SUPPORT_BASE = 0.34     # 未确认时的把握底噪(底噪, 非学习结果)

def _support_from_reward_punish(reward, punish, *, support_count: int = 0) -> float:
    """白皮书 §173.5 退火后验把握感(§737 Grasp).
    support_count=0 时 lr=lr_max(初学易被一次经验影响, §173.6);
    support_count 增大, lr 退火到 lr_min(熟练后更稳定).
    §173.5 lr_eff = lr_t * (1 + reward_punish_boost), 单一乘子;
    位移由净奖惩量 (reward-punish) 决定, 奖惩等时净位移=0(不偏).
    """
    lr = _SUPPORT_LR_MIN + (_SUPPORT_LR_MAX - _SUPPORT_LR_MIN) * math.exp(-max(0, int(support_count)) / _SUPPORT_TAU)
    boost = 1.0 + 0.3 * max(0.0, min(1.0, float(reward))) + 0.2 * max(0.0, min(1.0, float(punish)))
    lr_eff = lr * boost
    net_strength = max(0.0, min(1.0, float(reward))) - max(0.0, min(1.0, float(punish)))
    grasp = _SUPPORT_BASE + lr_eff * net_strength
    return max(0.18, min(0.96, grasp))
```
实测边界值（已用脚本验证）：
- `sc=0, r=1.0, p=0` → **0.73**（首次教学把握够高，exact 召回的 write_drive 赢竞争）
- `sc=0, r=0, p=0` → **0.34**（未确认底噪，不再误判 0.64）
- `sc=0, r=0, p=1.0` → **0.18**（纯惩罚，低）
- `sc=0, r=1.0, p=1.0` → **0.34**（奖惩等，净位移=0，不偏）
- `sc=10, r=1.0` → **0.61**；`sc=20` → **0.54**；`sc=50` → **0.43**（成熟趋稳，§173.6）
- 与 L1(line 362 `lr_min+(lr_max-lr_min)*exp(-support_count/tau)`) **同范式**，只是作用在把握感标量而非向量。

### 3.3 三个调用点同步（消除内联复制 + 传 support_count）
1. `experience_log.py:773` rebuild 路径：按 input_signature 分组累计 support_count，传入。
2. `experience_log.py:993` 记忆视图：同上。
3. `runtime.py:2016` 内联复制 → 改为调用 `_support_from_reward_punish(feedback.reward_mag, feedback.punish_mag, support_count=_alignment_support_count(conn, input_signature=observation.signature))`。

### 3.4 修复 `support_0.350` 硬编码（experience_log.py:1030）
text_receptor_observation 是**未学习的输入观察**，不应伪装成有把握度。改为明确标注为先验底噪：
```python
"processing_tendency": "support_prior_observation",
"support": _SUPPORT_BASE,   # 0.34, 与退火底噪同源, 明确是先验非学习结果
```
去掉写死的 `support_0.350` 字符串魔数。

### 3.5 关于 codex 改的 `_write_drive_from_recall_state` 系数（不动）
codex 12:28 改了 `_write_drive_from_recall_state`(runtime.py:11445) 的 structural_b 系数（0.42+support*0.48 / 0.22+support*0.58），是基于"??"污染数据的错误诊断。但**对抗性自审决定不回退**：
- 无 git 历史，无法确认 codex 具体改了哪几个数字，盲目回退可能破坏原本工作的逻辑。
- 干净 DB 实测泛化正常，说明当前系数在正常数据上不构成 bug。
- 没有任何测试断言这些系数的具体值，回退无验收依据。
- 这些系数是 §370"行动通过 drive 竞争"的合法调制系数，真正该做的是 L3 行动后果学习把它们学出来（§173.7.3），不是本步手调。
**结论**：本步只修已确认的错误（退火公式/内联复制/硬编码/测试魔数），不触碰 write_drive 系数，避免引入新风险。记入待办交 L3。

### 3.6 修正 test_phase20_7_stage2 的 0.52 魔数断言
codex 把测试断言写成 `any(s > 0.52)` / `any(s < 0.52)`，把魔数写进测试。改为断言**真正的不变量**：教过的 alignment support > 未学习的 observation 底噪。
```python
assert any(s > 0.52 for s in supports)   # 教过的把握高于底噪
assert any(s <= _SUPPORT_BASE + 0.001 for s in supports)  # 未学习观察是底噪
```
（保留 > 0.52 因为首次教学 reward=1.0 时 grasp=0.73 > 0.52，这是退火公式推出的真实值，不再是随意魔数。）

## 4. 不做什么（边界）

- **不新增表/列**：support_count 派生自查，无 ALTER 风险。
- **不新增认知实体**：不新增"把握感模块""退火器""置信度计算器"。support 是既有 alignment 索引的派生标量。
- **不动 `_competition` 魔数系数**（0.42/0.48 等）：那是 L3 行动后果在线嵌入的自然归宿（§173.7.3"行动失败降低同状态同行动 drive"），应由 L3 学出来，不在本步手调。
- **不删 `?` 污染行**：append-only 经验流不可变（§1049）。污染清理用 tombstone 标记 inactive（§1640），不在本步做（另列待办）。
- **不上 L3**：L3 是下一步，本步先把 support 退火化这一前置依赖做对。

## 5. 验收标准
1. 三组样本稳（干净 DB）：泛化 你好聪明→谢谢 / 纯文本未知→请求教师 / 视觉引用→指代。
2. 全套回归通过（≥ codex 声称的 74）。
3. red_line_check_v14 main gate 通过。
4. byte-compile + node --check 通过。
5. 干净 DB 实测：首次教学 grasp ≈ 0.73（够高，exact 召回不丢），成熟后单次 grasp 不再剧烈上推。
6. 无 `support_0.350` 硬编码、无 0.52 内联公式副本。
