# SSE / WebSocket helpers to broadcast world updates
import asyncio
from typing import AsyncGenerator

class ChangeStream:
    _subscribers = []

    @classmethod
    async def subscribe(cls) -> AsyncGenerator[str, None]:
        queue = asyncio.Queue()
        cls._subscribers.append(queue)
        try:
            while True:
                data = await queue.get()
                yield f"data: {data}\n\n"
        except asyncio.CancelledError:
            cls._subscribers.remove(queue)

    @classmethod
    def broadcast(cls, message: str):
        for q in cls._subscribers:
            q.put_nowait(message)
