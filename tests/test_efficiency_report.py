"""Tests for efficiency report."""


from app.reports.efficiency_report import (
    EfficiencyReportConfig,
    EfficiencyReportGenerator,
)


class TestEfficiencyReportGenerator:
    """Tests for report generator."""

    def test_generate(self):
        gen = EfficiencyReportGenerator()
        config = EfficiencyReportConfig(title='Test Report', report_type='summary')
        result = gen.generate(config)
        assert result.title == 'Test Report'

    def test_export_json(self):
        gen = EfficiencyReportGenerator()
        config = EfficiencyReportConfig(title='Test')
        report = gen.generate(config)
        output = gen.export(report.id, 'json')
        assert len(output) > 0

    def test_save_template(self):
        gen = EfficiencyReportGenerator()
        config = EfficiencyReportConfig(title='Template')
        gen.save_template('test_tpl', config)
        assert gen.get_template('test_tpl') is not None
