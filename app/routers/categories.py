from fastapi import APIRouter
from app.models import Category

router = APIRouter(prefix="/api/v1/categories", tags=["categories"])

@router.get("/")
async def list_categories():
    return [c.value for c in Category]
