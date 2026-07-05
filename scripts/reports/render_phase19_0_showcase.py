from __future__ import annotations

import html
import math
import sys
from pathlib import Path
from typing import Mapping, Sequence

from PIL import Image

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apv3test.runtime.visual_receptor import (
    extract_visual_audit_path,
    extract_visual_fast_path,
    prepare_visual_fast_frame,
    render_prototype_imagination,
    render_sensory_sketch,
    sample_audit_images,
)
from runtime.cognitive.state_pool.state_pool import load_constant


REPORT_PATH = Path("reports/APV3_Phase19_0_VisualReceptorSketch_Showcase_20260619.html")
ARTIFACT_DIR = Path("reports/phase19_0_inner_picture")


def main() -> None:
    paths = sample_audit_images(6)
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    examples = []
    for index, path in enumerate(paths[:6], start=1):
        trace = extract_visual_audit_path(path, tick=index)
        input_copy = ARTIFACT_DIR / f"example_{index}_input.png"
        Image.open(path).convert("RGB").save(input_copy, format="PNG")
        sensory = render_sensory_sketch(trace, out_dir=ARTIFACT_DIR, stem=f"example_{index}_sensory")
        proto = render_prototype_imagination(trace, out_dir=ARTIFACT_DIR, stem=f"example_{index}_proto")
        examples.append({
            "path": input_copy,
            "trace": trace,
            "sensory_path": sensory.path,
            "proto_path": proto.path,
            "sensory_meta": sensory.metadata,
            "proto_meta": proto.metadata,
        })
    fast_p95 = _measure_fast_p95(paths[:12])
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(render_page(examples, fast_p95), encoding="utf-8")
    print(REPORT_PATH.as_posix())


def render_page(examples: Sequence[Mapping[str, object]], fast_p95: float) -> str:
    cards = "\n".join(_render_example(example, idx) for idx, example in enumerate(examples, start=1))
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>APV3 Phase 19.0：视觉感受器和内心草图</title>
  <style>
    :root {{
      --bg: #f4f6f4;
      --paper: #ffffff;
      --ink: #17211d;
      --muted: #64736d;
      --line: #dbe4df;
      --accent: #2f6f5e;
      --accent-soft: #e7f3ee;
      --warn: #fff7e4;
      --blue: #245a8f;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", Arial, sans-serif;
      line-height: 1.62;
      letter-spacing: 0;
    }}
    header {{
      background: #fff;
      border-bottom: 1px solid var(--line);
      padding: 38px 22px 24px;
    }}
    main, .hero {{ max-width: 1180px; margin: 0 auto; }}
    main {{ padding: 20px; }}
    h1 {{ margin: 0 0 10px; font-size: 34px; line-height: 1.2; }}
    h2 {{ margin: 0 0 12px; font-size: 22px; }}
    h3 {{ margin: 0 0 8px; font-size: 17px; }}
    p {{ margin: 8px 0; color: var(--muted); }}
    .lead {{ max-width: 940px; color: #263630; font-size: 17px; }}
    .pill-row {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 16px; }}
    .pill {{
      border: 1px solid #bfd8cf;
      background: var(--accent-soft);
      color: #1f4a41;
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 13px;
    }}
    section {{
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 18px;
      margin: 14px 0;
    }}
    .metric-grid {{
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 10px;
    }}
    .metric {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      background: #fbfdfc;
    }}
    .metric b {{ display: block; color: var(--blue); font-size: 26px; }}
    .metric span {{ color: var(--muted); font-size: 13px; }}
    .flow {{
      display: grid;
      grid-template-columns: repeat(5, minmax(0, 1fr));
      gap: 8px;
    }}
    .flow div {{
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 10px;
      min-height: 110px;
      background: #fbfdfc;
    }}
    .flow b {{ display: block; color: var(--accent); margin-bottom: 4px; }}
    .example {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 14px;
      align-items: start;
    }}
    .images {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
    }}
    figure {{
      margin: 0;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfdfc;
      padding: 8px;
    }}
    figure img {{
      width: 100%;
      height: 172px;
      object-fit: contain;
      background: #fff;
      border-radius: 6px;
      display: block;
    }}
    figcaption {{ color: var(--muted); font-size: 12px; margin-top: 6px; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 8px; text-align: left; vertical-align: top; }}
    th {{ color: var(--muted); background: #fbfdfc; }}
    td:first-child {{ color: var(--blue); font-weight: 700; white-space: nowrap; }}
    code {{
      font-family: Consolas, "Courier New", monospace;
      border: 1px solid #d8e2de;
      background: #f0f4f2;
      border-radius: 6px;
      padding: 1px 5px;
      overflow-wrap: anywhere;
    }}
    .boundary {{ background: var(--warn); }}
    @media (max-width: 980px) {{
      h1 {{ font-size: 26px; }}
      .metric-grid, .flow, .example, .images {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="hero">
      <h1>APV3 Phase 19.0：视觉感受器和内心草图</h1>
      <p class="lead">这一阶段补的是“眼睛”和“内心画面回放”的地基：AP 不再只拿到粗颜色/粗形状，而是把一张图拆成 V0..V12 共 8654 维感受轨迹；同时把感知草图 <code>sensory_sketch</code> 和原型想象 <code>prototype_imagination</code> 分开渲染，避免把“看到的”和“想到的”混成一件事。</p>
      <div class="pill-row">
        <span class="pill">V0..V12 = 8654 维</span>
        <span class="pill">fast path p95 = {fast_p95:.2f} ms</span>
        <span class="pill">sensory/proto 源分离</span>
        <span class="pill">不证明 AP 已经会识别真实照片</span>
      </div>
    </div>
  </header>
  <main>
    <section>
      <h2>这次证明了什么</h2>
      <div class="metric-grid">
        <div class="metric"><b>8654</b><span>单张视觉 audit trace 的固定维度</span></div>
        <div class="metric"><b>4544</b><span>V0 近原始视网膜通道维度</span></div>
        <div class="metric"><b>{fast_p95:.2f}ms</b><span>已准备小帧上的 fast path p95</span></div>
        <div class="metric"><b>2</b><span>渲染模式：感知草图 / 原型想象</span></div>
      </div>
      <p>这一步解决的是前面真实照片泛化假阳性的根部问题之一：AP 先要有足够丰富、可审计、可回放的视觉感受轨迹。后续 19.2 才会接拟人把握感公式，19.3 才会重新做真实照片视觉-only 探测。</p>
    </section>

    <section>
      <h2>AP 看到一张图时发生了什么</h2>
      <div class="flow">
        <div><b>tick 快扫</b>fast path 只处理已准备的小帧，抽取粗颜色、粗边缘、粗布局，不渲染。</div>
        <div><b>audit 细看</b>按 V0..V12 采集 8654 维特征，包含低分辨率全局图、焦点 patch、颜色、纹理、边缘、形状、局部部件和颜色块空间分布。</div>
        <div><b>感知草图</b><code>R_sketch</code> 只从输入 trace 渲染，代表“我看到的大概样子”。</div>
        <div><b>原型想象</b><code>R_proto</code> 从原型/特征摘要渲染，代表“我脑补的典型样子”。</div>
        <div><b>来源审计</b>metadata 强制记录 <code>epistemic_source</code>、hash、confidence_score/tier，且不访问 evaluator label。</div>
      </div>
    </section>

    {cards}

    <section class="boundary">
      <h2>边界说明</h2>
      <p>Phase 19.0 不证明 AP 已经会识别真实照片，不证明“苹果/香蕉/橙子”泛化成功，也不实现 19.2 的拟人把握感公式、19.3 的 stratified LOO 探测、19.1 的听觉感受器或 19.5 的 source-aware feedback。它只把视觉通道、内心画面和来源审计地基补齐。</p>
    </section>
  </main>
</body>
</html>
"""


def _render_example(example: Mapping[str, object], index: int) -> str:
    path = Path(example["path"])
    trace = example["trace"]
    sensory_path = Path(example["sensory_path"])
    proto_path = Path(example["proto_path"])
    sensory_meta = example["sensory_meta"]
    return f"""
    <section>
      <h2>样例 {index}：输入图像到内心草图</h2>
      <div class="example">
        <div class="images">
          <figure>
            <img src="{_rel(path)}" alt="输入图像 {index}">
            <figcaption>输入图像：仅作为像素来源，AP trace 不读取文件名语义。</figcaption>
          </figure>
          <figure>
            <img src="{_rel(sensory_path)}" alt="sensory sketch {index}">
            <figcaption><code>sensory_sketch</code>：从输入 trace 渲染。</figcaption>
          </figure>
          <figure>
            <img src="{_rel(proto_path)}" alt="prototype imagination {index}">
            <figcaption><code>prototype_imagination</code>：原型想象草图。</figcaption>
          </figure>
        </div>
        <div>
          <h3>审计 metadata 摘要</h3>
          <table>
            <tr><td>feature_vector_dim</td><td>{len(trace.feature_vector)}</td></tr>
            <tr><td>V0..V12</td><td>{html.escape(str(trace.channel_lengths))}</td></tr>
            <tr><td>render_mode</td><td><code>{html.escape(str(sensory_meta["render_mode"]))}</code></td></tr>
            <tr><td>epistemic_source</td><td><code>{html.escape(str(sensory_meta["epistemic_source"]))}</code></td></tr>
            <tr><td>evaluator_label_accessed</td><td>{sensory_meta["evaluator_label_accessed"]}</td></tr>
            <tr><td>decision_tier</td><td><code>{html.escape(str(sensory_meta["decision_tier"]))}</code>（19.2 前固定不判断）</td></tr>
            <tr><td>input_trace_hash</td><td><code>{html.escape(str(sensory_meta["input_trace_hash"])[:24])}...</code></td></tr>
          </table>
        </div>
      </div>
    </section>
    """


def _measure_fast_p95(paths: Sequence[Path]) -> float:
    frames = [prepare_visual_fast_frame(Image.open(path).convert("RGB")) for path in paths[:12]]
    if not frames:
        return 0.0
    extract_visual_fast_path(frames[0])
    latencies = [extract_visual_fast_path(frame, tick=index).elapsed_ms for index, frame in enumerate(frames, start=1)]
    return sorted(latencies)[math.ceil(len(latencies) * 0.95) - 1]


def _rel(path: Path) -> str:
    try:
        return html.escape(path.resolve().relative_to(REPORT_PATH.parent.resolve()).as_posix())
    except ValueError:
        return html.escape(path.resolve().as_uri())


if __name__ == "__main__":
    main()
