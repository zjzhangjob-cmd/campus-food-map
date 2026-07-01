"""扩充上海餐厅数据到1000+家，覆盖各类场景，用于训练AI Agent"""
from __future__ import annotations

import random
from app.core.database import SessionLocal
from app.models.models import Restaurant, MenuItem, Review, User, Deal
from app.core.security import hash_password


# 上海各区域中心坐标（用于生成分布合理的餐厅）
SHANGHAI_AREAS = {
    "静安区": (31.2304, 121.4737),
    "黄浦区": (31.2300, 121.4700),
    "徐汇区": (31.1935, 121.4367),
    "长宁区": (31.2200, 121.4200),
    "普陀区": (31.2500, 121.4000),
    "虹口区": (31.2700, 121.4900),
    "杨浦区": (31.2500, 121.5100),
    "浦东新区": (31.2400, 121.5400),
    "闵行区": (31.1100, 121.3800),
    "宝山区": (31.4100, 121.4900),
}

# 菜系分类
CUISINE_CATEGORIES = [
    ("川菜", "🌶️", ["辣", "川菜", "麻辣", "重口味", "下饭"]),
    ("湘菜", "🌶️", ["辣", "湘菜", "香辣", "下饭"]),
    ("粤菜", "🥢", ["粤菜", "清淡", "煲汤", "早茶"]),
    ("本帮菜", "🥢", ["本帮菜", "上海菜", "浓油赤酱", "甜口"]),
    ("日料", "🍣", ["日料", "寿司", "刺身", "清淡", "健康"]),
    ("韩餐", "🍜", ["韩餐", "韩式", "烤肉", "部队锅"]),
    ("西餐", "🍝", ["西餐", "牛排", "意面", "约会", "浪漫"]),
    ("法餐", "🍷", ["法餐", "小酒馆", "约会", "浪漫", "高端"]),
    ("火锅", "🍲", ["火锅", "辣", "聚餐", "热闹"]),
    ("烧烤", "🍢", ["烧烤", "宵夜", "啤酒", "聚餐"]),
    ("麻辣烫", "🍲", ["麻辣烫", "便宜", "一人食", "宵夜"]),
    ("小吃", "🥟", ["小吃", "便宜", "早餐", "路边摊"]),
    ("面食", "🍜", ["面食", "面条", "便宜", "一人食", "早餐"]),
    ("甜品", "🍰", ["甜品", "蛋糕", "下午茶", "约会", "甜口"]),
    ("奶茶饮品", "🧋", ["奶茶", "饮品", "下午茶", "便宜", "学生最爱"]),
    ("咖啡", "☕", ["咖啡", "下午茶", "工作", "学习"]),
    ("轻食", "🥗", ["轻食", "沙拉", "健康", "减脂", "低卡"]),
    ("海鲜", "🦐", ["海鲜", "聚餐", "高端", "宴请"]),
    ("新疆菜", "🍖", ["新疆菜", "大盘鸡", "烤肉", "聚餐"]),
    ("东北菜", "🥟", ["东北菜", "量大", "便宜", "聚餐"]),
]

# 餐厅名称模板（按菜系）
NAME_TEMPLATES = {
    "川菜": ["川味小馆", "麻辣空间", "蜀香居", "川妹子", "老成都", "麻辣诱惑", "川味轩", "蜀都丰", "红辣椒", "川味坊"],
    "湘菜": ["湘菜馆", "湖南人家", "湘味小厨", "老长沙", "湘赣边界", "剁椒鱼头馆", "湘香阁", "湖南米粉", "湘西人家", "湘辣坊"],
    "粤菜": ["粤菜馆", "港式茶餐厅", "广东人家", "粤味轩", "潮汕牛肉火锅", "港式烧腊", "粤港茶餐厅", "顺德人家", "广式早茶", "粤味小馆"],
    "本帮菜": ["老上海", "本帮小馆", "上海人家", "弄堂菜", "石库门", "老克勒", "本帮菜社", "沪上人家", "上海老饭店", "弄堂里"],
    "日料": ["寿司屋", "居酒屋", "日式拉面", "日料小馆", "烧肉一筋", "寿司郎", "一风堂", "味千拉面", "日式炸猪排", "和牛烧肉"],
    "韩餐": ["韩式烤肉", "部队火锅", "石锅拌饭", "韩料理", "韩国街", "首尔烤肉", "韩式炸鸡", "泡菜汤", "韩屋村", "明洞烤肉"],
    "西餐": ["西餐厅", "牛排馆", "意大利餐厅", "美式餐厅", "汉堡店", "披萨店", "墨西哥餐厅", "西班牙餐厅", "德国餐厅", "东南亚菜"],
    "法餐": ["法式小酒馆", "法餐厅", "塞纳河", "巴黎小馆", "法式甜点", "红酒屋", "鹅肝酱", "松露餐厅", "法式面包房", "左岸咖啡"],
    "火锅": ["火锅店", "海底捞", "呷哺呷哺", "小龙坎", "大龙燚", "蜀大侠", "谭鸭血", "老北京涮肉", "潮汕牛肉火锅", "椰子鸡火锅"],
    "烧烤": ["烧烤摊", "撸串吧", "烤串王", "东北烧烤", "新疆烤肉", "木炭烧烤", "串吧", "夜猫子烧烤", "烤天下", "火焰山"],
    "麻辣烫": ["麻辣烫", "张亮麻辣烫", "杨国福", "串串香", "冒菜", "麻辣拌", "钵钵鸡", "冷锅串串", "麻辣烫王", "麻辣小屋"],
    "小吃": ["小吃店", "生煎包", "小笼包", "葱油饼", "煎饼果子", "烤冷面", "手抓饼", "臭豆腐", "章鱼小丸子", "炸鸡排"],
    "面食": ["面馆", "兰州拉面", "重庆小面", "老北京炸酱面", "武汉热干面", "山西刀削面", "陕西油泼面", "四川担担面", "鲜虾云吞面", "牛肉面"],
    "甜品": ["甜品店", "蛋糕店", "冰淇淋店", "糖水铺", "双皮奶", "芒果捞", "满记甜品", "许留山", "DQ冰雪皇后", "哈根达斯"],
    "奶茶饮品": ["奶茶店", "喜茶", "奈雪の茶", "蜜雪冰城", "一点点", "古茗", "茶百道", "CoCo都可", "快乐柠檬", "沪上阿姨"],
    "咖啡": ["星巴克", "瑞幸咖啡", "Manner Coffee", "Tims咖啡", "皮爷咖啡", "Seesaw咖啡", "% Arabica", "Blue Bottle", "太平洋咖啡", "咖世家"],
    "轻食": ["轻食餐厅", "沙拉店", "Wagas", "新元素", "蔬食店", "健康餐", "减脂餐", "低卡厨房", "有机餐厅", "绿色工坊"],
    "海鲜": ["海鲜大排档", "海鲜酒楼", "舟山海鲜", "象山海鲜", "海鲜自助", "帝王蟹", "生蚝吧", "海鲜市场", "渔家乐", "海鲜火锅"],
    "新疆菜": ["新疆大盘鸡", "羊肉串大王", "新疆饭店", "西域风情", "塔里木", "天山来客", "新疆烧烤", "手抓饭", "馕坑肉", "哈萨克奶茶"],
    "东北菜": ["东北菜馆", "饺子馆", "铁锅炖", "东北大拉皮", "锅包肉", "地三鲜", "杀猪菜", "东北虎", "黑土地", "闯关东"],
}

# 描述模板
DESC_TEMPLATES = [
    "开了{year}年的老店，周边居民的{favorite}。招牌{signature}是必点，{taste}。环境{env}，{price}。",
    "藏在{location}里的宝藏店，{specialty}一绝。{crowd}都爱来这里，{vibe}。人均{budget}元，性价比{ratio}。",
    "{style}风格的{type}店，{feature}是特色。{taste_desc}，一口下去超{feeling}。适合{scene}，{recommend}。",
    "网红{type}店，排队{viral}是常态。{signature}是招牌，{reason}。环境{decor}，拍照出片，适合{photo}。",
    "本地人推荐的{type}，{authentic}正宗。{dish}必点，{comment}。{price_desc}，{crowd_desc}的最爱。",
]

# 团购/优惠模板
DEAL_TEMPLATES = [
    ("双人套餐", "招牌菜品+饮品+主食，超值双人餐", 99, 168, "双人约会/聚餐"),
    ("单人套餐", "主食+饮品+小菜，一人食必备", 29, 45, "一人食/工作餐"),
    ("3-4人聚餐套餐", "招牌菜+热菜+汤品+主食，聚餐首选", 199, 328, "朋友聚餐/家庭聚会"),
    ("代金券", "全场通用，可叠加使用", 85, 100, "全场通用"),
    ("下午茶套餐", "甜品+饮品，悠闲时光", 39, 68, "下午茶/约会"),
    ("宵夜套餐", "烧烤+啤酒，深夜食堂", 68, 128, "宵夜/朋友小聚"),
    ("学生特惠套餐", "凭学生证享受专属优惠", 19, 35, "学生专属"),
    ("工作日午餐", "主食+汤+小菜，工作日特惠", 25, 42, "工作午餐"),
]


def generate_restaurant_name(cuisine: str, index: int) -> str:
    templates = NAME_TEMPLATES.get(cuisine, ["美食小馆"])
    base = random.choice(templates)
    suffixes = ["", "（总店）", "（分店）", "（旗舰店）", "（网红店）", "（老店）", "（NO.{}）".format(index % 10)]
    return base + random.choice(suffixes)


def generate_description(cuisine: str, name: str, price_min: int, price_max: int) -> str:
    template = random.choice(DESC_TEMPLATES)
    avg_price = (price_min + price_max) // 2
    
    signature_dishes = {
        "川菜": "麻婆豆腐、宫保鸡丁、水煮鱼",
        "湘菜": "剁椒鱼头、小炒黄牛肉、臭豆腐",
        "粤菜": "烧鹅、虾饺、叉烧包",
        "本帮菜": "红烧肉、松鼠鳜鱼、响油鳝糊",
        "日料": "寿司拼盘、三文鱼刺身、豚骨拉面",
        "韩餐": "韩式烤肉、部队火锅、石锅拌饭",
        "西餐": "牛排、意面、凯撒沙拉",
        "法餐": "鹅肝慕斯、松露意面、红酒炖牛肉",
        "火锅": "毛肚、肥牛、虾滑",
        "烧烤": "羊肉串、烤茄子、烤生蚝",
        "麻辣烫": "麻辣烫、麻辣拌、钵钵鸡",
        "小吃": "生煎包、小笼包、葱油饼",
        "面食": "牛肉面、炸酱面、担担面",
        "甜品": "提拉米苏、芒果班戟、双皮奶",
        "奶茶饮品": "珍珠奶茶、芝士奶盖、芋圆奶茶",
        "咖啡": "拿铁、美式、卡布奇诺",
        "轻食": "凯撒沙拉、牛油果三明治、藜麦碗",
        "海鲜": "清蒸鲈鱼、蒜蓉粉丝蒸扇贝、椒盐皮皮虾",
        "新疆菜": "大盘鸡、羊肉串、手抓饭",
        "东北菜": "锅包肉、地三鲜、饺子",
    }
    
    return template.format(
        year=random.randint(3, 25),
        favorite=random.choice(["心头好", "食堂", "据点", "秘密基地", "必打卡"]),
        signature=signature_dishes.get(cuisine, "招牌菜"),
        taste=random.choice(["味道正宗", "口味地道", "越吃越香", "回味无穷", "让人欲罢不能"]),
        env=random.choice(["温馨舒适", "干净整洁", "有格调", "烟火气十足", "简约大方"]),
        price=random.choice(["价格实惠", "性价比很高", "物超所值", "人均不贵", "亲民价格"]),
        location=random.choice(["弄堂", "街角", "商场", "写字楼", "校园周边"]),
        specialty=signature_dishes.get(cuisine, "招牌菜").split("、")[0],
        crowd=random.choice(["附近上班族", "学生党", "周边居民", "年轻人", "吃货们"]),
        vibe=random.choice(["氛围超棒", "烟火气很足", "很有感觉", "拍照好看", "适合聊天"]),
        budget=avg_price,
        ratio=random.choice(["超高", "不错", "相当可以", "拉满", "无敌"]),
        style=random.choice(["复古", "现代", "ins风", "日式", "韩式"]),
        type=cuisine,
        feature=signature_dishes.get(cuisine, "招牌菜").split("、")[0],
        taste_desc=random.choice(["入口即化", "香气扑鼻", "麻辣鲜香", "酸甜可口", "外酥里嫩"]),
        feeling=random.choice(["满足", "治愈", "幸福", "过瘾", "上头"]),
        scene=random.choice(["朋友聚餐", "一人食", "约会", "家庭聚会", "工作午餐"]),
        recommend=random.choice(["强烈推荐", "必打卡", "值得一试", "回头客超多", "好评如潮"]),
        viral=random.choice(["半小时", "一小时", "两小时", "排队到怀疑人生", "风雨无阻"]),
        reason=random.choice(["味道确实好", "颜值高", "分量足", "服务好", "性价比高"]),
        decor=random.choice(["精美", "有设计感", "ins风", "网红风", "很出片"]),
        photo=random.choice(["拍照打卡", "发朋友圈", "约会", "闺蜜下午茶", "纪念日"]),
        authentic=random.choice(["味道", "做法", "食材", "调料", "配方"]),
        dish=signature_dishes.get(cuisine, "招牌菜").split("、")[0],
        comment=random.choice(["一口就爱上", "绝了", "yyds", "每次必点", "念念不忘"]),
        price_desc=random.choice(["价格亲民", "人均不贵", "性价比超高", "学生党友好", "打工人首选"]),
        crowd_desc=random.choice(["周边上班族", "学生党", "年轻人", "附近居民", "吃货"]),
    )


def generate_tags(cuisine: str, tags_base: list, price_min: int, price_max: int) -> str:
    tags = list(tags_base)
    avg_price = (price_min + price_max) // 2
    
    if avg_price <= 30:
        tags.append("便宜")
        tags.append("学生党")
    elif avg_price <= 80:
        tags.append("性价比高")
    else:
        tags.append("高端")
        tags.append("约会")
    
    scenarios = ["一人食", "聚餐", "约会", "工作午餐", "宵夜", "早餐", "下午茶"]
    tags.extend(random.sample(scenarios, random.randint(1, 3)))
    
    return ",".join(tags[:8])


def add_shanghai_expanded_data():
    db = SessionLocal()
    try:
        existing_sh = db.query(Restaurant).filter(Restaurant.latitude > 30).count()
        print(f"现有上海餐厅数: {existing_sh}")
        
        target_count = 1000
        to_add = target_count - existing_sh
        if to_add <= 0:
            print("✅ 上海餐厅数据已达到1000家，无需扩充")
            return
        
        print(f"需要新增 {to_add} 家餐厅")
        
        reviewer = db.query(User).filter(User.username == "sh_student").first()
        if not reviewer:
            reviewer = User(
                username="sh_student", email="sh@campus-food.com",
                hashed_pw=hash_password("student123"),
                nickname="上海吃货", campus="复旦", is_admin=False
            )
            db.add(reviewer)
            db.flush()
        
        restaurants = []
        batch_size = 100
        
        for i in range(to_add):
            cuisine, emoji, tags_base = random.choice(CUISINE_CATEGORIES)
            area_name, (base_lat, base_lng) = random.choice(list(SHANGHAI_AREAS.items()))
            
            lat = base_lat + random.uniform(-0.02, 0.02)
            lng = base_lng + random.uniform(-0.02, 0.02)
            
            price_ranges = [
                (5, 15), (10, 25), (15, 35), (20, 50),
                (30, 70), (50, 100), (80, 150), (120, 250),
                (200, 400), (300, 600),
            ]
            price_min, price_max = random.choice(price_ranges)
            
            name = generate_restaurant_name(cuisine, i)
            description = generate_description(cuisine, name, price_min, price_max)
            tags = generate_tags(cuisine, tags_base, price_min, price_max)
            
            avg_rating = round(random.uniform(3.5, 5.0), 1)
            review_count = random.randint(10, 9999)
            
            street_names = ["南京西路", "淮海路", "徐家汇", "五角场", "陆家嘴", "人民广场", "静安寺", "中山公园", "莘庄", "四川北路"]
            street_num = random.randint(1, 999)
            address = f"{area_name}{random.choice(street_names)}{street_num}号"
            
            open_options = [
                "07:00-22:00", "10:00-22:00", "11:00-21:30",
                "11:00-14:00 17:00-22:00", "06:30-20:00",
                "16:00-02:00", "10:00-24:00", "08:00-23:00",
            ]
            
            r = Restaurant(
                name=name,
                description=description,
                cuisine=cuisine,
                campus="全部",
                address=address,
                phone=f"021-{random.randint(50000000, 69999999)}" if random.random() > 0.3 else "",
                open_hours=random.choice(open_options),
                price_min=price_min,
                price_max=price_max,
                distance_min=random.randint(50, 500),
                emoji=emoji,
                tags=tags,
                is_open=random.random() > 0.05,
                is_featured=random.random() < 0.1,
                is_active=True,
                latitude=lat,
                longitude=lng,
                avg_rating=avg_rating,
                review_count=review_count,
            )
            db.add(r)
            restaurants.append(r)
            
            if (i + 1) % batch_size == 0:
                db.flush()
                print(f"已生成 {i + 1}/{to_add} 家餐厅")
        
        db.flush()
        print(f"✅ 新增 {len(restaurants)} 家上海餐厅")
        
        print("正在生成菜单数据...")
        menu_count = 0
        for idx, rest in enumerate(restaurants):
            num_dishes = random.randint(2, 6)
            dish_names = {
                "川菜": ["麻婆豆腐", "宫保鸡丁", "水煮鱼", "回锅肉", "鱼香肉丝", "夫妻肺片", "口水鸡", "担担面"],
                "湘菜": ["剁椒鱼头", "小炒黄牛肉", "臭豆腐", "口味虾", "辣椒炒肉", "剁椒芋头", "酸辣鸡杂", "湖南米粉"],
                "粤菜": ["烧鹅", "虾饺", "叉烧包", "肠粉", "白切鸡", "煲仔饭", "老火靓汤", "潮汕牛肉丸"],
                "本帮菜": ["红烧肉", "松鼠鳜鱼", "响油鳝糊", "腌笃鲜", "糟钵头", "草头圈子", "八宝鸭", "本帮熏鱼"],
                "日料": ["寿司拼盘", "三文鱼刺身", "豚骨拉面", "天妇罗", "日式咖喱饭", "鳗鱼饭", "亲子丼", "味增汤"],
                "韩餐": ["韩式烤肉", "部队火锅", "石锅拌饭", "炸鸡", "泡菜汤", "冷面", "年糕", "紫菜包饭"],
                "西餐": ["牛排", "意大利面", "凯撒沙拉", "汉堡", "披萨", "薯条", "墨西哥卷饼", "海鲜饭"],
                "法餐": ["鹅肝慕斯", "松露意面", "红酒炖牛肉", "法式洋葱汤", "可颂", "马卡龙", "焦糖布丁", "法式吐司"],
                "火锅": ["毛肚", "肥牛卷", "虾滑", "羊肉卷", "鸭肠", "黄喉", "酥肉", "冰粉"],
                "烧烤": ["羊肉串", "烤茄子", "烤生蚝", "烤鸡翅", "烤韭菜", "烤馒头", "烤玉米", "烤鱿鱼"],
                "麻辣烫": ["麻辣烫套餐", "麻辣拌", "钵钵鸡", "串串香", "冒菜", "冷锅串串", "关东煮", "麻辣香锅"],
                "小吃": ["生煎包", "小笼包", "葱油饼", "煎饼果子", "烤冷面", "手抓饼", "臭豆腐", "章鱼小丸子"],
                "面食": ["牛肉面", "炸酱面", "担担面", "热干面", "刀削面", "油泼面", "云吞面", "拉面"],
                "甜品": ["提拉米苏", "芒果班戟", "双皮奶", "杨枝甘露", "芋圆", "烧仙草", "布丁", "冰淇淋"],
                "奶茶饮品": ["珍珠奶茶", "芝士奶盖", "芋圆奶茶", "水果茶", "柠檬茶", "抹茶拿铁", "红豆奶茶", "烧仙草奶茶"],
                "咖啡": ["拿铁", "美式", "卡布奇诺", "摩卡", "玛奇朵", "冰滴咖啡", "手冲咖啡", "燕麦拿铁"],
                "轻食": ["凯撒沙拉", "牛油果三明治", "藜麦碗", "鸡胸肉沙拉", "蔬菜沙拉", "全麦三明治", "酸奶碗", "水果沙拉"],
                "海鲜": ["清蒸鲈鱼", "蒜蓉粉丝蒸扇贝", "椒盐皮皮虾", "香辣蟹", "生蚝", "鲍鱼", "三文鱼", "龙虾"],
                "新疆菜": ["大盘鸡", "羊肉串", "手抓饭", "馕坑肉", "拉条子", "烤包子", "奶茶", "手抓肉"],
                "东北菜": ["锅包肉", "地三鲜", "饺子", "铁锅炖", "东北大拉皮", "杀猪菜", "酱骨头", "粘豆包"],
            }
            
            dishes = dish_names.get(rest.cuisine, ["招牌菜"])
            selected_dishes = random.sample(dishes, min(num_dishes, len(dishes)))
            
            for j, dish in enumerate(selected_dishes):
                price = random.randint(rest.price_min, min(rest.price_max, rest.price_min + 50))
                db.add(MenuItem(
                    restaurant_id=rest.id,
                    name=dish,
                    description=random.choice(["招牌·必点", "人气推荐", "店长推荐", "招牌菜", "爆款"]),
                    price=price,
                    emoji=rest.emoji,
                    is_recommended=(j == 0),
                    monthly_sold=random.randint(50, 2000),
                ))
                menu_count += 1
        
        print(f"✅ 新增 {menu_count} 道菜品")
        
        print("正在生成评价数据...")
        review_count = 0
        review_templates = [
            "{dish}太好吃了！{feeling}，下次还来。",
            "环境{env}，味道{taste}，性价比{ratio}。推荐{dish}。",
            "{cuisine}爱好者必打卡！{dish}绝了，{comment}。",
            "朋友推荐来的，果然没失望。{dish}是亮点，{feeling}。",
            "路过看到人很多就进去了，没想到{surprise}。{dish}必点！",
            "N刷了，每次来都要点{dish}。{comment}。",
            "排队{wait}才吃到，不过{worth}。{dish}名不虚传。",
            "人均{price}元，{value}。{dish}味道不错，{recommend}。",
            "{scene}来的，环境{env}，很适合{vibe}。{dish}推荐。",
            "{authentic}的{type}，味道{flavor}。{dish}必点，{comment}。",
        ]
        
        for rest in restaurants:
            num_reviews = random.randint(0, 5)
            for _ in range(num_reviews):
                dish = random.choice(["招牌菜", rest.cuisine + "特色菜", "店长推荐"])
                content = random.choice(review_templates).format(
                    dish=dish,
                    feeling=random.choice(["太满足了", "幸福感爆棚", "回味无穷", "一口就爱上", "越吃越香"]),
                    env=random.choice(["很舒适", "有格调", "温馨", "烟火气足", "干净整洁"]),
                    taste=random.choice(["很正宗", "超棒", "很不错", "惊艳", "地道"]),
                    ratio=random.choice(["很高", "不错", "可以", "拉满", "超高"]),
                    cuisine=rest.cuisine,
                    comment=random.choice(["强烈推荐", "yyds", "绝了", "念念不忘", "每次必点"]),
                    surprise=random.choice(["这么好吃", "超出预期", "宝藏店", "发现新大陆", "太惊喜了"]),
                    wait=random.choice(["半小时", "一小时", "20分钟", "40分钟", "一会儿"]),
                    worth=random.choice(["值得", "值了", "没白等", "不枉此行", "完全值得"]),
                    price=random.randint(rest.price_min, rest.price_max),
                    value=random.choice(["性价比超高", "物超所值", "不贵", "很划算", "可以接受"]),
                    recommend=random.choice(["值得一试", "推荐给大家", "可以来试试", "回头客超多", "好评如潮"]),
                    scene=random.choice(["约会", "聚餐", "一人食", "下午茶", "工作餐"]),
                    vibe=random.choice(["拍照", "聊天", "放松", "约会", "聚餐"]),
                    authentic=random.choice(["正宗", "地道", "纯正", "传统", "老式"]),
                    type=rest.cuisine,
                    flavor=random.choice(["很正", "很棒", "很地道", "不错", "超赞"]),
                )
                rating = round(random.uniform(3.5, 5.0), 1)
                
                db.add(Review(
                    restaurant_id=rest.id,
                    user_id=reviewer.id,
                    rating=rating,
                    content=content,
                    is_anonymous=random.random() < 0.3,
                ))
                review_count += 1
        
        print(f"✅ 新增 {review_count} 条评价")
        
        print("正在生成团购数据...")
        deal_count = 0
        for rest in restaurants:
            if random.random() < 0.4:
                num_deals = random.randint(1, 3)
                selected_deals = random.sample(DEAL_TEMPLATES, min(num_deals, len(DEAL_TEMPLATES)))
                for deal_name, deal_desc, deal_price, deal_original, deal_scene in selected_deals:
                    if deal_price < rest.price_max:
                        db.add(Deal(
                            restaurant_id=rest.id,
                            title=deal_name,
                            description=deal_desc,
                            original_price=deal_original,
                            deal_price=deal_price,
                            discount_text=f"{round(deal_price/deal_original*10, 1)}折",
                            valid_until="2026-12-31",
                            is_active=True,
                        ))
                        deal_count += 1
        
        print(f"✅ 新增 {deal_count} 个团购优惠")
        
        db.commit()
        total = db.query(Restaurant).filter(Restaurant.latitude > 30).count()
        print(f"🎉 上海餐厅数据扩充完成！当前总数: {total} 家")
        
    except Exception as e:
        db.rollback()
        print(f"❌ 失败：{e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    add_shanghai_expanded_data()
