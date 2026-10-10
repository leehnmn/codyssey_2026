#!/bin/bash
# ==============================================================================
# 보너스 1: 모니터링 로그 분석 및 통계 요약 리포트 생성 스크립트 (report.sh)
# 사용법:
#   ./report.sh
#   ./report.sh --start "2026-02-25 13:58:00" --end "2026-02-25 14:05:00"
# ==============================================================================

AGENT_LOG_DIR="${AGENT_LOG_DIR:-/var/log/agent-app}"
LOG_FILE="${1:-${AGENT_LOG_DIR}/monitor.log}"

START_TIME=""
END_TIME=""

# 옵션 파싱
while [[ $# -gt 0 ]]; do
    case "$1" in
        --start)
            START_TIME="$2"
            shift 2
            ;;
        --end)
            END_TIME="$2"
            shift 2
            ;;
        --file)
            LOG_FILE="$2"
            shift 2
            ;;
        *)
            if [ -f "$1" ]; then
                LOG_FILE="$1"
            fi
            shift
            ;;
    esac
done

if [ ! -f "$LOG_FILE" ]; then
    echo "[ERROR] Log file not found: ${LOG_FILE}"
    exit 1
fi

# awk를 이용한 정밀 통계 계산
awk -v start="$START_TIME" -v end="$END_TIME" '
BEGIN {
    count = 0;
    cpu_sum = 0; cpu_min = 999999; cpu_max = -1;
    mem_sum = 0; mem_min = 999999; mem_max = -1;
    disk_sum = 0; disk_min = 999999; disk_max = -1;
}
{
    # 포맷 파싱: [2026-02-25 13:58:01] PID:48291 CPU:10.2% MEM:3.2% DISK_USED:23%
    # $1=[YYYY-MM-DD, $2=HH:MM:SS]
    date_str = substr($1, 2) " " substr($2, 1, length($2)-1);

    # 시간 범위 필터링
    if (start != "" && date_str < start) next;
    if (end != "" && date_str > end) next;

    # 필드 추출
    cpu = 0; mem = 0; disk = 0;
    for (i = 3; i <= NF; i++) {
        if ($i ~ /^CPU:/) {
            val = substr($i, 5);
            gsub(/%/, "", val);
            cpu = val + 0;
        } else if ($i ~ /^MEM:/) {
            val = substr($i, 5);
            gsub(/%/, "", val);
            mem = val + 0;
        } else if ($i ~ /^DISK_USED:/) {
            val = substr($i, 11);
            gsub(/%/, "", val);
            disk = val + 0;
        }
    }

    count++;
    cpu_sum += cpu;
    if (cpu > cpu_max) { cpu_max = cpu; cpu_max_t = date_str; }
    if (cpu < cpu_min) { cpu_min = cpu; cpu_min_t = date_str; }

    mem_sum += mem;
    if (mem > mem_max) { mem_max = mem; mem_max_t = date_str; }
    if (mem < mem_min) { mem_min = mem; mem_min_t = date_str; }

    disk_sum += disk;
    if (disk > disk_max) { disk_max = disk; disk_max_t = date_str; }
    if (disk < disk_min) { disk_min = disk; disk_min_t = date_str; }
}
END {
    if (count == 0) {
        print "====== STATISTICS REPORT ======";
        print "[INFO] No data points found in the specified range.";
        exit 0;
    }

    print "====== STATISTICS REPORT ======";
    print "[CPU]";
    printf "Average : %.1f%%\n", (cpu_sum / count);
    printf "Maximum : %.1f%% at %s\n", cpu_max, cpu_max_t;
    printf "Minimum : %.1f%% at %s\n", cpu_min, cpu_min_t;
    print "";
    print "[Memory]";
    printf "Average : %.1f%%\n", (mem_sum / count);
    printf "Maximum : %.1f%% at %s\n", mem_max, mem_max_t;
    printf "Minimum : %.1f%% at %s\n", mem_min, mem_min_t;
    print "";
    print "[Disk]";
    printf "Average : %.1f%%\n", (disk_sum / count);
    printf "Maximum : %.0f%% at %s\n", disk_max, disk_max_t;
    printf "Minimum : %.0f%% at %s\n", disk_min, disk_min_t;
    print "";
    print "[Samples]";
    printf "Data Points: %d samples\n", count;
}
' "$LOG_FILE"
