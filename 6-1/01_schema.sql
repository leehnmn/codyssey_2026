-- ============================================================================
-- 과제: 스마트 도서관 대여 관리 시스템 (Smart Library Management System)
-- 파일명: 01_schema.sql
-- 설명: 데이터베이스 테이블 스키마 정의 (PK, FK, 제약조건, 1:N 관계)
-- DB 환경: SQLite 3 (표준 SQL 준수)
-- ============================================================================

-- 1. 외래키(Foreign Key) 활성화 (SQLite 필수 설정)
PRAGMA foreign_keys = ON;

-- 2. 기존 테이블 삭제 (참조 무결성 역순 삭제)
DROP TABLE IF EXISTS review;
DROP TABLE IF EXISTS rental;
DROP TABLE IF EXISTS book;
DROP TABLE IF EXISTS member;
DROP TABLE IF EXISTS category;

-- ============================================================================
-- 테이블 1: category (도서 카테고리)
-- ============================================================================
CREATE TABLE category (
    category_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name   VARCHAR(50) NOT NULL UNIQUE,       -- 카테고리명 중복 방지 (UNIQUE)
    description     TEXT,                              -- 카테고리 설명
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP -- 생성일시
);

-- ============================================================================
-- 테이블 2: member (도서관 회원)
-- ============================================================================
CREATE TABLE member (
    member_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    name            VARCHAR(50) NOT NULL,              -- 회원 이름 (NOT NULL)
    email           VARCHAR(100) NOT NULL UNIQUE,      -- 로그인/연락용 이메일 (UNIQUE)
    phone           VARCHAR(20) NOT NULL UNIQUE,       -- 연락처 (UNIQUE)
    membership_tier VARCHAR(20) NOT NULL DEFAULT 'STANDARD' -- 회원 등급
                    CHECK (membership_tier IN ('STANDARD', 'SILVER', 'GOLD', 'VIP')),
    join_date       DATE NOT NULL,                     -- 가입일자
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- 테이블 3: book (도서 정보)
-- 관계: category (1) : book (N)
-- ============================================================================
CREATE TABLE book (
    book_id         INTEGER PRIMARY KEY AUTOINCREMENT,
    title           VARCHAR(150) NOT NULL,             -- 도서 제목
    author          VARCHAR(100) NOT NULL,             -- 저자
    publisher       VARCHAR(100) NOT NULL,             -- 출판사
    publish_year    INTEGER NOT NULL CHECK (publish_year >= 1900), -- 출판년도
    price           INTEGER NOT NULL CHECK (price >= 0),           -- 정가
    category_id     INTEGER NOT NULL,                  -- 카테고리 외래키
    stock_quantity  INTEGER NOT NULL DEFAULT 1 CHECK (stock_quantity >= 0), -- 보유 권수
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_book_category
        FOREIGN KEY (category_id) REFERENCES category(category_id)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

-- ============================================================================
-- 테이블 4: rental (도서 대여 기록)
-- 관계: member (1) : rental (N), book (1) : rental (N)
-- ============================================================================
CREATE TABLE rental (
    rental_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id       INTEGER NOT NULL,                  -- 대여 회원 외래키
    book_id         INTEGER NOT NULL,                  -- 대여 도서 외래키
    rental_date     DATE NOT NULL,                     -- 대여일
    due_date        DATE NOT NULL,                     -- 반납 예정일
    return_date     DATE,                              -- 실제 반납일 (NULL이면 대여 중)
    status          VARCHAR(20) NOT NULL DEFAULT 'RENTED' -- 대여 상태
                    CHECK (status IN ('RENTED', 'RETURNED', 'OVERDUE')),
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_rental_member
        FOREIGN KEY (member_id) REFERENCES member(member_id)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    CONSTRAINT fk_rental_book
        FOREIGN KEY (book_id) REFERENCES book(book_id)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

-- ============================================================================
-- 테이블 5: review (도서 리뷰 및 평점)
-- 관계: member (1) : review (N), book (1) : review (N)
-- ============================================================================
CREATE TABLE review (
    review_id       INTEGER PRIMARY KEY AUTOINCREMENT,
    member_id       INTEGER NOT NULL,                  -- 작성 회원 외래키
    book_id         INTEGER NOT NULL,                  -- 대상 도서 외래키
    rating          INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5), -- 별점 (1~5)
    comment         TEXT,                              -- 한줄 리뷰
    review_date     DATE NOT NULL DEFAULT CURRENT_DATE,
    created_at      DATETIME DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_review_member
        FOREIGN KEY (member_id) REFERENCES member(member_id)
        ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_review_book
        FOREIGN KEY (book_id) REFERENCES book(book_id)
        ON DELETE CASCADE ON UPDATE CASCADE
);
