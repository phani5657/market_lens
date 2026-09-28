import time
from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from langchain_core.tools import StructuredTool


LIVE_MCP_URL = "https://mcp.nseindia.in/cmmkt/mcp"
HISTORICAL_MCP_URL = "https://mcp.nseindia.in/bhavcopy/cm/mcp"


# =========================================================
# MCP SESSION
# =========================================================

@asynccontextmanager
async def nse_session(url: str):

    start = time.perf_counter()

    print(f"\n[MCP START] Connecting")
    print(f"[MCP URL] {url}")

    async with streamable_http_client(url) as (
        read_stream,
        write_stream,
    ):

        print("[MCP] HTTP connection established")

        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:

            print("[MCP START] Initializing session")

            await session.initialize()

            print(
                f"[MCP END] Session initialized | "
                f"time={time.perf_counter() - start:.2f}s"
            )

            yield session

            print("[MCP] Session closed")


# =========================================================
# GET MCP TOOLS
# =========================================================

async def get_nse_tools(session):

    start = time.perf_counter()

    print("[START] Discovering MCP tools")

    result = await session.list_tools()

    print(
        f"[END] MCP tool discovery | "
        f"count={len(result.tools)} | "
        f"time={time.perf_counter() - start:.2f}s"
    )

    return result.tools


# =========================================================
# CALL MCP TOOL
# =========================================================

async def call_nse_tool(
    session,
    tool_name: str,
    arguments: dict,
):

    start = time.perf_counter()

    print(
        f"[MCP CALL START] {tool_name} | "
        f"args={arguments}"
    )

    try:

        result = await session.call_tool(
            tool_name,
            arguments=arguments,
        )

        print(
            f"[MCP CALL END] {tool_name} | "
            f"time={time.perf_counter() - start:.2f}s"
        )

        print(
            f"[MCP CALL RESULT] {result.content}"
        )

        return result.content

    except Exception as exc:

        print(
            f"[MCP CALL ERROR] {tool_name} | "
            f"{exc}"
        )

        raise


# =========================================================
# CONVERT MCP TOOL → LANGCHAIN TOOL
# =========================================================

def create_langchain_tool(
    session,
    mcp_tool,
    prefix: str,
):

    async def execute_tool(**arguments):

        return await call_nse_tool(
            session,
            mcp_tool.name,
            arguments,
        )

    return StructuredTool.from_function(
        coroutine=execute_tool,
        name=f"{prefix}_{mcp_tool.name}",
        description=mcp_tool.description or "",
        args_schema=mcp_tool.input_schema,
    )


# =========================================================
# CREATE ALL LANGCHAIN TOOLS
# =========================================================

async def get_langchain_tools(
    session,
    prefix: str,
):

    start = time.perf_counter()

    print(
        f"[START] Converting {prefix} MCP tools "
        f"to LangChain tools"
    )

    mcp_tools = await get_nse_tools(
        session
    )

    langchain_tools = [
        create_langchain_tool(
            session,
            mcp_tool,
            prefix,
        )
        for mcp_tool in mcp_tools
    ]

    print(
        f"[END] LangChain tools ready | "
        f"count={len(langchain_tools)} | "
        f"time={time.perf_counter() - start:.2f}s"
    )

    return langchain_tools