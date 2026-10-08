"""prompts.py - Commit 및 PR 생성을 위한 프롬프트 엔지니어링 모듈

Git 변경 사항(diff, changed files, branch)을 컨텍스트로 수입하여
정해진 규격(길이 제한, 불릿 규칙, 템플릿 섹션)을 준수하도록 AI에 지시하는 프롬프트를 구성합니다.
"""

from __future__ import annotations

from typing import List


class PromptBuilder:
    """Commit 및 PR 생성용 프롬프트 생성 빌더"""

    SYSTEM_ROLE_COMMIT = (
        "You are an expert software engineer and Git convention specialist. "
        "Your task is to analyze git status and git diff, and generate a concise, high-quality Git commit message. "
        "Strictly follow the formatting guidelines and return ONLY the final commit message without any extra chit-chat or code block markers."
    )

    SYSTEM_ROLE_PR = (
        "You are an expert technical lead and software architect. "
        "Your task is to analyze git branch, changed files, and git diff to write a clear, production-ready Pull Request draft. "
        "Strictly adhere to the required PR template and return ONLY the generated PR title and body without extra pleasantries or markdown wrappers around the entire answer."
    )

    @classmethod
    def build_commit_prompt(
        cls,
        branch: str,
        changed_files: List[str],
        diff_text: str,
    ) -> str:
        files_str = "\n".join(f"- {f}" for f in changed_files) if changed_files else "- (none)"

        return f"""[GIT CONTEXT]
- Current Branch: {branch}
- Changed Files ({len(changed_files)} files):
{files_str}

- Git Diff:
```diff
{diff_text}
```

[INSTRUCTIONS FOR COMMIT MESSAGE]
1. Write a professional, high-standard Git commit message based on the diff above.
2. Structure:
   - Line 1: Single commit title line in Korean (or English Conventional Commits prefix like 'feat:', 'fix:', 'docs:', 'refactor:', 'test:', 'chore:'). Recommended length under 50 chars, absolutely maximum 72 chars.
   - Line 2: Empty line (blank line separator).
   - Line 3+: Commit body (detailed explanation):
     * MUST explicitly mention 1 to 3 key changed files or modules.
     * MUST summarize 1 to 2 core modifications using bullet points ('- ').
3. Tone: Professional, clear, imperative mood.
4. Output Format:
Do NOT include markdown backticks around the entire message. Do NOT add meta commentary like 'Here is your commit message'. Return ONLY the commit message itself.

[EXAMPLE FORMAT]
feat: AWS VPC 웹 서비스 헬스체크 엔드포인트 및 Nginx 설정 추가

- nginx.conf: /health 경로 요청 시 200 OK JSON 응답을 반환하도록 설정 추가
- verify.sh: 외부 접근성 검증 및 상태 코드 판별 자동화 로직 구현
"""

    @classmethod
    def build_pr_prompt(
        cls,
        branch: str,
        changed_files: List[str],
        diff_text: str,
    ) -> str:
        files_str = "\n".join(f"- {f}" for f in changed_files) if changed_files else "- (none)"

        return f"""[GIT CONTEXT]
- Current Branch: {branch}
- Changed Files ({len(changed_files)} files):
{files_str}

- Git Diff:
```diff
{diff_text}
```

[INSTRUCTIONS FOR PULL REQUEST]
1. Analyze the context and generate a complete Pull Request draft (Title and Body).
2. PR Title Rules:
   - Must be exactly 1 line.
   - Maximum 80 characters.
   - Use Conventional Commits style (e.g., 'feat: ...', 'fix: ...').
3. PR Body Rules:
   - MUST strictly include the following 3 markdown section headers in order:
     ## Why
     ## What
     ## How to Test
   - Each section MUST contain at least one bullet point ('- ').
   - '## Why': Explain the motivation, problem solved, or background of the change.
   - '## What': Highlight the concrete implementation changes and affected components.
   - '## How to Test': Provide concrete commands, curl requests, or steps for reviewers to test.
4. Output Format:
Output the PR Title on the very first line prefixed by 'TITLE: ', followed by an empty line, then the PR Body starting with '## Why'.
Do NOT wrap the entire output in ``` markdown fences. Do NOT add preamble or concluding remarks.

[EXAMPLE OUTPUT FORMAT]
TITLE: feat: Nginx 헬스체크 및 안전 스크립트 기능 추가

## Why
- VPC 웹 서비스 운영 중 무중단 헬스체크와 인프라 자동 검증이 필요했습니다.
- 외부 모니터링 시스템에서 인스턴스 정상 가동 여부를 HTTP 200으로 확인할 필요가 있습니다.

## What
- configs/nginx.conf 파일에 /health 라우팅 블록 추가 및 JSON 응답 정의
- scripts/verify.sh 스크립트 추가로 cURL 기반 상태 검증 로직 구현

## How to Test
- nginx -t 실행 후 서비스 리로드: sudo systemctl reload nginx
- 터미널 헬스체크 호출: curl -i http://localhost/health
- HTTP 200 OK 및 상태 JSON 반환 여부 확인
"""
