"""
B5-1 Mini Redis - 코어 엔진 (Core Storage & Facade Engine) 모듈
학습 목적: HashMap, DoublyLinkedList, MinHeap을 결합하여
          O(1) LRU 추적, TTL 만료 관리, 메모리 회계 및 Eviction 루프 총괄.
제약 사항: 내장 dict, set, collections 사용 금지.
"""
import time
from typing import List, Optional

from doubly_linked_list import DoublyLinkedList, Node
from hash_map import HashMap
from min_heap import MinHeap


class MiniRedis:
    """
    Mini Redis의 모든 명령 실행, 메모리 회계, LRU 추적, TTL 만료를 제어하는 코어 파사드.
    """

    def __init__(self):
        # 1. 메인 데이터 저장소: key -> Node(key, value)
        self._store: HashMap = HashMap()
        # 2. LRU 추적용 이중 연결 리스트: Head는 MRU(최신), Tail은 LRU(오래됨)
        self._lru_list: DoublyLinkedList = DoublyLinkedList()
        # 3. TTL 유효 시각 보관소: key -> expire_at (float)
        self._ttl_store: HashMap = HashMap()
        # 4. TTL 만료 우선순위 큐: (expire_at, key)
        self._ttl_heap: MinHeap = MinHeap()

        # 메모리 회계 변수
        self._used_memory: int = 0
        self._maxmemory: int = 0  # 0은 무제한
        self._evicted_keys: int = 0

    # ─────────────────────────────────────────────────────────────
    # 내부 유틸리티 및 헬퍼 메서드
    # ─────────────────────────────────────────────────────────────

    @staticmethod
    def _calc_entry_bytes(key: str, value: str) -> int:
        """
        used_memory 산정 기준(공식):
        used_memory = Σ( len(utf8(key)) + len(utf8(value)) )
        """
        return len(str(key).encode('utf-8')) + len(str(value).encode('utf-8'))

    def _delete_key_internal(self, key: str) -> bool:
        """
        내부적으로 키를 완전히 제거 (스토어, LRU 리스트, TTL 맵에서 제거 및 메모리 차감).
        """
        node: Optional[Node] = self._store.get(key)
        if node is None:
            return False

        # 스토어에서 제거
        self._store.remove(key)
        # LRU 연결 리스트에서 제거
        self._lru_list.remove_node(node)
        # TTL 정보 제거
        self._ttl_store.remove(key)
        # 메모리 차감
        self._used_memory -= self._calc_entry_bytes(node.key, node.value)
        if self._used_memory < 0:
            self._used_memory = 0
        return True

    def _check_and_expire(self, key: str) -> bool:
        """
        키의 만료 여부를 확인하고, 만료되었으면 즉시 삭제(Passive Lazy Expiration).
        만료되어 삭제되었으면 True, 여전히 유효하거나 TTL이 없으면 False 반환.
        """
        expire_at = self._ttl_store.get(key)
        if expire_at is not None:
            if time.time() >= expire_at:
                self._delete_key_internal(key)
                return True
        return False

    def _active_expire_prune(self) -> None:
        """
        최소 힙의 루트를 확인하여 이미 만료 시각이 지난 엔트리를 선제적으로 청소.
        """
        now = time.time()
        while not self._ttl_heap.is_empty():
            peek_item = self._ttl_heap.peek()
            if peek_item is None:
                break
            expire_at, key = peek_item
            if expire_at <= now:
                self._ttl_heap.pop()
                current_ttl = self._ttl_store.get(key)
                # 힙의 타임스탬프와 현재 저장된 TTL이 일치할 때만 만료 삭제
                if current_ttl == expire_at:
                    self._delete_key_internal(key)
            else:
                break

    def _evict_lru_if_needed(self) -> None:
        """
        maxmemory > 0이고 used_memory > maxmemory인 경우,
        used_memory <= maxmemory가 될 때까지 가장 오래 사용되지 않은(LRU) 키를 방출.
        """
        while self._maxmemory > 0 and self._used_memory > self._maxmemory and self._lru_list.size() > 0:
            oldest_node = self._lru_list.remove_back()
            if oldest_node is None:
                break
            # 스토어 및 TTL에서 동기화 제거
            self._store.remove(oldest_node.key)
            self._ttl_store.remove(oldest_node.key)
            self._used_memory -= self._calc_entry_bytes(oldest_node.key, oldest_node.value)
            if self._used_memory < 0:
                self._used_memory = 0
            self._evicted_keys += 1

    # ─────────────────────────────────────────────────────────────
    # String 타입 기본 명령어 (6개)
    # ─────────────────────────────────────────────────────────────

    def set(self, key: str, value: str) -> str:
        """
        SET key value
        1. 단일 엔트리 크기가 maxmemory를 초과하는지 OOM 검사.
        2. 기존 키가 있으면 만료 확인 후 TTL 초기화(삭제) 및 메모리 갱신.
        3. 신규 키면 생성 후 LRU 헤드 삽입.
        4. SET 후 used_memory > maxmemory이면 LRU Eviction 루프 수행.
        """
        new_bytes = self._calc_entry_bytes(key, value)

        # 단일 엔트리 자체가 maxmemory를 초과하는 경우 에러 출력
        if self._maxmemory > 0 and new_bytes > self._maxmemory:
            return "(error) OOM command not allowed when used_memory > 'maxmemory'"

        # 기존 키의 만료 검사 (만료되었으면 먼저 정리)
        self._check_and_expire(key)

        existing_node: Optional[Node] = self._store.get(key)
        if existing_node is not None:
            # 덮어쓰기: 기존 바이트 차감
            old_bytes = self._calc_entry_bytes(existing_node.key, existing_node.value)
            self._used_memory -= old_bytes
            # 기존 TTL 초기화 (규칙: 기존 키 덮어쓸 때 TTL은 삭제)
            self._ttl_store.remove(key)
            # 값 갱신 및 LRU 이동
            existing_node.value = value
            self._lru_list.move_to_front(existing_node)
        else:
            # 신규 삽입
            new_node = Node(key=key, value=value)
            self._store.put(key, new_node)
            self._lru_list.insert_front(new_node)

        # 메모리 가산
        self._used_memory += new_bytes

        # maxmemory 초과 시 LRU 제거
        self._evict_lru_if_needed()

        return "OK"

    def get(self, key: str) -> str:
        """
        GET key
        만료된 키거나 존재하지 않으면 (nil).
        존재하면 값 반환 및 LRU 최신화 (성공 시에만 LRU 갱신).
        """
        if self._check_and_expire(key):
            return "(nil)"

        node: Optional[Node] = self._store.get(key)
        if node is None:
            return "(nil)"

        # 성공 시 LRU 순서 갱신
        self._lru_list.move_to_front(node)
        return f'"{node.value}"'

    def delete(self, key: str) -> str:
        """
        DEL key
        삭제 성공 시 (integer) 1, 없으면 (integer) 0.
        LRU/TTL 관련 구조에서도 완전 제거.
        """
        if self._check_and_expire(key):
            return "(integer) 0"

        if self._delete_key_internal(key):
            return "(integer) 1"
        return "(integer) 0"

    def exists(self, key: str) -> str:
        """
        EXISTS key
        존재하면 (integer) 1, 없으면 (integer) 0.
        """
        if self._check_and_expire(key):
            return "(integer) 0"

        if self._store.contains(key):
            return "(integer) 1"
        return "(integer) 0"

    def dbsize(self) -> str:
        """
        DBSIZE
        현재 저장된 유효 키 개수를 (integer) N으로 반환.
        """
        self._active_expire_prune()
        # 모든 키에 대해 만료 여부 최종 스캔
        keys = self._store.keys()
        valid_count = 0
        for k in keys:
            if not self._check_and_expire(k):
                valid_count += 1
        return f"(integer) {valid_count}"

    def keys(self) -> str:
        """
        KEYS
        전체 키 목록을 출력.
        키가 없으면 (empty array) 출력.
        """
        self._active_expire_prune()
        raw_keys = self._store.keys()
        valid_keys: List[str] = []
        for k in raw_keys:
            if not self._check_and_expire(k):
                valid_keys.append(k)

        if not valid_keys:
            return "(empty array)"

        lines = []
        for idx, k in enumerate(valid_keys, start=1):
            lines.append(f'{idx}. "{k}"')
        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────
    # 메모리 관리 명령어 (2개)
    # ─────────────────────────────────────────────────────────────

    def config_set_maxmemory(self, bytes_str: str) -> str:
        """
        CONFIG SET maxmemory bytes
        0 이상의 정수. 0은 무제한.
        """
        try:
            val = int(bytes_str)
            if val < 0:
                return "(error) ERR value is not an integer or out of range"
        except ValueError:
            return "(error) ERR value is not an integer or out of range"

        self._maxmemory = val
        # maxmemory를 낮췄을 때 초과분이 발생하면 즉시 Eviction 수행
        self._evict_lru_if_needed()
        return "OK"

    def info_memory(self) -> str:
        """
        INFO memory
        used_memory, maxmemory, evicted_keys 3개 항목 출력.
        """
        lines = [
            f"used_memory:{self._used_memory}",
            f"maxmemory:{self._maxmemory}",
            f"evicted_keys:{self._evicted_keys}"
        ]
        return "\n".join(lines)

    # ─────────────────────────────────────────────────────────────
    # TTL 관리 명령어 (2개)
    # ─────────────────────────────────────────────────────────────

    def expire(self, key: str, seconds_str: str) -> str:
        """
        EXPIRE key seconds
        1. key 부재 시 (integer) 0.
        2. seconds <= 0 시 즉시 만료 삭제 후 (integer) 1.
        3. 정상 시 (expire_at, key) 등록 후 (integer) 1.
        """
        try:
            seconds = int(seconds_str)
        except ValueError:
            return "(error) ERR value is not an integer or out of range"

        # 기존 만료 검사
        if self._check_and_expire(key):
            return "(integer) 0"

        if not self._store.contains(key):
            return "(integer) 0"

        if seconds <= 0:
            # 즉시 만료 삭제
            self._delete_key_internal(key)
            return "(integer) 1"

        expire_at = time.time() + seconds
        self._ttl_store.put(key, expire_at)
        self._ttl_heap.push((expire_at, key))
        return "(integer) 1"

    def ttl(self, key: str) -> str:
        """
        TTL key
        key 부재 시 (integer) -2.
        key 존재하나 TTL 미설정 시 (integer) -1.
        만료 시간 존재 시 남은 초 (integer) N.
        """
        if self._check_and_expire(key):
            return "(integer) -2"

        if not self._store.contains(key):
            return "(integer) -2"

        expire_at = self._ttl_store.get(key)
        if expire_at is None:
            return "(integer) -1"

        remaining = int(expire_at - time.time())
        if remaining < 0:
            self._delete_key_internal(key)
            return "(integer) -2"

        return f"(integer) {remaining}"