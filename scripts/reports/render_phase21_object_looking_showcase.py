from __future__ import annotations

import html
import math
import sys
from pathlib import Path

from PIL import Image, ImageDraw

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from runtime.cognitive.percept_vector.object_looking import (
    build_object_centric_training_traces,
    count_objects,
    enumerate_objects_in_image,
)
from runtime.cognitive.percept_vector.phase19_runtime import VisualTeachingExample, visual_recognize_v1_7
from runtime.cognitive.state_pool.state_pool import load_constant


ASSET_DIR = Path("reports/phase21_object_looking_assets")
REPORT = Path("reports/APV3_Phase21_ObjectCentricLooking_Showcase_20260619.html")


def main() -> None:
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    training = _generate_training_assets()
    concept_traces = build_object_centric_training_traces(training)
    probes = _generate_probe_assets()
    rows = []
    for path in probes:
        result = enumerate_objects_in_image(path, teaching_examples=training, concept_traces=concept_traces)
        full = visual_recognize_v1_7(path, teaching_examples=training, tick=700)
        rows.append((path, result, full))
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(_render(training, rows), encoding="utf-8")
    print(REPORT.as_posix())


def _generate_training_assets() -> tuple[VisualTeachingExample, ...]:
    examples: list[VisualTeachingExample] = []
    tick = 1
    for label in ("apple", "banana", "orange"):
        for index in range(int(load_constant("phase21.object_looking.synthetic_transform_count"))):
            path = ASSET_DIR / f"teacher_{label}_{index}.png"
            image = _single_fruit(label, index=index)
            image.save(path)
            examples.append(VisualTeachingExample(path, label, "phase21_synthetic_teacher", tick))
            tick += 1
    return tuple(examples)


def _generate_probe_assets() -> tuple[Path, ...]:
    paths: list[Path] = []
    for index, labels in enumerate((
        ("apple", "banana", "orange"),
        ("banana", "apple"),
        ("orange", "banana"),
        ("apple", "orange"),
    )):
        path = ASSET_DIR / f"probe_multi_{index}.png"
        _multi_fruit(labels, index=index).save(path)
        paths.append(path)
    return tuple(paths)


def _single_fruit(label: str, *, index: int) -> Image.Image:
    size = int(load_constant("phase21.object_looking.synthetic_canvas_px"))
    image = Image.new("RGB", (size, size), (247, 248, 244))
    draw = ImageDraw.Draw(image)
    cx = size // 2 + (index - 1) * 6
    cy = size // 2 + (index % 2) * 5
    scale = 1.0 + (index - 1.5) * 0.05
    _draw_fruit(draw, label, cx, cy, scale=scale, rotation=index * 0.17)
    return image.rotate((index - 1) * 4, resample=Image.Resampling.BICUBIC, fillcolor=(247, 248, 244))


def _multi_fruit(labels: tuple[str, ...], *, index: int) -> Image.Image:
    size = int(load_constant("phase21.object_looking.synthetic_canvas_px"))
    image = Image.new("RGB", (size, size), (246, 247, 242))
    draw = ImageDraw.Draw(image)
    positions_by_count = {
        2: ((72, 86), (184, 174)),
        3: ((66, 78), (188, 82), (128, 188)),
        4: ((62, 72), (190, 78), (72, 188), (188, 188)),
    }
    positions = positions_by_count.get(len(labels), positions_by_count[3])
    for slot, label in enumerate(labels):
        cx, cy = positions[slot]
        _draw_fruit(draw, label, cx, cy, scale=0.72 + 0.05 * slot, rotation=(index + slot) * 0.22)
    return image


def _draw_fruit(ImageDraw_obj: ImageDraw.ImageDraw, label: str, cx: int, cy: int, *, scale: float, rotation: float) -> None:
    if label == "apple":
        r = int(46 * scale)
        ImageDraw_obj.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(196, 35, 45), outline=(116, 24, 35), width=3)
        ImageDraw_obj.rectangle((cx - 5, cy - r - 22, cx + 4, cy - r + 2), fill=(94, 58, 31))
        ImageDraw_obj.ellipse((cx + 7, cy - r - 20, cx + 34, cy - r - 4), fill=(55, 135, 62))
        ImageDraw_obj.ellipse((cx - r // 3, cy - r // 4, cx - r // 8, cy - r // 12), fill=(242, 126, 126))
    elif label == "orange":
        r = int(45 * scale)
        ImageDraw_obj.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(232, 122, 28), outline=(159, 78, 18), width=3)
        for angle in range(0, 360, 45):
            px = cx + int(math.cos(math.radians(angle)) * r * 0.45)
            py = cy + int(math.sin(math.radians(angle)) * r * 0.45)
            ImageDraw_obj.ellipse((px - 2, py - 2, px + 2, py + 2), fill=(246, 170, 72))
    elif label == "banana":
        length = int(96 * scale)
        thickness = int(28 * scale)
        dx = int(math.cos(rotation) * length / 2)
        dy = int(math.sin(rotation) * length / 2)
        ImageDraw_obj.line((cx - dx, cy - dy, cx + dx, cy + dy), fill=(231, 198, 46), width=thickness)
        ImageDraw_obj.line((cx - dx, cy - dy, cx + dx, cy + dy), fill=(151, 105, 24), width=3)
        ImageDraw_obj.ellipse((cx - dx - 8, cy - dy - 8, cx - dx + 8, cy - dy + 8), fill=(116, 83, 33))
        ImageDraw_obj.ellipse((cx + dx - 8, cy + dy - 8, cx + dx + 8, cy + dy + 8), fill=(116, 83, 33))
    else:
        raise ValueError(label)


def _render(training: tuple[VisualTeachingExample, ...], rows: list[tuple[Path, object, object]]) -> str:
    cards = "\n".join(
        f"<figure><img src='{_rel(example.path)}'><figcaption>{html.escape(example.visible_teacher_label)}</figcaption></figure>"
        for example in training[:6]
    )
    result_rows = "\n".join(_result_row(path, result, full) for path, result, full in rows)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>APV3 Phase 21：对象中心扫视识别</title>
  <style>
    body{{margin:0;font-family:"Microsoft YaHei","Segoe UI",Arial,sans-serif;background:#f6f7f5;color:#18221d;line-height:1.65}}
    header,main{{max-width:1180px;margin:0 auto;padding:24px}}
    section{{background:white;border:1px solid #dce5df;border-radius:8px;padding:18px;margin:14px 0}}
    h1{{font-size:30px;margin:0 0 8px}} h2{{font-size:21px;margin:0 0 8px}}
    .cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:12px}}
    figure{{margin:0;border:1px solid #dce5df;border-radius:8px;padding:8px;background:#fbfcfa}}
    img{{max-width:100%;height:140px;object-fit:contain;display:block;margin:auto}}
    table{{width:100%;border-collapse:collapse;font-size:14px}} th,td{{border-bottom:1px solid #dce5df;padding:8px;text-align:left;vertical-align:top}}
    code{{background:#edf4f0;padding:1px 5px;border-radius:5px}} .good{{color:#17653a;font-weight:700}} .muted{{color:#65736b}}
  </style>
</head>
<body>
<header>
  <h1>APV3 Phase 21：对象中心扫视识别</h1>
  <p>这页展示一个最小闭环：先教 AP 看单个苹果、香蕉、橙子，再把少量变形后的水果放到同一张图里，让 AP 用候选目标、视焦点跳转和局部对象特征逐个列举。</p>
</header>
<main>
  <section><h2>教学材料</h2><div class="cards">{cards}</div></section>
  <section>
    <h2>AP 逐图输出</h2>
    <table><thead><tr><th>题目图</th><th>整图倾向</th><th>扫视过程</th><th>列举结果</th><th>计数</th></tr></thead><tbody>{result_rows}</tbody></table>
  </section>
  <section>
    <h2>证明了什么</h2>
    <p>本阶段证明识别不再只是整图 label：候选区域先以 class-agnostic 方式进入 state_pool，再由视觉注意力动作选择焦点，最后在局部对象视野里重算 V7/V10/V11/V12 等特征。它仍不宣称真实世界照片识别完成，也不宣称 Zvec 或开放对话底座已完成。</p>
  </section>
</main>
</body>
</html>"""


def _result_row(path: Path, result: object, full: object) -> str:
    objects = getattr(result, "objects")
    scan = getattr(result, "scan_trace")
    labels = [
        f"{item.recognition.top_visible_label} <code>{item.recognition.decision_tier}</code> {item.recognition.nearest_negative_margin:.3f}"
        for item in objects
    ]
    scan_text = "<br>".join(
        f"tick {row['tick']}: 看 bbox={row.get('bbox')} -> {html.escape(str(row.get('top_visible_label')))}"
        for row in scan
    )
    return (
        "<tr>"
        f"<td><img src='{_rel(path)}'><br><span class='muted'>{html.escape(path.name)}</span></td>"
        f"<td>{html.escape(full.top_visible_label)} <code>{html.escape(full.decision_tier)}</code><br>margin {full.nearest_negative_margin:.3f}</td>"
        f"<td>{scan_text}</td>"
        f"<td class='good'>{'<br>'.join(labels)}</td>"
        f"<td>{count_objects(result)}</td>"
        "</tr>"
    )


def _rel(path: Path) -> str:
    return html.escape(path.resolve().relative_to(REPORT.parent.resolve()).as_posix())


if __name__ == "__main__":
    main()
