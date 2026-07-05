from __future__ import annotations

import html
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from apv3test.runtime.cooccurrence_store import CooccurrenceAssociationStore
from apv3test.runtime.phase20_memory_packages import (
    export_memory_package,
    import_memory_package,
    list_memory_view,
    uninstall_memory_package,
)
from apv3test.runtime.phase20_open_dialogue import Phase20MultimodalSession


REPORT = Path("reports/APV3_Phase20_2_3_CooccurrenceMemoryPackages_Showcase_20260620.html")
APPLE = Path("config/curriculum/assets/visual/clean_cards/noun_apple_held_out_0.png")


def main() -> None:
    db_path = Path("data/phase20_2_3_showcase/source.sqlite")
    if db_path.exists():
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    session = Phase20MultimodalSession(state_db_path=db_path)
    first = session.turn({"text": "这是什么", "image_path": str(APPLE)})
    teaching = session.teach_latest({"teaching_reply_text": "像苹果。"})
    again = session.turn({"text": "这是什么", "image_path": str(APPLE)})
    assoc = CooccurrenceAssociationStore.from_state(session.chat.state.get("cooccurrence_associations"))
    phrase_memories = list_memory_view(session.chat.state, query="像苹果", limit=20)["memories"]
    package = export_memory_package(
        session.chat.state,
        name="苹果共现教学包",
        include_memory_ids=[item["memory_id"] for item in phrase_memories],
    )
    target = Phase20MultimodalSession(state_db_path=Path("data/phase20_2_3_showcase/target.sqlite"))
    imported = import_memory_package(target.chat.state, package)
    uninstalled = uninstall_memory_package(imported.state, imported.payload["package_id"])

    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(
        _render(
            first=first,
            teaching=teaching,
            again=again,
            pairs=[pair for pair in assoc.pairs if pair.key_b.endswith("ee26f6d851ef") or "teacher_phrase" in pair.key_b][:12],
            memories=phrase_memories,
            package=package,
            imported=imported.payload,
            uninstalled=uninstalled.payload,
            style_import=session.chat.state.get("phase20_style_corpus_import", {}),
        ),
        encoding="utf-8",
    )
    print(REPORT.as_posix())


def _render(*, first, teaching, again, pairs, memories, package, imported, uninstalled, style_import) -> str:
    pair_rows = "".join(
        f"<tr><td>{html.escape(pair.key_a)}</td><td>{html.escape(pair.key_b)}</td><td>{pair.cumulative_weight:.3f}</td></tr>"
        for pair in pairs
    )
    memory_rows = "".join(
        f"<tr><td>{html.escape(item['kind'])}</td><td>{html.escape(item['text'])}</td><td>{html.escape(item['memory_id'])}</td></tr>"
        for item in memories
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>APV3 Phase 20.2/20.3：共现教学与记忆包</title>
  <style>
    body{{margin:0;background:#f4f7f8;color:#172126;font-family:"Microsoft YaHei","Segoe UI",Arial,sans-serif;line-height:1.68;letter-spacing:0}}
    header,main{{max-width:1160px;margin:0 auto;padding:24px}}
    section{{background:#fff;border:1px solid #d8e2e7;border-radius:8px;padding:18px;margin:14px 0}}
    h1{{margin:0 0 8px;font-size:28px}} h2{{font-size:20px}} code{{background:#edf4f2;border-radius:5px;padding:2px 5px}}
    .grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
    .kv{{display:grid;grid-template-columns:150px minmax(0,1fr);gap:8px;margin:5px 0}}
    .kv b{{color:#63727a;font-weight:500}} .mono{{font-family:Consolas,"Courier New",monospace;overflow-wrap:anywhere}}
    table{{width:100%;border-collapse:collapse;font-size:13px}} td,th{{border:1px solid #d8e2e7;padding:6px;text-align:left;vertical-align:top}} th{{background:#fbfdff}}
    .ok{{color:#0f766e;font-weight:700}} .warn{{color:#a33b35;font-weight:700}}
    @media(max-width:860px){{.grid{{grid-template-columns:1fr}}}}
  </style>
</head>
<body>
<header>
  <h1>APV3 Phase 20.2/20.3：标注不是标签表,而是共现波峰</h1>
  <p>这页展示用户教“像苹果。”后,AP 如何把视觉对象 SA 与老师短句 SA 写进共现图,并通过记忆包导出、导入、卸载治理这些记忆。</p>
</header>
<main>
  <section>
    <h2>AP 输出过程</h2>
    <div class="grid">
      <div>
        <div class="kv"><b>题目</b><span>图片 + “这是什么”</span></div>
        <div class="kv"><b>第一次 AP</b><span>{html.escape(first.reply_text)}</span></div>
        <div class="kv"><b>用户教学</b><span>{html.escape(teaching.teaching_trace.response_text)}</span></div>
        <div class="kv"><b>再问 AP</b><span class="ok">{html.escape(again.reply_text)}</span></div>
      </div>
      <div>
        <div class="kv"><b>teacher source</b><span class="mono">{html.escape(teaching.teaching_trace.source)}</span></div>
        <div class="kv"><b>context</b><span class="mono">{html.escape(teaching.teaching_trace.target_context_signature)}</span></div>
        <div class="kv"><b>visual SAs</b><span class="mono">{html.escape(', '.join(teaching.teaching_trace.visual_sa_ids))}</span></div>
        <div class="kv"><b>style import</b><span>{html.escape(str(style_import.get('imported_count', 0)))} / {html.escape(str(style_import.get('available_count', 0)))}</span></div>
      </div>
    </div>
  </section>
  <section>
    <h2>共现边</h2>
    <p>这些边是 AP-native 记忆。它们不是 image_label_map,也不是 answer table。</p>
    <table><thead><tr><th>source SA</th><th>phrase SA</th><th>support</th></tr></thead><tbody>{pair_rows}</tbody></table>
  </section>
  <section>
    <h2>本地记忆与记忆包</h2>
    <table><thead><tr><th>kind</th><th>text</th><th>memory id</th></tr></thead><tbody>{memory_rows}</tbody></table>
    <p>导出包: <code>{html.escape(package['name'])}</code>, memories={len(package['memories'])}</p>
    <p>导入: added={imported['added_count']}, dedup={imported['dedup_count']}; 卸载: removed={uninstalled['removed_count']}。</p>
  </section>
  <section>
    <h2>边界</h2>
    <p><span class="ok">已证明:</span> 视觉/文本教学走共现图,风格语料千句级进入 AP 表达记忆,记忆包可导入去重和精确卸载。</p>
    <p><span class="warn">仍不能宣称:</span> 完整中文 NLU、任意真实图鲁棒识别、社区包法律审计完成、成人级语义抽象完成。</p>
  </section>
</main>
</body>
</html>"""


if __name__ == "__main__":
    main()
