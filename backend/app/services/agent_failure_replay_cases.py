"""
Real failure replay cases for 小觅 Agent.

These cases come from product-debug conversations and should stay small,
strict, and always-on. Broad synthetic data can expand coverage, but this file
guards against regressions users have already experienced.
"""
from __future__ import annotations

FAILURE_REPLAY_CASES: list[dict] = [
    {
        "id": "identity_should_not_recommend",
        "message": "你是谁",
        "mode": "normal_agent",
        "expected": {
            "no_recommendations": True,
            "reply_any": ["小觅", "美食助手", "位置"],
            "intent": "meta_or_product_help",
        },
    },
    {
        "id": "help_should_not_recommend",
        "message": "我该如何提问",
        "mode": "normal_agent",
        "expected": {
            "no_recommendations": True,
            "reply_any": ["位置", "预算", "口味"],
            "intent": "meta_or_product_help",
        },
    },
    {
        "id": "community_should_not_fallback_to_food",
        "message": "社群相关事项都有哪些",
        "mode": "normal_agent",
        "expected": {
            "no_recommendations": True,
            "reply_any": ["社区圈", "热帖", "评价", "探店"],
            "intent": "meta_or_product_help",
        },
    },
    {
        "id": "wishlist_product_question",
        "message": "心愿单和收藏是不是一个东西，怎么用",
        "mode": "normal_agent",
        "expected": {
            "no_recommendations": True,
            "reply_any": ["心愿单", "收藏", "加入地图"],
            "intent": "meta_or_product_help",
        },
    },
    {
        "id": "map_product_question",
        "message": "地图页除了看餐厅点位还能做什么",
        "mode": "map_agent",
        "expected": {
            "no_recommendations": True,
            "reply_any": ["地图", "地铁", "商场", "路线"],
            "intent": "meta_or_product_help",
        },
    },
    {
        "id": "sweet_should_not_recommend_savory_meal",
        "message": "我想吃甜的",
        "mode": "normal_agent",
        "expected": {
            "must_recommend": True,
            "first_candidate_tags_any": ["甜品", "奶茶", "饮品", "蛋糕", "糖水", "冰品"],
            "forbidden_candidate_tags": ["东北菜", "川菜", "火锅", "海鲜", "日料", "烧肉"],
            "intent": "food_recommendation",
        },
    },
    {
        "id": "cool_should_not_recommend_hot_stir_fry",
        "message": "我想吃凉的",
        "mode": "normal_agent",
        "expected": {
            "must_recommend": True,
            "first_candidate_tags_any": ["凉面", "冷食", "沙拉", "轻食", "冰品", "冷饮", "饮品"],
            "forbidden_candidate_tags": ["热汤", "火锅", "热炒", "炒菜", "川菜", "湘菜"],
            "intent": "food_recommendation",
        },
    },
    {
        "id": "cool_meal_prioritize_real_food",
        "message": "想吃冰一点的，但最好能当一餐",
        "mode": "normal_agent",
        "expected": {
            "must_recommend": True,
            "first_candidate_tags_any": ["凉面", "冷食", "沙拉", "轻食"],
            "forbidden_candidate_tags": ["热汤", "火锅", "热炒", "炒菜", "川菜", "湘菜"],
            "intent": "food_recommendation",
        },
    },
    {
        "id": "western_should_not_recommend_seafood_noodles_or_japanese",
        "message": "我想吃西餐",
        "mode": "normal_agent",
        "expected": {
            "must_recommend": True,
            "first_candidate_tags_any": ["西餐", "西式", "意面", "披萨", "牛排", "brunch", "法餐", "美式", "简餐"],
            "forbidden_candidate_tags": ["海鲜", "刺身", "日料", "寿司", "小面", "重庆", "麻辣", "川菜", "湘菜"],
            "intent": "food_recommendation",
        },
    },
    {
        "id": "korean_should_not_recommend_hotpot_or_noodles",
        "message": "想吃韩餐，部队锅或者拌饭都行",
        "mode": "normal_agent",
        "expected": {
            "must_recommend": True,
            "first_candidate_tags_any": ["韩餐", "韩国料理", "韩式", "部队锅", "石锅拌饭"],
            "forbidden_candidate_tags": ["火锅", "小面", "重庆", "西餐", "甜品"],
            "intent": "food_recommendation",
        },
    },
    {
        "id": "tea_drink_should_not_recommend_meal",
        "message": "想喝奶茶果茶，别推正餐",
        "mode": "normal_agent",
        "expected": {
            "must_recommend": True,
            "first_candidate_tags_any": ["奶茶", "饮品", "果茶", "茶饮", "冷饮"],
            "forbidden_candidate_tags": ["火锅", "海鲜", "东北菜", "小面", "烧烤"],
            "intent": "food_recommendation",
        },
    },
    {
        "id": "cafe_work_should_not_recommend_loud_meal",
        "message": "想找咖啡店办公，有插座安静一点",
        "mode": "normal_agent",
        "expected": {
            "must_recommend": True,
            "first_candidate_tags_any": ["咖啡", "办公", "自习", "插座", "安静"],
            "forbidden_candidate_tags": ["火锅", "烧烤", "海鲜", "夜宵"],
            "intent": "food_recommendation",
        },
    },
    {
        "id": "coffee_plain_should_not_recommend_meal",
        "message": "我想喝咖啡",
        "mode": "map_agent",
        "expected": {
            "must_recommend": True,
            "first_candidate_tags_any": ["咖啡", "咖啡馆", "办公", "插座", "安静"],
            "forbidden_candidate_tags": ["本帮菜", "上海菜", "烧烤", "海鲜", "小面", "川菜", "湘菜", "日料", "火锅"],
            "intent": "food_recommendation",
        },
    },
    {
        "id": "fruit_out_of_scope_no_cards",
        "message": "想买点水果，附近有什么推荐",
        "mode": "normal_agent",
        "expected": {
            "no_recommendations": True,
            "reply_any": ["水果", "餐厅", "商超", "便利店"],
            "intent": "out_of_scope_category",
        },
    },
    {
        "id": "daily_life_unclear_should_clarify",
        "message": "今天好累不想动，你看着办",
        "mode": "normal_agent",
        "expected": {
            "no_recommendations": True,
            "reply_any": ["不硬推", "预算", "位置", "安静", "热闹"],
            "intent": "lifestyle_planning_unclear",
        },
    },
    {
        "id": "small_talk_should_route",
        "message": "我随便问个问题你会做什么",
        "mode": "normal_agent",
        "expected": {
            "no_recommendations": True,
            "reply_any": ["小觅", "地图", "心愿单", "社区"],
            "intent": "meta_or_product_help",
        },
    },
]
