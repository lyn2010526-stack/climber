"""Test cases for localization."""


from tests.suites.localization_suite import LocalizationAssertions, LocalizationTestData


class TestLocalizationCreate:
    """Tests for create operations."""

    def test_create_valid(self):
        data = LocalizationTestData.generate_valid_payload()
        assert data['name'] == 'Test Item'

    def test_create_invalid(self):
        data = LocalizationTestData.generate_invalid_payload()
        assert data['name'] == ''

    def test_create_edge_case(self):
        data = LocalizationTestData.generate_edge_case_payload()
        assert len(data['name']) == 255


class TestLocalizationRead:
    """Tests for read operations."""

    def test_list_empty(self):
        response = {'items': [], 'total': 0, 'page': 1, 'page_size': 20}
        LocalizationAssertions.assert_pagination(response)

    def test_list_with_items(self):
        response = {'items': [{'id': 1}], 'total': 1, 'page': 1, 'page_size': 20}
        LocalizationAssertions.assert_pagination(response)


class TestLocalizationUpdate:
    """Tests for update operations."""

    def test_update_success(self):
        response = {'success': True, 'data': {'id': 1}}
        LocalizationAssertions.assert_success_response(response)

    def test_update_not_found(self):
        response = {'success': False, 'error': 'Not found', 'code': 404}
        LocalizationAssertions.assert_error_response(response, 404)


class TestLocalizationDelete:
    """Tests for delete operations."""

    def test_delete_success(self):
        response = {'success': True, 'data': {'id': 1}}
        LocalizationAssertions.assert_success_response(response)

    def test_delete_not_found(self):
        response = {'success': False, 'error': 'Not found', 'code': 404}
        LocalizationAssertions.assert_error_response(response, 404)


class TestLocalizationValidation:
    """Tests for validation."""

    def test_valid_payload(self):
        data = LocalizationTestData.generate_valid_payload()
        assert len(data['name']) > 0
        assert data['status'] in ('active', 'inactive')

    def test_invalid_name(self):
        data = {'name': '', 'status': 'active'}
        assert len(data['name']) == 0

    def test_invalid_status(self):
        data = {'name': 'test', 'status': 'invalid'}
        assert data['status'] not in ('active', 'inactive')


class TestLocalizationBatch:
    """Tests for batch operations."""

    def test_batch_create(self):
        payloads = LocalizationTestData.generate_batch_payloads(5)
        assert len(payloads) == 5

    def test_batch_empty(self):
        payloads = LocalizationTestData.generate_batch_payloads(0)
        assert len(payloads) == 0
