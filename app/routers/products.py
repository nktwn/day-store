from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from bson import ObjectId
from pydantic import BaseModel

from app.core.db import products_coll, actions_coll
from app.core.security import get_current_user
from app.models import ProductOut, Category, ActionEnum, UserInDB

router = APIRouter(prefix="/api/v1/products", tags=["products"])

class ProductsResponse(BaseModel):
    count: int
    items: List[ProductOut]

async def _find_product_doc(product_id: str):
    doc = await products_coll.find_one({"_id": product_id})
    if doc:
        return doc
    if ObjectId.is_valid(product_id):
        doc = await products_coll.find_one({"_id": ObjectId(product_id)})
    return doc

def _product_out(doc) -> ProductOut:
    return ProductOut(
        id=str(doc["_id"]),
        brand=doc.get("brand"),
        model=doc.get("model"),
        price=doc.get("price"),
        category=doc.get("category"),
    )


@router.get("/", response_model=List[ProductOut])
async def list_products():
    docs = await products_coll.find({}).to_list(length=1000)
    if not docs:
        raise HTTPException(status_code=404, detail="No products found")
    return [_product_out(d) for d in docs]


@router.get("/by-category", response_model=ProductsResponse)
async def products_by_category(
    category: str = Query(..., description="CSV: LAPTOP,PHONE,..."),
):
    cats = [c.strip().upper() for c in category.split(",") if c.strip()]
    q = {"category": {"$in": cats}} if cats else {}
    docs = await products_coll.find(q).to_list(length=1000)
    items = [_product_out(d) for d in docs]
    return ProductsResponse(count=len(items), items=items)


@router.get("/by-brand", response_model=List[ProductOut])
async def products_by_brand(brand: str):
    docs = await products_coll.find({"brand": brand}).to_list(length=1000)
    return [_product_out(d) for d in docs]


@router.get("/by-model", response_model=List[ProductOut])
async def products_by_model(model: str):
    docs = await products_coll.find({"model": model}).to_list(length=1000)
    return [_product_out(d) for d in docs]


@router.get("/by-price", response_model=List[ProductOut])
async def products_by_price(
    min: Optional[int] = Query(None, ge=0),
    max: Optional[int] = Query(None, ge=0),
):
    q = {}
    if min is not None or max is not None:
        q["price"] = {}
        if min is not None:
            q["price"]["$gte"] = min
        if max is not None:
            q["price"]["$lte"] = max
    docs = await products_coll.find(q).to_list(length=1000)
    return [_product_out(d) for d in docs]


@router.get("/{product_id}", response_model=ProductOut)
async def get_product(product_id: str, request: Request):
    doc = await _find_product_doc(product_id)
    if not doc:
        raise HTTPException(status_code=500, detail="Product not found")

    try:
        user: UserInDB = await get_current_user(request)
    except HTTPException:
        user = None

    if user:
        await actions_coll.insert_one(
            {
                "userId": user.id,
                "productId": str(doc["_id"]),
                "category": doc.get("category"),
                "action": ActionEnum.VIEW.value,
                "timestamp": datetime.utcnow(),
            }
        )

    return _product_out(doc)


@router.post("/{product_id}/like")
async def like_product(product_id: str, user: UserInDB = Depends(get_current_user)):
    doc = await _find_product_doc(product_id)
    if not doc:
        raise HTTPException(status_code=500, detail="Product not found")

    exists = await actions_coll.find_one(
        {"userId": user.id, "productId": str(doc["_id"]), "action": ActionEnum.LIKE.value}
    )
    if exists:
        raise HTTPException(status_code=400, detail="Like already exists")

    await actions_coll.insert_one(
        {
            "userId": user.id,
            "productId": str(doc["_id"]),
            "category": doc.get("category"),
            "action": ActionEnum.LIKE.value,
            "timestamp": datetime.utcnow(),
        }
    )
    return {"message": "liked"}


@router.delete("/{product_id}/like")
async def unlike_product(product_id: str, user: UserInDB = Depends(get_current_user)):
    doc = await _find_product_doc(product_id)
    if not doc:
        return {"status": 204}

    await actions_coll.delete_many(
        {
            "userId": user.id,
            "productId": str(doc["_id"]),
            "action": ActionEnum.LIKE.value,
        }
    )
    return {"status": 204}


@router.post("/{product_id}/buy")
async def buy_product(product_id: str, user: UserInDB = Depends(get_current_user)):
    doc = await _find_product_doc(product_id)
    if not doc:
        raise HTTPException(status_code=500, detail="Product not found")

    await actions_coll.insert_one(
        {
            "userId": user.id,
            "productId": str(doc["_id"]),
            "category": doc.get("category"),
            "action": ActionEnum.PURCHASE.value,
            "timestamp": datetime.utcnow(),
        }
    )
    return {"message": "purchased"}
