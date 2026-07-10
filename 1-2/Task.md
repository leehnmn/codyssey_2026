# 심층 트러블슈팅 미션 Task Tracker

## 1. 사전 환경 구성 (Orbstack 기반 Docker 가상화)
- [x] **운영체제 및 아키텍처 파악**: Mac 환경(Apple Silicon, 호스트 OS)에서 제공된 리눅스 전용 실행 파일(ELF 64-bit)을 구동하기 위한 호환성 확인.
- [x] **Docker(Orbstack) 컨테이너 세팅**: `ubuntu:22.04` 베이스 이미지를 활용하여 `linux/amd64` 아키텍처 환경 구축.
  - *세부 이유*: Mac 칩(arm64)과 바이너리(x86_64)의 아키텍처 불일치로 인한 `Exec format error`를 방지하기 위해 Rosetta 2 기반의 amd64 에뮬레이션 컨테이너 환경을 강제 지정(`--platform linux/amd64`).
- [x] **권한 및 보안 정책 우회**: Docker 기본 사용자인 `root`로 실행 시 바이너리의 자체 보안 로직에 의해 거부되는 문제 해결.
  - *세부 작업*: `useradd -m agentuser` 명령어를 통해 일반 사용자 권한을 생성하고, 파일 소유권을 넘겨 보안 정책을 우회.
- [x] **Agent 필수 디렉터리 및 환경변수(Env) 매핑**: 미션 요구사항에 명시된 필수 경로(`$AGENT_HOME`, `upload_files`, `api_keys`, `logs`)와 보안키(`secret.key`) 생성 및 주입.
- [x] **관제 툴(`monitor.sh`) 제작 및 백그라운드 구동**: 1초 단위로 대상 프로세스(`agent-leak-app-x86`)의 PID를 추적하여 OS 자원(CPU, Memory)을 `ps` 명령어 기반으로 로깅.

## 2. 메모리 누수 (Memory Leak / OOM) 시나리오 재현 및 분석
- [x] **트리거 조건 세팅**: `MEMORY_LIMIT=50`, `MULTI_THREAD_ENABLE=false`.
- [x] **현상 관측**: `CpuWorker`가 아닌 `MemoryWorker` 측에서 힙 메모리를 해제하지 않아 25MB -> 50MB로 누적됨을 확인.
- [x] **장애 발생**: 한계치 도달 시 내부 `MemoryGuard` 정책에 의해 OOM(Out of Memory) 방지를 위한 자가 강제 종료(Self-terminating) 발생 로그 확보.
- [x] **조치 및 검증**: `MEMORY_LIMIT`를 500으로 상향 조정하여 생존 시간 연장 검증.
- [x] **이슈 리포트 작성**: 육하원칙 및 기술적 인과관계(메모리 누수가 시스템 페이징 스래싱에 미치는 영향 등)를 포함한 `issue1_oom.md` 작성.

## 3. CPU 과점유 (CPU Spike) 시나리오 재현 및 분석
- [x] **트리거 조건 세팅**: `CPU_MAX_OCCUPY=100`, `MEMORY_LIMIT=500`. 
  - *세부 이유*: Watchdog이 CPU 과점유를 인지하기 위해서는 실제 연산 부하가 극단적으로 높아야 하므로 임계치를 100%로 설정하여 강제 부하 발생 유도.
- [x] **현상 관측**: `CpuWorker`의 부하율이 5%에서 점진적으로 증가하여 59.4%를 초과하는 구간 로깅.
- [x] **장애 발생**: 특정 프로세스의 CPU 독점으로 인한 시스템 기아(Starvation)를 방지하기 위해 내부 Watchdog이 `CPU Threshold Violated!` 에러와 함께 프로세스를 Emergency Abort시키는 현상 확보.
- [x] **조치 및 검증**: `CPU_MAX_OCCUPY=10` 수준으로 하향하여, 10% 도달 시 자체 Cooldown(냉각)을 통해 프로세스가 죽지 않고 생존하는 메커니즘 확인.
- [x] **이슈 리포트 작성**: 프로세스 독점이 OS 스케줄링 및 지연(Latency)에 미치는 영향을 포함한 `issue2_cpu.md` 작성.

## 4. 교착 상태 (Deadlock) 시나리오 재현 및 분석
- [x] **트리거 조건 세팅**: `MULTI_THREAD_ENABLE=true`. 
- [x] **현상 관측**: 다중 스레드(Worker-Thread-1, 2)가 동시 실행되며, 각각 `Shared_Memory_A`와 `Socket_Pool_B`에 대한 Lock을 획득.
- [x] **장애 발생**: 서로 상대방이 쥔 자원을 요구하며 무한 대기(BLOCKED) 상태에 빠지는 순환 대기(Circular Wait) 교착상태 발생. 프로세스는 살아있으나 CPU/MEM 변동률이 0.1% 미만으로 정체.
- [x] **조치 및 검증**: 단일 스레드 모드로 롤백하여 동시 자원 접근을 차단하고 정상 구동 확인.
- [x] **이슈 리포트 작성**: 교착상태 4대 조건(상호 배제, 점유 대기, 비선점, 순환 대기)을 근거로 한 `issue3_deadlock.md` 작성.

## 5. 스케줄링 알고리즘 추론 (보너스 과제)
- [x] **로그 패턴 분석**: 태스크가 진행도 0%에서 100%까지 완료될 때까지 단 한 번의 Context Switching이나 Preemption(선점) 없이 자원을 독점하는 현상 관측.
- [x] **알고리즘 역추론**: 해당 패턴이 시분할(Round-Robin)이나 우선순위(Priority) 방식이 아닌, 비선점형 방식인 FCFS (First-Come, First-Served) 방식임을 도출.
- [x] **아키텍처 적합도 분석**: 호위 효과(Convoy Effect) 발생에 따른 장단점을 서술하고, 실시간 반응이 필요한 웹 서버보다는 일괄 처리 중심의 배치 프로세싱(Batch Processing)에 적합함을 정리한 `bonus_scheduling.md` 작성.
