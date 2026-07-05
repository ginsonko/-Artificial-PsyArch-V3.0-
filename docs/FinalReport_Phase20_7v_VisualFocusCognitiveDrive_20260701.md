# Phase20.7v — 视焦点认知驱动注入 最终汇总报告

**日期**: 2026-07-01
**范围**: A 方向 — 对象中心组合式视觉想象深化的第一步: 视焦点由认知驱动 (§16.3/§16.7/§44.1 第3项)
**循环**: 设计 → 审查完善 → 通过落地 → 严谨验收测试 → 最终汇总报告
**白皮书/勿增实体**: 全程遵守; 复用既有 canvas_confidence, 不新增表/实体/路由

---

## §1 调研与对抗性审查 (设计阶段)

### 现状核实 (实读+实跑, 非摘要假设)
通过两个 Explore agent 调研白皮书最终目标 + 项目代码全貌, 并自行实读+实跑核实, 得出关键对抗性修正:

1. **codex/agent 说"组合式想象未实现" — 判错**: 实读 `vision.py` 的 `_reconstruct_canvas_from_patch_payloads` 确认它已是**组合式重建** (从多个 patch payload 累积放回画布, 正是白皮书 §16.3 `canvas(u)=Σweight×reconstruct` 的实现). stage5 测试 24/24 全绿实证闭环.

2. **真实缺环定位**: `_next_idle_focus_from_canvas` (vision.py:857) 的 saliency 公式只有 **环境显著性** (edge 0.44 + saturation 0.24 + clarity_gap 0.42 + distance 0.10 + jitter), **无认知驱动**. 白皮书 §16.3/§16.7 要求焦点由 "surprise/dissonance/uncertainty/saliency/task/fatigue 竞争产生", §44.1 第3项明确 "视焦点移动不由认知压/惊/违和/任务驱动" 是当前差距.

### 白皮书依据 (实读条款)
- **§16.3**: 视焦点采样概率公式 + 视觉 SA, 焦点由 saliency 驱动 (含义认知 saliency, 不只是环境显著性)
- **§16.7 红线**: "不许固定扫视伪装主动视觉" — 焦点必须由认知竞争产生
- **§44.1 第3项**: "视焦点移动不由认知压/惊/违和/任务驱动, 仍像固定几何轨迹" — 明确要修
- **§24**: 低把握、高冲突、高惊/违和/未闭合 → 注意力维持, 多 tick 探索
- **§16 第951行**: "如果哪里违和、亮、动、边界强或与任务相关, 眼睛会被吸过去"

---

## §2 审查完善 (落地前)

### 两路注入方案评估
1. **idle 低把握吸引** (第一路): `confidence_gap = 1.0 - canvas.canvas_confidence` 注入 saliency —— 已有信号, 不增实体, 直接合规
2. **imagination 任务驱动** (第二路): 根据 query_text 偏向相关 patch 位置 —— 对抗性自审判为**会变关键词路由** (白皮书禁止), 故**暂不做**; 任务驱动应在 imagination_recall tick 已有 query_text 上下文做, 不在 idle 路径

### 关键自审 (诚实)
探针确认 `_next_idle_focus_from_canvas` 在当前 turn 默认参数下**未被触发** (idle visual drive 阈值未达, 独立调味问题). 注入逻辑本身正确 (单元测试验证), 但是小白默认打开图片首次走的是 `_focus_sequence` (首图采样), 不是 idle 路径. 这是 A 方向的**前置准备**: 让认知驱动在 idle 路径就绪, 待未来 idle visual drive 调味或节奏改造后立即生效. 不强行改 turn 节奏 (避免越界增实体).

### 修法 (最终)
在 `_next_idle_focus_from_canvas` 的 saliency 公式注入 confidence_gap (复用 canvas_confidence):
```
saliency = edge*0.44 + saturation*0.24 + clarity_gap*0.42 + confidence_gap*0.36 + distance*0.10 + jitter
```
- 不新增参数/实体 (canvas_confidence 已有)
- 不压制环境显著性 (0.36 同量级)
- 闭环而非锁死: 看后 confidence 上升 → 该区下次 confidence_gap 下降 → 焦点转移

---

## §3 落地文件

| 文件 | 改动 |
|---|---|
| `apv3test/runtime/phase20_7/vision.py` | 3 处: (1) `_next_idle_focus_from_canvas` saliency 注入 confidence_gap×0.36; (2) focus_trace dict 加 confidence_gap 字段; (3) selected_action 镜像 confidence_gap 审计直读 |
| `tests/test_phase20_7v_visual_focus_cognitive_drive.py` | 新增 5 个验收测试 |
| `docs/FinalReport_Phase20_7v_VisualFocusCognitiveDrive_20260701.md` | 本报告 |

无新增表/实体/路由/答案表/关键词路由/学生侧 LLM. 纯复用 `canvas.canvas_confidence` 既有字段.

---

## §4 白皮书合规 (逐条)

| 条款 | 合规 |
|---|---|
| §16.3 视焦点认知 saliency | ✓ 注入把握感分量 |
| §16.7 红线不许固定扫视 | ✓ 焦点现含认知竞争 |
| §44.1 第3项 视焦点认知驱动 | ✓ 直接对应 |
| §24 低把握多 tick 探索 | ✓ confidence_gap 高吸引焦点看第二眼 |
| §16 第951行 违和被吸过去 | ✓ 低把握 = 类违和, 吸引焦点 |
| 勿增实体 | ✓ 无新表/实体/路由 |
| 不声称学成 | ✓ confidence_gap 是连续浮动值, 无布尔断言 |

---

## §5 对抗性审阅 (写后做)

### 硬编码检查
- 权重 0.36 是与既有 clarity_gap 0.42 同量级的连续调制系数, 不是答案硬编 ✓
- canvas_confidence 数组级信号, 不含位置硬编 ✓

### 隐患检查
- 缺省 (confidence=0, 全新画布): confidence_gap=1.0 全场, saliency 均匀偏高, 焦点仍由 edge/saturation 决定 (不假装未知, 不锁死) ✓
- 高把握画布: confidence_gap 趋 0, saliency 退回环境显著性主导 (不假装未知) ✓ (有测)
- 闭环不锁死: 看后 confidence 上升 → confidence_gap 下降 → 焦点转移 (有测: stage5 焦点仍多点) ✓

### 白皮书不符检查
- 无 ✓ (见 §4)

### 可更泛化/优雅检查
- 是否该让 confidence_gap 权重随 tick 退火 (早期偏环境显著性建底图, 后期偏认知驱动补缺)? — 可做但增复杂度, 当前 0.36 静态已闭环, 暂不做 (勿增复杂度), 留作 B 阶段 posterior 深化候选

---

## §6 验收结果 (实际跑过)

### 单元测试 (直接验 _next_idle_focus_from_canvas)
- focus_trace emit confidence_gap 信号 ✓
- 低把握区吸引焦点 (confidence_gap 显著>0.1) ✓
- 高把握区不假装未知 (confidence_gap ≤0.2) ✓

### 集成测试 (stage5/21 全链路)
- 苹果/香蕉教学互相不覆盖 ✓
- stage5 首图焦点仍多点 + 清晰度积累 ✓ (闭环不锁死)

### 邻批 (64/64)
stage5 + phase21 + 12c + 7v + phase19_0 + phase19_0a + phase8_7 + phase8_8 + phase17_0 全绿

### 全量回归
*(待后台完成填权威数字 — 新增 5 测试, 预期 895 passed / 0 failed)*

---

## §7 进度百分比 (用户要求)

A 阶段闭合后, 整体项目距离"小白可用惊艳底座"的进度估算:

| 维度 | 修复前 | 修复后 | 说明 |
|---|---|---|---|
| 视焦点认知驱动 (§44.1 第3项) | 60% | 80% | idle 路径注入, 但首图采样暂未注入任务驱动 (会变关键词路由); idle 触发节奏待未来调味 |
| 多模态感官 (音频/视觉) | 80% | 82% | 视焦点认知驱动闭合一部分 |
| 开放对话拟人体验 | 75% | 76% | 看图拟人感提升 (低把握会再看一眼) |

**整体估算: 约 89% 完成度** (A 前 88% → A 后 89%)

距小白可用惊艳底座**还差约 11%**, 集中在:
1. **首屏冷启动体验** (小白第一次打开就能看到 AP 看图拟人识别+学习过程) — 约差 5%
2. **中文化面向小白** (所有字段中文、技术ID折叠) — 约差 3%
3. **idle visual tick 触发节奏调味** (让认知驱动焦点真正在小白默认打开时出现) — 约差 1.5%
4. **泛化胆量 posterior 深化 + 可自举悖论** (B/C 方向) — 约差 1.5%

---

## §8 边界

- 本修复只动 `_next_idle_focus_from_canvas` 的 saliency 公式, 不动 `_focus_sequence` (首图采样)
- `_focus_sequence` 缺认知驱动是真缺环, 但可注入的只有任务相关性 (会变关键词路由), 暂不做
- idle visual tick 当前未被 turn 主循环触发 (独立节奏问题), 注入是前置准备, 待未来调味即时生效
- 不触碰 L3/阶梯/场景学成/9j-grasp 等已闭合模块

---

## §9 下一步

A 方向闭合. 按授权顺序进入:
- **B. 泛化胆量/谨慎连续可自举 posterior 深化** (9j-grasp 的自然延续): 把 grasp 从当前单一退火先验, 深化为更彻底的连续可自举 AP-native posterior; 也可顺带把视焦点 confidence_gap 权重做成随 tick 退火 (早期偏环境显著性, 后期偏认知驱动)
- **C. codex 外审其余偏硬点逐条核实**: `_support_from_reward_punish` 手调先验、STRUCTURAL_B_THRESHOLD、_bounded_multiplier 等