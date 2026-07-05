from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from pathlib import Path
from typing import Sequence


_CANONICAL_SCHEMA_VERSION = "apv3_pseudonymous_input/v1"
_DEFAULT_ID_LENGTH_CHARS = 32
_SALT_BYTES = 32
_SALT_FILENAME = "install_salt.bin"


def compute_pseudonymous_identifier(
    text_or_seq: str | Sequence[str],
    *,
    state_dir: str | Path = "state",
    length_chars: int = _DEFAULT_ID_LENGTH_CHARS,
) -> str:
    """Compute a local pseudonymous HMAC id for text-like input."""
    canonical = _canonicalize_input(text_or_seq)
    salt = get_or_create_install_salt(Path(state_dir))
    digest = hmac.new(salt, canonical.encode("utf-8"), hashlib.sha256).hexdigest()
    return digest[: max(1, int(length_chars))]


def get_or_create_install_salt(state_dir: str | Path) -> bytes:
    """Load or create the per-install salt used for local pseudonymous ids."""
    root = Path(state_dir)
    root.mkdir(parents=True, exist_ok=True)
    path = root / _SALT_FILENAME
    if path.exists():
        return path.read_bytes()
    salt = secrets.token_bytes(_SALT_BYTES)
    path.write_bytes(salt)
    return salt


def _canonicalize_input(text_or_seq: str | Sequence[str]) -> str:
    """Canonical JSON; tuple/list are equivalent, scalar str is distinct."""
    if isinstance(text_or_seq, str):
        normalized: dict[str, object] = {
            "kind": "scalar",
            "schema": _CANONICAL_SCHEMA_VERSION,
            "value": text_or_seq,
        }
    elif isinstance(text_or_seq, (tuple, list)):
        values: list[str] = []
        for item in text_or_seq:
            if not isinstance(item, str):
                raise TypeError(
                    "compute_pseudonymous_identifier expects str or a sequence "
                    f"of str, got sequence item {type(item).__name__}"
                )
            values.append(item)
        normalized = {
            "kind": "sequence",
            "schema": _CANONICAL_SCHEMA_VERSION,
            "values": values,
        }
    else:
        raise TypeError(
            "compute_pseudonymous_identifier expects str or sequence[str], "
            f"got {type(text_or_seq).__name__}"
        )
    return json.dumps(normalized, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


__all__ = [
    "compute_pseudonymous_identifier",
    "get_or_create_install_salt",
    "_canonicalize_input",
]
