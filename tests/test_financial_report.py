"""Tests for financial report."""


from app.reports.financial_report import (
    FinancialReportConfig,
    FinancialReportGenerator,
)


class TestFinancialReportGenerator:
    """Tests for report generator."""

    def test_generate(self):
        gen = FinancialReportGenerator()
        config = FinancialReportConfig(title='Test Report', report_type='summary')
        result = gen.generate(config)
        assert result.title == 'Test Report'

    def test_export_json(self):
        gen = FinancialReportGenerator()
        config = FinancialReportConfig(title='Test')
        report = gen.generate(config)
        output = gen.export(report.id, 'json')
        assert len(output) > 0

    def test_save_template(self):
        gen = FinancialReportGenerator()
        config = FinancialReportConfig(title='Template')
        gen.save_template('test_tpl', config)
        assert gen.get_template('test_tpl') is not None
