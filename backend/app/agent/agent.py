import asyncio
import hashlib
import json
import re
from collections.abc import AsyncIterable, AsyncIterator

from fastapi.concurrency import run_in_threadpool
from fastapi.sse import ServerSentEvent
from google import genai
from google.genai import types

from ..config import settings
from ..schemas import ChatMessage
from .image_service import generate_recipe_image
from .tools import execute_tool

SYSTEM_INSTRUCTION = (
    'Eres "SousChef", un asistente de cocina que prepara recetas usando SOLO lo que hay '
    "en la despensa del usuario.\n\n"
    "Reglas:\n"
    "1. Cuando el usuario pregunte qué puede cocinar, llama primero a get_inventario() "
    "para conocer el stock real.\n"
    "2. Usa SIEMPRE los nombres de ingrediente exactos que devuelve get_inventario() "
    "y las mismas unidades.\n"
    "3. Cuando sugieras una receta, además del texto, incluye al final un bloque JSON "
    "cercado con este esquema:\n"
    "```json\n"
    '{"nombre": "...", "resumen": "...", "tiempo_minutos": 25, "ingredientes": '
    '[{"nombre": "...", "cantidad": 200}], "instrucciones": "1. ..."}\n'
    "```\n"
    '   - "cantidad" va en la misma unidad que tiene ese ingrediente en la despensa.\n'
    "   - No inventes ingredientes que no estén en el inventario.\n"
    "4. Solo llama a descontar_stock(ingredientes=[...]) cuando el usuario pida "
    "explícitamente cocinar esa receta. Si falta stock, infórmalo amablemente.\n"
    "5. Responde siempre en español, de forma breve y útil.\n"
)

RECIPE_FENCE = "```json"

TRANSIENT_CODES = {429, 500, 502, 503}
MAX_ATTEMPTS = 3
RETRY_DELAY = 2.0


def _is_transient(exc: Exception) -> bool:
    return getattr(exc, "code", None) in TRANSIENT_CODES


def _tool_config() -> types.GenerateContentConfig:
    get_inventario_decl = types.FunctionDeclaration(
        name="get_inventario",
        description=(
            "Consulta el inventario actual de la despensa. Devuelve nombres, "
            "cantidades, unidades y categorías."
        ),
        parameters=types.Schema(type=types.Type.OBJECT, properties={}),
    )
    descontar_decl = types.FunctionDeclaration(
        name="descontar_stock",
        description=(
            "Descuenta las cantidades indicadas de la despensa tras cocinar una "
            "receta. Devuelve lo descontado o los faltantes."
        ),
        parameters=types.Schema(
            type=types.Type.OBJECT,
            properties={
                "ingredientes": types.Schema(
                    type=types.Type.ARRAY,
                    items=types.Schema(
                        type=types.Type.OBJECT,
                        properties={
                            "nombre": types.Schema(type=types.Type.STRING),
                            "cantidad": types.Schema(type=types.Type.NUMBER),
                        },
                        required=["nombre", "cantidad"],
                    ),
                )
            },
            required=["ingredientes"],
        ),
    )
    return types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        tools=[
            types.Tool(function_declarations=[get_inventario_decl, descontar_decl]),
        ],
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(
                mode=types.FunctionCallingConfigMode.AUTO
            )
        ),
        temperature=0.7,
    )


def _build_contents(messages: list[ChatMessage]) -> list[types.Content]:
    contents: list[types.Content] = []
    for msg in messages:
        role = "model" if msg.role == "assistant" else "user"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg.content)]))
    return contents


def _visible_prefix(text: str) -> str | None:
    idx = text.find(RECIPE_FENCE)
    return text[:idx] if idx != -1 else None


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


async def _model_turn(
    ai: genai.Client,
    contents: list[types.Content],
    config: types.GenerateContentConfig,
) -> AsyncIterator[tuple[str, object]]:
    """Streams one model turn, retrying transient errors that occur before any output."""
    for attempt in range(MAX_ATTEMPTS):
        response = await ai.aio.models.generate_content_stream(
            model=settings.gemini_model,
            contents=contents,
            config=config,
        )
        text = ""
        call_parts: list[types.Part] = []
        emitted = 0
        saw_content = False
        try:
            async for chunk in response:
                if not chunk.parts:
                    continue
                for part in chunk.parts:
                    if part.function_call is not None:
                        saw_content = True
                        if text:
                            call_parts.append(types.Part.from_text(text=text))
                            text = ""
                        call_parts.append(part)
                    elif part.text:
                        saw_content = True
                        text += part.text
                        limit = len(text)
                        prefix = _visible_prefix(text)
                        if prefix is not None:
                            limit = text.index(RECIPE_FENCE)
                        if limit > emitted:
                            delta = text[emitted:limit]
                            if delta:
                                yield ("token", delta)
                            emitted = limit
        except Exception as exc:  # noqa: BLE001
            if saw_content or not _is_transient(exc) or attempt >= MAX_ATTEMPTS - 1:
                raise
            await asyncio.sleep(RETRY_DELAY * (attempt + 1))
            continue
        yield ("result", (text, call_parts))
        return


async def stream_chat(
    messages: list[ChatMessage],
    client: genai.Client | None = None,
) -> AsyncIterable[ServerSentEvent]:
    if client is None and not settings.gemini_api_key:
        yield ServerSentEvent(
            data={"message": "Falta configurar GEMINI_API_KEY en el backend."},
            event="error",
        )
        return
    ai = client or genai.Client(api_key=settings.gemini_api_key)
    contents = _build_contents(messages)
    config = _tool_config()

    try:
        while True:
            text = ""
            call_parts: list[types.Part] = []
            async for kind, payload in _model_turn(ai, contents, config):
                if kind == "token":
                    yield ServerSentEvent(data={"delta": payload}, event="token")
                else:
                    text, call_parts = payload

            if call_parts:
                parts = list(call_parts)
                if text:
                    parts.append(types.Part.from_text(text=text))
                contents.append(types.Content(role="model", parts=parts))
                responses: list[types.Part] = []
                for part in call_parts:
                    fc = part.function_call
                    if fc is None:
                        continue
                    yield ServerSentEvent(
                        data={"name": fc.name, "args": fc.args or {}},
                        event="tool_call",
                    )
                    result = await run_in_threadpool(execute_tool, fc.name, fc.args or {})
                    yield ServerSentEvent(
                        data={"name": fc.name, "result": result},
                        event="tool_result",
                    )
                    responses.append(
                        types.Part(
                            function_response=types.FunctionResponse(
                                name=fc.name,
                                response={"result": result},
                                id=fc.id,
                            )
                        )
                    )
                if responses:
                    contents.append(types.Content(role="user", parts=responses))
                continue

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
            return
    except Exception as exc:  # noqa: BLE001
        yield ServerSentEvent(data={"message": str(exc)}, event="error")
