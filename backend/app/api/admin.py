from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import require_admin
from app.models.models import Restaurant, MenuItem, Deal, User, Review
from app.schemas.schemas import DealCreate, MenuItemCreate, MenuItemOut, DealOut, UserOut

router = APIRouter(prefix="/api/admin", tags=["管理后台"])

# ── 仪表盘统计 ──
@router.get("/stats", summary="仪表盘统计")
def dashboard_stats(db: Session = Depends(get_db), _admin = Depends(require_admin)):
    return {
        "total_restaurants": db.query(Restaurant).filter(Restaurant.is_active == True).count(),
        "total_users": db.query(User).count(),
        "total_reviews": db.query(Review).count(),
        "featured_count": db.query(Restaurant).filter(Restaurant.is_featured == True, Restaurant.is_active == True).count(),
    }

# ── 菜单管理 ──
@router.post("/menu-items", response_model=MenuItemOut, summary="新增菜品")
def create_menu_item(data: MenuItemCreate, db: Session = Depends(get_db), _admin = Depends(require_admin)):
    item = MenuItem(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item

@router.delete("/menu-items/{id}", summary="删除菜品")
def delete_menu_item(id: int, db: Session = Depends(get_db), _admin = Depends(require_admin)):
    item = db.query(MenuItem).filter(MenuItem.id == id).first()
    if not item:
        raise HTTPException(404, "菜品不存在")
    db.delete(item)
    db.commit()
    return {"ok": True}

# ── 优惠管理 ──
@router.post("/deals", response_model=DealOut, summary="新增优惠活动")
def create_deal(data: DealCreate, db: Session = Depends(get_db), _admin = Depends(require_admin)):
    deal = Deal(**data.model_dump())
    db.add(deal)
    db.commit()
    db.refresh(deal)
    return deal

@router.delete("/deals/{id}", summary="删除优惠")
def delete_deal(id: int, db: Session = Depends(get_db), _admin = Depends(require_admin)):
    deal = db.query(Deal).filter(Deal.id == id).first()
    if not deal:
        raise HTTPException(404, "优惠不存在")
    db.delete(deal)
    db.commit()
    return {"ok": True}

# ── 用户管理 ──
@router.get("/users", response_model=list[UserOut], summary="用户列表")
def list_users(db: Session = Depends(get_db), _admin = Depends(require_admin)):
    return db.query(User).order_by(User.created_at.desc()).limit(100).all()

@router.put("/users/{id}/toggle", summary="启用/禁用用户")
def toggle_user(id: int, db: Session = Depends(get_db), _admin = Depends(require_admin)):
    user = db.query(User).filter(User.id == id).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    user.is_active = not user.is_active
    db.commit()
    return {"is_active": user.is_active}

# ── 评价管理 ──
@router.delete("/reviews/{id}", summary="删除评价")
def admin_delete_review(id: int, db: Session = Depends(get_db), _admin = Depends(require_admin)):
    review = db.query(Review).filter(Review.id == id).first()
    if not review:
        raise HTTPException(404, "评价不存在")
    db.delete(review)
    db.commit()
    return {"ok": True}
