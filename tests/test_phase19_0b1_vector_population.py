from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from runtime.cognitive.percept_vector.phase19_runtime import (
    EXTERNAL_VISUAL,
    SELF_DRAFT_GRID,
    VisualTeachingExample,
    populate_visual_vectors,
)
from runtime.cognitive.state_pool.state_pool import load_constant


def _fruit_examples() -> tuple[VisualTeachingExample, ...]:
    root = Path("config/curriculum/assets/visual/clean_cards")
    return (
        VisualTeachingExample(root / "noun_apple_train_0.png", "apple_visible_teacher", "train", 191),
        VisualTeachingExample(root / "noun_banana_train_0.png", "banana_visible_teacher", "train", 192),
        VisualTeachingExample(root / "noun_orange_train_0.png", "orange_visible_teacher", "train", 193),
    )


def test_phase19_0b1_writes_real_foveated_vectors_and_full_vec_files(tmp_path: Path) -> None:
    result = populate_visual_vectors(_fruit_examples(), root=tmp_path / "vectors")

    assert result.metadata["layer1_count"] == 3
    assert result.metadata["layer2_count"] == len(_fruit_examples()) * len(
        load_constant("phase19.vector.layer2_part_channels")
    )
    assert result.metadata["layer3_count"] == 3
    assert result.metadata["receptor_version"] == "phase19_0a_foveated"
    assert all(path.exists() and path.suffix == ".npy" for path in result.stored_full_vectors)
    assert all(vector.receptor_version == "phase19_0a_foveated" for vector in result.percept_vectors)
    assert all(vector.metadata["used_filename_label"] is False for vector in result.percept_vectors)


def test_phase19_0b1_concept_ids_are_opaque_and_labels_are_visible_teacher_source(tmp_path: Path) -> None:
    result = populate_visual_vectors(_fruit_examples(), root=tmp_path / "vectors")
    concept_ids = [concept.concept_uuid for concept in result.concepts]
    joined_ids = " ".join(concept_ids).lower()

    assert "apple" not in joined_ids
    assert "banana" not in joined_ids
    assert "orange" not in joined_ids
    assert all(concept.metadata["teacher_label_source"] == "visible_curriculum_signal" for concept in result.concepts)


def test_phase19_0b1_packet_key_still_separates_self_draft_from_external_visual(tmp_path: Path) -> None:
    examples = (
        VisualTeachingExample(
            Path("config/curriculum/assets/visual/clean_cards/noun_apple_train_0.png"),
            "apple_visible_teacher",
            "train",
            194,
            EXTERNAL_VISUAL,
        ),
        VisualTeachingExample(
            Path("config/curriculum/assets/visual/clean_cards/noun_apple_train_0.png"),
            "apple_visible_teacher",
            "train",
            195,
            SELF_DRAFT_GRID,
        ),
    )
    result = populate_visual_vectors(examples, root=tmp_path / "vectors")

    assert result.percept_vectors[0].signature == result.percept_vectors[1].signature
    assert result.percept_vectors[0].packet_key() != result.percept_vectors[1].packet_key()


def test_phase19_0b1_redline_deliverables_pass() -> None:
    completed = subprocess.run(
        [sys.executable, "scripts/red_line_check_v14.py", "--phase", "19.0b1"],
        cwd=".",
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stdout + completed.stderr
