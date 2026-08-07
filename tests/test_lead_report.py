"""Tests for lead report."""


from app.reports.lead_report import (
    LeadReportConfig,
    LeadReportGenerator,
)


class TestLeadReportGenerator:
    """Tests for report generator."""

    def test_generate(self):
        gen = LeadReportGenerator()
        config = LeadReportConfig(title='Test Report', report_type='summary')
        result = gen.generate(config)
        assert result.title == 'Test Report'

    def test_export_json(self):
        gen = LeadReportGenerator()
        config = LeadReportConfig(title='Test')
        report = gen.generate(config)
        output = gen.export(report.id, 'json')
        assert len(output) > 0

    def test_save_template(self):
        gen = LeadReportGenerator()
        config = LeadReportConfig(title='Template')
        gen.save_template('test_tpl', config)
        assert gen.get_template('test_tpl') is not None
