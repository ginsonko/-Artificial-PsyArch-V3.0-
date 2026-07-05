#!/usr/bin/env python3
"""
check_constant_governance.py — 治理协议检查.
每常量必须分类 @structural / @scenario_tuneable / @experimental.
@experimental 必须有 initial_rationale.

v14 UNIFIED 配套.
"""

import re
import sys
from pathlib import Path


REQUIRED_CATEGORIES = {"@structural", "@scenario_tuneable", "@experimental"}


def parse_yaml_with_categories(yaml_path: str) -> list:
    """解析 yaml,提取每个 leaf 常量 + category 注释"""
    lines = Path(yaml_path).read_text(encoding="utf-8").splitlines()
    leaf_pattern = re.compile(
        r'^(\s*)([A-Za-z_][A-Za-z_0-9]*)\s*:\s*([0-9.\-+eE]+|true|false|"[^"]*")(\s*#.*)?$'
    )

    constants = []
    for i, line in enumerate(lines):
        m = leaf_pattern.match(line)
        if not m:
            continue
        indent, key, value, trailing = m.groups()
        category = None
        rationale = None

        # inline comment
        if trailing:
            comment = trailing.lstrip(" #")
            for cat in REQUIRED_CATEGORIES:
                if cat in comment:
                    category = cat
            if "—" in comment:
                rationale = comment.split("—", 1)[1].strip()
            elif "-" in comment[len(category) if category else 0:]:
                parts = comment.split("-", 1)
                if len(parts) == 2:
                    rationale = parts[1].strip()

        # 上一行 comment(如果 inline 无 category)
        if not category and i > 0:
            prev = lines[i - 1].strip()
            if prev.startswith("#"):
                prev_text = prev.lstrip("# ")
                for cat in REQUIRED_CATEGORIES:
                    if cat in prev_text:
                        category = cat
                        rationale = prev_text.replace(cat, "").strip()

        constants.append({
            "line": i + 1,
            "key": key,
            "value": value,
            "category": category,
            "rationale": rationale,
        })
    return constants


def check_governance(yaml_path: str) -> bool:
    constants = parse_yaml_with_categories(yaml_path)
    blockers = []
    warnings = []

    for c in constants:
        is_numeric = bool(re.match(r'^-?\d', c["value"]))
        if not is_numeric:
            continue

        if not c["category"]:
            blockers.append(
                f"L{c['line']}: '{c['key']}' = {c['value']} missing category "
                f"(must be @structural / @scenario_tuneable / @experimental)"
            )
            continue

        if c["category"] == "@experimental":
            if not c["rationale"] or len(c["rationale"]) < 3:
                warnings.append(
                    f"L{c['line']}: '{c['key']}' @experimental missing rationale (Phase X.Y to fill)"
                )

    if blockers:
        print(f"GOVERNANCE BLOCKERS ({len(blockers)}):")
        for v in blockers[:20]:
            print(f"  {v}")
        return False

    print(f"OK: Governance check passed ({len(constants)} numeric constants)")
    if warnings:
        print(f"  ({len(warnings)} warnings: @experimental constants pending rationale,")
        print(f"   to be filled in by Phase implementation reports)")
    return True


def main():
    yaml_path = "config/apv3_constants.yaml"
    if not Path(yaml_path).exists():
        print(f"FAIL: {yaml_path} not found")
        sys.exit(1)
    ok = check_governance(yaml_path)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
