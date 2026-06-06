"""
LLMProvider protocol — the contract both Ollama and Bedrock backends implement.
Any object satisfying this protocol can be used as the active provider.
"""
from typing import AsyncGenerator, Protocol, runtime_checkable


@runtime_checkable
class LLMProvider(Protocol):
    async def embed(self, text: str) -> list[float]:
        """Return an embedding vector for a single text string."""
        ...

    async def generate_stream(self, prompt: str) -> AsyncGenerator[str, None]:
        """Stream response tokens for a prompt, one token at a time."""
        ...
