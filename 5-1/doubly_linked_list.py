"""
B5-1 Mini Redis - 이중 연결 리스트 (Doubly Linked List) 모듈
학습 목적: O(1) 삽입/삭제/이동 연산 및 LRU 추적 지원.
제약 사항: 내장 dict, set, collections 사용 금지.
"""
from typing import Any, Optional


class Node:
    """이중 연결 리스트의 기본 노드 객체."""

    def __init__(self, key: Optional[str] = None, value: Any = None):
        self.key: Optional[str] = key
        self.value: Any = value
        self.prev: Optional['Node'] = None
        self.next: Optional['Node'] = None

    def __repr__(self) -> str:
        return f"Node(key={self.key}, value={self.value})"


class DoublyLinkedList:
    """
    센티넬(Head/Tail) 노드 기반의 이중 연결 리스트.
    모든 삽입, 삭제, 이동 연산은 O(1) 시간 복잡도를 보장함.
    """

    def __init__(self):
        # 센티넬 헤드(MRU)와 테일(LRU) 초기화
        self.head = Node(key="__HEAD__", value=None)
        self.tail = Node(key="__TAIL__", value=None)
        self.head.next = self.tail
        self.tail.prev = self.head
        self._count: int = 0

    def size(self) -> int:
        """현재 연결 리스트에 포함된 실제 노드 개수 반환 (O(1))."""
        return self._count

    def is_empty(self) -> bool:
        """리스트가 비어있는지 여부 반환 (O(1))."""
        return self._count == 0

    def insert_front(self, node: Node) -> None:
        """
        헤드(Head) 바로 뒤에 노드를 삽입 (가장 최근 사용 - MRU 위치).
        시간 복잡도: O(1)
        """
        first = self.head.next
        node.prev = self.head
        node.next = first
        self.head.next = node
        first.prev = node
        self._count += 1

    def insert_back(self, node: Node) -> None:
        """
        테일(Tail) 바로 앞에 노드를 삽입.
        시간 복잡도: O(1)
        """
        last = self.tail.prev
        node.prev = last
        node.next = self.tail
        last.next = node
        self.tail.prev = node
        self._count += 1

    def remove_node(self, node: Node) -> Optional[Node]:
        """
        주어진 노드를 리스트 연결에서 분리하여 반환.
        센티넬 노드는 삭제할 수 없음.
        시간 복잡도: O(1)
        """
        if node is self.head or node is self.tail:
            return None
        if node.prev is None or node.next is None:
            return None

        p = node.prev
        n = node.next
        p.next = n
        n.prev = p

        node.prev = None
        node.next = None
        self._count -= 1
        return node

    def remove_front(self) -> Optional[Node]:
        """
        가장 앞에 위치한 노드를 제거하고 반환.
        시간 복잡도: O(1)
        """
        if self.is_empty():
            return None
        return self.remove_node(self.head.next)

    def remove_back(self) -> Optional[Node]:
        """
        가장 뒤에 위치한 노드(가장 오래된 LRU 노드)를 제거하고 반환.
        시간 복잡도: O(1)
        """
        if self.is_empty():
            return None
        return self.remove_node(self.tail.prev)

    def move_to_front(self, node: Node) -> None:
        """
        기존에 리스트에 포함된 노드를 분리한 후 헤드(MRU) 바로 뒤로 이동.
        시간 복잡도: O(1)
        """
        self.remove_node(node)
        self.insert_front(node)
    