# 🍜 觅食 · 大学城美食地图

> 专为大学城学生打造的本地化美食发现平台，解决「今天吃什么」的决策困境。

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green?logo=fastapi)
![MySQL](https://img.shields.io/badge/MySQL-8.0-orange?logo=mysql)
![License](https://img.shields.io/badge/License-MIT-lightgrey)

---

## ✨ 功能特性

| 功能 | 说明 |
|------|------|
| 🔍 餐厅搜索 | 按名称、菜系、标签实时搜索 |
| 🤖 AI 推荐 | 接入 Claude API，描述心情即可推荐 |
| 🗺️ 高德地图 | 餐厅位置可视化，一键导航 |
| 🎓 学生优惠 | 聚合周边优惠活动 |
| ❤️ 收藏 & 评价 | 登录后可收藏餐厅、发布评价 |
| 🏆 口碑榜 | 实时评分排名 |
| 🔐 用户系统 | JWT 登录注册，权限分级 |
| 🛠️ 管理后台 | 餐厅/优惠/用户/评价管理 |

---

## 🖥️ 技术栈

```
前端：HTML5 + CSS3 + Vanilla JS + 高德地图 JS API
后端：Python 3.11 + FastAPI + SQLAlchemy ORM
数据库：MySQL 8.0
AI：Anthropic Claude API
```

---

## 🚀 快速开始

### 环境要求

- macOS / Linux
- Python 3.9+
- MySQL 8.0+

---

### 第一步：克隆项目

```bash
git clone https://github.com/你的用户名/campus-food-map.git
cd campus-food-map
```

---

### 第二步：安装 MySQL（macOS）

```bash
# 安装 Homebrew（已有则跳过）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 安装并启动 MySQL
brew install mysql
brew services start mysql

# 设置 root 密码
mysql_secure_installation
```

---

### 第三步：一键初始化

```bash
bash setup.sh
```

脚本会自动：检查环境、生成 .env、创建数据库、安装 Python 依赖。

> 首次运行会生成 .env，**填写配置后再运行一次** `bash setup.sh`。

---

### 第四步：填写配置

```bash
open -e .env    # macOS 用文本编辑器打开
```

**.env 必填：**

```bash
# 替换为你的 MySQL 密码
DATABASE_URL=mysql+pymysql://root:你的MySQL密码@localhost:3306/campus_food?charset=utf8mb4

# 可选：Claude AI 推荐（申请：https://console.anthropic.com）
ANTHROPIC_API_KEY=sk-ant-xxxxxxxx

# 可选：高德地图（申请：https://console.amap.com → Web服务Key）
AMAP_KEY=你的高德Key
```

**高德地图还需配置前端（可选）：**

打开 `frontend/index.html` 第 8 行，将 `YOUR_AMAP_JS_KEY` 替换为高德 **JS API Key**：
```html
<script src="https://webapi.amap.com/maps?v=2.0&key=YOUR_AMAP_JS_KEY"></script>
```

---

### 第五步：启动

```bash
bash start.sh
```

| 地址 | 说明 |
|------|------|
| http://localhost:3000 | 🌐 美食地图主页 |
| http://localhost:3000/admin.html | 🛠️ 管理后台 |
| http://localhost:8000/docs | 📖 API 文档 |

内置账号：管理员 `admin/admin123`，用户 `student/student123`

```bash
bash stop.sh    # 停止所有服务
```

---

## 📁 项目结构

```
campus-food-map/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── init_db.py           # 数据库初始化 & 种子数据
│   │   ├── api/                 # 路由：auth/restaurants/reviews/ai/admin
│   │   ├── models/              # SQLAlchemy 数据库模型
│   │   ├── schemas/             # Pydantic 数据验证
│   │   ├── core/                # 配置/数据库/JWT
│   │   └── services/            # Claude AI 服务
│   └── requirements.txt
├── frontend/
│   ├── index.html               # 主页
│   ├── login.html               # 登录/注册
│   ├── admin.html               # 管理后台
│   └── assets/api.js            # API 请求封装
├── setup.sh                     # 初始化脚本
├── start.sh                     # 启动脚本
├── stop.sh                      # 停止脚本
├── .env.example                 # 环境变量模板（安全，可上传）
└── .gitignore                   # 排除 .env 等敏感文件
```

---

## ❓ 常见问题

**MySQL 连接失败** → `brew services restart mysql`，确认密码正确

**端口被占用** → `lsof -i :8000` 查看进程，`kill -9 <PID>` 终止

**M1/M2/M3 依赖安装失败** → 先运行 `xcode-select --install`

**AI 不工作** → 未填 Key 时自动退化为规则推荐，不影响其他功能

---

## 📄 License

MIT License — 自由使用，欢迎 Star ⭐
