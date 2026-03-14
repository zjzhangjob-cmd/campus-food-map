from pydantic_settings import BaseSettings
from typing import List
import os

# 找到项目根目录（.env 所在位置）
def find_project_root():
    # 从 backend/app/core 往上找
    current = os.path.dirname(os.path.abspath(__file__))
    # backend/app/core -> backend/app -> backend -> project_root
    for _ in range(3):
        current = os.path.dirname(current)
    return current

PROJECT_ROOT = find_project_root()

class Settings(BaseSettings):
    APP_NAME: str = "觅食·大学城美食地图"
    DEBUG: bool = True

    # MySQL 连接（pymysql 驱动）
    DATABASE_URL: str = "mysql+pymysql://root:password@localhost:3306/campus_food?charset=utf8mb4"

    SECRET_KEY: str = "change-this-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080  # 7天

    # Anthropic Claude API（AI 推荐）
    ANTHROPIC_API_KEY: str = ""

    # 高德地图 Web 服务 Key（后端地理编码用）
    AMAP_KEY: str = ""

    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000,http://localhost:5500,http://127.0.0.1:5500"

    @property
    def origins(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = os.path.join(PROJECT_ROOT, ".env")
        extra = "ignore"

settings = Settings()
