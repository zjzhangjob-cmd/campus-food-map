#!/bin/bash
# =============================================================
#  觅食·大学城美食地图 — 一键启动脚本（Mac / Linux）
#  用法：bash setup.sh
# =============================================================

set -e  # 任何命令失败立即退出

# 颜色
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

echo ""
echo -e "${CYAN}${BOLD}======================================${NC}"
echo -e "${CYAN}${BOLD}  🍜  觅食·大学城美食地图            ${NC}"
echo -e "${CYAN}${BOLD}  一键初始化脚本                      ${NC}"
echo -e "${CYAN}${BOLD}======================================${NC}"
echo ""

# ── 1. 检查 Python ──────────────────────────────────────────
echo -e "${BLUE}[1/5] 检查 Python 环境...${NC}"
if ! command -v python3 &>/dev/null; then
  echo -e "${RED}✗ 未找到 python3，请先安装：https://www.python.org${NC}"
  exit 1
fi
PY_VER=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo -e "${GREEN}✓ Python $PY_VER${NC}"

# ── 2. 检查 MySQL ────────────────────────────────────────────
echo -e "${BLUE}[2/5] 检查 MySQL...${NC}"
if ! command -v mysql &>/dev/null; then
  echo -e "${YELLOW}⚠ 未找到 mysql，尝试用 Homebrew 安装...${NC}"
  if command -v brew &>/dev/null; then
    brew install mysql
    brew services start mysql
    echo -e "${GREEN}✓ MySQL 安装完成，请运行 mysql_secure_installation 设置密码${NC}"
  else
    echo -e "${RED}✗ 请手动安装 MySQL：https://dev.mysql.com/downloads/${NC}"
    exit 1
  fi
else
  echo -e "${GREEN}✓ MySQL 已安装${NC}"
fi

# ── 3. 配置 .env ─────────────────────────────────────────────
echo -e "${BLUE}[3/5] 配置环境变量...${NC}"
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo -e "${YELLOW}⚠ 已创建 .env 文件，请填写配置后重新运行脚本${NC}"
  echo ""
  echo -e "${BOLD}需要填写的内容：${NC}"
  echo "  1. DATABASE_URL 中的 MySQL 密码"
  echo "  2. ANTHROPIC_API_KEY（可选，AI推荐功能）"
  echo "  3. AMAP_KEY（可选，高德地图）"
  echo ""
  echo -e "  用编辑器打开：${CYAN}open -e .env${NC}  或  ${CYAN}nano .env${NC}"
  echo ""
  exit 0
else
  echo -e "${GREEN}✓ .env 已存在${NC}"
fi

# ── 4. 创建数据库 ─────────────────────────────────────────────
echo -e "${BLUE}[4/5] 初始化 MySQL 数据库...${NC}"
# 从 .env 提取密码
DB_URL=$(grep "^DATABASE_URL" .env | cut -d'=' -f2-)
DB_PASS=$(echo "$DB_URL" | sed 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/')
DB_HOST=$(echo "$DB_URL" | sed 's/.*@\([^:\/]*\).*/\1/')
DB_PORT=$(echo "$DB_URL" | sed 's/.*:\([0-9]*\)\/.*/\1/')
DB_NAME=$(echo "$DB_URL" | sed 's/.*\/\([^?]*\).*/\1/')

if mysql -u root -p"$DB_PASS" -h "$DB_HOST" -P "$DB_PORT" -e "USE $DB_NAME;" 2>/dev/null; then
  echo -e "${GREEN}✓ 数据库 $DB_NAME 已存在${NC}"
else
  echo -e "${YELLOW}  创建数据库 $DB_NAME ...${NC}"
  mysql -u root -p"$DB_PASS" -h "$DB_HOST" -P "$DB_PORT" \
    -e "CREATE DATABASE IF NOT EXISTS $DB_NAME CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;" \
    && echo -e "${GREEN}✓ 数据库创建成功${NC}" \
    || { echo -e "${RED}✗ 数据库创建失败，请检查 MySQL 密码和服务状态${NC}"; exit 1; }
fi

# ── 5. Python 虚拟环境 & 依赖 ────────────────────────────────
echo -e "${BLUE}[5/5] 安装 Python 依赖...${NC}"
cd backend
if [ ! -d "venv" ]; then
  python3 -m venv venv
  echo -e "${GREEN}✓ 虚拟环境已创建${NC}"
fi
source venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo -e "${GREEN}✓ 依赖安装完成${NC}"
cd ..

# ── 完成 ─────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}======================================${NC}"
echo -e "${GREEN}${BOLD}  ✅ 初始化完成！                     ${NC}"
echo -e "${GREEN}${BOLD}======================================${NC}"
echo ""
echo -e "  现在运行：${CYAN}${BOLD}bash start.sh${NC}"
echo ""
