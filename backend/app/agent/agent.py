import hashlib
import json
import re
from collections.abc import AsyncIterable

from fastapi.concurrency import run_in_threadpool
from fastapi.sse import ServerSentEvent

from ..config import settings
from ..schemas import ChatMessage
from .image_service import generate_recipe_image
from .llm import RECIPE_FENCE, gemini_stream, local_stream


def _extract_recipe(text: str) -> dict | None:
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = match.group(1) if match else _last_json_object(text)
    if candidate is None:
        return None
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    if (
        not isinstance(data, dict)
        or not data.get("nombre")
        or not isinstance(data.get("ingredientes"), list)
    ):
        return None
    return data


def _last_json_object(text: str) -> str | None:
    start = text.rfind("{")
    if start == -1:
        return None
    depth = 0
    in_string = False
    escape = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return text[start : i + 1]
    return None


def _recipe_hash(recipe: dict) -> str:
    payload = json.dumps(
        {"nombre": recipe.get("nombre"), "ingredientes": recipe.get("ingredientes")},
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()[:16]


async def stream_chat(
    messages: list[ChatMessage],
    client=None,
) -> AsyncIterable[ServerSentEvent]:
    """Stream del agente. `client` fuerza el proveedor Gemini (usado en tests)."""
    if client is not None or settings.llm_provider == "gemini":
        if client is None and not settings.gemini_api_key:
            yield ServerSentEvent(
                data={"message": "Falta configurar GEMINI_API_KEY en el backend."},
                event="error",
            )
            return
        events = gemini_stream(messages, client=client)
    else:
        events = local_stream(messages)

    text = ""
    try:
        async for event in events:
            if event.kind == "token":
                yield ServerSentEvent(data={"delta": event.data}, event="token")
            elif event.kind == "tool_call":
                yield ServerSentEvent(
                    data={"name": event.data["name"], "args": event.data["args"]},
                    event="tool_call",
                )
            elif event.kind == "tool_result":
                yield ServerSentEvent(
                    data={"name": event.data["name"], "result": event.data["result"]},
                    event="tool_result",
                )
            elif event.kind == "text":
                text = event.data

        recipe = _extract_recipe(text)
        if recipe is not None:
            recipe_hash = _recipe_hash(recipe)
            yield ServerSentEvent(
                data={**recipe, "hash": recipe_hash, "image_url": None},
                event="recipe",
            )
            image_url = await run_in_threadpool(generate_recipe_image, recipe, recipe_hash)
            yield ServerSentEvent(
                data={"hash": recipe_hash, "image_url": image_url},
                event="recipe_image",
            )
        final_text = text[: text.index(RECIPE_FENCE)] if RECIPE_FENCE in text else text
        yield ServerSentEvent(data={"message": final_text}, event="done")
    except Exception as exc:  # noqa: BLE001
        yield ServerSentEvent(data={"message": str(exc)}, event="error")
