from collections.abc import Callable
from typing import cast

from .cli import main

# cli.main is intentionally untyped (standalone stdlib-only entrypoint); cast to
# a typed callable so this module stays clean under strict mypy.
_main = cast("Callable[[], int]", main)

raise SystemExit(_main())
