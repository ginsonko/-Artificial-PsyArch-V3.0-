from __future__ import annotations

import html
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from runtime.cognitive.percept_vector.phase19_runtime import (
    VisualTeachingExample,
    visual_recognize_v1_7,
)
from runtime.cognitive.state_pool.state_pool import load_constant


REPORT = Path("reports/APV3_Phase19_GeneralizationEffectProbe_20260619.html")


def main() -> None:
    rows = []
    for mode, train in (
        ("clean_cards_only", _training_examples(include_real=False)),
        ("diagnostic_library", _training_examples(include_real=True)),
        ("curated_real_teaching", _curated_real_training_examples()),
    ):
        if not train:
            continue
        for index, (truth, path) in enumerate(_query_examples(), start=100):
            result = visual_recognize_v1_7(path, teaching_examples=train, tick=index)
            second = result.all_concept_scores[1] if len(result.all_concept_scores) > 1 else None
            rows.append(
                {
                    "mode": mode,
                    "file": path,
                    "truth": truth,
                    "top": result.top_visible_label,
                    "ok": result.top_visible_label == truth,
                    "tier": result.decision_tier,
                    "raw": result.raw_confidence,
                    "top_score": result.all_concept_scores[0].diagnostic_score if result.all_concept_scores else 0.0,
                    "second": second.visible_teacher_label if second is not None else "",
                    "second_score": second.diagnostic_score if second is not None else 0.0,
                    "margin": result.nearest_negative_margin,
                    "channels": "/".join(result.all_concept_scores[0].most_diagnostic_channels)
                    if result.all_concept_scores
                    else "",
                    "disabled": _disabled_channels(result.metadata.get("channel_validity", {})),
                    "stage": " > ".join(result.stage_trace),
                    "filename_used": result.used_filename_label,
                }
            )

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(_render(rows), encoding="utf-8")
    print(REPORT.as_posix())


def _training_examples(*, include_real: bool) -> tuple[VisualTeachingExample, ...]:
    clean = Path("config/curriculum/assets/visual/clean_cards")
    real = Path("config/curriculum/assets/visual/real")
    examples: list[VisualTeachingExample] = []
    tick = 1
    for label in ("apple", "banana", "orange"):
        for index in range(3):
            examples.append(
                VisualTeachingExample(
                    clean / f"noun_{label}_train_{index}.png",
                    label,
                    "clean_train",
                    tick,
                )
            )
            tick += 1
        if include_real:
            for index in range(3):
                examples.append(
                    VisualTeachingExample(
                        real / f"noun_{label}_train_{index}.png",
                        label,
                        "diagnostic_real_train",
                        tick,
                    )
                )
                tick += 1
    return tuple(examples)


def _query_examples() -> tuple[tuple[str, Path], ...]:
    asset_dir = Path("真实图片测试资产")
    return (
        ("apple", asset_dir / "真实苹果1.jpeg"),
        ("apple", asset_dir / "真实苹果2.jpg"),
        ("apple", asset_dir / "真实苹果3.jpeg"),
        ("banana", asset_dir / "真实香蕉1.webp"),
        ("banana", asset_dir / "真实香蕉2.webp"),
        ("banana", asset_dir / "真实香蕉3.webp"),
        ("banana", asset_dir / "真实香蕉4.webp"),
        ("orange", asset_dir / "真实橙子1.webp"),
        ("orange", asset_dir / "真实橙子2.webp"),
        ("orange", asset_dir / "真实橙子3.jpeg"),
        ("orange", asset_dir / "绿色橙子1.webp"),
        ("apple", asset_dir / "黄绿色苹果1.jpg"),
    )


def _curated_real_training_examples() -> tuple[VisualTeachingExample, ...]:
    manifest = Path("config/curriculum/assets/visual/real_teaching_manifest.json")
    if not manifest.exists():
        return ()
    payload = json.loads(manifest.read_text(encoding="utf-8"))
    examples: list[VisualTeachingExample] = []
    tick = 1000
    for record in payload.get("records", []):
        if record.get("split") != "train":
            continue
        concept = str(record.get("concept", ""))
        if concept not in {"apple", "banana", "orange"}:
            continue
        examples.append(
            VisualTeachingExample(
                Path(str(record["path"])),
                concept,
                "curated_real_teaching_train",
                tick,
            )
        )
        tick += 1
    return tuple(examples)


def _render(rows: list[dict]) -> str:
    clean_rows = [row for row in rows if row["mode"] == "clean_cards_only"]
    diagnostic_rows = [row for row in rows if row["mode"] == "diagnostic_library"]
    curated_rows = [row for row in rows if row["mode"] == "curated_real_teaching"]
    correct_clean = sum(1 for row in clean_rows if row["ok"])
    correct_diagnostic = sum(1 for row in diagnostic_rows if row["ok"])
    correct_curated = sum(1 for row in curated_rows if row["ok"])
    body = "\n".join(_row(row) for row in rows)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>APV3 Phase 19.8b 真实教学库泛化探测</title>
  <style>
    body{{margin:0;font-family:"Microsoft YaHei","Segoe UI",Arial,sans-serif;background:#f6f7f5;color:#17211d;line-height:1.6}}
    header,main{{max-width:1240px;margin:0 auto;padding:24px}}
    h1{{font-size:30px;margin:0 0 8px}} h2{{font-size:21px;margin:0 0 8px}}
    section{{background:white;border:1px solid #dbe4df;border-radius:8px;padding:18px;margin:14px 0}}
    table{{width:100%;border-collapse:collapse;font-size:13px}} th,td{{border-bottom:1px solid #dbe4df;padding:8px;vertical-align:middle;text-align:left}}
    img{{width:88px;height:68px;object-fit:contain;background:#fff;border:1px solid #dbe4df;border-radius:6px}}
    .ok{{color:#1d6b3a;font-weight:700}} .bad{{color:#a63a2a;font-weight:700}} code{{background:#eef4f1;border-radius:5px;padding:1px 5px}}
  </style>
</head>
<body>
<header>
  <h1>APV3 Phase 19.8b：真实教学库泛化探测</h1>
  <p>测试侧用用户放入的真实照片。AP 侧不读取文件名语义，文件名只用于这张审计表的人类对照。</p>
</header>
<main>
  <section>
    <h2>结论</h2>
    <p>只用干净卡片训练：<b>{correct_clean}/{len(clean_rows)}</b>。加入旧诊断库真实样本：<b>{correct_diagnostic}/{len(diagnostic_rows)}</b>。加入人工筛选真实教学库：<b>{correct_curated}/{len(curated_rows)}</b>。本页使用 Phase 19.7h 管线：C 召回 → B 召回 → 13 通道诊断 noisy-OR → 通道有效性门 → 拟人把握感，而不是旧版全维 cosine 直接 argmax。</p>
  </section>
  <section>
    <h2>逐图结果</h2>
    <table>
      <thead><tr><th>训练模式</th><th>图片</th><th>人类标签</th><th>AP 倾向</th><th>结果</th><th>把握</th><th>top</th><th>第二名</th><th>margin</th><th>top 通道</th><th>禁用通道</th><th>阶段</th></tr></thead>
      <tbody>{body}</tbody>
    </table>
  </section>
  <section>
    <h2>边界</h2>
    <p>Phase 19.8b 检查的是“人工筛选真实教学库是否缓解 clean-card 到真实图的域差”。它仍不宣称完整真实世界视觉识别完成；curated 结果只代表这些概念和这些图片下的阶段性证据。</p>
  </section>
</main>
</body>
</html>"""


def _row(row: dict) -> str:
    cls = "ok" if row["ok"] else "bad"
    mark = "正确" if row["ok"] else "错误"
    return (
        "<tr>"
        f"<td><code>{html.escape(row['mode'])}</code></td>"
        f"<td><img src='{_rel(row['file'])}'><br>{html.escape(row['file'].name)}</td>"
        f"<td>{html.escape(row['truth'])}</td>"
        f"<td>{html.escape(row['top'])}</td>"
        f"<td class='{cls}'>{mark}</td>"
        f"<td><code>{html.escape(row['tier'])}</code> {row['raw']:.3f}</td>"
        f"<td>{row['top_score']:.3f}</td>"
        f"<td>{html.escape(row['second'])} {row['second_score']:.3f}</td>"
        f"<td>{row['margin']:.3f}</td>"
        f"<td>{html.escape(row['channels'])}</td>"
        f"<td>{html.escape(row['disabled'])}</td>"
        f"<td>{html.escape(row['stage'])}</td>"
        "</tr>"
    )


def _disabled_channels(validity: dict) -> str:
    floor = float(load_constant("phase19_7.channel_validity_min_ratio"))
    disabled = [
        str(channel)
        for channel, ratio in sorted(validity.items())
        if float(ratio) < floor
    ]
    return "/".join(disabled)


def _rel(path: Path) -> str:
    try:
        return html.escape(path.resolve().relative_to(REPORT.parent.resolve()).as_posix())
    except ValueError:
        return html.escape(path.resolve().as_uri())


if __name__ == "__main__":
    main()
