# APV3 Phase 8.4-8.17 Final Report - Humanlike Multimodal Foundation

日期: 2026-06-17

状态: 通过

## 1. 设计

Phase 8.4-8.17 的目标是把 Phase 7 已验证的中文表达与用户风格学习，推进到更底层的拟人多模态地基:

- 同一内容按来源区分学习: PERCEIVED / IMAGINED / HEARSAY / REMEMBERED / CORRECTION
- 想象可以参与学习，也可以犯错后被纠正
- 外部 surprise 可以把注意力从内源链拉回现实
- 文本、视觉、音频都先变成一等 SA，再进入统一状态池
- 视觉组合、fast mapping、自然纠错、长时记忆、跨 session 意图、自传式回忆都有最小可验闭环

## 2. 审查完善

实施中主动修复了两个结构风险:

- Delta-P 候选不能因单组件重合而晋升。现在组合候选必须至少有两个组件，且 held-out 情况中所有组件共同出现才计入收益。
- Web 工作台只作为 render-only 审计界面。Phase8 audit 数据由后端 runtime helper 生成，前端不参与认知决策。

## 3. 通过落地

核心新增能力:

- Phase 8.4: SDPL packet、五层 Q backoff、ComposedVocab、Delta-P gate
- Phase 8.5: CFS 四通道和五类来源感受
- Phase 8.6-8.7: 视觉感受器、视觉焦点行动、overlay trace
- Phase 8.8: 视觉组合泛化与 ablation gate
- Phase 8.9: 自然纠错与 packet-level credit
- Phase 8.10: 持续内源驱动、Pi、习惯化、sleep-like dilation、safety gate
- Phase 8.11: Web 工作台 Phase8 审计页
- Phase 8.12: fast mapping、shape bias、反向想象
- Phase 8.13: 音频 filterbank 感受器模板
- Phase 8.14: SDPL 拟人四 gate
- Phase 8.15: long-term cold/active 双层
- Phase 8.16: 跨 session 延迟意图
- Phase 8.17: 自传式回忆和 entity anchor

## 4. 严谨验收测试

已执行:

```text
pytest -q tests/test_phase8_4_sdpl_composed_vocab.py ... tests/test_phase8_17_autobiographical_recall.py
python scripts/red_line_check_v14.py --phase 8.10
python scripts/red_line_check_v14.py
python scripts/check_constant_governance.py
python -m compileall apv3test runtime tests -q
pytest -q
```

结果:

- Phase 8.4-8.17 targeted: 41 passed
- Phase 8.10 deliverable gate: PASS
- v14 red-line check: PASS
- constants governance: PASS, 157 numeric constants governed
- compileall: PASS
- full suite after audit-index correction: 321 passed
- audit trail index: Phase 8.2-8.17 report/test matrix present and tested

## 5. 最终汇总

Phase 8 已经证明 APV3 的拟人多模态地基可以在代码中闭环:

- 真实、想象、听闻、记忆、纠错来源可区分并参与学习
- 想象不是被禁用，而是被纳入后果学习和安全门约束
- 视觉/音频/text 感受器能统一进入 SA 状态池
- 视觉组合和 fast mapping 有最小泛化与反例验收
- 长时记忆、跨 session 意图、自传式回忆有最小持久化/召回机制

仍需后续工程化扩展:

- 扩展真实词库、视觉识别器和音频前端
- 把 Phase8 audit 更自然地接入真实 Web 试玩
- 做更长时间真实用户运行观察
