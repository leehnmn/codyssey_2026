"""safety.py - 보안 및 민감정보 보호(Safe Mode) 모듈

git diff에 포함될 수 있는 API Key, 패스워드, 이메일 등 민감 정보를 정규표현식으로 마스킹하고,
대량 diff 전송으로 인한 토큰 낭비 및 정보 유출을 방지하기 위해 파일 수 및 줄 수를 제한합니다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class SafetyAuditResult:
    safe_diff: str
    safe_files: List[str]
    masked_count: int
    is_truncated: bool
    original_line_count: int
    final_line_count: int


class SafetyFilter:
    """Safe-mode 처리를 전담하는 필터 클래스"""

    # 민감 정보 탐지 정규표현식 패턴 목록
    SECRET_PATTERNS: List[Tuple[str, re.Pattern, str]] = [
        # AWS Access Key ID
        ("AWS_ACCESS_KEY", re.compile(r"\b(AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}\b"), "[REDACTED_AWS_KEY]"),
        # OpenAI / Standard API Key (sk-...)
        ("OPENAI_KEY", re.compile(r"\bsk-[a-zA-Z0-9_-]{20,}\b"), "[REDACTED_API_KEY]"),
        # JWT Token
        ("JWT_TOKEN", re.compile(r"\beyJ[a-zA-Z0-9_-]{10,}\.eyJ[a-zA-Z0-9_-]{10,}\.[a-zA-Z0-9_-]{10,}\b"), "[REDACTED_JWT]"),
        # Private Key 블록
        ("PRIVATE_KEY", re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+ PRIVATE KEY-----"), "[REDACTED_PRIVATE_KEY]"),
        # 키/패스워드 할당문 (예: password = "xxx", api_key: 'yyy')
        ("CREDENTIAL_ASSIGNMENT", re.compile(
            r"""(?i)([\"']?(?:api[_-]?key|secret(?:[_-]?key)?|password|passwd|auth[_-]?token|bearer|private[_-]?key)[\"']?\s*[:=]\s*[\"']?)([a-zA-Z0-9_\-\.\/+=@!#$%^&*]{8,})([\"']?)"""
        ), r"\1[REDACTED_SECRET]\3"),
        # 이메일 주소
        ("EMAIL_ADDRESS", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[REDACTED_EMAIL]"),
    ]

    def __init__(self, max_files: int = 10, max_lines: int = 200):
        self.max_files = max_files
        self.max_lines = max_lines

    def mask_sensitive_data(self, text: str) -> Tuple[str, int]:
        """텍스트 내의 민감 정보를 식별하여 안전한 대체 문자열로 마스킹합니다."""
        if not text:
            return text, 0

        masked_text = text
        total_masked = 0

        for name, pattern, replacement in self.SECRET_PATTERNS:
            if name == "CREDENTIAL_ASSIGNMENT":
                # 그룹 치환
                matches = list(pattern.finditer(masked_text))
                if matches:
                    total_masked += len(matches)
                    masked_text = pattern.sub(replacement, masked_text)
            else:
                matches = list(pattern.finditer(masked_text))
                if matches:
                    total_masked += len(matches)
                    masked_text = pattern.sub(replacement, masked_text)

        return masked_text, total_masked

    def truncate_diff(self, diff_text: str) -> Tuple[str, bool, int, int]:
        """diff 줄 수가 허용 상한(max_lines)을 초과할 경우 안전하게 절삭합니다."""
        lines = diff_text.splitlines()
        orig_count = len(lines)

        if orig_count <= self.max_lines:
            return diff_text, False, orig_count, orig_count

        truncated_lines = lines[:self.max_lines]
        truncated_lines.append(
            f"\n... [SAFE-MODE: diff 내용이 {self.max_lines}줄을 초과하여 보안 및 토큰 최적화를 위해 이후 변경사항 생략됨 (총 {orig_count}줄 중 {self.max_lines}줄 전송)] ..."
        )
        return "\n".join(truncated_lines), True, orig_count, len(truncated_lines)

    def apply(self, diff_text: str, changed_files: List[str], safe_mode_enabled: bool = True) -> SafetyAuditResult:
        """Safe-mode 정책을 적용하여 필터링된 diff 및 통계 반환"""
        if not safe_mode_enabled:
            line_count = len(diff_text.splitlines()) if diff_text else 0
            return SafetyAuditResult(
                safe_diff=diff_text,
                safe_files=changed_files,
                masked_count=0,
                is_truncated=False,
                original_line_count=line_count,
                final_line_count=line_count,
            )

        # 1. 파일 개수 제한
        safe_files = changed_files[:self.max_files]
        if len(changed_files) > self.max_files:
            safe_files.append(f"...외 {len(changed_files) - self.max_files}개 파일 (Safe-mode 파일 상한 {self.max_files}개)")

        # 2. 민감 정보 정규표현식 마스킹
        masked_diff, masked_count = self.mask_sensitive_data(diff_text)

        # 3. diff 줄 수 제한 (최대 200줄)
        final_diff, is_truncated, orig_lines, final_lines = self.truncate_diff(masked_diff)

        return SafetyAuditResult(
            safe_diff=final_diff,
            safe_files=safe_files,
            masked_count=masked_count,
            is_truncated=is_truncated,
            original_line_count=orig_lines,
            final_line_count=final_lines,
        )
