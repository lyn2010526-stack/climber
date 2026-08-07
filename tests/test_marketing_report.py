"""Tests for marketing report."""


from app.reports.marketing_report import (
    MarketingReportConfig,
    MarketingReportGenerator,
)


class TestMarketingReportGenerator:
    """Tests for report generator."""

    def test_generate(self):
        gen = MarketingReportGenerator()
        config = MarketingReportConfig(title='Test Report', report_type='summary')
        result = gen.generate(config)
        assert result.title == 'Test Report'

    def test_export_json(self):
        gen = MarketingReportGenerator()
        config = MarketingReportConfig(title='Test')
        report = gen.generate(config)
        output = gen.export(report.id, 'json')
        assert len(output) > 0

    def test_save_template(self):
        gen = MarketingReportGenerator()
        config = MarketingReportConfig(title='Template')
        gen.save_template('test_tpl', config)
        assert gen.get_template('test_tpl') is not None
