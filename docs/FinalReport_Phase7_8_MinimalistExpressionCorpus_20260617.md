# APV3 Phase7.8 Minimalist Expression Corpus 最终报告

日期: 2026-06-17
阶段: Phase7.8
状态: 通过

## 1. 设计

Phase7.8 吸收 `Design_APV3.0_MinimalistMutePersonaCorpus_v1_20260617.md`，目标是在 Phase7.7 的自然中文短句召回之上，建立一个极简、诚实、可教、低出错率的中文表达底座。

核心设计:

- 固定 120 条中文 phrase seed corpus，分为 tier 0/1/2 三层。
- `ExpressionPhraseMemory` 增加 `style_tier` 和 `phrase_kind` metadata。
- 召回时加入 `expression_style_bias`，同等支持度下更偏向 tier 0 极简短语。
- seed corpus 启动的词库默认 `allow_new_phrases=False`，runtime 不动态生成新 phrase。
- 新增 `style_redlines.py`，输出命中禁词、超过 3 token、感叹号等风格红线时 fallback 到 `不知道`。
- 新增 `observe_existing_phrase_cooccurrence`，外部教学表达必须匹配已有 phrase 序列，未匹配表达不倒灌进学生词库。

这一步不是让 APV3 变成固定回复机器人。词库只提供“可发声按钮”，真正何时使用哪个按钮仍由 feeling-expression 共现、支持度、奖励/惩罚和上下文证据逐步学习。

## 2. 审查完善

本阶段特别处理了 5 条红线:

- 禁词黑名单全程可验收: `非常/其实/但是/我觉得/你应该/...` 等输出命中即 fallback。
- token 数硬上限: 任意表达输出不得超过 3 个 token。
- 固定 seed corpus: `ExpressionPhraseMemory.from_seed_corpus()` 禁止动态新增 phrase。
- `phrase_kind` 只做 trace metadata，runtime 扫描禁止 `phrase_kind == ...` 语义分支。
- 失败偏诚实: 无强关联时输出 `不知道`，不编造长句。

为了不破坏 Phase7.0-7.7 的底层机制验收，本阶段没有把风格过滤器强塞到所有旧 runtime commit 路径里，而是先在 expression phrase 层完成风格守恒。后续多轮 dialogue runtime 接口接入时，可以把 `style_safe_tokens()` 放到最终提交前作为表达层出口。

## 3. 通过落地

新增:

- `apv3test/data/introspection_phrase_seed_corpus.json`
- `apv3test/runtime/style_redlines.py`
- `tests/test_phase7_8_minimalist_expression_corpus.py`
- `docs/FinalReport_Phase7_8_MinimalistExpressionCorpus_20260617.md`
- `reports/APV3_Phase7_8_MinimalistExpressionCorpus_Showcase_20260617.html`

更新:

- `apv3test/config/introspection_config.py`
- `apv3test/runtime/expression_phrase_memory.py`
- `apv3test/runtime/cooccurrence_learning.py`
- `apv3test/runtime/__init__.py`

实际 trace:

```text
records 120 tiers {0: 30, 1: 40, 2: 50}
p:resp:hello 你好 tier 0 safe 你好
p:resp:dunno 不知道 tier 0 safe 不知道
p:resp:cantyet 还不会 tier 0 safe 还不会
p:resp:morning 早 tier 0 safe 早
p:state:thinkw 想想看 tier 1 safe 想想看
p:combo:tryok 好试试 tier 2 safe 好试试
tier_win p:resp:ok
fallback 不知道
```

## 4. 严谨验收测试

已执行:

```text
python -m pytest APV3.0test\tests\test_phase7_8_minimalist_expression_corpus.py -q
python -m pytest APV3.0test\tests\test_phase7_7_natural_chinese_expression_stream.py -q
python -m pytest APV3.0test\tests\test_phase7_0_teacher_off_three_stage_milestone.py ... APV3.0test\tests\test_phase7_8_minimalist_expression_corpus.py -q
python -m pytest APV3.0test\tests -q
python -m compileall APV3.0test\apv3test APV3.0test\tests -q
rg -n "我觉得|其实|非常|但是|不过|所以|student_side_llm|answer_table|_most_common_reply|must_reply|phrase_kind ==|record\.phrase_kind ==" APV3.0test\apv3test\runtime --glob "!style_redlines.py"
```

结果:

- Phase7.8 targeted: `9 passed`
- Phase7.7 compatibility: `5 passed`
- Phase7.0-7.8 combined regression: `66 passed`
- Full suite: `239 passed`
- Compileall: passed
- Runtime redline/backdoor scan excluding the blacklist declaration file: no matches

## 5. 最终汇总

Phase7.8 证明了:

- APV3.0test 已拥有一个固定、可审计、低复杂度的中文表达按钮库。
- 同等证据下系统自然偏向更短、更诚实的表达。
- 未知表达不会被 runtime 动态加入 phrase memory，防止外部 LLM/教师倒灌污染。
- 风格红线能把 LLM 味、过长表达和夸张表达压回 `不知道`。
- SQLite warm-load 后，词库、学习到的支持度和召回行为保持一致。

仍不能宣称:

- 多轮连续中文对话已经完成。
- 同一 feeling 在不同 context 下的风格条件化已经完成。
- Web UI 和真实用户输入长程运行已经完成。

下一步建议 Phase7.9:

- 在这个固定风格底座上做多轮连续对话流。
- 每轮 `incoming_external_query -> feeling -> phrase recall -> style gate -> commit -> reward/punish/clarify`。
- 验证前一轮状态不会污染话题切换，惩罚会影响下一轮召回，SQLite 中途恢复后多轮行为等价。
