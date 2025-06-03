#!/usr/bin/env python3
import os
import logging

# 프로젝트 구조에 맞춰 import 경로를 조정하세요.
# 예시로, 프로젝트 루트에서 실행한다고 가정합니다.
from api_client import APIClient
from orders.order_manager import OrderManager
from db.db import init_db

def main():
    # 로깅 레벨 설정
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    # 환경변수에서 API 키/시크릿 읽어오기
    api_key     = os.getenv("KIS_API_KEY")
    app_secret  = os.getenv("KIS_APP_SECRET")

    if not api_key or not app_secret:
        print("❗️ 환경변수 KIS_API_KEY, KIS_APP_SECRET 를 설정한 후 다시 실행하세요.")
        return

    # (1) 데이터베이스 테이블이 아직 없으면 생성해 준다.
    init_db()

    # (2) OAuth 토큰 발급
    client = APIClient(api_key, app_secret)
    token = client.get_oauth_token()
    if not token:
        print("❌ 토큰 발급에 실패했습니다. 로그를 확인하세요.")
        return

    # (3) OrderManager 생성
    manager = OrderManager(api_key, app_secret, token)

    # ————————————————————————————————————————————————
    # (4) “절대로 체결되지 않을” 가격으로 매수 주문을 넣어본다.
    #     예시: 해외주식 코드가 "AAPL", 수량 1주, 가격을 1달러(너무 낮아서 체결 안 됨) 로 설정
    #     * 실제 계좌/거래소 코드(CANO, ACNT_PRDT_CD, OVRS_EXCG_CD) 는 사용자 환경에 맞게 수정해야 합니다.
    # ————————————————————————————————————————————————
    code       = "AAPL"         # 테스트용 종목 코드 (예시)
    name       = "Apple Inc."   # 종목명(로깅용)
    order_type = "신규매수"        # 사용자 정의 문자열 (DB 컬럼에는 크게 영향 없음)
    qty        = 1              # 매수 수량
    test_price = 1              # 시장가(체결가) 대비 너무 낮은 가격: 절대로 체결되지 않음

    order_id = manager.create_order(code, name, order_type, qty, test_price)
    if order_id:
        print(f"✅ 테스트 주문 생성됨 → order_id: {order_id}")
    else:
        print("❌ 테스트 주문 생성 실패")

    # (5) 세션 종료
    manager.close()


if __name__ == "__main__":
    main()
