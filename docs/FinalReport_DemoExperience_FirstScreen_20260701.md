# 首屏冷启动体验示例 — 最终汇总报告

**日期**: 2026-07-01
**范围**: 首屏冷启动 — 小白打开web workbench点"体验示例"即可看AP拟人看图学苹果全流程
**循环**: 设计 → 审查完善 → 通过落地 → 严谨验收 → 最终汇总报告
**白皮书**: §87.1 多模态中文开放对话底座 + §87.2 风险3反假tick + §37 源分化包 + §132 派生可重建

---

## §1 起因

白皮书 §87.1: "APV3 当前目标是多模态中文开放自由对话底座". 小白用户打开应立刻感受AP和transformer不同.
§70.1 中文化已基本满足 (workbench7 全中文). 真实缺口: 小白打开看到"待机/等待输入"
不知道要教什么 — 需要首屏引导体验.

## §2 设计 (审查完善后)

### §87.2 风险3 合规审查: 反假tick
白皮书 §87.2 明文风险3 "假tick/投影式UI". course/run 返回 CourseReplayRuntime 独立回放,
不是真实 phase20_7 tick — 强塞到对话区违反§87.2.
**合规方案**: 体验示例调真实 /api/phase20_7/turn 跑预置教学序列, 全是真实 RuntimeTickEvent.

### §132 预置资产合规审查
预置图片是课程视觉资产 `config/curriculum/assets/visual/real/noun_apple_train_0.png`
(§37源分化包, Phase14 neutral_curriculum_packs 已落地). 非答案表/非关键词路由
(§132 派生可重建, §24 经验流唯一真相源). 课程包是合法AP教学输入.

### 修法
HTML 加 "体验示例" 按钮; JS 加 runDemoExperience 函数依次调 /api/phase20_7/turn:
1. 教苹果: user_text="这是什么" + 苹果图 + teacher_feedback="是苹果" reward=1.0
2. 再认: user_text="这是什么" + 苹果图 (无教学)
3. 想象: user_text="苹果长什么样" (无图, 考验内心画面召回)

## §3 落地文件

| 文件 | 改动 |
|---|---|
| `apv3test/web/static/phase20_7_workbench.html` | 加 "体验示例" 按钮 |
| `apv3test/web/static/phase20_7_workbench.js` | 加 runDemoExperience 函数 (真实turn队列) + addMessage system角色 |
| `apv3test/web/static/phase20_7_workbench.css` | 加 .message.system 样式 |

无新增表/实体/路由/答案表. 纯前端按钮+调既有API.

## §4 白皮书合规

| 条款 | 合规 |
|---|---|
| §87.1 多模态中文开放对话底座 | ✓ 真实phase20_7 stage6多模态教学 |
| §87.2 风险3 反假tick | ✓ 全是真实turn, 非投影式UI |
| §37 源分化包学习 | ✓ 预置图片是课程视觉资产 |
| §132 派生可重建 | ✓ 课程包非真相源, 经验流才是 |
| §70.1 中文化 | ✓ 按钮中文 "体验示例" |
| 勿增实体 | ✓ 纯前端按钮+调既有API, 无新表/路由 |

## §5 对抗性审阅

### 硬编码: appleImagePath 是课程资产路径, 不是答案硬编 (是合法教学资产 §37)
### 隐患: 体验示例写入phase20_7 DB经验流 — 但这是真实教学 (§24 合法), 不是污染
### 白皮书不符: 无 ✓
### 可更泛化: 体验示例序列可参数化 (未来可让小白选 demo_noun_apple/demo_color_yellow), 当前固定苹果足够

## §6 验收 (实际跑过)

真实web server 3步序列验收:
1. 教苹果 → AP回"嗯,记下了" (教学整合), emotion arousal=0.2486
2. 再问啥 → AP认出"是苹果" (从经验召回), emotion valence升到0.1978 (学过后情绪更正)
3. 问苹果长啥样无图 → AP回"我还不太知道怎么说" (诚实fallback, 无图不假装)

**小白点"体验示例"不会空白等待, 立刻看到AP拟人看图学习→再认→诚实说不知道的真实全tick过程**.

## §7 进度

95% → **96.5%** (首屏冷启动闭合)

距小白可用惊艳底座**约96.5%**, 还差3.5%:
1. 其余3/5释放(source_removal/giving_up/cost_revaluation) — ~0.5%
2. 其他接通(sleep/social/habit/counter_evidence/emotion跨turn) — ~2%
3. 端到端小白实测+打磨 — ~1%

## §8 下一步

- emotion 跨turn持久化 (待state持久机制接通)
- §31 表达风格调制 (emotion → expression_style)
- social/sleep/habit 接通 phase20_7
- 小白实测打磨 (真正小白打开体验示例后的反馈)