# APV3.0 Phase 20 Design — Open Chinese Dialogue Foundation with Multimodal Input, Object Enumeration, and Source-Aware Correction

Date: 2026-06-20
Author: Claude(架构),银子老师(风格定调与最终签收)
Status: 设计稿(完整版 = MVP + 反馈纠错闭环),开工前等审查
Landing note:
- 本稿必须与 `Errata_Phase20_v1a_SourcePrivacyFeedbackGate_20260620.md` 合读。
- v1a 已覆盖并修正 §4.5 的 `visual_context_hint` 示例、§5/§10 中“一轮反馈后 raw_confidence 必涨”的硬验收口径、以及 Step 8 用户图片持久化边界。
Trigger:
1. Phase 21 验收完成 — truth-in-labels 11/12,候选检测 100%,firm-错 0/12
2. Phase 19.9 Zvec 召回加速底座完成
3. 银子老师明确"要完整版本",Option 3 双轨(Phase 20 主线 + Phase 21 v1b 并行微修)
Final Goal:
- **G1** 自由开放中文对话底座(用户任意中文 + 图片 + 反馈)
- **G2** 四大应用场景:**前端网页对话 demo / agent 结合 / 桌宠 / 具身智能**
  - 网页 demo 与 agent:最简单,Phase 20 一并交付
  - 桌宠:底座 Phase 20 能做,效果打磨需时间(Phase 22+)
  - 具身智能:暂不做(等硬件 + Phase 23+)
- **G3** 短期图片认知(扫视列举 + 拟人把握感)
License intent: AGPL-3.0-or-later
Real name handling: 全文件 grep 真名 = 0

---

## 0. 这一份做什么(一句话)

把已落地的 5 个独立子系统 — **Phase 21 object 列举** + **Phase 19.9 Zvec 召回** + **Phase 19.5 source-aware feedback** + **Phase 16 styled corpus** + **现有 MinimalistDialogueFlowRuntime** — 通过一个**对话回合循环**接通,让用户可以"输入中文+图片 → AP 扫视+列举+styled 回应 → 用户对/不对反馈 → AP source-aware 调权",从而实现 G1 自由开放中文对话底座的第一个可跑版本。

---

## 1. 设计原则(每条都对照最终目标)

| 原则 | 服务 G | Why |
|---|---|---|
| **复用既有 MinimalistDialogueFlowRuntime** 不重写对话引擎 | G1 | 现有 chat session 已经处理用户文字 + 学习短语 + cooccurrence 记忆,Phase 20 只**接入**新模态/反馈,不重新发明 |
| **图像输入走 Phase 21 ObjectLookingResult** 而非直识别 | G3 | 银子老师明确"识别 = 移动焦点列举",Phase 21 已实测 truth-in-labels 11/12 |
| **回应文本走 Phase 16 styled corpus 索引** 而非硬编 | G1, G2 | Phase 16 130 范式 × 90 候选 = 11830 styled candidates 已完成,小默风格 |
| **用户反馈走 Phase 19.5 source-aware** 不直接覆盖 weights | G1 | v1d/v1e 已锁:用户"不对" → 通过 R_net + eligibility 分摊到 source 路径 |
| **跨模态绑定 = 时间窗口 6 tick** 共享 ConceptPrototype 不另起 | G1, G3 | v1e §10 已定:6 tick 内多模态共现 → 同 concept,不为对话另搞 |
| **Zvec 召回不输出 label** 仅给 candidate UUID | G3 | Phase 19.9 已锁红线,Phase 20 不破 |

---

## 2. 对话回合循环(完整 8 步)

```
┌─────────────────────────────────────────────────────┐
│ 用户输入(可同时含):                                  │
│   - text: "这是什么"                                  │
│   - image: <可选>                                     │
│   - feedback: 对/不对/纠正(可选,针对上轮 AP 输出)    │
└─────────────────────────────────────────────────────┘
                ↓ Phase 20 turn loop
┌─────────────────────────────────────────────────────┐
│ Step 1: parse_user_input                            │
│   - 拆 text / image / feedback                       │
│   - feedback 类型: positive / negative / explicit_label│
└─────────────────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────────────┐
│ Step 2: process_feedback (若 last_turn 存在 + 用户给反馈)│
│   - 走 Phase 19.5 source-aware feedback              │
│   - R_ext = +1 / -1 / 0;计算 credit;调 Layer-3 w   │
│   - 不直接覆盖,仅注入信号                            │
└─────────────────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────────────┐
│ Step 3: process_image (若 image 存在)                │
│   - 走 Phase 21 enumerate_objects_in_image           │
│   - ObjectLookingResult → 多个 ObjectFile            │
│   - 每 ObjectFile 含 (label, tier, raw_conf)        │
└─────────────────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────────────┐
│ Step 4: bind_multimodal (若 image + text 同 turn)    │
│   - 6 tick 时间窗口绑定                              │
│   - vision_percept_uuid + text_vocab_sa_id 共享      │
│     temporal_event_uuid,可后续 promote 为 concept    │
└─────────────────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────────────┐
│ Step 5: minimalist_dialogue_turn                    │
│   - 走 MinimalistDialogueFlowRuntime                 │
│   - 输入: user_text + 视觉证据(ObjectFile labels)    │
│   - 输出: feeling_label + learned_phrase_id          │
└─────────────────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────────────┐
│ Step 6: select_styled_response                      │
│   - 根据 feeling + 视觉证据,从 styled corpus 选范式   │
│     - 有 ObjectFile 且 firm/soft → styled_agree     │
│     - 有 ObjectFile 但全 no_call → styled_co_silence│
│     - 无 ObjectFile → 走纯文字范式                    │
│     - feedback negative → styled_correction         │
│   - 从 130 范式池里 deterministic + variant 抽       │
└─────────────────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────────────┐
│ Step 7: assemble_reply                              │
│   - 把 styled response 与 ObjectFile labels 拼装     │
│   - 若有列举:"嗯,看到苹果。…香蕉?" (拼 N 段)        │
│   - 若拒绝:"...还不能确认。"                          │
│   - 通过 assert_style_compliant 检查                  │
└─────────────────────────────────────────────────────┘
                ↓
┌─────────────────────────────────────────────────────┐
│ Step 8: persist_turn + commit_to_zvec               │
│   - ChatTurn 入 SQLite                              │
│   - 若 image 存在 → image trace signature → Zvec     │
│   - last_turn snapshot 留给下轮 feedback 用          │
└─────────────────────────────────────────────────────┘
```

---

## 3. 数据结构(扩展现有 ChatTurn,不发明新类)

### 3.1 ChatTurn v2(扩展)

```python
@dataclass(frozen=True)
class ChatTurn:
    tick: int
    user_text: str
    user_text_hash: str
    user_text_length: int
    user_text_persisted: bool
    reply_text: str
    reply_tokens: tuple[str, ...]
    feeling_label: str
    learned_phrase_id: str

    # Phase 20 新增字段(全 audit-only,不进 packet_key)
    image_input_hash: str | None = None              # 用户传入图的 sha256
    object_files: tuple[ObjectFile, ...] = ()         # Phase 21 输出
    feedback_kind: str = "none"                       # positive/negative/explicit_label/none
    feedback_target_object_index: int | None = None   # 用户反馈针对第几个 object(可空)
    feedback_explicit_label: str | None = None        # 用户说"那是苹果不是橙子"
    styled_paradigm_id: str = ""                      # 走的 styled corpus 范式 ID(audit)
    multimodal_binding_event_uuid: str | None = None  # 跨模态绑定 event(可空)
```

### 3.2 不新增 family / marker_kind(继承 v14 marker_kinds cap=20)

Phase 20 只调度,不发明新认知机制。

### 3.3 为什么这样

- 现有 ChatTurn 已稳定,扩字段不破回归
- 所有新字段 audit-only,不影响 packet_key 或学习路径
- 维持 v14 marker cap 红线

---

## 4. 每步详细设计 + Why

### 4.1 Step 1: parse_user_input

```python
@dataclass
class UserTurnInput:
    text: str = ""
    image_path: Path | None = None
    feedback_kind: str = "none"                  # positive / negative / explicit_label
    feedback_target_object_index: int | None = None
    feedback_explicit_label: str | None = None

def parse_user_input(raw: Mapping[str, Any], last_turn: ChatTurn | None) -> UserTurnInput:
    """
    从 web 或 CLI 收到的 raw dict 转 UserTurnInput.
    - feedback 解析:用户文字含"对"/"嗯对" → positive
                   含"不对"/"不是" → negative + 可选 explicit_label
    - feedback 解析必须接到 last_turn,否则丢弃(只回顾上一轮)
    """
```

**Why**: 把"用户的实际话"拆成"AP 要处理的 3 个角色"(说点什么 / 给图 / 给反馈)。3 路径分离让后续每步只处理自己的事。

### 4.2 Step 2: process_feedback

```python
def process_feedback(
    feedback: UserTurnInput,
    last_turn: ChatTurn | None,
    *,
    state_pool: StatePool,
) -> FeedbackTrace:
    """
    若 last_turn 含 object_files,且用户给了反馈:
    - positive: R_ext = +1, target = last_turn.object_files[idx]
    - negative: R_ext = -1
    - explicit_label: R_ext = -1 + 标对的 label,触发 source-aware learning
    走 Phase 19.5 apply_natural_correction_credit + reward_packet_action
    返回 audit trace(不能直接改 Layer-3 weights — 必须通过既有 SDPL 路径)
    """
```

**Why**:
- 反馈不能是"用户说不对 → 立刻改 weight",必须经 R_net + eligibility(v1d/v1e/v1e 三轮锁)
- 走 `apply_natural_correction_credit` 复用既有自然纠错路径

### 4.3 Step 3: process_image

```python
def process_image(
    image_path: Path,
    *,
    teaching_examples: Sequence[VisualTeachingExample],
    state_pool: StatePool,
) -> ObjectLookingResult:
    """
    直接调 Phase 21 enumerate_objects_in_image.
    teaching_examples 走"Layer-3 ConceptPrototype 已学概念" → train.
    """
```

**Why**:
- Phase 21 实测 truth-in-labels 11/12 是 G3 当前最强可用形态
- 不绕过 Phase 21,不重新发明扫视

### 4.4 Step 4: bind_multimodal(关键,v1e §10 已设计但未落)

```python
def bind_multimodal(
    object_files: Sequence[ObjectFile],
    text_tokens: Sequence[str],
    tick: int,
    *,
    state_pool: StatePool,
) -> str | None:
    """
    若 vision + text 6 tick 内同时到 → temporal_event_bind.
    若该 event 反复出现 ≥ 4 次 → promote 到 ConceptPrototype (v1e §10.2).
    Phase 20 实施只到 bind,不实施 promotion(留 Phase 22).
    """
    if not object_files or not text_tokens:
        return None
    event_uuid = temporal_event_bind(
        tick,
        vision_percepts=[obj.recognition.top_concept_uuid for obj in object_files],
        text_tokens=text_tokens,
    )
    return event_uuid
```

**Why**:
- v1e §10 已经设计完,但前面阶段没接通(Phase 21 只看图不绑文字)
- Phase 20 是绑定第一次有真用户文字 + 真图像同 turn 出现的契机

### 4.5 Step 5: minimalist_dialogue_turn

```python
def call_minimalist_dialogue_turn(
    user_text: str,
    object_files: Sequence[ObjectFile],
    runtime: MinimalistDialogueFlowRuntime,
    tick: int,
) -> MinimalistDialogueTurnInput:
    """
    走既有对话引擎.
    object_files 当作"已感受到的视觉证据"注入 user_text 上下文.
    不替换 runtime 内部决策,只丰富输入.
    """
    visual_context_hint = (
        f"[视觉证据: {len(object_files)} 个对象, 顶 label = {object_files[0].recognition.top_visible_label if object_files else 'none'}]"
        if object_files else ""
    )
    augmented_text = (user_text + " " + visual_context_hint).strip()
    return runtime.turn(
        MinimalistDialogueTurnInput(text=augmented_text, tick=tick)
    )
```

**Why**:
- 现有 MinimalistDialogueFlowRuntime 已稳定运行 ~580 tests
- visual_context_hint 让 AP 内部 attention 知道"有视觉证据进来",但具体怎么用是 AP 自己决策
- 不强制塞 label 进 user_text 否则破坏自然对话

### 4.6 Step 6: select_styled_response(关键 — 银子老师的小默)

```python
PARADIGM_BY_SITUATION = {
    "object_firm":          "PAR-A.02",  # 招呼+确定承接
    "object_soft":          "PAR-A.06",  # 略微不确定
    "object_no_call":       "PAR-Q.06",  # 共在沉默
    "feedback_negative":    "PAR-N.01",  # 用户指错
    "feedback_positive":    "PAR-D.02",  # 表扬反应接受
    "no_object":            None,         # 走 MinimalistDialogueFlow 原回应
}

def select_styled_response(
    object_files: Sequence[ObjectFile],
    feedback_kind: str,
    feeling_label: str,
    affect_bucket: str,
    intensity_bucket: str,
    *,
    styled_corpus: Mapping,
    rng_seed: str,
) -> tuple[str, str]:
    """
    返回 (paradigm_id, response_tokens).
    根据 situation → 选 PAR;再按 (affect, intensity) 选 cell,
    deterministic 抽 variant(seed 来自 turn_hash).
    """
```

**Why**:
- Phase 16 130 范式池里已经有 `PAR-A 招呼` / `PAR-N 错误纠正` / `PAR-Q 物品互动` / `PAR-D 表扬接受` 等正好对应对话情境的范式
- 用 deterministic seed(turn_hash)使相同输入产生相同回应,可重跑 audit
- 不需要训练 NLG 模型,纯查表 — 这正是"AP-native 无 LLM"的具体落地

### 4.7 Step 7: assemble_reply

```python
def assemble_reply(
    styled_tokens: Sequence[str],
    object_files: Sequence[ObjectFile],
    runtime_reply: str | None,
) -> str:
    """
    拼装最终回复:
    - 单对象: f"{styled_tokens[0]} {object_label}。"        # 嗯,看到苹果。
    - 多对象: f"{styled_tokens[0]} {label1}。…还有 {label2}?"  # 嗯,苹果。…还有橙子?
    - 全 no_call: 走 styled_tokens 但不加 label             # 嗯。…
    - 无图: 走 runtime_reply 不改                            # 既有 MinimalistDialogue 输出
    最后过 assert_style_compliant 验证不超字数 + 不含 LLM 病禁词
    """
```

**Why**:
- 拼装规则非常拟人(小默风格"嗯,苹果。…橙子?")
- assert_style_compliant 是 Phase 16 既有的红线 — 复用不破

### 4.8 Step 8: persist_turn + commit_to_zvec

```python
def persist_turn(
    turn: ChatTurn,
    *,
    sqlite_store: SQLiteRuntimeStore,
    zvec_recall: Layer1ZvecRecallIndex | None,
) -> None:
    """
    1. SQLite 真源写 turn(全部字段)
    2. 若 turn.image_input_hash 存在 → 把 image trace signature 入 Layer-1 + Zvec
       - Zvec 仅存 signature_256 + UUID,不存 user_text, 不存 image bytes
    3. 不写 last_turn 短期缓存(单进程 session 内存即可)
    """
```

**Why**:
- SQLite 是真源(继承 v1e 红线),Zvec 是派生召回(Phase 19.9 红线)
- 用户传图 → 进 Layer-1 = 教学积累的开始(用户每次给 AP 看东西,都给 ConceptPrototype 加证据)

---

## 5. 反馈闭环 — 关键拟人路径

### 5.1 完整一轮反馈例子

```
Turn N:
  用户: [上传真实苹果1.jpeg]
  AP: 走 Phase 21 → object_files = [(banana, no_call, 0.13), (apple, no_call, 0.11)]
      走 styled → "嗯。…(列举)"
      reply: "嗯。…还不能确认。"

Turn N+1:
  用户: "那是苹果"
  AP: parse → feedback_kind = "explicit_label", target = 0, label = "apple"
      apply_natural_correction_credit:
        - 上轮 object_files[0] 的 R_ext = -1(预测 banana,真实 apple)
        - 通过 eligibility trace 调相关 V7/V10 channel weights for banana ↓
        - Layer-3 banana ConceptPrototype 这次的 contribution 减
        - 同时 Layer-3 apple ConceptPrototype + contribution (因 explicit_label)
      styled → PAR-N.01 (用户指错)
      reply: "嗯,我错了。"

Turn N+2:
  用户: [再上传真实苹果2.jpg]
  AP: 走 Phase 21 → object_files = [(apple, soft, 0.27)]
                   ← 显著上升,因为 N+1 已经调权
      styled → PAR-A.06 (略微不确定但承接)
      reply: "嗯,像是苹果。"
```

**Why 拟人**:
- AP 错过一次后**知道自己错了**(走 source-aware),不是"立刻学到 apple"
- 反复几次后,raw_confidence 自然升上来,出现 soft → firm
- 这就是 v1e §8 设计的 $\Delta w = \eta \cdot e_i \cdot \mathrm{credit}_i \cdot R_{\mathrm{net}}$ 第一次在用户对话中真生效

### 5.2 不允许的反馈路径(红线)

```
RL-20-Feedback-01: 用户"不对"不允许直接调用 Layer3.concept_prototype_weight = X
                  必须经 apply_natural_correction_credit
                  grep test: web_chat / minimalist_chat 路径不写 Layer3.weights[*] = *
RL-20-Feedback-02: feedback 不允许跨 turn 累积超过 last_turn 一个
                  只对上一轮 object_files 起作用
                  防止"AP 说了 5 次错,用户最后说一句不对" → 5 次错全部加固
RL-20-Feedback-03: explicit_label 仅在 last_turn 含 object_files 时有效
                  防止"用户给 label 但没图" → 凭空发明 concept
```

---

## 6. 四大场景的具体玩法(G2 举证,修订:正确场景)

### 6.1 前端网页对话 demo(**Phase 20 主交付**,最简单)

**形态**:基于既有 [apv3test/web_chat.py](apv3test/web_chat.py) 扩展,加 multipart 接收图 + 反馈。
银子老师在浏览器打开 http://127.0.0.1:8767/chat.html(参考 Phase 15 课程回放页),界面包含:
- 输入框:任意中文
- 上传按钮:任意图(可选)
- 反馈按钮:"对" / "不对" / "其实是 X"(针对 AP 上一条回应)
- AP 回应区:文本 + 列举对象框 + 把握感档位 chip

**5 turn demo 走 G3 + G1**:
```
T1: 用户输:"嗨"
    AP: "嗯,你好。"  (PAR-A.01)

T2: 用户上传 真实苹果1.jpeg
    AP: 走 Phase 21 → [(banana, no_call), (apple, no_call)]
        "嗯。…还不能确认。"  (PAR-Q.06 共在沉默)

T3: 用户:"那是苹果"
    AP: 反馈 explicit_label="apple", source-aware credit
        "嗯,我错了。"  (PAR-N.01 错误纠正)

T4: 用户上传 真实苹果2.jpg(同类不同图)
    AP: raw_conf ↑ 因为 Layer-3 已加证据
        "嗯,像是苹果。"  (PAR-A.06 略不确定承接)

T5: 用户:"对"
    AP: 反馈 positive
        "...还行。"  (PAR-D.02 表扬接受)
```

**为什么这是 Phase 20 主交付**:
- 上手成本零 — 浏览器即可
- 银子老师做开源 alpha 时这就是"演示用的 demo"
- 可分享 — 任何人打开都能看到 G1 + G3 工作
- **Phase 20 完成 = 这个页面跑通**

### 6.2 Agent 结合(简单,Phase 20 一并交付一个工具样例)

**形态**:把 Phase 20 turn loop 包成 Python 函数,作为外部 agent 框架(如 Cursor 内嵌、Claude Code 工具、其它 LLM Agent)的工具调用:

```python
# 在 agent 框架里注册
@agent_tool("ap_native_perceive_and_reply")
def ap_perceive_and_reply(text: str, image_path: str | None = None) -> dict:
    """
    AP-native 拟人感受 + 回应.
    返回:
        {
            "reply": str,                  # 小默风格回应
            "object_files": [...],         # 看到了什么(若有图)
            "decision_tier": str,          # firm / soft / ambig / no_call
            "raw_confidence": float,
            "epistemic_source": str,       # 这次回应的来源标(PERCEIVED/REMEMBERED/...)
        }
    """
    session = get_or_create_phase20_session()
    return session.turn(text=text, image_path=image_path).to_dict()
```

**用途**:
- 外部 LLM agent 拿不准时 → 调 `ap_perceive_and_reply` 拿到拟人化的"如果是人会怎么看 / 怎么说"
- 给 agent 加一个"AP-native 感受 + 记忆"工具,补 LLM 不擅长的拟人决策
- AP 的 source-aware feedback 让 agent 也能"教"AP

**Phase 20 工作量**:把 turn loop 输出一个干净 dataclass + 提供 tool 注册 schema → 半天

**为什么算简单**:
- 不需要新前端,只是 Python 接口
- agent 框架自己处理 UI
- Phase 20 turn loop 一旦稳定,agent tool wrapper 就是薄薄一层

### 6.3 桌宠(**底座 Phase 20 已支持,效果打磨在 Phase 22+**)

**形态**:桌面悬浮像素小人,接 Phase 20 turn loop:
- 用户右键 → 输入框 + 截屏给 AP 看
- AP "嗯,看到了。" → 小人表情切到对应 feeling_label
- AP source-aware feedback 让小人"学习"

**Phase 20 给桌宠提供的底座**:
- ✓ turn loop 已可被 GUI 调用(Python 函数)
- ✓ feeling_label 输出可驱动表情
- ✓ object_files 输出可驱动"小人看着 xx"动画
- ✓ source-aware 让小人有"记忆 + 学习"

**Phase 22+ 才做的(桌宠效果打磨)**:
- 像素小人美术资产(需要银子老师设计)
- 表情动画(joy / sad / curious / shy ...)
- 桌面集成(Electron / PyQt / WebView)
- 系统监控 hook(用户切应用,小人有反应)
- 长期共处状态(陪伴感 / 早晚招呼 / 节日)

**为什么"底座 Phase 20 能做,效果打磨需时间"**:
- 底座 = turn loop + feeling + object 输出 → Phase 20 完成时全部具备 ✓
- 效果打磨 = 美术 + 动画 + 系统集成 + 长期状态 → Phase 22+ 单独立项

### 6.4 具身智能(暂不做)

**形态**:Phase 23+ 启动。需要硬件(摄像头实时流 + 机械臂 / 移动底盘)+ Phase 19.6 active perception 真的实时驱动 + Phase 19.1a 听觉真接通麦克风。

**Phase 20 不做**,但 turn loop 设计已为之留接口位:
- Step 3 process_image 已经是"单帧入"形态 — 未来摄像头每秒 N 帧调用即可
- Phase 19.6 motion_map 接口已留 — 帧差计算可接
- Step 8 persist 已经异步友好

**何时启动**:银子老师采购摄像头 + Phase 22 桌宠效果稳定后再上。

---

## 7. 与已有底座的精确接口

| 已有子系统 | Phase 20 接口 | 不动 |
|---|---|---|
| MinimalistDialogueFlowRuntime | call Step 5 input augmentation 仅加视觉证据 hint | runtime 内部决策 |
| Phase 16 styled corpus(130 范式 yaml) | Step 6 select_styled_response 读取 | yaml 本身 |
| Phase 21 enumerate_objects_in_image | Step 3 直接调用 | object_looking.py 内部 |
| Phase 19.5 apply_natural_correction_credit | Step 2 反馈触发 | natural_correction.py |
| Phase 19.9 Zvec recall_index | Step 8 commit + 未来 Step 3 召回加速 | recall_index.py |
| SQLiteRuntimeStore | Step 8 persist | sqlite_runtime_store.py |
| MinimalistChatSession (apv3test/chat.py) | Phase 20 包成 Phase20MultimodalSession 继承 | 现有 chat.py |
| Web app (apv3test/web_chat.py) | 加 POST /turn 接受 multipart (text + image + feedback) | 现有 routes 不破 |

---

## 8. 实施分解(给 Codex,6 天)

| 天 | 工作 |
|---|---|
| **Day 1** | Phase20MultimodalSession 类 + UserTurnInput / ChatTurn v2 扩展 + parse_user_input + 单测 |
| **Day 2** | Step 3 process_image 接 Phase 21 + Step 4 bind_multimodal + 单测 |
| **Day 3** | Step 6 select_styled_response 加载 styled yaml + paradigm 选择规则 + 单测(每 situation 都过)|
| **Day 4** | Step 2 process_feedback 接 Phase 19.5 + Step 7 assemble_reply + 单测反馈闭环 |
| **Day 5** | Step 8 persist + Zvec commit + Web app 加 multipart 接口(§6.1 网页 demo)+ **agent tool wrapper(§6.2 半天)**|
| **Day 6** | §6.1 网页 demo 5 turn 端到端跑通 + agent tool 单测 + Final Report + 展示页(桌宠 §6.3 底座可用性说明)|

---

## 9. Deliverable Gates(20 条)

### 9.1 接口层(7)
| Gate |
|---|
| G-20-IF-01 Phase20MultimodalSession 类实现,继承 MinimalistChatSession 不重写 turn 决策 |
| G-20-IF-02 ChatTurn v2 加 7 字段全部 audit-only(不进 packet_key) |
| G-20-IF-03 parse_user_input 单测覆盖 text-only / image-only / text+image / feedback 4 路径 |
| G-20-IF-04 process_image 真调 Phase 21 enumerate_objects_in_image(grep test) |
| G-20-IF-05 select_styled_response 从 130 范式 yaml 真选(不硬编)|
| G-20-IF-06 persist 真写 SQLite 真源 + Zvec 加速(继承 19.9 红线)|
| G-20-IF-07 assemble_reply 走 assert_style_compliant 不破 Phase 16 风格 |

### 9.2 拟人对话层(7)
| Gate |
|---|
| G-20-Anth-01 单对象 firm/soft → "嗯,X。" 输出符合小默风格(单测)|
| G-20-Anth-02 单对象 no_call → "嗯。…还不能确认。" 不喊错(单测)|
| G-20-Anth-03 多对象 → "嗯,X。…还有 Y?" 拼装(单测)|
| G-20-Anth-04 用户"对"→ 走 PAR-D 表扬接受(单测)|
| G-20-Anth-05 用户"不对"→ 走 PAR-N 错误纠正(单测)|
| G-20-Anth-06 用户 explicit_label → 走 PAR-N + 触发 spawn_tentative_concept(若新 concept)|
| G-20-Anth-07 多 turn 反馈 → 同一图再传第二次,raw_confidence 上升(实测 ≥ 0.1)|

### 9.3 红线层(6)
| Gate |
|---|
| G-20-RL-01 反馈不直接写 Layer-3 weights(grep test)|
| G-20-RL-02 feedback 只对 last_turn 起作用(单测)|
| G-20-RL-03 image bytes 不进 packet_key / SQLite 长存(只 sha256)|
| G-20-RL-04 user_text 默认不持久化(继承 v14 RL),只 hash |
| G-20-RL-05 真名 0 命中(全 Phase 20 文件 grep)|
| G-20-RL-06 不调外部 LLM / API / TTS / Whisper(grep test)|

### 9.4 场景层(4 新增)
| Gate |
|---|
| **G-20-Scen-01** 前端网页 demo §6.1 5 turn 端到端跑通(银子老师签收 — Phase 20 通过验收的核心条件)|
| **G-20-Scen-02** agent tool §6.2 `ap_perceive_and_reply(text, image_path)` Python 函数实现 + 返回 dataclass + 单测验证 schema |
| **G-20-Scen-03** agent tool 单测覆盖 4 路径:text-only / image-only / text+image / feedback |
| **G-20-Scen-04** Phase 20 Final Report 含 §6.3 桌宠底座可用性说明(turn loop + feeling + object 输出可被 GUI 调用,**不**宣称桌宠美术 / 动画完成)|

---

## 10. 期待效果

### 10.1 量化

| 指标 | Phase 20 落地后 |
|---|---|
| 单对象 firm/soft 出现率 | ≥ 6/12(从 Phase 21 当前 0/12)|
| 多 turn 反馈后再传同图,raw_conf 上升 | ≥ 0.10 |
| 4 场景 demo 各跑通 5 turn | ✓ |
| firm + 错 | 0 ✓(继承 v1a 红线)|
| 拟人对话回应符合小默风格 | 银子老师签收 |

**Why "Phase 20 落地后 6/12 soft/firm 出现"** — 因为现在 Phase 21 全 no_call 是 train 集太少(9 张 clean cards),用户上传图 + 反馈一轮后 Layer-3 +几张样本,自然会形成 soft 把握。

### 10.2 质化(银子老师签收点)

- 用户在 web 上传"真实苹果1.jpeg" + 说"那是苹果"
- AP 在下一次看到"真实苹果2.jpg"时输出"嗯,像是苹果。"(soft)
- 用户在 web 上传冰箱照,AP 列举"嗯,牛奶。…橙子。"
- 用户难过时上传自己,AP 回"...嗯。"(不试图诊断,只共在)

---

## 11. 为什么这条路真能实现最终目标(逐条举证)

### G1 自由开放中文对话底座

**举证**:
- Step 5 复用已稳定 580 tests 的 MinimalistDialogueFlowRuntime → 自由开放中文已 in place
- Step 3 接入 Phase 21 列举 → 用户能给图,不只文字
- Step 2 接入 source-aware feedback → 用户能教,AP 能学
- Step 6 + Step 7 走 Phase 16 styled → 回应自然小默风格
- **整合产物**:用户在网页可以任意中文 + 图 + 反馈,AP 全 AP-native 处理,无 LLM
- 这正是 G1 第一个 demo-able 形态

### G2 四大场景

**举证(修订)**:见 §6 — 4 场景按交付难度分层:
- **§6.1 前端网页 demo**(Phase 20 主交付,5 turn demo 跑通 = Phase 20 通过验收的核心条件)
- **§6.2 agent 工具结合**(Phase 20 同期半天加 tool wrapper,提供 `ap_perceive_and_reply` Python 函数接口)
- **§6.3 桌宠**(Phase 20 提供底座 = turn loop + feeling + object 输出;效果打磨 = 美术 + 动画 + 系统集成 → Phase 22+)
- **§6.4 具身智能**(Phase 23+,需硬件,Phase 20 留接口位)

### G3 短期图片认知

**举证**:
- Phase 21 已落地 truth-in-labels 11/12 + 候选检测 100%(已验收)
- Phase 20 加反馈闭环后,用户每教一次,Layer-3 +证据 → 第 2 次再看同类相似图能 soft 把握(关键拟人发展)
- 不是"一次到位",是"用户教学积累" — 这才是 AP-native 拟人路径
- 多 turn 反馈测(G-20-Anth-07)是 G3 核心实证

---

## 12. 不会再被打脸的硬条件

| 风险 | 防护 |
|---|---|
| 又是 prose 装饰? | G-20-IF-04 grep test process_image 真调 Phase 21 |
| Styled 硬编绕过 yaml? | G-20-IF-05 单测必从 yaml 读 |
| 反馈直接覆盖 weights? | G-20-RL-01 grep test |
| Phase 16 风格被破坏? | G-20-IF-07 assert_style_compliant 是既有红线 |
| 外部 LLM 偷偷接入? | G-20-RL-06 grep test |
| Zvec 变 hidden classifier? | 继承 Phase 19.9 红线 |

---

## 13. 边界(Phase 20 不做的事)

- 不实现 ConceptPrototype promotion(temporal_event → concept 升级是 Phase 22)
- 不实现真正的中文 NLU(走 styled corpus 查表 + 现有 MinimalistDialogue 不变)
- 不接听觉(Phase 19.1 已设计但未实施,Phase 23)
- 不接桌宠图形界面(Web 即可,桌面 app 是 Phase 24)
- 不实现持久对话历史检索(单 session 即可,跨 session 是 Phase 22 加 cooccurrence 长存)
- 不做用户身份(单用户 / 单 session)

---

## 14. 银子老师拍板项

1. **完整版 Phase 20 设计(8 step + 反馈闭环 + 4 场景 分层交付)**:同意吗?
2. **Day 1-6 分解 + 20 Gate**:任何想加/删的吗?
3. **场景交付顺序**(我推荐):
   - **Phase 20 主交付 = 前端网页 demo §6.1** (5 turn 端到端跑通)
   - **Phase 20 同期 = agent tool wrapper §6.2**(半天加 Python 函数接口)
   - **Phase 20 提供桌宠底座 §6.3**(turn loop + feeling + object 输出可用,但不做美术 / 动画 / 系统集成)
   - **具身 §6.4 留接口位不实施**

---

## 15. 署名

- 原架构设计:银子老师(笔名)
- Phase 20 设计:Claude (Anthropic) 在 Phase 21 验收完成 + 银子老师"要完整版本"决策后,直接读 MinimalistDialogueFlowRuntime / styled corpus / natural_correction / Phase 21 / Phase 19.9 接口后产出
- 落地:Codex 在审查通过后 5-6 天落地

End of Phase 20 Design.
