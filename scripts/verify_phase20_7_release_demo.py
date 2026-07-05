from __future__ import annotations

import json
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RUN_ID = "20260626"
MANIFEST_PATH = ROOT / "reports" / f"Phase20_7_release_demo_manifest_{RUN_ID}.json"
PERFORMANCE_PATH = ROOT / "reports" / f"Phase20_7_performance_report_{RUN_ID}.json"
HTML_PATH = ROOT / "reports" / f"APV3_Phase20_7_ReleaseDemo_{RUN_ID}.html"
ZIP_PATH = ROOT / "reports" / f"APV3_Phase20_7_ReleaseDemo_Package_{RUN_ID}.zip"


def main() -> int:
    errors: list[str] = []
    for path in (MANIFEST_PATH, PERFORMANCE_PATH, HTML_PATH, ZIP_PATH):
        if not path.exists():
            errors.append(f"missing {path}")
    if errors:
        print("\n".join(errors))
        return 1

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    performance = json.loads(PERFORMANCE_PATH.read_text(encoding="utf-8"))
    flows = manifest.get("flows", {})

    if flows.get("text_learning", {}).get("recall_reply") != "你也好":
        errors.append("text recall demo did not return learned reply")
    if not flows.get("text_learning", {}).get("near_has_structural_b"):
        errors.append("near text demo did not show structural_b")
    if flows.get("unclosed_idle", {}).get("repeat_unknown_reply") != "我还在想这个。":
        errors.append("unclosed repeat demo did not maintain unclosed feeling")
    if flows.get("unclosed_idle", {}).get("cat_recall_reply") != "猫是一种动物":
        errors.append("cat teaching demo did not recall learned text")
    if int(flows.get("visual_patch_reconstruction", {}).get("visual_tick_count", 0)) < 2:
        errors.append("visual demo did not produce enough visual ticks")
    if flows.get("audio_tts", {}).get("tts_action", {}).get("voice_preference") != "xiaoyi":
        errors.append("tts demo did not prefer xiaoyi")

    samples = performance.get("samples", {})
    text_p95 = float(samples.get("text_ms", {}).get("p95_ms", 999999))
    visual_p95 = float(samples.get("visual_ms", {}).get("p95_ms", 999999))
    if text_p95 > float(performance["thresholds"]["text_turn_p95_ms"]):
        errors.append(f"text p95 too slow: {text_p95}")
    if visual_p95 > float(performance["thresholds"]["visual_turn_p95_ms"]):
        errors.append(f"visual p95 too slow: {visual_p95}")

    with zipfile.ZipFile(ZIP_PATH, "r") as zf:
        names = set(zf.namelist())
    required_in_zip = {
        "reports/Phase20_7_release_demo_manifest_20260626.json",
        "reports/Phase20_7_performance_report_20260626.json",
        "reports/APV3_Phase20_7_ReleaseDemo_20260626.html",
        "reports/Phase20_7_redline_report_20260626.txt",
        "docs/UserGuide_Phase20_7_ReleaseDemo_20260626.md",
        "apv3test/web/static/phase20_7_workbench.html",
        "apv3test/web/static/phase20_7_workbench.js",
    }
    missing = sorted(required_in_zip - names)
    if missing:
        errors.append(f"zip missing: {missing}")

    if errors:
        print("\n".join(errors))
        return 1
    print("OK: Phase20.7 release demo package verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
