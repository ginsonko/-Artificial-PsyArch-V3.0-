from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import uuid
from typing import Any, Iterable

from runtime.cognitive.state_pool.state_pool import load_constant


@dataclass(frozen=True)
class PacketKeyFields:
    sensory_feature_signature: tuple[int, ...]
    epistemic_source: str
    substrate: str
    receptor_version: str

    def packet_key(self) -> str:
        """@op_count: O(signature_dim)."""
        return make_packet_key(
            sensory_feature_signature=self.sensory_feature_signature,
            epistemic_source=self.epistemic_source,
            substrate=self.substrate,
            receptor_version=self.receptor_version,
        )


@dataclass(frozen=True)
class PerceptVector:
    vector_uuid: str
    signature: tuple[int, ...]
    full_vec_path: str | None
    epistemic_source: str
    substrate: str
    receptor_version: str
    tick_acquired: int
    importance: float
    metadata: dict[str, Any] = field(default_factory=dict)

    def packet_key(self) -> str:
        """@op_count: O(signature_dim)."""
        return make_packet_key(
            sensory_feature_signature=self.signature,
            epistemic_source=self.epistemic_source,
            substrate=self.substrate,
            receptor_version=self.receptor_version,
        )

    def to_json_dict(self) -> dict[str, Any]:
        """@op_count: O(signature_dim + metadata_size)."""
        return {
            "vector_uuid": self.vector_uuid,
            "signature": list(self.signature),
            "full_vec_path": self.full_vec_path,
            "epistemic_source": self.epistemic_source,
            "substrate": self.substrate,
            "receptor_version": self.receptor_version,
            "tick_acquired": self.tick_acquired,
            "importance": self.importance,
            "metadata": self.metadata,
            "packet_key": self.packet_key(),
        }

    @classmethod
    def from_json_dict(cls, payload: dict[str, Any]) -> PerceptVector:
        """@op_count: O(signature_dim + metadata_size)."""
        return cls(
            vector_uuid=str(payload["vector_uuid"]),
            signature=tuple(int(value) for value in payload["signature"]),
            full_vec_path=payload.get("full_vec_path"),
            epistemic_source=str(payload["epistemic_source"]),
            substrate=str(payload["substrate"]),
            receptor_version=str(payload["receptor_version"]),
            tick_acquired=int(payload["tick_acquired"]),
            importance=float(payload["importance"]),
            metadata=dict(payload.get("metadata", {})),
        )


@dataclass(frozen=True)
class PartPrototype:
    part_uuid: str
    channel: str
    patch_signature: tuple[int, ...]
    exemplar_id: str
    activation_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        """@op_count: O(signature_dim + metadata_size)."""
        return {
            "part_uuid": self.part_uuid,
            "channel": self.channel,
            "patch_signature": list(self.patch_signature),
            "exemplar_id": self.exemplar_id,
            "activation_count": self.activation_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_json_dict(cls, payload: dict[str, Any]) -> PartPrototype:
        """@op_count: O(signature_dim + metadata_size)."""
        return cls(
            part_uuid=str(payload["part_uuid"]),
            channel=str(payload["channel"]),
            patch_signature=tuple(int(value) for value in payload["patch_signature"]),
            exemplar_id=str(payload["exemplar_id"]),
            activation_count=int(payload.get("activation_count", 0)),
            metadata=dict(payload.get("metadata", {})),
        )


@dataclass(frozen=True)
class PartAssociation:
    part_uuid: str
    weight: float


@dataclass(frozen=True)
class ConceptPrototype:
    concept_uuid: str
    lifecycle_status: str
    part_weights: tuple[PartAssociation, ...] = ()
    vocab_associations: tuple[str, ...] = ()
    epistemic_source: str = ""
    lifetime_observations: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        """@op_count: O(parts + vocab + metadata_size)."""
        return {
            "concept_uuid": self.concept_uuid,
            "lifecycle_status": self.lifecycle_status,
            "part_weights": [
                {"part_uuid": association.part_uuid, "weight": association.weight}
                for association in self.part_weights
            ],
            "vocab_associations": list(self.vocab_associations),
            "epistemic_source": self.epistemic_source,
            "lifetime_observations": self.lifetime_observations,
            "metadata": self.metadata,
        }

    @classmethod
    def from_json_dict(cls, payload: dict[str, Any]) -> ConceptPrototype:
        """@op_count: O(parts + vocab + metadata_size)."""
        return cls(
            concept_uuid=str(payload["concept_uuid"]),
            lifecycle_status=str(payload["lifecycle_status"]),
            part_weights=tuple(
                PartAssociation(str(item["part_uuid"]), float(item["weight"]))
                for item in payload.get("part_weights", [])
            ),
            vocab_associations=tuple(str(item) for item in payload.get("vocab_associations", [])),
            epistemic_source=str(payload.get("epistemic_source", "")),
            lifetime_observations=int(payload.get("lifetime_observations", 0)),
            metadata=dict(payload.get("metadata", {})),
        )


@dataclass(frozen=True)
class TemporalEventBinding:
    event_uuid: str
    percept_uuids: tuple[str, ...]
    tick_window: tuple[int, int]
    source_markers: tuple[str, ...] = ()
    lifetime_cooccurrence_count: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_json_dict(self) -> dict[str, Any]:
        """@op_count: O(percepts + source_markers + metadata_size)."""
        return {
            "event_uuid": self.event_uuid,
            "percept_uuids": list(self.percept_uuids),
            "tick_window": list(self.tick_window),
            "source_markers": list(self.source_markers),
            "lifetime_cooccurrence_count": self.lifetime_cooccurrence_count,
            "metadata": self.metadata,
        }

    @classmethod
    def from_json_dict(cls, payload: dict[str, Any]) -> TemporalEventBinding:
        """@op_count: O(percepts + source_markers + metadata_size)."""
        tick_window = tuple(int(value) for value in payload["tick_window"])
        return cls(
            event_uuid=str(payload["event_uuid"]),
            percept_uuids=tuple(str(item) for item in payload.get("percept_uuids", [])),
            tick_window=(tick_window[0], tick_window[1]),
            source_markers=tuple(str(item) for item in payload.get("source_markers", [])),
            lifetime_cooccurrence_count=int(payload.get("lifetime_cooccurrence_count", 0)),
            metadata=dict(payload.get("metadata", {})),
        )


@dataclass(frozen=True)
class RecallSkeletonResult:
    candidate_uuids: tuple[str, ...]
    status: str
    boundary_note: str


class Layer1PerceptVectorStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, vector: PerceptVector, *, write_mode: str = "runtime") -> None:
        """@op_count: O(signature_dim + metadata_size)."""
        validate_signature(vector.signature)
        assert_opaque_identifier(vector.vector_uuid)
        if write_mode != str(load_constant("phase19.vector.schema_fixture_write_mode")):
            if not runtime_receptor_version_is_accepted(vector.receptor_version):
                raise ValueError("Layer-1 runtime writes require the foveated receptor version")
        _write_json(self._path(vector.vector_uuid), vector.to_json_dict())

    def get(self, vector_uuid: str) -> PerceptVector | None:
        """@op_count: O(signature_dim + metadata_size)."""
        path = self._path(vector_uuid)
        if not path.exists():
            return None
        return PerceptVector.from_json_dict(_read_json(path))

    def list_ids(self) -> tuple[str, ...]:
        """@op_count: O(records)."""
        return tuple(sorted(path.stem for path in self.root.glob("*.json")))

    def count(self) -> int:
        """@op_count: O(records)."""
        return len(self.list_ids())

    def _path(self, vector_uuid: str) -> Path:
        return self.root / f"{vector_uuid}.json"


class Layer2PartPrototypeStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, part: PartPrototype) -> None:
        """@op_count: O(signature_dim + metadata_size)."""
        assert_opaque_identifier(part.part_uuid)
        assert_opaque_identifier(part.exemplar_id)
        _write_json(self._path(part.part_uuid), part.to_json_dict())

    def get(self, part_uuid: str) -> PartPrototype | None:
        """@op_count: O(signature_dim + metadata_size)."""
        path = self._path(part_uuid)
        if not path.exists():
            return None
        return PartPrototype.from_json_dict(_read_json(path))

    def list_ids(self) -> tuple[str, ...]:
        """@op_count: O(records)."""
        return tuple(sorted(path.stem for path in self.root.glob("*.json")))

    def _path(self, part_uuid: str) -> Path:
        return self.root / f"{part_uuid}.json"


class Layer3ConceptPrototypeStore:
    def __init__(self, root: Path | str) -> None:
        self.root = Path(root)
        self.concept_root = self.root / "concepts"
        self.event_root = self.root / "temporal_events"
        self.concept_root.mkdir(parents=True, exist_ok=True)
        self.event_root.mkdir(parents=True, exist_ok=True)

    def put_concept(self, concept: ConceptPrototype) -> None:
        """@op_count: O(parts + vocab + metadata_size)."""
        assert_opaque_identifier(concept.concept_uuid)
        _write_json(self._concept_path(concept.concept_uuid), concept.to_json_dict())

    def get_concept(self, concept_uuid: str) -> ConceptPrototype | None:
        """@op_count: O(parts + vocab + metadata_size)."""
        path = self._concept_path(concept_uuid)
        if not path.exists():
            return None
        return ConceptPrototype.from_json_dict(_read_json(path))

    def spawn_tentative_concept(
        self,
        initial_part_associations: Iterable[PartAssociation],
        *,
        epistemic_source: str,
    ) -> ConceptPrototype:
        """@op_count: O(parts)."""
        concept = ConceptPrototype(
            concept_uuid=new_opaque_uuid("c"),
            lifecycle_status=str(load_constant("phase19.vector.tentative_lifecycle_status")),
            part_weights=tuple(initial_part_associations),
            vocab_associations=(),
            epistemic_source=epistemic_source,
            lifetime_observations=int(load_constant("phase19.vector.initial_observation_count")),
        )
        self.put_concept(concept)
        return concept

    def put_temporal_event(self, event: TemporalEventBinding) -> None:
        """@op_count: O(percepts + source_markers + metadata_size)."""
        assert_opaque_identifier(event.event_uuid)
        _write_json(self._event_path(event.event_uuid), event.to_json_dict())

    def get_temporal_event(self, event_uuid: str) -> TemporalEventBinding | None:
        """@op_count: O(percepts + source_markers + metadata_size)."""
        path = self._event_path(event_uuid)
        if not path.exists():
            return None
        return TemporalEventBinding.from_json_dict(_read_json(path))

    def list_concept_ids(self) -> tuple[str, ...]:
        """@op_count: O(records)."""
        return tuple(sorted(path.stem for path in self.concept_root.glob("*.json")))

    def _concept_path(self, concept_uuid: str) -> Path:
        return self.concept_root / f"{concept_uuid}.json"

    def _event_path(self, event_uuid: str) -> Path:
        return self.event_root / f"{event_uuid}.json"


def make_packet_key(
    *,
    sensory_feature_signature: Iterable[int],
    epistemic_source: str,
    substrate: str,
    receptor_version: str,
) -> str:
    """@op_count: O(signature_dim)."""
    fields = {
        "sensory_feature_signature": list(validate_signature(tuple(sensory_feature_signature))),
        "epistemic_source": str(epistemic_source),
        "substrate": str(substrate),
        "receptor_version": str(receptor_version),
    }
    canonical = json.dumps(fields, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def validate_signature(signature: tuple[int, ...]) -> tuple[int, ...]:
    """@op_count: O(signature_dim)."""
    expected = int(load_constant("phase19.vector.layer1_signature_dim"))
    low = int(load_constant("phase19.vector.signature_min_value"))
    high = int(load_constant("phase19.vector.signature_max_value"))
    if len(signature) != expected:
        raise ValueError("signature dimension mismatch")
    for value in signature:
        if int(value) < low or int(value) > high:
            raise ValueError("signature values must stay in uint8 range")
    return signature


def runtime_receptor_version_is_accepted(receptor_version: str) -> bool:
    """@op_count: O(1)."""
    return str(receptor_version) == str(load_constant("phase19.vector.min_runtime_receptor_version"))


def new_opaque_uuid(prefix: str) -> str:
    """@op_count: O(1)."""
    return f"{prefix}_{uuid.uuid4().hex}"


def assert_opaque_identifier(identifier: str) -> None:
    """@op_count: O(forbidden_terms)."""
    text = str(identifier)
    if any(token in text.lower() for token in load_constant("phase19.vector.forbidden_identifier_terms")):
        raise ValueError("identifier contains a forbidden semantic term")
    if any(token in text for token in (" ", "/", "\\", ":")):
        raise ValueError("identifier must be opaque and path-safe")


def c_recall_schema_skeleton(*, allow_mock: str = "") -> RecallSkeletonResult:
    """@op_count: O(1)."""
    if allow_mock == str(load_constant("phase19.vector.schema_fixture_write_mode")):
        return RecallSkeletonResult(
            candidate_uuids=(),
            status="schema_only_mock",
            boundary_note="Phase 19.0b0 mock proves interface shape only, not recall quality.",
        )
    return RecallSkeletonResult(
        candidate_uuids=(),
        status="empty_schema_skeleton",
        boundary_note="Phase 19.0b0 does not prove real C recall.",
    )


def b_recall_schema_skeleton(*, allow_mock: str = "") -> RecallSkeletonResult:
    """@op_count: O(1)."""
    if allow_mock == str(load_constant("phase19.vector.schema_fixture_write_mode")):
        return RecallSkeletonResult(
            candidate_uuids=(),
            status="schema_only_mock",
            boundary_note="Phase 19.0b0 mock proves interface shape only, not B recall quality.",
        )
    return RecallSkeletonResult(
        candidate_uuids=(),
        status="empty_schema_skeleton",
        boundary_note="Phase 19.0b0 does not prove real B recall.",
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2),
        encoding="utf-8",
    )


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))

