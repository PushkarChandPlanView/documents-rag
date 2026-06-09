"""
AWS Bedrock LLM + embedding provider.

Embedding model : amazon.titan-embed-text-v2:0  (1024 dims — matches pgvector column)
Generation model: anthropic.claude-3-5-sonnet-20241022-v2:0 (or config override)

Requires:
  - aioboto3 installed (added to requirements.txt)
  - AWS credentials available via env vars or IAM role:
      AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY  (or instance profile)
  - AWS_REGION env var (defaults to us-east-1)
"""
import json
import logging

import aioboto3

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

# Reusable aioboto3 session (thread-safe, one per process)
_boto_session = aioboto3.Session()


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


class BedrockProvider:
    async def embed(self, text: str) -> list[float]:
        """
        Embed a single text. Supports Titan Embed v2 and Nova Multimodal Embeddings.
        Returns a 1024-dimensional vector.
        """
        model_id = settings.bedrock_embed_model
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

    async def generate_stream(self, prompt: str):
        """
        Stream tokens from Anthropic Claude via Bedrock
        using invoke_model_with_response_stream.
        """
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": settings.bedrock_max_tokens,
            "temperature": settings.bedrock_temperature,
            "messages": [{"role": "user", "content": prompt}],
        })
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
                    # Claude streaming events
                    if data.get("type") == "content_block_delta":
                        token = data.get("delta", {}).get("text", "")
                        if token:
                            yield token
                    elif data.get("type") == "message_stop":
                        break

    async def generate(self, prompt: str) -> str:
        """
        Non-streaming generation — collects the full response string.
        Used by summarization workers.
        """
        tokens = []
        async for token in self.generate_stream(prompt):
            tokens.append(token)
        return "".join(tokens).strip()
