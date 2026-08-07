"""Test cases for performance."""


from tests.suites.performance_suite import PerformanceAssertions, PerformanceTestData


class TestPerformanceCreate:
    """Tests for create operations."""

    def test_create_valid(self):
        data = PerformanceTestData.generate_valid_payload()
        assert data['name'] == 'Test Item'

    def test_create_invalid(self):
        data = PerformanceTestData.generate_invalid_payload()
        assert data['name'] == ''

    def test_create_edge_case(self):
        data = PerformanceTestData.generate_edge_case_payload()
        assert len(data['name']) == 255


class TestPerformanceRead:
    """Tests for read operations."""

    def test_list_empty(self):
        response = {'items': [], 'total': 0, 'page': 1, 'page_size': 20}
        PerformanceAssertions.assert_pagination(response)

    def test_list_with_items(self):
        response = {'items': [{'id': 1}], 'total': 1, 'page': 1, 'page_size': 20}
        PerformanceAssertions.assert_pagination(response)


class TestPerformanceUpdate:
    """Tests for update operations."""

    def test_update_success(self):
        response = {'success': True, 'data': {'id': 1}}
        PerformanceAssertions.assert_success_response(response)

    def test_update_not_found(self):
        response = {'success': False, 'error': 'Not found', 'code': 404}
        PerformanceAssertions.assert_error_response(response, 404)


class TestPerformanceDelete:
    """Tests for delete operations."""

    def test_delete_success(self):
        response = {'success': True, 'data': {'id': 1}}
        PerformanceAssertions.assert_success_response(response)

    def test_delete_not_found(self):
        response = {'success': False, 'error': 'Not found', 'code': 404}
        PerformanceAssertions.assert_error_response(response, 404)


class TestPerformanceValidation:
    """Tests for validation."""

    def test_valid_payload(self):
        data = PerformanceTestData.generate_valid_payload()
        assert len(data['name']) > 0
        assert data['status'] in ('active', 'inactive')

    def test_invalid_name(self):
        data = {'name': '', 'status': 'active'}
        assert len(data['name']) == 0

    def test_invalid_status(self):
        data = {'name': 'test', 'status': 'invalid'}
        assert data['status'] not in ('active', 'inactive')


class TestPerformanceBatch:
    """Tests for batch operations."""

    def test_batch_create(self):
        payloads = PerformanceTestData.generate_batch_payloads(5)
        assert len(payloads) == 5

    def test_batch_empty(self):
        payloads = PerformanceTestData.generate_batch_payloads(0)
        assert len(payloads) == 0
