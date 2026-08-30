import json # JSONL 직렬화/역직렬화 라이브러리 로드
import os # 파일 및 디렉토리 제어 모듈 로드
import tempfile # 안전한 파일 원자적 교체를 위한 임시 파일 모듈
from typing import Generator, List, Dict # 스트리밍 제너레이터 및 타입 힌트 로드
from .models import Transaction # 거래 데이터 모델 로드

class DataStorage: # 3개 분리 파일(거래, 카테고리, 예산) 영구 저장소 클래스
    def __init__(self, data_dir: str = "./data"): # 저장 경로 초기화
        self.data_dir = data_dir # 저장 폴더 경로 저장
        os.makedirs(self.data_dir, exist_ok=True) # 폴더가 없으면 자동 생성
        self.tx_file = os.path.join(data_dir, "transactions.jsonl") # 거래 내역 파일 경로
        self.cat_file = os.path.join(data_dir, "categories.jsonl") # 카테고리 파일 경로
        self.bgt_file = os.path.join(data_dir, "budgets.jsonl") # 예산 설정 파일 경로
        self._init_files() # 기본 파일 자동 생성 및 초기화

    def _init_files(self) -> None: # 필수 3개 파일이 없을 경우 초기화 수행
        for f in [self.tx_file, self.bgt_file]: # 거래 및 예산 파일 순회
            if not os.path.exists(f): open(f, "a", encoding="utf-8").close() # 빈 파일 생성
        if not os.path.exists(self.cat_file): # 카테고리 파일이 없으면 기본 카테고리 생성 (안 A)
            cats = ["식비", "교통", "쇼핑", "급여", "기타"] # 기본 제공 카테고리 목록
            with open(self.cat_file, "w", encoding="utf-8") as f:
                for c in cats: f.write(json.dumps({"name": c}, ensure_ascii=False) + "\n") # 기본값 저장

    def append_transaction(self, tx: Transaction) -> None: # 신규 거래 1건 파일 끝에 추가
        with open(self.tx_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(tx.to_dict(), ensure_ascii=False) + "\n") # JSONL 1줄 추가

    def stream_transactions(self) -> Generator[Transaction, None, None]: # yield 기반 스트리밍 처리
        with open(self.tx_file, "r", encoding="utf-8") as f: # 파일 열기
            for line in f: # 대용량 파일도 1줄씩 순회하며 메모리 절약
                if line.strip(): yield Transaction.from_dict(json.loads(line.strip())) # 모델로 변환하여 yield

    def rewrite_transactions(self, tx_list: List[Transaction]) -> None: # 거래 목록 재작성 (수정/삭제용 원자적 교체)
        with tempfile.NamedTemporaryFile("w", dir=self.data_dir, delete=False, encoding="utf-8") as tf:
            for tx in tx_list: tf.write(json.dumps(tx.to_dict(), ensure_ascii=False) + "\n") # 임시 파일에 쓰기
            t_name = tf.name # 임시 파일 이름 저장
        os.replace(t_name, self.tx_file) # os.replace로 원자적 교체하여 파일 손상 방지

    def get_categories(self) -> List[str]: # 등록된 카테고리 목록 조회
        with open(self.cat_file, "r", encoding="utf-8") as f:
            return [json.loads(l)["name"] for l in f if l.strip()] # 이름 리스트 추출

    def add_category(self, name: str) -> bool: # 신규 카테고리 추가
        if name in self.get_categories(): return False # 중복 시 False 반환
        with open(self.cat_file, "a", encoding="utf-8") as f:
            f.write(json.dumps({"name": name}, ensure_ascii=False) + "\n") # 추가 저장
        return True # 성공 반환

    def remove_category(self, name: str) -> None: # 카테고리 삭제 처리
        cats = [c for c in self.get_categories() if c != name] # 삭제 대상 제외
        with open(self.cat_file, "w", encoding="utf-8") as f:
            for c in cats: f.write(json.dumps({"name": c}, ensure_ascii=False) + "\n") # 갱신 저장

    def set_budget(self, month: str, amount: int) -> None: # 특정 월의 예산 저장
        budgets = self.get_budgets() # 기존 예산 불러오기
        budgets[month] = amount # 해당 월 예산 갱신
        with open(self.bgt_file, "w", encoding="utf-8") as f:
            for m, amt in budgets.items(): f.write(json.dumps({"month": m, "amount": amt}) + "\n") # 저장

    def get_budgets(self) -> Dict[str, int]: # 전체 설정된 예산 맵 조회
        budgets = {} # 예산 저장 딕셔너리
        with open(self.bgt_file, "r", encoding="utf-8") as f:
            for line in f: # 1줄씩 파싱
                if line.strip():
                    data = json.loads(line.strip()) # 파싱
                    budgets[data["month"]] = data["amount"] # 딕셔너리에 월별 금액 매핑
        return budgets # 결과 반환