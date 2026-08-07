"""Tests for filter data processor."""


from app.processors.filter_processor import (
    FilterAggregator,
    FilterProcessor,
    FilterTransformer,
    FilterValidator,
)


class TestFilterProcessor:
    """Tests for processor."""

    def test_process_empty_batch(self):
        proc = FilterProcessor()
        result = proc.process_batch([])
        assert result.records_processed == 0

    def test_process_single_record(self):
        proc = FilterProcessor()
        result = proc.process_batch([{'id': 1, 'data': 'test'}])
        assert result.records_processed == 1
        assert result.success

    def test_process_multiple_records(self):
        proc = FilterProcessor()
        records = [{'id': i, 'value': i * 10} for i in range(100)]
        result = proc.process_batch(records)
        assert result.records_processed == 100

    def test_empty_record_raises(self):
        proc = FilterProcessor()
        result = proc.process_batch([{}])
        assert result.records_failed == 1

    def test_metrics_updated(self):
        proc = FilterProcessor()
        proc.process_batch([{'id': 1}])
        assert proc.metrics.total_processed == 1


class TestFilterTransformer:
    """Tests for transformer."""

    def test_normalize(self):
        result = FilterTransformer.normalize([10, 20, 30])
        assert result[0] == 0.0
        assert result[-1] == 1.0

    def test_standardize(self):
        result = FilterTransformer.standardize([1, 2, 3, 4, 5])
        assert len(result) == 5

    def test_moving_average(self):
        result = FilterTransformer.moving_average([1, 2, 3, 4, 5], window=3)
        assert result[0] == 2.0
        assert result[-1] == 4.0

    def test_detect_outliers(self):
        data = [1, 2, 3, 4, 5, 100]
        outliers = FilterTransformer.detect_outliers(data)
        assert 5 in outliers

    def test_interpolate_missing(self):
        data = [1.0, None, 3.0]
        result = FilterTransformer.interpolate_missing(data)
        assert result[1] == 2.0


class TestFilterAggregator:
    """Tests for aggregator."""

    def test_sum_by_key(self):
        records = [{'val': 10}, {'val': 20}, {'val': 30}]
        total = FilterAggregator.sum_by_key(records, 'val')
        assert total == 60

    def test_count_by_key(self):
        records = [{'cat': 'a'}, {'cat': 'b'}, {'cat': 'a'}]
        counts = FilterAggregator.count_by_key(records, 'cat')
        assert counts['a'] == 2

    def test_group_by(self):
        records = [{'type': 'x', 'v': 1}, {'type': 'y', 'v': 2}]
        groups = FilterAggregator.group_by(records, 'type')
        assert 'x' in groups
        assert 'y' in groups

    def test_aggregate_stats(self):
        stats = FilterAggregator.aggregate_stats([1, 2, 3, 4, 5])
        assert stats['count'] == 5
        assert stats['mean'] == 3.0


class TestFilterValidator:
    """Tests for validator."""

    def test_validate_schema_valid(self):
        record = {'id': 1, 'name': 'test'}
        schema = {'id': int, 'name': str}
        errors = FilterValidator.validate_schema(record, schema)
        assert len(errors) == 0

    def test_validate_schema_missing(self):
        record = {'id': 1}
        schema = {'id': int, 'name': str}
        errors = FilterValidator.validate_schema(record, schema)
        assert len(errors) == 1

    def test_validate_range(self):
        assert FilterValidator.validate_range(5, 1, 10)
        assert not FilterValidator.validate_range(15, 1, 10)

    def test_validate_required(self):
        record = {'id': 1}
        missing = FilterValidator.validate_required(record, ['id', 'name'])
        assert 'name' in missing

    def test_validate_uniqueness(self):
        records = [{'id': 1}, {'id': 2}, {'id': 1}]
        dups = FilterValidator.validate_uniqueness(records, 'id')
        assert 2 in dups
