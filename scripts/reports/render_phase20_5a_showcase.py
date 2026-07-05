from __future__ import annotations

from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from apv3test.web_chat import APV3WebChatApp


OUT = Path("reports/APV3_Phase20_5a_RuntimeWorkbench_Showcase_20260620.html")
DB = Path("data/phase20_5a_showcase/phase20_5a.sqlite")


def main() -> int:
    DB.parent.mkdir(parents=True, exist_ok=True)
    if DB.exists():
        DB.unlink()
    app = APV3WebChatApp(state_db_path=DB)
    first = app.phase20_turn({"text": "你好", "max_ticks": 8, "idle_ticks": 2})
    teach = app.phase20_teach({"teaching_reply_text": "你好。"})
    unrelated = app.phase20_turn({"text": "你是谁?", "max_ticks": 8, "idle_ticks": 2})
    repeat = app.phase20_turn({"text": "你好", "max_ticks": 8, "idle_ticks": 2})
    html = render(first, teach, unrelated, repeat)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(OUT.as_posix())
    return 0


def render(first: dict, teach: dict, unrelated: dict, repeat: dict) -> str:
    trace = repeat["turn"]["workbench_tick_trace"]
    rows = "\n".join(
        "<tr>"
        f"<td>{event['tick_index']}</td>"
        f"<td>{esc(event['title'])}</td>"
        f"<td>{esc(event['action_chosen'].get('action_id', ''))}</td>"
        f"<td>{esc('false' if not event['is_projection'] else 'true')}</td>"
        f"<td>{esc(event['summary'])}</td>"
        "</tr>"
        for event in trace
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>APV3 Phase 20.5a Runtime Workbench</title>
  <style>
    body {{ margin:0; font-family:"Microsoft YaHei",Arial,sans-serif; background:#f7f7f8; color:#1f2937; line-height:1.65; }}
    main {{ max-width:1120px; margin:0 auto; padding:28px 18px 42px; }}
    h1 {{ margin:0 0 8px; font-size:28px; }}
    h2 {{ margin:26px 0 10px; font-size:20px; }}
    .lead {{ color:#64748b; }}
    .grid {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:14px; }}
    .card, table {{ background:#fff; border:1px solid #d8e2e7; border-radius:8px; padding:14px; }}
    .bubble {{ max-width:78%; padding:10px 12px; border-radius:8px; margin:8px 0; white-space:pre-wrap; }}
    .user {{ margin-left:auto; background:#1f2937; color:#fff; }}
    .ap {{ background:#eef6ff; border:1px solid #cbddee; }}
    .system {{ margin-left:auto; margin-right:auto; background:#ecfdf5; border:1px solid #bbf7d0; color:#14532d; }}
    table {{ border-collapse:collapse; width:100%; padding:0; overflow:hidden; }}
    td, th {{ border-bottom:1px solid #e1e8ec; padding:9px 10px; text-align:left; vertical-align:top; }}
    tr:last-child td {{ border-bottom:0; }}
    .ok {{ color:#15803d; font-weight:700; }}
    .warn {{ color:#92400e; font-weight:700; }}
    @media (max-width:820px) {{ .grid {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
<main>
  <h1>Phase 20.5a: 真实 Runtime Tick 工作台骨架</h1>
  <p class="lead">这一阶段修的是底座真实性: tick 回放来自运行过程中即时产生的 RuntimeTickEvent, 不再从最终回复倒推展示故事。</p>

  <h2>本阶段证明了什么</h2>
  <div class="grid">
    <div class="card"><b class="ok">RuntimeTickEvent</b><p>每轮 turn 真实 emit 输入、视觉、文本运行时、共现召回、风格组装、提交、空 tick 事件。</p></div>
    <div class="card"><b class="ok">Projection = false</b><p>工作台 trace 全部读取真实 event; 若降级为 projection, UI 会显示警告。</p></div>
    <div class="card"><b class="ok">8 面板骨架</b><p>历史、聊天、回放、折线、内心、想法云、记忆、教学包生态已有布局入口。</p></div>
  </div>

  <h2>示例对话</h2>
  <div class="card">
    <div class="bubble user">你好</div>
    <div class="bubble ap">{esc(first['turn']['reply_text'])}</div>
    <div class="bubble system">{esc(teach['teaching']['trace']['ui_summary'])}</div>
    <div class="bubble user">你是谁?</div>
    <div class="bubble ap">{esc(unrelated['turn']['reply_text'])}</div>
    <div class="bubble user">你好</div>
    <div class="bubble ap">{esc(repeat['turn']['reply_text'])}</div>
  </div>

  <h2>真实 tick event</h2>
  <table>
    <thead><tr><th>#</th><th>阶段</th><th>action</th><th>projection</th><th>说明</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>

  <h2>边界</h2>
  <div class="card">
    <p><b class="warn">还没有宣称:</b> 主动停 action competition、慢记忆持久化、TTS、画布、录音识别、辅助线教学已经完成。这些属于 Phase 20.5b/20.5c。</p>
  </div>
</main>
</body>
</html>"""


def esc(value: object) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


if __name__ == "__main__":
    raise SystemExit(main())

