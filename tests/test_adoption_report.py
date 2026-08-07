"""Tests for adoption report."""


from app.reports.adoption_report import (
    AdoptionReportConfig,
    AdoptionReportGenerator,
)


class TestAdoptionReportGenerator:
    """Tests for report generator."""

    def test_generate(self):
        gen = AdoptionReportGenerator()
        config = AdoptionReportConfig(title='Test Report', report_type='summary')
        result = gen.generate(config)
        assert result.title == 'Test Report'

    def test_export_json(self):
        gen = AdoptionReportGenerator()
        config = AdoptionReportConfig(title='Test')
        report = gen.generate(config)
        output = gen.export(report.id, 'json')
        assert len(output) > 0

    def test_save_template(self):
        gen = AdoptionReportGenerator()
        config = AdoptionReportConfig(title='Template')
        gen.save_template('test_tpl', config)
        assert gen.get_template('test_tpl') is not None
