"""Tests for satisfaction report."""


from app.reports.satisfaction_report import (
    SatisfactionReportConfig,
    SatisfactionReportGenerator,
)


class TestSatisfactionReportGenerator:
    """Tests for report generator."""

    def test_generate(self):
        gen = SatisfactionReportGenerator()
        config = SatisfactionReportConfig(title='Test Report', report_type='summary')
        result = gen.generate(config)
        assert result.title == 'Test Report'

    def test_export_json(self):
        gen = SatisfactionReportGenerator()
        config = SatisfactionReportConfig(title='Test')
        report = gen.generate(config)
        output = gen.export(report.id, 'json')
        assert len(output) > 0

    def test_save_template(self):
        gen = SatisfactionReportGenerator()
        config = SatisfactionReportConfig(title='Template')
        gen.save_template('test_tpl', config)
        assert gen.get_template('test_tpl') is not None
