# APV3.0 Phase 13 — v3.2b + v3.3a 合并 Errata

日期: 2026-06-18
作者: 银子老师 / Claude
状态: **Codex 第五轮对抗审阅识别 7 个问题。本 Errata 是 v3.2a + v3.3 的精准补丁,根治每条问题(其中 3 条是 v3.2a/v3.3 自己造成的自相矛盾或灾难性设计漏洞)。Codex 实施依据 = v3 + v3.1 + v3.2 + v3.2a + v3.3 + v3.2b/3.3a(本稿)六稿合一。**

前作:
- [v3.2a Landing Errata](Design_APV3.0_Phase13_CognitiveCurriculum_v3_2a_LandingErrata_20260618.md)
- [v3.3 数学详细设计稿](Design_APV3.0_Phase13_5b_MathCurriculum_v3_3_20260618.md)

许可:AGPL-3.0-or-later
原架构设计:银子老师

---

## 0. v3.2b/3.3a 修复总览

| 编号 | 类型 | 来源 | 问题 | 严重度 |
|---|---|---|---|---|
| **E1** | v3.2b | v3.2a F2 | 伪匿名 ID 输入编码未标准化(tuple 用 `str` 会泄结构) | SERIOUS |
| **E2** | v3.2b | v3.2a F4 | PENDING_PERCEIVED_REVALIDATION 撑爆 marker cap=20 | BLOCKER |
| **E3** | v3.2b | v3.2a F4 | `trust_promoted_pending_perceived: bool` 字段示例违 v14 红线 | BLOCKER |
| **E4** | v3.2b | v3.2a F6 | held-out event_id 可能含语义(隐性泄漏) | SERIOUS |
| **E5** | v3.2b | v3.2a F5 | metadata 红线 AST 不全(漏 dict table 两步路由 / getattr) | SERIOUS |
| **E6** | v3.3a | v3.3 §4 | **数学坐标模仿泄漏(BLOCKER!)** — expected_action_sequence 给固定坐标表,系统会背坐标不学范式 | **CRITICAL BLOCKER** |
| **E7** | v3.3a | v3.3 §4.2 | "column_sum >= 10" 触发进位违反"从事实涌现"承诺 | BLOCKER |
| **E8** | v3.3a | v3.3 §1.3 | 自己读草稿 vs 外部视觉 PERCEIVED 混类(Q 表污染) | SERIOUS |

**3 个 BLOCKER + 4 个 SERIOUS + 1 个 CRITICAL BLOCKER(数学坐标泄漏是设计灾难)**。

---

## 第 1 章 E1 — 伪匿名 ID 输入编码标准化

### 1.1 v3.2a 错在哪

```python
# v3.2a (错):
def compute_pseudonymous_identifier(text: str, state_dir: Path) -> str:
    salt = get_or_create_install_salt(state_dir)
    h = hmac.new(salt, text.encode("utf-8"), hashlib.sha256)
    return h.hexdigest()[:16]
```

调用方:
```python
# minimalist_dialogue_flow.py / chat.py / web_chat.py
incoming_external_query: tuple[str, ...]
trace["incoming_query_hash"] = compute_pseudonymous_identifier(
    str(incoming_external_query)  # ← 这里用 str(tuple) 灾难
)
```

`str(("你好", "在吗"))` = `"('你好', '在吗')"`,这意味着:
- 引号、逗号、括号都进了 hash 语义
- `["你好", "在吗"]` 和 `("你好", "在吗")` hash 不同(虽然内容一样)
- 升级 Python 后 repr 格式变化 → hash 完全变(不可迁移)
- 攻击者反推时,带括号格式比纯文本更易猜

### 1.2 v3.2b 根治:JSON canonicalization

```python
# apv3test/util/pseudonymous_id.py v3.2b

from typing import Sequence, Union
import json


# v3.2b: 显式 schema 版本,未来升级时不破历史 hash
_CANONICAL_SCHEMA_VERSION = "v1"


def _canonicalize_input(
    text_or_seq: Union[str, Sequence[str]],
) -> str:
    """
    v3.2b: 把任意 text/tuple/list 输入规范化为不可歧义 JSON 字符串.
    
    保证:
    - tuple/list 视为同一(都序列化为 array)
    - 字符串 list ['hello'] 与单字符串 'hello' 不同(不歧义)
    - JSON 序列化不依赖 Python repr 格式
    - schema_version 嵌入,未来升级有据可查
    """
    if isinstance(text_or_seq, str):
        normalized = {
            "schema": _CANONICAL_SCHEMA_VERSION,
            "kind": "scalar",
            "value": text_or_seq,
        }
    elif isinstance(text_or_seq, (tuple, list)):
        # 强制成 list,避免 tuple/list 歧义
        normalized = {
            "schema": _CANONICAL_SCHEMA_VERSION,
            "kind": "sequence",
            "values": [str(v) for v in text_or_seq],
        }
    else:
        raise TypeError(
            f"compute_pseudonymous_identifier expects str or Sequence[str], "
            f"got {type(text_or_seq).__name__}"
        )
    
    # canonical JSON: sort_keys + ensure_ascii=False + separators
    return json.dumps(
        normalized,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )


def compute_pseudonymous_identifier(
    text_or_seq: Union[str, Sequence[str]],
    state_dir: Path = Path("state"),
) -> str:
    """
    v3.2b: 输入先经 _canonicalize_input,再走 HMAC.
    """
    canonical = _canonicalize_input(text_or_seq)
    salt = get_or_create_install_salt(state_dir)
    h = hmac.new(salt, canonical.encode("utf-8"), hashlib.sha256)
    return h.hexdigest()[:16]
```

### 1.3 必修测试

```python
def test_tuple_and_list_with_same_content_produce_same_id():
    """tuple ('a', 'b') 和 list ['a', 'b'] 应 hash 一样."""
    id_tuple = compute_pseudonymous_identifier(("a", "b"))
    id_list = compute_pseudonymous_identifier(["a", "b"])
    assert id_tuple == id_list


def test_str_and_singleton_list_differ():
    """字符串 'hello' 和 ['hello'] 不同."""
    id_str = compute_pseudonymous_identifier("hello")
    id_list = compute_pseudonymous_identifier(["hello"])
    assert id_str != id_list


def test_canonical_unaffected_by_repr_format():
    """input format 不应影响 hash."""
    id_a = compute_pseudonymous_identifier(("你好",))
    # 即使 Python repr 改了,canonicalize 后仍稳定
    canonical = _canonicalize_input(("你好",))
    assert "schema" in canonical
    assert "v1" in canonical


def test_unicode_in_canonical_does_not_escape():
    """中文不被 \\u 转义,保持人可读 + 一致."""
    canonical = _canonicalize_input("你好")
    assert "你好" in canonical
    assert "\\u" not in canonical
```

---

## 第 2 章 E2 — PENDING_PERCEIVED_REVALIDATION 不撑爆 cap

### 2.1 v3.2a 错在哪

v3.2a F4 写"MarkerKind.PENDING_PERCEIVED_REVALIDATION 加入 v14 documented kinds(扩 cap)"

但实际 `config/family_to_type_mapping.yaml`:

```yaml
MarkerSA:
  description: "瞬态状态标记(v14.1: cap 20 = documented 17 + reserved 3)"
  kinds_documented:  # 17 个
    - NOVELTY / TENTATIVE / PAIN / MISMATCH / CORRECTION
    - PERCEIVED / IMAGINED / HEARSAY / REMEMBERED / INFERRED
    - GAZE / JOINT_ATTENTION / IMITATION / KNOWLEDGE_GAP / EMPATHY_RESONANCE
    - TRUST_PROMOTED / BOREDOM
  kinds_reserved:  # 3 个
    - SATISFACTION / SURPRISE_RESIDUAL / SELF_REFERENCE
```

cap 严格 20。"加入 documented kinds"实际意思:**消耗一个 reserved**。但 v3.2a 没说消耗哪个,也没分析合并可能性。

### 2.2 v3.2b 三选一方案

**v3.2b 不引入新 marker kind**,而是**复用既有 CORRECTION marker + status 字段**:

#### 方案分析

| 方案 | 影响 | 我的判断 |
|---|---|---|
| 消耗 reserved(如 SURPRISE_RESIDUAL) | 永久占用 1 reserved 位 | ❌ 浪费宝贵 reserved |
| 移除/合并旧 marker | 影响其他 phase | ❌ 破坏既有 |
| **复用 CORRECTION marker + status** | 0 新增,语义清晰 | ✅ 采纳 |
| 重证 cap → 21 | 改架构主稿 | ❌ 不应为此扩 cap |

#### v3.2b 实施:复用 CORRECTION marker

CORRECTION marker 既有语义"系统行动后用户给负反馈"。

v3.2b 把"教师纯 HEARSAY 冲突,等待 PERCEIVED revalidation"也归入 CORRECTION,**用 marker 的 metadata.status 字段区分**:

```python
class CorrectionMarkerStatus(Enum):
    """CORRECTION marker 的 status,经 marker.metadata 携带."""
    SYSTEM_COMMIT_REJECTED = "system_commit_rejected"  # 原有用法(Phase 8.9)
    PENDING_PERCEIVED_REVALIDATION = "pending_perceived_revalidation"  # v3.2b 新增


def spawn_correction_marker_for_pending_revalidation(
    *,
    target_vocab_sa_id: str,
    tick: int,
    conflicting_teacher_ids: list[str],
) -> MarkerSA:
    """v3.2b: 复用 CORRECTION marker,status 区分."""
    return MarkerSA(
        kind=MarkerKind.CORRECTION,  # 复用,不新建 kind
        target_sa_id=target_vocab_sa_id,
        spawn_tick=tick,
        metadata={
            "status": "pending_perceived_revalidation",  # 字符串字段,不是 bool
            "conflicting_teachers": list(conflicting_teacher_ids),
            "requires_perceived_evidence": True,
        },
    )
```

### 2.3 status 字段的红线扫描

status 是 metadata 字符串字段,会不会违反 v14 "不许 if MarkerKind.X" 红线?

**不会**,因为:
- v14 红线禁止的是 `if marker.kind == MarkerKind.PERCEIVED`(按 kind 路由)
- v3.2b 是 `if marker.metadata.get("status") == "pending..."`(按状态机字段路由)

这两个不同。**状态机 status 字段是允许的**,但要明确扫描:

```python
def check_correction_marker_status_routing_is_explicit():
    """
    扫所有读 CORRECTION marker.metadata.status 的位置.
    
    要求:
    - 在 cognitive/learning 路径中读 status 必须显式处理两种 status
    - 不能假设 status 只有一种
    """
    # AST 扫描 marker.metadata.get("status") 模式
    # 验证调用方明确分别处理 SYSTEM_COMMIT_REJECTED / PENDING_PERCEIVED_REVALIDATION
    ...
```

### 2.4 yaml 不变

```yaml
# config/family_to_type_mapping.yaml — 不修改
MarkerSA:
  kinds_documented: [..., CORRECTION, ...]  # 17 个不变
  kinds_reserved: [SATISFACTION, SURPRISE_RESIDUAL, SELF_REFERENCE]  # 3 个不变
  # cap 仍 20,无新增
```

---

## 第 3 章 E3 — 删除 `trust_promoted_pending_perceived: bool` 字段示例

### 3.1 v3.2a 自相矛盾

v3.2a §4.4 同一段:

文字说:"v3.2a 不在 VocabSA 加 bool,改 spawn 单独 marker"

但代码示例:
```python
# v3.2a §4.2 实际给的代码
@dataclass
class ConflictResolution:
    ...
    trust_promoted_pending_perceived: bool = False  # ← bool 字段
```

**自相矛盾**。实现者很容易照抄这个 bool。

### 3.2 v3.2b 根治

删除 bool 字段。`ConflictResolution` 改用 marker 链接:

```python
# v3.2b
@dataclass
class ConflictResolution:
    """v3.2b: 不含 bool 字段,所有状态信息经 marker."""
    attribute_value: Optional[str]
    status: str  # str enum 而非 bool: "resolved_by_perceived" / "provisional_official_pending_perceived" / "awaiting_revalidation"
    correction_marker_id: Optional[str] = None  # 关联到 spawn 的 CORRECTION marker
    
    # 不再有:
    # ~trust_promoted_pending_perceived: bool = False~  # 删
    # ~requires_revalidation: bool = True~  # 用 status 推断
```

### 3.3 status 值规范

```python
class ConflictResolutionStatus(str, Enum):
    """字符串枚举,可序列化."""
    RESOLVED_BY_PERCEIVED = "resolved_by_perceived"
    PROVISIONAL_OFFICIAL_PENDING_PERCEIVED = "provisional_official_pending_perceived"
    AWAITING_REVALIDATION = "awaiting_revalidation"
```

### 3.4 红线扫描

```python
def test_no_bool_fields_with_trust_or_perceived_in_name():
    """v3.2b 红线:不许 bool 字段含 trust/perceived."""
    import ast
    for py_file in glob("runtime/cognitive/**/*.py"):
        tree = ast.parse(open(py_file).read())
        for node in ast.walk(tree):
            if isinstance(node, ast.AnnAssign):
                if isinstance(node.annotation, ast.Name) and node.annotation.id == "bool":
                    if isinstance(node.target, ast.Name):
                        name = node.target.id
                        forbidden_words = ["trust_promoted", "pending_perceived", "is_promoted", "is_pending"]
                        for word in forbidden_words:
                            assert word not in name, \
                                f"{py_file}: bool field '{name}' violates v14 no-bool-state rule"
```

---

## 第 4 章 E4 — held-out event_id 必须 opaque

### 4.1 v3.2a 错在哪

v3.2a F6 写 `_external_evaluator_meta[event.event_id] = evaluator_metadata`,但**没规定 event_id 必须 opaque**。

如果实现时 event_id = `"holdout_cat_image_005"`,等于把"这是猫的图"信息编码进 id。系统看到 id 字符串,即使不读 metadata,也能从 id 猜目标。

### 4.2 v3.2b 根治:opaque random id

```python
# runtime/cognitive/curriculum/held_out_pool.py v3.2b

import secrets


def _generate_opaque_event_id() -> str:
    """v3.2b: 随机不可预测 id,无语义."""
    # 128 bit 随机,base32 编码 → 26 字符
    return secrets.token_hex(16)  # 32 hex chars


class HeldOutEventPool_v3_2b:
    def add_during_curriculum(
        self,
        event: NormalizedSAEvent,
        evaluator_metadata: EvaluatorMetadata,
        k_fold_index: int,
    ):
        # v3.2b: 强制 event.event_id 必须是 opaque random
        if not self._is_opaque_id(event.event_id):
            # 如果不是,自动生成新 opaque id 覆盖
            event = event.replace(event_id=_generate_opaque_event_id())
        
        # 严格检查
        assert event.is_raw_normalized_sensor_event()
        assert not event.contains_vocab_label()
        assert not event.contains_proposition()
        
        if k_fold_index % K_FOLD == 0:
            self.held_out_events.append(event)
            self._external_evaluator_meta[event.event_id] = evaluator_metadata
    
    @staticmethod
    def _is_opaque_id(event_id: str) -> bool:
        """检查 id 是否是 opaque random."""
        # opaque id = 32 字符 hex,无人类可读语义
        import re
        return bool(re.match(r"^[0-9a-f]{32}$", event_id))
```

### 4.3 stratified 抽样(Codex 提的额外点)

v3.2a sample 是纯随机 — Codex 指出"稀有类 effect_size 不稳定"。

v3.2b 加 stratified 选项,**由外部 evaluator 决定分层策略**(不传 vocab_sa_id 给 AP):

```python
def sample_probe_events_for_evaluation_v3_2b(
    self,
    n: int,
    *,
    stratification_keys: Optional[list[str]] = None,
) -> list[NormalizedSAEvent]:
    """
    v3.2b: 支持 stratified sampling.
    
    stratification_keys 由外部 evaluator 传入(如 "is_rare" / "complexity_high"),
    AP 不知道这些 key 的语义,只用作 group key.
    """
    if stratification_keys is None:
        # 默认纯随机
        return random.sample(self.held_out_events, min(n, len(self.held_out_events)))
    
    # 按 stratification_keys 分组,每组按比例采
    grouped = defaultdict(list)
    for event in self.held_out_events:
        meta = self._external_evaluator_meta.get(event.event_id)
        if meta:
            # group key 是 evaluator 提供的,AP 不解析含义
            group_key = tuple(meta.attributes.get(k, "") for k in stratification_keys)
            grouped[group_key].append(event)
    
    # 比例抽样
    samples = []
    per_group = max(1, n // len(grouped))
    for group, events in grouped.items():
        samples.extend(random.sample(events, min(per_group, len(events))))
    
    return samples[:n]
```

---

## 第 5 章 E5 — metadata 红线 AST 扩展

### 5.1 v3.2a 漏掉的模式

Codex 指出 4 种漏扫场景:

```python
# 漏 1: 两步 dict route
table = {"default": foo, "rare_warmth": bar}
result = table[style_tag]  # ← AST scanner 看不到 if/match,漏

# 漏 2: getattr 动态访问
selected = getattr(self, style_tag, default)  # ← 漏

# 漏 3: apv3test runtime 也是 routing 风险点(但 v3.2a 只扫 runtime/cognitive 和 apv3test/runtime)
# v3.2a 实际只扫两个目录,漏掉 apv3test 其他

# 漏 4: 前端 JS 也可能把 tag 当 behavior switch
if (this.styleTag === "default_quiet") { ... }  # JS 端
```

### 5.2 v3.2b 增强 AST scanner

```python
# scripts/red_line_check_v14.py 扩展 v3.2b

class MetadataRoutingDetector_v3_2b(ast.NodeVisitor):
    """v3.2b 完整 4 种 routing 模式."""
    
    def __init__(self):
        self.violations = []
        self.assigned_dicts = {}  # 跟踪 dict 赋值,检测两步路由
    
    # 既有模式(v3.2a)
    def visit_Compare(self, node): ...  # if x == "literal"
    def visit_Match(self, node): ...  # match-case
    def visit_Call(self, node): ...  # .get("literal")
    def visit_Subscript(self, node): ...  # dict["literal"]
    def visit_Attribute(self, node): ...  # obj.context_tag
    
    # v3.2b 新增模式
    def visit_Assign(self, node):
        """跟踪 table = {"default": foo} 赋值."""
        if isinstance(node.value, ast.Dict):
            # 检查 dict keys 是否含 forbidden literal
            for key in node.value.keys:
                if isinstance(key, ast.Constant) and key.value in FORBIDDEN_LITERALS_IN_CHOICE:
                    # 记录这个 dict 名字 → 后续看是否被 metadata 字段索引
                    if isinstance(node.targets[0], ast.Name):
                        self.assigned_dicts[node.targets[0].id] = node.lineno
        self.generic_visit(node)
    
    def visit_Subscript_v3_2b(self, node):
        """既有 + 检测 dict[metadata_field] 模式."""
        # 既有:dict["literal"]
        if isinstance(node.slice, ast.Constant) and node.slice.value in FORBIDDEN_FIELDS_IN_LOGIC:
            self.violations.append(f"L{node.lineno}: subscript")
        
        # v3.2b 新增:table[style_tag] 两步路由
        if isinstance(node.value, ast.Name) and node.value.id in self.assigned_dicts:
            # 索引来自 metadata 字段?
            if isinstance(node.slice, ast.Name) and node.slice.id in FORBIDDEN_FIELDS_IN_LOGIC:
                self.violations.append(
                    f"L{node.lineno}: two-step routing via dict[{node.slice.id}] "
                    f"(dict at L{self.assigned_dicts[node.value.id]})"
                )
            # 或者 dict[obj.metadata_field]
            if isinstance(node.slice, ast.Attribute) and node.slice.attr in FORBIDDEN_FIELDS_IN_LOGIC:
                self.violations.append(
                    f"L{node.lineno}: two-step routing via dict[obj.{node.slice.attr}]"
                )
        self.generic_visit(node)
    
    def visit_Call(self, node):
        """既有 .get + v3.2b 新增 getattr."""
        # 既有 .get("literal")
        if isinstance(node.func, ast.Attribute) and node.func.attr == "get":
            ...
        
        # v3.2b 新增:getattr(obj, "metadata_field_literal")
        if isinstance(node.func, ast.Name) and node.func.id == "getattr":
            if len(node.args) >= 2 and isinstance(node.args[1], ast.Constant):
                if node.args[1].value in FORBIDDEN_FIELDS_IN_LOGIC:
                    self.violations.append(
                        f"L{node.lineno}: getattr(obj, '{node.args[1].value}') - check usage"
                    )
            # getattr(obj, variable_name) — 动态访问也可疑
            if len(node.args) >= 2 and isinstance(node.args[1], ast.Name):
                if node.args[1].id in FORBIDDEN_FIELDS_IN_LOGIC:
                    self.violations.append(
                        f"L{node.lineno}: getattr(obj, {node.args[1].id}) - dynamic access"
                    )
        self.generic_visit(node)


def check_no_metadata_routing_v3_2b():
    """v3.2b: 扫描范围扩大,白名单显式."""
    all_violations = []
    
    # v3.2b: 扫描整个 apv3test + runtime/cognitive,白名单 render/audit
    target_dirs = [
        Path("runtime/cognitive"),
        Path("apv3test"),  # ← v3.2b 扩,不只扫 runtime/
    ]
    
    # 白名单显式
    WHITELIST_PATTERNS = [
        "/audit",
        "/render",
        "/web/static",  # 前端 JS 暂不扫(单独 JS 红线)
        "trace_format",
        "/__pycache__",  # 跳过 cache
    ]
    
    for target_dir in target_dirs:
        if not target_dir.exists():
            continue
        for py_file in target_dir.rglob("*.py"):
            if any(p in str(py_file) for p in WHITELIST_PATTERNS):
                continue
            
            try:
                tree = ast.parse(py_file.read_text(encoding="utf-8"))
            except SyntaxError:
                continue
            
            detector = MetadataRoutingDetector_v3_2b()
            detector.visit(tree)
            
            for v in detector.violations:
                all_violations.append(f"{py_file}:{v}")
    
    return all_violations
```

### 5.3 前端 JS 单独红线(简单 grep)

```bash
# scripts/check_frontend_no_metadata_routing.sh
# 扫前端 JS,禁 metadata 字段当 switch

grep -rn "styleTag\|context_tag\|design_note" apv3test/web/static/ 2>&1 | \
    grep -v "// audit" | \
    grep -E "(if|switch|case)" && \
    { echo "Frontend metadata routing detected"; exit 1; } || \
    echo "OK: Frontend clean"
```

---

## 第 6 章 E6 — 数学坐标模仿泄漏(CRITICAL BLOCKER)

### 6.1 v3.3 的灾难性错误

v3.3 §4.1 给 expected_action_sequence:

```yaml
teaching_episodes:
  - input: {a: 23, b: 47}
    expected_action_sequence:
      - {action: "write_at_grid", row: 0, col: 2, char: "2"}  # ← 固定坐标
      - {action: "write_at_grid", row: 0, col: 3, char: "3"}
      - {action: "write_at_grid", row: 1, col: 0, char: "+"}
      - ...
```

**这是设计灾难**。原因:

1. **教学给的是固定坐标表**(row=0, col=2)→ 系统会 SDPL 学到 packet (23+47) → action chain with these exact coordinates
2. 真正学的是"在固定坐标背答案",**不是学竖式范式**
3. 换个 grid size 或换个数字宽度(456+789 vs 23+47)→ 系统完全不会
4. 这正是 LLM 套壳的反面教材

### 6.2 v3.3a 根治:相对空间 + 范式不变量

#### 6.2.1 教学策略改变

**不教坐标**,教**范式不变量**:

```yaml
# v3.3a 正确教学方式
package_id: "math.2b_grid_vertical_generation_v3_3a"
description: "竖式加法 - 经相对空间范式 emerge,无固定坐标"

content:
  - sa_id: "paradigm::grid_vertical_addition_invariants"
    description: |
      竖式加法的范式不变量(必学,不变):
      1. 两个数字垂直对齐(个位与个位对齐,十位与十位对齐)
      2. 运算符号(+)在第二个数的左侧
      3. 横线在两个数下方
      4. 答案在横线下方
      5. 从右往左逐位计算
    
    invariants_yaml:
      - {kind: "alignment", description: "ones_digit_aligns_with_ones_digit"}
      - {kind: "operator_position", description: "operator_left_of_second_operand"}
      - {kind: "separator", description: "horizontal_line_separates_operands_and_result"}
      - {kind: "computation_direction", description: "right_to_left_column_order"}
    
    # 教学时随机化坐标 + 数字宽度,迫使学范式不变量
    teaching_episodes_randomized:
      randomization_protocol:
        digit_width: {min: 1, max: 4}  # 单位数到四位数
        grid_origin_row: {min: 0, max: 3}  # 起始行随机
        grid_origin_col: {min: 0, max: 5}  # 起始列随机
        spacing_between_operands_and_line: {min: 0, max: 2}
      
      # 每次教学随机生成 grid layout,系统看到的是结构而非坐标
      example_random_episode_1:
        a: 23
        b: 47
        chosen_origin: {row: 2, col: 4}  # 这次随机选
        chosen_spacing: 1
        # 实际 grid:
        #   行 2 列 4-5: "23"
        #   行 3 列 3-5: "+47"   (+ 在 col 3, 47 在 col 4-5)
        #   行 4 列 3-5: "───"
        #   行 5 列 3-5: "070"   (答案 70,带前导空格)
        
        # 教学不给 expected_action_sequence(那是固定坐标)
        # 教学只给:
        teacher_demonstration: |
          "看,这是竖式。我们把 23 写在这里(指),把 47 写在下面对齐(指),
          画横线,从右往左算个位:3+7=10,写 0 进 1;
          再算十位:2+4+1=7,写 7。答案是 70。"
        
        # 教师的 "指" 走 visual percept,系统看到的是"指着这个位置"
        # 系统经多次随机 origin 教学,
        # 经 hierarchy SA 涌现"竖式对齐"范式(不绑定具体坐标)
      
      # 强制至少 N 次不同 origin/spacing 教学
      min_episodes_per_problem: 10
      origin_diversity_required: 8  # 至少 8 个不同 origin
```

#### 6.2.2 验收必须用未见配置

```yaml
validation:
  - test_id: "vertical_addition_unseen_origin"
    given_protocol:
      problems: "30 个 两位数加法"
      grid_origins: "全部用训练集中未出现的 origin"
      digit_widths: "包括三位数和四位数(训练时见过)"
    expected:
      - 系统能选择合适 origin(不需要固定坐标)
      - 答案正确率 ≥ 85%
      - grid 上可见对齐结构
  
  - test_id: "vertical_addition_unseen_digit_width"
    given:
      problems: "10 个 五位数加法"  # 训练时只到四位
    expected:
      - 系统能泛化范式到更宽数字
      - 准确率 ≥ 70%(略低,因为未见过的宽度)
  
  - test_id: "no_fixed_coordinate_memorization"
    redline: |
      不许系统对相同问题(23+47)总在相同坐标写.
      验收时换 origin,如果系统坐标固化,直接失败.
    test_method: |
      1. 教学时所有 23+47 在 (2,4) origin
      2. 测试时给 (0,0) origin,看系统是否能在新位置正确写
      3. 如果系统硬背 (2,4) → 失败
```

#### 6.2.3 redline 扫描

```python
def check_no_fixed_coordinate_table_in_yaml():
    """
    v3.3a: 课程包 yaml 不许直接给 row/col 数字表.
    
    禁:expected_action_sequence: [{action: write_at_grid, row: 0, col: 2}, ...]
    允:teacher_demonstration: "看,在这里写..." + visual percept
    """
    for yaml_file in Path("config/curriculum/packages/math").rglob("*.yaml"):
        content = yaml.safe_load(yaml_file.read_text())
        
        # 扫所有 teaching_episodes
        for content_item in content.get("content", []):
            episodes = content_item.get("teaching_episodes", [])
            for ep in episodes:
                if "expected_action_sequence" in ep:
                    actions = ep["expected_action_sequence"]
                    for action in actions:
                        if action.get("action") == "write_at_grid":
                            # 看是否有显式 row/col 数字
                            if "row" in action and "col" in action:
                                # 检查是否是 fixed table(全部 episode 同坐标 = 灾难)
                                # ... 复杂检查,这里建议直接禁止 expected_action_sequence
                                raise ValueError(
                                    f"{yaml_file}: expected_action_sequence with fixed row/col detected. "
                                    f"Use teacher_demonstration + visual percept instead."
                                )
```

### 6.3 影响

v3.3 §4.1 / §5 / §6 所有"expected_action_sequence with fixed coordinates"段都要重写,改为:
- 随机化 origin/spacing 教学
- 范式不变量声明
- teacher_demonstration + 视觉指示
- 验收强制未见配置

这是 v3.3a 最核心的修订,所有数学子阶段都要适用。

---

## 第 7 章 E7 — 进位/借位从事实涌现,不从 column_sum

### 7.1 v3.3 的错

v3.3 §4.2 写"进位作为 hierarchy SA emerge",但下一句又写:

> "SDPL 共现学习:packet {column_sum >= 10} → 范式 '进位'"

`column_sum >= 10` 是计算器式中间变量。系统**不该看到 column_sum**,该看到的是"个位 SA 召回的 fact 结果"。

### 7.2 v3.3a 根治:事实召回 → 视觉范式

```python
# v3.3a 正确路径

# Tick N: 系统读 grid 个位列两个数字
read_grid_cell(row=0, col=col_last)  # → percept "saw 3"
read_grid_cell(row=1, col=col_last)  # → percept "saw 7"

# Tick N+1: state pool 看到 packet {数字 3, 数字 7, 加号},
# SDPL recall fact::add::3_7 = 10
# vocab "10" 进入 attention,带 percept "result_is_10"

# Tick N+2: state pool 中,系统看到:
# - vocab "10" 是两位(经 Phase 8.4 学到"10 有两位数字")
# - 当前在写答案行的最右列
# - 范式 hierarchy SA "竖式答案写法" 涌现:
#   "两位结果,个位写本列,十位写左一列"
# 这是经大量教学例子学到的视觉范式

# Tick N+3: write_at_grid(answer_row, col_last, "0")  # 个位 0
# Tick N+4: write_at_grid(answer_row, col_last - 1, "1")  # 十位 1(进位)
# 或者按教学风格写在上方作进位标记
```

**关键**:
- 系统**不算 column_sum**
- 系统**召回 fact::add::3_7 = 10**(SDPL Q 表)
- 系统**看到 10 是两位**,经视觉范式知道"两位结果在竖式里要拆开写"
- 进位是"两位结果的左位"的自然处理,**不是特殊操作**

### 7.3 yaml 修订

v3.3a 把 v3.3 §4.2 改为:

```yaml
content:
  - sa_id: "paradigm::vertical_two_digit_result_layout"
    description: |
      当列相加结果是两位数时(10-18),
      系统不计算"是否进位",而是按视觉范式拆写:
      - 个位数字写本列答案行
      - 十位数字写左一列(或上方,根据教学风格)
    
    teaching_episodes_randomized:
      - example: |
          7 + 5 = 12
          → 在本列写 "2"
          → 在左一列(或上方)写 "1"
      - example: |
          9 + 9 = 18
          → 在本列写 "8"
          → 在左一列写 "1"
      # 多个对照样本,经 hierarchy SA 涌现"两位结果拆写"范式
    
    forbidden_implementation: |
      不许实现 if column_sum >= 10: carry = 1
      不许实现 if fact_result > 9: split
      必须经"两位数字 vocab + 答案位置范式"涌现
```

### 7.4 redline 扫描

```python
def check_no_column_sum_arithmetic():
    """v3.3a 红线:不许直接算 column_sum."""
    forbidden_patterns = [
        r"column_sum\s*[<>=]+\s*\d+",  # column_sum >= 10
        r"if.*sum.*>=\s*10",
        r"carry\s*=\s*sum\s*//\s*10",
        r"result.*%\s*10",  # 取个位
        r"result.*//\s*10",  # 取十位
    ]
    for py_file in glob("runtime/cognitive/**/*.py", recursive=True):
        content = open(py_file).read()
        for pat in forbidden_patterns:
            if re.search(pat, content):
                raise ValueError(f"{py_file}: forbidden arithmetic pattern '{pat}'")
```

---

## 第 8 章 E8 — 自己读草稿 vs 外部视觉来源分离

### 8.1 v3.3 的混淆

v3.3 §1.3 写:

> "read_grid_cell 等于'自己看自己写的东西',产生 percept SA,带 PERCEIVED marker"

但 PERCEIVED marker 也用于教师呈现的外部视觉(Phase 8.6)。**两者混类,Q 表会污染**:

- 教学时教师写"23" → percept SA "external_seen_23",PERCEIVED marker
- 系统自己写"23"在草稿 → percept SA "self_drawn_23",PERCEIVED marker
- **两个 packet_key 看起来相同**,Q 表混合
- 系统可能学到"看到 23 → 在草稿写下答案"(把自己的草稿当教师输入)

### 8.2 v3.3a 根治:source_substrate 区分

#### 8.2.1 percept SA 增 substrate 字段

```python
# runtime/cognitive/marker/spawn_perceived.py v3.3a

class PerceivedSource(str, Enum):
    """v3.3a: PERCEIVED 的 substrate 区分."""
    EXTERNAL_VISUAL = "external_visual"      # 教师/外部视觉感受器
    EXTERNAL_AUDIO = "external_audio"
    EXTERNAL_TEXT = "external_text"
    SELF_DRAFT_GRID = "self_draft_grid"      # 自己读草稿网格(新)
    SELF_DRAFT_TEXT_1D = "self_draft_text_1d"  # 自己读 1D 草稿
    # 未来可扩(如 SELF_INTERNAL_SIMULATION 给 deliberative 用)


def spawn_perceived_marker_v3_3a(
    *,
    target_sa_id: str,
    tick: int,
    substrate: PerceivedSource,
    metadata: dict,
) -> MarkerSA:
    """v3.3a: PERCEIVED 必须带 substrate."""
    return MarkerSA(
        kind=MarkerKind.PERCEIVED,
        target_sa_id=target_sa_id,
        spawn_tick=tick,
        metadata={
            **metadata,
            "substrate": substrate.value,  # 必填字段
        },
    )
```

#### 8.2.2 packet_key 包含 substrate

```python
# runtime/cognitive/sdpl/packet.py v3.3a

def compute_packet_key_v3_3a(packet: LearningPacket) -> tuple:
    """v3.3a: packet_key 包含 source substrate."""
    content_key = frozenset(
        (sa.id, R_bucket(sa.R)) for sa in packet.content_sas
    )
    
    # v3.3a: source 部分包含 substrate(来自 PERCEIVED marker 的 metadata.substrate)
    source_key_with_substrate = frozenset(
        (
            m.kind,
            m.metadata.get("substrate", "unspecified"),  # ← 新增维度
            R_bucket(m.real_energy),
        )
        for m in packet.source_markers
    )
    
    feeling_key = frozenset(
        (f.key, R_bucket(f.value)) for f in packet.feeling_sas
    )
    
    return (content_key, source_key_with_substrate, dominant_source(packet), feeling_key)
```

### 8.3 效果

现在 packet_key:

- 教师写 23 的视觉 percept:`(content={23}, source={(PERCEIVED, "external_visual", ...)}, ...)`
- 自己草稿读 23:`(content={23}, source={(PERCEIVED, "self_draft_grid", ...)}, ...)`

**两个 packet 不同 → Q 表独立学习**。系统不会混淆"教师呈现"和"自己写"。

### 8.4 验收

```python
def test_self_draft_and_external_visual_have_different_packet_keys():
    """v3.3a: 同 content 但不同 substrate 必有不同 packet_key."""
    content = "23"
    
    external_packet = make_packet(
        content_sas=[mock_vocab_sa(content)],
        source_markers=[spawn_perceived_marker_v3_3a(
            target_sa_id=content,
            tick=1,
            substrate=PerceivedSource.EXTERNAL_VISUAL,
            metadata={},
        )]
    )
    
    self_draft_packet = make_packet(
        content_sas=[mock_vocab_sa(content)],
        source_markers=[spawn_perceived_marker_v3_3a(
            target_sa_id=content,
            tick=1,
            substrate=PerceivedSource.SELF_DRAFT_GRID,
            metadata={},
        )]
    )
    
    assert external_packet.packet_key() != self_draft_packet.packet_key()


def test_q_table_isolation_between_substrates():
    """v3.3a: Q 表对不同 substrate 独立学习."""
    q_table = QTableWithBackoff()
    
    # 教学:teacher 写 23 → action "等等" 得 reward
    teacher_packet = make_packet_with_substrate("23", PerceivedSource.EXTERNAL_VISUAL)
    q_table.update(teacher_packet, "wait", outcome=1.0)
    
    # 测试:系统自己草稿读 23 → 应该没学到 "wait"
    self_packet = make_packet_with_substrate("23", PerceivedSource.SELF_DRAFT_GRID)
    q_wait_self = q_table.query(self_packet, "wait")
    
    # Q 应该接近 0(没数据)而不是 1.0(被污染)
    assert q_wait_self < 0.3
```

---

## 第 9 章 v3.2b/3.3a 实施清单(Phase 13.0 must-fix gates 扩展)

原 v3.2a 6 项 + v3.2b/3.3a 8 项 = **14 项 must-fix**:

### Phase 13.0(隐私 + 红线 + license + 课程 substrate)

- [ ] **F1**: 全状态 canary 扫描红线(v3.2a)
- [ ] **F2**: per-install salt + HMAC pseudonymous(v3.2a)
- [ ] **E1**: JSON canonicalization 输入(v3.2b)
- [ ] **F3**: trust gate effect_size 来自 held-out(v3.2a)
- [ ] **F4**: 多教师冲突默认 awaiting(v3.2a)
- [ ] **E2**: 复用 CORRECTION marker + status,不撑爆 cap(v3.2b)
- [ ] **E3**: 删 bool 字段示例,改 status str enum(v3.2b)
- [ ] **F5**: AST routing 扫描(v3.2a)
- [ ] **E5**: AST 扩 4 种新模式(v3.2b)
- [ ] **F6**: HeldOutEventPool raw sensor SA(v3.2a)
- [ ] **E4**: opaque event_id + stratified sampling(v3.2b)
- [ ] **License**: AGPL 表述对(v3.2)

### Phase 13.5b.0(数学 substrate proof,Codex 建议先做)

- [ ] **2D DraftGrid 实施**(v3.3 §1)
- [ ] **2D 不回归 1D**(双模式共存测试)
- [ ] **op_count + max_size**(防 grid 爆炸)
- [ ] **E8: substrate 区分**(v3.3a):PERCEIVED 增 substrate 字段 + packet_key 包含
- [ ] **随机 origin 测试**:同问题不同 origin 都能做
- [ ] **E6 redline**:扫 yaml 不含 fixed coordinate table
- [ ] **E7 redline**:扫代码不含 column_sum 算术

### Phase 13.5b.1+(数学正式课程)

- [ ] 子阶段 0-6 按 v3.3 顺序,每阶段独立验收
- [ ] 范式不变量教学(非固定坐标)
- [ ] 子阶段 5(应用题)前先确认子阶段 0-4 稳

---

## 第 10 章 给 Codex 的实施指令(v3.2b/3.3a)

1. **六稿配合**:v3 + v3.1 + v3.2 + v3.2a + v3.3 + v3.2b/3.3a(本稿)
2. **Phase 13.0 14 项 must-fix gates 是入门门票**,全过才进 13.1
3. **数学课程包**绝不许有 fixed coordinate table
4. **数学课程包**绝不许有 column_sum 算术
5. **PerceivedSource enum** 是 v3.3a 新增,packet_key 必须更新
6. **bool 字段红线**扫描含 trust_promoted/pending_perceived
7. **JSON canonicalization** 是 pseudonymous id 强制路径
8. **CORRECTION marker status** 字段是 enum string,不是 bool
9. **任何对 v3.2b/3.3a 的偏离先停下问 Claude/银子老师**

---

## 第 11 章 给银子老师的总结

Codex 这轮审阅找出 7 个真问题。其中:

**v3.2a 留下 4 个未根治问题**:
- E1 输入编码 → JSON canonicalization
- E2 marker cap 撑爆 → 复用 CORRECTION + status enum
- E3 bool 字段自相矛盾 → 删,改 str enum
- E4 event_id 含语义 → opaque random
- E5 AST 红线漏 4 种模式 → 扩

**v3.3 数学有 3 个新问题**(我的设计灾难):
- **E6 坐标模仿泄漏 — CRITICAL**:我给了固定坐标表,系统会背坐标不学范式
- **E7 column_sum 算术违反承诺**:我说"事实涌现"但样例又算 column_sum
- E8 self_draft vs external_visual 混类 → 加 substrate 字段

**E6 是我设计稿最大的失败**。我把"教系统在 (0,2) 位置写 2"当成"教竖式",这等于让系统背答案,完全违反 AP-native 哲学。Codex 一眼看穿,我必须诚实承认。

**v3.2b/3.3a 根治方案**:

- 教学**改为范式不变量声明 + teacher demonstration + 视觉指示**
- 教学**强制随机化 origin/spacing/digit_width**
- 验收**强制未见配置**
- redline **扫 yaml fixed coordinate** + **扫代码 column_sum**

---

## 第 12 章 给 Codex 对抗审阅者(下一轮)的指引

请重点审:

1. **E1 JSON canonicalization** 是否真稳定?Python 升级后是否仍给同 hash?
2. **E2 CORRECTION + status** 复用是否真不破坏 Phase 8.9 既有 CORRECTION 语义?
3. **E5 AST scanner** 是否覆盖所有 routing 模式?有无新漏?
4. **E6 范式不变量** 教学方式是否真能让系统学到"对齐范式"?Phase 10.6 hierarchy SA 实测数据支撑?
5. **E7 事实涌现** 是否真不需要 column_sum?教学样例是否能让"两位结果拆写"范式涌现?
6. **E8 substrate 维度** 加入 packet_key 后,Q 表稀疏度是否爆炸?

---

## 第 13 章 行动顺序(Codex 建议)

按 Codex 推荐顺序(我同意):

```
1. Phase 13.0 — license + 隐私 + 12 个 must-fix gates(2-3 天)
2. Phase 13.1 — curriculum substrate(1.5 天)
3. Phase 13.5b.0 — DraftGrid substrate proof + 6 项数学 must-fix gates(3 天)
   ↓ DECISION GATE
4. Phase 13.5b.1 — 数感(Math-0)
5. Phase 13.6 — 表达范式(并行 / 优先)
6. Phase 13.5b.2 — 个位事实库
7. Phase 13.2/3/4 — 内容浸泡(并行)
8. Phase 13.5b.3 — 两位数竖式(若 6.0 substrate 验过)
9. Phase 13.5b.4-6 — 乘法/长除法/应用题/方程(分阶段验收,失败止步)
10. Phase 13.9 四场景验收 + 开源 alpha
```

---

## 第 14 章 总结

v3.2b/3.3a 是必要的精准补丁。

**v3.2b**(4 项):
- E1 输入 canonicalization
- E2/E3 marker cap + bool 修复
- E4 opaque event_id
- E5 AST 4 种新模式

**v3.3a**(3 项):
- E6 删 fixed coordinate,改范式不变量(灾难性修复)
- E7 删 column_sum,改事实涌现
- E8 加 substrate 维度,Q 表隔离

**核心承诺**:数学不是教坐标,是教范式不变量。系统学到的是"如何对齐",不是"在 (0,2) 写 2"。

---

— 银子老师 / Claude
— 2026-06-18
