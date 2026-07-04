"""
Batch evaluator for 小觅 Agent training cases.

This is a local smoke-test runner. It does not call external LLM APIs.
It checks:
- The 5000-case dataset shape and distribution.
- Whether the current deterministic/rule path can process every case.
- Basic response guarantees needed by the product flow.

Usage:
    cd backend
    python app/services/agent_training_eval.py
    python app/services/agent_training_eval.py --json
"""
from __future__ import annotations

import argparse
import asyncio
import json
import random
import sys
import warnings
from collections import Counter, defaultdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parents[2]))

warnings.filterwarnings("ignore", message="urllib3 v2 only supports OpenSSL.*")

from app.services.agent_failure_replay_cases import FAILURE_REPLAY_CASES
from app.services.agent_training_cases import TRAINING_CASES
from app.services.ai_service import (
    COOL_FORBIDDEN_TAGS,
    COOL_TAGS,
    HOTPOT_TAGS,
    SWEET_FORBIDDEN_MAIN_TAGS,
    SWEET_PRIMARY_TAGS,
    SWEET_TAGS,
    WESTERN_TAGS,
    _is_sweet_candidate,
    _aligned_recommendation_reply,
    _merge_session_preferences,
    _parse_feedback,
    _parse_preferences,
    _rule_agent,
    chat_session,
)


SAMPLE_RESTAURANTS: list[dict[str, Any]] = [
    {
        "id": 1,
        "name": "绿野轻食碗",
        "emoji": "🥗",
        "cuisine": "轻食",
        "price_min": 24,
        "price_max": 36,
        "avg_rating": 4.7,
        "review_count": 860,
        "distance_min": 7,
        "tags": ["轻食", "低卡", "清淡", "午餐", "可外带"],
        "description": "清爽轻食，适合控卡和午餐。",
        "latitude": 31.2309,
        "longitude": 121.4742,
        "is_open": True,
        "signature_dish": "鸡胸藜麦碗",
        "walk_minutes": 7,
        "real_distance_m": 560,
    },
    {
        "id": 2,
        "name": "重庆秀山小面",
        "emoji": "🍜",
        "cuisine": "中餐",
        "price_min": 12,
        "price_max": 22,
        "avg_rating": 4.9,
        "review_count": 5621,
        "distance_min": 5,
        "tags": ["小面", "重庆", "麻辣", "早餐", "便宜"],
        "description": "麻辣小面，出餐快。",
        "latitude": 31.2312,
        "longitude": 121.4750,
        "is_open": True,
        "signature_dish": "牛肉小面",
        "walk_minutes": 5,
        "real_distance_m": 420,
    },
    {
        "id": 3,
        "name": "豆舍咖啡",
        "emoji": "☕",
        "cuisine": "西餐",
        "price_min": 28,
        "price_max": 48,
        "avg_rating": 4.8,
        "review_count": 1340,
        "distance_min": 8,
        "tags": ["咖啡", "办公", "安静", "插座", "轻食"],
        "description": "适合下午办公，座位相对稳定。",
        "latitude": 31.2298,
        "longitude": 121.4728,
        "is_open": True,
        "signature_dish": "燕麦拿铁",
        "walk_minutes": 8,
        "real_distance_m": 650,
    },
    {
        "id": 20,
        "name": "蓝门意面小馆",
        "emoji": "🍝",
        "cuisine": "西餐",
        "price_min": 48,
        "price_max": 88,
        "avg_rating": 4.8,
        "review_count": 1260,
        "distance_min": 8,
        "tags": ["西餐", "意面", "披萨", "简餐", "可坐"],
        "description": "意面和披萨为主，适合想吃西式简餐。",
        "latitude": 31.2301,
        "longitude": 121.4760,
        "is_open": True,
        "signature_dish": "番茄肉酱意面",
        "walk_minutes": 8,
        "real_distance_m": 620,
    },
    {
        "id": 21,
        "name": "街角牛排汉堡",
        "emoji": "🍔",
        "cuisine": "西餐",
        "price_min": 55,
        "price_max": 108,
        "avg_rating": 4.7,
        "review_count": 980,
        "distance_min": 10,
        "tags": ["西餐", "牛排", "汉堡", "美式", "brunch"],
        "description": "牛排、汉堡和brunch，适合西餐正餐。",
        "latitude": 31.2320,
        "longitude": 121.4782,
        "is_open": True,
        "signature_dish": "芝士牛肉汉堡",
        "walk_minutes": 10,
        "real_distance_m": 820,
    },
    {
        "id": 22,
        "name": "韩屋部队锅",
        "emoji": "🍲",
        "cuisine": "韩餐",
        "price_min": 48,
        "price_max": 92,
        "avg_rating": 4.7,
        "review_count": 1180,
        "distance_min": 9,
        "tags": ["韩餐", "韩国料理", "部队锅", "石锅拌饭", "韩式"],
        "description": "部队锅、拌饭和韩式小菜，适合想吃韩餐。",
        "latitude": 31.2331,
        "longitude": 121.4770,
        "is_open": True,
        "signature_dish": "芝士部队锅",
        "walk_minutes": 9,
        "real_distance_m": 740,
    },
    {
        "id": 23,
        "name": "泰兰亭",
        "emoji": "🍛",
        "cuisine": "泰餐",
        "price_min": 58,
        "price_max": 118,
        "avg_rating": 4.6,
        "review_count": 860,
        "distance_min": 12,
        "tags": ["泰餐", "泰国菜", "冬阴功", "咖喱", "泰式"],
        "description": "冬阴功、咖喱和菠萝炒饭，酸辣开胃。",
        "latitude": 31.2340,
        "longitude": 121.4790,
        "is_open": True,
        "signature_dish": "冬阴功汤",
        "walk_minutes": 12,
        "real_distance_m": 960,
    },
    {
        "id": 24,
        "name": "天山大盘鸡",
        "emoji": "🍗",
        "cuisine": "新疆菜",
        "price_min": 42,
        "price_max": 86,
        "avg_rating": 4.7,
        "review_count": 980,
        "distance_min": 10,
        "tags": ["新疆菜", "大盘鸡", "手抓饭", "烤包子", "羊肉串"],
        "description": "大盘鸡和手抓饭分量足，适合多人吃。",
        "latitude": 31.2289,
        "longitude": 121.4775,
        "is_open": True,
        "signature_dish": "大盘鸡",
        "walk_minutes": 10,
        "real_distance_m": 830,
    },
    {
        "id": 25,
        "name": "东北菜馆分店",
        "emoji": "🥟",
        "cuisine": "东北菜",
        "price_min": 35,
        "price_max": 72,
        "avg_rating": 4.6,
        "review_count": 1320,
        "distance_min": 11,
        "tags": ["东北菜", "锅包肉", "铁锅炖", "饺子", "量大"],
        "description": "锅包肉和铁锅炖分量足，适合聚餐。",
        "latitude": 31.2269,
        "longitude": 121.4748,
        "is_open": True,
        "signature_dish": "锅包肉",
        "walk_minutes": 11,
        "real_distance_m": 900,
    },
    {
        "id": 26,
        "name": "夜火烧烤",
        "emoji": "🍢",
        "cuisine": "烧烤",
        "price_min": 45,
        "price_max": 95,
        "avg_rating": 4.5,
        "review_count": 1500,
        "distance_min": 13,
        "tags": ["烧烤", "烤串", "烤肉", "羊肉串", "夜宵"],
        "description": "烤串和夜宵氛围，适合朋友聚餐。",
        "latitude": 31.2260,
        "longitude": 121.4808,
        "is_open": True,
        "signature_dish": "羊肉串",
        "walk_minutes": 13,
        "real_distance_m": 1050,
    },
    {
        "id": 4,
        "name": "阿婆本帮小馆",
        "emoji": "🥢",
        "cuisine": "中餐",
        "price_min": 42,
        "price_max": 78,
        "avg_rating": 4.6,
        "review_count": 2100,
        "distance_min": 10,
        "tags": ["本帮菜", "上海菜", "家庭聚餐", "长辈友好"],
        "description": "本帮家常菜，适合带家人。",
        "latitude": 31.2288,
        "longitude": 121.4715,
        "is_open": True,
        "signature_dish": "响油鳝丝",
        "walk_minutes": 10,
        "real_distance_m": 780,
    },
    {
        "id": 5,
        "name": "静安素食社",
        "emoji": "🥬",
        "cuisine": "素食",
        "price_min": 32,
        "price_max": 58,
        "avg_rating": 4.5,
        "review_count": 720,
        "distance_min": 9,
        "tags": ["素食", "清淡", "健康", "不辣"],
        "description": "素食但味型丰富。",
        "latitude": 31.2295,
        "longitude": 121.4602,
        "is_open": True,
        "signature_dish": "菌菇拌饭",
        "walk_minutes": 9,
        "real_distance_m": 720,
    },
    {
        "id": 6,
        "name": "浦东港式茶餐厅",
        "emoji": "🧋",
        "cuisine": "中餐",
        "price_min": 25,
        "price_max": 45,
        "avg_rating": 4.6,
        "review_count": 1900,
        "distance_min": 6,
        "tags": ["港式", "云吞面", "热汤", "宵夜", "外卖"],
        "description": "热汤和云吞面稳定，外卖友好。",
        "latitude": 31.2217,
        "longitude": 121.5445,
        "is_open": True,
        "signature_dish": "鲜虾云吞面",
        "walk_minutes": 6,
        "real_distance_m": 480,
    },
    {
        "id": 7,
        "name": "徐汇商场亲子餐厅",
        "emoji": "🍽️",
        "cuisine": "中餐",
        "price_min": 55,
        "price_max": 95,
        "avg_rating": 4.4,
        "review_count": 920,
        "distance_min": 11,
        "tags": ["亲子", "商场", "儿童友好", "不辣", "停车"],
        "description": "商场内，带娃和停车都方便。",
        "latitude": 31.1940,
        "longitude": 121.4372,
        "is_open": True,
        "signature_dish": "儿童套餐",
        "walk_minutes": 11,
        "real_distance_m": 850,
    },
    {
        "id": 8,
        "name": "川渝冒菜馆",
        "emoji": "🫕",
        "cuisine": "中餐",
        "price_min": 28,
        "price_max": 52,
        "avg_rating": 4.7,
        "review_count": 1680,
        "distance_min": 9,
        "tags": ["川菜", "麻辣", "冒菜", "聚餐", "夜宵"],
        "description": "重口味冒菜，适合想吃辣。",
        "latitude": 31.2919,
        "longitude": 121.5074,
        "is_open": True,
        "signature_dish": "毛肚冒菜",
        "walk_minutes": 9,
        "real_distance_m": 700,
    },
    {
        "id": 9,
        "name": "一人食饭团铺",
        "emoji": "🍙",
        "cuisine": "快餐",
        "price_min": 12,
        "price_max": 24,
        "avg_rating": 4.4,
        "review_count": 540,
        "distance_min": 4,
        "tags": ["快餐", "一人食", "早餐", "可带走", "便宜"],
        "description": "适合赶时间和打包。",
        "latitude": 31.2310,
        "longitude": 121.4730,
        "is_open": True,
        "signature_dish": "金枪鱼饭团",
        "walk_minutes": 4,
        "real_distance_m": 320,
    },
    {
        "id": 10,
        "name": "虹口汤面馆",
        "emoji": "🍲",
        "cuisine": "中餐",
        "price_min": 18,
        "price_max": 35,
        "avg_rating": 4.5,
        "review_count": 780,
        "distance_min": 7,
        "tags": ["热汤", "面馆", "清淡", "快餐", "宵夜"],
        "description": "热汤面，油度较低。",
        "latitude": 31.2648,
        "longitude": 121.5054,
        "is_open": True,
        "signature_dish": "鸡汤面",
        "walk_minutes": 7,
        "real_distance_m": 560,
    },
    {
        "id": 19,
        "name": "夏日凉面轻食",
        "emoji": "🥗",
        "cuisine": "轻食",
        "price_min": 18,
        "price_max": 32,
        "avg_rating": 4.7,
        "review_count": 680,
        "distance_min": 6,
        "tags": ["凉面", "冷食", "沙拉", "清爽", "可外带"],
        "description": "凉面和清爽沙拉，适合想吃不热不腻的一餐。",
        "latitude": 31.2302,
        "longitude": 121.4732,
        "is_open": True,
        "signature_dish": "鸡丝凉面",
        "walk_minutes": 6,
        "real_distance_m": 460,
    },
    {
        "id": 11,
        "name": "奈雪の茶",
        "emoji": "🧋",
        "cuisine": "甜品饮品",
        "price_min": 16,
        "price_max": 32,
        "avg_rating": 4.8,
        "review_count": 2860,
        "distance_min": 6,
        "tags": ["奶茶", "饮品", "甜品", "下午茶", "可坐"],
        "description": "奶茶和软欧包，适合下午茶和短暂停留。",
        "latitude": 31.2306,
        "longitude": 121.4736,
        "is_open": True,
        "signature_dish": "霸气芝士草莓",
        "walk_minutes": 6,
        "real_distance_m": 460,
    },
    {
        "id": 12,
        "name": "静安糖水铺",
        "emoji": "🍮",
        "cuisine": "甜品",
        "price_min": 18,
        "price_max": 30,
        "avg_rating": 4.7,
        "review_count": 1180,
        "distance_min": 8,
        "tags": ["糖水", "甜品", "冰品", "饭后甜点", "不辣"],
        "description": "糖水和小甜品，适合饭后轻量甜口。",
        "latitude": 31.2291,
        "longitude": 121.4599,
        "is_open": True,
        "signature_dish": "杨枝甘露",
        "walk_minutes": 8,
        "real_distance_m": 620,
    },
    {
        "id": 13,
        "name": "贝果蛋糕研究所",
        "emoji": "🍰",
        "cuisine": "烘焙甜品",
        "price_min": 22,
        "price_max": 42,
        "avg_rating": 4.7,
        "review_count": 960,
        "distance_min": 9,
        "tags": ["蛋糕", "烘焙", "甜品", "下午茶", "可坐"],
        "description": "蛋糕和烘焙甜点，适合两个人聊天。",
        "latitude": 31.1940,
        "longitude": 121.4367,
        "is_open": True,
        "signature_dish": "伯爵茶蛋糕",
        "walk_minutes": 9,
        "real_distance_m": 700,
    },
    {
        "id": 14,
        "name": "豆舍咖啡甜点",
        "emoji": "☕",
        "cuisine": "咖啡甜点",
        "price_min": 25,
        "price_max": 45,
        "avg_rating": 4.8,
        "review_count": 1340,
        "distance_min": 8,
        "tags": ["咖啡", "甜点", "蛋糕", "下午茶", "办公"],
        "description": "适合坐一会儿，甜点和咖啡稳定。",
        "latitude": 31.2298,
        "longitude": 121.4728,
        "is_open": True,
        "signature_dish": "燕麦拿铁配巴斯克",
        "walk_minutes": 8,
        "real_distance_m": 650,
    },
    {
        "id": 15,
        "name": "舟山海鲜下午茶",
        "emoji": "🦐",
        "cuisine": "海鲜",
        "price_min": 80,
        "price_max": 160,
        "avg_rating": 5.0,
        "review_count": 9999,
        "distance_min": 3,
        "tags": ["海鲜", "刺身", "聚餐", "下午茶", "高端"],
        "description": "海鲜和刺身正餐，被错误打上下午茶场景标签。",
        "latitude": 31.2305,
        "longitude": 121.4738,
        "is_open": True,
        "signature_dish": "刺身拼盘",
        "walk_minutes": 3,
        "real_distance_m": 240,
    },
    {
        "id": 16,
        "name": "烧肉一筋甜口酱",
        "emoji": "🥩",
        "cuisine": "日料",
        "price_min": 90,
        "price_max": 180,
        "avg_rating": 5.0,
        "review_count": 8800,
        "distance_min": 4,
        "tags": ["日料", "烧肉", "刺身", "下午茶", "约会"],
        "description": "日式烧肉正餐，甜口酱不能让它变成甜品候选。",
        "latitude": 31.2307,
        "longitude": 121.4740,
        "is_open": True,
        "signature_dish": "和牛烧肉",
        "walk_minutes": 4,
        "real_distance_m": 300,
    },
    {
        "id": 17,
        "name": "椰子鸡火锅",
        "emoji": "🥥",
        "cuisine": "火锅",
        "price_min": 68,
        "price_max": 120,
        "avg_rating": 4.9,
        "review_count": 2600,
        "distance_min": 9,
        "tags": ["火锅", "椰子鸡火锅", "不辣", "聚餐", "清淡"],
        "description": "不辣汤锅，适合想吃火锅但不吃辣。",
        "latitude": 31.2309,
        "longitude": 121.4741,
        "is_open": True,
        "signature_dish": "椰子鸡锅",
        "walk_minutes": 9,
        "real_distance_m": 680,
    },
    {
        "id": 18,
        "name": "潮汕牛肉火锅",
        "emoji": "🍲",
        "cuisine": "火锅",
        "price_min": 70,
        "price_max": 130,
        "avg_rating": 4.8,
        "review_count": 2200,
        "distance_min": 10,
        "tags": ["火锅", "潮汕牛肉火锅", "涮肉", "聚餐"],
        "description": "清汤牛肉火锅，适合多人聚餐。",
        "latitude": 31.2300,
        "longitude": 121.4727,
        "is_open": True,
        "signature_dish": "吊龙牛肉",
        "walk_minutes": 10,
        "real_distance_m": 760,
    },
]


REQUIRED_CASE_KEYS = {"id", "mode", "category", "variant", "turns", "context", "expected", "evaluation_checks"}
VALID_MODES = {"normal_agent", "map_agent"}


def _latest_user_message(case: dict[str, Any]) -> str:
    for turn in reversed(case["turns"]):
        if turn.get("role") == "user":
            return turn.get("content", "")
    return ""


def _seed_preferences(case: dict[str, Any]) -> dict[str, Any]:
    text = "\n".join(turn.get("content", "") for turn in case["turns"] if turn.get("role") == "user")
    pref = _parse_preferences(text)
    known = case.get("context", {}).get("known_preferences", [])
    if "avoid_spicy" in known:
        pref.setdefault("avoid_cuisines", []).append("spicy")
        pref.setdefault("avoid_tags", []).extend(["辣", "重庆", "川菜", "湘菜", "火锅"])
    if "prefer_light" in known:
        pref.setdefault("liked_cuisines", []).append("light")
    if "price_sensitive" in known or "budget_low" in known:
        pref["price_sensitivity"] = "high"
    if "distance_sensitive" in known:
        pref["distance_sensitivity"] = "high"
    if "avoid_seafood" in known:
        pref.setdefault("avoid_tags", []).extend(["海鲜", "寿司", "刺身"])
    if "low_sugar" in known:
        pref.setdefault("avoid_tags", []).extend(["全糖", "高糖"])
    for item in known:
        if item.startswith("avoid_restaurant:"):
            name = item.split(":", 1)[1]
            for restaurant in SAMPLE_RESTAURANTS:
                if restaurant["name"] == name:
                    pref.setdefault("avoid_restaurant_ids", []).append(restaurant["id"])
    learned = _parse_feedback(text, SAMPLE_RESTAURANTS, pref.get("recent_recommendation_ids", []))
    _merge_session_preferences(pref, {}, learned)
    pref["agent_mode"] = case["mode"]
    return pref


def _has_any_expected_tag(restaurant: dict[str, Any], tags: set[str]) -> bool:
    raw_tags = restaurant.get("tags", [])
    if isinstance(raw_tags, str):
        raw_tags = [tag.strip() for tag in raw_tags.split(",") if tag.strip()]
    text = " ".join([
        str(restaurant.get("name", "")),
        str(restaurant.get("cuisine", "")),
        " ".join(raw_tags),
        str(restaurant.get("description", "")),
    ])
    return any(tag and tag in text for tag in tags)


def validate_dataset(cases: list[dict[str, Any]]) -> list[str]:
    errors: list[str] = []
    ids: set[str] = set()
    for index, case in enumerate(cases):
        missing = REQUIRED_CASE_KEYS - set(case)
        if missing:
            errors.append(f"case[{index}] missing keys: {sorted(missing)}")
        case_id = case.get("id")
        if case_id in ids:
            errors.append(f"duplicate case id: {case_id}")
        ids.add(case_id)
        if case.get("mode") not in VALID_MODES:
            errors.append(f"{case_id}: invalid mode {case.get('mode')}")
        if not case.get("turns"):
            errors.append(f"{case_id}: no turns")
        expected = case.get("expected", {})
        for key in ("intent", "must_infer", "must_include", "must_avoid"):
            if key not in expected:
                errors.append(f"{case_id}: expected missing {key}")
    mode_counts = Counter(case.get("mode") for case in cases)
    if mode_counts != {"normal_agent": 2500, "map_agent": 2500}:
        errors.append(f"mode distribution mismatch: {dict(mode_counts)}")
    if len(cases) != 5000:
        errors.append(f"expected 5000 cases, got {len(cases)}")
    return errors


def run_rule_smoke(case: dict[str, Any]) -> dict[str, Any]:
    random.seed(case["id"])
    message = _latest_user_message(case)
    location = case.get("context", {}).get("location")
    location_tuple = tuple(location) if isinstance(location, list) and len(location) == 2 else None
    pref = _seed_preferences(case)
    reply, recommendations = _rule_agent(message, SAMPLE_RESTAURANTS, pref, location_tuple)
    aligned_reply = _aligned_recommendation_reply(message, recommendations, pref) if recommendations else reply

    failures: list[str] = []
    warnings: list[str] = []
    expected = case["expected"]

    if expected.get("no_recommendations"):
        if recommendations:
            failures.append("boundary_question_should_not_recommend_restaurants")
        if not any(word in aligned_reply for word in ("小觅", "可以", "提问", "推荐", "依据", "价格", "地图", "预算", "快速", "清淡", "聚餐", "坐一会儿")):
            failures.append("boundary_reply_missing_helpful_explanation")
        return {
            "id": case["id"],
            "mode": case["mode"],
            "category": case["category"],
            "intent": expected.get("intent"),
            "failures": failures,
            "warnings": warnings,
            "recommendation_names": [r["name"] for r in recommendations],
        }

    if len(recommendations) > 3:
        failures.append("too_many_recommendations")
    if any(phrase in aligned_reply for phrase in ("按你这轮需求重新筛了这几家", "文字和地图卡片是一一对应")):
        failures.append("reply_uses_stiff_template_intro")
    for restaurant in recommendations:
        if restaurant["name"] not in aligned_reply:
            failures.append(f"recommendation_not_in_reply:{restaurant['name']}")

    if case["mode"] == "map_agent" and not any(word in aligned_reply for word in ("地图", "点位", "路线", "地铁", "商场")):
        failures.append("map_agent_missing_spatial_language")
    if case["mode"] == "normal_agent" and not any(word in aligned_reply for word in ("心愿单", "地图", "卡片")):
        warnings.append("normal_agent_missing_action_handoff")

    avoid_text = " ".join(expected.get("must_avoid", []))
    if "重庆秀山小面" in avoid_text and any(r["name"] == "重庆秀山小面" for r in recommendations):
        failures.append("violated_avoid_restaurant:重庆秀山小面")
    if any(token in avoid_text for token in ("川菜", "湘菜", "火锅", "重辣", "麻辣")):
        spicy_names = [
            r["name"]
            for r in recommendations
            if any(t in r.get("tags", []) for t in ("川菜", "湘菜", "麻辣", "重庆", "辣"))
            and not any(t in r.get("tags", []) for t in ("不辣", "清淡", "椰子鸡火锅", "潮汕牛肉火锅"))
        ]
        if spicy_names and any(word in message for word in ("不辣", "不吃辣", "清淡", "轻食", "别太辣")):
            failures.append("violated_avoid_spicy:" + ",".join(spicy_names))

    expected_intents = set(expected.get("expected_intents", []))
    if expected.get("intent") == "sweet_craving" or "sweet_craving" in expected_intents:
        sweet_names = [r["name"] for r in recommendations if _is_sweet_candidate(r)]
        forbidden_names = [r["name"] for r in recommendations if _has_any_expected_tag(r, SWEET_FORBIDDEN_MAIN_TAGS)]
        if not sweet_names:
            failures.append("sweet_intent_missing_sweet_candidates")
        if forbidden_names:
            failures.append("sweet_intent_recommended_main_meal:" + ",".join(forbidden_names))
        if not any(word in aligned_reply for word in ("甜", "奶茶", "蛋糕", "糖水", "下午茶", "咖啡")):
            failures.append("sweet_intent_reply_missing_sweet_language")
        fake_afternoon_tea = [
            r["name"]
            for r in recommendations
            if "下午茶" in r.get("tags", []) and not _has_any_expected_tag(r, SWEET_PRIMARY_TAGS)
        ]
        if fake_afternoon_tea:
            failures.append("sweet_intent_used_afternoon_tea_as_only_signal:" + ",".join(fake_afternoon_tea))

    if expected.get("intent") == "cool_craving" or "cool_craving" in expected_intents:
        cool_names = [r["name"] for r in recommendations if _has_any_expected_tag(r, COOL_TAGS)]
        forbidden_names = [r["name"] for r in recommendations if _has_any_expected_tag(r, COOL_FORBIDDEN_TAGS)]
        if not cool_names:
            failures.append("cool_intent_missing_cool_candidates")
        if forbidden_names:
            failures.append("cool_intent_recommended_hot_or_stir_fry:" + ",".join(forbidden_names))
        if not any(word in aligned_reply for word in ("凉", "冰", "冷", "清爽", "冷饮", "冰品", "热炒")):
            failures.append("cool_intent_reply_missing_cool_language")

    if expected.get("intent") == "western_craving" or "western_craving" in expected_intents:
        western_names = [r["name"] for r in recommendations if _has_any_expected_tag(r, WESTERN_TAGS)]
        forbidden_names = [
            r["name"]
            for r in recommendations
            if _has_any_expected_tag(r, {"海鲜", "刺身", "日料", "寿司", "小面", "重庆", "麻辣", "川菜", "湘菜"})
        ]
        if not western_names:
            failures.append("western_intent_missing_western_candidates")
        if forbidden_names:
            failures.append("western_intent_recommended_wrong_category:" + ",".join(forbidden_names))
        if not any(word in aligned_reply for word in ("西餐", "意面", "披萨", "牛排", "汉堡", "西式")):
            failures.append("western_intent_reply_missing_western_language")

    expected_tags = set(expected.get("expected_candidate_tags", []))
    if expected_tags and recommendations:
        matched = [r["name"] for r in recommendations if _has_any_expected_tag(r, expected_tags)]
        if not matched:
            failures.append("missing_expected_candidate_tags:" + ",".join(sorted(expected_tags)))

    forbidden_tags = set(expected.get("forbidden_candidate_tags", []))
    if forbidden_tags:
        bad = [r["name"] for r in recommendations if _has_any_expected_tag(r, forbidden_tags)]
        if bad:
            failures.append("contains_forbidden_candidate_tags:" + ",".join(bad))

    required_all_tags = set(expected.get("required_candidate_tags_all", []))
    if required_all_tags and recommendations:
        bad = [r["name"] for r in recommendations if not _has_any_expected_tag(r, required_all_tags)]
        if bad:
            failures.append("candidate_outside_required_category:" + ",".join(bad))

    return {
        "id": case["id"],
        "mode": case["mode"],
        "category": case["category"],
        "intent": expected.get("intent"),
        "failures": failures,
        "warnings": warnings,
        "recommendation_names": [r["name"] for r in recommendations],
    }


def build_report(cases: list[dict[str, Any]]) -> dict[str, Any]:
    dataset_errors = validate_dataset(cases)
    results = [run_rule_smoke(case) for case in cases]
    failure_results = [result for result in results if result["failures"]]
    warning_results = [result for result in results if result["warnings"]]
    by_mode = defaultdict(lambda: {"total": 0, "failed": 0, "warned": 0})
    by_intent = defaultdict(lambda: {"total": 0, "failed": 0})
    for result in results:
        bucket = by_mode[result["mode"]]
        bucket["total"] += 1
        if result["failures"]:
            bucket["failed"] += 1
        if result["warnings"]:
            bucket["warned"] += 1
        intent_bucket = by_intent[result.get("intent") or "unknown"]
        intent_bucket["total"] += 1
        if result["failures"]:
            intent_bucket["failed"] += 1
    return {
        "dataset": {
            "total": len(cases),
            "errors": dataset_errors,
            "mode_counts": dict(Counter(case["mode"] for case in cases)),
            "category_counts": dict(Counter(case["category"] for case in cases)),
            "intent_counts": dict(Counter(case.get("expected", {}).get("intent") for case in cases)),
            "boundary_cases": sum(1 for case in cases if case.get("expected", {}).get("no_recommendations")),
        },
        "smoke": {
            "total": len(results),
            "passed": len(results) - len(failure_results),
            "failed": len(failure_results),
            "warned": len(warning_results),
            "by_mode": dict(by_mode),
            "by_intent": dict(by_intent),
            "failures": failure_results[:30],
            "warnings": warning_results[:30],
        },
    }


def run_entrypoint_regressions() -> list[str]:
    """Verify behavior at the public chat_session entry, not only the local rule helper."""
    errors: list[str] = []
    orm_restaurants = [
        SimpleNamespace(
            **{
                **restaurant,
                "tags": ",".join(restaurant.get("tags", []))
                if isinstance(restaurant.get("tags"), list)
                else restaurant.get("tags", ""),
            }
        )
        for restaurant in SAMPLE_RESTAURANTS
    ]

    async def _run() -> None:
        checks = [
            ("你是谁", "normal_agent"),
            ("我该如何提问你，才能推荐更准", "normal_agent"),
            ("地图页我该怎么问你", "map_agent"),
            ("我没开定位，可以先做什么", "map_agent"),
            ("社群相关事项都有哪些", "normal_agent"),
            ("社区里一般能看什么内容", "normal_agent"),
            ("这个产品除了推荐餐厅还能干嘛", "normal_agent"),
            ("我随便问个问题你会做什么", "normal_agent"),
            ("为什么我附近有些店搜不到", "normal_agent"),
            ("定位会不会保存我的位置，隐私安全吗", "normal_agent"),
            ("地图空白加载不出来怎么办", "map_agent"),
            ("为什么小觅回复很慢", "normal_agent"),
            ("评价写错了可以修改或删除吗", "normal_agent"),
            ("我想新增一家餐厅到库里", "normal_agent"),
            ("可以直接外卖下单或付款吗", "normal_agent"),
        ]
        for message, mode in checks:
            result = await chat_session(None, message, [], location=None, agent_mode=mode)
            if result.get("recommendations"):
                errors.append(f"entrypoint_meta_should_not_recommend:{message}")
            if not any(word in result.get("reply", "") for word in ("小觅", "提问", "地图", "定位", "预算", "推荐", "社区", "心愿单", "产品", "功能", "数据", "隐私", "刷新", "评价", "餐厅", "支付")):
                errors.append(f"entrypoint_meta_reply_unhelpful:{message}")

        vague = await chat_session(None, "我不知道吃什么，你看着办", orm_restaurants, agent_mode="normal_agent")
        if vague.get("recommendations"):
            errors.append("entrypoint_vague_need_should_clarify_without_cards")

        fruit = await chat_session(None, "想买点水果，附近有什么推荐", orm_restaurants, agent_mode="normal_agent")
        if fruit.get("recommendations"):
            errors.append("entrypoint_out_of_scope_category_should_not_recommend_cards")
        if not all(word in fruit.get("reply", "") for word in ("水果", "不", "餐厅")):
            errors.append("entrypoint_out_of_scope_category_missing_fallback_explanation")

        cool = await chat_session(None, "我想吃凉的", orm_restaurants, agent_mode="normal_agent")
        if not cool.get("recommendations"):
            errors.append("entrypoint_cool_should_recommend_cool_options")
        elif any(_has_any_expected_tag(r, COOL_FORBIDDEN_TAGS) for r in cool["recommendations"]):
            errors.append("entrypoint_cool_recommended_hot_or_stir_fry")
        if not any(word in cool.get("reply", "") for word in ("凉", "冰", "冷", "清爽", "热炒")):
            errors.append("entrypoint_cool_reply_missing_cool_language")
        cool_meal = await chat_session(None, "想吃冰一点的，但最好能当一餐", orm_restaurants, agent_mode="normal_agent")
        if not cool_meal.get("recommendations"):
            errors.append("entrypoint_cool_meal_should_recommend_cool_options")
        elif any(_has_any_expected_tag(r, COOL_FORBIDDEN_TAGS) for r in cool_meal["recommendations"]):
            errors.append("entrypoint_cool_meal_recommended_hot_or_stir_fry")
        elif not _has_any_expected_tag(cool_meal["recommendations"][0], {"凉面", "冷食", "沙拉", "轻食"}):
            errors.append("entrypoint_cool_meal_should_prioritize_real_meal")

        hotpot_first = await chat_session(None, "想吃火锅，人均100以内", orm_restaurants, agent_mode="normal_agent")
        hotpot_session_id = hotpot_first["session_id"]
        if not hotpot_first.get("recommendations"):
            errors.append("entrypoint_hotpot_should_recommend_hotpot")
        elif any(not _has_any_expected_tag(r, HOTPOT_TAGS) for r in hotpot_first["recommendations"]):
            errors.append("entrypoint_hotpot_recommended_non_hotpot")

        hotpot_second = await chat_session(
            hotpot_session_id,
            "这家不行，换一家",
            orm_restaurants,
            agent_mode="normal_agent",
        )
        first_ids = {r["id"] for r in hotpot_first.get("recommendations", [])}
        second_ids = {r["id"] for r in hotpot_second.get("recommendations", [])}
        if second_ids & first_ids:
            errors.append("entrypoint_revision_repeated_rejected_hotpot")
        if hotpot_second.get("recommendations") and any(not _has_any_expected_tag(r, HOTPOT_TAGS) for r in hotpot_second["recommendations"]):
            errors.append("entrypoint_revision_lost_hotpot_memory")

        hotpot_then_vague_place = await chat_session(
            hotpot_session_id,
            "我不知道吃什么，上海南站附近有什么好吃的",
            orm_restaurants,
            agent_mode="normal_agent",
        )
        if hotpot_then_vague_place.get("recommendations"):
            errors.append("entrypoint_vague_new_place_should_confirm_context")
        if not all(word in hotpot_then_vague_place.get("reply", "") for word in ("火锅", "重启")):
            errors.append("entrypoint_vague_new_place_missing_memory_confirmation")

        hotpot_continue = await chat_session(
            hotpot_session_id,
            "继续火锅，换个不辣的",
            orm_restaurants,
            agent_mode="normal_agent",
        )
        if hotpot_continue.get("recommendations") and any(not _has_any_expected_tag(r, HOTPOT_TAGS) for r in hotpot_continue["recommendations"]):
            errors.append("entrypoint_continue_context_lost_hotpot")

        hotpot_reset = await chat_session(
            hotpot_session_id,
            "不按上次了，重启口味",
            orm_restaurants,
            agent_mode="normal_agent",
        )
        if hotpot_reset.get("recommendations"):
            errors.append("entrypoint_reset_context_should_clarify_without_cards")
        if not any(word in hotpot_reset.get("reply", "") for word in ("不按上一轮", "清淡", "甜口", "快速")):
            errors.append("entrypoint_reset_context_reply_unhelpful")

    asyncio.run(_run())
    return errors


def run_failure_replay_regressions() -> list[str]:
    """Replay real user-reported failures and keep them as always-on gates."""
    errors: list[str] = []
    orm_restaurants = [
        SimpleNamespace(
            **{
                **restaurant,
                "tags": ",".join(restaurant.get("tags", []))
                if isinstance(restaurant.get("tags"), list)
                else restaurant.get("tags", ""),
            }
        )
        for restaurant in SAMPLE_RESTAURANTS
    ]

    async def _run() -> None:
        for case in FAILURE_REPLAY_CASES:
            expected = case["expected"]
            result = await chat_session(
                None,
                case["message"],
                orm_restaurants,
                agent_mode=case.get("mode", "normal_agent"),
            )
            recs = result.get("recommendations", [])
            reply = result.get("reply", "")
            if expected.get("no_recommendations") and recs:
                errors.append(f"{case['id']}:should_not_recommend")
            if expected.get("must_recommend") and not recs:
                errors.append(f"{case['id']}:should_recommend")
                continue
            if expected.get("intent") and result.get("intent") != expected["intent"]:
                errors.append(f"{case['id']}:intent_mismatch:{result.get('intent')}")
            reply_any = expected.get("reply_any")
            if reply_any and not any(word in reply for word in reply_any):
                errors.append(f"{case['id']}:reply_missing_any:{reply_any}")
            if recs and expected.get("first_candidate_tags_any"):
                if not _has_any_expected_tag(recs[0], set(expected["first_candidate_tags_any"])):
                    errors.append(f"{case['id']}:first_candidate_not_aligned:{recs[0].get('name')}")
            forbidden = set(expected.get("forbidden_candidate_tags", []))
            if recs and forbidden:
                bad = [r.get("name") for r in recs if _has_any_expected_tag(r, forbidden)]
                if bad:
                    errors.append(f"{case['id']}:forbidden_candidates:{','.join(bad)}")

    asyncio.run(_run())
    return errors


def run_intent_slot_regressions() -> list[str]:
    """Cuisine/entity prompts must not enter recommendation with empty slots."""
    errors: list[str] = []
    checks = [
        ("我想喝咖啡", "cafe"),
        ("拿铁", "cafe"),
        ("想吃西餐", "western"),
        ("意面披萨都可以", "western"),
        ("韩餐部队锅", "korean"),
        ("冬阴功", "thai"),
        ("大盘鸡", "xinjiang"),
        ("锅包肉", "northeast"),
        ("云吞面", "cantonese"),
        ("烧烤烤串", "barbecue"),
        ("米线", "noodles"),
        ("奶茶果茶", "tea_drink"),
    ]
    for message, expected_cuisine in checks:
        pref = _parse_preferences(message)
        if pref.get("cuisine") != expected_cuisine:
            errors.append(f"slot_mismatch:{message}:{pref.get('cuisine')}!={expected_cuisine}")
    return errors


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true", help="print full JSON report")
    args = parser.parse_args()
    report = build_report(TRAINING_CASES)
    entrypoint_errors = run_entrypoint_regressions()
    failure_replay_errors = run_failure_replay_regressions()
    intent_slot_errors = run_intent_slot_regressions()
    report["entrypoint"] = {"errors": entrypoint_errors}
    report["failure_replay"] = {"cases": len(FAILURE_REPLAY_CASES), "errors": failure_replay_errors}
    report["intent_slots"] = {"errors": intent_slot_errors}
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return

    dataset = report["dataset"]
    smoke = report["smoke"]
    print("Agent training dataset")
    print(f"- cases: {dataset['total']}")
    print(f"- modes: {dataset['mode_counts']}")
    print(f"- categories: {len(dataset['category_counts'])}")
    print(f"- intents: {len(dataset['intent_counts'])}")
    print(f"- boundary cases: {dataset['boundary_cases']}")
    print(f"- dataset errors: {len(dataset['errors'])}")
    print(f"- entrypoint errors: {len(entrypoint_errors)}")
    print(f"- failure replay: {len(FAILURE_REPLAY_CASES)} cases, {len(failure_replay_errors)} errors")
    print(f"- intent slot errors: {len(intent_slot_errors)}")
    print()
    print("Local rule smoke test")
    print(f"- passed: {smoke['passed']}/{smoke['total']}")
    print(f"- failed: {smoke['failed']}")
    print(f"- warnings: {smoke['warned']}")
    print(f"- by mode: {smoke['by_mode']}")
    if smoke["failures"]:
        print()
        print("Top failures")
        for item in smoke["failures"][:10]:
            print(f"- {item['id']} {item['category']}: {item['failures']}")


if __name__ == "__main__":
    main()
