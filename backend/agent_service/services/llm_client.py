"""Bedrock LLM client — thin wrapper for text generation (non-streaming + streaming)."""
import json
import logging
from typing import AsyncGenerator

import boto3

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def _get_client():
    kwargs = dict(
        service_name="bedrock-runtime",
        region_name=settings.aws_region,
    )
    if settings.aws_access_key_id:
        kwargs["aws_access_key_id"] = settings.aws_access_key_id
        kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
        if settings.aws_session_token:
            kwargs["aws_session_token"] = settings.aws_session_token
    return boto3.client(**kwargs)


async def generate(prompt: str, max_tokens: int = 2048) -> str:
    """Non-streaming generation — returns full text."""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_generate, prompt, max_tokens)


def _sync_generate(prompt: str, max_tokens: int) -> str:
    client = _get_client()
    body = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    resp = client.invoke_model(
        modelId=settings.bedrock_llm_model,
        body=json.dumps(body),
        contentType="application/json",
        accept="application/json",
    )
    result = json.loads(resp["body"].read())
    return result["content"][0]["text"]


async def generate_stream(prompt: str, system: str = "", max_tokens: int = 4096) -> AsyncGenerator[str, None]:
    """Stream tokens via Bedrock invoke_model_with_response_stream."""
    import asyncio
    from queue import Queue, Empty

    q: Queue = Queue()

    def _stream_worker():
        try:
            client = _get_client()
            messages = [{"role": "user", "content": prompt}]
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": max_tokens,
                "messages": messages,
            }
            if system:
                body["system"] = system
            resp = client.invoke_model_with_response_stream(
                modelId=settings.bedrock_llm_model,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json",
            )
            for event in resp["body"]:
                chunk = json.loads(event["chunk"]["bytes"])
                if chunk.get("type") == "content_block_delta":
                    text = chunk.get("delta", {}).get("text", "")
                    if text:
                        q.put(text)
        except Exception as exc:
            logger.error("LLM stream error: %s", exc)
        finally:
            q.put(None)  # sentinel

    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, _stream_worker)

    while True:
        try:
            token = await loop.run_in_executor(None, q.get, True, 0.05)
            if token is None:
                break
            yield token
        except Empty:
            await asyncio.sleep(0.01)
