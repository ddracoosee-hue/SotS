"""Unique id helper: `<prefix>_<ulid>` (03_DATA_MODELS)."""

from __future__ import annotations

import os
import threading
import time

_CROCKFORD = "0123456789ABCDEFGHJKMNPQRSTVWXYZ"
_TS_MASK = (1 << 48) - 1
_RAND_MASK = (1 << 80) - 1

_lock = threading.Lock()
_last_ts_ms = 0
_last_rand = 0


def _encode_ulid(ts_ms: int, rand: int) -> str:
    value = (ts_ms << 80) | rand
    chars = []
    for i in range(26):
        shift = 5 * (25 - i)
        chars.append(_CROCKFORD[(value >> shift) & 31])
    return "".join(chars)


def _ulid() -> str:
    """Monotonic ULID: 48-bit ms timestamp + 80-bit randomness (Crockford base32)."""
    global _last_ts_ms, _last_rand
    with _lock:
        ts_ms = int(time.time() * 1000) & _TS_MASK
        if ts_ms <= _last_ts_ms:
            ts_ms = _last_ts_ms
            rand = (_last_rand + 1) & _RAND_MASK
            if rand == 0:  # randomness overflow within the same ms: tick forward
                ts_ms = (ts_ms + 1) & _TS_MASK
        else:
            rand = int.from_bytes(os.urandom(10), "big")
        _last_ts_ms = ts_ms
        _last_rand = rand
        return _encode_ulid(ts_ms, rand)


def new_id(prefix: str) -> str:
    """Return a new `<prefix>_<ulid>` id, unique and lexicographically time-sortable."""
    return f"{prefix}_{_ulid()}"
