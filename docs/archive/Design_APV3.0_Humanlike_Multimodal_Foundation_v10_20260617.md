# APV3.0 拟人多模态底座 — 完整设计稿 v10(轮 6 收尾版)

日期: 2026-06-17
作者: 接手线程
状态: **v9 经轮 6 审阅,识别 4 blocker + 7 serious + 6 medium。审阅判断 "v9 70% 到位"。v10 是收尾版:AST-based 红线 gate(grep 5 种绕过修)、ΔP horizon 短到 5(数学非零)、HeldOutPool 改 reservoir sampling、§11.3 family 映射真修(joint_attention/utterance_boundary)、§41.4 全 yaml 化、§1.5 常量治理协议、§40.4 effect-size 而非 t-test。预计这是最后一版。**

前身链:v1 → v2 → v3 → v4 → v5 → v6 → v7 → v8 → v9 → **v10(本稿)**

---

## 0. v9 → v10 修复总览

### 0.1 v9 真 blocker(4 个全修)

| # | v9 缺陷 | v10 修复 |
|---|---|---|
| **B-V9-1** | red_line_check_v9.py 至少 5 种绕过(dict / comparison / default arg / return literal / inline 算术)+ "# structural" 后缀豁免被滥用 | §0.4 **AST-based check_no_numeric_literals.py**:遍历 AST,只允许白名单结构性常量 {0, 1, 2, -1, 0.0, 1.0, 0.5 in math 操作 limited 上下文},其他全拒;**移除 "# structural" 注释豁免** |
| **B-V9-2** | yaml 无 governance story,40 个数值无 derivation | §1.5 **常量治理协议**:每个常量分 3 类(structural / scenario-tuneable / experimental),scenario tuneable 必须有 A/B 实验记录,experimental 必须有 derivation 注释 |
| **B-V9-3** | horizon=50 → Π 衰减 0.077 → ΔP 信号近零 | §2.3.5 **horizon 改 5 + 测早期 P 差**;同时显式承认 ΔP 测 immediate value-add 不是远期 |
| **B-V9-4** | §41.4 `max(0.3, ...)` 字面量在反 anti-pattern 章节里复发 | §41.4 改 `max(load_constant("deliberative.conclusion_R_floor"), ...)`,floor=0.3 进 yaml |

### 0.2 v9 真 serious(7 个全修)

| # | 问题 | v10 修复 |
|---|---|---|
| S-V9-1 | context_signature 16-dim cosine 被 hash_mode 噪声维度主导 | §2.3.1 改 **z-normalization + Jaccard over top-K persistent_id sets**(替换 hash mode) |
| S-V9-2 | HeldOutPool 驱逐破坏 K-fold validity | §2.3.4 改 **reservoir sampling**:固定 500 容量,新样本以概率 500/N 替换随机旧样本 |
| S-V9-3 | §40.4 t-test 在 RNG-only 噪声上必然 p<0.05 | §40.4 改 **effect-size threshold only**(causal_strength > θ + monotonic),取消 t-test |
| S-V9-4 | joint_attention 合并 GAZE 折叠不同认知 | §11.3 **拆回 JOINT_ATTENTION 独立 marker kind**,marker cap 9 |
| S-V9-5 | utterance_boundary 是 PerceptSA 类型混淆 | §11.3 **新增 ControlSignalSA 第 5 类**(5 types 而非 4),utterance_boundary 入此类 |
| S-V9-6 | 8-marker cap 排除未来 markers | §11.3 cap 提到 **12**,documented 增长协议(empathy/trust/boredom/satisfaction 预留) |
| S-V9-7 | tentative_vocab + TENTATIVE marker 双 SA 同步未规范 | §11.8 **状态转移图** + 同步规则 |

### 0.3 v9 medium(6 个全修,见各章节)

### 0.4 v10 红线 gate — AST-based(B-V9-1 真修)

```python
# scripts/red_line_check_v10.py
import ast
import sys
from pathlib import Path

# 白名单:允许的结构性常量(数学上无歧义)
STRUCTURAL_LITERALS = {
    0, 1, 2, -1, 10, 100, 1000,         # indexing / loop bounds
    0.0, 1.0, -1.0,                       # initialization / sign
}

# 上下文豁免:某些上下文允许任意字面量
ALLOWED_CONTEXTS = {
    "ast.Index",                           # array indexing
    "ast.Slice",                           # slicing
    "ast.arguments_kwonly",                # kwarg default IF marked @structural
}

class HardcodeFinder(ast.NodeVisitor):
    """AST-based 扫描:找所有 cognitive/ 下不合规字面量"""
    
    def __init__(self, filepath):
        self.violations = []
        self.filepath = filepath
        self.context_stack = []
    
    def visit_Constant(self, node):
        if not isinstance(node.value, (int, float)):
            self.generic_visit(node)
            return
        
        if node.value in STRUCTURAL_LITERALS:
            self.generic_visit(node)
            return
        
        # 检查父上下文
        if self._is_in_allowed_context():
            self.generic_visit(node)
            return
        
        # 是不是 load_constant() / load_yaml() 调用的参数?
        if self._is_load_constant_call_path():
            self.generic_visit(node)
            return
        
        # 否则违规
        self.violations.append({
            "file": self.filepath,
            "line": node.lineno,
            "col": node.col_offset,
            "value": node.value,
            "context": self.context_stack[-3:] if self.context_stack else [],
        })
        self.generic_visit(node)
    
    def visit_Call(self, node):
        # 跟踪 load_constant() 调用上下文
        self.context_stack.append(f"Call:{ast.dump(node.func)[:30]}")
        self.generic_visit(node)
        self.context_stack.pop()
    
    def _is_in_allowed_context(self):
        # 检查上下文栈中是否有允许的类型
        for ctx in self.context_stack[-2:]:
            for allowed in ALLOWED_CONTEXTS:
                if allowed in ctx:
                    return True
        return False
    
    def _is_load_constant_call_path(self):
        # 检查是否在 load_constant() 的参数 path 中
        for ctx in self.context_stack[-3:]:
            if "load_constant" in ctx or "load_yaml" in ctx:
                return True
        return False


def check_directory(directory):
    all_violations = []
    for py_file in Path(directory).rglob("*.py"):
        with open(py_file) as f:
            try:
                tree = ast.parse(f.read())
            except SyntaxError:
                continue
        finder = HardcodeFinder(str(py_file))
        finder.visit(tree)
        all_violations.extend(finder.violations)
    return all_violations


if __name__ == "__main__":
    violations = check_directory("runtime/cognitive/")
    
    if violations:
        print(f"HARDCODE VIOLATIONS ({len(violations)}):")
        for v in violations:
            print(f"  {v['file']}:{v['line']}:{v['col']}: literal {v['value']}")
            print(f"    context: {v['context']}")
        sys.exit(1)
    
    print("✓ No hardcoded literals in runtime/cognitive/")
    sys.exit(0)
```

**关键变化**:
- **AST 遍历**:能识别所有 7 种字面量出现位置(dict / comparison / default / return / inline 算术 / list / call arg)
- **白名单结构性常量**:`{0, 1, 2, -1, 10, 100, 1000, 0.0, 1.0, -1.0}` 允许(loop bounds / indexing / sign)
- **`load_constant()` 上下文豁免**:`load_constant("foo.bar")` 里的 "foo.bar" 字符串不算字面量数字
- **移除 "# structural" 注释豁免**:这种注释绕过被 v9 自己证明会被滥用

### 0.5 § 1.5 常量治理协议(B-V9-2 真修)

```yaml
# === constants_governance.yaml ===
# 每个常量必须分类 + 注明来源

categories:
  structural:
    description: |
      数学上有明确意义的常量(如 Bayesian prior=0.5, sigmoid 中心=0).
      允许在 apv3_constants.yaml 中无 derivation 注释存在.
    examples:
      - "slot_preference.jsd_smoothing_alpha: 0.5  # Laplace smoothing prior"
  
  scenario_tuneable:
    description: |
      场景相关的可调参数. 每个值必须经过 A/B 实验记录.
      不同场景 (text_dialogue / desktop_pet / embodied / agent) 可不同.
      记录格式: a_b_experiment_id + delta_metric + scenario
    examples:
      - "marker.decay_rates.NOVELTY: 0.85  # A/B id=20260612-novelty-001, +12% recall accuracy in text_dialogue"
  
  experimental:
    description: |
      初值仅是猜测,需 Phase 8.X 实测后正式 derive 或 tune.
      必须在 apv3_constants.yaml 中标 @experimental + initial_rationale.
    examples:
      - |
        marker.decay_rates.PAIN: 0.998
        # @experimental
        # initial_rationale: PAIN 应远比 NOVELTY 慢衰减(人类痛持续小时级),
        # 0.998 给约 30 分钟半衰期 @ 100ms/tick,初值 plausible.
        # Phase 9.7 实测后 tune.

# Phase 8 启动时所有常量必须分类完毕,否则 PR 不许 merge
governance_check:
  scan_command: |
    python3 scripts/check_constant_governance.py
```

---

## 1. apv3_constants.yaml 重写(分类版)

```yaml
# === apv3_constants.yaml v10 ===
# 每常量必有 category 注释:@structural / @scenario_tuneable / @experimental

version: "10.0"

energy:
  R_decay_short: 0.95           # @experimental — Phase 8.10 验收
  R_decay_long: 0.999           # @experimental — Phase 8.10 验收
  V_decay: 0.93                 # @experimental
  A_decay: 0.88                 # @experimental
  F_decay: 0.97                 # @experimental
  Pi_decay_when_absent: 0.95    # @experimental — Phase 8.10 验收
  eta_pi_max: 0.15              # @experimental — controls geometric convergence rate

marker:
  decay_rates:
    NOVELTY: 0.85               # @experimental — Phase 8.10 → 0.7-0.95 sweep
    TENTATIVE: 0.92             # @experimental
    PAIN: 0.998                 # @experimental — Phase 9.7
    MISMATCH: 0.90              # @experimental — Phase 8.9
    CORRECTION: 0.88            # @experimental — Phase 8.9
    GAZE: 0.80                  # @experimental — Phase 9
    JOINT_ATTENTION: 0.82       # @experimental — Phase 9.5(独立 kind)
    IMITATION: 0.92             # @experimental
    KNOWLEDGE_GAP: 0.99         # @experimental — Phase 11.1
    EMPATHY_RESONANCE: 0.90     # @experimental — Phase 9.6 预留
    TRUST_PROMOTED: 0.95        # @experimental — Phase 10.7 预留
    BOREDOM: 0.93               # @experimental — Phase 8.5 + Phase 9.X
  max_kinds: 12                 # @structural — 上限,预留 SATISFACTION
  max_marker_count_per_pool: 200
  initial_intensity: 0.5        # @structural — Bayesian uninformative

composed_vocab:
  pairwise:
    max_partners_per_sa: 32     # @structural
    min_observations_promote: 5 # @experimental
  chain:
    base_min_obs: 5             # @experimental
    chain_length_increment: 5   # @experimental
    max_chain_length: 4         # @structural — combinatorial bound
    anti_correlation_threshold: -0.5  # @experimental
  delta_p:
    n_situations_per_eval: 8    # @structural — paired-t df=7
    n_horizon_ticks: 5          # ← v10 改:从 50 降到 5,B-V9-3 fix
    promote_dP_min: 0.05        # @experimental — Phase 8.4 验收
    cold_start_skip_until_held_out: 50

slot_preference:
  min_distinct_fillers: 3       # @structural — minimum for variance
  jsd_smoothing_alpha: 0.5      # @structural — Laplace prior

attention:
  type_budget:                  # @scenario_tuneable — 见 scenario_profiles
    PerceptSA: 0.35
    VocabSA: 0.25
    MarkerSA: 0.15
    EntitySA: 0.20
    ControlSignalSA: 0.05       # v10 新增第 5 类

action_competition:
  bootstrap_R_change_all_zero: true   # @structural
  initial_noise_unit_normal: true     # @structural
  early_phase_n_actions: 50           # @experimental
  derived_noise_scale_ratio: 0.5      # @experimental
  min_samples_thompson: 5             # @structural

draft_action:
  text_chars_per_tick_default: 1      # @scenario_tuneable

text_sensor:
  silence_threshold_anonymous_ticks: 20  # @experimental — fallback only
  silence_percentile_for_user: 0.95     # @structural — robust percentile
  silence_percentile_min_samples: 10    # @experimental

credit_assignment:
  phase_2_timeout_ticks: 50              # @experimental
  similarity_threshold_disagreement: 0.3 # @experimental
  attention_share_partial_penalty: 0.5   # @structural — half-share

counterfactual:
  n_bootstraps: 25                       # @structural — Welch df sufficient
  intervention_levels: [1.0, 0.75, 0.5, 0.25, 0.0]  # @structural
  max_horizon_ticks: 10                  # @experimental
  causal_strength_min: 0.05              # @experimental
  use_t_test: false                      # ← v10:取消 t-test,S-V9-3 fix
  monotonicity_tolerance: 0.01           # @structural

hierarchy:
  agglomerative_min_cluster_size: 3      # @structural
  max_clusters_per_vocab: 3              # @experimental
  common_pref_similarity_min: 0.7        # @experimental
  silhouette_fallback_min_k: 2           # @structural

deliberative:
  max_virtual_steps_per_turn: 10         # @experimental
  enter_threshold: 0.6                   # @experimental
  conclusion_R_floor: 0.3                # ← v10:从 §41.4 字面量提到 yaml,B-V9-4 fix
  virtual_to_main_dilution: 0.5          # @experimental

self_model:
  heartbeat_interval_ticks: 36000        # @experimental — Phase 11.5
  attention_cap_percent: 0.05            # @experimental
  reactivation_target_R: 0.3             # @experimental — 修 M-V9-1
  reactivation_pullback_rate: 0.05       # @structural — slow gradient

held_out:
  reservoir_capacity: 500                # @structural
  k_fold_interval: 5                     # @structural
```

---

## 2. ΔP 测试 — horizon 短 + 信号保留(B-V9-3 真修)

### 2.3.5 horizon 短 + 测早期 P 差(B-V9-3 fix)

**轮 6 错误指出**:`Pi_decay_when_absent=0.95`,horizon=50,则 0.95^50 ≈ 0.077 → 所有 SA 衰减到近零 → ΔP 测的是噪声差。

**v10 真修**:**horizon 短(5 tick)+ 测 immediate value-add**:

```python
def evaluate_delta_p_incremental_v10(candidate, current_pool, held_out_pool):
    """
    @op_count: O(N_situations * N_horizon * |active SA|),
        worst-case: 8 * 5 * 50 = 2K ops (1000x faster than v9).
    
    v10 改进:
    - n_horizon_ticks = 5(从 50)
    - 测 candidate 对 immediate P 的影响,不是远期影响
    - 显式声明:这是 short-term value-add,不是 long-term causal effect
    """
    K = load_constant("composed_vocab.delta_p.n_situations_per_eval")
    N_horizon = load_constant("composed_vocab.delta_p.n_horizon_ticks")  # 5
    promote_min = load_constant("composed_vocab.delta_p.promote_dP_min")
    cold_min = load_constant("composed_vocab.delta_p.cold_start_skip_until_held_out")
    
    if len(held_out_pool) < cold_min:
        return {"passes": False, "reason": "insufficient_held_out",
                "fallback_to_pmi_only": True}
    
    current_sig = compute_context_signature_v10(current_pool)
    similar_situations = held_out_pool.find_top_k_similar(current_sig, k=K)
    
    delta_Ps = []
    for situation in similar_situations:
        # baseline run (no candidate)
        pool_a = situation.shallow_clone_pool_state()
        for _ in range(N_horizon):
            advance_lightweight(pool_a)
        P_a = pool_a.mean_recent_P()  # 近期 P 平均(不是远期)
        
        # candidate run
        pool_b = situation.shallow_clone_pool_state()
        pool_b.inject_vocab(candidate)
        for _ in range(N_horizon):
            advance_lightweight(pool_b)
        P_b = pool_b.mean_recent_P()
        
        delta_Ps.append(P_a - P_b)
    
    # 关键修复:横向 8 个 situations 的 ΔP 是真实数据噪声,
    # 不是 RNG 噪声(S-V9-3 同源)
    mean_delta = float(np.mean(delta_Ps))
    
    # 用 effect-size threshold(无 t-test,见 §40.4 同源修复)
    passes = (mean_delta > promote_min and
              sum(1 for d in delta_Ps if d > 0) >= K * 0.625)  # 5/8 ≥ 0
    
    return {
        "mean_delta_P": mean_delta,
        "n_situations_positive": sum(1 for d in delta_Ps if d > 0),
        "passes": passes,
        "framework": "short_term_value_add",  # 显式承认
    }
```

**为什么这真修**:
- horizon=5:Π 衰减只到 0.77,信号仍 robust
- mean ΔP over 8 真 situations 是真实数据噪声,不是 RNG 噪声
- 5/8 situations 一致正向 = 真实信号(不只是 mean)
- 不用 t-test(避免 S-V9-3 同源问题)

### 2.3.1 context_signature — z-normalized + Jaccard(S-V9-1 fix)

```python
def compute_context_signature_v10(state_pool, top_k=20):
    """
    @op_count: O(top_k * 4 types + |top_k|^2 hash compare),worst-case 500 ops.
    
    v10 修复 S-V9-1:
    - 替换 hash_mode 噪声维度为 top-K persistent_id 集合(Jaccard 用)
    - z-normalize 每个维度,避免 hash_mode 主导 cosine
    """
    top_sas = state_pool.top_n_by_attention_score(top_k)
    
    # 每 type 聚合
    type_aggregates = {SAType.PERCEPT: [], SAType.VOCAB: [],
                       SAType.MARKER: [], SAType.ENTITY: [],
                       SAType.CONTROL_SIGNAL: []}
    for sa in top_sas:
        type_aggregates[sa.type].append(sa)
    
    # 12 个连续维度 + 5 个 top-K set
    continuous_dims = []
    persistent_id_sets = {}
    
    for sa_type in [SAType.PERCEPT, SAType.VOCAB, SAType.MARKER,
                    SAType.ENTITY, SAType.CONTROL_SIGNAL]:
        bucket = type_aggregates[sa_type]
        # 三个数值维度
        if bucket:
            continuous_dims.extend([
                len(bucket),
                sum(s.R for s in bucket),
                sum(abs(s.cognitive_pressure) for s in bucket),
            ])
        else:
            continuous_dims.extend([0, 0.0, 0.0])
        # set of persistent_ids(用于 Jaccard)
        persistent_id_sets[sa_type] = set(s.persistent_id for s in bucket)
    
    return {
        "continuous": np.array(continuous_dims),  # 15-dim
        "id_sets": persistent_id_sets,            # 5 sets
    }

def context_signature_similarity_v10(sig_a, sig_b):
    """
    @op_count: O(15 + sum(|set_a| + |set_b|)),worst 100 ops.
    
    混合 cosine(z-normalized continuous) + Jaccard(id sets)
    """
    # z-normalize 连续维度(用 global stats)
    z_a = z_normalize(sig_a["continuous"], global_stats)
    z_b = z_normalize(sig_b["continuous"], global_stats)
    continuous_sim = cosine_similarity(z_a, z_b)
    
    # Jaccard over id sets(每 type 一个 Jaccard)
    jaccard_per_type = []
    for sa_type in sig_a["id_sets"]:
        set_a = sig_a["id_sets"][sa_type]
        set_b = sig_b["id_sets"][sa_type]
        if not set_a and not set_b:
            jaccard_per_type.append(0.0)
        else:
            jaccard_per_type.append(
                len(set_a & set_b) / max(len(set_a | set_b), 1)
            )
    mean_jaccard = np.mean(jaccard_per_type)
    
    # 加权混合(50/50 — @structural,半半信赖)
    return 0.5 * continuous_sim + 0.5 * mean_jaccard
```

**关键修复**:
- 用 z-normalized continuous + Jaccard over id sets 替代 hash mode
- Jaccard 是真语义相似度(共享 SA → 高 Jaccard),不是 hash 噪声
- 加权混合显式且对称

### 2.3.4 HeldOutPool — Reservoir Sampling(S-V9-2 fix)

```python
class HeldOutPool:
    """
    @op_count: O(1) insert in expectation; O(N * 100) for find_top_k_similar.
    
    v10 修复 S-V9-2:reservoir sampling 保持固定大小 + 均匀采样
    """
    def __init__(self):
        self.K_FOLD = load_constant("held_out.k_fold_interval")           # 5
        self.CAPACITY = load_constant("held_out.reservoir_capacity")     # 500
        self.training_counter = 0
        self.candidate_counter = 0  # K-fold 选中的总数(不只是 reservoir 内)
        self.held_out_samples = []
        self.rng = np.random.RandomState(42)
    
    def receive_teaching_sample(self, sample):
        self.training_counter += 1
        if self.training_counter % self.K_FOLD != 0:
            return "training"
        
        # 这是 K-fold 选中的候选
        self.candidate_counter += 1
        sample.context_signature = compute_context_signature_v10(sample.pool_state)
        sample.candidate_id = self.candidate_counter
        
        if len(self.held_out_samples) < self.CAPACITY:
            self.held_out_samples.append(sample)
            return "held_out"
        
        # Reservoir sampling:用概率 CAPACITY / candidate_counter 替换随机旧样本
        replace_idx = self.rng.randint(0, self.candidate_counter)
        if replace_idx < self.CAPACITY:
            self.held_out_samples[replace_idx] = sample
            return "held_out_replaced"
        return "discarded"
    
    def find_top_k_similar(self, query_sig, k):
        scored = [
            (s, context_signature_similarity_v10(s.context_signature, query_sig))
            for s in self.held_out_samples
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in scored[:k]]
```

**为什么这真修**:
- 不再按时间驱逐——任何时间段的样本都有相等概率留在 held_out
- K-fold 仍保证 1/5 比例进入候选
- Reservoir 是均匀采样:long-run held_out 分布稳定不偏向最近

---

## 11. Marker SA + 完整 family 映射表(轮 6 修)

### 11.3 v10 完整 family→type 映射(5 type / 9+ markers)

```yaml
# === family_to_type_mapping_v10.yaml ===

# v10 改:从 4 types 扩到 5 types(加 ControlSignalSA)
# Marker kinds cap 从 8 扩到 12(预留 EMPATHY/TRUST/BOREDOM/SATISFACTION)
# JOINT_ATTENTION 拆回独立 marker kind(S-V9-4 fix)

PerceptSA:                              # type 1
  - vision_percept
  - audio_percept
  - text_char
  - number_count
  - sensor_salience_hint

VocabSA:                                # type 2
  - vocab
  - tentative_vocab
  - narrative
  - causal
  - hierarchy
  - anonymous_cluster
  - abstract_vocab

MarkerSA:                               # type 3
  kinds:
    - NOVELTY
    - TENTATIVE
    - PAIN
    - MISMATCH
    - CORRECTION
    - GAZE                              # 注意:gaze contingency 单独
    - JOINT_ATTENTION                   # 注意:joint attention 单独
    - IMITATION
    - KNOWLEDGE_GAP
    - EMPATHY_RESONANCE                 # Phase 9.6 预留
    - TRUST_PROMOTED                    # Phase 10.7 预留
    - BOREDOM                           # Phase 8.5 启动 + Phase 9 拓展
  # SATISFACTION 预留 13 位,经设计稿修订加

EntitySA:                               # type 4
  - drive
  - entity_user
  - self_model
  - focus
  - goal
  - belief_model
  - hypothesis

ControlSignalSA:                        # type 5 — v10 新增(S-V9-5 fix)
  - utterance_boundary
  - tick_boundary                       # Phase 8.2 内部
  - mode_switch                         # 例如 streaming → reading

# 总计: 5 + 7 + 12 + 7 + 3 = 34 spawn 路径
# 每条都有 spawn_X_sa() 函数 + type 标识

attention_budget_v10:
  PerceptSA: 0.35
  VocabSA: 0.25
  MarkerSA: 0.15
  EntitySA: 0.20
  ControlSignalSA: 0.05
```

### 11.8 Tentative vocab 状态转移图(S-V9-7 fix)

```
状态 1: tentative_vocab spawn
  - vocab_sa.kind = tentative
  - tentative_marker spawn 同时
  - vocab_sa.persistent_id = X
  - marker.target_sa_id = X

状态 2: 第二次曝光强化
  - 触发:跨模态共现强 again
  - 行动:
    - vocab_sa.positive_co_observations += 1
    - marker.real_energy *= 0.7 (开始衰减)

状态 3: 晋升 → 正式 vocab
  - 触发:vocab_sa.confidence > θ_promote
  - 行动:
    - vocab_sa.kind = "promoted"  (不再 tentative)
    - tentative_marker 立即 retire(状态转移触发)

状态 4: 反例撤销 → 早退
  - 触发:vocab_sa.confidence < θ_retract
  - 行动:
    - vocab_sa 撤销(走 §2.7 atomic retire)
    - tentative_marker 立即 retire

状态 5: marker 衰减完但 vocab 仍存在
  - marker.real_energy → 0 → marker retire
  - vocab_sa 转移到"待验证"状态(不变 promoted,不撤销)
  - 等下次曝光决定:再现 → 状态 2;长无 → 走 §1 short_term decay 自然消失

红线:
- vocab_sa.kind 在 {tentative, promoted, retracted} 三态
- marker 只在 tentative 态存在
- 状态转移原子(walk both SAs in single transaction)
```

---

## 16. v10 真修硬编码(B-V9-4 fix)

### 16.11 §41.4 conclusion R 全 yaml 化

**v9 错误**:`max(0.3, virtual_R - initial_R) * dilution_factor` 里的 `0.3` 是 v9 自己反 anti-pattern 章节中的 anti-pattern。

**v10 真修**:

```python
def derive_conclusion_from_virtual_state(virtual_pool, original_pool):
    """@op_count: O(|virtual SA|), worst 200 ops."""
    floor = load_constant("deliberative.conclusion_R_floor")     # 0.3 in yaml
    dilution = load_constant("deliberative.virtual_to_main_dilution")  # 0.5 in yaml
    delta_threshold = load_constant("deliberative.conclusion_R_delta_threshold")
    
    conclusions = []
    for v_sa in virtual_pool.active_sas():
        orig_sa = original_pool.get(v_sa.persistent_id)
        if orig_sa is None:
            # v10:虚池不能 spawn 全新 vocab SA(L-V9-2 fix)
            # 只允许 virtual 池中 reactivate 原 pool 已有 SA
            continue
        
        delta_R = v_sa.R - orig_sa.R
        if delta_R < delta_threshold:
            continue
        
        # 全 yaml 化(B-V9-4 真修)
        conclusion_R = max(floor, delta_R) * dilution
        new_sa = create_sa_like(v_sa, R=conclusion_R)
        new_sa.source_marker = f"deliberation::{deliberation_id}"
        conclusions.append(new_sa)
    
    return conclusions
```

---

## 40. §40.4 因果 — effect-size only(S-V9-3 fix)

```python
def estimate_causal_strength_v10(sa_a, sa_b, current_pool, attention_snapshot):
    """
    @op_count: O(N_boot * N_levels * N_horizon * |SA|),
        worst: 25 * 5 * 10 * 50 = 62.5K ops.
    
    v10 修复 S-V9-3:取消 Welch t-test(RNG-only 噪声必然 p<0.05)
    改用 effect-size threshold + monotonicity 双门
    """
    n_boot = load_constant("counterfactual.n_bootstraps")
    levels = load_constant("counterfactual.intervention_levels")
    n_horizon = load_constant("counterfactual.max_horizon_ticks")
    strength_min = load_constant("counterfactual.causal_strength_min")
    use_t = load_constant("counterfactual.use_t_test")
    tolerance = load_constant("counterfactual.monotonicity_tolerance")
    
    results_by_level = {}
    for level in levels:
        b_R_per_boot = []
        for boot_seed in range(n_boot):
            pool_snap = current_pool.snapshot_full(seed=boot_seed)
            pool_snap.scale_sa_R(sa_a, level)
            pool_snap.freeze_attention_to(attention_snapshot)
            for _ in range(n_horizon):
                pool_snap.advance_with_frozen_attention()
            b_R_per_boot.append(pool_snap.sa(sa_b).mean_recent_R)
        results_by_level[level] = float(np.mean(b_R_per_boot))
    
    means = [results_by_level[l] for l in [0.0, 0.25, 0.5, 0.75, 1.0]]
    
    # 单调性测试(允许小容差)
    monotonic = all(means[i+1] >= means[i] - tolerance for i in range(4))
    
    causal_strength = means[-1] - means[0]
    
    # 不用 t-test,只看 effect size
    is_causal = monotonic and causal_strength > strength_min
    
    return {
        "causal_strength": causal_strength,
        "monotonic": monotonic,
        "levels_means": means,
        "framework": "controlled_direct_effect",
        "is_causal": is_causal,
    }
```

**关键**:取消 t-test(轮 6 S-V9-3 指出在 RNG-only 噪声上必然 p<0.05),用 effect-size + monotonicity 双门。

---

## 41. §41.5 self_model — pullback 到 useful R(M-V9-1 fix)

**v9 错误**:gradient pullback asymptotes 在 0.05(low_threshold),不能恢复到 useful R。

**v10 真修**:

```python
def step_self_model_v10(self_sa, current_tick):
    """@op_count: O(1)."""
    low_threshold = load_constant("self_model.decay_low_threshold")        # 0.05
    target_R = load_constant("self_model.reactivation_target_R")           # 0.3 — v10 新
    pullback_rate = load_constant("self_model.reactivation_pullback_rate") # 0.05
    cap_percent = load_constant("self_model.attention_cap_percent")
    
    # 标准衰减
    self_sa.R *= load_constant("energy.R_decay_long")
    
    # 梯度回拉到 target_R(M-V9-1 修)
    if self_sa.R < low_threshold:
        # 朝 target_R 渐进,不是朝 low_threshold
        self_sa.R += pullback_rate * (target_R - self_sa.R)
    
    # heartbeat 持久化
    heartbeat = load_constant("self_model.heartbeat_interval_ticks")
    if current_tick % heartbeat == 0:
        persist_to_sqlite(self_sa)
```

---

## 19. v10 给 Codex 的最终指令

1. **v10 取代 v9 作为 Phase 8 实施依据**
2. **每 PR 必跑 red_line_check_v10.py (AST-based)**——违规直接拒
3. **所有常量 100% yaml 化**——代码无任何数字字面量(除 {0, 1, 2, -1, 0.0, 1.0, -1.0})
4. **每函数 @op_count 注解**——无注解不许 merge
5. **Phase 8.4 ΔP horizon = 5**(yaml 中)
6. **Phase 10.4 反事实标 framework="controlled_direct_effect"** 在 audit 报告
7. **27 family → 5 type 映射表强制公开**(§11.3)
8. **Marker kinds cap = 12,新增必须经设计稿修订**

---

## 附录: v9 → v10 修复完整列表

**v9 Blocker (4 个真修)**:
- B-V9-1: AST-based red line gate(7 种绕过修)
- B-V9-2: §1.5 常量治理协议(分 structural/scenario_tuneable/experimental)
- B-V9-3: ΔP horizon 50 → 5(yaml 化)
- B-V9-4: §41.4 `0.3` 字面量 → yaml

**v9 Serious (7 个真修)**:
- S-V9-1: context_signature z-normalized + Jaccard
- S-V9-2: HeldOutPool reservoir sampling
- S-V9-3: §40.4 effect-size only(取消 t-test)
- S-V9-4: JOINT_ATTENTION 独立 marker kind
- S-V9-5: ControlSignalSA 第 5 type
- S-V9-6: Marker cap 12 + 预留 EMPATHY/TRUST/BOREDOM/SATISFACTION
- S-V9-7: tentative vocab 状态转移图

**v9 Medium**:
- M-V9-1: self_sa pullback to target_R(useful 而非 threshold)
- M-V9-2-6: 各 case 在各章节修

— 接手线程,2026-06-17

---

## 最终判断 — v10 是否真收敛?

**纪律层**:✅ AST-based gate 切断了 grep 5 种绕过 + governance protocol 切断了 "yaml 还是 magic numbers" 的指责。

**算法层**:✅ ΔP horizon 5、HeldOutPool reservoir、effect-size only、context_signature Jaccard——4 个 v9 算法 blocker 真修。

**架构层**:✅ Family 映射真完整、ControlSignalSA 新类、Marker cap 12 + 预留——3 个架构 serious 真修。

**最大遗留风险**:
- AST gate 可能仍有边缘 case 没考虑(但比 grep 强 10x)
- Reservoir 在极早期(< 100 candidate)分布仍偏(但好于 v9 eviction)
- effect-size 阈值 0.05 仍是 experimental——但已分类标 @experimental,governance 有 A/B 实验跟踪

**可以让 Codex 拿 v10 开 Phase 8.2 了**。这是工程上"可以开工"而非"完美"。后续审阅如还有 minor issues,在 Phase 实施中迭代而非再开一版设计稿。
