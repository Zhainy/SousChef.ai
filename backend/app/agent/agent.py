import hashlib
import json
import re
from collections.abc import AsyncIterable

from fastapi.concurrency import run_in_threadpool
from fastapi.sse import ServerSentEvent

from ..config import settings
from ..schemas import ChatMessage, normalize_recipe
from .image_service import generate_recipe_image
from .llm import AIProviderError, local_stream, oci_stream


def _extract_recipe(text: str) -> dict | None:
    match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    candidate = match.group(1) if match else _last_json_object(text)
    if candidate is None:
        return None
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    recipe = normalize_recipe(data)
    return recipe.model_dump() if recipe is not None else None


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


def _visible_limit(text: str) -> int:
    """Índice donde empieza el JSON de la receta (fence ```), o el final del texto."""
    fence = text.find("```")
    return len(text) if fence == -1 else fence


async def _consume_events(
    events: AsyncIterable,
    text_acc: list[str],
    emitted_acc: list[int],
) -> AsyncIterable[ServerSentEvent]:
    """Itera sobre TurnEvents y los convierte en SSE.

    Recibe listas mutables para acumular el texto y la posición emitida,
    lo que permite que stream_chat() acceda al texto final tras el loop.
    Lanza AIProviderError si el proveedor falla ANTES de emitir tokens.
    """
    async for event in events:
        if event.kind == "token":
            text_acc[0] += event.data
            limit = _visible_limit(text_acc[0])
            delta = text_acc[0][emitted_acc[0] : limit]
            emitted_acc[0] = limit
            if delta:
                yield ServerSentEvent(data={"delta": delta}, event="token")
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
            text_acc[0] = event.data


async def stream_chat(
    messages: list[ChatMessage],
    force_recipe: bool = False,
) -> AsyncIterable[ServerSentEvent]:
    """Stream del agente con soporte de IA híbrida y fallback automático.

    Flujo:
      1. Selecciona el proveedor según LLM_PROVIDER (oci | local).
      2. Emite provider_info SSE al inicio para que el frontend muestre el badge.
      3. Si el proveedor primario lanza AIProviderError ANTES de emitir tokens
         y AI_FALLBACK_ENABLED=true, reintenta con el proveedor de fallback.
      4. Si ya se emitieron tokens, propaga el error normalmente.
    """
    provider = settings.llm_provider  # "oci" | "local"
    used_fallback = False

    # --- selección de proveedor primario ---
    if provider == "oci":
        events = oci_stream(messages, force_recipe=force_recipe)
    else:
        events = local_stream(messages, force_recipe=force_recipe)

    provider_info_emitted = False

    if provider == "local":
        yield ServerSentEvent(
            data={"provider": "local", "fallback": False},
            event="provider_info",
        )
        provider_info_emitted = True

    text_acc = [""]  # lista mutable para acceder al texto acumulado post-loop
    emitted_acc = [0]
    tokens_emitted = False

    try:
        # --- primer intento con el proveedor primario ---
        async for sse in _consume_events(events, text_acc, emitted_acc):
            if not provider_info_emitted:
                yield ServerSentEvent(
                    data={"provider": provider, "fallback": False},
                    event="provider_info",
                )
                provider_info_emitted = True
            if sse.event == "token":
                tokens_emitted = True
            yield sse

    except Exception as exc:
        # Solo hacemos fallback si no se emitió ningún token todavía
        if tokens_emitted or not settings.ai_fallback_enabled:
            yield ServerSentEvent(data={"message": str(exc)}, event="error")
            return

        # --- fallback al proveedor secundario ---
        used_fallback = True
        fallback_provider = settings.ai_fallback_provider  # siempre "local" por ahora
        yield ServerSentEvent(
            data={"provider": fallback_provider, "fallback": True},
            event="provider_info",
        )
        provider_info_emitted = True

        text_acc = [""]
        emitted_acc = [0]
        fallback_events = local_stream(messages, force_recipe=force_recipe)
        try:
            async for sse in _consume_events(fallback_events, text_acc, emitted_acc):
                if sse.event == "token":
                    tokens_emitted = True
                yield sse
        except Exception as fallback_exc:  # noqa: BLE001
            yield ServerSentEvent(data={"message": str(fallback_exc)}, event="error")
            return

    # Si por alguna razón el stream terminó sin eventos y sin haber emitido provider_info
    if not provider_info_emitted:
        actual_provider = settings.ai_fallback_provider if used_fallback else provider
        yield ServerSentEvent(
            data={"provider": actual_provider, "fallback": used_fallback},
            event="provider_info",
        )

    # --- post-procesamiento: receta e imagen ---
    text = text_acc[0]
    try:
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
        final_text = text[: _visible_limit(text)]
        yield ServerSentEvent(data={"message": final_text}, event="done")
    except Exception as exc:  # noqa: BLE001
        yield ServerSentEvent(data={"message": str(exc)}, event="error")
