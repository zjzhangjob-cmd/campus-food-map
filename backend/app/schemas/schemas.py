from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime

# ── Auth ──
class UserRegister(BaseModel):
    username: str = Field(..., min_length=2, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=6)
    nickname: Optional[str] = ""
    campus: Optional[str] = ""

class UserLogin(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    email: str
    nickname: str
    campus: str
    is_admin: bool
    created_at: datetime
    class Config: from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut

# ── MenuItem ──
class MenuItemOut(BaseModel):
    id: int
    name: str
    description: str
    price: float
    emoji: str
    is_recommended: bool
    monthly_sold: int
    class Config: from_attributes = True

# ── Deal ──
class DealOut(BaseModel):
    id: int
    title: str
    description: str
    original_price: Optional[float]
    deal_price: Optional[float]
    discount_text: str
    class Config: from_attributes = True

# ── Restaurant ──
class RestaurantCreate(BaseModel):
    name: str
    description: Optional[str] = ""
    cuisine: Optional[str] = "其他"
    campus: Optional[str] = "全部"
    address: Optional[str] = ""
    phone: Optional[str] = ""
    open_hours: Optional[str] = ""
    price_min: Optional[int] = 0
    price_max: Optional[int] = 0
    distance_min: Optional[int] = 0
    emoji: Optional[str] = "🍽️"
    tags: Optional[str] = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None

class RestaurantUpdate(RestaurantCreate):
    name: Optional[str] = None
    is_open: Optional[bool] = None
    is_featured: Optional[bool] = None
    is_active: Optional[bool] = None

class RestaurantOut(BaseModel):
    id: int
    name: str
    description: str
    cuisine: str
    campus: str
    address: str
    phone: str
    open_hours: str
    price_min: int
    price_max: int
    distance_min: int
    emoji: str
    tags: str
    is_open: bool
    is_featured: bool
    avg_rating: float
    review_count: int
    latitude: Optional[float]
    longitude: Optional[float]
    menu_items: List[MenuItemOut] = []
    deals: List[DealOut] = []
    class Config: from_attributes = True

class RestaurantList(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[RestaurantOut]

# ── Review ──
class ReviewCreate(BaseModel):
    restaurant_id: int
    rating: float = Field(..., ge=1, le=5)
    content: Optional[str] = ""
    is_anonymous: Optional[bool] = False

class ReviewOut(BaseModel):
    id: int
    restaurant_id: int
    user_id: int
    rating: float
    content: str
    is_anonymous: bool
    created_at: datetime
    user: Optional[UserOut] = None
    class Config: from_attributes = True

# ── AI ──
class AIRecommendRequest(BaseModel):
    message: str
    campus: Optional[str] = ""
    budget: Optional[int] = None

class AIRecommendResponse(BaseModel):
    reply: str
    recommended_ids: List[int] = []

# ── Favorite ──
class FavoriteOut(BaseModel):
    restaurant_id: int
    created_at: datetime
    restaurant: RestaurantOut
    class Config: from_attributes = True

# ── Admin ──
class DealCreate(BaseModel):
    restaurant_id: int
    title: str
    description: Optional[str] = ""
    original_price: Optional[float] = None
    deal_price: Optional[float] = None
    discount_text: Optional[str] = ""

class MenuItemCreate(BaseModel):
    restaurant_id: int
    name: str
    description: Optional[str] = ""
    price: float
    emoji: Optional[str] = "🍽️"
    is_recommended: Optional[bool] = False
