# 开源前检查清单 (V6)

**日期**: 2026-07-03

## 1. 红线 grep 汇总

以下命令在仓库根 `APV3.0test` 执行，各应 0 命中：

```bash
# OCR/ASR import
grep -rn "import.*ocr\|import.*asr\|pytesseract\|speech_recognition" apv3test/ | grep -v test
# 学生侧 LLM
grep -rn "openai\|anthropic\|student_side_llm\|llm.*student" apv3test/ | grep -v test | grep -v "# "
# 关键词路由
grep -rn 'if ".*" in text.*:.*reply\|if.*==.*answer' apv3test/ | grep -v test
# eval 算术
grep -rn "eval(" apv3test/runtime/phase20_7/ | grep -v "test\|self_eval\|reeval"
```

**状态**: 需运行一次确认 0 命中（由 V6 执行人跑）。

## 2. 全量回归

`python -m pytest tests/ -q` — 需运行一次记录 passed/failed 数字。
（V3/W3 裁剪回归已多次绿，全量需实际跑一次确认。）

## 3. 六时刻验收

见 `docs/SixMoments_Acceptance_20260703.md`（V5 生成）。
M-A~M-F 六时刻逐一复现，目标 6/6 PASS。

## 4. 已知边界诚实清单

| 边界 | 说明 |
|---|---|
| 数学竖式 | 仅两位数无进位+有进位；单位数/不等长段不支持（§65后续批次） |
| 听觉 | 感受器采证+TTS在；周期分辨率/内心音频重建未实现(~30%) |
| 桌面控制 | DraftGrid二维+画板闭环在；move/click/key行动器/risk门控未实现(~50%) |
| 视觉 | 内心画面重建+教学共现在；V10-V12局部通道精细化未实现 |
| 情绪表达 | 慢量跨turn+drive微调制在；情绪→词汇/句式/语气变化未实现 |
| 范式自发 | 种子+共现涌现+偏置注入在；完全无教师自发归纳未实现 |
| 状态池跨turn | 快照恢复式连续（非live pool常驻）；常驻进程形态留给桌宠壳 |
| 社交/睡眠/习惯 | 模块存在但未接通phase20_7（需pool持久前置） |

## 5. 隐私检查

工作台 DB `data/phase20_7_workbench.sqlite` 可能含开发期对话。
**建议**: 开源前清库重灌 starter pack（`scripts/build_starter_pack.py`）。
`scripts/cold_retest_harness.py` 可验证清库后召回能力。

## 6. 开源口径建议

主打"文本+视觉双模态拟人对话底座"；听觉标注"预览"；桌面控制标注"路线图"。
不声称"学会/收敛/完成/智能涌现"；用"记住了/会用范式组合了/还在学"。