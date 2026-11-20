"""Metadata harvester: DHT lookup -> libtorrent metadata-only fetch -> SQLite."""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import zlib
from datetime import date
from pathlib import Path

import libtorrent as lt

from .config import Config
from .dht import DHT
from .store import Store

log = logging.getLogger(__name__)


def _split_peer(value: str) -> tuple[str, int] | None:
    try:
        host, _, port = value.rpartition(":")
        return host, int(port)
    except (ValueError, AttributeError):
        return None


def _pick_ext(files: list[dict]) -> str | None:
    if not files:
        return None
    biggest = max(files, key=lambda item: item.get("size", 0))
    suffix = Path(str(biggest.get("path", ""))).suffix.lower().lstrip(".")
    if suffix and len(suffix) <= 10 and suffix.isalnum():
        return suffix
    return None


class Harvester:
    def __init__(self, config: Config, store: Store, dht: DHT) -> None:
        self.config = config
        self.store = store
        self.dht = dht
        self.scratch = Path(store.path).parent / "scratch"
        self.scratch.mkdir(parents=True, exist_ok=True)
        self._clean_scratch()

        settings = {
            "listen_interfaces": f"0.0.0.0:{config.harvest.port}",
            "enable_dht": False,
            "enable_lsd": False,
            "enable_upnp": False,
            "enable_natpmp": False,
            "connections_limit": 200,
            "upload_rate_limit": 16 * 1024,
            "download_rate_limit": 1024 * 1024,
            "alert_mask": int(
                lt.alert.category_t.status_notification
                | lt.alert.category_t.error_notification
                | lt.alert.category_t.storage_notification
            ),
        }
        self.session = lt.session(settings)

        self.active: dict[str, dict] = {}
        self.lookup_sem = asyncio.Semaphore(config.harvest.lookup_concurrency)
        self.lookup_tasks: set[asyncio.Task] = set()

        self.harvested = 0
        self.failed = 0
        self.skipped = 0
        self.lookups = 0
        self._today = date.today().isoformat()
        self._today_count = int(store.meta_get(f"harvested:{self._today}", "0") or 0)

        self._rate_tokens = float(config.harvest.max_per_minute)
        self._rate_last = time.monotonic()
        self._last_report = time.monotonic()
        self._report_harvested = 0

    # -- lifecycle ---------------------------------------------------------

    def _clean_scratch(self) -> None:
        for entry in self.scratch.iterdir():
            try:
                if entry.is_file():
                    entry.unlink()
                elif entry.is_dir():
                    import shutil

                    shutil.rmtree(entry, ignore_errors=True)
            except OSError:
                pass

    async def run(self) -> None:
        log.info(
            "harvester: listen=%d concurrency=%d limit=%d/day",
            self.config.harvest.port,
            self.config.harvest.concurrency,
            self.config.harvest.max_per_day,
        )
        while True:
            try:
                await asyncio.sleep(0.5)
                self._drain_alerts()
                self._expire()
                self._refill_rate()
                if self._budget_ok():
                    self._fill()
                self._report()
            except asyncio.CancelledError:
                self._shutdown()
                raise
            except Exception:
                log.exception("harvester loop error")
                await asyncio.sleep(2)

    def _shutdown(self) -> None:
        for ih, record in list(self.active.items()):
            try:
                self.session.remove_torrent(record["handle"], lt.options_t.delete_files)
            except Exception:
                pass
            self.active.pop(ih, None)

    # -- budget ------------------------------------------------------------

    def _refill_rate(self) -> None:
        now = time.monotonic()
        per_second = self.config.harvest.max_per_minute / 60.0
        self._rate_tokens = min(
            float(self.config.harvest.max_per_minute),
            self._rate_tokens + (now - self._rate_last) * per_second,
        )
        self._rate_last = now

    def _roll_day(self) -> None:
        today = date.today().isoformat()
        if today != self._today:
            self._today = today
            self._today_count = int(self.store.meta_get(f"harvested:{today}", "0") or 0)

    def _budget_ok(self) -> bool:
        self._roll_day()
        if self._today_count >= self.config.harvest.max_per_day:
            return False
        return self._rate_tokens >= 1.0

    def _consume(self) -> None:
        self._rate_tokens -= 1.0

    def _record_success(self) -> None:
        self.harvested += 1
        self._today_count += 1
        self.store.meta_set(f"harvested:{self._today}", str(self._today_count))

    # -- scheduling --------------------------------------------------------

    def _fill(self) -> None:
        free = self.config.harvest.concurrency - len(self.active) - len(self.lookup_tasks)
        if free <= 0:
            return
        rows = self.store.next_candidates(free)
        for index, row in enumerate(rows):
            if not self._budget_ok():
                for leftover in rows[index:]:
                    self.store.set_state(leftover["infohash"], "pending")
                return
            self._consume()
            peers = []
            if row["peers"]:
                try:
                    peers = json.loads(row["peers"])
                except (ValueError, TypeError):
                    peers = []
            self.lookups += 1
            task = asyncio.create_task(
                self._lookup_and_add(row["infohash"], row["source"], peers, int(row["attempts"]))
            )
            self.lookup_tasks.add(task)
            task.add_done_callback(self.lookup_tasks.discard)

    async def _lookup_and_add(self, infohash: str, source: str, peers: list[str], attempts: int) -> None:
        try:
            async with self.lookup_sem:
                if self.store.has_torrent(infohash):
                    self.store.set_state(infohash, "done")
                    return

                peer_list = [peer for peer in peers if peer]
                if not peer_list:
                    peer_list = await self.dht.lookup(bytes.fromhex(infohash), timeout=self.config.harvest.lookup_timeout)

                if self.config.harvest.self_ip:
                    peer_list = [p for p in peer_list if not p.startswith(self.config.harvest.self_ip + ":")]

                if not peer_list:
                    self._retry_or_give_up(infohash, "no_peers", attempts)
                    return

                self._add_torrent(infohash, source, peer_list, attempts)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("lookup failed for %s", infohash)
            self._retry_or_give_up(infohash, "failed", attempts)

    def _retry_or_give_up(self, infohash: str, state: str, attempts: int) -> None:
        attempts += 1
        if attempts <= self.config.harvest.retry:
            self.store.set_state(
                infohash,
                "pending",
                next_try=int(time.time()) + self.config.harvest.retry_after,
                bump_attempts=True,
            )
        else:
            self.store.set_state(infohash, state, bump_attempts=True)
            self.failed += 1

    def _add_torrent(self, infohash: str, source: str, peers: list[str], attempts: int) -> None:
        if len(self.active) >= self.config.harvest.concurrency:
            self.store.set_state(infohash, "pending")
            return

        parsed: list[tuple[str, int]] = []
        seen: set[str] = set()
        for peer in peers:
            if peer in seen:
                continue
            seen.add(peer)
            item = _split_peer(peer)
            if item is not None:
                parsed.append(item)
        if not parsed:
            self._retry_or_give_up(infohash, "no_peers", attempts)
            return

        try:
            params = lt.parse_magnet_uri(f"magnet:?xt=urn:btih:{infohash}")
            params.save_path = str(self.scratch)
            params.peers = parsed
            params.flags |= lt.torrent_flags.default_dont_download
            params.flags &= ~lt.torrent_flags.auto_managed
            # libtorrent 2.1 returns a paused params object from parse_magnet_uri.
            params.flags &= ~lt.torrent_flags.paused
            handle = self.session.add_torrent(params)
        except Exception:
            log.exception("add_torrent failed for %s", infohash)
            self._retry_or_give_up(infohash, "failed", attempts)
            return

        self.active[infohash] = {
            "handle": handle,
            "deadline": time.monotonic() + self.config.harvest.timeout,
            "peers": len(parsed),
            "attempts": attempts,
            "source": source,
        }
        self.store.set_state(infohash, "harvesting", peers=peers)

    # -- alerts ------------------------------------------------------------

    def _drain_alerts(self) -> None:
        for alert in self.session.pop_alerts():
            name = type(alert).__name__
            if name == "metadata_received_alert":
                self._on_metadata(alert.handle)
            elif name in ("torrent_error_alert", "file_error_alert"):
                self._on_error(alert)

    def _on_metadata(self, handle) -> None:
        infohash = str(handle.info_hash())
        record = self.active.get(infohash)
        info = handle.torrent_file()
        if record is None or info is None:
            return
        try:
            self._save(infohash, info, record)
        except Exception:
            log.exception("saving metadata failed for %s", infohash)
            self._retry_or_give_up(infohash, "failed", int(record["attempts"]))
        finally:
            self._remove(infohash)

    def _on_error(self, alert) -> None:
        handle = getattr(alert, "handle", None)
        if handle is None:
            return
        infohash = str(handle.info_hash())
        record = self.active.get(infohash)
        if record is None:
            return
        log.debug("torrent error %s: %s", infohash, alert)
        self._retry_or_give_up(infohash, "failed", int(record["attempts"]))
        self._remove(infohash)

    def _save(self, infohash: str, info, record: dict) -> None:
        file_count = info.num_files()
        if file_count == 0 or file_count > self.config.harvest.max_file_count:
            log.info("skip %s: %d files", infohash, file_count)
            self.store.set_state(infohash, "skipped")
            self.skipped += 1
            return

        storage = info.files()
        files = [
            {"path": storage.file_path(index), "size": storage.file_size(index)}
            for index in range(file_count)
        ]

        entry = lt.create_torrent(info).generate()
        # libtorrent returns nested entries as tuples, not dicts.
        if b"info" in entry:
            info_dict = entry[b"info"]
        else:  # pragma: no cover - older bindings
            info_dict = entry["info"]
        blob = lt.bencode(info_dict)
        if len(blob) > self.config.harvest.max_info_dict:
            log.info("skip %s: info dict %d bytes", infohash, len(blob))
            self.store.set_state(infohash, "skipped")
            self.skipped += 1
            return

        self.store.save_torrent(
            infohash=infohash,
            name=info.name(),
            total_size=info.total_size(),
            file_count=file_count,
            files=files,
            info_blob=zlib.compress(blob, 6),
            ext=_pick_ext(files),
            peers=int(record.get("peers", 0)),
            source=record.get("source"),
        )
        self._record_success()

    def _remove(self, infohash: str) -> None:
        record = self.active.pop(infohash, None)
        if record is None:
            return
        try:
            self.session.remove_torrent(record["handle"], lt.options_t.delete_files)
        except Exception:
            pass

    def _expire(self) -> None:
        now = time.monotonic()
        for infohash, record in list(self.active.items()):
            if now < record["deadline"]:
                continue
            self._retry_or_give_up(infohash, "failed", int(record["attempts"]))
            self._remove(infohash)

    def _report(self) -> None:
        now = time.monotonic()
        if now - self._last_report < 60:
            return
        elapsed = max(now - self._last_report, 1)
        rate = (self.harvested - self._report_harvested) / elapsed * 60
        log.info(
            "harvest: %d/min ok=%d total=%d/%d active=%d pending=%d failed=%d skipped=%d",
            round(rate),
            self.harvested - self._report_harvested,
            self._today_count,
            self.config.harvest.max_per_day,
            len(self.active),
            self.store.count_pending(),
            self.failed,
            self.skipped,
        )
        self._last_report = now
        self._report_harvested = self.harvested


def wrap_torrent(info_dict: bytes) -> bytes:
    """Rebuild a complete .torrent from a stored bencoded info dict."""
    from .krpc import bdecode, bencode

    info = bdecode(info_dict)
    return bencode({b"info": info, b"created by": b"bt-sniff"})
