from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Mapping, Sequence

from apv3test.runtime.course_replay import CourseReplayRuntime


REPORT_PATH = Path("reports/APV3_Phase18_1_RealPhotoGeneralizationProbe_Showcase_20260618.html")
DEMO_IDS = (
    "demo_generalize_clean_to_real_apple",
    "demo_generalize_clean_to_real_banana",
    "demo_generalize_clean_to_real_orange",
)


def main() -> None:
    runtime = CourseReplayRuntime()
    traces = [runtime.run_demo(demo_id) for demo_id in DEMO_IDS]
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(render_page(runtime, traces), encoding="utf-8")
    print(REPORT_PATH.as_posix())


def render_page(runtime: CourseReplayRuntime, traces: Sequence[Mapping[str, object]]) -> str:
    demos = "\n".join(render_demo(runtime, trace) for trace in traces)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>APV3 Phase 18.1：真实照片泛化探测审计纠正</title>
  <style>
    :root {{
      --bg: #f5f7f8;
      --paper: #ffffff;
      --ink: #172126;
      --muted: #60727a;
      --line: #d9e3e7;
      --accent: #0f766e;
      --accent-soft: #e7f4f1;
      --blue: #245a8f;
      --good: #16734e;
      --warn: #fff8e8;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: "Microsoft YaHei", "PingFang SC", "Segoe UI", Arial, sans-serif;
      line-height: 1.65;
      letter-spacing: 0;
    }}
    header {{
      padding: 40px 24px 24px;
      background: #ffffff;
      border-bottom: 1px solid var(--line);
    }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 22px; }}
    .hero {{ max-width: 1180px; margin: 0 auto; }}
    h1 {{ margin: 0; font-size: 34px; line-height: 1.2; }}
    h2 {{ margin: 0 0 12px; font-size: 22px; }}
    h3 {{ margin: 0 0 8px; font-size: 17px; }}
    p {{ margin: 8px 0; color: var(--muted); }}
    .lead {{ max-width: 900px; color: #2c3b41; font-size: 17px; }}
    .pill-row {{ display: flex; flex-wrap: wrap; gap: 8px; margin-top: 18px; }}
    .pill {{
      border: 1px solid #bfdbd6;
      background: var(--accent-soft);
      color: #17453f;
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
      background: #fbfdff;
      padding: 14px;
    }}
    .metric b {{ display: block; color: var(--blue); font-size: 26px; }}
    .metric span {{ color: var(--muted); font-size: 13px; }}
    .demo {{
      display: grid;
      grid-template-columns: minmax(320px, .9fr) minmax(440px, 1.1fr);
      gap: 14px;
      align-items: start;
    }}
    .asset-row {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      margin: 10px 0 16px;
    }}
    .probe-row {{
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 8px;
      margin: 10px 0 16px;
    }}
    .asset {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfdff;
      padding: 8px;
      display: grid;
      place-items: center;
      min-height: 148px;
    }}
    .asset img {{
      width: 100%;
      height: 132px;
      object-fit: contain;
      border-radius: 6px;
      background: #fff;
      display: block;
    }}
    .asset b {{ display: block; color: var(--blue); font-size: 12px; margin-top: 6px; }}
    .asset small {{ display: block; color: var(--muted); overflow-wrap: anywhere; font-size: 11px; }}
    .answer {{
      margin-top: 12px;
      border-left: 4px solid var(--good);
      background: #edf8f2;
      padding: 10px 12px;
      border-radius: 0 8px 8px 0;
      font-weight: 700;
    }}
    table {{ width: 100%; border-collapse: collapse; font-size: 14px; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 8px; vertical-align: top; text-align: left; }}
    th {{ color: var(--muted); font-weight: 600; background: #fbfdff; }}
    td:first-child {{ color: var(--blue); font-weight: 700; white-space: nowrap; }}
    code {{
      font-family: Consolas, "Courier New", monospace;
      background: #f0f4f5;
      border: 1px solid #d8e2e7;
      border-radius: 6px;
      padding: 1px 5px;
      overflow-wrap: anywhere;
    }}
    .flow {{
      display: grid;
      grid-template-columns: repeat(6, minmax(0, 1fr));
      gap: 8px;
    }}
    .flow div {{
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #fbfdff;
      padding: 10px;
      min-height: 104px;
    }}
    .flow b {{ display: block; color: var(--blue); margin-bottom: 4px; }}
    .boundary {{ background: var(--warn); }}
    @media (max-width: 980px) {{
      h1 {{ font-size: 26px; }}
      .metric-grid, .demo, .flow, .asset-row, .probe-row {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="hero">
      <h1>APV3 Phase 18.1：干净卡片到真实照片泛化探测</h1>
      <p class="lead">审计纠正：这一步不是有效视觉泛化证明。它只证明 clean-card 训练材料和 Phase 17 真实照片探测材料能进入同一条回放 trace；当前 Q 倾向仍然受到课程标签和 intended_use 能量桶影响，所以不能说 AP 真的从像素里分辨出了香蕉、橙子或苹果。</p>
      <div class="pill-row">
        <span class="pill">3 个 clean → real 审计 demo</span>
        <span class="pill">每个 demo 6 tick</span>
        <span class="pill">clean-card train</span>
        <span class="pill">标记为非视觉证明</span>
      </div>
    </div>
  </header>
  <main>
    <section>
      <h2>这次真实证明了什么</h2>
      <div class="metric-grid">
        <div class="metric"><b>2</b><span>同时出现的 manifest：phase18_clean_concept_cards_v1 + phase17_real_visual_assets_v1</span></div>
        <div class="metric"><b>3</b><span>苹果 / 香蕉 / 橙子跨资产回放审计</span></div>
        <div class="metric"><b>false</b><span>visual_generalization_valid</span></div>
        <div class="metric"><b>0</b><span>前端硬编码答案</span></div>
      </div>
      <p>用户指出真实照片素材本身太混杂：香蕉是香蕉树黑白图，橙子偏绿，苹果对照又偏红橙色。复核后确认：当前 trace 的“held-out 高于 contrast”不是视觉分辨结果，而是标签介导和能量桶差异造成的假阳性。报告现在把它作为失败审计样例保留。</p>
      <p><code>probe_packet_contains_curriculum_label_and_energy_bucket_confound</code></p>
    </section>

    <section>
      <h2>AP 的逐 tick 过程</h2>
      <div class="flow">
        <div><b>tick 1</b>干净卡片教学进入</div>
        <div><b>tick 2</b>概念 LearningPacket 稳定</div>
        <div><b>tick 3</b>真实照片 held-out 进入，但仍带课程标签</div>
        <div><b>tick 4</b>contrast 对照受到能量桶差异影响</div>
        <div><b>tick 5</b>行动竞争结果不可作为视觉证据</div>
        <div><b>tick 6</b>提交诚实结论：还不能确认</div>
      </div>
    </section>

    {demos}

    <section class="boundary">
      <h2>边界说明</h2>
      <p>Phase 18.1 现在只证明课程回放层面的跨素材接线可审计。它不宣称 AP 已经完成任意真实照片识别，不宣称已经能处理任意复杂场景，也不宣称开放对话底座已经完成多模态真实世界理解。下一步 Phase 18.2 必须实现视觉-only 探测：学生侧 packet 不能携带 label / entry_id / target class，held-out 与 contrast 的差异只能来自 AP-native 视觉特征或感知原型。</p>
    </section>
  </main>
</body>
</html>
"""


def render_demo(runtime: CourseReplayRuntime, trace: Mapping[str, object]) -> str:
    demo = trace["demo"]
    ticks = list(trace["ticks"])
    train_assets = ticks[0]["asset_refs"]
    real_held = ticks[2]["asset_refs"][0]
    real_contrast = ticks[3]["asset_refs"][0]
    train_images = "\n".join(render_asset(runtime, asset_id, "clean train") for asset_id in train_assets)
    real_images = "\n".join(
        (
            render_asset(runtime, real_held, "real held-out"),
            render_asset(runtime, real_contrast, "real contrast"),
        )
    )
    rows = "\n".join(render_tick_row(tick) for tick in ticks)
    return f"""
    <section>
      <h2>{escape(str(demo["title"]))}</h2>
      <div class="demo">
        <div>
          <h3>题目内容</h3>
          <p>{escape(str(demo["question"]))}</p>
          <p><b>先教：</b>干净卡片</p>
          <div class="asset-row">{train_images}</div>
          <p><b>再测：</b>真实 held-out 与 contrast 照片</p>
          <div class="probe-row">{real_images}</div>
          <div class="answer">AP 最终输出：{escape(str(trace["summary"]["final_output"]))}</div>
        </div>
        <div>
          <h3>AP 输出过程</h3>
          <table>
            <thead><tr><th>tick</th><th>阶段</th><th>材料/来源</th><th>Q 倾向</th><th>AP 输出</th></tr></thead>
            <tbody>{rows}</tbody>
          </table>
        </div>
      </div>
    </section>
"""


def render_asset(runtime: CourseReplayRuntime, asset_id: str, label: str) -> str:
    path = runtime.asset_path_for_id(asset_id).as_posix()
    rel = "../" + path
    return f"""<div class="asset"><img src="{escape(rel)}" alt="{escape(asset_id)}"><b>{escape(label)}</b><small><code>{escape(path)}</code></small></div>"""


def render_tick_row(tick: Mapping[str, object]) -> str:
    refs = " · ".join(str(item) for item in tick.get("asset_refs", ()))
    manifests = " · ".join(str(item) for item in tick.get("manifest_ids", ()))
    return (
        "<tr>"
        f"<td>tick {escape(str(tick['tick']))}</td>"
        f"<td>{escape(str(tick['title']))}</td>"
        f"<td><code>{escape(refs)}</code><br>{escape(manifests)}</td>"
        f"<td>{escape(str(tick['q_score']))}</td>"
        f"<td>{escape(str(tick['ap_output']))}</td>"
        "</tr>"
    )


if __name__ == "__main__":
    main()
