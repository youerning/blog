"""SQLite storage for harvested torrents and the candidate queue."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS torrents (
    infohash     TEXT PRIMARY KEY,
    name         TEXT NOT NULL,
    total_size   INTEGER NOT NULL,
    file_count   INTEGER NOT NULL,
    files        TEXT NOT NULL,
    info_dict    BLOB NOT NULL,
    ext          TEXT,
    peers        INTEGER NOT NULL DEFAULT 0,
    source       TEXT,
    first_seen   INTEGER NOT NULL,
    harvested_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_torrents_size ON torrents(total_size);
CREATE INDEX IF NOT EXISTS idx_torrents_time ON torrents(harvested_at);
CREATE INDEX IF NOT EXISTS idx_torrents_ext  ON torrents(ext);

CREATE TABLE IF NOT EXISTS candidates (
    infohash  TEXT PRIMARY KEY,
    source    TEXT,
    state     TEXT NOT NULL DEFAULT 'pending',
    attempts  INTEGER NOT NULL DEFAULT 0,
    peers     TEXT,
    seen_at   INTEGER NOT NULL,
    next_try  INTEGER NOT NULL DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_candidates_state ON candidates(state, next_try);

CREATE TABLE IF NOT EXISTS meta (
    k TEXT PRIMARY KEY,
    v TEXT
);
"""


class Store:
    def __init__(self, path: str) -> None:
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, timeout=30)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.execute("PRAGMA busy_timeout=30000")
        self.conn.executescript(SCHEMA)
        self.conn.commit()
        self._buffer: dict[str, tuple[str, str | None]] = {}
        # A crash can leave rows stuck in transient states; requeue them.
        self.conn.execute("UPDATE candidates SET state='pending' WHERE state IN ('lookup', 'harvesting')")
        self.conn.commit()

    def close(self) -> None:
        self.flush()
        self.conn.close()

    # -- candidates --------------------------------------------------------

    def add_candidate(self, infohash: str, source: str, peer: str | None = None) -> None:
        if len(infohash) != 40:
            return
        previous = self._buffer.get(infohash)
        if previous is None:
            self._buffer[infohash] = (source, peer)
        elif previous[1] is None and peer is not None:
            self._buffer[infohash] = (previous[0], peer)
        if len(self._buffer) >= 500:
            self.flush()

    def flush(self) -> int:
        if not self._buffer:
            return 0
        buffered = self._buffer
        self._buffer = {}
        now = int(time.time())
        rows = [(infohash, source, now) for infohash, (source, _) in buffered.items()]
        with_peers = [
            (json.dumps([peer]), infohash)
            for infohash, (_, peer) in buffered.items()
            if peer is not None
        ]
        with self.conn:
            self.conn.executemany(
                "INSERT OR IGNORE INTO candidates(infohash, source, state, seen_at, next_try) "
                "VALUES (?, ?, 'pending', ?, 0)",
                rows,
            )
            if with_peers:
                self.conn.executemany(
                    "UPDATE candidates SET peers=? WHERE infohash=? AND peers IS NULL",
                    with_peers,
                )
        return len(rows)

    def next_candidates(self, limit: int) -> list[sqlite3.Row]:
        now = int(time.time())
        rows = self.conn.execute(
            "SELECT infohash, source, peers, attempts FROM candidates "
            "WHERE state='pending' AND next_try<=? ORDER BY seen_at LIMIT ?",
            (now, limit),
        ).fetchall()
        if rows:
            with self.conn:
                self.conn.executemany(
                    "UPDATE candidates SET state='lookup' WHERE infohash=?",
                    [(row["infohash"],) for row in rows],
                )
        return rows

    def set_state(
        self,
        infohash: str,
        state: str,
        *,
        next_try: int = 0,
        peers: list[str] | None = None,
        bump_attempts: bool = False,
    ) -> None:
        with self.conn:
            self.conn.execute(
                "UPDATE candidates SET state=?, next_try=?, "
                "attempts = attempts + ? , "
                "peers = COALESCE(?, peers) "
                "WHERE infohash=?",
                (
                    state,
                    next_try,
                    1 if bump_attempts else 0,
                    json.dumps(peers) if peers is not None else None,
                    infohash,
                ),
            )

    def count_pending(self) -> int:
        row = self.conn.execute(
            "SELECT COUNT(*) AS n FROM candidates WHERE state IN ('pending','lookup')"
        ).fetchone()
        return int(row["n"]) if row else 0

    def candidate_counts(self) -> dict[str, int]:
        rows = self.conn.execute("SELECT state, COUNT(*) AS n FROM candidates GROUP BY state").fetchall()
        return {row["state"]: int(row["n"]) for row in rows}

    # -- torrents ----------------------------------------------------------

    def has_torrent(self, infohash: str) -> bool:
        row = self.conn.execute("SELECT 1 FROM torrents WHERE infohash=?", (infohash,)).fetchone()
        return row is not None

    def save_torrent(
        self,
        infohash: str,
        name: str,
        total_size: int,
        file_count: int,
        files: list[dict],
        info_blob: bytes,
        ext: str | None,
        peers: int,
        source: str | None,
        first_seen: int | None = None,
    ) -> None:
        now = int(time.time())
        with self.conn:
            self.conn.execute(
                "INSERT OR REPLACE INTO torrents"
                "(infohash, name, total_size, file_count, files, info_dict, ext, peers,"
                " source, first_seen, harvested_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    infohash,
                    name,
                    total_size,
                    file_count,
                    json.dumps(files, ensure_ascii=False),
                    info_blob,
                    ext,
                    peers,
                    source,
                    first_seen or now,
                    now,
                ),
            )
            self.conn.execute("UPDATE candidates SET state='done' WHERE infohash=?", (infohash,))

    def new_since(self, timestamp: int, limit: int = 50) -> list[sqlite3.Row]:
        return self.conn.execute(
            "SELECT infohash, name, total_size, file_count, ext, harvested_at FROM torrents "
            "WHERE harvested_at > ? ORDER BY harvested_at ASC LIMIT ?",
            (timestamp, limit),
        ).fetchall()

    def get_torrent(self, infohash: str) -> sqlite3.Row | None:
        return self.conn.execute("SELECT * FROM torrents WHERE infohash=?", (infohash,)).fetchone()

    def find_by_prefix(self, prefix: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM torrents WHERE infohash LIKE ? ORDER BY harvested_at DESC LIMIT 1",
            (prefix + "%",),
        ).fetchone()

    def search(
        self,
        query: str | None = None,
        ext: str | None = None,
        min_size: int | None = None,
        max_size: int | None = None,
        since_hours: float | None = None,
        limit: int = 50,
        offset: int = 0,
        order: str = "time",
    ) -> list[sqlite3.Row]:
        clauses: list[str] = []
        params: list[object] = []
        if query:
            clauses.append("name LIKE ?")
            params.append(f"%{query}%")
        if ext:
            clauses.append("ext = ?")
            params.append(ext.lower().lstrip("."))
        if min_size is not None:
            clauses.append("total_size >= ?")
            params.append(min_size)
        if max_size is not None:
            clauses.append("total_size <= ?")
            params.append(max_size)
        if since_hours is not None:
            clauses.append("harvested_at >= ?")
            params.append(int(time.time() - since_hours * 3600))
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        order_by = "total_size DESC" if order == "size" else "harvested_at DESC"
        params.extend([limit, offset])
        return self.conn.execute(
            f"SELECT infohash, name, total_size, file_count, ext, peers, harvested_at "
            f"FROM torrents {where} ORDER BY {order_by} LIMIT ? OFFSET ?",
            params,
        ).fetchall()

    def export_rows(self, since_hours: float | None = None, limit: int = 100_000) -> list[sqlite3.Row]:
        if since_hours is None:
            return self.conn.execute(
                "SELECT infohash, info_dict FROM torrents ORDER BY harvested_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return self.conn.execute(
            "SELECT infohash, info_dict FROM torrents WHERE harvested_at >= ? "
            "ORDER BY harvested_at DESC LIMIT ?",
            (int(time.time() - since_hours * 3600), limit),
        ).fetchall()

    def prune(self, days: float) -> int:
        cutoff = int(time.time() - days * 86400)
        with self.conn:
            cursor = self.conn.execute("DELETE FROM torrents WHERE harvested_at < ?", (cutoff,))
            self.conn.execute("DELETE FROM candidates WHERE state='done' AND seen_at < ?", (cutoff,))
        return cursor.rowcount

    def stats(self) -> dict:
        now = int(time.time())
        total = self.conn.execute("SELECT COUNT(*) AS n FROM torrents").fetchone()["n"]
        day = self.conn.execute(
            "SELECT COUNT(*) AS n FROM torrents WHERE harvested_at >= ?", (now - 86400,)
        ).fetchone()["n"]
        week = self.conn.execute(
            "SELECT COUNT(*) AS n FROM torrents WHERE harvested_at >= ?", (now - 7 * 86400,)
        ).fetchone()["n"]
        size = self.conn.execute("SELECT COALESCE(SUM(total_size), 0) AS n FROM torrents").fetchone()["n"]
        top_ext = self.conn.execute(
            "SELECT COALESCE(ext, '?') AS ext, COUNT(*) AS n FROM torrents "
            "GROUP BY ext ORDER BY n DESC LIMIT 10"
        ).fetchall()
        return {
            "total": total,
            "last_24h": day,
            "last_7d": week,
            "total_size": size,
            "top_ext": [(row["ext"], row["n"]) for row in top_ext],
            "candidates": self.candidate_counts(),
        }

    # -- meta --------------------------------------------------------------

    def meta_get(self, key: str, default: str | None = None) -> str | None:
        row = self.conn.execute("SELECT v FROM meta WHERE k=?", (key,)).fetchone()
        return row["v"] if row else default

    def meta_set(self, key: str, value: str) -> None:
        with self.conn:
            self.conn.execute(
                "INSERT INTO meta(k, v) VALUES (?, ?) ON CONFLICT(k) DO UPDATE SET v=excluded.v",
                (key, value),
            )

    def get_node_id(self) -> bytes | None:
        value = self.meta_get("node_id")
        if value:
            try:
                raw = bytes.fromhex(value)
            except ValueError:
                return None
            if len(raw) == 20:
                return raw
        return None

    def set_node_id(self, node_id: bytes) -> None:
        self.meta_set("node_id", node_id.hex())
