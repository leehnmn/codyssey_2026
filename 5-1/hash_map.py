"""
B5-1 Mini Redis - 해시맵 (Hash Map) 모듈
학습 목적: 직접 설계한 해시 함수, 체이닝 충돌 해결, 로드 팩터 기반 2배 확장 리사이징 구현.
제약 사항: 내장 dict, set, collections 사용 금지 (고정 리스트 인덱스 접근만 허용).
"""
from typing import Any, List, Optional


class HashEntry:
    """해시맵의 체이닝 슬롯에 저장되는 단일 엔트리."""

    def __init__(self, key: str, value: Any, next_entry: Optional['HashEntry'] = None):
        self.key: str = key
        self.value: Any = value
        self.next: Optional['HashEntry'] = next_entry

    def __repr__(self) -> str:
        return f"HashEntry({self.key}={self.value})"


class HashMap:
    """
    체이닝(Chaining) 방식과 동적 리사이징(Load Factor > 0.75)을 적용한 자체 해시맵.
    내장 dict나 set을 일체 사용하지 않고 고정 버킷 리스트로 구현됨.
    """

    DEFAULT_INITIAL_CAPACITY = 16
    LOAD_FACTOR_THRESHOLD = 0.75

    def __init__(self, initial_capacity: int = DEFAULT_INITIAL_CAPACITY):
        self._capacity: int = max(4, initial_capacity)
        self._size: int = 0
        # 고정 크기 버킷 배열: 각 원소는 HashEntry 체인의 헤드 포인터
        self._buckets: List[Optional[HashEntry]] = [None] * self._capacity

    def size(self) -> int:
        """저장된 유효 엔트리 개수 반환 (O(1))."""
        return self._size

    def is_empty(self) -> bool:
        """해시맵이 비어있는지 여부 반환 (O(1))."""
        return self._size == 0

    def capacity(self) -> int:
        """현재 할당된 총 버킷 용량 반환."""
        return self._capacity

    def _hash(self, key: str) -> int:
        """
        문자열 키에 대한 다항 롤링 해시(Polynomial Rolling Hash) 함수.
        소수 31을 밑으로 하여 각 문자의 유니코드 값을 가중 합산 후 버킷 용량으로 모듈러 연산.
        """
        hash_val = 0
        prime = 31
        for char in str(key):
            hash_val = (hash_val * prime + ord(char)) & 0x7FFFFFFF
        return hash_val % self._capacity

    def _resize(self, new_capacity: int) -> None:
        """
        버킷 테이블을 지정된 용량으로 2배 확장하고 전체 엔트리를 재해싱(Rehash)함.
        시간 복잡도: O(N)
        """
        old_buckets = self._buckets
        self._capacity = new_capacity
        self._buckets = [None] * self._capacity
        self._size = 0  # put 호출 시 다시 증가됨

        for head in old_buckets:
            curr = head
            while curr is not None:
                self.put(curr.key, curr.value)
                curr = curr.next

    def put(self, key: str, value: Any) -> None:
        """
        키와 값을 해시맵에 저장.
        기존 키가 존재하면 값을 덮어쓰고, 신규 키면 체인의 헤드에 추가.
        로드 팩터가 0.75를 초과하면 버킷을 2배 확장함.
        """
        idx = self._hash(key)
        curr = self._buckets[idx]

        # 1. 기존 키 존재 여부 탐색 (덮어쓰기)
        while curr is not None:
            if curr.key == key:
                curr.value = value
                return
            curr = curr.next

        # 2. 신규 키 추가 (체인의 헤드에 삽입)
        new_entry = HashEntry(key, value, next_entry=self._buckets[idx])
        self._buckets[idx] = new_entry
        self._size += 1

        # 3. 로드 팩터 검사 및 2배 확장
        if (self._size / self._capacity) > self.LOAD_FACTOR_THRESHOLD:
            self._resize(self._capacity * 2)

    def get(self, key: str) -> Optional[Any]:
        """
        키에 해당하는 값을 검색하여 반환. 존재하지 않으면 None 반환.
        시간 복잡도: 평균 O(1)
        """
        idx = self._hash(key)
        curr = self._buckets[idx]
        while curr is not None:
            if curr.key == key:
                return curr.value
            curr = curr.next
        return None

    def contains(self, key: str) -> bool:
        """해시맵에 특정 키가 존재하는지 여부 확인."""
        idx = self._hash(key)
        curr = self._buckets[idx]
        while curr is not None:
            if curr.key == key:
                return True
            curr = curr.next
        return False

    def remove(self, key: str) -> Optional[Any]:
        """
        키에 해당하는 엔트리를 체인에서 제거하고 기존 값을 반환.
        존재하지 않으면 None 반환.
        """
        idx = self._hash(key)
        curr = self._buckets[idx]
        prev = None

        while curr is not None:
            if curr.key == key:
                if prev is None:
                    # 체인의 첫 번째 노드 제거
                    self._buckets[idx] = curr.next
                else:
                    prev.next = curr.next
                self._size -= 1
                return curr.value
            prev = curr
            curr = curr.next
        return None

    def keys(self) -> List[str]:
        """
        현재 해시맵에 저장된 모든 키의 목록을 리스트로 반환.
        순서는 버킷 및 체인 탐색 순서를 따름.
        """
        result: List[str] = []
        for head in self._buckets:
            curr = head
            while curr is not None:
                result.append(curr.key)
                curr = curr.next
        return result