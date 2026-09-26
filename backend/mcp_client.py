from contextlib import asynccontextmanager

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from langchain_core.tools import StructuredTool


LIVE_MCP_URL = "https://mcp.nseindia.in/cmmkt/mcp"
HISTORICAL_MCP_URL = "https://mcp.nseindia.in/bhavcopy/cm/mcp"


@asynccontextmanager
async def nse_session(url: str):

    async with streamable_http_client(url) as (
        read_stream,
        write_stream,
    ):

        async with ClientSession(
            read_stream,
            write_stream,
        ) as session:

            await session.initialize()

            yield session


async def get_nse_tools(session):

    result = await session.list_tools()

    return result.tools


async def call_nse_tool(
    session,
    tool_name: str,
    arguments: dict,
):

    result = await session.call_tool(
        tool_name,
        arguments=arguments,
    )

    return result.content


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


async def get_langchain_tools(
    session,
    prefix: str,
):

    mcp_tools = await get_nse_tools(session)

    return [
        create_langchain_tool(
            session,
            mcp_tool,
            prefix,
        )
        for mcp_tool in mcp_tools
    ]