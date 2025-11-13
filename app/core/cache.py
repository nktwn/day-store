import time
import asyncio
from typing import Any, Callable, Dict, Tuple

class TTLCache:
    def __init__(self, ttl_seconds: int = 60):
        self.ttl = ttl_seconds
        self._data: Dict[str, Tuple[float, Any]] = {}
        self._lock = asyncio.Lock()

    async def get_or_set(self, key: str, producer: Callable[[], Any]):
        now = time.time()
        async with self._lock:
            if key in self._data:
                ts, val = self._data[key]
                if now - ts < self.ttl:
                    return val
            val = await producer()
            self._data[key] = (now, val)
            return val

    async def invalidate(self, key: str | None = None):
        async with self._lock:
            if key is None:
                self._data.clear()
            else:
                self._data.pop(key, None)
