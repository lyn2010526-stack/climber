"""In-memory registry of evaluation reports for the API layer."""

from __future__ import annotations

from collections import OrderedDict

from app.core.evaluation.models import EvaluationReport


class ReportStore:
    """Bounded FIFO registry of reports keyed by report id."""

    def __init__(self, max_reports: int = 256) -> None:
        self._max = max_reports
        self._reports: OrderedDict[str, EvaluationReport] = OrderedDict()

    def save(self, report: EvaluationReport) -> EvaluationReport:
        """Store a report, evicting the oldest when over capacity."""
        self._reports[report.report_id] = report
        while len(self._reports) > self._max:
            self._reports.popitem(last=False)
        return report

    def get(self, report_id: str) -> EvaluationReport | None:
        return self._reports.get(report_id)

    def list_all(self) -> list[EvaluationReport]:
        """Return stored reports in insertion order."""
        return list(self._reports.values())

    def clear(self) -> None:
        self._reports.clear()


REPORT_STORE = ReportStore()
