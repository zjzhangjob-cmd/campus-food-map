from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, get_current_user
from app.models.models import User
from app.schemas.schemas import UserRegister, UserLogin, Token, UserOut

router = APIRouter(prefix="/api/auth", tags=["认证"])

@router.post("/register", response_model=Token, summary="用户注册")
def register(data: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(400, "用户名已存在")
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, "邮箱已被注册")

    user = User(
        username=data.username,
        email=data.email,
        hashed_pw=hash_password(data.password),
        nickname=data.nickname or data.username,
        campus=data.campus or "",
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token, user=UserOut.model_validate(user))

@router.post("/login", response_model=Token, summary="用户登录")
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.hashed_pw):
        raise HTTPException(401, "用户名或密码错误")
    if not user.is_active:
        raise HTTPException(403, "账号已被禁用")

    token = create_access_token({"sub": str(user.id)})
    return Token(access_token=token, user=UserOut.model_validate(user))

@router.get("/me", response_model=UserOut, summary="获取当前用户信息")
def me(current_user: User = Depends(get_current_user)):
    return current_user
