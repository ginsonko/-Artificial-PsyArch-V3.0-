# APV3 Phase 20.6 历史回放 / 记忆包 / 画布教学补强报告

日期: 2026-06-21

## 结论

本轮补强完成了 Phase 20.6 工作台的三个关键缺口:

1. 历史会话 / 跨 turn tick 回放
   - 新增 `/api/phase20/history/list` 与 `/api/phase20/history/replay`。
   - 回放只读取 `phase20_turn_trace.runtime_tick_events`，不重新运行 AP，不写入状态。
   - 如果旧 turn 没有 RuntimeTickEvent，返回显式 warning，不补编假 tick。

2. 记忆包产品化
   - 本地记忆支持类型筛选: 表达短句 / 共现边 / 范式共现。
   - UI 支持全选当前、反选当前、清空勾选、排除勾选导出、包内预览。
   - 导入继续自动去重，卸载只删除该 batch 新增的 memory，不删除 dedup 共享 memory。

3. 画布 / 图片教学泛化验收
   - 画布输入仍作为视觉感受器输入，不做 OCR，不做图片标签表。
   - 图片教学通过视觉 SA 与教师短句共现完成。
   - 新增粗视觉特征 SA: `visual_feature::area/*`、`visual_feature::saliency/*`、`visual_feature::aspect/*`、`visual_feature::focus_grid/*`、`visual_scene::object_count/*`。
   - 这些 SA 不读文件名、不读路径语义、不输出 label，只为相似视觉状态提供 AP-native 共现召回桥。

## AP-native 边界

本轮没有引入独立图片标注模块、回答表、整图识别回复路线、OCR、云 TTS 或隐藏 LLM。

历史回放是 view 层:

- 数据来源: 已保存 RuntimeTickEvent。
- 禁止行为: 重跑 turn、预生成回复切片、把流程名伪装成 tick。
- 当前进程中的用户原文只存 WebChatApp 侧车缓存，供工作台显示。
- SQLite trace 仍只保存 hash 和长度，不保存用户原文或图片路径。

视觉教学是共现学习:

- 视觉候选 SA + 粗视觉特征 SA + 教师短句 SA 在同一 AP 记忆图中形成共现。
- 下次相似输入通过 `CooccurrenceAssociationStore` 与 `ExpressionPhraseMemory` 召回教师短句。
- 回复仍由 Phase20.6 runtime 每 tick 经 RecallCandidate、ActionCompetition、DraftGrid 写入和提交。

## 修改文件

- `apv3test/web_chat.py`
  - 新增历史列表 / 回放 API。
  - 新增进程内 live history，用于当前服务会话显示原文和媒体预览。
  - 历史回放转换为 workbench tick trace 时保留 `replay_source=stored_runtime_tick_events`。

- `apv3test/runtime/phase20_open_dialogue.py`
  - 撤回持久化 trace 中的用户原文和图片路径。
  - 增加视觉候选 bbox / area 序列化。
  - 增加 AP-native 粗视觉特征 SA，支持相似图片的早期共现泛化。

- `apv3test/runtime/phase20_memory_packages.py`
  - `list_memory_view` 增加 `kinds` 类型过滤。

- `apv3test/web/static/phase20_6_workbench.html`
  - 增加历史 turn 列表。
  - 增加记忆类型筛选、批量选择、排除导出、包内预览控件。

- `apv3test/web/static/phase20_6_workbench.js`
  - 接通历史 list/replay。
  - 接通记忆包筛选、预览、批量选择和排除导出。
  - 历史回放只替换当前 tick replay，不追加聊天 turn，不触发 runtime。

- `apv3test/web/static/phase20_6_workbench.css`
  - 补历史列表和记忆包控件样式。

- `tests/test_phase20_6_history_package_canvas.py`
  - 新增历史只读回放、记忆包产品化、画布图片共现召回测试。

- `tests/test_phase20_6_true_runtime_workbench_page.py`
  - 增加历史 / 记忆包产品化静态验收。

- `scripts/red_line_check_v14.py`
  - 增加新交付物和禁用捷径扫描。

## 验收结果

命令:

```powershell
python -m pytest tests/test_phase20_open_dialogue_foundation.py tests/test_phase20_1_teaching_paradigm.py tests/test_phase20_2_3_cooccurrence_memory.py tests/test_phase20_4_workbench_repair.py tests/test_phase20_5a_runtime_workbench.py tests/test_phase20_6_stage0_runtime_boundary.py tests/test_phase20_6_true_runtime_workbench_page.py tests/test_phase20_6_history_package_canvas.py -q
```

结果:

```text
50 passed in 92.94s
```

命令:

```powershell
python -m pytest tests/test_phase21_object_centric_looking.py tests/test_phase19_9_zvec_recall_index.py -q
```

结果:

```text
15 passed in 62.45s
```

命令:

```powershell
python scripts/red_line_check_v14.py --phase 20.6-stage0
```

结果:

```text
OK: Phase 20.6-stage0 deliverables present
OK: All red line checks pass on runtime/cognitive
```

命令:

```powershell
node --check apv3test/web/static/phase20_6_workbench.js
```

结果: PASS。

命令:

```powershell
python -m py_compile apv3test/web_chat.py apv3test/runtime/phase20_open_dialogue.py apv3test/runtime/phase20_memory_packages.py
```

结果: PASS。

## 浏览器 / API 冒烟

启动:

```powershell
python -m apv3test.web_chat --host 127.0.0.1 --port 8788 --state-db data\phase20_6_history_package_canvas_smoke.sqlite
```

页面:

```text
http://127.0.0.1:8788/phase20_6_workbench.html
```

验证:

- 页面标题为 `APV3 Phase20.6 真实运行工作台`。
- 页面包含历史 turn、用户输入、本地记忆 / 记忆包区域。
- API 冒烟确认 turn 产生非投影 RuntimeTickEvent。
- history replay 返回 `stored_runtime_tick_events` 且 `mutated_state=false`。
- memory list 返回 `apv3_phase20_3_memory_view/v1`。

说明: 本次浏览器自动输入被当前 browser-use 环境的虚拟剪贴板限制拦截，因此最终用页面加载 + 同端口 API 冒烟补充验证。后端和静态页面测试已覆盖 UI 依赖的接口和 DOM 控件。

## 仍不能宣称

本轮证明的是:

- Phase20.6 工作台可以跨 turn 读取真实 RuntimeTickEvent 回放。
- 记忆包可以围绕 AP-native 共现记忆进行筛选、导出、导入、预览和精确卸载。
- 画布 / 图片教学可以通过视觉 SA 与教师短句共现，在相似视觉状态下由 runtime 召回并写入 DraftGrid。

本轮仍不能宣称:

- 完整真实世界视觉识别已经成熟。
- 任意图片标注泛化已可靠。
- 听觉识别已经接通。
- 开放对话底座已完全达到最终形态。

下一步最稳的是继续做端到端前端体验验收和更强的视觉教学课程: 使用多张相似但不同路径/不同轻微形变图片，逐步验证视觉特征 SA 的泛化边界，并把失败样例纳入共现/纠错/再注视流程。
