from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.core.database import Base

class CampusEnum(str, enum.Enum):
    all = "全部"
    ligong = "理工大"
    shifan = "师范大"
    yike = "医科大"
    caijing = "财经大"

class CuisineEnum(str, enum.Enum):
    chinese = "中餐"
    japanese = "日料"
    korean = "韩餐"
    western = "西餐"
    fastfood = "快餐"
    snack = "小吃"
    other = "其他"

# ── 用户 ──
class User(Base):
    __tablename__ = "users"

    id          = Column(Integer, primary_key=True, index=True)
    username    = Column(String(50), unique=True, nullable=False, index=True)
    email       = Column(String(100), unique=True, nullable=False, index=True)
    hashed_pw   = Column(String(255), nullable=False)
    nickname    = Column(String(50), default="")
    campus      = Column(String(20), default="")
    is_admin    = Column(Boolean, default=False)
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())

    reviews     = relationship("Review", back_populates="user")
    favorites   = relationship("Favorite", back_populates="user")

# ── 餐厅 ──
class Restaurant(Base):
    __tablename__ = "restaurants"

    id           = Column(Integer, primary_key=True, index=True)
    name         = Column(String(100), nullable=False, index=True)
    description  = Column(Text, default="")
    cuisine      = Column(String(20), default="其他")
    campus       = Column(String(20), default="全部")    # 最近的校区
    address      = Column(String(200), default="")
    phone        = Column(String(20), default="")
    open_hours   = Column(String(100), default="")       # 例："06:00-22:00"
    price_min    = Column(Integer, default=0)             # 人均最低
    price_max    = Column(Integer, default=0)             # 人均最高
    distance_min = Column(Integer, default=0)             # 距最近校门步行分钟
    emoji        = Column(String(10), default="🍽️")
    tags         = Column(String(200), default="")        # 逗号分隔
    is_open      = Column(Boolean, default=True)
    is_featured  = Column(Boolean, default=False)
    is_active    = Column(Boolean, default=True)
    latitude     = Column(Float, nullable=True)
    longitude    = Column(Float, nullable=True)
    avg_rating   = Column(Float, default=0.0)
    review_count = Column(Integer, default=0)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())
    updated_at   = Column(DateTime(timezone=True), onupdate=func.now())

    reviews      = relationship("Review", back_populates="restaurant")
    menu_items   = relationship("MenuItem", back_populates="restaurant")
    favorites    = relationship("Favorite", back_populates="restaurant")
    deals        = relationship("Deal", back_populates="restaurant")

# ── 菜单 ──
class MenuItem(Base):
    __tablename__ = "menu_items"

    id            = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    name          = Column(String(100), nullable=False)
    description   = Column(String(200), default="")
    price         = Column(Float, nullable=False)
    emoji         = Column(String(10), default="🍽️")
    is_recommended= Column(Boolean, default=False)
    monthly_sold  = Column(Integer, default=0)

    restaurant    = relationship("Restaurant", back_populates="menu_items")

# ── 评价 ──
class Review(Base):
    __tablename__ = "reviews"

    id            = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating        = Column(Float, nullable=False)          # 1-5
    content       = Column(Text, default="")
    images        = Column(String(500), default="")        # 逗号分隔图片URL
    is_anonymous  = Column(Boolean, default=False)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    restaurant    = relationship("Restaurant", back_populates="reviews")
    user          = relationship("User", back_populates="reviews")

# ── 收藏 ──
class Favorite(Base):
    __tablename__ = "favorites"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=False)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    user          = relationship("User", back_populates="favorites")
    restaurant    = relationship("Restaurant", back_populates="favorites")

# ── 学生优惠 ──
class Deal(Base):
    __tablename__ = "deals"

    id            = Column(Integer, primary_key=True, index=True)
    restaurant_id = Column(Integer, ForeignKey("restaurants.id"), nullable=False)
    title         = Column(String(100), nullable=False)
    description   = Column(String(200), default="")
    original_price= Column(Float, nullable=True)
    deal_price    = Column(Float, nullable=True)
    discount_text = Column(String(50), default="")        # "8折" / "买一送一"
    valid_until   = Column(DateTime(timezone=True), nullable=True)
    is_active     = Column(Boolean, default=True)

    restaurant    = relationship("Restaurant", back_populates="deals")
