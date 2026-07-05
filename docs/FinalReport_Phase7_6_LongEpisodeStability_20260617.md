# APV3 Phase7.6 Long Episode Stability 最终报告

日期: 2026-06-17
阶段: Phase7.6
状态: 通过

## 1. 设计

Phase7.6 的目标是验证 Phase7.5 的 5 类 runtime 内省表达关联不是短跑偶然，而是在长 episode 中仍能保持稳定。

本阶段不引入新的表达机制，只把同一组事件扩展为 1200 tick 确定性混合序列:

- dialogue 不确定草稿
- work memory 未完成事项
- teacher_request 压力
- punishment 痕迹
- rewarded flow

验收重点:

- 长序列中 5 类 feeling prototype 不互相混淆。
- 存在稀疏类别长间隔，仍不被错误 evict。
- 中途 SQLite 保存 -> warm-load -> 继续运行，最终 teacher-off 行为与连续运行一致。
- 末尾 teacher-off confusion matrix 仍能召回各自 expression。

## 2. 审查完善

吸收 Claude 建议后，补了三项稳定性约束:

- 使用固定 seed 的确定性混合序列，避免测试随机抖动。
- 人为设置稀疏窗口，让第 5 类事件最大间隔达到 147 tick，检查稀疏类别保留。
- 保存恢复时同时保存主 state、cooccurrence store 和各 runtime 子状态，避免把 parity 测成半状态恢复。

## 3. 通过落地

新增:

- `tests/test_phase7_6_long_episode_stability.py`

测试项:

- `test_phase7_6_long_episode_keeps_five_feelings_stable`
- `test_phase7_6_sqlite_warmload_parity_matches_continuous_run`
- `test_phase7_6_runtime_redline_has_no_long_episode_routes`

实际 trace:

```text
ticks 1200
max_gaps {0: 23, 1: 18, 2: 35, 3: 25, 4: 147}
dialogue_uncertain feeling::draft::proto_0 expr::long_dialogue p:expr:long_dialogue target=0.7851 best_other=0.0960
work_memory_unfinished feeling::draft::proto_1 expr::long_work_memory p:expr:long_work_memory target=0.7493 best_other=0.0916
teacher_request_pressure feeling::draft::proto_2 expr::long_teacher_request p:expr:long_teacher_request target=0.7521 best_other=0.0919
recent_punishment feeling::draft::proto_3 expr::long_punishment p:expr:long_punishment target=0.9392 best_other=0.1148
rewarded_flow feeling::draft::proto_4 expr::long_flow p:expr:long_flow target=1.0916 best_other=0.1334
```

## 4. 严谨验收测试

已执行:

```text
python -m pytest APV3.0test\tests\test_phase7_6_long_episode_stability.py -q
python -m pytest APV3.0test\tests\test_phase7_0_teacher_off_three_stage_milestone.py ... APV3.0test\tests\test_phase7_6_long_episode_stability.py -q
python -m pytest APV3.0test\tests -q
python -m compileall APV3.0test\apv3test APV3.0test\tests -q
rg -n "expr::long_|phase7_6_|must_reply|undecidable_feeling_tokens|feeling::undecidable|find_by_cue_token|_most_common_reply|pressure_type_weights|student_side_llm|answer_table|LLM policy" APV3.0test\apv3test\runtime
```

结果:

- Phase7.6 targeted: `3 passed`
- Phase7.0-7.6 combined regression: `52 passed`
- Phase7.0-7.7 combined regression after Phase7.7: `57 passed`
- Full suite after Phase7.7: `230 passed`
- Compileall: passed
- Runtime redline scan: no matches

## 5. 最终汇总

Phase7.6 证明了:

- 5 类内省表达关联在 1200 tick 混合 episode 中保持稳定。
- 稀疏事件最大间隔 147 tick 后仍能被召回，没有被错误淘汰。
- SQLite warm-load 后继续运行，末尾 teacher-off 行为与连续运行等价。
- 长 episode 中没有引入 runtime 侧表达路线、答案表、旧 `must_reply` 通道或 student-side LLM。

仍不能宣称:

- 自然中文短语流已经接入。
- 完整中文开放自由对话底座已经完成。
- 长期 10G SQLite 级别遗忘/压测已经完成。

下一步 Phase7.7 已推进: expression token 从抽象 `expr::*` 探针进入真实中文短句 token 序列，并通过 teacher-off、干扰项和 SQLite warm-load 验收。
