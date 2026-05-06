import json
from typing import Any, Dict, List, Optional

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
    1. Gather data across the 5 Pillars: Property, Mortgage, Rental, Expenses,
       and Financing.
    2. Consult config://itp-rates resources to confirm the tax rate.
    3. Use the analyze_investment_roi tool once data is gathered or
       estimates are authorized.
    4. Present a professional report including Yield, Cashflow, and ROCE."""


# Global cache for tools schema to avoid repeated introspection and resolution
_cached_tools_schema: Optional[List[Dict[str, Any]]] = None


async def get_tools_schema():
    """
    Extracts inlined JSON schemas from tools for LLM compatibility
    (resolving $refs) with caching.
    """
    global _cached_tools_schema
    if _cached_tools_schema is not None:
        return _cached_tools_schema

    def resolve_refs(schema: Any, defs: Dict[str, Any]) -> Any:
        if isinstance(schema, dict):
            if "$ref" in schema:
                ref_key = schema["$ref"].split("/")[-1]
                return resolve_refs(defs[ref_key], defs)
            return {k: resolve_refs(v, defs) for k, v in schema.items()}
        elif isinstance(schema, list):
            return [resolve_refs(v, defs) for v in schema]
        return schema

    schemas = []
    tools = await mcp.list_tools()
    for tool in tools:
        raw_schema = tool.inputSchema
        definitions = raw_schema.get("$defs", {})
        inlined_parameters = resolve_refs(raw_schema, definitions)
        if "$defs" in inlined_parameters:
            del inlined_parameters["$defs"]

        schemas.append(
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": inlined_parameters,
                },
            }
        )

    _cached_tools_schema = schemas
    return _cached_tools_schema


async def call_mcp_tool(name: str, args: dict):
    """
    Executes an MCP tool by name using the FastMCP engine.
    Includes an adapter for Pydantic models expecting a 'data' envelope.
    """
    # Fix: If the tool expects a single 'data' argument but LLM sends fields at root
    if name == "analyze_investment_roi" and "data" not in args:
        # Wrap root fields into 'data' key for InvestmentAnalysisInput compatibility
        args = {"data": args}

    return await mcp.call_tool(name, args)
