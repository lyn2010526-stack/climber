"""Register MCP plugin tools with the global tool registry."""

from __future__ import annotations

import logging

from app.tools import tool_registry

logger = logging.getLogger(__name__)


def register_mcp_plugins() -> int:
    """Register all MCP plugin tools. Returns count of registered tools."""
    count = 0

    # Sandbox Runtime tools
    try:
        from app.tools.mcp_plugins.sandbox_runtime import SandboxRuntime
        _sandbox = SandboxRuntime()
        for tool_def in _sandbox.get_tool_definitions():
            tool_name = tool_def["name"]
            tool_desc = tool_def["description"]
            tool_params = tool_def.get("parameters", {})
            # Create a closure that captures the sandbox instance
            def _make_handler(sandbox, name):
                async def _handler(**kwargs):
                    if name == "sandbox_execute":
                        result = await sandbox.execute(kwargs.get("command", ""), kwargs.get("cwd"))
                        return {"stdout": result.stdout, "stderr": result.stderr, "exit_code": result.exit_code, "blocked": result.blocked}
                    if name == "sandbox_run_code":
                        result = await sandbox.execute_script(kwargs.get("code", ""), kwargs.get("language", "python"))
                        return {"stdout": result.stdout, "stderr": result.stderr, "exit_code": result.exit_code}
                    return {"error": "Unknown sandbox tool"}
                return _handler
            tool_registry.register(tool_name, tool_desc, tool_params, _make_handler(_sandbox, tool_name))
            count += 1
    except Exception as e:
        logger.warning(f"Failed to register sandbox tools: {e}")

    # Context Compression tools
    try:
        from app.tools.mcp_plugins.context_compression import ContextCompressor
        _compressor = ContextCompressor()
        for tool_def in _compressor.get_tool_definitions():
            tool_name = tool_def["name"]
            tool_desc = tool_def["description"]
            tool_params = tool_def.get("parameters", {})
            def _make_handler(compressor, name):
                async def _handler(**kwargs):
                    if name == "compress_context":
                        result = compressor.compress(kwargs.get("text", ""), kwargs.get("preserve_lines"))
                        return {"compressed_text": result.compressed_text, "ratio": result.ratio, "original_tokens": result.original_tokens, "compressed_tokens": result.compressed_tokens}
                    return {"error": "Unknown compression tool"}
                return _handler
            tool_registry.register(tool_name, tool_desc, tool_params, _make_handler(_compressor, tool_name))
            count += 1
    except Exception as e:
        logger.warning(f"Failed to register compression tools: {e}")

    # Dynamic Tool tools (meta-tools for creating new tools)
    try:
        from app.tools.mcp_plugins.dynamic_tool import DynamicToolGenerator
        _generator = DynamicToolGenerator()
        for tool_def in _generator.get_tool_definitions():
            tool_name = tool_def["name"]
            tool_desc = tool_def["description"]
            tool_params = tool_def.get("parameters", {})
            def _make_handler(generator, name):
                async def _handler(**kwargs):
                    return generator.execute_tool(name.replace("dynamic_", ""), kwargs)
                return _handler
            tool_registry.register(tool_name, tool_desc, tool_params, _make_handler(_generator, tool_name))
            count += 1
    except Exception as e:
        logger.warning(f"Failed to register dynamic tools: {e}")

    logger.info(f"Registered {count} MCP plugin tools")
    return count
