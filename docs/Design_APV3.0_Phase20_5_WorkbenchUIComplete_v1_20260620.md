# APV3.0 Phase 20.5 Design — Workbench UI/UX Complete Redesign for Beta Release

Date: 2026-06-20
Author: Claude(架构与前端体验),银子老师(风格定调与最终签收)
Status: 设计稿(前端完整重做 + 4 大新拟人功能),为这两天内测版本做准备
Trigger:
1. Phase 20.4 已修两个紧迫问题:UI 显示原文 + 主路径统一到 /api/phase20/turn
2. 银子老师 4 大新需求未落:**AP 主动停止**、**逐 tick 多媒体回放**(画面/音频/想法云)、**记忆中文化 + 快慢记忆双轨**、**TTS / 画布 / 辅助线 等拟人扩展**
3. 银子老师明确:**内测两天后发布,前端必须美观、简洁、一眼看懂,允许用户分享教学包**
License intent: AGPL-3.0-or-later
Real name handling: 全文件 grep 真名 = 0

---

## 0. 这一份做什么(一句话)

把 Phase 20 工作台从"调试面板拼贴"升级为"**用户一眼看懂的拟人对话工作台**":左中右三栏布局 + 8 大功能面板 + 4 个新拟人能力(AP 主动停 / 逐 tick 多媒体回放 / 快慢记忆双轨 / TTS+画布+辅助线扩展),所有面板风格统一,中文化记忆,无英文裸标签,内测就绪。

---

## 1. 核心原则(不能再被打脸)

| 原则 | Why |
|---|---|
| **不再做任何"独立 UI 模块"** | 所有面板都映射到 AP 既有机制(共现/marker/SA/能量/学习包),不发明新数据 |
| **复用桌宠老前端 StrongestNurturingSystem 已有 UI 资产** | 想法云、折线图、内心画面/音频图标都已实现,直接搬 |
| **每个按钮都有 tooltip 说明何时用** | 银子老师明确"按钮看不懂,缺少注释" |
| **记忆全中文化** | 银子老师明确"只有英文谁看得懂" |
| **快慢记忆双轨展示** | 银子老师明确"AP 严格逻辑流程有两种记忆" |
| **AP 主动停=拟人范式** | 银子老师明确"教会它解决完任务自动停" |
| **逐 tick 多媒体回放** | 银子老师明确"画面/音频/想法云都要逐 tick 变" |

---

## 2. 整体布局(三栏式 + 8 面板)

```
┌──────────────────────────────────────────────────────────────────────────┐
│  Header: APV3 拟人工作台  [本地 demo · v20.5 · session_id]   [设置⚙]    │
├────────────┬──────────────────────────────────┬───────────────────────┤
│            │                                  │                       │
│  [左栏]    │           [中栏-上]              │      [右栏-上]        │
│            │      聊天会话 + 输入区          │      内心画面+音频    │
│  对话历史  │   (Panel 1: Chat & Input)        │   (Panel 4: Inner)    │
│  缩略列表  │                                  │                       │
│  [搜索]    ├──────────────────────────────────┼───────────────────────┤
│  [新建]    │                                  │                       │
│  [清]      │           [中栏-中]              │      [右栏-中]        │
│            │       逐 tick 回放控制条         │      想法云 + 标签云  │
│  Panel 0   │   (Panel 2: Tick Replay)        │   (Panel 5: ThoughtCloud)│
│            │                                  │                       │
│            ├──────────────────────────────────┼───────────────────────┤
│            │                                  │                       │
│            │           [中栏-下]              │      [右栏-下]        │
│            │   能量折线图 / 共现波峰图        │   快慢记忆双栏        │
│            │  (Panel 3: Audit Charts)        │  (Panel 6: Memory)    │
│            │                                  │                       │
├────────────┴──────────────────────────────────┴───────────────────────┤
│                       [底栏] Panel 7: 教学包生态                     │
│         [导入] [导出] [本地包列表] [搜索] [批量勾选] [卸载]          │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## 3. 8 大面板详细设计

### Panel 0: 对话历史(左栏,常驻)

```
┌─────────────────┐
│ 🔍 搜索历史会话 │
├─────────────────┤
│ ➕ 新会话        │
│ 🗑 清空当前      │
├─────────────────┤
│ 今天             │
│  • 12:34 你好…   │← 点击恢复
│  • 11:20 这是…   │
│ 昨天             │
│  • 18:55 给…     │
└─────────────────┘
```

**Why**:
- 让用户能切换 / 回顾会话,不再"每次开都一切清"
- 搜索复用 §7 记忆检索接口

### Panel 1: 聊天会话 + 输入区(中栏-上,核心)

```
┌──────────────────────────────────────────────┐
│  [聊天气泡区]                                │
│                                              │
│   你: 你好                            12:34   │
│   AP: 嗯,你好。 [▶ 播放语音]         12:34   │
│                                              │
│   你: [图片缩略图] 这是什么?         12:35   │
│   AP: 嗯,像是苹果。 [▶]              12:35   │
│        ┌─ 我看见 ─────────┐                │
│        │ • 苹果 soft 0.42 │                │
│        │ • 桌面 no_call   │                │
│        └────────────────────┘                │
│                                              │
│   [📝 已教学:"嗯,水果。"  已记]     12:36   │
│                                              │
├──────────────────────────────────────────────┤
│ ┌─────────────────────────────────────────┐ │
│ │ 输入中文…(显示原文)                    │ │
│ └─────────────────────────────────────────┘ │
│ [📷 选图] [🎤 录音] [🎨 画布]    [发送]    │
│                                              │
│ ──── 教学(可折叠)─────────────────────── │
│ 当前回答不满意?请直接告诉它"应该这么说":  │
│ ┌─────────────────────────────────────────┐ │
│ │ 应该这么说…                              │ │
│ └─────────────────────────────────────────┘ │
│ [对(+奖励)] [不对(-惩罚)] [教这么说]       │
└──────────────────────────────────────────────┘
```

**Why**:
- **聊天气泡**完全像普通 IM:图片缩略图、音频播放按钮(TTS),不再"裸 JSON"
- **气泡下挂"我看见"小卡**显示 AP 当时识别的 ObjectFile + 把握感
- **教学**作为可折叠区,不再"教学顶掉聊天"(银子老师 16:07 抱怨的根因)
- **教学完成提示**作为系统消息 inline 显示"已学习",而不是覆盖
- **3 个按钮明文中文**:对(+奖励) / 不对(-惩罚) / 教这么说,每按钮 hover 显示 tooltip:
  - 对:奖励上轮回答,以后类似情境优先这种回答
  - 不对:惩罚上轮回答,降低权重但不删
  - 教这么说:把"应该这么说"作为教师范式与上轮情境共现入记忆
- **输入区按钮 tooltip**:
  - 📷 选图:本地浏览 + 缩略图预览 + 拖拽
  - 🎤 录音:录一段音频作为教学语料
  - 🎨 画布:打开手绘画布,画的东西作为视觉输入
  - 发送:把当前输入框 + 已选媒体作为 1 个 turn 提交
  - 默认状态用 tooltip 提示"📷 选图,可上传一张图给 AP 看"

### Panel 2: 逐 tick 回放控制条(中栏-中)

```
┌─────────────────────────────────────────────┐
│  本轮 tick 回放                              │
│  Tick 1/12  上次发送=Tick1  自动停=Tick 9   │
│                                              │
│  ◀◀  ◀  ⏸  ▶  ▶▶   速度 [1x▼]            │
│                                              │
│  ──●─────────────────                       │
│   1            ↑ 6              12         │
│                                              │
│ ✓ 同步内心画面 ✓ 同步想法云 □ 同步内心音频  │
│                                              │
│ ☰ tick 详情:                                │
│  Tick 6 [提交草稿]                          │
│   - 草稿: "嗯,像是…"                         │
│   - 视焦点: (245, 168)                       │
│   - 情绪: curious                             │
│   - 共现波峰: 苹果(0.42) > 桌面(0.05)       │
└─────────────────────────────────────────────┘
```

**Why**:
- 银子老师 16:07 抱怨"tick 回放没有播放按钮可以选择查看第几个 tick"
- **可拖拽进度条 + 播放/暂停/前进/后退** = 标准媒体控制
- **同步**复选框让画面/音频/想法云三个右栏面板**跟随**当前 tick
- "上次发送" + "自动停" 标记直观显示 AP 主动停的时刻(§5)
- 每 tick 详情显示草稿 + 视焦点 + 情绪 + 该 tick 共现波峰

### Panel 3: 能量折线图 / 共现波峰图(中栏-下,音频)

**复用桌宠老前端 [StrongestNurturingSystem/app.js:7428 已实现的折线图组件]**

```
┌──────────────────────────────────────────────┐
│  能量动力学 12 tick                          │
│  [R 真实能量] [A 注意] [P 认知压] [F 疲劳]   │
│       1.0 ──────────────                     │
│           │R▁▂▃▅▇█▇▅▃▂▁                     │
│       0.5 │A   ▂▃▅▇▆▄                       │
│       0.0 └──────────────                     │
│         1     6      12                       │
└──────────────────────────────────────────────┘
┌──────────────────────────────────────────────┐
│  共现波峰图 top-12                            │
│  苹果 ████████████ 0.85                       │
│  橙子 ████████ 0.51                            │
│  桌面 ██ 0.12                                  │
└──────────────────────────────────────────────┘
```

**Why**:
- 桌宠老前端**已有折线图实现**(看到 app.js:11088 渲染 mind cloud)— 直接搬,不重写
- 能量折线图反映 v14 4 能量字段在本轮的演化 = 拟人 AP 内部活力可视
- 共现波峰图 = §6.2 召回的可视化,用户能看"AP 心里联想到哪些词"

### Panel 4: 内心画面 + 内心音频(右栏-上)

```
┌──────────────────────────────────────────────┐
│  内心画面 ⚙(显示选项)                       │
│  ┌──────────────────────┐                    │
│  │                      │                    │
│  │  [64×64 sketch 画]   │  ← R_sketch        │
│  │                      │                    │
│  │   👁 视焦点 ●        │                    │
│  └──────────────────────┘                    │
│  Source: PERCEIVED_SENSORY_SKETCH            │
│  ⊕ 叠加 □REMEMBERED □INFERRED                │
│                                              │
│  本 tick #6                                   │
├──────────────────────────────────────────────┤
│  内心音频                                    │
│  ♪ ▶ ━━━━●━━━━━ 0:00 / 0:04                  │
│  [合成自 narrative chain]                    │
└──────────────────────────────────────────────┘
```

**Why**:
- v1c §4 SensoryCanvas + R_sketch / R_proto 已数学化(但实施层只接通了 V0/V7,V10-12 是 Phase 21 v1b 修)
- **视焦点 ● 叠在 sketch 上**,用户能直观看 AP "看哪里"
- 内心音频 ▶ 播放 narrative chain 合成的 1 秒 WAV(Phase 19.1 设计稿有)
- ⊕ 叠加 REMEMBERED/INFERRED — 让用户看到 AP **认知三层**(看见/想起/推测)
- **Tick 同步**:进度条改变时,这张图也跟着变(承接 v1c §4 多 tick 累积)

### Panel 5: 想法云 + 标签云(右栏-中)

```
┌──────────────────────────────────────────────┐
│  当前想法云                                  │
│                                              │
│        苹果                                  │
│       ●●●●●                                 │
│                  桌面                        │
│       橙子        ●                          │
│       ●●                                     │
│                                              │
│   关键标签: #fruit #red #round              │
└──────────────────────────────────────────────┘
```

**Why**:
- 老前端 app.js:11088 `renderMindCloud(frame.cloudItems)` **已实现** — 直接复用
- 想法云大小 = sparse_pairwise 共现强度
- 标签云 = Phase 19.7 channel ablation 给的 diagnostic top-3

### Panel 6: 快慢记忆双栏(右栏-下,关键)

银子老师明文:"记忆分为状态池快照的快记忆和注意焦点记忆的慢记忆,这两者在 AP 中不一样"。

```
┌──────────────────────────────────────────────┐
│  [快记忆] - 状态池快照(每 tick)             │
│  ── 当前 tick #6 ──                          │
│  • 苹果 SA  能量 0.85                        │
│  • 看图  SA  能量 0.42                        │
│  • 这是  SA  能量 0.18                        │
│  ▼ 展开全部(top-12)                          │
├──────────────────────────────────────────────┤
│  [慢记忆] - 注意焦点凝固                     │
│  ── 最近 6 个 ──                              │
│  • 看到苹果(图片+音频)                       │
│    📷 [记忆画面缩略图]  ♪ [▶]                │
│  • 教学"嗯,苹果"                              │
│  • 用户问"这是什么"                           │
│  ▼ 展开全部                                   │
└──────────────────────────────────────────────┘
```

**Why**:
- **快记忆 = 状态池每 tick 快照**:当前 tick 的 top-12 SA + 能量
- **慢记忆 = 注意焦点凝固的 SA**:多 tick 累积 attention_energy 高的 SA
- 每条慢记忆若含图像数据 → 展示 **R_proto 合成的"记忆画面"**(64×64 缩略图)
- 每条慢记忆若含音频数据 → 展示 **R_aud_proto 合成的"记忆音频"**(▶ 播放按钮)
- 内容中文化 — 不显示 `style_paradigm::xxx` 而显示"嗯,苹果。(教师范式)"
- Tick 回放同步,看到 AP 每 tick 想到什么 + 长期记得什么

### Panel 7: 教学包生态(底栏)

```
┌──────────────────────────────────────────────────────────────────┐
│  教学包                                                          │
│                                                                  │
│  [导入...] [导出当前选择...] [本地包]                            │
│                                                                  │
│  搜索:[ 关键词____ ] 时间:[全部▼] 技能:[全部▼]                  │
│                                                                  │
│  📦 fruit_basics_v1.zpkg  [author: yz]  CC-BY-4.0   2026-06-20   │
│    └ 共 48 条共现边 | 已导入(去重 12) | 包内浏览  [卸载]        │
│  📦 greeting_xiaomo_v3.zpkg  [author: yz]  AGPL    2026-06-19   │
│    └ 共 92 条                                       [卸载]        │
│                                                                  │
│  ⊕ 导出当前选择                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ ☐ 全选  ☐ 反选  ☐ 默认隐私(不带原图/不带原文)        │   │
│  │ 选中: 14/48                                              │   │
│  │ [● 共现边 #ce_a3f9] 苹果 ↔ 看图   support 0.85          │   │
│  │ [○ 共现边 #ce_8c2e] 桌面 ↔ 看图   support 0.12          │   │
│  │ ...                                                      │   │
│  │ [取消] [打包导出]                                        │   │
│  └──────────────────────────────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────┘
```

**Why**:
- 完全实现银子老师 §7 共现记忆包生态(Phase 20.3 设计)
- 选择/搜索/批量勾选/反选/卸载全部明文按钮 + tooltip
- 默认隐私选项打开 — 用户**主动**才能带原图/原文

---

## 4. 4 大新拟人能力的实现要点

### 4.1 AP 主动停(银子老师第 1 点)

**当前**:Phase 20 turn loop 固定 N tick 停。
**新**:AP 提交草稿后,若仍有"未闭合感 / 未完成任务",可继续写下一草稿,**一次输入产生多个回复**。

数学定义(完全 AP-native,复用既有机制):

```
unresolved_pressure(t) = mean(cognitive_pressure of state_pool items where role=="pending_speech")
                       + mean(MISMATCH marker intensity, last 3 tick)
                       + (1.0 - last_draft_commit_readiness)

每 tick:
  if just_committed(t):                            # 刚提交了草稿
    if unresolved_pressure(t) < release_threshold: # 完成感强
      → AP 主动停,本 turn 结束
    elif unresolved_pressure(t) >= max_threshold:  # 还想说
      → 进入"接着写"模式,继续下一草稿
    
  if (t - last_commit_tick) > max_silent_window:   # 长时间未提交也未停
    → 强行停(避免死锁)
```

新常量:

```yaml
phase20_5:
  unresolved_pressure_release_threshold: 0.25  # @experimental - 低于此值AP 主动停
  unresolved_pressure_max_threshold: 0.65       # @experimental - 高于此值继续写
  max_silent_window_ticks: 8                     # @structural - 距上次提交超过8 tick 强行停
```

**作为拟人范式教学**(银子老师明文):
- 用户可在 Panel 1 教学输入"完了" / "就这样" → 共现入 `unresolved_pressure < threshold` 这个内部状态对应的"停 token"
- 多次教学后,AP 自然学到"完成感 → 说'完了' → 停"的拟人范式

### 4.2 逐 tick 多媒体回放(银子老师第 2 点)

- Panel 2 进度条改变时,emit `current_tick` event
- Panel 4 内心画面订阅 event,从 `phase20.workbench_tick_trace[tick].inner_picture` 取 sketch + focus_xy 渲染
- Panel 4 内心音频订阅 event,从 `phase20.workbench_tick_trace[tick].inner_voice_wav_url` 取 audio
- Panel 5 想法云订阅 event,从 `phase20.workbench_tick_trace[tick].thought_cloud` 取 token + weight
- 同步开关默认全开(银子老师明文"勾选开关后,也播放对应 tick 的内心音频")

后端补充:

```python
def _phase20_workbench_tick_trace_v2(turn, payload):
    """返回 per-tick:
    {
      "tick": int,
      "draft_text": str | None,
      "committed": bool,
      "focus_xy": (int, int) | None,
      "inner_picture": {
        "sketch_url": str,        # /api/inner_picture/<tick>.png
        "source": str,             # PERCEIVED/IMAGINED/...
        "focus_xy": (int, int),
      } | None,
      "inner_voice": {
        "wav_url": str,            # /api/inner_voice/<tick>.wav
      } | None,
      "thought_cloud": [
        {"token": str, "weight": float, "source_sa_id": str}, ...
      ],
      "fast_memory_top12": [...],
      "slow_memory_top6": [...],
      "energy_RAPF": (float, float, float, float),
      "unresolved_pressure": float,
    }
    """
```

### 4.3 快慢记忆双轨(银子老师第 3 点)

完全按 §3 Panel 6 实现。后端:

```python
def fast_memory_snapshot(state_pool, tick) -> list[FastMemoryItem]:
    """返回当前 tick 的状态池 top-12 SA + 能量"""

def slow_memory_top(state_pool, n=6) -> list[SlowMemoryItem]:
    """返回 attention_energy 累积高的 SA top-N,可能跨多 tick"""

@dataclass
class SlowMemoryItem:
    sa_id_opaque: str
    label_human_readable: str       # 中文化:从 sparse_pairwise top 共现词翻译
    accumulated_attention: float
    inner_picture_url: str | None   # 若该 SA 含视觉证据,R_proto 合成
    inner_voice_url: str | None      # 若该 SA 含音频证据,R_aud_proto 合成
    source_tick_range: (int, int)
```

中文化策略:
- SA id 不显示
- label 走 sparse_pairwise.top_partners 取共现最强的 text_token 作显示名
- 如果没有共现 text_token → 显示"未命名(视觉:苹果状物)" 或 类似

### 4.4 拟人扩展:TTS / 画布 / 辅助线 / 录音(银子老师第 4 点)

#### TTS(默认接桌宠的小默声线)

```python
# 配置
tts:
  enabled: false                       # 用户主动启用
  voice_profile: "xiaomo_default"      # 用桌宠定义的默认声线
  backend: "local_pyttsx3_offline"     # 完全离线,不调外部 API
```

**红线**:
- 仅在用户**勾选启用**后生效
- 不调外部 API(Edge TTS / Google TTS 等)
- 用 pyttsx3 / espeak-ng 本地引擎(若无 → 优雅降级)
- Reply 文本走 TTS → audio bytes → 内联 audio 元素

#### 画布(用户手绘 → 视觉输入)

- HTML5 canvas,用户画完点"完成"
- 输出 PNG bytes → 走 Phase 21 enumerate_objects_in_image
- 银子老师明文桌宠"画布和绘画/画字"能力 — 复用其代码 (StrongestNurturingSystem/app.js 已有 canvas 绘制实现)

#### 辅助线(在原图上画框/箭头)

- 用户上传图后,可在缩略图上拖框 → 框选区域作为 candidate_bbox 强制提示
- 不替代 Phase 21 自动检测,而是"教师告诉 AP 看这里"
- 用作 v1e §10 temporal_event_bind 的视觉证据强化

#### 录音

- HTML5 MediaRecorder 录用户声音 → WAV
- 走 Phase 19.1 听觉感受器(若已实施)→ 否则只保留为审计音频
- Phase 20.5 仅做"接进来"+ 缩略波形显示,不要求真实听觉识别

---

## 5. UI 风格设计

### 5.1 视觉风格

| 元素 | 设计 |
|---|---|
| 字体 | 系统默认中文(PingFang SC / Microsoft YaHei),英文 Inter / SF Pro |
| 主色 | 米白底 #FAFAF7 + 深蓝点缀 #2E4960 + 暖黄强调 #E8C547(小默风格)|
| 圆角 | 8px(气泡)/ 4px(按钮)/ 12px(面板)|
| 阴影 | 极轻 box-shadow: 0 1px 3px rgba(0,0,0,0.06)|
| 间距 | 8px / 12px / 16px / 24px 网格 |
| 动效 | 仅"AP 在思考时" sketch 区轻微脉动,其余无动画 |

### 5.2 信息层级

```
H1 = 面板标题(16px 中等粗)
H2 = 小节(13px 灰)
Body = 12-13px 黑灰
Caption = 11px 浅灰(meta 信息如 tick / 时间)
```

### 5.3 状态色

| 状态 | 色 |
|---|---|
| firm | 蓝 #2E4960 |
| soft | 灰蓝 #6989A8 |
| ambig | 浅橙 #D9A45B |
| no_call | 灰 #8B8B8B |
| 教学已记 | 绿 #5B9F6B |
| 错误 / 惩罚 | 暗红 #B05050 |

### 5.4 emoji 用量

银子老师之前指示**默认不用 emoji**,但工作台按钮 emoji 作为图标可接受(不进入 AP 输出文本)。所有 AP 输出文本仍按 Phase 16 styled 不含 emoji 风格。

---

## 6. 实施分解(6 天)

| 天 | 工作 |
|---|---|
| **Day 1** | UI 骨架 HTML/CSS 三栏 + 8 面板空盒子,响应式;Panel 1 聊天气泡含图缩略 + TTS 按钮 |
| **Day 2** | Panel 2 tick 回放控制 + 进度条 + 同步开关;后端 _phase20_workbench_tick_trace_v2 |
| **Day 3** | Panel 4 内心画面 + 内心音频(对接现有 R_sketch);Panel 5 想法云(搬桌宠老前端 renderMindCloud)|
| **Day 4** | Panel 6 快慢记忆双轨(中文化 + R_proto/R_aud_proto 缩略图);Panel 3 能量折线图(搬桌宠老前端)|
| **Day 5** | AP 主动停(§4.1)+ Panel 7 教学包生态完善 + 画布 / 辅助线 / 录音输入 |
| **Day 6** | TTS 离线引擎接入 + 端到端 5 turn 跑通 + 内测发布版 |

---

## 7. 21 deliverable Gates

### 7.1 UI 体验(8)

| Gate |
|---|
| G-20.5-UI-01 三栏 + 8 面板布局响应式,1280×800 起 |
| G-20.5-UI-02 所有按钮 hover 有中文 tooltip |
| G-20.5-UI-03 聊天气泡支持图缩略 + 内联音频播放 |
| G-20.5-UI-04 教学完成显示"已学习"系统消息,不覆盖原回答 |
| G-20.5-UI-05 当前 session 显示用户原文,SQLite 仍只 hash |
| G-20.5-UI-06 每按钮 tooltip 说明"何时用"(银子老师"按钮看不懂"明确修)|
| G-20.5-UI-07 记忆面板完全中文化(grep test:UI 文本不含 `style_paradigm::` 等裸 id)|
| G-20.5-UI-08 默认 emoji 仅图标用,AP 输出文本不含 emoji |

### 7.2 拟人功能(8)

| Gate |
|---|
| G-20.5-Anth-01 AP 主动停:用户输入"完了"教学 3 次后,unresolved_pressure 公式触发主动停(单测)|
| G-20.5-Anth-02 多 tick 回放进度条改变 → 内心画面 / 想法云 / 内心音频(若开)同步切换 tick |
| G-20.5-Anth-03 视焦点 ● 叠在 sketch 上,tick 切换时位置改变 |
| G-20.5-Anth-04 快记忆 = 状态池 top-12 SA + 能量,每 tick 不同 |
| G-20.5-Anth-05 慢记忆 = attention_energy 累积 top-6,跨 tick 累积 |
| G-20.5-Anth-06 慢记忆含视觉证据 → R_proto 缩略图;含音频 → R_aud_proto ▶ 播放 |
| G-20.5-Anth-07 TTS 开关启用后,AP reply 自动合成本地 WAV inline 播放 |
| G-20.5-Anth-08 画布 / 录音 / 辅助线 三种新输入都能走 Phase 21 / Phase 19.1 |

### 7.3 红线(5)

| Gate |
|---|
| G-20.5-RL-01 SQLite 持久化普通 user_text 仍只 hash(单测)|
| G-20.5-RL-02 教学文本作为教师证据可入记忆(银子老师明确要)|
| G-20.5-RL-03 TTS / 录音 / 画布 不调外部 API(grep test)|
| G-20.5-RL-04 真名 0 命中(全 Phase 20.5 文件)|
| G-20.5-RL-05 默认导出包不含原图 / 原文(继承 Phase 20.3)|

---

## 8. 防 Codex 误会的明确措施

| 防误会 | 做法 |
|---|---|
| 不再做"独立 UI 模块" | §3 每面板都映射到 AP 既有数据源(state_pool / sparse_pairwise / canvas / marker)|
| 不再用裸 sa_id 显示 | G-20.5-UI-07 grep test |
| 不再用纯英文 | G-20.5-UI-07 |
| 复用桌宠老前端 UI | §3 显式标出"搬 StrongestNurturingSystem/app.js:7428 / 11088" |
| AP 主动停=拟人范式不是开关 | §4.1 用 unresolved_pressure 公式 + 教学共现 |
| 快慢记忆双轨不是新数据 | §4.3 全用现有 state_pool + attention_energy 累积 |

---

## 9. 银子老师拍板项

1. **三栏 + 8 面板 + 4 大新功能**:同意吗?
2. **§5 视觉风格(米白 + 深蓝 + 暖黄)**:同意吗?可改色
3. **演示用 5 turn 脚本**(银子老师拍 5 turn 用户对话 + 图片 + 教学 + TTS 试听)给 Codex 作 demo 验收用 — 您来给还是我设计?
4. **TTS 引擎选择**:`pyttsx3` (跨平台) vs `espeak-ng` vs `edge-tts(本地缓存)` — 您倾向?(我建议 pyttsx3 + 完全离线)

---

## 10. 与最终目标的对应

| 目标 | Phase 20.5 怎么交付 |
|---|---|
| **G1 自由开放对话** | Panel 1 聊天 + 教学 + TTS 让用户**一眼就会用** |
| **G2 网页 demo 应用场景** | **本设计就是 G2 网页 demo 的最终形态**,可直接发布内测 |
| **G2 agent 工具** | 已在 Phase 20.0 落地,本设计不破 |
| **G2 桌宠** | 本设计**搬桌宠老前端 UI 资产**,桌宠未来直接复用 |
| **G3 图片认知** | Panel 1 气泡里展示 ObjectFile + 把握感 + Panel 4 内心画面同步 |
| **G4 教学生态** | Panel 7 完整实现共现包导入/导出/卸载/搜索 |

---

## 11. 署名

- 原架构设计:银子老师(笔名)
- Phase 20.5 前端体验:Claude (Anthropic) 在银子老师 4 大新需求 + 演示截图 + 抱怨清单基础上,**直接读桌宠老前端 [StrongestNurturingSystem/app.js](StrongestNurturingSystem/app.js)** 后产出
- 落地:Codex 在审查通过后 6 天落地

End of Phase 20.5 Design.
