#!/bin/bash
# ==============================================================================
# 보너스 2: 시간 기반 로그 보존 및 아카이빙 정책 스크립트 (retention.sh)
# 규칙:
#   1. 7일 경과 로그: gzip 압축 후 /var/log/monitor/agent-app/archive/ 로 이동
#   2. 30일 경과 아카이브: *.gz 파일 영구 삭제
# ==============================================================================

SRC_LOG_DIR="${AGENT_LOG_DIR:-/var/log/agent-app}"
ARCHIVE_DIR="/var/log/monitor/agent-app/archive"

echo "====== LOG RETENTION EXECUTION ======"
echo "[INFO] Source log directory : ${SRC_LOG_DIR}"
echo "[INFO] Archive directory    : ${ARCHIVE_DIR}"

# 1. 예외 처리: 소스 디렉토리 존재 확인
if [ ! -d "$SRC_LOG_DIR" ]; then
    echo "[WARNING] Source log directory '${SRC_LOG_DIR}' does not exist. Nothing to process."
    exit 0
fi

# 2. 아카이브 디렉토리 확인 및 생성
if [ ! -d "$ARCHIVE_DIR" ]; then
    mkdir -p "$ARCHIVE_DIR" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "[ERROR] Failed to create archive directory '${ARCHIVE_DIR}'. Check permissions."
        exit 1
    fi
    echo "[INFO] Created archive directory: ${ARCHIVE_DIR}"
fi

# 3. 7일 이상 경과 로그 파일 압축 및 이동
echo "[STEP 1] Compressing and archiving logs older than 7 days..."
COMPRESSED_COUNT=0

# 활성 파일 monitor.log는 제외하고 회전된 로그 파일(*.log.* 또는 이전 로그) 대상 탐색
# (단, 7일 이상 경과한 *.log 파일 탐색)
find "$SRC_LOG_DIR" -maxdepth 1 -type f -name "*.log*" -mtime +7 2>/dev/null | while read -r log_file; do
    # 현재 기록 중인 메인 로그는 건너뜀
    if [ "$log_file" == "${SRC_LOG_DIR}/monitor.log" ]; then
        continue
    fi
    
    base_name=$(basename "$log_file")
    target_gz="${ARCHIVE_DIR}/${base_name}-$(date +%Y%m%d%H%M%S).gz"

    if gzip -c "$log_file" > "$target_gz" 2>/dev/null; then
        rm -f "$log_file"
        echo "  [OK] Archived: ${base_name} -> ${target_gz}"
    else
        echo "  [FAIL] Failed to compress: ${log_file}"
    fi
done

# 4. 30일 이상 경과된 압축 아카이브 파일(*.gz) 삭제
echo "[STEP 2] Cleaning up archives older than 30 days..."
DELETED_COUNT=0
find "$ARCHIVE_DIR" -maxdepth 1 -type f -name "*.gz" -mtime +30 2>/dev/null | while read -r gz_file; do
    if rm -f "$gz_file" 2>/dev/null; then
        echo "  [DELETED] Expired archive: $(basename "$gz_file")"
    else
        echo "  [FAIL] Failed to delete: ${gz_file}"
    fi
done

echo "[SUCCESS] Log retention cycle completed successfully."
exit 0
