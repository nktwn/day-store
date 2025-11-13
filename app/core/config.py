from pydantic import BaseModel
import os

class Settings(BaseModel):
    java_base_url: str = os.getenv("JAVA_BASE_URL", "http://localhost:8080")
    java_svc_username: str = os.getenv("JAVA_SVC_USERNAME", "service_bot")
    java_svc_password: str = os.getenv("JAVA_SVC_PASSWORD", "service_bot_secret")

    port: int = int(os.getenv("PORT", "9000"))

    http_connect_timeout: float = float(os.getenv("HTTP_CONNECT_TIMEOUT", "5"))
    http_read_timeout: float = float(os.getenv("HTTP_READ_TIMEOUT", "8"))
    http_write_timeout: float = float(os.getenv("HTTP_WRITE_TIMEOUT", "8"))
    http_pool_timeout: float = float(os.getenv("HTTP_POOL_TIMEOUT", "5"))

settings = Settings()
