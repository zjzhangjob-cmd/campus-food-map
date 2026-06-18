"""数据库初始化 & 种子数据（真实餐厅案例）"""
from app.core.database import Base, engine, SessionLocal
from app.core.security import hash_password
from app.models.models import User, Restaurant, MenuItem, Deal, PointsLog, UserPoints

def init_db():
    print("📦 创建数据库表...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).count() > 0:
            print("✅ 数据已存在，跳过初始化")
            return
        admin = User(username="admin", email="admin@campus-food.com",
                     hashed_pw=hash_password("admin123"), nickname="超级管理员",
                     campus="理工大", is_admin=True)
        db.add(admin)
        demo = User(username="student", email="student@campus-food.com",
                    hashed_pw=hash_password("student123"), nickname="张同学", campus="师范大")
        db.add(demo)
        db.flush()
        restaurants_data = [
            dict(name="陶陶居（大学城店）", description="百年粤式茶楼，主打传统广式早茶和点心。虾饺、叉烧包、肠粉是必点招牌，皮薄馅足，每天早上7点开始供应早茶，是大学城最受欢迎的粤菜老字号。", cuisine="中餐", campus="理工大", address="广州大学城外环西路美食街18号", phone="020-8888-0001", open_hours="07:00-22:00", price_min=28, price_max=55, distance_min=6, emoji="🍵", tags="粤菜,早茶,点心,虾饺,老字号,聚餐", is_featured=True, avg_rating=4.8, review_count=3241, latitude=23.0435, longitude=113.3995),
            dict(name="重庆秀山小面", description="正宗重庆移民开的小面馆，汤底用猪筒骨和香料熬制8小时，麻辣鲜香。招牌牛肉面和豌杂面月月售罄，早上6点半开门，附近学生排队是常态。学生证享9折。", cuisine="中餐", campus="全部", address="大学城北亭村美食巷5号", phone="138-2001-3344", open_hours="06:30-21:00", price_min=12, price_max=22, distance_min=3, emoji="🍜", tags="小面,重庆,麻辣,早餐,学生优惠,便宜", is_featured=True, avg_rating=4.9, review_count=5621, latitude=23.0462, longitude=113.4012),
            dict(name="大渔铁板烧·日料", description="环境精致的日式铁板烧餐厅，主厨有15年铁板烧经验，现场表演烹饪。三文鱼刺身、和牛铁板、抹茶甜品是招牌。适合生日聚餐、情侣约会，建议提前订座。", cuisine="日料", campus="中山大", address="大学城南亭村商业街32号", phone="020-8888-0032", open_hours="11:00-22:30", price_min=88, price_max=160, distance_min=14, emoji="🍣", tags="日料,铁板烧,刺身,约会,聚餐,三文鱼", is_featured=False, avg_rating=4.7, review_count=1893, latitude=23.0389, longitude=113.3967),
            dict(name="柒号煎饼铺", description="网红煎饼果子，用料扎实从不缩水。鸡蛋、生菜、脆薄脆、辣酱一样不少，还有创意口味如芝士培根、麻辣小龙虾。每天限量300份，卖完即止。", cuisine="小吃", campus="全部", address="理工大东门斜对面路边", phone="", open_hours="07:00-10:30,16:30-19:30", price_min=8, price_max=15, distance_min=1, emoji="🥞", tags="煎饼,早餐,快,便宜,网红,限量", is_featured=True, avg_rating=4.8, review_count=6782, latitude=23.0448, longitude=113.4021),
            dict(name="外婆家·江南菜", description="连锁江南菜品牌，招牌东坡肉肥而不腻、入口即化，龙井虾仁清爽鲜甜。装修古朴温馨，适合家庭聚餐或朋友小聚。工作日午市套餐性价比极高，人均40元含汤。", cuisine="中餐", campus="华师大", address="大学城商业广场C区3楼", phone="020-8888-0045", open_hours="10:30-21:30", price_min=38, price_max=75, distance_min=10, emoji="🥘", tags="江南菜,东坡肉,聚餐,连锁,午市套餐", is_featured=False, avg_rating=4.6, review_count=2341, latitude=23.0411, longitude=113.3978),
            dict(name="一笼小确幸·港式茶餐厅", description="正宗港式茶餐厅，菠萝油、奶茶、云吞面是核心招牌。丝袜奶茶用茶胆冲泡，香浓顺滑。午市套餐包含饮料，性价比极高。24小时营业，宵夜圣地。", cuisine="中餐", campus="广药大", address="大学城外环东路港式美食城8号", phone="020-8888-0056", open_hours="00:00-24:00", price_min=18, price_max=42, distance_min=8, emoji="🧋", tags="港式,奶茶,宵夜,24小时,云吞面,菠萝油", is_featured=False, avg_rating=4.7, review_count=4521, latitude=23.0423, longitude=113.4034),
            dict(name="韩尚宫韩式烤肉", description="韩国老板娘亲自经营的正宗韩式烤肉店，五花肉、牛短肋是必点，自制泡菜和小菜免费续加。石锅拌饭料足味美，人均60元含饮料，适合4-6人聚餐。", cuisine="韩餐", campus="暨南大", address="大学城南亭村韩餐街15号", phone="138-2001-6677", open_hours="11:00-23:00", price_min=55, price_max=95, distance_min=16, emoji="🥩", tags="韩餐,烤肉,五花肉,泡菜,聚餐,石锅拌饭", is_featured=False, avg_rating=4.5, review_count=1654, latitude=23.0377, longitude=113.3956),
            dict(name="绿·植物基轻食", description="主打植物基健康轻食，所有食材当日直采，无添加防腐剂。超级食物碗、冷压果汁、燕麦拿铁是爆款。健身人群和素食者的天堂，提供营养成分表，支持定制热量。", cuisine="西餐", campus="理工大", address="大学城创新创业园B栋1楼", phone="138-2001-8899", open_hours="08:00-20:00", price_min=28, price_max=52, distance_min=7, emoji="🥗", tags="轻食,健康,素食,低卡,健身,沙拉碗", is_featured=False, avg_rating=4.6, review_count=987, latitude=23.0441, longitude=113.4003),
            dict(name="川渝人家·火锅冒菜", description="四川人开的正宗麻辣火锅和冒菜，锅底用30多种香料熬制，麻辣鲜香层次丰富。毛肚、鸭肠、黄喉是必点涮品。冒菜可外带，单人份15元起，宿舍族最爱。", cuisine="中餐", campus="全部", address="大学城北亭村美食巷22号", phone="138-2001-5566", open_hours="10:30-02:00", price_min=35, price_max=80, distance_min=4, emoji="🫕", tags="火锅,冒菜,麻辣,川菜,宵夜,毛肚", is_featured=True, avg_rating=4.8, review_count=3876, latitude=23.0456, longitude=113.4018),
            dict(name="Café Beanery 豆舍咖啡", description="独立精品咖啡馆，自家烘焙单品豆，手冲、意式均有。招牌燕麦拿铁和桂花冷萃是网红款。空间宽敞有绿植，WiFi稳定，是学生写论文、小组讨论的首选地。", cuisine="西餐", campus="师范大", address="大学城中环西路文创园102号", phone="138-2001-7788", open_hours="08:00-22:00", price_min=22, price_max=45, distance_min=9, emoji="☕", tags="咖啡,精品咖啡,学习,WiFi,拿铁,轻食", is_featured=False, avg_rating=4.7, review_count=2134, latitude=23.0429, longitude=113.3989),
        ]
        restaurants = []
        for r_data in restaurants_data:
            r = Restaurant(**r_data)
            db.add(r)
            restaurants.append(r)
        db.flush()
        menus = [
            dict(restaurant_id=restaurants[0].id, name="招牌虾饺皇", description="必点·鲜虾饱满", price=38, emoji="🥟", is_recommended=True, monthly_sold=1200),
            dict(restaurant_id=restaurants[0].id, name="叉烧包", description="经典·松软香甜", price=22, emoji="🥐", is_recommended=True, monthly_sold=980),
            dict(restaurant_id=restaurants[1].id, name="招牌牛肉面", description="必点·月售1500+", price=18, emoji="🍜", is_recommended=True, monthly_sold=1500),
            dict(restaurant_id=restaurants[1].id, name="豌杂面", description="经典重庆味", price=12, emoji="🥣", is_recommended=True, monthly_sold=1200),
            dict(restaurant_id=restaurants[3].id, name="经典煎饼果子", description="加蛋加肠·爆款", price=10, emoji="🥞", is_recommended=True, monthly_sold=2800),
            dict(restaurant_id=restaurants[3].id, name="芝士培根煎饼", description="创意款·网红", price=15, emoji="🧀", is_recommended=True, monthly_sold=1200),
            dict(restaurant_id=restaurants[7].id, name="超级食物碗", description="低卡·高蛋白", price=38, emoji="🥗", is_recommended=True, monthly_sold=520),
            dict(restaurant_id=restaurants[9].id, name="燕麦拿铁", description="网红·爆款", price=32, emoji="☕", is_recommended=True, monthly_sold=680),
            dict(restaurant_id=restaurants[9].id, name="桂花冷萃", description="季节限定", price=36, emoji="🌸", is_recommended=True, monthly_sold=420),
        ]
        for m in menus:
            db.add(MenuItem(**m))
        deals = [
            dict(restaurant_id=restaurants[1].id, title="学生证9折", description="凭学生证享9折，工作日全天有效", original_price=18, deal_price=16, discount_text="9折"),
            dict(restaurant_id=restaurants[3].id, title="第二个半价", description="任意口味第二个半价", original_price=10, deal_price=15, discount_text="买一送半"),
            dict(restaurant_id=restaurants[0].id, title="早茶双人套餐", description="含4款点心+2杯茶，每日限20套", original_price=88, deal_price=68, discount_text="立减20元"),
            dict(restaurant_id=restaurants[8].id, title="宵夜外卖免配送", description="晚10点后外卖免配送费", original_price=None, deal_price=None, discount_text="免配送费"),
            dict(restaurant_id=restaurants[9].id, title="下午茶买二送一", description="14:00-17:00任意饮品买二送一", original_price=32, deal_price=21, discount_text="买二送一"),
        ]
        for d in deals:
            db.add(Deal(**d))
        db.commit()
        print("✅ 初始化完成！管理员：admin/admin123  用户：student/student123")
    except Exception as e:
        db.rollback()
        print(f"❌ 失败：{e}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    init_db()
