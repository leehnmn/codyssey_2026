#!/usr/bin/env python3
"""
Mini Git - CLI 기반 분산 버전 관리 시스템 구현체
===================================================
Git의 핵심 구조(커밋 DAG, 브랜치, 역색인, 직접 구현한 정렬, 최단 경로 BFS, 위상 정렬)를
순수 Python 표준 라이브러리(기본 자료형 dict/list/set 및 시간/문자열)만으로 구현한 프로그램입니다.

[제약 사항 준수]
- Python 표준 정렬 API (sorted(), list.sort()) 일절 사용 금지 -> MergeSort, QuickSort 직접 구현
- 그래프 전용 라이브러리 일절 사용 금지 -> 인접 리스트 및 BFS/Kahn's 위상 정렬 직접 구현
- 대소문자 무구분 명령어 파싱 및 따옴표 공백 처리 지원
"""

from __future__ import annotations
import sys
import os
import shlex
import hashlib
import time
import datetime
from collections import deque
import random
from typing import Optional, List, Dict, Set, Tuple, Callable, Any


# ============================================================================
# 1. 커밋 노드 및 데이터 모델
# ============================================================================

class Commit:
    """
    커밋 노드 (DAG의 정점)
    - hash: 유일한 커밋 식별자 (세션 내 중복 방지)
    - message: 커밋 메시지
    - author: 작성자 이름
    - timestamp: 커밋 생성 일시 (YYYY-MM-DD HH:MM:SS)
    - parents: 부모 커밋 해시 리스트 (0개 이상)
    - branch: 커밋 생성 당시의 브랜치 명
    """
    def __init__(
        self,
        commit_hash: str,
        message: str,
        author: str,
        timestamp: str,
        parents: Optional[List[str]] = None,
        branch: str = "main"
    ):
        self.hash: str = commit_hash
        self.message: str = message
        self.author: str = author
        self.timestamp: str = timestamp
        self.parents: List[str] = parents if parents is not None else []
        self.branch: str = branch

    def __repr__(self) -> str:
        return f"<Commit {self.hash} by {self.author}: {self.message}>"


# ============================================================================
# 2. 정렬 알고리즘 직접 구현 (표준 sorted(), list.sort() 사용 금지)
# ============================================================================

class CustomSort:
    """
    정렬 알고리즘 구현 클래스
    Python 내장 sorted() 및 list.sort()를 전혀 사용하지 않고
    직접 구현한 분할 정복(Divide & Conquer) 기반 정렬 알고리즘 모음입니다.
    """

    @staticmethod
    def merge_sort(items: List[Any], key: Optional[Callable[[Any], Any]] = None, reverse: bool = False) -> List[Any]:
        """
        병합 정렬 (Merge Sort)
        - 시간복잡도: 평균 O(N log N), 최악 O(N log N), 최선 O(N log N)
        - 공간복잡도: O(N)
        - 안정 정렬(Stable Sort): 동일한 키 값을 가진 원소들의 상대적 순서가 보존됨.
        """
        if len(items) <= 1:
            return list(items)

        mid = len(items) // 2
        left_half = CustomSort.merge_sort(items[:mid], key=key, reverse=reverse)
        right_half = CustomSort.merge_sort(items[mid:], key=key, reverse=reverse)

        merged: List[Any] = []
        i = j = 0
        while i < len(left_half) and j < len(right_half):
            val_l = key(left_half[i]) if key else left_half[i]
            val_r = key(right_half[j]) if key else right_half[j]

            # 안정 정렬 유지를 위해 동률일 때 왼쪽(먼저 나온 원소)을 우선 선택
            if not reverse:
                if val_l <= val_r:
                    merged.append(left_half[i])
                    i += 1
                else:
                    merged.append(right_half[j])
                    j += 1
            else:
                if val_l >= val_r:
                    merged.append(left_half[i])
                    i += 1
                else:
                    merged.append(right_half[j])
                    j += 1

        while i < len(left_half):
            merged.append(left_half[i])
            i += 1
        while j < len(right_half):
            merged.append(right_half[j])
            j += 1

        return merged

    @staticmethod
    def quick_sort(items: List[Any], key: Optional[Callable[[Any], Any]] = None, reverse: bool = False) -> List[Any]:
        """
        퀵 정렬 (Quick Sort)
        - 시간복잡도: 평균 O(N log N), 최악 O(N^2)
        - 공간복잡도: O(log N) 재귀 호출 스택
        - 불안정 정렬(Unstable Sort)
        - Median-of-Three 피벗 선택 전략으로 이미 정렬된 배열에서의 O(N^2) 최악 성능을 완화.
        """
        arr = list(items)

        def _partition(low: int, high: int) -> int:
            mid = (low + high) // 2
            # 3개 후보군(low, mid, high) 중 중앙값(Median) 선택
            candidates = [
                (low, key(arr[low]) if key else arr[low]),
                (mid, key(arr[mid]) if key else arr[mid]),
                (high, key(arr[high]) if key else arr[high])
            ]
            # 3개 원소 간단 비교 정렬
            for a in range(3):
                for b in range(a + 1, 3):
                    if candidates[a][1] > candidates[b][1]:
                        candidates[a], candidates[b] = candidates[b], candidates[a]

            pivot_index = candidates[1][0]
            # 피벗을 맨 끝으로 교환
            arr[pivot_index], arr[high] = arr[high], arr[pivot_index]
            pivot_val = key(arr[high]) if key else arr[high]

            i = low - 1
            for j in range(low, high):
                val_j = key(arr[j]) if key else arr[j]
                if (not reverse and val_j <= pivot_val) or (reverse and val_j >= pivot_val):
                    i += 1
                    arr[i], arr[j] = arr[j], arr[i]

            arr[i + 1], arr[high] = arr[high], arr[i + 1]
            return i + 1

        def _qsort(low: int, high: int) -> None:
            if low < high:
                pi = _partition(low, high)
                _qsort(low, pi - 1)
                _qsort(pi + 1, high)

        if len(arr) > 1:
            _qsort(0, len(arr) - 1)
        return arr

    @staticmethod
    def insertion_sort(items: List[Any], key: Optional[Callable[[Any], Any]] = None, reverse: bool = False) -> List[Any]:
        """
        삽입 정렬 (Insertion Sort) - 알고리즘 비교용
        - 시간복잡도: 최선 O(N), 평균 O(N^2), 최악 O(N^2)
        - 안정 정렬
        """
        arr = list(items)
        for i in range(1, len(arr)):
            current = arr[i]
            cur_val = key(current) if key else current
            j = i - 1
            while j >= 0:
                prev_val = key(arr[j]) if key else arr[j]
                if (not reverse and prev_val > cur_val) or (reverse and prev_val < cur_val):
                    arr[j + 1] = arr[j]
                    j -= 1
                else:
                    break
            arr[j + 1] = current
        return arr


# ============================================================================
# 3. 역색인 (Inverted Index)
# ============================================================================

class InvertedIndex:
    """
    역색인(Inverted Index) 엔진
    단어(keyword) 또는 작성자(author)를 키(Key)로 하고,
    해당 속성을 갖는 커밋 해시 리스트를 값(Value)으로 저장합니다.
    - 순회 검색: O(N) (모든 커밋을 열어보아야 함)
    - 역색인 검색: 해시 테이블 조회를 통해 O(1)에 후보군 커밋 목록 획득 가능
    """
    def __init__(self):
        # keyword (lowercase) -> list of commit hashes
        self.keyword_to_hashes: Dict[str, List[str]] = {}
        # author (lowercase) -> list of commit hashes
        self.author_to_hashes: Dict[str, List[str]] = {}

    def index_commit(self, commit: Commit) -> None:
        """새 커밋 생성 시 인덱스 업데이트"""
        # 1) 메시지 키워드 토큰화 (공백 기준 분리 + 소문자 정규화)
        tokens = commit.message.split()
        seen_in_message: Set[str] = set()

        for token in tokens:
            # 기본 문장부호 제거 및 소문자화
            cleaned = token.strip(".,!?:;\"'()[]{}").lower()
            if cleaned and cleaned not in seen_in_message:
                seen_in_message.add(cleaned)
                if cleaned not in self.keyword_to_hashes:
                    self.keyword_to_hashes[cleaned] = []
                self.keyword_to_hashes[cleaned].append(commit.hash)

        # 2) 작성자 인덱스 등록 (소문자 정규화)
        author_key = commit.author.strip().lower()
        if author_key not in self.author_to_hashes:
            self.author_to_hashes[author_key] = []
        self.author_to_hashes[author_key].append(commit.hash)

    def search_keyword(self, keyword: str) -> List[str]:
        """키워드로 커밋 해시 목록 조회"""
        cleaned = keyword.strip(".,!?:;\"'()[]{}").lower()
        return list(self.keyword_to_hashes.get(cleaned, []))

    def search_author(self, author: str) -> List[str]:
        """작성자명으로 커밋 해시 목록 조회"""
        cleaned = author.strip().lower()
        return list(self.author_to_hashes.get(cleaned, []))


# ============================================================================
# 4. 커밋 그래프 (DAG) 및 탐색 알고리즘
# ============================================================================

class CommitGraph:
    """
    커밋 그래프 자료구조 및 알고리즘
    - Git의 커밋 이력은 방향성 비순환 그래프(DAG, Directed Acyclic Graph)입니다.
    - 부모는 자식보다 과거에 생성되며, 자식이 부모를 참조하므로 사이클(순환)이 생성될 수 없습니다.
    """
    def __init__(self):
        # hash -> Commit 매핑 (O(1) 커밋 조회)
        self.commits: Dict[str, Commit] = {}

    def add_commit(self, commit: Commit) -> None:
        self.commits[commit.hash] = commit

    def get_commit(self, commit_hash: str) -> Optional[Commit]:
        return self.commits.get(commit_hash)

    def topological_sort_parents_first(self) -> List[Commit]:
        """
        위상 정렬 (Topological Sort):
        부모 커밋이 항상 자식 커밋보다 먼저 출력되도록 순서를 정렬합니다.
        (Kahn's Algorithm 구현)
        - 간선 방향 정의: Parent -> Child (부모가 자식의 선수 조건)
        - 진입 차수(in-degree): 해당 커밋의 부모 수
        - 진입 차수가 0인 커밋(루트 커밋)부터 큐에 넣고 순차 탐색
        """
        if not self.commits:
            return []

        # 1. 진입 차수 및 자식 인접 리스트 구축
        # graph: parent_hash -> list of child_hashes
        children_map: Dict[str, List[str]] = {h: [] for h in self.commits}
        in_degree: Dict[str, int] = {h: 0 for h in self.commits}

        for commit_hash, commit in self.commits.items():
            valid_parents = [p for p in commit.parents if p in self.commits]
            in_degree[commit_hash] = len(valid_parents)
            for p in valid_parents:
                children_map[p].append(commit_hash)

        # 2. 진입 차수 0인 노드 수집 (부모가 없는 최초 커밋들)
        zero_in_degree = [h for h, deg in in_degree.items() if deg == 0]
        # 일관된 출력을 위해 타임스탬프 순 병합 정렬
        zero_in_degree = CustomSort.merge_sort(
            zero_in_degree,
            key=lambda h: (self.commits[h].timestamp, h)
        )

        queue = deque(zero_in_degree)
        sorted_hashes: List[str] = []

        # 3. Kahn's Algorithm 수행
        while queue:
            curr_hash = queue.popleft()
            sorted_hashes.append(curr_hash)

            # 자식들의 진입 차수 감소
            ready_children: List[str] = []
            for child_hash in children_map[curr_hash]:
                in_degree[child_hash] -= 1
                if in_degree[child_hash] == 0:
                    ready_children.append(child_hash)

            # 여러 자식이 동시에 진입 차수 0이 되었을 때 일관된 순서 유지
            ready_children = CustomSort.merge_sort(
                ready_children,
                key=lambda h: (self.commits[h].timestamp, h)
            )
            for ch in ready_children:
                queue.append(ch)

        # 혹시 사이클이 있거나 누락된 노드가 있다면 보정
        if len(sorted_hashes) < len(self.commits):
            for h in self.commits:
                if h not in sorted_hashes:
                    sorted_hashes.append(h)

        return [self.commits[h] for h in sorted_hashes]

    def find_shortest_path(self, start_hash: str, end_hash: str) -> Optional[List[str]]:
        """
        두 커밋 사이의 최단 경로 탐색
        - 조건 1: 커밋-부모 연결을 '무방향 간선'으로 간주
        - 조건 2: 간선 수 최소인 최단 경로 (BFS 사용)
        - 조건 3: 최단 경로가 여러 개면 "hash1->hash2->..." 문자열 기준 사전순 최소 경로 선택
        """
        if start_hash not in self.commits or end_hash not in self.commits:
            return None

        if start_hash == end_hash:
            return [start_hash]

        # 무방향 인접 리스트 생성
        adj: Dict[str, List[str]] = {h: [] for h in self.commits}
        for c_hash, commit in self.commits.items():
            for p_hash in commit.parents:
                if p_hash in self.commits:
                    if p_hash not in adj[c_hash]:
                        adj[c_hash].append(p_hash)
                    if c_hash not in adj[p_hash]:
                        adj[p_hash].append(c_hash)

        # BFS로 최단 거리 계산 및 경로 수집
        queue = deque([(start_hash, [start_hash])])
        dist: Dict[str, int] = {start_hash: 0}
        shortest_paths: List[List[str]] = []
        min_depth: Optional[int] = None

        while queue:
            curr, path = queue.popleft()
            curr_depth = len(path) - 1

            if min_depth is not None and curr_depth > min_depth:
                break

            if curr == end_hash:
                min_depth = curr_depth
                shortest_paths.append(path)
                continue

            for neighbor in adj.get(curr, []):
                next_depth = curr_depth + 1
                if neighbor not in dist:
                    dist[neighbor] = next_depth
                    queue.append((neighbor, path + [neighbor]))
                elif dist[neighbor] == next_depth:
                    queue.append((neighbor, path + [neighbor]))

        if not shortest_paths:
            return None

        # 동률 경로 중 "hash1->hash2->..." 문자열 기준 사전순 최소 경로 선택
        # CustomSort.merge_sort 사용
        sorted_paths = CustomSort.merge_sort(
            shortest_paths,
            key=lambda p: "->".join(p)
        )
        return sorted_paths[0]

    def get_ancestors(self, commit_hash: str) -> List[Commit]:
        """
        특정 커밋의 모든 조상 커밋 탐색
        - 방향성 간선(자식 -> 부모)을 따라 재귀/BFS 탐색
        - 방문 집합(visited)을 두어 머지 커밋 등으로 인한 중복 방문 방지
        """
        if commit_hash not in self.commits:
            return []

        visited: Set[str] = set()
        queue = deque()

        # 시작 커밋의 직속 부모들을 큐에 등록
        start_commit = self.commits[commit_hash]
        for p in start_commit.parents:
            if p in self.commits:
                queue.append(p)
                visited.add(p)

        ancestors_list: List[Commit] = []

        while queue:
            curr_hash = queue.popleft()
            curr_commit = self.commits[curr_hash]
            ancestors_list.append(curr_commit)

            for parent_hash in curr_commit.parents:
                if parent_hash in self.commits and parent_hash not in visited:
                    visited.add(parent_hash)
                    queue.append(parent_hash)

        # 조상들을 부모 우선 순서(위상 정렬 순) 또는 시간 순으로 정렬
        return CustomSort.merge_sort(
            ancestors_list,
            key=lambda c: (c.timestamp, c.hash)
        )


# ============================================================================
# 5. Diff 알고리즘 (보너스 과제: LCS 기반 줄 단위 텍스트 비교)
# ============================================================================

class SimpleDiff:
    """
    LCS (Longest Common Subsequence, 최장 공통 부분 수열) 기반 Diff 알고리즘
    동적 계획법(DP)을 사용하여 추가(+), 삭제(-), 공통( ) 줄을 계산합니다.
    """
    @staticmethod
    def compare_lines(lines1: List[str], lines2: List[str]) -> List[str]:
        n = len(lines1)
        m = len(lines2)

        # DP 테이블 생성
        dp = [[0] * (m + 1) for _ in range(n + 1)]
        for i in range(1, n + 1):
            for j in range(1, m + 1):
                if lines1[i - 1] == lines2[j - 1]:
                    dp[i][j] = dp[i - 1][j - 1] + 1
                else:
                    dp[i][j] = dp[i - 1][j] if dp[i - 1][j] >= dp[i][j - 1] else dp[i][j - 1]

        # 역추적(Backtracking)으로 diff 결과 생성
        diff_result: List[str] = []
        i, j = n, m

        while i > 0 or j > 0:
            if i > 0 and j > 0 and lines1[i - 1] == lines2[j - 1]:
                diff_result.append(f"  {lines1[i - 1]}")
                i -= 1
                j -= 1
            elif j > 0 and (i == 0 or dp[i][j - 1] >= dp[i - 1][j]):
                diff_result.append(f"+ {lines2[j - 1]}")
                j -= 1
            elif i > 0 and (j == 0 or dp[i][j - 1] < dp[i - 1][j]):
                diff_result.append(f"- {lines1[i - 1]}")
                i -= 1

        # 역추적 결과이므로 뒤집기
        diff_result.reverse()
        return diff_result


# ============================================================================
# 6. Mini Git 저장소 코어 엔진
# ============================================================================

class MiniGit:
    """
    Mini Git 시스템 코어
    저장소 상태, 브랜치 참조, HEAD 포인터, 역색인 및 커밋 생성 관리
    """
    def __init__(self):
        self.is_initialized: bool = False
        self.current_user: str = ""
        self.head_branch: str = "main"
        # branch_name -> commit_hash
        self.branches: Dict[str, Optional[str]] = {}
        self.graph: CommitGraph = CommitGraph()
        self.index: InvertedIndex = InvertedIndex()
        self.counter: int = 0  # 커밋 해시 유일성 보장 카운터

    def init(self, user_name: str) -> Tuple[bool, str]:
        """저장소 초기화, main 브랜치 생성 및 사용자 설정"""
        self.is_initialized = True
        self.current_user = user_name
        self.head_branch = "main"
        self.branches = {"main": None}
        self.graph = CommitGraph()
        self.index = InvertedIndex()
        self.counter = 0

        msg = (
            "Initialized repository.\n"
            f"Current branch: {self.head_branch}\n"
            f"Current user: {self.current_user}"
        )
        return True, msg

    def _generate_hash(self, message: str, author: str, timestamp: str, parents: List[str]) -> str:
        """세션 내 유일한 6자리 16진수 커밋 해시 생성"""
        while True:
            self.counter += 1
            raw = f"{self.counter}:{author}:{timestamp}:{message}:{','.join(parents)}"
            h = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:6]
            if h not in self.graph.commits:
                return h

    def branch(self, branch_name: str) -> Tuple[bool, str]:
        """현재 HEAD가 가리키는 커밋을 참조하는 새 브랜치 생성"""
        if not self.is_initialized:
            return False, "Repository not initialized. Please run INIT <user_name> first."

        if branch_name in self.branches:
            return False, f"Branch already exists: {branch_name}"

        current_head_commit = self.branches.get(self.head_branch)
        if current_head_commit is None:
            return False, "Cannot create branch: No commits yet."

        self.branches[branch_name] = current_head_commit
        return True, f"Created branch: {branch_name}"

    def switch(self, branch_name: str) -> Tuple[bool, str]:
        """HEAD를 지정한 브랜치로 전환"""
        if not self.is_initialized:
            return False, "Repository not initialized. Please run INIT <user_name> first."

        if branch_name not in self.branches:
            return False, f"Unknown branch: {branch_name}"

        self.head_branch = branch_name
        return True, f"Switched to branch: {branch_name}"

    def commit(self, message: str) -> Tuple[bool, str]:
        """현재 HEAD를 부모로 하는 새 커밋 생성 및 역색인 업데이트"""
        if not self.is_initialized:
            return False, "Repository not initialized. Please run INIT <user_name> first."

        if not message.strip():
            return False, "Invalid args: Commit message cannot be empty."

        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        parent_commit = self.branches.get(self.head_branch)
        parents = [parent_commit] if parent_commit else []

        commit_hash = self._generate_hash(message, self.current_user, now_str, parents)
        new_commit = Commit(
            commit_hash=commit_hash,
            message=message,
            author=self.current_user,
            timestamp=now_str,
            parents=parents,
            branch=self.head_branch
        )

        # 그래프 및 역색인에 등록
        self.graph.add_commit(new_commit)
        self.index.index_commit(new_commit)

        # 현재 브랜치 헤드 이동
        self.branches[self.head_branch] = commit_hash

        return True, f"[{self.head_branch} {commit_hash}] {message}"

    def merge(self, branch_name: str) -> Tuple[bool, str]:
        """
        보너스 과제: 브랜치 병합 (Merge)
        현재 브랜치의 HEAD와 대상 브랜치의 HEAD를 2개의 부모로 갖는 머지 커밋 생성
        """
        if not self.is_initialized:
            return False, "Repository not initialized. Please run INIT <user_name> first."

        if branch_name not in self.branches:
            return False, f"Unknown branch: {branch_name}"

        target_head = self.branches[branch_name]
        current_head = self.branches.get(self.head_branch)

        if target_head is None:
            return False, f"Cannot merge: Target branch '{branch_name}' has no commits."

        if current_head == target_head:
            return True, "Already up to date."

        parents = [current_head, target_head] if current_head else [target_head]
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"Merge branch '{branch_name}' into {self.head_branch}"

        commit_hash = self._generate_hash(message, self.current_user, now_str, parents)
        merge_commit = Commit(
            commit_hash=commit_hash,
            message=message,
            author=self.current_user,
            timestamp=now_str,
            parents=parents,
            branch=self.head_branch
        )

        self.graph.add_commit(merge_commit)
        self.index.index_commit(merge_commit)
        self.branches[self.head_branch] = commit_hash

        return True, f"[{self.head_branch} {commit_hash}] {message}\nMerge parents: {', '.join(parents)}"

    def log(self, sort_by: Optional[str] = None) -> Tuple[bool, str]:
        """
        커밋 로그 출력
        - sort_by 미지정: 부모 커밋이 항상 자식 커밋보다 먼저 출력되는 위상 정렬 순서
        - sort_by="date": 타임스탬프 기준 정렬 (MergeSort 활용)
        - sort_by="author": 작성자 기준 정렬 (MergeSort 활용)
        """
        if not self.is_initialized:
            return False, "Repository not initialized. Please run INIT <user_name> first."

        if not self.graph.commits:
            return True, "No commits found."

        commits_to_show: List[Commit] = []

        if sort_by is None:
            # 기본 모드: 부모가 자식보다 먼저 출력되는 위상 정렬
            commits_to_show = self.graph.topological_sort_parents_first()
        elif sort_by == "date":
            all_list = list(self.graph.commits.values())
            commits_to_show = CustomSort.merge_sort(all_list, key=lambda c: (c.timestamp, c.hash))
        elif sort_by == "author":
            all_list = list(self.graph.commits.values())
            commits_to_show = CustomSort.merge_sort(all_list, key=lambda c: (c.author.lower(), c.timestamp, c.hash))
        else:
            return False, f"Invalid args: Invalid sort-by option '{sort_by}'"

        lines: List[str] = []
        for c in commits_to_show:
            branch_info = f" [{c.branch}]" if c.branch else ""
            lines.append(f"commit {c.hash} ({c.author}, {c.timestamp}){branch_info}")
            lines.append(c.message)

        return True, "\n".join(lines)

    def path(self, commit1: str, commit2: str) -> Tuple[bool, str]:
        """두 커밋 사이의 최단 경로 출력"""
        if not self.is_initialized:
            return False, "Repository not initialized. Please run INIT <user_name> first."

        if commit1 not in self.graph.commits:
            return False, f"Unknown commit: {commit1}"
        if commit2 not in self.graph.commits:
            return False, f"Unknown commit: {commit2}"

        shortest = self.graph.find_shortest_path(commit1, commit2)
        if shortest is None:
            return True, "No path"
        return True, f"Path: {' -> '.join(shortest)}"

    def ancestors(self, commit_hash: str) -> Tuple[bool, str]:
        """특정 커밋의 모든 조상 커밋 출력"""
        if not self.is_initialized:
            return False, "Repository not initialized. Please run INIT <user_name> first."

        if commit_hash not in self.graph.commits:
            return False, f"Unknown commit: {commit_hash}"

        anc = self.graph.get_ancestors(commit_hash)
        if not anc:
            return True, f"Commit {commit_hash} has no ancestors (Root commit)."

        lines = [f"Ancestors of {commit_hash} ({len(anc)} commits):"]
        for c in anc:
            lines.append(f"- {c.hash} ({c.author}, {c.timestamp}): {c.message}")
        return True, "\n".join(lines)

    def search_keyword(self, keyword: str) -> Tuple[bool, str]:
        """역색인을 사용한 키워드 검색"""
        if not self.is_initialized:
            return False, "Repository not initialized. Please run INIT <user_name> first."

        hashes = self.index.search_keyword(keyword)
        if not hashes:
            return True, f"Found 0 commits for keyword '{keyword}'."

        lines = [f"Found {len(hashes)} commit{'s' if len(hashes) > 1 else ''}:"]
        for h in hashes:
            c = self.graph.get_commit(h)
            if c:
                lines.append(f"- {c.hash}: {c.message}")
        return True, "\n".join(lines)

    def search_author(self, author: str) -> Tuple[bool, str]:
        """역색인을 사용한 작성자 검색"""
        if not self.is_initialized:
            return False, "Repository not initialized. Please run INIT <user_name> first."

        hashes = self.index.search_author(author)
        if not hashes:
            return True, f"Found 0 commits by author '{author}'."

        lines = [f"Found {len(hashes)} commit{'s' if len(hashes) > 1 else ''}:"]
        for h in hashes:
            c = self.graph.get_commit(h)
            if c:
                lines.append(f"- {c.hash}: {c.message} (by {c.author})")
        return True, "\n".join(lines)


# ============================================================================
# 7. 정렬 알고리즘 성능 벤치마크 (보너스 과제)
# ============================================================================

def run_sorting_benchmark() -> str:
    """
    서로 다른 정렬 알고리즘(Merge Sort, Quick Sort, Insertion Sort)의
    입력 크기(N)에 따른 실행 시간 및 안정성, 시간복잡도 비교 벤치마크
    """
    sizes = [200, 1000, 3000]
    results: List[str] = []
    results.append("================================================================================")
    results.append("           정렬 알고리즘 성능 및 특성 비교 벤치마크 (Sort Benchmark)           ")
    results.append("================================================================================")
    results.append(f"{'Algorithm':<16} | {'N':<6} | {'Time (sec)':<12} | {'Time Complexity':<15} | {'Stability'}")
    results.append("-" * 80)

    for n in sizes:
        # 동일한 무작위 난수 데이터 생성
        rng = random.Random(42)
        base_data = [rng.randint(1, 100000) for _ in range(n)]

        # 1) Merge Sort
        t0 = time.perf_counter()
        _ = CustomSort.merge_sort(base_data)
        t_merge = time.perf_counter() - t0
        results.append(f"{'Merge Sort':<16} | {n:<6} | {t_merge:<12.6f} | O(N log N)      | Stable")

        # 2) Quick Sort
        t0 = time.perf_counter()
        _ = CustomSort.quick_sort(base_data)
        t_quick = time.perf_counter() - t0
        results.append(f"{'Quick Sort':<16} | {n:<6} | {t_quick:<12.6f} | O(N log N) avg  | Unstable")

        # 3) Insertion Sort (N이 3000 이하일 때만 수행하여 과도한 지연 방지)
        if n <= 1000:
            t0 = time.perf_counter()
            _ = CustomSort.insertion_sort(base_data)
            t_insert = time.perf_counter() - t0
            results.append(f"{'Insertion Sort':<16} | {n:<6} | {t_insert:<12.6f} | O(N^2)           | Stable")
        else:
            results.append(f"{'Insertion Sort':<16} | {n:<6} | {'(Skipped >1k)':<12} | O(N^2)           | Stable")

        results.append("-" * 80)

    results.append("\n[요약 및 분석]")
    results.append("1. Merge Sort는 최악의 경우에도 O(N log N)을 보장하며, 순서가 유지되는 안정 정렬(Stable)입니다.")
    results.append("2. Quick Sort는 Median-of-Three 피벗을 채택하여 실측 속도가 매우 빠르나 불안정 정렬(Unstable)입니다.")
    results.append("3. Insertion Sort는 O(N^2)으로 데이터 크기 증가 시 급격하게 시간이 증가합니다.")
    return "\n".join(results)


# ============================================================================
# 8. CLI 및 REPL (명령어 파서)
# ============================================================================

class MiniGitCLI:
    """
    Mini Git CLI 대화형 인터페이스(REPL)
    - 대소문자 무구분 명령어 파싱
    - 따옴표 포함 인자 처리 (shlex 활용)
    - 표준화된 오류 메시지 출력
    """
    def __init__(self):
        self.git = MiniGit()

    def print_help(self) -> None:
        help_text = """
=== Mini Git 명령어 안내 ===
[저장소 및 브랜치 관리]
  INIT <user_name>               : 저장소 초기화 및 기본 사용자 설정
  BRANCH <branch_name>           : 현재 HEAD를 가리키는 새 브랜치 생성
  SWITCH <branch_name>           : HEAD를 지정한 브랜치로 전환
  COMMIT <message>               : 새 커밋 생성 및 역색인 업데이트

[커밋 로그 및 그래프 탐색]
  LOG                            : 부모가 자식보다 먼저 출력되는 위상 정렬 순서로 출력
  LOG --sort-by=date             : 날짜 순으로 정렬하여 로그 출력
  LOG --sort-by=author           : 작성자 이름 순으로 정렬하여 로그 출력
  PATH <commit1> <commit2>       : 두 커밋 간 최단 경로 출력 (없으면 No path)
  ANCESTORS <commit_hash>        : 특정 커밋의 모든 조상 커밋 출력

[검색]
  SEARCH <keyword>               : 커밋 메시지 키워드 역색인 검색
  SEARCH --author=<name>         : 작성자별 커밋 역색인 검색

[보너스 기능]
  DIFF <file1> <file2>           : 두 파일 간의 줄 단위 변경 사항 비교 (LCS 기반)
  MERGE <branch_name>            : 브랜치 병합 (2개의 부모를 갖는 머지 커밋 생성)
  BENCHMARK                      : 직접 구현한 정렬 알고리즘 성능 비교

[기타]
  HELP                           : 도움말 출력
  EXIT / QUIT                    : 프로그램 종료
"""
        print(help_text.strip())

    def execute_line(self, line: str) -> bool:
        """한 줄의 명령어를 파싱하고 실행. False 반환 시 REPL 종료."""
        line = line.strip()
        if not line:
            return True

        # shlex로 공백 및 따옴표 분리
        try:
            tokens = shlex.split(line)
        except ValueError as e:
            print(f"Invalid args: Quotation error ({e})")
            return True

        if not tokens:
            return True

        cmd = tokens[0].upper()
        args = tokens[1:]

        # 종료 명령
        if cmd in ("EXIT", "QUIT"):
            print("Exiting Mini Git.")
            return False

        if cmd == "HELP":
            self.print_help()
            return True

        # INIT <user_name>
        if cmd == "INIT":
            if len(args) != 1:
                print("Invalid args: INIT <user_name>")
                return True
            _, msg = self.git.init(args[0])
            print(msg)
            return True

        # BRANCH <branch_name>
        if cmd == "BRANCH":
            if len(args) != 1:
                print("Invalid args: BRANCH <branch_name>")
                return True
            _, msg = self.git.branch(args[0])
            print(msg)
            return True

        # SWITCH <branch_name>
        if cmd == "SWITCH":
            if len(args) != 1:
                print("Invalid args: SWITCH <branch_name>")
                return True
            _, msg = self.git.switch(args[0])
            print(msg)
            return True

        # COMMIT <message>
        if cmd == "COMMIT":
            if len(args) != 1:
                print("Invalid args: COMMIT <message>")
                return True
            _, msg = self.git.commit(args[0])
            print(msg)
            return True

        # LOG [--sort-by=date|author]
        if cmd == "LOG":
            sort_by = None
            if len(args) == 1:
                opt = args[0]
                if opt.startswith("--sort-by="):
                    val = opt.split("=", 1)[1].lower()
                    if val in ("date", "author"):
                        sort_by = val
                    else:
                        print("Invalid args: --sort-by must be 'date' or 'author'")
                        return True
                else:
                    print(f"Invalid args: Unknown option '{opt}'")
                    return True
            elif len(args) > 1:
                print("Invalid args: Too many arguments for LOG")
                return True

            _, msg = self.git.log(sort_by=sort_by)
            print(msg)
            return True

        # PATH <commit1> <commit2>
        if cmd == "PATH":
            if len(args) != 2:
                print("Invalid args: PATH <commit1> <commit2>")
                return True
            _, msg = self.git.path(args[0], args[1])
            print(msg)
            return True

        # ANCESTORS <commit_hash>
        if cmd == "ANCESTORS":
            if len(args) != 1:
                print("Invalid args: ANCESTORS <commit_hash>")
                return True
            _, msg = self.git.ancestors(args[0])
            print(msg)
            return True

        # SEARCH <keyword> 또는 SEARCH --author=<name>
        if cmd == "SEARCH":
            if len(args) != 1:
                print("Invalid args: SEARCH <keyword> or SEARCH --author=<name>")
                return True

            arg = args[0]
            if arg.startswith("--author="):
                author_name = arg.split("=", 1)[1]
                if not author_name:
                    print("Invalid args: Author name required in --author=<name>")
                    return True
                _, msg = self.git.search_author(author_name)
                print(msg)
            else:
                _, msg = self.git.search_keyword(arg)
                print(msg)
            return True

        # MERGE <branch_name> (보너스)
        if cmd == "MERGE":
            if len(args) != 1:
                print("Invalid args: MERGE <branch_name>")
                return True
            _, msg = self.git.merge(args[0])
            print(msg)
            return True

        # DIFF <file1> <file2> (보너스)
        if cmd == "DIFF":
            if len(args) != 2:
                print("Invalid args: DIFF <file1> <file2>")
                return True
            f1, f2 = args[0], args[1]
            if not os.path.exists(f1):
                print(f"File not found: {f1}")
                return True
            if not os.path.exists(f2):
                print(f"File not found: {f2}")
                return True
            try:
                with open(f1, "r", encoding="utf-8") as fp1:
                    lines1 = [line.rstrip("\r\n") for line in fp1]
                with open(f2, "r", encoding="utf-8") as fp2:
                    lines2 = [line.rstrip("\r\n") for line in fp2]
                diff_res = SimpleDiff.compare_lines(lines1, lines2)
                print(f"--- {f1}\n+++ {f2}")
                print("\n".join(diff_res))
            except Exception as e:
                print(f"Error reading files: {e}")
            return True

        # BENCHMARK (보너스)
        if cmd in ("BENCHMARK", "COMPARE-SORT"):
            bench_res = run_sorting_benchmark()
            print(bench_res)
            return True

        print(f"Unknown command: {tokens[0]}. Type 'HELP' for instructions.")
        return True

    def run(self) -> None:
        """대화형 REPL 루프"""
        while True:
            try:
                line = input("mini-git> ")
                if not self.execute_line(line):
                    break
            except (EOFError, KeyboardInterrupt):
                print("\nExiting Mini Git.")
                break


# ============================================================================
# 9. 자동 검증 테스트 및 데모 시나리오
# ============================================================================

def run_self_tests() -> None:
    """모든 핵심 요구사항 및 알고리즘 단위 검증"""
    print("[1/6] 정렬 알고리즘 검증 (MergeSort, QuickSort, InsertionSort)...")
    sample = [45, 12, 85, 32, 89, 39, 69, 44, 42, 1, 45, 8]
    expected = [1, 8, 12, 32, 39, 42, 44, 45, 45, 69, 85, 89]

    assert CustomSort.merge_sort(sample) == expected, "MergeSort 검증 실패"
    assert CustomSort.quick_sort(sample) == expected, "QuickSort 검증 실패"
    assert CustomSort.insertion_sort(sample) == expected, "InsertionSort 검증 실패"

    # 안정 정렬 검증 (MergeSort가 동일 키의 기존 순서를 보존하는지)
    pairs = [("a", 2), ("b", 1), ("c", 2), ("d", 1)]
    sorted_pairs = CustomSort.merge_sort(pairs, key=lambda x: x[1])
    assert sorted_pairs == [("b", 1), ("d", 1), ("a", 2), ("c", 2)], "MergeSort 안정 정렬 특성 검증 실패"

    print("[2/6] 저장소 기본 라이프사이클 및 브랜치 검증...")
    git = MiniGit()
    git.init("Alice")
    ok, _ = git.commit("Initial commit")
    c1 = git.branches["main"]
    assert ok and c1 is not None

    git.branch("feature")
    git.switch("feature")
    ok, _ = git.commit("Add login feature")
    c2 = git.branches["feature"]
    assert ok and c2 is not None

    git.switch("main")
    ok, _ = git.commit("Add payment feature")
    c3 = git.branches["main"]
    assert ok and c3 is not None

    print("[3/6] 위상 정렬 (LOG 부모 우선 출력) 검증...")
    # c1은 c2와 c3의 부모이므로 c1이 무조건 c2, c3보다 앞에 위치해야 함
    topo = git.graph.topological_sort_parents_first()
    hashes = [c.hash for c in topo]
    assert hashes.index(c1) < hashes.index(c2), "위상 정렬 실패: c1이 c2보다 뒤에 있음"
    assert hashes.index(c1) < hashes.index(c3), "위상 정렬 실패: c1이 c3보다 뒤에 있음"

    print("[4/6] 최단 경로(BFS) 및 조상 탐색 검증...")
    path = git.graph.find_shortest_path(c2, c3)
    # feature (c2) -> main root (c1) -> main (c3)
    assert path == [c2, c1, c3], f"최단 경로 오류: {path}"

    anc = git.graph.get_ancestors(c2)
    assert [c.hash for c in anc] == [c1], "조상 탐색 오류"

    print("[5/6] 역색인 검색 (키워드 및 작성자) 검증...")
    found_login = git.index.search_keyword("login")
    assert c2 in found_login, "키워드 역색인 검색 실패"

    found_author = git.index.search_author("Alice")
    assert len(found_author) == 3, "작성자 역색인 검색 실패"

    print("[6/6] 브랜치 병합(MERGE) 및 LCS Diff 검증...")
    ok, _ = git.merge("feature")
    assert ok
    merge_commit = git.graph.get_commit(git.branches["main"])
    assert merge_commit is not None and len(merge_commit.parents) == 2

    # Diff 검증
    l1 = ["apple", "banana", "cherry"]
    l2 = ["apple", "blueberry", "cherry"]
    d = SimpleDiff.compare_lines(l1, l2)
    assert "  apple" in d and "- banana" in d and "+ blueberry" in d and "  cherry" in d

    print(">> 모든 자체 검증 단위 테스트를 성공적으로 통과하였습니다! <<\n")


def run_demo() -> None:
    """과제 설명에 제시된 표준 예시 시나리오 실행"""
    print("=== 과제 예시 시나리오 데모 시작 ===")
    cli = MiniGitCLI()
    commands = [
        'init "Alice"',
        'commit "Initial commit"',
        'branch feature',
        'switch feature',
        'commit "Add login feature"',
        'switch main',
        'commit "Add payment feature"',
        'log',
        'search "login"',
        'log --sort-by=author'
    ]
    for cmd in commands:
        print(f"\nmini-git> {cmd}")
        cli.execute_line(cmd)

    # 경로 테스트
    c_hashes = list(cli.git.graph.commits.keys())
    if len(c_hashes) >= 3:
        p_cmd = f"path {c_hashes[0]} {c_hashes[2]}"
        print(f"\nmini-git> {p_cmd}")
        cli.execute_line(p_cmd)

    print("\n=== 데모 실행 완료 ===")


# ============================================================================
# 엔트리 포인트
# ============================================================================

def main():
    if len(sys.argv) > 1:
        arg = sys.argv[1].lower()
        if arg in ("--test", "-t", "test"):
            run_self_tests()
            return
        elif arg in ("--demo", "-d", "demo"):
            run_demo()
            return
        elif arg in ("--benchmark", "-b", "benchmark"):
            print(run_sorting_benchmark())
            return
        elif arg in ("--help", "-h", "help"):
            MiniGitCLI().print_help()
            return

    # 기본 대화형 모드 진입
    cli = MiniGitCLI()
    print("Mini Git에 오신 것을 환영합니다! (도움말은 'HELP', 종료는 'EXIT')")
    cli.run()


if __name__ == "__main__":
    main()
