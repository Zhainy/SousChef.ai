import asyncio
import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi.concurrency import run_in_threadpool
from openai import APIConnectionError, APIStatusError, APITimeoutError

from ..config import settings
from ..schemas import ChatMessage
from .tools import execute_tool, openai_tools

RECIPE_FENCE = "```json"

SYSTEM_INSTRUCTION = (
    'Eres "SousChef", un asistente de cocina que prepara recetas usando SOLO lo que hay '
    "en la despensa del usuario.\n\n"
    "Reglas:\n"
    "1. Cuando el usuario pregunte qué puede cocinar, llama primero a get_inventario() "
    "para conocer el stock real.\n"
    "2. Usa SIEMPRE los nombres de ingrediente exactos que devuelve get_inventario() "
    "y las mismas unidades.\n"
    "3. Cuando sugieras una receta, escribe ÚNICAMENTE una presentación breve de 1-2 "
    "frases. NO repitas en el texto los ingredientes ni las instrucciones: esos detalles "
    "van solo en el bloque JSON que añades al final, con este esquema:\n"
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
    "    5. Responde siempre en español, de forma breve y útil.\n"
)

FORCE_RECIPE_HINT = (
    "\n\n6. El usuario acaba de pedirte la ficha de una receta. Convierte tu respuesta "
    "anterior al formato de ficha: responde con una presentación breve de 1-2 frases "
    "seguida del bloque JSON ```json con el esquema indicado. Entrega la receta aunque "
    "falte algún ingrediente (usa la más cercana con lo disponible)."
)

TRANSIENT_CODES = {429, 500, 502, 503}
MAX_ATTEMPTS = 3
RETRY_DELAY = 2.0


@dataclass
class TurnEvent:
    kind: str
    data: Any


class AIProviderError(Exception):
    """Error recuperable de un proveedor de IA.
    Si se lanza antes de emitir tokens, activa el fallback automático.
    """

    def __init__(self, provider: str, cause: Exception) -> None:
        self.provider = provider
        self.cause = cause
        super().__init__(f"[{provider}] {cause}")


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
    force_recipe: bool = False,
) -> AsyncIterator[TurnEvent]:
    owns_client = client is None
    http = client or httpx.AsyncClient(timeout=None)
    messages: list[dict[str, Any]] = [{"role": m.role, "content": m.content} for m in history]
    system = SYSTEM_INSTRUCTION + (FORCE_RECIPE_HINT if force_recipe else "")
    messages.insert(0, {"role": "system", "content": system})
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
# Proveedor OCI Generative AI
# ---------------------------------------------------------------------------

def _build_oci_auth() -> Any:
    """Construye el signer correcto según OCI_AUTH_TYPE.

    - "api_key": lee ~/.oci/config (desarrollo local).
    - "instance_principal": usa el IAM role de la VM OCI (producción).
    """
    from oci_openai import OciInstancePrincipalAuth, OciUserPrincipalAuth

    if settings.oci_auth_type == "instance_principal":
        return OciInstancePrincipalAuth()
    return OciUserPrincipalAuth()  # default: api_key via ~/.oci/config


def _build_oci_client() -> Any:
    """Construye el AsyncOciOpenAI con endpoint y autenticación correctos."""
    from oci_openai import AsyncOciOpenAI

    endpoint = settings.oci_service_endpoint or (
        f"https://inference.generativeai.{settings.oci_region}.oci.oraclecloud.com"
    )
    return AsyncOciOpenAI(
        auth=_build_oci_auth(),
        service_endpoint=endpoint,
        compartment_id=settings.oci_compartment_id,
        timeout=float(settings.oci_timeout_seconds),
        max_retries=0,  # gestionamos los reintentos manualmente
    )


def _is_oci_transient(exc: Exception) -> bool:
    """Determina si un error de la API de OCI es transitorio y merece reintento."""
    if isinstance(exc, APITimeoutError):
        return True
    if isinstance(exc, APIStatusError):
        return exc.status_code in TRANSIENT_CODES
    return False


async def oci_stream(
    history: list[ChatMessage],
    force_recipe: bool = False,
) -> AsyncIterator[TurnEvent]:
    """Stream del proveedor OCI Generative AI.

    Usa la API Chat Completions compatible con OpenAI expuesta por OCI.
    Implementa el mismo contrato de TurnEvent que local_stream():
      token → tool_call → tool_result → text
    Lanza AIProviderError en fallos recuperables para activar el fallback.
    """
    if not settings.oci_compartment_id:
        raise AIProviderError(
            "oci",
            ValueError("OCI_COMPARTMENT_ID no está configurado en el entorno."),
        )

    client = _build_oci_client()
    messages: list[dict[str, Any]] = [{"role": m.role, "content": m.content} for m in history]
    system = SYSTEM_INSTRUCTION + (FORCE_RECIPE_HINT if force_recipe else "")
    messages.insert(0, {"role": "system", "content": system})

    try:
        while True:
            payload: dict[str, Any] = {
                "model": settings.oci_model_id,
                "messages": messages,
                "tools": openai_tools(),
                "stream": True,
            }

            # --- un turno con reintentos ante errores transitorios ---
            text = ""
            emitted = 0
            calls: dict[int, dict[str, Any]] = {}
            saw_content = False

            for attempt in range(MAX_ATTEMPTS):
                text = ""
                emitted = 0
                calls = {}
                saw_content = False
                try:
                    response = await client.chat.completions.create(**payload)
                    async for chunk in response:
                        choices = chunk.choices
                        if not choices:
                            continue
                        delta = choices[0].delta

                        content = getattr(delta, "content", None)
                        if content:
                            saw_content = True
                            text += content
                            partial, emitted = _emit_text_delta(text, emitted)
                            if partial:
                                yield TurnEvent("token", partial)

                        for tool_call in getattr(delta, "tool_calls", None) or []:
                            saw_content = True
                            index = tool_call.index
                            call = calls.setdefault(
                                index, {"name": "", "arguments": "", "id": None}
                            )
                            if tool_call.id:
                                call["id"] = tool_call.id
                            fn = getattr(tool_call, "function", None)
                            if fn:
                                call["name"] += fn.name or ""
                                call["arguments"] += fn.arguments or ""

                    break  # turno completado sin excepciones

                except (APITimeoutError, APIConnectionError, APIStatusError) as exc:
                    if saw_content or not _is_oci_transient(exc) or attempt >= MAX_ATTEMPTS - 1:
                        raise AIProviderError("oci", exc) from exc
                    await asyncio.sleep(RETRY_DELAY * (attempt + 1))
                    continue

            # --- resolver tool calls si las hay ---
            if calls:
                assistant_msg: dict[str, Any] = {
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
                messages.append(assistant_msg)
                for _, call in sorted(calls.items()):
                    try:
                        args = json.loads(call["arguments"]) if call["arguments"] else {}
                    except json.JSONDecodeError:
                        args = {}
                    yield TurnEvent("tool_call", {"name": call["name"], "args": args})
                    result = await run_in_threadpool(execute_tool, call["name"], args)
                    yield TurnEvent("tool_result", {"name": call["name"], "result": result})
                    messages.append(
                        {"role": "tool", "tool_call_id": call["id"], "content": result}
                    )
                continue  # siguiente turno del modelo

            yield TurnEvent("text", text)
            return

    except AIProviderError:
        raise  # propagar limpiamente para el fallback en stream_chat()
    except Exception as exc:
        raise AIProviderError("oci", exc) from exc
