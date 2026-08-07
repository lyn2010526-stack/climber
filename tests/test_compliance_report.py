"""Tests for compliance report."""


from app.reports.compliance_report import (
    ComplianceReportConfig,
    ComplianceReportGenerator,
)


class TestComplianceReportGenerator:
    """Tests for report generator."""

    def test_generate(self):
        gen = ComplianceReportGenerator()
        config = ComplianceReportConfig(title='Test Report', report_type='summary')
        result = gen.generate(config)
        assert result.title == 'Test Report'

    def test_export_json(self):
        gen = ComplianceReportGenerator()
        config = ComplianceReportConfig(title='Test')
        report = gen.generate(config)
        output = gen.export(report.id, 'json')
        assert len(output) > 0

    def test_save_template(self):
        gen = ComplianceReportGenerator()
        config = ComplianceReportConfig(title='Template')
        gen.save_template('test_tpl', config)
        assert gen.get_template('test_tpl') is not None
