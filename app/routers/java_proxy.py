from fastapi import APIRouter, HTTPException, Query, Request
from app.core.http_client import java_client
from app.core.cache import TTLCache

router = APIRouter(prefix="/api/v1/java", tags=["java-proxy"])
_products_cache = TTLCache(ttl_seconds=60)


def _auth_from_request(request: Request) -> str | None:
    return request.headers.get("authorization")


def _extra_headers(request: Request) -> dict:
    x = request.headers.get("x-user") or request.headers.get("x-username")
    return {"X-User": x} if x else {}


def _ensure_auth_or_401(request: Request):
    if not (_auth_from_request(request) or _extra_headers(request)):
        raise HTTPException(status_code=401, detail="Authorization required")


@router.get("/me/username")
async def me_username(request: Request):
    _ensure_auth_or_401(request)
    auth = _auth_from_request(request)
    extra = _extra_headers(request)

    async with java_client.make_client(auth_header=auth, extra_headers=extra) as c:
        resp = await c.get("/api/v1/users/me/username")

    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        resp.raise_for_status()
    except Exception:
        raise HTTPException(status_code=502, detail=f"Java me/username failed: {resp.text}")

    return {"java_username": resp.text.strip().strip('"')}


@router.get("/users/me/history")
async def me_history(request: Request, limit: int | None = None, all: bool | None = True):
    _ensure_auth_or_401(request)
    auth = _auth_from_request(request)
    extra = _extra_headers(request)

    params = {}
    if limit is not None:
        params["limit"] = str(limit)
    if all is not None:
        params["all"] = "true" if all else "false"

    async with java_client.make_client(auth_header=auth, extra_headers=extra) as c:
        resp = await c.get("/api/v1/users/me/history", params=params)

    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        resp.raise_for_status()
    except Exception:
        raise HTTPException(status_code=502, detail=f"Java me/history failed: {resp.text}")

    return resp.json()


@router.get("/users/me/recommendation")
async def me_recommendation(request: Request):
    _ensure_auth_or_401(request)
    auth = _auth_from_request(request)
    extra = _extra_headers(request)

    async with java_client.make_client(auth_header=auth, extra_headers=extra) as c:
        resp = await c.get("/api/v1/users/me/recommendation")

    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        resp.raise_for_status()
    except Exception:
        raise HTTPException(status_code=502, detail=f"Java recommendation failed: {resp.text}")
    return resp.json()


@router.get("/products")
async def list_products(request: Request, use_cache: bool = Query(True)):
    auth = _auth_from_request(request)
    extra = _extra_headers(request)

    async def producer():
        async with java_client.make_client(auth_header=auth, extra_headers=extra) as c:
            resp = await c.get("/api/v1/products/")
        if resp.status_code == 401:
            raise HTTPException(status_code=401, detail="Unauthorized")
        try:
            resp.raise_for_status()
        except Exception:
            raise HTTPException(status_code=502, detail=f"Java products failed: {resp.text}")
        return resp.json()

    data = await (_products_cache.get_or_set("all_products", producer) if use_cache and not auth else producer())
    return {"count": len(data), "items": data}


@router.get("/products/by-category")
async def products_by_category(request: Request, category: str = Query(..., description="CSV: LAPTOP,PHONE,...")):
    auth = _auth_from_request(request)
    extra = _extra_headers(request)

    categories_csv = ",".join([c.strip().upper() for c in category.split(",") if c.strip()])
    params = {"category": categories_csv} if categories_csv else {}

    async with java_client.make_client(auth_header=auth, extra_headers=extra) as c:
        resp = await c.get("/api/v1/products/by-category", params=params)

    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="Unauthorized")
    try:
        resp.raise_for_status()
    except Exception:
        raise HTTPException(status_code=502, detail=f"Java products/by-category failed: {resp.text}")

    data = resp.json()
    return {"count": len(data), "items": data}


@router.get("/products/{product_id}")
async def get_product(request: Request, product_id: str):
    auth = _auth_from_request(request)
    extra = _extra_headers(request)
    async with java_client.make_client(auth_header=auth, extra_headers=extra) as c:
        resp = await c.get(f"/api/v1/products/{product_id}")

    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if resp.status_code == 500:
        raise HTTPException(status_code=404, detail="Product not found")
    try:
        resp.raise_for_status()
    except Exception:
        raise HTTPException(status_code=502, detail=f"Java product {product_id} failed: {resp.text}")
    return resp.json()


@router.post("/products/{product_id}/like")
async def like_product(request: Request, product_id: str):
    _ensure_auth_or_401(request)
    auth = _auth_from_request(request)
    extra = _extra_headers(request)

    async with java_client.make_client(auth_header=auth, extra_headers=extra) as c:
        resp = await c.post(f"/api/v1/products/{product_id}/like")

    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if resp.status_code == 500:
        raise HTTPException(status_code=404, detail="Product not found")
    if resp.status_code not in (200, 204):
        raise HTTPException(status_code=502, detail=f"Java like failed: {resp.text}")

    await _products_cache.invalidate("all_products")
    return {"message": resp.text or "OK"}


@router.delete("/products/{product_id}/like")
async def unlike_product(request: Request, product_id: str):
    _ensure_auth_or_401(request)
    auth = _auth_from_request(request)
    extra = _extra_headers(request)

    async with java_client.make_client(auth_header=auth, extra_headers=extra) as c:
        resp = await c.delete(f"/api/v1/products/{product_id}/like")

    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if resp.status_code == 500:
        return {"status": 204}
    if resp.status_code not in (200, 204):
        raise HTTPException(status_code=502, detail=f"Java unlike failed: {resp.text}")

    await _products_cache.invalidate("all_products")
    return {"status": resp.status_code}


@router.post("/products/{product_id}/buy")
async def buy_product(request: Request, product_id: str):
    _ensure_auth_or_401(request)
    auth = _auth_from_request(request)
    extra = _extra_headers(request)

    async with java_client.make_client(auth_header=auth, extra_headers=extra) as c:
        resp = await c.post(f"/api/v1/products/{product_id}/buy")

    if resp.status_code == 401:
        raise HTTPException(status_code=401, detail="Unauthorized")
    if resp.status_code == 500:
        raise HTTPException(status_code=404, detail="Product not found")
    if resp.status_code not in (200, 204):
        raise HTTPException(status_code=502, detail=f"Java buy failed: {resp.text}")

    return {"message": resp.text or "OK"}

