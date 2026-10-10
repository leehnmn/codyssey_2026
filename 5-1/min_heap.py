"""
B5-1 Mini Redis - 최소 힙 (Min-Heap) 모듈
학습 목적: 완전 이진 트리를 1차원 리스트로 구현하고 O(log N) TTL 만료 시간 정렬 제공.
제약 사항: heapq, collections 등 내장 모듈 사용 금지.
"""
from typing import Any, List, Optional, Tuple


class MinHeap:
    """
    최소 힙(Min-Heap) 구현체.
    원소는 주로 (expire_at, key) 튜플 형태를 취하며, 첫 번째 원소(expire_at)를 우선순위 키로 비교함.
    """

    def __init__(self):
        # 1차원 리스트 기반 완전 이진 트리
        self._data: List[Tuple[float, str]] = []

    def size(self) -> int:
        """힙에 저장된 원소 개수 반환 (O(1))."""
        return len(self._data)

    def is_empty(self) -> bool:
        """힙이 비어있는지 여부 반환 (O(1))."""
        return len(self._data) == 0

    def peek(self) -> Optional[Tuple[float, str]]:
        """
        가장 우선순위가 높은(만료 시각이 가장 빠른) 루트 원소를 확인.
        힙이 비어있으면 None 반환. 시간 복잡도: O(1)
        """
        if self.is_empty():
            return None
        return self._data[0]

    def push(self, item: Tuple[float, str]) -> None:
        """
        새로운 원소를 힙의 맨 끝에 추가한 후 상향 힙화(_heapify_up) 수행.
        시간 복잡도: O(log N)
        """
        self._data.append(item)
        self._heapify_up(len(self._data) - 1)

    def pop(self) -> Optional[Tuple[float, str]]:
        """
        루트 원소(최소값)를 제거하여 반환하고, 맨 끝 원소를 루트로 이동시킨 후 하향 힙화(_heapify_down) 수행.
        시간 복잡도: O(log N)
        """
        if self.is_empty():
            return None
        if len(self._data) == 1:
            return self._data.pop()

        root = self._data[0]
        # 맨 끝 원소를 루트 위치로 이동
        self._data[0] = self._data.pop()
        self._heapify_down(0)
        return root

    def _heapify_up(self, index: int) -> None:
        """
        새로 삽입된 원소를 부모 노드와 비교하며 상향 이동.
        부모 인덱스: (index - 1) // 2
        """
        curr = index
        while curr > 0:
            parent = (curr - 1) // 2
            # expire_at 기준 비교 (튜플의 첫 번째 필드)
            if self._data[curr][0] < self._data[parent][0]:
                self._data[curr], self._data[parent] = self._data[parent], self._data[curr]
                curr = parent
            else:
                break

    def _heapify_down(self, index: int) -> None:
        """
        루트로 이동된 원소를 자식 노드들과 비교하며 하향 이동.
        왼쪽 자식: 2 * index + 1, 오른쪽 자식: 2 * index + 2
        """
        curr = index
        size = len(self._data)

        while True:
            smallest = curr
            left = 2 * curr + 1
            right = 2 * curr + 2

            if left < size and self._data[left][0] < self._data[smallest][0]:
                smallest = left

            if right < size and self._data[right][0] < self._data[smallest][0]:
                smallest = right

            if smallest != curr:
                self._data[curr], self._data[smallest] = self._data[smallest], self._data[curr]
                curr = smallest
            else:
                break