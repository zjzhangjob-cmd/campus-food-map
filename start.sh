#!/bin/bash
# =============================================================
#  觅食 — 启动脚本（Mac / Linux）
#  用法：bash start.sh
# =============================================================

RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'
CYAN='\033[0;36m'; BOLD='\033[1m'; NC='\033[0m'

if [ ! -f ".env" ]; then
  echo -e "${RED}✗ 未找到 .env，请先运行：bash setup.sh${NC}"; exit 1
fi
if [ ! -d "backend/venv" ]; then
  echo -e "${RED}✗ 未找到虚拟环境，请先运行：bash setup.sh${NC}"; exit 1
fi

echo ""
echo -e "${CYAN}${BOLD}🍜  启动觅食·大学城美食地图${NC}"
echo ""

# ── 读取高德 JS Key 并注入前端 ──────────────────────────────
AMAP_JS_KEY=$(grep "^AMAP_JS_KEY=" .env | cut -d'=' -f2- | tr -d '"' | tr -d "'")

if [ -n "$AMAP_JS_KEY" ] && [ "$AMAP_JS_KEY" != "你的高德JS_API_Key" ]; then
  sed -i.bak "s|key=AMAP_JS_KEY_PLACEHOLDER|key=${AMAP_JS_KEY}|g" frontend/index.html
  rm -f frontend/index.html.bak
  echo -e "${GREEN}✓ 高德地图 Key 已注入${NC}"
else
  echo -e "${YELLOW}⚠ 未配置高德 JS Key，地图将显示占位图（可在 .env 中设置 AMAP_JS_KEY）${NC}"
fi

# ── 启动后端 ──────────────────────────────────────────────────
echo -e "${CYAN}▶ 启动后端...${NC}"
cd backend
source venv/bin/activate
python -m app.init_db 2>/dev/null
mkdir -p ../logs
nohup uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload \
  > ../logs/backend.log 2>&1 &
echo $! > ../logs/backend.pid
cd ..

echo -n "  等待后端启动"
for i in {1..20}; do
  sleep 0.5
  if curl -s http://localhost:8000/health > /dev/null 2>&1; then
    echo -e " ${GREEN}✓${NC}"; break
  fi
  echo -n "."
done

# ── 启动前端 ──────────────────────────────────────────────────
echo -e "${CYAN}▶ 启动前端...${NC}"
nohup python3 -m http.server 3000 --directory frontend \
  > logs/frontend.log 2>&1 &
echo $! > logs/frontend.pid
sleep 0.5

echo ""
echo -e "${GREEN}${BOLD}======================================${NC}"
echo -e "${GREEN}${BOLD}  ✅ 服务已启动！                     ${NC}"
echo -e "${GREEN}${BOLD}======================================${NC}"
echo ""
echo -e "  🌐 美食地图   ${CYAN}http://localhost:3000${NC}"
echo -e "  🎯 趣味模式   ${CYAN}http://localhost:3000/fun.html${NC}"
echo -e "  👤 个人主页   ${CYAN}http://localhost:3000/profile.html${NC}"
echo -e "  🛠️  管理后台   ${CYAN}http://localhost:3000/admin.html${NC}"
echo -e "  📖 API 文档   ${CYAN}http://localhost:8000/docs${NC}"
echo ""
echo -e "  ${BOLD}账号：${NC}admin/admin123  student/student123"
echo -e "  停止服务：${YELLOW}bash stop.sh${NC}"
echo ""

if command -v open &>/dev/null; then
  sleep 1 && open http://localhost:3000
fi
