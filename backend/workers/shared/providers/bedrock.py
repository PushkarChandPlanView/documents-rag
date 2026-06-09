"""
AWS Bedrock worker provider — embedding and non-streaming generation
for the summarization and embedding workers.

Embedding model : amazon.titan-embed-text-v2:0  (1024 dims)
Generation model: anthropic.claude-3-5-sonnet-20241022-v2:0 (or config override)
"""
import asyncio
import json
import logging

import aioboto3

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_boto_session = aioboto3.Session()

# Max concurrent Bedrock calls — Bedrock has per-account TPS limits
CONCURRENCY = 4


def _embed_request_body(text: str, model_id: str) -> str:
    """Build the embed request body for the given model family."""
    if "nova" in model_id:
        # Nova Multimodal Embeddings — Messages API format
        return json.dumps({
            "messages": [{"role": "user", "content": text}],
        })
    # Titan Embed — legacy inputText format
    return json.dumps({"inputText": text})


def _parse_embed_response(result: dict, model_id: str) -> list[float]:
    """Extract the float vector from the Bedrock embed response."""
    if "nova" in model_id:
        return result["embeddings"][0]["floats"]
    return result["embedding"]


class BedrockWorkerProvider:
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a batch of texts concurrently.
        Supports Titan Embed v2 and Nova Multimodal Embeddings.
        Returns a list of 1024-dim vectors in the same order as input.
        """
        sem = asyncio.Semaphore(CONCURRENCY)
        model_id = settings.bedrock_embed_model

        async def _embed_one(text: str) -> list[float]:
            async with sem:
                body = _embed_request_body(text, model_id)
                async with _boto_session.client(
                    "bedrock-runtime", region_name=settings.aws_region
                ) as client:
                    resp = await client.invoke_model(
                        modelId=model_id,
                        body=body,
                        contentType="application/json",
                        accept="application/json",
                    )
                    result = json.loads(await resp["body"].read())
                    return _parse_embed_response(result, model_id)

        return list(await asyncio.gather(*[_embed_one(t) for t in texts]))

    async def generate(self, prompt: str) -> str:
        """
        Non-streaming generation via Claude on Bedrock.
        Collects the full streamed response into a single string.
        """
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": settings.bedrock_max_tokens,
            "temperature": settings.bedrock_temperature,
            "messages": [{"role": "user", "content": prompt}],
        })
        tokens = []
        async with _boto_session.client(
            "bedrock-runtime", region_name=settings.aws_region
        ) as client:
            resp = await client.invoke_model_with_response_stream(
                modelId=settings.bedrock_llm_model,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
            async for event in resp["body"]:
                chunk = event.get("chunk")
                if chunk:
                    data = json.loads(chunk["bytes"])
                    if data.get("type") == "content_block_delta":
                        token = data.get("delta", {}).get("text", "")
                        if token:
                            tokens.append(token)
                    elif data.get("type") == "message_stop":
                        break
        return "".join(tokens).strip()
