from dataclasses import dataclass, asdict, field # 데이터 클래스 및 딕셔너리 변환 도구 로드
from typing import List, Literal # 정적 타입 힌팅 도구 로드

# 거래 유형을 수입(income)과 지출(expense)로 엄격히 제한
TransactionType = Literal["income", "expense"]

@dataclass
class Transaction: # 거래 데이터 모델 정의
    id: str # 거래 고유 식별자 ID
    type: TransactionType # 수입/지출 구분
    date: str # 거래 일자 (YYYY-MM-DD 형식)
    amount: int # 거래 금액 (양수 정수)
    category: str # 등록된 카테고리명
    memo: str = "" # 메모 (선택 사항, 기본 빈 문자열)
    tags: List[str] = field(default_factory=list) # 태그 리스트 (선택 사항)

    def to_dict(self) -> dict: # 모델 인스턴스를 JSON 저장을 위한 딕셔너리로 변환
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "Transaction": # 딕셔너리 데이터를 받아 모델 인스턴스 생성
        return cls(
            id=data["id"], # ID 매핑
            type=data["type"], # 타입 매핑
            date=data["date"], # 날짜 매핑
            amount=int(data["amount"]), # 금액 매핑 (정수 보장)
            category=data["category"], # 카테고리 매핑
            memo=data.get("memo", ""), # 메모 매핑
            tags=data.get("tags", []), # 태그 목록 매핑
        )