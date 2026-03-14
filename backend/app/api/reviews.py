from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Review, Restaurant
from app.schemas.schemas import ReviewCreate, ReviewOut

router = APIRouter(prefix="/api/reviews", tags=["评价"])

@router.get("", response_model=list[ReviewOut], summary="获取餐厅评价列表")
def list_reviews(
    restaurant_id: int = Query(...),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    reviews = db.query(Review).options(joinedload(Review.user))\
        .filter(Review.restaurant_id == restaurant_id)\
        .order_by(Review.created_at.desc())\
        .offset((page - 1) * page_size).limit(page_size).all()
    return reviews

@router.post("", response_model=ReviewOut, summary="发布评价")
def create_review(
    data: ReviewCreate,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    # 检查餐厅存在
    restaurant = db.query(Restaurant).filter(Restaurant.id == data.restaurant_id).first()
    if not restaurant:
        raise HTTPException(404, "餐厅不存在")

    # 检查是否已评价
    existing = db.query(Review).filter(
        Review.user_id == current_user.id,
        Review.restaurant_id == data.restaurant_id,
    ).first()
    if existing:
        raise HTTPException(400, "您已经评价过该餐厅")

    review = Review(
        restaurant_id=data.restaurant_id,
        user_id=current_user.id,
        rating=data.rating,
        content=data.content or "",
        is_anonymous=data.is_anonymous or False,
    )
    db.add(review)

    # 更新餐厅平均评分
    all_reviews = db.query(Review).filter(Review.restaurant_id == data.restaurant_id).all()
    total = sum(r.rating for r in all_reviews) + data.rating
    count = len(all_reviews) + 1
    restaurant.avg_rating = round(total / count, 1)
    restaurant.review_count = count

    db.commit()
    db.refresh(review)
    return db.query(Review).options(joinedload(Review.user)).filter(Review.id == review.id).first()

@router.delete("/{id}", summary="删除评价")
def delete_review(id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    review = db.query(Review).filter(Review.id == id).first()
    if not review:
        raise HTTPException(404, "评价不存在")
    if review.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(403, "无权删除")
    db.delete(review)
    db.commit()
    return {"ok": True}
