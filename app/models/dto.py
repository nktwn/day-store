from pydantic import BaseModel

class JavaProduct(BaseModel):
    id: str
    brand: str | None = None
    model: str | None = None
    price: int | None = None
    category: str | None = None
