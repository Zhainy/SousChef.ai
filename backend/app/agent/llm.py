import asyncio
import json
import re
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi.concurrency import run_in_threadpool
from openai import APIConnectionError, APIStatusError, APITimeoutError

from ..config import settings
from ..schemas import ChatMessage
from .tools import TOOL_DEFS, execute_tool, openai_tools

RECIPE_FENCE = "```json"

SYSTEM_INSTRUCTION = (
    'Eres "SousChef", un asistente de cocina inteligente que prepara recetas deliciosas usando '
    "ÚNICAMENTE lo que hay disponible en la despensa del usuario.\n\n"
    "Reglas Obligatorias:\n"
    "1. Cuando el usuario pregunte qué cocinar o pida sugerencias, llama primero a get_inventario() "
    "para conocer el stock real disponible.\n"
    "2. REGLA CRÍTICA DE CANTIDADES: La cantidad de CADA ingrediente en la receta NUNCA debe superar "
    "la cantidad disponible en get_inventario(). Si el usuario tiene disponible 10 g de mantequilla, "
    "la receta debe usar COMO MÁXIMO 10 g de mantequilla (ej: 10 g o 5 g), NUNCA 15 g ni 20 g. "
    "Ajusta las porciones culinarias a lo disponible para que el usuario pueda cocinar sin que falte stock.\n"
    "3. Usa SIEMPRE los nombres exactos y las unidades del inventario (ej: 'g', 'ml', 'piezas', 'paquetes', 'latas'). "
    "Si un ingrediente está en 'paquete' (ej: pasta), pide en 'paquete' (ej: 0.5 paquete, 1 paquete) o en gramos 'g' "
    "sin superar los gramos totales disponibles (gramos_por_unidad * cantidad).\n"
    "4. Cuando sugieras una receta, escribe ÚNICAMENTE una presentación breve de 1-2 "
    "frases amables. NO repitas en el texto los ingredientes ni las instrucciones: esos detalles "
    "van solo en el bloque JSON que añades al final, con este esquema exacto:\n"
    "```json\n"
    '{"nombre": "...", "resumen": "...", "tiempo_minutos": 25, "ingredientes": '
    '[{"nombre": "...", "cantidad": 200, "unidad": "g"}], "instrucciones": "1. ...\\n2. ..."}\n'
    "```\n"
    '   - Escribe "instrucciones" como pasos numerados detallados y claros (1. ..., 2. ...), uno por línea. '
    'Cada paso debe explicar la técnica culinaria precisa (ej: saltear a fuego medio, hervir con sal, dorar), '
    'los tiempos de cocción aproximados y consejos prácticos para que el plato quede delicioso. '
    'Evita pasos telegráficos, vagos o excesivamente breves.\n'
    "   - No inventes ingredientes que no estén en el inventario.\n"
    "5. Solo llama a descontar_stock(ingredientes=[...]) cuando el usuario pida "
    "explícitamente cocinar esa receta.\n"
    "6. Responde siempre en español, de forma breve, cálida y útil.\n"
    "7. IMPORTANTE: Para llamar a una herramienta usa EXCLUSIVAMENTE el mecanismo nativo "
    "de function calling de la API. NUNCA escribas el JSON de una herramienta como texto "
    "plano en tu respuesta. Si necesitas llamar a get_inventario o descontar_stock, hazlo "
    "solo a través del mecanismo de tool_calls de la API.\n"
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


# ---------------------------------------------------------------------------
# Parser de tool calls escritos como texto plano.
# Soporta múltiples formatos que los modelos locales (Qwen, Llama) usan:
#   1. Nativo OpenAI:  {"name": "...", "arguments": {...}}
#   2. Qwen tag:       <tool_call>{"name": "...", "arguments": {...}}</tool_call>
#   3. Qwen/Llama alt: {"name": "...", "parameters": {...}}
# ---------------------------------------------------------------------------

_TOOL_NAMES = {d["name"] for d in TOOL_DEFS}

# Formato 1 y 3: objeto JSON con "name" + ("arguments" | "parameters")
_TEXT_TOOL_RE = re.compile(
    r'\{\s*"name"\s*:\s*"([^"]+)"\s*,\s*"(?:arguments|parameters)"\s*:\s*'
    r'(\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}|\{\s*\})\s*\}',
    re.DOTALL,
)
# Formato 2: tags <tool_call>...</tool_call> de Qwen
_QWEN_TAG_RE = re.compile(
    r'<tool_call>\s*(\{.*?\})\s*</tool_call>',
    re.DOTALL,
)


def _extract_text_tool_calls(text: str) -> list[dict[str, Any]]:
    """Extrae tool calls escritos como texto plano en el contenido.

    Detecta tres formatos comunes de modelos locales (Qwen, Llama 3.3):
      1. {"name": "...", "arguments": {...}}
      2. <tool_call>{"name": "...", "arguments": {...}}</tool_call>
      3. {"name": "...", "parameters": {...}}
    Solo reconoce herramientas registradas en TOOL_DEFS.
    Devuelve lista de dicts {name, arguments} donde arguments es str JSON.
    """
    results: list[dict[str, Any]] = []
    seen_names: set[str] = set()  # evitar duplicados

    # Primero buscar tags Qwen (más específico)
    for match in _QWEN_TAG_RE.finditer(text):
        try:
            obj = json.loads(match.group(1))
            name = obj.get("name", "")
            if name in _TOOL_NAMES and name not in seen_names:
                args = obj.get("arguments", obj.get("parameters", {}))
                args_str = json.dumps(args, ensure_ascii=False) if isinstance(args, dict) else args
                results.append({"name": name, "arguments": args_str})
                seen_names.add(name)
        except (json.JSONDecodeError, AttributeError):
            continue

    # Luego buscar formato JSON plano
    for match in _TEXT_TOOL_RE.finditer(text):
        name = match.group(1)
        if name in _TOOL_NAMES and name not in seen_names:
            results.append({"name": name, "arguments": match.group(2)})
            seen_names.add(name)

    return results


def _strip_text_tool_calls(text: str) -> str:
    """Elimina los JSON de tool calls del texto para no mostrarlos al usuario."""
    cleaned = _QWEN_TAG_RE.sub("", text)
    cleaned = _TEXT_TOOL_RE.sub("", cleaned)
    return re.sub(r'\n{3,}', '\n\n', cleaned).strip()


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
    target_urls = []
    # Si la URL usa el hostname de docker 'llama-cpp', priorizar host.docker.internal
    # para aprovechar la GPU del host si ./scripts/serve_local.sh está corriendo
    if "://llama-cpp:" in url:
        target_urls.append(url.replace("://llama-cpp:", "://host.docker.internal:"))
        target_urls.append(url)
        target_urls.append(url.replace("://llama-cpp:", "://127.0.0.1:"))
    else:
        target_urls.append(url)

    last_error: Exception | None = None
    for target_url in target_urls:
        try:
            async with client.stream("POST", target_url, json=payload) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if not data or data == "[DONE]":
                        continue
                    yield json.loads(data)
            return
        except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
            last_error = exc
            continue
        except httpx.HTTPStatusError as exc:
            body = ""
            try:
                body = (await exc.response.aread()).decode(errors="replace")
            except Exception:
                pass
            detail = f"{exc} ({body})" if body else str(exc)
            raise AIProviderError("local", RuntimeError(detail)) from exc

    if last_error:
        raise AIProviderError(
            "local",
            ConnectionError(
                f"No se pudo conectar con el LLM local en '{url}'. "
                "Asegúrate de que llama-server esté corriendo (ej: ./scripts/serve_local.sh) "
                "o ejecuta el stack completo con 'docker compose up'."
            ),
        ) from last_error


async def local_stream(
    history: list[ChatMessage],
    client: httpx.AsyncClient | None = None,
    force_recipe: bool = False,
) -> AsyncIterator[TurnEvent]:
    owns_client = client is None
    http = client or httpx.AsyncClient(timeout=None)
    messages: list[dict[str, Any]] = [{"role": m.role, "content": m.content} for m in history if m.content]
    system = SYSTEM_INSTRUCTION + (FORCE_RECIPE_HINT if force_recipe else "")
    messages.insert(0, {"role": "system", "content": system})

    # Si force_recipe se activa justo después de un mensaje del asistente,
    # añadir un turno de usuario explícito para no dejar al asistente al final
    if force_recipe and messages and messages[-1].get("role") == "assistant":
        messages.append({
            "role": "user",
            "content": "Entrega la ficha técnica de la receta en formato JSON con el esquema solicitado.",
        })

    url = settings.local_llm_base_url.rstrip("/") + "/chat/completions"
    try:
        while True:
            payload: dict[str, Any] = {
                "model": settings.local_llm_model,
                "messages": messages,
                "stream": True,
            }
            # Solo enviar herramientas si NO estamos forzando ficha de receta
            if not force_recipe:
                payload["tools"] = openai_tools()
                payload["tool_choice"] = "auto"  # fuerza decisión explícita al modelo
            text = ""
            emitted = 0
            calls: dict[int, dict[str, Any]] = {}
            # Igual que en oci_stream: detectar si el primer token es '{'
            # para poder capturar tool calls escritos como texto plano
            maybe_text_tool = False
            first_content = True
            async for chunk in _post_stream(http, url, payload):
                choices = chunk.get("choices")
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                if delta.get("content"):
                    text += delta["content"]
                    if first_content:
                        first_content = False
                        stripped = text.lstrip()
                        maybe_text_tool = (
                            stripped.startswith("{")
                            or stripped.startswith("<tool_call>")
                        )
                    if not maybe_text_tool:
                        partial, emitted = _emit_text_delta(text, emitted)
                        if partial:
                            yield TurnEvent("token", partial)
                for tool_call in delta.get("tool_calls") or []:
                    index = tool_call["index"]
                    call = calls.setdefault(index, {"name": "", "arguments": "", "id": f"call_{index}"})
                    if tool_call.get("id"):
                        call["id"] = tool_call["id"]
                    function = tool_call.get("function") or {}
                    call["name"] += function.get("name", "")
                    call["arguments"] += function.get("arguments", "")

            # --- detectar tool calls en texto plano (Qwen / Llama fallback) ---
            if not calls and text:
                text_calls = _extract_text_tool_calls(text)
                if text_calls:
                    for idx, tc in enumerate(text_calls):
                        calls[idx] = {
                            "name": tc["name"],
                            "arguments": tc["arguments"],
                            "id": f"local_text_{idx}",
                        }
                    text = _strip_text_tool_calls(text)

            # --- emitir tokens acumulados (buffereados por maybe_text_tool) ---
            if not calls and maybe_text_tool and text:
                partial, emitted = _emit_text_delta(text, emitted)
                if partial:
                    yield TurnEvent("token", partial)

            if calls:
                assistant_message: dict[str, Any] = {
                    "role": "assistant",
                    "content": text or "",
                    "tool_calls": [
                        {
                            "id": call["id"] or f"call_{idx}",
                            "type": "function",
                            "function": {
                                "name": call["name"],
                                "arguments": call["arguments"],
                            },
                        }
                        for idx, call in sorted(calls.items())
                    ],
                }
                messages.append(assistant_message)
                for idx, call in sorted(calls.items()):
                    call_id = call["id"] or f"call_{idx}"
                    try:
                        args = json.loads(call["arguments"]) if call["arguments"] else {}
                    except json.JSONDecodeError:
                        args = {}
                    yield TurnEvent("tool_call", {"name": call["name"], "args": args})
                    result = await run_in_threadpool(execute_tool, call["name"], args)
                    yield TurnEvent("tool_result", {"name": call["name"], "result": result})
                    messages.append({"role": "tool", "tool_call_id": call_id, "content": result})
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
    from oci_openai import HttpxOciAuth, OciInstancePrincipalAuth, OciUserPrincipalAuth

    try:
        import httpx2
        if hasattr(httpx2, "Auth") and httpx2.Auth not in HttpxOciAuth.__bases__:
            HttpxOciAuth.__bases__ = (httpx2.Auth,)
    except Exception:
        pass

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

    try:
        client = _build_oci_client()
    except Exception as exc:
        raise AIProviderError("oci", exc) from exc

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
                # Indica si el contenido podría ser un tool call en texto plano
                # (comienza con '{'); en ese caso buffereamos sin emitir tokens
                maybe_text_tool = False
                first_content = True
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
                            # Al recibir el primer fragmento, decidimos si
                            # es un posible tool call en texto ({...}) o texto normal
                            if first_content:
                                first_content = False
                                maybe_text_tool = text.lstrip().startswith("{")
                            # Solo emitir tokens en tiempo real si NO es un posible
                            # tool call en texto plano
                            if not maybe_text_tool:
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

            # --- detectar tool calls escritos como texto plano (fallback Llama 3.3) ---
            if not calls and text:
                text_calls = _extract_text_tool_calls(text)
                if text_calls:
                    # El modelo escribió el tool call como JSON en el texto;
                    # procesarlo como si fuera un tool_calls estructurado
                    for idx, tc in enumerate(text_calls):
                        calls[idx] = {
                            "name": tc["name"],
                            "arguments": tc["arguments"],
                            "id": f"text_call_{idx}",
                        }
                    # No emitir el texto con los JSON crudos; limpiar antes
                    text = _strip_text_tool_calls(text)

            # --- emitir tokens del texto acumulado (si no son tool calls) ---
            if not calls and text:
                partial, emitted = _emit_text_delta(text, emitted)
                if partial:
                    yield TurnEvent("token", partial)

            # --- resolver tool calls si las hay ---
            if calls:
                # Construir IDs sintéticos para text-based calls si es necesario
                tool_calls_list = [
                    {
                        "id": call["id"] or f"call_{idx}",
                        "type": "function",
                        "function": {
                            "name": call["name"],
                            "arguments": call["arguments"],
                        },
                    }
                    for idx, call in sorted(calls.items())
                ]
                assistant_msg: dict[str, Any] = {
                    "role": "assistant",
                    "content": text or None,
                    "tool_calls": tool_calls_list,
                }
                messages.append(assistant_msg)
                for idx, call in sorted(calls.items()):
                    call_id = call["id"] or f"call_{idx}"
                    try:
                        args = json.loads(call["arguments"]) if call["arguments"] else {}
                    except json.JSONDecodeError:
                        args = {}
                    yield TurnEvent("tool_call", {"name": call["name"], "args": args})
                    result = await run_in_threadpool(execute_tool, call["name"], args)
                    yield TurnEvent("tool_result", {"name": call["name"], "result": result})
                    messages.append({"role": "tool", "tool_call_id": call_id, "content": result})
                continue  # siguiente turno del modelo

            yield TurnEvent("text", text)
            return

    except AIProviderError:
        raise  # propagar limpiamente para el fallback en stream_chat()
    except Exception as exc:
        raise AIProviderError("oci", exc) from exc
