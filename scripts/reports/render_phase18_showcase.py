from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Mapping, Sequence

from apv3test.runtime.course_replay import CourseReplayRuntime


REPORT_PATH = Path("reports/APV3_Phase18_CleanConceptCards_Showcase_20260618.html")
DEMO_IDS = ("demo_clean_card_apple", "demo_clean_card_banana", "demo_clean_card_orange")


def main() -> None:
    runtime = CourseReplayRuntime()
    traces = [runtime.run_demo(demo_id) for demo_id in DEMO_IDS]
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(render_page(runtime, traces), encoding="utf-8")
    print(REPORT_PATH.as_posix())


def render_page(runtime: CourseReplayRuntime, traces: Sequence[Mapping[str, object]]) -> str:
    cards = "\n".join(render_demo(runtime, trace) for trace in traces)
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>APV3 Phase 18：干净概念卡片课程回放</title>
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
      grid-template-columns: minmax(280px, .8fr) minmax(430px, 1.2fr);
      gap: 14px;
      align-items: start;
    }}
    .material-strip {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
      margin-top: 10px;
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
      width: 118px;
      height: 118px;
      object-fit: contain;
      border-radius: 8px;
      background: #fff;
      display: block;
    }}
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
      min-height: 100px;
    }}
    .flow b {{ display: block; color: var(--blue); margin-bottom: 4px; }}
    .boundary {{ background: var(--warn); }}
    @media (max-width: 980px) {{
      h1 {{ font-size: 26px; }}
      .metric-grid, .demo, .flow {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <div class="hero">
      <h1>APV3 Phase 18：先学干净概念卡片</h1>
      <p class="lead">这一步把 Phase 17 的真实照片重新定位：真实照片先退到泛化探测，第一层教学改用无文字、低噪声、主体清楚的概念卡片。这样更像人类教小孩：先把对象本身看清楚，再把能力迁移到真实世界。</p>
      <div class="pill-row">
        <span class="pill">15 张 clean-card PNG</span>
        <span class="pill">3 个水果概念</span>
        <span class="pill">3 个 Web 回放 demo</span>
        <span class="pill">每个 demo 6 tick</span>
      </div>
    </div>
  </header>
  <main>
    <section>
      <h2>这次证明了什么</h2>
      <div class="metric-grid">
        <div class="metric"><b>15</b><span>无文字干净卡片资产</span></div>
        <div class="metric"><b>9 / 3 / 3</b><span>train / held-out / contrast</span></div>
        <div class="metric"><b>8</b><span>课程工作台 demo 总数，旧 5 个仍保留</span></div>
        <div class="metric"><b>0</b><span>前端硬编码输出</span></div>
      </div>
      <p>核心变化不是“更漂亮的图”，而是课程顺序更合理：早期学习先降低背景干扰，让 AP 更稳定地把注意力放在概念主体上；真实照片仍然保留，但放到后面的泛化探测阶段。</p>
    </section>

    <section>
      <h2>AP 看到一张卡片时，内部过程是什么</h2>
      <div class="flow">
        <div><b>tick 1</b>训练卡片进入，形成 PERCEIVED 来源</div>
        <div><b>tick 2</b>形成 SDPL LearningPacket</div>
        <div><b>tick 3</b>held-out 未见卡片探测</div>
        <div><b>tick 4</b>contrast 其它水果对照</div>
        <div><b>tick 5</b>行动竞争，课程倾向进入候选</div>
        <div><b>tick 6</b>提交可审计回应</div>
      </div>
    </section>

    {cards}

    <section class="boundary">
      <h2>边界说明</h2>
      <p>Phase 18.0 证明的是：干净概念卡片资产、课程包、课程回放 runtime、Web 工作台和逐 tick trace 已经接通。它不宣称 AP 已经完成真实世界视觉识别，也不宣称大规模物体学习已经完成。下一步才适合把 Phase 17 真实照片作为泛化探测接进来，看干净卡片形成的概念倾向能不能迁移到更复杂的真实图像。</p>
    </section>
  </main>
</body>
</html>
"""


def render_demo(runtime: CourseReplayRuntime, trace: Mapping[str, object]) -> str:
    demo = trace["demo"]
    ticks = list(trace["ticks"])
    first_tick = ticks[0]
    train_assets = first_tick["asset_refs"]
    images = "\n".join(render_asset(runtime, asset_id) for asset_id in train_assets)
    rows = "\n".join(render_tick_row(tick) for tick in ticks)
    return f"""
    <section>
      <h2>{escape(str(demo["title"]))}</h2>
      <div class="demo">
        <div>
          <h3>题目内容</h3>
          <p>{escape(str(demo["question"]))}</p>
          <div class="material-strip">{images}</div>
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


def render_asset(runtime: CourseReplayRuntime, asset_id: str) -> str:
    path = runtime.asset_path_for_id(asset_id).as_posix()
    rel = "../" + path
    return f"""<div class="asset"><img src="{escape(rel)}" alt="{escape(asset_id)}"><small><code>{escape(path)}</code></small></div>"""


def render_tick_row(tick: Mapping[str, object]) -> str:
    refs = " · ".join(str(item) for item in tick.get("asset_refs", ()))
    return (
        "<tr>"
        f"<td>tick {escape(str(tick['tick']))}</td>"
        f"<td>{escape(str(tick['title']))}</td>"
        f"<td><code>{escape(refs)}</code><br>{escape(str(tick['mind']['marker']))} / {escape(str(tick['mind']['source']))}</td>"
        f"<td>{escape(str(tick['q_score']))}</td>"
        f"<td>{escape(str(tick['ap_output']))}</td>"
        "</tr>"
    )


if __name__ == "__main__":
    main()
