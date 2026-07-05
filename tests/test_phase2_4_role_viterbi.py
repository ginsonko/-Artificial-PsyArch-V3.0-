from __future__ import annotations

from apv3test.runtime import AnchorRelativeAligner, ParadigmDiscoveryEngine, ParadigmObservation, RoleViterbiDecoder


def test_viterbi_keeps_fixed_successor_phrase_stable() -> None:
    alignment = AnchorRelativeAligner().align([tuple("我在"), tuple("我在")])

    assert alignment.role_sequence() == ("fixed_anchor", "fixed_anchor")


def test_viterbi_prefers_shared_fragment_only_with_repeated_reconvergence_evidence() -> None:
    alignment = AnchorRelativeAligner().align(
        [
            ("ma", "lu"),
            ("chen", "yu", "cao", "lu"),
            ("jun", "dao", "cao", "lu"),
        ]
    )

    role_by_values = {column.values: column.role for column in alignment.columns}

    assert role_by_values[("lu", "lu", "lu")] == "shared_fragment"
    assert any(column.role == "slot" for column in alignment.columns[:3])


def test_viterbi_is_modality_agnostic_for_parallel_roles() -> None:
    alignment = AnchorRelativeAligner().align(
        [
            ("vision::red", "object::apple"),
            ("text::红色", "object::apple"),
            ("audio::red_word", "object::apple"),
        ]
    )

    assert alignment.role_sequence()[0] == "slot"
    assert alignment.columns[1].role in {"fixed_anchor", "shared_fragment"}
    assert alignment.columns[1].anchor_label == "object::apple"
    assert alignment.columns[0].relation_coherence == 1.0


def test_viterbi_decoder_outputs_one_role_per_column() -> None:
    alignment = AnchorRelativeAligner().align(
        [
            ("color::red", "object::apple"),
            ("color::yellow", "object::apple"),
            ("color::blue", "object::apple"),
        ]
    )
    decoded = RoleViterbiDecoder().decode(alignment.columns)

    assert len(decoded.roles) == len(alignment.columns)
    assert decoded.roles == alignment.role_sequence()
    assert decoded.score > 0


def test_discovery_uses_joint_role_sequence_for_slot_types() -> None:
    discovered = ParadigmDiscoveryEngine().discover(
        [
            ParadigmObservation("role_sequence", ("cue",), ("ma", "lu")),
            ParadigmObservation("role_sequence", ("cue",), ("chen", "yu", "cao", "lu")),
            ParadigmObservation("role_sequence", ("cue",), ("jun", "dao", "cao", "lu")),
        ]
    )[0]

    assert "slot" in {column.role for column in discovered.columns}
    assert "shared_fragment" in {column.role for column in discovered.columns}
