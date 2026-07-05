# Phase20.7 Stage 7 API Workbench 验收报告

日期: 2026-06-26  
范围: Phase20.7 本地 API、统一记忆 API、RuntimeTickEvent 工作台页面。

---

## 1. 本阶段目标

Stage 7 的目标是让 Phase20.7 成为可被本地页面和其它项目调用的对话底座:

1. 提供独立 `/api/phase20_7/turn`。
2. 提供统一记忆查看与删除 API。
3. 页面只读取 RuntimeTickEvent, 不在前端补编流程。
4. 页面展示聊天、tick、B/C/C*、状态池、视觉/听觉、统一记忆、未闭合项。
5. Phase20.7 工作台不复用旧 Phase20.6 工作台数据路径。

---

## 2. 已落地内容

### 2.1 后端 API

`web_chat.py` 新增:

1. `phase20_7_turn(...)`
2. `phase20_7_memory_list(...)`
3. `phase20_7_memory_delete(...)`
4. `_phase20_7_media_inputs(...)`

新增路由:

```text
POST /api/phase20_7/turn
POST /api/phase20_7/memory/list
POST /api/phase20_7/memory/delete
GET  /phase20_7
```

### 2.2 工作台页面

新增:

1. `apv3test/web/static/phase20_7_workbench.html`
2. `apv3test/web/static/phase20_7_workbench.css`
3. `apv3test/web/static/phase20_7_workbench.js`

页面能力:

1. 文本输入。
2. 图片路径/音频路径输入。
3. 教学纠正输入。
4. 闲时 tick。
5. Tick 回放。
6. 统一记忆查看与删除。
7. 未闭合项查看。

---

## 3. 当前可展示效果

访问:

```text
http://127.0.0.1:8774/phase20_7
```

可演示:

```text
用户: 你好啊
教学: 你也好
AP: 嗯,记下了。

用户: 你好啊
AP: 你也好

Tick:
observe_text -> write_cell -> write_cell -> write_cell -> commit_reply -> reply_tts_audio

统一记忆:
你好啊 -> 你也好
```

---

## 4. 本阶段能证明什么

Stage 7 可以证明:

1. Phase20.7 已可通过本地 API 调用。
2. 工作台页面只消费 API 返回的 RuntimeTickEvent。
3. 统一记忆入口可展示和删除。
4. 未闭合、视觉、音频、TTS、B/C/C* 都能在同一 trace 中展示。
5. 页面不承担认知计算。

---

## 5. 本阶段尚未证明什么

Stage 7 还不证明:

1. 发布包完整性。
2. 性能报告。
3. Playwright 端到端页面验收。
4. 完整 demo assets 与用户说明。

这些进入 Stage 8。

---

## 6. 验收命令

### 6.1 Stage 0-7 单测

```powershell
python -m pytest .\tests\test_phase20_7_stage0_runtime_boundary.py .\tests\test_phase20_7_stage1_text_closed_loop.py .\tests\test_phase20_7_stage2_experience_memory_indexes.py .\tests\test_phase20_7_stage3_structural_bccstar.py .\tests\test_phase20_7_stage4_unclosed_idle.py .\tests\test_phase20_7_stage5_visual_patch_reconstruction.py .\tests\test_phase20_7_stage6_audio_tts.py .\tests\test_phase20_7_stage7_api_workbench.py -q
```

结果: `30 passed`。

### 6.2 Stage 7 红线扫描

```powershell
python .\scripts\red_line_check_v14.py --phase 20.7-stage7
```

结果: 见最终运行记录。

---

## 7. 下一阶段入口

Stage 8 应完成发布 demo:

1. Playwright 页面验收。
2. 性能报告。
3. demo assets。
4. 用户说明。
5. 最终发布报告。

