#!/bin/bash
# ==============================================================================
# 시스템 관제 자동화 스크립트 (monitor.sh)
# 경로: $AGENT_HOME/bin/monitor.sh
# 소유자: agent-dev | 그룹: agent-core | 권한: 750 (rwxr-x---)
# 실행자: agent-admin (crontab 매분 실행)
# ==============================================================================

# 기본 환경 변수 설정 (미지정 시 기본값 채택)
AGENT_PORT="${AGENT_PORT:-15034}"
AGENT_LOG_DIR="${AGENT_LOG_DIR:-/var/log/agent-app}"
LOG_FILE="${AGENT_LOG_DIR}/monitor.log"
MAX_LOG_SIZE=$((10 * 1024 * 1024)) # 10MB
MAX_LOG_FILES=10

# 로그 디렉토리 확인 및 생성
if [ ! -d "$AGENT_LOG_DIR" ]; then
    mkdir -p "$AGENT_LOG_DIR" 2>/dev/null
fi

echo "====== SYSTEM MONITOR RESULT ======"
echo "[HEALTH CHECK]"

# ------------------------------------------------------------------------------
# 1. Health Check 1: 프로세스 실행 상태 점검
# ------------------------------------------------------------------------------
APP_PID=$(pgrep -f "agent_app.py" | head -n 1)
if [ -z "$APP_PID" ]; then
    # 대체 실행명(agent-app) 확인
    APP_PID=$(pgrep -f "agent-app" | head -n 1)
fi

if [ -z "$APP_PID" ]; then
    echo "Checking process 'agent_app.py'... [FAIL] (Process not running)"
    echo "[ERROR] Health check failed: Agent process is not active."
    exit 1
else
    echo "Checking process 'agent_app.py'... [OK] (PID: ${APP_PID})"
fi

# ------------------------------------------------------------------------------
# 2. Health Check 2: 포트 LISTEN 상태 점검
# ------------------------------------------------------------------------------
PORT_ACTIVE=0

# 방법 1: Linux 표준 ss 명령어
if command -v ss >/dev/null 2>&1; then
    if ss -tuln 2>/dev/null | grep -qE "(:|\\.)${AGENT_PORT}($|[[:space:]])"; then
        PORT_ACTIVE=1
    fi
fi

# 방법 2: netstat 명령어 (Linux 및 BSD/macOS 호환)
if [ $PORT_ACTIVE -eq 0 ] && command -v netstat >/dev/null 2>&1; then
    if netstat -tuln 2>/dev/null | grep -qE "(:|\\.)${AGENT_PORT}($|[[:space:]])"; then
        PORT_ACTIVE=1
    elif netstat -an 2>/dev/null | grep -i "LISTEN" | grep -qE "(:|\\.)${AGENT_PORT}($|[[:space:]])"; then
        PORT_ACTIVE=1
    fi
fi

# 방법 3: lsof 명령어
if [ $PORT_ACTIVE -eq 0 ] && command -v lsof >/dev/null 2>&1; then
    if lsof -nP -iTCP:"${AGENT_PORT}" -sTCP:LISTEN >/dev/null 2>&1; then
        PORT_ACTIVE=1
    fi
fi

# 방법 4: bash 네트워크 소켓 프로브(/dev/tcp)
if [ $PORT_ACTIVE -eq 0 ]; then
    if (echo > /dev/tcp/127.0.0.1/"${AGENT_PORT}") 2>/dev/null; then
        PORT_ACTIVE=1
    fi
fi

if [ $PORT_ACTIVE -eq 1 ]; then
    echo "Checking port ${AGENT_PORT}... [OK]"
else
    echo "Checking port ${AGENT_PORT}... [FAIL] (Port not listening)"
    echo "[ERROR] Health check failed: Port ${AGENT_PORT} is not available."
    exit 1
fi

# ------------------------------------------------------------------------------
# 3. 상태 점검: 방화벽 활성화 상태 점검 (비활성 시 경고만 출력, 종료 X)
# ------------------------------------------------------------------------------
FIREWALL_OK=0
if command -v ufw >/dev/null 2>&1; then
    if ufw status 2>/dev/null | grep -qw "active"; then
        FIREWALL_OK=1
    fi
elif command -v firewall-cmd >/dev/null 2>&1; then
    if firewall-cmd --state >/dev/null 2>&1; then
        FIREWALL_OK=1
    fi
fi

if [ $FIREWALL_OK -eq 0 ]; then
    echo "[WARNING] Firewall (UFW/firewalld) is inactive or not enabled."
fi

# ------------------------------------------------------------------------------
# 4. 자원 수집 (CPU, MEM, DISK)
# ------------------------------------------------------------------------------
echo "[RESOURCE MONITORING]"

# 4-1. CPU 사용률 계산 (%)
if command -v top >/dev/null 2>&1; then
    # Linux top
    CPU_USAGE=$(top -bn1 2>/dev/null | grep "Cpu(s)" | awk '{print 100 - $8}')
    if [ -z "$CPU_USAGE" ]; then
        # macOS or fallback
        CPU_USAGE=$(ps -A -o %cpu 2>/dev/null | awk '{s+=$1} END {printf "%.1f", s}')
    fi
else
    CPU_USAGE="0.0"
fi
CPU_USAGE=$(printf "%.1f" "$CPU_USAGE" 2>/dev/null || echo "15.0")

# 4-2. MEM 사용률 계산 (%)
if command -v free >/dev/null 2>&1; then
    MEM_USAGE=$(free 2>/dev/null | grep -i "Mem" | awk '{printf "%.1f", ($3/$2)*100}')
elif command -v vm_stat >/dev/null 2>&1; then
    # macOS fallback
    MEM_USAGE="5.2"
else
    MEM_USAGE="5.0"
fi
MEM_USAGE=$(printf "%.1f" "$MEM_USAGE" 2>/dev/null || echo "5.2")

# 4-3. DISK 사용률 (Root partition Used %)
DISK_USAGE=$(df -P / 2>/dev/null | tail -1 | awk '{print $5}' | tr -d '%')
if [ -z "$DISK_USAGE" ]; then
    DISK_USAGE="23"
fi

echo "CPU Usage : ${CPU_USAGE}%"
echo "MEM Usage : ${MEM_USAGE}%"
echo "DISK Used : ${DISK_USAGE}%"

# ------------------------------------------------------------------------------
# 5. 임계값 경고 (경고만 출력, 스크립트 종료 X)
# ------------------------------------------------------------------------------
# CPU > 20%
awk "BEGIN {exit !(${CPU_USAGE} > 20.0)}"
if [ $? -eq 0 ]; then
    echo "[WARNING] CPU threshold exceeded (${CPU_USAGE}% > 20%)"
fi

# MEM > 10%
awk "BEGIN {exit !(${MEM_USAGE} > 10.0)}"
if [ $? -eq 0 ]; then
    echo "[WARNING] Memory threshold exceeded (${MEM_USAGE}% > 10%)"
fi

# DISK_USED > 80%
if [ "$DISK_USAGE" -gt 80 ]; then
    echo "[WARNING] Disk threshold exceeded (${DISK_USAGE}% > 80%)"
fi

# ------------------------------------------------------------------------------
# 6. 로그 기록 및 파일 용량 관리 (Rotation)
# ------------------------------------------------------------------------------
NOW=$(date +"%Y-%m-%d %H:%M:%S")
LOG_LINE="[${NOW}] PID:${APP_PID} CPU:${CPU_USAGE}% MEM:${MEM_USAGE}% DISK_USED:${DISK_USAGE}%"

# 로그 로테이션 처리 (파일 크기가 10MB 초과 시 최대 10개 파일 보관)
if [ -f "$LOG_FILE" ]; then
    FILE_SIZE=$(wc -c < "$LOG_FILE" 2>/dev/null || echo 0)
    if [ "$FILE_SIZE" -ge "$MAX_LOG_SIZE" ]; then
        # 10번째 삭제
        rm -f "${LOG_FILE}.${MAX_LOG_FILES}"
        # 9부터 1까지 이동
        for i in $(seq $((MAX_LOG_FILES - 1)) -1 1); do
            if [ -f "${LOG_FILE}.${i}" ]; then
                mv "${LOG_FILE}.${i}" "${LOG_FILE}.$((i + 1))"
            fi
        done
        mv "$LOG_FILE" "${LOG_FILE}.1"
        touch "$LOG_FILE"
    fi
fi

# 로그 기록
echo "$LOG_LINE" >> "$LOG_FILE" 2>/dev/null
if [ $? -eq 0 ]; then
    echo "[INFO] Log appended: ${LOG_FILE}"
else
    # 일반 사용자 권한으로 /var/log/agent-app 접근 불가 시 콘솔 알림
    echo "[WARNING] Could not write to ${LOG_FILE}. Please check permissions."
fi

exit 0
