"""Cross-file content retrieval tools (audit P2-2).

The file tools in ``builtins.py`` can read, write, patch, list and diff single
known paths. There was no primitive that finds *which* file or *where* in it,
so the only options for a model were ``run_command("grep ...")`` or reading
whole files. These two tools close that gap.

Both tools are citable, bounded, and honest about bounds:

* every hit is reported as ``path:line`` followed by the matching line, so the
  model can cite a location or jump straight to it with ``read_file``;
* the result header always states ``showing N of TOTAL matches``, so the model
  knows whether it is looking at everything;
* when the match cap or the byte cap drops hits, an explicit
  ``[truncated: ...]`` line says so and names the totals. Silent truncation
  would let the model conclude "no more matches exist" and stop searching.
"""

from __future__ import annotations

import fnmatch
import os
import re

from app.tools import tool
from app.tools.path_guard import resolve_search_path, workspace_root

# Directories that are never useful to a code search and are expensive to walk.
_SKIP_DIRS = frozenset({
    ".git", ".hg", ".svn", "__pycache__", ".pytest_cache", ".ruff_cache",
    ".mypy_cache", "node_modules", ".venv", "venv", ".tox", ".idea", ".vscode",
    "dist", "build", ".next", "coverage", "htmlcov", ".gradle", ".cache",
    "target", ".pytest_cache.d", ".DS_Store", ".ipynb_checkpoints",
})

DEFAULT_MAX_MATCHES = 50
MAX_MAX_MATCHES = 500
DEFAULT_MAX_BYTES = 20_000
MAX_MAX_BYTES = 200_000
MAX_LINE_CHARS = 500
# Files above this are skipped rather than streamed; a 5MB log tells a code
# search nothing and the byte cap would cut it mid-line anyway.
_MAX_SCAN_BYTES = 2_000_000


def _clamp(value: int, low: int, high: int, default: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        return default
    return max(low, min(high, value))


def _read_text(path: str) -> str | None:
    """Read a file as text, or return None when it is not searchable."""
    try:
        if os.path.getsize(path) > _MAX_SCAN_BYTES:
            return None
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read()
    except (OSError, ValueError):
        return None


def _compile(pattern: str, ignore_case: bool, fixed_string: bool) -> re.Pattern[str]:
    return re.compile(re.escape(pattern) if fixed_string else pattern, re.IGNORECASE if ignore_case else 0)


def _render_match(
    relative: str,
    line_number: int,
    line: str,
    byte_budget: int,
) -> tuple[str, int] | None:
    """Format one hit as ``path:line: text`` within the remaining byte budget."""
    stripped = line.rstrip("\n").replace("\t", "    ")
    if len(stripped) > MAX_LINE_CHARS:
        stripped = stripped[:MAX_LINE_CHARS] + " …[line clipped]"
    entry = f"{relative}:{line_number}: {stripped}\n"
    if byte_budget < len(entry.encode("utf-8")):
        return None
    return entry, len(entry.encode("utf-8"))


def _iter_files(root: str, include: str, exclude: str | None, max_files: int):
    """Yield searchable files under ``root`` in deterministic order."""
    include_patterns = [p for p in include.split() if p] or ["*"]
    exclude_patterns = [p for p in (exclude or "").split() if p]
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in _SKIP_DIRS and not d.startswith("."))
        for filename in sorted(filenames):
            full = os.path.join(dirpath, filename)
            relative = os.path.relpath(full, root)
            if not any(fnmatch.fnmatch(relative, p) or fnmatch.fnmatch(filename, p) for p in include_patterns):
                continue
            if any(fnmatch.fnmatch(relative, p) or fnmatch.fnmatch(filename, p) for p in exclude_patterns):
                continue
            yield full, relative
            count += 1
            if count >= max_files:
                return


@tool(
    description=(
        "Search file contents with a regular expression across a directory tree. "
        "Returns every hit as 'path:line: matching text' so results can be cited or "
        "opened directly with read_file. Prefer this over read_file when you do not "
        "yet know which file holds the code, and over run_command('grep ...') so the "
        "result is bounded and reports what it left out. Binary files and common "
        "build/vendor directories (.git, node_modules, __pycache__) are skipped."
    ),
    parameters={
        "type": "object",
        "properties": {
            "pattern": {
                "type": "string",
                "description": "Python regular expression, e.g. 'def (grep|search_code)\\(' or 'class .*Config'.",
            },
            "path": {
                "type": "string",
                "description": "File or directory to search. Defaults to the workspace root.",
                "default": ".",
            },
            "glob": {
                "type": "string",
                "description": (
                    "Space-separated filename globs limiting which files are read, "
                    "e.g. '*.py' or '*.py *.ts'. Matches the relative path or the "
                    "basename. Defaults to '*' (every file)."
                ),
                "default": "*",
            },
            "ignore_case": {
                "type": "boolean",
                "description": "Case-insensitive match. Default false.",
                "default": False,
            },
            "fixed_string": {
                "type": "boolean",
                "description": "Treat pattern as a literal string instead of a regex. Default false.",
                "default": False,
            },
            "context_lines": {
                "type": "integer",
                "description": "Lines of surrounding context to include per hit. Default 0.",
                "default": 0,
            },
            "max_matches": {
                "type": "integer",
                "description": f"Matches to return, 1-{MAX_MAX_MATCHES} (default {DEFAULT_MAX_MATCHES}).",
                "default": DEFAULT_MAX_MATCHES,
            },
            "max_bytes": {
                "type": "integer",
                "description": f"Byte cap for the returned text, 1000-{MAX_MAX_BYTES} (default {DEFAULT_MAX_BYTES}).",
                "default": DEFAULT_MAX_BYTES,
            },
            "exclude": {
                "type": "string",
                "description": "Space-separated globs to skip, applied after 'glob'.",
                "default": "",
            },
        },
        "required": ["pattern"],
    },
)
async def grep(
    pattern: str,
    path: str = ".",
    glob: str = "*",
    ignore_case: bool = False,
    fixed_string: bool = False,
    context_lines: int = 0,
    max_matches: int = DEFAULT_MAX_MATCHES,
    max_bytes: int = DEFAULT_MAX_BYTES,
    exclude: str = "",
) -> str:
    """Regex search across a directory tree, returning citable path:line hits."""
    try:
        regex = _compile(pattern, bool(ignore_case), bool(fixed_string))
    except re.error as exc:
        return f"Error: invalid regular expression {pattern!r}: {exc}"

    root, reason = resolve_search_path(path)
    if not root:
        return f"grep failed: {reason}"

    match_cap = _clamp(max_matches, 1, MAX_MAX_MATCHES, DEFAULT_MAX_MATCHES)
    byte_cap = _clamp(max_bytes, 1000, MAX_MAX_BYTES, DEFAULT_MAX_BYTES)
    context = _clamp(context_lines, 0, 5, 0)
    file_cap = 5000

    search_root = root if os.path.isdir(root) else os.path.dirname(root)
    single_file = None if os.path.isdir(root) else root
    # Label every hit relative to the workspace root, not to `search_root`, so
    # `path:line` stays stable and directly openable no matter which subdirectory
    # the search was pointed at.
    label_root = os.path.commonpath([search_root, workspace_root()])

    entries: list[str] = []
    total = 0
    files_scanned = 0
    files_skipped = 0
    byte_used = 0
    stop_reason = ""
    scanned_any = False
    # Once the byte cap trips we stop emitting but keep counting, so the
    # reported total is the real one. Reporting "showing 5 of 5" after dropping
    # 8 hits would tell the model the search space is exhausted when it is not.
    emitting = True
    # A match cap stops the walk, so the total is a lower bound ("3+"), not exact.
    count_exact = True

    for full, relative in _iter_files(search_root, glob, exclude, file_cap):
        if single_file is not None and os.path.abspath(full) != single_file:
            continue
        files_scanned += 1
        text = _read_text(full)
        if text is None:
            files_skipped += 1
            continue
        scanned_any = True
        label = os.path.relpath(full, label_root)
        lines = text.splitlines()
        for index, line in enumerate(lines):
            if not regex.search(line):
                continue
            total += 1
            if total > match_cap:
                count_exact = False
                stop_reason = stop_reason or f"match cap {match_cap} reached"
                break
            if not emitting:
                continue
            block: list[tuple[int, str]] = [(index + 1, line)]
            for offset in range(1, context + 1):
                if index - offset >= 0:
                    block.insert(0, (index - offset + 1, lines[index - offset]))
                if index + offset < len(lines):
                    block.append((index + offset + 1, lines[index + offset]))
            for number, block_line in block:
                rendered = _render_match(label, number, block_line, byte_cap - byte_used)
                if rendered is None:
                    stop_reason = stop_reason or f"byte cap {byte_cap} reached"
                    emitting = False
                    break
                entries.append(rendered[0])
                byte_used += rendered[1]
        if stop_reason.startswith("match cap"):
            break

    total_matches = total
    qualifier = "" if count_exact else "+"
    header = (
        f"grep {pattern!r} in {search_root}: "
        f"showing {len(entries)} of {total_matches}{qualifier} matching lines "
        f"across {files_scanned} scanned files ({files_skipped} unreadable/oversized skipped)"
    )
    if not total_matches:
        return f"{header}\nno matches"
    if len(entries) == 0:
        return (
            f"{header}\nno matches returned because {stop_reason}; "
            f"the pattern still has {total_matches}{qualifier} matching lines"
        )
    body = "".join(entries)
    if stop_reason:
        body += (
            f"[truncated: {stop_reason}; {len(entries)} of {total_matches}{qualifier} "
            f"matching lines shown, {byte_used} of {byte_cap} bytes used. "
            f"Narrow the pattern, set glob, or raise max_matches/max_bytes to see the rest.]"
        )
    elif not scanned_any:
        return f"{header}\nno searchable text files matched the given glob"
    return f"{header}\n{body}"


@tool(
    description=(
        "Find files by name using glob patterns (e.g. '**/test_*.py', '*.ts', "
        "'**/migrations/*.py'). Returns paths sorted by modification time, newest "
        "first, optionally with size and mtime. Use this to locate a file by name "
        "when its exact path is unknown; use grep to find where inside a file "
        "something is defined."
    ),
    parameters={
        "type": "object",
        "properties": {
            "patterns": {
                "type": "string",
                "description": (
                    "Space-separated glob patterns. '*' matches within one path "
                    "segment, '**' matches across segments, '?' matches one char."
                ),
            },
            "path": {
                "type": "string",
                "description": "Directory to search. Defaults to the workspace root.",
                "default": ".",
            },
            "limit": {
                "type": "integer",
                "description": "Paths to return, 1-2000 (default 200).",
                "default": 200,
            },
            "include_metadata": {
                "type": "boolean",
                "description": "Append size and modification time to each path. Default false.",
                "default": False,
            },
            "respect_gitignore": {
                "type": "boolean",
                "description": "Skip paths ignored by a .gitignore in the search root. Default true.",
                "default": True,
            },
        },
        "required": ["patterns"],
    },
)
async def glob(
    patterns: str,
    path: str = ".",
    limit: int = 200,
    include_metadata: bool = False,
    respect_gitignore: bool = True,
) -> str:
    """Filename glob search returning matching paths, newest first."""
    root, reason = resolve_search_path(path)
    if not root:
        return f"glob failed: {reason}"
    if not os.path.isdir(root):
        return f"glob failed: not a directory: {root}"

    pattern_list = [p for p in patterns.split() if p]
    if not pattern_list:
        return "glob failed: no patterns provided"
    cap = _clamp(limit, 1, 2000, 200)

    ignored = _load_gitignore_patterns(root) if respect_gitignore else None

    matches: list[tuple[float, str, os.stat_result]] = []
    total = 0
    for dirpath, dirnames, filenames in os.walk(root):
        if ignored:
            dirnames[:] = [d for d in sorted(dirnames) if not _gitignored(os.path.join(dirpath, d), root, ignored)]
        else:
            dirnames[:] = sorted(dirnames)
        if any(part in _SKIP_DIRS or part.startswith(".") for part in os.path.relpath(dirpath, root).split(os.sep) if part != "."):
            dirnames[:] = []
            continue
        for filename in sorted(filenames):
            full = os.path.join(dirpath, filename)
            relative = os.path.relpath(full, root)
            if ignored and _gitignored(full, root, ignored):
                continue
            if not any(fnmatch.fnmatch(relative, p) or fnmatch.fnmatch(filename, p) for p in pattern_list):
                continue
            try:
                stat = os.stat(full)
            except OSError:
                continue
            total += 1
            matches.append((stat.st_mtime, relative, stat))

    matches.sort(key=lambda item: (-item[0], item[1]))
    shown = matches[:cap]
    if include_metadata:
        from datetime import datetime

        body = "\n".join(
            f"{relative}  ({stat.st_size} bytes, modified {datetime.fromtimestamp(mtime).isoformat(timespec='seconds')})"
            for mtime, relative, stat in shown
        )
    else:
        body = "\n".join(relative for _, relative, _ in shown)

    header = f"glob {patterns!r} in {root}: showing {len(shown)} of {total} matching paths"
    if not total:
        return f"{header}\nno matches"
    if total > cap:
        body += f"\n[truncated: path cap {cap} reached; {len(shown)} of {total} paths shown. Raise limit or narrow the pattern.]"
    return f"{header}\n{body}"


def _load_gitignore_patterns(root: str) -> list[str] | None:
    gitignore = os.path.join(root, ".gitignore")
    if not os.path.isfile(gitignore):
        return None
    try:
        with open(gitignore, encoding="utf-8", errors="replace") as handle:
            lines = [line.strip() for line in handle]
    except OSError:
        return None
    return [line for line in lines if line and not line.startswith("#")]


def _gitignored(path: str, root: str, patterns: list[str]) -> bool:
    relative = os.path.relpath(path, root)
    parts = relative.split(os.sep)
    for raw in patterns:
        pattern = raw.rstrip("/")
        if fnmatch.fnmatch(relative, pattern) or fnmatch.fnmatch(parts[-1], pattern):
            return True
        if any(fnmatch.fnmatch(part, pattern) for part in parts):
            return True
        if pattern.startswith("/") and fnmatch.fnmatch(relative, pattern.lstrip("/")):
            return True
    return False


__all__ = ["glob", "grep"]
