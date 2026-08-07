"""Tests for app.tools.builtin_extended module."""

from __future__ import annotations

import importlib
from unittest import mock

import pytest

from app.tools.builtin_extended import (
    csv_parser_tool,
    json_transformer_tool,
    xml_processor_tool,
    data_validator_tool,
    data_converter_tool,
    data_aggregator_tool,
    data_filter_tool,
    data_sorter_tool,
    data_deduplicator_tool,
    data_normalizer_tool,
    data_sampler_tool,
    data_merger_tool,
    data_splitter_tool,
    data_enricher_tool,
    data_anonymizer_tool,
    data_masker_tool,
    password_generator_tool,
    password_strength_checker_tool,
    register_all,
)
from app.tools.builtin_extended.csv_parser import CsvParserTool
from app.tools.builtin_extended.password_generator import PasswordGeneratorTool


class TestCsvParserTool:
    """Tests for CsvParserTool class."""

    def test_execute(self):
        tool = CsvParserTool()
        result = tool.execute()
        assert result["tool"] == "csv_parser"

    def test_validate(self):
        tool = CsvParserTool()
        result = tool.validate()
        assert result["action"] == "validate"

    def test_configure(self):
        tool = CsvParserTool()
        result = tool.configure()
        assert result["action"] == "configure"

    def test_get_schema(self):
        tool = CsvParserTool()
        result = tool.get_schema()
        assert result["action"] == "get_schema"

    def test_get_info(self):
        tool = CsvParserTool()
        result = tool.get_info()
        assert result["action"] == "get_info"

    def test_get_capabilities(self):
        caps = CsvParserTool.get_capabilities()
        assert caps["name"] == "csv_parser"
        assert caps["version"] == "1.0.0"


class TestPasswordGeneratorTool:
    """Tests for PasswordGeneratorTool class."""

    def test_execute(self):
        tool = PasswordGeneratorTool()
        result = tool.execute()
        assert result["tool"] == "password_generator"

    def test_get_capabilities(self):
        caps = PasswordGeneratorTool.get_capabilities()
        assert caps["name"] == "password_generator"


class TestToolFunctions:
    """Tests for module-level tool functions."""

    def test_csv_parser_tool(self):
        result = csv_parser_tool()
        assert result["tool"] == "csv_parser"

    def test_json_transformer_tool(self):
        result = json_transformer_tool()
        assert result["tool"] == "json_transformer"

    def test_xml_processor_tool(self):
        result = xml_processor_tool()
        assert result["tool"] == "xml_processor"

    def test_data_validator_tool(self):
        result = data_validator_tool()
        assert result["tool"] == "data_validator"

    def test_data_converter_tool(self):
        result = data_converter_tool()
        assert result["tool"] == "data_converter"

    def test_data_aggregator_tool(self):
        result = data_aggregator_tool()
        assert result["tool"] == "data_aggregator"

    def test_data_filter_tool(self):
        result = data_filter_tool()
        assert result["tool"] == "data_filter"

    def test_data_sorter_tool(self):
        result = data_sorter_tool()
        assert result["tool"] == "data_sorter"

    def test_data_deduplicator_tool(self):
        result = data_deduplicator_tool()
        assert result["tool"] == "data_deduplicator"

    def test_data_normalizer_tool(self):
        result = data_normalizer_tool()
        assert result["tool"] == "data_normalizer"

    def test_data_sampler_tool(self):
        result = data_sampler_tool()
        assert result["tool"] == "data_sampler"

    def test_data_merger_tool(self):
        result = data_merger_tool()
        assert result["tool"] == "data_merger"

    def test_data_splitter_tool(self):
        result = data_splitter_tool()
        assert result["tool"] == "data_splitter"

    def test_data_enricher_tool(self):
        result = data_enricher_tool()
        assert result["tool"] == "data_enricher"

    def test_data_anonymizer_tool(self):
        result = data_anonymizer_tool()
        assert result["tool"] == "data_anonymizer"

    def test_data_masker_tool(self):
        result = data_masker_tool()
        assert result["tool"] == "data_masker"

    def test_password_generator_tool(self):
        result = password_generator_tool()
        assert result["tool"] == "password_generator"

    def test_password_strength_checker_tool(self):
        result = password_strength_checker_tool()
        assert result["tool"] == "password_strength_checker"


class TestRegisterAll:
    """Tests for register_all function."""

    def test_register_all_mock(self):
        """Test register_all with mocked registry."""
        import app.tools.builtin_extended as mod
        mock_registry = mock.Mock()
        with mock.patch.object(mod, "tool_registry", mock_registry):
            mod.register_all()
            assert mock_registry.register.call_count == 155


class TestToolClassesViaImport:
    """Test tool classes by importing from individual modules."""

    def test_csv_parser_class(self):
        from app.tools.builtin_extended.csv_parser import CsvParserTool
        tool = CsvParserTool()
        assert tool.execute()["tool"] == "csv_parser"

    def test_json_transformer_class(self):
        from app.tools.builtin_extended.json_transformer import JsonTransformerTool
        tool = JsonTransformerTool()
        assert tool.execute()["tool"] == "json_transformer"

    def test_xml_processor_class(self):
        from app.tools.builtin_extended.xml_processor import XmlProcessorTool
        tool = XmlProcessorTool()
        assert tool.execute()["tool"] == "xml_processor"

    def test_data_validator_class(self):
        from app.tools.builtin_extended.data_validator import DataValidatorTool
        tool = DataValidatorTool()
        assert tool.execute()["tool"] == "data_validator"

    def test_password_strength_checker_class(self):
        from app.tools.builtin_extended.password_strength_checker import PasswordStrengthCheckerTool
        tool = PasswordStrengthCheckerTool()
        assert tool.execute()["tool"] == "password_strength_checker"
