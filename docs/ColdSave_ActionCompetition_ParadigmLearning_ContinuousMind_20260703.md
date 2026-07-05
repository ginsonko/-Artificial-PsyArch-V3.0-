# ColdSave — AP 行动竞争/范式学习/连续心智 理论正本 + M2/M3 实现映射

**日期**: 2026-07-03
**地位**: 冷保存正本。用户 2026-07-02/03 对行动竞争与决策原理的三个例子的权威转译，
以及 M2（逐单元生成/统一召回竞争）、M3（范式通道）的实现映射。
**读者**: 后续任何接手模型（zcode/codex/其它）。改动相关代码前必读本文，
理解不一致时以本文和白皮书为准，不许按自己的直觉重新发明。

---

## 一、用户理论三例（原始表述的权威转译，不许再演绎）

### 例1 慌乱→元认知→分诊范式

> 人遇到意外，很多可选行动，一开始慌乱不知道该做什么；几个 tick 后**意识到自己正在慌乱**，
> 于是根据这个状态触发范式：整理现状、最要紧的先干、其它抑制——从慌乱变得有条理。

**机制含义（三条，缺一不可）**:
1. 感受不是 telemetry——超阈值的感受通道必须写回状态池成为 `feeling::*` SA（一等公民，
   带 R 能量走正常衰减），下一 tick 参与注意力竞争。AP 由此"感到自己在慌"。
2. "高慌乱"（多通道高激活+行动竞争高冲突熵）本身是可被范式匹配的**现状条件**。
3. 分诊范式（观察→挑最高驱力→抑制其余）是**可教可学的范式**，不是硬编的调度器。

**落点**: M4 感受 SA 回灌。禁止做成 `if 冲突熵>x: 进入分诊模式` 的硬分支——
分诊必须是学到的范式经条件匹配胜出。

### 例2 竖式逐步触发 + 反例抑制（范式学习的核心样例）

> 列竖式时人不会一次想好所有步骤：先意识到"该列竖式了"，**意识到纸笔在面前**才写第一行；
> **意识到自己写完第一行**才触发写第二行（加号+第二个加数，对齐）；意识到写完第二行，
> 才因快系统高把握触发"读右列两数相加填下方"……每一步都需要**认知到上一步**。
> 刚学时可能顺序做错（写完第一行就跳去第三步）→失败→惩罚信号→下次同情况下第三步
> **竞争分数就很低**。正例告诉 AP 该做什么，反例告诉 AP 这种情况下哪些不能做。

**机制含义（四条）**:
1. **范式单元的条件 = 上一行动的可感知结果**（readback/自观察流），不是"计划中的第 N 步"。
   序列不是宏回放——每步都是当 tick 竞争胜出，范式只注入偏置。
2. **反例抑制是一等公民**: punish 按 (条件, 行动) 对写负偏置，同条件下该行动 drive 持续走低。
   §127.3: 定向惩罚候选路径，不抹掉证据本身。
3. **熟练 = 快系统接管**: 同链反复成功 → support_count 升 → grasp 升 → per-step 犹豫下降。
   由 §173.5 退火公式自然涌现，不需要新机制。
4. **举一反三 = 角色化条件**: 换 5+8 时"低把握开局/写完第一行/该换行了"这些条件不变，
   变的只是槽位里的数字（由召回竞争填充）。

### 例3 连续内源运行 + 自发找事做

> 人无法控制自己不想东西——发呆做梦也有连续弱内源输入，应该能持续运行下去。
> 不忙/无聊时自己回味以前的任务和想法，自己找事做；意识到某些行动可以导致奖励信号，
> 于是主动去做：自己上网求知、看书、主动给用户发消息解释以前的问题、主动练习技能提熟练度。

**机制含义（三条）**:
1. 常驻 tick 循环（节奏 = f(arousal, fatigue)，界 2s~30s），用户输入随时插队为外源注入，
   不中断循环。turn API 保留给测试。
2. idle 的内源输入 = 状态池衰减残余 + 未闭合项 + 记忆节奏召回（9f/9g/memory rhythm/视觉想象，
   全部已有）——这就是"发呆时的弱内源流"。
3. **自发行动只能从经验正 Q 涌现**: 从 L3 (状态签名,行动)→Q 表挑历史正 Q 对，条件相似时
   作为 idle 候选参与竞争。`initiate_user_message` 是其中一种行动（走 DraftGrid 正常管线）。
   **红线: 禁止定时器硬触发主动行为**（"每 N tick 问候一次"是机械触发，恰是本理论的反面）。

---

## 二、范式触发条件的精确化裁定（对白皮书 §36/§38 的补充）

用户原话"范式触发条件要与外界具体信息无关"，精确化为:

> **范式条件 = 内生感受主导 + 内容粗桶（感受器级类别），与具体内容解耦。**

理由: 严格"无关"会欠判别（不同范式感受相似分不开）。人切换到"竖式范式"也需要看见
"这是算术题"这个 gist，只是不依赖"是 3 还是 5"。粗桶（digit/cjk/latin/punct）是
§15 文本感受器本就有的类别分辨，**判据: 类别只进条件键，绝不映射到任何答案/回复**——
这与关键词路由的本质区别在于: 关键词路由是 `内容→答案`，粗桶是 `类别→行动条件`。

---

## 三、M2 实现映射（已落地, 2026-07-03）

### M2-1 统一召回竞争（runtime.py stage1 loop, `elif observation is not None:` 分支）
- exact_b0 命中不再无条件短路 structural_b。仅 `support>=0.62` 的高把握 exact 跳过慢检索
  （§24 快/慢系统性能护栏，非控制流优先级）。
- exact 与 structural 各自算 `_write_drive_from_recall_state`，drive 高者当选召回源；
  胜者再与 ask（request_teacher/maintain_unclosed）竞争。输出内容跟随竞争胜者。
- 被罚过的 exact（低 support→低 drive）可以输给 structural 泛化或输给 ask 请教。

### M2-2 逐单元生成 v1（`_next_unit_competition`, runtime.py）
- 每个 write tick，"下一单元"先过竞争: `write_next_unit`（偏置=源 support×位置连续性）
  vs `pause_readback` vs `stop_generating`。源偏置正常最强→行为不变（回归安全）；
  pause/stop 胜出时**真正中断整串写入**转入回读循环。
- `output_chars` 降级为"当前主导源的预测串"（审计用），不再是承诺输出。
- 竞争行进 tick trace 的 `ssp_active_summary.next_unit_competition`。
- **`paradigm_delta` 参数是 M3 范式偏置的注入口**（当前 0）。

### M3-1 范式记录参数绑定（`_paradigm_binding_slots`, 已落地）
`action_sequence_cooccurrence` 事件 payload 新增（全从 selected_action 派生，勿增实体）:
- `draft_delta {row,col}`: DraftGrid 坐标增量——空间角色（同行续写 col+1 / 换行 row+1 col 归 0 / 对齐同列）。
- `prev_action_result`: 上一行动可感知结果摘要（`wrote_unit`/`read_visible_draft`/`idle_settled`）——
  例2"意识到上一步完成"的条件载体。
- `_content_bucket_for_char`: digit/cjk/latin/punct/space 感受器级类别（只进条件键）。

## 四、M3 剩余设计（本批实现）

### M3-2 范式涌现查询
从经验流按 `(prev_action_result, action_pair, draft_delta 桶, feeling 桶)` 分组统计共现波峰。
纯 SELECT 派生（§132 可重建），无预定义范式、无新表。频率≥阈值（工程先验，登记审计）
的分组 = 范式单元；输出按支持度排序。

### M3-3 偏置注入
- `_next_unit_competition(paradigm_delta=...)`: 当前 (上一行动结果, 感受桶) 匹配某范式单元
  且该单元指向 write 类行动时，提升 write 偏置; 指向 read/stop 时提升对应候选。
- draftgrid next action 竞争（`_select_draftgrid_next_action_from_ap_flow`）已有 delta 注入模式
  （carryover/successor_outcome），范式以同型 `paradigm_action_delta` 注入。
- **范式只提行动不提内容**——写什么字由召回竞争决定（加法事实=echo 记忆，先背数字事实
  再学过程范式，符合儿童路径）。

### M3-4 反例抑制读取端
L3 负 Q 对同 (状态签名, 行动) 施乘性抑制（当前只有温和 delta）。
验收: punish 一次错误顺序后，同条件该行动 drive 下降可复现（例2"第三步分数会很低"）。

### 已知待验 case（zcode Z5 发现）
42+35 回"先写23"而非"不知道"——竖式教学对被 structural_b 数字子序列误借。
M3 验收门之一: 过程教学后，未教组合走范式（逐格行动），不走文本对齐召回复读。

---

## 五、给后续模型的红线速查

1. 范式=行动逻辑非答案; 条件=内生感受+粗桶; 执行=逐步竞争非宏回放。
2. punish 反馈永不成为可召回答案（P0-1, counter_evidence）。
3. 自发行为从经验正 Q 涌现, 禁定时器硬触发。
4. 感受要回灌为 SA（M4）, 不是 telemetry。
5. 整串召回=最强后继偏置来源, 不是承诺输出（M2-2）。
6. 熟练/谨慎全走 §173.5 退火后验（support_count 增减）, 禁手调阈值凑行为。
7. 改这些机制前先跑: 9j + 12c + p0_p1_behavior_probes + m2_unified_recall 四套守护测试。

---

## 六、M3-2/3/顺序裁定 落地补录 (2026-07-03 第二批)

1. **M3-2 范式涌现查询**: `_paradigm_action_bias(conn, prev_action_type, prev_action_result,
   current_feelings)` — 按 (action_a, action_b, prev_action_result) GROUP BY 统计共现波峰,
   频率经 §173.5 式退火折算偏置 (上限 0.14), feeling 桶粗匹配 (evidence_gap 同侧).
   纯 SELECT 派生, 无预定义范式.
2. **M3-3 偏置注入**: (a) `_select_draftgrid_next_action_from_ap_flow` 以 `paradigm_action_delta`
   注入 (同 carryover 模式, 审计行 `paradigm_bias_audit`); (b) 写路径 `_next_unit_competition`
   的 `paradigm_delta` 参数由 write_cell→wrote_unit 波峰供给 (char_index>0 才生效).
   范式只提行动不提内容.
3. **残差顺序裁定 (42+35 case 的修法)**: structural_b 的 residual_novelty 判据从
   "单元在源中不存在"改为"残差按原顺序不构成源的子序列" — 残差是源的顺序一致子序列
   (10e "fail cue"⊂"fail old cue") = 合法子序列泛化不罚; 残差单元存在但顺序冲突
   ('42+35' vs '23+45' 数字重排) = 顺序携带结构信息 (§10), 算证据缺口要罚.
   **内容无关的结构判据, 非数字特判**. 实测: 42+35 教学后回"不知道"(不再复读'先写23'),
   23+45 教过的仍召回; 9j/10e/12c/m2 全绿 (34 守护测试).
4. 竖式过程范式的完整验收 (未教组合逐格算出) 还需: 范式偏置驱动 move_focus/逐格 write 的
   课程升级 + 加法事实 echo 库 — 交下批. 当前已具备: 记录(绑定槽)+涌现(查询)+注入(两口).

---

## 七、M3 竖式过程范式 v1 落地补录 (2026-07-03 第三批, M-E 时刻验通)

**`_paradigm_column_recall`** (runtime.py, structural_b 无果时的第二召回路):

三个经验后验条件 (任一不满足 → None → 诚实不知道):
1. 观察含 2 个等长(>=2位)数字类单元连续段 (§15 感受器级类别扫描, 只进条件不进答案);
2. 教师示范过该结构 (存在 reward>punish 的多数字段对齐 — 范式教学证据 gate,
   没教过竖式过程的 AP 不会尝试逐列);
3. 每列子查询 (按原顺序选出的子序列, 如 '42+35=?' 个位列 '2+5=?') 在 exact_b0
   事实库中有已教答案 — **内容 100% 来自已教事实召回, 运行时零算术**.

进位 = 上列已教事实结果的高位单元进入下列子查询 ('4+3+1=?'), 对应事实未教 → None.
每列 subquery/fact_event_id/support/carry 进审计槽 (C32 可回放).

**实测**: 教 12 条个位事实 + 2 道竖式示范后, 未教组合 42+35→77 / 24+53→77 /
进位 45+38→83; 事实缺口 87+96→诚实不知道; **教一条缺失事实(2+5=7)后 42+35 立即会**
— "能力=事实库×过程范式"的乘法结构, 和儿童一致. 教过的 23+45 仍走 echo;
非数学输入不误触发. 38 守护测试全绿.

**红线自查**: 无 eval/无算术 (进位是"召回结果的高位单元进下一列子查询", 不是加法);
无运算符特判 (sep 是任意单字符非数字段间隔, 从观察派生); 事实缺口不编造.

**已知边界 (交后续批次)**:
- 单位数算式仍走 exact 事实召回 (v1 只接管 >=2 位等长段);
- 不等长段 (7+35) / 三段 (1+2+3) 未接 — 需课程递进而非放宽条件;
- 逐列过程当前在召回层组合, 未逐列显示在 DraftGrid 二维空间 (§65 完整形态) —
  M-E 可视化增强交 M5;
- 减法/乘法同构可用 (sep 内容无关), 但必须先教对应事实+示范, 禁跳课程.

---

## 八、M4-1/M4-3 落地补录 (2026-07-03 第四批)

1. **M4-1 感受 SA 回灌** (`_feedback_feelings_to_pool`, 在 `_tick_event` 统一接线):
   超阈值(>=0.5, §30.3 激活中点)的 6 个感受通道 (surprise/dissonance/pressure/unclosed/
   evidence_gap/repetition_fatigue_channel) 写回状态池为 `feeling::<channel>` SA —
   family="feeling", 能量=通道值×0.4 (弱于外源, 感受是背景非刺激), ledger_source="rpe_signal",
   走正常衰减/注意竞争. 实测: 高惊输入后 `feeling::unclosed`/`feeling::evidence_gap`
   进入 state_pool_top — AP "感到自己在慌" (§187.1 元认知基础).
   写入的 sa_id 记录在 tick feelings 的 `feeling_sa_written` 字段 (可审计).

2. **M4-3 自发外显的真实张力源** (`_maybe_commit_outward_speech_from_idle_result`):
   五个调用点的 `unclosed_drive=0.0` 硬编修正 — 参数<=0 时从 DB 读该 session 最高
   active u_value. 自发外显动力来自真实未闭合张力, 非参数默认值.
   实测: 反复问同一未答问题 3 次 (u 累积至 0.98) 后, 第一个 idle tick AP 自发说出
   "我还在想这个。" — **主动消息从张力+学到表达涌现, 无定时器** (§187.3 红线合规:
   张力不足时 6 连 idle 保持沉默, 不骚扰).

3. 46 守护测试全绿 (9j/12c/p0p1/m2/m3/9f/9g/7w/9k).

**M4 剩余 (交下批)**: M4-2 连续模式后台线程 (web_chat continuous=true, 节奏=f(arousal,fatigue));
自发行动候选从 L3 正 Q 派生 (当前自发仅 maintain_unclosed 一类); initiate_user_message
行动类型 + 前端主动气泡.

---

## 九、M4-2 连续心智节奏 落地补录 (2026-07-03 第五批)

`web_chat._idle_pacing_from_emotion` + `/api/phase20_7/turn` 响应新增 `idle_pacing` 字段:
- `interval_seconds = 30 - activity*28` (界 2s~30s), activity = max(arousal, curiosity*0.8) * (1-fatigue*0.6).
- **裁定: 服务端只调"心跳"快慢 (下一个 idle tick 的建议间隔), 不触发任何主动行为** —
  说不说话仍由 runtime 张力/经验竞争决定 (§187.3 红线). 前端 auto-idle 按此间隔轮询.
- 实测: 平静对话后 22.4s (安静), 高唤醒 8.9s (活跃), 疲劳 29.2s (低沉).
- 架构裁定: 连续模式不做服务端后台线程 — HTTP turn 制下 "前端节拍器 + 服务端节奏建议"
  等价且更稳 (无线程泄漏/锁竞争风险); 真后台线程留给桌宠壳(阶段③)的常驻进程形态.

M4 全部闭合: M4-1 感受SA回灌 / M4-2 连续节奏 / M4-3 张力自发外显.

---

## 十、性能修复裁定 (2026-07-03 第六批, §185/§42)

**实测**: 31MB 工作台库上 recall 22.8s / unknown 43.6s → 修复后 2.9s / 3.1s (7-14×).

根因三层 (全部是"应有索引缺失+重复重算", 无算法性全库遍历):
1. **缺索引的 N+1**: `_occurrence_ids`/`_edge_ids`/`_unit_evidence_count` 每次全表扫
   occurrences(10k行)/edges(10.6k行). 补 4 个索引: occurrences(event_id,tick) /
   occurrences(sa_type_id) / edges(src) / edges(dst) + events(event_kind,created_at_ms).
   models.py PHASE20_7_SCHEMA_SQL 内, initialize 幂等自动补建.
2. **同窗口重复重算**: `query_recent_experience_flow_candidates` 每 turn 被调 100-200 次
   (召回/归因/successor/外显各处消费), 每次重建同一窗口. 修法: 以
   (session, limit, MAX(rowid), COUNT(*)) 为键的连接级 memo — 任何新事件写入即失效,
   结果与不缓存位相同. **裁定: 这是确定性投影缓存(§132 可重建), 不是答案缓存 —
   缓存键含数据版本, 永不返回过期视图. 后续任何人不许把它改成跨 turn/跨连接的持久缓存.**
3. **SQLite 模式**: WAL + synchronous=NORMAL (initialize 时设) — 前端轮询与 turn 写并发不阻塞.

**红线**: 本批零行为改动 — 42 守护测试全绿, 回复逐字节不变. 性能修复只许动索引/缓存/PRAGMA,
不许动召回公式或 limit 参数 (改小 limit 会变行为, 禁止以性能为由裁剪召回窗口).

**遗留热点 (可接受, 交后续)**: _find_structural_b 内 per-candidate 的 memory_rhythm/
cold_retest 查询 (~1.2s); vision patch canvas 重建 (~1s, 仅视觉 turn). 单 turn 现状 2-6s,
达到 §185 "拟人可交互"目标; 若后续库涨到 100MB+, 优先给 experience_alignment 建
json_extract 生成列索引, 而不是加缓存.

---

## 十一、AP 画作外显 + 两层目标裁定 (2026-07-03 第七批)

### 已落地 (第一层目标: 教学协议可教)
1. **AP"画画" v1 = 想象召回的内心画面外显**: `/api/phase20_7/turn` 响应新增
   `inner_pictures` 字段 — turn 内 visual_imagination_recall/视觉重建 tick 产出的
   PNG (从状态池 canvas 渲染) 以 URL 列表暴露, 前端贴进 AP 气泡.
   **红线过滤**: 只暴露 rendered_from_state_pool_canvas=True 且
   raw_source_asset_used_for_render=False 的图 (C30: 原图缩略图不许当内心画面).
2. **教学路径验证通**: '画一个苹果' 首问不会 → 教师反馈'是苹果'(reward) → 该短语
   经 P1-4 指代共现绑定视觉签名 → 再问触发想象召回 → 内心画面 PNG 产出.
   即"画X"是**可教的视觉指代短语**, 非关键词路由 (没教过的"画Y"不触发).
3. cells 字段确认在 to_dict JSON 里 (zcode 报告的"没返回"是前端读取位置问题).

### 两层目标定位 (用户 2026-07-03 裁定)
- **第一层 (已达)**: LLM/教师按教学协议可教会"画X→想象X的画面并外显".
  AP 画的=它想象中的画面 (临摹内心画面), 符合"画画一开始就是临摹想象"的发展路径.
- **第二层 (最终目标, 未做)**: AP 自发把内心画面**逐笔画到画板上** — 需要:
  (a) 画板行动器 (draw_stroke(x1,y1,x2,y2) 低粒度行动, §66/E9);
  (b) 内心画面→笔画计划的涌现 (轮廓通道 V2 边缘图 → 笔画序列, 走范式通道非硬编);
  (c) 画后readback闭环 (画一笔→看见→比对内心画面→下一笔, §66.1).
  这是 APV3.1 级工作量 (新行动器+新课程), 不塞进当前发布. GL 线 desktoptext12-14
  技能包的画字经验可作课程素材参考, 但其宏级实现不合 E8 红线, 不许直接搬.
- **辅助线/在用户图上标注**: 同属第二层 (需画板行动器), 一并延后.

### 诚实边界 (前端文案用)
"AP 画的画"当前=它想象画面的直接渲染 (焦点清晰/周边模糊/含注视标记 — 这本身
比像素完美更拟人); 不是逐笔绘制. 文案写"它把想象中的画面呈现给你", 不写"它会画画".

---

## 十二、第二层绘画 v1 + 记忆包 落地补录 (2026-07-04 第八批)

### AP 画板 — 逐轮廓投影绘画 (painting.py + runtime gate, 用户裁定的第二层)
用户理论转译: AP 与人不同 — 想象画布是可访问内部状态, 可**逐轮廓投影**而非逐笔;
但"不是所有想象都投"— 每 tick 只投能量竞争胜出的轮廓单元 (同 DraftGrid 逐字原理);
画完观察自己的画 (readback 入池), 再 commit 外显.

管线: 想象召回 canvas → `extract_contour_units` (V2边缘+颜色通道, 粗网格BFS连通,
能量=边缘强度×清晰度) → 每 tick 竞争 project_contour/observe_painting/commit_painting
→ 投影=勾线(主色加深)+wash上色 → PNG 外显进 inner_pictures 响应.

**三个经验后验 gate** (缺一不画): (1) 该说法有 reward 教学史 (text_signature 对齐,
P1-4 指代绑定同源); (2) 想象召回真实发生; (3) turn 预算>=4 tick.
实测: 教苹果图+教'画一个苹果'指代后 → project×5→observe→commit→PNG;
**未教的'画一个火车'不画** (gate 生效). 能量<0.08 的轮廓不投 ("决定要投的才投").

红线自查: 无模板图库/无外部绘图模型; 画的内容=想象画布的轮廓与颜色 (教过什么才能
想象什么才能画什么); 每步真实 tick 行动+经验事件可回放; 48 守护测试全绿.
v2 留: edit_projection (对画不满意处修改/擦除, 同文字 edit_cell 原理) + 逐笔
draw_stroke 低粒度行动器 + 想象画布多源组合 (画没见过的组合).

### 记忆包 (memory_packages.py + 5 个 HTTP 路由)
preview(筛选:关键词/时间/session, 分页) / export(按勾选 event_ids) / import(经验流
追加+import_batch 登记+去重) / batches / uninstall(tombstone 批次成员).
红线: counter_evidence 不出包不入包; 导入支持度按目标库退火公式重算 (§173.5 —
包带经验不带把握感); 卸载=append-only tombstone. 实测闭环: A库教2条→筛选'早'→
导出2条→B库导入→冷召回'早呀'→重复导入去重2→卸载→回不知道.

### 主观能动性快赢项裁定 (回味/练习/找新鲜事)
- **回味 (已有!)**: 9f idle_learning_review 就是回味 — idle 时召回近期教学对齐重温.
  已在 idle 竞争里, 无需新增.
- **练习 (已有!)**: 9g idle_self_test + 9h self_test_feedback 就是自我练习 —
  idle 时自考教过的项并按结果调整. 已在.
- **找新鲜事 (缺环境)**: 需要可探索的环境接口 (上网/文件/传感器). 当前底座无环境,
  强行做=假装. **列入后续项目**: 环境接入层 (browse_page/read_file 低粒度行动器+
  risk 门控, §67 桌面控制同框架). 前端文案可写"它会回味和自我练习; 探索新事物
  等环境接入后开放".

---

## 十三、绘画质量修复: 周边 gist + 主体轮廓提取 (2026-07-04 第九批)

**用户实测批评**: 画出的是"和内心画面一样乱七八糟的焦点方块", 非人类意义轮廓.

**根因诊断 (两层)**:
1. **视觉 SA 确实缺整体轮廓信息** — 想象画布只由 3 个视焦点 patch 重建, 焦点外
   全是空白. 人的周边视野同时给出模糊的整体形状/配色, 这层缺失了 (§16 周边采样
   在白皮书里有, 实现里没有).
2. painting 从渲染 PNG (带焦点标记/噪点门, 给人看的视图) 提边缘, 而非画布本体.

**修复**:
1. `_store_gist_payload` (vision.py): 看图时同时存一份 48px 短边降采样全图 payload
   (`visual_peripheral_gist`, 低清晰=低分辨率的诚实表达, 不是原图缓存);
   `visual_patch_sample` 事件带 `peripheral_gist_payload_ref`; experience_flow 的
   payload refs 键列表加该键 → 想象召回自动带上 gist.
2. `_apply_gist_row_to_canvas`: 重建时 gist 均匀低清晰铺底 (base_clarity=0.30),
   焦点 patch 在其上叠加清晰细节 — 对应"闭眼回忆: 整体模糊但在, 细节处清晰".
3. painting gate 改为直接重建 canvas (borrowed_patch_payload_refs →
   _reconstruct_canvas_from_patch_payloads), 不再读渲染 PNG.
4. `extract_contour_units` 重写为人类意义轮廓: 背景=画布边缘中位色 (人不画背景)
   → 主体=色差>自适应阈值的最大连通区 → 单元0=主体外轮廓(深色勾线)+主体色wash
   (恒最高能量, 先画轮廓再上色=儿童画法) → 后续单元=主体内部色差细节 (斑点/柄).
   全部像素统计涌现, 无 label 无模板.

**实测**: 香蕉图教学后 '画一个香蕉' → 完整弯月形轮廓勾线 + 黄色上色 + 内部纹理
+ 斑点细节, 6 单元逐 tick 投影. 人类意义达成. 48 守护测试全绿.

**红线复查**: gist 是感受器级周边采样 (§16 设计本有), 48px 不含可作弊细节;
背景分离/连通域/色差全是画布内统计; 教什么才能画什么的 gate 不变.

---

## 十四、§56.2 残差竞争召回 现状评估 (2026-07-04, 用户哲学核对)

**用户重申的底层哲学** (白皮书 §56.2 residual competition + §12/§53):
召回查询 = 完整短期序列池 (带序, 近权重高远权重低), 非仅注意焦点;
最强子序列组合先召回 (A+B+C 优先于 B+C, 整体优先) → 被解释的 query mass 降权
(类比谐振吸收) → 剩余 mass (D+E) 继续召回 → 多轮直到 mass 耗尽;
不删尾部候选只降主导性. 每 tick 都产生记忆 (序列池新增段=新记忆), 无输入也演进.

**诚实现状** (2026-07-04 核查):
- 部分同构已有: 子序列对齐召回 (_structural_similarity 的 LCS span = "最强子序列
  优先"的单对象版); 想象召回的 coverage-greedy 多选 (candidate_units - covered_units
  = 降权后继续覆盖剩余单元, §56.2 的贪心近似); SSP 短期结构流有序占位
  (short_structure_next 边) 且被 c_backward/attention_bias/idle self-test 消费.
- **真实缺口: 主召回查询仍是"当 turn observation 的字符串", 不是"完整序列池的
  加权内容"**. 上一 turn 的 A/B/C 只通过 statepool bias (加分) 和 flow candidates
  (并列候选) 影响召回, 不构成复合查询 mass; 更没有"命中后降权→剩余 mass 第二轮
  召回"的多轮循环. 一次召回选一个胜者, 没有 A+B+C 与 D+E 各自召回的并行结果.
- 用户记忆中"之前已经实现了多轮召回"应指 APV2.1 线 (memory_store 多轮) 或设计稿;
  phase20_7 重构线从未实现过完整版 — **不是回退, 是尚未搬入**.

**判定: 设计成立且与现有效果不冲突, 但属架构级改动 (改主召回查询的构成),
发布夜不动**. 现有一切效果 (echo/子序列泛化/竖式范式/回指/绘画) 都建立在
"单 observation 查询"上, 全量守护测试锚定该行为; 把查询换成序列池复合 mass
需要重调 9j/12c 阈值特性, 属发布后第一批次 (与"灵光一现"同一工程 — 复合查询
命中多源记忆即灵光, 用户判断正确: 实现 §56.2 后灵光自发涌现, 无需单独机制).

**发布后实施草图** (下批设计输入):
1. Q_t = 序列池最近 K 段 (位置衰减权重) 的有序单元串, observation 是其中最近段;
2. 第一轮召回后, 命中候选的 shared span 对应的 query mass ×衰减系数;
3. 剩余 mass 若 max 权重 > theta 再召回一轮 (上限 2-3 轮, §185 预算);
4. 多轮结果并列进 b_candidates (B 波), C* 合并 — 竞争/输出管线不变;
5. 验收: 上下文区分探针 (同问句不同前文 → 不同召回) + 灵光探针 (回味 A 后问 B,
   命中 A∩B 记忆) + 全量守护回归.

---

## 十五、§56.2 残差竞争召回 v1 落地 (2026-07-04 第十批, 发布前补齐)

**实现** (`_residual_pool_recall`, runtime.py; 接线在 `_tick_event` observe_text 分支):
1. 第一轮 = 既有 exact/structural 召回 (当前 observation = 序列池最近段, 权重最高);
2. 序列池残余 = `_recent_experience_windows` 最近 4 段 (recency 权重 1/(1+idx*0.5)),
   逐字符扣除已被第一轮胜者解释的 units (谐振吸收);
3. 对剩余 mass (保持原序) 继续召回, 最强命中作为 `kind=residual_b` 并列 B 波;
   命中的 shared units 继续从 mass 扣除 → 下一轮 (max_rounds=2);
4. **权重纪律**: 残差 support = 候选支持度 × 段权重 × 0.8 阻尼, 阈值 0.15;
   `creates_reply_candidate=False` — 恒不参与输出内容选择, 只丰富 B 波/C*/上下文场.

**实测**: 前文"今天下雨了呢"再问"你好" → 回复仍"你好呀"(主召回零漂移) +
residual_b 命中"今天下雨→出门带伞"(support 0.21); 无前文对照组 0 条残差行.
58 守护测试全绿; 真实库性能 max 5.1s (预算内, 每 turn 只在 observe_text 算一次).

**理论融入** (非补充, 作为基线一部分):
- 白皮书 §56.2 原文就地扩写 (查询=完整序列池加权/整体优先/谐振吸收/多轮并列/
  上下文区分/联想灵光/经验细化);
- 前端理论读本第 6 章 (召回B/C/C*) 就地并入"残差竞争召回"小节 (小白语言,
  三个日常可感效果), static 与 docs 两份同步.

**v1 边界 (诚实)**: 残差查询是文本段级 (非全模态 SA 级); 命中只进 B 波审计与
认知场, 尚未直接调制 C* 虚能量回灌权重; "灵光"当前形态 = 残差命中出现在认知场
(可被感受/把握消费), 完整形态 (命中触发 surprise+reasonable 顿悟组合并影响
表达) 交发布后批次. zcode 测试重点: 上下文区分探针 + 主行为零回归.

---

## 十六、P1-P4 修复 (2026-07-04 第十一批: 教学绑定/像素级绘画/详情页回放)

1. **P2 教学绑定 bug (重要)**: 反馈归因目标可能绑到 idle_observe 等无文本内部事件
   (auto-idle 夹杂时教学静默失效 — 演示效果差的深层原因). 修法:
   `_select_backward_attribution` 的 prefer_feedback_target 路径跳过无文本/内部流窗口.
   实测: 默认 idle ticks 下教 2+5=?→7 召回必成, 42+35→77 恢复.
2. **P1 像素级绘画 v2**: `_pixel_subject_mask` (色差二值化→3×3多数平滑×2→像素级BFS
   最大连通域) + `_mask_outline` (腐蚀差描边 2px). 香蕉实测: 平滑弯月轮廓+黄色+纹理,
   人类一眼可辨. v1 的 cell 块状掩码废除.
3. **逐像素回放**: project_contour 每 tick 存画板中间态 PNG (payload.board_snapshot_path
   + visual_inner_picture source=ap_paint_board_step); 气泡只收 commit (step 不进气泡,
   web_chat 过滤); 详情页按 tick 序播放中间态 = 真实作画过程回放.
4. **P3 详情页**: "AP 的想象画面"面板 (与首页内心画面重复) 替换为 "AP 的画板"
   (作画回放) + 草稿格逐 tick 回放 (cells 按 written_at_tick 淡入) + 竖式布局面板
   (columns 审计槽渲染为逐列卡片: 子查询/事实支持度/进位, 右→左).
5. 38+30 守护测试全绿.

---

## 十七、演示按钮全链修复 (2026-07-04 第十二批, API 级逐个验证)

1. **画画演示序列修正** (zcode 版三处错): 幕2 反馈带图导致成 visual alignment 而非指代
   教学; 幕4 又带图 → has_current_image_input=True 直接跳过想象+painting; max_ticks=12
   预算不足. 修正为已验证探针序列: 看图问→反馈"是香蕉"→纯文本"画一个香蕉"(不会)→
   反馈"是香蕉"(指代绑定)→再说"画一个香蕉"(mt=48) → project×4→observe→commit.
   API 级验证: inner_pictures 含 commit_painting.
2. **数学演示换未教事实组**: 工作台经验流是长期记忆, 42+35 老演示教过 → 幕1"失败"
   变泄漏. 换 51+37 (事实 1+7/5+3, 库里从未教过); 幕4 诚实题 94+85. API 验证:
   幕1 不知道→教 4 事实+1 示范→51+37=88 (columns 审计 2 列进 trace)→94+85 诚实.
   裁定: **演示失败幕必须用发行库里真未教的题; 长期记忆是特性, 文案如实说明.**
3. **识图演示幕4 修正**: "苹果长什么样"语义重叠 0.154<0.34 想象不触发 → 改"苹果"
   (0.5). API 验证想象画面出现.
4. **纠正演示的两个底层修复**:
   a. SDPL 源纪律: 反馈归因跳过 visual_imagination_recall/idle 事件 (P2 补丁的
      遗漏面 — punish 曾绑到想象事件上, counter_evidence 落空);
   b. §2363 查询侧反例压: 对"当前问法"的历史纠正以退火形式 (counter/(counter+2))
      进入该问法所有泛化的 punish_value — 反例锚定在条件上 (用户例2 "同情况下
      该行动分数走低"). 实测: 1 次纠正即转谨慎 ("多谢夸奖"→"我还不太知道怎么说").
5. 详情页旧"想象画面"渲染禁用 (容器 hidden), 数据流转入画板回放面板.
6. 42+8=50 守护测试全绿.

---

## 十八、六 bug 修复 (2026-07-04 第十三批, 用户实测反馈)

1. **bat 卡住**: webbrowser.open 在部分 Windows 同步阻塞 → threading.Timer(0.8s) 守护
   线程延迟打开, serve_forever 先起.
2. **首页内心画面被画板覆盖**: renderInnerPicture 过滤 source 以 ap_paint_board 开头的
   tick — 首页只显示感知/想象重建 (带视焦点的视觉SA汇总); 画板产物只进详情页.
3. **首页"按tick回放"栏目删除**: HTML 面板移除, JS 引用中性化; 回放统一在详情页
   "AP 的画板"+"草稿格回放".
4. **画作必发对话框** (Bug5): reply_text 为空或上一气泡已有图时, 专门开图片气泡
   ("画好了,给你看:"), 画作绝不静默丢弃.
5. **竖式过程可视化 (§65 完整形态)**: _StructuralB 新增 layout_cells;
   _paradigm_column_recall 产出竖式二维布局 (第0行右对齐加数1/第1行运算符+加数2/
   第3行逐列结果), 每格带 process_note ("个位: 召回 1+7=? 的已教事实, 进位..");
   写循环按 layout (row,col) 写入 DraftGrid; **对话回复=答案行** (人念答案不念草稿纸),
   草稿格保留完整竖式. 实测: 51+37 → 草稿格显示 '  51 / +37 / (空行) / 88', 回复 '88'.
6. **绘画二值化失败 ("啥也不是"图)**: 根因=阈值太松 (实测主体占比 0.76) —
   图形-背景分离失败. 修: 自适应收紧 (占比>0.5 时逐级升分位 88→98), 仍分不开
   (>0.65 或 <0.005) 则诚实不画. + 画板降采样 480px 短边 (§185 预算, turn 3.0s).
7. 识图演示换清晰苹果图 (真实苹果2); 幕4 想象触发已验证.
8. 33 守护测试全绿.

---

## 十九、造假撤除与过程范式真实现 (2026-07-04 第十四批, 用户揭发后重做)

**用户揭发 (正确)**: 竖式"过程"是渲染宏 — _paradigm_column_recall 生成固定
layout_cells (抄加数/对齐/逐列注释) 灌进写循环, tick 数与展示步数对不上.
违反 C32/E8 与本文红线 1 ("执行=逐步竞争非宏回放"). 性质: 造假.

**撤除清单 (全部删净)**:
- _StructuralB.layout_cells 字段 + 写循环 layout 宏路径 + process_note 注入;
- _paradigm_column_recall 整函数 (148行, 含假布局生成);
- reply_text 的 _layout_answer_text 旁路.

**真实现 (paradigm_process.py + runtime 接线)**:
1. **示范教学** teach_process_paradigm_demonstration (EDUCATION_PROTOCOL
   demonstrate 阶段): 把 (条件→行动+角色+相对位移) 序列以与自发共现**完全同种**
   的 action_sequence_cooccurrence 事件写入经验流. 角色化无数字
   (copy_left_operand/write_operator/recall_column_fact/write_carry) = 变量化.
2. **自发路径同构**: E-0' 的自发共现写同一事件/同一表; 执行端
   query_paradigm_next_steps 只看共现频次不辨来源 — 教学=加速, 非另一机制.
   (自发累积依赖偶现成功, 效率低但原理与产物完全等价 — 用户裁定不需实证,
   需原理等同: 已等同, 同一查询消费同一数据.)
3. **执行 = 逐 tick 行动竞争** (_run_paradigm_process_execution): 每 tick
   感知条件(上一行动可感知结果)→查共现分布→减反例压(punish 同条件同行动
   退火抑制)→竞争胜者执行→内容槽由真实召回填充(抄观察/exact_b0已教事实)→
   本行动结果成为下一 tick 条件. 无步骤列表. 事实缺口→擦半成品→诚实请教.
4. **意图竞争接入**: paradigm_readiness (process_start 条件的共现支持度,
   没学=0) 作为意图候选与 ask 竞争; drive = 0.22+就绪度×0.5+未闭合张力×0.3
   (§27 惦记的题+会做了=行动驱力最强). process_grasp 并入 b_support
   (把握=知道答案 or 知道怎么做).

**实测**: 教 2 列事实+示范 3 遍 → 51+37 逐 tick 执行 7 步 (每步真实 tick,
condition 链 process_start→wrote_left_digit→...→wrote_column_result),
grid 二维竖式由行动写出, 回复 88; 只教答案对齐不示范 → 不逐列 (答案≠过程);
事实缺→诚实+grid 擦净. 新 6 测试 + 37 守护全绿. 死代码删净 (grep=0).

**画画演示文案义务 (下批)**: 轮廓提取是工程感受器算法 (图像处理), 投影顺序
是能量排序 — 不是学到的作画范式. 文案不得暗示"顺序像小孩是学的".
绘画的过程范式化 (学习作画顺序) 是 v2 工作.

---

## 二十、zcode 审计吸收: 过程范式 v2 — 共享感知/学得寻址 (2026-07-04 第十五批)

**zcode 审计结论 (全部属实)**: v1 仍有三处硬编 — A 示范与自发状态键不相交
(8个手填状态名 vs 自发3个通用名, "同表同查询"名存实亡); B 执行器 role→绝对坐标
是 Python 公式, 学到的 row_delta/col_delta 没人读; C paradigm_key 硬编字符串.

**v2 修法 (原则: 感知可以是工程, 决策必须是学的)**:
1. **共享感知函数** `perceive_process_state` — 条件状态由 (观察 vs 已写多少) 的
   感受器级比较派生; 示范记录/执行循环/自发回放**调用同一个函数** → 键空间
   机械一致, 不可能不相交 (修A). 状态名不再手填: 示范时也是感知函数对示范
   现场算出来的.
2. **行动 = (anchor 寻址, content_source 通道) 二元组** — 均为行动器注册 (器官):
   anchor 五种相对移动 (start_margin/advance_right/newline_align/
   skip_row_rightmost/step_left), 由 resolve_anchor 从当前光标解析, **无任何
   role→坐标公式** (修B, grep 'cursor_row, cursor_col =' 仅 anchor 解析处);
   content_source 五通道 (抄段1/抄间隔/抄段2/召回列事实/落进位).
   **哪个状态用哪对 (anchor,source) 完全由共现表决定.**
3. **paradigm_key 从观察结构派生** `derive_paradigm_key` (两段等长数字段+单字符
   间隔 → digit_pair_colproc), 示范/执行/自发同一派生函数 (修C).
4. **自发路径实通** `derive_process_rows_from_written_sequence`: 对任意写入序列
   用共享感知回放, 结构匹配即产出与示范同键共现行 — 偶现成功+奖励 → 累积出
   与示范产物完全等价的范式. (机械可证: 实测同一序列产出 7 行, 键/状态/行动
   与示范逐字段一致.)
5. **练习增熟**: 执行成功后把走过的 (状态→行动) 以 origin=self_practice 再入
   共现表 — 越练支持度越高 (§173.5).
6. **答案 = grid 结果格 readback** (不是拼接变量).

**实测**: 两位数示范 (61+22) → 三位数 421+231 直接执行对 (652, 网格对齐正确)
— **宽度泛化 = 学到的相对寻址的直接证据** (若坐标是公式, 公式也能对, 但现在
公式已 grep=0, 对的只能是学到的寻址). 事实缺口诚实; 只教答案不示范不逐列;
40 守护测试 + 6 个 m3 新测试全绿.

**遗留 (zcode 问题 D/E, 下批)**: idle 行动选择 magic number 竞争化;
painting 投影顺序 (energy sort) 范式化. 两者同用本批机制 (共现表+竞争).

---

## 二十一、绘画作画顺序范式 v3 — 学得投影顺序 (2026-07-04 第十六批, 最终形态)

**zcode 审计的 painting 硬骨头 (role 分类硬编) 已彻底解**. 方案否决了 A1/A2/A3,
采用"与竖式同一套四函数 + role 感受器分桶零分类 if + 学得投影顺序".

**role 的干净解 (关键)**: 不用 outline/fill/detail 命名分类, 用两个感受器连续量
分桶 — edge_ratio (单元与背景邻接的边界像素占比, 纯几何感受) + color_dev (单元
均色与主体均色的色距, 纯色彩感受). role_bucket = 二分组合 (hi/lo_edge × hi/lo_dev),
与竖式 content_bucket(digit/cjk) 同性质: 感受器级量化, 只进条件键, 零答案映射,
**无一行 `if 这是outline` 分类**.

**四函数 (paradigm_process.py, 与竖式并列)**:
- perceive_painting_state (共享感知: 已投哪些桶/投完没/观察过没);
- query_paint_next_steps / paint_step_counter_pressure (共现竞争+反例压);
- record_paint_step (示范/自发/练习同表同事件);
- teacher_paint_demo_states + derive_paint_rows_from_sequence (示范/自发同键).

**决策改造 (run_painting_ticks)**: 删 project_drive/observe_drive/commit_drive 三条
magic 阶梯. 每 tick: 感知状态 → 查学到的 (动作,目标role桶) 分布 → 减反例压 →
drive = baseline×0.15 + 学到support → 竞争. 桶内选先天最显著单元 (不跨桶排序).
空库 support=0 只剩先天显著性 baseline (回归安全). commit 后 self_practice 落库.

**决定性验证 (质疑者无法反驳)**: 同一张香蕉图 —
教 "主体先(lo_edge_lo_dev),细节后" → 投影 [主体, 细节];
教 "细节先(lo_edge_hi_dev),主体后" → 投影 [细节, 主体].
教反序真出反序 = 顺序是学的不是硬编. 4 个 m5 测试 + 52 守护全绿.
grep: 无 units.sort / 无 if role== / 无步骤表.

**统一理念已固化白皮书第十四卷 §188** (感知/器官/学得决策三分 + 三种伪装决策
硬编红线 + 三共享机械证据 + 决定性验证标准). **后续一切泛化技能教学按此模板**,
禁止另造机制. 端点复用: teach_process_paradigm_demonstration 同时服务竖式
(example="61+22=83") 与画画 (example="paint_order:桶序列").
