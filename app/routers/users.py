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
    PurchaseOut,
    UserPasswordUpdate,
    AdminPasswordUpdate,
)


router = APIRouter(prefix="/api/v1/users", tags=["users"])

def _is_admin(user: UserInDB) -> bool:
    return user.username == "admin"


@router.post("/registration", response_model=UserPublic)
async def register_user(body: UserRegister):

    if body.password != body.passwordConfirmation:
        raise HTTPException(status_code=400, detail="Passwords do not match")

    if len(body.password) < 6:
        raise HTTPException(status_code=400, detail="Password must be at least 6 characters")

    if len(body.username.strip()) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")

    existing = await users_coll.find_one({"username": body.username.strip()})
    if existing:
        raise HTTPException(status_code=400, detail="Username already exists")

    doc = {
        "username": body.username.strip(),
        "password": hash_password(body.password),
        "created_at": datetime.utcnow()
    }

    res = await users_coll.insert_one(doc)

    return UserPublic(id=str(res.inserted_id), username=body.username.strip())


@router.post("/login")
async def login_user(username: str, password: str):
    if not username or not password:
        raise HTTPException(status_code=400, detail="Username and password required")

    user_doc = await users_coll.find_one({"username": username.strip()})
    if not user_doc:
        raise HTTPException(status_code=401, detail="Invalid username or password")

    if not verify_password(password, user_doc["password"]):
        raise HTTPException(status_code=401, detail="Invalid username or password")

    return {
        "id": str(user_doc["_id"]),
        "username": user_doc["username"],
        "message": "Login successful"
    }


@router.get("/me", response_model=UserPublic)
async def get_me(user: UserInDB = Depends(get_current_user)):
    return UserPublic(id=user.id, username=user.username)


@router.get("/me/username", response_class=PlainTextResponse)
async def get_me_username(user: UserInDB = Depends(get_current_user)):

    return user.username


@router.post("/me/update/username", response_model=UserPublic)
async def update_username(new_username: str, user: UserInDB = Depends(get_current_user)):
    if not new_username.strip():
        raise HTTPException(status_code=400, detail="Username cannot be empty")

    if len(new_username.strip()) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")

    existing = await users_coll.find_one({"username": new_username.strip()})
    if existing and str(existing["_id"]) != user.id:
        raise HTTPException(status_code=400, detail="Username already exists")

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

    acts = await actions_coll.find({"userId": user.id}).to_list(length=1000)
    if not acts:
        return []

    product_scores: Dict[str, float] = {}
    category_scores: Dict[str, float] = {}

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
        base += 0.5 * category_scores.get(cat, 0.0)
        if base <= 0:
            continue
        scored.append((base, p))

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

@router.get("/me/purchases", response_model=List[PurchaseOut])
async def me_purchases(
        limit: Optional[int] = Query(100, ge=1, le=500),
        user: UserInDB = Depends(get_current_user),
):
    q: Dict = {
        "userId": user.id,
        "action": ActionEnum.PURCHASE.value,
    }

    cursor = actions_coll.find(q).sort("timestamp", -1)
    if limit:
        cursor = cursor.limit(limit)

    acts = await cursor.to_list(length=limit or 500)
    result: List[PurchaseOut] = []

    for a in acts:
        pid = a.get("productId")
        if not pid:
            continue

        doc = await products_coll.find_one({"_id": ObjectId(pid)}) if ObjectId.is_valid(pid) \
            else await products_coll.find_one({"_id": pid})

        if not doc:
            continue

        product = ProductOut(
            id=str(doc["_id"]),
            brand=doc.get("brand"),
            model=doc.get("model"),
            price=doc.get("price"),
            category=doc.get("category"),
        )

        result.append(
            PurchaseOut(
                timestamp=a.get("timestamp", datetime.utcnow()),
                product=product,
            )
        )

    return result

@router.post("/me/update/password")
async def update_password(
    body: UserPasswordUpdate,
    user: UserInDB = Depends(get_current_user),
):
    if not verify_password(body.old_password, user.password):
        raise HTTPException(status_code=400, detail="Текущий пароль указан неверно")

    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="Новый пароль должен быть не менее 6 символов")

    if body.new_password != body.new_password_confirmation:
        raise HTTPException(status_code=400, detail="Повтор нового пароля не совпадает")

    if body.new_password == body.old_password:
        raise HTTPException(status_code=400, detail="Новый пароль не должен совпадать с текущим")

    await users_coll.update_one(
        {"_id": ObjectId(user.id)},
        {
            "$set": {
                "password": hash_password(body.new_password),
                "updated_at": datetime.utcnow(),
            }
        },
    )

    return {"message": "Password updated"}

@router.get("/admin/users", response_model=List[UserPublic])
async def admin_list_users(current: UserInDB = Depends(get_current_user)):
    if not _is_admin(current):
        raise HTTPException(status_code=403, detail="Admin only")

    cursor = users_coll.find({})
    docs = await cursor.to_list(length=1000)

    out: List[UserPublic] = []
    for d in docs:
        username = d.get("username", "")
        if username == "admin":
            continue
        out.append(UserPublic(id=str(d["_id"]), username=username))

    return out

@router.delete("/admin/users/{user_id}")
async def admin_delete_user(user_id: str, current: UserInDB = Depends(get_current_user)):
    if not _is_admin(current):
        raise HTTPException(status_code=403, detail="Admin only")

    doc = await users_coll.find_one({"_id": ObjectId(user_id)}) if ObjectId.is_valid(user_id) \
        else await users_coll.find_one({"_id": user_id})
    if not doc:
        raise HTTPException(status_code=404, detail="User not found")

    if doc.get("username") == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete admin user")

    await users_coll.delete_one({"_id": doc["_id"]})
    await actions_coll.delete_many({"userId": str(doc["_id"])})

    return {"status": "deleted"}

@router.post("/admin/users/{user_id}/password")
async def admin_update_user_password(
    user_id: str,
    body: AdminPasswordUpdate,
    current: UserInDB = Depends(get_current_user),
):
    if not _is_admin(current):
        raise HTTPException(status_code=403, detail="Admin only")

    if len(body.new_password) < 6:
        raise HTTPException(status_code=400, detail="Новый пароль должен быть не менее 6 символов")

    if body.new_password != body.new_password_confirmation:
        raise HTTPException(status_code=400, detail="Повтор нового пароля не совпадает")

    doc = await users_coll.find_one({"_id": ObjectId(user_id)}) if ObjectId.is_valid(user_id) \
        else await users_coll.find_one({"_id": user_id})

    if not doc:
        raise HTTPException(status_code=404, detail="User not found")

    if doc.get("username") == "admin":
        raise HTTPException(status_code=400, detail="Cannot change admin password here")

    await users_coll.update_one(
        {"_id": doc["_id"]},
        {
            "$set": {
                "password": hash_password(body.new_password),
                "updated_at": datetime.utcnow(),
            }
        },
    )

    return {"message": "Password updated by admin"}

