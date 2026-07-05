# zcode 任务追加 — 绘画外显 + 记忆包 UI 接线（2026-07-04 第九批）

**Fable5 本批落地（全部实测验证，48 守护测试绿）**:

1. **第二层绘画已做成**！`画一个苹果`（教过指代+教过苹果图）→ 想象召回 → AP 在自己的画板上
   **逐轮廓投影**（project_contour×5 → observe_painting → commit_painting）→ 画作 PNG 自动
   出现在 turn 响应的 `inner_pictures` 里（`action_type=commit_painting` 的那张）。
   未教的"画一个火车"不画（教学 gate）。每步是真实 tick 行动，trace 可回放。
2. **记忆包全套路由已通**:
   - `POST /api/phase20_7/package/preview` — 筛选（keyword/since_ms/until_ms/session_id）+分页（limit/offset），返回 items[{event_id,input_text,output_text,has_visual,reward,...}] + total
   - `POST /api/phase20_7/package/export` — 按勾选的 event_ids 导出，返回完整包 JSON（前端存为文件下载）
   - `POST /api/phase20_7/package/import` — body {package: <包JSON>, session_id}，返回 imported/skipped
   - `POST /api/phase20_7/package/batches` — 已导入批次列表
   - `POST /api/phase20_7/package/uninstall` — body {import_batch_id}，卸载（记忆即刻失效）
   实测闭环: 导出→导入→冷召回→重复导入去重→卸载→遗忘。

**必读**: ColdSave 第十二节（绘画机制+记忆包红线+能动性快赢裁定）。

**红线**:
- 绘画文案: "它把想象中的画面**投影到画板上，一个轮廓一个轮廓地画**"——可以说它在画画了，
  但不许说"它会画任何东西"（教过什么才能想象什么才能画什么——这本身是卖点，写出来）。
- 不动 runtime/painting/memory_packages 的 py 逻辑。

---

## R1. 绘画演示接入（最惊艳的部分，优先）

1. AP 气泡中 `inner_pictures` 里 `action_type=commit_painting` 的图用**画框样式**区分于想象画面
   （金色边框+"它画的"角标；想象画面仍是"它想象的"）。
2. 等待期阶段提示（U1 的 progress 轮询）已自动覆盖 project_contour/observe_painting/
   commit_painting——在 stage_labels 前端映射里补三个中文名: "往画板投影轮廓/端详自己的画/落笔完成"。
3. 首页加"看它画画示例"按钮（演示按钮第 4 个）: 自动执行——发苹果图问"这是什么"→教"是苹果"→
   发"画一个苹果"（第一次不会）→教"是苹果"→再发"画一个苹果"→AP 逐轮廓画出→气泡展示画作。
   每步系统提示解说，最后一条: "它先看过苹果，才能想象苹果，才能画出苹果——和人一样。"
4. 引导卡"教它画画"更新: 三步写"教它认识一样东西 → 教它'画一个X'这个说法 → 它就会把想象
   投影到画板上画给你"。
- 验收: 演示按钮全流程跑通，画作 PNG 显示在气泡里。

## R2. 记忆包 UI 完整接线（配置页）

用上面 5 个路由做完整交互:
1. **分享 tab**: 筛选栏（关键词/时间范围/session）→ 调 preview → 表格显示（勾选框/输入文本/
   输出文本/有无视觉/时间），支持全选/反选/翻页（offset 步进）→ "导出所选"→ 调 export →
   浏览器下载 JSON 文件（文件名=包名.json）。
2. **导入 tab**: 文件选择（.json）→ 读文件 → 调 import → 显示 imported/skipped 数字。
3. **已装包 tab**: 调 batches 列表（包名/条数/时间）→ 每行"卸载"按钮 → 调 uninstall → 刷新。
4. 说明文字: "记忆包=经验片段，不是插件。导入后 AP 像自己经历过一样使用这些记忆；卸载即遗忘。
   纠错记录不会被打包（那是它自己的诚实历史）。"
- 验收: 界面走通 导出下载→导入→对话验证记忆生效→卸载→记忆失效 全链。

## R3. 主观能动性文案补充

主观能动性演示的结尾解说补一句: "它还会在闲时自己回味学过的东西、自我练习（详情页的
学习节奏卡片能看到）；探索新事物的能力等环境接入后开放。"——对应 ColdSave 十二节裁定
（回味=9f 已有/练习=9g 已有/找新鲜事=缺环境接口，列入后续项目，不假装）。
- 验收: 文案存在，无过度声称。

---

执行顺序: R1 → R2 → R3。完成后连同 U/T/S 批次一起交 Fable5 发布前终审。
