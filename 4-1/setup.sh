#!/bin/bash
# ==============================================================================
# 시스템 초기 구성 및 프로비저닝 자동화 스크립트 (setup.sh)
# 사용 대상: Ubuntu 22.04 LTS (root 또는 sudo 권한으로 실행)
# ==============================================================================

if [ "$(id -u)" -ne 0 ]; then
    echo "[ERROR] This script must be run as root (or with sudo)."
    exit 1
fi

echo "=========================================================="
echo " Starting System Environment Setup for Agent App"
echo "=========================================================="

# 1. 그룹 생성
echo "[1/6] Creating user groups (agent-common, agent-core)..."
groupadd -f agent-common
groupadd -f agent-core

# 2. 계정 생성 및 그룹 할당
echo "[2/6] Creating user accounts..."
# agent-admin (홈 디렉토리 생성, agent-common 및 agent-core 소속)
if ! id "agent-admin" >/dev/null 2>&1; then
    useradd -m -s /bin/bash -g agent-core -G agent-common agent-admin
    echo "Created user agent-admin"
else
    usermod -aG agent-common,agent-core agent-admin
fi

# agent-dev (agent-common 및 agent-core 소속)
if ! id "agent-dev" >/dev/null 2>&1; then
    useradd -m -s /bin/bash -g agent-core -G agent-common agent-dev
    echo "Created user agent-dev"
else
    usermod -aG agent-common,agent-core agent-dev
fi

# agent-test (agent-common 전용 소속)
if ! id "agent-test" >/dev/null 2>&1; then
    useradd -m -s /bin/bash -g agent-common agent-test
    echo "Created user agent-test"
else
    usermod -aG agent-common agent-test
fi

# 3. 디렉토리 구조 생성 ($AGENT_HOME 기준)
AGENT_HOME="/home/agent-admin/agent-app"
LOG_DIR="/var/log/agent-app"

echo "[3/6] Setting up directory structure..."
mkdir -p "$AGENT_HOME/upload_files"
mkdir -p "$AGENT_HOME/api_keys"
mkdir -p "$AGENT_HOME/bin"
mkdir -p "$LOG_DIR"
mkdir -p "/var/log/monitor/agent-app/archive"

# 4. 접근 권한 및 소유권 설정 (요구사항 엄격 적용)
echo "[4/6] Applying permissions and ACL policies..."
# upload_files: group=agent-common, R/W 가능, SGID 적용
chown -R agent-admin:agent-common "$AGENT_HOME/upload_files"
chmod 2775 "$AGENT_HOME/upload_files"

# api_keys: group=agent-core ONLY, R/W 가능 (일반/test 접근 차단)
chown -R agent-admin:agent-core "$AGENT_HOME/api_keys"
chmod 2770 "$AGENT_HOME/api_keys"

# /var/log/agent-app: group=agent-core ONLY, R/W 가능
chown -R agent-admin:agent-core "$LOG_DIR"
chmod 2775 "$LOG_DIR"

# 5. 필수 키 파일 생성
echo "[5/6] Creating API secret key file..."
KEY_FILE="$AGENT_HOME/api_keys/t_secret.key"
echo "agent_api_key_test" > "$KEY_FILE"
chown agent-admin:agent-core "$KEY_FILE"
chmod 660 "$KEY_FILE"

# 스크립트 복사 및 권한 설정 (소유자: agent-dev, 그룹: agent-core, 750)
CURRENT_DIR=$(dirname "$(readlink -f "$0")")
if [ -f "$CURRENT_DIR/monitor.sh" ]; then
    cp "$CURRENT_DIR/monitor.sh" "$AGENT_HOME/bin/monitor.sh"
    chown agent-dev:agent-core "$AGENT_HOME/bin/monitor.sh"
    chmod 750 "$AGENT_HOME/bin/monitor.sh"
fi

if [ -f "$CURRENT_DIR/agent_app.py" ]; then
    cp "$CURRENT_DIR/agent_app.py" "$AGENT_HOME/agent_app.py"
    chown agent-admin:agent-core "$AGENT_HOME/agent_app.py"
    chmod 755 "$AGENT_HOME/agent_app.py"
fi

if [ -f "$CURRENT_DIR/report.sh" ]; then
    cp "$CURRENT_DIR/report.sh" "$AGENT_HOME/bin/report.sh"
    chown agent-dev:agent-core "$AGENT_HOME/bin/report.sh"
    chmod 750 "$AGENT_HOME/bin/report.sh"
fi

if [ -f "$CURRENT_DIR/retention.sh" ]; then
    cp "$CURRENT_DIR/retention.sh" "$AGENT_HOME/bin/retention.sh"
    chown agent-dev:agent-core "$AGENT_HOME/bin/retention.sh"
    chmod 750 "$AGENT_HOME/bin/retention.sh"
fi

# 6. 환경 변수 프로파일 등록
echo "[6/6] Configuring global environment variables..."
ENV_FILE="/etc/profile.d/agent_env.sh"
cat << 'EOF' > "$ENV_FILE"
export AGENT_HOME="/home/agent-admin/agent-app"
export AGENT_PORT="15034"
export AGENT_UPLOAD_DIR="/home/agent-admin/agent-app/upload_files"
export AGENT_KEY_PATH="/home/agent-admin/agent-app/api_keys/t_secret.key"
export AGENT_LOG_DIR="/var/log/agent-app"
EOF
chmod 644 "$ENV_FILE"

echo "=========================================================="
echo " Setup completed successfully!"
echo " Next steps:"
echo " 1. Configure SSH: Edit /etc/ssh/sshd_config -> Port 20022, PermitRootLogin no"
echo " 2. Configure UFW: ufw allow 20022/tcp && ufw allow 15034/tcp && ufw enable"
echo " 3. Start Agent App as agent-admin: python3 $AGENT_HOME/agent_app.py &"
echo " 4. Setup crontab for agent-admin: crontab -e -u agent-admin"
echo "=========================================================="
