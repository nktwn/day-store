from typing import Optional, List

from fastapi import APIRouter, Query

from app.core.db import products_coll

router = APIRouter(prefix="/api/v1/search", tags=["search"])


def _match_tokens(s: str, tokens: List[str]) -> bool:
    s = (s or "").lower()
    return all(t in s for t in tokens)


@router.get("")
async def search(
    q: str = Query(""),
    category: Optional[str] = None,
    price_from: Optional[int] = None,
    price_to: Optional[int] = None,
    limit: int = Query(50, ge=1, le=200),
):
    docs = await products_coll.find({}).to_list(length=1000)
    tokens = [t.strip().lower() for t in q.split()] if q else []

    out = []
    for d in docs:
        if category and d.get("category") != category:
            continue
        price = d.get("price") or 0
        if price_from is not None and price < price_from:
            continue
        if price_to is not None and price > price_to:
            continue
        if tokens:
            hay = " ".join([str(d.get("brand") or ""), str(d.get("model") or "")])
            if not _match_tokens(hay, tokens):
                continue

        out.append(
            {
                "id": str(d["_id"]),
                "brand": d.get("brand"),
                "model": d.get("model"),
                "price": d.get("price"),
                "category": d.get("category"),
            }
        )
        if len(out) >= limit:
            break

    return {"count": len(out), "items": out}
