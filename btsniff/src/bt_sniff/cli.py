"""Command line interface."""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
import sqlite3
import sys
import time
import zlib
from pathlib import Path

from .config import Config, load_config
from .crawler import Crawler
from .dht import DHT
from .harvester import Harvester, wrap_torrent
from .store import Store

log = logging.getLogger("bt_sniff")


def human_size(value: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(value) < 1024 or unit == "TB":
            return f"{value:.0f}{unit}" if unit == "B" else f"{value:.1f}{unit}"
        value /= 1024
    return f"{value:.1f}TB"


def parse_hours(text: str | None) -> float | None:
    if not text:
        return None
    text = text.strip().lower()
    units = {"m": 1 / 60, "h": 1.0, "d": 24.0, "w": 24 * 7}
    if text[-1] in units:
        return float(text[:-1]) * units[text[-1]]
    return float(text)


def parse_size(text: str | None) -> int | None:
    if not text:
        return None
    text = text.strip().lower()
    units = {"k": 1024, "m": 1024**2, "g": 1024**3, "t": 1024**4}
    if text and text[-1] in units:
        return int(float(text[:-1]) * units[text[-1]])
    return int(float(text))


def _open_store(args) -> Store:
    config = load_config(getattr(args, "config", None))
    if getattr(args, "db", None):
        config.store.path = args.db
    return Store(config.store.path)


# -- run -------------------------------------------------------------------


async def _run(config: Config, duration: float | None) -> None:
    store = Store(config.store.path)
    node_id = store.get_node_id()
    if node_id is None:
        node_id = os.urandom(20)
        store.set_node_id(node_id)

    holder: dict[str, Crawler] = {}

    def on_infohash(infohash: str, kind: str, peer: str | None) -> None:
        crawler = holder.get("crawler")
        if crawler is not None:
            crawler.on_infohash(infohash, kind, peer)

    dht = DHT(
        node_id=node_id,
        on_infohash=on_infohash,
        query_rate=config.dht.query_rate,
        seeds=config.dht.seeds,
        max_nodes=config.dht.max_nodes,
    )
    await dht.start(config.dht.port)
    await dht.bootstrap()

    crawler = Crawler(config, store, dht)
    holder["crawler"] = crawler
    harvester = Harvester(config, store, dht)

    log.info("db=%s node_id=%s", config.store.path, node_id.hex())

    tasks = [
        asyncio.create_task(crawler.run(), name="crawler"),
        asyncio.create_task(harvester.run(), name="harvester"),
    ]

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:  # pragma: no cover - windows
            pass

    try:
        if duration:
            await asyncio.wait_for(stop.wait(), timeout=duration)
        else:
            await stop.wait()
    except asyncio.TimeoutError:
        pass
    finally:
        log.info("shutting down")
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        store.flush()
        dht.close()
        store.close()


def cmd_run(args) -> int:
    config = load_config(args.config)
    if args.db:
        config.store.path = args.db
    _setup_logging(config.log_level)
    asyncio.run(_run(config, args.duration))
    return 0


# -- read-only commands ----------------------------------------------------


def cmd_stats(args) -> int:
    store = _open_store(args)
    try:
        stats = store.stats()
        print(f"torrents   : {stats['total']} (24h: {stats['last_24h']}, 7d: {stats['last_7d']})")
        print(f"content    : {human_size(stats['total_size'])} indexed")
        candidates = stats["candidates"]
        if candidates:
            print("candidates : " + ", ".join(f"{k}={v}" for k, v in sorted(candidates.items())))
        if stats["top_ext"]:
            print("top ext    : " + ", ".join(f"{ext}={n}" for ext, n in stats["top_ext"]))
    finally:
        store.close()
    return 0


def cmd_search(args) -> int:
    store = _open_store(args)
    try:
        rows = store.search(
            query=args.query,
            ext=args.ext,
            min_size=parse_size(args.min_size),
            max_size=parse_size(args.max_size),
            since_hours=parse_hours(args.since),
            limit=args.limit,
            offset=args.offset,
            order=args.order,
        )
        if not rows:
            print("no results")
            return 0
        for row in rows:
            when = time.strftime("%m-%d %H:%M", time.localtime(row["harvested_at"]))
            name = row["name"].replace("\n", " ")
            print(
                f"{row['infohash'][:12]}  {when}  {human_size(row['total_size']):>8}  "
                f"{row['file_count']:>4}f  {(row['ext'] or '-'):<5}  {name[:110]}"
            )
    finally:
        store.close()
    return 0


def cmd_backup(args) -> int:
    store = _open_store(args)
    try:
        target = sqlite3.connect(args.out)
        try:
            store.conn.backup(target)
        finally:
            target.close()
        print(f"backed up to {args.out}")
    finally:
        store.close()
    return 0


def cmd_sql(args) -> int:
    store = _open_store(args)
    try:
        store.conn.execute("PRAGMA query_only=ON")
        rows = store.conn.execute(args.query).fetchall()
        if not rows:
            print("(no rows)")
            return 0
        keys = list(rows[0].keys())
        print(" | ".join(keys))
        for row in rows:
            print(" | ".join("" if row[key] is None else str(row[key]) for key in keys))
    finally:
        store.close()
    return 0


def cmd_show(args) -> int:
    store = _open_store(args)
    try:
        row = store.get_torrent(args.infohash.lower())
        if row is None and len(args.infohash) >= 6:
            row = store.find_by_prefix(args.infohash.lower())
        if row is None:
            print("not found")
            return 1
        import json

        print(f"name    : {row['name']}")
        print(f"infohash: {row['infohash']}")
        print(f"size    : {human_size(row['total_size'])} in {row['file_count']} files")
        print(f"peers   : {row['peers']}   source: {row['source']}   ext: {row['ext']}")
        print(f"seen    : {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(row['harvested_at']))}")
        print("magnet  : magnet:?xt=urn:btih:" + row["infohash"])
        files = json.loads(row["files"])
        for item in files[:40]:
            print(f"  {human_size(item['size']):>8}  {item['path']}")
        if len(files) > 40:
            print(f"  ... {len(files) - 40} more")
    finally:
        store.close()
    return 0


def cmd_tail(args) -> int:
    store = _open_store(args)
    last = int(time.time()) - int(args.backfill)
    seen: set[str] = set()
    try:
        print("watching for new torrents (ctrl-c to stop)")
        while True:
            rows = store.conn.execute(
                "SELECT infohash, name, total_size, file_count, ext, harvested_at "
                "FROM torrents WHERE harvested_at >= ? ORDER BY harvested_at ASC",
                (last,),
            ).fetchall()
            for row in rows:
                if row["infohash"] in seen:
                    continue
                seen.add(row["infohash"])
                when = time.strftime("%H:%M:%S", time.localtime(row["harvested_at"]))
                print(
                    f"{when}  {human_size(row['total_size']):>8}  {row['file_count']:>4}f  "
                    f"{(row['ext'] or '-'):<5}  {row['name'][:110]}",
                    flush=True,
                )
            if rows:
                last = max(int(row["harvested_at"]) for row in rows)
            if len(seen) > 20_000:
                seen.clear()
            time.sleep(2)
    except KeyboardInterrupt:
        return 0
    finally:
        store.close()


def cmd_export(args) -> int:
    store = _open_store(args)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    written = 0
    try:
        rows = store.export_rows(since_hours=parse_hours(args.since), limit=args.limit)
        for row in rows:
            info = zlib.decompress(row["info_dict"])
            path = out / f"{row['infohash']}.torrent"
            path.write_bytes(wrap_torrent(info))
            written += 1
        print(f"wrote {written} .torrent files to {out}")
    finally:
        store.close()
    return 0


def cmd_prune(args) -> int:
    store = _open_store(args)
    try:
        removed = store.prune(args.days)
        print(f"removed {removed} torrents older than {args.days} days")
    finally:
        store.close()
    return 0


def cmd_lookup(args) -> int:
    config = load_config(args.config)
    _setup_logging("INFO")

    async def _lookup() -> list[str]:
        dht = DHT(node_id=os.urandom(20), on_infohash=lambda *a: None)
        await dht.start(config.dht.port)
        await dht.bootstrap()
        peers = await dht.lookup(bytes.fromhex(args.infohash), timeout=args.timeout)
        dht.close()
        return peers

    peers = asyncio.run(_lookup())
    print(f"{len(peers)} peers")
    for peer in peers:
        print(peer)
    return 0


# -- wiring ----------------------------------------------------------------


def _setup_logging(level: str) -> None:
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
        datefmt="%H:%M:%S",
        stream=sys.stderr,
    )
    logging.getLogger("asyncio").setLevel(logging.WARNING)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bt-sniff", description="BitTorrent DHT sniffer")
    sub = parser.add_subparsers(dest="cmd", required=True)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--config", help="path to config.toml")
        p.add_argument("--db", help="override database path")

    run = sub.add_parser("run", help="run crawler + harvester")
    common(run)
    run.add_argument("--duration", type=float, help="stop after N seconds (testing)")
    run.set_defaults(func=cmd_run)

    tail = sub.add_parser("tail", help="watch newly harvested torrents")
    common(tail)
    tail.add_argument("--backfill", type=int, default=60, help="show the last N seconds")
    tail.set_defaults(func=cmd_tail)

    search = sub.add_parser("search", help="search harvested torrents")
    common(search)
    search.add_argument("query", nargs="?", help="substring of the torrent name")
    search.add_argument("--ext", help="file extension, e.g. mkv")
    search.add_argument("--min-size", help="e.g. 1G")
    search.add_argument("--max-size", help="e.g. 20G")
    search.add_argument("--since", help="e.g. 24h, 7d")
    search.add_argument("--limit", type=int, default=50)
    search.add_argument("--offset", type=int, default=0, help="skip N rows (paging)")
    search.add_argument("--order", choices=["time", "size"], default="time")
    search.set_defaults(func=cmd_search)

    sql = sub.add_parser("sql", help="run a read-only SQL query against the database")
    common(sql)
    sql.add_argument("query")
    sql.set_defaults(func=cmd_sql)

    backup = sub.add_parser("backup", help="write a consistent copy of the database")
    common(backup)
    backup.add_argument("out")
    backup.set_defaults(func=cmd_backup)

    show = sub.add_parser("show", help="show one torrent and its files")
    common(show)
    show.add_argument("infohash")
    show.set_defaults(func=cmd_show)

    stats = sub.add_parser("stats", help="summary statistics")
    common(stats)
    stats.set_defaults(func=cmd_stats)

    export = sub.add_parser("export", help="write .torrent files")
    common(export)
    export.add_argument("--out", default="export")
    export.add_argument("--since", help="e.g. 24h")
    export.add_argument("--limit", type=int, default=100_000)
    export.set_defaults(func=cmd_export)

    prune = sub.add_parser("prune", help="delete old rows")
    common(prune)
    prune.add_argument("--days", type=float, default=90)
    prune.set_defaults(func=cmd_prune)

    lookup = sub.add_parser("lookup", help="look up peers for an infohash via DHT")
    common(lookup)
    lookup.add_argument("infohash")
    lookup.add_argument("--timeout", type=float, default=15)
    lookup.set_defaults(func=cmd_lookup)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except KeyboardInterrupt:
        return 130
    except sqlite3.OperationalError as exc:
        print(f"database error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
