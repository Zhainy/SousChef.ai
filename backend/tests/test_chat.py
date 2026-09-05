import asyncio
import json

import httpx
import pytest

from app.agent.agent import stream_chat
from app.agent.llm import (
    FORCE_RECIPE_HINT,
    AIProviderError,
    TurnEvent,
    local_stream,
    oci_stream,
)
from app.agent.tools import descontar_stock_tool, get_inventario
from app.schemas import ChatMessage

RECIPE_JSON = (
    '{"nombre": "Arroz con tomate", "resumen": "rápido", "tiempo_minutos": 20, '
    '"ingredientes": [{"nombre": "tomate", "cantidad": 1}, {"nombre": "arroz", "cantidad": 200}], '
    '"instrucciones": "1. Cocinar."}'
)


def _llama_body(*chunks: dict) -> bytes:
    body = "".join(f"data: {json.dumps(c)}\n" for c in chunks) + "data: [DONE]\n"
    return body.encode()


def _llama_content(text: str) -> dict:
    return {"choices": [{"index": 0, "delta": {"content": text}, "finish_reason": None}]}


def _llama_tool_fragment(index: int, *, id=None, name=None, arguments=None) -> dict:
    tool_call: dict = {"index": index}
    if id is not None:
        tool_call["id"] = id
    if name is not None or arguments is not None:
        function: dict = {}
        if name is not None:
            function["name"] = name
        if arguments is not None:
            function["arguments"] = arguments
        tool_call["function"] = function
    delta = {"tool_calls": [tool_call]}
    return {"choices": [{"index": 0, "delta": delta, "finish_reason": None}]}


def _llama_stop(finish: str) -> dict:
    return {"choices": [{"index": 0, "delta": {}, "finish_reason": finish}]}


# ---------------------------------------------------------------------------
# Tool tests
# ---------------------------------------------------------------------------


def test_get_inventario_tool(patched_tools):
    data = get_inventario()
    names = [i["nombre"] for i in data["inventario"]]
    assert "tomate" in names
    assert all("cantidad" in i for i in data["inventario"])


def test_descontar_tool_reports_faltantes(patched_tools):
    result = descontar_stock_tool(ingredientes=[{"nombre": "tomate", "cantidad": 999}])
    assert result["ok"] is False
    assert result["faltantes"][0]["motivo"] == "stock insuficiente"


# ---------------------------------------------------------------------------
# local_stream tests
# ---------------------------------------------------------------------------


def test_local_stream_text_only():
    body = _llama_body(
        _llama_content("Hola "),
        _llama_content("chef!"),
        _llama_stop("stop"),
    )

    def handler(request):
        return httpx.Response(200, content=body)

    async def _collect():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return [e async for e in local_stream([], client=http)]

    events = asyncio.run(_collect())
    assert [(e.kind, e.data) for e in events] == [
        ("token", "Hola "),
        ("token", "chef!"),
        ("text", "Hola chef!"),
    ]


def test_local_stream_tool_loop_and_recipe(patched_tools):
    turn1 = _llama_body(
        _llama_tool_fragment(0, id="call-1", name="get_inventario", arguments="{"),
        _llama_tool_fragment(0, arguments="}"),
        _llama_stop("tool_calls"),
    )
    turn2 = _llama_body(
        _llama_content(f"Te propongo:\n```json\n{RECIPE_JSON}\n```"),
        _llama_stop("stop"),
    )
    bodies = [turn1, turn2]
    seen_requests: list[dict] = []

    def handler(request):
        payload = json.loads(request.content)
        seen_requests.append(payload)
        return httpx.Response(200, content=bodies[len(seen_requests) - 1])

    async def _collect():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return [e async for e in local_stream([], client=http)]

    events = asyncio.run(_collect())
    assert [e.kind for e in events] == ["tool_call", "tool_result", "token", "text"]
    assert events[0].data["name"] == "get_inventario"
    assert events[1].data["name"] == "get_inventario"
    assert "inventario" in events[1].data["result"]
    assert events[3].data == f"Te propongo:\n```json\n{RECIPE_JSON}\n```"

    assert len(seen_requests) == 2
    assert seen_requests[0]["messages"][0]["role"] == "system"
    tool_message = seen_requests[1]["messages"][-1]
    assert tool_message["role"] == "tool"
    assert tool_message["tool_call_id"] == "call-1"
    assert "inventario" in tool_message["content"]
    assistant_message = seen_requests[1]["messages"][-2]
    assert assistant_message["role"] == "assistant"
    assert assistant_message["tool_calls"][0]["id"] == "call-1"


def test_local_stream_connection_failure_raises_ai_provider_error(monkeypatch):
    from app.agent.llm import AIProviderError, local_stream

    def handler(request):
        raise httpx.ConnectError("[Errno -2] Name or service not known")

    async def _collect():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            async for _ in local_stream([], client=http):
                pass

    with pytest.raises(AIProviderError) as exc_info:
        asyncio.run(_collect())
    assert exc_info.value.provider == "local"
    assert "llama-server" in str(exc_info.value)


def test_local_stream_force_recipe_injects_hint_in_system():
    body = _llama_body(
        _llama_content(f"Claro, aquí está:\n```json\n{RECIPE_JSON}\n```"),
        _llama_stop("stop"),
    )
    seen: list[dict] = []

    def handler(request):
        payload = json.loads(request.content)
        seen.append(payload)
        return httpx.Response(200, content=body)

    async def _collect():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return [e async for e in local_stream([], client=http, force_recipe=True)]

    events = asyncio.run(_collect())
    system = seen[0]["messages"][0]
    assert system["role"] == "system"
    assert FORCE_RECIPE_HINT in system["content"]
    assert events[-1].kind == "text"
    assert "```json" in events[-1].data


def test_local_stream_without_force_recipe_omits_hint():
    body = _llama_body(_llama_content("Hola"), _llama_stop("stop"))
    seen: list[dict] = []

    def handler(request):
        payload = json.loads(request.content)
        seen.append(payload)
        return httpx.Response(200, content=body)

    async def _collect():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as http:
            return [e async for e in local_stream([], client=http)]

    asyncio.run(_collect())
    assert FORCE_RECIPE_HINT not in seen[0]["messages"][0]["content"]


# ---------------------------------------------------------------------------
# oci_stream unit tests
# ---------------------------------------------------------------------------


def test_oci_stream_missing_compartment_raises_ai_provider_error(monkeypatch):
    from app.agent import llm as llm_mod

    monkeypatch.setattr(llm_mod.settings, "oci_compartment_id", None)

    async def _run():
        events = oci_stream([])
        await events.__anext__()

    with pytest.raises(AIProviderError) as exc_info:
        asyncio.run(_run())
    assert exc_info.value.provider == "oci"
    assert "OCI_COMPARTMENT_ID" in str(exc_info.value)


# ---------------------------------------------------------------------------
# stream_chat & Hybrid AI Fallback tests (Task 3)
# ---------------------------------------------------------------------------


def test_stream_chat_local_provider(monkeypatch):
    from app.agent import agent as agent_mod

    async def fake_local_stream(messages, force_recipe=False):
        yield TurnEvent("token", "Hola local!")
        yield TurnEvent("text", "Hola local!")

    monkeypatch.setattr(agent_mod, "local_stream", fake_local_stream)
    monkeypatch.setattr(agent_mod.settings, "llm_provider", "local")

    async def _collect():
        return [e async for e in stream_chat([ChatMessage(role="user", content="hola")])]

    events = asyncio.run(_collect())
    events_seen = [e.event for e in events]
    assert events_seen == ["provider_info", "token", "done"]

    provider_info = next(e for e in events if e.event == "provider_info")
    assert provider_info.data == {"provider": "local", "fallback": False}

    tokens = "".join(e.data["delta"] for e in events if e.event == "token")
    assert tokens == "Hola local!"
    assert next(e for e in events if e.event == "done").data["message"] == "Hola local!"


def test_stream_chat_oci_provider_success(monkeypatch):
    from app.agent import agent as agent_mod

    async def fake_oci_stream(messages, force_recipe=False):
        yield TurnEvent("token", "Hola desde OCI!")
        yield TurnEvent("text", "Hola desde OCI!")

    monkeypatch.setattr(agent_mod, "oci_stream", fake_oci_stream)
    monkeypatch.setattr(agent_mod.settings, "llm_provider", "oci")

    async def _collect():
        return [e async for e in stream_chat([ChatMessage(role="user", content="hola")])]

    events = asyncio.run(_collect())
    events_seen = [e.event for e in events]
    assert events_seen == ["provider_info", "token", "done"]

    provider_info = next(e for e in events if e.event == "provider_info")
    assert provider_info.data == {"provider": "oci", "fallback": False}
    tokens = "".join(e.data["delta"] for e in events if e.event == "token")
    assert tokens == "Hola desde OCI!"


def test_stream_chat_fallback_on_oci_error_before_tokens(monkeypatch):
    """Verifica que ante fallo de OCI antes de emitir tokens, conmuta a local_stream."""
    from app.agent import agent as agent_mod

    async def fake_failing_oci_stream(messages, force_recipe=False):
        raise AIProviderError("oci", TimeoutError("OCI timed out"))
        yield  # make it an async generator

    async def fake_local_stream(messages, force_recipe=False):
        yield TurnEvent("token", "Respuesta desde fallback local.")
        yield TurnEvent("text", "Respuesta desde fallback local.")

    monkeypatch.setattr(agent_mod, "oci_stream", fake_failing_oci_stream)
    monkeypatch.setattr(agent_mod, "local_stream", fake_local_stream)
    monkeypatch.setattr(agent_mod.settings, "llm_provider", "oci")
    monkeypatch.setattr(agent_mod.settings, "ai_fallback_enabled", True)
    monkeypatch.setattr(agent_mod.settings, "ai_fallback_provider", "local")

    async def _collect():
        return [e async for e in stream_chat([ChatMessage(role="user", content="hola")])]

    events = asyncio.run(_collect())
    events_seen = [e.event for e in events]
    assert events_seen == ["provider_info", "token", "done"]

    provider_info = next(e for e in events if e.event == "provider_info")
    assert provider_info.data == {"provider": "local", "fallback": True}

    tokens = "".join(e.data["delta"] for e in events if e.event == "token")
    assert tokens == "Respuesta desde fallback local."


def test_stream_chat_no_fallback_after_tokens_emitted(monkeypatch):
    """Verifica que si ya se emitieron tokens, NO se hace fallback y se emite error."""
    from app.agent import agent as agent_mod

    async def fake_oci_stream_mid_failure(messages, force_recipe=False):
        yield TurnEvent("token", "Primer token emitido.")
        raise AIProviderError("oci", RuntimeError("Conexión perdida a mitad del stream"))

    local_called = False

    async def fake_local_stream(messages, force_recipe=False):
        nonlocal local_called
        local_called = True
        yield TurnEvent("token", "No debería ejecutarse")

    monkeypatch.setattr(agent_mod, "oci_stream", fake_oci_stream_mid_failure)
    monkeypatch.setattr(agent_mod, "local_stream", fake_local_stream)
    monkeypatch.setattr(agent_mod.settings, "llm_provider", "oci")
    monkeypatch.setattr(agent_mod.settings, "ai_fallback_enabled", True)

    async def _collect():
        return [e async for e in stream_chat([ChatMessage(role="user", content="hola")])]

    events = asyncio.run(_collect())
    events_seen = [e.event for e in events]
    assert "token" in events_seen
    assert "error" in events_seen
    assert not local_called
    error_event = next(e for e in events if e.event == "error")
    assert "Conexión perdida" in error_event.data["message"]


def test_stream_chat_fallback_disabled(monkeypatch):
    """Verifica que si ai_fallback_enabled es False, no se activa el fallback."""
    from app.agent import agent as agent_mod

    async def fake_failing_oci_stream(messages, force_recipe=False):
        raise AIProviderError("oci", TimeoutError("OCI timeout"))
        yield

    local_called = False

    async def fake_local_stream(messages, force_recipe=False):
        nonlocal local_called
        local_called = True
        yield TurnEvent("token", "Local")

    monkeypatch.setattr(agent_mod, "oci_stream", fake_failing_oci_stream)
    monkeypatch.setattr(agent_mod, "local_stream", fake_local_stream)
    monkeypatch.setattr(agent_mod.settings, "llm_provider", "oci")
    monkeypatch.setattr(agent_mod.settings, "ai_fallback_enabled", False)

    async def _collect():
        return [e async for e in stream_chat([ChatMessage(role="user", content="hola")])]

    events = asyncio.run(_collect())
    assert not local_called
    assert [e.event for e in events] == ["error"]


def test_stream_chat_tool_call_loop_and_recipe(monkeypatch, patched_tools):
    from app.agent import agent as agent_mod

    monkeypatch.setattr(agent_mod, "generate_recipe_image", lambda recipe, recipe_hash: None)

    async def fake_local_stream(messages, force_recipe=False):
        yield TurnEvent("tool_call", {"name": "get_inventario", "args": {}})
        yield TurnEvent("tool_result", {"name": "get_inventario", "result": '{"inventario": []}'})
        yield TurnEvent("token", "Te propongo:")
        yield TurnEvent("token", f"\n```json\n{RECIPE_JSON}\n```")
        yield TurnEvent("text", f"Te propongo:\n```json\n{RECIPE_JSON}\n```")

    monkeypatch.setattr(agent_mod, "local_stream", fake_local_stream)
    monkeypatch.setattr(agent_mod.settings, "llm_provider", "local")

    async def _collect():
        return [e async for e in stream_chat([])]

    events = asyncio.run(_collect())
    events_seen = [e.event for e in events]
    assert events_seen == [
        "provider_info",
        "tool_call",
        "tool_result",
        "token",
        "token",
        "recipe",
        "recipe_image",
        "done",
    ]

    recipe = next(e for e in events if e.event == "recipe")
    assert recipe.data["nombre"] == "Arroz con tomate"
    assert recipe.data["hash"]

    done = next(e for e in events if e.event == "done")
    assert "Te propongo:" in done.data["message"]
    assert "```json" not in done.data["message"]


def test_agent_executes_descontar_tool_autonomously(engine, patched_tools, monkeypatch):
    from sqlmodel import Session

    from app.agent import agent as agent_mod
    from app.inventory import find_ingredient

    async def fake_local_stream(messages, force_recipe=False):
        args = {"ingredientes": [{"nombre": "tomate", "cantidad": 1}]}
        yield TurnEvent("tool_call", {"name": "descontar_stock", "args": args})
        from app.agent.tools import execute_tool

        result = execute_tool("descontar_stock", args)
        yield TurnEvent("tool_result", {"name": "descontar_stock", "result": result})
        yield TurnEvent("token", "Listo, cocinado!")
        yield TurnEvent("text", "Listo, cocinado!")

    monkeypatch.setattr(agent_mod, "local_stream", fake_local_stream)
    monkeypatch.setattr(agent_mod.settings, "llm_provider", "local")

    async def _collect():
        return [e async for e in stream_chat([])]

    events = asyncio.run(_collect())
    results = [e.data for e in events if e.event == "tool_result"]
    assert results[0]["result"].startswith("{")
    assert '"ok": true' in results[0]["result"]

    with Session(engine) as session:
        assert find_ingredient(session, "tomate").cantidad == 2


# ---------------------------------------------------------------------------
# API endpoint tests (/api/chat)
# ---------------------------------------------------------------------------


def test_chat_endpoint_sse(client, monkeypatch):
    from app.agent import agent as agent_mod

    monkeypatch.setattr(agent_mod, "generate_recipe_image", lambda recipe, recipe_hash: None)

    async def fake_local_stream(messages, force_recipe=False):
        yield TurnEvent("token", "Respuesta endpoint.")
        yield TurnEvent("text", "Respuesta endpoint.")

    monkeypatch.setattr(agent_mod, "local_stream", fake_local_stream)
    monkeypatch.setattr(agent_mod.settings, "llm_provider", "local")

    res = client.post("/api/chat", json={"messages": [{"role": "user", "content": "¿qué cocino?"}]})
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/event-stream")
    assert "event: provider_info" in res.text
    assert "event: token" in res.text
    assert "event: done" in res.text


def test_chat_endpoint_accepts_force_recipe(client, monkeypatch):
    from app.agent import agent as agent_mod

    monkeypatch.setattr(agent_mod, "generate_recipe_image", lambda recipe, recipe_hash: None)

    async def fake_local_stream(messages, force_recipe=False):
        assert force_recipe is True
        yield TurnEvent("token", "Aquí tienes:")
        yield TurnEvent("text", f"Aquí tienes:\n```json\n{RECIPE_JSON}\n```")

    monkeypatch.setattr(agent_mod, "local_stream", fake_local_stream)
    monkeypatch.setattr(agent_mod.settings, "llm_provider", "local")

    res = client.post("/api/chat", json={"messages": [], "force_recipe": True})
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/event-stream")
    assert "event: recipe" in res.text
