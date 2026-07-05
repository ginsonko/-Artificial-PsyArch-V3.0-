from __future__ import annotations

import html
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apv3test.runtime.phase20_open_dialogue import Phase20MultimodalSession


REPORT = Path("reports/APV3_Phase20_OpenDialogueFoundation_Showcase_20260620.html")
APPLE = Path("config/curriculum/assets/visual/clean_cards/noun_apple_held_out_0.png")
BANANA = Path("config/curriculum/assets/visual/clean_cards/noun_banana_held_out_0.png")


def main() -> None:
    db_path = Path("data/phase20_showcase/phase20.sqlite")
    if db_path.exists():
        db_path.unlink()
    session = Phase20MultimodalSession(state_db_path=db_path)
    turns = [
        session.turn({"text": "嗨"}),
        session.turn({"text": "这是什么", "image_path": str(APPLE)}),
        session.turn({"feedback_kind": "explicit_label", "feedback_explicit_label": "苹果"}),
        session.turn({"text": "再看看", "image_path": str(BANANA)}),
        session.turn({"feedback_kind": "positive"}),
    ]
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(_render(turns), encoding="utf-8")
    print(REPORT.as_posix())


def _render(turns) -> str:
    rows = "\n".join(_turn_card(index, turn) for index, turn in enumerate(turns, start=1))
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>APV3 Phase 20：开放中文对话底座</title>
  <style>
    body{{margin:0;font-family:"Microsoft YaHei","Segoe UI",Arial,sans-serif;background:#f5f7f6;color:#17211d;line-height:1.65}}
    header,main{{max-width:1120px;margin:0 auto;padding:24px}}
    section{{background:#fff;border:1px solid #dbe5df;border-radius:8px;padding:18px;margin:14px 0}}
    .turn{{display:grid;grid-template-columns:90px 1fr;gap:14px}}
    .badge{{font-weight:700;color:#0f4f43}}
    .chips span{{display:inline-block;border:1px solid #cddbd4;border-radius:6px;padding:2px 7px;margin:2px;background:#f8fbf9}}
    code{{background:#edf4f0;border-radius:5px;padding:1px 5px}}
  </style>
</head>
<body>
<header>
  <h1>APV3 Phase 20：开放中文对话底座</h1>
  <p>这页展示 Phase 20.0 的真实回合输出：用户中文、图片列举、styled 回应、上一轮反馈 trace、agent/web API 底座已经接通。它不宣称一次反馈后视觉识别能力已经稳定提升。</p>
</header>
<main>
  <section>
    <h2>证明了什么</h2>
    <p>Phase 20.0 证明五个既有底座可以在一个回合循环里协作：MinimalistDialogueFlowRuntime 处理用户文本，Phase 21 扫视列举图片对象，Phase 16 styled corpus 生成小默风格回应，Phase 19.5 产生反馈 credit trace，Phase 19.9 的 Zvec 继续保持“只召回 UUID、不输出 label”的边界。</p>
  </section>
  {rows}
  <section>
    <h2>边界</h2>
    <p>本阶段不证明完整中文 NLU、不证明真实照片识别鲁棒完成、不证明反馈后 raw_confidence 必然上升、不实现桌宠美术/动画、不实现具身智能。用户原文默认不持久化，用户图片只在 trace 中保留 <code>image_sha16</code>。</p>
  </section>
</main>
</body>
</html>"""


def _turn_card(index: int, turn) -> str:
    objects = "".join(
        f"<span>{html.escape(item.top_visible_label)} / {html.escape(item.decision_tier)} / {item.raw_confidence:.3f}</span>"
        for item in turn.object_files
    ) or "<span>无图片对象</span>"
    feedback = "none"
    if turn.feedback_trace is not None:
        feedback = (
            f"{turn.feedback_trace.feedback_kind}; outcome={turn.feedback_trace.correction_total_outcome:.3f}; "
            f"eligibility={turn.feedback_trace.eligibility:.3f}"
        )
    styled = turn.styled_response
    styled_text = "" if styled is None else f"{styled.paradigm_id} / {styled.entry_id}"
    return f"""<section class="turn">
  <div class="badge">Turn {index}</div>
  <div>
    <p><b>AP 输出:</b> {html.escape(turn.reply_text)}</p>
    <p><b>对象:</b> <span class="chips">{objects}</span></p>
    <p><b>反馈:</b> <code>{html.escape(feedback)}</code></p>
    <p><b>styled:</b> <code>{html.escape(styled_text)}</code>; <b>image:</b> <code>{html.escape(str(turn.image_sha16 or "none"))}</code></p>
  </div>
</section>"""


if __name__ == "__main__":
    main()
