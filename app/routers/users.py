from datetime import datetime
from typing import List, Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from bson import ObjectId

from app.core.db import users_coll, actions_coll, products_coll
from app.core.security import hash_password, verify_password, get_current_user
from app.models import (
    UserRegister,
    UserPublic,
    UserInDB,
    UserActionOut,
    ActionEnum,
    ProductOut,
    Category,
)

router = APIRouter(prefix="/api/v1/users", tags=["users"])


@router.post("/registration", response_model=UserPublic)
async def register_user(body: UserRegister):
    """
    Регистрация нового пользователя с проверкой паролей
    """
    # Проверка совпадения паролей
    if body.password != body.passwordConfirmation:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    # Проверка длины пароля
    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    # Проверка длины username
    if len(body.username.strip()) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")

    # Проверка существующего пользователя
    existing = await users_coll.find_one({"username": body.username.strip()})
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Создание нового пользователя с хешированным паролем
    doc = {
        "username": body.username.strip(),
        "password": hash_password(body.password),
        "created_at": datetime.utcnow()
    }

    res = await users_coll.insert_one(doc)

    return UserPublic(id=str(res.inserted_id), username=body.username.strip())


@router.post("/login")
async def login_user(username: str, password: str):
    """
    Проверка учетных данных пользователя
    """
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")

    # Поиск пользователя
    user_doc = await users_coll.find_one({"username": username.strip()})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    # Проверка пароля
    if not verify_password(password, user_doc["password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return {
        "id": str(user_doc["_id"]),
        "username": user_doc["username"],
        "message": "Login successful"
    }


@router.get("/me", response_model=UserPublic)
async def get_me(user: UserInDB = Depends(get_current_user)):
    """
    Получение информации о текущем пользователе
    """
    return UserPublic(id=user.id, username=user.username)


@router.get("/me/username", response_class=PlainTextResponse)
async def get_me_username(user: UserInDB = Depends(get_current_user)):
    """
    Получение username текущего пользователя
    """
    return user.username


@router.post("/me/update/username", response_model=UserPublic)
async def update_username(new_username: str, user: UserInDB = Depends(get_current_user)):
    """
    Обновление username пользователя
    """
    if not new_username.strip():
        raise HTTPException(status_code=400, detail="Username cannot be empty")

    if len(new_username.strip()) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")

    # Проверка, что username не занят другим пользователем
    existing = await users_coll.find_one({"username": new_username.strip()})
    if existing and str(existing["_id"]) != user.id:
        raise HTTPException(status_code=400, detail="Username already exists")

    # Обновление username
    await users_coll.update_one(
        {"_id": ObjectId(user.id)},
        {"$set": {"username": new_username.strip(), "updated_at": datetime.utcnow()}},
    )

    return UserPublic(id=user.id, username=new_username.strip())


@router.get("/me/history", response_model=List[UserActionOut])
async def me_history(
        all: bool = Query(True),
        limit: Optional[int] = Query(None, ge=1, le=500),
        user: UserInDB = Depends(get_current_user),
):
    """
    Получение истории действий пользователя
    """
    q: Dict = {"userId": user.id}
    if not all:
        q["action"] = {"$ne": ActionEnum.VIEW.value}

    cursor = actions_coll.find(q).sort("timestamp", -1)
    if limit:
        cursor = cursor.limit(limit)

    docs = await cursor.to_list(length=limit or 500)
    out: List[UserActionOut] = []
    for d in docs:
        out.append(
            UserActionOut(
                id=str(d.get("_id")),
                userId=d["userId"],
                action=d["action"],
                productId=d.get("productId"),
                category=d.get("category"),
                timestamp=d.get("timestamp", datetime.utcnow()),
            )
        )
    return out


def _weight(action: str) -> int:
    """Вес для разных типов действий"""
    if action == ActionEnum.VIEW.value:
        return 1
    if action == ActionEnum.LIKE.value:
        return 3
    if action == ActionEnum.PURCHASE.value:
        return 5
    return 0


@router.get("/me/recommendation", response_model=List[ProductOut])
async def me_recommendation(
        limit: int = Query(10, ge=1, le=100),
        user: UserInDB = Depends(get_current_user),
):
    """
    Получение персональных рекомендаций на основе истории действий
    """
    acts = await actions_coll.find({"userId": user.id}).to_list(length=1000)
    if not acts:
        return []

    product_scores: Dict[str, float] = {}
    category_scores: Dict[str, float] = {}

    # Подсчет весов для продуктов и категорий
    for a in acts:
        w = _weight(a["action"])
        pid = a.get("productId")
        cat = a.get("category")
        if pid:
            product_scores[pid] = product_scores.get(pid, 0.0) + w
        if cat:
            category_scores[cat] = category_scores.get(cat, 0.0) + w

    all_products = await products_coll.find({}).to_list(length=1000)
    scored: List[tuple] = []

    for p in all_products:
        pid = str(p["_id"])
        base = product_scores.get(pid, 0.0)
        cat = p.get("category")
        # Добавляем вес категории
        base += 0.5 * category_scores.get(cat, 0.0)
        if base <= 0:
            continue
        scored.append((base, p))

    # Сортировка по весу
    scored.sort(key=lambda x: x[0], reverse=True)
    top = [p for _, p in scored[:limit]]

    res: List[ProductOut] = []
    for d in top:
        res.append(
            ProductOut(
                id=str(d["_id"]),
                brand=d.get("brand"),
                model=d.get("model"),
                price=d.get("price"),
                category=d.get("category"),
            )
        )
    return res