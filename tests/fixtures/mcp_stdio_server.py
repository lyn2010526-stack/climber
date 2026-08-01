from mcp.server.fastmcp import FastMCP


server = FastMCP("test-server")


@server.tool()
def add(a: int, b: int) -> int:
    """Add two integers."""
    return a + b


if __name__ == "__main__":
    server.run(transport="stdio")
