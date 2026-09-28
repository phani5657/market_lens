import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import PlainTextResponse

from model import QueryRequest
from graph import build_graph

from mcp_client import (
    nse_session,
    get_langchain_tools,
    LIVE_MCP_URL,
    HISTORICAL_MCP_URL,
)


@asynccontextmanager
async def lifespan(app: FastAPI):

    print("\n========== MARKET LENS STARTUP ==========")

    startup_start = time.perf_counter()

    # --------------------------------------------------
    # LIVE MCP
    # --------------------------------------------------

    print("[START] Connecting to LIVE MCP")

    live_start = time.perf_counter()

    async with nse_session(LIVE_MCP_URL) as live_session:

        live_tools = await get_langchain_tools(
            live_session,
            "live",
        )

        app.state.live_session = live_session
        app.state.live_tools = live_tools

        print(
            f"[END] LIVE MCP ready | "
            f"tools={len(live_tools)} | "
            f"time={time.perf_counter() - live_start:.2f}s"
        )

        # --------------------------------------------------
        # HISTORICAL MCP
        # --------------------------------------------------

        print("[START] Connecting to HISTORICAL MCP")

        historical_start = time.perf_counter()

        async with nse_session(
            HISTORICAL_MCP_URL
        ) as historical_session:

            historical_tools = await get_langchain_tools(
                historical_session,
                "historical",
            )

            app.state.historical_session = historical_session
            app.state.historical_tools = historical_tools

            print(
                f"[END] HISTORICAL MCP ready | "
                f"tools={len(historical_tools)} | "
                f"time={time.perf_counter() - historical_start:.2f}s"
            )

            # --------------------------------------------------
            # BUILD GRAPH
            # --------------------------------------------------

            print("[START] Building LangGraph")

            graph_start = time.perf_counter()

            app.state.graph = build_graph(
                live_tools,
                historical_tools,
            )

            print(
                f"[END] LangGraph ready | "
                f"time={time.perf_counter() - graph_start:.2f}s"
            )

            print(
                f"[STARTUP COMPLETE] "
                f"time={time.perf_counter() - startup_start:.2f}s"
            )

            print("========================================\n")

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

    request_start = time.perf_counter()

    print("\n========== NEW QUERY ==========")
    print(f"[QUERY] {request.query}")

    initial_state = {
        "query": request.query,
        "market_type": "",
        "data": {},
        "analysis": "",
        "response": "",
    }

    print("[START] LangGraph execution")

    result = await app.state.graph.ainvoke(
        initial_state
    )

    print(
        f"[END] LangGraph execution | "
        f"time={time.perf_counter() - request_start:.2f}s"
    )

    print(
        f"[RESPONSE] {result['response']}"
    )

    print(
        f"[TOTAL REQUEST TIME] "
        f"{time.perf_counter() - request_start:.2f}s"
    )

    print("================================\n")

    return result["response"]