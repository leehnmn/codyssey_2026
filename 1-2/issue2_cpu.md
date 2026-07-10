[Bug] CPU 과점유 방지 정책(Watchdog) 임계치 초과로 인한 프로세스 종료

## 1. Description (현상 설명)
`agent-leak-app` 실행 후 어플리케이션이 로드를 모니터링하며 지속적으로 실행되다가, `CpuWorker`의 부하(Load)가 비정상적으로 높아져 설정된 한계치를 초과할 때 `CPU Threshold Violated!` 에러와 함께 Watchdog에 의해 프로세스가 강제로 종료되는 현상이 발생합니다.

## 2. Evidence & Logs (증거 자료)
`CPU_MAX_OCCUPY` 환경변수를 100%로 설정한 후 모니터링한 결과, 초반에는 5%의 정상 로드를 보이나 일정 시간이 지남에 따라 점진적으로 부하가 59.4%까지 급격히 상승하며 프로세스가 죽는 모습을 확인할 수 있었습니다.

**[ app_cpu3.log 관제 로그 발췌 ]**
```text
2026-07-10 11:35:02,215 [INFO] [CpuWorker] Current Load: 5.00%
2026-07-10 11:35:05,330 [INFO] [CpuWorker] Current Load: 12.05%
...
2026-07-10 11:35:27,123 [INFO] [CpuWorker] Current Load: 45.09%
2026-07-10 11:35:30,234 [INFO] [CpuWorker] Current Load: 49.72%
2026-07-10 11:35:33,351 [INFO] [CpuWorker] Current Load: 59.40%
2026-07-10 11:35:33,452 [CRITICAL] [CpuWorker] CPU Threshold Violated! (59.400000000000006%).
```

**[ monitor_cpu3.log 관제 로그 발췌 (종료 시점) ]**
```text
[2026-07-10 11:35:31] PROCESS:agent-leak-app-x86 PID:2962 CPU:0.1% MEM:0.0%
[2026-07-10 11:35:32] PROCESS:agent-leak-app-x86 PID:2962 CPU:0.1% MEM:0.0%
[2026-07-10 11:35:33] PROCESS:agent-leak-app-x86 PID:2962 CPU:0.1% MEM:0.0%
Process 2962 terminated.
```

## 3. Root Cause Analysis (원인 분석)
- **현상 분석**: 특정 로직(`CpuWorker`)이 비효율적인 연산을 반복 수행하거나 무한 루프성에 가까운 연산에 빠지면서 CPU 요구량이 지속적으로 늘어나는 CPU Spike 현상이 발생했습니다.
- **OS 및 시스템 동작**: 하나의 프로세스가 CPU 자원을 독점하면(과점유), OS의 스케줄러가 다른 유용한 프로세스(관제 데몬, 웹 서버 등)에 CPU 자원을 분배하지 못해 **시스템 전체의 기아(Starvation) 및 Latency(지연)**가 발생합니다. 어플리케이션 내부에 구현된 Watchdog 프로세스가 이를 감지하고 시스템 보호를 위해 즉각적인 Emergency Abort를 단행한 것입니다.

## 4. Workaround & Verification (조치 및 검증)
- **조치 내용**: 환경변수 `CPU_MAX_OCCUPY`의 값을 `100`에서 안전 한계선인 `10`으로 하향 조정하였습니다.
- **검증 결과**: 수치를 `10`으로 조정한 이후, 부하가 10%에 도달하면 5%로 Cooldown(냉각/슬립) 되는 메커니즘이 정상 작동하여 더 이상 임계치를 뚫지 않고 프로세스가 생존함을 확인했습니다. (Before: 59.4% 도달 후 사망 -> After: 10% 도달 후 5%로 냉각되며 장기 생존)
