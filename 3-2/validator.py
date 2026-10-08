"""validator.py - 출력 형식 검증 및 다듬기(Post-Processing & Validation) 모듈

AI가 생성한 원시 텍스트가 실무 규칙(커밋 제목 72자 이내, PR 제목 80자 이내,
PR 필수 섹션 Why/What/How to Test 및 각 섹션 불릿 포함)을 만족하는지 검증하고,
필요한 경우 자동 후처리를 통해 완벽한 양식으로 교정합니다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Tuple, List, Optional


@dataclass
class CommitValidationResult:
    is_valid: bool
    title: str
    body: str
    warnings: List[str]
    formatted_text: str


@dataclass
class PRValidationResult:
    is_valid: bool
    title: str
    body: str
    warnings: List[str]
    formatted_text: str


class OutputValidator:
    """커밋 메시지 및 PR 텍스트의 규격 검증 및 후처리를 담당하는 클래스"""

    MAX_COMMIT_TITLE_LEN = 72
    RECOMMENDED_COMMIT_TITLE_LEN = 50
    MAX_PR_TITLE_LEN = 80

    REQUIRED_PR_SECTIONS = ["## Why", "## What", "## How to Test"]

    @classmethod
    def clean_markdown_fences(cls, text: str) -> str:
        """응답 전체를 둘러싼 불필요한 코드 블록(```) 제거"""
        text = text.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            text = "\n".join(lines).strip()
        return text

    @classmethod
    def validate_and_refine_commit(cls, raw_text: str) -> CommitValidationResult:
        """커밋 메시지 규칙 검증 및 다듬기"""
        cleaned = cls.clean_markdown_fences(raw_text)
        lines = cleaned.splitlines()
        warnings = []

        if not lines:
            return CommitValidationResult(
                is_valid=False,
                title="chore: update changes",
                body="",
                warnings=["생성된 내용이 비어있어 기본 커밋 메시지로 대체되었습니다."],
                formatted_text="chore: update changes",
            )

        # 1. 제목 추출 및 다듬기
        raw_title = lines[0].strip()
        # 불필요한 접두어 정리 (예: "Commit Title: ", "Title: ")
        raw_title = re.sub(r"^(?:Commit\s+)?Title\s*:\s*", "", raw_title, flags=re.IGNORECASE).strip()

        # 길이 검증
        if len(raw_title) > cls.MAX_COMMIT_TITLE_LEN:
            warnings.append(
                f"커밋 제목이 최대 길이({cls.MAX_COMMIT_TITLE_LEN}자)를 초과하여({len(raw_title)}자) 자동 단축되었습니다."
            )
            title = raw_title[: cls.MAX_COMMIT_TITLE_LEN - 3].rstrip() + "..."
        else:
            title = raw_title

        if len(title) > cls.RECOMMENDED_COMMIT_TITLE_LEN:
            warnings.append(
                f"커밋 제목이 권장 길이({cls.RECOMMENDED_COMMIT_TITLE_LEN}자)를 초과했습니다 ({len(title)}자)."
            )

        # 2. 본문 추출 및 다듬기
        raw_body_lines = lines[1:] if len(lines) > 1 else []
        body_content = "\n".join(raw_body_lines).strip()

        # 본문 불릿 항목 검증
        bullet_lines = [l.strip() for l in raw_body_lines if l.strip().startswith("- ")]
        if not bullet_lines and body_content:
            # 불릿이 없지만 본문이 있는 경우 불릿으로 변환 후처리
            reformatted_bullets = []
            for b_line in body_content.splitlines():
                b_line = b_line.strip()
                if b_line:
                    reformatted_bullets.append(f"- {b_line}")
            body_content = "\n".join(reformatted_bullets)
            warnings.append("커밋 본문 항목에 불릿(- ) 형식을 자동 적용하였습니다.")

        formatted_text = f"{title}\n\n{body_content}" if body_content else title

        return CommitValidationResult(
            is_valid=len(warnings) == 0,
            title=title,
            body=body_content,
            warnings=warnings,
            formatted_text=formatted_text,
        )

    @classmethod
    def validate_and_refine_pr(cls, raw_text: str) -> PRValidationResult:
        """PR 제목 및 본문 규칙 검증 및 다듬기"""
        cleaned = cls.clean_markdown_fences(raw_text)
        warnings = []

        # 1. PR 제목 추출
        title_match = re.search(r"^(?:TITLE|PR Title)\s*:\s*(.+)$", cleaned, flags=re.MULTILINE | re.IGNORECASE)
        if title_match:
            raw_title = title_match.group(1).strip()
            # 본문은 TITLE 줄 이후
            body_part = cleaned[title_match.end() :].strip()
        else:
            # TITLE 태그가 없는 경우 첫 줄을 제목으로 간주
            lines = cleaned.splitlines()
            raw_title = lines[0].strip() if lines else "PR: Update changes"
            body_part = "\n".join(lines[1:]).strip() if len(lines) > 1 else ""

        # 제목 길이 검증
        if len(raw_title) > cls.MAX_PR_TITLE_LEN:
            warnings.append(
                f"PR 제목이 최대 길이({cls.MAX_PR_TITLE_LEN}자)를 초과하여({len(raw_title)}자) 자동 단축되었습니다."
            )
            title = raw_title[: cls.MAX_PR_TITLE_LEN - 3].rstrip() + "..."
        else:
            title = raw_title

        # 2. 필수 섹션 검증 (Why, What, How to Test)
        body = body_part
        missing_sections = []
        for sec in cls.REQUIRED_PR_SECTIONS:
            # 정규표현식으로 헤더 탐색 (대소문자 및 공백 유연 대응)
            pattern = re.compile(rf"{re.escape(sec)}\b", re.IGNORECASE)
            if not pattern.search(body):
                missing_sections.append(sec)

        # 누락된 섹션이 있으면 후처리로 보정 템플릿 주입
        if missing_sections:
            warnings.append(f"누락된 PR 필수 섹션이 있어 자동 보정되었습니다: {', '.join(missing_sections)}")
            for missing_sec in missing_sections:
                if missing_sec == "## Why":
                    body = f"## Why\n- 코드 변경 및 개선 필요에 따라 작업 수행\n\n" + body
                elif missing_sec == "## What":
                    body = body + f"\n\n## What\n- 관련 모듈 및 소스코드 수정 반영"
                elif missing_sec == "## How to Test":
                    body = body + f"\n\n## How to Test\n- 정상 실행 및 변경 기능 동작 확인"

        # 3. 각 섹션별 최소 1개 불릿(- ) 존재 여부 검증
        sections = re.split(r"(##\s+[^\n]+)", body)
        # re.split 결과: ['', '## Why', '내용...', '## What', '내용...']
        refined_sections = []
        current_header = ""

        for part in sections:
            part = part.strip()
            if not part:
                continue
            if part.startswith("## "):
                current_header = part
                refined_sections.append(part)
            else:
                # 섹션 내용 검사
                lines = [l.strip() for l in part.splitlines() if l.strip()]
                bullets = [l for l in lines if l.startswith("- ")]
                if not bullets and lines:
                    # 불릿이 없으면 각 줄에 불릿 추가
                    part = "\n".join(f"- {l}" if not l.startswith("- ") else l for l in lines)
                    warnings.append(f"섹션 [{current_header}] 내용에 불릿(- ) 형식을 자동 보정했습니다.")
                elif not lines:
                    part = "- 세부 변경 내용 참조"
                refined_sections.append(part)

        refined_body = "\n\n".join(refined_sections).strip()

        return PRValidationResult(
            is_valid=len(warnings) == 0,
            title=title,
            body=refined_body,
            warnings=warnings,
            formatted_text=f"{title}\n\n{refined_body}",
        )

    @classmethod
    def render_commit_box(cls, result: CommitValidationResult) -> str:
        """터미널에 구분선과 헤더로 구획된 커밋 메시지 박스 렌더링"""
        output = []
        output.append("--- Commit Message ---")
        output.append(result.title)
        if result.body:
            output.append("")
            output.append(result.body)
        output.append("----------------------")
        return "\n".join(output)

    @classmethod
    def render_pr_box(cls, result: PRValidationResult) -> str:
        """터미널에 구분선과 헤더로 구획된 PR 제목/본문 박스 렌더링"""
        output = []
        output.append("--- PR Title ---")
        output.append(result.title)
        output.append("")
        output.append("--- PR Body ---")
        output.append(result.body)
        output.append("----------------")
        return "\n".join(output)
