from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from scripts.curriculum.download_real_teaching_photos import build_fixture_candidates, write_index
from scripts.curriculum.ingest_real_teaching_photos import ingest_curated_photos
from scripts.curriculum.render_real_curation_page import load_candidate_records, render_page


def _make_fixture_images(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    specs = {
        "apple": (210, 50, 45),
        "banana": (225, 190, 35),
        "orange": (235, 120, 35),
    }
    for concept, color in specs.items():
        for index in range(8):
            image = Image.new("RGB", (360, 340), "white")
            draw = ImageDraw.Draw(image)
            if concept == "banana":
                draw.ellipse((60, 120 + index * 3, 300, 210 + index * 3), fill=color)
                draw.rectangle((60, 120 + index * 3, 300, 165 + index * 3), fill="white")
            else:
                draw.ellipse((90 + index * 3, 70, 270 + index * 3, 250), fill=color)
            image.save(root / f"{concept}_{index}.png")


def test_phase19_8_fixture_download_sidecars_and_curation_page(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture"
    candidates = tmp_path / "candidates"
    _make_fixture_images(fixture)

    records = build_fixture_candidates(fixture, candidates, ("apple", "banana", "orange"), 8)
    write_index(candidates, records)
    loaded = load_candidate_records(candidates)
    html = render_page(candidates, loaded, tmp_path / "curation.html")

    assert len(records) == 24
    assert all(record["license_id"] == "CC0-1.0" for record in records)
    assert "apv3_real_teaching_curation/v1" in html
    assert "默认全部保留" in html


def test_phase19_8_ingest_keeps_held_out_out_of_training_vectors(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture"
    candidates = tmp_path / "candidates"
    curated = tmp_path / "curated"
    vectors = tmp_path / "vectors"
    manifest = tmp_path / "manifest.json"
    _make_fixture_images(fixture)
    records = build_fixture_candidates(fixture, candidates, ("apple", "banana", "orange"), 8)
    curation = {
        "schema_id": "apv3_real_teaching_curation/v1",
        "records": [
            {"candidate_id": record["candidate_id"], "concept": record["concept"], "status": "keep"}
            for record in records
        ],
    }
    curation_path = candidates / "curation.json"
    curation_path.write_text(json.dumps(curation, ensure_ascii=False), encoding="utf-8")

    result = ingest_curated_photos(
        candidate_root=candidates,
        curation_json=curation_path,
        curated_dir=curated,
        vector_root=vectors,
        manifest_path=manifest,
    )
    payload = json.loads(manifest.read_text(encoding="utf-8"))

    assert result["curated_count"] == 24
    assert result["held_out_count"] > 0
    assert result["layer1_count"] == result["train_count"]
    assert all(item["split"] in {"train", "held_out"} for item in payload["records"])
    assert "Held-out files" in payload["boundary"]


def test_phase19_8_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "19.8a"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
