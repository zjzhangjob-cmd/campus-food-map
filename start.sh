#!/bin/bash
# =============================================================
#  觅食·大学城美食地图 — 启动脚本（Mac / Linux）
#  用法：bash start.sh
# =============================================================

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
BLUE='\033[0;34m'; CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

# 检查 .env
if [ ! -f ".env" ]; then
  echo -e "${RED}✗ 未找到 .env 文件，请先运行：bash setup.sh${NC}"
  exit 1
fi

# 检查虚拟环境
if [ ! -d "backend/venv" ]; then
  echo -e "${RED}✗ 未找到虚拟环境，请先运行：bash setup.sh${NC}"
  exit 1
fi

echo ""
echo -e "${CYAN}${BOLD}🍜  启动觅食·大学城美食地图${NC}"
echo ""

# ── 启动后端 ──────────────────────────────────────────────────
echo -e "${BLUE}▶ 启动后端 (FastAPI)...${NC}"
cd backend
source venv/bin/activate

# 初始化数据库（建表 + 种子数据，已有数据自动跳过）
python -m app.init_db

# 后台启动 uvicorn，日志写入 backend.log
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload \
  > ../logs/backend.log 2>&1 &
BACKEND_PID=$!
echo $BACKEND_PID > ../logs/backend.pid
cd ..

# 等待后端就绪
echo -n "  等待后端启动"
for i in {1..20}; do
  sleep 0.5
  if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e " ${GREEN}✓${NC}"
    break
  fi
  echo -n "."
done

# ── 启动前端 ──────────────────────────────────────────────────
echo -e "${BLUE}▶ 启动前端 (静态服务器)...${NC}"
mkdir -p logs
nohup python3 -m http.server 3000 --directory frontend \
  > logs/frontend.log 2>&1 &
FRONTEND_PID=$!
echo $FRONTEND_PID > logs/frontend.pid

sleep 0.5

# ── 完成提示 ─────────────────────────────────────────────────
echo ""
echo -e "${GREEN}${BOLD}======================================${NC}"
echo -e "${GREEN}${BOLD}  ✅ 服务已启动！                     ${NC}"
echo -e "${GREEN}${BOLD}======================================${NC}"
echo ""
echo -e "  🌐 美食地图主页    ${CYAN}http://localhost:3000${NC}"
echo -e "  🔧 管理后台        ${CYAN}http://localhost:3000/admin.html${NC}"
echo -e "  📖 API 文档        ${CYAN}http://localhost:8000/docs${NC}"
echo ""
echo -e "  ${BOLD}测试账号：${NC}"
echo -e "  管理员：admin / admin123"
echo -e "  用户：  student / student123"
echo ""
echo -e "  停止服务：${YELLOW}bash stop.sh${NC}"
echo ""

# 自动打开浏览器（Mac）
if command -v open &>/dev/null; then
  sleep 1 && open http://localhost:3000
fi
