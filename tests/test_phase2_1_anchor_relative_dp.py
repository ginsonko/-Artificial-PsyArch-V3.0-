from __future__ import annotations

from apv3test.runtime import AnchorRelativeAligner, ParadigmDiscoveryEngine, ParadigmObservation


def test_anchor_relative_dp_aligns_reconvergent_tail_across_gap_without_forcing_role() -> None:
    aligner = AnchorRelativeAligner()

    alignment = aligner.align([tuple("茅庐"), tuple("臣于草庐之中")])
    matched_columns = [column for column in alignment.columns if column.values == ("庐", "庐")]

    assert matched_columns
    assert matched_columns[0].role in {"fixed_anchor", "shared_fragment"}
    assert any(column.role == "slot" for column in alignment.columns[: matched_columns[0].col_index])


def test_anchor_relative_dp_keeps_repeated_character_interference_bounded() -> None:
    aligner = AnchorRelativeAligner()

    alignment = aligner.align([tuple("人人都说人"), tuple("人们都说人")])
    exact_columns = [column for column in alignment.columns if len(set(column.values)) == 1 and None not in column.values]

    assert len(alignment.columns) <= 6
    assert len(exact_columns) >= 4
    assert alignment.columns[-1].values == ("人", "人")


def test_discovery_uses_dp_columns_instead_of_plain_suffix_greedy() -> None:
    engine = ParadigmDiscoveryEngine()

    discovered = engine.discover(
        [
            ParadigmObservation("idiom_gap_reply", tuple("三顾"), tuple("茅庐")),
            ParadigmObservation("idiom_gap_reply", tuple("三顾"), tuple("臣于草庐")),
            ParadigmObservation("idiom_gap_reply", tuple("三顾"), tuple("君到草庐")),
        ]
    )
    item = discovered[0]
    reconvergent_columns = [column for column in item.columns if column.values == ("庐", "庐")]

    assert reconvergent_columns or any(column.anchor_label == "庐" for column in item.columns)
    assert "shared_fragment" in {column.role for column in item.columns}
    assert item.slot_spans[0][0] == "茅"
