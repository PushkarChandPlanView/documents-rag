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


class BedrockWorkerProvider:
    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Embed a batch of texts concurrently via Titan Embed v2.
        Returns a list of 1024-dim vectors in the same order as input.
        """
        sem = asyncio.Semaphore(CONCURRENCY)

        async def _embed_one(text: str) -> list[float]:
            async with sem:
                body = json.dumps({"inputText": text})
                async with _boto_session.client(
                    "bedrock-runtime", region_name=settings.aws_region
                ) as client:
                    resp = await client.invoke_model(
                        modelId=settings.bedrock_embed_model,
                        body=body,
                        contentType="application/json",
                        accept="application/json",
                    )
                    result = json.loads(await resp["body"].read())
                    return result["embedding"]

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
