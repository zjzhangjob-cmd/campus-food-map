from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models.models import Restaurant
from app.schemas.schemas import AIRecommendRequest, AIRecommendResponse
from app.services.ai_service import (
    chat_session,
    get_ai_recommendation,
    reset_session,
    welcome_message,
    create_session as _create_session,
)

router = APIRouter(prefix="/api/ai", tags=["AI推荐"])


# ── API 输入模型 ───────────────────────
class ChatMessageRequest(BaseModel):
    session_id: Optional[str] = None
    message: str = ""
    campus: Optional[str] = None
    location: Optional[List[float]] = None
    agent_mode: Optional[str] = "normal_agent"


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    recommendations: List[dict] = []
    preferences: dict = {}
    mode: str = "rule"
    agent_mode: str = "normal_agent"
    decision: Optional[str] = None
    intent: Optional[str] = None


# ── 1. 创建会话 ───────────────────────
@router.post("/sessions", response_model=ChatResponse)
def create_chat_session():
    s = _create_session()
    return ChatResponse(
        session_id=s.session_id,
        reply=welcome_message(),
        recommendations=[],
        preferences={},
        mode=_agent_mode(),
        agent_mode="normal_agent",
    )


# ── 2. 发送消息（多轮对话） ─────────────
@router.post("/sessions/{session_id}/messages", response_model=ChatResponse)
async def send_chat_message(
    session_id: str,
    body: ChatMessageRequest,
    db: Session = Depends(get_db),
):
    restaurants = _get_restaurants(db, body.campus)
    location = tuple(body.location) if body.location else None
    mode = _agent_mode()

    result = await chat_session(
        session_id=session_id,
        message=body.message,
        restaurants_orm=restaurants,
        campus=body.campus,
        location=location,
        agent_mode=body.agent_mode or "normal_agent",
    )
    return ChatResponse(
        session_id=result["session_id"],
        reply=result["reply"],
        recommendations=result["recommendations"],
        preferences=result.get("preferences", {}),
        mode=mode,
        agent_mode=result.get("agent_mode", body.agent_mode or "normal_agent"),
        decision=result.get("decision"),
        intent=result.get("intent"),
    )


# ── 3. 重置会话 ─────────────────────
@router.delete("/sessions/{session_id}", response_model=ChatResponse)
async def reset_chat_session(session_id: str):
    result = await reset_session(session_id)
    return ChatResponse(
        session_id=result["session_id"],
        reply=result["reply"],
        recommendations=[],
        preferences={},
        mode=_agent_mode(),
        agent_mode="normal_agent",
    )


# ── 4. 快捷：无需先创建会话，直接发消息 ────
@router.post("/messages", response_model=ChatResponse)
async def quick_chat(body: ChatMessageRequest, db: Session = Depends(get_db)):
    restaurants = _get_restaurants(db, body.campus)
    location = tuple(body.location) if body.location else None
    mode = _agent_mode()

    result = await chat_session(
        session_id=body.session_id,
        message=body.message,
        restaurants_orm=restaurants,
        campus=body.campus,
        location=location,
        agent_mode=body.agent_mode or "normal_agent",
    )
    return ChatResponse(
        session_id=result["session_id"],
        reply=result["reply"],
        recommendations=result["recommendations"],
        preferences=result.get("preferences", {}),
        mode=mode,
        agent_mode=result.get("agent_mode", body.agent_mode or "normal_agent"),
        decision=result.get("decision"),
        intent=result.get("intent"),
    )


# ── 5. 保留原接口（兼容旧前端） ───────────
@router.post("/recommend", response_model=AIRecommendResponse)
async def ai_recommend(data: AIRecommendRequest, db: Session = Depends(get_db)):
    query = db.query(Restaurant).filter(Restaurant.is_active == True)
    if data.campus and data.campus != "全部":
        districts = {"黄浦区", "徐汇区", "长宁区", "静安区", "普陀区", "虹口区", "杨浦区", "浦东新区", "闵行区", "宝山区"}
        if data.campus in districts:
            query = query.filter(Restaurant.address.ilike(f"%{data.campus}%"))
        else:
            query = query.filter(or_(Restaurant.campus == data.campus, Restaurant.campus == "全部"))

    restaurants = query.order_by(Restaurant.avg_rating.desc()).limit(15).all()
    context = "\n".join([
        f"- {r.name}（{r.cuisine}，人均¥{r.price_min}-{r.price_max}，{r.avg_rating}分，步行{r.distance_min}分钟，标签：{r.tags}）"
        for r in restaurants
    ])

    reply, recommended_ids = await get_ai_recommendation(data.message, context)
    return AIRecommendResponse(reply=reply, recommended_ids=recommended_ids)


# ── 辅助 ───────────────────
def _get_restaurants(db: Session, campus: str | None) -> list:
    q = db.query(Restaurant).filter(Restaurant.is_active == True)
    if campus and campus != "全部":
        districts = {"黄浦区", "徐汇区", "长宁区", "静安区", "普陀区", "虹口区", "杨浦区", "浦东新区", "闵行区", "宝山区"}
        if campus in districts:
            q = q.filter(Restaurant.address.ilike(f"%{campus}%"))
        else:
            q = q.filter(or_(Restaurant.campus == campus, Restaurant.campus == "全部"))
    return q.order_by(Restaurant.avg_rating.desc()).limit(30).all()


def _agent_mode() -> str:
    if settings.SEED_API_ENDPOINT and settings.SEED_API_KEY:
        return "seed"
    if settings.ANTHROPIC_API_KEY:
        return "claude"
    return "rule"
