from collections.abc import AsyncIterable

from fastapi import APIRouter
from fastapi.sse import EventSourceResponse, ServerSentEvent

from ..agent.agent import stream_chat
from ..schemas import ChatRequest

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_class=EventSourceResponse)
async def chat_endpoint(payload: ChatRequest) -> AsyncIterable[ServerSentEvent]:
    async for event in stream_chat(payload.messages, force_recipe=payload.force_recipe):
        yield event
