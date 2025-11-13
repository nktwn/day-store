from pydantic import BaseModel
import os
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseModel):
    port: int = int(os.getenv("PORT", "8080"))

    mongo_uri: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    mongo_db: str = os.getenv("MONGO_DB", "daystore")

    svc_username: str = os.getenv("SVC_USERNAME", "service_bot")
    svc_password: str = os.getenv("SVC_PASSWORD", "service_bot_secret")


settings = Settings()
