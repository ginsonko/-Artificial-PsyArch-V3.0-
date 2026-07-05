#!/usr/bin/env python3
from __future__ import annotations

import html
import json
from collections import Counter
from pathlib import Path


REPORT = Path("reports/APV3_Phase19_8_RealTeachingLibrary_Showcase_20260619.html")
CANDIDATE_INDEX = Path("config/curriculum/assets/visual/real_teaching_candidates/index.json")
MANIFEST = Path("config/curriculum/assets/visual/real_teaching_manifest.json")
CURATION_PAGE = Path("reports/APV3_Phase19_8_RealTeachingCuration.html")


def main() -> None:
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(render(), encoding="utf-8")
    print(REPORT.as_posix())


def render() -> str:
    candidate_summary = load_candidate_summary()
    ingest_summary = load_ingest_summary()
    cards = "".join(f"<div class='metric'><b>{html.escape(str(v))}</b><span>{html.escape(k)}</span></div>" for k, v in {**candidate_summary, **ingest_summary}.items())
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>APV3 Phase 19.8a 真实教学图库数据管线</title>
  <style>
    body{{margin:0;font-family:"Microsoft YaHei","Segoe UI",Arial,sans-serif;background:#f6f7f5;color:#17211d;line-height:1.65}}
    header,main{{max-width:1120px;margin:0 auto;padding:24px}}
    h1{{font-size:30px;margin:0 0 8px}} h2{{font-size:21px;margin:0 0 8px}}
    section{{background:#fff;border:1px solid #d9e3dd;border-radius:8px;padding:18px;margin:14px 0}}
    .metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px}}
    .metric{{border:1px solid #d9e3dd;border-radius:8px;padding:12px;background:#fbfcfb}}
    .metric b{{display:block;font-size:24px;color:#1d6045}} .metric span{{font-size:13px;color:#586b62}}
    code{{background:#eef4f1;border-radius:5px;padding:1px 5px}}
    a{{color:#1e5c43}}
  </style>
</head>
<body>
<header>
  <h1>APV3 Phase 19.8a：真实教学图库数据管线</h1>
  <p>这一页证明候选下载、许可证侧车、人工筛选页和 curated 入库链条成立。它不宣称 AP 已经完成真实照片高把握识别；最终识别效果要等人工筛选后的 Phase 19.8b 再验收。</p>
</header>
<main>
  <section><h2>当前状态</h2><div class="metrics">{cards}</div></section>
  <section>
    <h2>流程</h2>
    <p><code>download_real_teaching_photos.py</code> 生成候选和 sidecar；<code>real_curation.html</code> 由人工保留/删除；<code>ingest_real_teaching_photos.py</code> 只读取已保留图片,按 sha256 deterministic 拆分 train/held_out,再写入 Layer-1/2/3。</p>
    <p>筛选页: <a href="{html.escape(CURATION_PAGE.resolve().as_uri())}">{html.escape(CURATION_PAGE.as_posix())}</a></p>
  </section>
  <section>
    <h2>边界</h2>
    <p>候选图片不是已教学材料。held-out 图片不会参与训练向量写入。Pexels/Pixabay/Unsplash 暂未进入 19.8a 白名单,避免许可证语义含混。当前只接受 CC0 / CC-BY / PDM 这类可写进 sidecar 的授权。</p>
  </section>
</main>
</body>
</html>"""


def load_candidate_summary() -> dict[str, object]:
    if not CANDIDATE_INDEX.exists():
        return {"candidate_index": "missing", "candidate_count": 0}
    payload = json.loads(CANDIDATE_INDEX.read_text(encoding="utf-8"))
    records = payload.get("records", [])
    concepts = Counter(str(item.get("concept", "")) for item in records)
    return {"candidate_count": len(records), "candidate_concepts": len(concepts)}


def load_ingest_summary() -> dict[str, object]:
    if not MANIFEST.exists():
        return {"curated_manifest": "pending", "train_count": 0, "held_out_count": 0}
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    records = payload.get("records", [])
    return {
        "curated_count": len(records),
        "train_count": sum(1 for item in records if item.get("split") == "train"),
        "held_out_count": sum(1 for item in records if item.get("split") == "held_out"),
        "layer1_count": payload.get("layer1_count", 0),
    }


if __name__ == "__main__":
    main()
