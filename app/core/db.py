from motor.motor_asyncio import AsyncIOMotorClient
from .config import settings

client = AsyncIOMotorClient(settings.mongo_uri)
db = client[settings.mongo_db]

users_coll = db["users"]
products_coll = db["products"]
actions_coll = db["user_actions"]
