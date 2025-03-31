import logging
import uuid
from datetime import datetime
import requests
from src.db.db import SessionLocal
from src.db.models import OrderList

# 실제 API URL 및 payload 구조는 API 명세에 맞춰 수정하세요.
API_ORDER_URL = "https://openapi.koreainvestment.com:9443/uapi/overseas-stock/v1/trading/order"

class OrderManager:
    def __init__(self, api_key, app_secret, token):
        self.api_key = api_key
        self.app_secret = app_secret
        self.token = token
        self.session = SessionLocal()
        self.logger = logging.getLogger(__name__)

    def create_order(self, code, name, order_type, qty, price):
        """
        해외주식 주문 API를 호출하여 주문을 생성하고, 주문 정보를 DB에 기록합니다.
        """
        # 고유 주문 ID 생성 (실제 시스템에서는 API에서 발급한 order_id 사용 가능)
        order_id = str(uuid.uuid4())
        order_time = datetime.now()
        
        payload = {
            "CANO": "계좌번호",           # 실제 계좌 정보로 교체 필요
            "ACNT_PRDT_CD": "계좌상품코드",  # 실제 상품코드 사용
            "OVRS_EXCG_CD": "해외거래소코드", # 거래소 코드 예: NASD, NYSE 등
            "PDNO": code,
            "ORD_QTY": str(qty),
            "OVRS_ORD_UNPR": str(price),
            "ORD_SVR_DVSN_CD": "0",
            "ORD_DVSN": "00"
        }
        
        headers = {
            "Content-Type": "application/json; charset=UTF-8",
            "authorization": f"Bearer {self.token}",
            "appkey": self.api_key,
            "appsecret": self.app_secret,
        }
        
        try:
            response = requests.post(API_ORDER_URL, json=payload, headers=headers)
            response_data = response.json()
            if response_data.get("rt_cd") == "0":
                # 주문 API 호출 성공 시, 주문 정보를 DB에 저장
                new_order = OrderList(
                    order_id=order_id,
                    code=code,
                    name=name,
                    order_type=order_type,
                    qty=qty,
                    remain_qty=qty,
                    cum_price=price * qty,
                    order_time=order_time,
                    status="주문전송완료"
                )
                self.session.add(new_order)
                self.session.commit()
                self.logger.info(f"Order created successfully: {order_id}")
                return order_id
            else:
                self.logger.error(f"Order API Error: {response_data.get('msg1')}")
                return None
        except Exception as e:
            self.logger.exception("Exception during order creation")
            return None

    def modify_order(self, order_id, new_qty, new_price):
        """
        주문 정정 (수량 및 가격 변경) 예시 (실제 API 연동 및 로직에 맞게 수정)
        """
        self.logger.info(f"Modifying order {order_id} with new_qty={new_qty}, new_price={new_price}")
        order = self.session.query(OrderList).filter(OrderList.order_id == order_id).first()
        if order:
            order.qty = new_qty
            order.cum_price = new_price * new_qty
            self.session.commit()
            self.logger.info(f"Order {order_id} modified successfully")
            return True
        else:
            self.logger.error(f"Order {order_id} not found")
            return False

    def cancel_order(self, order_id):
        """
        주문 취소 예시 (실제 API 호출 및 취소 로직에 맞게 수정)
        """
        self.logger.info(f"Cancelling order {order_id}")
        order = self.session.query(OrderList).filter(OrderList.order_id == order_id).first()
        if order:
            order.status = "취소"
            self.session.commit()
            self.logger.info(f"Order {order_id} cancelled successfully")
            return True
        else:
            self.logger.error(f"Order {order_id} not found")
            return False

    def close(self):
        self.session.close()
