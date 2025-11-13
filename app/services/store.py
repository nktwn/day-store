import asyncio
from typing import Dict, List, Literal, TypedDict
from collections import defaultdict
from datetime import datetime

Action = Literal["VIEW", "LIKE", "PURCHASE"]

class Event(TypedDict):
    user_id: str
    product_id: str
    action: Action
    ts: str

class InMemoryEventStore:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self.events_by_user: Dict[str, List[Event]] = defaultdict(list)
        self.popularity: Dict[str, int] = defaultdict(int)

    def _weight(self, action: Action) -> int:
        if action == "VIEW":
            return 1
        if action == "LIKE":
            return 3
        if action == "PURCHASE":
            return 5
        return 0

    async def ingest(self, evs: List[Event]):
        async with self._lock:
            for e in evs:
                if not e.get("ts"):
                    e["ts"] = datetime.utcnow().isoformat() + "Z"
                self.events_by_user[e["user_id"]].append(e)
                self.popularity[e["product_id"]] += self._weight(e["action"])

    async def user_vector(self, user_id: str) -> Dict[str, int]:
        async with self._lock:
            vec: Dict[str, int] = defaultdict(int)
            for e in self.events_by_user.get(user_id, []):
                vec[e["product_id"]] += self._weight(e["action"])
            return dict(vec)

    async def top_popular(self, k: int = 50) -> List[str]:
        async with self._lock:
            return [pid for pid, _ in sorted(self.popularity.items(), key=lambda x: x[1], reverse=True)[:k]]

store = InMemoryEventStore()
