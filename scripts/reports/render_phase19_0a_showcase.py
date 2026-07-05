from __future__ import annotations

import html
import sys
from pathlib import Path

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apv3test.runtime.visual_receptor import (
    SensoryCanvas,
    extract_visual_audit_path_v2,
    render_prediction_overlay_stub,
    render_remembered_overlay_stub,
    render_sensory_canvas_sketch,
    sample_audit_images,
)


REPORT_PATH = Path("reports/APV3_Phase19_0a_FoveatedVisualRepair_Showcase_20260619.html")
ARTIFACT_DIR = Path("reports/phase19_0a_foveated")


def main() -> None:
    paths = sample_audit_images(1)
    if not paths:
        raise SystemExit("No audit image available")
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    source = paths[0]
    image = Image.open(source).convert("RGB")
    input_path = ARTIFACT_DIR / "input.png"
    image.save(input_path)
    trace = extract_visual_audit_path_v2(source, tick=190)
    canvas = SensoryCanvas.from_native_image(source, tick=0)
    width, height = image.size
    fixations = (
        (width // 2, height // 2),
        (width // 3, height // 3),
        ((width * 2) // 3, height // 3),
        (width // 3, (height * 2) // 3),
        ((width * 2) // 3, (height * 2) // 3),
        (width // 2, height // 2),
        (width // 2, height // 3),
        (width // 2, (height * 2) // 3),
        (width // 3, height // 2),
        ((width * 2) // 3, height // 2),
    )
    snapshots = {}
    for tick, focus in enumerate(fixations, start=1):
        canvas.update_from_native_image(source, focus_xy=focus, tick=tick)
        if tick in (1, 5, 10):
            artifact = render_sensory_canvas_sketch(canvas, out_dir=ARTIFACT_DIR, stem=f"canvas_tick_{tick}")
            snapshots[tick] = artifact.path
    remembered = render_remembered_overlay_stub(out_dir=ARTIFACT_DIR, stem="remembered_overlay")
    predicted = render_prediction_overlay_stub(out_dir=ARTIFACT_DIR, stem="prediction_overlay")
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(
        render_page(input_path, snapshots, remembered.path, predicted.path, trace),
        encoding="utf-8",
    )
    print(REPORT_PATH.as_posix())


def render_page(input_path: Path, snapshots: dict[int, Path], remembered: Path, predicted: Path, trace) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>APV3 Phase 19.0a：焦点高清与多 tick 内心画面</title>
  <style>
    body {{ margin:0; font-family:"Microsoft YaHei","Segoe UI",Arial,sans-serif; background:#f4f6f4; color:#17211d; line-height:1.62; }}
    header, main {{ max-width:1180px; margin:0 auto; padding:24px; }}
    h1 {{ font-size:32px; margin:0 0 10px; }}
    h2 {{ font-size:21px; margin:0 0 10px; }}
    section {{ background:white; border:1px solid #dbe4df; border-radius:8px; padding:18px; margin:14px 0; }}
    .grid {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:10px; }}
    figure {{ margin:0; border:1px solid #dbe4df; border-radius:8px; padding:8px; background:#fbfdfc; }}
    img {{ width:100%; height:210px; object-fit:contain; background:white; display:block; border-radius:6px; }}
    figcaption {{ color:#64736d; font-size:13px; margin-top:6px; }}
    code {{ background:#eef4f1; border:1px solid #d6e2dd; border-radius:5px; padding:1px 5px; }}
    table {{ width:100%; border-collapse:collapse; }}
    td {{ border-bottom:1px solid #dbe4df; padding:8px; }}
    td:first-child {{ color:#245a8f; font-weight:700; }}
    .warn {{ background:#fff7e4; }}
    @media(max-width:900px) {{ .grid {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
  <header>
    <h1>APV3 Phase 19.0a：焦点高清与多 tick 内心画面</h1>
    <p>这一阶段修复的是你指出的核心体验问题：AP 的内心画面必须来自原图焦点直采，周边按清晰度渐变，连续看多个 tick 后画布覆盖和相似度上升。</p>
  </header>
  <main>
    <section>
      <h2>逐 tick 回放</h2>
      <div class="grid">
        <figure><img src="{_rel(input_path)}" alt="原图"><figcaption>原图。用于 audit，对 AP 不暴露文件名语义。</figcaption></figure>
        <figure><img src="{_rel(snapshots[1])}" alt="单 tick"><figcaption>单 tick：只有一个注视点附近最清楚。</figcaption></figure>
        <figure><img src="{_rel(snapshots[5])}" alt="5 tick"><figcaption>5 tick：多个注视区域被拼到 SensoryCanvas。</figcaption></figure>
        <figure><img src="{_rel(snapshots[10])}" alt="10 tick"><figcaption>10 tick：覆盖更广，画面认知更稳定。</figcaption></figure>
      </div>
    </section>
    <section>
      <h2>三层内心画面边界</h2>
      <div class="grid">
        <figure><img src="{_rel(snapshots[10])}" alt="perceived"><figcaption><code>PERCEIVED_SENSORY_SKETCH</code>，只来自当前感受器和 canvas。</figcaption></figure>
        <figure><img src="{_rel(remembered)}" alt="remembered"><figcaption><code>REMEMBERED_SKETCH</code>，19.0b1 之前只是 schema overlay。</figcaption></figure>
        <figure><img src="{_rel(predicted)}" alt="predicted"><figcaption><code>INFERRED_SKETCH</code>，19.2 之前只是 schema overlay。</figcaption></figure>
      </div>
    </section>
    <section>
      <h2>审计数字</h2>
      <table>
        <tr><td>feature_vector_dim</td><td>{len(trace.feature_vector)}</td></tr>
        <tr><td>V0 foveated</td><td>{trace.channel_lengths["V0"]}</td></tr>
        <tr><td>receptor_version</td><td><code>{html.escape(str(trace.metadata["receptor_version"]))}</code></td></tr>
        <tr><td>patch_native_resolution</td><td>{trace.metadata["patch_native_resolution"]}</td></tr>
        <tr><td>evaluator_label_accessed</td><td>{trace.metadata["evaluator_label_accessed"]}</td></tr>
      </table>
    </section>
    <section class="warn">
      <h2>边界</h2>
      <p>Phase 19.0a 不证明真实照片识别、不证明对象泛化、不证明 B/C 召回质量、不证明多模态绑定，也不证明开放对话完成。它只证明 foveated visual repair：原图焦点直采、ClarityField、多 tick SensoryCanvas 和三层 overlay 边界。</p>
    </section>
  </main>
</body>
</html>"""


def _rel(path: Path) -> str:
    try:
        return html.escape(path.resolve().relative_to(REPORT_PATH.parent.resolve()).as_posix())
    except ValueError:
        return html.escape(path.resolve().as_uri())


if __name__ == "__main__":
    main()

