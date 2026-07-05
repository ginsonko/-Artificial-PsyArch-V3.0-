from __future__ import annotations

import hashlib
import json
import zlib
from dataclasses import dataclass


def _canonical_json(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


@dataclass(frozen=True)
class RuntimeStateCodec:
    codec: str = "zlib"

    def encode(self, payload: dict) -> dict:
        raw = _canonical_json(payload)
        if self.codec == "zlib":
            stored = zlib.compress(raw, level=6)
        elif self.codec in {"", "plain"}:
            stored = raw
        else:
            raise ValueError(f"unsupported codec: {self.codec}")
        return {
            "codec": self.codec,
            "raw_bytes": len(raw),
            "stored_bytes": len(stored),
            "sha256": hashlib.sha256(raw).hexdigest(),
            "blob": stored,
        }

    def decode(self, envelope: dict) -> dict:
        blob = bytes(envelope.get("blob", b""))
        codec = str(envelope.get("codec", self.codec) or "")
        if codec == "zlib":
            raw = zlib.decompress(blob)
        elif codec in {"", "plain"}:
            raw = blob
        else:
            raise ValueError(f"unsupported codec: {codec}")
        digest = hashlib.sha256(raw).hexdigest()
        expected = str(envelope.get("sha256", "") or "")
        if expected and digest != expected:
            raise ValueError("runtime state digest mismatch")
        value = json.loads(raw.decode("utf-8"))
        if not isinstance(value, dict):
            raise ValueError("runtime state must decode to a dict")
        return value

