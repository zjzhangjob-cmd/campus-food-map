"""添加上海高校周边餐厅 & 校园圈评价数据"""
from app.core.database import SessionLocal
from app.models.models import Restaurant, MenuItem, Review, User
from app.core.security import hash_password


def add_shanghai_data():
    db = SessionLocal()
    try:
        # 检查是否已有上海数据（通过纬度判断，上海纬度>31，广州纬度~23）
        existing_sh = db.query(Restaurant).filter(Restaurant.latitude > 30).count()
        if existing_sh > 0:
            print("✅ 上海数据已存在，跳过")
            return

        # 确保有上海用户
        user_sh = db.query(User).filter(User.username == "sh_student").first()
        if not user_sh:
            user_sh = User(
                username="sh_student", email="sh@campus-food.com",
                hashed_pw=hash_password("student123"),
                nickname="复旦小李", campus="复旦", is_admin=False
            )
            db.add(user_sh)
            db.flush()

        # 上海高校坐标
        # 复旦大学邯郸校区：31.2914, 121.5070
        # 上海交通大学徐汇校区：31.1935, 121.4367
        # 同济大学四平路校区：31.2936, 121.4998
        # 华东师范大学中山北路校区：31.2364, 121.4065
        # 上海财经大学：31.3112, 121.5103

        restaurants_data = [
            # 复旦周边
            dict(
                name="老盛兴汤包馆（复旦店）",
                description="上海老字号汤包馆，蟹粉汤包是招牌，皮薄馅大汤汁鲜美。鲜肉汤包、小笼包、三鲜大馄饨都是必点。开了二十多年的老店，复旦学子的集体回忆。",
                cuisine="中餐", campus="复旦",
                address="杨浦区国定路450号", phone="021-6511-2234",
                open_hours="06:30-21:00", price_min=15, price_max=35,
                emoji="🥟", tags="汤包,小笼,老字号,早餐,复旦周边,便宜",
                is_featured=True, avg_rating=4.8, review_count=4231,
                latitude=31.2932, longitude=121.5052
            ),
            dict(
                name="大学路烧肉一筋",
                description="日式烧肉店，和牛五花、牛舌是必点，肉质鲜嫩入口即化。装修有格调，适合聚餐约会。午市套餐性价比高，人均80元吃到饱。",
                cuisine="日料", campus="复旦",
                address="杨浦区大学路189号", phone="021-5566-7788",
                open_hours="11:30-22:30", price_min=80, price_max=150,
                emoji="🥩", tags="烧肉,日料,和牛,聚餐,约会,大学路",
                is_featured=False, avg_rating=4.6, review_count=1892,
                latitude=31.2956, longitude=121.5087
            ),
            dict(
                name="阿大葱油饼",
                description="上海网红葱油饼，酥脆外皮层层起酥，葱油香气扑鼻。每天限量200个，排队是常态。现做现卖，趁热吃最香。",
                cuisine="小吃", campus="复旦",
                address="杨浦区政通路23号", phone="",
                open_hours="06:00-11:00", price_min=5, price_max=12,
                emoji="🫓", tags="葱油饼,早餐,网红,排队,便宜,限量",
                is_featured=True, avg_rating=4.9, review_count=6782,
                latitude=31.2925, longitude=121.5043
            ),
            dict(
                name="Manner Coffee（复旦店）",
                description="精品咖啡连锁，性价比之王。燕麦拿铁、桂花拿铁是爆款。自带杯减5元，学生党福音。店面虽小但出杯快，上课路上顺手买一杯。",
                cuisine="西餐", campus="复旦",
                address="杨浦区邯郸路220号复旦校内", phone="",
                open_hours="07:30-20:00", price_min=15, price_max=28,
                emoji="☕", tags="咖啡,精品咖啡,性价比,学生最爱,拿铁,自带杯",
                is_featured=False, avg_rating=4.7, review_count=3421,
                latitude=31.2914, longitude=121.5070
            ),
            # 交大周边
            dict(
                name="小杨生煎（交大店）",
                description="上海生煎代表，皮薄底脆汤汁多。鲜肉生煎是经典，咬开爆汁。配一碗牛肉粉丝汤绝配。开了30多年的连锁品牌，品质稳定。",
                cuisine="中餐", campus="交大",
                address="徐汇区华山路1888号", phone="021-6282-3344",
                open_hours="07:00-21:30", price_min=12, price_max=28,
                emoji="🥟", tags="生煎,上海小吃,老字号,便宜,早餐,爆汁",
                is_featured=True, avg_rating=4.8, review_count=5432,
                latitude=31.1956, longitude=121.4345
            ),
            dict(
                name="交大东门麻辣烫",
                description="开了20年的麻辣烫老店，交大学子的深夜食堂。汤底用骨头熬制，食材新鲜种类多。晚上10点后人最多，排队也要吃。",
                cuisine="中餐", campus="交大",
                address="徐汇区番禺路69号", phone="",
                open_hours="10:00-02:00", price_min=18, price_max=38,
                emoji="🍲", tags="麻辣烫,宵夜,20年老店,便宜,交大周边,深夜食堂",
                is_featured=False, avg_rating=4.5, review_count=2987,
                latitude=31.1942, longitude=121.4389
            ),
            dict(
                name="Bistro 11 法餐小馆",
                description="隐蔽在弄堂里的法式小酒馆，鹅肝慕斯、松露意面是招牌。环境浪漫有氛围，适合约会庆祝。老板是留法回来的，很地道。",
                cuisine="西餐", campus="交大",
                address="徐汇区武康路11号", phone="021-5404-2011",
                open_hours="11:30-23:00", price_min=120, price_max=250,
                emoji="🍷", tags="法餐,小酒馆,约会,武康路,浪漫,松露",
                is_featured=False, avg_rating=4.7, review_count=876,
                latitude=31.2078, longitude=121.4356
            ),
            # 同济周边
            dict(
                name="同济大学食堂排骨年糕",
                description="同济大排面是传说中的校园美食，排骨外酥里嫩，面条筋道。食堂对外开放，校友返校必打卡。还有年糕炸串，性价比超高。",
                cuisine="中餐", campus="同济",
                address="杨浦区四平路1239号同济校内", phone="",
                open_hours="06:30-20:00", price_min=10, price_max=20,
                emoji="🍖", tags="食堂,排骨年糕,同济特色,便宜,校园美食,大排面",
                is_featured=True, avg_rating=4.9, review_count=8765,
                latitude=31.2936, longitude=121.4998
            ),
            dict(
                name="彰武路小龙虾",
                description="同济学生的宵夜圣地，十三香小龙虾、蒜香小龙虾是招牌。夏天露天座爆满，喝啤酒吃小龙虾，毕业季最热闹。",
                cuisine="中餐", campus="同济",
                address="杨浦区彰武路45号", phone="021-6598-1122",
                open_hours="16:00-03:00", price_min=50, price_max=120,
                emoji="🦐", tags="小龙虾,宵夜,啤酒,聚餐,毕业季,蒜香",
                is_featured=False, avg_rating=4.6, review_count=3456,
                latitude=31.2951, longitude=121.4975
            ),
            # 华师大周边
            dict(
                name="华师大后门黑暗料理街",
                description="华师大后门的黑暗料理一条街，煎饼果子、烤冷面、手抓饼、臭豆腐应有尽有。每晚6点后出摊，学生们的深夜慰藉。",
                cuisine="小吃", campus="华师大",
                address="普陀区枣阳路华师大后门", phone="",
                open_hours="18:00-24:00", price_min=5, price_max=15,
                emoji="🌯", tags="地摊,黑暗料理,宵夜,便宜,华师大,网红",
                is_featured=True, avg_rating=4.7, review_count=9234,
                latitude=31.2387, longitude=121.4045
            ),
            dict(
                name="长风公园酸菜鱼",
                description="开在长风公园旁边的酸菜鱼老店，鱼肉鲜嫩汤底酸爽。性价比超高，人均40元吃到饱。学生聚餐首选地，周末经常要等位。",
                cuisine="中餐", campus="华师大",
                address="普陀区枣阳路188号", phone="021-6286-5566",
                open_hours="10:00-22:00", price_min=35, price_max=65,
                emoji="🐟", tags="酸菜鱼,川菜,聚餐,便宜,华师大,酸爽",
                is_featured=False, avg_rating=4.5, review_count=2341,
                latitude=31.2356, longitude=121.4023
            ),
            # 上财周边
            dict(
                name="武东路老上海面馆",
                description="开了30年的老面馆，大肠面、辣肉面是招牌。汤头用骨头和鸡熬制，面条是手工拉面。上财学生的第二食堂。",
                cuisine="中餐", campus="上财",
                address="杨浦区武东路100号", phone="021-6510-9988",
                open_hours="06:00-20:00", price_min=15, price_max=32,
                emoji="🍜", tags="本帮面,老面馆,大肠面,上财周边,便宜,早餐",
                is_featured=True, avg_rating=4.8, review_count=4567,
                latitude=31.3125, longitude=121.5087
            ),
            dict(
                name="上财门口奶茶铺",
                description="开在上财门口的奶茶店，芝士奶盖、芋圆奶茶是爆款。料足味美，排队是常态。学生凭校园卡打九折。",
                cuisine="饮品", campus="上财",
                address="杨浦区武川路111号", phone="",
                open_hours="09:00-23:00", price_min=12, price_max=22,
                emoji="🧋", tags="奶茶,芝士奶盖,上财,便宜,学生优惠,芋圆",
                is_featured=False, avg_rating=4.6, review_count=5678,
                latitude=31.3105, longitude=121.5112
            ),
        ]

        restaurants = []
        for r_data in restaurants_data:
            r = Restaurant(**r_data)
            db.add(r)
            restaurants.append(r)
        db.flush()
        print(f"✅ 新增 {len(restaurants)} 家上海餐厅")

        # 添加菜单
        menus = [
            (0, "蟹粉汤包", "招牌·必点", 32, "🥟", True, 850),
            (0, "鲜肉小笼", "经典上海味", 18, "🥟", True, 1200),
            (2, "经典葱油饼", "酥脆·现做", 5, "🫓", True, 2800),
            (3, "燕麦拿铁", "爆款·推荐", 20, "☕", True, 1500),
            (4, "鲜肉生煎", "爆汁·招牌", 15, "🥟", True, 2000),
            (5, "麻辣烫套餐", "荤素搭配", 25, "🍲", True, 900),
            (7, "同济大排面", "校园传奇", 15, "🍖", True, 3000),
            (8, "十三香小龙虾", "宵夜必备", 98, "🦐", True, 600),
            (11, "酸菜鱼大份", "3-4人餐", 88, "🐟", True, 500),
            (12, "大肠面", "招牌推荐", 28, "🍜", True, 1200),
        ]
        for idx, name, desc, price, emoji, rec, sold in menus:
            if idx < len(restaurants):
                db.add(MenuItem(
                    restaurant_id=restaurants[idx].id,
                    name=name, description=desc, price=price, emoji=emoji,
                    is_recommended=rec, monthly_sold=sold
                ))
        print(f"✅ 新增 {len(menus)} 道招牌菜")

        # 添加校园圈评价
        review_contents = [
            ("复旦小李", "老盛兴的汤包真的绝了，每次来都要吃两笼！汤汁鲜甜，皮薄馅足，不愧是老字号。", 4.9),
            ("复旦小王", "阿大葱油饼名不虚传，早上7点去排了20分钟，刚出锅的酥脆到掉渣，太香了！", 5.0),
            ("交大阿杰", "小杨生煎还是熟悉的味道，一口爆汁，配牛肉粉丝汤绝了。大学四年吃了无数次。", 4.8),
            ("交大小周", "交大东门麻辣烫是我们寝室的深夜食堂，每次写论文写到崩溃就来吃一顿，治愈！", 4.6),
            ("同济小张", "同济大排面真的是神，毕业五年了还经常回去吃，一口就回到学生时代。", 5.0),
            ("同济小李", "彰武路小龙虾yyds！毕业季全班一起来吃，喝啤酒吃小龙虾，青春的味道。", 4.7),
            ("华师大小芳", "后门黑暗料理街是我减肥路上最大的阻碍，煎饼果子太好吃了😭", 4.8),
            ("华师大阿明", "长风公园酸菜鱼性价比超高，部门聚餐每次都去，人均40吃到撑。", 4.5),
            ("上财小陈", "武东路老面馆的大肠面太绝了，从上财入学吃到毕业，老板都认识我了。", 4.9),
            ("上财小周", "奶茶铺的芝士奶盖YYDS，写代码续命全靠它，期末周一天一杯。", 4.6),
            ("复旦老学姐", "Manner咖啡性价比真的高，自带杯减5块，燕麦拿铁yyds，写论文必备！", 4.7),
            ("交大学霸", "Bistro 11的法餐太惊喜了，约会首选，环境好味道正，就是有点小贵。", 4.6),
        ]

        # 找到一个可用的用户作为评价者
        reviewer = db.query(User).first()
        for i, (username, content, rating) in enumerate(review_contents):
            # 每个评价对应不同餐厅
            rest_idx = i % len(restaurants)
            db.add(Review(
                restaurant_id=restaurants[rest_idx].id,
                user_id=reviewer.id,
                rating=rating,
                content=content,
                is_anonymous=(i % 3 == 0),
            ))
        print(f"✅ 新增 {len(review_contents)} 条校园圈评价")

        db.commit()
        print("🎉 上海数据全部添加完成！")
    except Exception as e:
        db.rollback()
        print(f"❌ 失败：{e}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    add_shanghai_data()
