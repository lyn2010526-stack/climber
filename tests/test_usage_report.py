"""Tests for usage report."""


from app.reports.usage_report import (
    UsageReportConfig,
    UsageReportGenerator,
)


class TestUsageReportGenerator:
    """Tests for report generator."""

    def test_generate(self):
        gen = UsageReportGenerator()
        config = UsageReportConfig(title='Test Report', report_type='summary')
        result = gen.generate(config)
        assert result.title == 'Test Report'

    def test_export_json(self):
        gen = UsageReportGenerator()
        config = UsageReportConfig(title='Test')
        report = gen.generate(config)
        output = gen.export(report.id, 'json')
        assert len(output) > 0

    def test_save_template(self):
        gen = UsageReportGenerator()
        config = UsageReportConfig(title='Template')
        gen.save_template('test_tpl', config)
        assert gen.get_template('test_tpl') is not None
