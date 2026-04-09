import json
import logging
import time

from app.config import settings
from app.dependencies import get_anthropic_client

logger = logging.getLogger(__name__)


def _extract_text_content(response) -> str:
    parts: list[str] = []
    for block in getattr(response, "content", []) or []:
        text = getattr(block, "text", None)
        if text:
            parts.append(text)
    return "\n".join(parts).strip()


def _parse_json_text(content: str) -> dict | list:
    text = content.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    decoder = json.JSONDecoder()
    for idx, ch in enumerate(text):
        if ch not in "[{":
            continue
        try:
            parsed, _end = decoder.raw_decode(text[idx:])
            return parsed
        except json.JSONDecodeError:
            continue

    raise json.JSONDecodeError("No JSON object or array found in response", text, 0)


async def call_claude(
    prompt: str,
    system_prompt: str = "",
    model: str | None = None,
    max_tokens: int = 2048,
    temperature: float = 0.0,
    response_json: bool = True,
    label: str = "claude",
    tools: list[dict] | None = None,
    tool_choice: dict | None = None,
) -> dict | list | str:
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
    if tools:
        kwargs["tools"] = tools
    if tool_choice:
        kwargs["tool_choice"] = tool_choice

    prompt_chars = len(prompt) + len(system_prompt)
    logger.info(
        "[CLAUDE] %-28s | model=%-30s | max_tokens=%d | temp=%.1f | prompt_chars=%d | tools=%d",
        label, model, max_tokens, temperature, prompt_chars, len(tools or []),
    )

    t0 = time.monotonic()
    response = await client.messages.create(**kwargs)
    elapsed = time.monotonic() - t0

    content = _extract_text_content(response)
    usage = response.usage
    # server_tool_use lives under usage, not on the top-level response object
    server_tool_use = getattr(usage, "server_tool_use", None)
    web_search_requests = getattr(server_tool_use, "web_search_requests", 0) if server_tool_use else 0
    logger.info(
        "[CLAUDE] %-28s | done in %5.1fs | in_tokens=%d | out_tokens=%d | response_chars=%d | web_searches=%d",
        label, elapsed,
        getattr(usage, "input_tokens", 0),
        getattr(usage, "output_tokens", 0),
        len(content),
        web_search_requests,
    )

    if response_json:
        return _parse_json_text(content)

    return content


async def call_claude_streaming(
    prompt: str,
    system_prompt: str = "",
    model: str | None = None,
    max_tokens: int = 4096,
    temperature: float = 0.4,
    label: str = "claude/stream",
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

    prompt_chars = len(prompt) + len(system_prompt)
    logger.info(
        "[CLAUDE] %-28s | model=%-30s | max_tokens=%d | prompt_chars=%d | streaming=True",
        label, model, max_tokens, prompt_chars,
    )

    t0 = time.monotonic()
    chars_streamed = 0
    async with client.messages.stream(**kwargs) as stream:
        async for text in stream.text_stream:
            chars_streamed += len(text)
            yield text

    elapsed = time.monotonic() - t0
    logger.info(
        "[CLAUDE] %-28s | stream done in %5.1fs | chars_streamed=%d",
        label, elapsed, chars_streamed,
    )
