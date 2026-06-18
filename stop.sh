#!/bin/bash
# 停止所有服务

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; NC='\033[0m'

echo "🛑 停止觅食服务..."

stop_pid() {
  local name=$1
  local pidfile=$2
  if [ -f "$pidfile" ]; then
    PID=$(cat "$pidfile")
    if kill -0 "$PID" 2>/dev/null; then
      kill "$PID" && echo -e "  ${GREEN}✓ $name (PID $PID) 已停止${NC}"
    else
      echo -e "  ${YELLOW}⚠ $name 进程不存在${NC}"
    fi
    rm -f "$pidfile"
  else
    # 按端口查杀
    case $name in
      "后端") PORT=8000 ;;
      "前端") PORT=3000 ;;
    esac
    PID=$(lsof -ti :$PORT 2>/dev/null)
    if [ -n "$PID" ]; then
      kill "$PID" && echo -e "  ${GREEN}✓ $name (端口 $PORT) 已停止${NC}"
    fi
  fi
}

stop_pid "后端" "logs/backend.pid"
stop_pid "前端" "logs/frontend.pid"

echo ""
echo "✅ 所有服务已停止"
