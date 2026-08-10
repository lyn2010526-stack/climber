"""Large-scale code retrieval.

"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class CodeRetrievalService:
    """Retrieve and index code files for large-scale repositories.

    """

    def __init__(self, workspace_path: str = "./workspace"):
        self._workspace = Path(workspace_path)
        self._index: dict[str, str] = {}

    def index_repository(self, repo_path: str) -> dict[str, str]:
        """Index code files in a repository."""
        root = Path(repo_path)
        if not root.exists():
            raise FileNotFoundError(repo_path)
        ignore_dirs = {".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build"}
        extensions = {".py", ".ts", ".tsx", ".js", ".jsx", ".go", ".rs", ".java", ".cpp", ".c", ".h", ".md", ".json", ".yaml", ".yml"}
        self._index.clear()
        for path in root.rglob("*"):
            if any(part in ignore_dirs for part in path.parts):
                continue
            if path.is_file() and path.suffix in extensions:
                try:
                    content = path.read_text(encoding="utf-8", errors="ignore")
                    rel = str(path.relative_to(root))
                    self._index[rel] = content
                except Exception:
                    logger.debug("code_index_skip", path=str(path), exc_info=True)
                    continue
        logger.info("code_indexed", repo=repo_path, files=len(self._index))
        return self._index

    def search(self, query: str, top_k: int = 10) -> list[dict[str, Any]]:
        """Search indexed code by keyword."""
        results: list[dict[str, Any]] = []
        query_lower = query.lower()
        for path, content in self._index.items():
            score = 0
            lines = content.splitlines()
            for i, line in enumerate(lines, 1):
                if query_lower in line.lower():
                    score += 1
                    results.append({
                        "path": path,
                        "line": i,
                        "content": line.strip(),
                        "score": score,
                    })
        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:top_k]

    def get_file(self, path: str) -> str | None:
        return self._index.get(path)

    def list_files(self) -> list[str]:
        return list(self._index.keys())


code_retrieval = CodeRetrievalService()
