"""
LLM client — provider-agnostic factory proxy.

Reads LLM_PROVIDER / EMBED_PROVIDER from config and delegates to either:
  - OllamaProvider  (default, local)
  - BedrockProvider (AWS)

All callers (rag_chain.py, retriever.py, etc.) import from here unchanged.
"""
import logging
from typing import AsyncGenerator

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_llm_provider = None
_embed_provider = None


def _get_llm_provider():
    global _llm_provider
    if _llm_provider is None:
        if settings.llm_provider == "bedrock":
            from services.providers.bedrock import BedrockProvider
            _llm_provider = BedrockProvider()
            logger.info("LLM provider: AWS Bedrock (%s)", settings.bedrock_llm_model)
        else:
            from services.providers.ollama import OllamaProvider
            _llm_provider = OllamaProvider()
            logger.info("LLM provider: Ollama (%s)", settings.ollama_llm_model)
    return _llm_provider


def _get_embed_provider():
    global _embed_provider
    if _embed_provider is None:
        if settings.embed_provider == "bedrock":
            from services.providers.bedrock import BedrockProvider
            _embed_provider = BedrockProvider()
            logger.info("Embed provider: AWS Bedrock (%s)", settings.bedrock_embed_model)
        else:
            from services.providers.ollama import OllamaProvider
            _embed_provider = OllamaProvider()
            logger.info("Embed provider: Ollama (%s)", settings.ollama_embed_model)
    return _embed_provider


async def embed(text: str) -> list[float]:
    """Generate an embedding vector for a single text."""
    return await _get_embed_provider().embed(text)


async def generate_stream(prompt: str) -> AsyncGenerator[str, None]:
    """Stream response tokens for a prompt."""
    async for token in _get_llm_provider().generate_stream(prompt):
        yield token


async def generate(prompt: str) -> str:
    """Non-streaming generation — returns full response string."""
    return await _get_llm_provider().generate(prompt)


async def generate_with_model(prompt: str, model_id: str, max_tokens: int = 512) -> str:
    """Non-streaming generation with an explicit model override (e.g. Haiku for reflect node)."""
    provider = _get_llm_provider()
    if hasattr(provider, "generate_with_model"):
        return await provider.generate_with_model(prompt, model_id, max_tokens)
    # Fallback for Ollama — ignores model_id and uses default
    return await provider.generate(prompt)
