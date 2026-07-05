#!/usr/bin/env python3
from __future__ import annotations

import argparse
import html
import json
from collections import defaultdict
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from runtime.cognitive.state_pool.state_pool import load_constant


DEFAULT_CANDIDATE_ROOT = Path("config/curriculum/assets/visual/real_teaching_candidates")
DEFAULT_REPORT = Path("reports/APV3_Phase19_8_RealTeachingCuration.html")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--candidate-root", default=str(DEFAULT_CANDIDATE_ROOT))
    parser.add_argument("--out", default=str(DEFAULT_REPORT))
    args = parser.parse_args()

    root = Path(args.candidate_root)
    records = load_candidate_records(root)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_page(root, records, out), encoding="utf-8")
    print(out.as_posix())


def load_candidate_records(root: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for sidecar in sorted(root.glob("*/*.json")):
        if sidecar.name == "curation.json":
            continue
        record = json.loads(sidecar.read_text(encoding="utf-8"))
        if record.get("schema_id") == "apv3_real_teaching_candidate/v1":
            record["sidecar_path"] = sidecar.as_posix()
            records.append(record)
    return records


def render_page(root: Path, records: list[dict[str, object]], report_path: Path) -> str:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for record in records:
        grouped[str(record["concept"])].append(record)
    sections = "\n".join(render_concept(root, concept, grouped[concept], report_path) for concept in sorted(grouped))
    min_keep = int(load_constant("curriculum.real_assets.teaching_curated_min_per_concept"))
    max_keep = int(load_constant("curriculum.real_assets.teaching_curated_max_per_concept"))
    thumb = int(load_constant("curriculum.real_assets.teaching_curation_thumb_px"))
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>APV3 Phase 19.8 真实教学图筛选</title>
  <style>
    body{{margin:0;font-family:"Microsoft YaHei","Segoe UI",Arial,sans-serif;background:#f5f7f4;color:#17221d}}
    header,main{{max-width:1280px;margin:0 auto;padding:20px}}
    h1{{font-size:28px;margin:0 0 8px}} h2{{font-size:20px;margin:18px 0 8px}}
    .bar{{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin:10px 0}}
    button{{border:1px solid #9eb2a8;background:#fff;border-radius:6px;padding:8px 12px;cursor:pointer}}
    button.primary{{background:#1e5c43;color:#fff;border-color:#1e5c43}}
    .grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax({thumb}px,1fr));gap:10px}}
    .card{{background:#fff;border:2px solid #bfd1c8;border-radius:8px;padding:8px}}
    .card.drop{{opacity:.45;border-color:#b35b51}}
    .card img{{width:100%;height:{thumb}px;object-fit:contain;background:#fff;border-radius:5px}}
    .meta{{font-size:12px;color:#4d6258;word-break:break-all}}
    .status{{font-weight:700;margin:4px 0}}
    .keep .status{{color:#247241}} .drop .status{{color:#a64135}}
    code{{background:#edf3ef;border-radius:4px;padding:1px 4px}}
    textarea{{width:100%;min-height:180px}}
  </style>
</head>
<body>
<header>
  <h1>APV3 Phase 19.8：真实教学图人工筛选</h1>
  <p>默认全部保留。只点击明显不适合教学的图，把它改成删除。目标每个概念保留 <b>{min_keep}-{max_keep}</b> 张。</p>
  <div class="bar"><button class="primary" onclick="saveAll()">保存筛选 JSON</button><button onclick="showExport()">显示导出内容</button><span id="summary"></span></div>
  <p><code>D</code> 删除当前图，<code>S</code> 保留当前图，<code>空格</code> 下一张。双击图片可新窗口看大图。</p>
</header>
<main>{sections}<section><h2>导出内容</h2><textarea id="exportBox" readonly></textarea></section></main>
<script>
let cards=[...document.querySelectorAll('.card')]; let current=0;
function updateSummary(){{
  let counts={{}};
  for (const card of cards) {{
    let concept=card.dataset.concept;
    counts[concept]=counts[concept]||{{keep:0,total:0}};
    counts[concept].total++;
    if(card.dataset.status==='keep') counts[concept].keep++;
  }}
  document.getElementById('summary').textContent=Object.entries(counts).map(([k,v])=>`${{k}} ${{v.keep}}/${{v.total}}`).join('  |  ');
}}
function toggle(card){{ card.dataset.status=card.dataset.status==='keep'?'drop':'keep'; card.classList.toggle('drop',card.dataset.status==='drop'); card.classList.toggle('keep',card.dataset.status==='keep'); card.querySelector('.status').textContent=card.dataset.status==='keep'?'保留':'删除'; updateSummary(); }}
function payload(){{ return {{schema_id:'apv3_real_teaching_curation/v1', records: cards.map(c=>({{candidate_id:c.dataset.candidateId, concept:c.dataset.concept, status:c.dataset.status, sidecar_path:c.dataset.sidecarPath}}))}}; }}
function showExport(){{ document.getElementById('exportBox').value=JSON.stringify(payload(),null,2); }}
function saveAll(){{ showExport(); const blob=new Blob([document.getElementById('exportBox').value],{{type:'application/json'}}); const a=document.createElement('a'); a.href=URL.createObjectURL(blob); a.download='curation.json'; a.click(); }}
document.addEventListener('keydown',e=>{{ if(!cards.length)return; if(e.key===' '){{current=Math.min(cards.length-1,current+1);cards[current].scrollIntoView({{block:'center'}});e.preventDefault();}} if(e.key==='d'||e.key==='D') toggle(cards[current]); if(e.key==='s'||e.key==='S'){{ if(cards[current].dataset.status==='drop') toggle(cards[current]); }} }});
for (const [i,card] of cards.entries()) {{ card.addEventListener('click',()=>{{current=i; toggle(card);}}); card.querySelector('img').addEventListener('dblclick',e=>{{e.stopPropagation(); window.open(card.querySelector('img').src,'_blank');}}); }}
updateSummary(); showExport();
</script>
</body>
</html>"""


def render_concept(root: Path, concept: str, records: list[dict[str, object]], report_path: Path) -> str:
    cards = "\n".join(render_card(root, record, report_path) for record in records)
    return f"<section><h2>{html.escape(concept)}</h2><div class='grid'>{cards}</div></section>"


def render_card(root: Path, record: dict[str, object], report_path: Path) -> str:
    path = Path(str(record["path"]))
    try:
        rel = path.resolve().relative_to(report_path.parent.resolve()).as_posix()
    except ValueError:
        rel = path.resolve().as_uri()
    return f"""<div class="card keep" data-status="keep" data-concept="{html.escape(str(record['concept']))}" data-candidate-id="{html.escape(str(record['candidate_id']))}" data-sidecar-path="{html.escape(str(record['sidecar_path']))}">
      <img src="{html.escape(rel)}" alt="{html.escape(str(record['candidate_id']))}">
      <div class="status">保留</div>
      <div class="meta">{html.escape(str(record.get('license_id','')))} · {html.escape(str(record.get('source','')))}</div>
      <div class="meta">{html.escape(str(record.get('title',''))[:80])}</div>
    </div>"""


if __name__ == "__main__":
    main()
