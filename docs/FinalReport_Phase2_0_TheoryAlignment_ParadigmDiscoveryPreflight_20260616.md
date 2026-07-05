# APV3.0test Phase2.0 Preflight 理论核对与最小范式自发现报告

日期: 2026-06-16

## 1. 设计

本轮先回答一个关键问题:

> 当前 APV3.0test 是否已经符合 APV3.0 数学模型, 并且可以自发发现范式?

结论必须分层:

- Phase1.3 已经证明最小持久化学习闭环: 学习证据写入、草稿行动、commit、SQLite 恢复、再召回。
- 但 Phase1.3 的范式是结构化 `LearningEpisode` 教进去的, 不是从原始观察序列自发发现的。
- 因此在进入旧 GL 技能小批复现前, 必须补一个最小范式自发现门。

本轮新增的最小门:

- 从重复观察中发现固定后继。
- 从同 cue 多回复中发现共享片段和中间 slot。
- 把发现结果转换为 AP-native `LearningEpisode`。
- 保存到 SQLite 后恢复并再召回。

## 2. 审查完善

核对设计稿:

- `Design_持久化中文对话底座_范式通道重构_v2_20260615.md` 要求真正自发范式发现, 并明确旧成功多为 harness 脚手架。
- `Design_APV3.0能量本体数学模型_20260615.md` 要求范式层是 MPE 在结构化预测坐标上的实现, 与能量层通过 SA 的 R/V/P/A/F 耦合。

核对当前实现:

- 已有 `EnergyObserver` / `PredictionRuler`: 只是 observe-only 和 baseline/ruler 最小门。
- 已有 `LearningEpisodeWriter`: 能写入被教的范式证据, 不是自发现。
- 已有 `TeacherProtocolRunner`: 只做顺序编排, 不做范式发现。
- 因此此前不能宣称“已经完整自发发现范式”。

本轮实现定位:

- `ParadigmDiscoveryEngine` 是 Phase2.0 preflight, 不是完整 v2.1 范式通道。
- 它不靠具体词表、答案表、规则路线或学生侧 LLM。
- 它从观察序列中做通用前缀/后缀/中间 slot 对齐。
- 它先覆盖 echo/successor/multi-reply aggregation 的最小可测雏形。

仍未实现的完整设计项:

- 锚相对有界全局对齐(NW-style DP)。
- RhythmChannel 边界签名与边界感受 SA 竞争。
- RelativeRelationStore 有向序票参与对齐。
- OnlineEmbeddingStore 只读关系重叠/coherence 计算。
- 感知原型层的跨模态稳定 token。
- 角色序列 Viterbi 联合解码。
- conf 与真实 prediction error 下降量耦合。

## 3. 通过落地

新增/更新文件:

- `APV3.0test/apv3test/config/paradigm_config.py`
- `APV3.0test/apv3test/runtime/paradigm_discovery.py`
- `APV3.0test/apv3test/config/__init__.py`
- `APV3.0test/apv3test/runtime/__init__.py`
- `APV3.0test/tests/test_phase2_0_paradigm_discovery_preflight.py`

新增 API:

- `APV3ParadigmDiscoveryConfig`
- `ParadigmObservation`
- `DiscoveredParadigm`
- `ParadigmDiscoveryEngine`

最小发现能力:

- 固定后继: 重复 `你好 -> 我在。` 可发现 `p:discovered:greeting_discovered`。
- 多回复聚合: `三顾 -> 茅庐` 与 `三顾 -> 臣于草庐` 可发现共享片段 `庐` 和 slot spans。
- 持久化再召回: 发现的 `yellow_object` 范式可写入 state, 保存 SQLite, 恢复后 probe 结果一致。

## 4. 严谨验收测试

已运行:

```powershell
python -m pytest APV3.0test/tests -q
```

结果:

```text
38 passed in 1.85s
```

已运行:

```powershell
$files = Get-ChildItem -Path APV3.0test\apv3test\config,APV3.0test\apv3test\runtime -Filter *.py | ForEach-Object { $_.FullName }; python -m py_compile @files
```

结果: 通过。

已运行禁用通道扫描:

```powershell
rg -n "keyword|answer_table|student_side_llm|branch_alignment|math_process_tokens|regex|full_sentence_macro" APV3.0test\apv3test APV3.0test\tests
```

结果: 无命中。

新增测试覆盖:

- `test_discovers_fixed_successor_from_repeated_observations`
- `test_discovers_shared_fragment_and_slot_from_multiple_replies`
- `test_discovered_paradigm_survives_sqlite_restore_and_recall`

## 5. 最终汇总

对你的问题的准确回答:

- 在 Phase1.3 结束时: 不能说已经具备完整自发范式发现。那时范式主要来自结构化教学写入。
- 本轮后: 可以说 APV3.0test 具备了“最小序列观察范式自发现雏形”, 能发现固定后继、多回复共享片段和 slot, 并能持久化恢复再召回。
- 但仍不能说完整 v2.1/APV3.0 范式通道完成, 因为完整 DP 对齐、边界感受、跨模态原型、关系重叠 coherence、Viterbi 角色解码还没落地。

这一步是必要的, 因为它把旧 GL 技能小批复现前的理论债补了一块: 不能只复现被教写入的范式, 还要开始证明 AP 可以从重复观察中自己抽出范式。

## 6. 下一步

建议下一轮继续 Phase2.0, 但不要直接全量旧 GL 技能:

1. 用 `ParadigmDiscoveryEngine` 复现 3 个最小旧技能:
   - 问候固定后继。
   - 成语多回复聚合。
   - 颜色+对象 slot。
2. 再补 Phase2.1: 更接近 v2.1 的锚相对 DP 对齐。
3. 再补 Phase2.2: 边界感受与跨 tick 序列切分。
4. 再补 Phase2.3: 跨模态感知原型 token。
5. 这些过关后, 才进入旧 GL 成功技能 3-5 个小批复现。

