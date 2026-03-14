"""
数据库初始化 & 种子数据
运行方式：python -m app.init_db
"""
from app.core.database import Base, engine, SessionLocal
from app.core.security import hash_password
from app.models.models import User, Restaurant, MenuItem, Deal

def init_db():
    print("📦 创建数据库表...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()
    try:
        # 已有数据则跳过
        if db.query(User).count() > 0:
            print("✅ 数据已存在，跳过初始化")
            return

        print("👤 创建管理员账号...")
        admin = User(
            username="admin",
            email="admin@campus-food.com",
            hashed_pw=hash_password("admin123"),
            nickname="超级管理员",
            campus="理工大",
            is_admin=True,
        )
        db.add(admin)

        demo_user = User(
            username="student",
            email="student@campus-food.com",
            hashed_pw=hash_password("student123"),
            nickname="测试同学",
            campus="师范大",
        )
        db.add(demo_user)
        db.flush()

        print("🍜 导入示例餐厅...")
        restaurants_data = [
            dict(name="老林家重庆小面", description="开业12年的老字号面馆，汤底采用猪骨熬制12小时，鲜辣醇厚；面条每日新鲜制作，劲道爽滑。排骨面和豌杂面是招牌，强烈推荐！",
                 cuisine="中餐", campus="理工大", address="大学城美食街8号", phone="138-0001-0001",
                 open_hours="06:00-22:00", price_min=12, price_max=18, distance_min=5,
                 emoji="🍜", tags="辣,排骨面,豌杂面,学生优惠,早餐", is_featured=True,
                 avg_rating=4.9, review_count=2341, latitude=23.0437, longitude=113.3508),
            dict(name="绿野轻食工坊", description="新开的轻食品牌，食材每日直采，沙拉碗可自由搭配。健身党和减脂人士的福音，营养均衡口味好。",
                 cuisine="西餐", campus="师范大", address="大学城科创路20号", phone="138-0001-0002",
                 open_hours="09:00-21:00", price_min=25, price_max=38, distance_min=8,
                 emoji="🥗", tags="低卡,沙拉碗,健身餐,素食,减脂", is_featured=False,
                 avg_rating=4.7, review_count=856, latitude=23.0451, longitude=113.3521),
            dict(name="鱼跃回转寿司", description="环境精致，适合约饭聚餐。寿司新鲜，种类丰富，学生聚餐热门选择。",
                 cuisine="日料", campus="理工大", address="大学城商业广场B2层", phone="138-0001-0003",
                 open_hours="11:00-22:00", price_min=40, price_max=65, distance_min=12,
                 emoji="🍣", tags="回转寿司,刺身,约饭,聚餐,日料", is_featured=False,
                 avg_rating=4.6, review_count=1204, latitude=23.0425, longitude=113.3495),
            dict(name="胡同煎饼摊", description="学校门口的老摊子，煎饼现做现卖，热乎乎的超好吃。早上7-9点排队都是赶着上课的同学！",
                 cuisine="小吃", campus="全部", address="理工大东门路边摊", phone="",
                 open_hours="06:30-10:00,16:00-20:00", price_min=6, price_max=12, distance_min=2,
                 emoji="🌮", tags="煎饼果子,快,早餐,便宜,¥10以下", is_featured=True,
                 avg_rating=4.8, review_count=3102, latitude=23.0442, longitude=113.3512),
            dict(name="云贵小馆", description="正宗云贵风味，过桥米线是招牌，酸汤鱼也非常值得一试。凌晨2点还在营业，是宵夜首选。",
                 cuisine="中餐", campus="财经大", address="大学城美食街32号", phone="138-0001-0005",
                 open_hours="10:00-02:00", price_min=20, price_max=30, distance_min=7,
                 emoji="🍲", tags="酸辣,过桥米线,宵夜,24小时,云南", is_featured=True,
                 avg_rating=4.8, review_count=987, latitude=23.0418, longitude=113.3488),
            dict(name="韩味烤肉·浪", description="地道韩国烤肉店，石锅拌饭超赞，适合聚餐庆祝。周末可能需要等位，建议提前订座。",
                 cuisine="韩餐", campus="医科大", address="大学城商业广场A区", phone="138-0001-0006",
                 open_hours="11:30-23:00", price_min=45, price_max=80, distance_min=15,
                 emoji="🍖", tags="烤肉,石锅拌饭,约饭,聚餐,韩餐", is_featured=False,
                 avg_rating=4.5, review_count=762, latitude=23.0462, longitude=113.3535),
            dict(name="南亚咖喱坊", description="正宗印度泰国风味，咖喱口感浓郁层次丰富。素食者友好，工作日午餐套餐性价比超高。",
                 cuisine="西餐", campus="师范大", address="大学城文化路15号", phone="138-0001-0007",
                 open_hours="11:00-21:30", price_min=22, price_max=40, distance_min=10,
                 emoji="🍛", tags="咖喱,特色,素食友好,异域,泰国", is_featured=False,
                 avg_rating=4.6, review_count=543, latitude=23.0433, longitude=113.3502),
            dict(name="蜀香火锅", description="正宗四川火锅，锅底鲜香麻辣，食材新鲜丰富。多人聚餐必选，支持学生卡结算9折。",
                 cuisine="中餐", campus="理工大", address="大学城美食街66号", phone="138-0001-0008",
                 open_hours="11:00-23:30", price_min=50, price_max=90, distance_min=10,
                 emoji="🍲", tags="火锅,麻辣,聚餐,学生卡,川菜", is_featured=False,
                 avg_rating=4.7, review_count=1456, latitude=23.0445, longitude=113.3518),
        ]

        restaurants = []
        for r_data in restaurants_data:
            r = Restaurant(**r_data)
            db.add(r)
            restaurants.append(r)
        db.flush()

        print("🍽️ 导入菜单...")
        menus = [
            # 老林家重庆小面
            dict(restaurant_id=restaurants[0].id, name="招牌排骨面", description="必点·月售800+", price=18, emoji="🍜", is_recommended=True, monthly_sold=800),
            dict(restaurant_id=restaurants[0].id, name="豌杂面", description="经典·月售650+", price=12, emoji="🥩", is_recommended=True, monthly_sold=650),
            dict(restaurant_id=restaurants[0].id, name="红烧牛肉面", description="新品推荐", price=22, emoji="🥣", is_recommended=False, monthly_sold=320),
            # 绿野轻食
            dict(restaurant_id=restaurants[1].id, name="鸡胸肉沙拉碗", description="低卡·高蛋白", price=32, emoji="🥗", is_recommended=True, monthly_sold=420),
            dict(restaurant_id=restaurants[1].id, name="藜麦蔬菜碗", description="纯素·推荐", price=28, emoji="🥙", is_recommended=True, monthly_sold=280),
            # 胡同煎饼摊
            dict(restaurant_id=restaurants[3].id, name="招牌煎饼果子", description="加蛋加肠·最受欢迎", price=10, emoji="🌮", is_recommended=True, monthly_sold=1500),
            dict(restaurant_id=restaurants[3].id, name="素煎饼", description="基础款·实惠", price=6, emoji="🫓", is_recommended=False, monthly_sold=800),
        ]
        for m in menus:
            db.add(MenuItem(**m))

        print("🎟️ 导入优惠活动...")
        deals = [
            dict(restaurant_id=restaurants[0].id, title="学生证8折", description="凭学生证享8折，每日限量50份",
                 original_price=15, deal_price=12, discount_text="8折"),
            dict(restaurant_id=restaurants[1].id, title="双人套餐立减8元", description="双人套餐立减8元，周三额外折扣",
                 original_price=36, deal_price=28, discount_text="立减8元"),
            dict(restaurant_id=restaurants[3].id, title="第二个半价", description="买一个煎饼，第二个半价",
                 original_price=10, deal_price=15, discount_text="买一送半"),
            dict(restaurant_id=restaurants[4].id, title="午市特惠", description="工作日11-13点，米线套餐特惠",
                 original_price=28, deal_price=22, discount_text="立减6元"),
        ]
        for d in deals:
            db.add(Deal(**d))

        db.commit()
        print("✅ 初始化完成！")
        print("─────────────────────────────")
        print("🔑 管理员账号：admin / admin123")
        print("👤 测试账号：student / student123")
        print("📖 API 文档：http://localhost:8000/docs")

    except Exception as e:
        db.rollback()
        print(f"❌ 初始化失败：{e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
