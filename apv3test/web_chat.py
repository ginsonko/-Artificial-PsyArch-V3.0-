from __future__ import annotations

import argparse
import base64
import hashlib
import json
import mimetypes
import sqlite3
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import parse_qs, unquote, urlparse

from apv3test.chat import APV3MinimalistChatSession
from apv3test.runtime.phase20_memory_packages import (
    delete_memories,
    export_memory_package,
    import_memory_package,
    list_memory_view,
    uninstall_memory_package,
)
from apv3test.runtime.phase20_open_dialogue import Phase20MultimodalSession
from apv3test.runtime.phase20_7 import (
    MediaInput,
    TeacherFeedback,
    list_active_unclosed_items,
    list_unified_memory_entries,
    run_phase20_7_turn,
    synthesize_xiaoyi_tts,
    tombstone_memory_entry,
)
from apv3test.runtime.course_replay import CourseReplayRuntime
from apv3test.runtime import CooccurrenceAssociationStore, ExpressionPhraseMemory, load_runtime_profile
from runtime.cognitive.attention.visual_focus import propose_visual_focus_actions, visual_focus_overlay
from runtime.cognitive.cognitive_feelings.factory import build_cognitive_feelings
from runtime.cognitive.endogenous.step import step_endogenous_drive
from runtime.cognitive.marker.events import MarkerEvent
from runtime.cognitive.state_pool.state_pool import StateItem
from runtime.demo_substrate.audit_view import build_demo_audit_snapshot


PROJECT_ROOT = Path(__file__).resolve().parents[1]
WORKBENCH_MEDIA_ROOT = PROJECT_ROOT / "data" / "phase20_workbench_media"
PHASE20_7_DB_PATH = PROJECT_ROOT / "data" / "phase20_7_workbench.sqlite"
PHASE20_7_TTS_ROOT = PROJECT_ROOT / "data" / "phase20_7_tts"


class APV3WebChatApp:
    def __init__(self, *, state_db_path: str | Path | None = None) -> None:
        self.session = APV3MinimalistChatSession(
            profile=load_runtime_profile(sqlite_state_path=state_db_path),
        )
        self.phase20_session = Phase20MultimodalSession(state_db_path=state_db_path)
        course_db_path = None
        if state_db_path is not None:
            db_path = Path(state_db_path)
            course_db_path = db_path.with_name(f"{db_path.stem}_course_replay.sqlite")
        self.course_runtime = CourseReplayRuntime(state_db_path=course_db_path)
        self.lock = threading.Lock()
        self._phase20_live_progress: dict[str, dict[str, object]] = {}
        self._phase20_live_history: dict[str, dict[str, object]] = {}

    def send(self, payload: Mapping[str, object]) -> dict[str, object]:
        with self.lock:
            turn = self.session.say(
                str(payload.get("text", "")),
                mode=str(payload.get("mode", self.session.mode)),
            )
            return {"turn": _turn_payload(turn), "snapshot": snapshot_session(self.session)}

    def feedback(self, payload: Mapping[str, object]) -> dict[str, object]:
        kind = str(payload.get("kind", ""))
        reward = 0.1 if kind == "reward" else 0.0
        punish = 0.14 if kind == "punish" else 0.0
        with self.lock:
            turn = self.session.say("", reward_delta=reward, punish_delta=punish)
            return {"turn": _turn_payload(turn), "snapshot": snapshot_session(self.session)}

    def phase20_turn(self, payload: Mapping[str, object]) -> dict[str, object]:
        with self.lock:
            result = self.phase20_session.turn(payload)
            turn_payload = _phase20_turn_payload(result, payload)
            self._remember_phase20_live_history(payload, turn_payload)
            return {
                "turn": turn_payload,
                "snapshot": snapshot_session(self.phase20_session.chat),
            }

    def phase20_teach(self, payload: Mapping[str, object]) -> dict[str, object]:
        with self.lock:
            try:
                result = self.phase20_session.teach_latest(payload)
            except ValueError as exc:
                return {
                    "error": str(exc),
                    "snapshot": snapshot_session(self.phase20_session.chat),
                }
            return {"teaching": _phase20_teaching_payload(result), "snapshot": snapshot_session(self.phase20_session.chat)}

    def phase20_7_turn(self, payload: Mapping[str, object]) -> dict[str, object]:
        from apv3test.runtime.phase20_7.runtime import set_live_progress_hook
        media_inputs = _phase20_7_media_inputs(payload)
        teacher_feedback = None
        feedback_text = str(payload.get("teacher_feedback", "") or "")
        if feedback_text:
            teacher_feedback = TeacherFeedback(
                feedback_text=feedback_text,
                reward_mag=float(payload.get("reward_mag", 1.0) or 0.0),
                punish_mag=float(payload.get("punish_mag", 0.0) or 0.0),
                target_event_id=str(payload.get("target_event_id", "") or "") or None,
            )
        sid = str(payload.get("session_id", "phase20_7_workbench") or "phase20_7_workbench")

        _recent: list[dict[str, object]] = []

        def _on_tick(tick: int, action_type: str) -> None:
            _recent.append({"tick": tick, "action_type": action_type})
            if len(_recent) > 5:
                del _recent[:-5]
            self._phase20_live_progress[sid] = {
                "tick": tick,
                "action_type": action_type,
                "recent_actions": list(_recent),
            }

        with self.lock:
            set_live_progress_hook(_on_tick)
            try:
                result = run_phase20_7_turn(
                    user_text=str(payload.get("text", "") or ""),
                    media_inputs=media_inputs,
                    teacher_feedback=teacher_feedback,
                    session_id=str(payload.get("session_id", "phase20_7_workbench") or "phase20_7_workbench"),
                    db_path=PHASE20_7_DB_PATH,
                    max_ticks=_int_or_zero(payload.get("max_ticks", 32)) or 32,
                    post_commit_idle_ticks=_int_or_zero(payload.get("post_commit_idle_ticks", 0)),
                    runtime_stage=str(payload.get("runtime_stage", "stage6") or "stage6"),  # type: ignore[arg-type]
                )
            finally:
                set_live_progress_hook(None)
            return {
                "turn": result.to_dict(),
                # M4-2 (§187.3): 连续心智节奏 = f(arousal, fatigue) — 前端 auto-idle
                # 按此间隔跑下一个 idle tick. 情绪高涨→活跃(间隔短), 疲劳→安静(间隔长).
                # 服务端只给建议值, 不是定时器触发主动行为(红线): 说不说话仍由
                # runtime 的张力/经验竞争决定, 这里只调"心跳"快慢.
                "idle_pacing": _idle_pacing_from_emotion(result.emotion),
                # AP 画作外显 (§66/§16.4): turn 内产出的内心画面(想象召回/视觉重建 PNG,
                # 从状态池 canvas 渲染, 非原图) 以 URL 列表暴露 — 前端贴进 AP 气泡,
                # "AP 画的画" = 它想象中的画面. 纯视图层, 只读 tick trace 既有字段.
                "inner_pictures": _inner_picture_urls_from_turn(result),
                "memory": list(list_unified_memory_entries(PHASE20_7_DB_PATH, limit=80)),
                "unclosed": list(
                    list_active_unclosed_items(
                        PHASE20_7_DB_PATH,
                        limit=20,
                        session_id=str(payload.get("session_id", "phase20_7_workbench") or "phase20_7_workbench"),
                    )
                ),
            }

    def phase20_7_memory_list(self, payload: Mapping[str, object] | None = None) -> dict[str, object]:
        payload = payload or {}
        with self.lock:
            return {
                "schema_id": "apv3_phase20_7_unified_memory_view/v1",
                "items": list(
                    list_unified_memory_entries(
                        PHASE20_7_DB_PATH,
                        limit=_int_or_zero(payload.get("limit", 200)) or 200,
                        include_inactive=bool(payload.get("include_inactive", False)),
                    )
                ),
                "unclosed": list(
                    list_active_unclosed_items(
                        PHASE20_7_DB_PATH,
                        limit=50,
                        session_id=str(payload.get("session_id", "") or "") or None,
                    )
                ),
            }

    def phase20_7_memory_delete(self, payload: Mapping[str, object]) -> dict[str, object]:
        memory_entry_id = str(payload.get("memory_entry_id", "") or "")
        if not memory_entry_id:
            return {"error": "missing_memory_entry_id"}
        with self.lock:
            tombstone_id = tombstone_memory_entry(
                PHASE20_7_DB_PATH,
                memory_entry_id=memory_entry_id,
                reason=str(payload.get("reason", "user_delete") or "user_delete"),
            )
            return {
                "schema_id": "apv3_phase20_7_memory_delete/v1",
                "tombstone_id": tombstone_id,
                "memory": list(list_unified_memory_entries(PHASE20_7_DB_PATH, limit=80)),
            }

    def phase20_7_tts_synthesize(self, payload: Mapping[str, object]) -> dict[str, object]:
        reply_text = str(payload.get("reply_text", "") or "")
        try:
            result = synthesize_xiaoyi_tts(reply_text, out_dir=PHASE20_7_TTS_ROOT)
            path = Path(str(result["path"]))
            return {
                "schema_id": "apv3_phase20_7_xiaoyi_tts_playback/v1",
                "ok": True,
                "url": _phase20_media_url(path),
                "path": str(path),
                "voice_id": result["voice_id"],
                "voice_name": result["voice_name"],
                "local_only": True,
                "bytes": result["bytes"],
            }
        except Exception as exc:
            error = str(exc)
            if error == "pyttsx3_unavailable":
                message = "当前 Python 环境没有 pyttsx3，无法调用本地 SAPI 合成。"
            elif error == "xiaoyi_voice_not_available_in_local_sapi":
                message = "当前本机 SAPI 没有暴露 xiaoyi 音色，AP 只记录朗读意图，不伪造音频。"
            else:
                message = error
            return {
                "schema_id": "apv3_phase20_7_xiaoyi_tts_playback/v1",
                "ok": False,
                "error": error,
                "message": message,
                "local_only": True,
            }

    def phase20_media_upload(self, payload: Mapping[str, object]) -> dict[str, object]:
        name = _safe_media_name(str(payload.get("name", "uploaded.bin") or "uploaded.bin"))
        data_url = str(payload.get("data_url", "") or "")
        if not data_url.startswith("data:") or "," not in data_url:
            return {"error": "invalid_media_data"}
        header, encoded = data_url.split(",", 1)
        if ";base64" not in header:
            return {"error": "media_must_be_base64"}
        mime = header.removeprefix("data:").split(";", 1)[0] or "application/octet-stream"
        if not (mime.startswith("image/") or mime.startswith("audio/")):
            return {"error": "unsupported_media_type"}
        raw = base64.b64decode(encoded.encode("ascii"), validate=True)
        WORKBENCH_MEDIA_ROOT.mkdir(parents=True, exist_ok=True)
        suffix = mimetypes.guess_extension(mime) or Path(name).suffix or ".bin"
        path = WORKBENCH_MEDIA_ROOT / f"{Path(name).stem[:48] or 'media'}_{_sha16(raw)}{suffix}"
        path.write_bytes(raw)
        return {
            "schema_id": "apv3_phase20_4_uploaded_media/v1",
            "path": str(path),
            "media_type": mime,
            "url": _phase20_media_url(path),
            "bytes": len(raw),
            "raw_user_text_persisted": False,
        }

    def phase20_agent(self, payload: Mapping[str, object]) -> dict[str, object]:
        with self.lock:
            result = self.phase20_session.agent_tool(
                text=str(payload.get("text", "")),
                image_path=str(payload.get("image_path", "")) or None,
            )
            return {
                "reply": result.reply,
                "object_files": [_phase20_object_payload(item) for item in result.object_files],
                "decision_tier": result.decision_tier,
                "raw_confidence": result.raw_confidence,
                "epistemic_source": result.epistemic_source,
                "trace": result.trace,
            }

    def phase20_memory_list(self, payload: Mapping[str, object] | None = None) -> dict[str, object]:
        payload = payload or {}
        with self.lock:
            return list_memory_view(
                self.phase20_session.chat.state,
                query=str(payload.get("query", "") or ""),
                package_id=str(payload.get("package_id", "") or ""),
                kinds=tuple(payload.get("kinds", ()) if isinstance(payload.get("kinds"), list) else ()),
                limit=_int_or_zero(payload.get("limit", 200)) or 200,
            )

    def phase20_memory_export(self, payload: Mapping[str, object]) -> dict[str, object]:
        with self.lock:
            return export_memory_package(
                self.phase20_session.chat.state,
                name=str(payload.get("name", "APV3 记忆包") or "APV3 记忆包"),
                query=str(payload.get("query", "") or ""),
                include_memory_ids=tuple(payload.get("include_memory_ids", ()) if isinstance(payload.get("include_memory_ids"), list) else ()),
                exclude_memory_ids=tuple(payload.get("exclude_memory_ids", ()) if isinstance(payload.get("exclude_memory_ids"), list) else ()),
                kinds=tuple(payload.get("kinds", ()) if isinstance(payload.get("kinds"), list) else ()),
            )

    def phase20_memory_import(self, payload: Mapping[str, object]) -> dict[str, object]:
        package = payload.get("package", payload)
        if not isinstance(package, Mapping):
            return {"error": "missing_package"}
        with self.lock:
            result = import_memory_package(self.phase20_session.chat.state, package)
            self.phase20_session.chat.state = result.state
            self.phase20_session.chat.store.save_state(result.state)
            return {"import": result.payload, "memory": list_memory_view(result.state, limit=80)}

    def phase20_memory_uninstall(self, payload: Mapping[str, object]) -> dict[str, object]:
        with self.lock:
            result = uninstall_memory_package(self.phase20_session.chat.state, str(payload.get("package_id", "")))
            self.phase20_session.chat.state = result.state
            self.phase20_session.chat.store.save_state(result.state)
            return {"uninstall": result.payload, "memory": list_memory_view(result.state, limit=80)}

    def phase20_memory_delete(self, payload: Mapping[str, object]) -> dict[str, object]:
        ids = payload.get("memory_ids", ())
        if not isinstance(ids, list):
            ids = ()
        with self.lock:
            result = delete_memories(self.phase20_session.chat.state, tuple(str(item) for item in ids))
            self.phase20_session.chat.state = result.state
            self.phase20_session.chat.store.save_state(result.state)
            return {"delete": result.payload, "memory": list_memory_view(result.state, limit=80)}

    def phase20_history_list(self, payload: Mapping[str, object] | None = None) -> dict[str, object]:
        payload = payload or {}
        with self.lock:
            return _phase20_history_list(
                self.phase20_session.chat.state,
                live_history=self._phase20_live_history,
                limit=_int_or_zero(payload.get("limit", 80)) or 80,
            )

    def phase20_history_replay(self, payload: Mapping[str, object]) -> dict[str, object]:
        with self.lock:
            return _phase20_history_replay(
                self.phase20_session.chat.state,
                payload,
                live_history=self._phase20_live_history,
            )

    def _remember_phase20_live_history(
        self,
        payload: Mapping[str, object],
        turn_payload: Mapping[str, object],
    ) -> None:
        rows = _rows(self.phase20_session.chat.state.get("phase20_turn_trace"))
        if not rows:
            return
        index = len(rows) - 1
        turn_id = _phase20_history_turn_id(index, rows[-1])
        self._phase20_live_history[turn_id] = {
            "user_text": str(payload.get("text", "") or ""),
            "media": dict(turn_payload.get("media", {})) if isinstance(turn_payload.get("media", {}), Mapping) else {},
        }

    def mode(self, payload: Mapping[str, object]) -> dict[str, object]:
        with self.lock:
            mode = self.phase20_session.chat.set_mode(str(payload.get("mode", "")))
            return {"mode": mode, "snapshot": snapshot_session(self.phase20_session.chat)}

    def snapshot(self) -> dict[str, object]:
        with self.lock:
            return snapshot_session(self.phase20_session.chat)

    def course_demos(self) -> dict[str, object]:
        return self.course_runtime.list_demos()

    def course_run(self, payload: Mapping[str, object]) -> dict[str, object]:
        return self.course_runtime.run_demo(str(payload.get("demo_id", "demo_color_yellow")))

    def import_styled_seeds(self) -> dict[str, object]:
        from apv3test.runtime.phase20_7.runtime import import_styled_paradigm_seeds
        with self.lock:
            return import_styled_paradigm_seeds(PHASE20_7_DB_PATH)

    def phase20_7_paradigm_demonstrate(self, payload: Mapping[str, object]) -> dict[str, object]:
        """过程范式示范教学接口 (修复 R1: 让 teach_process_paradigm_demonstration 真有 HTTP 入口).

        红线: 教师演示是 teacher_knowledge (课程层), 不是学生侧 LLM 答案表 — 教师对
        具体例子 (如 "61+22=83") 给出完整 action 序列, 共享感知函数 perceive_process_state
        对每步现场的状态命名, 落库为 action_sequence_cooccurrence (与执行/自发同表同事件).
        AP 自己不直接读教师给出的序列; 它读的是示范现场被共享感知函数标注后的共现,
        与自发偶现被奖励累积出的范式键同空间 (§173.5 熟练涌现).
        """
        from apv3test.runtime.phase20_7.runtime import teach_process_paradigm_demonstration
        example = str(payload.get("example", "61+22=83") or "61+22=83")
        repeats = int(payload.get("repeats", 3) or 3)
        session_id = str(payload.get("session_id", "phase20_7_workbench") or "phase20_7_workbench")
        with self.lock:
            return teach_process_paradigm_demonstration(
                PHASE20_7_DB_PATH,
                session_id=session_id,
                example=example,
                repeats=repeats,
            )

    def load_starter_pack(self) -> dict[str, object]:
        from scripts.build_starter_pack import build_starter_pack
        with self.lock:
            return build_starter_pack(PHASE20_7_DB_PATH)

    def course_asset_path(self, asset_id: str) -> Path:
        return self.course_runtime.asset_path_for_id(asset_id)

    # --- Phase20.7 记忆包 (§34.3/§39): 预览筛选/导出/导入/列表/卸载 ---
    def phase20_7_package_preview(self, payload: Mapping[str, object]) -> dict[str, object]:
        from apv3test.runtime.phase20_7.memory_packages import preview_package_entries
        with self.lock:
            return preview_package_entries(
                PHASE20_7_DB_PATH,
                session_id=str(payload.get("session_id", "") or "") or None,
                keyword=str(payload.get("keyword", "") or ""),
                since_ms=int(payload.get("since_ms", 0) or 0),
                until_ms=int(payload.get("until_ms", 0) or 0),
                limit=min(500, int(payload.get("limit", 200) or 200)),
                offset=max(0, int(payload.get("offset", 0) or 0)),
            )

    def phase20_7_package_export(self, payload: Mapping[str, object]) -> dict[str, object]:
        from apv3test.runtime.phase20_7.memory_packages import export_package
        event_ids = payload.get("event_ids")
        if not isinstance(event_ids, Sequence) or isinstance(event_ids, (str, bytes)):
            return {"error": "event_ids_required"}
        with self.lock:
            return export_package(
                PHASE20_7_DB_PATH,
                event_ids=[str(e) for e in event_ids],
                package_name=str(payload.get("package_name", "memory_package") or "memory_package"),
            )

    def phase20_7_package_import(self, payload: Mapping[str, object]) -> dict[str, object]:
        from apv3test.runtime.phase20_7.memory_packages import import_package
        package = payload.get("package")
        if not isinstance(package, Mapping):
            return {"error": "package_required"}
        with self.lock:
            return import_package(
                PHASE20_7_DB_PATH,
                package,
                session_id=str(payload.get("session_id", "phase20_7_workbench") or "phase20_7_workbench"),
            )

    def phase20_7_package_batches(self, payload: Mapping[str, object] | None = None) -> dict[str, object]:
        from apv3test.runtime.phase20_7.memory_packages import list_import_batches
        with self.lock:
            return {"batches": list_import_batches(PHASE20_7_DB_PATH)}

    def phase20_7_package_uninstall(self, payload: Mapping[str, object]) -> dict[str, object]:
        from apv3test.runtime.phase20_7.memory_packages import uninstall_import_batch
        batch_id = str(payload.get("import_batch_id", "") or "")
        if not batch_id:
            return {"error": "import_batch_id_required"}
        with self.lock:
            return uninstall_import_batch(PHASE20_7_DB_PATH, import_batch_id=batch_id)

    def phase20_7_progress(self, payload: Mapping[str, object] | None = None) -> dict[str, object]:
        """turn 进行中的实时阶段透视 (内存回调, 无锁无 DB 读).

        前端在等待 turn 响应期间轮询此接口, 显示 AP 当前在做什么.
        数据来源: _append_runtime_tick 的 live_progress_hook 每 tick 写入
        self._phase20_live_progress[session_id], 无需等事务提交.
        fallback: 无 hook 数据时读已提交 action_records (turn 结束后).
        """
        payload = payload or {}
        session_id = str(payload.get("session_id", "phase20_7_workbench") or "phase20_7_workbench")
        stage_labels = {
            "observe_text": "观察输入",
            "move_focus": "移动视线看图",
            "maintain_focus": "凝视细节",
            "visual_imagination_recall": "回忆画面",
            "request_teacher": "想要请教",
            "maintain_unclosed": "惦记未解的问题",
            "integrate_feedback": "消化教师反馈",
            "write_cell": "逐字写草稿",
            "continue_writing": "继续写",
            "read_draft": "回读草稿",
            "edit_cell": "修改草稿",
            "stop_generating": "停笔思考",
            "commit_reply": "决定发出回复",
            "reply_tts_audio": "准备朗读",
            "idle_think": "发呆想事情",
            "idle_observe": "静静观察",
            "outward_speech": "主动开口",
        }
        # 优先从内存 hook 读 (turn 进行中事务未提交也可见)
        live = self._phase20_live_progress.get(session_id)
        if live:
            action = str(live.get("action_type") or "")
            tick_n = int(live.get("tick") or 0)
            recent = live.get("recent_actions")
            if isinstance(recent, list):
                recent_out = [
                    {"tick": int(r.get("tick", 0)), "action_type": str(r.get("action_type", "")),
                     "label": stage_labels.get(str(r.get("action_type", "")), str(r.get("action_type", "")))}
                    for r in recent[-5:]
                ]
            else:
                recent_out = [{"tick": tick_n, "action_type": action, "label": stage_labels.get(action, action)}]
            return {
                "schema_id": "apv3_phase20_7_live_progress/v1",
                "tick": tick_n,
                "action_type": action,
                "stage_label": stage_labels.get(action, action or "准备中"),
                "recent_actions": recent_out,
            }
        # fallback: turn 已结束, 从已提交的 action_records 读
        try:
            with sqlite3.connect(PHASE20_7_DB_PATH) as conn:
                rows = conn.execute(
                    "SELECT tick, action_type FROM phase20_7_action_records "
                    "WHERE session_id=? ORDER BY tick DESC, created_at_ms DESC LIMIT 5",
                    (session_id,),
                ).fetchall()
        except sqlite3.Error:
            rows = []
        latest = rows[0] if rows else None
        action = str(latest[1]) if latest else ""
        return {
            "schema_id": "apv3_phase20_7_live_progress/v1",
            "tick": int(latest[0]) if latest else 0,
            "action_type": action,
            "stage_label": stage_labels.get(action, action or "准备中"),
            "recent_actions": [
                {"tick": int(t), "action_type": str(a), "label": stage_labels.get(str(a), str(a))}
                for t, a in rows
            ],
        }


def _inner_picture_urls_from_turn(result: Any) -> list[dict[str, object]]:
    """收集 turn 内产出的内心画面 PNG (§16.4 想象/重建渲染) 为前端可显 URL 列表.

    只读 tick trace 既有 visual_inner_picture 字段; 只暴露从状态池 canvas 渲染的
    图 (rendered_from_state_pool_canvas=True 且 raw_source_asset_used_for_render=False
    — 红线 C30: 原图缩略图不许当内心画面).
    """
    out: list[dict[str, object]] = []
    seen: set[str] = set()
    for event in getattr(result, "tick_trace", ()) or ():
        vip = getattr(event, "visual_inner_picture", None)
        if not isinstance(vip, Mapping):
            continue
        if not vip.get("rendered_from_state_pool_canvas"):
            continue
        if vip.get("raw_source_asset_used_for_render"):
            continue
        if str(vip.get("source") or "") == "ap_paint_board_step":
            continue  # 中间态只进详情页回放 (tick trace), 不进气泡
        source = str(vip.get("source") or "")
        # 气泡纪律 (用户 2026-07-04 实测批评"每次回复都配 clarity 0 的图"):
        # 1. 画作 (ap_paint_board_commit) 永远发 — AP 主动交付的产物;
        # 2. 想象画面 (visual_imagination_recall) 发 — 它只在语义重叠>=0.34 的真实
        #    召回时触发, 本身就稀疏; clarity_coverage 是"高清晰像素占比", 大画布上
        #    想象天然很低 (0.006), 不能作门槛;
        # 3. 看图过程的逐焦点重建 (sensory_canvas_patch_payload) 一律不进气泡 —
        #    那是"它正在看"的过程视图 (每图 3 张 · 正是刷屏来源), 属于详情页.
        if source not in {"ap_paint_board_commit", "visual_imagination_recall"}:
            continue
        raw_path = str(vip.get("path") or "")
        if not raw_path or raw_path in seen:
            continue
        seen.add(raw_path)
        try:
            resolved = _resolve_local_media_path(raw_path)
        except (FileNotFoundError, ValueError):
            continue
        out.append(
            {
                "url": _phase20_media_url(resolved),
                "tick": int(getattr(event, "tick", 0) or 0),
                "action_type": str((getattr(event, "selected_action", {}) or {}).get("action_type") or ""),
                "source": str(vip.get("source") or ""),
                "clarity_coverage": float(vip.get("clarity_coverage") or 0.0),
            }
        )
    return out[:6]


def _idle_pacing_from_emotion(emotion: Mapping[str, Any] | None) -> dict[str, object]:
    """M4-2 (§187.3): 连续心智的自适应节奏 — interval = f(arousal, fatigue), 界 2s~30s.

    只调"心跳"快慢(下一个 idle tick 的建议间隔), 不触发任何主动行为(红线:
    说话与否由 runtime 张力/经验竞争决定). 情绪高涨/好奇→活跃; 疲劳/低落→安静.
    """
    arousal = 0.0
    fatigue = 0.0
    curiosity = 0.0
    if isinstance(emotion, Mapping):
        try:
            arousal = max(0.0, min(1.0, float(emotion.get("arousal", 0.0) or 0.0)))
            fatigue = max(0.0, min(1.0, float(emotion.get("fatigue_tone", 0.0) or 0.0)))
            curiosity = max(0.0, min(1.0, float(emotion.get("curiosity_tone", 0.0) or 0.0)))
        except (TypeError, ValueError):
            pass
    activity = max(arousal, curiosity * 0.8) * (1.0 - fatigue * 0.6)
    interval_s = round(30.0 - activity * 28.0, 1)  # activity 0→30s, 1→2s
    return {
        "formula_id": "apv3_m4_2_idle_pacing_from_emotion/v1",
        "interval_seconds": max(2.0, min(30.0, interval_s)),
        "arousal": round(arousal, 4),
        "fatigue_tone": round(fatigue, 4),
        "curiosity_tone": round(curiosity, 4),
        "triggers_action": False,
        "source": "emotion_slow_channel_pacing_only",
    }


def snapshot_session(session: APV3MinimalistChatSession) -> dict[str, object]:
    state = session.state
    chat_trace = _rows(state.get("chat_session_trace"))
    runtime_trace = _rows(state.get("minimalist_dialogue_trace"))
    phase20_trace = _rows(state.get("phase20_turn_trace"))
    feelings = _rows(state.get("introspection_feelings"))
    memory = _phrase_memory(session)
    assoc = CooccurrenceAssociationStore.from_state(state.get("cooccurrence_associations"))
    top = [
        {
            "phrase_id": item.phrase_id,
            "text": item.text,
            "tokens": list(item.tokens),
            "support": item.support,
        }
        for item in session.top_phrases(top_k=8)
    ]
    fallback_count = sum(1 for row in chat_trace if row.get("used_honest_fallback"))
    learned_count = sum(1 for row in chat_trace if row.get("learned_phrase_id"))
    unique_feelings = sorted({str(row.get("feeling_label", "")) for row in chat_trace if row.get("feeling_label")})
    payload = {
        "schema_id": "apv3_web_chat_snapshot/v1",
        "tick": session.tick,
        "mode": session.mode,
        "db_path": str(session.store.db_path),
        "top_phrases": top,
        "chat_trace": chat_trace[-160:],
        "runtime_trace": runtime_trace[-160:],
        "phase20_turn_trace": phase20_trace[-80:],
        "phase20_last_teaching_trace": dict(state.get("phase20_last_teaching_trace", {}))
        if isinstance(state.get("phase20_last_teaching_trace"), Mapping)
        else {},
        "feelings": feelings[-80:],
        "metrics": {
            "phrase_records": len(memory.records),
            "association_pairs": len(assoc.pairs),
            "paradigm_pairs": len(assoc.paradigm_pairs),
            "fallback_count": fallback_count,
            "learned_count": learned_count,
            "unique_feeling_count": len(unique_feelings),
        },
        "chart": _chart_rows(chat_trace, runtime_trace),
        "audit": {
            "latest_chat": chat_trace[-1] if chat_trace else {},
            "latest_runtime": runtime_trace[-1] if runtime_trace else {},
            "latest_feeling": feelings[-1] if feelings else {},
            "unique_feelings": unique_feelings,
        },
        "phase8_audit": _phase8_audit_payload(chat_trace, feelings),
        "phase20_6_memory": _phase20_6_memory_payload(state),
    }
    payload["phase12_demo"] = build_demo_audit_snapshot(payload)
    return payload


def _phase20_6_memory_payload(state: Mapping[str, object]) -> dict[str, object]:
    fast = state.get("phase20_6_fast_action_chains")
    slow = state.get("phase20_6_slow_memory")
    carry = state.get("phase20_6_unresolved_carry")
    tick_mem = state.get("phase20_6_tick_memories")
    fast_rows = list(fast.get("chains", [])) if isinstance(fast, Mapping) and isinstance(fast.get("chains"), list) else []
    slow_rows = list(slow.get("memories", [])) if isinstance(slow, Mapping) and isinstance(slow.get("memories"), list) else []
    carry_rows = list(carry) if isinstance(carry, list) else []
    tick_rows = list(tick_mem.get("memories", [])) if isinstance(tick_mem, Mapping) and isinstance(tick_mem.get("memories"), list) else []
    fast_tick_rows = [dict(row) for row in tick_rows if isinstance(row, Mapping) and row.get("memory_tier") == "fast"]
    slow_tick_rows = [dict(row) for row in tick_rows if isinstance(row, Mapping) and row.get("memory_tier") == "slow"]
    return {
        "schema_id": "apv3_phase20_6_memory_snapshot/v1",
        "fast_schema_id": str(fast.get("schema_id", "")) if isinstance(fast, Mapping) else "",
        "slow_schema_id": str(slow.get("schema_id", "")) if isinstance(slow, Mapping) else "",
        "fast_count": len(fast_rows),
        "slow_count": len(slow_rows),
        "fast_tick_count": len(fast_tick_rows),
        "slow_tick_count": len(slow_tick_rows),
        "unresolved_count": len(carry_rows),
        "fast_top": [dict(item) for item in fast_rows[:12] if isinstance(item, Mapping)],
        "slow_top": [dict(item) for item in slow_rows[:12] if isinstance(item, Mapping)],
        "fast_tick_top": fast_tick_rows[:12],
        "slow_tick_top": slow_tick_rows[:12],
        "unresolved_top": [dict(item) for item in carry_rows[:6] if isinstance(item, Mapping)],
    }


def make_handler(app: APV3WebChatApp) -> type[BaseHTTPRequestHandler]:
    static_root = Path(__file__).resolve().parent / "web" / "static"

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/api/state":
                self._json(app.snapshot())
                return
            if parsed.path == "/api/phase20_7/progress":
                query = parse_qs(parsed.query)
                self._json(app.phase20_7_progress({"session_id": (query.get("session_id") or [""])[0]}))
                return
            if parsed.path == "/api/replay":
                query = parse_qs(parsed.query)
                tick = _int_or_zero(query.get("tick", ["0"])[0])
                self._json(_replay_payload(app.snapshot(), tick))
                return
            if parsed.path == "/api/course/demos":
                self._json(app.course_demos())
                return
            if parsed.path.startswith("/api/course/assets/"):
                asset_id = unquote(parsed.path.removeprefix("/api/course/assets/"))
                self._asset(asset_id)
                return
            if parsed.path == "/api/phase20/media":
                query = parse_qs(parsed.query)
                self._local_media(query.get("path", [""])[0])
                return
            if parsed.path in {"/phase20_7", "/phase20_7/"}:
                path = "phase20_7_workbench.html"
            else:
                path = "phase20_6_workbench.html" if parsed.path in {"/", ""} else parsed.path.lstrip("/")
            self._static(static_root / path)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            payload = self._payload()
            if parsed.path == "/api/message":
                self._json(app.send(payload))
                return
            if parsed.path == "/api/feedback":
                self._json(app.feedback(payload))
                return
            if parsed.path == "/api/phase20/turn":
                self._json(app.phase20_turn(payload))
                return
            if parsed.path == "/api/phase20/teach":
                self._json(app.phase20_teach(payload))
                return
            if parsed.path == "/api/phase20_7/turn":
                self._json(app.phase20_7_turn(payload))
                return
            if parsed.path == "/api/phase20_7/package/preview":
                self._json(app.phase20_7_package_preview(payload))
                return
            if parsed.path == "/api/phase20_7/package/export":
                self._json(app.phase20_7_package_export(payload))
                return
            if parsed.path == "/api/phase20_7/package/import":
                self._json(app.phase20_7_package_import(payload))
                return
            if parsed.path == "/api/phase20_7/package/batches":
                self._json(app.phase20_7_package_batches(payload))
                return
            if parsed.path == "/api/phase20_7/package/uninstall":
                self._json(app.phase20_7_package_uninstall(payload))
                return
            if parsed.path == "/api/phase20_7/import_seeds":
                self._json(app.import_styled_seeds())
                return
            if parsed.path == "/api/phase20_7/paradigm_demonstrate":
                self._json(app.phase20_7_paradigm_demonstrate(payload))
                return
            if parsed.path == "/api/phase20_7/load_starter_pack":
                self._json(app.load_starter_pack())
                return
            if parsed.path == "/api/phase20_7/memory/list":
                self._json(app.phase20_7_memory_list(payload))
                return
            if parsed.path == "/api/phase20_7/memory/delete":
                self._json(app.phase20_7_memory_delete(payload))
                return
            if parsed.path == "/api/phase20_7/tts/synthesize":
                self._json(app.phase20_7_tts_synthesize(payload))
                return
            if parsed.path == "/api/phase20/media/upload":
                self._json(app.phase20_media_upload(payload))
                return
            if parsed.path == "/api/phase20/agent":
                self._json(app.phase20_agent(payload))
                return
            if parsed.path == "/api/phase20/memory/list":
                self._json(app.phase20_memory_list(payload))
                return
            if parsed.path == "/api/phase20/memory/export":
                self._json(app.phase20_memory_export(payload))
                return
            if parsed.path == "/api/phase20/memory/import":
                self._json(app.phase20_memory_import(payload))
                return
            if parsed.path == "/api/phase20/memory/uninstall":
                self._json(app.phase20_memory_uninstall(payload))
                return
            if parsed.path == "/api/phase20/memory/delete":
                self._json(app.phase20_memory_delete(payload))
                return
            if parsed.path == "/api/phase20/history/list":
                self._json(app.phase20_history_list(payload))
                return
            if parsed.path == "/api/phase20/history/replay":
                self._json(app.phase20_history_replay(payload))
                return
            if parsed.path == "/api/mode":
                self._json(app.mode(payload))
                return
            if parsed.path == "/api/course/run":
                self._json(app.course_run(payload))
                return
            self.send_error(HTTPStatus.NOT_FOUND, "not found")

        def log_message(self, format: str, *args: object) -> None:
            return

        def _payload(self) -> Mapping[str, object]:
            length = _int_or_zero(self.headers.get("Content-Length"))
            if length <= 0:
                return {}
            raw = self.rfile.read(length)
            try:
                value = json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                return {}
            return value if isinstance(value, Mapping) else {}

        def _json(self, payload: object) -> None:
            raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _static(self, path: Path) -> None:
            if not _is_child(path, static_root) or not path.exists() or not path.is_file():
                self.send_error(HTTPStatus.NOT_FOUND, "not found")
                return
            raw = path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _asset(self, asset_id: str) -> None:
            try:
                path = app.course_asset_path(asset_id)
            except (KeyError, ValueError):
                self.send_error(HTTPStatus.NOT_FOUND, "not found")
                return
            raw = path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

        def _local_media(self, value: str) -> None:
            try:
                path = _resolve_local_media_path(value)
            except (FileNotFoundError, ValueError):
                self.send_error(HTTPStatus.NOT_FOUND, "not found")
                return
            raw = path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", mimetypes.guess_type(path.name)[0] or "application/octet-stream")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)

    return Handler


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="APV3 local web chat")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--state-db", default=None)
    parser.add_argument("--open", action="store_true")
    args = parser.parse_args(argv)
    app = APV3WebChatApp(state_db_path=args.state_db)
    server = ThreadingHTTPServer((args.host, int(args.port)), make_handler(app))
    url = f"http://{args.host}:{int(args.port)}/phase20_7"
    if args.open:
        # webbrowser.open 在部分 Windows 环境会同步阻塞到浏览器进程退出/中断,
        # 导致 serve_forever 迟迟不启动 (bat 卡住需 Ctrl+C). 放到守护线程里,
        # 延迟 0.8s 等 server 先起.
        threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    print(url, flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


def _turn_payload(turn: object) -> dict[str, object]:
    return {
        "tick": int(getattr(turn, "tick")),
        "user_text": str(getattr(turn, "user_text")) if bool(getattr(turn, "user_text_persisted", False)) else None,
        "user_text_hash": str(getattr(turn, "user_text_hash", "")),
        "user_text_hash_display": str(getattr(turn, "user_text_hash", ""))[:16],
        "user_text_length": int(getattr(turn, "user_text_length", 0)),
        "user_text_persisted": bool(getattr(turn, "user_text_persisted", False)),
        "reply_text": str(getattr(turn, "reply_text")),
        "reply_tokens": list(getattr(turn, "reply_tokens")),
        "feeling_label": str(getattr(turn, "feeling_label")),
        "learned_phrase_id": str(getattr(turn, "learned_phrase_id")),
        "committed_phrase_id": str(getattr(turn, "committed_phrase_id")),
        "state_id": int(getattr(turn, "state_id")),
    }


def _phase20_turn_payload(turn: object, live_payload: Mapping[str, object] | None = None) -> dict[str, object]:
    styled = getattr(turn, "styled_response", None)
    feedback = getattr(turn, "feedback_trace", None)
    teaching = getattr(turn, "teaching_trace", None)
    metadata = dict(getattr(turn, "metadata", {}) or {})
    live_payload = live_payload or {}
    live_text = str(live_payload.get("text", "") or "")
    media_path = str(live_payload.get("media_path", "") or live_payload.get("image_path", "") or "")
    media_type = str(live_payload.get("media_type", "") or "")
    media_url = ""
    if media_path:
        try:
            media_url = _phase20_media_url(_resolve_local_media_path(media_path))
        except (FileNotFoundError, ValueError):
            media_url = ""
    return {
        "tick": int(getattr(turn, "tick")),
        "reply_text": str(getattr(turn, "reply_text")),
        "reply_tokens": list(getattr(turn, "reply_tokens")),
        "live_user_text": live_text,
        "live_user_text_persisted": False,
        "user_text_hash_display": str(getattr(turn, "user_text_hash", ""))[:16],
        "image_sha16": getattr(turn, "image_sha16"),
        "media": {
            "path": media_path,
            "url": media_url,
            "media_type": media_type or (mimetypes.guess_type(media_path)[0] or ""),
        },
        "object_files": [_phase20_object_payload(item) for item in getattr(turn, "object_files")],
        "feedback_trace": None if feedback is None else {
            "feedback_kind": feedback.feedback_kind,
            "target_object_index": feedback.target_object_index,
            "correction_total_outcome": feedback.correction_total_outcome,
            "eligibility": feedback.eligibility,
            "target_label": feedback.target_label,
            "explicit_label": feedback.explicit_label,
        },
        "teaching_trace": None if teaching is None else _teaching_trace_payload(teaching),
        "teaching_applied": bool(metadata.get("teaching_candidate_applied", False)),
        "teaching_id": str(metadata.get("teaching_id", "")),
        "context_signature": str(metadata.get("context_signature", "")),
        "sensor_actuator_context": dict(metadata.get("phase20_6_sensor_actuator_context", {}))
        if isinstance(metadata.get("phase20_6_sensor_actuator_context", {}), Mapping)
        else {},
        "styled": None if styled is None else {
            "entry_id": styled.entry_id,
            "paradigm_id": styled.paradigm_id,
            "source_path": styled.source_path,
        },
        "workbench_runtime": _phase20_workbench_runtime(turn, live_payload),
        "workbench_tick_trace": _phase20_workbench_tick_trace(turn, live_payload),
    }


def _phase20_object_payload(item: object) -> dict[str, object]:
    return {
        "candidate_id": str(getattr(item, "candidate_id")),
        "top_visible_label": str(getattr(item, "top_visible_label")),
        "top_concept_uuid": str(getattr(item, "top_concept_uuid")),
        "raw_confidence": float(getattr(item, "raw_confidence")),
        "decision_tier": str(getattr(item, "decision_tier")),
        "nearest_negative_margin": float(getattr(item, "nearest_negative_margin")),
        "tick_seen": int(getattr(item, "tick_seen")),
        "focus_xy": list(getattr(item, "focus_xy", ()) or ()),
        "bbox": list(getattr(item, "bbox", ()) or ()),
        "area_ratio": float(getattr(item, "area_ratio", 0.0)),
        "image_size": list(getattr(item, "image_size", ()) or ()),
        "dominant_color_hex": str(getattr(item, "dominant_color_hex", "#8aa7a0")),
        "shape_bucket": str(getattr(item, "shape_bucket", "unknown")),
        "visual_signature_ids": list(getattr(item, "visual_signature_ids", ()) or ()),
        "visual_receptor_sketch": dict(getattr(item, "visual_receptor_sketch", {}) or {}),
    }


def _phase20_teaching_payload(result: object) -> dict[str, object]:
    trace = getattr(result, "teaching_trace")
    metadata = dict(getattr(result, "metadata", {}) or {})
    return {
        "tick": int(getattr(result, "tick")),
        "trace": _teaching_trace_payload(trace),
        "candidate_support": float(metadata.get("candidate_support", 0.0)),
        "source_boundary": str(metadata.get("source_boundary", "")),
    }


def _teaching_trace_payload(trace: object) -> dict[str, object]:
    response_text = str(getattr(trace, "response_text"))
    return {
        "teaching_id": str(getattr(trace, "teaching_id")),
        "target_context_signature": str(getattr(trace, "target_context_signature")),
        "response_text": response_text,
        "response_tokens": list(getattr(trace, "response_tokens")),
        "reward_delta": float(getattr(trace, "reward_delta")),
        "previous_reply_punish_delta": float(getattr(trace, "previous_reply_punish_delta")),
        "previous_reply_hash": str(getattr(trace, "previous_reply_hash")),
        "rewarded_teaching": bool(getattr(trace, "rewarded_teaching")),
        "punished_previous": bool(getattr(trace, "punished_previous")),
        "source": str(getattr(trace, "source")),
        "ordinary_user_text_persisted": bool(getattr(trace, "ordinary_user_text_persisted")),
        "teaching_text_persisted": bool(getattr(trace, "teaching_text_persisted")),
        "ui_summary": f"纠正回答 \"{response_text}\" 已学习",
    }


def _phrase_memory(session: APV3MinimalistChatSession) -> ExpressionPhraseMemory:
    memory = ExpressionPhraseMemory.from_state(session.state.get("expression_phrase_memory"))
    if memory.records:
        return memory
    return ExpressionPhraseMemory.from_seed_corpus(session.profile.seed_corpus_path)


def _rows(value: object) -> list[dict[str, object]]:
    return [dict(item) for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


def _chart_rows(chat_trace: list[dict[str, object]], runtime_trace: list[dict[str, object]]) -> list[dict[str, object]]:
    runtime_by_tick = {int(row.get("tick", 0)): row for row in runtime_trace}
    rows = []
    learned_total = 0
    fallback_total = 0
    for row in chat_trace[-80:]:
        tick = int(row.get("tick", 0))
        learned_total += 1 if row.get("learned_phrase_id") else 0
        fallback_total += 1 if row.get("used_honest_fallback") else 0
        runtime = runtime_by_tick.get(tick, {})
        rows.append(
            {
                "tick": tick,
                "learned_total": learned_total,
                "fallback_total": fallback_total,
                "candidate_count": len(runtime.get("candidate_phrase_ids", []))
                if isinstance(runtime.get("candidate_phrase_ids"), list)
                else 0,
            }
        )
    return rows


def _replay_payload(snapshot: Mapping[str, object], tick: int) -> dict[str, object]:
    chat = next((row for row in snapshot.get("chat_trace", []) if int(row.get("tick", -1)) == tick), {})
    runtime = next((row for row in snapshot.get("runtime_trace", []) if int(row.get("tick", -1)) == tick), {})
    feeling = next((row for row in snapshot.get("feelings", []) if int(row.get("tick", -1)) == tick), {})
    return {"tick": tick, "chat": chat, "runtime": runtime, "feeling": feeling}


def _phase8_audit_payload(
    chat_trace: list[dict[str, object]],
    feelings: list[dict[str, object]],
) -> dict[str, object]:
    latest_chat = chat_trace[-1] if chat_trace else {}
    latest_feeling = feelings[-1] if feelings else {}
    item = StateItem(
        sa_id="web::latest_turn",
        family="control",
        label=str(
            latest_chat.get("presented_text")
            or latest_chat.get("user_text_hash")
            or latest_chat.get("user_text_length")
            or "idle"
        ),
        real_energy=1.0,
        virtual_energy=0.4,
        attention_energy=0.4,
        cognitive_pressure=0.3,
        fatigue=0.1,
        metadata={
            "low_grasp_score": 0.7 if latest_chat.get("used_honest_fallback") else 0.2,
            "candidate_entropy": 0.6,
            "prediction_mismatch": 0.4 if latest_chat.get("used_honest_fallback") else 0.1,
        },
    )
    item.gain_ledger.inject("external", 0.7 if int(latest_chat.get("incoming_query_count", 0) or 0) > 0 else 0.1)
    item.gain_ledger.inject("unfinished_pressure", 0.5 if latest_chat.get("used_honest_fallback") else 0.1)
    marker = MarkerEvent(
        tick=int(latest_chat.get("tick", 0) or 0),
        kind="PERCEIVED",
        target_sa_id=item.sa_id,
        real_energy=0.8,
    )
    feeling_snapshot = build_cognitive_feelings(item, (marker,))
    endogenous = step_endogenous_drive((item,), tick=int(latest_chat.get("tick", 0) or 0), idle_score=0.5)
    visual_item = StateItem(
        sa_id="vision::inner_stage::latest",
        family="percept",
        label="inner_stage",
        real_energy=0.5,
        attention_energy=0.4,
        cognitive_pressure=0.2,
        fatigue=0.1,
        channel_signature=("vision", "inner"),
    )
    overlay = visual_focus_overlay(propose_visual_focus_actions((visual_item,)))
    return {
        "ledger_pie": [
            {"source": source, "value": value}
            for source, value in item.gain_ledger.snapshot().items()
            if value > 0.0
        ],
        "feelings_display": feeling_snapshot.all_values(),
        "endogenous_chain": endogenous.injected_by_sa,
        "visual_focus_overlay": list(overlay),
        "latest_structural_feeling": latest_feeling,
    }


def _is_child(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _resolve_local_media_path(value: str | Path) -> Path:
    raw = str(value or "").strip()
    if not raw:
        raise FileNotFoundError("empty_media_path")
    path = Path(raw)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    resolved = path.resolve()
    if not _is_child(resolved, PROJECT_ROOT):
        raise ValueError("media_path_outside_project")
    if not resolved.exists() or not resolved.is_file():
        raise FileNotFoundError(raw)
    return resolved


def _phase20_media_url(path: Path) -> str:
    from urllib.parse import quote

    return f"/api/phase20/media?path={quote(str(path.resolve()), safe='')}"


def _phase20_7_media_inputs(payload: Mapping[str, object]) -> tuple[MediaInput, ...]:
    rows: list[MediaInput] = []
    image_path = str(payload.get("image_path", "") or "")
    audio_path = str(payload.get("audio_path", "") or "")
    if image_path:
        rows.append(MediaInput(media_type="image", path=image_path))
    if audio_path:
        rows.append(MediaInput(media_type="audio", path=audio_path))
    media_inputs = payload.get("media_inputs")
    if isinstance(media_inputs, Sequence) and not isinstance(media_inputs, (str, bytes, bytearray)):
        for item in media_inputs:
            if not isinstance(item, Mapping):
                continue
            media_type = str(item.get("media_type", "") or "")
            if media_type not in {"image", "audio", "canvas", "tool", "text"}:
                continue
            rows.append(
                MediaInput(
                    media_type=media_type,  # type: ignore[arg-type]
                    path=str(item.get("path", "") or "") or None,
                    payload_ref=str(item.get("payload_ref", "") or "") or None,
                    source_hash=str(item.get("source_hash", "") or "") or None,
                )
            )
    return tuple(rows)


def _safe_media_name(name: str) -> str:
    kept = [ch if ch.isalnum() or ch in {".", "_", "-"} else "_" for ch in str(name or "media")]
    return "".join(kept).strip("._") or "media.bin"


def _phase20_workbench_runtime(turn: object, payload: Mapping[str, object]) -> dict[str, object]:
    max_ticks = _bounded_int(payload.get("max_ticks"), default=8, minimum=4, maximum=24)
    idle_ticks = _bounded_int(payload.get("idle_ticks"), default=2, minimum=0, maximum=8)
    metadata = dict(getattr(turn, "metadata", {}) or {})
    events = _runtime_tick_events_from_turn(turn)
    commit_index = _first_draft_action_index(events, "commit")
    return {
        "schema_id": "apv3_phase20_5a_workbench_runtime/v1",
        "max_ticks_if_no_commit": max_ticks,
        "idle_ticks_after_commit": idle_ticks,
        "commit_tick_index": commit_index or min(len(events) or max_ticks, max_ticks),
        "committed": bool(str(getattr(turn, "reply_text", "") or "")),
        "event_count": len(events),
        "event_source": str(metadata.get("runtime_tick_event_source", "")) or "phase20_turn_loop",
        "is_projection": any(bool(item.get("is_projection", True)) for item in events) if events else True,
        "all_events_projection_free": bool(events) and all(not bool(item.get("is_projection", True)) for item in events),
        "boundary": "per_tick_ap_loop_snapshot_not_stage_pipeline" if events else "projection_warning_no_runtime_events",
    }


def _phase20_workbench_tick_trace(turn: object, payload: Mapping[str, object]) -> list[dict[str, object]]:
    runtime = _phase20_workbench_runtime(turn, payload)
    events = _runtime_tick_events_from_turn(turn)
    if not events:
        return [
            {
                "tick_index": 1,
                "runtime_tick": int(getattr(turn, "tick", 0)),
                "stage": "projection_warning",
                "title": "降级展示",
                "summary": "没有 RuntimeTickEvent，只能显示投影警告。",
                "detail": "Phase 20.5a 红线要求真实 event；正常实现不应进入此分支。",
                "is_projection": True,
                "state_pool_top12": [],
                "action_chosen": {},
                "actions_proposed": [],
                "energy_RAPF": [0.0, 0.0, 0.0, 0.0],
                "cognitive_pressure": 0.0,
                "unresolved_pressure": 0.0,
                "focus_xy": None,
                "inner_picture_state": None,
                "boundary": runtime["boundary"],
            }
        ]
    rows: list[dict[str, object]] = []
    for event in events[: int(runtime["max_ticks_if_no_commit"])]:
        rows.append(
            {
                "tick_index": int(event.get("tick_index", len(rows) + 1)),
                "runtime_tick": int(event.get("runtime_tick", getattr(turn, "tick", 0)) or 0),
                "stage": str(event.get("stage", "")),
                "title": str(event.get("title", "")),
                "summary": str(event.get("summary", "")),
                "detail": str(event.get("detail", "")),
                "is_projection": bool(event.get("is_projection", True)),
                "state_pool_top12": event.get("state_pool_top12", []),
                "action_chosen": event.get("action_chosen", {}),
                "actions_proposed": event.get("actions_proposed", []),
                "energy_RAPF": event.get("energy_RAPF", [0.0, 0.0, 0.0, 0.0]),
                "cognitive_pressure": event.get("cognitive_pressure", 0.0),
                "unresolved_pressure": event.get("unresolved_pressure", 0.0),
                "focus_xy": event.get("focus_xy"),
                "inner_picture_state": event.get("inner_picture_state"),
                "inner_audio_state": event.get("inner_audio_state"),
                "reply_tts_request": event.get("reply_tts_request", {}),
                "sensor_actuator_context": dict(event.get("draft_changes", {})).get("sensor_actuator_context", {}),
                "recall_candidates": event.get("recall_candidates", []),
                "action_competition": event.get("action_competition", {}),
                "draft_grid_snapshot": event.get("draft_grid_snapshot", {}),
                "thought_cloud_items": event.get("thought_cloud_items", []),
                "boundary": runtime["boundary"],
                "draft_snapshot": event.get("draft_changes", {}),
                "audit_metrics": dict(event.get("draft_changes", {})).get("audit_metrics", {}),
            }
        )
    return rows


def _phase20_workbench_tick_trace_from_events(
    events: Sequence[Mapping[str, object]],
    *,
    base_tick: int,
    max_ticks: int | None = None,
) -> list[dict[str, object]]:
    event_rows = [dict(item) for item in events if isinstance(item, Mapping)]
    if not event_rows:
        return [
            {
                "tick_index": 1,
                "runtime_tick": int(base_tick),
                "stage": "stored_trace_warning",
                "title": "无可回放 RuntimeTickEvent",
                "summary": "这条历史 turn 没有保存 RuntimeTickEvent，工作台不会补编流程。",
                "detail": "只能查看 turn 摘要；请选择 Phase20.6 之后产生的 turn 做逐 tick 回放。",
                "is_projection": True,
                "state_pool_top12": [],
                "action_chosen": {},
                "actions_proposed": [],
                "energy_RAPF": [0.0, 0.0, 0.0, 0.0],
                "cognitive_pressure": 0.0,
                "unresolved_pressure": 0.0,
                "focus_xy": None,
                "inner_picture_state": None,
                "boundary": "stored_trace_missing_runtime_events",
                "replay_source": "stored_phase20_turn_trace",
            }
        ]
    runtime = {
        "boundary": "stored_runtime_tick_events_replay",
        "max_ticks_if_no_commit": max_ticks or len(event_rows),
    }
    rows: list[dict[str, object]] = []
    for event in event_rows[: int(runtime["max_ticks_if_no_commit"])]:
        rows.append(
            {
                "tick_index": int(event.get("tick_index", len(rows) + 1)),
                "runtime_tick": int(event.get("runtime_tick", base_tick) or 0),
                "stage": str(event.get("stage", "")),
                "title": str(event.get("title", "")),
                "summary": str(event.get("summary", "")),
                "detail": str(event.get("detail", "")),
                "is_projection": bool(event.get("is_projection", True)),
                "source": str(event.get("source", "")),
                "state_pool_top12": event.get("state_pool_top12", []),
                "action_chosen": event.get("action_chosen", {}),
                "actions_proposed": event.get("actions_proposed", []),
                "energy_RAPF": event.get("energy_RAPF", [0.0, 0.0, 0.0, 0.0]),
                "cognitive_pressure": event.get("cognitive_pressure", 0.0),
                "unresolved_pressure": event.get("unresolved_pressure", 0.0),
                "focus_xy": event.get("focus_xy"),
                "inner_picture_state": event.get("inner_picture_state"),
                "inner_audio_state": event.get("inner_audio_state"),
                "reply_tts_request": event.get("reply_tts_request", {}),
                "sensor_actuator_context": dict(event.get("draft_changes", {})).get("sensor_actuator_context", {}),
                "recall_candidates": event.get("recall_candidates", []),
                "action_competition": event.get("action_competition", {}),
                "draft_grid_snapshot": event.get("draft_grid_snapshot", {}),
                "thought_cloud_items": event.get("thought_cloud_items", []),
                "boundary": runtime["boundary"],
                "draft_snapshot": event.get("draft_changes", {}),
                "audit_metrics": dict(event.get("draft_changes", {})).get("audit_metrics", {}),
                "replay_source": "stored_runtime_tick_events",
            }
        )
    return rows


def _phase20_history_list(
    state: Mapping[str, object],
    *,
    live_history: Mapping[str, Mapping[str, object]] | None = None,
    limit: int = 80,
) -> dict[str, object]:
    rows = _rows(state.get("phase20_turn_trace"))
    live_history = live_history or {}
    items = []
    for index, row in enumerate(rows):
        events = row.get("runtime_tick_events", [])
        event_count = len(events) if isinstance(events, list) else 0
        turn_id = _phase20_history_turn_id(index, row)
        live = live_history.get(turn_id, {})
        items.append(
            {
                "schema_id": "apv3_phase20_6_history_turn_summary/v1",
                "turn_id": turn_id,
                "trace_index": index,
                "tick": int(row.get("tick", 0) or 0),
                "user_text": str(live.get("user_text", "") or ""),
                "user_text_hash_display": str(row.get("user_text_hash", ""))[:16],
                "user_text_length": int(row.get("user_text_length", 0) or 0),
                "reply_text": str(row.get("reply_text", "") or ""),
                "image_sha16": row.get("image_sha16"),
                "object_count": len(row.get("object_files", [])) if isinstance(row.get("object_files"), list) else 0,
                "runtime_event_count": event_count,
                "has_runtime_tick_events": event_count > 0,
                "teaching_candidate_applied": bool(row.get("teaching_candidate_applied", False)),
                "teaching_id": str(row.get("teaching_id", "") or ""),
            }
        )
    return {
        "schema_id": "apv3_phase20_6_history_list/v1",
        "replay_policy": "read_stored_phase20_turn_trace_without_rerun",
        "turns": list(reversed(items))[: max(0, int(limit))],
        "total_turns": len(items),
    }


def _phase20_history_replay(
    state: Mapping[str, object],
    payload: Mapping[str, object],
    *,
    live_history: Mapping[str, Mapping[str, object]] | None = None,
) -> dict[str, object]:
    rows = _rows(state.get("phase20_turn_trace"))
    live_history = live_history or {}
    target = str(payload.get("turn_id", "") or "")
    trace_index = _optional_history_index(payload.get("trace_index"))
    selected_index = -1
    selected: dict[str, object] | None = None
    if target:
        for index, row in enumerate(rows):
            if _phase20_history_turn_id(index, row) == target:
                selected_index = index
                selected = row
                break
    elif trace_index is not None and 0 <= trace_index < len(rows):
        selected_index = trace_index
        selected = rows[trace_index]
    if selected is None:
        return {
            "schema_id": "apv3_phase20_6_history_replay/v1",
            "error": "history_turn_not_found",
            "mutated_state": False,
            "replay_source": "stored_phase20_turn_trace",
        }
    events = selected.get("runtime_tick_events", [])
    if not isinstance(events, list):
        events = []
    workbench = _phase20_workbench_tick_trace_from_events(
        tuple(dict(item) for item in events if isinstance(item, Mapping)),
        base_tick=int(selected.get("tick", 0) or 0),
    )
    turn_id = _phase20_history_turn_id(selected_index, selected)
    live = live_history.get(turn_id, {})
    return {
        "schema_id": "apv3_phase20_6_history_replay/v1",
        "replay_policy": "read_only_no_runtime_rerun",
        "mutated_state": False,
        "replay_source": "stored_runtime_tick_events" if events else "stored_trace_missing_runtime_events",
        "turn": {
            "turn_id": turn_id,
            "trace_index": selected_index,
            "tick": int(selected.get("tick", 0) or 0),
            "live_user_text": str(live.get("user_text", "") or ""),
            "user_text_hash_display": str(selected.get("user_text_hash", ""))[:16],
            "user_text_length": int(selected.get("user_text_length", 0) or 0),
            "reply_text": str(selected.get("reply_text", "") or ""),
            "image_sha16": selected.get("image_sha16"),
            "media": _phase20_history_media_payload(live.get("media", {})),
                "object_files": list(selected.get("object_files", [])) if isinstance(selected.get("object_files"), list) else [],
            "context_signature": str(selected.get("context_signature", "") or ""),
            "teaching_applied": bool(selected.get("teaching_candidate_applied", False)),
            "teaching_id": str(selected.get("teaching_id", "") or ""),
            "workbench_runtime": {
                "schema_id": "apv3_phase20_6_history_workbench_runtime/v1",
                "event_count": len(events),
                "is_projection": any(bool(item.get("is_projection", True)) for item in events if isinstance(item, Mapping)) if events else True,
                "all_events_projection_free": bool(events) and all(not bool(item.get("is_projection", True)) for item in events if isinstance(item, Mapping)),
                "boundary": "stored_runtime_tick_events_replay" if events else "stored_trace_missing_runtime_events",
            },
            "workbench_tick_trace": workbench,
        },
    }


def _phase20_history_turn_id(index: int, row: Mapping[str, object]) -> str:
    basis = f"{int(row.get('tick', 0) or 0)}|{row.get('user_text_hash', '')}|{row.get('reply_text_hash', '')}|{index}"
    return f"phase20hist::{_sha16(basis)}"


def _phase20_history_media_payload(value: object) -> dict[str, object]:
    media = dict(value) if isinstance(value, Mapping) else {}
    path = str(media.get("path", "") or "")
    url = ""
    if path:
        try:
            url = _phase20_media_url(_resolve_local_media_path(path))
        except (FileNotFoundError, ValueError):
            url = ""
    return {
        "path": path,
        "url": url,
        "media_type": str(media.get("media_type", "") or (mimetypes.guess_type(path)[0] or "")),
        "media_source": str(media.get("media_source", "") or ""),
    }


def _optional_history_index(value: object) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _runtime_tick_events_from_turn(turn: object) -> list[dict[str, object]]:
    metadata = dict(getattr(turn, "metadata", {}) or {})
    rows = metadata.get("runtime_tick_events", ())
    if not isinstance(rows, Sequence):
        return []
    return [dict(item) for item in rows if isinstance(item, Mapping)]


def _first_event_index(events: Sequence[Mapping[str, object]], stage: str) -> int:
    for event in events:
        if str(event.get("stage", "")) == stage:
            return int(event.get("tick_index", 0) or 0)
    return 0


def _first_draft_action_index(events: Sequence[Mapping[str, object]], kind: str) -> int:
    for event in events:
        changes = event.get("draft_changes", {})
        if isinstance(changes, Mapping) and str(changes.get("draft_action_kind", "")) == kind:
            return int(event.get("tick_index", 0) or 0)
    return 0


def _bounded_int(value: object, *, default: int, minimum: int, maximum: int) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        number = int(default)
    return max(int(minimum), min(int(maximum), number))


def _sha16(value: object) -> str:
    raw = value if isinstance(value, bytes) else str(value).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()[:16]


def _int_or_zero(value: object) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
