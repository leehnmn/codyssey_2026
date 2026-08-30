import csv # CSV 가져오기/내보내기 라이브러리 로드
import uuid # 거래 고유 ID 생성 도구 로드
from collections import defaultdict # 카테고리별 합산 집계용 딕셔너리 로드
from typing import List, Optional, Dict, Any, Tuple # 타입 힌트 로드
from .models import Transaction # 거래 모델 로드
from .storage import DataStorage # 저장소 계층 로드

class BudgetService: # 비즈니스 로직 처리 계층
    def __init__(self, storage: DataStorage): # 저장소 주입
        self.storage = storage # 저장소 인스턴스 저장

    def add_transaction(self, date: str, tx_type: str, cat: str, amount: int, memo: str, tags: List[str]) -> str: # 거래 추가
        if cat not in self.storage.get_categories(): raise ValueError(f"'{cat}'은(는) 존재하지 않는 카테고리입니다.") # 카테고리 검증
        tx_id = uuid.uuid4().hex[:8] # 8자리 고유 ID 발급
        tx = Transaction(id=tx_id, type=tx_type, date=date, amount=amount, category=cat, memo=memo, tags=tags) # type: ignore
        self.storage.append_transaction(tx) # 영구 저장
        return tx_id # 생성된 거래 ID 반환

    def list_transactions(self, limit: int = 10) -> List[Transaction]: # 목록 최신순 조회
        txs = sorted(list(self.storage.stream_transactions()), key=lambda x: (x.date, x.id), reverse=True) # 최신순 정렬
        return txs[:limit] # limit 개수만큼 반환

    def search(self, f_date: Optional[str], t_date: Optional[str], cat: Optional[str], t_type: Optional[str], q: Optional[str], tag: Optional[str]) -> List[Transaction]: # 검색
        res = [] # 검색 결과 리스트
        for tx in self.storage.stream_transactions(): # 스트리밍 순회
            if f_date and tx.date < f_date: continue # 시작일 필터
            if t_date and tx.date > t_date: continue # 종료일 필터
            if cat and tx.category != cat: continue # 카테고리 필터
            if t_type and tx.type != t_type: continue # 타입 필터
            if q and (q.lower() not in tx.memo.lower()): continue # 메모 검색어 필터
            if tag and (tag not in tx.tags): continue # 태그 필터
            res.append(tx) # 조건 만족 시 추가
        return sorted(res, key=lambda x: (x.date, x.id), reverse=True) # 최신순 정렬 반환

    def summary(self, month: str, top_n: int = 5) -> Dict[str, Any]: # 월별 요약 통계
        inc, exp, cat_exp, cnt = 0, 0, defaultdict(int), 0 # 변수 초기화
        for tx in self.storage.stream_transactions(): # 스트리밍 집계
            if tx.date.startswith(month): # 해당 월 데이터만 처리
                cnt += 1 # 건수 증가
                if tx.type == "income": inc += tx.amount # 수입 합산
                elif tx.type == "expense": # 지출 합산 및 카테고리별 집계
                    exp += tx.amount; cat_exp[tx.category] += tx.amount
        top_cats = sorted(cat_exp.items(), key=lambda x: x[1], reverse=True)[:top_n] # TOP N 정렬
        return {"count": cnt, "income": inc, "expense": exp, "balance": inc - exp, "top": top_cats, "budget": self.storage.get_budgets().get(month)}

    def delete_transaction(self, tx_id: str) -> bool: # 거래 삭제
        all_tx = list(self.storage.stream_transactions()) # 전체 조회
        new_tx = [t for t in all_tx if t.id != tx_id] # 해당 ID 제외
        if len(all_tx) == len(new_tx): return False # 삭제 대상 없으면 실패
        self.storage.rewrite_transactions(new_tx) # 갱신 저장
        return True # 삭제 성공

    def update_transaction(self, tx_id: str, **kwargs) -> bool: # 거래 수정
        all_tx = list(self.storage.stream_transactions()) # 전체 조회
        for tx in all_tx:
            if tx.id == tx_id: # 대상 ID 발견 시
                for k, v in kwargs.items(): # 전달된 수정 필드 반영
                    if v is not None: setattr(tx, k, v)
                self.storage.rewrite_transactions(all_tx) # 저장소 반영
                return True # 수정 성공
        return False # ID 없으면 실패

    def remove_category(self, name: str, fallback: Optional[str]) -> Tuple[bool, str]: # 카테고리 삭제 (내역 확인)
        txs = list(self.storage.stream_transactions()) # 거래 내역 조회
        using = [t for t in txs if t.category == name] # 해당 카테고리 사용 거래 확인
        if using: # 사용 중인 내역이 있는 경우
            if not fallback: return False, f"'{name}' 사용 내역이 {len(using)}건 있습니다. 대체 카테고리(--fallback)를 지정하세요."
            for t in using: t.category = fallback # 대체 카테고리로 교체
            self.storage.rewrite_transactions(txs) # 거래 내역 갱신
        self.storage.remove_category(name) # 카테고리 파일에서 삭제
        return True, "삭제 완료"

    def export_csv(self, out_path: str, month: Optional[str], f_date: Optional[str], t_date: Optional[str]) -> int: # CSV 내보내기
        if not month and not (f_date and t_date): raise ValueError("--month 또는 (--from 과 --to) 조건이 필수입니다.") # 조건 검증
        txs = self.search(f_date or f"{month}-01", t_date or f"{month}-31", None, None, None, None) if month else self.search(f_date, t_date, None, None, None, None)
        with open(out_path, "w", newline="", encoding="utf-8") as f: # CSV 작성
            writer = csv.writer(f) # csv writer 생성
            writer.writerow(["date", "type", "category", "amount", "memo", "tags"]) # 헤더 작성
            for t in txs: writer.writerow([t.date, t.type, t.category, t.amount, t.memo, ",".join(t.tags)]) # 행 작성
        return len(txs) # 내보낸 행 수 반환

    def import_csv(self, file_path: str) -> int: # CSV 가져오기
        cats = set(self.storage.get_categories()) # 등록 카테고리 목록
        count = 0 # 가져온 건수 카운트
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f) # 딕셔너리 리더 생성
            for r in reader: # 각 줄 순회
                cat = r["category"].strip() # 카테고리 추출
                if cat not in cats: self.storage.add_category(cat); cats.add(cat) # 미등록 시 자동 추가
                tags = [t.strip() for t in r.get("tags", "").split(",") if t.strip()] # 태그 파싱
                self.storage.append_transaction(Transaction(uuid.uuid4().hex[:8], r["type"].strip(), r["date"].strip(), int(r["amount"]), cat, r.get("memo", "").strip(), tags)) # type: ignore
                count += 1 # 카운트 증가
        return count # 등록된 건수 반환