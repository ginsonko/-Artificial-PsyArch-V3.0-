# APV3.0 Phase 21 Design — Object-Centric Identifying-by-Looking + Phase 19.9 Zvec Recall Substrate

Date: 2026-06-19
Author: Claude(架构),银子老师(风格定调与最终签收)
Status: 设计稿(基于现有底座盘点 + 银子老师明确"识别 = 移动视焦点扫视 + 列举",写完后等审查)
Final Goal: **自由开放中文对话底座 + 四大应用场景 + 短期图片内容认知**
Real name handling: 全文件 grep 真名 = 0
License intent: AGPL-3.0-or-later

---

## 0. 终极目标先锁定(每条设计都必须服务于此)

| 目标 | 含义 |
|---|---|
| **G1** 自由开放中文对话底座 | 用户输入任意中文,AP 用 Phase 16 小默风格回应,**包含视觉/听觉/记忆/共情/把握感**多模态判断 |
| **G2** 四大应用场景 | 桌宠 / 老师/教练 / 倾听者(共情陪伴)/ 家庭助理(看图 + 听声 + 算数) |
| **G3** 短期图片内容认知 | **不是给图打一个 label**,是**列出图里有几样东西、各自在哪、各自把握** |

每条设计在 §X 末尾都会写"为什么这一条服务 G1/G2/G3"。如果某条不能 trace 到任一目标,说明它是噪声,要删除。

---

## 1. 现状盘点(我直接读完代码 + AP_Core_Proof 之后,这是真实情况)

### 1.1 银子老师指出的盲点 — 实测确认

读 [phase19_runtime.py:716 `_diagnostic_fixation_log`](runtime/cognitive/percept_vector/phase19_runtime.py#L716) 和 [phase19_runtime.py:429 `visual_recognize_v1_7`](runtime/cognitive/percept_vector/phase19_runtime.py#L429):

- `visual_recognize_v1_7` 只调用一次 `extract_visual_audit_path_v2(query_image_path)`(用默认焦点 = 图像中心)
- `_diagnostic_fixation_log` 生成的 fixation 是**纯几何 prose**(用 `width * phase` 计算 chosen_x/y),**没有真重新采样**
- `choose_next_fixation` 和 `active_visual_scan` **已实现**,但**没被 recognize() 调用**
- `update_from_native_image` 真把 patch fusion 实现了,但识别管线没接

**铁证**:Phase 19 7 份 errata 反复写 fixation,但识别路径**根本没用**。

### 1.2 已存在但未接通的"应该用"

| 文件 / 函数 | 实际做了什么 | 是否被识别用 |
|---|---|---|
| [visual_focus.py](runtime/cognitive/attention/visual_focus.py) `propose_visual_focus_actions` | 已实现 saccade_to_visual / fixate_visual / release_visual 三个 action proposal,基于 `_visual_salience = R + A + P - F` | **未接入识别** |
| `choose_next_fixation` | 用 clarity_need + confidence_need + motion_map 选下一个焦点,纯 numpy | **未接入识别** |
| `active_visual_scan` | 多 tick 扫视 + canvas 累积,**完整实现** | **未接入识别**,只有测试调过 |
| `SensoryCanvas.update_from_native_image` | 真做了 confidence-weighted Bayesian blending | 只有 active_visual_scan 内部调 |
| [epistemic_source_feelings.py](runtime/cognitive/cognitive_feelings/epistemic_source_feelings.py) `imagination_sense` | IMAGINED marker 推算 | 接了对话情绪但不接识别 |
| MISMATCH / NOVELTY / CORRECTION marker | 8.2/8.3 设计完整 | 不参与识别路径 |
| `propose_visual_focus_actions` 输入 = state_pool item (channel_signature contains "vision") | 必须有 vision item 才能扫视 | 识别时无 vision item 注入,直接死循环 |

### 1.3 已实现可借鉴的 "拟人扫视样本"

[`countloop0_object_quantity_successor_acquisition`](experiments/countloop0_object_quantity_successor_acquisition.py) — 在 AP_Core_Proof 里教 AP 数物体数量(0/1/2/3 个 slot),并学到"后继关系"(N → N+1)。**这是已通过的拟人测试**,SlotCase 的逻辑 = 在抽象 SA 层数物体。这等同于:**AP 已经知道"几个东西"这种概念**,只是从来没接到视觉通道上。

### 1.4 真实问题集中诊断

**Phase 19 v1c..v1h + 19.7/19.8 全部的根因**:**识别 = 全图采样 + 通道公式 + nearest neighbor**。这是 image classifier 范式,不是拟人。修公式 / 修通道 / 修 mask / 加数据都治标。

**真正 AP 拟人识别 = 用扫视构建对象列表**,这是范式转变,需要 Phase 21。

---

## 2. Phase 21 总设计 — 三段管线

```
┌──────────────────────────────────────────────┐
│  阶段 A: 候选目标检测(看见这张图有哪些东西可能值得看)│
│  - 输入: 整图(只看一遍,生成 saliency map)         │
│  - 输出: List[(x, y, region_size, saliency)]      │
│         ≤ 6 个候选点                              │
└──────────────────────────────────────────────┘
                ↓ 注入 state_pool 作为 "未看清楚的视觉候选"
┌──────────────────────────────────────────────┐
│  阶段 B: 先天因素 + 后天因素 决定下一焦点          │
│  - 先天: saliency / 运动 / 颜色对比 / 中心偏置     │
│  - 后天: cognitive_pressure / MISMATCH / NOVELTY  │
│         /用户语言指引 / 任务 attention goal         │
│  - 调度: 通过 propose_visual_focus_actions       │
└──────────────────────────────────────────────┘
                ↓ 选定 fixation_xy
┌──────────────────────────────────────────────┐
│  阶段 C: Per-focus 识别 + IOR + 列举            │
│  - 在 fixation_xy 用 extract_visual_audit_path  │
│         _v2 高清采样                              │
│  - 走当前 visual_recognize_v1_7 但 query 是 focus │
│         patch feature,不是全图 feature           │
│  - 产 (label, tier, conf, position)              │
│  - 加 IOR,本焦点压制 30 tick 不再被选            │
│  - 回到 阶段 B 选下一个,直到 saliency 全压或预算用完│
└──────────────────────────────────────────────┘
                ↓
        List[Object]: 经 Phase 16 styled corpus 渲染
        "嗯,看到苹果。…右下香蕉?…还有橙子。"
```

### 2.1 为什么这条管线服务 G3

- 阶段 A 解决"图里有什么"的列举问题(不是单 label)
- 阶段 B 让先天因素(强度/意外/违和/运动) + 后天学习的注意力 联合决定看哪里 — 拟人正确根据
- 阶段 C 用 v1c 设计的 foveated patch 真正只采样焦点高清区,**避开背景污染** — 这就是您一直说的"焦点扫到苹果就识别成苹果",不是"看全图判断像谁"

### 2.2 为什么这条管线服务 G1

阶段 C 输出多对象列表 + 用户问"这张图里有啥?" → Phase 16 styled corpus 渲染"嗯,苹果。…还有橙子。" — 这就是开放对话底座要用图像输入的真实接通

### 2.3 为什么这条管线服务 G2

- 桌宠场景:用户给桌宠看一张图,桌宠"嗯,猫?" — 拟人,且**承认有限**(soft tier)
- 老师/教练场景:让 AP 看一张课堂图,问"你看到几个学生?" — 阶段 A 数候选点 = 数物体
- 倾听者场景:用户传一张照片说"今天去看了爸妈" — AP 看到多个对象后选最重要的回应"嗯,看到他们了。"
- 家庭助理场景:用户传冰箱照片 → AP 列举里面有什么

---

## 3. 阶段 A: 候选目标检测器(用现有底座,不写新组件)

### 3.1 数学

输入 RGB 整图 $I$,产 saliency map $S$:

$$
S(x, y) = w_e \cdot |\nabla I| + w_c \cdot \mathrm{LAB}\_\mathrm{contrast\_to\_neighbours}(x, y) + w_p \cdot \mathrm{center\_prior}(x, y) + w_n \cdot \mathrm{novelty}(x, y)
$$

每项:

- $|\nabla I|$ — Sobel 边缘强度(已有 `_sobel_magnitude` in `visual_receptor.py`)
- $\mathrm{LAB\_contrast}$ — 像素周围 K 邻域 LAB 距离(已有 `_rgb_to_lab`)
- $\mathrm{center\_prior}$ — 已有 `_center_prior` in `visual_receptor.py`
- $\mathrm{novelty}$ — 跟当前 Layer-3 ConceptPrototype 平均特征的负 cosine(可省略,初版设 0)

### 3.2 候选点提取

```python
def extract_candidate_targets(rgb, *, max_targets=6) -> list[CandidateTarget]:
    """
    1. 算 saliency map S
    2. 非极大值压制 (NMS) 半径 = min(W,H) * 0.08(避免相邻点聚)
    3. 取 top-max_targets 高 S 点
    4. 每点估周边 region_size:从该点扩散,直到 saliency 降到 0.4 倍以下
    5. 输出 [(x, y, region_size, saliency_score), ...]
    """
```

### 3.3 注入 state_pool

每个候选点产一个 SA 注入 state_pool:

```python
StateItem(
    sa_id=f"visual_candidate::<image_trace_hash>::{idx}",
    family="visual_candidate",
    real_energy=saliency_score,
    cognitive_pressure=1.0 - saliency_score,  # 越显眼越需要看清楚
    channel_signature=("vision", "candidate"),  # 关键:vision 让 propose_visual_focus_actions 选它
    metadata={
        "focus_xy": (x, y),
        "region_size": region_size,
        "saliency_score": saliency_score,
    }
)
```

### 3.4 为什么这样

**channel_signature 含 "vision"** → 复用 [visual_focus.py:97 `_is_visual_item`](runtime/cognitive/attention/visual_focus.py#L97) → 自动进入 `propose_visual_focus_actions` 候选 — 完全用现有底座调度,不写新调度器。

### 3.5 服务目标 — G3 直接服务(列举里有什么),G2 桌宠/家庭助理直接服务

---

## 4. 阶段 B: 先天因素 + 后天因素 决定下一焦点

### 4.1 银子老师指出的因素清单

| 因素 | 类型 | 数学化 | 已有底座 |
|---|---|---|---|
| **强度(显眼)** | 先天 | saliency_score | candidate 的 real_energy |
| **意外输入** | 先天 | 突然出现的 SA → NOVELTY marker | Phase 8 NOVELTY 已实现 |
| **违和感** | 先天 + 后天 | MISMATCH marker 强度 | Phase 8.5 已实现 |
| **运动跟随** | 先天 | motion_map(帧差) | choose_next_fixation 接口已留,实现待补 |
| **后天主动学习** | 后天 | 用户教学时焦点位置 → 学到的 attention prior | Layer-3 加 association_attention_prior 字段 |
| **任务驱动(用户问"看到几个?")** | 后天 | task_drive 接口已留 | v1d §6 设计稿有,实现待补 |

### 4.2 统一打分公式(把现有底座的扫视调度真的接通)

每个 candidate SA 在每 tick 重新打分:

$$
\mathrm{score}(p) = w_{\mathrm{innate}} \cdot S_{\mathrm{innate}}(p) + w_{\mathrm{learned}} \cdot S_{\mathrm{learned}}(p) - w_{\mathrm{IOR}} \cdot \mathrm{IOR}(p)
$$

$$
S_{\mathrm{innate}}(p) = \alpha_1 \mathrm{saliency}(p) + \alpha_2 \mathrm{novelty}(p) + \alpha_3 \mathrm{mismatch}(p) + \alpha_4 \mathrm{motion}(p)
$$

$$
S_{\mathrm{learned}}(p) = \beta_1 \mathrm{task\_drive}(p) + \beta_2 \mathrm{attention\_prior\_from\_layer3}(p)
$$

`IOR(p)` = 已注视过且 30 tick 内的位置 mask × 衰减。

### 4.3 复用既有底座

这个公式**90%** 与 [visual_focus.py:88 `_visual_salience = R + A + P - F`](runtime/cognitive/attention/visual_focus.py#L88) **完全对应**:

- $R$(real_energy)= saliency_score(阶段 A 注入)
- $A$(attention_energy)= 学习先验 attention_prior(后天)
- $P$(cognitive_pressure)= 1 - saliency_score(看不清的压力)
- $F$(fatigue)= IOR(已经看过的疲劳)

也就是说,**只需在阶段 A 把 candidate 注入,然后 `propose_visual_focus_actions` 自动选 saccade_to_visual → choose_next_fixation 拿出 chosen_xy**。**不需要写新调度器**。

### 4.4 为什么这样

- **拟人**:先天因素(显眼/意外/违和/运动)+ 后天因素(任务/学到的 attention prior)汇合,完全对应人类视觉 attention 的 Itti-Koch saliency 模型 + Posner cue paradigm + Yarbus task-driven scanning
- **复用既有底座**:不写新调度器,**完全用 Phase 8/9/11 已实现的 attention + marker 体系**
- **接通既有 R / A / P / F 能量动力学**:这是 v14 锁定的 4 能量字段,所有学习都在它们之上,我们识别也不绕过

### 4.5 服务目标 — 阶段 B 是 G3 拟人化扫视的核心,也是 G1/G2 多模态对话的注意力底座

---

## 5. 阶段 C: Per-focus 识别 + IOR + 列举

### 5.1 关键差异(跟当前 visual_recognize_v1_7)

| | 当前 visual_recognize_v1_7 | Phase 21 per-focus |
|---|---|---|
| query feature | extract_visual_audit_path_v2(全图,默认中心) | extract_visual_audit_path_v2(focus_xy=阶段 B 选的位置) |
| 候选 region | 全图 mask | focus_xy 周围 32×32 像素(原图直采,继承 v1c V0 foveal) |
| V7/V10/V11 抽取范围 | 全图 → 通常被背景污染 | 只在 focus patch 内 SLIC → V7 干净 |
| 输出 | 1 个 label | per-focus 一个 ObjectCandidate |

### 5.2 Per-focus 识别函数(直接用现有 visual_recognize_v1_7,改 query path 即可)

```python
def recognize_at_focus(image_path, focus_xy, *, teaching_examples, tick) -> ObjectCandidate:
    """
    在指定焦点位置做一次拟人识别。
    """
    # 关键:用焦点位置抽特征(不是默认全图中心)
    query_trace = extract_visual_audit_path_v2(image_path, focus_xy=focus_xy, tick=tick)

    # 走当前 visual_recognize_v1_7 已实现的 channel noisy-OR + 拟人 Conf
    # 唯一改变 = 传入的是 focus-scoped trace
    result = _visual_recognize_v1_7_with_trace(query_trace, teaching_examples, tick)

    return ObjectCandidate(
        focus_xy=focus_xy,
        label=result.top_visible_label,
        tier=result.decision_tier,
        raw_confidence=result.raw_confidence,
        margin=result.nearest_negative_margin,
    )
```

### 5.3 列举主循环

```python
def enumerate_objects_in_image(image_path, *, teaching_examples, max_objects=6, tick_budget=30):
    """
    完整 Phase 21 三段管线。
    """
    rgb = _as_rgb_array(image_path)

    # 阶段 A
    candidates = extract_candidate_targets(rgb, max_targets=max_objects)
    inject_candidates_to_state_pool(candidates, image_trace_hash=hash(image_path))

    objects: list[ObjectCandidate] = []
    seen_ior_mask = np.zeros(rgb.shape[:2], dtype=np.float32)
    tick = 0

    while tick < tick_budget and len(objects) < max_objects:
        # 阶段 B - 走现有 propose_visual_focus_actions
        state_items = state_pool.get_visual_candidates(image_trace_hash)
        proposals = propose_visual_focus_actions(state_items)
        if not proposals: break

        # 按 §4 score 排,取最高的 saccade_to_visual
        chosen = next((p for p in proposals if p.action_kind == "saccade_to_visual"), None)
        if not chosen: break
        chosen_meta = state_pool.get_by_sa_id(chosen.target_sa_id).metadata
        focus_xy = chosen_meta["focus_xy"]

        # IOR 检查 - 若 30 tick 内已注视过,跳过
        if seen_ior_mask[focus_xy[1], focus_xy[0]] > 0.5:
            apply_visual_focus_action(state_items, chosen, tick=tick)  # release
            tick += 1; continue

        # 阶段 C - per-focus 识别
        obj = recognize_at_focus(image_path, focus_xy=focus_xy, teaching_examples=teaching_examples, tick=tick)
        objects.append(obj)

        # IOR 注入(30 tick 衰减)
        seen_ior_mask = update_ior_mask(seen_ior_mask, focus_xy, half_life=30)

        # 该 candidate SA 注 fatigue → 不再被选(用 release_visual)
        release_proposal = next(p for p in proposals if p.action_kind == "release_visual")
        apply_visual_focus_action(state_items, release_proposal, tick=tick)
        tick += 1

    return ListOfObjects(objects, tick_budget_used=tick, ior_mask=seen_ior_mask)
```

### 5.4 输出 styled

```python
def render_list_of_objects_as_styled(objects: list[ObjectCandidate]) -> str:
    """
    走 Phase 16 styled corpus 渲染.
    单 object: "嗯,看到苹果。" (firm) / "像是苹果。" (soft) / "可能是苹果,也可能是橙子。" (ambig)
    多 object: "嗯,苹果。…还有香蕉?…橙子。"
    无 object: "...还不能确认。"
    """
```

### 5.5 服务目标

- G3 直接服务:**这就是"列出图里有什么"**
- G1 接通:输出 = 自然中文回应
- G2 桌宠 / 老师 / 家庭助理 全部直接受益

---

## 6. 数手指 / 数物体能力的接通

银子老师明确说"数手指/数数"。这正是 G2 老师/教练场景必需。

### 6.1 已有底座

[`countloop0_object_quantity_successor_acquisition`](experiments/countloop0_object_quantity_successor_acquisition.py) **已经通过的拟人测试** — AP 在 SlotCase 抽象 SA 层能数 0/1/2/3 个物体并学后继。

### 6.2 接通方法

```
图片输入 (Phase 21 enumerate_objects_in_image)
    → ListOfObjects(N 个 ObjectCandidate)
    → 注入 N 个 visual_candidate SA 到 state_pool
    → 触发 countloop 的"数 SA 数量"机制
    → AP 内部计数 = N
    → Phase 16 styled corpus 渲染:"嗯,看到三个。" / "两个苹果一个橙子。"
```

**关键**:阶段 A 候选检测器**直接产 N 个 SA**,数感系统自动数得到 N。这就是为什么阶段 A 把候选注入 state_pool 是关键 — 不只识别用,**数感也用**。

### 6.3 服务目标 — G2 老师/教练 + G3 列举

---

## 7. Phase 19.9 — Zvec 接入(向量召回加速底座)

### 7.1 Zvec 实测情况

- License: **Apache 2.0** ✓
- PyPI: `pip install zvec`,Python 3.10-3.14
- Embedded in-process(像 SQLite,不需 server)✓
- DiskANN + WAL 持久化
- Dense + Sparse + Hybrid Retrieval
- Windows / Linux / macOS / Android
- Battle-tested(Taobao 搜索、Alipay 人脸、Youku 都在用)
- 性能 8000+ QPS on VectorDBBench Cohere 10M

### 7.2 Codex 的判断(我完全同意)

**Zvec 做派生缓存,不取代真源**:

```
真源(继续用):
  - SQLite / JSON / NPZ — epistemic_source, substrate, receptor_version
  - license_id, source_url, 课程来源, held-out 标记
  - 审计日志, packet_key 红线
  - Phase 19.5 source-aware contribution 计算

派生缓存(改用 Zvec):
  - Layer-1 PerceptVector signature 召回索引(C 召回)
  - Layer-2 PartPrototype codebook 倒排索引
  - Layer-3 ConceptPrototype association 索引

绝不允许:
  - Zvec 输出 "这是苹果"(它只能"这些向量像 query")
  - Zvec 跨 source/substrate/receptor_version 串库
  - Zvec 单独运行 — 必须可由真源完整重建
```

### 7.3 工程接入

```python
# 真源仍是 SQLite
class Layer1PerceptVectorStore:
    def __init__(self, sqlite_path, zvec_path):
        self.sql = sqlite3.connect(sqlite_path)         # 真源
        self.zvec = zvec.Collection(zvec_path)          # 召回索引(派生)

    def insert(self, vector_uuid, signature_uint8_256, full_vec_path, metadata):
        # 1. 真源(SQLite)
        self.sql.execute("INSERT INTO percept_vectors ...", (vector_uuid, full_vec_path, json.dumps(metadata)))
        # 2. 派生索引(Zvec)
        self.zvec.insert(
            id=vector_uuid,
            vector=signature_uint8_256,
            metadata={"epistemic_source": metadata["epistemic_source"],
                      "substrate": metadata["substrate"],
                      "receptor_version": metadata["receptor_version"]}
        )

    def c_recall(self, query_signature, *, source_filter, top_k=10):
        # 用 Zvec 高速召回,但严格过滤 source/substrate/version
        return self.zvec.search(
            vector=query_signature,
            top_k=top_k,
            filter={"epistemic_source": source_filter.epistemic_source,
                    "substrate": source_filter.substrate,
                    "receptor_version": source_filter.receptor_version}
        )

    def rebuild_zvec_from_sqlite(self):
        """红线: Zvec 删除后,必须能由 SQLite 完整重建"""
        ...
```

### 7.4 为什么这样

- **G1 对话底座**:对话累积久了 Layer-1 会有几千张 instance,brute-force topK 慢,Zvec 8000 QPS 解决性能瓶颈
- **G2 四大场景**:桌宠 + 家庭助理 用户教学积累快,需要召回性能
- **G3 短期图片认知**:Phase 21 阶段 C 用 C 召回找 candidate concepts,需要快
- **工程简洁**:一个 `pip install zvec` 解决,不用自己写 ANN
- **AP-native 红线不破**:Zvec 只是召回加速,识别决策仍 100% 走 AP 拟人 Conf

### 7.5 边界(写死红线)

| RL | 描述 |
|---|---|
| RL-19.9-Z01 | Zvec 仅做派生召回,不存唯一真源 |
| RL-19.9-Z02 | 删除 Zvec 索引后,必须能由 SQLite/NPZ 完整重建 |
| RL-19.9-Z03 | Zvec 召回结果不允许直接输出 label,必须经 AP 拟人 Conf 公式 |
| RL-19.9-Z04 | Zvec 不允许跨 epistemic_source / substrate / receptor_version 召回 |
| RL-19.9-Z05 | Zvec 不存 license_id / source_url / 真名 / 用户原文 |
| RL-19.9-Z06 | Zvec 接入必须有 fallback (Zvec 不可用时 brute-force topK 仍能跑) |
| RL-19.9-Z07 | grep test: visual_recognize / enumerate_objects 不直接调 zvec.search,只调 Layer1.c_recall |

---

## 8. 落地路线 + 必备 Gate

### 8.1 Phase 21 (5-6 天)

| 阶段 | 工作量 | Gate |
|---|---|---|
| A: 候选目标检测器 + 注入 state_pool | 2 天 | 12 张图每张产 ≥ 1 ≤ 6 候选;saliency map > 0.5 的点至少包含主体 |
| B: 扫视调度真接通 propose_visual_focus_actions | 1 天 | grep test: enumerate_objects 调 propose_visual_focus_actions ≥ 1 次;**禁止** `_diagnostic_fixation_log` 那种 prose |
| C: per-focus 识别 + IOR + ListOfObjects | 2 天 | 12 张图重跑,期待 ≥ 9/12 至少一个对象正确识别;**新增多物体合成图测试**:把真苹果+真香蕉+真橙子拼成一张图,期待 ≥ 2 对象正确列举 |
| 数感接通 | 0.5 天 | countloop 数感接 ListOfObjects 长度;"图里有几个" 输出正确 N |
| Phase 16 styled 渲染 | 0.5 天 | 输出符合小默风格("嗯,苹果。…橙子。") |

### 8.2 Phase 19.9 Zvec(平行/穿插,3 天)

| 阶段 | Gate |
|---|---|
| pip install zvec + Layer1.c_recall 接入 | brute-force vs Zvec 召回 top-10 结果一致(模糊度 ≤ 5%) |
| SQLite 真源不变 | 重启进程,删除 Zvec 索引,可由 SQLite 重建,再跑 12 张图结果同 Phase 21 不接 Zvec 时一致 |
| 红线 RL-19.9-Z01..Z07 | grep test 全过 |

### 8.3 Phase 20 对话底座(Phase 21 完成后,5-6 天)

| 阶段 | Gate |
|---|---|
| 接通 Phase 16 styled + Phase 21 enumerate + Phase 15 课程回放 | 用户上传图 + 中文输入 → AP 回应自然 styled 列举 |
| 用户教学反馈(v1e §5 eligibility)接通 | 用户说"不对",触发 Layer-3 weight 调整 |
| 4 场景小 demo(桌宠 / 老师 / 倾听 / 家庭) | 每场景 1 个 5 turn demo,银子老师签收 |

---

## 9. 关键自查(避免再被打脸的硬条件)

| 自查项 | 答 |
|---|---|
| 这次还会不会"fixation 设计但没接"? | 8.1 阶段 B Gate **强制 grep test** `enumerate_objects` 必须调 `propose_visual_focus_actions` ≥ 1 次;**禁止** `_diagnostic_fixation_log` 那种 prose,违反就 Gate fail |
| 还有没有别的"设计与实现脱节"? | 阶段 A 候选注入 state_pool 必须真注 SA(grep test: state_pool 接到 family="visual_candidate" 的 SA);per-focus 识别真在 focus_xy 抽特征(grep test: `extract_visual_audit_path_v2(image_path, focus_xy=` 在 enumerate_objects 调用 ≥ 2 次) |
| 复用既有底座的"非声明而是实指"? | §3.3 visual_candidate 必须 channel_signature 含 "vision"(单测验);§4.3 R/A/P/F 与 saliency/attention_prior/cognitive_pressure/IOR 必须真对应 |
| Zvec 不会变 hidden classifier? | RL-19.9-Z03 红线 grep test;Z02 重建测;Z04 跨 source 测;Z06 fallback 测 |
| 12 张图测不到的边界? | **新增**多物体合成图测(真苹果+真香蕉+真橙子拼)— 这是 G3 列举能力的真测,12 张单主体测不到这能力 |

---

## 10. 三大目标举证总结

### G1 自由开放中文对话底座

**举证**:
- Phase 21 输出 ListOfObjects → Phase 16 styled corpus → "嗯,看到苹果。" — 接到 Phase 20 对话底座,用户提图就有反应
- 阶段 B 扫视调度复用 Phase 8/9/11 R/A/P/F + marker — 视觉注意力跟既有对话注意力**同一套机制**,这就是"自由开放" — 不分独立 image 系统
- Phase 19.9 Zvec 解决对话久了召回慢的问题

### G2 四大应用场景

**举证**:
- 桌宠:Phase 21 输出 + styled "嗯,看到了。"
- 老师/教练:数感接通(图里有 3 个) + 对应 Phase 13.x 课程教学已有
- 倾听者:Phase 9.6 共情已实现,Phase 21 给共情提供视觉输入语义
- 家庭助理:列表输出可直接"冰箱里有牛奶、面包、橙子"

### G3 短期图片内容认知

**举证**:
- Phase 21 阶段 A 解决"列举有什么"(不是单 label)
- 阶段 B 扫视根据 saliency / 意外 / 违和 / 运动 / 任务驱动 / 学到的 attention prior 选下一焦点 — 完全拟人
- 阶段 C 用 focus patch 抽特征 — 避开背景污染(实测当前 6-7/12 卡在背景污染)
- IOR 防重复;数感接通能数物体数量
- 期待 12 张单主体 ≥ 9/12 + 多物体合成图能列 ≥ 2/3 对象

---

## 11. 不再做的事(诚实承认)

- ❌ 继续在公式层调 noisy-OR / 拟人 Conf 阈值
- ❌ 继续扩 V0-V12 加新通道(V7/V10/V11 实测已经够)
- ❌ 继续在 clean cards 数据增强
- ❌ 让 AP 在没有用户教学时就达到识别正确率指标
- ❌ 把 Zvec 当 hidden classifier

这些都是已被实测证明无效的方向。

---

## 12. 银子老师拍板项

**问题 1**: 这套 Phase 21 (扫视 + 列举) + Phase 19.9 (Zvec) 方向是否对?

**问题 2**: 落地优先级:
- (推荐) Phase 21 立即开始 + Phase 19.9 平行接 → Phase 20 对话底座
- 或:Phase 19.9 先做 → Phase 21 → Phase 20

**问题 3**: 多物体合成图测试 — 我建议**银子老师自己拼几张**(真苹果 + 真香蕉 + 真橙子放一起拍 5-10 张),这比合成更真实

---

## 13. 署名

- 原架构设计:银子老师(笔名)
- Phase 21 + 19.9 设计:Claude (Anthropic) 在亲手读完底座盘点 + Codex 实测 9/4/6/7/8 后产出
- 落地:Codex 在通过对抗审查后实施

End of Phase 21 + 19.9 Design.
