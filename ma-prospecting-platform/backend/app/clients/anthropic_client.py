import json
import logging

from anthropic import AsyncAnthropic

from app.config import settings
from app.dependencies import get_anthropic_client

logger = logging.getLogger(__name__)


async def call_claude(
    prompt: str,
    system_prompt: str = "",
    model: str | None = None,
    max_tokens: int = 2048,
    temperature: float = 0.0,
    response_json: bool = True,
) -> dict | str:
    """Call Claude and return parsed JSON or raw text."""
    client = get_anthropic_client()
    model = model or settings.claude_model

    messages = [{"role": "user", "content": prompt}]

    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
        "temperature": temperature,
    }
    if system_prompt:
        kwargs["system"] = system_prompt

    logger.info(f"Calling Claude ({model}) | max_tokens={max_tokens} | temp={temperature}")

    response = await client.messages.create(**kwargs)
    content = response.content[0].text

    if response_json:
        # Strip markdown code fences if present
        text = content.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())

    return content


async def call_claude_streaming(
    prompt: str,
    system_prompt: str = "",
    model: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.4,
):
    """Stream Claude response for chat interface."""
    client = get_anthropic_client()
    model = model or settings.claude_model

    messages = [{"role": "user", "content": prompt}]

    kwargs = {
        "model": model,
        "max_tokens": max_tokens,
        "messages": messages,
        "temperature": temperature,
    }
    if system_prompt:
        kwargs["system"] = system_prompt

    async with client.messages.stream(**kwargs) as stream:
        async for text in stream.text_stream:
            yield text
