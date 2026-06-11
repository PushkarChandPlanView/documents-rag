"""Synthesizer node — assembles retrieved chunks into context and calls LLM."""
import logging

from services import llm_client

logger = logging.getLogger(__name__)

_FORMAT_INSTRUCTIONS = {
    "markdown": "Respond in well-formatted Markdown with headers, bullet points, and code blocks as appropriate.",
    "text":     "Respond in plain text with no Markdown formatting.",
    "json":     "Respond with a single valid JSON object. Do not include any text outside the JSON.",
}


async def synthesizer_node(state: dict) -> dict:
    query         = state.get("query", "")
    system_prompt = state.get("system_prompt", "You are a helpful assistant.")
    output_format = state.get("output_format", "markdown")
    step_results  = state.get("step_results", [])

    # Build context from all gathered chunks
    context_parts = []
    seen_ids: set = set()
    for sr in step_results:
        for chunk in sr.get("chunks", []):
            cid = chunk.get("chunk_id", "")
            if cid in seen_ids:
                continue
            seen_ids.add(cid)
            doc_name = chunk.get("document_name", "Unknown")
            text     = chunk.get("text", "")
            context_parts.append(f"[Source: {doc_name}]\n{text}")

    context = "\n\n---\n\n".join(context_parts[:30])  # cap at 30 chunks

    fmt_instruction = _FORMAT_INSTRUCTIONS.get(output_format, _FORMAT_INSTRUCTIONS["markdown"])

    prompt = f"""{system_prompt}

You have gathered the following information from various documents:

{context}

---

User query: {query}

{fmt_instruction}

Provide a comprehensive answer based solely on the information above."""

    logger.info("Synthesizing answer from %d chunks (format=%s)", len(seen_ids), output_format)

    answer_parts = []
    async for token in llm_client.generate_stream(prompt, system=system_prompt):
        answer_parts.append(token)

    answer = "".join(answer_parts)
    return {"answer": answer}
