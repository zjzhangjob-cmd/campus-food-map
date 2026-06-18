from app.core.config import settings
from typing import List

SYSTEM_PROMPT = """你是「觅食」大学城美食地图的AI推荐助手。
你了解周边所有餐厅的信息，会根据用户的心情、预算、人数、口味偏好来推荐最合适的餐厅。
回复要简洁有趣，用 emoji 增加亲切感，重点突出餐厅名称和理由。
如果提到具体餐厅，请在名称前后加上**号，例如：**老林家重庆小面**。
回复控制在150字以内。"""

async def get_ai_recommendation(message: str, restaurants_context: str = "") -> tuple[str, List[int]]:
    """
    调用 Claude API 获取 AI 推荐
    返回 (回复文本, 推荐餐厅ID列表)
    """
    if not settings.ANTHROPIC_API_KEY:
        # 未配置 API Key 时返回本地规则推荐
        return _rule_based_recommend(message), []

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)

        user_content = message
        if restaurants_context:
            user_content = f"当前可选餐厅信息：\n{restaurants_context}\n\n用户需求：{message}"

        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_content}],
        )
        reply = response.content[0].text
        return reply, []

    except Exception as e:
        return _rule_based_recommend(message), []

def _rule_based_recommend(message: str) -> str:
    """未配置 AI 时的规则推荐兜底"""
    rules = {
        "辣": "🌶️ 推荐你试试 **老林家重庆小面**！汤底鲜辣醇厚，越辣越过瘾，步行5分钟就到，人均¥15超划算！",
        "快": "⚡ **胡同煎饼摊** 是你的最佳选择！步行2分钟，5分钟搞定，¥8一个煎饼果子，赶课必备！",
        "便宜|省钱|预算": "💰 推荐 **胡同煎饼摊**（¥6起）和 **老林家重庆小面**（¥12起），都是学生口碑之选！",
        "健康|减脂|轻食": "🥗 **绿野轻食工坊** 正适合你！低卡沙拉碗，食材新鲜，减脂不减口感，人均¥30左右。",
        "宵夜|深夜|晚上": "🌙 **云贵小馆** 凌晨2点还营业！过桥米线热乎乎的，深夜觅食就选它，步行7分钟。",
        "聚餐|约饭|多人": "👥 推荐 **鱼跃回转寿司** 或 **韩味烤肉·浪**，环境好、适合拍照，聚餐氛围满分！",
        "日料|寿司": "🍣 **鱼跃回转寿司** 是大学城日料首选，种类丰富新鲜，步行12分钟，人均¥50左右。",
    }
    for keys, reply in rules.items():
        for key in keys.split("|"):
            if key in message:
                return reply
    return "🍽️ 根据你的需求，推荐先看看口碑榜前三：**老林家重庆小面**（4.9分）、**胡同煎饼摊**（4.8分）、**云贵小馆**（4.8分），都是学生最爱！"
