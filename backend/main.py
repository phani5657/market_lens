from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from model import QueryRequest
from graph import build_graph

from mcp_client import (
    nse_session,
    get_langchain_tools,
    LIVE_MCP_URL,
)


@asynccontextmanager
async def lifespan(app: FastAPI):

    async with nse_session(
        LIVE_MCP_URL
    ) as live_session:

        live_tools = await get_langchain_tools(
            live_session,
            "live",
        )

        app.state.live_session = live_session
        app.state.live_tools = live_tools

        app.state.graph = build_graph(
            live_tools,
            [],
        )

        yield


app = FastAPI(
    lifespan=lifespan
)


@app.post(
    "/query",
    response_class=PlainTextResponse,
)
async def query(
    request: QueryRequest,
):

    initial_state = {
        "query": request.query,
        "market_type": "",
        "company": "",
        "tool_name": "",
        "tool_arguments": {},
        "data": {},
        "analysis": "",
        "response": "",
    }

    result = await app.state.graph.ainvoke(
        initial_state
    )

    return result["response"]