"""扩充上海餐厅数据到1000+家"""
import random
from datetime import datetime
from app.core.database import SessionLocal
from app.models.models import Restaurant, MenuItem, Review, Deal, User
from app.core.security import hash_password


def main():
    db = SessionLocal()
    try:
        existing_sh = db.query(Restaurant).filter(Restaurant.latitude > 30).count()
        print("现有上海餐厅:", existing_sh)

        target = 1000
        to_add = target - existing_sh
        if to_add <= 0:
            print("已达到目标数量")
            return
        print("需要新增:", to_add)

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

        CUISINES = [
            ("川菜", "🌶️", ["辣", "川菜", "麻辣", "下饭"]),
            ("湘菜", "🌶️", ["辣", "湘菜", "香辣", "下饭"]),
            ("粤菜", "🥢", ["粤菜", "清淡", "煲汤", "早茶"]),
            ("本帮菜", "🥢", ["本帮菜", "上海菜", "浓油赤酱"]),
            ("日料", "🍣", ["日料", "寿司", "刺身", "清淡"]),
            ("韩餐", "🍜", ["韩餐", "韩式", "烤肉", "部队锅"]),
            ("西餐", "🍝", ["西餐", "牛排", "意面", "约会"]),
            ("火锅", "🍲", ["火锅", "辣", "聚餐", "热闹"]),
            ("烧烤", "🍢", ["烧烤", "宵夜", "啤酒", "聚餐"]),
            ("麻辣烫", "🍲", ["麻辣烫", "便宜", "一人食", "宵夜"]),
            ("小吃", "🥟", ["小吃", "便宜", "早餐", "路边摊"]),
            ("面食", "🍜", ["面食", "面条", "便宜", "一人食"]),
            ("甜品", "🍰", ["甜品", "蛋糕", "下午茶", "约会"]),
            ("奶茶饮品", "🧋", ["奶茶", "饮品", "下午茶", "便宜"]),
            ("咖啡", "☕", ["咖啡", "下午茶", "工作", "学习"]),
            ("轻食", "🥗", ["轻食", "沙拉", "健康", "减脂"]),
            ("海鲜", "🦐", ["海鲜", "聚餐", "高端", "宴请"]),
            ("新疆菜", "🍖", ["新疆菜", "大盘鸡", "烤肉", "聚餐"]),
            ("东北菜", "🥟", ["东北菜", "量大", "便宜", "聚餐"]),
            ("法餐", "🍷", ["法餐", "小酒馆", "约会", "高端"]),
        ]

        NAME_TEMPLATES = {
            "川菜": ["川味小馆", "麻辣空间", "蜀香居", "老成都", "麻辣诱惑"],
            "湘菜": ["湘菜馆", "湖南人家", "湘味小厨", "老长沙", "剁椒鱼头馆"],
            "粤菜": ["粤菜馆", "港式茶餐厅", "广东人家", "粤味轩", "潮汕牛肉火锅"],
            "本帮菜": ["老上海", "本帮小馆", "上海人家", "弄堂菜", "石库门"],
            "日料": ["寿司屋", "居酒屋", "日式拉面", "烧肉一筋", "寿司郎"],
            "韩餐": ["韩式烤肉", "部队火锅", "石锅拌饭", "韩料理", "韩式炸鸡"],
            "西餐": ["西餐厅", "牛排馆", "意大利餐厅", "汉堡店", "披萨店"],
            "火锅": ["火锅店", "海底捞", "小龙坎", "大龙燚", "蜀大侠"],
            "烧烤": ["烧烤摊", "撸串吧", "烤串王", "东北烧烤", "新疆烤肉"],
            "麻辣烫": ["麻辣烫", "张亮麻辣烫", "杨国福", "串串香", "冒菜"],
            "小吃": ["小吃店", "生煎包", "小笼包", "葱油饼", "煎饼果子"],
            "面食": ["面馆", "兰州拉面", "重庆小面", "老北京炸酱面", "武汉热干面"],
            "甜品": ["甜品店", "蛋糕店", "冰淇淋店", "糖水铺", "双皮奶"],
            "奶茶饮品": ["奶茶店", "喜茶", "奈雪の茶", "蜜雪冰城", "一点点"],
            "咖啡": ["星巴克", "瑞幸咖啡", "Manner Coffee", "Tims咖啡", "皮爷咖啡"],
            "轻食": ["轻食餐厅", "沙拉店", "Wagas", "新元素", "健康餐"],
            "海鲜": ["海鲜大排档", "海鲜酒楼", "舟山海鲜", "象山海鲜", "海鲜自助"],
            "新疆菜": ["新疆大盘鸡", "羊肉串大王", "新疆饭店", "西域风情", "塔里木"],
            "东北菜": ["东北菜馆", "饺子馆", "铁锅炖", "东北大拉皮", "锅包肉"],
            "法餐": ["法式小酒馆", "法餐厅", "巴黎小馆", "法式甜点", "红酒屋"],
        }

        SCENARIOS = ["一人食", "聚餐", "约会", "工作午餐", "宵夜", "早餐", "下午茶"]
        STREETS = ["南京西路", "淮海路", "徐家汇", "五角场", "陆家嘴", "人民广场", "静安寺", "中山公园", "莘庄", "四川北路"]
        DESC_WORDS = ["味道正宗", "性价比高", "环境舒适", "服务周到", "人气火爆"]
        REVIEW_CONTENTS = [
            "味道不错，下次还来！",
            "环境很好，服务周到。",
            "性价比超高，推荐！",
            "人很多，需要排队，但值得。",
            "菜品新鲜，味道正宗。",
        ]

        reviewer = db.query(User).filter(User.username == "sh_student").first()
        if not reviewer:
            reviewer = User(
                username="sh_student", email="sh@campus-food.com",
                hashed_pw=hash_password("student123"),
                nickname="上海吃货", campus="复旦", is_admin=False
            )
            db.add(reviewer)
            db.flush()

        batch_size = 200
        for batch in range(0, to_add, batch_size):
            batch_end = min(batch + batch_size, to_add)
            restaurants = []

            for i in range(batch, batch_end):
                cuisine, emoji, tags_base = random.choice(CUISINES)
                area_name, (base_lat, base_lng) = random.choice(list(SHANGHAI_AREAS.items()))

                lat = base_lat + random.uniform(-0.02, 0.02)
                lng = base_lng + random.uniform(-0.02, 0.02)

                price_ranges = [
                    (5, 15), (10, 25), (15, 35), (20, 50),
                    (30, 70), (50, 100), (80, 150), (120, 250), (200, 400),
                ]
                price_min, price_max = random.choice(price_ranges)

                name_base = random.choice(NAME_TEMPLATES.get(cuisine, ["美食小馆"]))
                suffixes = ["", "（总店）", "（分店）", "（旗舰店）", "（网红店）", "（老店）"]
                name = name_base + random.choice(suffixes)

                tags = list(tags_base)
                avg_price = (price_min + price_max) // 2
                if avg_price <= 30:
                    tags.extend(["便宜", "学生党"])
                elif avg_price <= 80:
                    tags.append("性价比高")
                else:
                    tags.extend(["高端", "约会"])
                tags.extend(random.sample(SCENARIOS, random.randint(1, 3)))

                street = random.choice(STREETS)
                street_num = random.randint(1, 999)
                address = area_name + street + str(street_num) + "号"

                open_options = [
                    "07:00-22:00", "10:00-22:00", "11:00-21:30",
                    "11:00-14:00 17:00-22:00", "06:30-20:00",
                    "16:00-02:00", "10:00-24:00", "08:00-23:00",
                ]

                desc = cuisine + "餐厅，" + random.choice(DESC_WORDS) + "。"

                r = Restaurant(
                    name=name,
                    description=desc,
                    cuisine=cuisine,
                    campus="全部",
                    address=address,
                    phone="021-" + str(random.randint(50000000, 69999999)) if random.random() > 0.3 else "",
                    open_hours=random.choice(open_options),
                    price_min=price_min,
                    price_max=price_max,
                    distance_min=random.randint(50, 500),
                    emoji=emoji,
                    tags=",".join(tags[:8]),
                    is_open=random.random() > 0.05,
                    is_featured=random.random() < 0.1,
                    is_active=True,
                    latitude=lat,
                    longitude=lng,
                    avg_rating=round(random.uniform(3.5, 5.0), 1),
                    review_count=random.randint(10, 9999),
                )
                db.add(r)
                restaurants.append(r)

            db.flush()
            print("已生成", batch_end, "/", to_add, "家餐厅")

            # 菜单
            for rest in restaurants:
                num_dishes = random.randint(2, 5)
                for j in range(num_dishes):
                    price = random.randint(rest.price_min, min(rest.price_max, rest.price_min + 50))
                    db.add(MenuItem(
                        restaurant_id=rest.id,
                        name="招牌菜" + str(j + 1),
                        description=random.choice(["招牌·必点", "人气推荐", "店长推荐", "爆款"]),
                        price=price,
                        emoji=rest.emoji,
                        is_recommended=(j == 0),
                        monthly_sold=random.randint(50, 2000),
                    ))

            # 评价
            for rest in restaurants:
                num_reviews = random.randint(1, 3)
                for _ in range(num_reviews):
                    db.add(Review(
                        restaurant_id=rest.id,
                        user_id=reviewer.id,
                        rating=round(random.uniform(3.5, 5.0), 1),
                        content=random.choice(REVIEW_CONTENTS),
                        is_anonymous=random.random() < 0.3,
                    ))

            # 团购
            for rest in restaurants:
                if random.random() < 0.4:
                    avg_p = (rest.price_min + rest.price_max) // 2
                    deal_types = [
                        ("单人套餐", "主食+饮品+小菜", max(19, int(avg_p * 0.6)), max(35, int(avg_p * 0.9))),
                        ("双人套餐", "招牌菜品+饮品+主食", max(59, int(avg_p * 2 * 0.6)), max(128, int(avg_p * 2 * 0.9))),
                        ("代金券", "全场通用", max(75, int(100 * 0.85)), 100),
                    ]
                    num_deals = random.randint(1, 2)
                    selected = random.sample(deal_types, num_deals)
                    for deal_name, deal_desc, deal_price, original_price in selected:
                        db.add(Deal(
                            restaurant_id=rest.id,
                            title=deal_name,
                            description=deal_desc,
                            original_price=original_price,
                            deal_price=deal_price,
                            discount_text=str(round(deal_price / original_price * 10, 1)) + "折",
                            valid_until=datetime(2026, 12, 31),
                            is_active=True,
                        ))

        db.commit()
        final_count = db.query(Restaurant).filter(Restaurant.latitude > 30).count()
        print("✅ 完成！上海餐厅总数:", final_count)

        menu_count = db.query(MenuItem).count()
        review_count = db.query(Review).count()
        deal_count = db.query(Deal).count()
        print("菜品总数:", menu_count)
        print("评价总数:", review_count)
        print("团购优惠:", deal_count)

    except Exception as e:
        db.rollback()
        print("❌ 失败:", e)
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    main()
