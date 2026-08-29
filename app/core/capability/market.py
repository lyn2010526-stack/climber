"""Capability market — .cap package distribution, lazy loading, LRU eviction.

Capabilities are distributed as .cap files (zip with metadata.json + code).
The agent automatically searches and installs missing capabilities on demand.
Only the core 10 capabilities are loaded at startup; the rest are loaded
lazily on first use. LRU eviction unloads the least recently used
capabilities under memory pressure.
"""

from __future__ import annotations

import json
import zipfile
from collections import OrderedDict
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any

from app.core.capability.capability import Capability, CapabilityMeta, WrappedCapability

CORE_CAPABILITY_IDS = {
    "model_call",
    "device_operation",
    "memory_search",
    "skill_load",
    "config_manage",
    "tool_execute",
    "perception_screenshot",
    "perception_ui_tree",
    "memory_store",
    "log_query",
}

SENSITIVE_KEYS = ("api_key", "token", "secret", "password", "credential", "private_key")


@dataclass
class CapabilityPackage:
    cap_id: str
    name: str
    description: str
    version: str = "1.0.0"
    author: str = ""
    meta: CapabilityMeta | None = None
    files: dict[str, bytes] = field(default_factory=dict)


class CapabilityMarket:
    """Manages .cap package distribution, scanning, and lazy loading."""

    def __init__(
        self,
        registry: Any,
        market_dir: str | Path = "data/cap_market",
        lru_capacity: int = 50,
    ) -> None:
        self._registry = registry
        self._market_dir = Path(market_dir)
        self._market_dir.mkdir(parents=True, exist_ok=True)
        self._lru: OrderedDict[str, Capability] = OrderedDict()
        self._lru_capacity = lru_capacity
        self._lazy_loaded: set[str] = set()

    def export_package(self, capability: Capability) -> bytes:
        meta = capability.meta
        buf = BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("metadata.json", json.dumps({
                "id": meta.id,
                "name": meta.name,
                "description": meta.description,
                "type": meta.capability_type,
                "version": meta.version,
                "input_schema": meta.input_schema,
                "output_schema": meta.output_schema,
                "prerequisites": meta.prerequisites,
                "side_effects": meta.side_effects,
                "cost_profile": meta.cost_profile,
            }, ensure_ascii=False))
        return buf.getvalue()

    def scan_package(self, package_bytes: bytes) -> CapabilityPackage:
        with zipfile.ZipFile(BytesIO(package_bytes), "r") as zf:
            meta_raw = json.loads(zf.read("metadata.json").decode("utf-8"))
            files: dict[str, bytes] = {}
            for name in zf.namelist():
                if name != "metadata.json":
                    files[name] = zf.read(name)
        return CapabilityPackage(
            cap_id=meta_raw["id"],
            name=meta_raw["name"],
            description=meta_raw.get("description", ""),
            version=meta_raw.get("version", "1.0.0"),
            files=files,
        )

    def install_package(self, pkg: CapabilityPackage) -> Capability:
        meta = CapabilityMeta(
            id=pkg.cap_id,
            name=pkg.name,
            description=pkg.description,
            capability_type="market",
            version=pkg.version,
        )
        path = self._market_dir / f"{pkg.cap_id}.cap"
        buf = BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("metadata.json", json.dumps({
                "id": pkg.cap_id,
                "name": pkg.name,
                "description": pkg.description,
                "version": pkg.version,
            }))
            for name, content in pkg.files.items():
                zf.writestr(name, content)
        path.write_bytes(buf.getvalue())
        cap = WrappedCapability(meta=meta, fn=lambda **kw: {"installed": pkg.cap_id})
        self._registry.register(cap)
        return cap

    def search_market(self, query: str) -> list[dict[str, Any]]:
        available = self._registry.list_capabilities()
        q = query.lower()
        return [c for c in available if q in c["name"].lower() or q in c["description"].lower()]

    def is_core_capability(self, cap_id: str) -> bool:
        return cap_id in CORE_CAPABILITY_IDS

    def needs_lazy_load(self, cap_id: str) -> bool:
        return not self.is_core_capability(cap_id) and cap_id not in self._lazy_loaded

    def mark_loaded(self, cap_id: str) -> None:
        self._lazy_loaded.add(cap_id)

    def touch(self, cap_id: str, cap: Capability) -> None:
        self._lru[cap_id] = cap
        self._lru.move_to_end(cap_id)
        self._evict_lru()

    def _evict_lru(self) -> None:
        while len(self._lru) > self._lru_capacity:
            evicted_id, evicted = self._lru.popitem(last=False)
            self._registry.unregister(evicted_id, evicted)


_default_market: CapabilityMarket | None = None


def get_capability_market(registry: Any = None) -> CapabilityMarket:
    global _default_market
    if _default_market is None or registry is not None:
        from app.core.capability.registry import get_capability_registry

        _default_market = CapabilityMarket(registry or get_capability_registry())
    return _default_market
