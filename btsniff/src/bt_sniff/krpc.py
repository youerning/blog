"""Bencode codec and KRPC wire helpers.

Only what a Mainline DHT node needs: strings, ints, lists, dicts and the
26-byte node-info encoding.
"""

from __future__ import annotations

import socket
import struct

MAX_DEPTH = 32
MAX_ITEMS = 100_000


class BencodeError(ValueError):
    """Raised when a payload is not valid bencode."""


def bencode(value: object) -> bytes:
    out = bytearray()
    _encode(value, out, 0)
    return bytes(out)


def _encode(value: object, out: bytearray, depth: int) -> None:
    if depth > MAX_DEPTH:
        raise BencodeError("nesting too deep")

    if isinstance(value, bool):
        # bool is a subclass of int; DHT never uses booleans.
        raise BencodeError("bool is not bencode")

    if isinstance(value, int):
        out += b"i%de" % value
    elif isinstance(value, (bytes, bytearray, memoryview)):
        data = bytes(value)
        out += b"%d:" % len(data)
        out += data
    elif isinstance(value, str):
        data = value.encode("utf-8")
        out += b"%d:" % len(data)
        out += data
    elif isinstance(value, (list, tuple)):
        out += b"l"
        for item in value:
            _encode(item, out, depth + 1)
        out += b"e"
    elif isinstance(value, dict):
        pairs = []
        for key, item in value.items():
            if isinstance(key, str):
                key = key.encode("utf-8")
            elif not isinstance(key, (bytes, bytearray)):
                raise BencodeError(f"bad dict key type: {type(key)!r}")
            pairs.append((bytes(key), item))
        pairs.sort(key=lambda kv: kv[0])
        out += b"d"
        for key, item in pairs:
            _encode(key, out, depth + 1)
            _encode(item, out, depth + 1)
        out += b"e"
    else:
        raise BencodeError(f"cannot bencode {type(value)!r}")


def bdecode(data: bytes) -> object:
    value, offset = _decode(data, 0, 0)
    # Some clients append padding; ignore trailing bytes like libtorrent does.
    return value


def _decode(data: bytes, i: int, depth: int) -> tuple[object, int]:
    if depth > MAX_DEPTH:
        raise BencodeError("nesting too deep")
    if i >= len(data):
        raise BencodeError("unexpected end of data")

    marker = data[i : i + 1]

    if marker == b"i":
        end = data.find(b"e", i + 1)
        if end < 0:
            raise BencodeError("unterminated integer")
        raw = data[i + 1 : end]
        if not raw or raw == b"-" or raw.startswith(b"0") and len(raw) > 1:
            raise BencodeError("bad integer")
        if raw.startswith(b"-0"):
            raise BencodeError("bad integer")
        return int(raw), end + 1

    if marker == b"l":
        i += 1
        items = []
        while data[i : i + 1] != b"e":
            if i >= len(data):
                raise BencodeError("unterminated list")
            value, i = _decode(data, i, depth + 1)
            items.append(value)
            if len(items) > MAX_ITEMS:
                raise BencodeError("list too long")
        return items, i + 1

    if marker == b"d":
        i += 1
        result: dict[bytes, object] = {}
        while data[i : i + 1] != b"e":
            if i >= len(data):
                raise BencodeError("unterminated dict")
            key, i = _decode(data, i, depth + 1)
            if not isinstance(key, bytes):
                raise BencodeError("dict key must be bytes")
            value, i = _decode(data, i, depth + 1)
            result[key] = value
            if len(result) > MAX_ITEMS:
                raise BencodeError("dict too big")
        return result, i + 1

    if marker.isdigit():
        colon = data.find(b":", i)
        if colon < 0:
            raise BencodeError("unterminated string length")
        length = int(data[i:colon])
        start = colon + 1
        end = start + length
        if end > len(data):
            raise BencodeError("string exceeds payload")
        return data[start:end], end

    raise BencodeError(f"invalid marker {marker!r}")


def decode_nodes(blob: object) -> list[tuple[bytes, str, int]]:
    """Decode a compact node-info string (BEP 5) into (id, ip, port)."""
    if not isinstance(blob, (bytes, bytearray)):
        return []
    out: list[tuple[bytes, str, int]] = []
    for offset in range(0, len(blob) - 25, 26):
        node_id = bytes(blob[offset : offset + 20])
        ip = socket.inet_ntoa(bytes(blob[offset + 20 : offset + 24]))
        port = struct.unpack(">H", blob[offset + 24 : offset + 26])[0]
        if port:
            out.append((node_id, ip, port))
    return out


def encode_nodes(nodes: list[tuple[bytes, str, int]]) -> bytes:
    out = bytearray()
    for node_id, ip, port in nodes:
        try:
            out += node_id[:20].ljust(20, b"\0")
            out += socket.inet_aton(ip)
            out += struct.pack(">H", port)
        except (OSError, struct.error):
            continue
    return bytes(out)
