from fastapi import FastAPI
import uvicorn

from fastapi.middleware.cors import CORSMiddleware
from starlette.staticfiles import StaticFiles

from app.core.config import settings
from app.core.security import ensure_service_user
from app.routers import health, users, products, categories, search


app = FastAPI(
    title="DayStore Backend (FastAPI)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    await ensure_service_user()

app.include_router(health.router)
app.include_router(users.router)
app.include_router(products.router)
app.include_router(categories.router)
app.include_router(search.router)

app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.port, reload=True)
