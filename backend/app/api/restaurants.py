from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_
from typing import Optional
from app.core.database import get_db
from app.core.security import get_current_user, require_admin, get_current_user_optional
from app.models.models import Restaurant, Favorite
from app.schemas.schemas import RestaurantCreate, RestaurantUpdate, RestaurantOut, RestaurantList

router = APIRouter(prefix="/api/restaurants", tags=["餐厅"])

def _load_restaurant(db, id):
    r = db.query(Restaurant).options(
        joinedload(Restaurant.menu_items),
        joinedload(Restaurant.deals),
    ).filter(Restaurant.id == id, Restaurant.is_active == True).first()
    if not r:
        raise HTTPException(404, "餐厅不存在")
    return r

@router.get("", response_model=RestaurantList, summary="获取餐厅列表")
def list_restaurants(
    q: Optional[str] = Query(None, description="搜索关键词"),
    cuisine: Optional[str] = Query(None, description="菜系"),
    campus: Optional[str] = Query(None, description="校区"),
    price_max: Optional[int] = Query(None, description="人均上限"),
    is_open: Optional[bool] = Query(None, description="仅营业中"),
    tags: Optional[str] = Query(None, description="标签（逗号分隔）"),
    sort: str = Query("recommend", description="排序: recommend|rating|distance|price"),
    page: int = Query(1, ge=1),
    page_size: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
):
    query = db.query(Restaurant).options(
        joinedload(Restaurant.menu_items),
        joinedload(Restaurant.deals),
    ).filter(Restaurant.is_active == True)

    if q:
        query = query.filter(or_(
            Restaurant.name.ilike(f"%{q}%"),
            Restaurant.tags.ilike(f"%{q}%"),
            Restaurant.description.ilike(f"%{q}%"),
        ))
    if cuisine:
        query = query.filter(Restaurant.cuisine == cuisine)
    if campus and campus != "全部":
        query = query.filter(or_(Restaurant.campus == campus, Restaurant.campus == "全部"))
    if price_max:
        query = query.filter(Restaurant.price_min <= price_max)
    if is_open is not None:
        query = query.filter(Restaurant.is_open == is_open)
    if tags:
        for tag in tags.split(","):
            query = query.filter(Restaurant.tags.ilike(f"%{tag.strip()}%"))

    if sort == "rating":
        query = query.order_by(Restaurant.avg_rating.desc())
    elif sort == "distance":
        query = query.order_by(Restaurant.distance_min.asc())
    elif sort == "price":
        query = query.order_by(Restaurant.price_min.asc())
    else:  # recommend
        query = query.order_by(Restaurant.is_featured.desc(), Restaurant.avg_rating.desc())

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return RestaurantList(total=total, page=page, page_size=page_size, items=items)

@router.get("/featured", response_model=list[RestaurantOut], summary="获取精选餐厅")
def featured_restaurants(db: Session = Depends(get_db)):
    return db.query(Restaurant).options(
        joinedload(Restaurant.menu_items),
        joinedload(Restaurant.deals),
    ).filter(Restaurant.is_featured == True, Restaurant.is_active == True)\
     .order_by(Restaurant.avg_rating.desc()).limit(5).all()

@router.get("/ranking", response_model=list[RestaurantOut], summary="口碑榜")
def ranking(db: Session = Depends(get_db)):
    return db.query(Restaurant).options(
        joinedload(Restaurant.menu_items),
        joinedload(Restaurant.deals),
    ).filter(Restaurant.is_active == True)\
     .order_by(Restaurant.avg_rating.desc(), Restaurant.review_count.desc())\
     .limit(10).all()

@router.get("/{id}", response_model=RestaurantOut, summary="餐厅详情")
def get_restaurant(id: int, db: Session = Depends(get_db)):
    return _load_restaurant(db, id)

@router.post("", response_model=RestaurantOut, summary="新增餐厅（管理员）")
def create_restaurant(
    data: RestaurantCreate,
    db: Session = Depends(get_db),
    _admin = Depends(require_admin),
):
    r = Restaurant(**data.model_dump())
    db.add(r)
    db.commit()
    db.refresh(r)
    return _load_restaurant(db, r.id)

@router.put("/{id}", response_model=RestaurantOut, summary="更新餐厅（管理员）")
def update_restaurant(
    id: int,
    data: RestaurantUpdate,
    db: Session = Depends(get_db),
    _admin = Depends(require_admin),
):
    r = db.query(Restaurant).filter(Restaurant.id == id).first()
    if not r:
        raise HTTPException(404, "餐厅不存在")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(r, k, v)
    db.commit()
    return _load_restaurant(db, id)

@router.delete("/{id}", summary="删除餐厅（管理员）")
def delete_restaurant(id: int, db: Session = Depends(get_db), _admin = Depends(require_admin)):
    r = db.query(Restaurant).filter(Restaurant.id == id).first()
    if not r:
        raise HTTPException(404, "餐厅不存在")
    r.is_active = False
    db.commit()
    return {"ok": True}

# ── 收藏 ──
@router.post("/{id}/favorite", summary="收藏/取消收藏")
def toggle_favorite(id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    fav = db.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.restaurant_id == id,
    ).first()
    if fav:
        db.delete(fav)
        db.commit()
        return {"favorited": False}
    else:
        db.add(Favorite(user_id=current_user.id, restaurant_id=id))
        db.commit()
        return {"favorited": True}

@router.get("/{id}/is_favorited", summary="是否已收藏")
def is_favorited(id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user_optional)):
    if not current_user:
        return {"favorited": False}
    fav = db.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.restaurant_id == id,
    ).first()
    return {"favorited": bool(fav)}
