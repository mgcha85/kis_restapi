# src/db/db.py

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base, HoldList, OrderList, TradeHistory
from dotenv import load_dotenv

# .env 파일을 불러옵니다.
load_dotenv()  

# .env에서 개별 변수 읽어오기 (없다면 기본값 사용)
POSTGRES_USER     = os.getenv("POSTGRES_USER", "username")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
POSTGRES_DB       = os.getenv("POSTGRES_DB", "mydatabase")
POSTGRES_HOST     = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT     = os.getenv("POSTGRES_PORT", "5432")

# 만약 DATABASE_URL이 .env나 환경변수로 이미 정의되어 있으면 그것을 우선 사용
default_url = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
DATABASE_URL = os.getenv("DATABASE_URL", default_url)

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """
    데이터베이스에 테이블이 없으면 모두 생성합니다.
    """
    Base.metadata.create_all(bind=engine)


# -----------------------------
#  보유 생성/삭제, 매도 거래 기록 유틸리티
# -----------------------------
def create_hold_from_order(order):
    """
    OrderList 객체를 받아서 HoldList 레코드를 생성합니다.
    avg_price는 cum_price / qty로 계산합니다.
    """
    session = SessionLocal()
    try:
        avg_price = float(order.cum_price) / order.qty if order.qty else 0
        new_hold = HoldList(
            code=order.code,
            qty=order.qty,
            avg_price=int(avg_price),
            remain_qty=order.qty,
            order_id=order.order_id,
            num_buy=1,
            # buy_time 은 server_default current_timestamp로 자동 입력
        )
        session.add(new_hold)
        # 주문 상태를 '체결'로 업데이트
        order.status = "체결"
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_trade_from_hold_and_delete(hold, sell_price):
    """
    HoldList 객체를 받아서 TradeHistory 레코드를 생성하고,
    동일 세션에서 해당 보유를 삭제합니다.
    """
    session = SessionLocal()
    try:
        # 1) TradeHistory 생성
        profit = (sell_price - hold.avg_price) * hold.qty if hold.qty else 0
        new_trade = TradeHistory(
            code=hold.code,
            회사명=None,
            avg_price=hold.avg_price,
            qty=hold.qty,
            sell_price=sell_price,
            stop_price=hold.stop_price,
            num_buy=hold.num_buy,
            buy_price=hold.avg_price,
            profit=profit,
            fee=hold.fee,
            tax=hold.tax,
            buy_time=hold.buy_time,
            due_date=hold.due_date,
            order_id=hold.order_id
        )
        session.add(new_trade)

        # 2) 보유 삭제
        session.delete(hold)

        # 3) 만약 원 주문(OrderList) 상태를 '매도완료'로 업데이트하려면 여기서 처리할 수도 있음
        order = session.query(OrderList).filter(OrderList.order_id == hold.order_id).first()
        if order:
            order.status = "매도완료"

        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
