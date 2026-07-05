from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from runtime.cognitive.state_pool.state_pool import load_constant


@dataclass(frozen=True)
class DemoScenario:
    scenario_id: str
    label: str
    capability_tags: tuple[str, ...]


@dataclass(frozen=True)
class DemoProfile:
    schema_version: int
    voice_style: str
    scenarios: tuple[DemoScenario, ...]


def load_demo_profile(raw: Mapping[str, object]) -> DemoProfile:
    version = int(raw.get("schema_version", 0))
    expected = int(load_constant("demo_substrate.profile_schema_version"))
    if version != expected:
        raise ValueError("unsupported demo substrate profile schema_version")
    scenarios = tuple(_scenario(item) for item in _sequence(raw.get("scenarios")))
    return DemoProfile(
        schema_version=version,
        voice_style=str(raw.get("voice_style", "quiet_girl")),
        scenarios=scenarios,
    )


def default_demo_profile() -> DemoProfile:
    return load_demo_profile(
        {
            "schema_version": int(load_constant("demo_substrate.profile_schema_version")),
            "voice_style": "quiet_girl",
            "scenarios": (
                {
                    "scenario_id": "text_dialogue",
                    "label": "text dialogue",
                    "capability_tags": ("chat", "reward", "memory", "audit"),
                },
                {
                    "scenario_id": "desktop_companion",
                    "label": "desktop multimodal companion",
                    "capability_tags": ("vision", "audio", "chat", "audit"),
                },
                {
                    "scenario_id": "agent_collaboration",
                    "label": "agent collaboration",
                    "capability_tags": ("goal", "deliberative", "trust", "audit"),
                },
                {
                    "scenario_id": "embodied_preview",
                    "label": "embodied preview",
                    "capability_tags": ("vision", "action", "joint_attention", "audit"),
                },
            ),
        }
    )


def _scenario(raw: object) -> DemoScenario:
    if not isinstance(raw, Mapping):
        raise ValueError("scenario must be a mapping")
    return DemoScenario(
        scenario_id=str(raw.get("scenario_id", "")),
        label=str(raw.get("label", "")),
        capability_tags=tuple(str(item) for item in _sequence(raw.get("capability_tags"))),
    )


def _sequence(value: object) -> Sequence[object]:
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return value
    return ()
