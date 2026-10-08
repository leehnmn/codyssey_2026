#!/usr/bin/env python3
"""main.py - 내가 고친 코드 설명을 AI가 대신 써주는 도우미 CLI 메인 엔트리포인트

Git status 및 Git diff 결과를 수집하고, AI API를 단 1회 호출하여
Conventional Commits 및 규격화된 PR 템플릿(Why / What / How to Test)을 생성합니다.
"""

from __future__ import annotations

import argparse
import os
import sys

from git_collector import GitCollector
from safety import SafetyFilter
from prompts import PromptBuilder
from ai_client import AIClient, AIRequestConfig
from validator import OutputValidator


def setup_argument_parser() -> argparse.ArgumentParser:
    """CLI 인자 및 서브커맨드 파서 설정 (서브커맨드 앞/뒤 옵션 모두 지원)"""
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument(
        "--model",
        type=str,
        default="gpt-4o-mini",
        help="사용할 AI 모델 명칭 (기본값: gpt-4o-mini)",
    )
    common_parser.add_argument(
        "--temperature",
        type=float,
        default=0.2,
        help="생성 온도 파라미터 (기본값: 0.2, 낮을수록 정형화된 결과)",
    )
    common_parser.add_argument(
        "--max-tokens",
        type=int,
        default=800,
        help="최대 생성 토큰 수 (기본값: 800)",
    )
    common_parser.add_argument(
        "--safe-mode",
        action="store_true",
        default=False,
        help="보안 안전 모드 활성화 (민감 정보 마스킹 및 diff 길이/파일 수 제한)",
    )
    common_parser.add_argument(
        "--mock",
        action="store_true",
        default=False,
        help="API Key 없이 로컬 모의 응답(Mock) 테스트 모드로 실행",
    )
    common_parser.add_argument(
        "--verbose",
        action="store_true",
        default=False,
        help="상세 디버그 로그 출력",
    )

    main_parser = argparse.ArgumentParser(
        prog="ai-git-assistant",
        description="내가 고친 코드 설명을 AI가 대신 써주는 도우미 (Git Commit & PR 자동 생성 CLI)",
        epilog="예시: python main.py commit --safe-mode\n      python main.py pr --temperature 0.3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        parents=[common_parser],
    )

    subparsers = main_parser.add_subparsers(dest="command", help="실행할 작업 선택")

    # 1. commit 서브커맨드
    subparsers.add_parser(
        "commit",
        parents=[common_parser],
        help="Git 변경 사항을 기반으로 커밋 메시지 초안 자동 생성",
    )

    # 2. pr 서브커맨드
    subparsers.add_parser(
        "pr",
        parents=[common_parser],
        help="현재 브랜치 및 변경 사항을 기반으로 PR 제목/본문 초안 자동 생성",
    )

    # 3. diff-check 서브커맨드 (보조 진단)
    subparsers.add_parser(
        "diff-check",
        parents=[common_parser],
        help="AI 호출 없이 현재 변경 내역 및 Safe-mode 마스킹 점검",
    )

    return main_parser


def handle_commit(args, git_ctx, client, safety_filter):
    """commit 서브커맨드 실행 로직"""
    # 1. Safe-mode 적용
    audit = safety_filter.apply(
        diff_text=git_ctx.diff_text,
        changed_files=git_ctx.changed_files,
        safe_mode_enabled=args.safe_mode,
    )

    if args.safe_mode:
        if audit.masked_count > 0:
            print(f"[SECURITY] Safe-mode: 민감정보 {audit.masked_count}건 마스킹 완료")
        if audit.is_truncated:
            print(f"[SECURITY] Safe-mode: diff {audit.original_line_count}줄 -> {audit.final_line_count}줄로 절삭")

    # 2. 프롬프트 생성
    user_prompt = PromptBuilder.build_commit_prompt(
        branch=git_ctx.current_branch,
        changed_files=audit.safe_files,
        diff_text=audit.safe_diff,
    )

    print("[INFO] AI API 요청 중...")
    try:
        raw_response = client.generate_chat_completion(
            system_role=PromptBuilder.SYSTEM_ROLE_COMMIT,
            user_prompt=user_prompt,
        )
    except Exception as e:
        print(f"[ERROR] AI API 호출 실패: {e}", file=sys.stderr)
        sys.exit(1)

    print("[DONE] 커밋 메시지 생성 완료\n")

    # 3. 출력 형식 검증 및 다듬기
    validation = OutputValidator.validate_and_refine_commit(raw_response)
    if args.verbose and validation.warnings:
        for w in validation.warnings:
            print(f"[WARN] {w}")

    # 4. 터미널 결과 렌더링
    rendered_output = OutputValidator.render_commit_box(validation)
    print(rendered_output)


def handle_pr(args, git_ctx, client, safety_filter):
    """pr 서브커맨드 실행 로직"""
    print(f"[INFO] 현재 브랜치: {git_ctx.current_branch}")

    # 1. Safe-mode 적용
    audit = safety_filter.apply(
        diff_text=git_ctx.diff_text,
        changed_files=git_ctx.changed_files,
        safe_mode_enabled=args.safe_mode,
    )

    if args.safe_mode:
        if audit.masked_count > 0:
            print(f"[SECURITY] Safe-mode: 민감정보 {audit.masked_count}건 마스킹 완료")
        if audit.is_truncated:
            print(f"[SECURITY] Safe-mode: diff {audit.original_line_count}줄 -> {audit.final_line_count}줄로 절삭")

    # 2. 프롬프트 생성
    user_prompt = PromptBuilder.build_pr_prompt(
        branch=git_ctx.current_branch,
        changed_files=audit.safe_files,
        diff_text=audit.safe_diff,
    )

    print("[INFO] AI API 요청 중...")
    try:
        raw_response = client.generate_chat_completion(
            system_role=PromptBuilder.SYSTEM_ROLE_PR,
            user_prompt=user_prompt,
        )
    except Exception as e:
        print(f"[ERROR] AI API 호출 실패: {e}", file=sys.stderr)
        sys.exit(1)

    print("[DONE] PR 초안 생성 완료\n")

    # 3. 출력 형식 검증 및 다듬기
    validation = OutputValidator.validate_and_refine_pr(raw_response)
    if args.verbose and validation.warnings:
        for w in validation.warnings:
            print(f"[WARN] {w}")

    # 4. 터미널 결과 렌더링
    rendered_output = OutputValidator.render_pr_box(validation)
    print(rendered_output)


def handle_diff_check(args, git_ctx, safety_filter):
    """diff-check 보조 서브커맨드 실행 로직"""
    print("=== Git Change Diagnostics ===")
    print(f"현재 브랜치: {git_ctx.current_branch}")
    print(f"변경 파일 수: {len(git_ctx.changed_files)}")
    for f in git_ctx.changed_files:
        print(f"  * {f}")
    print(f"총 diff 라인 수: {git_ctx.diff_line_count}")

    audit = safety_filter.apply(
        diff_text=git_ctx.diff_text,
        changed_files=git_ctx.changed_files,
        safe_mode_enabled=args.safe_mode,
    )
    print(f"\n[Safe-Mode 상태: {'ON' if args.safe_mode else 'OFF'}]")
    print(f"탐지 및 마스킹된 민감정보: {audit.masked_count}건")
    print(f"diff 절삭 여부: {'예' if audit.is_truncated else '아니오'} ({audit.final_line_count}줄)")
    print("===============================")


def main():
    parser = setup_argument_parser()
    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(0)

    # 1. Git 상태 수집
    collector = GitCollector()
    git_ctx = collector.collect()

    if not git_ctx.is_repo:
        print(f"[ERROR] {git_ctx.error_message}", file=sys.stderr)
        sys.exit(1)

    # 변경 사항 감지 여부 검사
    if not git_ctx.has_changes:
        cmd_kr = "커밋 메시지를" if args.command == "commit" else "PR 초안을"
        print(f"[INFO] 변경 사항이 없습니다. {cmd_kr} 생성하지 않고 종료합니다.")
        sys.exit(0)

    print(f"[INFO] Git status 수집 완료: {len(git_ctx.changed_files)}개 파일 변경 감지")
    print(f"[INFO] Git diff 수집 완료: {git_ctx.diff_line_count}줄")

    # 2. AI 클라이언트 및 필터 준비
    config = AIRequestConfig(
        model=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        is_mock=args.mock,
    )
    client = AIClient(config=config)
    safety_filter = SafetyFilter(max_files=10, max_lines=200)

    # diff-check는 API 키 검증 불필요
    if args.command == "diff-check":
        handle_diff_check(args, git_ctx, safety_filter)
        return

    # API 키 선제 검증
    if not client.validate_api_key():
        sys.exit(1)

    # 3. 서브커맨드 분기 실행
    if args.command == "commit":
        handle_commit(args, git_ctx, client, safety_filter)
    elif args.command == "pr":
        handle_pr(args, git_ctx, client, safety_filter)


if __name__ == "__main__":
    main()
