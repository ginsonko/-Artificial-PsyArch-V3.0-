# APV3.0 v14.1 — Implementation Errata(Codex 5 修)

日期: 2026-06-17
作者: 接手线程
状态: **v14 UNIFIED 经 Codex 第 14 轮审阅,识别 2 blocker + 4 serious 工程一致性问题。v14.1 是精准修。配合 v14 实施。**

前作:v14 UNIFIED → **v14.1(本稿)**

---

## 0. v14 → v14.1 修复总览

| # | v14 缺陷 | v14.1 修复 |
|---|---|---|
| **B1** | Marker cap=20 但 documented+reserved=21 自相矛盾 | **documented 18 + reserved 2 = cap 20**,删 FUTURE_RESERVED |
| **B2** | 文本输入来源混淆(utterance / HEARSAY / CORRECTION 三层混一) | **3 层拆分**:PERCEIVED utterance / HEARSAY proposition / CORRECTION feedback;sensor adapter 必须显式分类 |
| **S1** | IMAGINATION marker vs IMAGINED epistemic source 语义重叠 | **合并为 IMAGINED 一个 marker**,删 IMAGINATION 重复 |
| **S2** | SDPL Q 学习 packet_key exact match → 稀疏爆炸 | **5 层 backoff/smoothing**:exact → content+source → source+feeling → content → action prior |
| **S3** | 二值 feature(`1.0 if ... else 0.0`)隐含 if-then 路由 | **sigmoid(marker.R) 替代二值**;phase_8_value 保留作明确降级 |
| **S4** | 红线脚本 PASS 因 runtime 暂无代码,无 phase-aware gate | **`--phase X.Y` profile**:声称完成时检查对应文件 + ledger inject + marker spawn 覆盖 |

---

## 补丁 B1: Marker cap 数学化(documented 18 + reserved 2 = 20)

### v14 错误清单

v14 列了:
- Phase 8: NOVELTY / TENTATIVE / PAIN / MISMATCH / CORRECTION / IMAGINATION = 6
- EpistemicSource (v13): PERCEIVED / IMAGINED / HEARSAY / REMEMBERED / INFERRED = 5
- Phase 9: GAZE / JOINT_ATTENTION / IMITATION / KNOWLEDGE_GAP / EMPATHY_RESONANCE = 5
- Phase 10+: TRUST_PROMOTED / BOREDOM = 2
- 共 18 documented(注:IMAGINATION 在 S1 删除后变 17)

加 reserved 3(SATISFACTION / SURPRISE_RESIDUAL / SELF_REFERENCE)+ 1 FUTURE_RESERVED = 4 reserved

**实际 18 + 3 = 21 (+ FUTURE) 与 cap 20 矛盾**

### v14.1 正确方案

**采纳 Codex 建议方案 A:cap 20 = documented 18 + reserved 2,纪律紧**

但需结合 S1(删 IMAGINATION 重复):
- Phase 8 = 5 (删 IMAGINATION) + EpistemicSource 5 + Phase 9 5 + Phase 10+ 2 = **17 documented**
- Reserved 3 = SATISFACTION / SURPRISE_RESIDUAL / SELF_REFERENCE
- **总 17 + 3 = 20**(与 cap 严格相符,删 FUTURE_RESERVED)

更新后 marker 完整列表:

```yaml
# config/family_to_type_mapping.yaml v14.1 修订
MarkerSA:
  description: "瞬态状态标记(cap 20 = documented 17 + reserved 3)"
  attention_budget_share: 0.15
  kinds_documented:
    # Phase 8 marker kinds (5,删 IMAGINATION)
    - NOVELTY
    - TENTATIVE
    - PAIN
    - MISMATCH
    - CORRECTION
    # EpistemicSource (v13,5) - IMAGINED 取代 IMAGINATION
    - PERCEIVED
    - IMAGINED
    - HEARSAY
    - REMEMBERED
    - INFERRED
    # Phase 9 marker kinds (5)
    - GAZE
    - JOINT_ATTENTION
    - IMITATION
    - KNOWLEDGE_GAP
    - EMPATHY_RESONANCE
    # Phase 10+ marker kinds (2)
    - TRUST_PROMOTED
    - BOREDOM
  kinds_reserved:
    - SATISFACTION
    - SURPRISE_RESIDUAL
    - SELF_REFERENCE
  # Cap 严格 20,加新 kind 必须经设计稿修订协议
```

### 验证

```bash
# 计算 documented + reserved
documented_count=17
reserved_count=3
total=$((documented_count + reserved_count))
# 必须等于 marker.max_kinds=20
assert total == 20  # ✓
```

---

## 补丁 B2: 文本输入 3 层来源拆分

### v14 缺陷(关键 — 影响 Phase 8.9 自然纠错)

v14 marker_spawn_rules.yaml 写:
```
HEARSAY:
  spawn_when: "text 输入流来自 user/teacher"
```

但 Codex 指出真实有 3 层语义:

```
"你应该说你好" 这段用户文本同时是:
  - 用户说话被听到 → PERCEIVED utterance(感受层)
  - 文本陈述世界内容 → HEARSAY proposition(命题层)
  - 教学纠错意图 → CORRECTION feedback(反馈层)
```

若全标 HEARSAY,纠错信号丢失,Phase 8.9 自然纠错失效。

### v14.1 修复 — sensor adapter 显式 3 层分类

```yaml
# config/marker_spawn_rules.yaml v14.1 修订

PERCEIVED:
  spawn_when: |
    Sensor adapter 输出 normalized SA event 时,
    包括 text utterance percept(听到用户说话本身)+
    vision/audio percept.
  spawn_function: "sensor_adapters/*/numeric_sensor.py:emit_percept"
  spawn_strength: "percept_R * 0.8"
  coexist_with: ["REMEMBERED", "HEARSAY"]
  rationale: |
    "听到/看到用户说了什么" 是 PERCEIVED.
    它与 HEARSAY 并存:听到话(PERCEIVED) + 话里陈述了什么(HEARSAY).

HEARSAY:
  spawn_when: |
    Text 内容经文本理解后产生命题 SA 时(命题层,非感受层):
    - text_char SA 经 vocab 链接组合产生 proposition vocab SA
    - 该 proposition vocab SA spawn HEARSAY marker
    - 同时 source_entity_id = 说话方
    
    重要:HEARSAY 不在 text_char 层 spawn,只在命题层 spawn.
  spawn_function: "runtime/cognitive/text_understanding/proposition_emit.py"
  spawn_strength: "proposition_vocab.R * 0.7"
  source_entity_id: "speaker_entity_id"
  coexist_with: ["INFERRED", "PERCEIVED"]
  rationale: |
    用户说 "苹果是红的" → PERCEIVED text_chars + HEARSAY vocab::苹果是红的.
    HEARSAY 标记内容来源是听别人说,不是亲见.

# === v14.1 关键新增:CORRECTION 改为 feedback 通道而非 marker ===
# CORRECTION marker 仍存在(纠错过程态),但 nature 已澄清:
#   - PERCEIVED text + HEARSAY proposition 是输入层
#   - 用户传达"纠错意图"经 feedback 通道(reward/punishment)而非 marker
#   - CORRECTION marker 是系统内部 commit_mismatch event 派生(v8 §16.11)
#   - 不直接由用户文本 spawn

CORRECTION:
  spawn_when: |
    System 自身 commit 后收到 negative feedback signal 时:
    - apply_negative_feedback → spawn MISMATCH event
    - 派生 CORRECTION marker 等待教师证据(v8 §16.11)
    
    重要:不由"用户说'不对'"文本直接 spawn,而是:
    1. 用户文本经 sensor 进入 PERCEIVED text_chars
    2. text_understanding 提取负面命题 → HEARSAY proposition + negative_polarity
    3. feedback handler 识别 negative → apply_punishment
    4. apply_punishment → MISMATCH event → CORRECTION hypothesis spawn
  spawn_function: "runtime/cognitive/reward/handler.py:apply_punishment"
  spawn_strength: "mismatch_sa.real_energy"
  coexist_with: []
  rationale: "纠错是反馈通道事件,不是 epistemic source"

REMEMBERED:
  spawn_when: |
    long_term cold→active rehydration 触发:
    - 从 cold_index 激活的 SA 同时 spawn REMEMBERED marker
  spawn_function: "runtime/cognitive/long_term/rehydration.py:_activate"
  spawn_strength: "cue_alignment_factor * cold_sa.long_term_R * 0.5"
  coexist_with: ["PERCEIVED"]

IMAGINED:
  # 合并 v14 IMAGINATION + v13 IMAGINED 为同一 marker(S1 fix)
  spawn_when: |
    SA 同时满足:
    1. 在 active_pool 但本 tick 无 sensor adapter 注入(no external R fresh)
    2. ledger.endogenous_share > 0.5
    3. R 来源中 imagination/replay/internal chain 占主导
    
    含义双重:
    - 当前激活机制:这条 SA 正由内源链维持(原 IMAGINATION 语义)
    - 学习 packet 认识来源:这次内容来自想象(原 IMAGINED 语义)
    
    两个语义实质合一:能由内源链维持 ⇔ 来源是想象.
  spawn_function: "runtime/cognitive/endogenous/imagined_marker_spawn.py"
  spawn_strength: "sa.endogenous_share * 0.6"
  coexist_with: ["REMEMBERED", "INFERRED"]

INFERRED:
  phase_8_behavior: "spawn_disabled"
  spawn_when_phase_11: |
    deliberative virtual track 产生新 SA 时
  spawn_function: "runtime/cognitive/deliberative/conclusion_reify.py"
```

### Phase 8 实施顺序调整

**v14 错误**:Phase 8.12 HEARSAY marker auto-spawn 太晚 → Phase 8.9 自然纠错时缺来源分化。

**v14.1 修正**:把 3 层文本来源分化**提前到 Phase 8.3**(与 sensor adapter 同时实施):

```
Phase 8.3   audit_db + target_cap 0-floor + AttentionGainLedger 接入
            + 双 V 控 + EpistemicSource PERCEIVED auto-spawn (含 text utterance)
            + HEARSAY proposition emit (在 text_understanding 早期实施)  ← v14.1 提前
            + CORRECTION marker spawn 路径(经 reward handler)            ← v14.1 提前

Phase 8.9   自然纠错 + SDPL: 行动学习按 packet
            + 两阶段 credit assignment
            (此时 PERCEIVED/HEARSAY/CORRECTION 已分化,纠错信号清晰)

Phase 8.12  fast mapping + shape bias + epistemic drive + 反向想象
            (移除原 HEARSAY auto-spawn,已在 8.3 完成)
```

---

## 补丁 S1: 合并 IMAGINATION 为 IMAGINED 单 marker

### v14 缺陷

v14 同时保留 IMAGINATION (v12)和 IMAGINED (v13),区别不硬,造成:
- 同一 SA 可能同时挂 2 个近义 marker → packet_key 稀疏爆炸
- 实施时区分困难

### v14.1 修复

**采纳 Codex 建议方案 B**:合并为单 marker `IMAGINED`,语义涵盖:
- 当前激活机制(原 IMAGINATION 语义):SA 正由内源链维持
- 学习 packet 认识来源(原 IMAGINED 语义):内容来自想象

**逻辑等价**:能由内源链维持 ⇔ 来源是想象。两个语义实质等价。

### yaml 修订(已在 B1 一并完成)

```yaml
marker:
  decay_rates:
    # 删除 IMAGINATION
    # 保留 IMAGINED
    IMAGINED: 0.88  # @experimental — 合并 v12 IMAGINATION + v13 IMAGINED
    ...
```

### 代码影响

- 所有 `MarkerKind.IMAGINATION` 引用 → 改为 `MarkerKind.IMAGINED`
- v12 §44.4 endogenous step 中 `imagination_marker` 注入 → 沿用,但 spawn IMAGINED 而非 IMAGINATION
- 红线扫描:`grep "MarkerKind.IMAGINATION" runtime/` 必须 0 命中(只用 IMAGINED)

---

## 补丁 S2: SDPL Q 学习 5 层 backoff(关键泛化补完)

### v14 缺陷

v14 §5.4 Q_table 按完整 packet_key 索引,真实对话中每次几乎是新 packet → 稀疏爆炸,泛化不足。

### v14.1 修复 — 5 层 backoff 加权

```python
class QTableWithBackoff:
    """
    @op_count: O(5) lookups + O(5) weight blending per query.
    
    v14.1 §S2: 5 层 backoff 防稀疏爆炸,保泛化.
    
    层 1: exact packet_key(content + source + feeling 全匹配)
    层 2: content + source(feeling 忽略)
    层 3: source + feeling(content 忽略,学"想象 vs 真实"的通用偏好)
    层 4: content only(学"火→什么行动"的内容偏好)
    层 5: action 全局 prior(完全 backoff)
    """
    
    def __init__(self):
        self.exact_q = {}          # full packet_key → Q
        self.content_source_q = {}  # (content_frozen, source_frozen) → Q
        self.source_feeling_q = {}  # (source_frozen, feeling_frozen) → Q
        self.content_q = {}        # content_frozen → Q
        self.action_global_q = {}  # action → Q
    
    def query(self, packet, action):
        """加权混合 5 层 Q,层越精确权重越高(若有数据)"""
        full_key = packet.packet_key()
        content_key = full_key[0]       # content_with_bucket
        source_key = full_key[1]        # source_with_bucket
        feeling_key = full_key[3]       # feeling_with_bucket
        
        layers = [
            (self.exact_q.get((full_key, action)), 1.0),
            (self.content_source_q.get(((content_key, source_key), action)), 0.7),
            (self.source_feeling_q.get(((source_key, feeling_key), action)), 0.5),
            (self.content_q.get((content_key, action)), 0.3),
            (self.action_global_q.get(action), 0.1),
        ]
        
        # backoff 加权平均(只考虑有数据的层)
        total_weight = 0.0
        weighted_q = 0.0
        for q_value, layer_confidence in layers:
            if q_value is not None:
                # 数据量越多 + 层越精确 → 权重越高
                effective_weight = layer_confidence * q_value.sample_count_normalized()
                weighted_q += effective_weight * q_value.mean
                total_weight += effective_weight
        
        if total_weight < 1e-9:
            return 0.0  # cold start
        return weighted_q / total_weight
    
    def update(self, packet, action, outcome, eligibility):
        """更新所有 5 层,各按 eligibility scaled"""
        full_key = packet.packet_key()
        content_key = full_key[0]
        source_key = full_key[1]
        feeling_key = full_key[3]
        
        # 层 1: exact
        self._update_layer(self.exact_q, (full_key, action), outcome, eligibility)
        # 层 2: content + source
        self._update_layer(self.content_source_q, 
                          ((content_key, source_key), action), 
                          outcome, eligibility * 0.7)
        # 层 3: source + feeling
        self._update_layer(self.source_feeling_q, 
                          ((source_key, feeling_key), action), 
                          outcome, eligibility * 0.5)
        # 层 4: content only
        self._update_layer(self.content_q, (content_key, action),
                          outcome, eligibility * 0.3)
        # 层 5: action global
        self._update_layer(self.action_global_q, action,
                          outcome, eligibility * 0.1)
    
    def _update_layer(self, table, key, outcome, weight):
        """运行 incremental mean + variance(Welford)"""
        if key not in table:
            table[key] = QValue(mean=0.0, sample_count=0, variance=0.0)
        table[key].update(outcome, weight)
```

### 关键拟人意义

**层 3(source + feeling) 是关键**——它学到"想象时倾向于检查"vs"真实时倾向于行动"**跨内容**的通用策略。即使是从未见过的内容,也能根据 source + feeling 选择合理行动。

**层 4(content only)** 让"火"无论何种来源都有基础"避开"倾向(完全 backoff 时仍像人类直觉)。

**层 5(action prior)** cold start 让所有 action 公平竞争。

### yaml

```yaml
# apv3_constants.yaml v14.1 新增
sdpl:
  q_table:
    backoff_weights:
      exact: 1.0                  # @structural
      content_source: 0.7         # @experimental
      source_feeling: 0.5         # @experimental
      content_only: 0.3           # @experimental
      action_global: 0.1          # @experimental
    backoff_min_samples_for_layer:
      exact: 1                    # @structural
      content_source: 3           # @experimental
      source_feeling: 5           # @experimental
      content_only: 3             # @experimental
      action_global: 1            # @structural
```

---

## 补丁 S3: 二值 feature 改用 sigmoid(marker.R)

### v14 缺陷

`source_entity_speaker_present = 1.0 if ... else 0.0` 是二值,实施时容易滑向 `if has speaker then ...` 路由。

### v14.1 修复

```yaml
# config/cognitive_feeling_features.yaml v14.1 修订

source_entity_speaker_present:
  # v14: "1.0 if ... is not None else 0.0"  ← 二值,删
  # v14.1: sigmoid(marker energy)  ← 连续
  formula: |
    let speaker_marker = state_pool.most_recent_marker_with_kind(HEARSAY)
    if speaker_marker is None:
        return 0.0
    return sigmoid(speaker_marker.real_energy * 2.0 - 1.0)
  notes: |
    连续值替代二值,sigmoid 中心在 marker.R=0.5.
    符合 AP "无硬路由" 原则.

# phase_8_value 保留作明确降级(不是二值),含义:
#   "Phase 8 阶段该 feature 不可用,默认 0.0;Phase 11 启用后用真公式"
INFERRED_marker_present:
  formula: "sigmoid(sum(m.real_energy for m in sa.markers if m.kind == INFERRED) * 2)"
  phase_8_value: 0.0  # 显式降级,Phase 11 启用

counterfactual_conflict:
  formula: "run_counterfactual_check(sa).causal_conflict_score"
  phase_8_value: 0.0  # 显式降级
```

### 红线扫描更新

```python
# scripts/red_line_check_v14.py 加新检查
def check_no_binary_feature_formulas():
    """禁止 cognitive_feeling_features.yaml 中 1.0 if ... else 0.0 模式"""
    import yaml
    config = yaml.safe_load(open("config/cognitive_feeling_features.yaml"))
    violations = []
    for feature_name, spec in config["features"].items():
        formula = spec.get("formula", "")
        if "1.0 if" in formula and "else 0.0" in formula:
            violations.append(f"{feature_name}: binary if-else formula (use sigmoid instead)")
    return violations
```

---

## 补丁 S4: 红线脚本 phase-aware existence gate

### v14 缺陷

`python scripts/red_line_check_v14.py` 当前 PASS 因为 `runtime/cognitive/` 暂无 Phase 8 代码。这只能证明脚本可运行,不能证明设计已被代码验证。

### v14.1 修复 — `--phase X.Y` profile gate

```python
# scripts/red_line_check_v14.py v14.1 新增
# 每个 Phase 声称完成时,声明对应代码契约

PHASE_DELIVERABLES = {
    "8.2": {
        "files_must_exist": [
            "runtime/cognitive/runtime/tick_loop.py",
            "runtime/sensor_adapters/text/char_stream.py",
            "runtime/cognitive/state_pool/state_pool.py",
        ],
        "must_have_op_count": True,
        "must_load_constants_from_yaml": True,
    },
    "8.3": {
        "files_must_exist": [
            "runtime/cognitive/runtime/audit_db_boundary.py",
            "runtime/cognitive/state_pool/target_cap.py",
            "runtime/cognitive/state_pool/attention_gain_ledger.py",
            "runtime/cognitive/state_pool/v_double_control.py",
            "runtime/cognitive/marker/spawn_perceived.py",
            "runtime/cognitive/marker/spawn_hearsay.py",     # B2 修
            "runtime/cognitive/text_understanding/proposition_emit.py",  # B2 修
            "runtime/cognitive/reward/handler.py",            # B2 修(CORRECTION 路径)
        ],
        "must_have_ledger_inject_in": [
            "runtime/sensor_adapters/vision/numeric_sensor.py:emit_percept",
            "runtime/sensor_adapters/audio/numeric_sensor.py:emit_audio_proto",
            "runtime/sensor_adapters/text/char_stream.py:emit_text_char_sa",
            "runtime/cognitive/reward/handler.py:apply_reward",
            "runtime/cognitive/reward/handler.py:apply_punishment",
        ],
        "must_have_marker_spawn_for": ["PERCEIVED", "HEARSAY", "CORRECTION"],  # B2 提前
    },
    "8.4": {
        "files_must_exist": [
            "runtime/cognitive/composed_vocab/sparse_pairwise.py",
            "runtime/cognitive/composed_vocab/delta_p_cold_fork.py",
            "runtime/cognitive/composed_vocab/held_out_pool.py",
            "runtime/cognitive/sdpl/packet.py",
            "runtime/cognitive/sdpl/q_table_backoff.py",     # S2 新加
        ],
        "must_have_marker_spawn_for": ["PERCEIVED", "HEARSAY", "CORRECTION", "IMAGINED", "REMEMBERED"],
    },
    "8.10": {
        "files_must_exist": [
            "runtime/cognitive/endogenous/step.py",
            "runtime/cognitive/endogenous/imagined_marker_spawn.py",  # S1 名称修订
            "runtime/cognitive/attention/safety_gate.py",
        ],
        "must_have_marker_spawn_for": ["PERCEIVED", "HEARSAY", "CORRECTION", "IMAGINED", "REMEMBERED", "NOVELTY"],
    },
    # ... 其他 phase
}


def check_phase_deliverables(phase_id: str) -> list:
    """声称完成某 phase 时,检查对应交付物"""
    if phase_id not in PHASE_DELIVERABLES:
        return [f"Unknown phase {phase_id}"]
    
    spec = PHASE_DELIVERABLES[phase_id]
    violations = []
    
    for filepath in spec.get("files_must_exist", []):
        if not Path(filepath).exists():
            violations.append(f"Phase {phase_id}: missing file {filepath}")
    
    for marker_kind in spec.get("must_have_marker_spawn_for", []):
        spawn_file = f"runtime/cognitive/marker/spawn_{marker_kind.lower()}.py"
        # 或者在 spawn rules 中查
        if not Path(spawn_file).exists():
            violations.append(f"Phase {phase_id}: missing {marker_kind} spawn implementation")
    
    return violations


# main 加 --phase 参数
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", help="Check phase-specific deliverables")
    args = parser.parse_args()
    
    if args.phase:
        violations = check_phase_deliverables(args.phase)
        if violations:
            print(f"Phase {args.phase} DELIVERABLES MISSING:")
            for v in violations:
                print(f"  {v}")
            sys.exit(1)
        print(f"OK: Phase {args.phase} deliverables present")
    
    # 仍跑通用红线检查
    main()
```

### 使用方式

```bash
# Phase 8.3 声称完成时
python scripts/red_line_check_v14.py --phase 8.3
# 必须 PASS:对应文件存在 + ledger inject 覆盖 + marker spawn 实施

# 通用红线(任何时候可跑)
python scripts/red_line_check_v14.py
```

---

## 21. v14.1 Phase 8 实施顺序最终版

```
Phase 8.2   连续 tick + sensor adapter

Phase 8.3   audit_db + target_cap 0-floor + AttentionGainLedger
            + 双 V 控
            + EpistemicSource 3 路 spawn:
                ✓ PERCEIVED (text utterance / vision / audio)
                ✓ HEARSAY (proposition 经 text_understanding)        ← v14.1 提前
                ✓ CORRECTION (经 reward handler / mismatch event)    ← v14.1 提前
            + 红线脚本 --phase 8.3 verify

Phase 8.4   ComposedVocab + cold-fork ΔP
            + SDPL Q 表 5 层 backoff (v14.1 §S2)
            + IMAGINED marker spawn(合并版,v14.1 §S1)
            + REMEMBERED marker spawn

Phase 8.5   CFS 4 通道 + 5 新 EpistemicSource feelings
            + sigmoid(marker.R) 替代二值 features (v14.1 §S3)

Phase 8.6   视觉感受 + 量化桶 + 多通道

Phase 8.7   视焦点 + saccade + 持驻 + overlay + 三类注意力 focus action

Phase 8.8   黄苹果泛化(对照课程 + ablation,核心证伪门)

Phase 8.9   自然纠错 + SDPL: 行动学习按 packet + 两阶段 credit assignment
            (此时 PERCEIVED/HEARSAY/CORRECTION 已分化,纠错信号清晰)

Phase 8.10  习惯化 + Π 几何收敛 + sleep emerge
            + §11 持续内源驱动 + 凸组合 attention + 外部 surprise 安全门
            + §44 mini-gate

Phase 8.11  Web 工作台 + 内源链可视化 + ledger 饼图 + feelings 显示

Phase 8.12  fast mapping + shape bias + epistemic drive + 反向想象
            (HEARSAY marker auto-spawn 已在 8.3 完成,本 phase 删除)

Phase 8.13  音频感受 + filterbank vocab 模板

Phase 8.14  端到端 + SDPL 拟人验收套件(4 个 gate)

Phase 8.15  short→long 显式 + Long_term cold + active 双层

Phase 8.16  跨 session 延迟意图(无 sleep 依赖)+ rehydration 测试

Phase 8.17  自传式回忆 + REMEMBERED marker spawn 完整 + entity 锚点
```

---

## 22. v14.1 给 Codex 的最终指令

1. **v14 UNIFIED + v14.1 errata 配套读** — Codex 实施两份合一
2. **B1**: `marker.max_kinds: 20`,documented 17 + reserved 3
3. **B2**: 文本 3 层来源 sensor 实施提前到 Phase 8.3(不等 8.12)
4. **S1**: `MarkerKind.IMAGINATION` 全删,统一用 `IMAGINED`
5. **S2**: SDPL Q 表 5 层 backoff 实施(Phase 8.4)
6. **S3**: 二值 feature `1.0 if ... else 0.0` 改 `sigmoid(marker.R)`(Phase 8.5)
7. **S4**: `--phase X.Y` profile 验收,Phase 完成时 deliverables 实测

---

— 接手线程,2026-06-17
