"""git_collector.py - Git 변경 사항 수집 및 상태 감지 모듈

git status와 git diff 명령 결과를 실행하여 변경된 파일 목록,
코드 변경 diff 텍스트, 현재 브랜치 정보를 안전하게 수집합니다.
"""

from __future__ import annotations

import subprocess
import os
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class GitContext:
    is_repo: bool = False
    current_branch: str = "main"
    changed_files: List[str] = field(default_factory=list)
    diff_text: str = ""
    diff_line_count: int = 0
    error_message: Optional[str] = None

    @property
    def has_changes(self) -> bool:
        return bool(self.changed_files or self.diff_text.strip())


class GitCollector:
    """Git CLI와 연동하여 변경 내역을 수집하는 수집기 클래스"""

    def __init__(self, cwd: Optional[str] = None):
        self.cwd = cwd or os.getcwd()

    def _run_git_command(self, args: List[str]) -> tuple[int, str, str]:
        """subprocess를 통해 git 명령어를 안전하게 실행합니다."""
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
                encoding="utf-8",
                errors="replace",
            )
            return result.returncode, result.stdout.strip(), result.stderr.strip()
        except FileNotFoundError:
            return -1, "", "Git이 설치되어 있지 않거나 PATH에 등록되지 않았습니다."
        except Exception as e:
            return -1, "", str(e)

    def is_git_installed(self) -> bool:
        """Git 실행 파일 존재 여부 확인"""
        code, _, _ = self._run_git_command(["--version"])
        return code == 0

    def is_git_repository(self) -> bool:
        """현재 디렉토리가 Git 저장소 내부인지 확인"""
        code, stdout, _ = self._run_git_command(["rev-parse", "--is-inside-work-tree"])
        return code == 0 and stdout.lower() == "true"

    def get_current_branch(self) -> str:
        """현재 체크아웃된 브랜치명 조회"""
        code, stdout, _ = self._run_git_command(["branch", "--show-current"])
        if code == 0 and stdout:
            return stdout
        # detached HEAD 상태 대응
        code, stdout, _ = self._run_git_command(["rev-parse", "--short", "HEAD"])
        if code == 0 and stdout:
            return f"HEAD({stdout})"
        return "unknown-branch"

    def get_changed_files(self) -> List[str]:
        """git status --porcelain 명령을 통해 변경/추가/삭제된 파일 목록 조회"""
        code, stdout, _ = self._run_git_command(["status", "--porcelain"])
        if code != 0 or not stdout:
            return []

        files = []
        for line in stdout.splitlines():
            line = line.strip()
            if not line:
                continue
            # 포맷: XY PATH 또는 XY ORIG_PATH -> NEW_PATH
            parts = line[3:].strip()
            if "->" in parts:
                parts = parts.split("->")[-1].strip()
            if parts:
                files.append(parts)
        return files

    def get_git_diff(self) -> str:
        """Staged 및 Unstaged diff를 모두 수집하여 포괄적인 변경 내역을 반환"""
        # 1. staged diff 확인
        code_staged, stdout_staged, _ = self._run_git_command(["diff", "--cached"])
        # 2. unstaged diff 확인
        code_unstaged, stdout_unstaged, _ = self._run_git_command(["diff"])

        combined_diff = []
        if code_staged == 0 and stdout_staged:
            combined_diff.append(stdout_staged)
        if code_unstaged == 0 and stdout_unstaged:
            combined_diff.append(stdout_unstaged)

        # 만약 diff 명령으로 안 잡히지만 untracked 파일이 있는 경우 (git status에만 존재)
        if not combined_diff:
            # HEAD와의 diff 시도
            code_head, stdout_head, _ = self._run_git_command(["diff", "HEAD"])
            if code_head == 0 and stdout_head:
                combined_diff.append(stdout_head)

        full_diff = "\n".join(combined_diff).strip()
        return full_diff

    def collect(self) -> GitContext:
        """전체 Git 컨텍스트를 수집하여 GitContext 객체로 반환"""
        if not self.is_git_installed():
            return GitContext(
                is_repo=False,
                error_message="Git이 설치되어 있지 않거나 환경변수 PATH에서 찾을 수 없습니다.",
            )

        if not self.is_git_repository():
            return GitContext(
                is_repo=False,
                error_message="현재 디렉토리가 Git 저장소가 아닙니다. git init 또는 Git 프로젝트 루트에서 실행하세요.",
            )

        branch = self.get_current_branch()
        files = self.get_changed_files()
        diff = self.get_git_diff()
        line_count = len(diff.splitlines()) if diff else 0

        # diff가 비어있지만 신규 생성 파일(Untracked)이 있는 경우 파일 목록을 diff 힌트로 제공
        if not diff and files:
            diff = f"# Untracked / newly added files:\n" + "\n".join(f"+ {f}" for f in files)
            line_count = len(files)

        return GitContext(
            is_repo=True,
            current_branch=branch,
            changed_files=files,
            diff_text=diff,
            diff_line_count=line_count,
            error_message=None,
        )
