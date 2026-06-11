"""
Agentic search chain — LangGraph state graph for multi-turn retrieval.

Graph: START → router → search → reflect → (sufficient? generate : router) → END

The graph runs fully in-process; SSE streaming is handled by the caller
in routers/query.py which consumes events from run_agentic_search().
"""
import json
import logging
import operator
import uuid
from typing import Annotated, AsyncGenerator, Optional

from langchain_core.messages import BaseMessage
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from nodes.router_node import router_node
from nodes.reflect_node import reflect_node
from nodes.generate_node import generate_node
from services import llm_client
from services import es_retriever

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class AgenticState(TypedDict):
    trace_id: str
    query: str
    refined_query: Optional[str]
    user_id: str
    document_ids: Optional[list]
    source_types: Optional[list]
    file_types: Optional[list]
    folder_id: Optional[str]
    mode: str                                           # hybrid | semantic | keyword
    retrieved_chunks: Annotated[list, operator.add]     # accumulate across iterations
    messages: Annotated[list, operator.add]
    iteration: int
    max_iter: int
    sufficient: Optional[bool]
    reflection: Optional[str]
    answer: Optional[str]
    _sources: Optional[list]


# ---------------------------------------------------------------------------
# Search node (inline — calls existing es_retriever)
# ---------------------------------------------------------------------------

async def search_node(state: AgenticState) -> dict:
    query        = state.get("refined_query") or state["query"]
    mode         = state.get("mode", "hybrid")
    user_id      = state.get("user_id", "")
    doc_ids      = state.get("document_ids")
    source_types = state.get("source_types")
    file_types   = state.get("file_types")
    folder_id    = state.get("folder_id")
    top_k        = 10

    logger.info("Search: mode=%s iteration=%d query=%r", mode, state.get("iteration", 0), query[:80])

    try:
        if mode == "keyword":
            chunks = await es_retriever.keyword_search(
                query_text=query, user_id=user_id, document_ids=doc_ids, top_k=top_k,
                source_types=source_types, file_types=file_types, folder_id=folder_id,
            )
        elif mode == "semantic":
            embedding = await llm_client.embed(query)
            chunks = await es_retriever.semantic_search(
                query_vector=embedding, user_id=user_id, document_ids=doc_ids, top_k=top_k,
                source_types=source_types, file_types=file_types, folder_id=folder_id,
            )
        else:  # hybrid (default)
            embedding = await llm_client.embed(query)
            chunks = await es_retriever.hybrid_search(
                query_text=query, query_vector=embedding,
                user_id=user_id, document_ids=doc_ids, top_k=top_k,
                source_types=source_types, file_types=file_types, folder_id=folder_id,
            )
    except Exception as exc:
        logger.error("Search node error: %s", exc, exc_info=True)
        chunks = []

    # Convert Chunk dataclass to plain dicts for the state
    raw = [
        {
            "chunk_id":      c.chunk_id,
            "document_id":   c.document_id,
            "document_name": c.document_name,
            "text":          c.text,
            "score":         c.score,
            "page_number":   c.page_number,
        }
        for c in chunks
    ]
    return {"retrieved_chunks": raw}


# ---------------------------------------------------------------------------
# Conditional edge: reflect → generate  OR  reflect → router
# ---------------------------------------------------------------------------

def _should_generate(state: AgenticState) -> str:
    if state.get("sufficient") or (state.get("iteration", 0) >= state.get("max_iter", 3)):
        return "generate"
    return "router"


# ---------------------------------------------------------------------------
# Build the graph
# ---------------------------------------------------------------------------

def _build_graph() -> StateGraph:
    g = StateGraph(AgenticState)
    g.add_node("router",   router_node)
    g.add_node("search",   search_node)
    g.add_node("reflect",  reflect_node)
    g.add_node("generate", generate_node)

    g.add_edge(START,      "router")
    g.add_edge("router",   "search")
    g.add_edge("search",   "reflect")
    g.add_conditional_edges("reflect", _should_generate, {"generate": "generate", "router": "router"})
    g.add_edge("generate", END)
    return g


_graph = _build_graph().compile()


# ---------------------------------------------------------------------------
# Public streaming interface — yields SSE strings for the FastAPI endpoint
# ---------------------------------------------------------------------------

async def run_agentic_search(
    query: str,
    user_id: str,
    document_ids: Optional[list] = None,
    max_iter: int = 3,
    source_types: Optional[list] = None,
    file_types: Optional[list] = None,
    folder_id: Optional[str] = None,
) -> AsyncGenerator[str, None]:
    """
    Run the agentic graph and yield SSE event strings.

    Event types:
      routing    — graph chose a search mode
      searching  — about to hit ES
      reflecting — Haiku judged the results
      token      — one token of the final answer
      done       — terminal event with sources + iteration count
      error      — something went wrong
    """

    def _sse(data: dict) -> str:
        return "data: " + json.dumps(data) + "\n\n"

    trace_id = str(uuid.uuid4())
    initial_state: AgenticState = {
        "trace_id":        trace_id,
        "query":           query,
        "refined_query":   None,
        "user_id":         user_id,
        "document_ids":    document_ids,
        "source_types":    source_types,
        "file_types":      file_types,
        "folder_id":       folder_id,
        "mode":            "hybrid",
        "retrieved_chunks": [],
        "messages":        [],
        "iteration":       0,
        "max_iter":        max_iter,
        "sufficient":      None,
        "reflection":      None,
        "answer":          None,
        "_sources":        None,
    }

    try:
        # LangGraph stream — we get state snapshots after each node
        prev_iteration = -1
        final_state = None

        async for event in _graph.astream(initial_state):
            # event is a dict: {node_name: updated_state_slice}
            for node_name, updates in event.items():
                if node_name == "router":
                    yield _sse({"type": "routing", "mode": updates.get("mode", "hybrid")})

                elif node_name == "search":
                    iteration = updates.get("iteration", 0) if updates else 0
                    yield _sse({"type": "searching", "iteration": iteration})

                elif node_name == "reflect":
                    yield _sse({
                        "type":       "reflecting",
                        "sufficient": updates.get("sufficient"),
                        "reflection": updates.get("reflection"),
                        "iteration":  updates.get("iteration", 0),
                    })

                elif node_name == "generate":
                    final_state = updates

        # Stream answer tokens
        answer  = (final_state or {}).get("answer", "") if final_state else ""
        sources = (final_state or {}).get("_sources", []) if final_state else []

        # Stream answer word-by-word (already fully generated by generate_node)
        if answer:
            words = answer.split(" ")
            for i, word in enumerate(words):
                token = word if i == len(words) - 1 else word + " "
                yield _sse({"type": "token", "content": token})

        yield _sse({"type": "done", "sources": sources or []})

    except Exception as exc:
        logger.error("Agentic chain error: %s", exc, exc_info=True)
        yield _sse({
            "type":    "error",
            "content": "Sorry, an error occurred during agentic search.",
            "sources": [],
            "done":    True,
        })
