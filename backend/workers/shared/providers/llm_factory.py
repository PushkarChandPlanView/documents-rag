"""
Worker LLM factory — provider-agnostic proxy used by summarization strategies
and the embedding consumer.

Usage (summarization strategies):
    from shared.providers import llm_factory
    text = await llm_factory.generate(prompt)

Usage (embedding consumer):
    from shared.providers import llm_factory
    vectors = await llm_factory.embed_batch(texts)
"""
import logging

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_llm_provider = None
_embed_provider = None


def _get_llm_provider():
    global _llm_provider
    if _llm_provider is None:
        if settings.llm_provider == "bedrock":
            from shared.providers.bedrock import BedrockWorkerProvider
            _llm_provider = BedrockWorkerProvider()
            logger.info("Worker LLM provider: AWS Bedrock (%s)", settings.bedrock_llm_model)
        else:
            from shared.providers.ollama import OllamaWorkerProvider
            _llm_provider = OllamaWorkerProvider()
            logger.info("Worker LLM provider: Ollama (%s)", settings.ollama_llm_model)
    return _llm_provider


def _get_embed_provider():
    global _embed_provider
    if _embed_provider is None:
        if settings.embed_provider == "bedrock":
            from shared.providers.bedrock import BedrockWorkerProvider
            _embed_provider = BedrockWorkerProvider()
            logger.info("Worker embed provider: AWS Bedrock (%s)", settings.bedrock_embed_model)
        else:
            from shared.providers.ollama import OllamaWorkerProvider
            _embed_provider = OllamaWorkerProvider()
            logger.info("Worker embed provider: Ollama (%s)", settings.ollama_embed_model)
    return _embed_provider


async def generate(prompt: str) -> str:
    """Non-streaming generation — returns full response string."""
    return await _get_llm_provider().generate(prompt)


async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Embed a batch of texts. Returns a list of embedding vectors."""
    return await _get_embed_provider().embed_batch(texts)
