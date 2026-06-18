from pydantic_settings import BaseSettings
from typing import List
import os

_ENV_PATH = os.path.join(os.path.dirname(__file__), "../../../.env")

class Settings(BaseSettings):
    APP_NAME: str = "觅食·大学城美食地图"
    DEBUG: bool = True

    DATABASE_URL: str = "sqlite:///./campus_food.db"

    SECRET_KEY: str = "campus-food-map-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080

    ANTHROPIC_API_KEY: str = ""
    AMAP_KEY: str = ""
    AMAP_JS_KEY: str = ""

    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5500,http://127.0.0.1:5500"

    @property
    def origins(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = _ENV_PATH
        extra = "ignore"

settings = Settings()
