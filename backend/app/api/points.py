"""
积分 API
完整积分体系：获取、消耗、查询、每日限额、等级计算
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import PointsLog, UserPoints, User

router = APIRouter(prefix="/api/points", tags=["积分"])

# ── 积分动作枚举与规则 ────────────────────────────────────────
POINTS_RULES = {
    "review":        {"points": 10, "daily_limit": 50,  "desc": "发布评价"},
    "checkin":       {"points": 5,  "daily_limit": 5,   "desc": "每日签到"},
    "checkin_streak":{"points": 20, "daily_limit": 20,  "desc": "连续签到7天奖励"},
    "liked":         {"points": 2,  "daily_limit": 30,  "desc": "帖子被点赞"},
    "invite":        {"points": 50, "daily_limit": None,"desc": "邀请新用户"},
    "wheel_spin":    {"points": 3,  "daily_limit": 15,  "desc": "使用随机转盘"},
    "battle_win":    {"points": 5,  "daily_limit": 5,   "desc": "完成PK赛"},
    "redeem":        {"points": 0,  "daily_limit": None,"desc": "积分兑换"},  # 消耗，points由调用方指定
}

# ── 等级体系 ─────────────────────────────────────────────────
LEVELS = [
    {"level": 1, "name": "觅食新人",   "min": 0,    "max": 199},
    {"level": 2, "name": "美食探索者", "min": 200,  "max": 999},
    {"level": 3, "name": "美食达人",   "min": 1000, "max": 1999},
    {"level": 4, "name": "美食鉴赏家", "min": 2000, "max": 4999},
    {"level": 5, "name": "大学城食神", "min": 5000, "max": 999999},
]

def calc_level(total_earned: int) -> dict:
    for lv in reversed(LEVELS):
        if total_earned >= lv["min"]:
            next_lv = next((l for l in LEVELS if l["level"] == lv["level"] + 1), None)
            return {
                "level": lv["level"],
                "name": lv["name"],
                "min": lv["min"],
                "max": lv["max"],
                "next_min": next_lv["min"] if next_lv else None,
                "next_name": next_lv["name"] if next_lv else None,
            }
    return {"level": 1, "name": "觅食新人", "min": 0, "max": 199}

def get_or_create_user_points(db: Session, user_id: int) -> UserPoints:
    up = db.query(UserPoints).filter(UserPoints.user_id == user_id).first()
    if not up:
        up = UserPoints(user_id=user_id, total_points=0, total_earned=0, level=1, level_name="觅食新人")
        db.add(up)
        db.flush()
    return up

def get_today_earned(db: Session, user_id: int, action: str) -> int:
    """查询今日该动作已获得积分"""
    today_start = datetime.combine(date.today(), datetime.min.time())
    result = db.query(func.sum(PointsLog.points)).filter(
        PointsLog.user_id == user_id,
        PointsLog.action == action,
        PointsLog.points > 0,
        PointsLog.created_at >= today_start,
    ).scalar()
    return result or 0

# ── Schemas ──────────────────────────────────────────────────
class EarnRequest(BaseModel):
    action: str
    note: Optional[str] = ""

class RedeemRequest(BaseModel):
    points: int
    note: str

class PointsOut(BaseModel):
    total_points: int
    total_earned: int
    level: int
    level_name: str
    next_level_name: Optional[str]
    points_to_next: Optional[int]
    expert_badges: str

class LogOut(BaseModel):
    id: int
    points: int
    action: str
    note: str
    desc: str
    created_at: datetime
    class Config: from_attributes = True

# ── 获取积分信息 ─────────────────────────────────────────────
@router.get("/me", response_model=PointsOut, summary="我的积分概览")
def my_points(db: Session = Depends(get_db), user = Depends(get_current_user)):
    up = get_or_create_user_points(db, user.id)
    lv = calc_level(up.total_earned)
    return PointsOut(
        total_points=up.total_points,
        total_earned=up.total_earned,
        level=up.level,
        level_name=up.level_name,
        next_level_name=lv.get("next_name"),
        points_to_next=(lv["next_min"] - up.total_earned) if lv.get("next_min") else None,
        expert_badges=up.expert_badges or "",
    )

@router.get("/logs", summary="积分明细")
def points_logs(
    page: int = 1, page_size: int = 20,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    logs = db.query(PointsLog).filter(PointsLog.user_id == user.id)\
        .order_by(PointsLog.created_at.desc())\
        .offset((page-1)*page_size).limit(page_size).all()
    total = db.query(PointsLog).filter(PointsLog.user_id == user.id).count()
    return {
        "total": total,
        "items": [{
            "id": l.id,
            "points": l.points,
            "action": l.action,
            "note": l.note,
            "desc": POINTS_RULES.get(l.action, {}).get("desc", l.action),
            "created_at": l.created_at.isoformat(),
        } for l in logs]
    }

@router.get("/today", summary="今日积分情况")
def today_summary(db: Session = Depends(get_db), user = Depends(get_current_user)):
    result = {}
    for action, rule in POINTS_RULES.items():
        earned = get_today_earned(db, user.id, action)
        result[action] = {
            "earned": earned,
            "limit": rule["daily_limit"],
            "remaining": max(0, rule["daily_limit"] - earned) if rule["daily_limit"] else None,
        }
    return result

@router.get("/ranking", summary="积分排行榜")
def ranking(limit: int = 10, db: Session = Depends(get_db)):
    rows = db.query(UserPoints, User).join(User, UserPoints.user_id == User.id)\
        .filter(User.is_active == True)\
        .order_by(UserPoints.total_points.desc())\
        .limit(limit).all()
    return [{"rank": i+1, "user_id": up.user_id, "nickname": u.nickname or u.username,
             "campus": u.campus, "total_points": up.total_points,
             "level_name": up.level_name} for i, (up, u) in enumerate(rows)]

# ── 获取积分 ─────────────────────────────────────────────────
@router.post("/earn", summary="获取积分")
def earn_points(
    data: EarnRequest,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    rule = POINTS_RULES.get(data.action)
    if not rule:
        raise HTTPException(400, f"未知积分动作：{data.action}")
    if rule["points"] <= 0:
        raise HTTPException(400, "该动作不能直接获取积分")

    pts = rule["points"]

    # 检查每日限额
    if rule["daily_limit"]:
        today_earned = get_today_earned(db, user.id, data.action)
        if today_earned >= rule["daily_limit"]:
            return {"ok": False, "message": f"今日「{rule['desc']}」积分已达上限 {rule['daily_limit']} 分", "points": 0}
        # 不超出限额
        pts = min(pts, rule["daily_limit"] - today_earned)

    # 签到特殊逻辑：检查连续签到
    if data.action == "checkin":
        yesterday = datetime.combine(
            date.today().replace(day=date.today().day - 1), datetime.min.time()
        )
        yesterday_end = datetime.combine(date.today(), datetime.min.time())
        has_yesterday = db.query(PointsLog).filter(
            PointsLog.user_id == user.id,
            PointsLog.action == "checkin",
            PointsLog.created_at >= yesterday,
            PointsLog.created_at < yesterday_end,
        ).first()
        # 检查连续天数（简化：看最近7天是否每天签到）
        if has_yesterday:
            streak_days = 1
            for i in range(1, 7):
                d_start = datetime.combine(date.today().replace(day=date.today().day - i), datetime.min.time())
                d_end = datetime.combine(date.today().replace(day=date.today().day - i + 1), datetime.min.time())
                if db.query(PointsLog).filter(
                    PointsLog.user_id == user.id,
                    PointsLog.action == "checkin",
                    PointsLog.created_at >= d_start,
                    PointsLog.created_at < d_end,
                ).first():
                    streak_days += 1
                else:
                    break
            if streak_days >= 7:
                # 发放连签奖励
                streak_pts = POINTS_RULES["checkin_streak"]["points"]
                db.add(PointsLog(user_id=user.id, points=streak_pts, action="checkin_streak", note="连续签到7天"))
                _update_user_points(db, user.id, streak_pts)

    # 记录积分日志
    log = PointsLog(user_id=user.id, points=pts, action=data.action, note=data.note or rule["desc"])
    db.add(log)

    # 更新汇总
    up = _update_user_points(db, user.id, pts)
    db.commit()

    return {
        "ok": True,
        "points": pts,
        "total_points": up.total_points,
        "level_name": up.level_name,
        "message": f"+{pts} 积分 · {rule['desc']}",
    }

# ── 消耗积分 ─────────────────────────────────────────────────
@router.post("/redeem", summary="消耗积分兑换")
def redeem_points(
    data: RedeemRequest,
    db: Session = Depends(get_db),
    user = Depends(get_current_user),
):
    if data.points <= 0:
        raise HTTPException(400, "消耗积分必须大于0")
    up = get_or_create_user_points(db, user.id)
    if up.total_points < data.points:
        raise HTTPException(400, f"积分不足，当前 {up.total_points} 分，需要 {data.points} 分")

    log = PointsLog(user_id=user.id, points=-data.points, action="redeem", note=data.note)
    db.add(log)
    up.total_points -= data.points
    db.commit()

    return {
        "ok": True,
        "points_cost": data.points,
        "total_points": up.total_points,
        "message": f"已消耗 {data.points} 积分 · {data.note}",
    }

# ── 内部：更新积分汇总 ────────────────────────────────────────
def _update_user_points(db: Session, user_id: int, pts: int) -> UserPoints:
    up = get_or_create_user_points(db, user_id)
    up.total_points = max(0, up.total_points + pts)
    if pts > 0:
        up.total_earned += pts
    lv = calc_level(up.total_earned)
    up.level = lv["level"]
    up.level_name = lv["name"]
    return up
