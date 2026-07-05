from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from runtime.cognitive.curriculum.asset_governance import (
    CurriculumAssetManifest,
    CurriculumAssetRecord,
    load_asset_manifest_file,
    load_neutral_curriculum_pack_file,
)
from runtime.cognitive.marker.events import MarkerEvent
from runtime.cognitive.sdpl.packet import FeelingValue, LearningPacket, make_packet
from runtime.cognitive.sdpl.q_table_backoff import QTableWithBackoff
from runtime.cognitive.state_pool.state_pool import StateItem, load_constant


DEFAULT_MANIFEST_PATH = Path("config/curriculum/assets/manifest.yaml")
DEFAULT_CLEAN_CARD_MANIFEST_PATH = Path("config/curriculum/assets/clean_card_manifest.yaml")
DEFAULT_REAL_MANIFEST_PATH = Path("config/curriculum/assets/real_manifest.yaml")
DEFAULT_ASSET_ROOT = Path("config/curriculum/assets")
DEFAULT_PACKAGE_ROOT = Path("config/curriculum/packages/neutral")
DEFAULT_CLEAN_PACKAGE_ROOT = Path("config/curriculum/packages/clean")
DEFAULT_REAL_PACKAGE_ROOT = Path("config/curriculum/packages/real")
DEFAULT_ADDITIONAL_MANIFEST_PATHS = (DEFAULT_CLEAN_CARD_MANIFEST_PATH, DEFAULT_REAL_MANIFEST_PATH)
DEFAULT_ADDITIONAL_PACKAGE_ROOTS = (DEFAULT_CLEAN_PACKAGE_ROOT, DEFAULT_REAL_PACKAGE_ROOT)


@dataclass(frozen=True)
class CourseReplayDemoSpec:
    demo_id: str
    package_id: str
    entry_id: str
    title: str
    question: str
    demo_group: str = "synthetic"
    probe_package_id: str | None = None
    probe_entry_id: str | None = None


DEFAULT_DEMOS = (
    CourseReplayDemoSpec("demo_color_yellow", "neutral_colors_v1", "color_yellow", "颜色：黄", "这组材料在教什么颜色？"),
    CourseReplayDemoSpec("demo_shape_triangle", "neutral_shapes_v1", "shape_triangle", "形状：三角", "这组材料在教什么形状？"),
    CourseReplayDemoSpec("demo_noun_apple", "neutral_daily_nouns_v1", "noun_apple", "物体：苹果", "这组材料在教什么日常物体？"),
    CourseReplayDemoSpec("demo_audio_soft_call", "neutral_audio_patterns_v1", "audio_soft_call", "声音：轻声呼唤", "这组声音材料在教什么模式？"),
    CourseReplayDemoSpec("demo_feedback_correct", "neutral_feedback_symbols_v1", "feedback_correct", "反馈：对", "这组材料在教什么反馈信号？"),
)
CLEAN_CARD_DEMOS = (
    CourseReplayDemoSpec("demo_clean_card_apple", "clean_fruit_cards_v1", "noun_apple", "干净卡片：苹果", "这组无文字卡片在教什么水果？", "clean_card"),
    CourseReplayDemoSpec("demo_clean_card_banana", "clean_fruit_cards_v1", "noun_banana", "干净卡片：香蕉", "这组无文字卡片在教什么水果？", "clean_card"),
    CourseReplayDemoSpec("demo_clean_card_orange", "clean_fruit_cards_v1", "noun_orange", "干净卡片：橙子", "这组无文字卡片在教什么水果？", "clean_card"),
)
GENERALIZATION_DEMOS = (
    CourseReplayDemoSpec(
        "demo_generalize_clean_to_real_apple",
        "clean_fruit_cards_v1",
        "noun_apple",
        "泛化探测：卡片到真实苹果",
        "先看无文字苹果卡片，再看真实苹果照片，倾向是否仍然指向苹果？",
        "real_photo_generalization",
        "real_fruit_photos_v1",
        "noun_apple",
    ),
    CourseReplayDemoSpec(
        "demo_generalize_clean_to_real_banana",
        "clean_fruit_cards_v1",
        "noun_banana",
        "泛化探测：卡片到真实香蕉",
        "先看无文字香蕉卡片，再看真实香蕉照片，倾向是否仍然指向香蕉？",
        "real_photo_generalization",
        "real_fruit_photos_v1",
        "noun_banana",
    ),
    CourseReplayDemoSpec(
        "demo_generalize_clean_to_real_orange",
        "clean_fruit_cards_v1",
        "noun_orange",
        "泛化探测：卡片到真实橙子",
        "先看无文字橙子卡片，再看真实橙子照片，倾向是否仍然指向橙子？",
        "real_photo_generalization",
        "real_fruit_photos_v1",
        "noun_orange",
    ),
)
ALL_DEMOS = DEFAULT_DEMOS + CLEAN_CARD_DEMOS + GENERALIZATION_DEMOS


class CourseReplayRuntime:
    def __init__(
        self,
        *,
        manifest_path: str | Path = DEFAULT_MANIFEST_PATH,
        additional_manifest_paths: Sequence[str | Path] = DEFAULT_ADDITIONAL_MANIFEST_PATHS,
        asset_root: str | Path = DEFAULT_ASSET_ROOT,
        package_root: str | Path = DEFAULT_PACKAGE_ROOT,
        additional_package_roots: Sequence[str | Path] = DEFAULT_ADDITIONAL_PACKAGE_ROOTS,
        state_db_path: str | Path | None = None,
    ) -> None:
        self.manifest_path = Path(manifest_path)
        self.additional_manifest_paths = tuple(Path(path) for path in additional_manifest_paths)
        self.asset_root = Path(asset_root)
        self.package_root = Path(package_root)
        self.additional_package_roots = tuple(Path(path) for path in additional_package_roots)
        self.state_db_path = Path(state_db_path) if state_db_path is not None else None
        self.manifests = self._load_manifests()
        self.assets_by_id: dict[str, CurriculumAssetRecord] = {}
        self.asset_manifest_by_id: dict[str, str] = {}
        for manifest in self.manifests:
            for asset in manifest.assets:
                if asset.asset_id in self.assets_by_id:
                    raise ValueError(f"duplicate asset id across manifests: {asset.asset_id}")
                self.assets_by_id[asset.asset_id] = asset
                self.asset_manifest_by_id[asset.asset_id] = manifest.manifest_id
        self.packages = {
            str(package["package_id"]): package
            for package in (
                load_neutral_curriculum_pack_file(path) for path in self._package_paths()
            )
        }

    def list_demos(self) -> dict[str, object]:
        """@op_count: O(demos)."""
        return {
            "schema_id": "apv3_course_replay_demo_list/v1",
            "demos": [
                {
                    "demo_id": demo.demo_id,
                    "package_id": demo.package_id,
                    "entry_id": demo.entry_id,
                    "title": demo.title,
                    "question": demo.question,
                    "demo_group": demo.demo_group,
                    "probe_package_id": demo.probe_package_id,
                    "probe_entry_id": demo.probe_entry_id,
                }
                for demo in ALL_DEMOS
            ],
        }

    def run_demo(self, demo_id: str) -> dict[str, object]:
        """@op_count: O(demos + ticks + assets)."""
        demo = self._demo(demo_id)
        package = self.packages[demo.package_id]
        entry = self._entry(package, demo.entry_id)
        trace = self._run_generalization_trace(demo, entry) if demo.probe_package_id else self._run_entry_trace(demo, package, entry)
        summary = self._summary(trace)
        if demo.demo_group == "real_photo_generalization":
            summary.update(
                {
                    "visual_generalization_valid": False,
                    "audit_status": "plumbing_only_label_mediated_probe",
                    "rejection_reason": "probe_packet_contains_curriculum_label_and_energy_bucket_confound",
                }
            )
        payload = {
            "schema_id": "apv3_course_replay_trace/v1",
            "demo": {
                "demo_id": demo.demo_id,
                "package_id": demo.package_id,
                "entry_id": demo.entry_id,
                "title": demo.title,
                "question": demo.question,
                "demo_group": demo.demo_group,
                "probe_package_id": demo.probe_package_id,
                "probe_entry_id": demo.probe_entry_id,
            },
            "asset_root": self.asset_root.as_posix(),
            "ticks": trace,
            "summary": summary,
        }
        self._persist(payload)
        return payload

    def asset_path_for_id(self, asset_id: str) -> Path:
        """@op_count: O(1)."""
        record = self.assets_by_id[asset_id]
        rel = Path(record.path)
        if rel.is_absolute() or ".." in rel.parts:
            raise ValueError("unsafe asset path")
        path = self.asset_root / rel
        path.resolve().relative_to(self.asset_root.resolve())
        return path

    def _run_entry_trace(
        self,
        demo: CourseReplayDemoSpec,
        package: Mapping[str, object],
        entry: Mapping[str, object],
    ) -> list[dict[str, object]]:
        q_table = QTableWithBackoff()
        train_refs = tuple(str(item) for item in entry.get("train_asset_refs", ()))
        held_out_refs = tuple(str(item) for item in entry.get("held_out_asset_refs", ()))
        contrast_refs = tuple(str(item) for item in entry.get("contrast_asset_refs", ()))
        selected_train = train_refs[: int(load_constant("curriculum.replay.trace_top_asset_count"))]
        ticks: list[dict[str, object]] = []

        intro_packet = self._packet(entry, self.assets_by_id[selected_train[0]], tick=1, phase="course_material_ingress")
        q_table.update(
            intro_packet,
            self._action_id(entry),
            outcome=float(load_constant("curriculum.replay.q_positive_outcome")),
        )
        ticks.append(self._tick_row(1, "课程材料进入", demo, entry, selected_train, intro_packet, q_table, "看到训练材料"))

        packet = self._packet(entry, self.assets_by_id[selected_train[1]], tick=2, phase="sdpl_packet_build")
        q_table.update(
            packet,
            self._action_id(entry),
            outcome=float(load_constant("curriculum.replay.q_positive_outcome")),
        )
        ticks.append(self._tick_row(2, "形成 SDPL 学习包", demo, entry, selected_train, packet, q_table, "把材料和中性标签联结"))

        held_record = self.assets_by_id[held_out_refs[0]]
        held_packet = self._packet(entry, held_record, tick=3, phase="held_out_probe")
        held_score = q_table.query(held_packet, self._action_id(entry))
        ticks.append(
            self._tick_row(
                3,
                "held-out 探测",
                demo,
                entry,
                held_out_refs,
                held_packet,
                q_table,
                "未见材料仍能得到同类倾向",
                q_score=held_score,
            )
        )

        contrast_record = self.assets_by_id[contrast_refs[0]]
        contrast_packet = self._packet(entry, contrast_record, tick=4, phase="contrast_probe")
        q_table.update(
            contrast_packet,
            f"reject::{self._action_id(entry)}",
            outcome=float(load_constant("curriculum.replay.q_contrast_outcome")),
        )
        ticks.append(
            self._tick_row(
                4,
                "干扰项对照",
                demo,
                entry,
                contrast_refs,
                contrast_packet,
                q_table,
                "干扰项被单独标记为对照",
            )
        )

        combined_packet = self._packet(entry, held_record, tick=5, phase="action_competition")
        q_score = q_table.query(combined_packet, self._action_id(entry))
        ticks.append(
            self._tick_row(
                5,
                "行动竞争",
                demo,
                entry,
                held_out_refs,
                combined_packet,
                q_table,
                "课程倾向进入可解释输出候选",
                q_score=q_score,
            )
        )

        final_packet = self._packet(entry, held_record, tick=6, phase="commit_trace")
        ticks.append(
            self._tick_row(
                6,
                "提交可审计回应",
                demo,
                entry,
                held_out_refs,
                final_packet,
                q_table,
                self._response_text(entry),
                q_score=q_table.query(final_packet, self._action_id(entry)),
            )
        )
        return ticks[: int(load_constant("curriculum.replay.demo_tick_count"))]

    def _run_generalization_trace(
        self,
        demo: CourseReplayDemoSpec,
        train_entry: Mapping[str, object],
    ) -> list[dict[str, object]]:
        """@op_count: O(ticks + assets)."""
        if demo.probe_package_id is None or demo.probe_entry_id is None:
            raise ValueError("generalization demo requires a probe package and entry")
        probe_entry = self._entry(self.packages[demo.probe_package_id], demo.probe_entry_id)
        q_table = QTableWithBackoff()
        train_refs = tuple(str(item) for item in train_entry.get("train_asset_refs", ()))
        selected_train = train_refs[: int(load_constant("curriculum.replay.trace_top_asset_count"))]
        real_held_refs = tuple(str(item) for item in probe_entry.get("held_out_asset_refs", ()))
        real_contrast_refs = tuple(str(item) for item in probe_entry.get("contrast_asset_refs", ()))
        ticks: list[dict[str, object]] = []

        intro_packet = self._packet(train_entry, self.assets_by_id[selected_train[0]], tick=1, phase="clean_card_ingress")
        q_table.update(
            intro_packet,
            self._action_id(train_entry),
            outcome=float(load_constant("curriculum.replay.q_positive_outcome")),
        )
        ticks.append(
            self._tick_row(
                1,
                "干净卡片教学进入",
                demo,
                train_entry,
                selected_train,
                intro_packet,
                q_table,
                "先用低噪声卡片稳定概念",
            )
        )

        packet = self._packet(train_entry, self.assets_by_id[selected_train[1]], tick=2, phase="clean_card_packet_build")
        q_table.update(
            packet,
            self._action_id(train_entry),
            outcome=float(load_constant("curriculum.replay.q_positive_outcome")),
        )
        ticks.append(
            self._tick_row(
                2,
                "概念 LearningPacket 稳定",
                demo,
                train_entry,
                selected_train,
                packet,
                q_table,
                "概念倾向写入 SDPL Q 表",
            )
        )

        held_record = self.assets_by_id[real_held_refs[0]]
        held_packet = self._packet(probe_entry, held_record, tick=3, phase="real_photo_held_out_probe")
        held_score = q_table.query(held_packet, self._action_id(probe_entry))
        ticks.append(
            self._tick_row(
                3,
                "真实照片 held-out 泛化探测",
                demo,
                probe_entry,
                real_held_refs,
                held_packet,
                q_table,
                "未见真实照片触发同类倾向",
                q_score=held_score,
            )
        )

        contrast_record = self.assets_by_id[real_contrast_refs[0]]
        contrast_packet = self._packet(probe_entry, contrast_record, tick=4, phase="real_photo_contrast_probe")
        ticks.append(
            self._tick_row(
                4,
                "真实照片 contrast 对照",
                demo,
                probe_entry,
                real_contrast_refs,
                contrast_packet,
                q_table,
                "其它水果照片不获得同等倾向",
                q_score=q_table.query(contrast_packet, self._action_id(probe_entry)),
            )
        )

        competition_packet = self._packet(probe_entry, held_record, tick=5, phase="real_photo_action_competition")
        q_score = q_table.query(competition_packet, self._action_id(probe_entry))
        ticks.append(
            self._tick_row(
                5,
                "真实照片行动竞争",
                demo,
                probe_entry,
                real_held_refs,
                competition_packet,
                q_table,
                "真实照片倾向进入输出候选",
                q_score=q_score,
            )
        )

        final_packet = self._packet(probe_entry, held_record, tick=6, phase="real_photo_commit_trace")
        ticks.append(
            self._tick_row(
                6,
                "提交可审计回应",
                demo,
                probe_entry,
                real_held_refs,
                final_packet,
                q_table,
                "还不能确认",
                q_score=q_table.query(final_packet, self._action_id(probe_entry)),
            )
        )
        return ticks[: int(load_constant("curriculum.replay.demo_tick_count"))]

    def _packet(
        self,
        entry: Mapping[str, object],
        asset: CurriculumAssetRecord,
        *,
        tick: int,
        phase: str,
    ) -> LearningPacket:
        media = "audio" if asset.media_type == "audio/wav" else "vision"
        energy = self._energy_for_asset(asset)
        content = self._cognitive_content(entry)
        content["media_type"] = asset.media_type
        item = StateItem(
            sa_id=f"course::{entry['entry_id']}::{asset.asset_id}",
            family="course_asset",
            label=str(content.get("neutral_label", entry["entry_id"])),
            real_energy=energy,
            virtual_energy=0.0,
            attention_energy=energy,
            cognitive_pressure=energy,
            channel_signature=(media, "course_replay"),
            source="phase15_course_replay",
            metadata={
                "cognitive_content": content,
                "asset_id": asset.asset_id,
                "asset_use": asset.intended_use,
                "phase": phase,
                "perceived_substrate": "COURSE_REPLAY_ASSET",
            },
        )
        marker = MarkerEvent(
            tick=int(tick),
            kind="PERCEIVED",
            target_sa_id=item.sa_id,
            real_energy=energy,
            metadata={
                "substrate": "COURSE_REPLAY_ASSET",
                "asset_id": asset.asset_id,
                "intended_use": asset.intended_use,
            },
        )
        feeling = FeelingValue("course_attention", energy)
        return make_packet(content_sas=(item,), source_markers=(marker,), feeling_sas=(feeling,))

    def _tick_row(
        self,
        tick: int,
        title: str,
        demo: CourseReplayDemoSpec,
        entry: Mapping[str, object],
        asset_refs: Sequence[str],
        packet: LearningPacket,
        q_table: QTableWithBackoff,
        ap_output: str,
        *,
        q_score: float | None = None,
    ) -> dict[str, object]:
        score = q_table.query(packet, self._action_id(entry)) if q_score is None else q_score
        return {
            "tick": int(tick),
            "title": title,
            "question": demo.question,
            "entry_id": str(entry["entry_id"]),
            "neutral_label": str(entry["public_payload"]["neutral_label"]),
            "asset_refs": list(asset_refs),
            "asset_urls": [f"/api/course/assets/{asset_id}" for asset_id in asset_refs],
            "asset_origins": [self.assets_by_id[asset_id].asset_origin for asset_id in asset_refs],
            "manifest_ids": [self.asset_manifest_by_id[asset_id] for asset_id in asset_refs],
            "mind": {
                "focus": str(entry["public_payload"]["concept_kind"]),
                "marker": "PERCEIVED",
                "source": "COURSE_REPLAY_ASSET",
                "feeling": "course_attention",
            },
            "packet": {
                "content_key": repr(packet.content_key()),
                "source_key": repr(packet.source_key()),
                "feeling_key": repr(packet.feeling_key()),
            },
            "q_score": round(float(score), 4),
            "ap_output": ap_output,
        }

    def _summary(self, ticks: Sequence[Mapping[str, object]]) -> dict[str, object]:
        return {
            "tick_count": len(ticks),
            "final_output": str(ticks[-1].get("ap_output", "")) if ticks else "",
            "asset_ref_count": sum(len(tick.get("asset_refs", ())) for tick in ticks),
            "manifest_ids": sorted({str(item) for tick in ticks for item in tick.get("manifest_ids", ())}),
            "asset_origins": sorted({str(item) for tick in ticks for item in tick.get("asset_origins", ())}),
            "runtime_generated": True,
        }

    def _persist(self, payload: Mapping[str, object]) -> None:
        if self.state_db_path is None:
            return
        self.state_db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(self.state_db_path)
        try:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS course_replay_trace "
                "(id INTEGER PRIMARY KEY AUTOINCREMENT, demo_id TEXT NOT NULL, payload_json TEXT NOT NULL)"
            )
            conn.execute(
                "INSERT INTO course_replay_trace(demo_id, payload_json) VALUES (?, ?)",
                (
                    str(payload["demo"]["demo_id"]),
                    json.dumps(payload, ensure_ascii=False, sort_keys=True),
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def _demo(self, demo_id: str) -> CourseReplayDemoSpec:
        for demo in ALL_DEMOS:
            if demo.demo_id == demo_id:
                return demo
        raise KeyError(demo_id)

    def _load_manifests(self) -> tuple[CurriculumAssetManifest, ...]:
        """@op_count: O(manifests * assets)."""
        paths = (self.manifest_path,) + tuple(path for path in self.additional_manifest_paths if path.exists())
        return tuple(load_asset_manifest_file(path) for path in paths)

    def _package_paths(self) -> tuple[Path, ...]:
        """@op_count: O(package_roots * files)."""
        roots = (self.package_root,) + tuple(path for path in self.additional_package_roots if path.exists())
        return tuple(path for root in roots for path in sorted(root.glob("*.yaml")))

    def _entry(self, package: Mapping[str, object], entry_id: str) -> Mapping[str, object]:
        for entry in package.get("entries", ()):
            if isinstance(entry, Mapping) and entry.get("entry_id") == entry_id:
                return entry
        raise KeyError(entry_id)

    def _energy_for_asset(self, asset: CurriculumAssetRecord) -> float:
        if asset.intended_use == "held_out":
            return float(load_constant("curriculum.replay.held_out_energy"))
        if asset.intended_use == "contrast":
            return float(load_constant("curriculum.replay.contrast_energy"))
        return float(load_constant("curriculum.replay.perceived_energy"))

    def _action_id(self, entry: Mapping[str, object]) -> str:
        return f"course_attend::{entry['entry_id']}"

    def _response_text(self, entry: Mapping[str, object]) -> str:
        return f"像是 {entry['public_payload']['neutral_label']}"

    def _cognitive_content(self, entry: Mapping[str, object]) -> dict[str, object]:
        """@op_count: O(payload_fields)."""
        metadata_only = {"teaching_intent"}
        return {
            str(key): value
            for key, value in dict(entry.get("public_payload", {})).items()
            if str(key) not in metadata_only
        }
