# APV3.0 v11 收尾补丁(对 v10 的 5 个精准修复)

日期: 2026-06-17
作者: 接手线程
状态: **轮 7 审阅识别 v10 仍有 3 blocker + 9 serious,但全部是"v10 自我矛盾"或"vapor"性质。审阅建议"小 v11,5 个精准补丁,1-2 小时,然后开工"。本稿就是这 5 个补丁,不重写 v10,只补 patch。**

前身链:v10 → **v11(本补丁)**

**本稿与 v10 配套读**:Codex 实施时以 v10 为主文档,本补丁 5 个 fix 是 v10 的 errata。所有 v10 其他内容不变。

---

## 补丁 1: Marker cap 修(轮 7 G1 修)

### v10 错误

§11.3 写 12 marker kinds 但在备注里说 "SATISFACTION 预留 13 位"。cap=12 + 13 位 = 自相矛盾。

### v11 修复

**Cap 提到 16**,documented 增长协议:

```yaml
# apv3_constants.yaml 修订
marker:
  max_kinds: 16          # ← 从 12 改 16(headroom)
  kinds_v10_documented:  # 已规范的 12 个(可用)
    - NOVELTY
    - TENTATIVE
    - PAIN
    - MISMATCH
    - CORRECTION
    - GAZE
    - JOINT_ATTENTION
    - IMITATION
    - KNOWLEDGE_GAP
    - EMPATHY_RESONANCE
    - TRUST_PROMOTED
    - BOREDOM
  kinds_reserved:        # 预留 4 个(必须经设计稿修订方激活)
    - SATISFACTION
    - SURPRISE_RESIDUAL  # Phase 9 预留 - 与 NOVELTY 互补
    - SELF_REFERENCE     # Phase 11 预留 - meta_cognition 辅助
    - FUTURE_RESERVED    # 未来扩展
```

**红线扫描更新**:`grep "MarkerKind\." runtime/` 必须只匹配 `kinds_v10_documented` 中的值;新增 reserved kind 必须经 PR 审计才能启用。

---

## 补丁 2: AST gate 不与 v10 自身代码冲突(轮 7 A2 A3 D1 修)

### v10 错误

§2.3.1 v10 自己的示例代码里有 `return 0.5 * continuous_sim + 0.5 * mean_jaccard` — `0.5` 不在 AST 白名单,gate 会拒绝 v10 自己的代码。

### v11 修复

**选项 A:把 §2.3.1 的 0.5 也移到 yaml**(推荐,符合 v10 哲学):

```python
# §2.3.1 v11 修订
def context_signature_similarity_v11(sig_a, sig_b):
    """@op_count: O(15 + sum(|set_a| + |set_b|))"""
    weight_continuous = load_constant("context_signature.weight_continuous")  # 0.5
    weight_jaccard = load_constant("context_signature.weight_jaccard")        # 0.5
    
    z_a = z_normalize(sig_a["continuous"], global_stats)
    z_b = z_normalize(sig_b["continuous"], global_stats)
    continuous_sim = cosine_similarity(z_a, z_b)
    
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
    
    return weight_continuous * continuous_sim + weight_jaccard * mean_jaccard
```

```yaml
# apv3_constants.yaml 新增
context_signature:
  weight_continuous: 0.5    # @structural — 加权 50/50 平衡 vector 相似度 + 集合相似度
  weight_jaccard: 0.5       # @structural — 镜像对称
```

**选项 B:AST gate 白名单加 0.5**(不推荐,会持续滋长):

不采纳。**采纳选项 A**。

### v11 AST gate 范围调整

```python
# scripts/red_line_check_v11.py
STRUCTURAL_LITERALS = {
    0, 1, 2, 3, -1, -2,                    # indexing / sign
    0.0, 1.0, -1.0,                          # initialization
    # 注:0.5 不再在白名单(必须 load_constant)
    # 注:10, 100, 1000 也不在白名单(改为必须显式 load_constant("..._max"))
}

# 全部其他数字字面量必须经 load_constant() 加载
```

**实际影响**:Codex 实施时所有 0.5 / 10 / 100 / 1000 等"边界值"也必须经 yaml。这强化了 v10 纪律。

---

## 补丁 3: 常量治理 checker 真实化(轮 7 B1 修)

### v10 错误

§1.5 promises `check_constant_governance.py` 但只给 yaml 描述,无 script body。

### v11 修复

**完整 script**:

```python
# scripts/check_constant_governance_v11.py
import yaml
import re
import sys
from pathlib import Path

REQUIRED_CATEGORIES = {"@structural", "@scenario_tuneable", "@experimental"}

def parse_constants_yaml(path):
    """解析 apv3_constants.yaml,提取每个 leaf 常量 + 注释"""
    raw_lines = Path(path).read_text().splitlines()
    
    leaf_pattern = re.compile(r'^(\s*)([A-Za-z_][A-Za-z_0-9]*)\s*:\s*([0-9.\-+e]+)(.*)$')
    constants = []
    
    for i, line in enumerate(raw_lines):
        m = leaf_pattern.match(line)
        if m:
            indent, key, value, trailing = m.groups()
            # 查 inline 注释 或 上一行注释
            category = None
            rationale = None
            if "#" in trailing:
                comment = trailing.split("#", 1)[1].strip()
                for cat in REQUIRED_CATEGORIES:
                    if cat in comment:
                        category = cat
                if "—" in comment:
                    rationale = comment.split("—", 1)[1].strip()
            
            # 若 inline 无,看上一行
            if not category and i > 0:
                prev = raw_lines[i-1]
                if "#" in prev:
                    prev_comment = prev.split("#", 1)[1].strip()
                    for cat in REQUIRED_CATEGORIES:
                        if cat in prev_comment:
                            category = cat
                            rationale = prev_comment.replace(cat, "").strip()
            
            constants.append({
                "line": i + 1,
                "key": key,
                "value": value,
                "category": category,
                "rationale": rationale,
            })
    
    return constants

def check_governance(yaml_path):
    constants = parse_constants_yaml(yaml_path)
    violations = []
    
    for c in constants:
        # 每个常量必须有 category
        if not c["category"]:
            violations.append(
                f"L{c['line']}: '{c['key']}' = {c['value']} 缺少 category 注释"
                f" (必须有 @structural / @scenario_tuneable / @experimental)"
            )
            continue
        
        # @experimental 必须有 rationale 或 Phase 引用
        if c["category"] == "@experimental":
            if not c["rationale"] or len(c["rationale"]) < 5:
                violations.append(
                    f"L{c['line']}: '{c['key']}' 标 @experimental 但缺 rationale 或 Phase 引用"
                )
        
        # @scenario_tuneable 必须在 scenario_profiles/ 中至少一个有 override
        # (Phase 8.2 实施时启用此检查;v11 当前阶段先 warn 不 fail)
    
    if violations:
        print(f"GOVERNANCE VIOLATIONS ({len(violations)}):")
        for v in violations:
            print(f"  {v}")
        return False
    
    print(f"✓ Governance check passed ({len(constants)} constants)")
    return True

if __name__ == "__main__":
    ok = check_governance("config/apv3_constants.yaml")
    sys.exit(0 if ok else 1)
```

**实际效果**:每常量必须有 `@structural` / `@scenario_tuneable` / `@experimental` 注释,`@experimental` 必须有 rationale。PR-gate 强制。

---

## 补丁 4: causal_strength 范围锚定(轮 7 F1 修)

### v10 错误

`causal_strength_min = 0.05` 没有 R 范围基线 → 无法判断是 5% 还是 noise。

### v11 修复

**显式声明 R 归一化范围 + relative threshold**:

```yaml
# apv3_constants.yaml 新增
energy:
  R_normalization_invariant: "R values bounded to [0.0, 1.0] within single SA family"
  # 注:状态池任一 SA 的 R 在 [0, 1] 范围内
  # PerceptSA 单 SA R 不超 1.0;聚合时按类型预算限制
  # 这是工程约束,Phase 8.5 验收必须验证

counterfactual:
  # v11 修订:从绝对 threshold 改 relative
  causal_strength_min_relative: 0.10
  # 含义:means[1.0] - means[0.0] 必须 ≥ 0.10 of means[0.0],
  # 即 effect 相对于 baseline 至少 10%
  monotonicity_tolerance: 0.005   # 从 0.01 → 0.005 (轮 7 F2 fix)
```

**实施修改**:

```python
def estimate_causal_strength_v11(sa_a, sa_b, current_pool, attention_snapshot):
    # ... (same as v10) ...
    
    # v11 修订:relative threshold
    baseline_mean = means[0]
    full_mean = means[-1]
    
    strength_min_relative = load_constant("counterfactual.causal_strength_min_relative")  # 0.10
    causal_strength_relative = (full_mean - baseline_mean) / max(baseline_mean, 0.01)
    
    # monotonicity 用更严格 tolerance(0.005)
    tolerance = load_constant("counterfactual.monotonicity_tolerance")
    monotonic = all(means[i+1] >= means[i] - tolerance for i in range(4))
    
    is_causal = monotonic and causal_strength_relative > strength_min_relative
    
    return {
        "causal_strength_absolute": full_mean - baseline_mean,
        "causal_strength_relative": causal_strength_relative,
        "monotonic": monotonic,
        "framework": "controlled_direct_effect",
        "is_causal": is_causal,
    }
```

**这才修对**:
- "10% relative change" 在任何 R 范围下都有意义
- baseline=0.1 时,causal_strength=0.01 already passes(10%)
- baseline=0.5 时,causal_strength=0.05 才 passes(10%)
- 不再依赖任意 absolute threshold

---

## 补丁 5: Tentative vocab "待验证"状态规范(轮 7 I1 修)

### v10 错误

§11.8 状态 5 说"marker 衰减但 vocab 仍存在 → 待验证 state",但红线说 vocab kind 只能在 {tentative, promoted, retracted} 三态。第 4 态"待验证"未定义。

### v11 修复

**显式扩展 vocab kind 到 4 态**:

```yaml
# apv3_constants.yaml 新增
vocab:
  kinds: [tentative, promoted, retracted, awaiting_revalidation]
  # @structural — vocab 生命周期 4 态
  awaiting_revalidation_max_age_ticks: 1000
  # @experimental — 待验证态最长 1000 tick (~100 秒),超过自然 short-term decay
```

```python
# §11.8 状态机 v11 修订
"""
状态 1: tentative_vocab spawn
  vocab.kind = "tentative"
  marker (TENTATIVE) spawn

状态 2: 第二次曝光强化
  vocab.positive_co_observations += 1
  marker.real_energy *= decay

状态 3: 晋升到 promoted
  vocab.confidence > θ_promote
  → vocab.kind = "promoted"
  → marker.retire() (atomic)

状态 4: 反例撤销
  vocab.confidence < θ_retract
  → vocab.kind = "retracted"
  → marker.retire() (atomic)

状态 5: marker 衰减但 vocab 仍存在(轮 7 I1 fix)
  marker.real_energy → 0
  → vocab.kind = "awaiting_revalidation"  (显式 4th 态)
  → vocab 继续在状态池,但不参与 ΔP 评估 / slot 填充
  → 等下一次跨模态曝光:
    - 再现 → 回状态 2(spawn 新 marker)
    - 1000 tick 内无再现 → vocab.kind = "retracted" (自然撤销)
"""
```

**State machine 完整 4 态 + 原子转移**:

```python
class TentativeVocabStateMachine:
    """@op_count: O(1) per transition."""
    
    VALID_KINDS = ["tentative", "promoted", "retracted", "awaiting_revalidation"]
    
    def transition_atomic(self, vocab, new_kind, marker):
        """状态转移必须原子:vocab + marker 同时改"""
        assert new_kind in self.VALID_KINDS
        
        # 模拟事务(state pool 无 native transactions, 用临时 transaction log)
        with state_pool.transaction_log() as log:
            log.record_before(vocab)
            log.record_before(marker) if marker else None
            
            old_kind = vocab.kind
            vocab.kind = new_kind
            
            if new_kind == "promoted":
                # marker 必 retire
                if marker:
                    state_pool.retire(marker)
            elif new_kind == "retracted":
                # marker 必 retire + 触发 cascade(§2.7)
                if marker:
                    state_pool.retire(marker)
                cascade_retire_vocab_refs(vocab)
            elif new_kind == "awaiting_revalidation":
                # marker 已自然衰减完,vocab 进入 dormant
                vocab.dormant_since_tick = current_tick
            
            log.commit()
```

**"状态池无 native transaction"承认**:用 transaction_log 模式(类 SQLite WAL),Codex Phase 8.3 实施时必须做此抽象。

---

## v11 完整工程清单(Codex 实施前必读)

### 5 个 patches 必须落地

1. **补丁 1**: `apv3_constants.yaml` marker.max_kinds 改 16 + kinds_reserved
2. **补丁 2**: 把 0.5 / 10 / 100 / 1000 等也移到 yaml,AST 白名单收紧到 {0,1,2,3,-1,-2,0.0,1.0,-1.0}
3. **补丁 3**: 落地 `check_constant_governance_v11.py`(完整 script 已给)
4. **补丁 4**: causal_strength 改 relative + R_normalization_invariant 声明
5. **补丁 5**: vocab.kinds 加 "awaiting_revalidation" + 状态机原子转移

### Phase 8.2 启动前的清单

```
[ ] config/apv3_constants.yaml 落地(含 v10 + v11 补丁的所有常量)
[ ] config/constants_governance.yaml 落地(描述 3 类 + 协议)
[ ] scripts/red_line_check_v10.py + v11 patches 上 PR-gate
[ ] scripts/check_constant_governance_v11.py 上 PR-gate
[ ] scripts/check_op_count_annotations.py 上 PR-gate
[ ] config/scenario_profiles/text_dialogue.yaml 创建(至少一个 scenario override 示例)
[ ] Phase 8 红线扫描脚本完整 + 每个 PR 必跑
[ ] family_to_type_mapping_v10.yaml 落地(含 ControlSignalSA + 13 marker kinds)
```

### v11 后已知可接受的 risk(实施中迭代,不阻塞)

| 风险 | 处理时机 |
|---|---|
| ΔP horizon=5 漏掉 long-form vocab | Phase 8.5 增加"long-form complementary gate"(轮 7 C1) |
| HeldOutPool 冷启 500 候选偏 earliest | Phase 9 实测后改 reservoir 参数 |
| Tolerance 0.005 仍可能容忍噪声 | Phase 10.4 校准时收紧 |
| ControlSignalSA 5% 预算可能不够 | Phase 8.2 实测后调 |
| z-normalize 冷启动 global_stats 空 | Phase 8.3 实施时 fallback unit normal |
| Reservoir fixed seed 42 多实例同步 | 多实例部署时改 seed 策略 |

---

## 最终结论

**v10 + v11 patches = 可开工的设计基础**

v3-v11 经 7 轮对抗审阅:
- v3 设计稿初版
- v4-v10 各轮每轮发现并修 8-22 个问题
- v11 是清理 v10 自我矛盾,5 个精准补丁

**所有 v10 + v11 内容综合后**:
- 纪律层:AST gate + governance checker + op_count + family map + R 范围声明
- 算法层:ΔP horizon 5、Reservoir、Effect-size only、Jaccard + z-norm、Two-phase credit、Lag-PMI
- 架构层:5 types + 16 marker kinds cap + 完整 family map + 类型预算

**Codex 现在拿 v10 + v11 开 Phase 8.2,可以了**。

后续 Phase 中如发现新问题,在 Phase 闭环报告中提出 + 通过 PR 修补 yaml/code,**不再开新设计稿**。设计稿 v11 是收尾版。

---

— 接手线程,2026-06-17
