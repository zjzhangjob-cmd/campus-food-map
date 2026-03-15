# 🍜 觅食 · 大学城美食地图

> 专为大学城学生打造的本地化美食发现平台，解决「今天吃什么」的决策困境。

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

| 功能 | 说明 |
|------|------|
| 🔍 智能搜索 | 按名称、菜系、标签实时搜索 |
| 🤖 AI 推荐 | 描述心情即可获得个性化推荐 |
| 🗺️ 高德地图 | 餐厅位置可视化，点击定位，一键导航 |
| 🎟️ 学生优惠 | 聚合周边优惠活动 |
| ❤️ 收藏 & 评价 | 登录后可收藏餐厅、发布评价 |
| 🎯 趣味模式 | 随机转盘 + 美食PK赛，还能赚积分 |
| 🏆 积分体系 | 签到/评价/PK赛获得积分，兑换优惠券 |
| 👤 个人主页 | 积分等级、美食专家徽章、收藏、关注 |
| 👥 校园圈 | 发帖、评论、点赞、求推荐 |
| 🛠️ 管理后台 | 餐厅 / 优惠 / 用户 / 评价管理 |

---

## 🖥️ 技术栈

```
前端：HTML5 + CSS3 + Vanilla JS + 高德地图 JS API
后端：Python 3.11 + FastAPI + SQLAlchemy ORM
数据库：SQLite（内置，无需安装任何数据库）
AI：Anthropic Claude API（选填，不填则用规则推荐）
```

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

用文本编辑器打开 `.env`，**只需改这一行**（把路径换成你电脑上的实际路径）：

```bash
# 打开编辑
open -e .env
```

找到这一行，改成你的实际路径：
```
DATABASE_URL=sqlite:////你的用户名/路径/campus-food-map/backend/campus_food.db
```

例如用户名是 `zhangsan`，路径是 Downloads：
```
DATABASE_URL=sqlite:////Users/zhangsan/Downloads/campus-food-map/backend/campus_food.db
```

> 💡 查看你的实际路径：在终端执行 `pwd`，把结果中的 `campus-food-map` 后面加上 `/backend/campus_food.db`

其余配置均为选填，不影响基本功能：
```bash
# 选填：Claude AI 推荐（不填则用规则推荐，功能正常）
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
| http://localhost:3000 | 🌐 美食地图主页 |
| http://localhost:3000/fun.html | 🎯 趣味模式（转盘+PK赛）|
| http://localhost:3000/profile.html | 👤 个人主页 & 积分中心 |
| http://localhost:3000/circle.html | 👥 校园圈 |
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

### 后端启动报 MySQL 连接错误

`.env` 里的 `DATABASE_URL` 路径不对，或者 `config.py` 默认值是 MySQL。

**解决：** 直接在终端覆盖 config.py 的默认值：
```bash
cat > backend/app/core/config.py << 'EOF'
from pydantic_settings import BaseSettings
from typing import List
import os

_ENV_PATH = os.path.join(os.path.dirname(__file__), "../../../.env")

class Settings(BaseSettings):
    APP_NAME: str = "觅食·大学城美食地图"
    DEBUG: bool = True
    DATABASE_URL: str = "sqlite:///./campus_food.db"
    SECRET_KEY: str = "campus-food-map-secret-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 10080
    ANTHROPIC_API_KEY: str = ""
    AMAP_KEY: str = ""
    AMAP_JS_KEY: str = ""
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    @property
    def origins(self) -> List[str]:
        return [o.strip() for o in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        env_file = _ENV_PATH
        extra = "ignore"

settings = Settings()
EOF
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
│   │   └── services/            # Claude AI 推荐服务
│   └── requirements.txt
├── frontend/
│   ├── index.html               # 主页（美食地图）
│   ├── fun.html                 # 趣味模式（转盘+PK赛）
│   ├── profile.html             # 个人主页 & 积分中心
│   ├── circle.html              # 校园圈
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
| POST | `/api/ai/recommend` | AI 推荐 |
| GET  | `/api/points/me` | 我的积分 |
| POST | `/api/points/earn` | 获取积分 |
| POST | `/api/points/redeem` | 兑换积分 |
| GET  | `/api/points/ranking` | 积分排行榜 |

完整文档：http://localhost:8000/docs

---

## 📄 License

MIT License · 欢迎 Star ⭐ 和 Fork 🍴
