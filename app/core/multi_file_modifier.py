"""Multi-file parallel modification.

"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.core.file_patch import FilePatchService

logger = logging.getLogger(__name__)


@dataclass
class FileModification:
    file_path: str
    patch: str
    description: str = ""


@dataclass
class ModificationResult:
    file_path: str
    success: bool
    applied: bool = False
    error: str | None = None
    preview: str | None = None


class MultiFileModifier:
    """Apply modifications to multiple files in parallel.

    """

    def __init__(self, max_parallel: int = 4):
        self._max_parallel = max_parallel
        self._patcher = FilePatchService()

    async def apply_modifications(self, modifications: list[FileModification], dry_run: bool = False) -> list[ModificationResult]:
        semaphore = asyncio.Semaphore(self._max_parallel)

        async def apply_one(mod: FileModification) -> ModificationResult:
            async with semaphore:
                return await self._apply_single(mod, dry_run)

        tasks = [apply_one(mod) for mod in modifications]
        return list(await asyncio.gather(*tasks))

    async def _apply_single(self, mod: FileModification, dry_run: bool) -> ModificationResult:
        path = Path(mod.file_path)
        if not path.exists():
            return ModificationResult(file_path=mod.file_path, success=False, error="File not found")
        try:
            if dry_run:
                preview = mod.patch
                return ModificationResult(file_path=mod.file_path, success=True, applied=False, preview=preview)
            ok, msg = self._patcher.apply_patch_to_file(mod.file_path, mod.patch)
            if ok:
                return ModificationResult(file_path=mod.file_path, success=True, applied=True, preview=mod.patch)
            return ModificationResult(file_path=mod.file_path, success=False, applied=False, error=msg)
        except Exception as e:
            return ModificationResult(file_path=mod.file_path, success=False, applied=False, error=str(e))


multi_file_modifier = MultiFileModifier()
