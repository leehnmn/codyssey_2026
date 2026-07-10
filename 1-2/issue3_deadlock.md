[Bug] 멀티스레드 환경에서 교착상태(Deadlock) 발생으로 프로세스 무응답

## 1. Description (현상 설명)
`agent-leak-app`을 `MULTI_THREAD_ENABLE=true`로 구동하면 멀티스레드 기반의 Transaction Processor가 초기화됩니다. 이 상태에서 어플리케이션을 가동시키면 일정 시간 후 PID(프로세스 ID)는 살아있고 죽지 않으나, 더 이상 CPU나 메모리를 사용하지 않으며 로그 출력도 완전히 멈추는 **무응답 현상(Hang)**이 관측됩니다.

## 2. Evidence & Logs (증거 자료)
`monitor_deadlock.log`를 보면 `app_deadlock.log` 상의 로깅이 멈춘 시점인 11:37:54 이후에도 프로세스는 종료되지 않았으나(PID 3369 유지), CPU 사용률은 0.1~0.2% 수준으로 바닥을 치며 더 이상 어떤 작업도 진행하지 못함을 알 수 있습니다.

**[ monitor_deadlock.log 데이터 발췌 ]**
```text
[2026-07-10 11:38:27] PROCESS:agent-leak-app-x86 PID:3369 CPU:0.1% MEM:0.0%
[2026-07-10 11:38:28] PROCESS:agent-leak-app-x86 PID:3369 CPU:0.1% MEM:0.0%
[2026-07-10 11:38:29] PROCESS:agent-leak-app-x86 PID:3369 CPU:0.1% MEM:0.0%
```

**[ app_deadlock.log 프로그램 실행 로그 발췌 ]**
```text
2026-07-10 11:37:52,492 [INFO] [AgentWorker][Worker-Thread-1] LOCK ACQUIRED: [Shared_Memory_A]. (Holding...)
2026-07-10 11:37:52,493 [INFO] [AgentWorker][Worker-Thread-2] LOCK ACQUIRED: [Socket_Pool_B]. (Holding...)
2026-07-10 11:37:54,503 [INFO] [AgentWorker][Worker-Thread-1] Need resource [Socket_Pool_B] to finish job.
2026-07-10 11:37:54,503 [INFO] [AgentWorker][Worker-Thread-1] WAITING for [Socket_Pool_B]... (Status: BLOCKED)
2026-07-10 11:37:54,504 [INFO] [AgentWorker][Worker-Thread-2] Need resource [Shared_Memory_A] to write logs.
2026-07-10 11:37:54,504 [INFO] [AgentWorker][Worker-Thread-2] WAITING for [Shared_Memory_A]... (Status: BLOCKED)
```
위 로그가 출력된 이후로 시스템이 멈춥니다.

## 3. Root Cause Analysis (원인 분석)
- **현상 분석**: `Worker-Thread-1`이 `Shared_Memory_A` 락을 획득하고 보유한 상태에서 작업을 마치기 위해 `Socket_Pool_B`를 요구합니다. 하지만 동시에 `Worker-Thread-2`는 `Socket_Pool_B`를 선점하여 락을 걸고 있고, 일을 마치기 위해 `Shared_Memory_A`를 요구합니다. 이로 인해 두 스레드가 서로의 자원을 무한정 기다리는 전형적인 **교착상태(Deadlock)**에 빠졌습니다.
- **OS 이론**: 이는 교착상태의 4대 조건인 상호 배제(Mutual Exclusion), 점유 대기(Hold and Wait), 비선점(No Preemption), 순환 대기(Circular Wait)가 모두 완벽하게 성립했기 때문입니다. 운영체제가 이를 감지하거나 강제로 자원을 회수하지 않기 때문에 스레드는 영원히 BLOCKED 상태에 머무르며, 이로 인해 프로세스의 CPU 활동이 중단된 것입니다.

## 4. Workaround & Verification (조치 및 검증)
- **조치 내용**: 환경변수 `MULTI_THREAD_ENABLE` 값을 `true`에서 `false`로 변경하여 어플리케이션을 단일 스레드(Sequential) 모드로 작동하게 설정했습니다.
- **검증 결과**: 재실행 시 자원(Resource)에 대한 동시 다발적 락 획득 시도가 사라지므로 순환 대기 조건이 파괴되었습니다. 그 결과 스레드가 중간에 BLOCKED 되지 않고 작업을 순차적으로 완료하여 프로세스가 멈춤 없이 정상 구동됨을 확인했습니다.
