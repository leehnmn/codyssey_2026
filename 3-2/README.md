[![Python Version](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Zero Dependency](https://img.shields.io/badge/Dependency-Zero%20External%20Pip-orange?logo=pypi&logoColor=white)](https://docs.python.org/3/library/)
[![Codyssey Track](https://img.shields.io/badge/Codyssey%202026-AI%2FSW%20Track-purple)](https://github.com/leehnmn/codyssey_2026)
[![Linked Project](https://img.shields.io/badge/Linked%20Project-aws--vpc--web--service-FF9900?logo=amazon-aws&logoColor=white)](https://github.com/leehnmn/codyssey_2026/tree/main/aws-vpc-web-service)

> **내가 고친 코드 설명을 AI가 대신 써주는 도우미 (`ai-git-assistant`)**  
> 본 프로젝트는 [`aws-vpc-web-service`](https://github.com/leehnmn/codyssey_2026/tree/main/aws-vpc-web-service) 인프라 프로젝트를 비롯한 다양한 소프트웨어 개발 과정에서, **Git 변경 사항(`git status`, `git diff`)을 자동으로 수집**하고 **AI REST API를 단 1회 호출**하여 실무 규칙(Conventional Commits, Why/What/How to Test PR 템플릿)을 만족하는 커밋 메시지와 PR 초안을 자동 생성하는 프로덕션 CLI 도구입니다.

---

## 📑 목차 (Table of Contents)
1. [프로젝트 소개 및 이전 미션(aws-vpc-web-service) 연계 배경](#1-프로젝트-소개-및-이전-미션aws-vpc-web-service-연계-배경)
2. [최종 제출 결과물 3종 요약](#2-최종-제출-결과물-3종-요약)
3. [설치 및 환경 준비 (Zero-Dependency)](#3-설치-및-환경-준비-zero-dependency)
4. [환경변수(API Key) 설정 방법](#4-환경변수api-key-설정-방법)
5. [CLI 사용법 및 실행 명령어](#5-cli-사용법-및-실행-명령어)
6. [실행 및 출력 예시 (Execution Examples)](#6-실행-및-출력-예시-execution-examples)
   - [케이스 1: 커밋 메시지 자동 생성 (`commit`)](#케이스-1-커밋-메시지-자동-생성-commit)
   - [케이스 2: Pull Request 초안 자동 생성 (`pr`)](#케이스-2-pull-request-초안-자동-생성-pr)
   - [케이스 3: API Key 누락 시 안전 안내](#케이스-3-api-key-누락-시-안전-안내)
   - [케이스 4: 변경 사항 부재 시 Early Exit](#케이스-4-변경-사항-부재-시-early-exit)
7. [보안 및 민감정보 보호 정책 (`--safe-mode`)](#7-보안-및-민감정보-보호-정책---safe-mode)
8. [비용 최적화 및 API 요청 횟수 제약 정책](#8-비용-최적화-및-api-요청-횟수-제약-정책)
9. [프로젝트 아키텍처 및 소스코드 구성 (총 9개 파일)](#9-프로젝트-아키텍처-및-소스코드-구성-총-9개-파일)
10. [핵심 개념 학습 가이드 (`CORE_CONCEPTS.md`)](#10-핵심-개념-학습-가이드-core_conceptsmd)

---

## 1. 프로젝트 소개 및 이전 미션(aws-vpc-web-service) 연계 배경

[`codyssey_2026/aws-vpc-web-service`](https://github.com/leehnmn/codyssey_2026/tree/main/aws-vpc-web-service) 미션에서 격리된 VPC 네트워크 환경을 구축하고 Nginx 웹 서버, 자동 배포 스크립트(`deploy.sh`), 트러블슈팅 진단 도구(`verify.sh`), 컨테이너 Dockerfile을 제작하면서 수많은 커밋과 문서화 작업이 수반되었습니다.

```text
┌─────────────────────────────────────────────────────────────┐
│ 이전 미션: codyssey_2026/aws-vpc-web-service                 │
│  - configs/nginx.conf  (헬스체크 /health 라우팅 수정)        │
│  - scripts/deploy.sh   (VPC/Subnet 보안그룹 규칙 추가)      │
│  - docker/Dockerfile   (Alpine Nginx 이미지 최적화)         │
└──────────────────────────────┬──────────────────────────────┘
                               │ git diff 발생
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 본 프로젝트: ai-git-assistant                                │
│  - git status / diff 파이프라인 수집                        │
│  - Safe-mode 민감정보 마스킹 (AWS Key, Token 유출 방지)     │
│  - AI REST API 1회 호출 (온도 0.2, 프롬프트 엔지니어링)     │
│  - 규격 검증 및 포매터 (72자 커밋 제목 / PR 3대 섹션 강제) │
└──────────────────────────────┬──────────────────────────────┘
                               ▼
┌─────────────────────────────────────────────────────────────┐
│ 표준화된 협업 산출물 자동 생성                             │
│  - Conventional Commit: feat: AWS VPC 헬스체크 추가...      │
│  - PR 초안: ## Why / ## What / ## How to Test               │
└─────────────────────────────────────────────────────────────┘
```

본 프로젝트 **`ai-git-assistant`**는 이러한 인프라 및 소프트웨어 변경 사항을 터미널에서 즉각 감지하여, 사람이 직접 작성하는 데 소요되는 인지적 피로를 줄이고 팀 전체의 커밋/PR 컨벤션을 일관되게 유지해주는 개발 생산성 도우미입니다.

---

## 2. 최종 제출 결과물 3종 요약

| 구분 | 요구사항 | 구현 결과물 위치 | 상태 |
|:---|:---|:---|:---:|
| **1. AI API 연동 및 자동화 CLI** | 단일 실행으로 git status/diff 수집, AI 1회 호출, 검증된 커밋/PR 출력 | [`main.py`](main.py), [`git_collector.py`](git_collector.py), [`ai_client.py`](ai_client.py) | ✅ 완료 |
| **2. GitHub 리포지토리 구성** | 표준 소스코드 구조, Git 초기화, 커밋 히스토리 보존, 10개 이내 압축 | 본 리포지토리 루트 (총 9개 핵심 파일 구성) | ✅ 완료 |
| **3. 사용 가이드 및 핵심 개념** | 설치/실행법, Key 설정법, 안전모드/비용 정책, 5대 핵심 개념 문서화 | [`README.md`](README.md), [`CORE_CONCEPTS.md`](CORE_CONCEPTS.md) | ✅ 완료 |

---

## 3. 설치 및 환경 준비 (Zero-Dependency)

본 도구는 **Python 3.10 이상**의 표준 라이브러리(`urllib`, `json`, `subprocess`, `argparse`, `re` 등)만을 사용하여 제작되었습니다. 별도의 무거운 외부 패키지(`pip install openai requests ...`)를 설치할 필요 없이 즉시 실행할 수 있습니다.

### 시스템 요구사항
- Python 3.10 이상
- Git 2.20 이상

```bash
# 리포지토리 복제
git clone https://github.com/leehnmn/codyssey_2026.git
cd codyssey_2026/ai-git-assistant

# 파이썬 버전 확인
python3 --version  # Python 3.10+ 권장
```

---

## 4. 환경변수(API Key) 설정 방법

보안 원칙에 따라 AI API Key는 코드 내에 절대 하드코딩되지 않으며, 환경변수를 통해 안전하게 주입됩니다.

### Linux / macOS (Zsh / Bash)
```bash
# OpenAI 호환 API Key 등록
export AI_API_KEY="sk-your-actual-api-key-here"

# 정상 등록 확인
echo $AI_API_KEY
```

### Windows (PowerShell)
```powershell
$env:AI_API_KEY="sk-your-actual-api-key-here"
```

> 💡 **오프라인 / MOCK 테스트 안내:**  
> API Key가 없거나 네트워크 연결이 제한된 환경에서는 `--mock` 플래그를 추가하여 모든 CLI 동작 흐름을 무료로 검증할 수 있습니다.

---

## 5. CLI 사용법 및 실행 명령어

```bash
python main.py [-h] [--model MODEL] [--temperature TEMPERATURE]
               [--max-tokens MAX_TOKENS] [--safe-mode] [--mock] [--verbose]
               {commit,pr,diff-check}
```

### 서브커맨드(Subcommands)
- `commit`: 현재 Git 변경 사항을 요약하여 Conventional Commits 커밋 메시지 초안 생성
- `pr`: 현재 브랜치 및 변경 사항을 바탕으로 Why/What/How to Test PR 제목/본문 생성
- `diff-check`: AI 호출 없이 현재 변경 파일 목록, diff 라인 수, 민감정보 마스킹 여부 진단

### 주요 옵션(Options)
| 옵션 | 기본값 | 설명 |
|:---|:---:|:---|
| `--safe-mode` | `False` | 민감정보(API 키, 토큰, 이메일) 정규식 마스킹 및 diff 전송 상한 적용 |
| `--model` | `gpt-4o-mini` | 사용할 AI 모델 식별자 (OpenAI 규격 호환) |
| `--temperature` | `0.2` | 생성 다양성 제어 (0.0~1.0, 낮을수록 정형화된 규격 준수) |
| `--max-tokens` | `800` | 최대 생성 토큰 수 (PR 템플릿 완성도 보장) |
| `--mock` | `False` | 외부 API 호출 없이 로컬 모의 응답 생성 (테스트/평가용) |
| `--verbose` | `False` | 유효성 검사 경고 및 상세 디버그 로그 출력 |

---

## 6. 실행 및 출력 예시 (Execution Examples)

### 케이스 1: 커밋 메시지 자동 생성 (`commit`)
Git 작업 디렉토리에서 코드를 수정한 뒤 커밋 메시지를 생성합니다.

```bash
python main.py commit --safe-mode
```

**터미널 실제 출력 결과:**
```text
[INFO] Git status 수집 완료: 2개 파일 변경 감지
[INFO] Git diff 수집 완료: 48줄
[INFO] AI API 요청 중...
[INFO] AI API 호출: 1회 완료 (Model: gpt-4o-mini, Status: 200 OK)
[DONE] 커밋 메시지 생성 완료

--- Commit Message ---
feat: AWS VPC 웹 서비스 헬스체크 엔드포인트 및 Nginx 설정 추가

- configs/nginx.conf: /health 경로 요청 시 200 OK JSON 응답을 반환하도록 설정 추가
- scripts/verify.sh: 외부 접근성 검증 및 상태 코드 판별 자동화 로직 구현
----------------------
```

---

### 케이스 2: Pull Request 초안 자동 생성 (`pr`)
기능 브랜치에서 변경 사항에 대한 PR 문서를 생성합니다.

```bash
python main.py pr --safe-mode
```

**터미널 실제 출력 결과:**
```text
[INFO] Git status 수집 완료: 2개 파일 변경 감지
[INFO] Git diff 수집 완료: 48줄
[INFO] 현재 브랜치: feature/nginx-healthcheck
[INFO] AI API 요청 중...
[INFO] AI API 호출: 1회 완료 (Model: gpt-4o-mini, Status: 200 OK)
[DONE] PR 초안 생성 완료

--- PR Title ---
feat: AWS VPC 기반 Nginx 헬스체크 및 안전 스크립트 기능 추가

--- PR Body ---
## Why
- VPC 웹 서비스 환경에서 무중단 서비스 모니터링을 위한 /health 엔드포인트가 필요했습니다.
- 외부 cURL 검증 및 트러블슈팅 자동화를 위해 통합 진단 스크립트를 구현해야 했습니다.

## What
- configs/nginx.conf 파일에 /health 라우팅 및 200 OK JSON 반환 설정 추가
- scripts/verify.sh 스크립트 작성으로 외부 접근성 및 상태 코드 검증 로직 구현
- main.py 및 git_collector.py 연동을 통한 Git 상태 파이프라인 완성

## How to Test
- 환경변수 설정: export AI_API_KEY="YOUR_KEY"
- 커밋 메시지 생성: python main.py commit
- PR 초안 생성: python main.py pr
- 결과로 출력된 PR 본문이 Why/What/How to Test 구조와 길이 규칙을 만족하는지 확인
----------------
```

---

### 케이스 3: API Key 누락 시 안전 안내
환경변수가 지정되지 않은 상태에서 실행하면 원인을 즉시 안내하고 안전하게 중단됩니다.

```bash
# 환경변수 미설정 상태
python main.py commit
```

**터미널 실제 출력 결과:**
```text
[INFO] Git status 수집 완료: 1개 파일 변경 감지
[INFO] Git diff 수집 완료: 12줄
[ERROR] AI_API_KEY 환경변수가 설정되지 않았습니다.
예) export AI_API_KEY="YOUR_KEY"
```

---

### 케이스 4: 변경 사항 부재 시 Early Exit
워킹 트리가 깨끗한 상태(Clean)에서는 불필요한 API 요청을 방지합니다.

```bash
python main.py commit
```

**터미널 실제 출력 결과:**
```text
[INFO] 변경 사항이 없습니다. 커밋 메시지를 생성하지 않고 종료합니다.
```

---

## 7. 보안 및 민감정보 보호 정책 (`--safe-mode`)

개발 중 실수로 Git diff에 민감한 정보(AWS Secret, API Key, DB Password 등)가 포함될 경우, 이를 그대로 외부 AI API로 전송하면 심각한 보안 침해가 발생합니다. 본 도구는 이를 원천 차단하기 위해 **이중 안전망(Dual Defense Layer)**을 제공합니다.

### 🛡️ 정책 (A) 정규표현식 기반 민감정보 자동 마스킹
`--safe-mode` 활성화 시, 프롬프트 전송 전 diff 본문에서 다음 패턴을 자동 감지하여 대체합니다:
- **AWS Access Key ID**: `AKIA...` ➔ `[REDACTED_AWS_KEY]`
- **OpenAI / Third-party API Key**: `sk-...` ➔ `[REDACTED_API_KEY]`
- **JWT 토큰**: `eyJ...` ➔ `[REDACTED_JWT]`
- **Private Key 블록**: `-----BEGIN PRIVATE KEY-----` ➔ `[REDACTED_PRIVATE_KEY]`
- **패스워드/비밀키 할당문**: `password = "..."` ➔ `password = "[REDACTED_SECRET]"`
- **개인 이메일 주소**: `user@domain.com` ➔ `[REDACTED_EMAIL]`

### 🛡️ 정책 (B) 전송량 및 diff 상한선 제어
대량의 바이너리나 수천 줄의 변경사항이 전송되어 토큰이 낭비되거나 문맥이 왜곡되는 것을 방지합니다:
- **최대 파일 수**: 최대 10개 파일까지만 분석 컨텍스트로 전달.
- **최대 diff 줄 수**: 최대 200줄까지만 전송하며, 초과 시 안전 절삭 안내문구를 주입합니다.

---

## 8. 비용 최적화 및 API 요청 횟수 제약 정책

AI API는 호출 횟수 및 입출력 토큰량에 비례하여 비용이 부과됩니다. 본 도구는 엄격한 비용 통제 원칙을 준수합니다:

1. **1회 실행 1회 호출 원칙 (Strict 1-Call Policy)**:
   - `commit` 및 `pr` 명령어는 각각 **단 1회의 REST API 호출**로 최종 완성본을 도출합니다.
   - 불필요한 다단계 체인 호출을 배제하여 비용을 최소화합니다.
2. **호출 카운팅 로깅**:
   - 매 실행 시 `[INFO] AI API 호출: 1회 완료` 로그를 출력하여 사용자가 호출 빈도를 명확히 인지할 수 있습니다.
3. **사전 검사 기반 Early Exit**:
   - `git status` 및 `git diff` 결과가 0건이면 API 호출 단계에 진입하지 않고 즉시 종료합니다.
4. **저비용 고성능 모델 기본 채택**:
   - 기본 모델로 `gpt-4o-mini`를 지정하여 1회 생성당 비용을 $0.0001 미만 수준으로 억제합니다.

---

## 9. 프로젝트 아키텍처 및 소스코드 구성 (총 9개 파일)

프로젝트는 단일 책임 원칙(SRP)에 따라 모듈화되어 있으며, **문서 및 설정 포함 총 9개 파일**로 압축 구성되었습니다.

```text
ai-git-assistant/
├── .gitignore              # Python 캐시, .env, 키 파일 유출 방지
├── README.md               # [결과물 3] 프로젝트 총괄 가이드 및 실행 매뉴얼
├── CORE_CONCEPTS.md        # [결과물 3] 5대 핵심 개념 심층 해설서
├── main.py                 # [결과물 1] CLI 진입점 및 서브커맨드 오케스트레이션
├── git_collector.py        # [결과물 1] Git CLI(status, diff) 프로세스 수집기
├── safety.py               # [결과물 1] Safe-Mode 민감정보 정규식 마스킹 & 절삭 필터
├── prompts.py              # [결과물 1] Conventional Commits 및 PR 프롬프트 빌더
├── ai_client.py            # [결과물 1] urllib 기반 REST API 클라이언트 & Mock 엔진
└── validator.py            # [결과물 1] 커밋 72자 / PR 3대 섹션 규격 검증 및 포매터
```

---

## 10. 핵심 개념 학습 가이드 (`CORE_CONCEPTS.md`)

본 미션을 통해 학습자가 반드시 말로 설명할 수 있어야 하는 5대 핵심 개념에 대한 상세 이론과 해설은 [`CORE_CONCEPTS.md`](CORE_CONCEPTS.md)에 수록되어 있습니다:

1. **AI API의 REST 연동 아키텍처 및 예외 대응 라이프사이클**
2. **생성형 AI 하이퍼파라미터(Temperature, Max Tokens)의 영향도 분석**
3. **Git CLI와 서브프로세스 IPC 파이프라인 연동 원리**
4. **Commit/PR 양식 강제를 위한 프롬프트 엔지니어링 원리**
5. **실무 규칙 검증(Validation) 및 결정론적 후처리(Post-Processing)**

---

- **Author**: `codyssey_2026` Core Engineering Team
- **Linked Project**: [`codyssey_2026/aws-vpc-web-service`](https://github.com/leehnmn/codyssey_2026/tree/main/aws-vpc-web-service)
- **License**: MIT License
