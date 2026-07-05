# APV3.0 Phase 20.5 v1a Errata — AP Philosophy Hardening Before Workbench UI Implementation

Date: 2026-06-20
Author: Claude(架构),银子老师(风格定调与最终签收)
Status: 设计稿微修订(叠加在 Phase 20.5 v1 之上 — 两份合读)
Source: 吸收 Codex Phase 20.5 v1 对抗审阅全部 9 项 + 我自查 3 项隐患
License intent: AGPL-3.0-or-later
Real name handling: 全文件 grep 真名 = 0

---

## 0. 这一份做什么(一句话)

把 Phase 20.5 v1 设计稿的 12 处会让"前端体验倒逼后端伪装"的接口缝隙钉死 — 拆 `stop_generating` 独立 action / runtime loop 真升级 / TTS ≠ inner_voice / 隐私默认不长存原文 / 中文化显置信 / UI 红线只测可见层 / 慢记忆持久化路径补完 / 画布不识字。**12 条修订全部把"UI 体验"还原为"AP 既有机制的视图层"**。

---

## 1. 全部修订清单(9 收 Codex + 3 自查)

| ID | 来源 | 内容 | §X |
|---|---|---|---|
| **C1** | Codex | AP 主动停拆为独立 action candidate,不绑"说完了" | §2 |
| **C2** | Codex | unresolved_pressure 需真 runtime loop,不能 projection only | §3 |
| **C3** | Codex | TTS ≠ inner_voice,拆 reply_tts_audio vs inner_voice_sketch | §4 |
| **C4** | Codex | 录音边界分级:audio_audit_only / phase19_1_pending | §5 |
| **C5** | Codex | 辅助线 = teacher_guided_focus_candidates,与 auto_focus_candidates 并存 | §6 |
| **C6** | Codex | 历史会话默认不存原文,仅时间 + hash + 用户命名 | §7 |
| **C7** | Codex | 记忆中文化显共现支持 + 来源,无共现时显"未命名视觉记忆" | §8 |
| **C8** | Codex | UI 红线测**可见层**不 grep 源码 | §9 |
| **C9** | Codex | 配色改浅灰白 + 少量状态色;emoji 改正式图标 | §10 |
| **Self-1** | 自查 | 慢记忆跨 tick / 跨 turn 持久化路径补完 | §11 |
| **Self-2** | 自查 | Phase 20.5 拆 a/b/c 三步,UI 真实化 → 主动停 → 扩展能力 | §12 |
| **Self-3** | 自查 | 画布不识字,产 PNG 走视觉 SA + 共现,不宣称 OCR | §13 |

---

## 2. C1 — Stop Generating 作为独立 Action Candidate

### 2.1 v1 错误

v1 §4.1 把"低 unresolved_pressure → 说'完了' → 停"写成可教学范式 — 这把"停止动作"和"输出一句话"耦合,违反 AP action competition 原则。

### 2.2 v1a 修正

把 AP 主动停拆成 4 个独立 action,在每 tick 末由 action competition 选一个:

```python
ACTIONS_AT_TURN_END = (
    "continue_draft",          # 继续写下一草稿
    "commit_reply",            # 提交当前草稿作为回复
    "stop_generating",         # 主动停止本 turn
    "request_teacher",         # 反问用户("还要继续吗?")
)
```

每 action 的打分(完全 AP-native,无新机制):

$$
\mathrm{score}(\mathrm{continue\_draft}) = w_p \cdot \mathrm{unresolved\_pressure} + w_n \cdot \mathrm{NOVELTY\_marker} - w_f \cdot \mathrm{fatigue}
$$

$$
\mathrm{score}(\mathrm{commit\_reply}) = w_r \cdot \mathrm{commit\_readiness} + w_c \cdot \mathrm{coherence\_score} - w_u \cdot \mathrm{unresolved\_pressure}
$$

$$
\mathrm{score}(\mathrm{stop\_generating}) = w_t \cdot \mathrm{task\_completion\_signal} - w_p \cdot \mathrm{unresolved\_pressure} - w_n \cdot \mathrm{recent\_NOVELTY}
$$

$$
\mathrm{score}(\mathrm{request\_teacher}) = w_a \cdot \mathrm{ambiguity\_count} + w_c \cdot \mathrm{recent\_CORRECTION\_count}
$$

走既有 `action_competition` (Phase 8 已实现) → Thompson sampling → 选一个执行。

### 2.3 教学共现的正确位置

**用户教"完了"不直接触发停**,而是与"stop_generating 之后该说什么"共现入记忆:

```
1. action_competition 选 stop_generating(基于内部状态)
2. 同 tick 内,sparse_pairwise 中查找 stop_generating action SA 的高共现 token
3. 若有("完了" / "就这样")→ Phase 16 styled 渲染输出 "嗯,就这样。"
4. 若无 → 仅停,无输出
```

**教学如何影响**:
- 用户教"完了" → stop_generating action SA 与 "完了" token 共现 +1
- 多次后,选了 stop_generating action 时自然输出"完了"
- **"停"本身仍由 action competition 决定,不被"完了"反向触发**

### 2.4 红线

```
RL-20.5a-C1-01: stop_generating 必须经 action_competition,不允许由 token "完了" 直接触发
                grep test: 不允许 "if token == '完了': stop()"
RL-20.5a-C1-02: 教学路径只能改 sparse_pairwise.observe_packet,不能改 action score 公式
RL-20.5a-C1-03: 4 个 action 必须全部在 ACTIONS_AT_TURN_END 注册,缺一不可
```

---

## 3. C2 — Runtime Loop 真升级(致命修)

### 3.1 v1 错误

v1 全文假设 "逐 tick" 工作,但 Phase 20.4 的 `workbench_tick_trace` **已被 Codex 报告标为 projection only**(从已提交结果反推的展示投影)。20.5 若直接做主动停 / 多 tick 回放 / 快慢记忆,**全部是前端模拟 AP 思考** — 假拟人。

### 3.2 v1a 修正:Phase 20.5a 先升级 runtime loop

把 Phase 20.5 拆 a/b/c 三步,**a 先升 runtime loop**:

```
Phase 20.5a (3 天):  Runtime loop 真升级 + UI 骨架
  - turn loop 改成每 tick 真演化,每 tick emit RuntimeTickEvent
  - tick trace 由真 event 流采集,不再 projection
  - UI 骨架 + Panel 2 真接 tick event

Phase 20.5b (2 天):  AP 主动停 + 快慢记忆持久化
  - 4 个 action 接入 action_competition
  - 慢记忆持久化路径(§11)
  - 教学共现入 sparse_pairwise

Phase 20.5c (2 天):  扩展能力
  - TTS(reply_tts_audio,§4)
  - 画布(§13)/ 录音(§5)/ 辅助线(§6)
  - Panel 7 包生态完善
```

### 3.3 RuntimeTickEvent 数据结构

```python
@dataclass(frozen=True)
class RuntimeTickEvent:
    tick: int
    source: str                              # "phase20_turn_loop"
    actions_proposed: tuple[ActionCandidate, ...]   # 本 tick action_competition 的所有候选
    action_chosen: ActionCandidate
    state_pool_top12: tuple[StateItemSnapshot, ...] # 快记忆
    state_pool_slow_promotions: tuple[str, ...]     # 本 tick 升入慢记忆的 SA id
    draft_changes: dict[str, Any]                   # 草稿字段 diff
    focus_xy: tuple[int, int] | None
    inner_picture_state: dict[str, Any] | None      # 当前内心画面状态(若有视觉输入)
    energy_RAPF: tuple[float, float, float, float]
    cognitive_pressure: float
    unresolved_pressure: float
    is_projection: bool = False              # 真 runtime event = False; 仅展示降级 = True
```

**红线**:

```
RL-20.5a-C2-01: 任何 Panel 显示 tick 数据时,必须读 RuntimeTickEvent.is_projection 字段
                若 True → UI 显示"⚠ 展示投影,非真 runtime tick"
RL-20.5a-C2-02: workbench_tick_trace_v2 只接真 RuntimeTickEvent,不允许从 turn 结果反推
RL-20.5a-C2-03: 真 runtime loop 未上线时,Phase 20.5b/c 的 AP 主动停 / 快慢记忆 等
                必须延迟实现,不允许用 projection 模拟
```

### 3.4 Gate 升级

```
G-20.5a-Runtime-01: runtime loop 每 tick emit RuntimeTickEvent 单测
G-20.5a-Runtime-02: workbench_tick_trace_v2 100% 来自真 event,is_projection 全为 False
G-20.5a-Runtime-03: Panel 2 进度条切换 tick 时,Panel 3/4/5/6 同步切换的数据来自 RuntimeTickEvent[tick]
```

---

## 4. C3 — TTS ≠ Inner Voice

### 4.1 v1 错误

v1 §4.4 把"pyttsx3 TTS"接到 Panel 4 内心音频区,**严重违反** v1c-audio 设计:`inner_voice_sketch` 必须来自 Phase 19.1 听觉路径,不能是文本 → TTS。

### 4.2 v1a 修正:拆 2 个完全分离的字段

```python
@dataclass
class TurnAudioOutputs:
    # 字段 1: 回复朗读(外部 TTS,可选,默认关)
    reply_tts_audio: Optional[bytes]              # pyttsx3 把 reply_text 朗读
    reply_tts_engine: str                          # "pyttsx3_offline"
    reply_tts_voice_profile: str                   # "xiaomo_default"

    # 字段 2: 内心音频(AP-native,来自 Phase 19.1)
    inner_voice_sketch: Optional[bytes]            # Phase 19.1 R_aud_sketch 合成
    inner_voice_source: str                        # "PERCEIVED" / "REMEMBERED" / "IMAGINED"
    inner_voice_available: bool                    # Phase 19.1 实施完才 True
```

**Phase 20.5c 实施**:
- `reply_tts_audio`:接 pyttsx3,默认关,用户主动开
- `inner_voice_sketch`:**Phase 19.1 未实施前 = None**,UI Panel 4 内心音频区显示"听觉感受器尚未启用"
- **不允许用 reply_tts_audio 假装 inner_voice_sketch**

### 4.3 UI 区分

```
┌──── Panel 1 聊天气泡 ────────┐
│ AP: 嗯,你好。 [▶ 朗读]        │← reply_tts_audio
└─────────────────────────────┘

┌──── Panel 4 内心音频 ────────┐
│ ♪ ▶━━━━●━━━━ 0:00 / 0:04    │← inner_voice_sketch
│ Source: PERCEIVED             │   (Phase 19.1 ON 才有)
│ ⚠ Phase 19.1 听觉感受器未启用 │   (未实施时)
└─────────────────────────────┘
```

### 4.4 红线

```
RL-20.5a-C3-01: Panel 4 内心音频区不允许显示 reply_tts_audio
RL-20.5a-C3-02: reply_tts_audio 与 inner_voice_sketch 必须不同 family / 不同 channel_signature
RL-20.5a-C3-03: Phase 19.1 未实施时,UI 必须明示"听觉感受器尚未启用"
RL-20.5a-C3-04: TTS 引擎必须本地 (pyttsx3),不允许 Edge TTS / Google TTS / OpenAI TTS
```

---

## 5. C4 — 录音边界分级

### 5.1 v1 错误

v1 §4.4 说"录音 → 走 Phase 19.1 听觉感受器(若已实施)→ 否则只保留为审计音频" — 措辞太软,用户可能误以为 AP 已经"听懂"。

### 5.2 v1a 修正:三档明确

```python
@dataclass
class UserAudioInput:
    audio_bytes: bytes
    sample_rate: int
    processing_tier: str   # 三档之一,明确显示给用户
    # "audio_audit_only"           — 仅存,UI 显示波形,不"听懂"
    # "phase19_1_basic_listen"     — Phase 19.1 a 实施后,做 A0..A8 富特征 + 共现
    # "phase19_4_recognition"      — Phase 19.4 实施后,完整听觉概念识别
```

**当前(Phase 20.5)** 默认 `audio_audit_only`:
- 显示波形
- 可回放
- **不**宣称"AP 听懂了"
- 仅存 hash + audit 元数据

### 5.3 UI 显示

```
┌──── 上传音频 ──────────────────┐
│ ♪ ▶━━━━●━━━━ 0:00 / 0:04      │
│                                 │
│ 处理: audio_audit_only          │
│ ⚠ 听觉感受器(Phase 19.1)尚未  │
│   启用,AP 仅记录音频,不识别  │
└─────────────────────────────────┘
```

### 5.4 红线

```
RL-20.5a-C4-01: UserAudioInput.processing_tier 必须显式三档之一,不允许空
RL-20.5a-C4-02: Phase 20.5 默认 audio_audit_only;未来升级到 phase19_1 必须显式更新 tier
RL-20.5a-C4-03: UI 必须显示当前 processing_tier 给用户(banner / chip 形式)
```

---

## 6. C5 — 辅助线 = Teacher-Guided Focus,不是答案标注

### 6.1 v1 错误

v1 §4.4 说"用户上传图后,可在缩略图上拖框 → 框选区域作为 candidate_bbox 强制提示" — "强制"二字 + 没说"不能绑 label",可能让 Codex 实施时让辅助线直接绑标签。

### 6.2 v1a 修正:两条 trace 并存

```python
@dataclass
class FocusCandidates:
    auto_focus_candidates: tuple[CandidateTarget, ...]
    # Phase 21 enumerate_objects_in_image 自动产的候选

    teacher_guided_focus_candidates: tuple[CandidateTarget, ...]
    # 用户在 UI 拖框教师引导,标 source="teacher_attention_cue"
    # 不携带 label,仅一个 bbox 区域
```

教师引导的处理:

1. **不替代** auto_focus_candidates,而是**并存**(合并去重)
2. 用户拖框只产 (x_min, y_min, x_max, y_max) + opaque uuid
3. AP 仍按 Phase 21 三段管线扫视(候选检测 → 视焦点移动 → per-focus 识别)
4. **教师引导 candidate 的 saliency 加成**:`teacher_attention_boost = 0.3` @experimental
5. 仍不绑 label

### 6.3 UI 区分

```
┌──── 图像区 ──────────────────┐
│  [原图]                       │
│  ┌──────┐ auto                │
│  │ ●    │ <- Phase 21 自动    │
│  └──────┘                     │
│        ┌──┐ teacher           │
│        │  │ <- 用户拖框引导    │
│        └──┘                   │
│                                │
│ Auto candidates: 4            │
│ Teacher cues: 1                │
└────────────────────────────────┘
```

### 6.4 红线

```
RL-20.5a-C5-01: teacher_guided_focus_candidates 不允许携带 label / concept
RL-20.5a-C5-02: 教师引导 candidate 必须与 auto_focus_candidates 显式分离存储 + 显示
                grep test: UI 上必须有"auto" vs "teacher"两色 chip
RL-20.5a-C5-03: 教师引导仅 boost saliency 0.3,不替代 Phase 21 自动管线
```

---

## 7. C6 — 历史会话默认不存原文

### 7.1 v1 错误

v1 §3 Panel 0 历史会话列表暗示会存"12:34 你好…"这样的原文摘要,违反 v14 隐私规则(普通 user_text 默认不持久化)。

### 7.2 v1a 修正

历史会话条目默认:

```python
@dataclass
class SessionHistoryEntry:
    session_id: str                          # opaque uuid
    started_at_iso: str
    turn_count: int
    duration_seconds: float
    user_label: str = ""                      # 用户手动命名(空则只显示时间)
    summary_hash: str = ""                    # 内容 hash,可用于去重 / 关联
    save_user_text_explicit: bool = False     # 必须用户点 "保存原文" 才 True
```

**显示策略**:

| 用户是否命名 | 显示 |
|---|---|
| 命名 = "苹果教学" | "苹果教学 · 12:34" |
| 未命名,save_explicit=False | "12:34 · 12 turn" |
| 未命名,save_explicit=True | "12:34 · 你好…(原文)" |

### 7.3 红线

```
RL-20.5a-C6-01: 历史会话默认 save_user_text_explicit=False
RL-20.5a-C6-02: 仅 explicit=True 时,SQLite 才存原文(继承 v14 user_text_persisted 标志)
RL-20.5a-C6-03: 用户可在设置中"清除所有原文",清后 explicit→False,只剩 hash
```

---

## 8. C7 — 记忆中文化显示置信 + 来源

### 8.1 v1 错误

v1 §4.3 说"sparse_pairwise top 共现词翻译" 但没说显示置信/来源,容易变"语义脑补"。

### 8.2 v1a 修正:中文化必带证据

```python
def render_memory_label_human_readable(sa_id: str) -> MemoryLabelDisplay:
    """
    返回:
    - 中文名(来自 sparse_pairwise top 共现 token)
    - 置信值 (共现 support)
    - 来源(teacher_event / natural_dialogue)
    - 若无共现 → "未命名视觉记忆"(opaque uuid 缩略 8 位)
    """
    partners = sparse_pairwise.top_partners(sa_id, top_k=3)
    if not partners or partners[0].support < 0.15:
        return MemoryLabelDisplay(
            display_name=f"未命名记忆 {sa_id[:8]}",
            support=0.0,
            source="unnamed",
            evidence=[],
        )
    return MemoryLabelDisplay(
        display_name=partners[0].token,
        support=partners[0].support,
        source=partners[0].packet_source,    # "teacher_event" / "natural_dialogue"
        evidence=[(p.token, p.support, p.source) for p in partners[:3]],
    )
```

### 8.3 UI 显示

```
慢记忆 #3
  名: 苹果  (置信 0.82)
  ⓘ 来源: 教师短句 × 3 次 + 自然对话 × 1 次
       hover 显示 top-3 partners
```

**关键**:
- 不只显示"苹果",显示"苹果 0.82"
- 来源教师 vs 自然对话明示
- top-3 partners hover 可看(用户能审阅"为什么 AP 觉得这是苹果")

### 8.4 红线

```
RL-20.5a-C7-01: 记忆 display_name 必须附带 support 值
RL-20.5a-C7-02: support < 0.15 不允许显示"具体名字",必须显示"未命名记忆 XXX"
RL-20.5a-C7-03: hover 显示 top-3 partners 强制
```

---

## 9. C8 — UI 红线测可见层,不 grep 源码

### 9.1 v1 错误

v1 G-20.5-UI-07 写 "grep test:UI 文本不含 `style_paradigm::` 等裸 id" — 但**源码必须处理这些 id**,grep 必然命中。

### 9.2 v1a 修正:测**渲染后的 DOM**,不测源码

```python
def test_phase20_5a_visible_ui_no_raw_sa_ids():
    """
    用 Playwright 渲染 UI,抓 visible text,检查无裸 sa_id 模式.
    """
    page = playwright.new_page()
    page.goto("http://127.0.0.1:8765")
    visible_text = page.locator("body").inner_text()

    forbidden_patterns = ["style_paradigm::", "vision_object::",
                          "inner_picture::perceived::"]
    for pat in forbidden_patterns:
        assert pat not in visible_text, f"裸 sa_id 模式 '{pat}' 出现在用户可见 UI"
```

### 9.3 审计折叠层

允许用户开"调试模式",在折叠区可看 raw sa_id(给开发者排查用):

```
┌──── 慢记忆 #3 ─────────────────┐
│ 名: 苹果  (置信 0.82)           │
│ ⓘ 教师短句 × 3 次               │
│                                 │
│ ▶ 调试信息(折叠默认隐藏)       │
│   sa_id: style_paradigm::a3f9b1 │
│   source family: inner_picture..│
└─────────────────────────────────┘
```

### 9.4 红线

```
RL-20.5a-C8-01: 默认可见 UI(任何不需要"展开调试"的位置)不含裸 sa_id 模式
RL-20.5a-C8-02: 用户点击"开调试模式"才能看 raw id
RL-20.5a-C8-03: Playwright 渲染后 DOM 不含 forbidden patterns(单测)
```

---

## 10. C9 — 配色 + 图标改正式

### 10.1 v1 错误

v1 §5 米白 #FAFAF7 + 暖黄 #E8C547 → 偏奶油色。emoji 当主图标不稳。

### 10.2 v1a 修正

| 元素 | v1 | v1a |
|---|---|---|
| 背景主色 | #FAFAF7 米白 | **#F7F7F8 浅灰白** |
| 文字主色 | #2E4960 深蓝 | **#1F2937 深灰蓝** |
| 强调色 | #E8C547 暖黄 | **#5B9F6B 状态绿**(教学已记 / 完成)|
| 焦点蓝 | (无) | **#3B82F6 蓝**(用户操作高亮)|
| 警告 | #B05050 暗红 | 保留 |
| 状态色面板 | (大面积)| **小色块 chip 用,大面积保留灰白** |
| 图标 | emoji 📷🎤 | **Heroicons 或 Lucide outline 图标**(SVG)|
| 字体 | 系统默认 | 同 v1 |

### 10.3 图标库选择

Lucide ([https://lucide.dev/](https://lucide.dev/)) — Apache 2.0,SVG,体积小,16×16 / 20×20 标准。

替换示例:
- 📷 → `<Image />` 或 `<Camera />`
- 🎤 → `<Mic />`
- 🎨 → `<Pencil />` 或 `<Brush />`
- 🔍 → `<Search />`
- ➕ → `<Plus />`

### 10.4 红线

```
RL-20.5a-C9-01: emoji 不允许作为主图标(grep test:不允许 \U0001F4F7 等 emoji 在 button 文本)
RL-20.5a-C9-02: 引入图标库 = Lucide / Heroicons / Phosphor,任一 (Apache 2.0 / MIT)
RL-20.5a-C9-03: 大面积用浅灰白,状态色仅 chip / badge 形式
```

---

## 11. Self-1 — 慢记忆跨 tick / 跨 turn 持久化路径

### 11.1 v1 缺口

v1 §4.3 说"慢记忆 = attention_energy 累积 top-6 跨 tick",但 state_pool 当前不持久化跨 turn。

### 11.2 v1a 修正:Slow Memory Store

```python
class SlowMemoryStore:
    """跨 tick + 跨 turn 持久化的 attention_energy 累积 top-N store."""

    def __init__(self, sqlite_path: Path):
        self.db = sqlite3.connect(sqlite_path)
        self._init_schema()

    def observe(self, tick: int, state_items: Sequence[StateItem]) -> None:
        """每 tick 调用 — 累积该 tick 高 attention_energy 的 SA 到长期表."""
        for item in sorted(state_items, key=lambda i: -i.attention_energy)[:6]:
            if item.attention_energy > float(load_constant("slow_memory.promotion_threshold")):
                self._upsert_slow_memory_record(
                    sa_id=item.sa_id,
                    accumulated_attention=item.attention_energy,
                    last_seen_tick=tick,
                    channel_signature=item.channel_signature,
                )

    def top_n_persistent(self, n: int = 6) -> list[SlowMemoryRecord]:
        """跨 turn 持久化 top-N attention_energy 累积."""
        return self.db.execute(
            "SELECT * FROM slow_memory ORDER BY accumulated_attention DESC LIMIT ?",
            (n,)
        ).fetchall()

    def decay_step(self) -> None:
        """每 turn 调用一次衰减,防止永久饱和."""
        decay_rate = float(load_constant("slow_memory.decay_per_turn"))
        self.db.execute(
            "UPDATE slow_memory SET accumulated_attention = accumulated_attention * ?",
            (decay_rate,)
        )
```

新常量:

```yaml
slow_memory:
  promotion_threshold: 0.6       # @experimental - attention_energy > 0.6 进慢记忆
  decay_per_turn: 0.95           # @experimental - 每 turn 衰减 5%
  max_records: 1000              # @structural
```

### 11.3 红线

```
RL-20.5a-Self1-01: 慢记忆持久化必须独立 SQLite 表,不混入 chat_session_trace
RL-20.5a-Self1-02: 用户可在设置中"清除慢记忆",清后表清空(隐私选项)
RL-20.5a-Self1-03: 慢记忆衰减必须每 turn 调用,防止永久饱和
```

---

## 12. Self-2 — Phase 20.5 拆 a/b/c 三步

### 12.1 v1 缺口

v1 一份设计稿想 6 天做完所有东西,但 Codex C2 揭示 runtime loop 没真升级,直接做主动停 / 多 tick 回放是假拟人。

### 12.2 v1a 修正:三步走

| 阶段 | 内容 | 工作量 |
|---|---|---|
| **Phase 20.5a** | Runtime loop 真升级 + RuntimeTickEvent + UI 骨架 + Panel 1/2 真接 event | 3 天 |
| **Phase 20.5b** | 4 个 action competition + 慢记忆持久化 + Panel 3/4/5/6 完整 | 2 天 |
| **Phase 20.5c** | TTS reply / 画布 / 录音 audit / 辅助线 / Panel 7 | 2 天 |

每阶段独立验收 + Final Report。

### 12.3 Gate

```
G-20.5a-Phase-01: 20.5a 完成后,workbench_tick_trace 来自真 RuntimeTickEvent(is_projection 全 False)
G-20.5b-Phase-01: 20.5b 完成前,不允许实施 TTS / 画布 / 录音(防止 a 没扎实就堆功能)
G-20.5c-Phase-01: 20.5c 完成前,慢记忆持久化必须先在 20.5b 通过验收
```

---

## 13. Self-3 — 画布不识字,产 PNG 走视觉 SA

### 13.1 v1 缺口

v1 §4.4 提画字能力,但**"画字识别"= OCR**,违反银子老师之前明文"不要独立 OCR 模块"。

### 13.2 v1a 修正

画布输出 PNG,走 Phase 21 视觉管线,**不识字**:

```python
class UserCanvasInput:
    canvas_png_bytes: bytes
    width: int
    height: int
    processing_tier: str = "visual_audit_via_phase21"
    # AP 把画布当一张图,产视觉 SA + 候选检测
    # 不识字,不 OCR
```

**用户画一个"苹果"字**:
- AP 走 Phase 21 → 产视觉 SA + 共现学习
- 若用户同 turn 教"这是苹果字" → "苹果字" token 与该视觉 SA 共现
- 多次教学后,看到类似手绘"苹果"字时,sparse_pairwise 召回"苹果字" token
- **本质是视觉共现学习,不是 OCR**

### 13.3 UI 说明

```
┌──── 画布 ──────────────────┐
│  [画板 256×256]            │
│  [清空] [完成]             │
│                            │
│ ⚠ 画布按视觉图处理,        │
│   不识别字符;教 AP 必须    │
│   配合文字共现.            │
└────────────────────────────┘
```

### 13.4 红线

```
RL-20.5a-Self3-01: 画布输出严格走 Phase 21 视觉路径,不接 OCR
                    grep test: 不允许 import pytesseract / easyocr / paddleocr
RL-20.5a-Self3-02: UI 必须明示"不识字,需配合教学"
```

---

## 14. 修订后的 Deliverable Gates(增量)

### 14.1 Phase 20.5a Gates(8)

| Gate |
|---|
| G-20.5a-R-01 RuntimeTickEvent dataclass 实现 + emit 测 |
| G-20.5a-R-02 workbench_tick_trace_v2 100% 来自真 event |
| G-20.5a-R-03 Panel 2 进度条切换 → Panel 3/4/5/6 真同步 event |
| G-20.5a-R-04 UI 骨架三栏 + 8 面板空盒子,响应式 |
| G-20.5a-R-05 Panel 1 聊天气泡含图缩略,显示 ObjectFile + 把握感 |
| G-20.5a-R-06 历史会话默认不存原文(C6)|
| G-20.5a-R-07 真名 0 命中 |
| G-20.5a-R-08 全量回归不破 |

### 14.2 Phase 20.5b Gates(10)

| Gate |
|---|
| G-20.5b-S-01 4 个 action(continue_draft/commit/stop/request_teacher)接入 action_competition |
| G-20.5b-S-02 stop_generating 不允许由 token "完了" 直接触发(C1)|
| G-20.5b-S-03 SlowMemoryStore 持久化(Self-1)|
| G-20.5b-S-04 慢记忆每 turn 衰减 |
| G-20.5b-S-05 中文化显示带 support + 来源(C7)|
| G-20.5b-S-06 无共现时显示"未命名记忆"(C7)|
| G-20.5b-S-07 调试折叠层可看 raw sa_id(C8)|
| G-20.5b-S-08 Playwright DOM 不含裸 sa_id(C8)|
| G-20.5b-S-09 Panel 3 能量折线图 + Panel 5 想法云完整 |
| G-20.5b-S-10 Panel 6 快慢记忆双轨 + R_proto 缩略图 |

### 14.3 Phase 20.5c Gates(8)

| Gate |
|---|
| G-20.5c-X-01 reply_tts_audio 接 pyttsx3,默认关 |
| G-20.5c-X-02 reply_tts_audio 与 inner_voice_sketch 不同 family(C3)|
| G-20.5c-X-03 录音 audio_audit_only 默认,UI 显示 banner(C4)|
| G-20.5c-X-04 辅助线 teacher_guided_focus_candidates 与 auto 分存(C5)|
| G-20.5c-X-05 画布走 Phase 21,不接 OCR(Self-3)|
| G-20.5c-X-06 配色改浅灰白 + Lucide 图标(C9)|
| G-20.5c-X-07 Panel 7 包生态完善(导入/导出/卸载/搜索)|
| G-20.5c-X-08 端到端 5 turn demo 跑通 + 银子老师签收 |

---

## 15. 总检查清单(v1 + v1a 合读后)

- [ ] AP 主动停 = action competition,不绑 token
- [ ] runtime loop 真升级,is_projection 全 False
- [ ] TTS = reply_tts_audio,inner_voice 留给 Phase 19.1
- [ ] 录音 audio_audit_only 三档
- [ ] 辅助线两条 trace 并存,不绑 label
- [ ] 历史会话默认不存原文
- [ ] 中文化显示 support + 来源,无共现时"未命名"
- [ ] UI 红线测渲染 DOM,不测源码
- [ ] 配色浅灰白 + 状态色 chip
- [ ] emoji → Lucide
- [ ] 慢记忆持久化 + 衰减
- [ ] Phase 20.5 拆 a/b/c 三步
- [ ] 画布不识字
- [ ] 真名 0 命中

---

## 16. 银子老师拍板项(v1a)

1. **Phase 20.5 拆 a/b/c 三步**(7 天总,而非 6 天一气):同意吗?
2. **stop_generating 改 action competition**(C1):同意拟人原则?
3. **TTS ≠ inner_voice**(C3):同意拆 reply_tts_audio?
4. **画布不识字**(Self-3):同意走 Phase 21 视觉路径 + 配合文字共现?
5. **配色改浅灰白 + Lucide**(C9):还是您喜欢温暖的米白?可以选其它配色

---

## 17. 署名

- 原架构设计:银子老师(笔名)
- v1a Errata:Claude (Anthropic) 吸收 Codex 9 项必修 + 自查 3 项隐患后产出
- 落地:Codex 在 v1a 通过最终复核后启动 Phase 20.5a

End of Phase 20.5 v1a Errata.
