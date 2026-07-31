import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi.concurrency import run_in_threadpool
from google import genai
from google.genai import types

from ..config import settings
from ..schemas import ChatMessage
from .tools import execute_tool, gemini_tools, openai_tools

RECIPE_FENCE = "```json"

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
    '[{"nombre": "...", "cantidad": 200, "unidad": "g"}], "instrucciones": "1. ...\\n2. ..."}\n'
    "```\n"
    '   - "cantidad" y "unidad" van en la misma unidad que tiene ese ingrediente en la '
    "despensa (p. ej. g, ml, pieza, cucharada, lata).\n"
    '   - Si un ingrediente usa "latas", "sobres" o "bolsas", el inventario incluye '
    '"gramos_por_unidad"; puedes expresar la cantidad en gramos multiplicando por ese dato.\n'
    '   - Escribe "instrucciones" como pasos numerados (1. ..., 2. ...), uno por línea.\n'
    "   - No inventes ingredientes que no estén en el inventario.\n"
    "4. Solo llama a descontar_stock(ingredientes=[...]) cuando el usuario pida "
    "explícitamente cocinar esa receta. Si falta stock, infórmalo amablemente.\n"
    "5. Responde siempre en español, de forma breve y útil.\n"
)

TRANSIENT_CODES = {429, 500, 502, 503}
MAX_ATTEMPTS = 3
RETRY_DELAY = 2.0


@dataclass
class TurnEvent:
    kind: str
    data: Any


def _is_transient(exc: Exception) -> bool:
    return getattr(exc, "code", None) in TRANSIENT_CODES


def _emit_text_delta(text: str, emitted: int) -> tuple[str, int]:
    limit = text.find(RECIPE_FENCE)
    if limit == -1:
        limit = len(text)
    delta = text[emitted:limit]
    return delta, limit


# ---------------------------------------------------------------------------
# Proveedor local (llama.cpp / API compatible con OpenAI)
# ---------------------------------------------------------------------------


async def _post_stream(
    client: httpx.AsyncClient, url: str, payload: dict[str, Any]
) -> AsyncIterator[dict[str, Any]]:
    async with client.stream("POST", url, json=payload) as response:
        response.raise_for_status()
        async for line in response.aiter_lines():
            if not line.startswith("data:"):
                continue
            data = line[5:].strip()
            if not data or data == "[DONE]":
                continue
            yield json.loads(data)


async def local_stream(
    history: list[ChatMessage],
    client: httpx.AsyncClient | None = None,
) -> AsyncIterator[TurnEvent]:
    owns_client = client is None
    http = client or httpx.AsyncClient(timeout=None)
    messages: list[dict[str, Any]] = [{"role": m.role, "content": m.content} for m in history]
    messages.insert(0, {"role": "system", "content": SYSTEM_INSTRUCTION})
    url = settings.local_llm_base_url.rstrip("/") + "/chat/completions"
    try:
        while True:
            payload = {
                "model": settings.local_llm_model,
                "messages": messages,
                "tools": openai_tools(),
                "stream": True,
            }
            text = ""
            emitted = 0
            calls: dict[int, dict[str, Any]] = {}
            async for chunk in _post_stream(http, url, payload):
                choices = chunk.get("choices")
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                if delta.get("content"):
                    text += delta["content"]
                    partial, emitted = _emit_text_delta(text, emitted)
                    if partial:
                        yield TurnEvent("token", partial)
                for tool_call in delta.get("tool_calls") or []:
                    index = tool_call["index"]
                    call = calls.setdefault(index, {"name": "", "arguments": "", "id": None})
                    if tool_call.get("id"):
                        call["id"] = tool_call["id"]
                    function = tool_call.get("function") or {}
                    call["name"] += function.get("name", "")
                    call["arguments"] += function.get("arguments", "")

            if calls:
                assistant_message: dict[str, Any] = {
                    "role": "assistant",
                    "content": text or None,
                    "tool_calls": [
                        {
                            "id": call["id"],
                            "type": "function",
                            "function": {
                                "name": call["name"],
                                "arguments": call["arguments"],
                            },
                        }
                        for _, call in sorted(calls.items())
                    ],
                }
                messages.append(assistant_message)
                for _, call in sorted(calls.items()):
                    try:
                        args = json.loads(call["arguments"]) if call["arguments"] else {}
                    except json.JSONDecodeError:
                        args = {}
                    yield TurnEvent("tool_call", {"name": call["name"], "args": args})
                    result = await run_in_threadpool(execute_tool, call["name"], args)
                    yield TurnEvent("tool_result", {"name": call["name"], "result": result})
                    messages.append({"role": "tool", "tool_call_id": call["id"], "content": result})
                continue

            yield TurnEvent("text", text)
            return
    finally:
        if owns_client:
            await http.aclose()


# ---------------------------------------------------------------------------
# Proveedor Gemini
# ---------------------------------------------------------------------------


def _build_contents(messages: list[ChatMessage]) -> list[types.Content]:
    contents: list[types.Content] = []
    for msg in messages:
        role = "model" if msg.role == "assistant" else "user"
        contents.append(types.Content(role=role, parts=[types.Part.from_text(text=msg.content)]))
    return contents


def _tool_config() -> types.GenerateContentConfig:
    return types.GenerateContentConfig(
        system_instruction=SYSTEM_INSTRUCTION,
        tools=gemini_tools(),
        tool_config=types.ToolConfig(
            function_calling_config=types.FunctionCallingConfig(
                mode=types.FunctionCallingConfigMode.AUTO
            )
        ),
        temperature=0.7,
    )


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
                        delta, limit = _emit_text_delta(text, emitted)
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


async def gemini_stream(
    history: list[ChatMessage],
    client: genai.Client | None = None,
) -> AsyncIterator[TurnEvent]:
    ai = client or genai.Client(api_key=settings.gemini_api_key)
    contents = _build_contents(history)
    config = _tool_config()

    while True:
        text = ""
        call_parts: list[types.Part] = []
        async for kind, payload in _model_turn(ai, contents, config):
            if kind == "token":
                yield TurnEvent("token", payload)
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
                yield TurnEvent("tool_call", {"name": fc.name, "args": fc.args or {}})
                result = await run_in_threadpool(execute_tool, fc.name, fc.args or {})
                yield TurnEvent("tool_result", {"name": fc.name, "result": result})
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

        yield TurnEvent("text", text)
        return
