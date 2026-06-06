"""Single-pass summarization for documents ≤ TOKEN_THRESHOLD tokens."""
from shared.providers import llm_factory

SUMMARIZE_PROMPT = """/no_think
You are a document summarization assistant.
Provide a clear, concise summary of the following document text.
Focus on the main topics, key findings, and important details.
Keep the summary between 3-8 sentences.

Document:
{text}

Summary:"""


async def summarize(text: str) -> str:
    prompt = SUMMARIZE_PROMPT.format(text=text[:12000])  # safety truncation
    return await llm_factory.generate(prompt)
