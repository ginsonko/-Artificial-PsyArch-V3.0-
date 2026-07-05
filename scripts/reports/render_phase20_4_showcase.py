from __future__ import annotations

from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from apv3test.runtime.phase20_memory_packages import list_memory_view
from apv3test.web_chat import APV3WebChatApp


OUT = Path("reports/APV3_Phase20_4_OpenDialogueWorkbenchRepair_Showcase_20260620.html")
DB = Path("data/phase20_4_showcase/phase20_4.sqlite")
APPLE = Path("config/curriculum/assets/visual/clean_cards/noun_apple_held_out_0.png")


def main() -> int:
    DB.parent.mkdir(parents=True, exist_ok=True)
    if DB.exists():
        DB.unlink()
    app = APV3WebChatApp(state_db_path=DB)
    first = app.phase20_turn({"text": "你好", "max_ticks": 8, "idle_ticks": 2})
    teach_greet = app.phase20_teach({"teaching_reply_text": "你好。"})
    image_turn = app.phase20_turn({"text": "这是什么", "image_path": str(APPLE), "max_ticks": 8, "idle_ticks": 2})
    teach_image = app.phase20_teach({"teaching_reply_text": "像苹果。"})
    repeat_image = app.phase20_turn({"text": "这是什么", "image_path": str(APPLE), "max_ticks": 8, "idle_ticks": 2})
    unrelated = app.phase20_turn({"text": "你是谁?", "max_ticks": 8, "idle_ticks": 2})
    memory = list_memory_view(app.phase20_session.chat.state, query="像苹果", limit=8)
    html = render(first, teach_greet, image_turn, teach_image, repeat_image, unrelated, memory)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(OUT.as_posix())
    return 0


def render(first, teach_greet, image_turn, teach_image, repeat_image, unrelated, memory) -> str:
    ticks = repeat_image["turn"]["workbench_tick_trace"]
    rows = "\n".join(
        f"<tr><td>{item['tick_index']}</td><td>{esc(item['title'])}</td><td>{esc(item['summary'])}</td><td>{esc(item['detail'])}</td></tr>"
        for item in ticks
    )
    memories = "\n".join(
        f"<li><b>{esc(item.get('display_title', ''))}</b><span>{esc(item.get('display_detail', ''))}</span></li>"
        for item in memory["memories"]
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>APV3 Phase 20.4 工作台修复展示</title>
  <style>
    body {{ margin:0; font-family:"Microsoft YaHei",Arial,sans-serif; background:#f4f7f8; color:#172126; line-height:1.65; }}
    main {{ max-width:1120px; margin:0 auto; padding:28px 18px 42px; }}
    h1 {{ margin:0 0 8px; font-size:28px; }}
    h2 {{ margin:26px 0 10px; font-size:20px; }}
    .lead {{ color:#63727a; }}
    .grid {{ display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }}
    .card, table, ul {{ background:#fff; border:1px solid #d8e2e7; border-radius:8px; padding:14px; }}
    .bubble {{ max-width:78%; padding:10px 12px; border-radius:8px; margin:8px 0; white-space:pre-wrap; }}
    .user {{ margin-left:auto; background:#12343b; color:#fff; }}
    .ap {{ background:#e8f4f2; border:1px solid #cbdeda; }}
    .system {{ margin-left:auto; margin-right:auto; background:#fff7ed; border:1px solid #e8c9a1; color:#5f3a0c; }}
    table {{ border-collapse:collapse; width:100%; padding:0; overflow:hidden; }}
    td, th {{ border-bottom:1px solid #e1e8ec; padding:9px 10px; text-align:left; vertical-align:top; }}
    tr:last-child td {{ border-bottom:0; }}
    img {{ width:180px; max-height:150px; object-fit:contain; border:1px solid #d8e2e7; border-radius:8px; background:#fff; }}
    li {{ margin:8px 0; }}
    li span {{ display:block; color:#63727a; font-size:13px; }}
    .num {{ font-size:24px; color:#0f766e; font-weight:700; }}
    @media (max-width:780px) {{ .grid {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
<main>
  <h1>Phase 20.4: 本地对话工作台修复</h1>
  <p class="lead">这页给非技术读者看: 这次不是证明 AP 已经完整会聊天,而是证明工作台现在能清楚展示 AP 的输入、回复、教学、tick 回放和记忆内容,并且主聊天路径统一走 Phase20 共现学习底座。</p>

  <h2>这次修了什么</h2>
  <div class="grid">
    <div class="card"><span class="num">1</span><p>发送文字和发送图文都走同一个 Phase20 runtime,不再一半旧聊天、一半新教学。</p></div>
    <div class="card"><span class="num">2</span><p>当前会话直接显示用户原文；SQLite 仍只保存 hash/长度,不保存普通用户原文。</p></div>
    <div class="card"><span class="num">3</span><p>教学不会覆盖聊天泡泡,而是追加“纠正回答已学习”。</p></div>
    <div class="card"><span class="num">4</span><p>记忆列表显示真实短句和共现关系,支持记忆包查看/卸载。</p></div>
  </div>

  <h2>示例对话</h2>
  <div class="card">
    <div class="bubble user">你好</div>
    <div class="bubble ap">{esc(first['turn']['reply_text'])}</div>
    <div class="bubble system">{esc(teach_greet['teaching']['trace']['ui_summary'])}</div>
    <div class="bubble user">这是什么<br><img src="../config/curriculum/assets/visual/clean_cards/noun_apple_held_out_0.png" alt="apple"></div>
    <div class="bubble ap">{esc(image_turn['turn']['reply_text'])}</div>
    <div class="bubble system">{esc(teach_image['teaching']['trace']['ui_summary'])}</div>
    <div class="bubble user">这是什么</div>
    <div class="bubble ap">{esc(repeat_image['turn']['reply_text'])}</div>
    <div class="bubble user">你是谁?</div>
    <div class="bubble ap">{esc(unrelated['turn']['reply_text'])}</div>
  </div>

  <h2>AP 输出过程</h2>
  <table>
    <thead><tr><th>tick</th><th>阶段</th><th>做了什么</th><th>细节</th></tr></thead>
    <tbody>{rows}</tbody>
  </table>

  <h2>可读记忆</h2>
  <ul>{memories}</ul>

  <h2>边界</h2>
  <div class="card">
    <p>Phase 20.4 的 tick trace 是工作台从 Phase20 runtime 事件投影出来的展示序列,不是宣称已经完成更深层的开放式长程推理。音频在工作台可以上传和播放,但本阶段不宣称听觉识别完成。</p>
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
