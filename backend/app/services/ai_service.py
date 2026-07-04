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


@dataclass
class ConversationDecision:
    action: str
    reply: str | None = None
    allow_recommendations: bool = True
    clear_recent: bool = False
    reason: str = ""


@dataclass
class IntentFrame:
    primary: str
    action: str
    confidence: float = 0.7
    slots: dict[str, Any] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)

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
- 当用户问“你是谁/你能做什么/我该如何提问/推荐依据是什么/价格准吗”等边界问题时，先回答能力、用法或依据，不要硬推餐厅
- 不确定时少编造，多追问一个关键问题
"""

MODE_INSTRUCTIONS = {
    "normal_agent": """【当前形态：普通小觅agent】
- 主要目标是通过自然多轮对话深挖用户真实需求，再用餐厅卡片流承接。
- 不要一上来机械推荐很多家；信息不足时追问一个最关键问题。
- 当信息足够时，输出2-3家餐厅，并明确为什么适合、有什么风险、下一步可加入心愿单或地图。
- 如果用户提到后续行动、空间方位、地铁/商场/展会/回家，应主动建议进入全屏地图综合选择。""",
    "map_agent": """【当前形态：地图小觅agent】
- 主要目标是把用户需求转成空间选择：餐厅点位、用户位置、距离弧线、地铁站、商场、展会、办公/自习点、停车点等。
- 推荐新餐厅时应默认替换旧推荐点位；若用户说保留某家或心愿单，则只保留指定点位。
- 信息不足时优先追问路线必需信息：下一站、交通方式、时间上限、是否要少走路/少过街/近地铁。
- 输出应说明地图动作，例如“我会把这几家放到地图上，并标出最近地铁站/商场”。""",
}


def _mode_instruction(agent_mode: str | None) -> str:
    return MODE_INSTRUCTIONS.get(agent_mode or "normal_agent", MODE_INSTRUCTIONS["normal_agent"])

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
NEGATIVE_PATTERN = re.compile(r"(不吃|不要|别|不想|不喜欢|讨厌|避开|换一家|不行|踩雷|难吃|太贵|太远|排队|不合适|不太行|一般般|不太好|不是很|不怎么样|换个|换下|换一家|再看看|再考虑考虑|再想想|没感觉|没什么兴趣|不感兴趣)")
POSITIVE_PATTERN = re.compile(r"(喜欢|爱吃|想吃|以后多推|可以多推荐|不错|好吃|满意)")
META_IDENTITY_PATTERN = re.compile(r"(你是谁|你叫什么|小觅是谁|这是.*什么)")
META_HELP_PATTERN = re.compile(r"(怎么问|如何提问|怎么使用|怎么用|能做什么|可以做什么|会做什么|帮我做什么|还能干嘛|除了.*还能|使用方法|没开定位|没定位|没有定位|不开定位)")
META_TRUST_PATTERN = re.compile(r"(依据|靠谱吗|准吗|为什么推荐|怎么推荐|怎么算|人均是什么意思|价格准)")
PRODUCT_COMMUNITY_PATTERN = re.compile(r"(社区圈|社群|社区|帖子|发帖|探店|附近评价|邻居|热帖)")
PRODUCT_WISHLIST_PATTERN = re.compile(r"(心愿单|收藏|想吃|加入地图|一键规划|批量加入|移出心愿单|取消收藏)")
PRODUCT_MAP_PATTERN = re.compile(r"(全屏地图|地图页|地图助手|定位|搜索地点|地图点位|路线|地铁站|商场|展会|停车)")
PRODUCT_AGENT_MODE_PATTERN = re.compile(r"(普通小觅|地图小觅|小觅agent|小觅助手|agent形态|对话入口|地图结合)")
PRODUCT_DETAIL_PATTERN = re.compile(r"(菜单|评价|详情|营业时间|地址|电话|收藏餐厅|餐厅详情|查看详情)")
PRODUCT_ACCOUNT_PATTERN = re.compile(r"(登录|账号|个人页|个人中心|我的评价|资料|同步|退出登录)")
PRODUCT_FEEDBACK_PATTERN = re.compile(r"(推荐不准|不准确|不符合|怎么告诉你|反馈|纠错|重新推荐|重筛|保留哪家)")
PRODUCT_GENERAL_PATTERN = re.compile(r"(这个产品|产品|觅食|功能范围)")
PRODUCT_DATA_PATTERN = re.compile(r"(数据|覆盖|收录|餐厅库|更新频率|评分|价格|营业时间|为什么没有|没有这家|搜不到|没搜到|查不到|信息不准|地址错|电话错)")
PRODUCT_PRIVACY_PATTERN = re.compile(r"(隐私|定位权限|位置会不会|会保存|保存我的|数据安全|授权定位|不开定位)")
PRODUCT_ERROR_PATTERN = re.compile(r"(加载不出来|加载失败|地图空白|卡住|很慢|响应慢|没反应|报错|网络|刷新|重启后端)")
PRODUCT_REVIEW_PATTERN = re.compile(r"(评论|评价|删除评价|修改评价|举报|审核|点赞|回复)")
PRODUCT_MERCHANT_PATTERN = re.compile(r"(商家入驻|新增餐厅|添加餐厅|认领店铺|上传菜单|补充餐厅|改餐厅信息)")
PRODUCT_BOUNDARY_PATTERN = re.compile(r"(外卖|订座|付款|支付|优惠券|团购券|导航|打车|客服|人工|投诉)")
PRODUCT_PROBLEM_PATTERN = re.compile(r"(点不动|打不开|没反应|怎么没有|找不到|入口在哪|在哪看|怎么操作|不会用|不跳转)")
PRODUCT_CONTEXT_PATTERN = re.compile(r"(相关|事项|功能|介绍|说明|规则|内容|怎么玩|能看什么|有什么)")
WHY_HOW_PATTERN = re.compile(r"(为什么|怎么|如何|哪里|在哪|能不能|可不可以|是否|是不是|吗|呢)")
FOOD_REQUEST_PATTERN = re.compile(
    r"吃|喝|餐厅|饭|菜|面|粉|火锅|甜品|奶茶|咖啡|小吃|早餐|午饭|晚饭|夜宵|好吃|"
    r"推荐.*店|找.*店|附近.*吃|排队|等位|少等|出餐|评分不用|口味|人均|"
    r"凉的|冰的|冷的|冰一点|凉快|冷饮|冰饮|凉面|冷面|"
    r"西餐|意面|披萨|牛排|汉堡|brunch|法餐|美式|西式|"
    r"聚餐|宴请|商务|约会|纪念日|求婚|表白|浪漫|情调|"
    r"亲子|带娃|儿童|宝宝|家庭聚餐|家庭|"
    r"生日|圣诞|新年|情人节|中秋|国庆|节日|"
    r"养生|滋补|药膳|养胃|食疗|"
    r"夏天|解暑|冬天|暖胃|秋冬进补|季节|"
    r"团建|年会|谢师宴|升学宴|庆功宴|"
    r"网红店|打卡|拍照|氛围感|仪式感|"
    r"素食|清真|无辣|少油|少盐|无糖|清淡|"
    r"老字号|本地特色|必吃榜|米其林|黑珍珠|"
    r"下午茶|早茶|深夜食堂|夜宵|"
    r"请客|款待|招待|做客|"
    r"环境好|包厢|包房|私密|安静|停车|"
    r"性价比|实惠|便宜|贵的|高档|奢华|"
    r"炸酱面|拉面|小面|米线|米粉|酸辣粉|螺蛳粉|"
    r"烤肉|烤串|烧烤|烤鱼|小龙虾|"
    r"寿司|刺身|生鱼片|"
    r"咖喱|冬阴功|菠萝饭|"
    r"大盘鸡|手抓饭|烤包子|羊肉串|"
    r"锅包肉|铁锅炖|地三鲜|饺子|"
    r"红烧肉|生煎|小笼包|"
    r"烧腊|云吞面|煲仔饭|点心|"
    r"咖啡馆|拿铁|美式|冷萃|"
    r"海鲜|生蚝|螃蟹|虾|"
    r"果茶|柠檬茶|冷饮"
)
MAP_RERANK_PATTERN = re.compile(r"(不要只看|也看看|按.*排|排序|重排|筛|最近|距离|热度|评分|价格|路线|点位|保留)")
VAGUE_NEED_PATTERN = re.compile(r"(不知道吃什么|随便|都行|你看着办|帮我选|没想好|纠结)")
CONTEXT_RESET_PATTERN = re.compile(r"(重启|重新来|重新开始|不按上次|别按上次|换口味|不吃火锅|别按火锅|不是火锅)")
CONTEXT_CONTINUE_PATTERN = re.compile(r"(继续|按上次|还是火锅|继续火锅|就火锅|按火锅)")
OUT_OF_SCOPE_CATEGORY_PATTERN = re.compile(r"(水果|果切|鲜果|买果|生鲜|菜市场|超市|便利店|药店|药房)")
DAILY_LIFE_PATTERN = re.compile(
    r"(无聊|好累|累死|困|压力|焦虑|烦|开心|庆祝|约会|带娃|带孩子|带爸妈|老人|同事|朋友|加班|自习|办公|散步|遛弯|逛街|看电影|展会|演出|下雨|太热|太冷|不想动|赶地铁|回家)"
)
SMALL_TALK_PATTERN = re.compile(r"(你好|嗨|哈喽|早上好|晚上好|在吗|有人吗|随便聊|陪我聊|我随便问)")
PRODUCT_PATTERNS = (
    PRODUCT_COMMUNITY_PATTERN,
    PRODUCT_WISHLIST_PATTERN,
    PRODUCT_MAP_PATTERN,
    PRODUCT_AGENT_MODE_PATTERN,
    PRODUCT_DETAIL_PATTERN,
    PRODUCT_ACCOUNT_PATTERN,
    PRODUCT_FEEDBACK_PATTERN,
    PRODUCT_GENERAL_PATTERN,
    PRODUCT_DATA_PATTERN,
    PRODUCT_PRIVACY_PATTERN,
    PRODUCT_ERROR_PATTERN,
    PRODUCT_REVIEW_PATTERN,
    PRODUCT_MERCHANT_PATTERN,
    PRODUCT_BOUNDARY_PATTERN,
)

SPICY_TAGS = {"川菜", "湘菜", "重庆", "火锅", "辣", "川", "湘"}
HOTPOT_TAGS = {"火锅", "小火锅", "汤锅", "椰子鸡火锅", "潮汕牛肉火锅", "涮肉", "锅底"}
LIGHT_TAGS = {"轻食", "沙拉", "健康", "低卡", "日料", "寿司", "粥", "粤菜"}
COOL_TAGS = {"冰品", "冷饮", "冰饮", "饮品", "奶茶", "果茶", "咖啡", "糖水", "凉面", "冷面", "沙拉", "轻食", "甜品"}
COOL_FORBIDDEN_TAGS = {"热汤", "火锅", "冒菜", "热炒", "炒菜", "烧烤", "麻辣", "川菜", "湘菜", "汤面", "粥", "砂锅", "煲仔", "干锅"}
FAST_TAGS = {"煎饼", "快餐", "盖饭", "米线", "小面", "汉堡", "三明治"}
NIGHT_TAGS = {"烧烤", "宵夜", "小龙虾", "串串", "啤酒", "夜市"}
DATE_TAGS = {"日料", "意面", "法餐", "咖啡", "甜品", "brunch"}
GROUP_TAGS = {"烤肉", "火锅", "寿司", "聚餐", "包房", "商务", "宴请", "多人"}
BUSINESS_TAGS = {"商务", "宴请", "包厢", "包房", "适合聚会", "环境好", "停车方便", "安静", "私密性"}
DATE_TAGS = {"日料", "意面", "法餐", "咖啡", "甜品", "brunch", "西餐", "浪漫", "情调", "氛围"}
PARENTING_TAGS = {"亲子", "儿童", "宝宝", "家庭聚餐", "家庭", "小孩", "孩子", "儿童友好", "游乐场", "母婴室"}
CELEBRATION_TAGS = {"生日", "纪念日", "庆祝", "节日", "圣诞", "新年", "情人节", "中秋", "国庆", "庆功", "谢师"}
HEALTH_TAGS = {"养生", "滋补", "药膳", "养胃", "食疗", "清淡", "少油", "少盐", "健康"}
SEASON_TAGS = {"夏天", "解暑", "冬天", "暖胃", "秋冬进补", "季节", "冬季", "夏季"}
INSTAGRAM_TAGS = {"网红店", "打卡", "拍照", "氛围感", "仪式感", "颜值", "好看", "出片"}
VEGETARIAN_TAGS = {"素食", "素菜", "素", "素食主义", "斋菜", "清真"}
LOCAL_TAGS = {"老字号", "本地特色", "必吃榜", "米其林", "黑珍珠", "本地", "地道", "特色"}
AFTERNOON_TEA_TAGS = {"下午茶", "早茶", "甜品", "咖啡", "点心", "奶茶", "蛋糕"}
LUXURY_TAGS = {"高档", "奢华", "高端", "米其林", "黑珍珠", "五星", "精致"}
BUDGET_TAGS = {"性价比", "实惠", "便宜", "平价", "亲民", "经济"}
WESTERN_TAGS = {"西餐", "西式", "意面", "披萨", "牛排", "汉堡", "brunch", "法餐", "美式", "简餐", "三明治"}
JAPANESE_TAGS = {"日料", "日本料理", "寿司", "刺身", "拉面", "烧鸟", "居酒屋", "鳗鱼饭", "寿喜锅"}
KOREAN_TAGS = {"韩餐", "韩国料理", "韩料", "韩式", "韩式烤肉", "部队锅", "泡菜", "石锅拌饭", "炸鸡"}
THAI_TAGS = {"泰餐", "泰国菜", "冬阴功", "咖喱", "菠萝炒饭", "泰式", "青木瓜沙拉"}
XINJIANG_TAGS = {"新疆菜", "新疆", "大盘鸡", "手抓饭", "烤包子", "羊肉串", "馕", "拌面"}
NORTHEAST_TAGS = {"东北菜", "东北", "锅包肉", "铁锅炖", "地三鲜", "饺子", "酸菜白肉"}
SHANGHAI_TAGS = {"本帮菜", "上海菜", "本地菜", "红烧肉", "响油鳝丝", "生煎", "小笼"}
CANTONESE_TAGS = {"粤菜", "广东菜", "港式", "茶餐厅", "早茶", "烧腊", "云吞面", "煲仔饭", "点心"}
BARBECUE_TAGS = {"烧烤", "烤肉", "烤串", "羊肉串", "串", "烤鱼", "烤鸡翅"}
NOODLE_TAGS = {"面馆", "面", "粉", "米线", "小面", "拉面", "拌面", "汤面", "酸辣粉", "螺蛳粉"}
CAFE_TAGS = {"咖啡", "咖啡馆", "办公", "自习", "插座", "安静"}
SEAFOOD_TAGS = {"海鲜", "小龙虾", "生蚝", "蟹", "虾", "舟山", "海产"}
TEA_DRINK_TAGS = {"奶茶", "饮品", "果茶", "茶饮", "冷饮", "柠檬茶"}
CUISINE_TAG_GROUPS = {
    "western": WESTERN_TAGS,
    "japanese": JAPANESE_TAGS,
    "korean": KOREAN_TAGS,
    "thai": THAI_TAGS,
    "xinjiang": XINJIANG_TAGS,
    "northeast": NORTHEAST_TAGS,
    "shanghai": SHANGHAI_TAGS,
    "cantonese": CANTONESE_TAGS,
    "barbecue": BARBECUE_TAGS,
    "noodles": NOODLE_TAGS,
    "cafe": CAFE_TAGS,
    "seafood": SEAFOOD_TAGS,
    "tea_drink": TEA_DRINK_TAGS,
}
CUISINE_SYNONYMS = [
    ("hotpot", HOTPOT_TAGS, ("火锅", "小火锅", "汤锅", "涮肉", "锅底", "椰子鸡火锅", "潮汕牛肉火锅")),
    ("western", WESTERN_TAGS, ("西餐", "西式", "意面", "披萨", "牛排", "汉堡", "brunch", "法餐", "美式")),
    ("korean", KOREAN_TAGS, ("韩餐", "韩国料理", "韩料", "韩式", "部队锅", "泡菜", "石锅拌饭", "韩式烤肉")),
    ("thai", THAI_TAGS, ("泰餐", "泰国菜", "冬阴功", "泰式", "菠萝炒饭", "青木瓜沙拉")),
    ("xinjiang", XINJIANG_TAGS, ("新疆菜", "新疆", "大盘鸡", "手抓饭", "烤包子", "馕", "新疆拌面")),
    ("northeast", NORTHEAST_TAGS, ("东北菜", "东北", "锅包肉", "铁锅炖", "地三鲜", "酸菜白肉")),
    ("shanghai", SHANGHAI_TAGS, ("本帮", "本帮菜", "上海菜", "本地菜", "红烧肉", "响油鳝丝", "生煎", "小笼")),
    ("cantonese", CANTONESE_TAGS, ("粤菜", "广东菜", "港式", "茶餐厅", "早茶", "烧腊", "云吞面", "煲仔饭")),
    ("barbecue", BARBECUE_TAGS, ("烧烤", "烤肉", "烤串", "烤鱼", "烤鸡翅")),
    ("noodles", NOODLE_TAGS, ("面馆", "吃面", "汤面", "拌面", "米线", "粉", "酸辣粉", "螺蛳粉", "拉面")),
    ("seafood", SEAFOOD_TAGS, ("海鲜", "小龙虾", "生蚝", "螃蟹", "吃虾")),
    ("cafe", CAFE_TAGS, ("咖啡", "咖啡店", "咖啡馆", "拿铁", "美式咖啡", "冷萃")),
    ("tea_drink", TEA_DRINK_TAGS, ("奶茶", "茶饮", "果茶", "柠檬茶")),
    ("japanese", JAPANESE_TAGS, ("日料", "日本料理", "寿司", "刺身", "烧鸟", "居酒屋", "鳗鱼饭", "寿喜锅")),
]
SWEET_TAGS = {"甜品", "奶茶", "饮品", "咖啡", "蛋糕", "烘焙", "糖水", "冰品", "下午茶", "甜点"}
SWEET_PRIMARY_TAGS = {"甜品", "奶茶", "饮品", "蛋糕", "烘焙", "糖水", "冰品", "甜点"}
SWEET_PRIMARY_CUISINES = {"甜品", "奶茶饮品", "饮品", "咖啡", "咖啡甜点", "甜品饮品", "烘焙甜品"}
SWEET_FORBIDDEN_MAIN_TAGS = {
    "东北菜",
    "本帮菜",
    "川菜",
    "湘菜",
    "火锅",
    "烧烤",
    "冒菜",
    "盖饭",
    "烤肉",
    "面馆",
    "海鲜",
    "小龙虾",
    "日料",
    "寿司",
    "刺身",
    "烧肉",
    "麻辣烫",
}

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


def _travel_text(r: dict) -> str:
    meters = r.get("real_distance_m")
    walk = r.get("walk_minutes") or r.get("distance_min")
    if meters is not None:
        try:
            meters = float(meters)
        except (TypeError, ValueError):
            meters = None
    if walk is not None:
        try:
            walk = float(walk)
        except (TypeError, ValueError):
            walk = None
    if meters is not None and meters <= 1200:
        return f"步行{max(1, round(meters / 80))}分钟"
    if meters is None and walk is not None and walk <= 15:
        return f"步行{max(1, round(walk))}分钟"
    if meters is None and walk is None:
        return "距离待确认"
    km = (meters / 1000) if meters is not None else ((walk or 0) * 80 / 1000)
    if km < 2.2:
        return f"骑行约{max(6, round(km * 5 + 3))}分钟"
    subway = max(12, round(km * 4 + 8))
    drive = max(10, round(km * 3 + 6))
    return f"地铁约{subway}分钟 / 驾车约{drive}分钟"


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


def _is_sweet_candidate(rest: dict) -> bool:
    """甜口候选必须有甜品/饮品主身份，不能只靠“下午茶”场景标签命中。"""
    name = str(rest.get("name", ""))
    cuisine = str(rest.get("cuisine", ""))
    tags = {str(tag).strip() for tag in rest.get("tags", []) if str(tag).strip()}
    identity_text = " ".join([name, cuisine, " ".join(tags)])
    name_hits = ("奶茶", "甜品", "蛋糕", "糖水", "冰淇淋", "双皮奶", "芒果捞", "咖啡", "甜点", "烘焙")
    if cuisine in {"海鲜", "日料", "韩餐", "川菜", "湘菜", "火锅", "烧烤", "麻辣烫", "面食", "东北菜", "新疆菜"}:
        return cuisine in SWEET_PRIMARY_CUISINES or bool(tags & SWEET_PRIMARY_TAGS)
    return (
        cuisine in SWEET_PRIMARY_CUISINES
        or bool(tags & SWEET_PRIMARY_TAGS)
        or any(word in identity_text for word in name_hits)
    )


def _is_sweet_forbidden_main(rest: dict) -> bool:
    if _is_sweet_candidate(rest):
        return False
    return _match_tag(rest, SWEET_FORBIDDEN_MAIN_TAGS)


def _is_cool_candidate(rest: dict) -> bool:
    text = _restaurant_text(rest)
    if _match_tag(rest, COOL_FORBIDDEN_TAGS):
        return False
    return _match_tag(rest, COOL_TAGS) or any(word in text for word in ("冰", "冷", "凉", "清爽", "果茶", "冷萃"))


def _is_western_candidate(rest: dict) -> bool:
    return _match_tag(rest, WESTERN_TAGS)


def _match_fine_category(rest: dict, fine_category: str | None) -> bool:
    if fine_category == "hotpot":
        return _match_tag(rest, HOTPOT_TAGS)
    return True


def _append_unique(pref: dict, key: str, values: list[str] | set[str]) -> None:
    items = list(pref.get(key, []))
    for value in values:
        if value and value not in items:
            items.append(value)
    if items:
        pref[key] = items


def _detect_cuisine_from_text(text: str) -> tuple[str | None, set[str]]:
    for cuisine_key, tag_group, words in CUISINE_SYNONYMS:
        if any(word and word in text for word in words):
            return cuisine_key, set(tag_group)
    return None, set()


def _has_food_entity_signal(text: str) -> bool:
    if _detect_cuisine_from_text(text)[0]:
        return True
    return any(
        word in text
        for word in (
            "甜品", "蛋糕", "糖水", "冰淇淋", "冷饮", "冰饮", "凉面", "冷面",
            "轻食", "沙拉", "粥", "盖饭", "饭团", "早餐", "午饭", "晚饭", "夜宵",
        )
    )


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
    sweet_words = {"甜", "甜品", "蛋糕", "奶茶", "糖水", "冰淇淋", "下午茶", "咖啡甜点", "烘焙"}

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
        hard_avoid_sweet = any(k in text for k in ("不吃甜", "不要甜品", "别推甜品", "不想吃甜", "讨厌甜"))
        if hard_avoid_sweet:
            avoid_cuisines.add("sweet")
            avoid_tags.update(SWEET_TAGS)

    if positive and not negative:
        if any(k in text for k in spicy_words):
            liked_cuisines.add("spicy")
        if any(k in text for k in light_words):
            liked_cuisines.add("light")
        if any(k in text for k in fast_words):
            liked_cuisines.add("fast")
        if any(k in text for k in night_words):
            liked_cuisines.add("night")
        if any(k in text for k in sweet_words):
            liked_cuisines.add("sweet")

    mentioned_ids: list[int] = []
    for r in restaurants:
        name = r.get("name") or ""
        if name and name in text:
            mentioned_ids.append(r["id"])

    # 提取餐厅名中的关键词，做模糊匹配（比如"老北京炸酱面"能匹配到"炸酱面"相关的餐厅）
    if not mentioned_ids:
        for r in restaurants:
            name = r.get("name") or ""
            cuisine = r.get("cuisine") or ""
            tags = " ".join(r.get("tags", []) if isinstance(r.get("tags"), list) else [])
            text_clean = text.replace("感觉", "").replace("不太", "").replace("不太行", "").replace("不合适", "")
            words = [w for w in text_clean.split() if len(w) >= 2]
            if any(word and (word in name or word in cuisine or word in tags) for word in words):
                if r["id"] not in mentioned_ids:
                    mentioned_ids.append(r["id"])

    if mentioned_ids and negative:
        learned["avoid_restaurant_ids"] = mentioned_ids
    elif mentioned_ids and positive:
        learned["liked_restaurant_ids"] = mentioned_ids
    elif negative and recent_ids and any(k in text for k in ("这家", "这个", "刚才", "上一家", "换一家", "不行", "不合适", "不太行", "一般", "不喜欢")):
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
    if new_pref.get("reset_cuisine_context"):
        for key in ("cuisine", "fine_category", "liked_cuisines", "recent_recommendation_ids"):
            current.pop(key, None)
        current["context_reset_pending"] = True

    new_cuisine = new_pref.get("cuisine")
    if new_cuisine and new_cuisine != current.get("cuisine") and "fine_category" not in new_pref:
        current.pop("fine_category", None)
    if new_cuisine or new_pref.get("continue_previous_context"):
        current.pop("context_reset_pending", None)

    for k, v in new_pref.items():
        if v is not None and k not in {"reset_cuisine_context", "continue_previous_context"}:
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
        "sweet": "甜品/甜口",
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

    reset_context = bool(CONTEXT_RESET_PATTERN.search(text))
    if reset_context:
        pref["reset_cuisine_context"] = True
    if not reset_context and CONTEXT_CONTINUE_PATTERN.search(text):
        pref["continue_previous_context"] = True
    if OUT_OF_SCOPE_CATEGORY_PATTERN.search(text):
        pref["out_of_scope_category"] = "fruit" if any(k in text for k in ("水果", "果切", "鲜果", "买果")) else "non_restaurant"

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

    # business scenario
    if any(k in text for k in ("商务", "宴请", "应酬", "客户", "领导", "同事聚餐")):
        pref["business"] = True
        if not pref.get("budget"):
            pref["budget"] = 150
        if not pref.get("people"):
            pref["people"] = 6
        _append_unique(pref, "liked_tags", list(BUSINESS_TAGS))

    # dating scenario
    if any(k in text for k in ("约会", "纪念日", "求婚", "表白", "浪漫", "情调")):
        pref["dating"] = True
        if not pref.get("people"):
            pref["people"] = 2
        if not pref.get("budget"):
            pref["budget"] = 120
        _append_unique(pref, "liked_tags", list(DATE_TAGS))
        _append_unique(pref, "avoid_tags", list(FAST_TAGS))

    # parenting/family scenario
    if any(k in text for k in ("亲子", "带娃", "儿童", "宝宝", "家庭聚餐", "带爸妈", "老人")):
        pref["parenting"] = True
        if not pref.get("people"):
            pref["people"] = 4
        _append_unique(pref, "liked_tags", list(PARENTING_TAGS))

    # celebration scenario
    if any(k in text for k in ("生日", "圣诞", "新年", "情人节", "中秋", "国庆", "节日", "庆功宴", "谢师宴", "升学宴")):
        pref["celebration"] = True
        if not pref.get("people"):
            pref["people"] = 6
        _append_unique(pref, "liked_tags", list(CELEBRATION_TAGS))

    # health/nourishing scenario
    if any(k in text for k in ("养生", "滋补", "药膳", "养胃", "食疗")):
        pref["health"] = True
        pref["cuisine"] = "light"
        _append_unique(pref, "liked_tags", list(HEALTH_TAGS))
        _append_unique(pref, "avoid_tags", list(SPICY_TAGS))

    # season scenario
    if any(k in text for k in ("夏天", "解暑", "冬天", "暖胃", "秋冬进补", "冬季", "夏季")):
        pref["season"] = True
        if any(k in text for k in ("夏天", "解暑", "夏季")):
            pref["cuisine"] = "cool"
            _append_unique(pref, "liked_tags", list(COOL_TAGS))
            _append_unique(pref, "avoid_tags", list(COOL_FORBIDDEN_TAGS))
        else:
            _append_unique(pref, "liked_tags", list(HEALTH_TAGS))

    # team building scenario
    if any(k in text for k in ("团建", "年会", "公司聚餐")):
        pref["team_building"] = True
        if not pref.get("budget"):
            pref["budget"] = 100
        if not pref.get("people"):
            pref["people"] = 8
        _append_unique(pref, "liked_tags", list(GROUP_TAGS))

    # instagram/wanghong scenario
    if any(k in text for k in ("网红店", "打卡", "拍照", "氛围感", "仪式感")):
        pref["instagram"] = True
        _append_unique(pref, "liked_tags", list(INSTAGRAM_TAGS))

    # vegetarian scenario
    if any(k in text for k in ("素食", "素菜", "素", "清真")):
        pref["vegetarian"] = True
        _append_unique(pref, "liked_tags", list(VEGETARIAN_TAGS))
        _append_unique(pref, "avoid_tags", list(BARBECUE_TAGS | SEAFOOD_TAGS))

    # local/old brand scenario
    if any(k in text for k in ("老字号", "本地特色", "必吃榜", "米其林", "黑珍珠")):
        pref["local"] = True
        _append_unique(pref, "liked_tags", list(LOCAL_TAGS))

    # afternoon tea scenario
    if any(k in text for k in ("下午茶", "早茶")):
        pref["afternoon_tea"] = True
        pref["cuisine"] = "sweet"
        _append_unique(pref, "liked_tags", list(AFTERNOON_TEA_TAGS))

    # luxury scenario
    if any(k in text for k in ("高档", "奢华", "高端", "米其林", "黑珍珠")):
        pref["luxury"] = True
        if not pref.get("budget"):
            pref["budget"] = 200
        _append_unique(pref, "liked_tags", list(LUXURY_TAGS))

    # budget value scenario
    if any(k in text for k in ("性价比", "实惠", "便宜", "平价")):
        pref["budget_sensitive"] = True
        pref["price_sensitivity"] = "high"
        _append_unique(pref, "liked_tags", list(BUDGET_TAGS))

    # location hint
    if LOC_PATTERN.search(text):
        pref["location_hint"] = True

    # cuisine tag
    detected_cuisine, detected_tags = _detect_cuisine_from_text(text)
    if detected_cuisine:
        pref["cuisine"] = detected_cuisine
        if detected_cuisine == "hotpot":
            pref["fine_category"] = "hotpot"
        _append_unique(pref, "liked_tags", detected_tags)

    sweet_words = ("甜", "甜品", "蛋糕", "奶茶", "糖水", "冰淇淋", "冰品", "下午茶", "咖啡甜点", "烘焙")
    cool_words = ("凉的", "冰的", "冷的", "冰一点", "冰一点的", "凉快", "冷饮", "冰饮", "冰品", "凉面", "冷面", "清爽一点", "清爽降温", "降温", "适合夏天", "不热不腻", "不想吃热", "别太热")
    no_spicy = any(k in text for k in ("不辣", "不要辣", "不吃辣", "别太辣", "不能吃辣"))
    no_japanese = bool(re.search(r"(不是|不要|别|不想|排除).{0,8}(日料|寿司|刺身|烧肉)", text))
    if no_spicy:
        _append_unique(pref, "avoid_tags", list(SPICY_TAGS | {"麻辣", "重辣"}))
    if not pref.get("cuisine") and any(k in text for k in sweet_words):
        pref["cuisine"] = "sweet"
    if not pref.get("cuisine") and any(k in text for k in cool_words):
        pref["cuisine"] = "cool"
        _append_unique(pref, "liked_tags", list(COOL_TAGS))
        _append_unique(pref, "avoid_tags", list(COOL_FORBIDDEN_TAGS))
        if any(k in text for k in ("当一餐", "吃饱", "正餐", "一顿", "能饱", "饱一点")):
            pref["cool_meal"] = True
    if not pref.get("cuisine") and not no_spicy and any(k in text for k in ("辣", "川菜", "湘菜", "重庆")):
        pref["cuisine"] = "spicy"
    if not pref.get("cuisine") and any(k in text for k in ("轻食", "健康", "减脂", "沙拉", "低卡", "清淡", "少油", "少盐")):
        pref["cuisine"] = "light"
    if any(k in text for k in ("孕妇", "生冷", "少油", "少盐", "清淡")):
        _append_unique(pref, "avoid_tags", list(SPICY_TAGS | {"刺身", "生食", "烧烤", "麻辣", "小龙虾"}))
    if not pref.get("cuisine") and not no_japanese and any(k in text for k in ("日料", "寿司", "拉面")):
        pref["cuisine"] = "japanese"
    if not pref.get("cuisine") and any(k in text for k in ("快", "赶时间", "课间", "马上")):
        pref["cuisine"] = "fast"
    if not pref.get("cuisine") and any(k in text for k in ("宵夜", "深夜", "晚上 10", "晚上 11", "凌晨")):
        pref["cuisine"] = "night"

    return pref


def _product_feature_reply(message: str, agent_mode: str = "normal_agent") -> str | None:
    wants_how = bool(
        PRODUCT_PROBLEM_PATTERN.search(message)
        or PRODUCT_CONTEXT_PATTERN.search(message)
        or WHY_HOW_PATTERN.search(message)
        or any(k in message for k in ("是什么", "怎么", "如何", "入口", "在哪", "有什么用", "是不是", "区别", "一样", "合并", "同步"))
    )
    is_food_request = bool(FOOD_REQUEST_PATTERN.search(message))
    is_map_rerank = agent_mode == "map_agent" and bool(MAP_RERANK_PATTERN.search(message))
    if is_map_rerank:
        return None
    product_only = not is_food_request
    if PRODUCT_COMMUNITY_PATTERN.search(message) and (wants_how or (product_only and not is_map_rerank)):
        return (
            "社区圈是看附近真实反馈和探店内容的地方，不等同于餐厅推荐卡片。"
            "你可以在顶部“社区圈”进入，按当前社区/行政区看热帖、评价和大家提到的餐厅；"
            "如果你想发帖，可以写探店体验、排队情况、适合人群或避雷点。要我推荐时，再告诉我预算、口味和位置。"
        )
    if PRODUCT_AGENT_MODE_PATTERN.search(message) and (wants_how or product_only):
        return (
            "普通小觅更像需求分析入口：先通过多轮对话弄清口味、预算、人数、情绪和场景，再用卡片流承接。"
            "地图小觅更偏空间决策：结合定位、搜索地点、下一站、地铁/商场/展会/停车等点位，把餐厅放到地图上比较路线。"
        )
    if PRODUCT_WISHLIST_PATTERN.search(message) and (wants_how or product_only):
        return (
            "心愿单就是统一后的收藏入口：餐厅卡片、帖子里的餐厅、小觅推荐卡和地图点位都可以加入。"
            "打开心愿单后可以查看列表、移出餐厅、逐个勾选加入地图，也可以一键规划，把想去的店放到地图上比较路线。"
        )
    if PRODUCT_PRIVACY_PATTERN.search(message) and (wants_how or product_only):
        return (
            "定位主要用于帮你计算附近餐厅、地图点位和路线便利性；不开定位也可以手动搜索地点。"
            "我不会把“未说明用途的问题”硬转成餐厅推荐。如果你担心隐私，可以只用搜索地点或行政区筛选。"
        )
    if PRODUCT_REVIEW_PATTERN.search(message) and (wants_how or product_only):
        return (
            "评价和评论主要在餐厅详情页、社区圈里承接。你可以查看评价、发探店反馈、点赞互动；"
            "如果内容不合适，应该进入举报/审核流程，避免影响其他用户判断。"
        )
    if PRODUCT_DATA_PATTERN.search(message) and (wants_how or product_only):
        return (
            "餐厅数据会受覆盖区域、标签质量和更新时间影响，所以价格、营业时间、评分可能需要用户反馈继续校正。"
            "如果发现地址、电话、菜单或标签不准，可以直接告诉我“哪家店哪里错了”，我会把它作为纠错信号，而不是继续硬推。"
        )
    if PRODUCT_MAP_PATTERN.search(message) and (wants_how or product_only):
        if agent_mode == "map_agent":
            return (
                "全屏地图页可以做空间选择：先定位或搜索地点，再让小觅按预算、口味、下一站和交通方式筛餐厅。"
                "你也可以让我标地铁站、商场、展会、停车点或回家方向；等需求明确后，我会更新地图点位并按路线帮你比较。"
            )
        return (
            "地图适合处理“位置和下一步安排”。你可以从小觅推荐或心愿单跳到全屏地图，"
            "再问“吃完去地铁”“附近商场里解决”“把心愿单放地图上比较”。普通对话里我会先帮你筛方向。"
        )
    if PRODUCT_DETAIL_PATTERN.search(message) and (wants_how or product_only):
        return (
            "餐厅详情页用来看菜单、评价、地址、营业时间和心愿单状态。"
            "你可以从首页餐厅卡、帖子餐厅、小觅推荐卡或地图点位进入详情；如果觉得推荐不准，也可以告诉我哪点不合适，我会重筛。"
        )
    if PRODUCT_ACCOUNT_PATTERN.search(message) and (wants_how or product_only):
        return (
            "账号和个人页主要用于同步心愿单、查看评价记录和管理个人信息。"
            "未登录时也可以浏览和对话；登录后可以同步心愿单、查看自己的评价记录，社区互动也会更完整。"
        )
    if PRODUCT_ERROR_PATTERN.search(message) and (wants_how or product_only):
        return (
            "如果页面加载慢、地图空白或按钮没反应，可以先刷新页面、确认后端和地图服务是否启动，再检查定位/网络权限。"
            "如果是小觅响应慢，通常和模型接口或网络有关；这时我会尽量走本地规则兜底，但不会乱推无关餐厅。"
        )
    if PRODUCT_MERCHANT_PATTERN.search(message) and (wants_how or product_only):
        return (
            "新增餐厅、补充菜单、修改地址电话这类属于数据维护/商家信息流程。"
            "你可以提供店名、地址、菜系、人均、标签和坐标，我会优先把它当作数据补充需求，而不是立刻推荐餐厅。"
        )
    if PRODUCT_BOUNDARY_PATTERN.search(message) and (wants_how or product_only):
        return (
            "这部分目前更适合做跳转或提示：觅食主要负责推荐、地图规划、社区反馈和心愿单管理。"
            "外卖下单、支付、订座、打车和人工客服暂不作为核心闭环，我会先说明边界，再给你可行的下一步。"
        )
    if PRODUCT_FEEDBACK_PATTERN.search(message) and (wants_how or product_only):
        return (
            "如果推荐不准，你可以直接指出偏差：太贵、太远、不吃某类、想保留哪家、要换口味或换地点。"
            "我会把这些当成偏好记住，重新筛选；在地图页还可以问我要不要清空旧点位、保留心愿单里的店或按下一站重排。"
        )
    if PRODUCT_GENERAL_PATTERN.search(message) and (wants_how or product_only):
        return (
            "觅食不只是推荐餐厅，还包括四块：小觅 Agent 帮你分析需求，全屏地图帮你做路线和空间选择，"
            "社区圈看附近真实探店和热帖，心愿单负责收藏、批量加入地图和一键规划。"
            "你可以问我社区圈怎么玩、心愿单怎么规划，或直接说你的吃饭需求。"
        )
    return None


def _meta_reply(message: str, agent_mode: str = "normal_agent") -> str | None:
    if META_IDENTITY_PATTERN.search(message):
        return (
            "我是小觅，帮你把“想吃什么”和“去哪更顺路”一起想清楚的美食助手。"
            "你可以直接说口味、预算、人数、位置和吃完后的安排，比如“附近30以内清淡点，吃完去地铁”。"
        )
    product_reply = _product_feature_reply(message, agent_mode)
    if product_reply:
        return product_reply
    if META_HELP_PATTERN.search(message):
        if any(k in message for k in ("能做什么", "可以做什么", "会做什么", "帮我做什么", "还能干嘛")):
            return (
                "我是小觅，可以帮你做四类事：先聊清楚吃饭需求，再推荐餐厅；"
                "把候选放到地图上比较距离、地铁、商场和下一站；管理心愿单并一键规划；"
                "也能解释社区圈、餐厅详情和推荐依据。你随便问也行，我会先判断该回答功能、追问需求，还是进入推荐。"
            )
        if agent_mode == "map_agent":
            return (
                "在地图页你可以这样问：附近预算30、吃完去2号线、心愿单放地图比较、带小孩找商场、下雨少走露天。"
                "我会结合位置、路线、地铁/商场等点位帮你收窄。"
            )
        return (
            "你可以按“位置 + 预算 + 口味 + 人数 + 场景/下一步”来问我。"
            "例如：我想吃甜的、附近能坐；不吃辣预算30；三个人聚餐人均80；吃完要去地铁。"
        )
    if META_TRUST_PATTERN.search(message):
        return (
            "我会综合餐厅标签、价格、人均、距离、评分、社区热度和你刚说的偏好来排。"
            "如果你指出“不准/太贵/太远/不是这个口味”，我会把它当成偏好记住并重新筛。"
        )
    return None


def _pref_cuisine_label(value: str | None) -> str:
    labels = {
        "hotpot": "火锅",
        "sweet": "甜品/甜口",
        "spicy": "辣味/重口",
        "light": "清淡/轻食",
        "cool": "冷食/冰饮",
        "western": "西餐",
        "japanese": "日料",
        "korean": "韩餐",
        "thai": "泰餐",
        "xinjiang": "新疆菜",
        "northeast": "东北菜",
        "shanghai": "本帮/上海菜",
        "cantonese": "粤菜/茶餐厅",
        "barbecue": "烧烤/烤肉",
        "noodles": "粉面",
        "cafe": "咖啡办公",
        "seafood": "海鲜",
        "tea_drink": "茶饮/奶茶",
        "fast": "快餐",
        "night": "夜宵",
    }
    return labels.get(value or "", value or "之前的口味")


def _clarifying_reply(
    message: str,
    pref: dict,
    new_pref: dict | None = None,
    previous_pref: dict | None = None,
) -> str | None:
    if pref.get("agent_mode") == "map_agent" and any(word in message for word in ("下一步", "后续", "方便下一步")):
        return (
            "我先不急着换地图点位。你说的“下一步”更像是哪种：去地铁、去商场、找地方自习/办公、回家，还是见朋友？"
            "我确认后会把餐厅、路线和关键点位一起放到地图上比较。"
        )
    new_pref = new_pref or {}
    previous_pref = previous_pref or {}
    vague = bool(VAGUE_NEED_PATTERN.search(message))
    new_has_cuisine = any(new_pref.get(key) for key in ("cuisine", "fine_category"))
    previous_cuisine = previous_pref.get("cuisine")
    if vague and previous_cuisine and not new_has_cuisine:
        place = "你刚提到的新位置附近" if new_pref.get("location_hint") else "这次"
        return (
            f"我记得上一轮你在看{_pref_cuisine_label(previous_cuisine)}，但{place}你又说“不知道吃什么”。"
            f"要继续按{_pref_cuisine_label(previous_cuisine)}在新位置附近筛，还是这轮重启口味？"
            "你也可以直接告诉我想偏清淡、甜口、快餐、聚餐，或预算/距离要求。"
        )
    has_concrete_need = any(new_pref.get(key) for key in ("cuisine", "budget", "people", "location_hint", "fine_category"))
    if vague and not has_concrete_need:
        return (
            "我先不硬塞餐厅卡片，咱们把范围缩小一点。"
            "你现在更想要哪一种：快速吃饱、清淡舒服、想吃点甜的、多人聚餐，还是找个能坐一会儿的地方？"
        )
    return None


def _has_product_signal(message: str) -> bool:
    return any(pattern.search(message) for pattern in PRODUCT_PATTERNS)


def _classify_intent(
    message: str,
    agent_mode: str,
    new_pref: dict,
    previous_pref: dict,
    current_pref: dict,
) -> IntentFrame:
    """Step 1: classify user intent before any recommendation is generated."""
    has_food_request = bool(FOOD_REQUEST_PATTERN.search(message) or _has_food_entity_signal(message))
    has_concrete_food_need = any(
        new_pref.get(key) for key in ("cuisine", "budget", "people", "location_hint", "fine_category")
    )
    has_product_signal = _has_product_signal(message)
    is_map_rerank = agent_mode == "map_agent" and bool(MAP_RERANK_PATTERN.search(message))
    has_lifestyle_signal = bool(DAILY_LIFE_PATTERN.search(message))
    reasons: list[str] = []

    if _meta_reply(message, agent_mode):
        return IntentFrame(
            primary="meta_or_product_help",
            action="answer",
            confidence=0.95,
            reasons=["matched_meta_or_product_pattern"],
        )

    # 上下文感知：如果上一轮是推荐餐厅，且这一轮有负反馈，应该继续推荐而不是兜底
    last_intent = current_pref.get("last_intent", {})
    has_recommendation_context = last_intent.get("action") == "recommend" or last_intent.get("primary") == "food_recommendation"
    has_negative_feedback = bool(NEGATIVE_PATTERN.search(message))
    has_followup_signal = any(
        k in message for k in ("换", "再", "还有", "其他", "别的", "重新", "换个", "换一家", "再看看", "不太", "不太行", "不合适", "一般", "不喜欢")
    )
    if has_recommendation_context and (has_negative_feedback or has_followup_signal):
        return IntentFrame(
            primary="feedback_and_recontinue",
            action="recommend",
            confidence=0.88,
            reasons=["negative_feedback_in_recommendation_context"],
        )

    if new_pref.get("out_of_scope_category"):
        return IntentFrame(
            primary="out_of_scope_category",
            action="fallback",
            confidence=0.95,
            slots={"category": new_pref.get("out_of_scope_category")},
            reasons=["requested_category_not_in_restaurant_database"],
        )
    if current_pref.get("context_reset_pending") and not any(new_pref.get(key) for key in ("cuisine", "fine_category")):
        return IntentFrame(
            primary="context_reset_needs_new_need",
            action="clarify",
            confidence=0.9,
            reasons=["user_reset_previous_context_without_new_food_need"],
        )
    if is_map_rerank:
        return IntentFrame(
            primary="map_rerank_or_spatial_planning",
            action="recommend",
            confidence=0.9,
            reasons=["map_agent_spatial_sort_signal"],
        )
    if has_product_signal and not has_food_request:
        return IntentFrame(
            primary="product_help",
            action="answer",
            confidence=0.85,
            reasons=["product_signal_without_food_request"],
        )
    if has_lifestyle_signal and not (has_food_request or has_concrete_food_need):
        return IntentFrame(
            primary="lifestyle_planning_unclear",
            action="clarify",
            confidence=0.78,
            reasons=["daily_life_signal_without_clear_food_request"],
        )
    if VAGUE_NEED_PATTERN.search(message) and not any(new_pref.get(key) for key in ("cuisine", "fine_category")):
        previous_cuisine = previous_pref.get("cuisine")
        if previous_cuisine and not any(new_pref.get(key) for key in ("cuisine", "fine_category")):
            return IntentFrame(
                primary="vague_food_need_with_memory",
                action="clarify",
                confidence=0.9,
                slots={"previous_cuisine": previous_cuisine},
                reasons=["vague_need_may_continue_or_reset_previous_context"],
            )
        return IntentFrame(
            primary="vague_food_need",
            action="clarify",
            confidence=0.82,
            reasons=["food_need_is_too_open"],
        )
    if has_concrete_food_need or has_food_request:
        if new_pref.get("cuisine"):
            reasons.append(f"cuisine:{new_pref['cuisine']}")
        if new_pref.get("fine_category"):
            reasons.append(f"fine_category:{new_pref['fine_category']}")
        return IntentFrame(
            primary="food_recommendation",
            action="recommend",
            confidence=0.86,
            slots={k: v for k, v in new_pref.items() if v},
            reasons=reasons or ["food_request_signal"],
        )
    if SMALL_TALK_PATTERN.search(message):
        return IntentFrame(
            primary="small_talk_or_opening",
            action="clarify",
            confidence=0.72,
            reasons=["small_talk_without_task"],
        )
    return IntentFrame(
        primary="unclear_non_food",
        action="clarify",
        confidence=0.62,
        reasons=["no_reliable_food_or_product_signal"],
    )


def _intent_clarification_reply(intent: IntentFrame, message: str) -> str:
    if intent.primary == "lifestyle_planning_unclear":
        return (
            "我先不硬推餐厅。你这句更像是在说今天的状态或后续安排。"
            "你想让我帮你安排“吃什么”，还是一起规划吃完去哪儿？"
            "可以补一句：预算、位置、想安静/热闹、要不要近地铁或商场。"
        )
    if intent.primary == "small_talk_or_opening":
        return (
            "我在～我是小觅，可以帮你选吃的，也可以讲清楚社区圈、心愿单和地图怎么用。"
            "你可以直接说“附近30以内清淡点”，也可以问“心愿单怎么规划到地图”。"
        )
    return (
        "我先不直接推餐厅，避免又给你兜底错方向。"
        "你现在是想了解产品功能，比如社区圈、心愿单、地图怎么用；"
        "还是想让我帮你选吃的？如果是选吃的，可以告诉我口味、预算、位置或人数。"
    )


def _decide_conversation(
    message: str,
    agent_mode: str,
    new_pref: dict,
    previous_pref: dict,
    current_pref: dict,
) -> tuple[ConversationDecision, IntentFrame]:
    intent = _classify_intent(message, agent_mode, new_pref, previous_pref, current_pref)
    if intent.action == "answer":
        meta = _meta_reply(message, agent_mode) or _intent_clarification_reply(intent, message)
        return ConversationDecision(
            action="answer",
            reply=meta,
            allow_recommendations=False,
            clear_recent=True,
            reason=intent.primary,
        ), intent

    if intent.primary == "out_of_scope_category":
        if new_pref["out_of_scope_category"] == "fruit":
            reply = (
                "水果/果切这类目前不在餐厅推荐库里，我先不硬凑餐厅卡片。"
                "你可以换成我能稳定推荐的方向：附近甜品/奶茶、咖啡甜点、轻食，"
                "或者告诉我具体地点，我帮你按“商超/便利店/水果店”思路做地图搜索兜底。"
            )
        else:
            reply = (
                "这个需求更像非餐厅服务，目前不在餐厅库的稳定收录范围里，我不直接生成餐厅卡片。"
                "你可以告诉我地点，我帮你转成附近商超/便利店/生活服务的搜索思路，或改成餐饮口味继续筛。"
            )
        return ConversationDecision(
            action="fallback",
            reply=reply,
            allow_recommendations=False,
            clear_recent=False,
            reason=intent.primary,
        ), intent

    if intent.primary == "context_reset_needs_new_need":
        return ConversationDecision(
            action="clarify",
            reply=(
                "好，我们这轮先不按上一轮口味走。"
                "你现在更想要哪种方向：清淡舒服、甜口饮品、快速吃饱、多人聚餐，还是找个能坐一会儿的地方？"
            ),
            allow_recommendations=False,
            clear_recent=True,
            reason=intent.primary,
        ), intent

    if intent.action == "clarify" and intent.primary not in {"vague_food_need", "vague_food_need_with_memory"}:
        return ConversationDecision(
            action="clarify",
            reply=_intent_clarification_reply(intent, message),
            allow_recommendations=False,
            clear_recent=False,
            reason=intent.primary,
        ), intent

    clarify = _clarifying_reply(message, current_pref, new_pref, previous_pref)
    if clarify:
        return ConversationDecision(
            action="clarify",
            reply=clarify,
            allow_recommendations=False,
            reason="need_more_information",
        ), intent

    return ConversationDecision(action="recommend", reason=intent.primary), intent


def _pick_candidates(restaurants: list[dict], pref: dict, location: tuple | None, limit: int = 5) -> list[dict]:
    """基于偏好打分 + 排序，返回 limit 个候选餐厅。"""
    avoid_ids = {int(x) for x in pref.get("avoid_restaurant_ids", [])}
    if avoid_ids:
        restaurants = [r for r in restaurants if int(r.get("id") or 0) not in avoid_ids]
        if not restaurants:
            return []

    fine_category = pref.get("fine_category")
    if fine_category:
        exact_pool = [r for r in restaurants if _match_fine_category(r, fine_category)]
        if exact_pool:
            restaurants = exact_pool
        else:
            return []

    if pref.get("cuisine") == "sweet":
        sweet_pool = [r for r in restaurants if _is_sweet_candidate(r) and not _is_sweet_forbidden_main(r)]
        if sweet_pool:
            restaurants = sweet_pool
        else:
            return []

    if pref.get("cuisine") == "cool":
        cool_pool = [r for r in restaurants if _is_cool_candidate(r)]
        if cool_pool:
            restaurants = cool_pool
        else:
            return []

    if pref.get("cuisine") == "western":
        western_pool = [r for r in restaurants if _is_western_candidate(r)]
        if western_pool:
            restaurants = western_pool
        else:
            return []

    cuisine_group = CUISINE_TAG_GROUPS.get(pref.get("cuisine"))
    if cuisine_group and pref.get("cuisine") != "western":
        cuisine_pool = [r for r in restaurants if _match_tag(r, cuisine_group)]
        if cuisine_pool:
            restaurants = cuisine_pool
        else:
            return []

    def score(r: dict) -> tuple:
        s = 0.0
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
        # business scenario
        if pref.get("business"):
            if _match_tag(r, BUSINESS_TAGS):
                s += 20
            if _match_tag(r, FAST_TAGS):
                s -= 30
            if _match_tag(r, {"小吃", "路边摊", "大排档", "夜市"}):
                s -= 25
            pmin = r.get("price_min") or 0
            if pmin >= 80:
                s += 10
        # dating scenario
        if pref.get("dating"):
            if _match_tag(r, DATE_TAGS):
                s += 15
            if _match_tag(r, FAST_TAGS):
                s -= 25
            pmin = r.get("price_min") or 0
            if pmin >= 60:
                s += 8
        # parenting/family scenario
        if pref.get("parenting"):
            if _match_tag(r, PARENTING_TAGS):
                s += 15
            if _match_tag(r, SPICY_TAGS):
                s -= 15
        # celebration scenario
        if pref.get("celebration"):
            if _match_tag(r, CELEBRATION_TAGS):
                s += 12
            if _match_tag(r, GROUP_TAGS):
                s += 10
        # health/nourishing scenario
        if pref.get("health"):
            if _match_tag(r, HEALTH_TAGS):
                s += 15
            if _match_tag(r, SPICY_TAGS):
                s -= 25
        # instagram/wanghong scenario
        if pref.get("instagram"):
            if _match_tag(r, INSTAGRAM_TAGS):
                s += 15
            if _match_tag(r, {"快餐", "小吃", "路边摊"}):
                s -= 15
        # vegetarian scenario
        if pref.get("vegetarian"):
            if _match_tag(r, VEGETARIAN_TAGS):
                s += 20
            if _match_tag(r, BARBECUE_TAGS | SEAFOOD_TAGS):
                s -= 30
        # local/old brand scenario
        if pref.get("local"):
            if _match_tag(r, LOCAL_TAGS):
                s += 15
        # luxury scenario
        if pref.get("luxury"):
            if _match_tag(r, LUXURY_TAGS):
                s += 20
            pmin = r.get("price_min") or 0
            if pmin >= 150:
                s += 15
        # team building scenario
        if pref.get("team_building"):
            if _match_tag(r, GROUP_TAGS):
                s += 15
            if _match_tag(r, BUSINESS_TAGS):
                s += 10
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
        if "sweet" in avoid_cuisines and _match_tag(r, SWEET_TAGS):
            s -= 35
        if "cool" in avoid_cuisines and _match_tag(r, COOL_TAGS):
            s -= 35
        if "spicy" in liked_cuisines and _match_tag(r, SPICY_TAGS):
            s += 10
        if "light" in liked_cuisines and _match_tag(r, LIGHT_TAGS):
            s += 10
        if "fast" in liked_cuisines and _match_tag(r, FAST_TAGS):
            s += 8
        if "night" in liked_cuisines and _match_tag(r, NIGHT_TAGS):
            s += 8
        if "sweet" in liked_cuisines and _match_tag(r, SWEET_TAGS):
            s += 12
        if "cool" in liked_cuisines and _match_tag(r, COOL_TAGS):
            s += 12
        if "western" in liked_cuisines and _match_tag(r, WESTERN_TAGS):
            s += 12
        for cuisine_key, tag_group in CUISINE_TAG_GROUPS.items():
            if cuisine_key in liked_cuisines and _match_tag(r, tag_group):
                s += 12
        if cuisine == "spicy" and _match_tag(r, SPICY_TAGS):
            s += 15
        if cuisine == "light" and _match_tag(r, LIGHT_TAGS):
            s += 15
        if cuisine == "fast" and _match_tag(r, FAST_TAGS):
            s += 15
        if cuisine == "night" and _match_tag(r, NIGHT_TAGS):
            s += 15
        if cuisine == "hotpot" and _match_tag(r, HOTPOT_TAGS):
            s += 25
        if cuisine == "western" and _match_tag(r, WESTERN_TAGS):
            s += 35
        if cuisine in CUISINE_TAG_GROUPS and cuisine != "western" and _match_tag(r, CUISINE_TAG_GROUPS[cuisine]):
            s += 35
        if cuisine == "sweet":
            if _is_sweet_candidate(r):
                s += 45
            if _is_sweet_forbidden_main(r):
                s -= 120
        if cuisine == "cool":
            if _is_cool_candidate(r):
                s += 45
            if _match_tag(r, COOL_FORBIDDEN_TAGS):
                s -= 120
            if pref.get("cool_meal"):
                if _match_tag(r, {"凉面", "冷食", "沙拉", "轻食"}):
                    s += 28
                if _match_tag(r, {"饮品", "奶茶", "咖啡", "冰品", "糖水"}) and not _match_tag(r, {"凉面", "冷食", "沙拉", "轻食"}):
                    s -= 18
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
    if pref.get("business"):
        return "商务场景匹配度高，环境雅致有包厢，适合宴请客户或同事聚餐。"
    if pref.get("dating"):
        return "约会氛围拉满，环境浪漫有情调，适合表白或纪念日。"
    if pref.get("parenting"):
        return "亲子友好，有儿童餐或游乐区，适合带娃家庭聚餐。"
    if pref.get("celebration"):
        return "适合庆祝节日或生日，氛围热闹，菜品丰富。"
    if pref.get("health"):
        return "养生滋补，口味清淡，适合养胃或调理身体。"
    if pref.get("instagram"):
        return "颜值超高，氛围感拉满，出片率百分百。"
    if pref.get("vegetarian"):
        return "素食友好，菜品丰富，适合素食主义者。"
    if pref.get("local"):
        return "本地特色或老字号，味道正宗，值得一试。"
    if pref.get("luxury"):
        return "高端精致，服务周到，适合重要场合或犒劳自己。"
    if pref.get("team_building"):
        return "适合团队聚餐，氛围轻松，方便交流。"
    if pref.get("distance_sensitivity") == "high":
        return "距离优先，少绕路，适合现在就去。"
    if pref.get("price_sensitivity") == "high":
        return "价格更稳，适合想控制预算又不想踩雷。"
    if pref.get("cuisine") == "light" or "light" in set(pref.get("liked_cuisines", [])):
        return "口味更清爽，吃完不容易犯困。"
    if pref.get("cuisine") == "cool" or "cool" in set(pref.get("liked_cuisines", [])):
        return "更偏凉爽、清口或冰饮方向，避开热汤热炒。"
    if pref.get("cuisine") == "sweet" or "sweet" in set(pref.get("liked_cuisines", [])):
        return "甜口匹配度高，适合饭后甜点、下午茶或想轻松坐一会儿。"
    if pref.get("cuisine") == "western" or "western" in set(pref.get("liked_cuisines", [])):
        return "西餐方向匹配度更高，适合想吃意面、披萨、牛排或轻松坐一会儿。"
    cuisine_labels = {
        "korean": "韩餐方向更明确，优先看韩式烤肉、部队锅、拌饭这类匹配项。",
        "thai": "泰餐方向更明确，优先看冬阴功、咖喱和泰式主食。",
        "xinjiang": "新疆菜方向更明确，优先看大盘鸡、手抓饭、烤包子和羊肉串。",
        "northeast": "东北菜方向更明确，适合想吃锅包肉、铁锅炖或分量足的家常菜。",
        "shanghai": "本帮/上海菜方向更明确，优先看本地口味和稳定家常菜。",
        "cantonese": "粤菜/茶餐厅方向更明确，优先看港式、烧腊、早茶和云吞面。",
        "barbecue": "烧烤/烤肉方向更明确，适合想吃重烟火气或多人一起点。",
        "noodles": "粉面方向更明确，优先看面馆、米线、汤面和拌面。",
        "cafe": "咖啡办公方向更明确，优先看安静、插座和能坐一会儿。",
        "seafood": "海鲜方向更明确，优先看海鲜、小龙虾、生蚝这类候选。",
        "tea_drink": "茶饮方向更明确，优先看奶茶、果茶和冷饮。",
    }
    if pref.get("cuisine") in cuisine_labels:
        return cuisine_labels[pref["cuisine"]]
    if pref.get("people") and pref["people"] >= 4:
        return "适合多人一起点，选择多，分摊下来更舒服。"
    return f"{tags}匹配度高，评分和距离都比较稳。"


def _recommendation_intro(message: str, pref: dict, picks: list[dict]) -> str:
    """Generate a human-sounding analysis intro while keeping cards aligned."""
    cuisine = pref.get("cuisine")
    tags = "、".join((picks[0].get("tags") or [])[:2]) if picks else ""
    map_suffix = "，再结合地图距离和路线筛：" if pref.get("agent_mode") == "map_agent" else "："
    if cuisine == "sweet":
        return "你这句核心是想吃甜的，我先把正餐类排除，优先看甜品、奶茶、咖啡甜点和能坐一会儿的店" + map_suffix
    if cuisine == "cool":
        return "你想要凉一点、清爽一点的，我先避开热汤热炒，优先筛冷饮、冰品、凉面和轻食" + map_suffix
    if cuisine == "hotpot":
        return "你明确想吃火锅，我就不混推别的品类了，先按锅底选择、价格和距离筛" + map_suffix
    if cuisine == "spicy":
        return "你偏向辣口，我按重口味匹配度、距离和评分综合看" + map_suffix
    if cuisine == "light":
        return "你更想吃清淡舒服一点的，我优先看少油、轻食和吃完不负担的选择" + map_suffix
    if cuisine == "western":
        return "你明确想吃西餐，我先把中餐、海鲜和日料这类排开，按西式简餐、意面、披萨、牛排筛" + map_suffix
    cuisine_intro = {
        "korean": "你想吃韩餐，我先按韩式烤肉、部队锅、石锅拌饭这些方向筛，不混推其他菜系：",
        "thai": "你想吃泰餐，我先按冬阴功、咖喱、泰式主食和距离评分筛：",
        "xinjiang": "你想吃新疆菜，我先按大盘鸡、手抓饭、烤包子、羊肉串这类匹配项筛：",
        "northeast": "你想吃东北菜，我先按锅包肉、铁锅炖、饺子和分量感来筛：",
        "shanghai": "你想吃本帮/上海菜，我先按本地口味、家常稳定度和距离评分筛：",
        "cantonese": "你想吃粤菜或茶餐厅，我先按港式、烧腊、早茶、云吞面这类方向筛：",
        "barbecue": "你想吃烧烤/烤肉，我先按烟火气、适合多人和距离评分筛：",
        "noodles": "你想吃粉面，我先按面馆、米线、汤面、拌面这些更对口的候选筛：",
        "cafe": "你想找咖啡或能坐会儿的地方，我先按安静、插座、可办公和距离筛：",
        "seafood": "你想吃海鲜，我先按海鲜、小龙虾、生蚝这类候选筛，不混推普通正餐：",
        "tea_drink": "你想喝茶饮/奶茶，我先按饮品、果茶、冷饮方向筛，不混推正餐：",
    }
    if cuisine in cuisine_intro:
        return cuisine_intro[cuisine].rstrip("：") + map_suffix
    if pref.get("business"):
        return f"商务宴请场景，我优先看环境、私密性、包厢和人均预算（默认¥150），筛了几家适合招待客户或领导的："
    if pref.get("dating"):
        return f"约会场景，我优先看浪漫氛围、环境和人均预算（默认¥120），筛了几家适合表白或纪念日的："
    if pref.get("parenting"):
        return f"亲子家庭场景，我优先看儿童友好、环境安全和菜品丰富度，筛了几家适合带娃聚餐的："
    if pref.get("celebration"):
        return f"节日庆祝场景，我优先看氛围、菜品丰富和适合多人，筛了几家适合生日或节日聚餐的："
    if pref.get("health"):
        return f"养生滋补场景，我优先看清淡养胃、药膳滋补和健康食材，筛了几家适合调理身体的："
    if pref.get("instagram"):
        return f"网红打卡场景，我优先看颜值、氛围感和出片率，筛了几家适合拍照发圈的："
    if pref.get("vegetarian"):
        return f"素食场景，我优先看素食友好、菜品丰富和健康食材，筛了几家适合素食主义者的："
    if pref.get("local"):
        return f"本地特色场景，我优先看老字号、本地风味和地道口味，筛了几家值得一试的："
    if pref.get("luxury"):
        return f"高端奢华场景，我优先看精致环境、高端食材和人均预算（默认¥200），筛了几家适合重要场合的："
    if pref.get("team_building"):
        return f"团队建设场景，我优先看适合多人、氛围轻松和菜品丰富，筛了几家适合公司聚餐的："
    if pref.get("season"):
        if any(k in message for k in ("夏天", "解暑", "夏季")):
            return f"夏季场景，我优先看清爽解暑、冷饮冰品和适合夏天的菜品："
        else:
            return f"冬季场景，我优先看暖胃滋补、热汤热菜和适合冬天的菜品："
    if pref.get("agent_mode") == "map_agent":
        if pref.get("location_hint") or "附近" in message or "路线" in message:
            return "我先按地图位置看了一遍，优先保留距离、路线和评分都更稳的几家："
        return "我把候选放到地图语境里重新看了下，先给你这几家方便比较点位和路线："
    if pref.get("price_sensitivity") == "high" or pref.get("budget"):
        return "你对预算比较敏感，我没有只看评分，先按价格稳定、距离和口碑一起筛："
    if pref.get("distance_sensitivity") == "high" or pref.get("location_hint"):
        return "你更在意近一点、少折腾，我先按距离优先，再兼顾评分和口味匹配："
    if pref.get("people") and pref["people"] >= 4:
        return "你这是多人一起吃，我优先看桌型、分摊友好度和菜品选择，不只看单人评分："
    if pref.get("mood") == "累了":
        return "你现在更需要低决策、少走路、吃完舒服的选择，我先帮你收窄到这几家："
    if tags:
        return f"我先从你这轮需求里抓到“{tags}”这些方向，再结合评分、距离和价格筛了几家："
    return "我先按你现在给到的信息做了一轮筛选，重点看口味匹配、距离、评分和价格是否均衡："


def _aligned_recommendation_reply(message: str, picks: list[dict], pref: dict) -> str:
    """用实际返回给前端的 picks 生成回答，避免文字推荐和卡片不一致。"""
    if not picks:
        return "我这轮没有找到足够匹配的餐厅。你可以告诉我预算、口味、距离上限或吃完后的安排，我再重新筛一轮。"

    intro = _recommendation_intro(message, pref, picks)
    blocks = []
    for r in picks[:3]:
        price = f"¥{r.get('price_min') or 0}-{r.get('price_max') or 0}"
        rating = f"★{round(r.get('avg_rating') or 0, 1)}"
        dist = _travel_text(r)
        tags = "、".join((r.get("tags") or [])[:3]) or r.get("cuisine") or "附近好店"
        dish = r.get("signature_dish") or "看店内招牌菜"
        blocks.append(
            f"🎯 **{r['name']}**（{tags}，人均{price}，{rating}，{dist}）\n"
            f"· 为什么推荐：{_scene_reason(r, pref)}\n"
            f"· 可以点：{dish}"
        )

    if pref.get("agent_mode") == "map_agent":
        follow = "我会把这几家同步成地图点位。你接下来要去地铁、商场、展会、自习点还是回家？我可以继续标出关键位置并按路线收窄。"
    else:
        follow = "要不要把这几家加入心愿单或地图？如果你接下来要自习、赶地铁、开车停车、散步或见朋友，我可以切到地图综合选择。"
    return intro + "\n\n" + "\n\n".join(blocks) + "\n\n" + follow


# ============================================================
# 规则 Agent · 纯本地，永远可用
# ============================================================
def _rule_agent(message: str, restaurants: list[dict], pref: dict, location: tuple | None) -> tuple[str, list[dict]]:
    meta = _meta_reply(message, pref.get("agent_mode", "normal_agent"))
    if meta:
        return meta, []
    clarify = _clarifying_reply(message, pref)
    if clarify:
        return clarify, []

    mood = pref.get("mood")
    budget = pref.get("budget")
    people = pref.get("people")
    cuisine = pref.get("cuisine")

    candidates = _pick_candidates(restaurants, pref, location, limit=3)
    if not candidates:
        return "目前还没有符合条件的餐厅 😅 先把预算放宽一点，或者换个口味试试？", []

    # 共情 + 分析开头
    opening = _recommendation_intro(message, pref, candidates)
    if mood:
        emoji = EMOJI_BY_MOOD.get(mood, "🍜")
        if mood == "压力大":
            opening = f"{emoji} 先照顾一下你现在压力大的状态，口味我会偏解压但不乱推："
        elif mood == "累了":
            opening = f"{emoji} 你现在需要少走路、低决策、吃完舒服，我先按这个方向筛："
        elif mood == "想庆祝":
            opening = f"{emoji} 既然是想庆祝，我会把氛围、评分和预算一起看："

    # 生成推荐文本
    blocks = []
    for i, r in enumerate(candidates, 1):
        name = f"**{r['name']}**"
        price_range = f"¥{r.get('price_min') or 0}-{r.get('price_max') or 0}"
        rating = f"★{round(r.get('avg_rating') or 0, 1)}"
        distance_text = _travel_text(r)
        tags = "、".join(r.get("tags", [])[:3]) or r.get("cuisine") or "宝藏小店"

        # 情绪价值理由
        if pref.get("business"):
            reason = "环境雅致有包厢，适合商务宴请，面子里子都到位"
        elif pref.get("dating"):
            reason = "浪漫氛围拉满，环境有情调，表白成功率翻倍"
        elif pref.get("parenting"):
            reason = "亲子友好有儿童餐，带娃吃饭省心又放心"
        elif pref.get("celebration"):
            reason = "氛围热闹菜品丰富，生日节日庆祝超有感觉"
        elif pref.get("health"):
            reason = "养生滋补清淡养胃，吃完身体暖暖的"
        elif pref.get("instagram"):
            reason = "颜值超高氛围感足，出片率百分百"
        elif pref.get("vegetarian"):
            reason = "素食友好菜品丰富，健康又美味"
        elif pref.get("local"):
            reason = "本地老字号味道正宗，值得一试"
        elif pref.get("luxury"):
            reason = "高端精致服务周到，犒劳自己超合适"
        elif pref.get("team_building"):
            reason = "适合团队聚餐氛围轻松，方便交流"
        elif mood == "压力大":
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

        # 场景标签
        if pref.get("business"):
            social_tag = "商务宴请"
        elif pref.get("dating"):
            social_tag = "约会浪漫"
        elif pref.get("parenting"):
            social_tag = "亲子家庭"
        elif pref.get("celebration"):
            social_tag = "节日庆祝"
        elif pref.get("health"):
            social_tag = "养生滋补"
        elif pref.get("instagram"):
            social_tag = "网红打卡"
        elif pref.get("vegetarian"):
            social_tag = "素食友好"
        elif pref.get("local"):
            social_tag = "本地特色"
        elif pref.get("luxury"):
            social_tag = "高端精致"
        elif pref.get("team_building"):
            social_tag = "团队聚餐"
        else:
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
    agent_mode: str = "normal_agent",
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
            dist = _travel_text(r)
            tags = "、".join(r.get("tags", [])[:3]) or r.get("cuisine") or ""
            ctx_lines.append(f"- {r['name']}（{tags}，人均{price}，{rating}，{dist}，id={r['id']}）")
        restaurants_context = "\n".join(ctx_lines)
    else:
        restaurants_context = "（暂无餐厅数据）"

    user_content = ""
    if location:
        user_content += f"【当前地图位置】纬度{location[0]:.4f}，经度{location[1]:.4f}\n"
    user_content += (
        f"【当前Agent形态】\n{_mode_instruction(agent_mode)}\n\n"
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
    agent_mode: str = "normal_agent",
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
            dist = _travel_text(r)
            tags = "、".join(r.get("tags", [])[:3]) or r.get("cuisine") or ""
            ctx_lines.append(f"- {r['name']}（{tags}，人均{price}，{rating}，{dist}，id={r['id']}）")
        restaurants_context = "\n".join(ctx_lines)
    else:
        restaurants_context = "（暂无餐厅数据）"

    user_content = ""
    if location:
        user_content += f"【当前地图位置】纬度{location[0]:.4f}，经度{location[1]:.4f}\n"
    user_content += (
        f"【当前Agent形态】\n{_mode_instruction(agent_mode)}\n\n"
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
    meta = _meta_reply(message, "normal_agent")
    if meta:
        return meta, []

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
    agent_mode: str = "normal_agent",
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
    previous_preferences = dict(session.preferences)
    new_pref = _parse_preferences(message)
    learned = _parse_feedback(message, restaurants, session.preferences.get("recent_recommendation_ids", []))
    _merge_session_preferences(session.preferences, new_pref, learned)
    if location:
        session.preferences["location"] = list(location)
    agent_mode = agent_mode if agent_mode in MODE_INSTRUCTIONS else "normal_agent"
    session.preferences["agent_mode"] = agent_mode

    decision, intent = _decide_conversation(message, agent_mode, new_pref, previous_preferences, session.preferences)
    session.preferences["last_intent"] = {
        "primary": intent.primary,
        "action": intent.action,
        "confidence": intent.confidence,
        "reasons": intent.reasons,
    }
    if not decision.allow_recommendations:
        if decision.clear_recent:
            session.preferences["recent_recommendation_ids"] = []
        session.history.append({"role": "user", "content": message})
        session.history.append({"role": "assistant", "content": decision.reply or ""})
        return {
            "session_id": session.session_id,
            "reply": decision.reply or "",
            "recommendations": [],
            "preferences": session.preferences,
            "agent_mode": agent_mode,
            "decision": decision.action,
            "intent": intent.primary,
        }

    # 选择 Agent 实现（优先级：Seed > Claude > 规则）
    has_seed = bool(settings.SEED_API_ENDPOINT) and bool(settings.SEED_API_KEY)
    has_claude = bool(settings.ANTHROPIC_API_KEY)
    
    if has_seed:
        reply, recs = await _seed_agent(
            message, restaurants, session.history, location, session.preferences, agent_mode
        )
    elif has_claude:
        reply, recs = await _claude_agent(
            message, restaurants, session.history, location, session.preferences, agent_mode
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
        "agent_mode": agent_mode,
        "decision": decision.action,
        "intent": intent.primary,
    }


async def reset_session(session_id: str | None) -> dict:
    """重置会话。"""
    if session_id and session_id in SESSIONS:
        SESSIONS.pop(session_id, None)
    new_session = create_session()
    return {"session_id": new_session.session_id, "reply": random.choice(WELCOME_GREETINGS), "recommendations": []}


def welcome_message() -> str:
    return random.choice(WELCOME_GREETINGS)
