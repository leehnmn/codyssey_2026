"""
B5-1 Mini Redis 종합 단위 및 통합 검증 테스트 스위트
모든 필수 요구사항, 자료구조 3종, 메모리 산정, OOM 방어, LRU 방출, TTL 만료, CLI 파싱 검증.
"""
import time
import unittest

from doubly_linked_list import DoublyLinkedList, Node
from hash_map import HashMap
from min_heap import MinHeap
from mini_redis import MiniRedis
from cli import parse_line, MiniRedisCLI


class TestDoublyLinkedList(unittest.TestCase):
    """이중 연결 리스트 6대 연산 O(1) 검증."""

    def test_insert_and_remove(self):
        dll = DoublyLinkedList()
        self.assertEqual(dll.size(), 0)

        n1 = Node("k1", "v1")
        n2 = Node("k2", "v2")
        n3 = Node("k3", "v3")

        dll.insert_front(n1)
        dll.insert_front(n2)
        dll.insert_back(n3)
        # MRU 순서: n2 -> n1 -> n3 (LRU)
        self.assertEqual(dll.size(), 3)

        # move_to_front
        dll.move_to_front(n3)
        # 순서: n3 -> n2 -> n1

        # remove_back (가장 오래된 노드 n1)
        removed = dll.remove_back()
        self.assertEqual(removed.key, "k1")
        self.assertEqual(dll.size(), 2)

        # remove_front (n3)
        removed_front = dll.remove_front()
        self.assertEqual(removed_front.key, "k3")
        self.assertEqual(dll.size(), 1)

        # 남아있는 n2 제거
        dll.remove_node(n2)
        self.assertEqual(dll.size(), 0)
        self.assertTrue(dll.is_empty())


class TestHashMap(unittest.TestCase):
    """해시맵 체이닝, 리사이징(로드팩터 0.75), 기본 연산 검증."""

    def test_basic_crud(self):
        hm = HashMap(initial_capacity=4)
        hm.put("a", "1")
        hm.put("b", "2")
        hm.put("c", "3")
        self.assertEqual(hm.size(), 3)
        self.assertEqual(hm.get("a"), "1")
        self.assertEqual(hm.get("b"), "2")
        self.assertTrue(hm.contains("c"))
        self.assertFalse(hm.contains("d"))

        # 덮어쓰기
        hm.put("a", "100")
        self.assertEqual(hm.get("a"), "100")
        self.assertEqual(hm.size(), 3)

        # 삭제
        val = hm.remove("b")
        self.assertEqual(val, "2")
        self.assertEqual(hm.size(), 2)
        self.assertIsNone(hm.get("b"))

    def test_resizing_on_load_factor(self):
        hm = HashMap(initial_capacity=4)
        # initial capacity 4, threshold = 4 * 0.75 = 3. 4번째 원소 삽입 시 2배 확장(8)
        hm.put("k1", "v1")
        hm.put("k2", "v2")
        hm.put("k3", "v3")
        self.assertEqual(hm.capacity(), 4)

        # 4번째 삽입 -> size 4 -> 4/4 = 1.0 > 0.75 -> resize to 8
        hm.put("k4", "v4")
        self.assertGreaterEqual(hm.capacity(), 8)
        self.assertEqual(hm.size(), 4)

        # 재해싱 후 모든 키 접근 가능 확인
        self.assertEqual(hm.get("k1"), "v1")
        self.assertEqual(hm.get("k2"), "v2")
        self.assertEqual(hm.get("k3"), "v3")
        self.assertEqual(hm.get("k4"), "v4")


class TestMinHeap(unittest.TestCase):
    """최소 힙 만료 시점 정렬 검증."""

    def test_heap_order(self):
        heap = MinHeap()
        heap.push((100.5, "k3"))
        heap.push((10.0, "k1"))
        heap.push((50.2, "k2"))
        heap.push((5.1, "k0"))

        self.assertEqual(heap.size(), 4)
        self.assertEqual(heap.peek()[1], "k0")

        # 꺼낼 때마다 오름차순
        self.assertEqual(heap.pop()[1], "k0")
        self.assertEqual(heap.pop()[1], "k1")
        self.assertEqual(heap.pop()[1], "k2")
        self.assertEqual(heap.pop()[1], "k3")
        self.assertTrue(heap.is_empty())


class TestMiniRedisCore(unittest.TestCase):
    """MiniRedis 코어 비즈니스 로직 및 과제 예시 시나리오 검증."""

    def test_specification_example_scenario(self):
        """과제 명세의 8번 결과 예시 시나리오 100% 재현 테스트."""
        redis = MiniRedis()

        # mini-redis> CONFIG SET maxmemory 30
        res = redis.config_set_maxmemory("30")
        self.assertEqual(res, "OK")

        # mini-redis> SET user:1 "Alice"  -> len("user:1")=6, len("Alice")=5 -> entry=11, total=11
        res = redis.set("user:1", "Alice")
        self.assertEqual(res, "OK")

        # mini-redis> SET user:2 "Bob"    -> len("user:2")=6, len("Bob")=3 -> entry=9, total=20
        res = redis.set("user:2", "Bob")
        self.assertEqual(res, "OK")

        # mini-redis> SET user:3 "Charlie" -> len("user:3")=6, len("Charlie")=7 -> entry=13, total=33 (>30)
        # maxmemory(30) 초과로 가장 오래된 user:1(11바이트) Eviction -> used_memory=22 <= 30
        res = redis.set("user:3", "Charlie")
        self.assertEqual(res, "OK")

        # mini-redis> GET user:1 -> (nil)
        self.assertEqual(redis.get("user:1"), "(nil)")

        # mini-redis> INFO memory -> used_memory:22, maxmemory:30, evicted_keys:1
        info = redis.info_memory()
        self.assertIn("used_memory:22", info)
        self.assertIn("maxmemory:30", info)
        self.assertIn("evicted_keys:1", info)

        # mini-redis> KEYS -> user:2, user:3
        keys_out = redis.keys()
        self.assertIn('"user:2"', keys_out)
        self.assertIn('"user:3"', keys_out)
        self.assertNotIn('"user:1"', keys_out)

        # mini-redis> EXPIRE user:2 3
        res = redis.expire("user:2", "3")
        self.assertEqual(res, "(integer) 1")

        # mini-redis> TTL user:2 -> 남은 초 (integer) 2 또는 3
        ttl_out = redis.ttl("user:2")
        self.assertTrue(ttl_out.startswith("(integer) "))

    def test_single_entry_oom(self):
        """단일 엔트리 > maxmemory 시 저장 거부 및 OOM 에러 출력 검증."""
        redis = MiniRedis()
        redis.config_set_maxmemory("10")
        # key: "bigkey"(6) + value: "toolargevalue"(13) = 19 > 10
        res = redis.set("bigkey", "toolargevalue")
        self.assertEqual(res, "(error) OOM command not allowed when used_memory > 'maxmemory'")
        self.assertEqual(redis.get("bigkey"), "(nil)")
        self.assertIn("used_memory:0", redis.info_memory())

    def test_ttl_lazy_expiration(self):
        """TTL 만료 후 GET 시 (nil) 및 TTL -2 반환 검증."""
        redis = MiniRedis()
        redis.set("temp", "val")
        # 즉시 만료 (seconds=0)
        res = redis.expire("temp", "0")
        self.assertEqual(res, "(integer) 1")
        self.assertEqual(redis.get("temp"), "(nil)")
        self.assertEqual(redis.ttl("temp"), "(integer) -2")

    def test_set_clears_existing_ttl(self):
        """기존 키 덮어쓰기 시 TTL 삭제 검증."""
        redis = MiniRedis()
        redis.set("k", "v1")
        redis.expire("k", "100")
        self.assertNotEqual(redis.ttl("k"), "(integer) -1")

        # 덮어쓰기
        redis.set("k", "v2")
        # TTL 초기화되어 -1 반환
        self.assertEqual(redis.ttl("k"), "(integer) -1")
        self.assertEqual(redis.get("k"), '"v2"')


class TestCLIParser(unittest.TestCase):
    """CLI 따옴표 토크나이징 및 표준 에러 검증."""

    def test_parse_quoted_strings(self):
        tokens = parse_line('SET user:1 "Alice In Wonderland"')
        self.assertEqual(tokens, ["SET", "user:1", "Alice In Wonderland"])

    def test_cli_error_messages(self):
        cli = MiniRedisCLI()
        # unknown command
        res = cli.execute_command(["HELLO"])
        self.assertEqual(res, "(error) ERR unknown command 'HELLO'")

        # wrong number of arguments
        res = cli.execute_command(["GET"])
        self.assertEqual(res, "(error) ERR wrong number of arguments for 'get' command")

        # integer parsing error
        res = cli.execute_command(["CONFIG", "SET", "maxmemory", "abc"])
        self.assertEqual(res, "(error) ERR value is not an integer or out of range")


if __name__ == "__main__":
    unittest.main()