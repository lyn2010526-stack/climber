"""Tests for risk report."""


from app.reports.risk_report import (
    RiskReportConfig,
    RiskReportGenerator,
)


class TestRiskReportGenerator:
    """Tests for report generator."""

    def test_generate(self):
        gen = RiskReportGenerator()
        config = RiskReportConfig(title='Test Report', report_type='summary')
        result = gen.generate(config)
        assert result.title == 'Test Report'

    def test_export_json(self):
        gen = RiskReportGenerator()
        config = RiskReportConfig(title='Test')
        report = gen.generate(config)
        output = gen.export(report.id, 'json')
        assert len(output) > 0

    def test_save_template(self):
        gen = RiskReportGenerator()
        config = RiskReportConfig(title='Template')
        gen.save_template('test_tpl', config)
        assert gen.get_template('test_tpl') is not None
