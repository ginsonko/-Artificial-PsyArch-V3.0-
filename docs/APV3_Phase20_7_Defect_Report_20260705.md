# APV3 Phase 20.7 地毯式对抗性审查报告

**审查日期：** 2026-07-05  
**审查范围：** APV3.0test/apv3test/runtime/phase20_7/ 全部核心文件  
**审查方法：** 5路并行智能体独立审查，按白皮书逐条验证  
**理论依据：** AP_Core_Whitepaper_APV3_20260705.md

---

## 一、审查路径与文件覆盖

| 路径 | 主审文件 | 审查重点 |
|---|---|---|
| A1 | runtime.py | 主循环、行动SA、常驻tick、性能预算、B召回残差、行动竞争 |
| A2 | cognitive_cycle.py + experience_recall.py | 认知周期完整性、B召回残差中和、C*回灌 |
| A3 | paradigm_process.py | §188三分原则、范式硬编码、动态注册 |
| A4 | experience_flow.py + experience_candidate.py + experience_log.py | L1/L2/L3在线学习、共现统计 |
| A5 | models.py + memory_packages.py + vision.py + audio.py | 情感场数据模型、感官SA注入 |

---

## 二、全量缺陷清单

### 2.1 CRITICAL级缺陷（共18项）

---

**[DEFECT-RT-1] CRITICAL — 行动SA一等公民完全缺失**  
文件: `runtime.py`（全文，所有 insert_action_record 调用点，共14处）  
问题: grep "action::" 返回零匹配。所有 insert_action_record 调用后均直接进入 insert_experience_event，从不调用 upsert_sa_type + insert_occurrence。行动在SA存储层完全不可见，无L1/L2向量，不进 occurrences 表，不参与B召回，无法"靠想触发行动"。  
白皮书: §1.2 所有模态一等公民化；§7.3 行动SA命名 `action::<action_type>::<context_key>`，R能量=determination胜出量。

---

**[DEFECT-RT-2] CRITICAL — 无常驻tick后台循环**  
文件: `runtime.py:285`（run_phase20_7_turn 入口）  
问题: tick执行入口是同步函数，调用者每次传入一条用户消息才运行一轮后返回。代码中无后台线程、无asyncio循环、无任何持续调度机制。AP在用户沉默时完全静止。  
白皮书: §12（GAP-04）常驻tick是AP内驱的物理基础，idle tick期间须继续做SA衰减和C*回灌。

---

**[DEFECT-RT-3] CRITICAL — 无wall-clock性能预算（time模块未导入）**  
文件: `runtime.py:1-9`（import段）  
问题: 文件完全未导入time模块（time/perf_counter/monotonic均无）。turn_tick_budget = max(1, int(max_ticks))，所有预算判断均为 `tick - turn_start_tick >= turn_tick_budget`，与wall-clock无关。  
白皮书: §12.3（GAP-05）预算必须为wall-clock ms（50-150ms），而非tick计数。

---

**[DEFECT-RT-4] CRITICAL — 超预算无降级行为**  
文件: `runtime.py`（全文，所有预算超出分支）  
问题: tick达到turn_tick_budget时，所有分支仅执行`break`截断。无K减半逻辑（grep "K_factor"/"K.*halv" 零匹配），无request_teacher偏置注入，无分段耗时写入RuntimeTickEvent。  
白皮书: §12.3 超预算时须K减半 + request_teacher偏置置位 + 分段耗时写入。

---

**[DEFECT-CC-1] CRITICAL — no_write_reason guard跳过整个认知周期**  
文件: `cognitive_cycle.py:33-34`  
问题: `if event.no_write_reason: return event` 在入口处直接提前返回，跳过整个认知周期（B召回、C_forward/backward、C*回灌、feeling通道更新全部被跳过）。no_write_reason是信息来源标注，不应控制认知周期的执行。  
白皮书: 每tick必须完整执行认知周期，感知"未产生写入"不等于认知不活动。

---

**[DEFECT-CC-2] CRITICAL — B召回残差中和三路机制完全缺失**  
文件: `cognitive_cycle.py:759-770`（_neutralized_occurrences）  
问题: 中和逻辑仅为每个occurrence_id附上neutralize_score浮点标注，无任何能量修改。无"记忆侧多余部分→保留虚能量"与"现实侧多余部分→保留实能量"的分拆计算。grep "memory.*excess"/"virtual_energy.*resid" 零匹配。  
白皮书: §5 B召回三路：完全匹配→中和；记忆多余→虚能量留池；现实多余→实能量留池。

---

**[DEFECT-PD-1] CRITICAL — derive_paradigm_key()硬编码字符串返回**  
文件: `paradigm_process.py:73`  
问题: 函数直接 `return "digit_pair_colproc"`，无注册表查询。除此字符串外所有输入均返回空字符串，新范式不能在运行时注册生效。  
白皮书: §11（§188-B面）决策层禁止硬编码，范式触发必须查可注册表。

---

**[DEFECT-PD-2] CRITICAL — ANCHORS/CONTENT_SOURCES硬编码Python元组**  
文件: `paradigm_process.py:47-56`  
问题: `ANCHORS = ("row", "col", "cell", ...)` 和 `CONTENT_SOURCES = ("digit_pair",...)` 是模块级硬编码元组。所有范式锚点和内容源均写死在Python代码中。  
白皮书: §11（§188-B面）锚点和内容源必须来自可注册的数据结构，不能写死在代码里。

---

**[DEFECT-PD-3] CRITICAL — query_paradigm_next_steps()静态白名单阻塞动态注册**  
文件: `paradigm_process.py:211`  
问题: 函数包含 `anchor not in ANCHORS` 过滤条件，所有动态注册的新锚点均被该静态白名单过滤掉，永远无法进入候选步骤。  
白皮书: §11 新注册的范式步骤必须可被动态发现，不能被硬编码白名单拦截。

---

**[DEFECT-PD-4] CRITICAL — resolve_anchor()是if/elif分发表，坐标硬编码**  
文件: `paradigm_process.py:127-146`  
问题: 函数是纯 if/elif 链，每种锚点类型返回硬编码坐标（如`start_margin: return (0, 2)`）。新锚点类型无法通过注册接入。  
白皮书: §11（§188-B面）锚点解析必须查注册表，不能是代码内分发表。

---

**[DEFECT-L1-1] CRITICAL — L1更新仅存在于离线批量重建，无实时在线更新**  
文件: `experience_log.py:953-1084`（rebuild_phase20_7_indexes）  
问题: 所有L1向量更新均在rebuild_phase20_7_indexes批量函数中执行（先全量清零再顺序重放）。三个文件中找不到每次tick共现时触发的实时L1更新路径。  
白皮书: §10.1 L1是在线学习，每次两个SA共现时立即做梯度更新。

---

**[DEFECT-L2-1] CRITICAL — L2是pair-level线性对，白皮书要求group-level超图共现**  
文件: `experience_log.py:1091-1133`  
问题: L2实现遍历output_chars[0]→output_chars[1]→...，每次只建立前后两字符的pair edge。这是序列对，不是同tick所有SA作为一个整体的组级共现。无法表达"视觉SA和文本SA在同tick出现"这种跨模态组内关联。  
白皮书: §10.2 L2记录多个SA在同一tick共现，是超图节点级别的组关系，不是相邻对。

---

**[DEFECT-EM-1] CRITICAL — 8通道NT情感场无数据类，无DB持久化表**  
文件: `models.py:75`（RuntimeTickEventV2.emotion字段），`models.py:156-394`（PHASE20_7_SCHEMA_SQL）  
问题: emotion字段是`Mapping[str, Any]`无结构dict；SCHEMA的14张表中无phase20_7_emotion_field持久化表；无DA/ADR/OXY/SER/END/COR/NOV/FOC 8个命名字段。每turn结束后情感状态丢失，从未被持久化。  
白皮书: §8 8通道NT情感场是AP持续内心状态的核心，必须有结构化数据模型和持久化。

---

**[DEFECT-VS-1] CRITICAL — feeling::* SA注入在vision.py中完全缺失**  
文件: `vision.py`（run_visual_receptor_ticks函数，全文）  
问题: feelings字段在run_visual_receptor_ticks中从不填充，永远为空。视觉感知不向状态池注入任何feeling::*类SA。  
白皮书: §9 视觉感知应触发feeling::* SA注入（如feeling::curious当看到新奇内容）。

---

**[DEFECT-VS-2] CRITICAL — 视觉SA虚能量v=0.0硬编码，FOC通道未耦合**  
文件: `vision.py:1033/1048`；`vision.py:1134-1148`（_inject_visual_state）  
问题: 所有视觉occurrence的v硬编码为0.0；_inject_visual_state中real_energy=0.42硬编码，与FOC通道完全无关。  
白皮书: §13.1 视觉清晰度（real_energy）应耦合FOC通道；虚能量v应反映视觉SA的预期程度。

---

**[DEFECT-AU-1] CRITICAL — 音频无频率带提取，仅文件存在性审计**  
文件: `audio.py:422-434`（_inject_audio_state）  
问题: 函数只提取source_hash和duration_ms，无任何频率带、能量、节奏特征提取。audio_unit:: SA注入在整个文件中不存在（grep"audio_unit::" 零匹配）。音频感知退化为"知道有个声音文件"。  
白皮书: §13.2 音频感受器应提取频率带、幅度、节奏等特征作为SA，这是听觉通道的基础信息。

---

**[DEFECT-AU-2] CRITICAL — TTS输出回路断裂，AP听不到自己说话**  
文件: `audio.py:283-340`（TTS合成段）  
问题: synthesized wav合成后直接返回，从不经过audio receptor重处理。AP的语音输出不会生成任何SA，AP无法感知自己说的话。  
白皮书: §13.2 TTS输出应回流音频感受器，AP应能"听到自己说话"并产生对应SA。

---

**[DEFECT-AU-3] CRITICAL — feeling::* SA注入在audio.py中完全缺失**  
文件: `audio.py`（全文）  
问题: 所有SA的family均为audio_audit::或tts_voice::，无任何feeling::前缀SA。音频感知不向状态池注入任何情感感受SA。  
白皮书: §9 音频感知应触发feeling::* SA注入（如feeling::alert当听到突然的声音）。

---

### 2.2 MAJOR级缺陷（共15项）

---

**[DEFECT-RT-5] MAJOR — idle tick是一次性调用，非持续循环**  
文件: `runtime.py:472`  
问题: _run_idle_think_tick仅在条件全部满足时单次调用后返回，没有循环调度，没有在等待用户时持续执行。

---

**[DEFECT-RT-6] MAJOR — B召回残差residual_units未接入能量通道**  
文件: `runtime.py:240`（_StructuralB.residual_units）  
问题: residual_units字段存在但只用于覆盖范围计算，未与virtual/real能量通道的pool entry挂钩。

---

**[DEFECT-RT-7] MAJOR — determination是绝对drive值，不是竞争胜出量**  
文件: `runtime.py:7221-7228`（_selected_drive_from_competition）  
问题: 函数直接返回胜者绝对drive值，未计算winner_drive - second_drive差值。grep "determination"/"win_margin"/"second_drive" 零匹配。

---

**[DEFECT-CC-3] MAJOR — C*虚能量计算但未注入状态池**  
文件: `cognitive_cycle.py:554`（_apply_cstar_statepool_feedback）  
问题: C*虚能量值被计算出来，但仅被记录为日志字段，从不调用任何insert_occurrence或update_occurrence写入状态池。

---

**[DEFECT-L1-2] MAJOR — L1学习率是退火公式，白皮书要求固定α=0.01**  
文件: `experience_log.py:367-368`  
问题: lr = lr_min + (lr_max - lr_min) * exp(-support_count/tau)，lr_max=0.08是白皮书值的8倍，导致早期学习过激。

---

**[DEFECT-L1-3] MAJOR — L1更新是单向的，input SA向量从不更新**  
文件: `experience_log.py:1037-1058`  
问题: rebuild只遍历output_sa_ids做更新，input_sa_ids只用于计算参考均值，input SA自身向量从不更新。

---

**[DEFECT-L1-4] MAJOR — flow候选召回未传l1_vector_similarity，L1学习成果不影响实际召回**  
文件: `experience_flow.py:564-596`（_support_from_occurrences）  
问题: 调用compute_unified_experience_support时未传l1_vector_similarity，该参数默认0.0，学到的向量在召回路径中完全无效。

---

**[DEFECT-L2-2] MAJOR — L2仅批量重建，无实时在线更新**  
文件: `experience_log.py:1091-1159`  
问题: L2 rebuild与L1 rebuild同样只在rebuild函数中执行，无tick触发的实时L2在线更新。

---

**[DEFECT-L2-3] MAJOR — L2只统计输出字符序列内部，不含跨角色/跨模态共现**  
文件: `experience_log.py:1097-1099`  
问题: 只处理len(output_chars)>=2的事件，只追踪输出字符序列内部相邻对。不统计：①input与output间共现；②文本SA与视觉SA跨模态共现；③感受/行动SA与文本SA共现。

---

**[DEFECT-L3-1] MAJOR — L3通过时序近似恢复action，不是direct action_record_id关联**  
文件: `experience_log.py:1210-1223`  
问题: rebuild L3时取feedback_tick之前最近一条action_record近似恢复，同tick行动被`tick<?`条件漏掉，多并发行动时恢复可能错位。

---

**[DEFECT-COV-1] MAJOR — 共现统计窗口不包含行动类事件**  
文件: `experience_flow.py:88-99`（event_kind IN列表）  
问题: 共现候选SQL的event_kind白名单完全不包含行动类事件，行动SA永远不进入共现窗口，L1/L2学不到行动与其他模态的关联。

---

**[DEFECT-COV-2] MAJOR — 共现统计窗口不包含感受/情绪类事件**  
文件: `experience_flow.py:88-99`  
问题: feeling_update/emotion_receptor等感受模态事件不在event_kind白名单中，感受SA无法参与共现统计。

---

**[DEFECT-EM-2] MAJOR — 无跨turn情感持久化，每turn重置到默认值**  
文件: `models.py`（无phase20_7_emotion_snapshot表）  
问题: 状态池是纯内存，每turn开始时从默认值初始化情感状态，用户感受不到情绪积累。这是用户反馈"呆感"的直接根因之一。

---

**[DEFECT-VS-3] MAJOR — 无source_mask，R_sketch和V_sketch共用canvas_pixels**  
文件: `vision.py`（全文，SA注入段）  
问题: 无source_mask字段标注视觉SA来源（感受器/记忆/预测）。内心画面三层合成（白皮书§13.1 inner_picture = α×R_sketch + β×B_recall + γ×C*）无法实现。

---

**[DEFECT-AU-4] MAJOR — audio.py无感受SA注入路径**  
文件: `audio.py`（全文）  
问题: 全文无任何feeling::*SA注入，音频感知不产生情感响应。

---

### 2.3 MINOR级缺陷（共6项）

---

**[DEFECT-CC-4] MINOR — C_forward生成文字注释字符串，不是虚能量SA结构**  
文件: `cognitive_cycle.py:430-462`  
问题: C_forward产生的是文本注释字符串，不是带v字段的虚能量SA结构，无法直接向状态池注入虚能量。

---

**[DEFECT-RT-8] MINOR — residual_units字段存在但未被处理**  
文件: `runtime.py:240`  
问题: _StructuralB dataclass有residual_units字段但后续代码只用于集合运算，从不对应能量通道。

---

**[DEFECT-L1-5] MINOR — prediction_error使用固定代理公式**  
文件: `experience_log.py:1043`  
问题: prediction_error = min(1.0, 0.5+reward*0.3+punish*0.3)，中性事件错误地被赋予0.5的预测误差，影响向量更新方向。

---

**[DEFECT-L3-2] MINOR — L3硬编码5种行动类型白名单**  
文件: `experience_log.py:626-628`（L3_OUTWARD_ACTION_TYPES）  
问题: L3只调制5种硬编码行动类型，新增行动类型（如express_emotion）后L3对其静默不学习，无运行时警告。

---

**[DEFECT-COV-3] MINOR — L2重建使用单事务，中途崩溃全量回滚**  
文件: `experience_log.py:957, 1275`  
问题: L1/L2/L3所有向量更新在单个事务中直到1275行才commit，中途崩溃导致全量回滚且index_registry未更新，重建状态不可恢复。

---

**[DEFECT-VS-4] MINOR — _inject_visual_state的real_energy=0.42完全硬编码**  
文件: `vision.py:1134-1148`  
问题: 视觉SA的real_energy用硬编码常量0.42，不反映图像内容特征（如显著性、新颖度、清晰度）。

---

## 三、缺陷分布统计

| 审查路径 | CRITICAL | MAJOR | MINOR | 合计 |
|---|---|---|---|---|
| A1 runtime.py | 4 | 3 | 1 | 8 |
| A2 cognitive_cycle.py | 2 | 1 | 1 | 4 |
| A3 paradigm_process.py | 4 | 0 | 0 | 4 |
| A4 experience_*.py | 2 | 9 | 3 | 14 |
| A5 models/vision/audio | 6 | 4 | 1 | 11 |
| **合计** | **18** | **17** | **6** | **41** |

---

## 四、白皮书条款覆盖核查

| 白皮书条款 | 描述 | 当前状态 |
|---|---|---|
| §1.2 | 所有模态SA一等公民 | **未实现（行动模态缺失）** |
| §5 | B召回三路残差中和 | **未实现（仅打标签，无能量操作）** |
| §7.3 | action:: SA命名与R能量 | **未实现** |
| §8 | 8通道NT情感场结构化+持久化 | **未实现（untyped dict，无DB表）** |
| §9 | feeling::* SA注入（视觉/音频通道） | **未实现（两个通道均缺失）** |
| §10.1 | L1在线实时梯度更新 | **未实现（仅离线批量重建）** |
| §10.2 | L2 group-level超图共现 | **未实现（仅pair-level线性对）** |
| §10.3 | L3 action_record_id直接关联 | **部分实现（通过时序近似，有丢失风险）** |
| §11/§188-B | 范式动态注册，决策无硬编码 | **未实现（4处硬编码）** |
| §12/GAP-04 | 常驻tick循环 | **未实现（每turn单次调用）** |
| §12.3/GAP-05 | wall-clock性能预算+降级 | **未实现（tick计数，无降级）** |
| §13.1 | 视觉SA source_mask + 三层合成 | **未实现** |
| §13.2 | 音频频率带提取 + TTS回路 | **未实现** |
| §14 | C*虚能量注入状态池 | **未实现（仅计算未注入）** |

**14项白皮书核心条款，当前全部未实现或部分实现。**

---

## 五、"呆感"直接根因对应

> 用户2026-07-04晚间测试反馈："呆呆傻傻"

| 呆感表现 | 对应缺陷 |
|---|---|
| 情感无连续性，每轮情绪重置 | DEFECT-EM-1（无持久化表）+ DEFECT-EM-2（无跨turn恢复） |
| 开放性问题失语 | DEFECT-L1-1（L1学习无效）+ DEFECT-L1-4（学到的L1不影响召回） |
| 无内驱驻波，用户沉默时AP完全静止 | DEFECT-RT-2（无常驻tick）+ DEFECT-RT-5（idle tick一次性） |
| B召回内容单薄，C_forward预测无效 | DEFECT-CC-2（B残差中和缺失）+ DEFECT-CC-3（C*未注入）+ DEFECT-RT-6（残差未接能量） |

---

*本报告由5路并行对抗性智能体于2026-07-05生成，共计发现缺陷41项（CRITICAL 18项，MAJOR 17项，MINOR 6项）。*
