#!/bin/bash
# =============================================================
#  觅食·大学城美食地图 — 一键初始化脚本（Mac / Linux）
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

# ── 2. 确认本地数据库模式 ──────────────────────────────────────
echo -e "${BLUE}[2/5] 确认数据库模式...${NC}"
echo -e "${GREEN}✓ 本地开发默认使用 SQLite，无需安装 MySQL/PostgreSQL${NC}"

# ── 3. 配置 .env ─────────────────────────────────────────────
echo -e "${BLUE}[3/5] 配置环境变量...${NC}"
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo -e "${GREEN}✓ 已创建 .env 文件${NC}"
  echo ""
  echo -e "${BOLD}可选配置：${NC}"
  echo "  1. ANTHROPIC_API_KEY（AI 推荐；不填则使用规则推荐）"
  echo "  2. AMAP_KEY / AMAP_JS_KEY（高德地图；不填则显示占位图）"
  echo ""
  echo -e "  如需配置，可用编辑器打开：${CYAN}open -e .env${NC}  或  ${CYAN}nano .env${NC}"
  echo ""
else
  echo -e "${GREEN}✓ .env 已存在${NC}"
fi

# ── 4. 确认 SQLite 数据文件 ─────────────────────────────────────
echo -e "${BLUE}[4/5] 准备 SQLite 数据库...${NC}"
echo -e "${GREEN}✓ 首次启动时会自动创建 backend/campus_food.db 并导入示例数据${NC}"

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
