# APV3.0 Phase 20.6 Design — Full AP Runtime Loop with Fast/Slow Memory, DraftGrid, Per-Tick Action Competition, Vision-While-Writing, and Workbench Faithful Mirror

Date: 2026-06-20
Author: Claude(架构),银子老师(风格定调与最终签收)
Status: 完整设计稿(替换 Phase 20.5 全部 a/b/c 子阶段;一次性落地)
Trigger:
1. 银子老师亲手在 20.5a 之后两次实测发现:tick 回放是假 / 内心画面是能量可视化不是反向重建 / 审计图是 turn 总量除以 N / 想法云无物理排斥 / 快慢记忆没真做 / 历史会话隐私栏是多余 / "命中教学"路径残留 / 右上角 ?~+! 死按钮 / 20.5b/c 全没做
2. 银子老师指出我之前漏了**整个快系统**(运动协调 / 后继增益 / 模仿抽象泛化)
3. 银子老师拍板:"OK,把这些落地成完整设计吧,记得不要有遗漏"
Final Goal:
- **G1** 自由开放中文对话底座(用户任意中文 + 图片 + 反馈)
- **G2** 四大场景 — 当前 Phase 20.6 主交付 = 前端网页 demo + agent tool
- **G3** 短期图片认知(扫视 + 边看边写)
- **G4** 教学生态(导入/导出/卸载)
- **G5(新)** AP-native 拟人主循环可视化(每 tick 独立竞争)
License intent: AGPL-3.0-or-later
Real name handling: 全文件 grep 真名 = 0

---

## 0. 这一份做什么(一句话)

把 Phase 20.0 / 20.1 / 20.2 / 20.3 / 20.4 / 20.5a / 20.5a2 / 20.5a3 留下的**所有"投影式 / 演示式 / 预先决定"假实现**全部拆掉,改成 **真 AP runtime 主循环** — 每个 tick 独立 action_competition、状态池真演化、Fast/Slow 两系统都经历 B/C 召回、DraftGrid 二维写入、边看边写边决策、未闭合任务可恢复 — 同时把 Web 工作台 8 面板改成这套真 runtime 的**忠实镜像**(不再有任何前端伪装),并把 20.5b/c 的主动停 / TTS / 画布 / 录音 / 教师辅助视焦点 / 竖式 一并落地,最终交付一个**可对外演示的 AP-native 中文对话底座**。

---

## 1. 设计原则(每条都对照最终目标)

| 原则 | 服务 G | Why |
|---|---|---|
| **每个 tick 独立 action_competition** 不预先决定整句 | G1, G5 | 银子老师明文:"我们真实 AP 是每个 tick 都会独立决策要做的事的" |
| **快/慢系统都经历 B/C 召回** 先快后慢 | G3, G5 | 银子老师明文:"快系统和慢系统不仅数据库不一样,里面储存的记忆也不一样,而且它们都能独立经历 B 和 C 过程来召回,先快后慢" |
| **快系统含模仿/抽象/泛化期** + 后继增益 | G3, G5 | 银子老师明文:"快系统也有后继增益,也是有模仿期,抽象期,泛化期等等学习的过程,包括动作的学习和练习也是如此" |
| **DraftGrid 二维写入** 不字符串拆字 | G1 | 复用既有 Phase 13 DraftGrid 实现,字逐 (row, col) 填,允许回看 / 改 / 插入 / 删 |
| **边看边写边决策** 不整图识别后再说 | G3 | 银子老师明文:"不能先整图识别,再让对话层拿标签填答案。视焦点移动 → 每 tick 采集局部 → 同步进行" |
| **未闭合恢复**(被打断 → 下次召回继续) | G1, G5 | 银子老师明文:"我们的真实 AP 即使流程被打断,也能通过未闭合感,召回我们还没做完的任务,然后继续把任务完成" |
| **教学不是独立模块** 只是共现源标记 | G4 | 不存在"命中教学记忆"路径 |
| **召回唯一一套算子** 教学 vs 自然对话不分支 | G4 | source 标记仅用于 v1e source-aware credit 反馈分摊 |
| **8 面板都是 RuntimeTickEvent 的视图** 不前端伪装 | G5 | Codex v1a §3 已锁,本设计稿继承 |
| **慢记忆持久化** 跨 turn 衰减 | G1, G5 | v1a §11 SlowMemoryStore 设计 |
| **画布走视觉,不识字** | G3 | v1a §13 红线 |
| **TTS = reply 朗读,不是 inner_voice** | G2 | v1a §4 红线 |
| **历史会话无隐私栏** | G1 | 银子老师明文:"我不要任何的历史隐私设计" |

---

## 2. 总架构(三层 + 一个主循环)

```
┌──────────────────────────────────────────────────────────────┐
│                       Web Workbench(纯视图层)                │
│  Panel 1-8 全部订阅 RuntimeTickEvent 流,无任何独立逻辑        │
└──────────────────────────────────────────────────────────────┘
                            ↑ subscribes
┌──────────────────────────────────────────────────────────────┐
│                    Phase 20.6 Turn Loop(主循环)              │
│                                                                │
│  while not finished and tick < TICK_BUDGET:                   │
│      tick += 1                                                 │
│      1. 状态池能量更新(R/A/P/F 衰减,未闭合保留)            │
│      2. 焦点采样(若有视觉输入,只采当前焦点局部)             │
│      3. Fast Recall (Fast-C → Fast-B)                         │
│      4. Slow Recall (Slow-C → Slow-B)若快放弃                │
│      5. Build action candidates(continue_draft / write_char  │
│         / move_focus / look_again_draft / edit_draft /       │
│         commit_reply / stop_generating / request_teacher /   │
│         idle)                                                 │
│      6. action_competition(Thompson sample)                  │
│      7. Execute chosen action(状态池真改)                    │
│      8. Emit RuntimeTickEvent(真数据,is_projection=False)    │
│  end while                                                     │
└──────────────────────────────────────────────────────────────┘
       ↑ uses                                       ↑ uses
┌──────────────────────────────┐         ┌────────────────────┐
│       Fast Memory System     │         │  Slow Memory System │
│  - FastActionChainStore      │         │  - sparse_pairwise  │
│  - 模仿/抽象/泛化期记录       │         │  - Layer-1/2/3      │
│  - 后继增益                   │         │  - Zvec recall      │
│  - 独立 SQLite               │         │  - cooccurrence     │
│  - Fast-C 倒排查情境          │         │  - Slow-C / Slow-B │
│  - Fast-B 链精算              │         │  - 后继增益(语义近邻)│
└──────────────────────────────┘         └────────────────────┘
       ↑ both observe                              ↑
┌──────────────────────────────────────────────────────────────┐
│                       State Pool(状态池)                     │
│  - 视觉 SA / 文本 SA / 听觉 SA / 草稿 SA / 内心画面 SA       │
│  - R/A/P/F 能量字段                                           │
│  - cognitive_pressure / unresolved_pressure                  │
│  - DraftGrid(二维 cells)                                     │
│  - SlowMemoryStore promote(高 A 跨 turn 持久化)             │
└──────────────────────────────────────────────────────────────┘
```

---

## 3. RuntimeTickEvent 数据结构(忠实记录每 tick 真相)

```python
@dataclass(frozen=True)
class RuntimeTickEvent:
    # 基本
    tick: int
    turn_id: str
    elapsed_ms: float                          # 本 tick 耗时(真测,非除N)
    is_projection: bool = False                # 永远 False(真 runtime)

    # 状态池快照(本 tick 演化后)
    state_pool_top12: tuple[StateItemSnapshot, ...]
    state_pool_size: int                       # 当前 SA 总数
    energy_R: float; energy_A: float; energy_P: float; energy_F: float
    cognitive_pressure: float
    unresolved_pressure: float                 # 未闭合任务的累积压力

    # 视觉焦点(若有视觉输入)
    focus_xy: tuple[int, int] | None
    focus_changed_this_tick: bool              # 上 tick → 本 tick 焦点是否变
    foveated_canvas_snapshot_hash: str | None  # 本 tick 累积的 canvas hash

    # 召回(Fast / Slow 双轨)
    fast_recall_attempts: int                  # Fast-C 候选数
    fast_recall_top1_score: float              # Fast-B 最高分
    fast_recall_used: bool                     # 本 tick 是否走快系统
    fast_recalled_chain_id: str | None
    slow_recall_attempts: int                  # Slow-C 候选数
    slow_recall_top1_score: float
    slow_recall_used: bool
    slow_recalled_sa_ids: tuple[str, ...]

    # action competition(本 tick 所有候选 + 选择)
    action_candidates: tuple[ActionCandidate, ...]   # 全部候选 + 各自分数
    action_chosen: ActionCandidate
    action_succession_bonus: float             # 来自上 tick 的后继增益

    # 执行结果
    draft_grid_changes: tuple[DraftCellChange, ...]  # 本 tick 改了哪些 cell
    draft_grid_snapshot_hash: str              # 本 tick 末 grid 状态 hash
    new_sa_injected: tuple[str, ...]           # 本 tick 注入的 SA id
    sa_promoted_to_slow_memory: tuple[str, ...]

    # 内心画面 / 内心音频(若有)
    inner_picture_canvas_png_hash: str | None
    inner_voice_sketch_wav_hash: str | None    # Phase 19.1 ON 才有

    # 想法云(中文化后的状态池可视化数据)
    thought_cloud_items: tuple[ThoughtCloudItem, ...]
```

**关键性质**:
- 8 个面板订阅本结构 → 都是同一 runtime 真实状态的视图
- is_projection 永远 False(假实现路径全删)
- 每 tick 独立数据(审计图能真展示每 tick 变化)

---

## 4. 主循环逐步设计(每 tick 完整流程)

### 4.1 Step 1 — 状态池能量更新

```python
def step_1_state_pool_evolve(state_pool, tick):
    """
    每 tick 独立演化,不预先决定。
    """
    # 1.1 R/A/P/F 衰减(继承 v14 能量公式)
    for item in state_pool.items.values():
        item.real_energy *= R_DECAY_SHORT       # 0.95
        item.attention_energy *= A_DECAY        # 0.88
        item.cognitive_pressure *= P_DECAY      # 0.95
        item.fatigue *= F_DECAY                 # 0.97
    
    # 1.2 未闭合任务保留(关键 — 银子老师明文)
    for item in state_pool.items.values():
        if item.unresolved_flag and item.cognitive_pressure < UNRESOLVED_PRESSURE_FLOOR:
            item.cognitive_pressure = UNRESOLVED_PRESSURE_FLOOR
            # 未闭合的任务不让 P 归零 → 下 tick 召回时它仍能脱颖而出
    
    # 1.3 删除低能量 SA(垃圾回收)
    state_pool.gc_low_energy_items()
```

### 4.2 Step 2 — 焦点采样(边看边写的核心)

```python
def step_2_focus_sample(state_pool, tick, current_image_path):
    """
    本 tick 只采一个焦点的局部。
    不一次性整图识别。
    """
    if not current_image_path:
        return
    
    # 2.1 当前焦点位置(由上 tick action 决定 / 默认中心)
    focus_xy = state_pool.current_focus_xy or default_focus(current_image_path)
    
    # 2.2 在 focus_xy 局部抽取(继承 Phase 21 v1b 真 local)
    local_trace = extract_visual_audit_path_v2_object_centric(
        current_image_path,
        candidate_bbox=focus_to_bbox(focus_xy, patch_size=64),
        tick=tick,
    )
    
    # 2.3 注入视觉 SA(只一个局部,不整图)
    state_pool.inject(StateItem(
        sa_id=f"vision_local::{local_trace.input_trace_hash}::{tick}",
        family="vision_local",
        channel_signature=("vision", "local_focus"),
        real_energy=local_trace.segmentation_confidence,
        metadata={"focus_xy": focus_xy, "trace": local_trace},
    ))
    
    # 2.4 SensoryCanvas 累积(v1c 设计真接通)
    state_pool.sensory_canvas.update_from_native_image(
        current_image_path,
        focus_xy=focus_xy,
        tick=tick,
    )
```

### 4.3 Step 3 — Fast Recall(Fast-C → Fast-B)

```python
def step_3_fast_recall(state_pool, last_action, tick) -> list[FastCandidate]:
    """
    快系统先召回(运动协调 / 已练习过的动作链)。
    先快后慢:若 Fast 找到高匹配 → 慢系统跳过。
    """
    # 3.1 Fast-C 粗召回(倒排索引)
    context_signature = compute_context_signature(state_pool, last_action)
    candidate_chains = fast_action_chain_store.recall_by_context(
        context_signature,
        top_k=int(load_constant("phase20_6.fast_recall_top_k")),  # 8 @experimental
    )
    
    if not candidate_chains:
        return []
    
    # 3.2 Fast-B 精算
    scored = []
    for chain in candidate_chains:
        # 当前状态池能量 × 链激活次数 × 后继增益
        score = (
            chain.context_match_score(state_pool)
            * sigmoid(chain.activation_count / 10)
            * chain.succession_bonus_from(last_action)
            * abstraction_match_score(chain, current_situation_specificity)
        )
        scored.append(FastCandidate(chain=chain, score=score))
    
    scored.sort(key=lambda c: c.score, reverse=True)
    return scored
```

### 4.4 Step 4 — Slow Recall(Fast 放弃后才走)

```python
def step_4_slow_recall(state_pool, fast_top_score, tick) -> list[SlowCandidate]:
    """
    Slow-C → Slow-B,继承 v1d 三层向量库 + 拟人 Conf。
    若 fast_top_score > FAST_THRESHOLD → 慢系统省略大部分计算
    (但仍保留低强度召回,作为 action_competition 的 backup 候选).
    """
    if fast_top_score > float(load_constant("phase20_6.fast_takeover_threshold")):  # 0.6
        # 慢系统仅做最小召回(背景候选)
        return slow_minimal_recall(state_pool)
    
    # 4.1 Slow-C 粗召回(走 Layer-2 倒排 + Zvec 加速)
    candidate_concepts = layer2.match_parts(state_pool.visual_signature) + \
                         layer3.lookup_by_parts(...)
    
    # 4.2 Slow-B 精算(Phase 19.2 拟人 Conf)
    scored = []
    for concept in candidate_concepts:
        conf = compute_humanlike_confidence(
            state_pool.visual_signature, concept,
            with_succession_bonus=True,    # 语义近邻加分
        )
        scored.append(SlowCandidate(concept=concept, confidence=conf))
    
    # 4.3 Slow 也召回 sparse_pairwise top partners(为文本生成提供候选 token)
    for sa_id in state_pool.high_attention_sa_ids():
        partners = sparse_pairwise.top_partners(sa_id, top_k=4)
        for partner in partners:
            scored.append(SlowCandidate(token_sa_id=partner.sa_id, confidence=partner.support))
    
    return scored
```

### 4.5 Step 5 — Build Action Candidates(9 种 action)

```python
ALL_ACTIONS_AT_TICK = (
    "continue_draft",      # 继续写下一字(不指定写啥,由 Fast/Slow 提供 token)
    "write_char",          # 在 DraftGrid 写一个具体字(参数: char, row, col)
    "move_focus",          # 移动视焦点到 (new_x, new_y)
    "look_again_draft",    # 回看草稿框某 (row, col),触发该 cell 周围 SA 重新活跃
    "edit_draft",          # 改 / 删 DraftGrid 某 cell
    "commit_reply",        # 把当前 DraftGrid 内容提交为回复
    "stop_generating",     # 主动停(不输出 / 输出空)
    "request_teacher",     # 反问("还要继续吗?")
    "idle",                # 不做事(状态池只衰减)
)

def step_5_build_action_candidates(state_pool, fast_candidates, slow_candidates, last_action, tick):
    """
    每 tick 完全重新算所有候选打分,无任何预先决定。
    """
    candidates = []
    
    # 5.1 Fast 候选转 action(运动协调链的下一步)
    for fc in fast_candidates:
        action = fc.chain.next_action_at_step(state_pool.fast_chain_progress)
        candidates.append(ActionCandidate(
            kind=action.kind,
            params=action.params,
            source="fast",
            score=fc.score + succession_bonus(last_action, action.kind),
        ))
    
    # 5.2 Slow 候选转 action
    for sc in slow_candidates:
        # 慢候选可能是 concept(填字)或 partner token(填字)或 candidate concept(continue think)
        if sc.token_sa_id:
            candidates.append(ActionCandidate(
                kind="write_char",
                params={"char": resolve_token_to_char(sc.token_sa_id),
                        "row": draft_grid.next_write_position()[0],
                        "col": draft_grid.next_write_position()[1]},
                source="slow",
                score=sc.confidence + slow_semantic_succession_bonus(last_action, sc.token_sa_id),
            ))
    
    # 5.3 内驱 action(总是参与竞争,不靠 Fast/Slow)
    candidates.extend(build_innate_action_candidates(state_pool, last_action, tick))
    # 包括:
    #   - commit_reply 候选:得分 = commit_readiness × draft_coherence
    #   - stop_generating:得分 = task_completion - unresolved_pressure  
    #   - request_teacher:得分 = ambiguity_count × CORRECTION_marker_intensity
    #   - move_focus:候选若干新焦点(saliency + uncertainty + IOR)
    #   - look_again_draft:得分 = NOVELTY_in_draft_neighborhood
    #   - edit_draft:得分 = MISMATCH_marker_intensity in draft area
    #   - idle:基线 0.1(永远存在但低)
    
    return candidates
```

### 4.6 Step 6 — Action Competition(Thompson Sampling)

```python
def step_6_action_competition(candidates, state_pool, tick) -> ActionCandidate:
    """
    继承 v14 action_competition + Thompson sampling.
    每候选独立抽样,选最高 sampled_score.
    """
    sampled = []
    for c in candidates:
        # 用既有 Phase 8 Thompson sampling 接口
        noisy_score = c.score + np.random.normal(0, c.uncertainty)
        sampled.append((c, noisy_score))
    
    sampled.sort(key=lambda x: x[1], reverse=True)
    chosen = sampled[0][0]
    
    # 记录所有候选(为 RuntimeTickEvent 提供完整 action_candidates 字段)
    return chosen, [c for c, _ in sampled]
```

### 4.7 Step 7 — Execute Chosen Action

```python
def step_7_execute(chosen, state_pool, draft_grid, image_path, tick):
    """
    执行选中动作 — 真的改状态池 / DraftGrid / focus。
    """
    if chosen.kind == "write_char":
        char = chosen.params["char"]
        row, col = chosen.params["row"], chosen.params["col"]
        draft_grid.write(char, row, col, tick=tick)
        # 注入 SA
        state_pool.inject(StateItem(
            sa_id=f"draft_cell::{tick}::{row}_{col}",
            family="draft_grid",
            channel_signature=("draft", "write"),
            real_energy=1.0,
            metadata={"char": char, "row": row, "col": col, "tick": tick},
        ))
    
    elif chosen.kind == "move_focus":
        new_focus = chosen.params["new_focus_xy"]
        state_pool.current_focus_xy = new_focus
        state_pool.mark_focus_changed(tick)
    
    elif chosen.kind == "look_again_draft":
        row, col = chosen.params["row"], chosen.params["col"]
        # 周围 SA 注意力 boost
        for sa_id, item in state_pool.items.items():
            if item.metadata.get("row") == row and item.metadata.get("col") in [col-1, col, col+1]:
                item.attention_energy += float(load_constant("phase20_6.look_again_boost"))
    
    elif chosen.kind == "edit_draft":
        row, col = chosen.params["row"], chosen.params["col"]
        new_char = chosen.params.get("char")  # None 表示删
        draft_grid.edit(row, col, new_char, tick=tick)
    
    elif chosen.kind == "commit_reply":
        reply_text = draft_grid.to_string()
        state_pool.commit(reply_text, tick)
        return CommitSignal()  # 标记 turn 结束
    
    elif chosen.kind == "stop_generating":
        state_pool.commit("", tick)  # 提交空回复
        return CommitSignal()
    
    elif chosen.kind == "request_teacher":
        state_pool.commit(_styled_question_from_corpus(), tick)
        return CommitSignal()
    
    elif chosen.kind == "continue_draft":
        # 没具体内容,只让 Fast/Slow 下 tick 继续给候选
        pass
    
    elif chosen.kind == "idle":
        pass
    
    # 学习反馈:Fast 系统记录这次 action 用了哪条链 → 后继增益累积
    fast_action_chain_store.observe_action_executed(chosen, tick, state_pool)
```

### 4.8 Step 8 — Emit RuntimeTickEvent

```python
def step_8_emit_event(state_pool, draft_grid, chosen, all_candidates, tick, elapsed_ms):
    """
    本 tick 真状态的完整快照。
    8 面板订阅这个流。
    """
    event = RuntimeTickEvent(
        tick=tick,
        turn_id=state_pool.current_turn_id,
        elapsed_ms=elapsed_ms,
        is_projection=False,  # 必须 False,grep test 防回归
        
        # 状态池
        state_pool_top12=state_pool.top_n_by_attention(12),
        state_pool_size=len(state_pool.items),
        energy_R=state_pool.aggregate_R(),
        energy_A=state_pool.aggregate_A(),
        energy_P=state_pool.aggregate_P(),
        energy_F=state_pool.aggregate_F(),
        cognitive_pressure=state_pool.aggregate_cognitive_pressure(),
        unresolved_pressure=state_pool.aggregate_unresolved_pressure(),
        
        # 焦点
        focus_xy=state_pool.current_focus_xy,
        focus_changed_this_tick=state_pool.focus_changed_in(tick),
        foveated_canvas_snapshot_hash=hash(state_pool.sensory_canvas.canvas_pixels.tobytes())[:16],
        
        # 召回
        fast_recall_attempts=...,
        fast_recall_top1_score=...,
        fast_recall_used=chosen.source == "fast",
        slow_recall_attempts=...,
        slow_recall_top1_score=...,
        slow_recall_used=chosen.source == "slow",
        
        # 动作
        action_candidates=tuple(all_candidates),  # 全部候选 + 各自分数
        action_chosen=chosen,
        action_succession_bonus=chosen.succession_bonus,
        
        # 执行结果
        draft_grid_changes=draft_grid.changes_this_tick(tick),
        draft_grid_snapshot_hash=draft_grid.snapshot_hash(),
        new_sa_injected=state_pool.new_sa_in(tick),
        sa_promoted_to_slow_memory=slow_memory_store.promoted_in(tick),
        
        # 内心画面(真反向重建)
        inner_picture_canvas_png_hash=R_sketch_render_and_hash(state_pool.sensory_canvas),
        inner_voice_sketch_wav_hash=None,  # Phase 19.1 未实施
        
        # 想法云(中文化的状态池可视化)
        thought_cloud_items=state_pool.to_thought_cloud_items(),
    )
    
    # 发布事件(web 工作台订阅 SSE / WebSocket)
    event_bus.publish(event)
    return event
```

### 4.9 Main Loop

```python
def phase20_6_turn(user_text, image_path, last_turn, *, runtime, tick_budget=200):
    """
    完整一次 turn — 真主循环。
    每 tick 独立竞争,无任何预先决定。
    """
    state_pool = runtime.state_pool
    draft_grid = runtime.draft_grid.reset_for_new_turn()
    
    # 注入用户输入 SA(只是输入,不预计算回复)
    state_pool.inject_user_text_sa(user_text, tick=0)
    if image_path:
        state_pool.inject_image_input_metadata(image_path, tick=0)
    
    # 未闭合任务恢复 — 上 turn 的未闭合 SA 仍在 state_pool 中(未被 gc)
    state_pool.activate_unresolved_from_previous_turn(last_turn)
    
    tick = 0
    last_action = None
    events = []
    last_commit_or_action_tick = 0
    
    while tick < tick_budget:
        tick += 1
        t0 = time.monotonic()
        
        # 1. 状态池能量
        step_1_state_pool_evolve(state_pool, tick)
        
        # 2. 焦点采样
        step_2_focus_sample(state_pool, tick, image_path)
        
        # 3. Fast Recall
        fast_candidates = step_3_fast_recall(state_pool, last_action, tick)
        
        # 4. Slow Recall (即使快有也跑最小,保证 backup)
        slow_candidates = step_4_slow_recall(
            state_pool,
            fast_top_score=fast_candidates[0].score if fast_candidates else 0.0,
            tick=tick,
        )
        
        # 5. Build candidates
        candidates = step_5_build_action_candidates(
            state_pool, fast_candidates, slow_candidates, last_action, tick
        )
        
        # 6. Action competition
        chosen, all_candidates = step_6_action_competition(candidates, state_pool, tick)
        
        # 7. Execute
        commit_signal = step_7_execute(chosen, state_pool, draft_grid, image_path, tick)
        
        # 8. Emit event
        elapsed_ms = (time.monotonic() - t0) * 1000
        event = step_8_emit_event(state_pool, draft_grid, chosen, all_candidates, tick, elapsed_ms)
        events.append(event)
        
        # 9. 慢系统持久化(每 tick 检查高注意力 SA 是否需要 promote)
        slow_memory_store.observe(tick, state_pool.items.values())
        
        # 10. 检查 commit / 强制停止条件
        if commit_signal:
            break
        if chosen.kind != "idle":
            last_commit_or_action_tick = tick
        # 银子老师明文:距离上次提交经过 N tick 还未提交也未主动停 → 强行停
        if tick - last_commit_or_action_tick > int(load_constant("phase20_6.idle_force_stop_ticks")):  # 30
            state_pool.commit(draft_grid.to_string() or "...", tick)
            break
        
        last_action = chosen
    
    # turn 结束 — 慢系统每 turn 衰减一次
    slow_memory_store.decay_step()
    
    return TurnResult(events=events, final_reply=state_pool.last_committed_reply)
```

---

## 5. 快系统(Fast System)— 全新模块

银子老师明文:"快系统是实现多个已经经历过的动作组合的流畅配合,也就是'运动协调'能力的关键,它也有后继增益,也是有模仿期,抽象期,泛化期等等学习的过程,包括动作的学习和练习也是如此。"

### 5.1 FastActionChainStore — 数据结构

```python
@dataclass(frozen=True)
class FastActionChain:
    chain_id: str                          # opaque uuid
    actions: tuple[ActionRecord, ...]      # 一串动作(2-N 步)
    learning_phase: str                    # imitation / abstract / generalized
    abstraction_level: float               # 0.0 完全具体 → 1.0 完全抽象
    activation_count: int                  # 被激活次数
    succession_strength: float             # 链内后继增益强度
    context_signature: bytes               # 触发该链的情境哈希
    source_event_uuid: str                 # 来源 event(teacher / natural / self_drive)
    last_used_tick: int
    decay_rate: float                      # 不用就衰减

@dataclass(frozen=True)
class ActionRecord:
    action_kind: str                       # write_char / move_focus / commit / ...
    action_params_abstract: dict           # 抽象后的 params(如 char_class="vocab_token")
    action_params_concrete: dict           # 当时具体执行的 params
```

### 5.2 三阶段学习

| 阶段 | abstraction_level | 触发 | 描述 |
|---|---|---|---|
| **模仿期** | 0.0 | 首次激活 | 完全具体记录,只能在完全相同情境复用 |
| **抽象期** | 0.5 | activation_count >= 3 | 某些参数变 class(如 char 抽象为 "任意 token"),情境签名也开始抽象 |
| **泛化期** | 1.0 | activation_count >= 10 + 跨多个情境激活成功 | 链结构保留,所有 params 都可填新内容 |

**升级触发**(`fast_system.observe_action_executed`):
- 每次成功激活 → activation_count += 1
- 满 3 次 → 自动升抽象期(部分参数抽象化)
- 满 10 次 + 跨 ≥ 3 个不同 context_signature 成功 → 升泛化期

### 5.3 Fast-C 粗召回(倒排索引)

```python
class FastActionChainStore:
    def __init__(self, sqlite_path):
        self.db = sqlite3.connect(sqlite_path)
        self._init_schema()  # tables: fast_action_chains, fast_action_records, fast_succession, fast_context_inverted_index
    
    def recall_by_context(self, context_signature: bytes, *, top_k=8) -> list[FastActionChain]:
        """
        Fast-C 粗召回 — 用 context_signature 倒排查最匹配的链。
        毫秒级。
        """
        # 用 MinHash / SimHash 做 context fuzzy match
        candidate_ids = self._inverted_index.query(context_signature, top_k=top_k * 3)
        chains = self.db.execute(
            "SELECT * FROM fast_action_chains WHERE chain_id IN (?)", candidate_ids
        ).fetchall()
        # Fast-C 不精算,只返回 top_k 个
        return chains[:top_k]
```

### 5.4 Fast-B 精算

```python
def fast_b_score(chain, state_pool, last_action) -> float:
    """
    在 Fast-C 召回的 top_k 链上精算。
    """
    # 1. 当前状态池与链情境的相似度
    context_match = cosine_similarity(
        compute_context_signature(state_pool, last_action),
        chain.context_signature
    )
    
    # 2. 链激活次数(熟练度)
    activation_score = sigmoid(chain.activation_count / 10)
    
    # 3. 后继增益(上 action 是否在链里 + 链里有没有后续)
    succession = chain.succession_bonus_from(last_action)
    
    # 4. 抽象度匹配(模仿期适合相同情境,泛化期可以新情境)
    abstraction_match = (
        1.0 if chain.learning_phase == "imitation" and context_match > 0.95 else
        0.7 if chain.learning_phase == "abstract" and context_match > 0.7 else
        0.5 if chain.learning_phase == "generalized" else
        0.3
    )
    
    # 5. 衰减(久不用)
    recency = exp(-(current_tick - chain.last_used_tick) / decay_tau)
    
    return context_match * activation_score * succession * abstraction_match * recency
```

### 5.5 模仿期学习 — 完整记录教师示范

```python
def observe_teacher_demonstration(turn_events: list[RuntimeTickEvent], *, source="teacher_event"):
    """
    教师完整演示一次 turn → 记录成完整动作链(模仿期 abstraction_level=0)。
    """
    actions_in_turn = [e.action_chosen for e in turn_events if e.action_chosen.kind != "idle"]
    if len(actions_in_turn) < 2:
        return  # 不形成链
    
    context_at_start = compute_context_signature_from_event(turn_events[0])
    
    chain = FastActionChain(
        chain_id=opaque_uuid(),
        actions=tuple(actions_in_turn),
        learning_phase="imitation",
        abstraction_level=0.0,
        activation_count=1,
        succession_strength=1.0,
        context_signature=context_at_start,
        source_event_uuid=source_event_uuid_from(source),
        last_used_tick=turn_events[-1].tick,
        decay_rate=0.99,
    )
    fast_action_chain_store.insert(chain)
```

### 5.6 抽象期学习 — 多次激活自动升级

```python
def maybe_promote_to_abstract(chain: FastActionChain):
    if chain.learning_phase == "imitation" and chain.activation_count >= 3:
        # 找该链多次激活时,哪些 params 在变,哪些不变
        param_variability = analyze_param_variability(chain.activation_history)
        # 变的 → 抽象为 class
        # 不变的 → 保留具体值
        new_actions = abstract_actions(chain.actions, param_variability)
        chain.learning_phase = "abstract"
        chain.abstraction_level = 0.5
        chain.actions = new_actions
```

### 5.7 泛化期学习 — 跨情境成功

```python
def maybe_promote_to_generalized(chain: FastActionChain):
    if chain.learning_phase == "abstract" \
       and chain.activation_count >= 10 \
       and chain.distinct_context_count >= 3:
        chain.learning_phase = "generalized"
        chain.abstraction_level = 1.0
        # 所有 params 都可填新内容,只保留链结构
        chain.actions = full_abstract_actions(chain.actions)
```

### 5.8 后继增益(链内 + 跨链)

```python
def succession_bonus(last_action: ActionCandidate, candidate_action_kind: str) -> float:
    """
    Fast 系统的后继增益:
    - 链内:已选了链 X 的 action 第 i 步,链 X 的 action 第 i+1 步在打分中 +α
    - 跨链:某 action 历史上经常跟在 last_action 后面 → +β
    """
    # 链内
    chain_internal_bonus = 0.0
    if last_action and last_action.source == "fast":
        chain = fast_action_chain_store.get(last_action.fast_chain_id)
        next_step = chain.next_step_after(last_action.step_index)
        if next_step and next_step.kind == candidate_action_kind:
            chain_internal_bonus = float(load_constant("phase20_6.fast_internal_succession_bonus"))  # 0.4
    
    # 跨链(从所有链统计 last_action.kind → candidate_action_kind 的频率)
    cross_chain_bonus = fast_action_chain_store.cross_chain_succession_prob(
        last_action.kind if last_action else None,
        candidate_action_kind,
    ) * float(load_constant("phase20_6.fast_cross_chain_bonus_scale"))  # 0.2
    
    return chain_internal_bonus + cross_chain_bonus
```

### 5.9 红线

```
RL-20.6-Fast-01: FastActionChainStore 独立 SQLite 表(fast_*),不混入 slow_memory / chat_session
RL-20.6-Fast-02: Fast-C / Fast-B 调用必须有 elapsed_ms 记录(Fast-C 应 < 5ms,Fast-B < 10ms × top_k)
RL-20.6-Fast-03: 模仿/抽象/泛化期升级必须 deterministic(同一历史输入产生同一升级)
RL-20.6-Fast-04: 链内 / 跨链后继增益必须可分别 audit
RL-20.6-Fast-05: 每 turn 衰减一次(防永久饱和)
```

---

## 6. 慢系统(Slow System)— 已有 + 补完

### 6.1 复用既有

- `sparse_pairwise.SparsePairwiseGraph`
- `CooccurrenceAssociationStore`
- Layer-1/2/3 (Phase 19.0b1)
- Zvec (Phase 19.9)
- `delta_p_cold_fork`

### 6.2 新增 SlowMemoryStore(v1a §11 真实施)

```python
class SlowMemoryStore:
    """跨 turn 持久化的高注意力 SA 累积 store。"""
    
    def observe(self, tick, state_items):
        """每 tick 调用,promote 高 attention_energy 的 SA 到长期表."""
        threshold = float(load_constant("slow_memory.promotion_threshold"))  # 0.6
        for item in state_items:
            if item.attention_energy > threshold:
                self._upsert(
                    sa_id=item.sa_id,
                    accumulated_attention=item.attention_energy,
                    last_seen_tick=tick,
                    family=item.family,
                    channel_signature=item.channel_signature,
                )
    
    def decay_step(self):
        """每 turn 衰减一次."""
        decay_rate = float(load_constant("slow_memory.decay_per_turn"))  # 0.95
        self.db.execute(
            "UPDATE slow_memory SET accumulated_attention = accumulated_attention * ?",
            (decay_rate,)
        )
    
    def top_n_persistent(self, n=12):
        """跨 turn 持久化 top-N."""
        return self.db.execute(
            "SELECT * FROM slow_memory ORDER BY accumulated_attention DESC LIMIT ?", (n,)
        ).fetchall()
```

### 6.3 慢系统后继增益(语义近邻)

```python
def slow_semantic_succession_bonus(last_action, candidate_token_sa_id) -> float:
    """
    慢系统后继增益 — 已召回某 concept 时,其语义近邻在下 tick 加分。
    """
    if not last_action or last_action.kind != "write_char":
        return 0.0
    
    last_token_sa_id = sparse_pairwise.find_sa_id_for_token(last_action.params.get("char"))
    if not last_token_sa_id:
        return 0.0
    
    partners = sparse_pairwise.top_partners(last_token_sa_id, top_k=10)
    for partner in partners:
        if partner.sa_id == candidate_token_sa_id:
            return partner.support * float(load_constant("phase20_6.slow_succession_scale"))  # 0.3
    return 0.0
```

### 6.4 Slow-C / Slow-B 显式接通

```python
def slow_c_recall(state_pool) -> list:
    """Slow-C 粗召回(C 召回)."""
    # 视觉走 Layer-2 part 倒排 → Layer-3 candidate concepts
    # 文本走 sparse_pairwise top_partners
    # 全部走 Zvec 加速召回
    ...

def slow_b_recall(state_pool, slow_c_candidates) -> list:
    """Slow-B 精算 — 走 Phase 19.2 拟人 Conf 公式 + 后继增益."""
    ...
```

---

## 7. DraftGrid 二维写入(复用 Phase 13 既有 + 接通 turn loop)

### 7.1 复用 Phase 13 既有

`apv3test/runtime/draft_grid.py` 已有 DraftGrid 实现。

### 7.2 接通

```python
class DraftGrid:
    def __init__(self, rows=10, cols=20):
        self.cells: dict[tuple[int, int], str] = {}
        self.tick_writes: dict[int, list[tuple[int, int, str]]] = {}
    
    def write(self, char, row, col, *, tick):
        old = self.cells.get((row, col))
        self.cells[(row, col)] = char
        self.tick_writes.setdefault(tick, []).append((row, col, char))
        return DraftCellChange(row, col, old, char, tick)
    
    def edit(self, row, col, new_char, *, tick):
        old = self.cells.get((row, col))
        if new_char is None:
            self.cells.pop((row, col), None)
        else:
            self.cells[(row, col)] = new_char
        self.tick_writes.setdefault(tick, []).append((row, col, new_char))
    
    def next_write_position(self) -> tuple[int, int]:
        """决定下一个写位置(行内填满换行)."""
        if not self.cells: return (0, 0)
        max_row = max(r for r, _ in self.cells)
        cols_in_row = [c for r, c in self.cells if r == max_row]
        if max(cols_in_row) >= self.cols - 1:
            return (max_row + 1, 0)
        return (max_row, max(cols_in_row) + 1)
    
    def to_string(self) -> str:
        """提交时 — 按行扁平化."""
        rows_used = sorted(set(r for r, _ in self.cells))
        out = []
        for r in rows_used:
            row_chars = [self.cells[(r, c)] for c in sorted(c for rr, c in self.cells if rr == r)]
            out.append("".join(row_chars))
        return "\n".join(out)
    
    def snapshot_hash(self) -> str:
        return sha256(str(sorted(self.cells.items())).encode()).hexdigest()[:16]
    
    def changes_this_tick(self, tick) -> tuple:
        return tuple(self.tick_writes.get(tick, []))
```

### 7.3 竖式支持(银子老师明文要)

竖式 = 多列对齐 + 进位逻辑。**这正是 Phase 13 DraftGrid 设计目的**。Phase 20.6 不重写,接通即可:
- 加法竖式:write_char 在多列对齐位置上写数字
- AP 自然通过看草稿(look_again_draft)累积进位

### 7.4 红线

```
RL-20.6-Draft-01: 提交回复必须从 DraftGrid.to_string() 拿,不允许从字符串拆字
RL-20.6-Draft-02: 每 tick write 必须经 DraftGrid.write,grep test 防回归
RL-20.6-Draft-03: turn 开始时 reset_for_new_turn(),旧 grid 不混
```

---

## 8. 边看边写边决策(Phase 21 真接通)

### 8.1 不再用 enumerate_objects_in_image

旧:`enumerate_objects_in_image()` 一次性识别所有候选 → 错。

新:turn loop 的 step 2(焦点采样)每 tick 只采一个焦点局部。识别和写字**同一个 action_competition 决定**。

### 8.2 焦点选择(move_focus action 的候选)

```python
def build_move_focus_candidates(state_pool, image_path) -> list[ActionCandidate]:
    """每 tick 计算多个移动焦点候选."""
    candidates = []
    
    # 候选 1: saliency 高的未注视过的点
    saliency_map = compute_saliency_map(image_path, state_pool.sensory_canvas)
    ior_mask = state_pool.ior_mask(image_path)  # 已注视过的位置
    top_saliency_pts = topk((1 - ior_mask) * saliency_map, k=5)
    
    for pt in top_saliency_pts:
        candidates.append(ActionCandidate(
            kind="move_focus",
            params={"new_focus_xy": pt},
            source="innate",
            score=saliency_map[pt] * float(load_constant("phase20_6.move_focus_saliency_weight")),
        ))
    
    # 候选 2: surprise(prediction overlay - sensory canvas 差大)
    surprise_pts = topk(state_pool.surprise_map(), k=3)
    for pt in surprise_pts:
        candidates.append(ActionCandidate(
            kind="move_focus",
            params={"new_focus_xy": pt},
            source="innate",
            score=state_pool.surprise_map()[pt] * 0.4,
        ))
    
    return candidates
```

### 8.3 红线

```
RL-20.6-Vision-01: turn loop 中不允许调用 enumerate_objects_in_image 整图函数
                    grep test: phase20_open_dialogue 不导入 enumerate_objects_in_image
RL-20.6-Vision-02: 视觉局部 SA 只通过 step_2_focus_sample 注入
RL-20.6-Vision-03: 内心画面 = R_sketch(state_pool.sensory_canvas) 真反向重建,
                    不允许从原图缩略图 / 能量可视化伪装
```

---

## 9. 未闭合恢复

### 9.1 未闭合 SA 的标记

```python
@dataclass
class UnresolvedSAFlag:
    unresolved_flag: bool = False
    unresolved_kind: str = ""        # "task_incomplete" / "question_unanswered" / "draft_unfinished"
    unresolved_since_tick: int = 0
    unresolved_carry_to_next_turn: bool = False
```

### 9.2 turn 结束时保留 unresolved

```python
def turn_end_cleanup(state_pool, last_event):
    if last_event.unresolved_pressure > float(load_constant("phase20_6.unresolved_carry_threshold")):  # 0.4
        # 留下未闭合 SA(衰减但不删)
        for item in state_pool.items.values():
            if item.unresolved_flag:
                item.unresolved_carry_to_next_turn = True
                # 跨 turn 衰减率比单 turn 慢
                item.cross_turn_decay_rate = 0.8
```

### 9.3 下 turn 开始时激活

```python
def activate_unresolved_from_previous_turn(state_pool, last_turn):
    if last_turn and last_turn.has_unresolved:
        for item in last_turn.unresolved_items:
            # 注入到当前 state_pool,attention_energy 设为继承值的 0.5
            state_pool.inject(item.refresh(
                attention_energy=item.attention_energy * 0.5,
                tick=0,
            ))
```

### 9.4 多任务被打断的恢复 demo

银子老师明文提:"多物体被干扰后,能否继续任务的设计"。

实测场景:
```
Turn 1: 用户传图(图里苹果+橙子+香蕉)说"列举一下"
   AP turn loop:
     tick 1-5: 看苹果区,写"嗯,苹果。"
     tick 6: 用户突然打断说"等下,这个香蕉是哪种?"
     → tick 7: 状态池注入用户新打断的 SA + 标记原任务"列举"为 unresolved
     tick 8-15: AP 回答"嗯,看着是黄香蕉。"提交
   turn 1 commit "嗯,苹果。嗯,看着是黄香蕉。"
   状态池保留 unresolved("列举还有橙子没说")

Turn 2: 用户说"嗯"(承接)
   tick 1: 状态池激活上 turn 未闭合 SA → 高 unresolved_pressure
   tick 2-N: action_competition 选 move_focus 到橙子区
   tick N+1: write_char("嗯,橙子。") 提交
```

### 9.5 红线

```
RL-20.6-Unresolved-01: turn 结束 cleanup 时,unresolved SA 必须保留到下 turn
RL-20.6-Unresolved-02: 下 turn 开始时必须激活上 turn 未闭合 SA
RL-20.6-Unresolved-03: 未闭合 SA 必须能审计(在 RuntimeTickEvent.unresolved_pressure 字段可见)
```

---

## 10. 教学 = 共现 + Fast 链记录(双轨)

### 10.1 慢系统侧(教学 = 共现源标记)

```python
def observe_teacher_text_correction(last_turn, correction_text, *, sparse_graph):
    """
    用户教"那应该说 XXX"
    1. 解析 correction_text → text token SA
    2. 当时状态池的视觉/上下文 SA 与新 token SA 共现 +1
    3. source 标 "teacher_event"(用于反馈分摊,不分支召回)
    """
    last_state_pool_snapshot = last_turn.state_pool_top12
    correction_tokens = tokenize(correction_text)
    
    for snap_sa in last_state_pool_snapshot:
        for token in correction_tokens:
            sparse_graph.observe_pair(
                snap_sa.sa_id,
                f"text_token::{token_hash(token)}",
                packet_key=f"teacher_event::{turn_id}",
            )
```

### 10.2 快系统侧(教学 = 完整动作链记录)

如果用户教学是完整 turn 示范("从头到尾这种情况下,你应该这样回"),那是 §5.5 `observe_teacher_demonstration` → 完整记成模仿期动作链。

### 10.3 没有"命中教学记忆"路径

```
RL-20.6-Teaching-01: grep test:不允许出现 "命中教学" / "teaching_hit" / "taught_reply" 
                     字符串在 phase20_open_dialogue / web_chat 任何路径
RL-20.6-Teaching-02: 召回时 source 标记仅用于反馈分摊,不分支召回流
RL-20.6-Teaching-03: Phase 20.0/20.1/20.2/20.3 留下的 PHASE20_1_TEACHING_SCHEMA_ID 
                     等独立教学 schema 完全删除(不只 deprecated)
```

---

## 11. Web 工作台 8 面板(纯视图层)

### 11.1 面板布局(银子老师调整后)

```
┌──────────────────────────────────────────────────────────────────────┐
│  Header: APV3 中文对话工作台                          [设置] [调试]   │
├──────────┬───────────────────────────────────────────┬───────────────┤
│          │  Panel 1 聊天气泡区                       │ Panel 6       │
│ 左栏:    │  ┌──────────────────────────────────┐    │ 记忆          │
│ 历史会话 │  │ 用户: 你好                        │    │  - 快记忆     │
│ (列表)   │  │ AP:   嗯,你好。                  │    │    list      │
│          │  │ 用户: [上传图] 这是啥?            │    │  - 慢记忆     │
│ - 12:34  │  │ AP:   嗯,看到苹果。…还有橙子?    │    │    list      │
│   12 turn│  │ 用户: 那是橙子,不是苹果           │    │  - R_sketch   │
│ - 13:01  │  │ AP:   嗯,我错了。                │    │    缩略图     │
│   8 turn │  └──────────────────────────────────┘    │               │
│ - 当前   │                                            ├───────────────┤
│          │  Panel 7 DraftGrid 二维(本 turn)         │ Panel 8       │
│          │  ┌──────────────────────────────────┐    │ 包生态        │
│          │  │ . . . . . . . . . . . . . . . .  │    │  导入/导出/   │
│          │  │ . . . . . . . . . . . . . . . .  │    │  卸载/搜索    │
│          │  │ 嗯 , 看 到 苹 果 。 . . . . .    │    │               │
│          │  │ . . . . . . . . . . . . . . . .  │    │               │
│          │  └──────────────────────────────────┘    │               │
│          ├───────────────────────────────────────────┤               │
│          │  输入框 + [图文] [发送] [教学]           │               │
└──────────┴───────────────────────────────────────────┴───────────────┘
┌──────────────────────────────────────────────────────────────────────┐
│  Panel 2  Tick Progress: tick 12 / 30   [◀ ▶ ⏸]                     │
│  Tick: ─────────●────────────────────                                 │
├──────────────────────────────────────────────────────────────────────┤
│ Panel 3 能量折线│ Panel 4 内心画面 │ Panel 5 想法云                  │
│ R/A/P/F 4 线   │ R_sketch 渲染    │ force-directed 物理排斥         │
│ 一图多线        │ + 焦点 marker    │ 中文化 + 显置信                 │
├──────────────────────────────────────────────────────────────────────┤
│ Panel 9 (审计) 多图各自独立 + 一图多线                                │
│  - 每 tick 耗时(分过程)       - 状态池规模 / 能量 / draft 长度       │
│  - Fast vs Slow 召回次数        - action 候选分数对比                │
│  - 未闭合压力曲线              - 后继增益激活次数                    │
└──────────────────────────────────────────────────────────────────────┘
```

### 11.2 各面板数据来源(全部 RuntimeTickEvent)

| 面板 | 数据 |
|---|---|
| Panel 1 聊天气泡 | TurnResult.final_reply + 图片缩略 + ObjectFile chip |
| Panel 2 Tick 进度条 | TurnResult.events 流(可拖动到任意 tick)|
| Panel 3 R/A/P/F 折线 | events[i].energy_R/A/P/F(每 tick 一点,4 线一图)|
| Panel 4 内心画面 | events[i].foveated_canvas_snapshot_hash → 渲染 → PNG 显示 + events[i].focus_xy marker |
| Panel 5 想法云 | events[i].thought_cloud_items 中文化 + force-directed 布局 |
| Panel 6 快慢记忆 | FastActionChainStore.top_n + SlowMemoryStore.top_n_persistent |
| Panel 7 DraftGrid | events[i].draft_grid_snapshot 渲染二维 cells |
| Panel 8 包生态 | 既有 Phase 20.3 记忆包 API |
| Panel 9 审计 | events 数组 → 多个独立指标的折线图 |

### 11.3 历史会话(左栏)

银子老师明文:"我不要任何的历史隐私设计"

```python
@dataclass
class SessionListItem:
    session_id: str
    started_at: str
    turn_count: int
    last_reply_preview: str    # 最后一轮 reply 前 20 字(用户自己机器上,不上传)
```

点击切换 → 加载该 session 的 RuntimeTickEvent 流 → Panel 2-7 全部回放该 session。

### 11.4 右上角设置/调试

替换原来的死按钮 ?~+!:
- **[设置]**:TTS 开关 / Lucide icons / 字体大小 / 历史保留天数
- **[调试]**:开启后 Panel 6 显示 raw sa_id 折叠层

### 11.5 输入区(银子老师明文调整)

```
┌──── 输入区(更大,排版稳定)──────────────────────┐
│  [输入中文]                                       │
│  ─────────────────────────────────────            │
│  [📷 选图]  [🎤 录音]  [🎨 画布]  [拖框引导焦点]   │
│  缩略图:                                         │
│   ┌──┐                                            │
│   │  │ 真实苹果1.jpeg                             │
│   └──┘                                            │
│                                                    │
│  [发送]  [纠正/教学]                              │
│   - 发送:    把上面内容作为新一轮用户输入        │
│   - 纠正/教学: 针对上一轮 AP 回应,教它该怎么说   │
│                                                    │
└────────────────────────────────────────────────────┘
```

每按钮配 tooltip 说明。图标用 Lucide outline(v1a §10)。

### 11.6 红线

```
RL-20.6-UI-01: 任何面板显示 tick 数据必须读 is_projection,True 时显示"⚠ 展示投影"
RL-20.6-UI-02: 用户可见 UI 不显示裸 sa_id(grep DOM)
RL-20.6-UI-03: emoji 仅作 decoration,主图标用 Lucide
RL-20.6-UI-04: 不存在历史隐私栏
RL-20.6-UI-05: 输入框不能因为输入长文本而排版爆炸(autosize textarea)
RL-20.6-UI-06: Panel 1 聊天气泡显示原文(当前 session),后端 SQLite 默认不长存原文(继承 v14)
RL-20.6-UI-07: 不存在"命中教学记忆"/ "Phase20 · 命中教学" 等字样
```

---

## 12. 内心画面真反向重建(v1c R_sketch 真接通)

### 12.1 v1c R_sketch 已设计但未真用

旧 Phase 20.5a3 把"状态池视觉 SA 画成能量层"伪装内心画面。错。

### 12.2 真实施

```python
def render_inner_picture(state_pool, tick) -> bytes:
    """
    用 v1c R_sketch 算子真反向重建。
    输入: state_pool.sensory_canvas(累积 N tick foveated patches)
    输出: PNG bytes
    """
    canvas = state_pool.sensory_canvas
    sketch_image = R_sketch(canvas, target_size=128)
    
    # 加焦点 marker
    sketch_image = annotate_focus_marker(
        sketch_image,
        focus_xy=state_pool.current_focus_xy,
    )
    
    return png_bytes(sketch_image)
```

### 12.3 红线

```
RL-20.6-Inner-01: render_inner_picture 必须调 R_sketch 算子(grep test)
RL-20.6-Inner-02: 不允许把原图直接缩略图作为内心画面
RL-20.6-Inner-03: 不允许把能量可视化作为内心画面
RL-20.6-Inner-04: Phase 19.1 听觉未实施时,inner_voice_sketch = None,UI 显"听觉感受器尚未启用"
```

---

## 13. 扩展能力(20.5b/c 一并实施)

### 13.1 主动停 stop_generating

走 §4.5 action_competition 候选。**不绑"完了" token**(v1a §2)。

### 13.2 TTS reply 朗读

```python
def synthesize_reply_tts(reply_text: str, *, voice_profile="xiaomo_default") -> bytes:
    """pyttsx3 离线 TTS,默认关."""
    import pyttsx3
    engine = pyttsx3.init()
    engine.setProperty('voice', voice_profile)
    engine.setProperty('rate', 150)
    return engine.save_to_bytes(reply_text)
```

红线:
- `RL-20.6-TTS-01`: pyttsx3 本地,不调 Edge / Google / OpenAI TTS
- `RL-20.6-TTS-02`: reply_tts_audio 与 inner_voice_sketch 完全分离(v1a §4)

### 13.3 画布

```python
class UserCanvasInput:
    canvas_png_bytes: bytes
    processing_tier: str = "visual_audit_via_phase21"
```

走 Phase 21 视觉路径,不识字(v1a §13)。

### 13.4 录音

```python
class UserAudioInput:
    audio_bytes: bytes
    processing_tier: str = "audio_audit_only"   # 默认
```

仅波形显示 + 存 hash,UI 显 banner(v1a §5)。

### 13.5 教师辅助视焦点

用户拖框 → `teacher_guided_focus_candidates`(opaque uuid,无 label),saliency boost 0.3(v1a §6)。

### 13.6 竖式

已在 §7.3 DraftGrid 二维结构里支持。

---

## 14. 删除清单(必须清掉的旧代码 / 旧路径)

| 旧物 | 删 / 改 |
|---|---|
| `PHASE20_1_TEACHING_SCHEMA_ID` 独立 schema | **删**(不只 deprecated)|
| `phase20_teaching_paradigms` SQLite 表 | **删** |
| "命中教学记忆" 任何字样(UI / 后端) | **删** |
| "Phase20 · 命中教学" UI | **删** |
| 旧 `_diagnostic_fixation_log` prose 装饰 | **删**(若 Phase 21 还有残留)|
| 旧 `workbench_tick_trace` projection 路径 | **删** |
| 把 reply_text 拆字模拟 tick 的代码 | **删** |
| 整图识别 `enumerate_objects_in_image` 在 phase20 路径的调用 | **删** |
| 右上角 ?~+! 按钮 | **删** |
| 历史会话隐私栏 | **删** |
| `inner_picture = 能量可视化` 假实现 | **删** |
| `audit_chart_data = turn_total / N` 假数据 | **删** |
| Phase 20.0/20.1/20.2/20.3 留下的所有"label 表 / 教学映射表"残留 | **全删** |

---

## 15. Deliverable Gates(35 条)

### 15.1 真主循环(8)
| Gate |
|---|
| G-20.6-Loop-01 turn loop 每 tick 独立 action_competition,无任何预先决定 |
| G-20.6-Loop-02 每 tick emit RuntimeTickEvent,is_projection 永远 False |
| G-20.6-Loop-03 单测:同一输入跑两次,action_chosen 由 Thompson sampling 引入随机性(不 deterministic 同答案,但 deterministic seed 可复现)|
| G-20.6-Loop-04 单测:tick > 30 idle 强制停 |
| G-20.6-Loop-05 turn 结束 cleanup 保留未闭合 SA |
| G-20.6-Loop-06 下 turn 激活上 turn 未闭合 SA |
| G-20.6-Loop-07 多任务打断恢复 demo(§9.4 场景)单测 |
| G-20.6-Loop-08 全 turn 期间不调用 enumerate_objects_in_image |

### 15.2 快系统(6)
| Gate |
|---|
| G-20.6-Fast-01 FastActionChainStore + 独立 SQLite 表 |
| G-20.6-Fast-02 Fast-C 倒排索引 < 5ms |
| G-20.6-Fast-03 Fast-B 精算 < 10ms × top_k |
| G-20.6-Fast-04 模仿期 → 抽象期 → 泛化期 升级 deterministic(单测)|
| G-20.6-Fast-05 链内 + 跨链后继增益分别可 audit |
| G-20.6-Fast-06 每 turn 衰减一次 |

### 15.3 慢系统(4)
| Gate |
|---|
| G-20.6-Slow-01 SlowMemoryStore 独立 SQLite 表 + 跨 turn 持久 |
| G-20.6-Slow-02 Slow-C / Slow-B 显式接通 |
| G-20.6-Slow-03 慢系统语义近邻后继增益 |
| G-20.6-Slow-04 Zvec 召回与 brute-force 一致(继承 Phase 19.9)|

### 15.4 DraftGrid(3)
| Gate |
|---|
| G-20.6-Draft-01 二维 grid 写入,提交从 to_string 拿 |
| G-20.6-Draft-02 竖式 demo:加法 12+34 用 DraftGrid 列对齐 |
| G-20.6-Draft-03 每 tick draft_grid_changes 真记录 |

### 15.5 视觉接通(3)
| Gate |
|---|
| G-20.6-Vision-01 视觉局部 SA 仅经 step_2_focus_sample |
| G-20.6-Vision-02 内心画面 = R_sketch 真重建(不能像 / 不能能量)|
| G-20.6-Vision-03 多对象图扫视:tick 流可见焦点跨 ≥ 2 个对象 |

### 15.6 教学红线(3)
| Gate |
|---|
| G-20.6-Teaching-01 grep 0 命中"命中教学" / "teaching_hit" / "taught_reply" |
| G-20.6-Teaching-02 PHASE20_1_TEACHING_SCHEMA_ID 完全删除 |
| G-20.6-Teaching-03 召回唯一一套,无分支(grep test)|

### 15.7 UI 工作台(5)
| Gate |
|---|
| G-20.6-UI-01 8 面板全部订阅 RuntimeTickEvent,无前端独立逻辑 |
| G-20.6-UI-02 Panel 1 聊天显示原文(当前 session)|
| G-20.6-UI-03 Panel 3 R/A/P/F 一图四线,每 tick 一点 |
| G-20.6-UI-04 Panel 4 真 R_sketch,焦点 marker |
| G-20.6-UI-05 Panel 5 force-directed 物理排斥 |

### 15.8 扩展能力(3)
| Gate |
|---|
| G-20.6-Ext-01 主动停 / TTS / 画布 / 录音 / 教师辅助视焦点 / 竖式 全部 demo 跑通 |
| G-20.6-Ext-02 reply_tts_audio 与 inner_voice_sketch 完全分离 |
| G-20.6-Ext-03 画布走视觉路径,grep 禁 OCR(pytesseract / easyocr / paddleocr)|

---

## 16. 落地分解(10 天 一次性 全做完才交)

| 天 | 工作 |
|---|---|
| **Day 1** | 删除清单 §14 全部清理 + grep test 防回归;改 web_chat / phase20_open_dialogue 入口接 turn loop 骨架 |
| **Day 2** | turn loop §4 主框架(8 step)+ RuntimeTickEvent + state_pool 演化 + 焦点采样 step 2 |
| **Day 3** | Fast System §5 全实施:FastActionChainStore + Fast-C + Fast-B + 模仿期记录 + 单测 |
| **Day 4** | Fast 抽象期/泛化期升级 + 后继增益 + Slow System §6 SlowMemoryStore + Slow-C/B + 语义近邻 |
| **Day 5** | action_competition §4.6 + 9 个 action 候选生成 + DraftGrid §7 接通 + 竖式 demo |
| **Day 6** | 边看边写 §8 + 未闭合恢复 §9 + 多任务打断 demo |
| **Day 7** | 教学路径整改 §10 + 共现接通 + 删 PHASE20_1 残留;v1c R_sketch §12 真接通 |
| **Day 8** | UI Workbench §11 8 面板真接 + 历史会话列表 + 删隐私栏 / 死按钮 / 改输入区 |
| **Day 9** | 扩展能力 §13:TTS / 画布 / 录音 / 教师辅助 / Panel 8 包生态完善 |
| **Day 10** | 35 Gate 全部跑通 + Final Report + 展示页 + 银子老师端到端实测演示 |

**关键**:**10 天连续做完才交**,不再分 5a/5b/5c 让您验收。

---

## 17. 给最终目标的对应

| 目标 | Phase 20.6 怎么交付 |
|---|---|
| **G1 自由开放中文对话** | 真 turn loop + 每 tick 独立 + 共现教学 + 自然对话同一召回 |
| **G2 四大场景** | 网页 demo + agent tool(同既有,但 turn loop 真,可对外演示)|
| **G3 短期图片认知** | 边看边写,扫视多对象,DraftGrid 列举 |
| **G4 教学生态** | 共现源标记 + 包导入导出(Phase 20.3 既有,改完整)|
| **G5 AP-native 主循环可视化** | 8 面板都是 RuntimeTickEvent 视图,无任何前端伪装 |

---

## 18. 红线汇总(全本设计稿)

| 红线 ID | 描述 |
|---|---|
| RL-20.6-Loop-01 | 每 tick 独立 action_competition,无预先决定 reply |
| RL-20.6-Loop-02 | RuntimeTickEvent.is_projection 永远 False |
| RL-20.6-Fast-01 | FastActionChainStore 独立 SQLite,不混 slow |
| RL-20.6-Fast-04 | 模仿/抽象/泛化期升级 deterministic |
| RL-20.6-Slow-01 | SlowMemoryStore 独立 SQLite + 跨 turn 持久 |
| RL-20.6-Draft-01 | reply 从 DraftGrid.to_string,不字符串拆字 |
| RL-20.6-Vision-01 | 不调 enumerate_objects_in_image |
| RL-20.6-Vision-02 | R_sketch 必接 v1c 算子 |
| RL-20.6-Unresolved-01 | 未闭合 SA 跨 turn 保留 |
| RL-20.6-Teaching-01 | grep 0 "命中教学"等字样 |
| RL-20.6-Teaching-02 | PHASE20_1_TEACHING_SCHEMA_ID 完全删 |
| RL-20.6-Teaching-03 | 召回唯一一套,无分支 |
| RL-20.6-UI-04 | 不存在历史隐私栏 |
| RL-20.6-UI-07 | 不存在"命中教学"字样 |
| RL-20.6-Inner-01 | 内心画面真 R_sketch |
| RL-20.6-Inner-02 | 不能拿原图缩略图 |
| RL-20.6-Inner-03 | 不能拿能量可视化 |
| RL-20.6-TTS-01 | pyttsx3 本地,不调外部 TTS |
| RL-20.6-TTS-02 | reply_tts_audio 与 inner_voice_sketch 完全分离 |
| RL-20.6-Canvas-01 | 画布走 Phase 21 视觉,grep 禁 OCR |
| 真名 0 命中 | 全文件 grep 王嘉豪 / wangjiahao |

---

## 19. 银子老师拍板项

1. **10 天一次性做完**(不再分 a/b/c 让您验收):同意吗?
2. **35 Gate 全部必过才能交**(不再"先跑通底座再补 UI"):同意吗?
3. **G-20.6-Loop-07 多任务打断恢复 demo** — 您给一个 5 turn 真场景,我让 Codex 写进 unit test 防回归?
4. **快系统 SQLite 路径** 默认 `data/fast_memory.sqlite`,您 OK 吗?

---

## 20. 署名

- 原架构设计:银子老师(笔名)
- Phase 20.6 完整设计:Claude (Anthropic) 在银子老师两次实测发现假实现 + 明文指出漏了快系统 + "OK 落地成完整设计,记得不要有遗漏"决策下产出
- 落地:Codex 在 v1 通过对抗审查后,10 天一次性实施

End of Phase 20.6 Design.
