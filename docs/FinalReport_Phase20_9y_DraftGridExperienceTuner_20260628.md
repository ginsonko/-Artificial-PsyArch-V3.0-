# Phase20.9y DraftGrid 经验调参投影最终报告

日期：2026-06-28

## 1. 本阶段目标

Phase20.9y 的目标不是新增一个“胆量模块”或“人格参数表”，而是把 Phase20.9x 中较固定的 DraftGrid 后继行动调制，继续下沉到 AP 主流程：

- 当前 DraftGrid 已经通过 ExperienceFlow / SSP 找到“草稿后面还可能继续写什么”。
- Phase20.9x 已经能用奖励、惩罚、冲突、疲劳调制“继续写 / 回读 / 修改 / 停下 / 提交”。
- Phase20.9y 进一步让这些调制读取历史经验：最近类似后继被奖励过，就更敢继续和提交；最近类似后继被惩罚、回读、修改、停下、重复过，就更谨慎、更多核查和疲劳。

这对应白皮书里的经验调参原则：调参不是外部工程开关，而是已有经验流、奖惩、行动后果对后继行动竞争的投影。

## 2. AP-native 设计审查

本阶段严格遵守“勿增实体”：

- 未新增 SQLite 表。
- 未新增独立认知池、人格池、调参器实体。
- 未新增关键词回复、答案表、LLM 兜底或专属解题模块。
- 新增的 `experience_tuner_projection` 只读取现有 `phase20_7_experience_events` 和 `phase20_7_action_records`。
- 投影结果只改变行动竞争 delta，不直接写答案、不创建 reply candidate。

换成小白说法：它不是“写死一个更大胆按钮”，而是 AP 每次要不要继续写时，回头看看自己最近这样做有没有被夸、有没有被纠正、有没有一直重复，然后当场变得更敢或更谨慎。

## 3. 实现内容

修改文件：

- `apv3test/runtime/phase20_7/runtime.py`
- `tests/test_phase20_9y_draftgrid_experience_tuner.py`

核心新增公式：

```text
apv3_phase20_9y_draftgrid_experience_tuner_projection/v1
```

新增投影读取：

- `experience_alignment` 的 reward / punish 历史。
- `continue_writing / read_draft / edit_cell / stop_generating / commit_reply` 的近期行动记录。
- `draft_grid_commit` 的提交历史。
- 同文本 hash、同 intent、重复提交带来的疲劳。
- 当前 DraftGrid 上下文中的低把握、冲突、重复疲劳。

输出倍率：

- `boldness_multiplier`：奖励和成功继续写历史越强，越敢继续/提交。
- `caution_multiplier`：惩罚、冲突、修改、停下越强，越谨慎。
- `verification_multiplier`：惩罚、回读、修改越多，越想核查。
- `fatigue_multiplier`：重复提交、同 intent 重复、停下历史越多，越疲劳。

这些倍率只调制 Phase20.9x 的基础 delta：

- 正向 continue / commit 用 boldness。
- 正向 read 用 verification。
- 正向 edit 用 caution。
- 正向 stop 用 fatigue。
- 负向 delta 用相应的反向谨慎倍率。

## 4. 可观察效果

奖励历史场景：

```text
教：long source prompt -> alpha first fragment beta successor fragment，奖励
再问：first fragment prompt
```

AP 会先写出 `alpha first fragment`，回读草稿后通过 ExperienceFlow 找到后继 ` beta successor fragment`。因为类似后继曾被奖励，它的投影表现为更大胆：

```text
boldness_multiplier ≈ 1.32
continue_writing_delta: 0.2392 -> 0.3154
commit_reply_delta: 0.1058 -> 0.1394
```

惩罚历史场景：

```text
教：long source prompt -> alpha first fragment beta successor fragment，惩罚
再问：first fragment prompt
```

AP 仍能召回后继，但会更谨慎：

```text
boldness_multiplier ≈ 0.77
caution_multiplier ≈ 1.49
verification_multiplier ≈ 1.40
continue_writing_delta: 0.0508 -> 0.0390
read_draft_delta: 0.0704 -> 0.0982
edit_cell_delta: 0.0800 -> 0.1195
commit_reply_delta: -0.0649 -> -0.0968
```

这比固定阈值更拟人：不是“低把握一律不知道”，而是会因为历史奖惩逐渐学会什么时候可以试着泛化，什么时候该回读、修改或保留未闭合。

## 5. 严谨验收

已通过：

```text
python -m py_compile apv3test\runtime\phase20_7\runtime.py
python -m py_compile tests\test_phase20_9y_draftgrid_experience_tuner.py
pytest -q tests\test_phase20_9y_draftgrid_experience_tuner.py -vv
pytest -q tests\test_phase20_9x_draftgrid_successor_outcome_modulation.py -vv
pytest -q tests\test_phase20_9*.py
pytest -q tests\test_phase20_8*.py
pytest -q tests\test_phase20_7*.py
python scripts\red_line_check_v14.py --phase 20.7-stage8
python scripts\check_constant_governance.py
```

结果：

- Phase20.9：73 passed
- Phase20.8：58 passed
- Phase20.7：48 passed
- Red line：PASS
- Constant governance：PASS，仍有既有 91 个 experimental warning，非本阶段新增阻断。

## 6. 对抗性自审

结论：Phase20.9y 阶段合格，但仍不是最终完整学习系统。

已解决：

- 9x 的固定调制不再完全固定，已经接入历史经验投影。
- 奖励后更敢泛化、惩罚后更谨慎的底层倾向开始出现。
- 调参投影不写答案、不绕过 DraftGrid、不新增实体。

仍然不能过度宣称：

- 还不是完整 L1/L2/L3 在线嵌入。
- 还不是完整六阶段 runtime。
- 还没有完成数学列竖式。
- 还没有完成 Phase21 视觉教学泛化闭环。
- 还没有把同一套经验调参投影扩展到所有行动候选。

潜在风险：

- 当前倍率仍是手工设计的有界公式，虽然输入来自 AP 经验流，但还不是完全由长期调参历史自己收敛出来。
- 经验窗口目前为近期窗口，适合拟人短期状态变化，但长期性格/习惯式调参还需要后续通过同一经验流继续沉淀，不能新增“人格参数表”。

## 7. 下一步

下一步该做 Phase20.9z：

把这套经验调参投影从 DraftGrid successor 扩展到统一行动竞争中的更多候选，尤其是：

- `request_teacher`：什么时候该问、什么时候先自己试。
- `maintain_unclosed`：什么时候继续想、什么时候暂时放下。
- `outward_speech`：什么时候主动发给用户、什么时候只在私有想法里流动。
- `commit_reply / read_draft / edit_cell / stop_generating` 的更统一调制。

要求仍然不新增实体，只允许读取现有 ExperienceFlow、SSP、ActionRecord、reward/punish、C* 残差和未闭合感，让“胆量、谨慎、重复疲劳、请教倾向”继续作为 AP 主流程的经验投影长出来。
