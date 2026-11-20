"""Crawler: passive harvest from inbound queries + active BEP 51 sampling."""

from __future__ import annotations

import asyncio
import logging
import os
import time

from .config import Config
from .dht import DHT
from .store import Store

log = logging.getLogger(__name__)


class Crawler:
    def __init__(self, config: Config, store: Store, dht: DHT) -> None:
        self.config = config
        self.store = store
        self.dht = dht
        self.pending = 0
        self.added = 0
        self.sampled_nodes = 0
        self.samples_received = 0
        self.started = time.monotonic()
        self._last_report = time.monotonic()
        self._tasks: set[asyncio.Task] = set()
        self._sample_cursor = 0

    def on_infohash(self, infohash: str, kind: str, peer: str | None) -> None:
        self.store.add_candidate(infohash, kind, peer)
        self.added += 1

    async def run(self) -> None:
        await asyncio.gather(
            self._flush_loop(),
            self._expand_loop(),
            self._sample_loop(),
            self._report_loop(),
        )

    # -- helpers -----------------------------------------------------------

    def _spawn(self, coro, limit: int = 48) -> None:
        """Fire and forget, but keep a hard cap on concurrent queries."""
        if len(self._tasks) >= limit:
            coro.close()
            return
        task = asyncio.create_task(coro)
        self._tasks.add(task)
        task.add_done_callback(self._tasks.discard)

    async def _flush_loop(self) -> None:
        while True:
            await asyncio.sleep(1.0)
            self.store.flush()

    # -- loops -------------------------------------------------------------

    async def _expand_loop(self) -> None:
        """Keep the routing table fresh and make ourselves known to other nodes."""
        last_bootstrap = 0.0
        while True:
            try:
                if len(self.dht.table) < 500 and time.monotonic() - last_bootstrap > 60:
                    await self.dht.bootstrap()
                    last_bootstrap = time.monotonic()

                for node in self.dht.table.random(2):
                    self._spawn(
                        self.dht.query(
                            node.ip,
                            node.port,
                            "find_node",
                            {b"target": os.urandom(20)},
                            timeout=3.0,
                        )
                    )

                if len(self.dht.table) > 1_000 and int(time.monotonic()) % 600 < 1:
                    removed = self.dht.table.prune()
                    if removed:
                        log.info("routing table pruned: -%d", removed)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("expand loop error")
            await asyncio.sleep(0.5)

    async def _sample_loop(self) -> None:
        """Ask nodes for the infohashes they store (BEP 51)."""
        last_count = 0.0
        while True:
            try:
                now = time.monotonic()
                if now - last_count > 5:
                    self.pending = self.store.count_pending()
                    last_count = now

                if (
                    self.pending < self.config.dht.max_pending
                    and len(self.dht.table) > 30
                    and len(self._tasks) < 32
                ):
                    due = self.dht.table.due_for_sample(4, now)
                    for node in due:
                        self._spawn(self._sample_node(node))
                await asyncio.sleep(0.25)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("sample loop error")
                await asyncio.sleep(5.0)

    async def _sample_node(self, node) -> None:
        hashes = await self.dht.sample_infohashes(node)
        self.sampled_nodes += 1
        if not hashes:
            return
        self.samples_received += len(hashes)
        for infohash in hashes:
            self.store.add_candidate(infohash, "sample_infohashes")

    async def _report_loop(self) -> None:
        while True:
            await asyncio.sleep(60)
            now = time.monotonic()
            elapsed = max(now - self._last_report, 1)
            self._last_report = now
            self.pending = self.store.count_pending()
            log.info(
                "crawl: passive=%d/min samples=%d/min nodes=%d pending=%d inflight=%d",
                round(self.added / elapsed * 60),
                round(self.samples_received / elapsed * 60),
                len(self.dht.table),
                self.pending,
                len(self._tasks),
            )
            self.added = 0
            self.samples_received = 0
