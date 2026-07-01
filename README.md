# 🍜 觅食 · 社区生活地图

> 基于 AI 的本地生活「地图选店 + 社区种草」一体化决策平台，解决「今天吃什么」的决策困境。

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-009688?logo=fastapi&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-内置无需安装-003B57?logo=sqlite&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-f4b942)

## 🖼️ 在线预览

> 无需部署，点击直接在浏览器查看所有页面效果：
>
> **[👉 点击查看在线预览 Demo](https://zjzhangjob-cmd.github.io/campus-food-map/)**

---

## ✨ 功能一览

### 🍽️ 三条核心路径

| 路径 | 说明 |
|------|------|
| 🤖 **觅食帮选** | 全屏地图 + AI 对话，一句话搞定「今天吃什么」 |
| 🔍 **我来选择** | 货架式卡片浏览，支持多维度筛选排序 |
| 👥 **社区种草** | 附近真实评价，邻里美食分享阵地 |

### 🤖 AI 能力

| 功能 | 说明 |
|------|------|
| 💬 **对话式推荐** | 自然语言表达需求（心情/预算/口味/人数），AI 精准匹配 |
| 📍 **空间感知** | 基于 LBS 实时定位，计算真实物理距离，推荐步行可达餐厅 |
| 🎭 **情绪陪伴** | 专属 IP 助手「小觅」，场景预判，提供情绪价值 |
| 🏙️ **多城切换** | 支持广州/上海双城，虚拟定位切换校区/商圈 |

### 🗺️ 地图功能

| 功能 | 说明 |
|------|------|
| 🗺️ **全屏地图模式** | 沉浸式地图浏览，餐厅气泡可视化 |
| 📌 ** Marker 标记** | 餐厅位置一目了然，点击查看详情 |
| 🧭 **一键导航** | 调起高德地图，步行/骑行路线规划 |
| 🔭 **虚拟定位** | 切换不同商圈/区域，探索周边美食 |

### 👥 社区 & 社交

| 功能 | 说明 |
|------|------|
| 💬 **社区圈** | 发帖、评论、点赞、求推荐 |
| 🏷️ **评价标签** | AI 自动提炼餐厅优缺点标签 |
| ❤️ **心愿单** | 收藏种草餐厅，想吃就存 |
| 🏆 **积分体系** | 签到/评价/PK赛获得积分 |

### 🎯 趣味玩法

| 功能 | 说明 |
|------|------|
| 🎡 **随机转盘** | 选择困难症救星，让命运帮你决定 |
| ⚔️ **美食 PK 赛** | 两两对决，选出你的最爱 |
| 🎖️ **等级徽章** | 美食达人成长体系 |

### 🛠️ 管理后台

| 功能 | 说明 |
|------|------|
| 🍜 **餐厅管理** | 增删改查餐厅信息 |
| 🎟️ **团购管理** | 优惠活动上下架 |
| 👤 **用户管理** | 用户状态管理 |
| ⭐ **评价审核** | 社区内容治理 |

---

## 🖥️ 技术栈

```
前端：HTML5 + CSS3 + Vanilla JS + 高德地图 JS API
后端：Python 3.11 + FastAPI + SQLAlchemy ORM
数据库：SQLite（内置，无需安装任何数据库）
AI：豆包 Seed 大模型 / Anthropic Claude API（选填，不填则用规则推荐）
```

---

## 📊 数据规模

当前已内置 **1193+ 家餐厅** 数据：

| 城市 | 区域 | 餐厅数量 | 说明 |
|------|------|---------|------|
| 🇬🇿 **广州** | 大学城 | 10+ | 中山大学、华南理工等高校周边 |
| 🇸🇭 **上海** | 漕河泾开发区 | 300 | 田林路/古美路/虹梅路等核心区域 |
| 🇸🇭 **上海** | 徐汇区 | 291 | 徐家汇/衡山路/建国西路等 |
| 🇸🇭 **上海** | 静安区 | 109 | 南京西路/静安寺等 |
| 🇸🇭 **上海** | 黄浦区 | ~100 | 人民广场/淮海路等 |
| 🇸🇭 **上海** | 浦东新区 | ~100 | 陆家嘴/张江等 |
| 🇸🇭 **上海** | 其他区 | ~200 | 长宁/普陀/虹口/杨浦/闵行/宝山 |

覆盖 **20+ 种菜系**：川菜、湘菜、粤菜、本帮菜、日料、韩餐、西餐、火锅、烧烤、小吃、甜品、奶茶、咖啡、轻食、海鲜、新疆菜、东北菜、法餐...

---

## 🚀 快速开始

### ⚠️ 环境要求

- macOS / Linux
- **Python 3.9 ~ 3.12**（**强烈推荐 3.11**）
- ❌ **不支持 Python 3.13 / 3.14**（pydantic-core 不兼容）

查看 Python 版本：
```bash
python3 --version
```

如果版本不对，安装 3.11：
```bash
brew install python@3.11
```

---

### 第一步：克隆项目

```bash
git clone https://github.com/zjzhangjob-cmd/campus-food-map.git
cd campus-food-map
```

---

### 第二步：创建 .env 配置文件

```bash
cp .env.example .env
```

本地开发默认使用 SQLite，复制后即可运行；数据库文件会自动生成在：

```
backend/campus_food.db
```

如需配置 AI 推荐或地图，再用文本编辑器打开 `.env`：

```bash
# 打开编辑
open -e .env
```

以下配置均为选填，不影响基本功能：
```bash
# 选填：豆包 Seed AI 推荐（推荐使用，效果更好）
SEED_API_ENDPOINT=ep-xxxxxxxxxx
SEED_API_KEY=ark-xxxxxxxxxx

# 选填：Claude AI 推荐（备选）
ANTHROPIC_API_KEY=

# 选填：高德地图 Web 服务 Key（不填地图不显示）
AMAP_KEY=

# 选填：高德地图 JS API Key（不填地图不显示）
# 申请地址：https://console.amap.com → 创建应用 → JS API
AMAP_JS_KEY=
```

---

### 第三步：初始化环境（首次运行）

```bash
bash setup.sh
```

> 如果遇到 Python 版本问题，手动执行：
> ```bash
> cd backend
> python3.11 -m venv venv
> source venv/bin/activate
> pip install -r requirements.txt --break-system-packages
> cd ..
> ```

---

### 第四步：启动项目

**终端一（后端）：**
```bash
cd backend
source venv/bin/activate
python -m app.init_db   # 首次运行建表并导入餐厅数据
uvicorn app.main:app --reload --port 8000
```

看到 `Uvicorn running on http://127.0.0.1:8000` 表示后端启动成功。

**终端二（前端）：**
```bash
cd campus-food-map   # 项目根目录
python3 -m http.server 3000 --directory frontend
```

浏览器打开：**http://localhost:3000**

---

### 页面入口

| 地址 | 说明 |
|------|------|
| http://localhost:3000 | 🌐 社区生活地图主页 |
| http://localhost:3000/fun.html | 🎯 趣味模式（转盘+PK赛）|
| http://localhost:3000/profile.html | 👤 个人主页 & 积分中心 |
| http://localhost:3000/circle.html | 👥 社区圈 |
| http://localhost:3000/login.html | 🔐 登录 / 注册 |
| http://localhost:3000/admin.html | 🛠️ 管理后台 |
| http://localhost:8000/docs | 📖 API 交互文档 |

**内置测试账号：**

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | `admin` | `admin123` |
| 普通用户 | `student` | `student123` |

---

## ❓ 常见问题

### 后端启动报数据库连接错误

本地开发应使用 SQLite。请确认 `.env` 中的数据库配置是：

```bash
DATABASE_URL=sqlite:///./campus_food.db
```

然后重新运行：

```bash
bash start.sh
```

### 餐厅加载失败 / Failed to fetch

后端没有在运行，或端口不对。

**解决：**
```bash
# 确认后端是否在跑
curl http://localhost:8000/health

# 确认前端请求的端口
grep BASE_URL frontend/assets/api.js
# 应该显示 http://localhost:8000
```

### Python 版本不兼容（3.13/3.14）

```bash
brew install python@3.11
cd backend
rm -rf venv
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 地图显示「点击配置高德地图」

需要配置高德 JS API Key：
1. 前往 [高德开放平台](https://console.amap.com) 注册并创建应用
2. 申请「JS API」类型的 Key
3. 在 `.env` 里填入：`AMAP_JS_KEY=你的Key`
4. 执行注入：
```bash
sed -i '' "s/AMAP_JS_KEY_PLACEHOLDER/你的Key/g" frontend/index.html
```

### 端口被占用

```bash
# 查看占用 8000 端口的进程
lsof -i :8000
# 杀掉进程（把 PID 换成上面看到的数字）
kill -9 PID
```

### 登录很慢或超时

说明后端没有在运行，不是代码慢。检查后端终端是否有报错，重启后端即可。

### AI 推荐不生效 / 回退到规则推荐

检查 `.env` 中的 AI 配置是否正确：

```bash
# 确认配置
grep SEED .env

# 测试 API 是否可用
curl -X POST https://ark.cn-beijing.volces.com/api/v3/chat/completions \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"ep-xxx","messages":[{"role":"user","content":"hi"}]}'
```

---

## 📁 项目结构

```
campus-food-map/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── init_db.py           # 数据库初始化 & 示例餐厅数据
│   │   ├── api/                 # 路由：auth/restaurants/reviews/ai/admin/points
│   │   ├── models/              # SQLAlchemy 数据库模型
│   │   ├── schemas/             # Pydantic 数据验证
│   │   ├── core/                # 配置/数据库连接/JWT 认证
│   │   └── services/            # AI 推荐服务（Seed + Claude + 规则）
│   └── requirements.txt
├── frontend/
│   ├── index.html               # 主页（社区生活地图 + 全屏AI模式）
│   ├── fun.html                 # 趣味模式（转盘+PK赛）
│   ├── profile.html             # 个人主页 & 积分中心
│   ├── circle.html              # 社区圈
│   ├── login.html               # 登录 / 注册
│   ├── admin.html               # 管理后台
│   └── assets/api.js            # 统一 API 请求封装
├── docs/
│   └── index.html               # GitHub Pages 在线预览
├── setup.sh                     # 初始化脚本
├── start.sh                     # 启动脚本（含高德Key注入）
├── stop.sh                      # 停止脚本
├── .env.example                 # 环境变量模板
└── .gitignore
```

---

## 🔌 主要 API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/auth/register` | 用户注册 |
| POST | `/api/auth/login` | 用户登录 |
| GET  | `/api/restaurants` | 餐厅列表（筛选/排序/分页）|
| GET  | `/api/restaurants/{id}` | 餐厅详情 |
| POST | `/api/restaurants/{id}/favorite` | 收藏/取消 |
| POST | `/api/reviews` | 发布评价 |
| POST | `/api/ai/chat` | AI 对话推荐（多轮对话）|
| POST | `/api/ai/recommend` | AI 推荐（单次）|
| GET  | `/api/points/me` | 我的积分 |
| POST | `/api/points/earn` | 获取积分 |
| POST | `/api/points/redeem` | 兑换积分 |
| GET  | `/api/points/ranking` | 积分排行榜 |

完整文档：http://localhost:8000/docs

---

## 📄 License

MIT License · 欢迎 Star ⭐ 和 Fork 🍴
