#!/usr/bin/env python3
"""
red_line_check_v14.py — APV3 v14 红线 PR-gate.

5 项检查综合:
1. AST-based 数字字面量(runtime/cognitive/ 不许字面量,白名单除外)
2. attention_gain 注入必经 ledger.inject() 同步
3. MarkerKind 分支检查(SDPL 学习规则不许按 source 分支)
4. @op_count 注解(cognitive 内函数必须有)
5. audit_db 不许在 runtime/cognitive/ 路径

违规任一即拒。

v14 UNIFIED 配套.
"""

import ast
import os
import re
import sys
import glob
from pathlib import Path

# 白名单:允许的结构性常量(白名单严格,v11 P2)
STRUCTURAL_LITERALS = {0, 1, 2, 3, -1, -2, 0.0, 1.0, -1.0}


def find_violations(directory: str) -> dict:
    """运行 5 项红线检查,返回违规字典"""
    violations = {
        "hardcoded_literals": [],
        "missing_ledger_inject": [],
        "marker_kind_branch": [],
        "missing_op_count": [],
        "audit_db_in_cognitive": [],
    }

    for py_file in glob.glob(f"{directory}/**/*.py", recursive=True):
        try:
            with open(py_file, encoding="utf-8") as f:
                source = f.read()
                tree = ast.parse(source)
        except (SyntaxError, OSError):
            continue

        # 1. AST 数字字面量
        check_hardcoded_literals(py_file, tree, violations)

        # 2. attention_gain 注入必经 ledger
        check_ledger_inject(py_file, tree, violations)

        # 3. MarkerKind 分支(豁免:packet_key / sdpl / sensor_adapters / marker_spawn / @packet_derive)
        check_marker_kind_branch(py_file, source, violations)

        # 4. @op_count 注解
        check_op_count_annotations(py_file, tree, violations)

        # 5. audit_db 不在 cognitive
        if "/cognitive/" in py_file.replace("\\", "/"):
            check_no_audit_db(py_file, source, violations)

    return violations


def check_hardcoded_literals(py_file, tree, violations):
    """AST 遍历找不合规字面量"""
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant):
            continue
        if not isinstance(node.value, (int, float)):
            continue
        if node.value in STRUCTURAL_LITERALS:
            continue
        # 简化检查:不在 load_constant() 调用内?
        # (完整 AST parent-stack 需要更复杂逻辑,这里简化为按文件路径粗判)
        if "/cognitive/" not in py_file.replace("\\", "/"):
            continue
        violations["hardcoded_literals"].append(
            f"{py_file}:{node.lineno}: literal {node.value}"
        )


def check_ledger_inject(py_file, tree, violations):
    """每个 attention_gain += 同函数内必须有 ledger.inject()"""
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        has_attention_inject = False
        has_ledger_inject = False
        for stmt in ast.walk(func):
            if (isinstance(stmt, ast.AugAssign)
                and isinstance(stmt.target, ast.Attribute)
                and stmt.target.attr == "attention_gain"):
                has_attention_inject = True
            if (isinstance(stmt, ast.Call)
                and hasattr(stmt.func, 'attr')
                and stmt.func.attr == "inject"):
                has_ledger_inject = True
        if has_attention_inject and not has_ledger_inject:
            violations["missing_ledger_inject"].append(
                f"{py_file}:{func.lineno}: {func.name} attention_gain inject without ledger"
            )


def check_marker_kind_branch(py_file, source, violations):
    """禁 `if MarkerKind.X ==`,豁免 sensor adapters / packet_key 派生路径"""
    if any(p in py_file.replace("\\", "/") for p in [
        "/packet_key/", "/sdpl/", "/sensor_adapters/", "/marker_spawn/"
    ]):
        return
    # @packet_derive 注释豁免
    pattern = re.compile(r'if\s+.*MarkerKind\.\w+')
    for i, line in enumerate(source.split("\n"), 1):
        if pattern.search(line):
            if "@packet_derive" in line:
                continue
            violations["marker_kind_branch"].append(
                f"{py_file}:{i}: MarkerKind branch in learning rule"
            )


def check_op_count_annotations(py_file, tree, violations):
    """cognitive 内函数必须有 @op_count 注解(私有/短函数跳过)"""
    if "/cognitive/" not in py_file.replace("\\", "/"):
        return
    for func in ast.walk(tree):
        if not isinstance(func, ast.FunctionDef):
            continue
        if func.name.startswith("_") or len(func.body) < 3:
            continue
        docstring = ast.get_docstring(func)
        if not docstring or "@op_count" not in docstring:
            violations["missing_op_count"].append(
                f"{py_file}:{func.lineno}: {func.name} missing @op_count"
            )


def check_no_audit_db(py_file, source, violations):
    """cognitive 路径下不许 import / 使用 audit_db"""
    if "audit_db" in source.lower():
        for i, line in enumerate(source.split("\n"), 1):
            if "audit_db" in line.lower():
                violations["audit_db_in_cognitive"].append(
                    f"{py_file}:{i}: audit_db usage in cognitive path"
                )


def main():
    import argparse
    parser = argparse.ArgumentParser(description="APV3 v14.1 red line PR-gate")
    parser.add_argument("--phase", help="Check phase-specific deliverables (e.g. 8.3)")
    args = parser.parse_args()

    # v14.1 §S4: phase-aware existence gate
    if args.phase:
        phase_violations = check_phase_deliverables(args.phase)
        if phase_violations:
            print(f"Phase {args.phase} DELIVERABLES MISSING ({len(phase_violations)}):")
            for v in phase_violations:
                print(f"  {v}")
            sys.exit(1)
        print(f"OK: Phase {args.phase} deliverables present")

    # v14.1 §S3: 二值 feature 检查
    binary_violations = check_no_binary_feature_formulas()
    binary_violations = check_no_binary_feature_formulas()
    if binary_violations:
        print(f"BINARY FEATURE VIOLATIONS ({len(binary_violations)}):")
        for v in binary_violations:
            print(f"  {v}")
        sys.exit(1)

    phase13_violations = check_phase13_redlines()
    if phase13_violations:
        print(f"PHASE 13 RED LINE VIOLATIONS ({len(phase13_violations)}):")
        for v in phase13_violations:
            print(f"  {v}")
        sys.exit(1)

    phase19_violations = check_phase19_redlines()
    if phase19_violations:
        print(f"PHASE 19 RED LINE VIOLATIONS ({len(phase19_violations)}):")
        for v in phase19_violations:
            print(f"  {v}")
        sys.exit(1)

    # 通用红线
    target_dirs = ["runtime/cognitive", "runtime/sensor_adapters", "runtime"]
    target = None
    for d in target_dirs:
        if Path(d).exists():
            target = d
            break

    if not target:
        print(f"WARN: no target directory found. Phase 8.2 will create runtime/cognitive/.")
        print(f"Red line check skipped (no code yet).")
        sys.exit(0)

    violations = find_violations(target)
    total = sum(len(v) for v in violations.values())
    if total == 0:
        print(f"OK: All red line checks pass on {target}")
        sys.exit(0)

    print(f"v14 RED LINE VIOLATIONS ({total}):\n")
    for category, items in violations.items():
        if items:
            print(f"=== {category} ({len(items)}) ===")
            for v in items[:10]:
                print(f"  {v}")
            if len(items) > 10:
                print(f"  ... and {len(items) - 10} more")
            print()
    sys.exit(1)


# === v14.1 §S3: binary feature formula check ===
def check_no_binary_feature_formulas():
    """禁 cognitive_feeling_features.yaml 中 '1.0 if ... else 0.0' 模式"""
    yaml_path = Path("config/cognitive_feeling_features.yaml")
    if not yaml_path.exists():
        return []
    try:
        import yaml
        config = yaml.safe_load(yaml_path.read_text(encoding="utf-8"))
    except (ImportError, yaml.YAMLError):
        return []

    violations = []
    features = config.get("features", {})
    for feature_name, spec in features.items():
        formula = spec.get("formula", "")
        if not isinstance(formula, str):
            continue
        # 检测 "1.0 if ... else 0.0" 二值模式
        if "1.0 if" in formula and "else 0.0" in formula:
            violations.append(
                f"{feature_name}: binary if-else formula (use sigmoid(marker.R) instead)"
            )
    return violations


# === v14.1 §S4: phase-aware deliverables ===
DESIGN_METADATA_FIELDS = {"style_tag", "context_tag", "design_note"}


def check_phase13_redlines():
    """Phase 13 implementation redlines for privacy/curriculum metadata routes."""
    violations = []
    for root in ("runtime", "apv3test"):
        for py_file in Path(root).glob("**/*.py"):
            if "__pycache__" in py_file.parts:
                continue
            try:
                source = py_file.read_text(encoding="utf-8")
                ast.parse(source)
            except (OSError, SyntaxError):
                continue
            violations.extend(check_no_design_metadata_routing_from_source(source, str(py_file)))
            violations.extend(check_no_context_tokens_literal_branching_from_source(source, str(py_file)))
            violations.extend(check_no_trust_pending_bool_fields_from_source(source, str(py_file)))
            violations.extend(check_no_phase13_math_shortcuts_from_source(source, str(py_file)))
            if _status_metadata_path_is_forbidden(py_file):
                violations.extend(check_no_status_metadata_access_from_source(source, str(py_file)))
    static_root = Path("apv3test/web/static")
    if static_root.exists():
        for js_file in static_root.glob("**/*.js"):
            source = js_file.read_text(encoding="utf-8")
            for index, line in enumerate(source.splitlines(), start=1):
                if any(field in line for field in ("styleTag", "context_tag", "design_note")):
                    violations.append(f"{js_file}:{index}: design metadata in frontend route")
    return violations


def check_phase19_redlines():
    """Phase 19 receptor redlines for no model shortcuts and source-separated metadata."""
    violations = []
    for py_file in (Path("apv3test/runtime/visual_receptor.py"),):
        if not py_file.exists():
            continue
        source = py_file.read_text(encoding="utf-8")
        forbidden_imports = (
            "import cv2",
            "import torch",
            "import tensorflow",
            "import sklearn",
            "import librosa",
            "from cv2",
            "from torch",
            "from tensorflow",
            "from sklearn",
            "from librosa",
        )
        for token in forbidden_imports:
            if token in source:
                violations.append(f"{py_file}: external model/library shortcut {token}")
        for index, line in enumerate(source.splitlines(), start=1):
            compact = line.replace(" ", "")
            if "evaluator_label_accessed" in compact and "True" in compact:
                violations.append(f"{py_file}:{index}: evaluator_label_accessed must never be True")
            if "decision_tier" in compact and (">" in compact or "<" in compact):
                violations.append(f"{py_file}:{index}: decision_tier must not be compared as numeric")
            if "prototype_imagination" in compact and "sensory_sketch" in compact and "==" in compact:
                violations.append(f"{py_file}:{index}: render modes must stay source-separated")
    return violations


def check_no_design_metadata_routing_from_source(source: str, filename: str = "<source>") -> list[str]:
    """Detect Phase 13 style/context metadata hard routing in Python source."""
    tree = ast.parse(source)
    detector = _DesignMetadataRouteDetector(filename)
    detector.visit(tree)
    return detector.violations


def check_no_context_tokens_literal_branching_from_source(source: str, filename: str = "<source>") -> list[str]:
    """Detect literal branches over learned AP-native context evidence."""
    tree = ast.parse(source)
    detector = _ContextTokensLiteralBranchDetector(filename)
    detector.visit(tree)
    return detector.violations


def check_no_status_metadata_access_from_source(source: str, filename: str = "<source>") -> list[str]:
    """Detect CORRECTION metadata.status use in learning/selection paths."""
    tree = ast.parse(source)
    detector = _StatusMetadataDetector(filename)
    detector.visit(tree)
    return detector.violations


def check_no_trust_pending_bool_fields_from_source(source: str, filename: str = "<source>") -> list[str]:
    """Detect bool fields that smuggle trust/pending lifecycle states."""
    tree = ast.parse(source)
    detector = _TrustPendingBoolDetector(filename)
    detector.visit(tree)
    return detector.violations


def check_no_phase13_math_shortcuts_from_source(source: str, filename: str = "<source>") -> list[str]:
    """Detect fixed-solver shortcuts in Phase 13 draft-grid/math runtime code."""
    normalized = filename.replace("\\", "/")
    if "apv3test/runtime/" not in normalized and "runtime/cognitive/" not in normalized:
        return []
    forbidden = (
        "column_sum",
        "compute_addition",
        "solve_equation",
        "expected_action_sequence",
        "read_grid_cell",
        "filter_by_similarity_to",
        "fact::add::3_7",
    )
    violations = []
    for index, line in enumerate(source.splitlines(), start=1):
        for token in forbidden:
            if token in line:
                violations.append(f"{filename}:{index}: Phase 13 math shortcut token {token}")
    return violations


class _DesignMetadataRouteDetector(ast.NodeVisitor):
    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.violations: list[str] = []

    def visit_Attribute(self, node):
        if node.attr in DESIGN_METADATA_FIELDS:
            self.violations.append(f"{self.filename}:{node.lineno}: design metadata attribute route {node.attr}")
        self.generic_visit(node)

    def visit_Subscript(self, node):
        key = _constant_string(node.slice)
        if key in DESIGN_METADATA_FIELDS:
            self.violations.append(f"{self.filename}:{node.lineno}: design metadata subscript route {key}")
        if _name_text(node.slice) in DESIGN_METADATA_FIELDS:
            self.violations.append(f"{self.filename}:{node.lineno}: table indexed by design metadata")
        self.generic_visit(node)

    def visit_Call(self, node):
        if _call_name(node.func) == "getattr" and len(node.args) >= 2:
            key = _constant_string(node.args[1])
            if key in DESIGN_METADATA_FIELDS:
                self.violations.append(f"{self.filename}:{node.lineno}: getattr design metadata route {key}")
        if isinstance(node.func, ast.Attribute) and node.func.attr == "get" and node.args:
            key = _constant_string(node.args[0])
            if key in DESIGN_METADATA_FIELDS:
                self.violations.append(f"{self.filename}:{node.lineno}: metadata.get design route {key}")
        self.generic_visit(node)


class _ContextTokensLiteralBranchDetector(ast.NodeVisitor):
    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.violations: list[str] = []

    def visit_Compare(self, node):
        if _is_context_tokens_access(node.left):
            for comparator in node.comparators:
                if _contains_forbidden_context_literal(comparator):
                    self.violations.append(f"{self.filename}:{node.lineno}: literal compare on context tokens")
        for comparator in node.comparators:
            if _is_context_tokens_access(comparator) and _contains_forbidden_context_literal(node.left):
                self.violations.append(f"{self.filename}:{node.lineno}: literal membership in context tokens")
        self.generic_visit(node)

    def visit_Match(self, node):
        if _is_context_tokens_access(node.subject):
            self.violations.append(f"{self.filename}:{node.lineno}: match-case on context tokens")
        self.generic_visit(node)

    def visit_Subscript(self, node):
        if isinstance(node.value, ast.Name) and _is_context_tokens_element_access(node.slice):
            self.violations.append(f"{self.filename}:{node.lineno}: dict route via context token element")
        self.generic_visit(node)


class _StatusMetadataDetector(ast.NodeVisitor):
    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.violations: list[str] = []

    def visit_Subscript(self, node):
        if _constant_string(node.slice) == "status":
            self.violations.append(f"{self.filename}:{node.lineno}: metadata status access in learning path")
        self.generic_visit(node)

    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute) and node.func.attr == "get" and node.args:
            if _constant_string(node.args[0]) == "status":
                self.violations.append(f"{self.filename}:{node.lineno}: metadata.get('status') in learning path")
        self.generic_visit(node)


class _TrustPendingBoolDetector(ast.NodeVisitor):
    def __init__(self, filename: str) -> None:
        self.filename = filename
        self.violations: list[str] = []

    def visit_AnnAssign(self, node):
        name = _target_name(node.target)
        if name and _is_forbidden_bool_lifecycle_name(name) and _annotation_is_bool(node.annotation):
            self.violations.append(f"{self.filename}:{node.lineno}: bool lifecycle field {name}")
        self.generic_visit(node)

    def visit_Assign(self, node):
        if isinstance(node.value, ast.Constant) and isinstance(node.value.value, bool):
            for target in node.targets:
                name = _target_name(target)
                if name and _is_forbidden_bool_lifecycle_name(name):
                    self.violations.append(f"{self.filename}:{node.lineno}: bool lifecycle assignment {name}")
        self.generic_visit(node)


def _status_metadata_path_is_forbidden(path: Path) -> bool:
    normalized = path.as_posix()
    return any(
        part in normalized
        for part in (
            "runtime/cognitive/sdpl/",
            "runtime/cognitive/attention/",
            "runtime/cognitive/composed_vocab/",
            "runtime/cognitive/action",
            "runtime/cognitive/deliberative/",
        )
    )


def _is_forbidden_bool_lifecycle_name(name: str) -> bool:
    lowered = name.lower()
    return any(part in lowered for part in ("trust_promoted", "pending_perceived", "is_promoted", "is_pending"))


def _annotation_is_bool(annotation) -> bool:
    return isinstance(annotation, ast.Name) and annotation.id == "bool"


def _target_name(target) -> str:
    if isinstance(target, ast.Name):
        return target.id
    if isinstance(target, ast.Attribute):
        return target.attr
    return ""


def _call_name(func) -> str:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return ""


def _name_text(node) -> str:
    return node.id if isinstance(node, ast.Name) else ""


def _constant_string(node) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _contains_string_literal(node) -> bool:
    return any(isinstance(item, ast.Constant) and isinstance(item.value, str) for item in ast.walk(node))


def _contains_forbidden_context_literal(node) -> bool:
    allowed_field_names = {"context_tokens", "context_tags"}
    for item in ast.walk(node):
        if isinstance(item, ast.Constant) and isinstance(item.value, str):
            if item.value not in allowed_field_names:
                return True
    return False


def _is_context_tokens_access(node) -> bool:
    if isinstance(node, ast.Attribute) and node.attr in {"context_tokens", "context_tags"}:
        return True
    if isinstance(node, ast.Name) and node.id in {"context_tokens", "context_tags"}:
        return True
    return False


def _is_context_tokens_element_access(node) -> bool:
    return isinstance(node, ast.Subscript) and _is_context_tokens_access(node.value)


PHASE_DELIVERABLES = {
    "8.2": {
        "files_must_exist": [
            "runtime/cognitive/runtime/tick_loop.py",
            "runtime/sensor_adapters/text/char_stream.py",
            "runtime/cognitive/state_pool/state_pool.py",
        ],
    },
    "8.3": {
        "files_must_exist": [
            "runtime/cognitive/runtime/audit_db_boundary.py",
            "runtime/cognitive/state_pool/target_cap.py",
            "runtime/cognitive/state_pool/attention_gain_ledger.py",
            "runtime/cognitive/state_pool/v_double_control.py",
            # v14.1 §B2 提前到 8.3 的 3 路 marker spawn
            "runtime/cognitive/marker/spawn_perceived.py",
            "runtime/cognitive/marker/spawn_hearsay.py",
            "runtime/cognitive/text_understanding/proposition_emit.py",
            "runtime/cognitive/reward/handler.py",
        ],
        "must_have_marker_spawn_for": ["PERCEIVED", "HEARSAY", "CORRECTION"],
    },
    "8.4": {
        "files_must_exist": [
            "runtime/cognitive/composed_vocab/sparse_pairwise.py",
            "runtime/cognitive/composed_vocab/delta_p_cold_fork.py",
            "runtime/cognitive/composed_vocab/held_out_pool.py",
            "runtime/cognitive/sdpl/packet.py",
            "runtime/cognitive/sdpl/q_table_backoff.py",  # v14.1 §S2
        ],
        "must_have_marker_spawn_for": [
            "PERCEIVED", "HEARSAY", "CORRECTION", "IMAGINED", "REMEMBERED",
        ],
    },
    "8.5": {
        "files_must_exist": [
            "runtime/cognitive/cognitive_feelings/factory.py",
            "runtime/cognitive/cognitive_feelings/epistemic_source_feelings.py",
        ],
    },
    "8.10": {
        "files_must_exist": [
            "runtime/cognitive/endogenous/step.py",
            "runtime/cognitive/endogenous/imagined_marker_spawn.py",  # v14.1 §S1 重命名
            "runtime/cognitive/attention/safety_gate.py",
        ],
        "must_have_marker_spawn_for": [
            "PERCEIVED", "HEARSAY", "CORRECTION", "IMAGINED", "REMEMBERED", "NOVELTY",
        ],
    },
    "9.1": {
        "files_must_exist": [
            "runtime/cognitive/drive/__init__.py",
            "runtime/cognitive/drive/homeostatic_drive.py",
            "tests/test_phase9_1_drive_homeostasis.py",
            "docs/FinalReport_Phase9_1_DriveSAHomeostasis_20260617.md",
            "reports/APV3_Phase9_1_DriveSAHomeostasis_Showcase_20260617.html",
        ],
    },
    "9.2": {
        "files_must_exist": [
            "runtime/cognitive/reward/rpe.py",
            "tests/test_phase9_2_rpe_dopamine.py",
            "docs/FinalReport_Phase9_2_RPEDopamineAnalog_20260617.md",
        ],
    },
    "9.3": {
        "files_must_exist": [
            "runtime/cognitive/affect/frustration.py",
            "tests/test_phase9_3_frustration_helplessness.py",
            "docs/FinalReport_Phase9_3_FrustrationHelplessness_20260617.md",
        ],
    },
    "9.4": {
        "files_must_exist": [
            "runtime/cognitive/social/attachment.py",
            "tests/test_phase9_4_attachment_familiarity.py",
            "docs/FinalReport_Phase9_4_AttachmentFamiliarity_20260617.md",
        ],
    },
    "9.5": {
        "files_must_exist": [
            "runtime/cognitive/social/joint_attention.py",
            "tests/test_phase9_5_joint_attention.py",
            "docs/FinalReport_Phase9_5_JointAttention_20260617.md",
        ],
    },
    "9.6": {
        "files_must_exist": [
            "runtime/cognitive/social/empathy.py",
            "tests/test_phase9_6_empathy_resonance.py",
            "docs/FinalReport_Phase9_6_EmpathyResonance_20260617.md",
        ],
    },
    "9.7": {
        "files_must_exist": [
            "runtime/cognitive/affect/pain_memory.py",
            "tests/test_phase9_7_pain_memory.py",
            "docs/FinalReport_Phase9_7_PainMemory_20260617.md",
        ],
    },
    "9.8": {
        "files_must_exist": [
            "runtime/cognitive/sleep/replay_consolidation.py",
            "tests/test_phase9_8_sleep_replay.py",
            "docs/FinalReport_Phase9_8_SleepReplayConsolidation_20260617.md",
        ],
    },
    "9.9": {
        "files_must_exist": [
            "runtime/cognitive/play/exploratory_play.py",
            "tests/test_phase9_9_exploratory_play.py",
            "docs/FinalReport_Phase9_9_ExploratoryPlay_20260617.md",
            "docs/FinalReport_Phase9_1_to_9_9_MindDepth_20260617.md",
            "reports/APV3_Phase9_1_to_9_9_MindDepth_Showcase_20260617.html",
        ],
    },
    "10.1": {
        "files_must_exist": [
            "runtime/cognitive/narrative/lag_pmi.py",
            "tests/test_phase10_1_narrative_lag_pmi.py",
            "docs/FinalReport_Phase10_1_NarrativeLagPMI_20260618.md",
        ],
    },
    "10.2": {
        "files_must_exist": [
            "runtime/cognitive/hierarchy/anonymous_cluster.py",
            "tests/test_phase10_2_anonymous_super_cluster.py",
            "docs/FinalReport_Phase10_2_AnonymousSuperCluster_20260618.md",
        ],
    },
    "10.3": {
        "files_must_exist": [
            "runtime/cognitive/counterfactual/simulator.py",
            "tests/test_phase10_3_counterfactual_cde.py",
            "docs/FinalReport_Phase10_3_CounterfactualCDE_20260618.md",
        ],
    },
    "10.4": {
        "files_must_exist": [
            "runtime/cognitive/causal/causal_sa.py",
            "tests/test_phase10_4_causal_sa.py",
            "docs/FinalReport_Phase10_4_CausalSA_20260618.md",
        ],
    },
    "10.5": {
        "files_must_exist": [
            "runtime/cognitive/theory_of_mind/belief_model.py",
            "tests/test_phase10_5_theory_of_mind_belief.py",
            "docs/FinalReport_Phase10_5_TheoryOfMindBelief_20260618.md",
        ],
    },
    "10.6": {
        "files_must_exist": [
            "runtime/cognitive/hierarchy/hierarchy_sa.py",
            "tests/test_phase10_6_hierarchy_sa.py",
            "docs/FinalReport_Phase10_6_HierarchySA_20260618.md",
        ],
    },
    "10.7": {
        "files_must_exist": [
            "runtime/cognitive/trust/trust_prior.py",
            "tests/test_phase10_7_trust_prior.py",
            "docs/FinalReport_Phase10_7_TrustPrior_20260618.md",
        ],
    },
    "10.8": {
        "files_must_exist": [
            "runtime/cognitive/reading/reading_pipeline.py",
            "tests/test_phase10_8_reading_pipeline.py",
            "docs/FinalReport_Phase10_8_ReadingPipeline_20260618.md",
            "docs/FinalReport_Phase10_1_to_10_8_HierarchicalMind_20260618.md",
            "reports/APV3_Phase10_1_to_10_8_HierarchicalMind_Showcase_20260618.html",
        ],
    },
    "11.1": {
        "files_must_exist": [
            "runtime/cognitive/metacognition/monitor.py",
            "tests/test_phase11_1_metacognition.py",
            "docs/FinalReport_Phase11_1_MetaCognition_20260618.md",
        ],
    },
    "11.2": {
        "files_must_exist": [
            "runtime/cognitive/abstract_vocab/cross_cluster_gate.py",
            "tests/test_phase11_2_abstract_vocab.py",
            "docs/FinalReport_Phase11_2_AbstractVocab_20260618.md",
        ],
    },
    "11.3": {
        "files_must_exist": [
            "runtime/cognitive/goal/horizon.py",
            "tests/test_phase11_3_goal_horizon.py",
            "docs/FinalReport_Phase11_3_GoalHorizon_20260618.md",
        ],
    },
    "11.4": {
        "files_must_exist": [
            "runtime/cognitive/deliberative/virtual_track.py",
            "runtime/cognitive/deliberative/conclusion_reify.py",
            "tests/test_phase11_4_deliberative_virtual_track.py",
            "docs/FinalReport_Phase11_4_DeliberativeVirtualTrack_20260618.md",
        ],
        "must_have_marker_spawn_for": ["INFERRED"],
    },
    "11.5": {
        "files_must_exist": [
            "runtime/cognitive/self_model/heartbeat.py",
            "tests/test_phase11_5_self_model.py",
            "docs/FinalReport_Phase11_5_SelfModel_20260618.md",
            "docs/FinalReport_Phase11_1_to_11_5_MetacognitiveLayer_20260618.md",
            "reports/APV3_Phase11_1_to_11_5_MetacognitiveLayer_Showcase_20260618.html",
        ],
    },
    "12.1": {
        "files_must_exist": [
            "runtime/demo_substrate/audit_view.py",
            "tests/test_phase12_1_demo_audit_view.py",
            "docs/FinalReport_Phase12_1_DemoAuditView_20260618.md",
        ],
    },
    "12.2": {
        "files_must_exist": [
            "runtime/demo_substrate/profile.py",
            "tests/test_phase12_2_demo_profile.py",
            "docs/FinalReport_Phase12_2_DemoProfile_20260618.md",
        ],
    },
    "12.3": {
        "files_must_exist": [
            "runtime/demo_substrate/scenario_readiness.py",
            "tests/test_phase12_3_scenario_readiness.py",
            "docs/FinalReport_Phase12_3_ScenarioReadiness_20260618.md",
            "docs/FinalReport_Phase12_1_to_12_3_DemoSubstrate_20260618.md",
            "reports/APV3_Phase12_1_to_12_3_DemoSubstrate_Showcase_20260618.html",
        ],
    },
    "13.0": {
        "files_must_exist": [
            "apv3test/util/pseudonymous_id.py",
            "runtime/cognitive/curriculum/held_out_private_pool.py",
            "runtime/cognitive/curriculum/trust_gate.py",
            "runtime/cognitive/curriculum/conflict_resolution.py",
            "tests/test_phase13_0_privacy_curriculum_foundation.py",
            "docs/FinalReport_Phase13_0_PrivacyCurriculumFoundation_20260618.md",
            "reports/APV3_Phase13_0_PrivacyCurriculumFoundation_Showcase_20260618.html",
        ],
    },
    "13.1": {
        "files_must_exist": [
            "runtime/cognitive/curriculum/package_schema.py",
            "runtime/cognitive/curriculum/loader.py",
            "runtime/cognitive/curriculum/consistency_validator.py",
            "runtime/cognitive/curriculum/progress_backup.py",
            "tests/test_phase13_1_curriculum_substrate.py",
            "docs/FinalReport_Phase13_1_CurriculumSubstrate_20260618.md",
        ],
    },
    "13.2": {
        "files_must_exist": [
            "runtime/cognitive/curriculum/content_curriculum.py",
            "tests/test_phase13_2_character_radical_curriculum.py",
            "docs/FinalReport_Phase13_2_CharacterRadicalCurriculum_20260618.md",
        ],
    },
    "13.3": {
        "files_must_exist": [
            "runtime/cognitive/curriculum/content_curriculum.py",
            "tests/test_phase13_3_vocabulary_curriculum.py",
            "docs/FinalReport_Phase13_3_VocabularyCurriculum_20260618.md",
        ],
    },
    "13.4": {
        "files_must_exist": [
            "runtime/cognitive/curriculum/content_curriculum.py",
            "tests/test_phase13_4_visual_curriculum.py",
            "docs/FinalReport_Phase13_4_VisualCommonSenseCurriculum_20260618.md",
        ],
    },
    "13.5": {
        "files_must_exist": [
            "runtime/cognitive/curriculum/content_curriculum.py",
            "tests/test_phase13_5_audio_curriculum.py",
            "docs/FinalReport_Phase13_5_AudioCommonSenseCurriculum_20260618.md",
        ],
    },
    "13.5b": {
        "files_must_exist": [
            "apv3test/runtime/draft_grid.py",
            "apv3test/runtime/math_curriculum.py",
            "runtime/cognitive/attention/draft_focus_modulation.py",
            "tests/test_phase13_5b_draftgrid_charfocus_math.py",
            "docs/FinalReport_Phase13_5b_DraftGridMathCurriculum_20260618.md",
        ],
    },
    "13.6": {
        "files_must_exist": [
            "runtime/cognitive/curriculum/expression_paradigm.py",
            "tests/test_phase13_6_expression_paradigm_curriculum.py",
            "docs/FinalReport_Phase13_6_ExpressionParadigmCurriculum_20260618.md",
        ],
    },
    "13.7": {
        "files_must_exist": [
            "runtime/cognitive/curriculum/action_social.py",
            "tests/test_phase13_7_action_prototype_curriculum.py",
            "docs/FinalReport_Phase13_7_ActionPrototypeCurriculum_20260618.md",
        ],
    },
    "13.8": {
        "files_must_exist": [
            "runtime/cognitive/curriculum/action_social.py",
            "tests/test_phase13_8_social_common_sense_curriculum.py",
            "docs/FinalReport_Phase13_8_SocialCommonSenseCurriculum_20260618.md",
        ],
    },
    "13.9": {
        "files_must_exist": [
            "runtime/cognitive/curriculum/alpha_validation.py",
            "tests/test_phase13_9_alpha_validation.py",
            "docs/FinalReport_Phase13_9_AlphaValidation_20260618.md",
            "docs/FinalReport_Phase13_0_to_13_9_CognitiveCurriculum_20260618.md",
            "reports/APV3_Phase13_CognitiveCurriculum_Showcase_20260618.html",
        ],
    },
    "14.0": {
        "files_must_exist": [
            "runtime/cognitive/curriculum/asset_governance.py",
            "config/curriculum/assets/manifest.yaml",
            "scripts/curriculum/generate_synthetic_assets.py",
            "tests/test_phase14_0_asset_governance.py",
            "docs/FinalReport_Phase14_0_ContentAssetGovernance_20260618.md",
        ],
    },
    "14.1": {
        "files_must_exist": [
            "config/curriculum/assets/visual/synthetic/color_red_train_0.png",
            "config/curriculum/assets/audio/synthetic/audio_soft_call_train_0.wav",
            "tests/test_phase14_1_synthetic_assets.py",
            "docs/FinalReport_Phase14_1_SyntheticAssetPack_20260618.md",
        ],
    },
    "14.2": {
        "files_must_exist": [
            "config/curriculum/packages/neutral/neutral_colors_v1.yaml",
            "config/curriculum/packages/neutral/neutral_audio_patterns_v1.yaml",
            "tests/test_phase14_2_neutral_curriculum_packs.py",
            "docs/FinalReport_Phase14_2_NeutralCurriculumPacks_20260618.md",
        ],
    },
    "14.3": {
        "files_must_exist": [
            "tests/test_phase14_3_public_showcase.py",
            "docs/FinalReport_Phase14_3_PublicShowcase_20260618.md",
            "docs/FinalReport_Phase14_0_to_14_3_ContentAssets_20260618.md",
            "reports/APV3_Phase14_PublicReadable_Showcase_20260618.html",
        ],
    },
    "15.0": {
        "files_must_exist": [
            "apv3test/runtime/course_replay.py",
            "tests/test_phase15_0_course_replay_runtime.py",
            "docs/FinalReport_Phase15_0_CourseReplayRuntime_20260618.md",
        ],
    },
    "15.1": {
        "files_must_exist": [
            "apv3test/web_chat.py",
            "tests/test_phase15_1_course_replay_web_api.py",
            "docs/FinalReport_Phase15_1_CourseReplayWebAPI_20260618.md",
        ],
    },
    "15.2": {
        "files_must_exist": [
            "apv3test/web/static/course.html",
            "apv3test/web/static/course.js",
            "apv3test/web/static/styles.css",
            "tests/test_phase15_2_course_replay_frontend_contract.py",
            "docs/FinalReport_Phase15_2_CourseReplayWorkbench_20260618.md",
        ],
    },
    "15.3": {
        "files_must_exist": [
            "tests/test_phase15_3_public_showcase.py",
            "docs/FinalReport_Phase15_3_PublicShowcase_20260618.md",
            "docs/FinalReport_Phase15_0_to_15_3_WebCourseReplay_20260618.md",
            "reports/APV3_Phase15_WebCourseReplay_Showcase_20260618.html",
        ],
    },
    "16.0": {
        "files_must_exist": [
            "scripts/curriculum/generate_styled_corpus.py",
            "config/curriculum/packages/styled/styled_greeting_v1.yaml",
            "tests/test_phase16_0_styled_expression_corpus.py",
            "docs/FinalReport_Phase16_0_StyledExpressionCorpus_20260618.md",
            "reports/APV3_Phase16_StyledExpression_Showcase_20260618.html",
        ],
    },
    "17.0": {
        "files_must_exist": [
            "scripts/curriculum/download_real_visual_assets.py",
            "config/curriculum/assets/real_manifest.yaml",
            "config/curriculum/assets/visual/real/noun_apple_train_0.png",
            "config/curriculum/assets/visual/real/_sources.json",
            "config/curriculum/packages/real/real_fruit_photos_v1.yaml",
            "tests/test_phase17_0_real_visual_assets.py",
            "docs/FinalReport_Phase17_0_RealVisualAssets_20260618.md",
            "reports/APV3_Phase17_RealVisualAssets_Showcase_20260618.html",
        ],
    },
    "18.0": {
        "files_must_exist": [
            "scripts/curriculum/generate_clean_concept_cards.py",
            "config/curriculum/assets/clean_card_manifest.yaml",
            "config/curriculum/assets/visual/clean_cards/noun_apple_train_0.png",
            "config/curriculum/packages/clean/clean_fruit_cards_v1.yaml",
            "apv3test/runtime/course_replay.py",
            "tests/test_phase18_0_clean_concept_cards.py",
            "docs/Design_APV3.0_Phase18_CleanConceptCards_v1_20260618.md",
            "docs/FinalReport_Phase18_0_CleanConceptCards_20260618.md",
            "reports/APV3_Phase18_CleanConceptCards_Showcase_20260618.html",
        ],
    },
    "18.1": {
        "files_must_exist": [
            "apv3test/runtime/course_replay.py",
            "config/curriculum/assets/clean_card_manifest.yaml",
            "config/curriculum/assets/real_manifest.yaml",
            "config/curriculum/packages/clean/clean_fruit_cards_v1.yaml",
            "config/curriculum/packages/real/real_fruit_photos_v1.yaml",
            "tests/test_phase18_1_real_photo_generalization_probe.py",
            "scripts/reports/render_phase18_1_showcase.py",
            "docs/Design_APV3.0_Phase18_1_RealPhotoGeneralizationProbe_v1_20260618.md",
            "docs/Errata_Phase18_1_AuditCorrection_20260619.md",
            "docs/FinalReport_Phase18_1_RealPhotoGeneralizationProbe_20260618.md",
            "reports/APV3_Phase18_1_RealPhotoGeneralizationProbe_Showcase_20260618.html",
        ],
    },
    "19.0": {
        "files_must_exist": [
            "apv3test/runtime/visual_receptor.py",
            "tests/test_phase19_0_visual_receptor.py",
            "scripts/reports/render_phase19_0_showcase.py",
            "docs/Design_APV3.0_Phase19_0_VisualSensorEnrichmentAndReconstructionAudit_v1_20260619.md",
            "docs/Errata_Phase19_v1a_AnthropomorphicAndEngineeringClosure_20260619.md",
            "docs/Errata_Phase19_v1b_ImplementationSensitiveClosure_20260619.md",
            "docs/FinalReport_Phase19_0_VisualReceptorSketch_20260619.md",
            "reports/APV3_Phase19_0_VisualReceptorSketch_Showcase_20260619.html",
        ],
    },
    "19.0b0": {
        "files_must_exist": [
            "runtime/cognitive/percept_vector/__init__.py",
            "runtime/cognitive/percept_vector/vector_substrate.py",
            "tests/test_phase19_0b0_vector_schema.py",
            "docs/FinalReport_Phase19_0b0_VectorSubstrateSchema_20260619.md",
        ],
    },
    "19.0a": {
        "files_must_exist": [
            "apv3test/runtime/visual_receptor.py",
            "tests/test_phase19_0a_foveated_visual_repair.py",
            "scripts/reports/render_phase19_0a_showcase.py",
            "docs/FinalReport_Phase19_0a_FoveatedVisualRepair_20260619.md",
            "reports/APV3_Phase19_0a_FoveatedVisualRepair_Showcase_20260619.html",
        ],
    },
    "19.0b1": {
        "files_must_exist": [
            "runtime/cognitive/percept_vector/phase19_runtime.py",
            "tests/test_phase19_0b1_vector_population.py",
            "docs/FinalReport_Phase19_0b1_VectorPopulation_20260619.md",
        ],
    },
    "19.2": {
        "files_must_exist": [
            "runtime/cognitive/percept_vector/phase19_runtime.py",
            "tests/test_phase19_2_humanlike_confidence.py",
            "docs/FinalReport_Phase19_2_HumanlikeConfidence_20260619.md",
        ],
    },
    "19.3a": {
        "files_must_exist": [
            "runtime/cognitive/percept_vector/phase19_runtime.py",
            "tests/test_phase19_3_visual_probes.py",
            "docs/FinalReport_Phase19_3a_VisualLOOProbe_20260619.md",
        ],
    },
    "19.3b": {
        "files_must_exist": [
            "runtime/cognitive/percept_vector/phase19_runtime.py",
            "tests/test_phase19_3_visual_probes.py",
            "docs/FinalReport_Phase19_3b_RealPhotoStressProbe_20260619.md",
        ],
    },
    "19.1": {
        "files_must_exist": [
            "runtime/cognitive/percept_vector/phase19_runtime.py",
            "tests/test_phase19_audio_feedback_active.py",
            "docs/FinalReport_Phase19_1_AudioReceptor_20260619.md",
        ],
    },
    "19.1a": {
        "files_must_exist": [
            "runtime/cognitive/percept_vector/phase19_runtime.py",
            "tests/test_phase19_audio_feedback_active.py",
            "docs/FinalReport_Phase19_1a_AudioFoveatedRepair_20260619.md",
        ],
    },
    "19.4a": {
        "files_must_exist": [
            "runtime/cognitive/percept_vector/phase19_runtime.py",
            "tests/test_phase19_audio_feedback_active.py",
            "docs/FinalReport_Phase19_4a_AudioProbe_20260619.md",
        ],
    },
    "19.4b": {
        "files_must_exist": [
            "runtime/cognitive/percept_vector/phase19_runtime.py",
            "tests/test_phase19_audio_feedback_active.py",
            "docs/FinalReport_Phase19_4b_AudioTransferProbe_20260619.md",
        ],
    },
    "19.5": {
        "files_must_exist": [
            "runtime/cognitive/percept_vector/phase19_runtime.py",
            "tests/test_phase19_audio_feedback_active.py",
            "docs/FinalReport_Phase19_5_FeedbackBinding_20260619.md",
        ],
    },
    "19.6": {
        "files_must_exist": [
            "runtime/cognitive/percept_vector/phase19_runtime.py",
            "tests/test_phase19_audio_feedback_active.py",
            "docs/FinalReport_Phase19_6_ActivePerception_20260619.md",
            "scripts/reports/render_phase19_complete_showcase.py",
        ],
    },
    "19.7": {
        "files_must_exist": [
            "apv3test/runtime/visual_receptor.py",
            "runtime/cognitive/percept_vector/phase19_runtime.py",
            "tests/test_phase19_7_mask_recovery.py",
            "tests/test_phase19_7h_local_diagnostic_channels.py",
            "scripts/reports/render_phase19_generalization_effect_probe.py",
            "docs/Errata_Phase19_v1g_MaskRecoveryChannelValidityDiagnosticLibrary_20260619.md",
            "docs/FinalReport_Phase19_7_MaskRecoveryDiagnosticRecognition_20260619.md",
            "docs/FinalReport_Phase19_7h_LocalDiagnosticChannels_20260619.md",
            "reports/APV3_Phase19_GeneralizationEffectProbe_20260619.html",
        ],
    },
    "19.8a": {
        "files_must_exist": [
            "docs/Design_APV3.0_Phase19_8_RealPhotoTeachingLibrary_v1_20260619.md",
            "scripts/curriculum/download_real_teaching_photos.py",
            "scripts/curriculum/render_real_curation_page.py",
            "scripts/curriculum/ingest_real_teaching_photos.py",
            "scripts/reports/render_phase19_8_showcase.py",
            "tests/test_phase19_8_real_teaching_library.py",
            "docs/FinalReport_Phase19_8a_RealTeachingLibraryPipeline_20260619.md",
            "reports/APV3_Phase19_8_RealTeachingLibrary_Showcase_20260619.html",
        ],
    },
    "19.8b": {
        "files_must_exist": [
            "config/curriculum/assets/visual/real_teaching_candidates/curation.json",
            "config/curriculum/assets/visual/real_teaching_manifest.json",
            "docs/FinalReport_Phase19_8b_RealTeachingLibraryProbe_20260619.md",
            "reports/APV3_Phase19_GeneralizationEffectProbe_20260619.html",
        ],
    },
    "19.9": {
        "files_must_exist": [
            "docs/Design_APV3.0_Phase21_ObjectCentricLooking_AND_Phase19_9_ZvecRecall_v1_20260619.md",
            "runtime/cognitive/percept_vector/recall_index.py",
            "tests/test_phase19_9_zvec_recall_index.py",
            "scripts/reports/render_phase19_9_recall_showcase.py",
            "docs/FinalReport_Phase19_9_ZvecRecallIndex_20260620.md",
            "reports/APV3_Phase19_9_ZvecRecallIndex_Showcase_20260620.html",
        ],
    },
    "19.all": {
        "files_must_exist": [
            "runtime/cognitive/percept_vector/phase19_runtime.py",
            "docs/FinalReport_Phase19_Complete_20260619.md",
            "scripts/reports/render_phase19_complete_showcase.py",
            "reports/APV3_Phase19_MultimodalReceptorConfidence_Showcase_20260619.html",
        ],
    },
    "20.0": {
        "files_must_exist": [
            "docs/Design_APV3.0_Phase20_OpenChineseDialogueFoundation_v1_20260620.md",
            "docs/Errata_Phase20_v1a_SourcePrivacyFeedbackGate_20260620.md",
            "apv3test/runtime/phase20_open_dialogue.py",
            "apv3test/web_chat.py",
            "tests/test_phase20_open_dialogue_foundation.py",
            "scripts/reports/render_phase20_showcase.py",
            "docs/FinalReport_Phase20_0_OpenDialogueFoundation_20260620.md",
            "reports/APV3_Phase20_OpenDialogueFoundation_Showcase_20260620.html",
        ],
    },
    "20.1": {
        "files_must_exist": [
            "docs/Design_APV3.0_Phase20_1_WebDemoTeachingParadigm_v1_20260620.md",
            "apv3test/runtime/phase20_open_dialogue.py",
            "apv3test/web_chat.py",
            "apv3test/web/static/index.html",
            "apv3test/web/static/app.js",
            "tests/test_phase20_1_teaching_paradigm.py",
            "scripts/reports/render_phase20_1_showcase.py",
            "docs/FinalReport_Phase20_1_WebDemoTeachingParadigm_20260620.md",
            "reports/APV3_Phase20_1_WebDemoTeachingParadigm_Showcase_20260620.html",
        ],
    },
    "20.2_20.3": {
        "files_must_exist": [
            "docs/Design_APV3.0_Phase20_2_and_20_3_CooccurrenceTeachingAndMemoryPackages_v1_20260620.md",
            "apv3test/runtime/phase20_open_dialogue.py",
            "apv3test/runtime/phase20_memory_packages.py",
            "apv3test/web_chat.py",
            "apv3test/web/static/index.html",
            "apv3test/web/static/app.js",
            "tests/test_phase20_2_3_cooccurrence_memory.py",
            "scripts/reports/render_phase20_2_3_showcase.py",
            "docs/FinalReport_Phase20_2_3_CooccurrenceTeachingAndMemoryPackages_20260620.md",
            "reports/APV3_Phase20_2_3_CooccurrenceMemoryPackages_Showcase_20260620.html",
        ],
    },
    "20.4": {
        "files_must_exist": [
            "docs/Design_APV3.0_Phase20_4_OpenDialogueWorkbenchRepair_v1_20260620.md",
            "apv3test/web_chat.py",
            "apv3test/runtime/phase20_memory_packages.py",
            "apv3test/web/static/index.html",
            "apv3test/web/static/app.js",
            "apv3test/web/static/styles.css",
            "tests/test_phase20_4_workbench_repair.py",
            "scripts/reports/render_phase20_4_showcase.py",
            "docs/FinalReport_Phase20_4_OpenDialogueWorkbenchRepair_20260620.md",
            "reports/APV3_Phase20_4_OpenDialogueWorkbenchRepair_Showcase_20260620.html",
        ],
    },
    "20.5a": {
        "files_must_exist": [
            "docs/Design_APV3.0_Phase20_5_WorkbenchUIComplete_v1_20260620.md",
            "docs/Errata_Phase20_5_v1a_APPhilosophyHardening_20260620.md",
            "apv3test/runtime/phase20_open_dialogue.py",
            "apv3test/web_chat.py",
            "apv3test/web/static/index.html",
            "apv3test/web/static/app.js",
            "apv3test/web/static/styles.css",
            "tests/test_phase20_5a_runtime_workbench.py",
            "scripts/reports/render_phase20_5a_showcase.py",
            "docs/FinalReport_Phase20_5a_RuntimeWorkbench_20260620.md",
            "reports/APV3_Phase20_5a_RuntimeWorkbench_Showcase_20260620.html",
        ],
    },
    "20.6-stage0": {
        "files_must_exist": [
            "docs/Design_APV3.0_Phase20_6_FullRuntimeLoopFastSlowMemory_v1_20260620.md",
            "docs/Errata_Phase20_6_v1b_AntiProjectionFastSlowClosure_20260621.md",
            "docs/Errata_Phase20_6_v1c_APNativePerformanceAndAttentionClosure_20260621.md",
            "docs/Errata_Phase20_6_v1d_FormalModelAndImplementationClosure_20260621.md",
            "docs/Errata_Phase20_6_v1e_FinalSealing_20260621.md",
            "docs/Errata_Phase20_6_v1f_AffectiveCoRecallAndConcurrencyHardening_20260621.md",
            "docs/Errata_Phase20_6_v1g_APNativePhilosophyClosure_20260621.md",
            "apv3test/runtime/phase20_6_memory.py",
            "apv3test/runtime/phase20_6_runtime.py",
            "apv3test/runtime/phase20_open_dialogue.py",
            "apv3test/web/static/phase20_6_workbench.html",
            "apv3test/web/static/phase20_6_workbench.css",
            "apv3test/web/static/phase20_6_workbench.js",
            "tests/test_phase20_6_stage0_runtime_boundary.py",
            "tests/test_phase20_6_true_runtime_workbench_page.py",
            "tests/test_phase20_6_history_package_canvas.py",
            "docs/FinalReport_Phase20_6_Stage0_RuntimeBoundary_20260621.md",
        ],
    },
    "20.7-stage0": {
        "files_must_exist": [
            "docs/AP_Bottom_Principles_Whitepaper_20260626.txt",
            "docs/Design_APV3_Phase20_7_OpenDialogueFoundation_EngineeringMath_v1a_20260626.md",
            "docs/Errata_Phase20_7_v1a_OpenDialogueFoundationEngineeringClosure_20260626.md",
            "apv3test/runtime/phase20_7/__init__.py",
            "apv3test/runtime/phase20_7/api_schema.py",
            "apv3test/runtime/phase20_7/experience_log.py",
            "apv3test/runtime/phase20_7/models.py",
            "apv3test/runtime/phase20_7/runtime.py",
            "tests/test_phase20_7_stage0_runtime_boundary.py",
            "docs/FinalReport_Phase20_7_Stage0_RuntimeBoundary_20260626.md",
        ],
    },
    "20.7-stage1": {
        "files_must_exist": [
            "docs/AP_Bottom_Principles_Whitepaper_20260626.txt",
            "docs/Design_APV3_Phase20_7_OpenDialogueFoundation_EngineeringMath_v1a_20260626.md",
            "docs/Errata_Phase20_7_v1a_OpenDialogueFoundationEngineeringClosure_20260626.md",
            "apv3test/runtime/phase20_7/__init__.py",
            "apv3test/runtime/phase20_7/api_schema.py",
            "apv3test/runtime/phase20_7/experience_log.py",
            "apv3test/runtime/phase20_7/models.py",
            "apv3test/runtime/phase20_7/runtime.py",
            "tests/test_phase20_7_stage0_runtime_boundary.py",
            "tests/test_phase20_7_stage1_text_closed_loop.py",
            "docs/FinalReport_Phase20_7_Stage0_RuntimeBoundary_20260626.md",
            "docs/FinalReport_Phase20_7_Stage1_TextClosedLoop_20260626.md",
        ],
    },
    "20.7-stage2": {
        "files_must_exist": [
            "docs/AP_Bottom_Principles_Whitepaper_20260626.txt",
            "docs/Design_APV3_Phase20_7_OpenDialogueFoundation_EngineeringMath_v1a_20260626.md",
            "docs/Errata_Phase20_7_v1a_OpenDialogueFoundationEngineeringClosure_20260626.md",
            "apv3test/runtime/phase20_7/__init__.py",
            "apv3test/runtime/phase20_7/experience_log.py",
            "apv3test/runtime/phase20_7/models.py",
            "apv3test/runtime/phase20_7/runtime.py",
            "tests/test_phase20_7_stage0_runtime_boundary.py",
            "tests/test_phase20_7_stage1_text_closed_loop.py",
            "tests/test_phase20_7_stage2_experience_memory_indexes.py",
            "docs/FinalReport_Phase20_7_Stage0_RuntimeBoundary_20260626.md",
            "docs/FinalReport_Phase20_7_Stage1_TextClosedLoop_20260626.md",
            "docs/FinalReport_Phase20_7_Stage2_ExperienceMemoryIndexes_20260626.md",
        ],
    },
    "20.7-stage3": {
        "files_must_exist": [
            "docs/AP_Bottom_Principles_Whitepaper_20260626.txt",
            "docs/Design_APV3_Phase20_7_OpenDialogueFoundation_EngineeringMath_v1a_20260626.md",
            "apv3test/runtime/phase20_7/experience_log.py",
            "apv3test/runtime/phase20_7/models.py",
            "apv3test/runtime/phase20_7/runtime.py",
            "tests/test_phase20_7_stage0_runtime_boundary.py",
            "tests/test_phase20_7_stage1_text_closed_loop.py",
            "tests/test_phase20_7_stage2_experience_memory_indexes.py",
            "tests/test_phase20_7_stage3_structural_bccstar.py",
            "docs/FinalReport_Phase20_7_Stage0_RuntimeBoundary_20260626.md",
            "docs/FinalReport_Phase20_7_Stage1_TextClosedLoop_20260626.md",
            "docs/FinalReport_Phase20_7_Stage2_ExperienceMemoryIndexes_20260626.md",
            "docs/FinalReport_Phase20_7_Stage3_StructuralBCCStar_20260626.md",
        ],
    },
    "20.7-stage4": {
        "files_must_exist": [
            "docs/AP_Bottom_Principles_Whitepaper_20260626.txt",
            "docs/Design_APV3_Phase20_7_OpenDialogueFoundation_EngineeringMath_v1a_20260626.md",
            "apv3test/runtime/phase20_7/experience_log.py",
            "apv3test/runtime/phase20_7/models.py",
            "apv3test/runtime/phase20_7/runtime.py",
            "tests/test_phase20_7_stage0_runtime_boundary.py",
            "tests/test_phase20_7_stage1_text_closed_loop.py",
            "tests/test_phase20_7_stage2_experience_memory_indexes.py",
            "tests/test_phase20_7_stage3_structural_bccstar.py",
            "tests/test_phase20_7_stage4_unclosed_idle.py",
            "docs/FinalReport_Phase20_7_Stage0_RuntimeBoundary_20260626.md",
            "docs/FinalReport_Phase20_7_Stage1_TextClosedLoop_20260626.md",
            "docs/FinalReport_Phase20_7_Stage2_ExperienceMemoryIndexes_20260626.md",
            "docs/FinalReport_Phase20_7_Stage3_StructuralBCCStar_20260626.md",
            "docs/FinalReport_Phase20_7_Stage4_UnclosedIdleThink_20260626.md",
        ],
    },
    "20.7-stage5": {
        "files_must_exist": [
            "docs/AP_Bottom_Principles_Whitepaper_20260626.txt",
            "docs/Design_APV3_Phase20_7_OpenDialogueFoundation_EngineeringMath_v1a_20260626.md",
            "apv3test/runtime/phase20_7/experience_log.py",
            "apv3test/runtime/phase20_7/models.py",
            "apv3test/runtime/phase20_7/runtime.py",
            "apv3test/runtime/phase20_7/vision.py",
            "tests/test_phase20_7_stage0_runtime_boundary.py",
            "tests/test_phase20_7_stage1_text_closed_loop.py",
            "tests/test_phase20_7_stage2_experience_memory_indexes.py",
            "tests/test_phase20_7_stage3_structural_bccstar.py",
            "tests/test_phase20_7_stage4_unclosed_idle.py",
            "tests/test_phase20_7_stage5_visual_patch_reconstruction.py",
            "docs/FinalReport_Phase20_7_Stage0_RuntimeBoundary_20260626.md",
            "docs/FinalReport_Phase20_7_Stage1_TextClosedLoop_20260626.md",
            "docs/FinalReport_Phase20_7_Stage2_ExperienceMemoryIndexes_20260626.md",
            "docs/FinalReport_Phase20_7_Stage3_StructuralBCCStar_20260626.md",
            "docs/FinalReport_Phase20_7_Stage4_UnclosedIdleThink_20260626.md",
            "docs/FinalReport_Phase20_7_Stage5_VisualPatchReconstruction_20260626.md",
        ],
    },
    "20.7-stage6": {
        "files_must_exist": [
            "docs/AP_Bottom_Principles_Whitepaper_20260626.txt",
            "docs/Design_APV3_Phase20_7_OpenDialogueFoundation_EngineeringMath_v1a_20260626.md",
            "apv3test/runtime/phase20_7/audio.py",
            "apv3test/runtime/phase20_7/experience_log.py",
            "apv3test/runtime/phase20_7/models.py",
            "apv3test/runtime/phase20_7/runtime.py",
            "apv3test/runtime/phase20_7/vision.py",
            "tests/test_phase20_7_stage0_runtime_boundary.py",
            "tests/test_phase20_7_stage1_text_closed_loop.py",
            "tests/test_phase20_7_stage2_experience_memory_indexes.py",
            "tests/test_phase20_7_stage3_structural_bccstar.py",
            "tests/test_phase20_7_stage4_unclosed_idle.py",
            "tests/test_phase20_7_stage5_visual_patch_reconstruction.py",
            "tests/test_phase20_7_stage6_audio_tts.py",
            "docs/FinalReport_Phase20_7_Stage0_RuntimeBoundary_20260626.md",
            "docs/FinalReport_Phase20_7_Stage1_TextClosedLoop_20260626.md",
            "docs/FinalReport_Phase20_7_Stage2_ExperienceMemoryIndexes_20260626.md",
            "docs/FinalReport_Phase20_7_Stage3_StructuralBCCStar_20260626.md",
            "docs/FinalReport_Phase20_7_Stage4_UnclosedIdleThink_20260626.md",
            "docs/FinalReport_Phase20_7_Stage5_VisualPatchReconstruction_20260626.md",
            "docs/FinalReport_Phase20_7_Stage6_AudioTTS_20260626.md",
        ],
    },
    "20.7-stage7": {
        "files_must_exist": [
            "docs/AP_Bottom_Principles_Whitepaper_20260626.txt",
            "docs/Design_APV3_Phase20_7_OpenDialogueFoundation_EngineeringMath_v1a_20260626.md",
            "apv3test/runtime/phase20_7/audio.py",
            "apv3test/runtime/phase20_7/experience_log.py",
            "apv3test/runtime/phase20_7/models.py",
            "apv3test/runtime/phase20_7/runtime.py",
            "apv3test/runtime/phase20_7/vision.py",
            "apv3test/web/static/phase20_7_workbench.html",
            "apv3test/web/static/phase20_7_workbench.css",
            "apv3test/web/static/phase20_7_workbench.js",
            "apv3test/web_chat.py",
            "tests/test_phase20_7_stage0_runtime_boundary.py",
            "tests/test_phase20_7_stage1_text_closed_loop.py",
            "tests/test_phase20_7_stage2_experience_memory_indexes.py",
            "tests/test_phase20_7_stage3_structural_bccstar.py",
            "tests/test_phase20_7_stage4_unclosed_idle.py",
            "tests/test_phase20_7_stage5_visual_patch_reconstruction.py",
            "tests/test_phase20_7_stage6_audio_tts.py",
            "tests/test_phase20_7_stage7_api_workbench.py",
            "docs/FinalReport_Phase20_7_Stage7_APIWorkbench_20260626.md",
        ],
    },
    "20.7-stage8": {
        "files_must_exist": [
            "docs/AP_Bottom_Principles_Whitepaper_20260626.txt",
            "docs/Design_APV3_Phase20_7_OpenDialogueFoundation_EngineeringMath_v1a_20260626.md",
            "docs/UserGuide_Phase20_7_ReleaseDemo_20260626.md",
            "docs/FinalReport_Phase20_7_Stage8_ReleaseDemo_20260626.md",
            "scripts/run_phase20_7_release_demo.py",
            "scripts/verify_phase20_7_release_demo.py",
            "tests/test_phase20_7_stage8_release_demo.py",
            "reports/Phase20_7_release_demo_manifest_20260626.json",
            "reports/Phase20_7_performance_report_20260626.json",
            "reports/APV3_Phase20_7_ReleaseDemo_20260626.html",
            "reports/APV3_Phase20_7_ReleaseDemo_Package_20260626.zip",
            "reports/Phase20_7_redline_report_20260626.txt",
        ],
    },
    "21.0": {
        "files_must_exist": [
            "docs/Design_APV3.0_Phase21_ObjectCentricLooking_AND_Phase19_9_ZvecRecall_v1_20260619.md",
            "runtime/cognitive/percept_vector/object_looking.py",
            "tests/test_phase21_object_centric_looking.py",
            "scripts/reports/render_phase21_object_looking_showcase.py",
            "docs/FinalReport_Phase21_0_ObjectCentricLooking_20260619.md",
            "reports/APV3_Phase21_ObjectCentricLooking_Showcase_20260619.html",
        ],
    },
    "21.v1b": {
        "files_must_exist": [
            "docs/Errata_Phase21_v1b_TrulyLocalMasksForV10V11V12_20260620.md",
            "tests/test_phase21_object_centric_looking.py",
            "docs/FinalReport_Phase21_v1b_TrulyLocalObjectChannels_20260620.md",
        ],
    },
}


def check_phase_deliverables(phase_id: str) -> list:
    """声称完成某 phase 时检查对应交付物"""
    if phase_id not in PHASE_DELIVERABLES:
        return [f"Unknown phase {phase_id} (defined: {list(PHASE_DELIVERABLES.keys())})"]

    spec = PHASE_DELIVERABLES[phase_id]
    violations = []
    for filepath in spec.get("files_must_exist", []):
        if not Path(filepath).exists():
            violations.append(f"Phase {phase_id}: missing file {filepath}")

    # marker spawn rules 覆盖检查
    spawn_rules_path = Path("config/marker_spawn_rules.yaml")
    if spawn_rules_path.exists():
        try:
            import yaml
            rules = yaml.safe_load(spawn_rules_path.read_text(encoding="utf-8"))
            for kind in spec.get("must_have_marker_spawn_for", []):
                if kind not in rules:
                    violations.append(f"Phase {phase_id}: marker {kind} not in spawn rules")
        except ImportError:
            pass

    if phase_id == "20.6-stage0":
        violations.extend(check_phase20_6_stage0_redlines())
    if phase_id == "20.7-stage0":
        violations.extend(check_phase20_7_stage0_redlines())
    if phase_id == "20.7-stage1":
        violations.extend(check_phase20_7_stage1_redlines())
    if phase_id == "20.7-stage2":
        violations.extend(check_phase20_7_stage2_redlines())
    if phase_id == "20.7-stage3":
        violations.extend(check_phase20_7_stage3_redlines())
    if phase_id == "20.7-stage4":
        violations.extend(check_phase20_7_stage4_redlines())
    if phase_id == "20.7-stage5":
        violations.extend(check_phase20_7_stage5_redlines())
    if phase_id == "20.7-stage6":
        violations.extend(check_phase20_7_stage6_redlines())
    if phase_id == "20.7-stage7":
        violations.extend(check_phase20_7_stage7_redlines())
    if phase_id == "20.7-stage8":
        violations.extend(check_phase20_7_stage8_redlines())

    return violations


def check_phase20_6_stage0_redlines() -> list:
    """Phase 20.6 Stage0/Stage1 boundary scan for fake dialogue paths."""
    target_files = [
        Path("apv3test/runtime/phase20_open_dialogue.py"),
        Path("apv3test/runtime/phase20_6_memory.py"),
        Path("apv3test/runtime/phase20_6_runtime.py"),
        Path("apv3test/web_chat.py"),
        Path("apv3test/web/static/app.js"),
        Path("apv3test/web/static/phase20_6_workbench.html"),
        Path("apv3test/web/static/phase20_6_workbench.js"),
    ]
    forbidden = (
        "输入进入",
        "视觉聚焦",
        "文本运行时",
        "风格组装",
        "提交回复",
        "enumerate_objects_in_image",
        "reply_text = taught.response_text",
        "_phase20_5a2",
        "_build_phase20_5a2_workbench_ticks",
        "Phase20MultimodalSession.turn =",
        "命中教学",
        "教学命中",
        "未命中教师",
        "teaching_hit",
        "taught_answer",
        "direct_label_reply",
        "image_label_map",
        "_select_visible_token_source",
        "writable_count",
        "candidate_text",
        "fast_direct_reply",
        "answer_text",
        "history_projection",
        "replay_fake",
        "canvas_label",
        "direct_visual_label",
        "workbench_projection_over_phase20_runtime_events",
        "pytesseract",
        "easyocr",
        "paddleocr",
        "OpenAI TTS",
        "Google TTS",
        "Edge TTS",
        "audio_recognition_label",
    )
    required = (
        "run_phase20_6_runtime",
        "_next_token_candidates",
        "commit_reply",
        "system_stop_not_ap_stop",
        "extract_candidate_targets",
        "sensor_actuator_context",
        "reply_tts_audio",
        "teacher_guided_focus",
        "phase20_history_replay",
        "stored_runtime_tick_events",
        "visual_feature::",
    )
    violations = []
    combined = ""
    for path in target_files:
        if not path.exists():
            violations.append(f"Phase 20.6-stage0: missing scan target {path}")
            continue
        source = path.read_text(encoding="utf-8")
        combined += f"\n# {path}\n{source}"
        for token in forbidden:
            if token in source:
                violations.append(f"Phase 20.6-stage0: forbidden token {token!r} in {path}")
    for token in required:
        if token not in combined:
            violations.append(f"Phase 20.6-stage0: required boundary token {token!r} not found")
    return violations


def check_phase20_7_stage0_redlines() -> list:
    """Phase 20.7 Stage0 boundary scan for new-runtime isolation."""
    target_root = Path("apv3test/runtime/phase20_7")
    target_files = sorted(target_root.glob("*.py"))
    forbidden = (
        "phase20_6_runtime",
        "phase20_open_dialogue",
        "enumerate_objects_in_image",
        "image_label_map",
        "teaching_hit",
        "taught_answer",
        "direct_label_reply",
        "reply_text = taught",
        "full_reply_candidate",
        "candidate_text",
        "if keyword then answer",
        "regex route answer",
        "student_side_llm",
        "workbench_projection",
        "fake_tick_stage",
        "pytesseract",
        "easyocr",
        "paddleocr",
        "OpenAI TTS",
        "Google TTS",
        "Edge TTS",
        "audio_recognition_label",
    )
    required = (
        "run_phase20_7_turn",
        "RuntimeTickEventV2",
        "SourceTrustKey",
        "phase20_7_experience_events",
        "phase20_7_source_packets",
        "phase20_7_package_memberships",
        "experience_event_ids_written",
        "stage0_boundary_only",
    )
    violations = []
    if not target_root.exists():
        return [f"Phase 20.7-stage0: missing runtime boundary {target_root}"]
    combined = ""
    for path in target_files:
        source = path.read_text(encoding="utf-8")
        combined += f"\n# {path}\n{source}"
        for token in forbidden:
            if token in source:
                violations.append(f"Phase 20.7-stage0: forbidden token {token!r} in {path}")
    for token in required:
        if token not in combined:
            violations.append(f"Phase 20.7-stage0: required boundary token {token!r} not found")
    return violations


def check_phase20_7_stage1_redlines() -> list:
    """Phase 20.7 Stage1 scan for text closed-loop isolation."""
    violations = check_phase20_7_stage0_redlines()
    target_root = Path("apv3test/runtime/phase20_7")
    target_files = sorted(target_root.glob("*.py"))
    required = (
        "PHASE20_7_STAGE1_SCHEMA_ID",
        "text_receptor_observation",
        "experience_alignment",
        "exact_b0",
        "draft_grid_write",
        "request_teacher",
        "insert_experience_event",
        "insert_occurrence",
        "insert_structure_edge",
        "phase20_7_occurrences",
        "phase20_7_structure_edges",
    )
    combined = ""
    for path in target_files:
        combined += f"\n# {path}\n{path.read_text(encoding='utf-8')}"
    for token in required:
        if token not in combined:
            violations.append(f"Phase 20.7-stage1: required text-loop token {token!r} not found")
    return violations


def check_phase20_7_stage2_redlines() -> list:
    """Phase 20.7 Stage2 scan for rebuildable indexes and unified memory view."""
    violations = check_phase20_7_stage1_redlines()
    target_root = Path("apv3test/runtime/phase20_7")
    combined = ""
    for path in sorted(target_root.glob("*.py")):
        combined += f"\n# {path}\n{path.read_text(encoding='utf-8')}"
    required = (
        "phase20_7_exact_b0_index",
        "phase20_7_memory_tombstones",
        "rebuild_phase20_7_indexes",
        "list_unified_memory_entries",
        "tombstone_memory_entry",
        "create_import_batch",
        "unload_import_batch",
        "local_memory_package_unified",
        "fast_tendency",
        "slow_trace",
    )
    for token in required:
        if token not in combined:
            violations.append(f"Phase 20.7-stage2: required memory/index token {token!r} not found")
    return violations


def check_phase20_7_stage3_redlines() -> list:
    """Phase 20.7 Stage3 scan for B/C/C* structural recall."""
    violations = check_phase20_7_stage2_redlines()
    target_root = Path("apv3test/runtime/phase20_7")
    combined = ""
    for path in sorted(target_root.glob("*.py")):
        combined += f"\n# {path}\n{path.read_text(encoding='utf-8')}"
    required = (
        "PHASE20_7_STAGE3_SCHEMA_ID",
        "STRUCTURAL_B_THRESHOLD",
        "_find_structural_b",
        "_structural_similarity",
        "structural_bccstar",
        "c_forward",
        "c_backward",
        "cstar_packet",
        "writes_answer_directly",
    )
    for token in required:
        if token not in combined:
            violations.append(f"Phase 20.7-stage3: required B/C/C* token {token!r} not found")
    if "_inject_cstar_virtuals" not in combined and "_apply_cstar_statepool_feedback" not in combined:
        violations.append(
            "Phase 20.7-stage3: required B/C/C* token '_inject_cstar_virtuals' "
            "or current '_apply_cstar_statepool_feedback' not found"
        )
    return violations


def check_phase20_7_stage4_redlines() -> list:
    """Phase 20.7 Stage4 scan for unclosed feeling and idle thinking."""
    violations = check_phase20_7_stage3_redlines()
    target_root = Path("apv3test/runtime/phase20_7")
    combined = ""
    for path in sorted(target_root.glob("*.py")):
        combined += f"\n# {path}\n{path.read_text(encoding='utf-8')}"
    required = (
        "PHASE20_7_STAGE4_SCHEMA_ID",
        "phase20_7_unclosed_items",
        "upsert_unclosed_item",
        "resolve_unclosed_items",
        "list_active_unclosed_items",
        "idle_think",
        "maintain_unclosed",
        "unclosed_item_update",
        "unclosed_item_resolved",
    )
    for token in required:
        if token not in combined:
            violations.append(f"Phase 20.7-stage4: required unclosed/idle token {token!r} not found")
    return violations


def check_phase20_7_stage5_redlines() -> list:
    """Phase 20.7 Stage5 scan for visual patch payload reconstruction."""
    violations = check_phase20_7_stage4_redlines()
    target_root = Path("apv3test/runtime/phase20_7")
    combined = ""
    for path in sorted(target_root.glob("*.py")):
        combined += f"\n# {path}\n{path.read_text(encoding='utf-8')}"
    required = (
        "PHASE20_7_STAGE5_SCHEMA_ID",
        "run_visual_receptor_ticks",
        "SensoryCanvas",
        "visual_patch_payload",
        "visual_patch_sample",
        "visual_inner_picture",
        "clarity_coverage",
        "focus_samples_patch",
        "phase20_7_payload_blobs",
        "raw_path_stored",
    )
    forbidden = (
        "filename_label",
        "whole_image_label",
        "classify_image",
        "ocr_image",
    )
    for token in required:
        if token not in combined:
            violations.append(f"Phase 20.7-stage5: required visual token {token!r} not found")
    for token in forbidden:
        if token in combined:
            violations.append(f"Phase 20.7-stage5: forbidden visual token {token!r} found")
    return violations


def check_phase20_7_stage6_redlines() -> list:
    """Phase 20.7 Stage6 scan for audio audit and local xiaoyi TTS."""
    violations = check_phase20_7_stage5_redlines()
    target_root = Path("apv3test/runtime/phase20_7")
    combined = ""
    for path in sorted(target_root.glob("*.py")):
        combined += f"\n# {path}\n{path.read_text(encoding='utf-8')}"
    required = (
        "PHASE20_7_STAGE6_SCHEMA_ID",
        "run_audio_audit_ticks",
        "record_tts_actuator_tick",
        "select_xiaoyi_voice",
        "audio_audit_sample",
        "audio_audit_only",
        "reply_tts_audio",
        "xiaoyi",
        "local_only",
    )
    forbidden = (
        "cloud_tts",
        "remote_tts",
        "speech_recognition_label",
    )
    for token in required:
        if token not in combined:
            violations.append(f"Phase 20.7-stage6: required audio/TTS token {token!r} not found")
    for token in forbidden:
        if token in combined:
            violations.append(f"Phase 20.7-stage6: forbidden audio/TTS token {token!r} found")
    return violations


def check_phase20_7_stage7_redlines() -> list:
    """Phase 20.7 Stage7 scan for API and RuntimeTickEvent workbench."""
    violations = check_phase20_7_stage6_redlines()
    target_files = [
        Path("apv3test/web_chat.py"),
        Path("apv3test/web/static/phase20_7_workbench.html"),
        Path("apv3test/web/static/phase20_7_workbench.js"),
        Path("apv3test/web/static/phase20_7_workbench.css"),
    ]
    combined = ""
    for path in target_files:
        combined += f"\n# {path}\n{path.read_text(encoding='utf-8')}"
    required = (
        "/api/phase20_7/turn",
        "/api/phase20_7/memory/list",
        "/api/phase20_7/memory/delete",
        "phase20_7_workbench.html",
        "RuntimeTickEvent",
        "list_unified_memory_entries",
        "run_phase20_7_turn",
    )
    forbidden = (
        "phase20_6_workbench.js",
        "workbench_projection",
        "fake_tick_stage",
    )
    for token in required:
        if token not in combined:
            violations.append(f"Phase 20.7-stage7: required API/workbench token {token!r} not found")
    for token in forbidden:
        if token in combined:
            violations.append(f"Phase 20.7-stage7: forbidden API/workbench token {token!r} found")
    return violations


def check_phase20_7_stage8_redlines() -> list:
    """Phase 20.7 Stage8 scan for complete release demo package."""
    violations = check_phase20_7_stage7_redlines()
    target_files = [
        Path("scripts/run_phase20_7_release_demo.py"),
        Path("scripts/verify_phase20_7_release_demo.py"),
        Path("docs/UserGuide_Phase20_7_ReleaseDemo_20260626.md"),
        Path("docs/FinalReport_Phase20_7_Stage8_ReleaseDemo_20260626.md"),
    ]
    combined = ""
    for path in target_files:
        if path.exists():
            combined += f"\n# {path}\n{path.read_text(encoding='utf-8')}"
    required = (
        "APV3_Phase20_7_ReleaseDemo_Package_20260626.zip",
        "Phase20_7_performance_report_20260626.json",
        "Phase20_7_release_demo_manifest_20260626.json",
        "UserGuide_Phase20_7_ReleaseDemo_20260626.md",
        "verify_phase20_7_release_demo",
        "会学",
        "不是全知 LLM",
    )
    for token in required:
        if token not in combined:
            violations.append(f"Phase 20.7-stage8: required release token {token!r} not found")
    return violations


if __name__ == "__main__":
    main()
