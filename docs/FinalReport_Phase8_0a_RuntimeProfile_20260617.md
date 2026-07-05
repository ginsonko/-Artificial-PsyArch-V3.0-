# APV3 Phase8.0a Runtime Profile 最终报告
日期: 2026-06-17
阶段: Phase8.0a
状态: 通过

## 1. 设计

Phase8.0a 的目标是把 Phase7.8-7.11 已经验证通过的“极简中文表达 + 多轮对话 + 用户风格趋同”机制，整理成一个干净的真实运行合同。

本阶段不新增心智机制，不增加测试探针，不引入 LLM policy。它只回答一个工程化问题:

- 真正启动用户体验 runtime 时，应该加载哪些核心模块。
- 固定 seed phrase corpus 在哪里。
- SQLite 状态应该写到哪里。
- 哪些字段属于 dev/test-only，不应进入上线 profile。
- style gate、固定词库、禁用动态扩词这些红线是否在启动前就被声明和校验。

## 2. 审查完善

本阶段吸收了“测试污染”和“探针混入 runtime”的风险提醒。设计上做了三层隔离:

- `runtime_profile_minimalist_cli.json` 是启动合同，不是测试脚本。
- 测试可以通过 `sqlite_state_path` override 指向 `tmp_path`，正式 profile 默认指向 `state/apv3_minimalist_cli.sqlite`。
- profile loader 会校验固定词库、style gate、`allow_new_phrases=false`，避免启动时误开动态扩词。

关键红线:

- profile 不指向 `tests.*`。
- runtime 模块列表不包含测试 fixture。
- profile 显式列出 `answer_table/student_side_llm/_most_common_reply/must_reply` 等 forbidden markers。

## 3. 通过落地

新增:

- `apv3test/data/runtime_profile_minimalist_cli.json`
- `apv3test/runtime/runtime_profile.py`
- `tests/test_phase8_0a_runtime_profile.py`

更新:

- `apv3test/runtime/__init__.py`

核心结果:

- `load_runtime_profile()` 可以解析默认 profile。
- seed corpus 路径解析为真实文件。
- SQLite 状态路径支持正式默认与测试 override。
- profile 校验会拒绝关闭 style gate 或打开动态 phrase 创建的配置。

## 4. 严谨验收测试

已执行:

```text
python -m pytest tests\test_phase8_0a_runtime_profile.py tests\test_phase8_0b_minimal_cli_entry.py -q
python -m pytest tests\test_phase7_8_minimalist_expression_corpus.py tests\test_phase7_9_minimalist_multiturn_dialogue_flow.py tests\test_phase7_10_longrun_stability.py tests\test_phase7_11_user_style_mirroring.py tests\test_phase8_0a_runtime_profile.py tests\test_phase8_0b_minimal_cli_entry.py -q
```

结果:

- Phase8.0 targeted: `7 passed`
- Phase7.8-8.0 combined: `32 passed`

## 5. 最终汇总

Phase8.0a 证明了 APV3.0test 已经从“测试阶段机制”整理出一个可启动的干净 runtime profile。后续最小 CLI、Web UI 或其他体验入口，都可以从同一个 profile 加载核心模块和固定词库，并把真实用户状态与测试临时数据库隔离。
