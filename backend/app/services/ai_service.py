"""
觅食 Agent — 社区美食地图 AI 助手
- 多轮对话（session 管理）
- 基于用户心情/预算/人数/口味/地理位置来匹配餐厅
- 提供情绪价值与社交价值：共情 → 披露 → 兜底
- 支持规则兜底，即使没配置 Anthropic Key 也可用
"""
from __future__ import annotations

import math
import random
import re
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

import requests

from app.core.config import settings

# ============================================================
# System Prompt · 多轮对话
# ============================================================
SYSTEM_PROMPT = """你是「觅食 · 社区生活美食地图」的 AI 推荐助手，名字叫「小觅」。
你的角色：一个懂吃、懂得共情的附近生活向导，说话有趣、像朋友，擅长给用户提供情绪价值、路线判断和场景建议。
用户不只可能是大学生，也可能是附近居民、上班族、游客、家长、情侣、朋友聚餐、临时来办事的人；不要默认称呼用户为学生党。
任务：当用户不知道吃什么时，通过多轮对话了解用户的真实需求。

【对话风格】
- 语气轻松活泼，用 emoji 点缀，像朋友聊天
- 先共情再给出推荐：先回应用户的情绪（压力大、累、开心、纠结），再给餐厅建议
- 一次推荐 2~3 家餐厅，只能推荐「当前可选餐厅」里出现过的餐厅，餐厅名必须和结构化推荐卡片一致，格式如下：
  🎯 **推荐餐厅名** （菜系，人均¥预算，★评分，步行X分钟）
  · 为什么推荐：一句话理由，带情绪价值
  · 必吃：招牌菜
  · 场景标签：适合一个人 / 朋友聚餐 / 约会 / 自习前后 / 赶地铁 / 遛弯

【你需要主动询问的维度】（用户没说时追问）
1. 现在的心情 / 状态（压力大、刚下班、刚考完、想犒劳自己、赶时间）
2. 预算范围
3. 几个人吃（一个人 / 2人约会 / 家庭 / 3-6人聚餐）
4. 口味偏好（辣 / 清淡 / 日料 / 中餐 …）
5. 地点 / 时间要求（附近、立即吃、晚上宵夜）
6. 吃完后的安排（自习/办公、赶地铁、开车停车、遛弯、见朋友、带小孩、想安静或想热闹）

【回复长度】
- 控制在 200 字以内
- 餐厅名用 **餐厅名** 包裹
- 给用户保留选择空间，比如「你更倾向哪种？」

【工具调用】
当用户给你一个地点坐标，或你看到"当前地图位置"时，请优先推荐附近的餐厅，并在推荐文本里写上步行距离和评分。

【记忆与纠错】
- 你会看到「已经学到的用户偏好」，这些偏好优先级高于单次猜测
- 如果用户说“不吃/不要/别推荐/不喜欢”，立刻承认并调整，不要继续推荐相关餐厅或口味
- 如果用户明确喜欢某类店、预算、距离、场景，请在后续推荐里主动沿用
- 推荐完新餐厅后，主动询问是否加入地图或心愿单，以及是否保留上一轮推荐
- 当用户问发散问题（约会、带娃、聚餐、低预算、停车、离地铁近、安静办公、吃完散步、不堵车）时，把餐厅选择和后续行动一起考虑
- 不确定时少编造，多追问一个关键问题
"""

# ============================================================
# 规则库 · 用于无 Claude Key 时的本地 Agent
# ============================================================
MOOD_KEYWORDS = {
    "累|困|加班|疲劳|筋疲": "累了",
    "压力|考试|期末|焦虑|紧张|崩溃": "压力大",
    "开心|高兴|庆祝|约饭|约会": "想庆祝",
    "饿|饿死|很饿": "急需碳水",
    "减脂|健身|减肥|健康|轻食|低卡": "减脂期",
    "无聊|纠结|选择困难|不知道": "纠结中",
    "失眠|睡不着|深夜": "熬夜党",
}

BUDGET_PATTERN = re.compile(r"(¥?\d{2,4}|人均|预算|左右|以内|不超|不超过|\d{2,4}块|\d{2,4}元)")
PEOPLE_PATTERN = re.compile(r"(\d+)\s*(个|人|位|位朋友|朋友|同学)")
LOC_PATTERN = re.compile(r"(附近|周边|走路|步行|距离|靠近|地图|定位|这里)")
NEGATIVE_PATTERN = re.compile(r"(不吃|不要|别|不想|不喜欢|讨厌|避开|换一家|不行|踩雷|难吃|太贵|太远|排队)")
POSITIVE_PATTERN = re.compile(r"(喜欢|爱吃|想吃|以后多推|可以多推荐|不错|好吃|满意)")

SPICY_TAGS = {"川菜", "湘菜", "重庆", "火锅", "辣", "川", "湘"}
LIGHT_TAGS = {"轻食", "沙拉", "健康", "低卡", "日料", "寿司", "粥", "粤菜"}
FAST_TAGS = {"煎饼", "快餐", "盖饭", "米线", "小面", "汉堡", "三明治"}
NIGHT_TAGS = {"烧烤", "宵夜", "小龙虾", "串串", "啤酒", "夜市"}
DATE_TAGS = {"日料", "意面", "法餐", "咖啡", "甜品", "brunch"}
GROUP_TAGS = {"烤肉", "火锅", "寿司", "聚餐", "包房"}

EMOJI_BY_MOOD = {
    "累了": "🛋️",
    "压力大": "🔥",
    "想庆祝": "🎉",
    "急需碳水": "🍜",
    "减脂期": "🥗",
    "纠结中": "🤔",
    "熬夜党": "🌙",
}

WELCOME_GREETINGS = [
    "嗨～欢迎来找「小觅」！今天你是想吃点好的犒劳自己，还是简单快速解决一餐？跟我说说心情和预算，我来给你挑最合适的🍜",
    "你好呀，我是小觅 🤖！不知道吃什么很正常，告诉我：现在是几个人吃、预算大概多少？我立刻给你量身推荐～",
    "嗨嗨！你已经进入「觅食 · 附近生活 AI 模式」✨ 告诉我：想吃辣还是清淡？一个人还是约朋友？我帮你缩小选择范围～",
]

SOCIALLY_CAPABLE_OPENING = [
    "一个人吃也能吃出仪式感",
    "和朋友的好回忆，从一起吃饭开始",
    "约会吃对了，心情直接翻倍",
]


# ============================================================
# Session · 内存中保存会话状态（默认 30 分钟过期）
# ============================================================
@dataclass
class Session:
    session_id: str
    created_at: float
    last_used: float
    history: list[dict] = field(default_factory=list)  # {"role":"user"|"assistant","content":str}
    preferences: dict = field(default_factory=dict)    # mood/budget/people/cuisine/location

    def touch(self):
        self.last_used = time.time()


SESSIONS: dict[str, Session] = {}
SESSION_TTL = 30 * 60  # 30 分钟


def _gc():
    now = time.time()
    expired = [sid for sid, s in SESSIONS.items() if now - s.last_used > SESSION_TTL]
    for sid in expired:
        SESSIONS.pop(sid, None)


def create_session() -> Session:
    _gc()
    sid = uuid.uuid4().hex[:12]
    s = Session(session_id=sid, created_at=time.time(), last_used=time.time())
    SESSIONS[sid] = s
    return s


def get_session(sid: str) -> Session | None:
    _gc()
    return SESSIONS.get(sid)


# ============================================================
# 工具函数
# ============================================================
def _haversine(lat1, lng1, lat2, lng2):
    """粗略计算两点之间的步行距离（米）。"""
    R = 6371000
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def _rest_to_dict(r, location: tuple | None = None) -> dict:
    """把 ORM 对象转成前端可消费的 dict。"""
    data = {
        "id": r.id,
        "name": r.name,
        "emoji": r.emoji or "🍽️",
        "cuisine": r.cuisine or "",
        "price_min": r.price_min or 0,
        "price_max": r.price_max or 0,
        "avg_rating": r.avg_rating or 0,
        "review_count": r.review_count or 0,
        "distance_min": r.distance_min or 99,
        "tags": (r.tags or "").split(",") if r.tags else [],
        "description": r.description or "",
        "latitude": r.latitude,
        "longitude": r.longitude,
        "is_open": bool(getattr(r, "is_open", True)),
        "signature_dish": getattr(r, "signature_dish", ""),
    }
    # 基于坐标算真实距离
    if location and data["latitude"] and data["longitude"]:
        meters = _haversine(location[0], location[1], data["latitude"], data["longitude"])
        data["real_distance_m"] = int(meters)
        data["walk_minutes"] = max(1, int(meters / 80))  # 80m/min
    else:
        data["real_distance_m"] = None
        data["walk_minutes"] = data["distance_min"]
    return data


def _match_tag(rest, tag_set: set) -> bool:
    haystack = " ".join([rest.get("cuisine", "") or ""] + rest.get("tags", [])).lower()
    for t in tag_set:
        if t.lower() in haystack:
            return True
    return False


def _restaurant_text(r: dict) -> str:
    return " ".join([
        str(r.get("name", "")),
        str(r.get("cuisine", "")),
        " ".join(r.get("tags", [])),
        str(r.get("description", "")),
    ]).lower()


def _append_unique(pref: dict, key: str, values: list[str] | set[str]) -> None:
    items = list(pref.get(key, []))
    for value in values:
        if value and value not in items:
            items.append(value)
    if items:
        pref[key] = items


def _parse_feedback(text: str, restaurants: list[dict], recent_ids: list[int] | None = None) -> dict:
    """把用户自然语言反馈转成可复用的会话记忆。"""
    learned: dict[str, Any] = {}
    negative = bool(NEGATIVE_PATTERN.search(text))
    positive = bool(POSITIVE_PATTERN.search(text))

    avoid_cuisines: set[str] = set()
    liked_cuisines: set[str] = set()
    avoid_tags: set[str] = set()
    liked_tags: set[str] = set()

    spicy_words = {"辣", "火锅", "川菜", "湘菜", "重庆"}
    light_words = {"清淡", "轻食", "健康", "减脂", "沙拉", "低卡"}
    fast_words = {"快餐", "盖饭", "煎饼", "汉堡"}
    night_words = {"宵夜", "烧烤", "小龙虾", "串串"}

    if negative:
        if any(k in text for k in spicy_words):
            avoid_cuisines.add("spicy")
            avoid_tags.update(SPICY_TAGS)
        if any(k in text for k in light_words):
            avoid_cuisines.add("light")
            avoid_tags.update(LIGHT_TAGS)
        if any(k in text for k in fast_words):
            avoid_cuisines.add("fast")
            avoid_tags.update(FAST_TAGS)
        if any(k in text for k in night_words):
            avoid_cuisines.add("night")
            avoid_tags.update(NIGHT_TAGS)

    if positive and not negative:
        if any(k in text for k in spicy_words):
            liked_cuisines.add("spicy")
        if any(k in text for k in light_words):
            liked_cuisines.add("light")
        if any(k in text for k in fast_words):
            liked_cuisines.add("fast")
        if any(k in text for k in night_words):
            liked_cuisines.add("night")

    mentioned_ids: list[int] = []
    for r in restaurants:
        name = r.get("name") or ""
        if name and name in text:
            mentioned_ids.append(r["id"])

    if mentioned_ids and negative:
        learned["avoid_restaurant_ids"] = mentioned_ids
    elif mentioned_ids and positive:
        learned["liked_restaurant_ids"] = mentioned_ids
    elif negative and recent_ids and any(k in text for k in ("这家", "这个", "刚才", "上一家", "换一家", "不行")):
        learned["avoid_restaurant_ids"] = [int(x) for x in recent_ids[:3]]

    if avoid_cuisines:
        learned["avoid_cuisines"] = sorted(avoid_cuisines)
    if liked_cuisines:
        learned["liked_cuisines"] = sorted(liked_cuisines)
    if avoid_tags:
        learned["avoid_tags"] = sorted(avoid_tags)
    if liked_tags:
        learned["liked_tags"] = sorted(liked_tags)

    if negative and ("太贵" in text or "便宜" in text or "省钱" in text):
        learned["price_sensitivity"] = "high"
    if negative and ("太远" in text or "不想走" in text or "近一点" in text):
        learned["distance_sensitivity"] = "high"

    return learned


def _merge_session_preferences(current: dict, new_pref: dict, learned: dict) -> None:
    for k, v in new_pref.items():
        if v is not None:
            current[k] = v

    for key in ("avoid_cuisines", "liked_cuisines", "avoid_tags", "liked_tags"):
        _append_unique(current, key, learned.get(key, []))

    for key in ("avoid_restaurant_ids", "liked_restaurant_ids"):
        ids = [int(x) for x in learned.get(key, [])]
        existing = [int(x) for x in current.get(key, [])]
        for item in ids:
            if item not in existing:
                existing.append(item)
        if existing:
            current[key] = existing

    for key in ("price_sensitivity", "distance_sensitivity"):
        if learned.get(key):
            current[key] = learned[key]

    if current.get("cuisine") in current.get("avoid_cuisines", []):
        current.pop("cuisine", None)


def _format_learned_preferences(pref: dict) -> str:
    labels = {
        "spicy": "重口/辣",
        "light": "清淡/轻食",
        "fast": "快餐/赶时间",
        "night": "夜宵",
        "japanese": "日料",
    }
    lines = [
        f"- 心情：{pref.get('mood', '暂不清楚')}",
        f"- 预算：{pref.get('budget', '暂不清楚')}",
        f"- 人数：{pref.get('people', '暂不清楚')}",
        f"- 当前口味：{labels.get(pref.get('cuisine'), pref.get('cuisine', '暂不清楚'))}",
    ]
    if pref.get("liked_cuisines"):
        lines.append("- 偏好口味：" + "、".join(labels.get(x, x) for x in pref["liked_cuisines"]))
    if pref.get("avoid_cuisines"):
        lines.append("- 避免口味：" + "、".join(labels.get(x, x) for x in pref["avoid_cuisines"]))
    if pref.get("avoid_tags"):
        lines.append("- 避免标签：" + "、".join(pref["avoid_tags"][:8]))
    if pref.get("liked_restaurant_ids"):
        lines.append("- 喜欢过的餐厅 id：" + "、".join(map(str, pref["liked_restaurant_ids"][-5:])))
    if pref.get("avoid_restaurant_ids"):
        lines.append("- 不再推荐餐厅 id：" + "、".join(map(str, pref["avoid_restaurant_ids"][-8:])))
    if pref.get("price_sensitivity") == "high":
        lines.append("- 对价格敏感：优先性价比，少推贵店")
    if pref.get("distance_sensitivity") == "high":
        lines.append("- 对距离敏感：优先近，少推远")
    return "\n".join(lines)


def _parse_preferences(text: str) -> dict:
    """把用户输入解析为偏好维度：mood/budget/people/cuisine."""
    pref: dict[str, Any] = {}

    # mood
    for keys, label in MOOD_KEYWORDS.items():
        if re.search(keys, text):
            pref["mood"] = label
            break

    # budget
    nums = [int(x) for x in re.findall(r"\d{2,4}", text)]
    if nums:
        pref["budget"] = max(nums)  # 保守取最大作为预算上限

    # people
    m = PEOPLE_PATTERN.search(text)
    if m:
        pref["people"] = int(m.group(1))
    elif "一个人" in text or "一个人吃" in text or "一人食" in text:
        pref["people"] = 1
    elif "聚餐" in text or "一起" in text or "朋友" in text:
        pref["people"] = 4

    # location hint
    if LOC_PATTERN.search(text):
        pref["location_hint"] = True

    # cuisine tag
    no_spicy = any(k in text for k in ("不辣", "不要辣", "不吃辣", "别太辣", "不能吃辣"))
    if not no_spicy and any(k in text for k in ("辣", "火锅", "川菜", "湘菜", "重庆")):
        pref["cuisine"] = "spicy"
    if any(k in text for k in ("轻食", "健康", "减脂", "沙拉", "低卡")):
        pref["cuisine"] = "light"
    if any(k in text for k in ("日料", "寿司", "拉面")):
        pref["cuisine"] = "japanese"
    if any(k in text for k in ("快", "赶时间", "课间", "马上")):
        pref["cuisine"] = "fast"
    if any(k in text for k in ("宵夜", "深夜", "晚上 10", "晚上 11", "凌晨")):
        pref["cuisine"] = "night"

    return pref


def _pick_candidates(restaurants: list[dict], pref: dict, location: tuple | None, limit: int = 5) -> list[dict]:
    """基于偏好打分 + 排序，返回 limit 个候选餐厅。"""
    def score(r: dict) -> tuple:
        s = 0.0
        if r.get("id") in set(pref.get("avoid_restaurant_ids", [])):
            s -= 1000
        if r.get("id") in set(pref.get("liked_restaurant_ids", [])):
            s += 20
        if r.get("id") in set(pref.get("recent_recommendation_ids", [])):
            s -= 12
        text = _restaurant_text(r)
        for tag in pref.get("avoid_tags", []):
            if tag and tag.lower() in text:
                s -= 35
        for tag in pref.get("liked_tags", []):
            if tag and tag.lower() in text:
                s += 8
        # 评分加权
        s += (r.get("avg_rating") or 0) * 4
        # 距离优先（如果有坐标）
        walk = r.get("walk_minutes") or 99
        s += max(0, 30 - walk) * 0.3
        # 预算匹配
        budget = pref.get("budget")
        if budget:
            pm = r.get("price_max") or budget
            pmin = r.get("price_min") or 0
            if pmin <= budget <= (pm + 10):
                s += 20
            elif budget < pmin:
                s -= 18 if pref.get("price_sensitivity") == "high" else 10
        if pref.get("price_sensitivity") == "high":
            s += max(0, 60 - (r.get("price_max") or 60)) * 0.2
        # 人数场景：一个人偏好有"一人食"/"快餐"标签
        people = pref.get("people")
        if people and people <= 1:
            if _match_tag(r, FAST_TAGS):
                s += 6
        if people and people >= 4:
            if _match_tag(r, GROUP_TAGS):
                s += 8
        # 口味
        cuisine = pref.get("cuisine")
        avoid_cuisines = set(pref.get("avoid_cuisines", []))
        liked_cuisines = set(pref.get("liked_cuisines", []))
        if "spicy" in avoid_cuisines and _match_tag(r, SPICY_TAGS):
            s -= 40
        if "light" in avoid_cuisines and _match_tag(r, LIGHT_TAGS):
            s -= 40
        if "fast" in avoid_cuisines and _match_tag(r, FAST_TAGS):
            s -= 25
        if "night" in avoid_cuisines and _match_tag(r, NIGHT_TAGS):
            s -= 25
        if "spicy" in liked_cuisines and _match_tag(r, SPICY_TAGS):
            s += 10
        if "light" in liked_cuisines and _match_tag(r, LIGHT_TAGS):
            s += 10
        if "fast" in liked_cuisines and _match_tag(r, FAST_TAGS):
            s += 8
        if "night" in liked_cuisines and _match_tag(r, NIGHT_TAGS):
            s += 8
        if cuisine == "spicy" and _match_tag(r, SPICY_TAGS):
            s += 15
        if cuisine == "light" and _match_tag(r, LIGHT_TAGS):
            s += 15
        if cuisine == "fast" and _match_tag(r, FAST_TAGS):
            s += 15
        if cuisine == "night" and _match_tag(r, NIGHT_TAGS):
            s += 15
        # 营业状态加分
        if r.get("is_open"):
            s += 5
        # review 数量加权
        s += min(5, math.log1p(r.get("review_count") or 0))
        if pref.get("distance_sensitivity") == "high":
            s -= max(0, walk - 10) * 1.2
        return (-s, walk)

    return sorted(restaurants, key=score)[:limit]


def _scene_reason(r: dict, pref: dict) -> str:
    tags = "、".join((r.get("tags") or [])[:3]) or r.get("cuisine") or "附近好店"
    if pref.get("distance_sensitivity") == "high":
        return "距离优先，少绕路，适合现在就去。"
    if pref.get("price_sensitivity") == "high":
        return "价格更稳，适合想控制预算又不想踩雷。"
    if pref.get("cuisine") == "light" or "light" in set(pref.get("liked_cuisines", [])):
        return "口味更清爽，吃完不容易犯困。"
    if pref.get("people") and pref["people"] >= 4:
        return "适合多人一起点，选择多，分摊下来更舒服。"
    return f"{tags}匹配度高，评分和距离都比较稳。"


def _aligned_recommendation_reply(message: str, picks: list[dict], pref: dict) -> str:
    """用实际返回给前端的 picks 生成回答，避免文字推荐和卡片不一致。"""
    if not picks:
        return "我这轮没有找到足够匹配的餐厅。你可以告诉我预算、口味、距离上限或吃完后的安排，我再重新筛一轮。"

    intro = "我按你这轮需求重新筛了这几家，下面的文字和地图卡片是一一对应的："
    blocks = []
    for r in picks[:3]:
        price = f"¥{r.get('price_min') or 0}-{r.get('price_max') or 0}"
        rating = f"★{round(r.get('avg_rating') or 0, 1)}"
        dist = f"步行{r.get('walk_minutes')}分钟"
        tags = "、".join((r.get("tags") or [])[:3]) or r.get("cuisine") or "附近好店"
        dish = r.get("signature_dish") or "看店内招牌菜"
        blocks.append(
            f"🎯 **{r['name']}**（{tags}，人均{price}，{rating}，{dist}）\n"
            f"· 为什么推荐：{_scene_reason(r, pref)}\n"
            f"· 可以点：{dish}"
        )

    follow = "要不要把这几家加入地图或心愿单？如果你接下来要自习、赶地铁、开车停车、散步或见朋友，我可以继续按下一步安排收窄。"
    return intro + "\n\n" + "\n\n".join(blocks) + "\n\n" + follow


# ============================================================
# 规则 Agent · 纯本地，永远可用
# ============================================================
def _rule_agent(message: str, restaurants: list[dict], pref: dict, location: tuple | None) -> tuple[str, list[dict]]:
    mood = pref.get("mood")
    budget = pref.get("budget")
    people = pref.get("people")
    cuisine = pref.get("cuisine")

    # 共情开头
    opening = ""
    if mood:
        emoji = EMOJI_BY_MOOD.get(mood, "🍜")
        if mood == "累了":
            opening = f"{emoji} 懂，累的时候就想吃点汤汤水水暖一下胃，不用想太多～"
        elif mood == "压力大":
            opening = f"{emoji} 抱抱，压力大的时候必须给味觉一点刺激！辣味是最好的解压良药。"
        elif mood == "想庆祝":
            opening = f"{emoji} 太棒了！值得一顿有氛围的好饭～"
        elif mood == "急需碳水":
            opening = f"{emoji} 饿得发昏？我推荐端上来就能吃、饱腹感最强的几家！"
        elif mood == "减脂期":
            opening = f"{emoji} 保持身材的时候也不能亏待味蕾，轻食也可以很有味道～"
        elif mood == "纠结中":
            opening = f"{emoji} 纠结是正常的！让我帮你缩小范围，先看 3 家再说～"
        elif mood == "熬夜党":
            opening = f"{emoji} 深夜食堂模式开启，我挑几家最适合宵夜的给你～"
    else:
        opening = random.choice(SOCIALLY_CAPABLE_OPENING) + "，我帮你挑几家！"

    candidates = _pick_candidates(restaurants, pref, location, limit=3)
    if not candidates:
        return "目前还没有符合条件的餐厅 😅 先把预算放宽一点，或者换个口味试试？", []

    # 生成推荐文本
    blocks = []
    for i, r in enumerate(candidates, 1):
        name = f"**{r['name']}**"
        price_range = f"¥{r.get('price_min') or 0}-{r.get('price_max') or 0}"
        rating = f"★{round(r.get('avg_rating') or 0, 1)}"
        if r.get("real_distance_m") is not None:
            distance_text = f"步行{r.get('walk_minutes')}分钟"
        else:
            distance_text = f"步行{r.get('walk_minutes')}分钟"
        tags = "、".join(r.get("tags", [])[:3]) or r.get("cuisine") or "宝藏小店"

        # 情绪价值理由
        if mood == "压力大":
            reason = "热辣感直冲天灵盖，吃完把压力一起排掉 💪"
        elif mood == "累了":
            reason = "坐下来 10 分钟就能吃上，吃完回血 80%"
        elif mood == "想庆祝":
            reason = "环境有氛围好拍照，吃完朋友圈发一张直接开炸"
        elif mood == "减脂期":
            reason = "高蛋白高纤维，吃完不犯困还能去自习"
        elif mood == "熬夜党":
            reason = "营业到深夜，越晚越有味道，宵夜氛围感拉满"
        elif people and people >= 4:
            reason = "可以拼好几种菜，每人一道招牌的话吃得超爽"
        elif people and people <= 2:
            reason = "两个人分着吃也很合适，能多点几样"
        else:
            reason = "附近口碑之选，踩雷概率极低"

        social_tag = "一个人" if (people and people == 1) else "朋友聚餐"
        line = (
            f"🎯 {name}（{tags}，人均{price_range}，{rating}，{distance_text}）\n"
            f"  · 为什么推荐：{reason}\n"
            f"  · 场景：{social_tag}"
        )
        blocks.append(line)

    # 追问或收尾
    missing_dims = []
    if not budget:
        missing_dims.append("预算")
    if not people:
        missing_dims.append("人数")
    if not cuisine and not mood:
        missing_dims.append("口味")

    if missing_dims:
        close = f"\n\n对了～你可以再告诉我{'/'.join(missing_dims)}，我可以把推荐再精准缩小～"
    else:
        close = "\n\n想让我在地图上标出它们的位置吗？或者直接帮你选一家也行！"

    reply = opening + "\n\n" + "\n\n".join(blocks) + close
    return reply, candidates


# ============================================================
# Claude Agent · 有 Key 时用
# ============================================================
async def _claude_agent(
    message: str,
    restaurants: list[dict],
    history: list[dict],
    location: tuple | None,
    pref: dict | None = None,
) -> tuple[str, list[dict]]:
    try:
        import anthropic
    except Exception:
        return _rule_agent(message, restaurants, _parse_preferences(message), location)

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

    # 只挑 top5 给 Claude，避免上下文太大
    pref = pref or _parse_preferences(message)
    top = _pick_candidates(restaurants, pref, location, limit=5)
    if top:
        ctx_lines = []
        for r in top:
            price = f"¥{r.get('price_min') or 0}-{r.get('price_max') or 0}"
            rating = f"★{round(r.get('avg_rating') or 0, 1)}"
            dist = f"步行{r.get('walk_minutes')}分钟"
            tags = "、".join(r.get("tags", [])[:3]) or r.get("cuisine") or ""
            ctx_lines.append(f"- {r['name']}（{tags}，人均{price}，{rating}，{dist}，id={r['id']}）")
        restaurants_context = "\n".join(ctx_lines)
    else:
        restaurants_context = "（暂无餐厅数据）"

    user_content = ""
    if location:
        user_content += f"【当前地图位置】纬度{location[0]:.4f}，经度{location[1]:.4f}\n"
    user_content += (
        f"【当前可选餐厅】\n{restaurants_context}\n\n"
        f"【已经学到的用户偏好】\n{_format_learned_preferences(pref)}\n\n"
        f"【用户当前消息】\n{message}"
    )

    # 把历史拼成 messages（Claude 格式）
    messages: list[dict] = []
    for h in history[-6:]:  # 最多带 6 轮
        if h["role"] == "user":
            messages.append({"role": "user", "content": h["content"]})
        else:
            messages.append({"role": "assistant", "content": h["content"]})
    messages.append({"role": "user", "content": user_content})

    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=450,
            system=SYSTEM_PROMPT,
            messages=messages,
        )
        reply = response.content[0].text
    except Exception as e:
        # Claude 失败就退化为规则 Agent
        reply, _ = _rule_agent(message, restaurants, pref, location)
        reply = f"（AI 暂不可用，切换本地推荐👇）\n\n{reply}"

    picks = _pick_candidates(restaurants, pref, location, limit=3)
    reply = _aligned_recommendation_reply(message, picks, pref)
    return reply, picks


# ============================================================
# Seed Agent · 豆包 Seed 模型（火山引擎 ARK，OpenAI 兼容协议）
# ============================================================
async def _seed_agent(
    message: str,
    restaurants: list[dict],
    history: list[dict],
    location: tuple | None,
    pref: dict | None = None,
) -> tuple[str, list[dict]]:
    endpoint = settings.SEED_API_ENDPOINT
    api_key = settings.SEED_API_KEY
    
    if not endpoint or not api_key:
        return _rule_agent(message, restaurants, pref or _parse_preferences(message), location)

    pref = pref or _parse_preferences(message)
    top = _pick_candidates(restaurants, pref, location, limit=5)
    
    if top:
        ctx_lines = []
        for r in top:
            price = f"¥{r.get('price_min') or 0}-{r.get('price_max') or 0}"
            rating = f"★{round(r.get('avg_rating') or 0, 1)}"
            dist = f"步行{r.get('walk_minutes')}分钟"
            tags = "、".join(r.get("tags", [])[:3]) or r.get("cuisine") or ""
            ctx_lines.append(f"- {r['name']}（{tags}，人均{price}，{rating}，{dist}，id={r['id']}）")
        restaurants_context = "\n".join(ctx_lines)
    else:
        restaurants_context = "（暂无餐厅数据）"

    user_content = ""
    if location:
        user_content += f"【当前地图位置】纬度{location[0]:.4f}，经度{location[1]:.4f}\n"
    user_content += (
        f"【当前可选餐厅】\n{restaurants_context}\n\n"
        f"【已经学到的用户偏好】\n{_format_learned_preferences(pref)}\n\n"
        f"【用户当前消息】\n{message}"
    )

    messages: list[dict] = []
    for h in history[-6:]:
        if h["role"] == "user":
            messages.append({"role": "user", "content": h["content"]})
        else:
            messages.append({"role": "assistant", "content": h["content"]})
    messages.append({"role": "user", "content": user_content})

    try:
        base_url = "https://ark.cn-beijing.volces.com/api/v3"
        response = requests.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": endpoint,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    *messages
                ],
                "max_tokens": 450,
                "temperature": 0.6
            },
            timeout=18
        )
        
        if response.status_code == 200:
            data = response.json()
            reply = data["choices"][0]["message"]["content"]
        else:
            raise Exception(f"Seed API returned {response.status_code}: {response.text}")
    
    except Exception as e:
        reply, _ = _rule_agent(message, restaurants, pref, location)
        reply = f"（AI 暂不可用，切换本地推荐👇）\n\n{reply}"

    picks = _pick_candidates(restaurants, pref, location, limit=3)
    reply = _aligned_recommendation_reply(message, picks, pref)
    return reply, picks


# ============================================================
# 对外 API 适配
# ============================================================
async def get_ai_recommendation(message: str, restaurants_context: str = "", campus: str | None = None) -> tuple[str, list[int]]:
    """
    兼容旧接口：单次推荐。
    新代码请使用 chat_session()。
    """
    # 旧接口拿不到真实的餐厅 ORM，只能走规则 + 上下文文本
    if settings.ANTHROPIC_API_KEY:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            user_content = f"{restaurants_context}\n\n用户需求：{message}" if restaurants_context else message
            response = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=300,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_content}],
            )
            return response.content[0].text, []
        except Exception:
            pass
    return _rule_agent(message, [], _parse_preferences(message), None)[0], []


async def chat_session(
    session_id: str | None,
    message: str,
    restaurants_orm: list,
    campus: str | None = None,
    location: tuple | None = None,
) -> dict:
    """
    多轮对话主入口。
    返回：{session_id, reply, recommendations:[...], preferences:{...}}
    """
    session = get_session(session_id) if session_id else None
    if session is None:
        session = create_session()

    session.touch()

    # 把 ORM 列表转成 dict，并计算与坐标的真实距离
    restaurants = [_rest_to_dict(r, location) for r in restaurants_orm]

    # 解析偏好和纠错反馈，并合并进 session
    new_pref = _parse_preferences(message)
    learned = _parse_feedback(message, restaurants, session.preferences.get("recent_recommendation_ids", []))
    _merge_session_preferences(session.preferences, new_pref, learned)
    if location:
        session.preferences["location"] = list(location)

    # 选择 Agent 实现（优先级：Seed > Claude > 规则）
    has_seed = bool(settings.SEED_API_ENDPOINT) and bool(settings.SEED_API_KEY)
    has_claude = bool(settings.ANTHROPIC_API_KEY)
    
    if has_seed:
        reply, recs = await _seed_agent(
            message, restaurants, session.history, location, session.preferences
        )
    elif has_claude:
        reply, recs = await _claude_agent(
            message, restaurants, session.history, location, session.preferences
        )
    else:
        reply, recs = _rule_agent(message, restaurants, session.preferences, location)

    session.preferences["recent_recommendation_ids"] = [int(r["id"]) for r in recs[:5] if r.get("id")]

    # 写回 history
    session.history.append({"role": "user", "content": message})
    session.history.append({"role": "assistant", "content": reply})

    return {
        "session_id": session.session_id,
        "reply": reply,
        "recommendations": recs,
        "preferences": session.preferences,
    }


async def reset_session(session_id: str | None) -> dict:
    """重置会话。"""
    if session_id and session_id in SESSIONS:
        SESSIONS.pop(session_id, None)
    new_session = create_session()
    return {"session_id": new_session.session_id, "reply": random.choice(WELCOME_GREETINGS), "recommendations": []}


def welcome_message() -> str:
    return random.choice(WELCOME_GREETINGS)
