"""
Agent execution chain — LangGraph state graph.

Graph: START → planner → tool_executor (loop until all steps done) → synthesizer → uploader → END

SSE events yielded:
  plan          — {"type":"plan", "steps":[...]}
  step_start    — {"type":"step_start", "step":N, "text":"..."}
  step_done     — {"type":"step_done", "step":N, "chunks_found":K}
  generating    — {"type":"generating"}
  token         — {"type":"token", "content":"..."}
  uploaded      — {"type":"uploaded", "document_id":"..."}
  done          — {"type":"done", "document_id":"..."}
  error         — {"type":"error", "content":"..."}
"""
import json
import logging
import operator
import uuid
from typing import Annotated, AsyncGenerator, Optional

from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from nodes.planner_node import planner_node
from nodes.tool_executor_node import tool_executor_node
from nodes.synthesizer_node import synthesizer_node
from nodes.uploader_node import uploader_node

logger = logging.getLogger(__name__)


# ── State ──────────────────────────────────────────────────────────────────────

class AgentRunState(TypedDict):
    run_id:          str
    agent_id:        str
    agent_name:      str
    user_id:         str
    query:           str
    system_prompt:   str
    output_format:   str
    enabled_tools:   list
    plan:            list
    current_step:    int
    step_results:    Annotated[list, operator.add]
    answer:          Optional[str]
    result_document_id: Optional[str]


# ── Conditional: loop tool_executor until all steps done ─────────────────────

def _should_continue(state: AgentRunState) -> str:
    if state.get("current_step", 0) >= len(state.get("plan", [])):
        return "synthesizer"
    return "tool_executor"


# ── Build graph ────────────────────────────────────────────────────────────────

def _build_graph() -> StateGraph:
    g = StateGraph(AgentRunState)
    g.add_node("planner",       planner_node)
    g.add_node("tool_executor", tool_executor_node)
    g.add_node("synthesizer",   synthesizer_node)
    g.add_node("uploader",      uploader_node)

    g.add_edge(START, "planner")
    g.add_conditional_edges("planner", _should_continue,
                             {"tool_executor": "tool_executor", "synthesizer": "synthesizer"})
    g.add_conditional_edges("tool_executor", _should_continue,
                             {"tool_executor": "tool_executor", "synthesizer": "synthesizer"})
    g.add_edge("synthesizer", "uploader")
    g.add_edge("uploader", END)
    return g


_graph = _build_graph().compile()


# ── Public streaming interface ─────────────────────────────────────────────────

async def run_agent(
    run_id: str,
    agent_id: str,
    agent_name: str,
    user_id: str,
    query: str,
    system_prompt: str,
    output_format: str,
    enabled_tools: list,
) -> AsyncGenerator[str, None]:
    """Run the agent graph and yield SSE event strings."""

    def _sse(data: dict) -> str:
        return "data: " + json.dumps(data) + "\n\n"

    initial_state: AgentRunState = {
        "run_id":            run_id,
        "agent_id":          agent_id,
        "agent_name":        agent_name,
        "user_id":           user_id,
        "query":             query,
        "system_prompt":     system_prompt,
        "output_format":     output_format,
        "enabled_tools":     enabled_tools,
        "plan":              [],
        "current_step":      0,
        "step_results":      [],
        "answer":            None,
        "result_document_id": None,
    }

    try:
        final_state = None

        async for event in _graph.astream(initial_state):
            for node_name, updates in event.items():
                if node_name == "planner":
                    yield _sse({"type": "plan", "steps": updates.get("plan", [])})

                elif node_name == "tool_executor":
                    step_results = updates.get("step_results", [])
                    if step_results:
                        sr = step_results[-1]
                        yield _sse({
                            "type":         "step_done",
                            "step":         sr["step"],
                            "step_text":    sr["step_text"],
                            "source_types": sr.get("source_types"),
                            "chunks_found": len(sr.get("chunks", [])),
                        })

                elif node_name == "synthesizer":
                    yield _sse({"type": "generating"})
                    # Stream the answer token-by-token (it's pre-generated in synthesizer_node)
                    answer = updates.get("answer", "")
                    if answer:
                        for word in answer.split(" "):
                            yield _sse({"type": "token", "content": word + " "})
                    final_state = updates

                elif node_name == "uploader":
                    doc_id = updates.get("result_document_id", "")
                    yield _sse({"type": "uploaded", "document_id": doc_id})
                    final_state = {**(final_state or {}), **updates}

        doc_id = (final_state or {}).get("result_document_id", "")
        yield _sse({"type": "done", "document_id": doc_id})

    except Exception as exc:
        logger.error("Agent chain error: %s", exc, exc_info=True)
        yield _sse({"type": "error", "content": f"Agent execution failed: {exc}"})
