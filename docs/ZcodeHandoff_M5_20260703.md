# zcode 任务交接 — M5 批次「小白一键惊艳」（2026-07-03 第四批）

**目标重申（用户原话转译）**: 小白拉取仓库后，**双击一个 bat 文件**就能进前端测试观察——
一个除 transformer 外、有足够泛化能力和拟人效果的全新架构自由对话底座。
惊艳 = 六时刻可现场复现（M-A 活的 / M-B 在想 / M-C 教得动 / M-D 不糊弄 / M-E 会算不是背 / M-F 有心情），
且全部由真实 tick trace 支撑，无脚本伪造。

**Fable5 已完成**: M4-2 连续心智节奏——`/api/phase20_7/turn` 响应新增 `idle_pacing` 字段
（`interval_seconds` 2~30s，由 arousal/curiosity/fatigue 派生；只调心跳快慢不触发行为）。
实测: 平静 22.4s / 高唤醒 8.9s / 疲劳 29.2s。
**必读**: `docs/ColdSave_ActionCompetition_ParadigmLearning_ContinuousMind_20260703.md` 第八、九节。

**全局红线**（每任务后必跑）:
```
python -m pytest tests/test_phase20_9j_grasp_gating.py tests/test_phase20_12c_text_input_no_borrowed_visual_signature.py tests/test_phase20_p0_p1_behavior_probes.py tests/test_phase20_m2_unified_recall_competition.py tests/test_phase20_m3_paradigm_column_recall.py tests/test_phase20_m4_feeling_sa_and_spontaneous_speech.py -q
```
- 前端/脚本不许预置任何答案或伪造 tick；所有演示必须走真实 turn。
- 文案不许出现"学会/收敛/完成/智能涌现"这类过度声称；用"记住了/会用范式组合了/还在学"。
- 规格不清 → BLOCKED。

---

## V1. auto-idle 接入自适应节奏

`apv3test/web/static/phase20_7_workbench.js`:
- auto-idle 轮询间隔从固定值改为读上一次 turn 响应的 `idle_pacing.interval_seconds`（毫秒化）。
  无该字段时退回现有默认。
- 状态栏显示当前心跳: `心智节奏: 8.9s (活跃)` — interval<10 显示"活跃"，>20 显示"安静"，中间"平稳"。
- 验收: 打开 auto-idle，教学互动几轮后观察间隔变化（对话热烈时变短）；关闭 auto-idle 一切如旧。

## V2. 一键启动 bat + README 快速开始

1. 仓库根目录新建 `启动APV3体验台.bat`（GBK 编码保存，防中文乱码）:
   ```bat
   @echo off
   cd /d %~dp0
   python -m apv3test.web_chat --port 8765 --open
   pause
   ```
   `--open` 参数已存在（web_chat.py main），会自动开浏览器。
2. 若 `--open` 打开的是根路径而非 /phase20_7，改 web_chat.py 的 webbrowser.open 目标为
   `http://{host}:{port}/phase20_7`（只改 URL 字符串，别的不动）。
3. `README.md` 顶部加"快速开始"一节: 装 Python 3.11+ → `pip install -r requirements.txt`
   （若无 requirements.txt，列出实际依赖 pyyaml 等，先 `python -c "import yaml"` 验证哪些缺）→
   双击 bat → 浏览器自动打开体验台。
- 验收: 干净 shell 双击 bat，浏览器自动开 /phase20_7 且页面可交互。

## V3. 首屏「教学之旅」引导卡

前端右侧（或顶部）加 5 张可点击引导卡（纯前端，点卡自动往输入框填内容+提示下一步，
不自动发送——让小白自己按发送，参与感）:
1. **教它说话**: 提示输入"你好"→ AP 说不知道 → 提示填反馈"你好呀"奖励 → 再问"你好"→ 会了
2. **考它泛化**: 提示输入"没错,你真聪明"教"谢谢"，再问"你真聪明"→ 泛化回答
3. **纠正它**: 提示对一个回答给 punish 反馈 → 再问 → 它变谨慎（不复读被纠正的话）
4. **教它算术**: 按"体验数学"按钮（已有）→ 看它用范式算没教过的题
5. **看它主动**: 提示连问三遍"周末去哪玩好呢"不给答案 → 开 auto-idle → 等它自己说"我还在想这个。"
每张卡完成后打个 ✓（前端 localStorage 记录）。
- 验收: 5 张卡全流程手动走通，各步实际行为与卡文案一致（不一致改文案，不许改 runtime）。

## V4. 首屏预热包（可选加载，非默认）

前端加"加载生活经验包"按钮（与"加载范式种子"并排）:
- 新建 `scripts/build_starter_pack.py`: 用真实教学管线（run_phase20_7_turn + TeacherFeedback）
  向指定 DB 教 ~25 条日常对话对（内容自拟: 问候/道谢/道别/简单常识各几条）+ 13 条个位加法事实
  + 2 道竖式示范（抄 teach_vertical_addition.py 序列）。
- web_chat.py 加 `/api/phase20_7/load_starter_pack` 路由，调该脚本逻辑写工作台 DB（session_id
  用 `starter_pack`）。
- **判据（红线）**: 预热包=正常教学写入经验流，删除后能力按遗忘/召回机制自然变化——绝不是答案表。
- 验收: 点按钮后，问包里教过的问候能答、问没教过的仍诚实说不知道。

## V5. 六时刻演示验收脚本

新建 `scripts/six_moments_acceptance.py`: 对临时 DB 依次自动复现六时刻，输出 markdown 报告
（每时刻: 场景/输入/实际输出/判定 PASS-FAIL）:
- M-A: 张力场景后 idle 自发说话（W1-B 逻辑）
- M-B: 任一 turn 的 tick_trace 含 write→read_draft→commit 序列 + next_unit_competition 审计
- M-C: 教学召回 + 9j 泛化 + punish 后不复读
- M-D: 未知问题诚实 + 教苹果图后"刚刚图片是啥"回指（图片资产路径抄 12c 测试）
- M-E: Y1 竖式序列（42+35=77 + 87+96 诚实）
- M-F: 你好×4 后 emotion.channel_averages.repetition_fatigue_channel>0 且 rhythm_sense>0
结果存 `docs/SixMoments_Acceptance_20260703.md`。任何 FAIL → BLOCKED 报 Fable5。
- 验收: 6/6 PASS。

## V6. 开源前检查清单（只报告不改）

写 `docs/OpenSource_Readiness_20260703.md`:
1. 红线 grep 汇总（OCR/ASR import、学生侧 LLM、关键词路由、eval 算术——各 0 命中的证据命令+输出）
2. 全量回归数字（跑一次 `python -m pytest tests/ -q`）
3. 六时刻验收结果（引 V5）
4. 已知边界诚实清单（从 ColdSave 第七节抄: 单位数/不等长段/听觉 30%/桌面 50% 等）
5. 隐私检查: data/ 下工作台 DB 是否含开发期对话（若有，建议清库重灌 starter pack——只报告，等指令）
- 验收: 文档存在且 5 节齐全。

---

执行顺序: V1 → V2 → V3 → V4 → V5 → V6。V5 任何 FAIL 全停。
完成后 Fable5 做最终对抗性验收 + 开源裁定。
