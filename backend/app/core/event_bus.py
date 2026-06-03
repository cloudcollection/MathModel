from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from collections import defaultdict
from collections.abc import AsyncIterator

from app.config.settings import get_settings
from app.models.message import WSMessage

logger = logging.getLogger(__name__)


class EventBus:
    """Task-scoped event history and pub/sub with Redis fallback support."""

    def __init__(self) -> None:
        self._history: dict[str, list[WSMessage]] = defaultdict(list)
        self._subscribers: dict[str, set[asyncio.Queue[WSMessage]]] = defaultdict(set)
        self._redis: object | None = None
        self._redis_failed = False

    async def _get_redis(self):
        settings = get_settings()
        if not settings.redis_url or self._redis_failed:
            return None
        if self._redis is not None:
            return self._redis

        try:
            from redis.asyncio import Redis

            redis = Redis.from_url(settings.redis_url, decode_responses=True)
            await redis.ping()
            self._redis = redis
            return redis
        except Exception as exc:  # pragma: no cover - depends on environment
            self._redis_failed = True
            logger.warning("Redis is unavailable, using in-memory event bus: %s", exc)
            return None

    async def publish_event(self, task_id: str, message: WSMessage) -> None:
        """Append a message to history and publish it to live subscribers."""

        self._history[task_id].append(message)
        for queue in list(self._subscribers.get(task_id, set())):
            queue.put_nowait(message)

        redis = await self._get_redis()
        if redis is not None:
            payload = message.model_dump_json()
            await redis.rpush(f"task:{task_id}:history", payload)
            await redis.publish(f"task:{task_id}:events", payload)

    async def get_history(self, task_id: str) -> list[WSMessage]:
        """Return event history for a task."""

        redis = await self._get_redis()
        if redis is not None:
            rows = await redis.lrange(f"task:{task_id}:history", 0, -1)
            return [WSMessage.model_validate_json(row) for row in rows]
        return list(self._history.get(task_id, []))

    async def subscribe(self, task_id: str) -> AsyncIterator[WSMessage]:
        """Subscribe to future task events."""

        redis = await self._get_redis()
        if redis is not None:
            async for message in self._subscribe_redis(redis, task_id):
                yield message
            return

        queue: asyncio.Queue[WSMessage] = asyncio.Queue()
        self._subscribers[task_id].add(queue)
        try:
            while True:
                yield await queue.get()
        finally:
            self._subscribers[task_id].discard(queue)

    async def _subscribe_redis(self, redis, task_id: str) -> AsyncIterator[WSMessage]:
        channel = f"task:{task_id}:events"
        pubsub = redis.pubsub()
        await pubsub.subscribe(channel)
        try:
            async for raw in pubsub.listen():
                if raw.get("type") != "message":
                    continue
                data = raw.get("data")
                if isinstance(data, bytes):
                    data = data.decode("utf-8")
                yield WSMessage.model_validate(json.loads(data))
        finally:
            with contextlib.suppress(Exception):
                await pubsub.unsubscribe(channel)
                await pubsub.close()


event_bus = EventBus()


async def publish_event(task_id: str, message: WSMessage) -> None:
    """Public helper used by agents and routes."""

    await event_bus.publish_event(task_id, message)

