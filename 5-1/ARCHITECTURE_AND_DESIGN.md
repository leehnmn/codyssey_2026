# B5-1 Mini Redis 아키텍처 및 상세 설계서 (ARCHITECTURE_AND_DESIGN)

## 1. 시스템 구조 및 계층 분리 (Layered Architecture)

```
+-------------------------------------------------------------------------+
|                              CLI REPL 계층                              |
|   cli.py (프롬프트 렌더링, shlex 기반 토크나이징, 에러 포맷팅, exit/quit)    |
+-------------------------------------------------------------------------+
                                    │
                                    ▼ (커맨드 인자 리스트)
+-------------------------------------------------------------------------+
|                           MiniRedis 엔진 파사드                         |
|   mini_redis.py                                                         |
|   - 명령 라우팅 (SET, GET, DEL, EXISTS, DBSIZE, KEYS, CONFIG, INFO, etc) |
|   - 메모리 회계 (used_memory 추적, OOM 가드, LRU 방출 루프)             |
|   - 만료 라이프사이클 (Passive Lazy Expiration + Active Heap Pruning)     |
+-------------------------------------------------------------------------+
            │                               │                   │
            ▼                               ▼                   ▼
┌───────────────────────┐       ┌───────────────────────┐   ┌─────────────┐
│  HashMap (main_store) │       │    DoublyLinkedList   │   │   MinHeap   │
│  - key -> Node        │ <---> │  - 센티넬 Head/Tail   │   │  - TTL 관리 │
│  - O(1) 조회/삽입     │       │  - O(1) 헤드/꼬리 조작│   │  - O(log N) │
│  - 체이닝 & 리사이징  │       │  - LRU 우선순위 큐    │   │             │
└───────────────────────┘       └───────────────────────┘   └─────────────┘
```

---

## 2. 모듈별 상세 설계 규격

### 1) `doubly_linked_list.py` (이중 연결 리스트)
* **목적**: LRU 순서 유지 및 해시맵 체이닝 슬롯용 순수 자료구조.
* **클래스 구성**:
  * `Node`: `key: str`, `value: Any`, `prev: Node`, `next: Node`
  * `DoublyLinkedList`:
    * `head = Node(None, None)` (센티넬 헤드: 가장 최근 사용 - Most Recently Used)
    * `tail = Node(None, None)` (센티넬 테일: 가장 오래됨 - Least Recently Used)
    * `head.next = tail`, `tail.prev = head`
    * `_count: int` (현재 연결된 실제 노드 개수)
* **주요 메서드 명세**:
  * `insert_front(node)`: `head`와 `head.next` 사이에 노드 삽입 ($O(1)$)
  * `insert_back(node)`: `tail.prev`와 `tail` 사이에 노드 삽입 ($O(1)$)
  * `remove_front()`: `head.next` 노드 분리 및 반환 ($O(1)$)
  * `remove_back()`: `tail.prev` 노드 분리 및 반환 ($O(1)$)
  * `remove_node(node)`: 특정 노드의 `prev`와 `next`를 직접 연결하여 분리 ($O(1)$)
  * `move_to_front(node)`: `remove_node(node)` 호출 후 `insert_front(node)` 수행 ($O(1)$)

### 2) `hash_map.py` (체이닝 해시맵)
* **목적**: $O(1)$ 평균 탐색/삽입을 제공하는 핵심 Key-Value 테이블. (내장 dict/set 일체 배제)
* **클래스 구성**:
  * `HashMap`:
    * `_capacity: int` (기본값: 16)
    * `_size: int` (저장된 엔트리 수)
    * `_buckets: list` (크기 `_capacity`의 고정 리스트 `[None] * _capacity`)
    * 각 버킷은 충돌 해결을 위해 체인 노드 리스트를 가짐.
* **해시 함수 설계 (`_hash(key)`)**:
  * 다항 롤링 해시: `hash = sum(ord(c) * (31 ** i)) % _capacity`
* **동적 리사이징 (`_resize`)**:
  * $\text{Load Factor} = \frac{\_size}{\_capacity} > 0.75$ 발생 시:
  * 신규 용량 = `_capacity * 2`
  * 새 버킷 리스트 생성 후 기존 모든 엔트리를 새 버킷으로 재배치(Rehash).
* **주요 메서드**:
  * `put(key, value)`: 기존 키 존재 시 값 교체, 신규 시 체인에 추가 및 리사이즈 검사.
  * `get(key)`: 키 검색 후 value 반환, 없으면 None.
  * `remove(key)`: 체인에서 키 검색 후 노드 삭제, 삭제된 value 반환.
  * `contains(key)`: 키 존재 여부 boolean 반환.
  * `keys()`: 전체 키를 담은 리스트 반환.
  * `size()`: 현재 `_size` 반환.

### 3) `min_heap.py` (최소 힙)
* **목적**: TTL 만료 시점이 가장 빠른 키를 $O(1)$에 확인하고 $O(\log N)$에 방출하기 위한 우선순위 큐.
* **클래스 구성**:
  * `MinHeap`:
    * `_data: list` (완전 이진 트리를 1차원 리스트로 표현)
* **비교 기준**:
  * 원소: `(expire_at: float, key: str)`
  * `item[0]` (타임스탬프) 기준으로 최소 힙 유지.
* **주요 메서드**:
  * `push(item)`: 리스트 끝에 추가 후 `_heapify_up(len(_data) - 1)`
  * `pop()`: 루트와 끝 요소 swap 후 제거, `_heapify_down(0)` 호출 후 루트 반환
  * `peek()`: `_data[0]` 반환 (비어있으면 None)
  * `size()`: `len(_data)`

### 4) `mini_redis.py` (코어 엔진 파사드)
* **필드 구성**:
  * `_store = HashMap()`: `key -> Node` 매핑 (Node는 `key`, `value`를 담음)
  * `_lru_list = DoublyLinkedList()`: 전체 캐시 엔트리의 사용 순서 추적
  * `_ttl_store = HashMap()`: `key -> expire_at` 매핑 (현재 유효한 만료 시각)
  * `_ttl_heap = MinHeap()`: `(expire_at, key)` 힙
  * `_used_memory: int = 0`: 현재 사용 메모리 바이트 합계
  * `_maxmemory: int = 0`: 최대 허용 메모리 (0: 무제한)
  * `_evicted_keys: int = 0`: LRU로 제거된 누적 키 수
* **핵심 알고리즘 1: 메모리 계산 및 LRU Eviction**:
  * `calc_entry_size(key, value) = len(key.encode('utf-8')) + len(value.encode('utf-8'))`
  * `SET` 시 단일 엔트리 크기 > `_maxmemory` (단, `_maxmemory > 0`) 검사:
    * 초과 시 즉시 `(error) OOM command not allowed when used_memory > 'maxmemory'` 발생.
  * 데이터 삽입/갱신 후 `while _maxmemory > 0 and _used_memory > _maxmemory and _lru_list.size() > 0:`
    * `oldest_node = _lru_list.remove_back()`
    * `_store.remove(oldest_node.key)`
    * `_ttl_store.remove(oldest_node.key)`
    * `_used_memory -= calc_entry_size(oldest_node.key, oldest_node.value)`
    * `_evicted_keys += 1`
* **핵심 알고리즘 2: TTL 만료 처리 (Lazy + Active)**:
  * `_check_and_expire(key)`:
    * 키가 존재하고 `expire_at <= time.time()` 이면:
      * 즉시 `_delete_key(key)` 호출 (스토어, LRU 리스트, TTL 맵에서 제거, memory 차감)
      * 만료 처리 반환 True
  * `SET`으로 덮어쓸 때: 기존 키의 TTL을 `_ttl_store.remove(key)`로 초기화(삭제).

### 5) `cli.py` (사용자 인터페이스)
* **명령 파싱**: `shlex.split(line)`을 통해 따옴표(`"Alice"`, `'Bob'`) 안의 공백 보존.
* **에러 포맷팅 표준**:
  * 파싱 에러/따옴표 미완결: `(error) ERR syntax error`
  * 인자 개수 불일치: `(error) ERR wrong number of arguments for '<cmd>' command`
  * 정수 변환 실패: `(error) ERR value is not an integer or out of range`
  * 미등록 명령: `(error) ERR unknown command '<cmd>'`
  * OOM 에러: `(error) OOM command not allowed when used_memory > 'maxmemory'`
* **REPL 루프**:
  * `mini-redis> ` 프롬프트
  * `exit` 또는 `quit` 시 루프 종료 및 안전 종료.
  * Python Traceback이 사용자 화면에 일절 노출되지 않도록 최상단 `try-except Exception` 캡슐화.

---

## 3. 구현 단계 (Step-by-Step Implementation Roadmap)

* **STEP 1**: 기초 자료구조 3종 독립 모듈 구현 및 무결성 단위 검증
  * `doubly_linked_list.py` 구현 및 O(1) 동작 검증
  * `hash_map.py` 구현 및 체이닝/리사이징(0.75 임계치) 검증
  * `min_heap.py` 구현 및 최소 힙 우선순위 정렬 검증
* **STEP 2**: MiniRedis 코어 비즈니스 로직 및 메모리/LRU/TTL 통합 구현
  * `mini_redis.py` 구현 (String 6개 커맨드, 메모리 관리 2개, TTL 2개)
  * UTF-8 바이트 계산, LRU $O(1)$ 연동, Eviction 루프 및 단일 엔트리 OOM 방어
  * 만료 검사 및 덮어쓰기 시 TTL 삭제 정책 구현
* **STEP 3**: CLI REPL 및 Redis 표준 출력/에러 포맷팅 레이어 완성
  * `cli.py` 구현 (프롬프트, 따옴표 인자 파서, 예외 핸들러)
* **STEP 4**: 실증 테스트 및 과제 결과 예시 시나리오 100% 일치 검증
  * 단위 테스트 스크립트 작성 및 자동 실행 (`tests/test_mini_redis.py`)
  * 실제 터미널 실행을 통한 결과 예시(SET, LRU 방출, INFO memory, EXPIRE, TTL, 에러 등) 대조 검증