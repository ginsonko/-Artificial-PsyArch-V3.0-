from __future__ import annotations

import html
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from runtime.cognitive.percept_vector.phase19_runtime import (
    EXTERNAL_VISUAL,
    PERCEIVED,
    RECEPTOR_VERSION_VISUAL,
)
from runtime.cognitive.percept_vector.recall_index import Layer1RecallIndex, RecallFilter
from runtime.cognitive.percept_vector.vector_substrate import Layer1PerceptVectorStore, PerceptVector
from runtime.cognitive.state_pool.state_pool import load_constant


REPORT = Path("reports/APV3_Phase19_9_ZvecRecallIndex_Showcase_20260620.html")


def main() -> None:
    root = Path("data/phase19_9_recall_showcase")
    store = Layer1PerceptVectorStore(root / "truth" / "layer1")
    vectors = _populate(store)
    index = Layer1RecallIndex(store, index_root=root / "zvec_index", prefer_zvec=True)
    stats = index.rebuild_from_truth()
    query = vectors[2]
    recall_filter = RecallFilter(query.epistemic_source, query.substrate, query.receptor_version)
    indexed = index.c_recall(query.signature, recall_filter=recall_filter, top_k=5)
    brute = index.brute_force_recall(query.signature, recall_filter=recall_filter, top_k=5)
    REPORT.parent.mkdir(parents=True, exist_ok=True)
    REPORT.write_text(_render(stats, indexed, brute), encoding="utf-8")
    print(REPORT.as_posix())


def _populate(store: Layer1PerceptVectorStore) -> tuple[PerceptVector, ...]:
    vectors = []
    for index in range(int(load_constant("phase19_9.recall.synthetic_vector_count"))):
        source = PERCEIVED if index % 2 == 0 else "IMAGINED"
        substrate = EXTERNAL_VISUAL if index % 3 else "SELF_DRAFT_GRID"
        version = RECEPTOR_VERSION_VISUAL if index % 5 else "phase19_old"
        vector = PerceptVector(
            vector_uuid=f"pv_showcase_{index:04x}",
            signature=tuple(
                (index * 17 + dim * 13) % 256
                for dim in range(int(load_constant("phase19.vector.layer1_signature_dim")))
            ),
            full_vec_path=None,
            epistemic_source=source,
            substrate=substrate,
            receptor_version=version,
            tick_acquired=index,
            importance=1.0,
            metadata={"used_filename_label": False, "showcase_fixture": True},
        )
        store.put(vector, write_mode=str(load_constant("phase19.vector.schema_fixture_write_mode")))
        vectors.append(vector)
    return tuple(vectors)


def _render(stats, indexed, brute) -> str:
    indexed_ids = [hit.vector_uuid for hit in indexed]
    brute_ids = [hit.vector_uuid for hit in brute]
    rows = "\n".join(
        f"<tr><td>{rank}</td><td>{html.escape(hit.vector_uuid)}</td>"
        f"<td>{hit.score:.4f}</td><td>{html.escape(hit.epistemic_source)}</td>"
        f"<td>{html.escape(hit.substrate)}</td><td>{html.escape(hit.receptor_version)}</td></tr>"
        for rank, hit in enumerate(indexed, start=1)
    )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>APV3 Phase 19.9：Zvec 向量召回索引</title>
  <style>
    body{{margin:0;font-family:"Microsoft YaHei","Segoe UI",Arial,sans-serif;background:#f6f7f5;color:#17211d;line-height:1.65}}
    header,main{{max-width:1040px;margin:0 auto;padding:24px}}
    section{{background:white;border:1px solid #dce4df;border-radius:8px;padding:18px;margin:14px 0}}
    table{{width:100%;border-collapse:collapse}} th,td{{border-bottom:1px solid #dce4df;padding:8px;text-align:left}}
    code{{background:#edf4f0;border-radius:5px;padding:1px 5px}}
  </style>
</head>
<body>
<header>
  <h1>APV3 Phase 19.9：Zvec 向量召回索引</h1>
  <p>这一页展示的是召回加速底座：Zvec 或 fallback 只返回 PerceptVector UUID 候选，不返回 label，也不是 AP 的识别结论。</p>
</header>
<main>
  <section>
    <h2>索引状态</h2>
    <p>backend: <code>{html.escape(stats.backend)}</code>; indexed_count: <code>{stats.indexed_count}</code>; fallback_available: <code>{stats.fallback_available}</code>; rebuildable_from_truth: <code>{stats.rebuildable_from_truth}</code></p>
    <p>Zvec topK 与 brute-force topK 是否一致: <code>{indexed_ids == brute_ids}</code></p>
  </section>
  <section>
    <h2>召回候选</h2>
    <table><thead><tr><th>rank</th><th>vector_uuid</th><th>score</th><th>source</th><th>substrate</th><th>receptor_version</th></tr></thead><tbody>{rows}</tbody></table>
  </section>
  <section>
    <h2>边界</h2>
    <p>Phase 19.9 不证明视觉识别更聪明，不证明真实照片泛化完成，也不把 Zvec 变成分类器。它只证明 Layer-1 向量召回可以用派生索引加速，并且删除索引后能从真源重建。</p>
  </section>
</main>
</body>
</html>"""


if __name__ == "__main__":
    main()
