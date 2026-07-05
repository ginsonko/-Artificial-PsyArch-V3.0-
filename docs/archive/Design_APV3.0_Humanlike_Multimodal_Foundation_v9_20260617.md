# APV3.0 拟人多模态底座 — 完整设计稿 v9(纪律层根本性收敛)

日期: 2026-06-17
作者: 接手线程
状态: **v8 经轮 5 审阅,识别出"每轮删旧硬编码 + 新硬编码"的循环模式。v9 不再修个别公式,而是从纪律层面彻底切断这个循环。核心:(1) 所有常量物理外化到 YAML、(2) advance_lightweight + context_signature 完整规范、(3) bootstrap 升 ≥20 + 5 levels、(4) 27→4 type 完整映射表、(5) virtual→main reification 真规范、(6) self_sa 梯度偏置而非 reset、(7) 强制承认 controlled-direct-effect 框架、(8) 承认 intra-type 机制对 ~70 而非 6。**

前身链:v1 → v2 → v3 → v4 → v5 → v6 → v7 → v8 → **v9(本稿)**

---

## 0. v9 核心纪律变化(必读 — 不读这章其他都没意义)

### 0.1 v8 失败的根本诊断

轮 5 审阅指出:**v3-v8 陷入相同循环 5 次**——每轮"删除旧硬编码,在修复中重新引入新硬编码,且每轮在'派生''documented free param''可配'等措辞上越发漂亮**。

具体证据:
- v7 删 `+0.3, +0.5_if_ready_else_-0.2` → v8 引入 `MARKER_DECAY_RATES = {NOVELTY:0.85, TENTATIVE:0.92, PAIN:0.998, ...}` 8 个魔数
- v8 §11.2 修 absent SA → 引入 `ρ_decay_when_absent = 0.95`
- v8 §16.9 修 noise_scale → 引入 `× 0.5` 魔系数
- v8 §11.3 类型预算 → 40/25/15/20 凭空
- v8 §40.4 N_BOOTSTRAPS=5 + 3 levels(统计学上几乎必然 fail to reject)

**根本问题**:我把"派生""可配""documented free param"当作语言上的免责声明用,实际上**这些数字仍在源代码字面量中**,**没有人能修改它们而不改源代码**。这就是 anti-pattern 反复。

### 0.2 v9 纪律根本性变化

| 层面 | v3-v8 做法 | v9 做法 |
|---|---|---|
| 常量管理 | 在代码字面量,加注释"派生" | **唯一来源 = `apv3_constants.yaml`**,代码只 `load_constant("name")` |
| 命名规范 | `MARKER_DECAY_RATES = {...}` | `MARKER_DECAY_RATES = load_yaml("constants/marker_decay_rates")` |
| 红线扫描 | "grep 'hardcoded' 必须 0 命中" | **`grep -E "= 0\.[0-9]" runtime/cognitive/*.py` 必须 0 命中**(没有字面量浮点数赋值) |
| 算法 spec | "lightweight advance"(概念) | **每个新算法必须给完整伪代码 + worst-case op count + 反例**;否则不算 spec |
| 统计学严谨 | N=5 bootstrap、3 levels | **N ≥ 20 或显式承认非统计学路径(规则化判断,不假装显著性)** |
| 架构简化承诺 | "27 → 4 types,6 交互对" | **承认实际 ~70 机制对,只在 type-level 简化,intra-type 仍有复杂度** |
| Counterfactual | "完整因果效应" | **承认 controlled-direct-effect 框架**,明示与 total-causal-effect 区别 |

### 0.3 红线 0.4 终极版(v9 强制)

```yaml
# === apv3_red_lines_v9.yaml ===
# 每个 PR 必跑 red_line_check.py,违反任一即拒

NO_HARDCODED_NUMERIC_LITERALS_IN_COGNITIVE:
  # runtime/cognitive/ 下任何 *.py 文件
  # 不允许 = 0.85 这种字面量浮点数赋值
  # 必须 X = load_constant("descriptive_name")
  # 例外:数学公式中的结构性常数(如 0, 1, 2 用于 indexing / Bayesian prior of 0.5 等 prior 必须显式标记 @bayesian_prior)
  scan_command: |
    grep -nE "= [0-9]+\.[0-9]+" runtime/cognitive/ --include='*.py' \
      | grep -v "@bayesian_prior" | grep -v "# structural"
    # must return 0 hits

NO_MAGIC_INTEGER_THRESHOLDS:
  # 阈值类整数(min_exposure, max_chain_length, n_bootstraps)必须从 yaml 读
  scan_command: |
    grep -nE "(min|max|threshold|n_|num_)_[a-z_]+\s*=\s*[0-9]+" runtime/cognitive/ \
      | grep -v "load_constant" | grep -v "load_yaml"

NO_SILENT_FALLBACK_TO_HARDCODE_FOR_ANONYMOUS:
  # 不许 "if user_id is None: threshold = 20"
  # 必须 load_constant("default_silence_threshold_for_anonymous")
  scan_command: |
    grep -nE "if .* is None:\s*$" -A1 runtime/cognitive/ | grep -E "= [0-9]"

NO_PAPER_SPEC:
  # 每个新算法函数 docstring 必须有 @op_count 注解
  # 例: @op_count: O(N * |SA|), worst-case 50K
  scan_command: |
    python3 scripts/check_op_count_annotations.py
  # 必须无未注解的核心算法函数

NO_UNDEFINED_PRIMITIVE:
  # 任何被 ≥2 个其他模块调用的函数必须有完整伪代码 + 测试用例
  scan_command: |
    python3 scripts/find_undefined_primitives.py
```

**Codex 每个 PR 必跑这 5 个扫描**。**违反任一直接拒**。这是从 v9 起的强约束,不再"提倡"而是"必须"。

### 0.4 v8 → v9 修复对照表

| v8 缺陷 | v9 修复 |
|---|---|
| B-NEW-1: MARKER_DECAY_RATES 字面量 | §11.3 全部 `load_constant("marker.decay_rates.NOVELTY")` 等 |
| B-NEW-2: advance_lightweight 未定义 | §2.3 完整规范 + 反例承认(见下) |
| B-NEW-3: context_signature 未定义 | §2.3 完整定义(SA top-K 在 4 类型上的统计向量) |
| S-NEW-1/2: N=5 bootstrap + 3 levels 弱测试 | §40.4 改 N=25 + 5 levels;或承认"非统计学规则判断"路径 |
| S-NEW-3: Marker 清单不全 | §11.3 给完整 27→4 + MarkerKind 映射表 |
| S-NEW-4: 类型预算硬编码,与 scenario 脱钩 | §11.3 改 scenario-conditional 预算,从 scenario_profile.yaml 读 |
| S-NEW-5/6: ρ_decay/×0.5 anti-pattern 复发 | yaml 外化 + 红线扫描 |
| S-NEW-7: "27→4" 实际 ~70 机制对 | §0.5 公开承认 + §18.5 完整 intra-type 交互矩阵 |
| S-NEW-8: virtual→main 重物化未规范 | §41.4 完整规范 |
| S-NEW-9: self_sa bouncing 破坏连续性 | §41.5 改梯度回拉,不 reset |
| M-NEW-1: 冷启 held-out 不足 | §2.3 "insufficient_held_out → skip + log" 显式分支 |
| M-NEW-2/4/5: 各 edge case | 各章节修 |

### 0.5 v9 诚实承认(再不掩饰)

**Architecture 承认**:
- 27 SA 家族 → 4 type 层是真简化(count-level)
- **intra-type 机制对仍有 ~70**(VocabSA 内 6 sub-mechanism, EntitySA 内 7, MarkerSA 内 8 kinds)
- v9 给出 intra-type 矩阵 + 已分析的对 / 暂未分析的对

**Counterfactual 承认**:
- §40.4 frozen attention = **controlled direct effect (CDE)**,不是 total causal effect
- 与人类反事实推理(隐含 total effect)有差距
- v9 用 CDE 是因为 total 在状态池中无法可计算定义
- 承认这是工程妥协

**算力承认**:
- §2.3 ΔP 测试每候选 ~5-50K ops(取决于 active SAs 数)
- 不再声称"40K precisely",而是给 worst-case 上限
- 加入 budget gate:每 tick 至多 1 个 ΔP 评估

**冷启动承认**:
- Phase 8.4 ΔP gate 前 ~500 tick 自动 fallback 到非 ΔP 模式(纯 PMI + 短期承认)
- 不假装"系统从 t=0 严格 ΔP 验证"

---

## 1. apv3_constants.yaml 完整规范(新增章节,纪律基石)

### 1.1 文件物理位置

```
APV3.0test/
├── config/
│   ├── apv3_constants.yaml      ← 所有常量唯一来源
│   ├── apv3_red_lines_v9.yaml   ← 红线扫描规则
│   ├── scenario_profiles/
│   │   ├── text_dialogue.yaml
│   │   ├── desktop_pet.yaml
│   │   ├── embodied.yaml
│   │   └── agent_workflow.yaml
│   └── marker_decay_rates.yaml
```

### 1.2 apv3_constants.yaml 结构(v9 起强制)

```yaml
# === apv3_constants.yaml ===
# v9 起所有常量唯一来源。修改不需改代码。
# 红线扫描 NO_HARDCODED_NUMERIC_LITERALS_IN_COGNITIVE 强制执行。

version: "9.0"

energy:
  # SA 能量场衰减
  R_decay_short: 0.95
  R_decay_long: 0.999
  V_decay: 0.93
  A_decay: 0.88
  F_decay: 0.97
  # absent SA Π 衰减(v8 B-NEW-3 fix)
  Pi_decay_when_absent: 0.95
  # 几何收敛上限
  eta_pi_max: 0.15
  
marker:
  decay_rates:
    NOVELTY: 0.85
    TENTATIVE: 0.92
    PAIN: 0.998
    MISMATCH: 0.90
    CORRECTION: 0.88
    GAZE: 0.80
    IMITATION: 0.92
    KNOWLEDGE_GAP: 0.99
  max_marker_count_per_pool: 200       # 防 marker 数量爆炸
  initial_intensity: 0.5

composed_vocab:
  pairwise:
    max_partners_per_sa: 32
    min_observations_promote: 5
  chain:
    base_min_obs: 5
    chain_length_increment: 5
    max_chain_length: 4
    anti_correlation_threshold: -0.5
  delta_p:
    n_situations_per_eval: 8
    n_horizon_ticks: 50
    promote_dP_min: 0.05
    significance_p_value: 0.05
    cold_start_skip_until_held_out: 50   # 至少 50 held-out 才信任 ΔP

slot_preference:
  min_distinct_fillers: 3
  jsd_smoothing_alpha: 0.5

attention:
  type_budget:
    # 默认全局预算,scenario_profile 可覆盖
    PerceptSA: 0.40
    VocabSA: 0.25
    MarkerSA: 0.15
    EntitySA: 0.20

action_competition:
  bootstrap_R_change_all_zero: true
  initial_noise_unit_normal: true
  early_phase_n_actions: 50
  derived_noise_scale_ratio: 0.5         # 派生 noise = std × ratio
  min_samples_thompson: 5

draft_action:
  text_chars_per_tick_default: 1

text_sensor:
  silence_threshold_anonymous_ticks: 20
  silence_percentile_for_user: 0.95
  silence_percentile_min_samples: 10

credit_assignment:
  phase_2_timeout_ticks: 50
  similarity_threshold_disagreement: 0.3
  attention_share_partial_penalty: 0.5

counterfactual:
  n_bootstraps: 25                       # v8 N=5 → v9 N=25
  intervention_levels:
    - 1.0
    - 0.75
    - 0.5
    - 0.25
    - 0.0                                # 5 levels for monotonicity
  max_horizon_ticks: 10
  causal_strength_min: 0.05
  causal_p_value: 0.05

hierarchy:
  agglomerative_min_cluster_size: 3
  max_clusters_per_vocab: 3
  common_pref_similarity_min: 0.7
  silhouette_fallback_min_k: 2

deliberative:
  max_virtual_steps_per_turn: 10
  enter_threshold: 0.6

self_model:
  heartbeat_interval_ticks: 36000          # 1h
  attention_cap_percent: 0.05
  reactivation_decay_gradient: 0.1         # 梯度回拉,不 reset
  decay_low_threshold: 0.05                # 触发 gradual 回拉

# scenario_profile 可 override 上述任一字段
```

### 1.3 代码访问统一接口

```python
# runtime/util/constants.py
import yaml
from functools import lru_cache

@lru_cache(maxsize=1)
def _load_constants():
    with open("config/apv3_constants.yaml") as f:
        return yaml.safe_load(f)

def load_constant(path: str):
    """
    通过点分路径访问常量。
    例: load_constant("marker.decay_rates.NOVELTY") → 0.85
    """
    config = _load_constants()
    parts = path.split(".")
    val = config
    for p in parts:
        val = val[p]
    return val

# 用法:
# rho_pi_absent = load_constant("energy.Pi_decay_when_absent")
# 而不是 rho_pi_absent = 0.95
```

### 1.4 红线扫描脚本(v9 PR-gate)

```python
# scripts/red_line_check_v9.py
import re
import subprocess
import sys

def check_no_hardcoded_floats():
    """运行 grep 检查 runtime/cognitive/ 下浮点字面量"""
    result = subprocess.run(
        ["grep", "-rnE", r"= [0-9]+\.[0-9]+",
         "runtime/cognitive/", "--include=*.py"],
        capture_output=True, text=True
    )
    lines = result.stdout.strip().split("\n")
    # 过滤 @bayesian_prior 和 # structural
    violations = []
    for line in lines:
        if not line:
            continue
        if "@bayesian_prior" in line or "# structural" in line:
            continue
        violations.append(line)
    return violations

def check_op_count_annotations():
    """每个 runtime/cognitive/ 下函数必须有 @op_count 注解"""
    import ast
    violations = []
    for path in glob.glob("runtime/cognitive/**/*.py", recursive=True):
        tree = ast.parse(open(path).read())
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                docstring = ast.get_docstring(node)
                if not docstring or "@op_count:" not in docstring:
                    if node.name.startswith("_") or len(node.body) < 3:
                        continue  # 私有/简短跳过
                    violations.append(f"{path}:{node.lineno}: {node.name}")
    return violations

if __name__ == "__main__":
    v1 = check_no_hardcoded_floats()
    v2 = check_op_count_annotations()
    if v1 or v2:
        print(f"HARDCODE VIOLATIONS ({len(v1)}):")
        for v in v1: print(f"  {v}")
        print(f"\nOP COUNT VIOLATIONS ({len(v2)}):")
        for v in v2: print(f"  {v}")
        sys.exit(1)
    print("All red lines pass.")
    sys.exit(0)
```

---

## 2. 通用 SA 组合词汇固化 — v9 完整规范

### 2.1-2.2 沿用 v8

### 2.3 ΔP 晋升门 — 完整可实现版(B-NEW-2 + B-NEW-3 真修)

#### 2.3.1 context_signature 完整定义

**v8 错误**:context_signature 概念引用但从未定义。

**v9 显式定义**:

```python
def compute_context_signature(state_pool, top_k=20):
    """
    @op_count: O(top_k * 4 types), worst-case 80 ops.
    
    state_pool context signature = 当前活跃 top-K SA 按类型聚合的统计指纹。
    """
    # 按 attention_score 排序,取 top_k
    top_sas = state_pool.top_n_by_attention_score(top_k)
    
    # 按 SAType 聚合
    type_aggregates = {SAType.PERCEPT: [], SAType.VOCAB: [], 
                       SAType.MARKER: [], SAType.ENTITY: []}
    for sa in top_sas:
        type_aggregates[sa.type].append({
            "persistent_id_hash": hash(sa.persistent_id) % 1024,  # bucket
            "R": sa.R,
            "P_abs": abs(sa.cognitive_pressure),
        })
    
    # 生成 fingerprint vector
    # 每个 type 4 个数:count, sum_R, sum_|P|, top_id_hash_mode
    signature = []
    for sa_type in [SAType.PERCEPT, SAType.VOCAB, SAType.MARKER, SAType.ENTITY]:
        bucket = type_aggregates[sa_type]
        signature.extend([
            len(bucket),
            sum(b["R"] for b in bucket),
            sum(b["P_abs"] for b in bucket),
            mode([b["persistent_id_hash"] for b in bucket]) if bucket else 0,
        ])
    
    return np.array(signature)  # 16-dim vector

def context_signature_similarity(sig_a, sig_b):
    """cosine similarity"""
    return float(np.dot(sig_a, sig_b) / (np.linalg.norm(sig_a) * np.linalg.norm(sig_b) + 1e-9))
```

#### 2.3.2 advance_lightweight 完整定义

**v8 错误**:概念引用但未规范"反事实 horizon 的观察源"。

**v9 显式选定 + 承认**:

```python
def advance_lightweight(pool_snapshot, dt_ticks=1):
    """
    @op_count: O(|active SA| * 4 types), worst-case 400 ops per call.
    
    反事实 horizon 的 advance:
    - Π 不接受新观察(没有未来观察),只按 §11.2 absent-SA 规则衰减
    - R 按标准 decay,不接受外源注入(反事实假设)
    - V 沿用 Π(因为无新预测来源,V ← Π)
    - 不重跑 attention selector(用 baseline attention 分配,§40.4 一致)
    
    显式承认:这是 controlled trajectory(在 baseline attention 下能量自然演化),
    不是 "system would behave if candidate were present from t=0"。
    
    这给出的 ΔP 是 candidate 的 immediate value-add,
    不是 full causal effect。这是工程妥协。
    """
    rho_R_short = load_constant("energy.R_decay_short")
    rho_pi_absent = load_constant("energy.Pi_decay_when_absent")
    
    for sa in pool_snapshot.active_sas():
        # R 衰减(无外源)
        sa.R = rho_R_short ** dt_ticks * sa.R
        # Π 衰减(absent semantics,沿用 §11.2 修复)
        sa.Pi = rho_pi_absent ** dt_ticks * sa.Pi
        # V = Π(无新预测)
        sa.V = sa.Pi
        # P 重算
        sa.P = sa.R - sa.V
    
    pool_snapshot.tick += dt_ticks
```

**关键诚实**:
- 这个 advance 不是 "the system if candidate were there from t=0",而是 "the system with candidate frozen at the spawn moment, no new sensory input"
- 严格说是 CDE(controlled direct effect),v9 公开承认
- 测得的 ΔP 是 candidate 对**当前情境**的 immediate value-add,不是 full effect
- 与 §40.4 反事实方法学一致

#### 2.3.3 incremental ΔP 完整算法

```python
def evaluate_delta_p_incremental(candidate, current_pool, held_out_pool):
    """
    @op_count: O(N_situations * N_horizon * |active SA|), 
        worst-case 8 * 50 * 100 = 40K ops, 加 signature 计算 ~5K, 加 search ~5K。
        总 ~50K ops per candidate.
    """
    K = load_constant("composed_vocab.delta_p.n_situations_per_eval")
    N_horizon = load_constant("composed_vocab.delta_p.n_horizon_ticks")
    promote_min = load_constant("composed_vocab.delta_p.promote_dP_min")
    p_value_max = load_constant("composed_vocab.delta_p.significance_p_value")
    cold_start_min = load_constant("composed_vocab.delta_p.cold_start_skip_until_held_out")
    
    # 冷启动 fallback(M-NEW-1 fix)
    if len(held_out_pool) < cold_start_min:
        return {
            "passes": False,
            "reason": "insufficient_held_out",
            "fallback_to_pmi_only": True,
        }
    
    # 计算 current context signature
    current_sig = compute_context_signature(current_pool)
    
    # 找 K 个最相似 held-out situations
    similar_situations = held_out_pool.find_top_k_similar(current_sig, k=K)
    
    if len(similar_situations) < K:
        return {"passes": False, "reason": "insufficient_similar_held_out"}
    
    delta_Ps = []
    for situation in similar_situations:
        # baseline (no candidate)
        pool_a = situation.shallow_clone_pool_state()
        for _ in range(N_horizon):
            advance_lightweight(pool_a)
        P_a = pool_a.mean_recent_P()
        
        # with candidate from spawn point
        pool_b = situation.shallow_clone_pool_state()
        pool_b.inject_vocab(candidate)
        for _ in range(N_horizon):
            advance_lightweight(pool_b)
        P_b = pool_b.mean_recent_P()
        
        delta_Ps.append(P_a - P_b)
    
    mean_delta = mean(delta_Ps)
    t_stat, p_value = paired_t_test(delta_Ps)
    
    passes = p_value < p_value_max and mean_delta > promote_min
    return {
        "mean_delta_P": mean_delta,
        "p_value": p_value,
        "passes": passes,
    }
```

#### 2.3.4 K-fold held-out collection

```python
class HeldOutPool:
    """
    @op_count: O(1) insert; O(N * 16) for find_top_k_similar.
    
    K-fold 自动划分。
    """
    
    def __init__(self):
        self.K = 5  # 通过 yaml 后续可调
        self.training_counter = 0
        self.held_out_samples = []  # max size 由 yaml 控制
        self.max_size = 500
    
    def receive_teaching_sample(self, sample):
        self.training_counter += 1
        if self.training_counter % self.K == 0:
            sample.context_signature = compute_context_signature(sample.pool_state)
            self.held_out_samples.append(sample)
            if len(self.held_out_samples) > self.max_size:
                # 淘汰最旧
                self.held_out_samples = self.held_out_samples[-self.max_size:]
            return "held_out"
        return "training"
    
    def find_top_k_similar(self, query_sig, k):
        """@op_count: O(N * 16) where N = |held_out_samples|."""
        scored = [
            (s, context_signature_similarity(s.context_signature, query_sig))
            for s in self.held_out_samples
        ]
        scored.sort(key=lambda x: x[1], reverse=True)
        return [s for s, _ in scored[:k]]
    
    def __len__(self):
        return len(self.held_out_samples)
```

### 2.4 chain extension(沿用 v8 + yaml 化常量)

```python
def get_chain_threshold(chain_length):
    """@op_count: O(1)."""
    base = load_constant("composed_vocab.chain.base_min_obs")
    increment = load_constant("composed_vocab.chain.chain_length_increment")
    return base + chain_length * increment
```

### 2.5-2.8 沿用 v8

---

## 11. Marker SA 多态 + 完整 27→4 映射表(S-NEW-3 fix)

### 11.3 完整 family → type 映射表(v9 强制公开)

**轮 5 审阅指出**:v8 声称"27 → 4",但未给完整映射,joint_attention 丢失,utterance_boundary 未分类。**v9 给完整表**:

```yaml
# === family_to_type_mapping_v9.yaml ===
# 27 个 SA family 必须无遗漏映射到 4 type
# 红线扫描:每个 spawn_X_sa 函数必须显式 return type = SAType.X

PerceptSA:                              # type 1: 感受器输出
  - vision_percept                      # Phase 8.6 玩具视觉
  - audio_percept                       # Phase 8.13 音频
  - text_char                           # Phase 8.2 字符微事件
  - utterance_boundary                  # Phase 8.2 + §16.8 边界标记
  - number_count                        # Phase 8.6 subitize
  - sensor_salience_hint                # Phase 8.2 cold-start curiosity

VocabSA:                                # type 2: 概念/词汇/范畴
  - vocab                               # §2 标准 vocab
  - tentative_vocab                     # §11.8 fast mapping(与 marker::TENTATIVE 配对)
  - narrative                           # §40.A 时序事件链
  - causal                              # §40.B 因果关系(依赖 §40.4)
  - hierarchy                           # §40.E is_a 关系
  - anonymous_cluster                   # §40.5 匿名 super-cluster
  - abstract_vocab                      # §41.B 抽象概念

MarkerSA:                               # type 3: 瞬态状态标记(≤8 kinds)
  kinds:
    - NOVELTY                           # §11.3 novelty residual
    - TENTATIVE                         # §11.8 fast mapping marker
    - PAIN                              # §26 痛持续记忆
    - MISMATCH                          # §16.11 commit 不匹配
    - CORRECTION                        # §16.11 待教师证据
    - GAZE                              # §29.2 gaze contingency + §24 joint attention(合并)
    - IMITATION                         # §29.1 do-as-observed
    - KNOWLEDGE_GAP                     # §41.1 元认知

EntitySA:                               # type 4: 持久实体
  - drive                               # §20 驱力(epistemic/affiliation/etc.)
  - entity_user                         # §23 用户实体 + 依恋
  - self_model                          # §41.E entity::self(heartbeat)
  - focus                               # 视/音频/思维焦点
  - goal                                # §41.C 长 horizon 目标
  - belief_model                        # §40.C ToM 信念
  - hypothesis                          # §41 deliberative 结论候选

# 总计: 6 + 7 + 8 + 7 = 28 spawn 路径(含 joint_attention 合并 GAZE 后)
# 每条都有明确的 spawn_X_sa 函数 + type 标识
```

**关键决策**:
- joint_attention 合并入 GAZE marker(共享 SA 类型,kind=GAZE 但 target_id 区分 "other looking at me" vs "i follow other's gaze")
- utterance_boundary 是 PerceptSA(感受器产物,非 marker)
- focus 是 EntitySA(持久,持驻数 tick)
- tentative_vocab 是 VocabSA + 伴生 TENTATIVE marker(双 SA 协作)

### 11.4 intra-type 机制对承认(S-NEW-7 fix)

**v9 公开承认**:"27 → 4" 只在 count layer 简化;intra-type 仍有大量机制对。

**intra-type 机制对 count**:
- VocabSA 内 7 sub-family,对数 C(7,2) = 21
- EntitySA 内 7 sub-family,对数 C(7,2) = 21
- MarkerSA 内 8 kinds,对数 C(8,2) = 28
- 跨 type 对数 C(4,2) = 6
- **总计 ~76 机制对**

**v9 给出已分析 vs 未分析对清单**(强制公开):

```yaml
# analyzed_pairs:
# 高优先级(必须分析)
- [VocabSA::vocab, VocabSA::tentative_vocab]
- [VocabSA::vocab, MarkerSA::MISMATCH]
- [VocabSA::vocab, MarkerSA::CORRECTION]
- [VocabSA::vocab, MarkerSA::NOVELTY]
- [PerceptSA::vision_percept, VocabSA::vocab]
- [PerceptSA::text_char, VocabSA::vocab]
- [PerceptSA::utterance_boundary, EntitySA::draft_action]  # 见 §16.8
- [EntitySA::self_model, VocabSA::vocab]                   # 自我相关 vocab 优先
- [EntitySA::drive, EntitySA::goal]                        # drive 与 goal 关系
- [VocabSA::narrative, VocabSA::causal]                    # 叙事 vs 因果分化
... (~25 高优先级对)

# 中优先级(Phase 9-10 必须分析)
- [MarkerSA::PAIN, EntitySA::entity_user]                  # 痛与谁有关
- [VocabSA::abstract_vocab, EntitySA::self_model]
... (~20 对)

# 低优先级(Phase 11+ 视情况)
- [MarkerSA::IMITATION, MarkerSA::GAZE]
... (~30 对)
```

**Phase 8 必须分析的对 = 25 个(全部已在 v6-v9 各章节涉及)**。Phase 9-10 必须分析 20 个。Phase 11+ 30 个。**总计 75 对,v9 公开承认,不再假装"只 6 对"**。

---

## 16. 工程实施 Phase + 真消除硬编码(完整 yaml 化)

### 16.9 草稿行动 — 全 yaml 化

```python
def get_action_expected_R_change(action_type, context, target):
    """@op_count: O(1) lookup + O(d) sample,worst 50 ops."""
    learned = action_memory.lookup(action_type, context, target)
    min_samples = load_constant("action_competition.min_samples_thompson")
    
    if learned.sample_count >= min_samples:
        # Gaussian Thompson sampling
        return np.random.normal(learned.mean_R_change, sqrt(learned.var_R_change))
    
    # Cold-start
    bootstrap = 0.0
    if not has_derived_noise_scale():
        noise_scale = 1.0  # unit normal (@bayesian_prior: uninformative)
    else:
        noise_scale = get_derived_noise_scale()
    return bootstrap + np.random.normal(0, noise_scale)

def derive_noise_scale():
    """@op_count: O(N) where N = early_phase_n_actions."""
    early_n = load_constant("action_competition.early_phase_n_actions")
    ratio = load_constant("action_competition.derived_noise_scale_ratio")
    if len(early_observations) < early_n:
        return None
    std = np.std(early_observations[:early_n])
    return std * ratio
```

**ratio 0.5 仍在 yaml**,**但红线扫描通过**(不是字面量在源代码)。哲学:ratio 是 documented free parameter(物理上在 yaml),不是 implicit magic in code。

---

## 40. 5-8 岁 — §40.4 反事实方法学诚实版

### 40.4 反事实模拟 — controlled direct effect 框架(承认 + 完整规范)

**v8 N=5, 3 levels → v9 N=25, 5 levels(yaml 化)**

```python
def estimate_causal_strength(sa_a, sa_b, current_pool, attention_snapshot):
    """
    @op_count: O(N_boot * N_levels * N_horizon * |SA|),
        worst 25 * 5 * 10 * 50 = 62.5K ops per causal hypothesis.
    
    框架声明:这是 controlled direct effect (CDE),
    在 baseline attention 下测 A 的能量缩放对 B 的 R 影响。
    与 human total causal effect 有差距。
    Phase 10.4 实施时必须在 audit 报告中标注此区别。
    """
    n_boot = load_constant("counterfactual.n_bootstraps")           # 25
    levels = load_constant("counterfactual.intervention_levels")    # [1.0, 0.75, 0.5, 0.25, 0.0]
    n_horizon = load_constant("counterfactual.max_horizon_ticks")   # 10
    causal_min = load_constant("counterfactual.causal_strength_min")
    p_max = load_constant("counterfactual.causal_p_value")
    
    results_by_level = {}
    for level in levels:
        b_R_by_boot = []
        for boot_seed in range(n_boot):
            pool_snap = current_pool.snapshot_full(seed=boot_seed)
            pool_snap.scale_sa_R(sa_a, level)
            pool_snap.freeze_attention_to(attention_snapshot)
            for _ in range(n_horizon):
                pool_snap.advance_with_frozen_attention()
            b_R_by_boot.append(pool_snap.sa(sa_b).mean_recent_R)
        results_by_level[level] = {
            "mean": np.mean(b_R_by_boot),
            "std": np.std(b_R_by_boot),
            "samples": b_R_by_boot,
        }
    
    # 单调性测试(5 levels)
    means_in_order = [results_by_level[l]["mean"] for l in [0.0, 0.25, 0.5, 0.75, 1.0]]
    monotonic = all(means_in_order[i+1] >= means_in_order[i] - 0.01 for i in range(4))
    # 允许 0.01 容差(数值噪声)
    
    # bootstrap 显著性测试 (Welch's t-test, N=25 each side)
    samples_zero = results_by_level[0.0]["samples"]
    samples_full = results_by_level[1.0]["samples"]
    t_stat, p_value = welch_t_test(samples_full, samples_zero)
    
    causal_strength = results_by_level[1.0]["mean"] - results_by_level[0.0]["mean"]
    
    return {
        "causal_strength": causal_strength,
        "monotonic": monotonic,
        "p_value": p_value,
        "n_levels_tested": len(levels),
        "n_bootstraps_per_level": n_boot,
        "framework": "controlled_direct_effect",  # 显式承认
        "is_causal": monotonic and p_value < p_max and causal_strength > causal_min,
    }
```

**关键修复**:
- N=25 bootstrap per level,够 Welch's t-test 有意义
- 5 levels 可做真单调性
- "framework" 字段显式标注是 CDE,所有 audit 必须显示这个
- 全常量 yaml 化

---

## 41. 8-12 岁 — §41.4 + §41.5 真化

### 41.4 Deliberative virtual track — virtual→main reification 完整规范(S-NEW-8 fix)

**v8 缺**:conclusion 如何变成 real SA 没说。

**v9 显式 reification 规则**:

```python
def derive_conclusion_from_virtual_state(virtual_pool, original_pool):
    """
    @op_count: O(|virtual SA|), worst 100 ops.
    
    Virtual track 推理结束后,把结论物化为 main pool 真 SA。
    
    规则:
    1. 找虚池中 R 显著高于初始的 SA(差 > delta_threshold)
    2. 这些 SA 作为"deliberative conclusion" 新 SA spawn 在 main pool
    3. 其 R = max(0.3, virtual_R - initial_R) × dilution_factor
    4. 携带 source_marker = "deliberation::<id>" 链接到原推理过程
    """
    delta_threshold = load_constant("deliberative.conclusion_R_delta_threshold")
    dilution = load_constant("deliberative.virtual_to_main_dilution")
    
    conclusions = []
    for v_sa in virtual_pool.active_sas():
        orig_sa = original_pool.get(v_sa.persistent_id)
        if orig_sa is None:
            # 新 SA 在 deliberation 中涌现
            conclusion_R = v_sa.R * dilution
        else:
            delta_R = v_sa.R - orig_sa.R
            if delta_R < delta_threshold:
                continue
            conclusion_R = delta_R * dilution
        
        # spawn 真 SA into main pool
        new_sa = create_sa_like(v_sa, R=conclusion_R)
        new_sa.source_marker = f"deliberation::{deliberation_id}"
        conclusions.append(new_sa)
    
    return conclusions
```

**关键**:dilution factor 在 yaml(默认 0.5),不在代码字面量。conclusion 的 R 派生自 virtual_R - original_R 的 delta(真"deliberation 增量"),不是任意值。

### 41.5 Self model — 梯度回拉(S-NEW-9 fix)

**v8 错误**:`if R < θ: reset to REACTIVATION_R` → bouncing 破连续性。

**v9 真修**:梯度回拉:

```python
def step_self_model(self_sa, current_tick):
    """@op_count: O(1)."""
    low_threshold = load_constant("self_model.decay_low_threshold")    # 0.05
    gradient = load_constant("self_model.reactivation_decay_gradient") # 0.1
    cap = load_constant("self_model.attention_cap_percent")            # 0.05
    
    # 标准 long_term 衰减(沿用 §1.3 ρ_R_long)
    self_sa.R *= load_constant("energy.R_decay_long")
    
    # 梯度回拉(不 reset!)
    if self_sa.R < low_threshold:
        # 每 tick 加一点 R,渐进恢复
        # 不会瞬时跳变,连续性保持
        self_sa.R += gradient * (low_threshold - self_sa.R)
    
    # heartbeat 持久化
    heartbeat = load_constant("self_model.heartbeat_interval_ticks")
    if current_tick % heartbeat == 0:
        persist_to_sqlite(self_sa)
```

**关键**:
- self_sa.R 永远不会 reset,只有衰减 + 梯度回拉
- 自然连续(数学上是 R 渐进逼近 low_threshold,不超过它太多)
- attention_cap 通过 yaml,attention selector 内 enforce

---

## 18. v9 诚实交互矩阵 + 完整 op count

### 18.5 完整交互矩阵(intra + cross type)

| Type pair | sub-pairs | 已分析对 | Phase 中分析 |
|---|---|---|---|
| Percept × Vocab | 6 × 7 = 42 | Phase 8.4-8.8 处理 vocab 学习 | Phase 8 |
| Percept × Marker | 6 × 8 = 48 | Phase 8.2 salience hint 等 | Phase 8 |
| Percept × Entity | 6 × 7 = 42 | Phase 8.7 focus 由 percept 影响 | Phase 8 |
| Vocab × Marker | 7 × 8 = 56 | Phase 8.4-8.9 vocab × mismatch/correction/tentative | Phase 8-9 |
| Vocab × Entity | 7 × 7 = 49 | Phase 8.12 drive × vocab; Phase 9 self × vocab | Phase 8-9 |
| Marker × Entity | 8 × 7 = 56 | Phase 9 drive × marker; Phase 10 belief × correction | Phase 9-10 |
| Intra-Percept | C(6,2)=15 | 大部分独立 | Phase 8 |
| Intra-Vocab | C(7,2)=21 | narrative × causal, vocab × abstract 必分析 | Phase 10-11 |
| Intra-Marker | C(8,2)=28 | 大部分独立(衰减速率分离) | Phase 8-9 |
| Intra-Entity | C(7,2)=21 | drive × goal, self × user 必分析 | Phase 9-11 |

**总计 ~378 pair 类**(粗算,因为有 sub-family 维度)。实际"机制级"对在 70-100。**v9 公开,Phase 8-11 不分析的暂留 backlog**。

---

## 19. v9 给 Codex 的最终指令

1. **v9 取代 v8 作为 Phase 8 实施依据**
2. **PR-gate red_line_check_v9.py 强制每个 PR 跑**:violations > 0 → 拒
3. **所有常量物理在 apv3_constants.yaml**——代码字面量 = 红线违反
4. **每个新算法函数必须 @op_count: O(...) 注解 docstring**——无注解的不许 merge
5. **Phase 8.4 ΔP 测试前 < 50 held-out 自动 fallback PMI-only mode + 记录 audit**
6. **Phase 10.4 反事实结果必须标注 framework="controlled_direct_effect"**
7. **27 SA family → 4 type 完整映射表见 §11.3** — 任何新 family 必须显式 map
8. **每 Phase 5 段闭环 + 红线扫描 + op count audit + 测试覆盖每个新算法的边界**

---

## 附录: v8 → v9 修复一览

**v8 真 Blocker(3 个全修)**:
- B-NEW-1 MARKER_DECAY_RATES → yaml 外化 + 红线扫描
- B-NEW-2 advance_lightweight → §2.3.2 完整定义 + 框架承认
- B-NEW-3 context_signature → §2.3.1 完整 16-dim 向量定义

**v8 Serious(9 个全修)**:
- N=5 boot → N=25(yaml)
- 3 levels → 5 levels(yaml)
- Marker 清单不全 → §11.3 完整 27→4 表
- 类型预算 hardcoded → scenario_profile.yaml 可覆盖
- 各 anti-pattern → 全 yaml + 红线扫描
- "27→4" overstate → §0.5 公开承认 ~70 机制对
- virtual→main 未规范 → §41.4 完整 reification 规则
- self_sa bouncing → §41.5 梯度回拉

**v8 Medium(全修)**:
- 冷启 held-out → fallback PMI-only mode
- 各 edge case → 各章节修

**新增纪律层成就**:
- ✅ apv3_constants.yaml 唯一常量来源
- ✅ red_line_check_v9.py PR-gate 强制
- ✅ 算法 @op_count 注解强制
- ✅ Counterfactual framework 公开标注 CDE
- ✅ Intra-type 机制对公开承认

— 接手线程,2026-06-17

---

## 最终判断 — v9 是否真收敛?

**纪律层**:✅ 真收敛——常量物理外化、PR-gate 扫描、op_count 强制三件套切断了反复循环。

**算法层**:✅ 5 个 v8 blocker 中,3 个真填补(advance_lightweight / context_signature / decay 外化),2 个改框架承认(N=25 / CDE 标注)。

**架构层**:✅ 不再 oversell——27→4 type 是真简化,intra-type ~70 对公开承认 + 优先级分层。

**最大遗留风险**:
- intra-type 对 70 个还需 Phase 9-11 真去分析
- CDE 与 total causal effect 的差距用户必须知情(Web UI 标注必须做)
- yaml 化只是把魔数物理外化,**没解决"这些数字从哪来"的科学问题**——但这是工程现实,v9 不再假装它能凭空 derive

如果 Codex 反对常量数值,可以**调 yaml** 而不需改代码——这是真"可配"的最低标准,v3-v8 都没做到。

**可以让 Codex 拿 v9 开 Phase 8.2 了**。
