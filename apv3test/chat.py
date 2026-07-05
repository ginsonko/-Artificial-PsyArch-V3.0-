from __future__ import annotations

import argparse
import json
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from apv3test.runtime.cooccurrence_store import CooccurrenceAssociationStore
from apv3test.runtime.expression_phrase_memory import ExpressionPhraseMemory
from apv3test.runtime.minimalist_dialogue_flow import (
    MinimalistDialogueFlowRuntime,
    MinimalistDialogueTurnInput,
)
from apv3test.runtime.runtime_profile import RuntimeProfile, load_runtime_profile
from apv3test.runtime.sqlite_runtime_store import SQLiteRuntimeStore
from apv3test.runtime.style_redlines import HONEST_FALLBACK_TOKENS, assert_style_compliant
from apv3test.util.pseudonymous_id import compute_pseudonymous_identifier


@dataclass(frozen=True)
class _View:
    role: str
    is_filled: bool
    fit_margin: float = 0.7
    occupancy: float = 0.7
    commit_readiness: float = 0.5


@dataclass(frozen=True)
class ChatPhraseView:
    phrase_id: str
    text: str
    tokens: tuple[str, ...]
    support: float


@dataclass(frozen=True)
class ChatTurn:
    tick: int
    user_text: str
    user_text_hash: str
    user_text_length: int
    user_text_persisted: bool
    reply_text: str
    reply_tokens: tuple[str, ...]
    feeling_label: str
    learned_phrase_id: str
    committed_phrase_id: str
    state_id: int


_VIEWS_BY_MODE: dict[str, tuple[_View, ...]] = {
    "uncertain": (
        _View("slot", False, 0.0, 0.0, 0.0),
        _View("shared_fragment", True, 0.9, 1.0, 0.35),
    ),
    "flow": (
        _View("slot", True, 0.95, 1.0, 0.95),
        _View("fixed_anchor", True, 0.95, 1.0, 0.95),
    ),
    "request": (
        _View("slot", False, 0.15, 0.25, 0.2),
    ),
    "corrective": (
        _View("slot", True, 0.05, 1.0, 0.65),
        _View("fixed_anchor", True, 0.05, 1.0, 0.65),
    ),
}


class APV3MinimalistChatSession:
    """Minimal user-facing shell around the verified APV3 dialogue flow."""

    def __init__(
        self,
        profile: RuntimeProfile | None = None,
        *,
        profile_path: str | Path | None = None,
        state_db_path: str | Path | None = None,
        mode: str = "uncertain",
        autoload: bool = True,
        persist_user_text: bool | None = None,
    ) -> None:
        env_state = os.environ.get("APV3_CHAT_STATE_DB")
        resolved_state = state_db_path if state_db_path is not None else env_state
        self.profile = profile or load_runtime_profile(profile_path, sqlite_state_path=resolved_state)
        self.runtime = MinimalistDialogueFlowRuntime(self.profile.seed_corpus_path)
        self.store = SQLiteRuntimeStore(self.profile.sqlite_state_path)
        self.mode = _mode_or_default(mode)
        self.persist_user_text = bool(self.profile.persist_user_text if persist_user_text is None else persist_user_text)
        self.state = self._load_or_initial() if autoload else self.profile.initial_state()
        self.state = _sanitize_persisted_privacy(self.state)

    @property
    def tick(self) -> int:
        return int(self.state.get("apv3_chat_tick", 0))

    def say(
        self,
        user_text: str,
        *,
        reward_delta: float = 0.0,
        punish_delta: float = 0.0,
        mode: str | None = None,
    ) -> ChatTurn:
        active_mode = _mode_or_default(mode or self.mode)
        self.mode = active_mode
        text = str(user_text).strip()
        privacy = _privacy_summary(
            (text,) if text else (),
            state_dir=self.profile.sqlite_state_path.parent,
            persist_user_text=self.persist_user_text,
            pseudonymous_id_enabled=self.profile.pseudonymous_id_enabled,
            id_length_chars=self.profile.pseudonymous_id_length_chars,
        )
        tick = self.tick + 1
        observed_tokens = self._known_phrase_tokens(text)
        result = self.runtime.run_turn(
            self.state,
            MinimalistDialogueTurnInput(
                tick=tick,
                incoming_external_query=(text,) if text else (),
                incoming_query_hash=str(privacy.get("incoming_query_hash") or "") or None,
                incoming_query_count=int(privacy.get("incoming_query_count", 0)),
                incoming_query_total_length=int(privacy.get("incoming_query_total_length", 0)),
                context_tokens=(f"cli_mode:{active_mode}",),
                views=_VIEWS_BY_MODE[active_mode],
                observed_expression_tokens=observed_tokens,
                observed_attention_weight=0.72,
                reward_delta=float(reward_delta),
                punish_delta=float(punish_delta),
            ),
        )
        presented_tokens = result.committed_tokens or HONEST_FALLBACK_TOKENS
        presented_text = "".join(presented_tokens)
        self.state = dict(result.state)
        self.state["apv3_chat_tick"] = tick
        self.state["apv3_chat_mode"] = active_mode
        self.state["last_presented_text"] = presented_text
        self.state["last_presented_tokens"] = list(presented_tokens)
        self.state["chat_session_trace"] = _chat_trace_with(
            self.state,
            {
                "schema_id": "apv3_minimalist_chat_presented_turn/v1",
                "tick": tick,
                "mode": active_mode,
                "user_text": text if self.persist_user_text else None,
                **privacy,
                "runtime_committed_text": result.committed_text,
                "presented_text": presented_text,
                "presented_tokens": list(presented_tokens),
                "used_honest_fallback": not bool(result.committed_tokens),
                "learned_phrase_id": result.learned_phrase_id,
                "committed_phrase_id": result.committed_phrase_id,
                "feeling_label": result.feeling_label,
            },
        )
        state_id = self.store.save_state(self.state)
        assert_style_compliant(presented_tokens, max_tokens=self.profile.style_max_tokens)
        return ChatTurn(
            tick=tick,
            user_text=text,
            user_text_hash=str(privacy.get("user_text_hash") or ""),
            user_text_length=int(privacy.get("user_text_length", 0)),
            user_text_persisted=self.persist_user_text,
            reply_text=presented_text,
            reply_tokens=presented_tokens,
            feeling_label=result.feeling_label,
            learned_phrase_id=result.learned_phrase_id,
            committed_phrase_id=result.committed_phrase_id,
            state_id=state_id,
        )

    def set_mode(self, mode: str) -> str:
        self.mode = _mode_or_default(mode)
        self.state["apv3_chat_mode"] = self.mode
        self.store.save_state(self.state)
        return self.mode

    def top_phrases(self, *, top_k: int = 5) -> tuple[ChatPhraseView, ...]:
        tick = max(1, self.tick)
        memory = ExpressionPhraseMemory.from_state(self.state.get("expression_phrase_memory"))
        label = _latest_feeling_label(self.state)
        if label:
            assoc = CooccurrenceAssociationStore.from_state(self.state.get("cooccurrence_associations"))
            pids = assoc.nearest_paradigms_by_label((label,), top_k=max(1, int(top_k)) * 4, current_tick=tick)
            records = memory.recall(pids, top_k=max(1, int(top_k)), current_tick=tick)
        else:
            rows = sorted(memory.records, key=lambda item: (-item.decayed_support(tick, memory.config), item.phrase_id))
            records = tuple(rows[: max(1, int(top_k))])
        return tuple(
            ChatPhraseView(
                phrase_id=record.phrase_id,
                text="".join(record.tokens),
                tokens=record.tokens,
                support=round(float(record.decayed_support(tick, memory.config)), 6),
            )
            for record in records
        )

    def _load_or_initial(self) -> dict[str, object]:
        try:
            state = self.store.load_state()
        except KeyError:
            state = self.profile.initial_state()
            state["apv3_chat_mode"] = self.mode
            return state
        if not isinstance(state, dict):
            return self.profile.initial_state()
        return dict(state)

    def _known_phrase_tokens(self, text: str) -> tuple[str, ...]:
        if not text:
            return ()
        memory = ExpressionPhraseMemory.from_state(self.state.get("expression_phrase_memory"))
        if not memory.records:
            memory = ExpressionPhraseMemory.from_seed_corpus(self.profile.seed_corpus_path)
        for record in memory.records:
            if "".join(record.tokens) == text:
                return record.tokens
        return ()


def main(argv: Sequence[str] | None = None) -> int:
    _configure_stdio()
    parser = argparse.ArgumentParser(description="APV3 minimalist Chinese dialogue CLI")
    parser.add_argument("--profile", default=None, help="runtime profile JSON path")
    parser.add_argument("--state-db", default=None, help="SQLite state path")
    parser.add_argument("--mode", default="uncertain", choices=tuple(sorted(_VIEWS_BY_MODE)))
    parser.add_argument("--once", default=None, help="run one user turn and exit")
    parser.add_argument("--privacy-status", action="store_true", help="print local privacy status and exit")
    parser.add_argument("--export-my-data", default=None, help="write sanitized runtime state JSON to this path")
    parser.add_argument("--delete-my-data", action="store_true", help="delete local runtime DB and install salt")
    args = parser.parse_args(argv)

    session = APV3MinimalistChatSession(
        profile_path=args.profile,
        state_db_path=args.state_db,
        mode=args.mode,
    )
    if args.privacy_status:
        _print_privacy_status(session)
        return 0
    if args.export_my_data:
        _export_my_data(session, Path(args.export_my_data))
        return 0
    if args.delete_my_data:
        _delete_my_data(session)
        return 0
    if args.once is not None:
        turn = session.say(args.once)
        print(turn.reply_text)
        return 0
    _run_repl(session)
    return 0


def _run_repl(session: APV3MinimalistChatSession) -> None:
    print("APV3 minimalist chat ready. 输入中文；:top 查看短语；:mode uncertain|flow|request|corrective 切换结构态；:quit 退出。")
    for line in sys.stdin:
        text = line.strip()
        if not text:
            continue
        if text in {":quit", ":exit"}:
            break
        if text.startswith(":mode"):
            parts = text.split(maxsplit=1)
            mode = session.set_mode(parts[1] if len(parts) > 1 else session.mode)
            print(f"mode={mode}")
            continue
        if text.startswith(":top"):
            parts = text.split(maxsplit=1)
            n = _safe_int(parts[1], 5) if len(parts) > 1 else 5
            for index, phrase in enumerate(session.top_phrases(top_k=n), start=1):
                print(f"{index}. {phrase.text} support={phrase.support}")
            continue
        if text == ":+": 
            turn = session.say("", reward_delta=0.08)
        elif text == ":-":
            turn = session.say("", punish_delta=0.12)
        else:
            turn = session.say(text)
        print(turn.reply_text)


def _latest_feeling_label(state: Mapping[str, object]) -> str:
    rows = state.get("minimalist_dialogue_trace", [])
    if not isinstance(rows, list):
        return ""
    for row in reversed(rows):
        if isinstance(row, Mapping) and row.get("feeling_label"):
            return str(row.get("feeling_label", ""))
    return ""


def _chat_trace_with(state: Mapping[str, object], row: Mapping[str, object]) -> list[dict[str, object]]:
    rows = state.get("chat_session_trace", [])
    trace = [_sanitize_chat_row(dict(item)) for item in rows if isinstance(item, Mapping)] if isinstance(rows, list) else []
    trace.append(dict(row))
    return trace


def _privacy_summary(
    incoming: tuple[str, ...],
    *,
    state_dir: Path,
    persist_user_text: bool,
    pseudonymous_id_enabled: bool,
    id_length_chars: int,
) -> dict[str, object]:
    total_length = sum(len(item) for item in incoming)
    payload: dict[str, object] = {
        "incoming_query_count": len(incoming),
        "incoming_query_total_length": total_length,
        "user_text_length": total_length,
        "user_text_persisted": bool(persist_user_text),
    }
    if pseudonymous_id_enabled and incoming:
        payload["incoming_query_hash"] = compute_pseudonymous_identifier(
            incoming,
            state_dir=state_dir,
            length_chars=id_length_chars,
        )
        payload["user_text_hash"] = payload["incoming_query_hash"]
    else:
        payload["incoming_query_hash"] = None
        payload["user_text_hash"] = None
    return payload


def _sanitize_persisted_privacy(state: Mapping[str, object]) -> dict[str, object]:
    sanitized = dict(state)
    rows = sanitized.get("chat_session_trace", [])
    if isinstance(rows, list):
        sanitized["chat_session_trace"] = [
            _sanitize_chat_row(dict(item)) for item in rows if isinstance(item, Mapping)
        ]
    runtime_rows = sanitized.get("minimalist_dialogue_trace", [])
    if isinstance(runtime_rows, list):
        sanitized["minimalist_dialogue_trace"] = [
            _sanitize_runtime_row(dict(item)) for item in runtime_rows if isinstance(item, Mapping)
        ]
    return sanitized


def _sanitize_chat_row(row: dict[str, object]) -> dict[str, object]:
    if row.get("user_text_persisted") is not True:
        row["user_text"] = None
    return row


def _sanitize_runtime_row(row: dict[str, object]) -> dict[str, object]:
    row.pop("incoming_external_query", None)
    return row


def _mode_or_default(mode: str) -> str:
    value = str(mode).strip().lower()
    return value if value in _VIEWS_BY_MODE else "uncertain"


def _safe_int(value: object, default: int) -> int:
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return default


def _configure_stdio() -> None:
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except AttributeError:
            pass


def _print_privacy_status(session: APV3MinimalistChatSession) -> None:
    payload = {
        "schema_id": "apv3_privacy_status/v1",
        "persist_user_text": session.persist_user_text,
        "pseudonymous_id_enabled": session.profile.pseudonymous_id_enabled,
        "pseudonymous_id_length_chars": session.profile.pseudonymous_id_length_chars,
        "sqlite_state_path": str(session.profile.sqlite_state_path),
        "install_salt_path": str(session.profile.sqlite_state_path.parent / "install_salt.bin"),
    }
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True))


def _export_my_data(session: APV3MinimalistChatSession, path: Path) -> None:
    state = _sanitize_persisted_privacy(session.state)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2), encoding="utf-8")
    print(str(path))


def _delete_my_data(session: APV3MinimalistChatSession) -> None:
    for path in (session.profile.sqlite_state_path, session.profile.sqlite_state_path.parent / "install_salt.bin"):
        try:
            path.unlink()
        except FileNotFoundError:
            pass
    print("deleted")


if __name__ == "__main__":
    raise SystemExit(main())
