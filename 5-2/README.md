# Mini Git - CLI 기반 분산 버전 관리 시스템

> 파일이 언제 어떻게 바뀌었는지 기록하고 관리하는 Git의 내부 핵심 자료구조(DAG, 해시, 역색인)와 그래프/정렬 알고리즘을 직접 구현한 CLI Mini Git 프로그램입니다.

---

## 1. 프로젝트 개요 (Introduction)

Git의 커밋 이력은 단순한 선형 리스트가 아니라, **방향성 비순환 그래프(DAG, Directed Acyclic Graph)**와 **해시(Hash)**로 구성되어 있습니다.  
본 프로젝트는 외부 라이브러리 및 파이썬 내장 정렬 API(`sorted()`, `list.sort()`)를 일절 배제하고, 순수 기본 자료구조(`dict`, `list`, `set`)와 직접 구현한 알고리즘만을 사용하여 다음을 완성합니다.

- **커밋 그래프 및 브랜치 관리**: 세션 내 유일한 SHA-1 커밋 해시 생성, 브랜치 분기 및 HEAD 이동, 2개 부모 커밋을 지원하는 병합(Merge)
- **위상 정렬 기반 로그 출력**: 부모 커밋이 항상 자식 커밋보다 먼저 출력되는 위상 정렬(Topological Sort - Kahn's Algorithm)
- **최단 경로 및 조상 탐색**: 무방향 간선 BFS 최단 경로 탐색(동률 시 사전순 최소 경로 선택) 및 조상 도달성 탐색
- **직접 구현한 정렬 알고리즘**: 표준 API 없는 분할 정복 병합 정렬(Merge Sort) 및 퀵 정렬(Quick Sort) 구현
- **역색인(Inverted Index)**: 전체 커밋 순회 $O(N)$ 없이 단어 및 작성자별 커밋을 $O(1)$에 검색하는 색인 엔진
- **LCS 기반 파일 비교(Diff)**: 최장 공통 부분 수열 동적 계획법(DP)을 활용한 줄 단위 텍스트 diff

---

## 2. 파일 구성 및 실행 방법

### 파일 구조
```
Desktop/5-2/
├── main.py          # Mini Git 전체 엔트리 포인트 (REPL, 알고리즘, 테스트 내장)
└── README.md        # 프로젝트 설명 및 기술적 분석 보고서
```

### 환경 요구사항
- Python 3.10 이상 (Python 3.9 ~ 3.12+ 완벽 호환)
- 외부 의존성 없음 (No external libraries required)

### 실행 커맨드

#### 1) 대화형 REPL 실행 (기본)
```bash
python main.py
# 또는
python3 main.py
```

#### 2) 자체 검증 단위 테스트 실행
모든 알고리즘(정렬 안정성, 위상 정렬, BFS 최단 경로, 조상 탐색, 역색인, 머지, diff)을 자동 검증합니다.
```bash
python main.py --test
```

#### 3) 과제 표준 시나리오 데모 실행
과제 명세서의 실행 예시 흐름을 자동으로 시뮬레이션합니다.
```bash
python main.py --demo
```

#### 4) 정렬 알고리즘 성능 벤치마크 실행
입력 크기($N=200, 1000, 3000$)에 따른 Merge Sort, Quick Sort, Insertion Sort의 실측 실행 시간 및 시간복잡도 표를 출력합니다.
```bash
python main.py --benchmark
```

---

## 3. 명령어 명세 및 사용 예시

명령어는 **대소문자를 구분하지 않으며**, 공백이 포함된 인자는 따옴표(`"..."`)로 감쌉니다.

| 명령어 | 형식 | 설명 및 예시 |
|---|---|---|
| `INIT` | `INIT <user_name>` | 저장소를 초기화하고 기본 `main` 브랜치 및 사용자를 설정합니다. |
| `BRANCH` | `BRANCH <branch_name>` | 현재 HEAD가 가리키는 커밋을 참조하는 새 브랜치를 생성합니다. |
| `SWITCH` | `SWITCH <branch_name>` | 지정한 브랜치로 HEAD를 전환합니다. |
| `COMMIT` | `COMMIT <message>` | 현재 HEAD를 부모로 하는 새 커밋을 생성하고 역색인을 갱신합니다. |
| `LOG` | `LOG` | 부모 커밋이 항상 자식 커밋보다 먼저 출력되는 위상 정렬 순서로 로그를 출력합니다. |
| `LOG` (정렬) | `LOG --sort-by=date`<br>`LOG --sort-by=author` | 타임스탬프(`date`) 또는 작성자(`author`) 기준으로 커밋 목록을 정렬하여 출력합니다. |
| `PATH` | `PATH <commit1> <commit2>` | 두 커밋 사이의 최단 경로(무방향 간선 수 최소)를 출력합니다. 동률 시 사전순 최소 경로 선택. |
| `ANCESTORS` | `ANCESTORS <commit_hash>` | 해당 커밋에서 도달 가능한 모든 조상 커밋 목록을 출력합니다. |
| `SEARCH` | `SEARCH <keyword>` | 역색인을 기반으로 커밋 메시지에 해당 키워드가 포함된 커밋들을 빠르게 검색합니다. |
| `SEARCH` (작성자) | `SEARCH --author=<name>` | 역색인을 기반으로 특정 작성자가 작성한 커밋들을 빠르게 검색합니다. |
| `MERGE` (보너스) | `MERGE <branch_name>` | 대상 브랜치를 현재 브랜치로 병합하며 2개의 부모를 갖는 머지 커밋을 생성합니다. |
| `DIFF` (보너스) | `DIFF <file1> <file2>` | 두 텍스트 파일을 줄 단위로 비교하여 추가(`+`), 삭제(`-`), 공통(` `)을 출력합니다. |
| `BENCHMARK` (보너스) | `BENCHMARK` | 직접 구현한 정렬 알고리즘들의 성능 비교 표를 출력합니다. |
| `HELP` | `HELP` | 사용 가능한 전체 명령어 도움말을 확인합니다. |
| `EXIT` / `QUIT` | `EXIT` | 프로그램을 종료합니다. |

### 표준 실행 시나리오 예시

```
mini-git> init "Alice"
Initialized repository.
Current branch: main
Current user: Alice

mini-git> commit "Initial commit"
[main a1b2c3] Initial commit

mini-git> branch feature
Created branch: feature

mini-git> switch feature
Switched to branch: feature

mini-git> commit "Add login feature"
[feature d4e5f6] Add login feature

mini-git> switch main
Switched to branch: main

mini-git> commit "Add payment feature"
[main g7h8i9] Add payment feature

mini-git> log
commit a1b2c3 (Alice, 2024-01-15 09:00:00) [main]
Initial commit
commit d4e5f6 (Alice, 2024-01-15 09:15:00) [feature]
Add login feature
commit g7h8i9 (Alice, 2024-01-15 09:30:00) [main]
Add payment feature

mini-git> path a1b2c3 g7h8i9
Path: a1b2c3 -> g7h8i9

mini-git> search "login"
Found 1 commit:
- d4e5f6: Add login feature

mini-git> log --sort-by=author
commit a1b2c3 (Alice, 2024-01-15 09:00:00)
Initial commit
commit d4e5f6 (Alice, 2024-01-15 09:15:00)
Add login feature
commit g7h8i9 (Alice, 2024-01-15 09:30:00)
Add payment feature
```

---

## 4. 핵심 기술적 설명 및 과제 목표 5가지 문답

### 1) Git의 커밋 구조가 왜 DAG(방향성 비순환 그래프)인가?
- **방향성(Directed)**: 커밋은 생성될 때 자신의 직전 상태인 **부모 커밋(Parent)**의 해시를 명시적으로 가리킵니다($Child \to Parent$).
- **비순환(Acyclic)**: 시간은 앞으로만 흐르며, 새로운 커밋은 반드시 이미 존재하는 부모 커밋들의 해시를 기반으로 생성됩니다. 미래의 커밋이 과거의 커밋의 부모가 되거나 자기 자신을 참조하는 순환 루프(Cycle)는 구조적으로 발생할 수 없습니다.
- **다중 부모(Merge)** 및 **다중 자식(Branch)**: 한 커밋에서 여러 브랜치가 뻗어나갈 수 있고(1개 부모, 다중 자식), 브랜치 병합 시 2개 이상의 부모를 가질 수 있으므로(다중 부모, 1개 자식) 단순한 트리(Tree)가 아닌 일반적인 **DAG** 형태를 이룹니다.

### 2) “부모가 먼저 출력되는 로그”를 만들기 위해 왜 위상 정렬이 필요한가?
- 커밋 이력에서 부모 커밋은 자식 커밋의 논리적 전제 조건(선수 작업)입니다.
- 단순 생성 시간(timestamp)으로 정렬할 경우, 분산 환경이나 시스템 시계 오차로 인해 부모의 타임스탬프가 자식보다 늦어지는 역전 현상이 발생할 수 있습니다.
- 따라서 **"간선 $Parent \to Child$가 존재할 때 항상 $Parent$가 $Child$보다 먼저 나열된다"**는 위상 정렬(Topological Sort)을 적용해야 합니다.
- **구현 방식**: 본 프로그램은 **Kahn's Algorithm**을 채택하였습니다.
  1. 각 커밋의 부모 수(진입 차수, in-degree)를 계산합니다.
  2. 부모가 없는 루트 커밋(in-degree = 0)들을 큐에 삽입합니다.
  3. 큐에서 커밋 $u$를 꺼내 결과 리스트에 추가하고, $u$의 자식 노드들의 진입 차수를 1씩 감소시킵니다.
  4. 진입 차수가 0이 된 자식 노드(모든 부모가 이미 출력된 노드)를 큐에 추가합니다.
  5. 이를 통해 모든 부모 커밋이 자식보다 앞서 출력됨이 수학적으로 보장됩니다.

### 3) 두 커밋 사이 최단 경로 및 모든 조상 탐색 알고리즘
- **두 커밋 사이 최단 경로 (`PATH <commit1> <commit2>`)**:
  - 커밋 간의 부모-자식 연결을 가중치가 1인 **무방향 간선**으로 모델링합니다.
  - 가중치가 동일한 그래프에서 최단 경로(최소 간선 수)를 찾는 가장 효율적인 알고리즘은 **너비 우선 탐색(BFS)**입니다.
  - 시작 정점부터 큐(`deque`)를 통해 거리별로 탐색하며, 목적 정점에 도달하는 모든 최단 경로들을 수집합니다.
  - 동률 최단 경로가 여러 개 존재할 경우, 경로 문자열(`hash1->hash2->...`) 기준 사전순 최소 경로를 선택하도록 타이브레이커를 구현했습니다.
- **모든 조상 탐색 (`ANCESTORS <commit_hash>`)**:
  - 시작 커밋부터 방향성 간선($Child \to Parent$)만을 따라 역방향으로 탐색합니다.
  - 브랜치 머지가 포함된 DAG에서는 여러 경로를 통해 동일한 공통 조상에 도달할 수 있으므로, `visited` 집합(Set)을 유지하여 중복 연산과 무한 루프를 방지합니다.

### 4) 정렬 알고리즘 직접 구현 및 시간복잡도 / 안정성 비교
본 프로젝트는 제약 사항에 따라 파이썬 내장 `sorted()`, `list.sort()`를 전혀 사용하지 않고 분할 정복 기반 알고리즘을 직접 작성했습니다.

| 알고리즘 | 평균 시간복잡도 | 최악 시간복잡도 | 공간복잡도 | 안정 정렬(Stable) 여부 | 특징 |
|---|---|---|---|---|---|
| **병합 정렬 (Merge Sort)** | $O(N \log N)$ | $O(N \log N)$ | $O(N)$ | **안정 (Stable)** | 데이터 상태에 무관하게 일정한 성능을 보장하며, 동일 키의 원래 순서를 유지함 (`LOG` 기본 정렬로 채택) |
| **퀵 정렬 (Quick Sort)** | $O(N \log N)$ | $O(N^2)$ | $O(\log N)$ | **불안정 (Unstable)** | 캐시 효율이 뛰어나 실측 속도가 빠름. Median-of-Three 피벗을 적용하여 최악 케이스 확률을 최소화함 |
| **삽입 정렬 (Insertion Sort)**| $O(N^2)$ | $O(N^2)$ | $O(1)$ | **안정 (Stable)** | 작은 데이터셋에서 오버헤드가 적으나, $N$이 커질수록 급격히 느려짐 (비교군용) |

> **안정 정렬(Stable Sort)의 중요성**: 작성자 이름으로 정렬할 때, 동일한 작성자가 커밋한 여러 항목들은 원래의 커밋 생성 순서(시간 순)가 유지되어야 합니다. 병합 정렬은 동률 비교 시 왼쪽 원소를 우선 취하여 안정 정렬 특성을 완벽히 만족합니다.

### 5) 역색인(Inverted Index)의 동작 원리와 순회 검색 대비 시간복잡도 우위
- **순회 검색 (Full Scan)**:
  - 저장된 $N$개의 커밋 메시지 전체를 하나씩 순회하며 키워드 포함 여부를 검사합니다.
  - 시간복잡도: $O(N \times L)$ ($N$: 전체 커밋 수, $L$: 메시지 평균 길이). 커밋 수가 수만 개로 늘어나면 검색 지연이 선형적으로 증가합니다.
- **역색인 (Inverted Index)**:
  - 책 맨 뒤의 "찾아보기(색인)"처럼, 단어(Key) $\to$ [해당 단어가 등장하는 커밋 해시 리스트](Value) 구조의 해시 테이블(`dict`)을 미리 구축합니다.
  - 커밋이 생성되는 시점에 단어를 공백으로 분리하고 소문자로 정규화하여 $O(1)$에 인덱스에 추가합니다.
  - 검색 시에는 단어 해시 조회를 통해 **$O(1)$ 시간**에 일치하는 커밋 해시 목록을 즉시 획득합니다.
  - 일치하는 결과 개수가 $K$개라면 전체 검색 시간은 $O(K)$에 불과하므로, 전체 커밋 수 $N$에 전혀 영향을 받지 않고 초고속 검색이 가능합니다.

---

## 5. 보너스 과제 구현 상세

### 1) LCS 기반 줄 단위 비교 (`DIFF <file1> <file2>`)
- 동적 계획법(DP)을 기반으로 두 텍스트 파일 간의 최장 공통 부분 수열(LCS)을 계산합니다.
- DP 역추적을 통해 변경되지 않은 줄(`  `), 삭제된 줄(`- `), 추가된 줄(`+ `)을 Git 스타일의 Unified Diff 포맷으로 출력합니다.

### 2) 다중 부모 브랜치 병합 (`MERGE <branch_name>`)
- 현재 브랜치의 HEAD와 대상 브랜치의 HEAD를 동시에 부모(`parents = [current_head, target_head]`)로 갖는 머지 커밋을 생성합니다.
- 부모가 2개인 커밋이 DAG에 정상적으로 연결되며, 위상 정렬(`LOG`) 및 최단 경로(`PATH`), 조상 탐색(`ANCESTORS`)에서도 다중 부모 구조가 완벽하게 반영됩니다.

### 3) 정렬 알고리즘 벤치마크 (`BENCHMARK`)
- $N = 200, 1000, 3000$의 무작위 정수 데이터를 생성하여 `Merge Sort`, `Quick Sort`, `Insertion Sort`의 실행 시간을 실측 비교합니다.
- 이를 통해 $O(N \log N)$과 $O(N^2)$ 알고리즘 간의 스케일링 격차를 수치로 직접 확인할 수 있습니다.

---

## 6. 제약 사항 준수 검증

- [x] **Python 3.10 이상 지원**: 파이썬 3.10+ 최신 문법 및 타입 힌트 준수
- [x] **표준 정렬 API 금지**: `sorted()`, `list.sort()`를 코드베이스 내에서 일절 사용하지 않음
- [x] **그래프 라이브러리 금지**: `networkx` 등의 외부 패키지 없이 순수 해시맵 인접 리스트로 그래프 알고리즘 구현
- [x] **세션 내 커밋 해시 유일성 보장**: 충돌 방지 카운터와 SHA-1 해시를 결합한 유일 키 생성
- [x] **표준화된 에러 메시지**: `Invalid args`, `Unknown branch: <name>`, `Unknown commit: <hash>` 처리
