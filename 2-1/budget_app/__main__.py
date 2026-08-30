import os
import sys

# 패키지 상위 디렉토리를 파이썬 모듈 검색 경로(sys.path)에 추가
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

try:
    from .cli import main
except ImportError:
    from budget_app.cli import main

if __name__ == "__main__":
    main()