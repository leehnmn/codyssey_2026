# 🧠 AI/SW 기초 핵심 개념 해설 가이드 (CORE CONCEPTS)

> **프로젝트**: 내가 고친 코드 설명을 AI가 대신 써주는 도우미 (`ai-git-assistant`)  
> **트랙**: `codyssey_2026` / 클라우드와 AI API (학습시간 40시간)  
> **목적**: 본 문서는 AI API 연동부터 Git CLI IPC 파이프라인, 프롬프트 엔지니어링, 출력 검증까지의 5대 핵심 개념을 누구나 다른 사람에게 명확하게 설명할 수 있도록 체계적으로 정리한 마스터 가이드입니다.

---

## 📑 목차
1. [핵심 개념 1: AI API의 REST 방식 연동 및 예외 대응 라이프사이클](#1-핵심-개념-1-ai-api의-rest-방식-연동-및-예외-대응-라이프사이클)
2. [핵심 개념 2: 하이퍼파라미터(Temperature, Max Tokens)가 생성 품질에 미치는 영향](#2-핵심-개념-2-하이퍼파라미터temperature-max-tokens가-생성-품질에-미치는-영향)
3. [핵심 개념 3: Git CLI(status, diff) 프로세스 연동 및 자동화 파이프라인](#3-핵심-개념-3-git-clistatus-diff-프로세스-연동-및-자동화-파이프라인)
4. [핵심 개념 4: Commit/PR 규격 준수를 위한 프롬프트 엔지니어링 원리](#4-핵심-개념-4-commitpr-규격-준수를-위한-프롬프트-엔지니어링-원리)
5. [핵심 개념 5: 실무 규칙 기반 출력 검증(Validation) 및 후처리(Post-processing)](#5-핵심-개념-5-실무-규칙-기반-출력-검증validation-및-후처리post-processing)

---

## 1. 핵심 개념 1: AI API의 REST 방식 연동 및 예외 대응 라이프사이클

### 1.1 REST API 연동 전체 흐름 (End-to-End Lifecycle)
AI 모델(예: OpenAI, Anthropic, Gemini 등)은 복잡한 딥러닝 인프라를 직접 운영하지 않고도 표준 HTTP 통신 규약인 **REST(Representational State Transfer) API**를 통해 호출할 수 있습니다.

```text
[Client: ai-git-assistant]
       │
       │  1. HTTP POST Request
       │     - URL: https://api.openai.com/v1/chat/completions
       │     - Headers: Authorization: Bearer <API_KEY>, Content-Type: application/json
       │     - Body: { "model": "gpt-4o-mini", "messages": [...], "temperature": 0.2 }
       ▼
┌──────────────────────────────────────────────┐
│       AI Model Provider Gateway              │
│  - 인증(Auth) -> 할당량(Rate Limit) -> 추론  │
└──────────────────────────────────────────────┘
       │
       │  2. HTTP Response
       │     - Success: HTTP 200 OK + JSON Body {"choices": [{"message": {"content": "..."}}]}
       │     - Error:   HTTP 4xx / 5xx + Error JSON
       ▼
[Client: ai-git-assistant]
   3. 역직렬화(Deserialization) & 안전 검증
```

### 1.2 요청(Request) 구성의 3대 필수 요소
1. **HTTP Method 및 엔드포인트 URL**:
   - `POST /v1/chat/completions` (입력 데이터가 크고 상태를 변경/생성하는 연산이므로 `POST` 사용)
2. **헤더(Headers)**:
   - `Authorization: Bearer <AI_API_KEY>`: 비대칭 인증 토큰을 통해 요청자를 식별. 코드 하드코딩을 절대 금지하고 `os.getenv("AI_API_KEY")`로 주입.
   - `Content-Type: application/json`: 페이로드가 JSON 직렬화 문자열임을 명시.
3. **바디(Payload Body)**:
   - `model`: 호출할 추론 모델 식별자 (예: `gpt-4o-mini`)
   - `messages`: 대화 히스토리 및 역할(`system`, `user`, `assistant`) 구조화 리스트.
   - `temperature`, `max_tokens`: 생성 제어 하이퍼파라미터.

### 1.3 응답 처리 및 예외 대응(Fault Tolerance) 매트릭스
네트워크 통신은 언제든 실패할 수 있으므로, 클라이언트는 HTTP 상태 코드별로 명확한 원인을 사용자에게 안내해야 합니다.

| 상태 코드 / 예외 | 발생 원인 | 프로그램 대응 방식 |
|:---|:---|:---|
| **HTTP 200 OK** | 모델 추론 성공 | JSON 본문의 `choices[0].message.content` 파싱 및 반환 |
| **HTTP 401 Unauthorized** | 유효하지 않거나 만료된 API Key | `API Key가 유효하지 않습니다` 에러 메시지 출력 후 안전 종료 |
| **HTTP 429 Too Many Requests** | 호출 분당 한도(RPM/TPM) 초과 또는 크레딧 소진 | `요청 한도 초과/크레딧 부족` 안내 및 재시도 간격 권고 |
| **HTTP 5xx Server Error** | AI 제공업체 내부 인프라 장애 | `AI 서버 일시 장애` 출력 및 잠시 후 재시도 유도 |
| **URLError (네트워크 단절)** | 로컬 오프라인, DNS 해석 실패, 방화벽 차단 | 엔드포인트 연결 실패 사유 안내 (`--mock` 모드 대안 제시) |
| **TimeoutError** | 응답 지연 (기본 30초 초과) | 요청 시간 초과 안내 및 네트워크 상태 점검 가이드 |

---

## 2. 핵심 개념 2: 하이퍼파라미터(Temperature, Max Tokens)가 생성 품질에 미치는 영향

생성형 LLM은 이전 토큰들을 바탕으로 다음 토큰의 **확률 분포(Probability Distribution)**를 계산합니다. 하이퍼파라미터는 이 확률 분포를 어떻게 샘플링할지 제어합니다.

```text
Logits (원시 점수) ──> [ Softmax with Temperature (T) ] ──> 샘플링 확률 분포
```

### 2.1 Temperature (온도: $T$)
Softmax 수식:
$$P(x_i) = \frac{\exp(z_i / T)}{\sum_j \exp(z_j / T)}$$

- **$T \to 0$ (저온: 0.0 ~ 0.3) [본 도구의 기본값: `0.2`]**:
  - 가장 확률이 높은 최상위 토큰(Argmax)으로 확률이 급격히 집중됩니다.
  - **효과**: 출력 결과가 **결정론적(Deterministic)**이며, 정형화되고 논리적 일관성이 극대화됩니다.
  - **Git 도우미에서의 의미**: 커밋 메시지나 PR 양식은 문학적 창의성이 아닌 **규격 준수, 사실 기반 요약, 템플릿 정확도**가 핵심이므로 낮은 온도(`0.2`)가 필수적입니다.
- **$T \to 1.0+$ (고온)**:
  - 확률 분포가 평평(Flatten)해져 상대적으로 드문 단어가 선택될 가능성이 높아집니다.
  - **효과**: 창의적이고 다채로운 표현이 생성되지만, 규격 이탈, 환각(Hallucination), 엉뚱한 포맷 출력 위험이 급증합니다.

### 2.2 Max Tokens (최대 생성 토큰 수)
- **개념**: AI 모델이 단일 응답에서 생성할 수 있는 최대 단어/서브워드 토큰 수의 상한선입니다.
- **영향도**:
  - **너무 작을 경우 (예: 100)**: PR 템플릿 생성 도중 `## How to Test` 섹션 중간에서 문장이 뚝 끊기는 **불완전 생성(Truncation)** 현상이 발생합니다.
  - **적정 범위 (예: 500 ~ 800) [본 도구 기본값: `800`]**: 커밋 메시지(약 100~200 토큰)와 상세 PR 초안(약 400~600 토큰)을 끊김 없이 완전하게 생성하면서도, 무한 루프나 과도한 과금을 방지합니다.
  - **너무 클 경우 (예: 4000+)**: 모델이 불필요한 장문의 미사여구를 길게 늘어놓아 가독성을 저해하고 API 비용이 상승합니다.

---

## 3. 핵심 개념 3: Git CLI(status, diff) 프로세스 연동 및 자동화 파이프라인

본 도구는 OS 수준의 프로세스 통신(Inter-Process Communication, IPC)을 활용하여 Git CLI의 실행 결과를 AI의 입력 데이터로 파이프라이닝합니다.

```text
┌─────────────────┐  subprocess.run(['git', 'status', '--porcelain'])
│  Local Worktree │ ───────────────────────────────────────────────────► [ GitCollector ]
│ (코드 변경 발생) │  subprocess.run(['git', 'diff', '--cached'])          │ - 변경 파일 추출
└─────────────────┘ ───────────────────────────────────────────────────► │ - diff 라인 수집
                                                                         │ - 변경점 유무 판별
                                                                         ▼
                                                           [ GitContext 데이터 객체 ]
                                                                         │
                                                                         ▼
                                                           [ SafetyFilter (Safe-Mode) ]
                                                           - 정규식 민감정보 마스킹
                                                           - 200줄/10개 파일 상한 절삭
                                                                         │
                                                                         ▼
                                                           [ Prompt Context 주입 ]
```

### 3.1 Git 명령어의 프로그래밍적 활용
1. **`git status --porcelain`**:
   - 일반 `git status`는 사람이 읽기 위한 다채로운 안내 문구가 포함되어 파싱이 어렵습니다.
   - `--porcelain` 옵션은 머신이 읽기 쉬운 정형화된 2글자 상태 코드(`M `, `A `, `D `, `?? `)와 상대 경로만을 반환하므로 견고한 파싱이 가능합니다.
2. **`git diff --cached` & `git diff`**:
   - 사용자가 `git add`로 스테이징한 변경점(`--cached`)과 아직 스테이징하지 않은 변경점을 포괄적으로 결합 수집하여, 어떤 상태에서도 누락 없이 diff를 추출합니다.
3. **변경 사항 부재 시 Early Exit**:
   - 변경된 파일이 없고 diff가 0줄인 경우 불필요한 AI API 호출을 사전에 차단(`[INFO] 변경 사항이 없습니다`)하여 API 비용 낭비를 원천 차단합니다.

---

## 4. 핵심 개념 4: Commit/PR 규격 준수를 위한 프롬프트 엔지니어링 원리

프롬프트 엔지니어링은 LLM에게 단순한 질문을 던지는 것이 아니라, **원하는 출력의 형식(Format), 제약(Constraints), 페르소나(Persona), 문맥(Context)**을 구조화하여 주입하는 기법입니다.

### 4.1 4단계 프롬프트 아키텍처
```text
1. System Role (페르소나 부여)
   "You are an expert software engineer and Git convention specialist..."
   └─ 전문성과 엄격한 규칙 준수 태도를 모델의 기본 동작 상태로 설정.

2. Grounding Context (사실 기반 문맥 주입)
   - Current Branch: feature/healthcheck
   - Changed Files: configs/nginx.conf, scripts/verify.sh
   - Git Diff: +location = /health { return 200 ... }
   └─ 오직 제공된 diff에 기반하여 사실만을 말하도록 접지(Grounding)하여 환각(Hallucination) 방지.

3. Strict Constraints (구체적 규칙 정의)
   - Conventional Commits 형식 (feat, fix, refactor 등)
   - 제목 최대 72자(권장 50자), PR 필수 3대 섹션(## Why, ## What, ## How to Test) 강제
   - 각 섹션 최소 1개 이상 불릿('- ') 포함 필수.

4. Few-shot Exemplar (모범 출력 예시 제공)
   - 모델이 추론할 표준 출력 양식을 예시로 직접 제시하여 출력 포맷 준수율을 99% 이상으로 끌어올림.
```

---

## 5. 핵심 개념 5: 실무 규칙 기반 출력 검증(Validation) 및 후처리(Post-processing)

생성형 AI는 본질적으로 확률 모델이므로, 프롬프트에서 제약을 명시하더라도 간혹 제목이 80자를 넘거나 섹션 헤더를 빼먹는 예외가 발생할 수 있습니다.  
따라서 프로덕션 수준의 도구는 **AI의 출력을 맹신하지 않고 결정론적(Deterministic) 코드 기반의 검증 및 후처리 레이어**를 두어야 합니다.

```text
[ AI 원시 응답 (Raw String) ]
             │
             ▼
┌──────────────────────────────────────────────┐
│           OutputValidator                    │
│                                              │
│  1. Markdown Fence(```) 정리                │
│  2. 제목 길이 검사 (Commit: 72자, PR: 80자)  │
│     -> 초과 시 말줄임표(...) 자동 트리밍     │
│  3. 필수 섹션(Why/What/How to Test) 검사     │
│     -> 누락 시 기본 보정 템플릿 주입         │
│  4. 불릿('- ') 누락 검사 및 자동 서식화      │
└──────────────────────────────────────────────┘
             │
             ▼
[ 규격이 100% 보장된 최종 터미널 뷰 ]
```

### 5.1 왜 검증과 후처리가 필수적인가?
1. **GitHub 및 협업 도구의 UI 깨짐 방지**:
   - Git 커밋 제목이 72자를 초과하면 `git log --oneline`이나 GitHub 웹 UI에서 제목이 잘려 표시됩니다.
2. **코드 리뷰 프로세스의 표준화**:
   - PR 본문에 Why(배경)와 How to Test(검증법)가 누락되면 리뷰어가 변경 의도를 파악하기 어렵고 리뷰 비용이 급증합니다.
3. **Fail-Safe 보장**:
   - AI 응답이 규격에서 미세하게 벗어나더라도 사용자가 에러를 맞닥뜨리지 않고 즉시 실무에 복사해 쓸 수 있는 완성형 텍스트를 제공합니다.

---

- **Author**: `codyssey_2026` Core Curriculum Team
- **Version**: 1.0.0
- **Document Status**: Production Complete
