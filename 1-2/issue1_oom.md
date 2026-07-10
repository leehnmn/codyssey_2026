[Bug] MemoryGuard 정책에 의한 비정상 강제 종료 (OOM)

## 1. Description (현상 설명)
`agent-leak-app` 어플리케이션을 실행하고 잠시 대기하면, 터미널에 `[MemoryGuard] Self-terminating process` 메시지가 출력되며 프로세스가 예고 없이 종료됩니다. 
이는 프로세스 내부의 힙 메모리가 지속적으로 상승하다가, 시스템 불안정을 방지하기 위해 강제로 자가 종료 정책(MemoryGuard)이 발동한 것입니다.

## 2. Evidence & Logs (증거 자료)
`monitor_oom.log`를 통해 수집된 관제 로그를 확인하면, **메모리(MEM)** 퍼센티지는 OS 차원에서 미미하게 보일 수 있으나(0.0%), 내부 로그(`app_oom.log`)를 보면 힙 메모리가 25MB -> 50MB로 급격히 상승하는 것을 관측할 수 있습니다. 

**[ monitor_oom.log 관제 로그 발췌 ]**
```text
[2026-07-10 11:29:36] PROCESS:agent-leak-app-x86 PID:146 CPU:1.6% MEM:0.0%
[2026-07-10 11:29:38] PROCESS:agent-leak-app-x86 PID:146 CPU:1.2% MEM:0.0%
[2026-07-10 11:29:39] PROCESS:agent-leak-app-x86 PID:146 CPU:1.0% MEM:0.0%
Process 146 terminated.
```

**[ app_oom.log 프로그램 실행 로그 발췌 ]**
```text
2026-07-10 11:29:36,105 [INFO] [MemoryWorker] Current Heap: 25MB
2026-07-10 11:29:39,148 [INFO] [MemoryWorker] Current Heap: 50MB
2026-07-10 11:29:39,149 [CRITICAL] [MemoryGuard] Memory limit exceeded (50MB >= 50MB) / (Recommend Over 256MB)
2026-07-10 11:29:39,149 [CRITICAL] [MemoryGuard] Self-terminating process 159 to prevent system instability.
```

## 3. Root Cause Analysis (원인 분석)
- **현상 분석**: 프로그램(`MemoryWorker`)이 작업을 수행하며 확보한 힙 영역의 메모리를 정상적으로 반환(Free/Release)하지 않고 지속적으로 축적하는 **메모리 누수(Memory Leak)**가 발생하고 있습니다.
- **OS 및 시스템 원리**: 운영체제 위에서 실행되는 프로세스는 할당된 한계치 이상의 메모리를 요구할 경우 시스템 전체의 OOM(Out of Memory)과 페이징 스래싱(Thrashing)을 유발할 수 있습니다. 이를 방지하고자 앱 내부의 안전 장치(`MemoryGuard`)가 지정된 제한치(`MEMORY_LIMIT`) 도달 시 프로세스를 스스로 종료시킨 것입니다.

## 4. Workaround & Verification (조치 및 검증)
- **조치 내용**: 환경변수 `MEMORY_LIMIT` 값을 기존 `50`에서 `500`으로 상향 조정하였습니다 (`export MEMORY_LIMIT=500`).
- **결과 확인**: 설정 변경 후, 50MB 도달 시 죽던 프로그램이 종료되지 않고 500MB까지 버티며 프로세스 생존 시간이 대폭 길어짐을 확인했습니다. 
- **근본 해결책**: 근본적인 조치를 위해서는 소스코드 레벨에서 `MemoryWorker`가 사용을 마친 데이터를 즉시 소멸시키거나 Garbage Collector가 회수할 수 있도록 불필요한 참조를 해제해야 합니다.
