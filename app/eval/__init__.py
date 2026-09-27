"""Real evaluation runtime for Climber.

The competition brief for this project is *"build and evaluate production-grade
agent harnesses"*, so an evaluation endpoint that only inserts a database row is
worth nothing. This package turns the ARC-Bench adapter under
``adapters/arcbench/`` into a service the ``/eval`` API can call for a real
measurement.

Three properties drive every design decision here:

1. **No invented numbers.** A score only ever appears in this package when it
   was derived from a real measurement of a real run. See :mod:`app.eval.scoring`.
2. **Inconclusive is propagated faithfully.** When the test infrastructure or a
   usable report is missing, the affected rows are reported as
   :data:`~app.eval.types.Verdict.INCONCLUSIVE` with a reason, and no score.
   A fabricated number is worse than no number.
3. **Everything is re-readable.** Every run stores an evidence artifact, and the
   score table is recomputed from that artifact rather than cached, so a run can
   be reproduced without re-executing it.

Public surface:

- :mod:`app.eval.types` - verdicts, capability checks, score tables.
- :mod:`app.eval.targets` - the evaluation target registry.
- :mod:`app.eval.service` - ``EvaluationService.run()`` and persistence.
- :mod:`app.eval.persistence` - async ORM access against the existing eval tables.
- :mod:`app.eval.scoring` - evidence to score-table reduction.
"""

from app.eval.errors import EvaluationError, TargetNotFoundError, TargetSetupError
from app.eval.service import EvaluationService
from app.eval.types import (
    CapabilityCheck,
    CaseRow,
    Evidence,
    RunStatus,
    ScoreTable,
    TargetRunResult,
    Verdict,
    capability_from_mapping,
    run_result_from_mapping,
    target_run_result_from_mapping,
)

__all__ = [
    "CaseRow",
    "CapabilityCheck",
    "EvaluationError",
    "EvaluationService",
    "Evidence",
    "RunStatus",
    "ScoreTable",
    "TargetNotFoundError",
    "TargetRunResult",
    "TargetSetupError",
    "Verdict",
    "capability_from_mapping",
    "run_result_from_mapping",
    "target_run_result_from_mapping",
]
