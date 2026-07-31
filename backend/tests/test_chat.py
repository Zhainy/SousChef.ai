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


def test_tool_call_loop_and_recipe():
    import asyncio

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

    monkeypatch.setattr("app.agent.agent.RETRY_DELAY", 0)

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

    fake = FakeClient(
        [
            FakeGen([_fc_chunk("get_inventario", {})]),
            FakeGen([_text_chunk(f"Receta lista.\n```json\n{RECIPE_JSON}\n```")]),
        ]
    )
    monkeypatch.setattr(agent_mod.genai, "Client", lambda *a, **k: fake)
    monkeypatch.setattr(agent_mod.settings, "gemini_api_key", "test-key")
    res = client.post("/api/chat", json={"messages": [{"role": "user", "content": "¿qué cocino?"}]})
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/event-stream")
    assert "event: token" in res.text
    assert "event: tool_call" in res.text
    assert "event: recipe" in res.text
    assert "event: done" in res.text
