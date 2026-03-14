from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.models import Restaurant
from app.schemas.schemas import AIRecommendRequest, AIRecommendResponse
from app.services.ai_service import get_ai_recommendation

router = APIRouter(prefix="/api/ai", tags=["AI推荐"])

@router.post("/recommend", response_model=AIRecommendResponse, summary="AI智能推荐")
async def ai_recommend(data: AIRecommendRequest, db: Session = Depends(get_db)):
    # 获取餐厅列表作为上下文
    query = db.query(Restaurant).filter(Restaurant.is_active == True)
    if data.campus and data.campus != "全部":
        from sqlalchemy import or_
        query = query.filter(or_(Restaurant.campus == data.campus, Restaurant.campus == "全部"))
    if data.budget:
        query = query.filter(Restaurant.price_min <= data.budget)

    restaurants = query.order_by(Restaurant.avg_rating.desc()).limit(15).all()

    # 构建上下文
    context = "\n".join([
        f"- {r.name}（{r.cuisine}，人均¥{r.price_min}-{r.price_max}，{r.avg_rating}分，步行{r.distance_min}分钟，标签：{r.tags}）"
        for r in restaurants
    ])

    reply, recommended_ids = await get_ai_recommendation(data.message, context)
    return AIRecommendResponse(reply=reply, recommended_ids=recommended_ids)
