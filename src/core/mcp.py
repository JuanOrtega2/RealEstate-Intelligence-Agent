import json

from mcp.server.fastmcp import FastMCP

# Initialize the MCP server
mcp = FastMCP("RealEstateInvest")


# --- RESOURCES ---
@mcp.resource("config://itp-rates")
def get_itp_rates() -> str:
    """Returns the official ITP tax rates by Autonomous Community in Spain."""
    from src.core.tools import ITP_RATES

    return json.dumps(ITP_RATES, indent=2, ensure_ascii=False)


@mcp.resource("config://irpf-trams")
def get_irpf_trams() -> str:
    """Returns the current IRPF income tax brackets used in the model."""
    from src.core.tools import IRPF_TRAMS

    return json.dumps(IRPF_TRAMS, indent=2, ensure_ascii=False)


# --- PROMPTS ---
@mcp.prompt("analyze-investment")
def analyze_investment_prompt():
    """Master template for performing a real estate investment analysis."""
    return """Act as a Senior Investment Analyst.
    Follow these steps:
    1. Check config://itp-rates resources to ensure the correct tax rate.
    2. Use the calculate_investment_metrics tool with the provided data.
    3. If salary or fixed expenses are missing, request them from the user.
    4. Present a professional report including Gross/Net Yield, Cashflow, and ROCE."""


# --- BACKEND HELPERS (Now Async) ---
async def get_tools_schema():
    """Extracts JSON schemas from tools registered in FastMCP for external API calls."""
    schemas = []
    # FastMCP.list_tools() is a coroutine, we must await it
    tools = await mcp.list_tools()
    for tool in tools:
        schemas.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            }
        )
    return schemas


async def call_mcp_tool(name: str, args: dict):
    """Executes an MCP tool by name using the FastMCP engine."""
    # FastMCP.call_tool is also a coroutine
    return await mcp.call_tool(name, args)
