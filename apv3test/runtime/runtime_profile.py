from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


@dataclass(frozen=True)
class RuntimeProfile:
    """Clean startup contract for a user-facing APV3 runtime."""

    schema_id: str
    profile_id: str
    profile_version: str
    runtime_entry: str
    state_schema_id: str
    seed_corpus_path: Path
    sqlite_state_path: Path
    style_gate_enabled: bool
    style_max_tokens: int
    allow_new_phrases: bool
    seed_phrase_count: int
    runtime_modules: tuple[str, ...]
    disabled_dev_fields: tuple[str, ...]
    forbidden_runtime_markers: tuple[str, ...]
    persist_user_text: bool
    pseudonymous_id_enabled: bool
    pseudonymous_id_length_chars: int

    def initial_state(self) -> dict[str, object]:
        return {
            "schema_id": self.state_schema_id,
            "runtime_profile_id": self.profile_id,
            "runtime_profile_version": self.profile_version,
        }

    def validate(self) -> None:
        if self.schema_id != "apv3_runtime_profile/v1":
            raise ValueError(f"unsupported runtime profile schema: {self.schema_id}")
        if not self.profile_id:
            raise ValueError("runtime profile requires profile_id")
        if not self.seed_corpus_path.exists():
            raise FileNotFoundError(f"seed corpus not found: {self.seed_corpus_path}")
        if self.allow_new_phrases:
            raise ValueError("minimalist runtime profile must keep phrase creation disabled")
        if not self.style_gate_enabled:
            raise ValueError("minimalist runtime profile requires style gate")
        if self.style_max_tokens > 3:
            raise ValueError("minimalist runtime profile must keep max_tokens <= 3")
        if self.persist_user_text:
            raise ValueError("default minimalist runtime profile must not persist user text")


def default_runtime_profile_path() -> Path:
    return _project_root() / "apv3test" / "data" / "runtime_profile_minimalist_cli.json"


def load_runtime_profile(
    path: str | Path | None = None,
    *,
    sqlite_state_path: str | Path | None = None,
) -> RuntimeProfile:
    profile_path = Path(path) if path is not None else default_runtime_profile_path()
    raw = json.loads(profile_path.read_text(encoding="utf-8"))
    if not isinstance(raw, Mapping):
        raise ValueError("runtime profile must be a JSON object")
    profile = _profile_from_payload(raw, profile_path=profile_path, sqlite_state_path=sqlite_state_path)
    profile.validate()
    return profile


def _profile_from_payload(
    payload: Mapping[str, object],
    *,
    profile_path: Path,
    sqlite_state_path: str | Path | None,
) -> RuntimeProfile:
    style_gate = _mapping(payload.get("style_gate"))
    phrase_memory = _mapping(payload.get("phrase_memory"))
    privacy = _mapping(payload.get("privacy"))
    resolved_seed = _resolve_profile_path(profile_path, str(payload.get("seed_corpus_path", "")))
    state_path_raw = sqlite_state_path if sqlite_state_path is not None else payload.get("sqlite_state_path", "")
    resolved_state = _resolve_profile_path(profile_path, str(state_path_raw))
    return RuntimeProfile(
        schema_id=str(payload.get("schema_id", "")),
        profile_id=str(payload.get("profile_id", "")),
        profile_version=str(payload.get("profile_version", "")),
        runtime_entry=str(payload.get("runtime_entry", "")),
        state_schema_id=str(payload.get("state_schema_id", "")),
        seed_corpus_path=resolved_seed,
        sqlite_state_path=resolved_state,
        style_gate_enabled=bool(style_gate.get("enabled", False)),
        style_max_tokens=int(style_gate.get("max_tokens", 3)),
        allow_new_phrases=bool(phrase_memory.get("allow_new_phrases", True)),
        seed_phrase_count=int(phrase_memory.get("seed_phrase_count", 0)),
        runtime_modules=_string_tuple(payload.get("runtime_modules", ())),
        disabled_dev_fields=_string_tuple(payload.get("disabled_dev_fields", ())),
        forbidden_runtime_markers=_string_tuple(payload.get("forbidden_runtime_markers", ())),
        persist_user_text=bool(privacy.get("persist_user_text", False)),
        pseudonymous_id_enabled=bool(privacy.get("pseudonymous_id_enabled", True)),
        pseudonymous_id_length_chars=int(privacy.get("pseudonymous_id_length_chars", 32)),
    )


def _resolve_profile_path(profile_path: Path, value: str) -> Path:
    if not value:
        return profile_path.parent
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return (_project_root() / candidate).resolve()


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _mapping(value: object) -> Mapping[str, object]:
    return value if isinstance(value, Mapping) else {}


def _string_tuple(value: object) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return ()
    return tuple(str(item) for item in value if str(item))
