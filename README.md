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
| 🎟️ 学生优惠 | 聚合周边优惠活动，一键领取 |
| ❤️ 收藏 & 评价 | 登录后可收藏餐厅、发布评价 |
| 🏆 口碑榜 | 实时评分排名 |
| 👥 校园圈 | 发帖、评论、点赞、求推荐 |
| 🛠️ 管理后台 | 餐厅 / 优惠 / 用户 / 评价管理 |

---

## 🖥️ 技术栈

```
前端：HTML5 + CSS3 + Vanilla JS + 高德地图 JS API
后端：Python 3.11 + FastAPI + SQLAlchemy ORM
数据库：SQLite（内置，无需安装任何数据库）
AI：Anthropic Claude API（选填）
```

---

## 🚀 快速开始（3步启动）

### 环境要求

- macOS / Linux
- Python 3.9 ~ 3.13（**推荐 3.11**，3.14 暂不支持）

> ⚠️ 如果你是 Python 3.14，请先安装 3.11：
> ```bash
> brew install python@3.11
> ```

---

### 第一步：克隆项目

```bash
git clone https://github.com/你的用户名/campus-food-map.git
cd campus-food-map
```

---

### 第二步：一键初始化

```bash
bash setup.sh
```

首次运行会生成 `.env` 文件，**用文本编辑器打开填写配置后再运行一次**：

```bash
open -e .env   # macOS
```

**.env 只需填这一行（其余可选）：**

```bash
# SQLite 无需安装数据库，保持默认即可
DATABASE_URL=sqlite:////完整路径/campus-food-map/backend/campus_food.db

# 可选：Claude AI 推荐（不填则用规则推荐，功能正常）
# 申请：https://console.anthropic.com
ANTHROPIC_API_KEY=sk-ant-xxxxxxxx

# 可选：高德地图（不填则显示占位图）
# 申请：https://console.amap.com → Web服务 Key
AMAP_KEY=你的高德Key
```

> 💡 `DATABASE_URL` 中的完整路径示例：
> `/Users/yourname/Downloads/campus-food-map/backend/campus_food.db`

再次运行初始化：
```bash
bash setup.sh
```

---

### 第三步：启动

```bash
bash start.sh
```

浏览器自动打开，访问地址：

| 地址 | 说明 |
|------|------|
| http://localhost:3000 | 🌐 美食地图主页 |
| http://localhost:3000/login.html | 🔐 登录 / 注册 |
| http://localhost:3000/admin.html | 🛠️ 管理后台 |
| http://localhost:3000/circle.html | 👥 校园圈 |
| http://localhost:8000/docs | 📖 API 交互文档 |

**内置测试账号：**

| 角色 | 用户名 | 密码 |
|------|--------|------|
| 管理员 | `admin` | `admin123` |
| 普通用户 | `student` | `student123` |

```bash
bash stop.sh   # 停止所有服务
```

---

## 📁 项目结构

```
campus-food-map/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── init_db.py           # 数据库初始化 & 10家示例餐厅
│   │   ├── api/                 # 路由：auth / restaurants / reviews / ai / admin
│   │   ├── models/              # SQLAlchemy 数据库模型
│   │   ├── schemas/             # Pydantic 数据验证
│   │   ├── core/                # 配置 / 数据库连接 / JWT 认证
│   │   └── services/            # Claude AI 推荐服务
│   └── requirements.txt
├── frontend/
│   ├── index.html               # 主页（美食地图）
│   ├── login.html               # 登录 / 注册
│   ├── admin.html               # 管理后台
│   ├── circle.html              # 校园圈
│   └── assets/api.js            # 统一 API 请求封装
├── setup.sh                     # 初始化脚本
├── start.sh                     # 启动脚本
├── stop.sh                      # 停止脚本
├── update.sh                    # 更新脚本
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
| POST | `/api/restaurants/{id}/favorite` | 收藏 / 取消 |
| POST | `/api/reviews` | 发布评价 |
| POST | `/api/ai/recommend` | AI 推荐 |
| GET  | `/api/admin/stats` | 管理员统计 |

完整交互文档：http://localhost:8000/docs

---

## ❓ 常见问题

**Python 3.14 安装依赖失败**
```bash
brew install python@3.11
cd backend && rm -rf venv
python3.11 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
```

**端口被占用**
```bash
lsof -i :8000   # 查看占用进程
kill -9 <PID>   # 终止进程
```

**餐厅加载失败 / Failed to fetch**
```bash
# 确认后端在运行
curl http://localhost:8000/health
# 确认 api.js 端口正确
grep BASE_URL frontend/assets/api.js
```

**数据库重置（清空所有数据重新初始化）**
```bash
rm backend/campus_food.db
cd backend && source venv/bin/activate && python -m app.init_db
```

---

## 🔄 更新到最新版本

```bash
cd campus-food-map
bash update.sh
```

---

## 📄 License

MIT License — 自由使用，欢迎 Star ⭐ 和 Fork 🍴
