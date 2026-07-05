# Phase20.7 Stage 8 Release Demo 最终验收报告

日期: 2026-06-26  
范围: 完整发布 demo 包、自动验收、性能报告、红线报告、用户说明。

---

## 1. 本阶段目标

Stage 8 的目标是把 Stage 0-7 的 AP-native 底座能力整理成可发布、可运行、可审计的本地 demo:

1. 可运行本地工作台。
2. 隔离测试数据库。
3. 演示素材。
4. 自动化验收脚本。
5. 红线扫描报告。
6. 性能报告。
7. Final Report。
8. 一页用户说明。
9. 发布 zip 包。

---

## 2. 已落地交付物

### 2.1 自动发布 demo 脚本

```text
scripts/run_phase20_7_release_demo.py
```

功能:

1. 生成演示素材。
2. 创建隔离 demo SQLite。
3. 跑文本学习、结构类比、未闭合、视觉 patch、音频 audit、xiaoyi TTS 流程。
4. 输出 manifest。
5. 输出性能报告。
6. 输出 HTML 展示页。
7. 打包 zip。

### 2.2 自动验收脚本

```text
scripts/verify_phase20_7_release_demo.py
```

验证:

1. 文本教学召回成立。
2. structural B/C/C* 演示成立。
3. 未闭合重复维护成立。
4. 教学后未闭合解决成立。
5. 视觉 patch tick 数量足够。
6. TTS voice preference 为 xiaoyi。
7. 性能阈值满足。
8. zip 包包含必要文件。

### 2.3 用户说明

```text
docs/UserGuide_Phase20_7_ReleaseDemo_20260626.md
```

说明该 demo 是“会学的小孩级 AP 底座”, 不是全知 LLM。

### 2.4 发布输出

脚本生成:

```text
reports/Phase20_7_release_demo_manifest_20260626.json
reports/Phase20_7_performance_report_20260626.json
reports/APV3_Phase20_7_ReleaseDemo_20260626.html
reports/APV3_Phase20_7_ReleaseDemo_Package_20260626.zip
reports/Phase20_7_redline_report_20260626.txt
```

---

## 3. 全阶段能力汇总

### Stage 0

独立 Phase20.7 runtime 边界和红线。

### Stage 1

StatePool + SSP + 最小 EventLog + exact B0 + DraftGrid 文本闭环。

### Stage 2

可重建 exact B0 索引、统一记忆视图、tombstone 删除、记忆包 provenance。

### Stage 3

结构 B/C/C* 与 C* 虚能量回灌。

### Stage 4

未闭合感、重复未知降噪、idle_think、教师反馈解决 U。

### Stage 5

视觉 patch payload、焦点采样、clarity map、内心画面重建。

### Stage 6

audio audit sensor、xiaoyi 本地 TTS actuator intent。

### Stage 7

Phase20.7 API 与 RuntimeTickEvent 工作台。

### Stage 8

完整发布 demo 包、性能验收、红线验收、用户说明与最终报告。

---

## 4. 当前可以证明什么

Phase20.7 当前可以证明:

1. 文本教学能进入统一经验流。
2. 学过的同结构内容能被 exact B0 召回。
3. 近似结构能触发 structural B/C/C*。
4. 不同输入不会被上一条教学全局污染。
5. DraftGrid 是逐 tick 写入, 不是前端假回放。
6. 未知内容会形成未闭合感。
7. 闲时 tick 会把注意拉回未闭合项。
8. 视觉输入走 patch payload 与 SensoryCanvas 重建。
9. 音频输入只做 audit。
10. 回复朗读是本地 xiaoyi TTS actuator intent。
11. 工作台只显示 RuntimeTickEvent。

---

## 5. 当前边界

Phase20.7 当前还不证明:

1. 成人级无限知识闲聊。
2. 真实水果视觉识别已经完全泛化。
3. 长程因果解释和反例松动已经完整数学闭合。
4. 麦克风实时识别、画板工具行动和桌宠接入已完成。

这些是 Phase20.8+ 的继续方向。

---

## 6. 验收命令

### 6.1 生成发布 demo

```powershell
python .\scripts\run_phase20_7_release_demo.py
```

### 6.2 验证发布 demo

```powershell
python .\scripts\verify_phase20_7_release_demo.py
```

### 6.3 Stage 0-8 新测试

```powershell
python -m pytest .\tests\test_phase20_7_stage0_runtime_boundary.py .\tests\test_phase20_7_stage1_text_closed_loop.py .\tests\test_phase20_7_stage2_experience_memory_indexes.py .\tests\test_phase20_7_stage3_structural_bccstar.py .\tests\test_phase20_7_stage4_unclosed_idle.py .\tests\test_phase20_7_stage5_visual_patch_reconstruction.py .\tests\test_phase20_7_stage6_audio_tts.py .\tests\test_phase20_7_stage7_api_workbench.py .\tests\test_phase20_7_stage8_release_demo.py -q
```

### 6.4 红线扫描

```powershell
python .\scripts\red_line_check_v14.py --phase 20.7-stage8
```

---

## 7. 结论

Phase20.7 已形成可运行、可验收、可发布的 AP-native 中文开放对话底座 demo。

它不是全知 LLM, 而是“会学的小孩级 AP”底座: 能学、能记、能低把握、能未闭合、能闲时回想、能逐 tick 通过 DraftGrid 输出, 并且视觉/听觉/TTS 都回到同一条 RuntimeTickEvent 审计链。

