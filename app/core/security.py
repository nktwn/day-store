import base64
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from passlib.context import CryptContext
from bson import ObjectId

from .db import users_coll
from app.models import UserInDB
from .config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    if hashed.startswith("$2a$") or hashed.startswith("$2b$") or hashed.startswith("$2y$"):
        return pwd_context.verify(plain, hashed)
    return plain == hashed


async def _find_user_by_username(username: str) -> Optional[UserInDB]:
    doc = await users_coll.find_one({"username": username})
    if not doc:
        return None
    return UserInDB(
        id=str(doc.get("_id")),
        username=doc["username"],
        password=doc["password"],
    )


async def get_current_user(request: Request) -> UserInDB:
    auth = request.headers.get("Authorization")
    if not auth or not auth.startswith("Basic "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Basic"},
        )

    try:
        decoded = base64.b64decode(auth.split(" ", 1)[1]).decode("utf-8")
        username, password = decoded.split(":", 1)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header",
            headers={"WWW-Authenticate": "Basic"},
        )

    user = await _find_user_by_username(username)
    if not user or not verify_password(password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Basic"},
        )

    return user


async def ensure_service_user():
    existing = await users_coll.find_one({"username": settings.svc_username})
    if existing:
        return

    doc = {
        "username": settings.svc_username,
        "password": hash_password(settings.svc_password),
    }
    await users_coll.insert_one(doc)
