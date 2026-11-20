"""Mainline DHT node: routing table, KRPC server, iterative lookup, BEP 51."""

from __future__ import annotations

import asyncio
import hashlib
import heapq
import hmac
import ipaddress
import logging
import os
import random
import socket
import struct
import time
from dataclasses import dataclass

from .krpc import BencodeError, bdecode, bencode, decode_nodes, encode_nodes

log = logging.getLogger(__name__)

K = 8
DEFAULT_SEEDS = [
    "router.bittorrent.com:6881",
    "dht.transmissionbt.com:6881",
    "router.utorrent.com:6881",
    "dht.libtorrent.org:25401",
    "dht.aelitis.com:6881",
]


def xor_distance(left: bytes, right: bytes) -> int:
    return int.from_bytes(left, "big") ^ int.from_bytes(right, "big")


def is_public_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return addr.is_global and not addr.is_multicast


@dataclass(slots=True)
class Node:
    nid: bytes
    ip: str
    port: int
    seen: float
    next_sample: float = 0.0

    @property
    def key(self) -> tuple[str, int]:
        return (self.ip, self.port)


class RoutingTable:
    """A flat table instead of proper k-buckets.

    For a sniffing node we care about "reachable nodes we can query", not about
    being a perfect DHT citizen, so keeping every node we hear from is enough.
    """

    def __init__(self, max_nodes: int = 50_000) -> None:
        self.max_nodes = max_nodes
        self._nodes: dict[tuple[str, int], Node] = {}

    def __len__(self) -> int:
        return len(self._nodes)

    def add(self, nid: bytes, ip: str, port: int) -> Node | None:
        if len(nid) != 20 or not port or not is_public_ip(ip):
            return None
        key = (ip, port)
        now = time.monotonic()
        node = self._nodes.get(key)
        if node is not None:
            node.nid = nid
            node.seen = now
            return node
        if len(self._nodes) >= self.max_nodes:
            # Drop the stalest 10% instead of doing expensive LRU bookkeeping.
            victims = sorted(self._nodes.values(), key=lambda n: n.seen)[: max(1, self.max_nodes // 10)]
            for victim in victims:
                self._nodes.pop(victim.key, None)
        node = Node(nid=nid, ip=ip, port=port, seen=now)
        self._nodes[key] = node
        return node

    def get(self, ip: str, port: int) -> Node | None:
        return self._nodes.get((ip, port))

    def closest(self, target: bytes, count: int = K) -> list[Node]:
        if not self._nodes:
            return []
        return heapq.nsmallest(count, self._nodes.values(), key=lambda n: xor_distance(n.nid, target))

    def random(self, count: int) -> list[Node]:
        if not self._nodes:
            return []
        return random.sample(list(self._nodes.values()), min(count, len(self._nodes)))

    def due_for_sample(self, count: int, now: float | None = None) -> list[Node]:
        now = now or time.monotonic()
        due = [n for n in self._nodes.values() if n.next_sample <= now]
        if len(due) <= count:
            return due
        return random.sample(due, count)

    def prune(self, max_age: float = 3600.0) -> int:
        cutoff = time.monotonic() - max_age
        stale = [n.key for n in self._nodes.values() if n.seen < cutoff]
        for key in stale:
            self._nodes.pop(key, None)
        return len(stale)


class DHT(asyncio.DatagramProtocol):
    """A single-node Mainline DHT: answers queries, harvests, looks up, samples."""

    def __init__(
        self,
        node_id: bytes,
        on_infohash,
        query_rate: float = 10.0,
        seeds: list[str] | None = None,
        max_nodes: int = 50_000,
    ) -> None:
        self.node_id = node_id
        self.on_infohash = on_infohash
        self.query_rate = max(1.0, query_rate)
        self.seeds = seeds or DEFAULT_SEEDS
        self.table = RoutingTable(max_nodes=max_nodes)
        self.secret = os.urandom(16)

        self._transport: asyncio.DatagramTransport | None = None
        self._pending: dict[bytes, asyncio.Future] = {}
        self._tokens = self.query_rate
        self._last_refill = time.monotonic()
        self.stats = {
            "sent": 0,
            "received": 0,
            "queries_in": 0,
            "announce_in": 0,
            "timeouts": 0,
            "bad_packets": 0,
        }

    # -- lifecycle ---------------------------------------------------------

    async def start(self, port: int = 6881) -> None:
        loop = asyncio.get_running_loop()
        await loop.create_datagram_endpoint(lambda: self, local_addr=("0.0.0.0", port))
        log.info("DHT listening on udp/%d node_id=%s", port, self.node_id.hex())

    def close(self) -> None:
        if self._transport is not None:
            self._transport.close()
            self._transport = None

    # -- protocol callbacks ------------------------------------------------

    def connection_made(self, transport) -> None:
        self._transport = transport

    def datagram_received(self, data: bytes, addr) -> None:
        self.stats["received"] += 1
        try:
            message = bdecode(data)
        except (BencodeError, ValueError):
            self.stats["bad_packets"] += 1
            return
        if not isinstance(message, dict):
            self.stats["bad_packets"] += 1
            return

        kind = message.get(b"y")
        if kind == b"r":
            self._handle_response(message, addr)
        elif kind == b"q":
            self._handle_query(message, addr)
        elif kind == b"e":
            tid = message.get(b"t")
            future = self._pending.pop(tid, None) if isinstance(tid, bytes) else None
            if future is not None and not future.done():
                future.set_result(None)

    def _handle_response(self, message: dict, addr) -> None:
        body = message.get(b"r")
        if not isinstance(body, dict):
            return
        node_id = body.get(b"id")
        if isinstance(node_id, bytes) and len(node_id) == 20:
            self.table.add(node_id, addr[0], addr[1])
        for nid, ip, port in decode_nodes(body.get(b"nodes")):
            self.table.add(nid, ip, port)
        tid = message.get(b"t")
        future = self._pending.pop(tid, None) if isinstance(tid, bytes) else None
        if future is not None and not future.done():
            future.set_result(body)

    def _handle_query(self, message: dict, addr) -> None:
        self.stats["queries_in"] += 1
        method = message.get(b"q", b"")
        args = message.get(b"a")
        if not isinstance(args, dict):
            args = {}
        transaction = message.get(b"t", b"")

        node_id = args.get(b"id")
        if isinstance(node_id, bytes) and len(node_id) == 20:
            self.table.add(node_id, addr[0], addr[1])

        infohash = args.get(b"info_hash")
        if isinstance(infohash, bytes) and len(infohash) == 20:
            if method == b"announce_peer":
                self.stats["announce_in"] += 1
                self.on_infohash(infohash.hex(), "announce_peer", f"{addr[0]}:{addr[1]}")
            elif method == b"get_peers":
                self.on_infohash(infohash.hex(), "get_peers", None)

        reply: dict[bytes, object] = {b"id": self.node_id}
        if method == b"get_peers":
            reply[b"token"] = self._token(addr[0])
            target = infohash if isinstance(infohash, bytes) else os.urandom(20)
            reply[b"nodes"] = encode_nodes([(n.nid, n.ip, n.port) for n in self.table.closest(target, K)])
        elif method == b"find_node":
            target = args.get(b"target")
            if not isinstance(target, bytes) or len(target) != 20:
                target = os.urandom(20)
            reply[b"nodes"] = encode_nodes([(n.nid, n.ip, n.port) for n in self.table.closest(target, K)])
        elif method == b"sample_infohashes":
            # We do not store infohashes, so hand back an empty sample.
            reply[b"interval"] = 3600
            reply[b"num"] = 0
            reply[b"samples"] = b""

        self._send({b"y": b"r", b"t": transaction, b"r": reply}, addr)

    # -- outbound ----------------------------------------------------------

    def _send(self, message: dict, addr: tuple[str, int]) -> None:
        if self._transport is None:
            return
        try:
            self._transport.sendto(bencode(message), addr)
            self.stats["sent"] += 1
        except OSError:
            pass

    def _token(self, ip: str) -> bytes:
        return hmac.new(self.secret, ip.encode(), hashlib.sha1).digest()[:4]

    async def _rate_limit(self) -> None:
        while True:
            now = time.monotonic()
            self._tokens = min(self.query_rate, self._tokens + (now - self._last_refill) * self.query_rate)
            self._last_refill = now
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return
            await asyncio.sleep(0.01)

    async def query(
        self,
        ip: str,
        port: int,
        method: str,
        args: dict | None = None,
        timeout: float = 4.0,
    ) -> dict | None:
        if self._transport is None:
            return None
        await self._rate_limit()

        transaction = os.urandom(4)
        future: asyncio.Future = asyncio.get_running_loop().create_future()
        self._pending[transaction] = future
        payload = {b"id": self.node_id}
        if args:
            payload.update(args)
        message = {b"t": transaction, b"y": b"q", b"q": method.encode(), b"a": payload}

        try:
            self._send(message, (ip, port))
            return await asyncio.wait_for(future, timeout=timeout)
        except (asyncio.TimeoutError, OSError):
            self.stats["timeouts"] += 1
            return None
        finally:
            self._pending.pop(transaction, None)

    async def bootstrap(self, timeout: float = 4.0) -> int:
        loop = asyncio.get_running_loop()
        addresses: list[tuple[str, int]] = []
        for seed in self.seeds:
            host, _, port = seed.rpartition(":")
            if not host:
                continue
            try:
                infos = await loop.getaddrinfo(host, int(port), type=socket.SOCK_DGRAM)
            except (OSError, ValueError):
                continue
            for info in infos:
                ip = info[4][0]
                if is_public_ip(ip):
                    addresses.append((ip, int(port)))
                    break

        if not addresses:
            log.warning("DHT bootstrap: no seed resolved")
            return 0

        await asyncio.gather(
            *(
                self.query(ip, port, "find_node", {b"target": os.urandom(20)}, timeout=timeout)
                for ip, port in addresses
            ),
            return_exceptions=True,
        )
        log.info("DHT bootstrap: %d seeds, %d nodes known", len(addresses), len(self.table))
        return len(addresses)

    async def lookup(self, infohash: bytes, timeout: float = 15.0, max_peers: int = 60) -> list[str]:
        """Iterative get_peers. Returns reachable-looking peer addresses."""
        if len(self.table) == 0:
            await self.bootstrap()

        deadline = time.monotonic() + timeout
        queried: set[tuple[str, int]] = set()
        peers: set[str] = set()

        while time.monotonic() < deadline and len(peers) < max_peers:
            candidates = [n for n in self.table.closest(infohash, 64) if n.key not in queried][:K]
            if not candidates:
                break
            results = await asyncio.gather(
                *(
                    self.query(n.ip, n.port, "get_peers", {b"info_hash": infohash}, timeout=3.0)
                    for n in candidates
                )
            )
            for node, body in zip(candidates, results):
                queried.add(node.key)
                if not body:
                    continue
                for nid, ip, port in decode_nodes(body.get(b"nodes")):
                    added = self.table.add(nid, ip, port)
                    if added is not None:
                        added.seen = time.monotonic()
                values = body.get(b"values")
                if isinstance(values, list):
                    for value in values:
                        if isinstance(value, bytes) and len(value) >= 6:
                            ip = socket.inet_ntoa(value[:4])
                            port = struct.unpack(">H", value[4:6])[0]
                            if is_public_ip(ip) and port:
                                peers.add(f"{ip}:{port}")

        return sorted(peers)

    async def sample_infohashes(self, node: Node, timeout: float = 5.0) -> list[str]:
        """BEP 51: ask a node for a sample of the infohashes it stores."""
        body = await self.query(
            node.ip,
            node.port,
            "sample_infohashes",
            {b"target": os.urandom(20)},
            timeout=timeout,
        )
        now = time.monotonic()
        if not body:
            node.next_sample = now + 1800
            return []

        interval = body.get(b"interval")
        if not isinstance(interval, int) or interval <= 0:
            interval = 600
        node.next_sample = now + max(120, min(interval, 3600))

        samples = body.get(b"samples")
        if not isinstance(samples, bytes):
            return []
        return [samples[i : i + 20].hex() for i in range(0, len(samples) - 19, 20)]
