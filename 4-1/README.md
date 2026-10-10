# 시스템 관제 및 서버 자동화 엔지니어링 실습 (4-1)

> **컴퓨터가 알아서 자기 상태를 점검하게 만들기**  
> Linux OS 보안 설정(SSH, UFW), 계정/권한 분립, 애플리케이션 Boot Sequence 검증, 시스템 관제 쉘 스크립트(`monitor.sh`) 및 로그 자동화

---

## 1. 프로젝트 개요

본 프로젝트는 리눅스 서버 운영 환경을 직접 구축하고, 프로세스/포트/시스템 리소스를 실시간 관제하여 로그로 기록하는 자동화 엔지니어링 미션입니다.

- **대상 OS**: Ubuntu 22.04 LTS (동등 Linux 환경)
- **주요 구성 요소**:
  - **기본 보안**: SSH 20022 포트 변경, Root 원격 접속 차단, UFW 방화벽(20022/tcp, 15034/tcp 허용)
  - **권한 체계**: 역할 기반 계정(`admin`, `dev`, `test`), 그룹(`common`, `core`), SGID 기반 디렉토리 격리
  - **에이전트 앱**: 5단계 Boot Sequence 검증 및 TCP 15034 포트 리슨 데몬
  - **자동화 스크립트**: 프로세스/포트 헬스체크, 리소스 수집, 임계값 경고, 10MB 로그 로테이션, cron 매분 주기 실행
  - **보너스 기능**: `report.sh` 통계 요약 리포트, `retention.sh` 7일 압축 아카이빙 및 30일 삭제 정책

---

## 2. 파일 목록

```
Desktop/4-1/
├── 요구사항_수행_내역서.md     # [필수 제출물 1] 전체 수행 내역 및 증거 자료 문서
├── monitor.sh               # [필수 제출물 2] 시스템 관제 자동화 쉘 스크립트
├── agent_app.py             # 5단계 Boot Sequence 검증 및 15034 리슨 제공 앱
├── report.sh                # [보너스 1] monitor.log 파싱 통계 요약 리포트 스크립트
├── retention.sh             # [보너스 2] 시간 기반 로그 보존(7일 압축, 30일 삭제) 스크립트
├── setup.sh                 # 계정/그룹/디렉토리/환경변수 원클릭 자동 셋업 스크립트
└── README.md                # 본 안내 문서
```

---

## 3. 빠른 실행 및 검증 가이드

### 1) 환경 변수 및 사전 준비
```bash
export AGENT_HOME="$HOME/agent-app"
export AGENT_PORT="15034"
export AGENT_UPLOAD_DIR="$AGENT_HOME/upload_files"
export AGENT_KEY_PATH="$AGENT_HOME/api_keys/t_secret.key"
export AGENT_LOG_DIR="/var/log/agent-app"

mkdir -p "$AGENT_HOME/upload_files" "$AGENT_HOME/api_keys" "$AGENT_HOME/bin" "$AGENT_LOG_DIR"
echo "agent_api_key_test" > "$AGENT_KEY_PATH"
```

### 2) 애플리케이션 실행 (Boot Sequence 5단계 [OK] 확인)
```bash
python3 agent_app.py &
```
*출력*:
```text
> Starting Agent Boot Sequence...
[1/5] Checking User Account [OK]
... Running as service user 'agent-admin' (uid=1001)
[2/5] Verifying Environment Variables [OK]
... All required Envs correct
[3/5] Checking Required Files [OK]
... Verified key file with correct key string.
[4/5] Checking Port Availability [OK]
... Port 15034 is available.
[5/5] Verifying Log Permission [OK]
... Log directory is writable: /var/log/agent-app
------------------------------------------------------------
All Boot Checks Passed!
Agent READY
```

### 3) 관제 스크립트 실행 (`monitor.sh`)
```bash
bash monitor.sh
```

### 4) 통계 요약 리포트 확인 (`report.sh` - 보너스 1)
```bash
bash report.sh
# 또는 특정 로그 지정
bash report.sh /var/log/agent-app/monitor.log
```

### 5) 로그 보존 관리 실행 (`retention.sh` - 보너스 2)
```bash
bash retention.sh
```

---

## 4. 필수 증거 자료 8종 요약표

상세한 명령어 실행 결과 및 캡처 데이터는 **[`요구사항_수행_내역서.md`](file:///Users/dlgusals01205864/Desktop/4-1/요구사항_수행_내역서.md)**에서 확인하실 수 있습니다.

1. **SSH 보안**: `Port 20022`, `PermitRootLogin no` 반영 및 `sshd -T`, `ss -tulnp` 확인
2. **UFW 방화벽**: 20022/tcp, 15034/tcp 인바운드 개방 및 `ufw status verbose` 확인
3. **계정/그룹**: `agent-admin`, `agent-dev`, `agent-test` 및 `agent-common`, `agent-core` 생성 확인
4. **디렉토리/권한**: `upload_files` (2775), `api_keys` (2770), `/var/log/agent-app` (2775) 권한 확인
5. **앱 기동**: 5단계 검증 통과 및 "Agent READY", 15034 LISTEN 상태 확인
6. **관제 스크립트**: 프로세스/포트 정상, 리소스 수집, 임계값 경고 출력 확인
7. **로그 누적**: `/var/log/agent-app/monitor.log` 포맷에 맞춘 누적 기록 확인
8. **crontab 등록**: `agent-admin` 계정 매분 실행 등록 및 1분 후 자동 로그 누적 확인
