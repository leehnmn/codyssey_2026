import argparse, sys, functools # CLI 파서 및 시스템, 데코레이터 도구 로드
from .storage import DataStorage # 저장소 모듈 로드
from .service import BudgetService # 서비스 모듈 로드

def cli_handler(func): # 공통 예외 처리 및 종료 코드(0: 정상, 1: 비정상) 제어 데코레이터
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try: return func(*args, **kwargs) # 본 함수 실행
        except Exception as e: # 오류 발생 시
            print(f"❌ 오류: {e}") # 사용자 친화적 오류 메시지 출력
            sys.exit(1) # 비정상 종료 코드(1) 반환
    return wrapper

def print_txs(txs): # 거래 목록 단순 콘솔 출력 함수
    if not txs: print("조회된 거래 내역이 없습니다."); return # 데이터 없음 처리
    print("-" * 75) # 구분선 출력
    print(f"{'ID':<10} | {'날짜':<12} | {'구분':<6} | {'카테고리':<8} | {'금액':>10} | {'메모'}") # 헤더 출력
    print("-" * 75) # 구분선 출력
    for t in txs: # 거래 순회
        tp = "수입" if t.type == "income" else "지출" # 타입 한글 변환
        print(f"{t.id:<10} | {t.date:<12} | {tp:<6} | {t.category:<8} | {t.amount:>10,}원 | {t.memo}") # 행 출력
    print("-" * 75) # 구분선 출력

@cli_handler
def main(): # 메인 CLI 구동 함수
    p = argparse.ArgumentParser(prog="python -m budget_app", description="개인 가계부 CLI") # 메인 파서
    p.add_argument("--data-dir", default="./data", help="데이터 저장 경로") # 저장 경로 옵션
    sub = p.add_subparsers(dest="cmd", help="명령어") # 서브 파서 모음

    sub.add_parser("add", help="거래 추가 (대화형)") # add 명령어 등록
    l_p = sub.add_parser("list", help="거래 목록"); l_p.add_argument("--limit", type=int, default=10) # list 명령어 등록
    s_p = sub.add_parser("search", help="거래 검색"); s_p.add_argument("--from", dest="f_date"); s_p.add_argument("--to", dest="t_date"); s_p.add_argument("--category"); s_p.add_argument("--type"); s_p.add_argument("--q"); s_p.add_argument("--tag") # search 등록
    sm_p = sub.add_parser("summary", help="월별 요약"); sm_p.add_argument("--month", required=True); sm_p.add_argument("--top", type=int, default=5) # summary 등록
    bg_p = sub.add_parser("budget", help="예산 관리"); bg_sub = bg_p.add_subparsers(dest="b_cmd"); bg_set = bg_sub.add_parser("set"); bg_set.add_argument("--month", required=True); bg_set.add_argument("--amount", type=int, required=True) # budget set 등록
    ct_p = sub.add_parser("category", help="카테고리"); ct_sub = ct_p.add_subparsers(dest="c_cmd"); ct_sub.add_parser("list"); c_add = ct_sub.add_parser("add"); c_add.add_argument("name"); c_rm = ct_sub.add_parser("remove"); c_rm.add_argument("name"); c_rm.add_argument("--fallback") # category 등록
    u_p = sub.add_parser("update", help="거래 수정 (대화형)"); u_p.add_argument("--id", required=True) # update 등록
    d_p = sub.add_parser("delete", help="거래 삭제"); d_p.add_argument("--id", required=True) # delete 등록
    im_p = sub.add_parser("import", help="CSV 가져오기"); im_p.add_argument("--from", dest="f_file", required=True) # import 등록
    ex_p = sub.add_parser("export", help="CSV 내보내기"); ex_p.add_argument("--out", required=True); ex_p.add_argument("--month"); ex_p.add_argument("--from", dest="f_date"); ex_p.add_argument("--to", dest="t_date") # export 등록

    args = p.parse_args() # 인자 파싱
    if not args.cmd: p.print_help(); return # 명령어가 없으면 도움말 출력
    svc = BudgetService(DataStorage(args.data_dir)) # 서비스 계층 인스턴스 초기화

    if args.cmd == "add": # add 대화형 실행
        d = input("날짜 (YYYY-MM-DD): ").strip() # 날짜 입력
        t = input("타입 (income/expense): ").strip() # 타입 입력
        c = input(f"카테고리 ({svc.storage.get_categories()}): ").strip() # 카테고리 입력
        a = int(input("금액: ").strip()) # 금액 입력
        m = input("메모 (선택): ").strip() # 메모 입력
        tg = [x.strip() for x in input("태그 (쉼표 구분): ").split(",") if x.strip()] # 태그 입력
        tx_id = svc.add_transaction(d, t, c, a, m, tg) # 저장 실행
        print(f"✅ 거래가 성공적으로 등록되었습니다. (ID: {tx_id})") # 결과 메시지

    elif args.cmd == "list": print_txs(svc.list_transactions(args.limit)) # 최신 목록 출력
    elif args.cmd == "search": print_txs(svc.search(args.f_date, args.t_date, args.category, args.type, args.q, args.tag)) # 검색 목록 출력
    elif args.cmd == "summary": # 월별 요약 출력
        r = svc.summary(args.month, args.top) # 집계 조회
        if r["count"] == 0: print(f"📊 [{args.month}] 데이터 없음"); return # 데이터 없음 처리
        print(f"📊 [{args.month} 요약] 수입: {r['income']:,}원 | 지출: {r['expense']:,}원 | 잔액: {r['balance']:,}원") # 통계 출력
        if r["budget"]: # 예산 설정이 있는 경우
            pct = (r["expense"] / r["budget"]) * 100 # 사용률 계산
            print(f" • 예산: {r['budget']:,}원 (사용률: {pct:.1f}%)" + (" ⚠️ 예산 초과!" if r["expense"] > r["budget"] else "")) # 경고 출력
        print(f"🏆 지출 TOP {len(r['top'])}: " + ", ".join([f"{c}: {a:,}원" for c, a in r["top"]])) # TOP 카테고리 출력

    elif args.cmd == "budget" and args.b_cmd == "set": # 예산 설정
        svc.storage.set_budget(args.month, args.amount); print(f"✅ [{args.month}] 예산 {args.amount:,}원 설정 완료")
    elif args.cmd == "category": # 카테고리 관리
        if args.c_cmd == "list": print("카테고리 목록:", svc.storage.get_categories()) # 목록
        elif args.c_cmd == "add": print("✅ 추가 완료" if svc.storage.add_category(args.name) else "⚠️ 이미 존재함") # 추가
        elif args.c_cmd == "remove": # 삭제
            ok, msg = svc.remove_category(args.name, args.fallback) # 삭제 실행
            if ok: print("✅ 삭제 완료") # 성공
            else: raise ValueError(msg) # 실패 시 예외 던짐

    elif args.cmd == "update": # update 대화형 실행
        print(f"수정할 거래 ID: {args.id} (변경하지 않을 항목은 Enter)") # 안내 문구
        d = input("새 날짜: ").strip() or None # 새 날짜
        t = input("새 타입(income/expense): ").strip() or None # 새 타입
        c = input("새 카테고리: ").strip() or None # 새 카테고리
        a_in = input("새 금액: ").strip(); a = int(a_in) if a_in else None # 새 금액
        m = input("새 메모: ").strip() or None # 새 메모
        if svc.update_transaction(args.id, date=d, type=t, category=c, amount=a, memo=m): print("✅ 수정 성공")
        else: raise ValueError(f"ID '{args.id}'를 찾을 수 없습니다.")

    elif args.cmd == "delete": # 거래 삭제
        if svc.delete_transaction(args.id): print("✅ 삭제 성공")
        else: raise ValueError(f"ID '{args.id}'를 찾을 수 없습니다.")

    elif args.cmd == "import": print(f"✅ {svc.import_csv(args.f_file)}건 가져오기 완료") # CSV 가져오기
    elif args.cmd == "export": print(f"✅ {svc.export_csv(args.out, args.month, args.f_date, args.t_date)}건 내보내기 완료") # CSV 내보내기