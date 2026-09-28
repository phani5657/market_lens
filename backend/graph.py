import asyncio
import time

from typing import TypedDict, Any

from langchain_core.messages import HumanMessage
from langgraph.graph import StateGraph, START, END

from llm import llm

from tool import (
    calculate_return,
    calculate_volatility,
    find_largest_drop,
    compare_stocks,
)


# =========================================================
# STATE
# =========================================================

class MarketState(TypedDict):

    query: str

    market_type: str

    data: list

    analysis: str

    response: str


# =========================================================
# HELPERS
# =========================================================

def content_to_text(content):

    if isinstance(content, str):
        return content

    if isinstance(content, list):

        text = ""

        for block in content:

            if isinstance(block, dict):

                text += block.get(
                    "text",
                    "",
                )

            elif isinstance(block, str):

                text += block

        return text

    return str(content)


def select_market_tools(
    query: str,
    live_tools: list,
    historical_tools: list,
):

    query_lower = query.lower()

    historical_keywords = [
        "historical",
        "history",
        "historically",
        "past",
        "previous",
        "earlier",
        "yesterday",
        "previous day",
        "last year",
        "last month",
        "last week",
        "previous year",
        "previous month",
        "previous week",
        "on 2024",
        "on 2025",
        "on 2026",
        "in 2024",
        "in 2025",
        "in 2026",
    ]

    if any(
        keyword in query_lower
        for keyword in historical_keywords
    ):

        print("[ROUTER] HISTORICAL tools selected")

        return historical_tools

    print("[ROUTER] LIVE tools selected")

    return live_tools


def get_tool_by_name(
    tools: list,
    name: str,
):

    for tool in tools:

        if tool.name == name:

            return tool

    return None


# =========================================================
# EXECUTE MCP CALLS
# =========================================================

async def execute_tool_calls(
    tool_calls,
    tools,
):

    async def execute_one(
        tool_call,
    ):

        tool_name = tool_call["name"]
        arguments = tool_call["args"]

        print(
            f"[MCP START] {tool_name} | "
            f"args={arguments}"
        )

        tool_start = time.perf_counter()

        tool = get_tool_by_name(
            tools,
            tool_name,
        )

        if tool is None:

            print(
                f"[MCP ERROR] {tool_name} | "
                f"tool not found"
            )

            return {
                "tool": tool_name,
                "arguments": arguments,
                "error": (
                    f"Tool '{tool_name}' "
                    "was not found."
                ),
            }

        try:

            result = await tool.ainvoke(
                arguments
            )

            print(
                f"[MCP END] {tool_name} | "
                f"time={time.perf_counter() - tool_start:.2f}s"
            )

            print(
                f"[MCP RESULT] {result}"
            )

            return {
                "tool": tool_name,
                "arguments": arguments,
                "result": result,
            }

        except Exception as exc:

            print(
                f"[MCP ERROR] {tool_name} | "
                f"{exc}"
            )

            return {
                "tool": tool_name,
                "arguments": arguments,
                "error": str(exc),
            }

    results = await asyncio.gather(
        *[
            execute_one(tool_call)
            for tool_call in tool_calls
        ],
        return_exceptions=False,
    )

    return results


# =========================================================
# MARKET DATA
# =========================================================

async def get_market_data(
    state: MarketState,
    live_tools: list,
    historical_tools: list,
):

    node_start = time.perf_counter()

    query = state["query"]

    print("\n[START NODE] market_data")
    print(f"[MARKET QUERY] {query}")

    # -----------------------------------------------------
    # SELECT LIVE / HISTORICAL
    # -----------------------------------------------------

    selected_tools = select_market_tools(
        query,
        live_tools,
        historical_tools,
    )

    print(
        f"[MARKET TOOLS READY] "
        f"count={len(selected_tools)}"
    )

    if not selected_tools:

        print(
            "[MARKET DATA ERROR] "
            "No market-data tools available"
        )

        return {
            "data": [
                {
                    "error": (
                        "No market-data tools "
                        "are available."
                    )
                }
            ]
        }

    # -----------------------------------------------------
    # FIRST MCP PLANNING ROUND
    # -----------------------------------------------------

    print("[START] First market-data LLM call")

    llm_start = time.perf_counter()

    tool_llm = llm.bind_tools(
        selected_tools
    )

    prompt = f"""
You are the market-data retrieval agent for Market Lens.

User question:

{query}

Use the available market-data tools to retrieve
everything required to answer the question.

Important rules:

1. You may call multiple tools in this response.
2. If the user asks about multiple companies,
   retrieve data for ALL requested companies.
3. Independent company requests should each receive
   their own appropriate tool call.
4. If a company name needs symbol resolution,
   use the appropriate equity/symbol lookup tool.
5. If the symbol is already known, use the quote/data
   tool directly when possible.
6. Do not answer the user.
7. Do not calculate anything.
8. Do not invent symbols or arguments.
9. Retrieve only the data needed to answer the query.
"""

    first_result = await tool_llm.ainvoke(
        [
            HumanMessage(
                content=prompt
            )
        ]
    )

    print(
        f"[END] First market-data LLM call | "
        f"time={time.perf_counter() - llm_start:.2f}s"
    )

    first_tool_calls = first_result.tool_calls

    print(
        f"[FIRST LLM] Tool calls={len(first_tool_calls)}"
    )

    for call in first_tool_calls:

        print(
            f"[FIRST LLM TOOL] "
            f"{call['name']} | "
            f"args={call['args']}"
        )

    if not first_tool_calls:

        print(
            "[MARKET DATA ERROR] "
            "LLM selected no tools"
        )

        return {
            "data": [
                {
                    "error": (
                        "The market-data model "
                        "did not select any tools."
                    )
                }
            ]
        }

    # -----------------------------------------------------
    # EXECUTE FIRST MCP BATCH
    # -----------------------------------------------------

    print("[START] First MCP tool execution")

    first_mcp_start = time.perf_counter()

    first_results = await execute_tool_calls(
        first_tool_calls,
        selected_tools,
    )

    print(
        f"[END] First MCP tool execution | "
        f"time={time.perf_counter() - first_mcp_start:.2f}s"
    )

    collected_data = list(
        first_results
    )

    print(
        f"[DATA AFTER FIRST MCP] "
        f"{collected_data}"
    )

    # -----------------------------------------------------
    # SECOND MCP PLANNING ROUND
    # -----------------------------------------------------

    print("[START] Second market-data LLM call")

    second_llm_start = time.perf_counter()

    second_prompt = f"""
You are continuing a market-data retrieval task.

User question:

{query}

Results from the first market-data calls:

{collected_data}

Determine whether additional market-data calls are
required to fully answer the user's question.

Rules:

1. If a company was resolved to a stock symbol but
   its requested price/data has not yet been retrieved,
   call the appropriate quote/data tool.
2. If the first results already contain the requested
   information, do not call another tool.
3. For multiple companies, retrieve missing data
   for ALL requested companies.
4. You may call multiple tools.
5. Do not calculate anything.
6. Do not answer the user.
7. Do not repeat successful calls unnecessarily.
"""

    second_result = await tool_llm.ainvoke(
        [
            HumanMessage(
                content=second_prompt
            )
        ]
    )

    print(
        f"[END] Second market-data LLM call | "
        f"time={time.perf_counter() - second_llm_start:.2f}s"
    )

    second_tool_calls = second_result.tool_calls

    print(
        f"[SECOND LLM] "
        f"Tool calls={len(second_tool_calls)}"
    )

    for call in second_tool_calls:

        print(
            f"[SECOND LLM TOOL] "
            f"{call['name']} | "
            f"args={call['args']}"
        )

    # -----------------------------------------------------
    # SECOND MCP BATCH
    # -----------------------------------------------------

    if second_tool_calls:

        print("[START] Second MCP tool execution")

        second_mcp_start = time.perf_counter()

        second_results = await execute_tool_calls(
            second_tool_calls,
            selected_tools,
        )

        print(
            f"[END] Second MCP tool execution | "
            f"time={time.perf_counter() - second_mcp_start:.2f}s"
        )

        collected_data.extend(
            second_results
        )

        print(
            f"[DATA AFTER SECOND MCP] "
            f"{collected_data}"
        )

    else:

        print(
            "[SECOND MCP] No additional data required"
        )

    print(
        f"[END NODE] market_data | "
        f"time={time.perf_counter() - node_start:.2f}s"
    )

    return {
        "data": collected_data
    }


# =========================================================
# FINAL ANALYSIS
# =========================================================

async def analyze_data(
    state: MarketState,
):

    node_start = time.perf_counter()

    query = state["query"]
    data = state["data"]

    print("\n[START NODE] analyze")
    print(f"[ANALYSIS QUERY] {query}")
    print(f"[ANALYSIS INPUT DATA] {data}")

    calculation_tools = [
        calculate_return,
        calculate_volatility,
        find_largest_drop,
        compare_stocks,
    ]

    analysis_llm = llm.bind_tools(
        calculation_tools
    )

    prompt = f"""
You are Market Lens.

User question:

{query}

Market data retrieved from the NSE market-data tools:

{data}

Answer the user's question using the retrieved data.

Rules:

1. Use only the supplied market data.
2. Never invent prices, dates, percentages,
   symbols, or other values.
3. If one company failed but other companies
   returned data, still answer using the successful
   results and clearly mention the failed company.
4. If the market-data provider returned an error,
   clearly identify that error.
5. If a calculation is required, use the available
   calculation tools.
6. Keep the answer concise and structured.
7. For multiple companies, clearly separate the
   result for each company.
"""

    print("[START] Analysis LLM call")

    analysis_start = time.perf_counter()

    result = await analysis_llm.ainvoke(
        [
            HumanMessage(
                content=prompt
            )
        ]
    )

    print(
        f"[END] Analysis LLM call | "
        f"time={time.perf_counter() - analysis_start:.2f}s"
    )

    print(
        f"[ANALYSIS RESULT] "
        f"{result.content}"
    )

    if result.tool_calls:

        print(
            f"[ANALYSIS TOOLS] "
            f"calls={len(result.tool_calls)}"
        )

        for call in result.tool_calls:

            print(
                f"[ANALYSIS TOOL] "
                f"{call['name']} | "
                f"args={call['args']}"
            )

    else:

        print(
            "[ANALYSIS TOOLS] No calculation tool used"
        )

    print(
        f"[END NODE] analyze | "
        f"time={time.perf_counter() - node_start:.2f}s"
    )

    return {
        "analysis": result
    }


# =========================================================
# RESPONSE
# =========================================================

def generate_response(
    state: MarketState,
):

    print("\n[START NODE] response")

    analysis = state["analysis"]

    if hasattr(
        analysis,
        "content",
    ):

        response = content_to_text(
            analysis.content
        )

    else:

        response = content_to_text(
            analysis
        )

    print(
        f"[RESPONSE RESULT] {response}"
    )

    print("[END NODE] response")

    return {
        "response": response
    }


# =========================================================
# BUILD GRAPH
# =========================================================

def build_graph(
    live_tools,
    historical_tools,
):

    print("[START] Creating LangGraph")

    workflow = StateGraph(
        MarketState
    )

    # -----------------------------------------------------
    # MARKET DATA NODE
    # -----------------------------------------------------

    async def market_data_node(
        state: MarketState,
    ):

        return await get_market_data(
            state,
            live_tools,
            historical_tools,
        )

    # -----------------------------------------------------
    # ANALYSIS NODE
    # -----------------------------------------------------

    async def analysis_node(
        state: MarketState,
    ):

        return await analyze_data(
            state
        )

    # -----------------------------------------------------
    # ADD NODES
    # -----------------------------------------------------

    workflow.add_node(
        "market_data",
        market_data_node,
    )

    workflow.add_node(
        "analyze",
        analysis_node,
    )

    workflow.add_node(
        "response",
        generate_response,
    )

    # -----------------------------------------------------
    # EDGES
    # -----------------------------------------------------

    workflow.add_edge(
        START,
        "market_data",
    )

    workflow.add_edge(
        "market_data",
        "analyze",
    )

    workflow.add_edge(
        "analyze",
        "response",
    )

    workflow.add_edge(
        "response",
        END,
    )

    graph = workflow.compile()

    print("[END] LangGraph created")

    return graph