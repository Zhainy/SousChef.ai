import json

from google.genai import types

from app.agent.agent import stream_chat
from app.agent.tools import descontar_stock_tool, get_inventario


def _chunk(*parts) -> types.GenerateContentResponse:
    return types.GenerateContentResponse(
        candidates=[types.Candidate(content=types.Content(role="model", parts=list(parts)))]
    )


def _text_chunk(text: str) -> types.GenerateContentResponse:
    return _chunk(types.Part.from_text(text=text))


def _fc_chunk(name: str, args: dict) -> types.GenerateContentResponse:
    return _chunk(types.Part.from_function_call(name=name, args=args))


RECIPE_JSON = (
    '{"nombre": "Arroz con tomate", "resumen": "rápido", "tiempo_minutos": 20, '
    '"ingredientes": [{"nombre": "tomate", "cantidad": 1}, {"nombre": "arroz", "cantidad": 200}], '
    '"instrucciones": "1. Cocinar."}'
)


class FakeGen:
    def __init__(self, chunks):
        self._chunks = list(chunks)
        self._i = 0

    def __aiter__(self):
        return self

    async def __anext__(self):
        if self._i >= len(self._chunks):
            raise StopAsyncIteration
        chunk = self._chunks[self._i]
        self._i += 1
        return chunk


class FakeModels:
    def __init__(self, turns):
        self._turns = list(turns)

    async def generate_content_stream(self, *, model, contents, config):
        if not self._turns:
            raise AssertionError("no more turns expected")
        return self._turns.pop(0)


class _Aio:
    def __init__(self, turns):
        self.models = FakeModels(turns)


class FakeClient:
    def __init__(self, turns):
        self.aio = _Aio(turns)


def test_simple_text_streams_tokens():
    import asyncio

    async def _collect():
        return [
            e
            async for e in stream_chat(
                [], client=FakeClient([FakeGen([_text_chunk("Hola "), _text_chunk("chef!")])])
            )
        ]

    events = asyncio.run(_collect())
    events_seen = [e.event for e in events]
    assert events_seen == ["token", "token", "done"]
    assert "".join(e.data["delta"] for e in events if e.event == "token") == "Hola chef!"
    assert next(e for e in events if e.event == "done").data["message"] == "Hola chef!"


def test_tool_call_loop_and_recipe(monkeypatch):
    import asyncio

    from app.agent import agent as agent_mod

    monkeypatch.setattr(agent_mod, "generate_recipe_image", lambda recipe, recipe_hash: None)

    turns = [
        FakeGen([_fc_chunk("get_inventario", {})]),
        FakeGen(
            [
                _text_chunk("Te propongo: "),
                _text_chunk(f"\n```json\n{RECIPE_JSON}\n```"),
            ]
        ),
    ]

    async def _collect():
        return [e async for e in stream_chat([], client=FakeClient(turns))]

    events = asyncio.run(_collect())

    events_seen = [e.event for e in events]
    assert "tool_call" in events_seen
    assert "tool_result" in events_seen
    assert "token" in events_seen
    assert "recipe" in events_seen
    assert "recipe_image" in events_seen
    assert "done" in events_seen

    tool_call = next(e for e in events if e.event == "tool_call")
    assert tool_call.data["name"] == "get_inventario"

    recipe = next(e for e in events if e.event == "recipe")
    assert recipe.data["nombre"] == "Arroz con tomate"
    assert recipe.data["ingredientes"][0]["nombre"] == "tomate"
    assert recipe.data["image_url"] is None
    assert recipe.data["hash"]

    done = next(e for e in events if e.event == "done")
    assert "Te propongo:" in done.data["message"]
    assert "```json" not in done.data["message"]

    joined_tokens = "".join(e.data["delta"] for e in events if e.event == "token")
    assert "Te propongo:" in joined_tokens
    assert "```json" not in joined_tokens


def test_agent_executes_descontar_tool_autonomously(engine, patched_tools):
    import asyncio

    turns = [
        FakeGen(
            [
                _fc_chunk(
                    "descontar_stock",
                    {"ingredientes": [{"nombre": "tomate", "cantidad": 1}]},
                )
            ]
        ),
        FakeGen([_text_chunk("Listo, cocinado!")]),
    ]

    async def _collect():
        return [e async for e in stream_chat([], client=FakeClient(turns))]

    events = asyncio.run(_collect())
    results = [e.data for e in events if e.event == "tool_result"]
    assert results[0]["result"].startswith("{")
    assert '"ok": true' in results[0]["result"]
    from sqlmodel import Session

    from app.inventory import find_ingredient

    with Session(engine) as session:
        assert find_ingredient(session, "tomate").cantidad == 2


def test_get_inventario_tool(patched_tools):
    data = get_inventario()
    names = [i["nombre"] for i in data["inventario"]]
    assert "tomate" in names
    assert all("cantidad" in i for i in data["inventario"])


def test_descontar_tool_reports_faltantes(patched_tools):
    result = descontar_stock_tool(ingredientes=[{"nombre": "tomate", "cantidad": 999}])
    assert result["ok"] is False
    assert result["faltantes"][0]["motivo"] == "stock insuficiente"


def test_preserves_thought_signature_and_function_id(patched_tools):
    import asyncio

    fc_part = types.Part(
        function_call=types.FunctionCall(name="get_inventario", args={}, id="fc-1"),
        thought_signature=b"sig-a",
    )
    second_call_contents: list = []

    class RecordingFakeModels(FakeModels):
        async def generate_content_stream(self, *, model, contents, config):
            if not self._turns:
                raise AssertionError("no more turns expected")
            if second_call_contents is not None:
                second_call_contents.append(list(contents))
            return self._turns.pop(0)

    class RecordingAio:
        def __init__(self, models):
            self.models = models

    class RecordingClient:
        def __init__(self, turns):
            self.aio = RecordingAio(RecordingFakeModels(turns))

    turns = [
        FakeGen([_chunk(fc_part)]),
        FakeGen([_text_chunk("Listo.")]),
    ]

    async def _collect():
        return [e async for e in stream_chat([], client=RecordingClient(turns))]

    asyncio.run(_collect())

    model_content = second_call_contents[1][0]
    assert model_content.role == "model"
    saved = model_content.parts[0]
    assert saved.function_call.id == "fc-1"
    assert saved.thought_signature == b"sig-a"
    same_call = saved.function_call is fc_part.function_call
    assert same_call or saved.function_call == fc_part.function_call

    user_content = second_call_contents[1][1]
    assert user_content.role == "user"
    assert user_content.parts[0].function_response.name == "get_inventario"
    assert user_content.parts[0].function_response.id == "fc-1"


def test_retries_transient_errors_before_content(monkeypatch):
    import asyncio

    monkeypatch.setattr("app.agent.llm.RETRY_DELAY", 0)

    class _Retryable(Exception):
        code = 503

    class FlakyGen:
        def __init__(self):
            self._raised = False
            self._chunks = [_text_chunk("Bien.")]
            self._i = 0

        def __aiter__(self):
            return self

        async def __anext__(self):
            if not self._raised:
                self._raised = True
                raise _Retryable
            if self._i >= len(self._chunks):
                raise StopAsyncIteration
            chunk = self._chunks[self._i]
            self._i += 1
            return chunk

    calls = {"n": 0}

    class CountingModels(FakeModels):
        async def generate_content_stream(self, *, model, contents, config):
            calls["n"] += 1
            if calls["n"] == 1:
                return FlakyGen()
            return self._turns.pop(0)

    class CountingAio:
        def __init__(self, models):
            self.models = models

    class CountingClient:
        def __init__(self, turns):
            self.aio = CountingAio(CountingModels(turns))

    async def _collect():
        return [
            e
            async for e in stream_chat(
                [],
                client=CountingClient([FakeGen([_text_chunk("Bien.")])]),
            )
        ]

    events = asyncio.run(_collect())
    assert calls["n"] == 2
    assert [e.event for e in events] == ["token", "done"]


def test_chat_endpoint_sse(client, monkeypatch):
    from app.agent import agent as agent_mod
    from app.agent import llm as llm_mod

    monkeypatch.setattr(agent_mod, "generate_recipe_image", lambda recipe, recipe_hash: None)

    fake = FakeClient(
        [
            FakeGen([_fc_chunk("get_inventario", {})]),
            FakeGen([_text_chunk(f"Receta lista.\n```json\n{RECIPE_JSON}\n```")]),
        ]
    )
    monkeypatch.setattr(llm_mod.genai, "Client", lambda *a, **k: fake)
    monkeypatch.setattr(llm_mod.settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(llm_mod.settings, "llm_provider", "gemini")
    res = client.post("/api/chat", json={"messages": [{"role": "user", "content": "¿qué cocino?"}]})
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/event-stream")
    assert "event: token" in res.text
    assert "event: tool_call" in res.text
    assert "event: recipe" in res.text
    assert "event: done" in res.text


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


def test_local_stream_text_only():
    import asyncio

    import httpx

    from app.agent.llm import local_stream

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
    import asyncio

    import httpx

    from app.agent.llm import local_stream

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


def test_stream_chat_local_provider(monkeypatch, patched_tools):
    import asyncio

    from app.agent import agent as agent_mod
    from app.agent.llm import TurnEvent
    from app.schemas import ChatMessage

    async def fake_local_stream(messages, force_recipe=False):
        yield TurnEvent("token", "Hola local!")
        yield TurnEvent("text", "Hola local!")

    monkeypatch.setattr(agent_mod, "local_stream", fake_local_stream)
    monkeypatch.setattr(agent_mod.settings, "llm_provider", "local")

    async def _collect():
        return [e async for e in stream_chat([ChatMessage(role="user", content="hola")])]

    events = asyncio.run(_collect())
    assert [e.event for e in events] == ["token", "done"]
    assert "".join(e.data["delta"] for e in events if e.event == "token") == "Hola local!"
    assert next(e for e in events if e.event == "done").data["message"] == "Hola local!"


def test_local_stream_force_recipe_injects_hint_in_system():
    import asyncio

    import httpx

    from app.agent.llm import FORCE_RECIPE_HINT, local_stream

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
    import asyncio

    import httpx

    from app.agent.llm import FORCE_RECIPE_HINT, local_stream

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


class _RecordingClient:
    """Gemini fake que captura los configs de cada llamada al modelo."""

    def __init__(self, turns):
        self.configs = []

        class _Models(FakeModels):
            def __init__(self, turns, configs):
                super().__init__(turns)
                self._configs = configs

            async def generate_content_stream(self, *, model, contents, config):
                self._configs.append(config)
                return await super().generate_content_stream(
                    model=model, contents=contents, config=config
                )

        class _Aio:
            def __init__(self, models):
                self.models = models

        self.aio = _Aio(_Models(turns, self.configs))


def test_gemini_force_recipe_injects_hint_and_emits_recipe(monkeypatch):
    import asyncio

    from app.agent import agent as agent_mod
    from app.agent.llm import FORCE_RECIPE_HINT

    monkeypatch.setattr(agent_mod, "generate_recipe_image", lambda recipe, recipe_hash: None)

    client = _RecordingClient(
        [FakeGen([_text_chunk(f"Aquí tienes.\n```json\n{RECIPE_JSON}\n```")])]
    )

    async def _collect():
        return [e async for e in stream_chat([], client=client, force_recipe=True)]

    events = asyncio.run(_collect())
    assert FORCE_RECIPE_HINT in client.configs[0].system_instruction
    recipe = next(e for e in events if e.event == "recipe")
    assert recipe.data["nombre"] == "Arroz con tomate"


def test_gemini_without_force_recipe_omits_hint(monkeypatch):
    import asyncio

    from app.agent import agent as agent_mod
    from app.agent.llm import FORCE_RECIPE_HINT

    monkeypatch.setattr(agent_mod, "generate_recipe_image", lambda recipe, recipe_hash: None)

    client = _RecordingClient([FakeGen([_text_chunk("Solo texto.")])])

    async def _collect():
        return [e async for e in stream_chat([], client=client)]

    asyncio.run(_collect())
    assert FORCE_RECIPE_HINT not in client.configs[0].system_instruction


def test_chat_endpoint_accepts_force_recipe(client, monkeypatch):
    from app.agent import agent as agent_mod
    from app.agent import llm as llm_mod

    monkeypatch.setattr(agent_mod, "generate_recipe_image", lambda recipe, recipe_hash: None)

    fake = FakeClient([FakeGen([_text_chunk(f"Receta.\n```json\n{RECIPE_JSON}\n```")])])
    monkeypatch.setattr(llm_mod.genai, "Client", lambda *a, **k: fake)
    monkeypatch.setattr(llm_mod.settings, "gemini_api_key", "test-key")
    monkeypatch.setattr(llm_mod.settings, "llm_provider", "gemini")
    res = client.post("/api/chat", json={"messages": [], "force_recipe": True})
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/event-stream")
    assert "event: recipe" in res.text
