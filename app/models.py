from datetime import datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, Field


class Category(str, Enum):
    LAPTOP = "LAPTOP"
    PC = "PC"
    HEADPHONE = "HEADPHONE"
    SMART_WATCH = "SMART_WATCH"
    CAMERA = "CAMERA"
    PHONE = "PHONE"


class ActionEnum(str, Enum):
    VIEW = "VIEW"
    LIKE = "LIKE"
    PURCHASE = "PURCHASE"

class UserRegister(BaseModel):
    username: str
    password: str
    passwordConfirmation: str


class UserInDB(BaseModel):
    id: str
    username: str
    password: str


class UserPublic(BaseModel):
    id: str
    username: str


class ProductIn(BaseModel):
    brand: Optional[str] = None
    model: Optional[str] = None
    price: Optional[int] = None
    category: Optional[Category] = None


class ProductOut(ProductIn):
    id: str


class UserActionOut(BaseModel):
    id: Optional[str] = None
    userId: str
    action: ActionEnum
    productId: Optional[str] = None
    category: Optional[Category] = None
    timestamp: datetime = Field(..., alias="timestamp")

class PurchaseOut(BaseModel):
    timestamp: datetime
    product: ProductOut
