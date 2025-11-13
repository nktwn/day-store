# app/core/http_client.py
import base64
import httpx
from .config import settings

def make_basic_auth_header(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return f"Basic {token}"

class JavaClient:

    def __init__(self) -> None:
        self.base_url = settings.java_base_url.rstrip("/")
        self._svc_headers = {
            "Authorization": make_basic_auth_header(settings.java_svc_username, settings.java_svc_password),
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        self._timeout = httpx.Timeout(
            connect=settings.http_connect_timeout,
            read=settings.http_read_timeout,
            write=settings.http_write_timeout,
            pool=settings.http_pool_timeout,
        )
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            headers=self._svc_headers,
            timeout=self._timeout,
        )

    def make_client(self, auth_header: str | None = None, extra_headers: dict | None = None):
        headers = dict(self._svc_headers)
        if auth_header is not None:
            if auth_header == "":
                headers.pop("Authorization", None)
            else:
                headers["Authorization"] = auth_header
        if extra_headers:
            headers.update(extra_headers)
        return httpx.AsyncClient(base_url=self.base_url, headers=headers, timeout=self._timeout)

    async def ensure_service_user(self) -> None:
        body = {
            "username": settings.java_svc_username,
            "password": settings.java_svc_password,
            "passwordConfirmation": settings.java_svc_password,
        }
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=10) as c:
                await c.post("/api/v1/users/registration", json=body)
        except Exception:
            pass

    async def aclose(self):
        await self._client.aclose()

    async def get_products(self):
        resp = await self._client.get("/api/v1/products/")
        resp.raise_for_status()
        return resp.json()

    async def get_product_by_id(self, product_id: str):
        resp = await self._client.get(f"/api/v1/products/{product_id}")
        resp.raise_for_status()
        return resp.json()

    async def like_product(self, product_id: str):
        resp = await self._client.post(f"/api/v1/products/{product_id}/like")
        resp.raise_for_status()
        return resp.text

    async def unlike_product(self, product_id: str):
        resp = await self._client.delete(f"/api/v1/products/{product_id}/like")
        if resp.status_code not in (200, 204):
            resp.raise_for_status()
        return {"status": resp.status_code}

    async def buy_product(self, product_id: str):
        resp = await self._client.post(f"/api/v1/products/{product_id}/buy")
        resp.raise_for_status()
        return resp.text

    async def get_username(self):
        resp = await self._client.get("/api/v1/users/me/username")
        resp.raise_for_status()
        return resp.text.strip('"')

    async def get_categories(self):
        resp = await self._client.get("/api/v1/categories/")
        resp.raise_for_status()
        return resp.text

    async def aclose(self):
        await self._client.aclose()

java_client = JavaClient()
