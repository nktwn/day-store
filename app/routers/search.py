from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List
from app.core.http_client import java_client

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
    try:
        items = await java_client.get_products()
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Java products failed: {e}")

    tokens = [t.strip().lower() for t in q.split()] if q else []
    out = []
    for it in items:
        if category and it.get("category") != category:
            continue
        price = it.get("price") or 0
        if price_from is not None and price < price_from:
            continue
        if price_to is not None and price > price_to:
            continue
        if tokens:
            hay = " ".join([str(it.get("brand") or ""), str(it.get("model") or "")])
            if not _match_tokens(hay, tokens):
                continue
        out.append(it)
        if len(out) >= limit:
            break

    return {"count": len(out), "items": out}
