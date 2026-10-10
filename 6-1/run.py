#!/usr/bin/env python3
"""
스마트 도서관 대여 관리 시스템 (Smart Library Management System)
실행 및 결과 자동 생성 스크립트 (run.py)
=============================================================================
이 스크립트는 다음 작업을 전자동으로 수행합니다:
1. SQLite DB (library.db) 초기화 및 01_schema.sql 적용
2. 02_sample_data.sql 샘플 데이터 적재
3. 03_queries.sql의 핵심 16개 쿼리 및 보너스 쿼리 3개 실행
4. 각 쿼리별 실행 결과를 results/ 폴더에 개별 텍스트 파일 및 종합 리포트로 저장
5. Pillow(PIL)를 활용하여 시각적 ERD 다이어그램(erd_diagram.png) 생성
"""

import os
import sys
import sqlite3
import datetime
from typing import List, Tuple, Any

DB_PATH = os.path.join(os.path.dirname(__file__), "library.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "01_schema.sql")
DATA_PATH = os.path.join(os.path.dirname(__file__), "02_sample_data.sql")
RESULTS_DIR = os.path.join(os.path.dirname(__file__), "results")


def format_table(headers: List[str], rows: List[Tuple[Any, ...]]) -> str:
    """ASCII 테이블 형태로 깔끔하게 포맷팅"""
    if not headers and not rows:
        return "(결과 없음 / 빈 집합)"

    col_widths = [len(str(h)) for h in headers]
    for row in rows:
        for idx, val in enumerate(row):
            val_str = str(val) if val is not None else "NULL"
            if len(val_str) > col_widths[idx]:
                col_widths[idx] = len(val_str)

    # 헤더 라인
    header_line = " | ".join(f"{h:<{col_widths[i]}}" for i, h in enumerate(headers))
    separator = "-+-".join("-" * col_widths[i] for i in range(len(headers)))

    data_lines = []
    for row in rows:
        row_str = " | ".join(
            f"{str(val) if val is not None else 'NULL':<{col_widths[i]}}"
            for i, val in enumerate(row)
        )
        data_lines.append(row_str)

    return f"{header_line}\n{separator}\n" + "\n".join(data_lines)


def setup_database():
    """DB 초기화 및 스키마, 샘플 데이터 로드"""
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
        except Exception:
            pass

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    conn.executescript(schema_sql)

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        data_sql = f.read()
    conn.executescript(data_sql)

    conn.commit()
    conn.close()
    print("[1/3] 데이터베이스 초기화 및 샘플 데이터 로드 완료! (library.db)")


QUERIES = [
    {
        "id": "q01",
        "title": "Q01. IT/과학 카테고리 중 20,000원 이상 고가 도서 목록 조회",
        "purpose": "특정 분류 내 고가 전문서적 필터링 및 가격 기준 정렬 확인",
        "category": "기본 조회",
        "sql": """
SELECT 
    book_id,
    title,
    author,
    price,
    stock_quantity
FROM book
WHERE category_id = 4 AND price >= 20000
ORDER BY price DESC;
"""
    },
    {
        "id": "q02",
        "title": "Q02. 2024년 이후 가입한 VIP/GOLD 등급 회원 상위 5명 조회",
        "purpose": "신규 가입자 중 VIP/GOLD 등급 프로모션 대상자 선별 및 다중 조건 필터링 확인",
        "category": "기본 조회",
        "sql": """
SELECT 
    member_id,
    name,
    email,
    membership_tier,
    join_date
FROM member
WHERE join_date >= '2024-01-01' 
  AND membership_tier IN ('VIP', 'GOLD')
ORDER BY join_date ASC
LIMIT 5;
"""
    },
    {
        "id": "q03",
        "title": "Q03. 현재 대여 중인 도서 중 반납예정일 임박 상위 5건 조회",
        "purpose": "반납 안내 알림 발송을 위해 마감 기한이 얼마 남지 않은 대여 건 우선 추출",
        "category": "기본 조회",
        "sql": """
SELECT 
    rental_id,
    member_id,
    book_id,
    rental_date,
    due_date,
    status
FROM rental
WHERE status = 'RENTED'
ORDER BY due_date ASC
LIMIT 5;
"""
    },
    {
        "id": "q04",
        "title": "Q04. 최신 출판년도순 도서 페이징 조회 (3건 건너뛰고 3건 조회)",
        "purpose": "웹/앱 서비스 페이징 처리를 위한 LIMIT과 OFFSET 동작 확인",
        "category": "기본 조회",
        "sql": """
SELECT 
    book_id,
    title,
    author,
    publish_year,
    price
FROM book
ORDER BY publish_year DESC, title ASC
LIMIT 3 OFFSET 3;
"""
    },
    {
        "id": "q05",
        "title": "Q05. [INNER JOIN] 대여 중인 도서와 대여 회원 및 카테고리 상세 정보 종합 조회",
        "purpose": "4개 테이블(rental, member, book, category)을 조인하여 대출 실황의 종합 상세 정보 확인",
        "category": "조인 쿼리",
        "sql": """
SELECT 
    r.rental_id,
    m.name AS member_name,
    m.membership_tier,
    b.title AS book_title,
    c.category_name,
    r.rental_date,
    r.due_date
FROM rental r
INNER JOIN member m ON r.member_id = m.member_id
INNER JOIN book b ON r.book_id = b.book_id
INNER JOIN category c ON b.category_id = c.category_id
WHERE r.status = 'RENTED'
ORDER BY r.due_date ASC;
"""
    },
    {
        "id": "q06",
        "title": "Q06. [INNER JOIN] 도서별 카테고리 및 총 재고 자산 가치(가격 * 재고량) 계산 조회",
        "purpose": "1:N 관계 조인과 수치 연산 컬럼을 조합하여 도서관 자산 가치 평가",
        "category": "조인 쿼리",
        "sql": """
SELECT 
    b.book_id,
    b.title,
    c.category_name,
    b.price,
    b.stock_quantity,
    (b.price * b.stock_quantity) AS total_inventory_value
FROM book b
INNER JOIN category c ON b.category_id = c.category_id
ORDER BY total_inventory_value DESC;
"""
    },
    {
        "id": "q07",
        "title": "Q07. [LEFT JOIN] 전체 도서 목록과 도서별 누적 대여 횟수 집계 (미대여 도서 포함)",
        "purpose": "대여 이력이 없는 비인기 도서도 누락되지 않고 0건으로 조회되는 LEFT JOIN의 특성 확인",
        "category": "조인 쿼리",
        "sql": """
SELECT 
    b.book_id,
    b.title,
    b.author,
    COUNT(r.rental_id) AS rental_count
FROM book b
LEFT JOIN rental r ON b.book_id = r.book_id
GROUP BY b.book_id, b.title, b.author
ORDER BY rental_count DESC, b.book_id ASC;
"""
    },
    {
        "id": "q08",
        "title": "Q08. [LEFT JOIN] 전체 회원 목록과 현재 대여 중인 도서 목록 조회 (미대여 회원 포함)",
        "purpose": "전체 회원 중 현재 도서를 대출 중인 회원과 대출하지 않은 회원을 한눈에 파악",
        "category": "조인 쿼리",
        "sql": """
SELECT 
    m.member_id,
    m.name AS member_name,
    m.membership_tier,
    COALESCE(b.title, '(대여 중인 도서 없음)') AS currently_rented_book,
    r.due_date
FROM member m
LEFT JOIN rental r ON m.member_id = r.member_id AND r.status = 'RENTED'
LEFT JOIN book b ON r.book_id = b.book_id
ORDER BY m.member_id ASC;
"""
    },
    {
        "id": "q09",
        "title": "Q09. [집계] 카테고리별 등록 도서 수, 평균 가격, 최고/최저 가격 통계 집계",
        "purpose": "다중 집계 함수(COUNT, AVG, MAX, MIN)와 GROUP BY를 활용한 카테고리별 분포 분석",
        "category": "집계 쿼리",
        "sql": """
SELECT 
    c.category_name,
    COUNT(b.book_id) AS book_count,
    ROUND(AVG(b.price), 0) AS avg_price,
    MAX(b.price) AS max_price,
    MIN(b.price) AS min_price
FROM category c
INNER JOIN book b ON c.category_id = b.category_id
GROUP BY c.category_id, c.category_name
ORDER BY book_count DESC, avg_price DESC;
"""
    },
    {
        "id": "q10",
        "title": "Q10. [집계] 회원 등급별 회원 수 및 총 대여 건수 집계 (대여 3건 이상 등급만 HAVING 필터링)",
        "purpose": "집계 후 조건 필터링을 위한 HAVING 절의 동작 원리 확인",
        "category": "집계 쿼리",
        "sql": """
SELECT 
    m.membership_tier,
    COUNT(DISTINCT m.member_id) AS member_count,
    COUNT(r.rental_id) AS total_rentals
FROM member m
LEFT JOIN rental r ON m.member_id = r.member_id
GROUP BY m.membership_tier
HAVING total_rentals >= 3
ORDER BY total_rentals DESC;
"""
    },
    {
        "id": "q11",
        "title": "Q11. [집계] 월별 도서 대여 건수 추이 및 상태별(반납/대여중/연체) 건수 분석",
        "purpose": "날짜 함수(strftime)와 조건부 집계(CASE WHEN)를 결합한 월별 비즈니스 트렌드 분석",
        "category": "집계 쿼리",
        "sql": """
SELECT 
    strftime('%Y-%m', rental_date) AS rental_month,
    COUNT(*) AS total_rentals,
    SUM(CASE WHEN status = 'RETURNED' THEN 1 ELSE 0 END) AS returned_count,
    SUM(CASE WHEN status = 'RENTED' THEN 1 ELSE 0 END) AS active_rental_count,
    SUM(CASE WHEN status = 'OVERDUE' THEN 1 ELSE 0 END) AS overdue_count
FROM rental
GROUP BY strftime('%Y-%m', rental_date)
ORDER BY rental_month ASC;
"""
    },
    {
        "id": "q12",
        "title": "Q12. [서브쿼리] 가입 이후 한 번도 도서를 대여하지 않은 비활성 회원 조회",
        "purpose": "NOT IN / NOT EXISTS 서브쿼리를 통한 비활성/휴면 회원 마케팅 타겟 추출",
        "category": "서브쿼리",
        "sql": """
SELECT 
    member_id,
    name,
    email,
    membership_tier,
    join_date
FROM member
WHERE member_id NOT IN (
    SELECT DISTINCT member_id 
    FROM rental
)
ORDER BY member_id ASC;
"""
    },
    {
        "id": "q13",
        "title": "Q13. [서브쿼리] 전체 도서의 평균 정가보다 비싼 고가 도서 목록 조회",
        "purpose": "WHERE 절 내 집계 연산 서브쿼리를 통한 동적 기준치 초과 데이터 필터링",
        "category": "서브쿼리",
        "sql": """
SELECT 
    book_id,
    title,
    author,
    price,
    (SELECT ROUND(AVG(price), 0) FROM book) AS overall_avg_price
FROM book
WHERE price > (SELECT AVG(price) FROM book)
ORDER BY price DESC;
"""
    },
    {
        "id": "q14",
        "title": "Q14. [UPDATE] 반납예정일이 2024-04-10 이전인 미반납 건을 'OVERDUE'(연체)로 일괄 갱신",
        "purpose": "대여 기한 초과 건에 대한 배치성 상태 갱신 작업 확인",
        "category": "데이터 수정",
        "is_write": True,
        "sql": """
UPDATE rental
SET status = 'OVERDUE'
WHERE status = 'RENTED' 
  AND due_date < '2024-04-10'
  AND return_date IS NULL;
""",
        "verify_sql": """
SELECT rental_id, member_id, book_id, due_date, status 
FROM rental 
WHERE status = 'OVERDUE';
"""
    },
    {
        "id": "q15",
        "title": "Q15. [DELETE] 대여 및 리뷰 이력이 전혀 없는 미활동 회원(member_id=11) 안전 삭제",
        "purpose": "외래키 참조 무결성을 위반하지 않는 안전한 조건부 레코드 삭제 확인",
        "category": "데이터 삭제",
        "is_write": True,
        "sql": """
DELETE FROM member
WHERE member_id = 11
  AND member_id NOT IN (SELECT DISTINCT member_id FROM rental)
  AND member_id NOT IN (SELECT DISTINCT member_id FROM review);
""",
        "verify_sql": """
SELECT member_id, name, email FROM member WHERE member_id = 11;
"""
    },
    {
        "id": "q16",
        "title": "Q16. [INDEX] 대여 상태 및 반납예정일 복합 인덱스 생성 및 실행 계획(EXPLAIN QUERY PLAN) 확인",
        "purpose": "대용량 테이블에서 빈번한 조건 조회의 성능 극대화를 위한 복합 인덱스 적용 및 최적화 확인",
        "category": "인덱스 최적화",
        "is_write": True,
        "sql": """
CREATE INDEX IF NOT EXISTS idx_rental_status_due_date 
ON rental(status, due_date);

CREATE INDEX IF NOT EXISTS idx_book_category_id 
ON book(category_id);
""",
        "verify_sql": """
EXPLAIN QUERY PLAN
SELECT * FROM rental 
WHERE status = 'RENTED' AND due_date < '2024-04-20';
"""
    }
]


def run_all_queries():
    """모든 쿼리 실행 및 파일 저장"""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON;")
    cur = conn.cursor()

    all_results_content = []
    all_results_content.append("=" * 80)
    all_results_content.append("스마트 도서관 대여 관리 시스템 - 핵심 SQL 쿼리 전체 실행 결과 리포트")
    all_results_content.append(f"생성 일시: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    all_results_content.append("=" * 80 + "\n")

    for q in QUERIES:
        q_id = q["id"]
        q_title = q["title"]
        q_purpose = q["purpose"]
        sql = q["sql"].strip()

        result_text_lines = []
        result_text_lines.append(f"[{q_title}]")
        result_text_lines.append(f"- 확인 목적: {q_purpose}")
        result_text_lines.append("\n[실행 SQL 문]:")
        result_text_lines.append(sql)
        result_text_lines.append("\n[실행 결과]:")

        if q.get("is_write"):
            # UPDATE, DELETE, CREATE INDEX
            cur.executescript(sql)
            conn.commit()
            verify_sql = q.get("verify_sql", "").strip()
            if verify_sql:
                result_text_lines.append(f">> 작업 수행 완료! 검증 쿼리 실행 결과:")
                cur.execute(verify_sql)
                headers = [desc[0] for desc in cur.description] if cur.description else []
                rows = cur.fetchall()
                tbl_str = format_table(headers, rows)
                result_text_lines.append(tbl_str)
                result_text_lines.append(f"(영향을 받은/조회된 행 수: {len(rows)}개)")
        else:
            cur.execute(sql)
            headers = [desc[0] for desc in cur.description] if cur.description else []
            rows = cur.fetchall()
            tbl_str = format_table(headers, rows)
            result_text_lines.append(tbl_str)
            result_text_lines.append(f"(조회된 총 행 수: {len(rows)}개)")

        result_str = "\n".join(result_text_lines)
        single_path = os.path.join(RESULTS_DIR, f"{q_id}_result.txt")
        with open(single_path, "w", encoding="utf-8") as f:
            f.write(result_str + "\n")

        all_results_content.append(result_str)
        all_results_content.append("\n" + "-" * 80 + "\n")

    # =========================================================================
    # 보너스 과제 1: 조인 vs 서브쿼리 비교
    # =========================================================================
    bonus1_lines = []
    bonus1_lines.append("[보너스 1] 동일한 요구사항을 JOIN과 서브쿼리 2가지 방식으로 풀고 실행 계획 비교")
    bonus1_lines.append("- 요구사항: '한 번이라도 리뷰를 작성한 적이 있는 회원 목록 조회'")
    
    sql_join = """
SELECT DISTINCT m.member_id, m.name, m.membership_tier
FROM member m
INNER JOIN review r ON m.member_id = r.member_id
ORDER BY m.member_id ASC;
"""
    cur.execute(sql_join)
    rows_join = cur.fetchall()
    headers_join = [desc[0] for desc in cur.description]
    bonus1_lines.append("\n1) 방식 A [INNER JOIN + DISTINCT]:")
    bonus1_lines.append(sql_join.strip())
    bonus1_lines.append(format_table(headers_join, rows_join))

    sql_sub = """
SELECT m.member_id, m.name, m.membership_tier
FROM member m
WHERE EXISTS (
    SELECT 1 FROM review r WHERE r.member_id = m.member_id
)
ORDER BY m.member_id ASC;
"""
    cur.execute(sql_sub)
    rows_sub = cur.fetchall()
    headers_sub = [desc[0] for desc in cur.description]
    bonus1_lines.append("\n2) 방식 B [WHERE EXISTS 서브쿼리]:")
    bonus1_lines.append(sql_sub.strip())
    bonus1_lines.append(format_table(headers_sub, rows_sub))

    bonus1_lines.append("\n3) 실행 계획(EXPLAIN QUERY PLAN) 비교 및 분석:")
    cur.execute(f"EXPLAIN QUERY PLAN {sql_join}")
    bonus1_lines.append(">> 방식 A 실행 계획:")
    bonus1_lines.append(format_table([d[0] for d in cur.description], cur.fetchall()))
    cur.execute(f"EXPLAIN QUERY PLAN {sql_sub}")
    bonus1_lines.append(">> 방식 B 실행 계획:")
    bonus1_lines.append(format_table([d[0] for d in cur.description], cur.fetchall()))
    bonus1_lines.append("""
[비교 해설]:
- 방식 A (JOIN + DISTINCT): review 테이블 전체와 조인 후 발생하는 중복 회원을 제거하기 위해
  추가적인 정렬 및 중복 제거(DISTINCT/B-TREE 정렬) 오버헤드가 발생합니다.
- 방식 B (WHERE EXISTS): 한 회원이 리뷰를 여러 개 작성했더라도, 첫 번째 일치하는 리뷰를
  찾는 즉시 서브쿼리가 참(True)으로 단락 평가(Short-circuit evaluation)되므로
  불필요한 임시 집합 생성과 중복 제거 비용이 없어 대용량 데이터에서 성능상 훨씬 유리합니다.
""")
    b1_str = "\n".join(bonus1_lines)
    with open(os.path.join(RESULTS_DIR, "bonus1_join_vs_subquery.txt"), "w", encoding="utf-8") as f:
        f.write(b1_str + "\n")
    all_results_content.append(b1_str)
    all_results_content.append("\n" + "-" * 80 + "\n")

    # =========================================================================
    # 보너스 과제 2: 데이터 정합성 깨뜨려 보기 (FK 위반 시도)
    # =========================================================================
    bonus2_lines = []
    bonus2_lines.append("[보너스 2] 외래키(FK) 참조 무결성 제약조건 위반 실험")
    bonus2_lines.append("- 실험 내용: 부모 테이블(member)에 존재하지 않는 회원(member_id = 9999)으로 대여(rental) 삽입 시도")
    fk_test_sql = """
INSERT INTO rental (member_id, book_id, rental_date, due_date, status)
VALUES (9999, 1, '2024-04-20', '2024-05-04', 'RENTED');
"""
    bonus2_lines.append("\n[시도한 SQL]:")
    bonus2_lines.append(fk_test_sql.strip())
    try:
        cur.execute(fk_test_sql)
        conn.commit()
        bonus2_lines.append("\n[결과]: 에러 미발생 (실패)")
    except sqlite3.IntegrityError as e:
        bonus2_lines.append(f"\n[발생한 실제 DB 엔진 에러]:\n>> sqlite3.IntegrityError: {e}")
        bonus2_lines.append("""
[원인 분석]:
- rental 테이블의 member_id 컬럼에는 FOREIGN KEY (member_id) REFERENCES member(member_id)
  제약조건이 걸려 있습니다.
- DB 엔진은 데이터를 삽입하기 전, 부모 테이블인 member에 member_id = 9999 레코드가
  실제로 존재하는지 검사합니다.
- 존재하지 않는 유령 회원의 ID를 참조하려고 하였으므로 참조 무결성(Referential Integrity)을
  지키기 위해 DB 엔진 차원에서 삽입을 거부하고 에러를 발생시킵니다.

[해결 방법]:
1. 부모 테이블(member)에 member_id = 9999 회원을 먼저 INSERT하여 생성하거나,
2. 실제로 등록되어 있는 올바른 회원의 ID(예: 1~12)를 지정하여 INSERT해야 합니다.
""")
    b2_str = "\n".join(bonus2_lines)
    with open(os.path.join(RESULTS_DIR, "bonus2_foreign_key_violation.txt"), "w", encoding="utf-8") as f:
        f.write(b2_str + "\n")
    all_results_content.append(b2_str)
    all_results_content.append("\n" + "-" * 80 + "\n")

    # =========================================================================
    # 보너스 과제 3: 핵심 비즈니스 지표 3개 미니 리포트
    # =========================================================================
    bonus3_lines = []
    bonus3_lines.append("[보너스 3] 도서관 핵심 비즈니스 지표 3종 미니 리포트")
    
    # 지표 1: 가장 인기 있는 도서 TOP 5
    m1_sql = """
SELECT 
    b.title,
    b.author,
    c.category_name,
    COUNT(r.rental_id) AS total_rentals,
    ROUND(AVG(rv.rating), 1) AS avg_rating
FROM book b
INNER JOIN category c ON b.category_id = c.category_id
LEFT JOIN rental r ON b.book_id = r.book_id
LEFT JOIN review rv ON b.book_id = rv.book_id
GROUP BY b.book_id, b.title, b.author, c.category_name
ORDER BY total_rentals DESC, avg_rating DESC
LIMIT 5;
"""
    cur.execute(m1_sql)
    bonus3_lines.append("\n[지표 1] 가장 인기 있는 도서 TOP 5 (대여 횟수 및 평균 평점):")
    bonus3_lines.append(format_table([d[0] for d in cur.description], cur.fetchall()))

    # 지표 2: 회원별 독서량 및 우수 고객 TOP 5
    m2_sql = """
SELECT 
    m.member_id,
    m.name,
    m.membership_tier,
    COUNT(r.rental_id) AS rental_count,
    COUNT(rv.review_id) AS review_count
FROM member m
LEFT JOIN rental r ON m.member_id = r.member_id
LEFT JOIN review rv ON m.member_id = rv.member_id
GROUP BY m.member_id, m.name, m.membership_tier
ORDER BY rental_count DESC, review_count DESC
LIMIT 5;
"""
    cur.execute(m2_sql)
    bonus3_lines.append("\n[지표 2] 회원별 독서량 및 우수 고객 랭킹 TOP 5:")
    bonus3_lines.append(format_table([d[0] for d in cur.description], cur.fetchall()))

    # 지표 3: 전체 대여 현황 및 연체율
    m3_sql = """
SELECT 
    COUNT(*) AS total_rentals,
    SUM(CASE WHEN status = 'RETURNED' THEN 1 ELSE 0 END) AS returned_count,
    SUM(CASE WHEN status = 'RENTED' THEN 1 ELSE 0 END) AS active_count,
    SUM(CASE WHEN status = 'OVERDUE' THEN 1 ELSE 0 END) AS overdue_count,
    ROUND(
        (CAST(SUM(CASE WHEN status = 'OVERDUE' THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*)) * 100, 
        2
    ) || '%' AS overdue_rate_percentage
FROM rental;
"""
    cur.execute(m3_sql)
    bonus3_lines.append("\n[지표 3] 전체 대여 현황 및 연체율(Overdue Rate) 지표:")
    bonus3_lines.append(format_table([d[0] for d in cur.description], cur.fetchall()))

    b3_str = "\n".join(bonus3_lines)
    with open(os.path.join(RESULTS_DIR, "bonus3_business_metrics_report.txt"), "w", encoding="utf-8") as f:
        f.write(b3_str + "\n")
    all_results_content.append(b3_str)

    # 전체 종합 리포트 저장
    all_report_path = os.path.join(RESULTS_DIR, "all_query_results.txt")
    with open(all_report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(all_results_content) + "\n")

    conn.close()
    print(f"[2/3] 16개 핵심 쿼리 및 3개 보너스 쿼리 실행 완료! (results/ 폴더 저장 완료)")


def generate_erd_image():
    """Pillow를 활용하여 깔끔한 ERD 다이어그램 이미지 (erd_diagram.png) 생성"""
    try:
        from PIL import Image, ImageDraw, ImageFont

        width, height = 1200, 800
        image = Image.new("RGB", (width, height), color="#F8FAFC")
        draw = ImageDraw.Draw(image)

        # 시스템 폰트 로드 시도
        try:
            title_font = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 26)
            header_font = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 18)
            body_font = ImageFont.truetype("/System/Library/Fonts/AppleSDGothicNeo.ttc", 14)
        except Exception:
            title_font = header_font = body_font = ImageFont.load_default()

        # 상단 타이틀
        draw.rectangle([(0, 0), (width, 70)], fill="#1E293B")
        draw.text((40, 20), "Smart Library Management System - ERD (Entity Relationship Diagram)", fill="#FFFFFF", font=title_font)

        # 테이블 박스 정의 (x, y, w, h, table_name, columns, header_color)
        tables = [
            {
                "name": "category (카테고리)",
                "color": "#3B82F6",
                "x": 60, "y": 120, "w": 260, "h": 170,
                "cols": [
                    ("category_id", "INTEGER (PK)"),
                    ("category_name", "VARCHAR(50) (UQ)"),
                    ("description", "TEXT"),
                    ("created_at", "DATETIME")
                ]
            },
            {
                "name": "book (도서)",
                "color": "#10B981",
                "x": 460, "y": 120, "w": 280, "h": 270,
                "cols": [
                    ("book_id", "INTEGER (PK)"),
                    ("title", "VARCHAR(150) (NN)"),
                    ("author", "VARCHAR(100) (NN)"),
                    ("publisher", "VARCHAR(100)"),
                    ("publish_year", "INTEGER"),
                    ("price", "INTEGER (NN)"),
                    ("category_id", "INTEGER (FK)"),
                    ("stock_quantity", "INTEGER (NN)"),
                    ("created_at", "DATETIME")
                ]
            },
            {
                "name": "member (회원)",
                "color": "#8B5CF6",
                "x": 860, "y": 120, "w": 280, "h": 230,
                "cols": [
                    ("member_id", "INTEGER (PK)"),
                    ("name", "VARCHAR(50) (NN)"),
                    ("email", "VARCHAR(100) (UQ)"),
                    ("phone", "VARCHAR(20) (UQ)"),
                    ("membership_tier", "VARCHAR(20)"),
                    ("join_date", "DATE (NN)"),
                    ("created_at", "DATETIME")
                ]
            },
            {
                "name": "rental (대여 기록)",
                "color": "#F59E0B",
                "x": 460, "y": 480, "w": 280, "h": 240,
                "cols": [
                    ("rental_id", "INTEGER (PK)"),
                    ("member_id", "INTEGER (FK)"),
                    ("book_id", "INTEGER (FK)"),
                    ("rental_date", "DATE (NN)"),
                    ("due_date", "DATE (NN)"),
                    ("return_date", "DATE"),
                    ("status", "VARCHAR(20) (NN)"),
                    ("created_at", "DATETIME")
                ]
            },
            {
                "name": "review (도서 리뷰)",
                "color": "#EC4899",
                "x": 860, "y": 480, "w": 280, "h": 220,
                "cols": [
                    ("review_id", "INTEGER (PK)"),
                    ("member_id", "INTEGER (FK)"),
                    ("book_id", "INTEGER (FK)"),
                    ("rating", "INTEGER (NN)"),
                    ("comment", "TEXT"),
                    ("review_date", "DATE"),
                    ("created_at", "DATETIME")
                ]
            }
        ]

        # 테이블 그리기
        for t in tables:
            x, y, w, h = t["x"], t["y"], t["w"], t["h"]
            # 본체 그림자 & 배경
            draw.rectangle([(x + 3, y + 3), (x + w + 3, y + h + 3)], fill="#CBD5E1")
            draw.rectangle([(x, y), (x + w, y + h)], fill="#FFFFFF", outline="#94A3B8", width=2)
            # 헤더
            draw.rectangle([(x, y), (x + w, y + 38)], fill=t["color"])
            draw.text((x + 12, y + 8), t["name"], fill="#FFFFFF", font=header_font)

            # 컬럼 목록
            cur_y = y + 48
            for col, col_type in t["cols"]:
                draw.text((x + 12, cur_y), col, fill="#1E293B", font=body_font)
                draw.text((x + w - 110, cur_y), col_type, fill="#64748B", font=body_font)
                cur_y += 22

        # 관계 선(1:N) 그리기
        # 1. category(1) -> book(N)
        draw.line([(320, 200), (460, 200)], fill="#3B82F6", width=3)
        draw.text((330, 180), "1 : N", fill="#1E40AF", font=body_font)

        # 2. book(1) -> rental(N)
        draw.line([(600, 390), (600, 480)], fill="#10B981", width=3)
        draw.text((610, 425), "1 : N", fill="#065F46", font=body_font)

        # 3. member(1) -> rental(N)
        draw.line([(860, 260), (740, 520)], fill="#8B5CF6", width=3)
        draw.text((790, 360), "1 : N", fill="#5B21B6", font=body_font)

        # 4. member(1) -> review(N)
        draw.line([(1000, 350), (1000, 480)], fill="#8B5CF6", width=3)
        draw.text((1010, 410), "1 : N", fill="#5B21B6", font=body_font)

        # 5. book(1) -> review(N)
        draw.line([(740, 300), (860, 520)], fill="#EC4899", width=2)
        draw.text((790, 430), "1 : N", fill="#9D174D", font=body_font)

        erd_path = os.path.join(os.path.dirname(__file__), "erd_diagram.png")
        image.save(erd_path)
        print(f"[3/3] ERD 다이어그램 생성 완료! ({erd_path})")
    except Exception as e:
        print(f"[3/3] ERD 다이어그램 생성 건너뜀 (이미지 라이브러리 예외: {e})")


def main():
    print("================================================================================")
    print("       스마트 도서관 데이터베이스 실습 전자동 실행기 (run.py)       ")
    print("================================================================================")
    setup_database()
    run_all_queries()
    generate_erd_image()
    print("\n>> 모든 과제 산출물이 성공적으로 생성되었습니다! <<")
    print(f">> 결과 폴더 확인: {RESULTS_DIR}")


if __name__ == "__main__":
    main()
