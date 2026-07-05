# Phase20.9z 统一行动经验调参投影最终报告

日期：2026-06-28

## 1. 本阶段目标

Phase20.9z 的目标是把 Phase20.9y 的经验调参投影，从 DraftGrid successor 扩展到更统一的行动竞争候选：

- `request_teacher`
- `maintain_unclosed`
- `outward_speech`
- `write_cell / continue_writing`
- `read_draft / edit_cell / stop_generating / commit_reply`
- `idle_think / sleep_lower_frequency`

核心要求：不能新增“外显意图模块”“人格胆量表”“专属调参实体”。所有调制都必须从 AP 已有信息流中读出：ExperienceFlow、ActionRecord、reward/punish、无反馈、重复疲劳、未闭合感、DraftGrid 回读/修改/提交记录。

## 2. 设计与审查

新增公式：

```text
apv3_phase20_9z_unified_action_experience_tuner_projection/v1
```

它不是新实体，只是当前 tick 的经验投影：

- 不新增 SQLite 表。
- 不新增长期人格参数。
- 不新增关键词回复、答案表或 LLM 兜底。
- 不产生回复候选。
- 不直接写答案。
- 只调制已有行动候选的 drive。

拟人解释：

AP 现在不只是“固定阈值决定要不要问/说/提交”，而会看自己最近的经验：

- 最近类似行为被奖励：更敢继续、提交、外显。
- 最近被惩罚或修改：更谨慎、更想核查。
- 反复回读：初期提高核查，重复过多后转为疲劳，避免陷入无限回读。
- 主动说话后没人反馈：降低继续主动说的倾向。
- 重复同类未闭合：维持思考/继续整理的倾向略增。

## 3. 实现内容

修改文件：

- `apv3test/runtime/phase20_7/runtime.py`
- `tests/test_phase20_9b_learning_protocol_drive_modulation.py`
- `tests/test_phase20_9z_unified_action_experience_tuner.py`

新增核心函数：

- `_action_experience_tuner_projection(...)`
- `_apply_action_experience_tuner_to_rows(...)`
- `_recent_action_feedback_projection(...)`
- `_recent_outward_no_feedback_count(...)`

接入位置：

- `_teacher_request_drive_context(...)`：真实调制 `request_teacher / maintain_unclosed`。
- `_outward_speech_candidate_from_idle_context(...)`：真实调制主动外显 drive。
- `_select_draftgrid_next_action_from_ap_flow(...)`：真实调制 DraftGrid 的 `continue/read/edit/stop/commit` 选择。
- `_tick_event(...)`：每 tick 的 action competition 都带可审计的统一投影 trace。

## 4. 可观察效果

重复未知请求场景：

```text
用户：phase20.9z repeated unknown
AP：我还不太知道怎么说。
用户：phase20.9z repeated unknown
```

第二次 AP 会把未闭合经验投影进 `maintain_unclosed`：

```text
maintain_drive: 0.6667 -> 0.6757
ask_pressure: 0.08
maintain_multiplier: 1.0135
```

这不是硬编码“第二次就维持”，而是未闭合和近期行动记录给 maintain 一个轻微偏置。

DraftGrid 场景：

```text
候选：continue / read / edit / stop / commit
```

9z 会进入每个候选行，例如一次验收中：

```text
selected: commit_reply
commit_reply multiplier: 1.011
read_draft multiplier: 0.9863
stop_generating multiplier: 1.0019
```

主动外显场景：

```text
AP 闲时想把私有想法说出来。
之前说过一次，也得到过奖励，但还有重复/无反馈疲劳。
```

实际投影：

```text
outward drive: 0.6108 -> 0.5728
reward_total: 0.0719
outward_multiplier: 0.9379
```

这很关键：不是“奖励过就一直刷屏”，而是奖励、重复、无反馈疲劳共同竞争，更接近人的主动表达。

## 5. 对抗性自审修正

初版 20.9z 暴露了一个问题：

```text
read_draft 会因为近期 read_count 增多而越来越想 read，导致“不知道”写完后反复回读，不提交。
```

这违反拟人直觉：人会检查，但反复检查后应该疲劳，转向提交或停下。

修正后：

- 前 1-2 次回读提供核查压力。
- 过多回读转入 `read_repetition_pressure`。
- `read_repetition_pressure` 降低 `verify_multiplier`，提高疲劳。
- 9j 的“远文本不泄漏泛化”和“惩罚后回到请教”恢复通过。

这次修正是本阶段最重要的对抗性收获。

## 6. 严谨验收

已通过：

```text
python -m py_compile apv3test\runtime\phase20_7\runtime.py
python -m py_compile tests\test_phase20_9z_unified_action_experience_tuner.py
pytest -q tests\test_phase20_9z_unified_action_experience_tuner.py ...
pytest -q tests\test_phase20_9*.py
pytest -q tests\test_phase20_8*.py
pytest -q tests\test_phase20_7*.py
python scripts\red_line_check_v14.py --phase 20.7-stage8
python scripts\check_constant_governance.py
```

结果：

- Phase20.9：76 passed
- Phase20.8：58 passed
- Phase20.7：48 passed
- Red line：PASS
- Constant governance：PASS，仍有既有 91 个 experimental warning，非本阶段新增阻断。

## 7. 当前边界

现在可以证明：

- 统一行动经验投影已经进入真实行动竞争。
- 请教、维持未闭合、主动外显、DraftGrid 读/改/停/提交都开始受同一套经验投影调制。
- 经验投影不会直接写答案，不新增实体，不绕过 AP 主流程。

仍不能声明：

- 完整 L1/L2/L3 在线嵌入完成。
- 完整六阶段 runtime 完成。
- 数学列竖式完成。
- object-centric 视觉想象完成。
- Phase21 视觉教学泛化闭环完成。
- 长期“性格式”调参已经完全自学习完成。

## 8. 下一步

下一步该做 Phase20.10a：

把“统一行动经验调参”继续接到六阶段学习 runtime 的真实阶段推进里。也就是让 AP 不只是在当前 tick 调 drive，而是能围绕一个学习对象形成更完整的循环：

```text
接触 -> 模仿 -> 纠错 -> 复盘 -> 自测 -> 泛化 -> 教师退场 -> 冷启动复测
```

仍然不新增课程脚本或外部教学模块，只允许使用现有 ExperienceFlow、SSP、StatePool、C*、ActionRecord、reward/punish 和 unclosed pressure。这样才会继续靠近“会学的开放对话底座”，也会为后面的视觉教学泛化、范式自学习和数学竖式铺路。
