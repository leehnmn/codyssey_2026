-- ============================================================================
-- 과제: 스마트 도서관 대여 관리 시스템 (Smart Library Management System)
-- 파일명: 03_queries.sql
-- 설명: 요구사항을 충족하는 핵심 SQL 쿼리 15개 + 인덱스 + 보너스 쿼리
-- 각 쿼리 상단에 "무엇을 확인하는 쿼리인지" 명시되어 있습니다.
-- ============================================================================

PRAGMA foreign_keys = ON;

-- ============================================================================
-- [카테고리 1] 기본 조회 쿼리 (WHERE, ORDER BY, LIMIT) - 4개
-- ============================================================================

-- Q01. 특정 카테고리(IT/과학)에 속하고 가격이 20,000원 이상인 도서 목록을 가격 내림차순으로 조회
-- [확인 목적]: 특정 분류 내 고가 전문서적 필터링 및 가격 기준 정렬 확인
SELECT 
    book_id,
    title,
    author,
    price,
    stock_quantity
FROM book
WHERE category_id = 4 AND price >= 20000
ORDER BY price DESC;

-- Q02. 2024년 이후 가입한 회원 중 우수 등급('VIP', 'GOLD') 회원 상위 5명을 가입일 오름차순으로 조회
-- [확인 목적]: 신규 가입자 중 VIP/GOLD 등급 프로모션 대상자 선별 및 다중 조건 필터링 확인
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

-- Q03. 현재 대여 중('RENTED')인 대여 건 중 반납예정일(due_date)이 가장 임박한 순서대로 상위 5건 조회
-- [확인 목적]: 반납 안내 알림 발송을 위해 마감 기한이 얼마 남지 않은 대여 건 우선 추출
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

-- Q04. 전체 도서 목록을 출판년도(최신순) 및 도서명(가나다순)으로 정렬하여 페이지네이션(3건씩 건너뛰어 3건 조회)
-- [확인 목적]: 웹/앱 서비스 페이징 처리를 위한 LIMIT과 OFFSET 동작 확인
SELECT 
    book_id,
    title,
    author,
    publish_year,
    price
FROM book
ORDER BY publish_year DESC, title ASC
LIMIT 3 OFFSET 3;


-- ============================================================================
-- [카테고리 2] 조인 쿼리 (INNER JOIN, LEFT JOIN) - 4개
-- ============================================================================

-- Q05. [INNER JOIN] 현재 대여 중인 도서의 대여ID, 회원 이름, 도서 제목, 카테고리명, 대여일자, 반납예정일 조회
-- [확인 목적]: 4개 테이블(rental, member, book, category)을 조인하여 대출 실황의 종합 상세 정보 확인
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

-- Q06. [INNER JOIN] 도서와 카테고리를 조인하여 도서별 분류명 및 총 재고 금액(price * stock_quantity) 계산 조회
-- [확인 목적]: 1:N 관계 조인과 수치 연산 컬럼을 조합하여 도서관 자산 가치 평가
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

-- Q07. [LEFT JOIN] 모든 도서 목록을 조회하고, 각 도서의 누적 대여 횟수를 집계 (한 번도 대여되지 않은 도서도 포함)
-- [확인 목적]: 대여 이력이 없는 비인기 도서도 누락되지 않고 0건으로 조회되는 LEFT JOIN의 특성 확인
SELECT 
    b.book_id,
    b.title,
    b.author,
    COUNT(r.rental_id) AS rental_count
FROM book b
LEFT JOIN rental r ON b.book_id = r.book_id
GROUP BY b.book_id, b.title, b.author
ORDER BY rental_count DESC, b.book_id ASC;

-- Q08. [LEFT JOIN] 모든 회원 목록과 각 회원이 현재 대여 중('RENTED')인 도서명을 함께 조회 (대여 중인 도서가 없는 회원 포함)
-- [확인 목적]: 전체 회원 중 현재 도서를 대출 중인 회원과 대출하지 않은 회원을 한눈에 파악
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


-- ============================================================================
-- [카테고리 3] 집계 쿼리 (COUNT, SUM, AVG, GROUP BY, HAVING) - 3개
-- ============================================================================

-- Q09. 카테고리별 등록 도서 수, 평균 도서 가격, 최고 가격, 최저 가격을 집계하여 도서 수 내림차순 정렬
-- [확인 목적]: 다중 집계 함수(COUNT, AVG, MAX, MIN)와 GROUP BY를 활용한 카테고리별 분포 분석
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

-- Q10. 회원 등급별 회원 수, 총 대여 건수 집계 및 총 대여 건수가 3건 이상인 등급만 필터링 (HAVING 사용)
-- [확인 목적]: 집계 후 조건 필터링을 위한 HAVING 절의 동작 원리 확인
SELECT 
    m.membership_tier,
    COUNT(DISTINCT m.member_id) AS member_count,
    COUNT(r.rental_id) AS total_rentals
FROM member m
LEFT JOIN rental r ON m.member_id = r.member_id
GROUP BY m.membership_tier
HAVING total_rentals >= 3
ORDER BY total_rentals DESC;

-- Q11. 월별 도서 대여 건수 및 반납 완료/진행중 건수 추이 집계
-- [확인 목적]: 날짜 함수(strftime)와 조건부 집계(CASE WHEN)를 결합한 월별 비즈니스 트렌드 분석
SELECT 
    strftime('%Y-%m', rental_date) AS rental_month,
    COUNT(*) AS total_rentals,
    SUM(CASE WHEN status = 'RETURNED' THEN 1 ELSE 0 END) AS returned_count,
    SUM(CASE WHEN status = 'RENTED' THEN 1 ELSE 0 END) AS active_rental_count,
    SUM(CASE WHEN status = 'OVERDUE' THEN 1 ELSE 0 END) AS overdue_count
FROM rental
GROUP BY strftime('%Y-%m', rental_date)
ORDER BY rental_month ASC;


-- ============================================================================
-- [카테고리 4] 서브쿼리 (Subquery) - 2개
-- ============================================================================

-- Q12. [다중 행 서브쿼리] 가입 이후 지금까지 단 한 번도 도서를 대여한 적이 없는 회원 목록 조회
-- [확인 목적]: NOT IN / NOT EXISTS 서브쿼리를 통한 비활성/휴면 회원 마케팅 타겟 추출
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

-- Q13. [단일 행 스칼라 서브쿼리] 전체 도서의 평균 정가보다 비싼 고가 도서 목록 조회
-- [확인 목적]: WHERE 절 내 집계 연산 서브쿼리를 통한 동적 기준치 초과 데이터 필터링
SELECT 
    book_id,
    title,
    author,
    price,
    (SELECT ROUND(AVG(price), 0) FROM book) AS overall_avg_price
FROM book
WHERE price > (SELECT AVG(price) FROM book)
ORDER BY price DESC;


-- ============================================================================
-- [카테고리 5] 데이터 수정 및 삭제 쿼리 (UPDATE, DELETE) - 2개
-- ============================================================================

-- Q14. [UPDATE] 반납예정일(due_date)이 2024-04-10 이전인데 아직 반납되지 않은 대여 건의 상태를 'OVERDUE'(연체)로 일괄 변경
-- [확인 목적]: 대여 기한 초과 건에 대한 배치성 상태 갱신 작업 확인
UPDATE rental
SET status = 'OVERDUE'
WHERE status = 'RENTED' 
  AND due_date < '2024-04-10'
  AND return_date IS NULL;

-- (Q14 검증 쿼리: 갱신된 연체 목록 확인)
SELECT rental_id, member_id, book_id, due_date, status 
FROM rental 
WHERE status = 'OVERDUE';

-- Q15. [DELETE] 대여 이력 및 리뷰가 전혀 없는 미활동 테스트 회원(임지훈, member_id = 11) 삭제
-- [확인 목적]: 외래키 참조 무결성을 위반하지 않는 안전한 조건부 레코드 삭제 확인
DELETE FROM member
WHERE member_id = 11
  AND member_id NOT IN (SELECT DISTINCT member_id FROM rental)
  AND member_id NOT IN (SELECT DISTINCT member_id FROM review);

-- (Q15 검증 쿼리: 삭제 후 회원 존재 여부 확인)
SELECT member_id, name, email FROM member WHERE member_id = 11;


-- ============================================================================
-- [카테고리 6] 인덱스 생성 및 적용 이유 (CREATE INDEX) - 1개 이상
-- ============================================================================

-- Q16. [INDEX] 대여 상태(status)와 반납예정일(due_date)을 결합한 복합 인덱스 생성 및 적용 이유
-- [적용 이유]:
-- 매일 자정 또는 실시간으로 실행되는 "연체 알림 및 연체 상태 업데이트" 작업은
-- WHERE status = 'RENTED' AND due_date < ? 조건을 가장 빈번하게 조회합니다.
-- 전체 대여 데이터가 수십만 건으로 증가할 경우 풀 테이블 스캔(Full Table Scan)을 방지하고,
-- 인덱스 레인지 스캔(Index Range Scan)으로 처리 속도를 O(log N)으로 비약적으로 향상시키기 위해 적용합니다.
CREATE INDEX IF NOT EXISTS idx_rental_status_due_date 
ON rental(status, due_date);

-- 카테고리별 도서 조회 및 조인 성능 향상을 위한 외래키 인덱스
CREATE INDEX IF NOT EXISTS idx_book_category_id 
ON book(category_id);

-- (Q16 실행 계획 검증: 인덱스 활용 여부 EXPLAIN QUERY PLAN으로 확인)
EXPLAIN QUERY PLAN
SELECT * FROM rental 
WHERE status = 'RENTED' AND due_date < '2024-04-20';


-- ============================================================================
-- [보너스 과제]
-- ============================================================================

-- 보너스 1: 조인 1개를 두 방식(JOIN vs 서브쿼리)으로 풀고 비교
-- 요구사항: "한 번이라도 리뷰를 작성한 적이 있는 회원 목록 조회"

-- 방식 A: INNER JOIN + DISTINCT 활용
SELECT DISTINCT 
    m.member_id, 
    m.name, 
    m.membership_tier
FROM member m
INNER JOIN review r ON m.member_id = r.member_id
ORDER BY m.member_id ASC;

-- 방식 B: 서브쿼리 (IN / EXISTS) 활용
SELECT 
    m.member_id, 
    m.name, 
    m.membership_tier
FROM member m
WHERE EXISTS (
    SELECT 1 FROM review r WHERE r.member_id = m.member_id
)
ORDER BY m.member_id ASC;

-- 보너스 2: 데이터 정합성 깨뜨려 보기 (FK 위반 시도)
-- 존재하지 않는 회원(member_id = 9999)으로 대여 기록을 삽입 시도 -> 에러 발생 유도!
-- INSERT INTO rental (member_id, book_id, rental_date, due_date, status)
-- VALUES (9999, 1, '2024-04-20', '2024-05-04', 'RENTED');
-- -> [결과]: Error: FOREIGN KEY constraint failed
-- -> [해설]: 부모 테이블(member)에 존재하지 않는 PK를 자식 테이블(rental)에서 참조하려 했으므로
--           외래키 참조 무결성(Referential Integrity) 규칙에 의해 DB 엔진이 삽입을 원천 차단함.

-- 보너스 3: 핵심 지표 3개 미니 리포트
-- 지표 1: 가장 인기 있는 도서 TOP 5 (누적 대여 횟수 랭킹)
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

-- 지표 2: 회원별 독서량 및 우수 고객 랭킹 TOP 5
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

-- 지표 3: 전체 대여 현황 및 연체율(Overdue Rate) 지표
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
