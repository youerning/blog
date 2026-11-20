"""Configuration loading: config.toml plus sensible defaults."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field, fields
from pathlib import Path

from .dht import DEFAULT_SEEDS


@dataclass
class DHTConfig:
    port: int = 6881
    query_rate: float = 10.0
    max_nodes: int = 50_000
    max_pending: int = 50_000
    seeds: list[str] = field(default_factory=lambda: list(DEFAULT_SEEDS))


@dataclass
class HarvestConfig:
    port: int = 6882
    concurrency: int = 20
    lookup_concurrency: int = 8
    timeout: float = 40.0
    lookup_timeout: float = 15.0
    retry: int = 1
    retry_after: int = 1800
    max_file_count: int = 5_000
    max_info_dict: int = 2 * 1024 * 1024
    max_per_day: int = 5_000
    max_per_minute: int = 30
    self_ip: str | None = None


@dataclass
class StoreConfig:
    path: str = str(Path.home() / ".local" / "share" / "bt-sniff" / "bt.db")


@dataclass
class Config:
    dht: DHTConfig = field(default_factory=DHTConfig)
    harvest: HarvestConfig = field(default_factory=HarvestConfig)
    store: StoreConfig = field(default_factory=StoreConfig)
    log_level: str = "INFO"


def _apply(section: dict, target) -> None:
    allowed = {f.name for f in fields(target)}
    for key, value in section.items():
        if key in allowed:
            setattr(target, key, value)


def load_config(path: str | None = None) -> Config:
    candidates = []
    explicit = path or os.environ.get("BT_SNIFF_CONFIG")
    if explicit:
        candidates.append(Path(explicit))
    else:
        candidates.extend(
            [
                Path.cwd() / "config.toml",
                Path("/etc/bt-sniff/config.toml"),
            ]
        )

    config = Config()
    for candidate in candidates:
        if candidate and candidate.is_file():
            with candidate.open("rb") as handle:
                data = tomllib.load(handle)
            if "dht" in data:
                _apply(data["dht"], config.dht)
            if "harvest" in data:
                _apply(data["harvest"], config.harvest)
            if "store" in data:
                _apply(data["store"], config.store)
            if "log_level" in data:
                config.log_level = str(data["log_level"])
            config.source = str(candidate)  # type: ignore[attr-defined]
            break

    config.harvest.max_info_dict = max(64 * 1024, config.harvest.max_info_dict)
    return config
