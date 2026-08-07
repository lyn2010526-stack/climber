"""Data processor: index - Handles data transformation and processing."""

from __future__ import annotations

import statistics
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TypeVar

import structlog

logger = structlog.get_logger()

T = TypeVar('T')


@dataclass
class IndexConfig:
    """Configuration for index processor."""
    batch_size: int = 1000
    max_retries: int = 3
    timeout_seconds: int = 30
    enable_caching: bool = True
    cache_ttl: int = 300
    compression_enabled: bool = False
    parallel_workers: int = 4
    error_threshold: float = 0.05
    sampling_rate: float = 1.0


@dataclass
class IndexResult:
    """Result from index processing."""
    success: bool = False
    records_processed: int = 0
    records_failed: int = 0
    processing_time_ms: float = 0.0
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class IndexMetrics:
    """Metrics for index processor."""
    total_processed: int = 0
    total_failed: int = 0
    avg_processing_time: float = 0.0
    throughput_per_second: float = 0.0
    error_rate: float = 0.0
    cache_hit_rate: float = 0.0


class IndexProcessor:
    """Main processor for index."""

    def __init__(self, config: IndexConfig | None = None):
        self.config = config or IndexConfig()
        self._cache: dict[str, Any] = {}
        self._metrics = IndexMetrics()
        self._error_log: list[dict[str, Any]] = []

    @property
    def metrics(self) -> IndexMetrics:
        """Get current metrics."""
        return self._metrics

    def process_batch(
        self, records: list[dict[str, Any]]
    ) -> IndexResult:
        """Process a batch of records."""
        start = datetime.utcnow()
        processed = 0
        failed = 0
        errors: list[str] = []

        for i in range(0, len(records), self.config.batch_size):
            batch = records[i:i + self.config.batch_size]
            for record in batch:
                try:
                    self._process_single(record)
                    processed += 1
                except Exception as e:
                    failed += 1
                    errors.append(str(e))
                    self._log_error(record, str(e), 20)

        elapsed = (datetime.utcnow() - start).total_seconds() * 1000
        self._update_metrics(processed, failed, elapsed)

        return IndexResult(
            success=failed <= len(records) * self.config.error_threshold,
            records_processed=processed,
            records_failed=failed,
            processing_time_ms=elapsed,
            errors=errors,
        )

    def _process_single(self, record: dict[str, Any]) -> dict[str, Any]:
        """Process a single record."""
        if not record:
            raise ValueError('Empty record')
        result = dict(record)
        result['_processed_at'] = datetime.utcnow().isoformat()
        result['_processor_id'] = 'index'
        return result

    def _log_error(self, record: dict[str, Any], error: str, processor_id: int) -> None:
        """Log processing error."""
        self._error_log.append({
            'timestamp': datetime.utcnow().isoformat(),
            'error': error,
            'record_id': record.get('id', 'unknown'),
            'processor_id': processor_id,
        })

    def _update_metrics(self, processed: int, failed: int, elapsed_ms: float) -> None:
        """Update internal metrics."""
        self._metrics.total_processed += processed
        self._metrics.total_failed += failed
        total = processed + failed
        if elapsed_ms > 0:
            self._metrics.throughput_per_second = total / (elapsed_ms / 1000)
        if total > 0:
            self._metrics.error_rate = failed / total

    def get_errors(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent errors."""
        return self._error_log[-limit:]

    def clear_cache(self) -> int:
        """Clear processing cache."""
        size = len(self._cache)
        self._cache.clear()
        return size


class IndexTransformer:
    """Data transformer for index."""

    @staticmethod
    def normalize(data: list[float]) -> list[float]:
        """Normalize data to 0-1 range."""
        if not data:
            return []
        min_val = min(data)
        max_val = max(data)
        if min_val == max_val:
            return [0.5] * len(data)
        return [(x - min_val) / (max_val - min_val) for x in data]

    @staticmethod
    def standardize(data: list[float]) -> list[float]:
        """Standardize data to zero mean unit variance."""
        if len(data) < 2:
            return [0.0] * len(data)
        mean = statistics.mean(data)
        stdev = statistics.stdev(data)
        if stdev == 0:
            return [0.0] * len(data)
        return [(x - mean) / stdev for x in data]

    @staticmethod
    def moving_average(data: list[float], window: int = 5) -> list[float]:
        """Calculate moving average."""
        if window <= 0 or len(data) < window:
            return data
        result = []
        for i in range(len(data) - window + 1):
            window_data = data[i:i + window]
            result.append(sum(window_data) / window)
        return result

    @staticmethod
    def detect_outliers(data: list[float], threshold: float = 2.0) -> list[int]:
        """Detect outlier indices using z-score."""
        if len(data) < 3:
            return []
        mean = statistics.mean(data)
        stdev = statistics.stdev(data)
        if stdev == 0:
            return []
        return [i for i, x in enumerate(data) if abs((x - mean) / stdev) > threshold]

    @staticmethod
    def interpolate_missing(data: list[float | None]) -> list[float]:
        """Interpolate missing values."""
        result = []
        last_valid = 0.0
        for i, x in enumerate(data):
            if x is not None:
                result.append(x)
                last_valid = x
            else:
                next_valid = last_valid
                for j in range(i + 1, len(data)):
                    if data[j] is not None:
                        next_valid = data[j]
                        break
                result.append((last_valid + next_valid) / 2)
        return result


class IndexAggregator:
    """Data aggregator for index."""

    @staticmethod
    def sum_by_key(records: list[dict[str, Any]], key: str) -> float:
        """Sum values by key."""
        return sum(r.get(key, 0) for r in records if isinstance(r.get(key), (int, float)))

    @staticmethod
    def count_by_key(records: list[dict[str, Any]], key: str) -> dict[str, int]:
        """Count records by key value."""
        counts: dict[str, int] = defaultdict(int)
        for r in records:
            val = str(r.get(key, 'unknown'))
            counts[val] += 1
        return dict(counts)

    @staticmethod
    def group_by(records: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
        """Group records by key."""
        groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for r in records:
            groups[str(r.get(key, 'unknown'))].append(r)
        return dict(groups)

    @staticmethod
    def aggregate_stats(data: list[float]) -> dict[str, float]:
        """Calculate aggregate statistics."""
        if not data:
            return {"count": 0, "sum": 0, "mean": 0, "min": 0, "max": 0}
        return {
            "count": len(data),
            "sum": sum(data),
            "mean": statistics.mean(data),
            "min": min(data),
            "max": max(data),
        }


class IndexValidator:
    """Data validator for index."""

    @staticmethod
    def validate_schema(record: dict[str, Any], schema: dict[str, type]) -> list[str]:
        """Validate record against schema."""
        errors = []
        for field_name, field_type in schema.items():
            if field_name not in record:
                errors.append(f'Missing field: {field_name}')
            elif not isinstance(record[field_name], field_type):
                errors.append(f'Invalid type for {field_name}: expected {field_type.__name__}')
        return errors

    @staticmethod
    def validate_range(value: float, min_val: float, max_val: float) -> bool:
        """Validate numeric range."""
        return min_val <= value <= max_val

    @staticmethod
    def validate_required(record: dict[str, Any], fields: list[str]) -> list[str]:
        """Validate required fields."""
        return [f for f in fields if f not in record or record[f] is None]

    @staticmethod
    def validate_uniqueness(records: list[dict[str, Any]], key: str) -> list[int]:
        """Find duplicate indices."""
        seen: dict[str, int] = {}
        duplicates = []
        for i, r in enumerate(records):
            val = str(r.get(key, ''))
            if val in seen:
                duplicates.append(i)
            seen[val] = i
        return duplicates
