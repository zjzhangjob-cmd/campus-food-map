from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import Base, engine
from app.api import auth, restaurants, reviews, ai, admin

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description="大学城美食地图 · 完整前后端 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 路由注册
app.include_router(auth.router)
app.include_router(restaurants.router)
app.include_router(reviews.router)
app.include_router(ai.router)
app.include_router(admin.router)

@app.get("/", tags=["健康检查"])
def root():
    return {"status": "ok", "app": settings.APP_NAME, "docs": "/docs"}

@app.get("/health", tags=["健康检查"])
def health():
    return {"status": "healthy"}
