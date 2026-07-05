# 范式偏置观察报告 (Y4)

**日期**: 2026-07-03
**会话**: 20-turn混合（10寒暄教学+召回、5数学、5未知问句）

## 统计

- paradigm_action_delta出现次数: 114
- 最大delta: 0.1093 (≤0.14阈值 ✓)
- delta范围: 0.0000 ~ 0.1093
- 分布: 寒暄教学后逐步涌现（0→0.06→0.08→0.10），未教学时为0

## 判定

✅ 所有delta≤0.14 — 范式偏置在上限内，不会hijack行动竞争。
✅ 无writes_answer_directly!=False的行出现paradigm_delta。

## 样本

| 输入 | 字段 | delta |
|---|---|---|
| 你好 | paradigm_delta | 0.0000→0.0618 (教学后涌现) |
| 嗯 | paradigm_delta | 0.0000→0.0752→0.0945 |
| 你好啊 | paradigm_delta | 0.0000→0.0967 |
| 数学 | paradigm_delta | 0.0000 (数学走列召回非范式偏置) |
| 未知 | paradigm_delta | 0.0000 (无范式可匹配) |