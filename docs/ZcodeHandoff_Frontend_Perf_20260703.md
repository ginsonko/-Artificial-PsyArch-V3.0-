# zcode 任务交接 — 前端修尾 + 性能接线批次（2026-07-03 第五批）

**背景**: Fable5 已完成性能修复（22.8s→2.9s，7-14×提速；根因=缺索引N+1+同窗口每turn重算100+次+SQLite模式；
详见 ColdSave 第十节——**红线: 零行为改动，不许以性能为由改召回公式或limit**）+ 两个后端支撑：
1. `/api/phase20_7/turn` 响应已有 `idle_pacing`（V1 已接）。
2. **新增 `GET /api/phase20_7/progress?session_id=xxx`**——turn 进行中实时返回 AP 当前阶段
   （中文 stage_label 如"逐字写草稿/回读草稿/想要请教"+ 最近5个行动），WAL 并发读不阻塞。

**全局红线**（每任务后必跑）:
```
python -m pytest tests/test_phase20_9j_grasp_gating.py tests/test_phase20_12c_text_input_no_borrowed_visual_signature.py tests/test_phase20_p0_p1_behavior_probes.py tests/test_phase20_m2_unified_recall_competition.py tests/test_phase20_m3_paradigm_column_recall.py tests/test_phase20_m4_feeling_sa_and_spontaneous_speech.py -q
```
- 不许动 runtime/*.py 和 experience_flow.py（性能修复刚收口）。
- 前端所有展示必须来自真实 API 数据，禁止假进度条/假动画。

---

## U1. 等待期实时阶段提示（用户点名要的）

`phase20_7_workbench.js`: 发送 turn 请求后、响应回来前，每 600ms 轮询
`GET /api/phase20_7/progress?session_id=<当前session>`，把状态栏从静态"处理输入中"改为动态:
`AP 正在: 逐字写草稿 (tick 583)`——用返回的 `stage_label` + `tick`。响应到达后停止轮询。
再加一行小字显示 `recent_actions` 的最近 3 个 label（如 `观察输入 → 逐字写草稿 → 回读草稿`），
让用户看到 AP 的"思考过程"在推进。
- 验收: 发一条消息，等待期状态栏至少变化一次且显示真实行动名；响应后恢复正常。

## U2. 想法云回滚为旧版效果（用户点名不满意）

用户原话:"想法云的样式和之前不一样,我要的是之前的前端那种半透明,浮动效果,互相之间有碰撞的那个想法云,你直接照搬过来"。
旧实现在 `apv3test/web/static/phase20_6_workbench.js`（thought cloud 相关函数）+ 对应 CSS。
把旧版想法云的渲染逻辑/样式**原样搬**进 phase20_7 前端（数据源仍是 phase20_7 的 tick trace），
不要自己重新设计。
- 验收: 想法云半透明、浮动、有碰撞回弹，视觉与 phase20_6 版一致。

## U3. 帮助页扩容到 2 万字以上（用户点名太少）

用户要求把白皮书非工程化内容整理进帮助页，分章节，2万-5万字。素材源（按此顺序抄写改写）:
1. `docs/AP_Bottom_Principles_Whitepaper_20260626.txt` 第一卷(总论/哲学)、第二卷(能量系统)、
   第五卷(情绪/行动)、第六卷(学习/记忆)、第十卷(场景案例)——去掉公式和工程红线，
   把每章改写成小白能懂的说明+比喻。
2. `docs/ColdSave_ActionCompetition_ParadigmLearning_ContinuousMind_20260703.md` 第一节
   （三个例子直接当"AP 如何决策"的科普素材，它们本来就是生活化例子）。
3. 固定内容（用户指定，逐字放）: 创始人:银子老师 / 联系: ginsonko@foxmail.com / QQ:474764004 /
   交流群:671372218 / 报道链接: https://www.scxxb.com.cn/index/index/articleDetail?id=195629&htmltype=not_html
   / 仅学术研究使用,禁止商业用途(商用需联系作者),禁止抄袭剽窃。
4. 必须有的章节: 什么是AP / 内生认知主义 / 与transformer的区别 / 与符号主义和规则系统的区别
   （防误解:不是if-else规则库——用"范式=学出来的行动逻辑,可退化可进化"解释）/ 为什么能数学泛化
   （用42+35例子）/ 为什么能实时学习 / 12种认知感受 / 情绪如何工作 / 六阶段学习协议 /
   教学协议与teacher-off / 接口一览(HTTP API 各端点) / FAQ。
- 布局: 左侧章节目录树+右侧正文，锚点跳转。
- 验收: 总字数≥2万（`python -c` 数一下正文字符），章节齐全，无"学会/智能涌现"过度声称。

## U4. 详情页样式修缮（用户点名太丑）

按用户原话逐项:
1. 学习闭环/生命周期验收/tick回放: 每条记录用卡片式分块（边框+标题+字段网格），不许纯文本堆叠。
2. 审计曲线: 缩小为 2-3 个/行的小图，**必须有横纵坐标轴+数值刻度**，图例清晰。
3. 记忆列表: 表格化（列: 时间/类型/内容摘要/角色标记），[纠错] 行用浅红底色区分。
4. 每个卡片头部加一句"这是什么"的说明文字（素材抄 U3 帮助页对应章节的首句）。
- 验收: 逐项截图对照用户批评点，全部消除。

## U5. 配置页音色试听 bug（用户点名）

用户原话:"更换音色后,测试朗读内容总是一样的,测试朗读的对象根本不是前端选择的这个对象,但实际用的音色是默认的xiaoyi"。
排查 `phase20_7_workbench.js` 配置页试听按钮: 它应读取**当前下拉框选中的 voice** 传给
speechSynthesis（或 TTS 合成接口），而不是写死 xiaoyi。修好后：选不同音色→试听声音不同；
保存后对话朗读用所选音色。另外确认 xiaoyi 音色的实现方式——若它是 Windows 本地 TTS 音色名，
在配置页注明"该音色依赖系统语音包，不同机器可用音色不同"（回答用户关于 github 分发的疑问:
**浏览器 speechSynthesis 的音色来自用户本机系统，无法随仓库分发**；若 xiaoyi 是本地合成文件
另议——先查明实现，在 `docs/TTS_Voice_Distribution_Answer_20260703.md` 写清楚结论给用户）。
- 验收: 试听对象=所选音色；文档写清音色分发结论。

## U6. 技能包分享/导入接通（用户点名之前就有）

旧功能在 `apv3test/runtime/phase20_memory_packages.py`（export/import/list/uninstall 全套已有，
web_chat.py 已 import）。前端配置页或详情页加"记忆包"区块: 导出（可按时间范围/关键词筛选——
看 `export_memory_package` 实际支持的筛选参数，有什么暴露什么，不新增后端逻辑）/导入/列表/卸载。
- 验收: 导出一个包→清一个测试 session→导入→记忆恢复可召回。

## U7. 预热包加载慢的体验修补

用户反馈"点击后加载时间非常久"。不改后端（灌包本来就要跑几十个真实 turn，这是特性不是bug——
它真的在学）: 前端把按钮点击后改为进度式提示——用 U1 的 progress 接口轮询显示
"正在教 AP 第 N 课: 逐字写草稿…"，加载完成显示"共学了 X 条对话+Y 条算术"。
- 验收: 加载期间有实时进度感，用户知道它在学而不是卡死。

---

执行顺序: U1 → U5 → U2 → U4 → U6 → U7 → U3（U3 字数多放最后慢慢写）。
全部完成后 Fable5 做发布前终审。
