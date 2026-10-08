"""ai_client.py - AI API REST 연동 및 호출 관리 모듈

Python 표준 라이브러리(urllib)를 사용하여 외부 의존성 없이
REST API 규격으로 AI 모델에 요청을 전송하고 응답을 수신합니다.
API 키 검증, 하이퍼파라미터 제어, 오류 처리 및 1회 호출 원칙을 보장합니다.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class AIRequestConfig:
    model: str = "gpt-4o-mini"
    temperature: float = 0.2
    max_tokens: int = 800
    base_url: str = "https://api.openai.com/v1"
    timeout: int = 30
    is_mock: bool = False


class AIClient:
    """AI REST API 호출 및 통신을 담당하는 클라이언트 클래스"""

    def __init__(self, config: Optional[AIRequestConfig] = None):
        self.config = config or AIRequestConfig()
        self.call_count = 0
        self.api_key = self._resolve_api_key()

    def _resolve_api_key(self) -> Optional[str]:
        """환경변수에서 AI API Key를 탐색합니다 (하드코딩 금지 준수)."""
        # AI_API_KEY 우선, 보조로 OPENAI_API_KEY 지원
        key = os.getenv("AI_API_KEY") or os.getenv("OPENAI_API_KEY")
        return key.strip() if key else None

    def validate_api_key(self) -> bool:
        """API 키 유효성(존재 여부) 검사"""
        if self.config.is_mock:
            return True
        if not self.api_key:
            print("[ERROR] AI_API_KEY 환경변수가 설정되지 않았습니다.", file=sys.stderr)
            print("예) export AI_API_KEY=\"YOUR_KEY\"", file=sys.stderr)
            return False
        return True

    def generate_chat_completion(
        self,
        system_role: str,
        user_prompt: str,
    ) -> str:
        """단일 REST API 호출을 통해 AI 완성 텍스트를 생성합니다 (1회 호출 원칙 준수)."""
        if self.config.is_mock:
            self.call_count += 1
            print(f"[INFO] (MOCK 모드) AI API 호출: {self.call_count}회 완료")
            return self._generate_mock_response(user_prompt)

        if not self.validate_api_key():
            raise ValueError("API Key가 누락되었습니다.")

        endpoint = f"{self.config.base_url.rstrip('/')}/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
            "User-Agent": "ai-git-assistant/1.0",
        }

        payload: Dict[str, Any] = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_role},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")

        self.call_count += 1
        try:
            with urllib.request.urlopen(req, timeout=self.config.timeout) as response:
                body = response.read().decode("utf-8")
                res_data = json.loads(body)
                content = res_data["choices"][0]["message"]["content"]
                print(f"[INFO] AI API 호출: {self.call_count}회 완료 (Model: {self.config.model}, Status: 200 OK)")
                return content.strip()

        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode("utf-8")
                parsed = json.loads(error_body)
                error_msg = parsed.get("error", {}).get("message", error_body)
            except Exception:
                error_msg = error_body or str(e)

            if e.code == 401:
                raise RuntimeError(f"인증 실패 (401 Unauthorized): API Key가 유효하지 않습니다. 원인: {error_msg}")
            elif e.code == 429:
                raise RuntimeError(f"요청 한도 초과 (429 Rate Limit / Quota Exceeded): API 사용량 또는 크레딧을 확인하세요. 원인: {error_msg}")
            elif e.code >= 500:
                raise RuntimeError(f"AI 서버 오류 ({e.code} Server Error): AI 서비스 공급자 장애가 발생했습니다. 원인: {error_msg}")
            else:
                raise RuntimeError(f"API 요청 실패 ({e.code}): {error_msg}")

        except urllib.error.URLError as e:
            raise ConnectionError(f"네트워크 연결 오류: AI API 엔드포인트({endpoint})에 접속할 수 없습니다. 원인: {e.reason}")

        except TimeoutError:
            raise TimeoutError(f"API 요청 시간 초과: {self.config.timeout}초 내에 응답을 받지 못했습니다.")

        except json.JSONDecodeError as e:
            raise ValueError(f"응답 데이터 파싱 실패: 정상적인 JSON 응답이 아닙니다. 원인: {e}")

    def _generate_mock_response(self, prompt: str) -> str:
        """네트워크/API 키 없이 로컬 시연 및 테스트를 위해 제공하는 모의 응답 생성기"""
        is_pr = "[INSTRUCTIONS FOR PULL REQUEST]" in prompt or "TITLE: " in prompt

        if is_pr:
            return (
                "TITLE: feat: AWS VPC 기반 Nginx 헬스체크 및 안전 스크립트 기능 추가\n\n"
                "## Why\n"
                "- VPC 웹 서비스 환경에서 무중단 서비스 모니터링을 위한 /health 엔드포인트가 필요했습니다.\n"
                "- 외부 cURL 검증 및 트러블슈팅 자동화를 위해 통합 진단 스크립트를 구현해야 했습니다.\n\n"
                "## What\n"
                "- configs/nginx.conf 파일에 /health 라우팅 및 200 OK JSON 반환 설정 추가\n"
                "- scripts/verify.sh 스크립트 작성으로 외부 접근성 및 상태 코드 검증 로직 구현\n"
                "- main.py 및 git_collector.py 연동을 통한 Git 상태 파이프라인 완성\n\n"
                "## How to Test\n"
                "- export AI_API_KEY=\"YOUR_KEY\" 환경변수 설정\n"
                "- python main.py commit 및 python main.py pr 실행 후 터미널 출력 형식 확인\n"
                "- curl -i http://localhost/health 호출하여 200 OK 응답 및 JSON 바디 수신 검증"
            )
        else:
            return (
                "feat: AWS VPC 웹 서비스 헬스체크 엔드포인트 및 Nginx 설정 추가\n\n"
                "- configs/nginx.conf: /health 경로 요청 시 200 OK JSON 응답을 반환하도록 설정 추가\n"
                "- scripts/verify.sh: 외부 접근성 검증 및 상태 코드 판별 자동화 로직 구현"
            )
