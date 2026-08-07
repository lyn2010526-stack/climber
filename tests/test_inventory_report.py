"""Tests for inventory report."""


from app.reports.inventory_report import (
    InventoryReportConfig,
    InventoryReportGenerator,
)


class TestInventoryReportGenerator:
    """Tests for report generator."""

    def test_generate(self):
        gen = InventoryReportGenerator()
        config = InventoryReportConfig(title='Test Report', report_type='summary')
        result = gen.generate(config)
        assert result.title == 'Test Report'

    def test_export_json(self):
        gen = InventoryReportGenerator()
        config = InventoryReportConfig(title='Test')
        report = gen.generate(config)
        output = gen.export(report.id, 'json')
        assert len(output) > 0

    def test_save_template(self):
        gen = InventoryReportGenerator()
        config = InventoryReportConfig(title='Template')
        gen.save_template('test_tpl', config)
        assert gen.get_template('test_tpl') is not None
