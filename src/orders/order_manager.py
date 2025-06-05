import logging
import uuid
from datetime import datetime
import requests
from typing import Optional

from pydantic import ValidationError

from src.db.db import SessionLocal
from src.db.models import OrderList
from src.orders.order_models import RequestHeader, RequestBody, ResponseBody as OrderResponseBody
from src.orders.base_manager import BaseManager


class OrderManager(BaseManager):
    """
    해외주식 주문 생성/정정/취소 기능(v1_해외주식-001).
    """

    def __init__(self):
        super().__init__()  # BaseManager 초기화

        # 주문 API 경로(config.yaml의 path.api) 사용
        order_path = self.PATH_CFG.get("api", "/uapi/overseas-stock/v1/trading/order")
        base = self.DOMAIN_MOCK if self.use_mock else self.DOMAIN_REAL
        self.api_url = f"{base}{order_path}"

        self.session = SessionLocal()
        self.logger  = logging.getLogger(__name__)

    def _build_tr_id(self, is_buy: bool) -> str:
        """
        미국주식 전용 TR ID 생성
        실전 매수: TTTT1002U / 실전 매도: TTTT1006U
        모의 매수: VTTT1002U / 모의 매도: VTTT1001U
        """
        if self.use_mock:
            return "VTTT1002U" if is_buy else "VTTT1001U"
        else:
            return "TTTT1002U" if is_buy else "TTTT1006U"

    def create_order(
        self,
        is_buy: bool,
        CANO: str,
        ACNT_PRDT_CD: str,
        OVRS_EXCG_CD: str,
        PDNO: str,
        ORD_QTY: int,
        OVRS_ORD_UNPR: int,
        order_type: str,
        name: str,
        qty: int,
        price: int,
        CTAC_TLNO: str = None,
        MGCO_APTM_ODNO: str = None,
        SLL_TYPE: str = None,
        START_TIME: str = None,
        END_TIME: str = None,
        ALGO_ORD_TMD_DVSN_CD: str = None,
        custtype: str = None,
        seq_no: str = None,
        mac_address: str = None,
        phone_number: str = None,
        ip_addr: str = None,
        gt_uid: str = None,
    ) -> Optional[str]:
        """
        해외주식 주문 API 호출 → DB에 저장 → order_id 반환
        """
        order_id = str(uuid.uuid4())
        order_time = datetime.now()

        tr_id = self._build_tr_id(is_buy)

        # Header 검증용 Pydantic
        try:
            header_model = RequestHeader(
                **{
                    "content-type": "application/json; charset=UTF-8",
                    "authorization": f"Bearer {self.token}",
                    "appkey": self.api_key,
                    "appsecret": self.app_secret,
                    "tr_id": tr_id,
                }
            )
        except ValidationError as ve:
            self.logger.error(f"[OrderManager] RequestHeader 검증 실패: {ve.json()}")
            return None

        # Body 검증용 Pydantic
        try:
            body_model = RequestBody(
                CANO=CANO,
                ACNT_PRDT_CD=ACNT_PRDT_CD,
                OVRS_EXCG_CD=OVRS_EXCG_CD,
                PDNO=PDNO,
                ORD_QTY=str(ORD_QTY),
                OVRS_ORD_UNPR=str(OVRS_ORD_UNPR),
                ORD_SVR_DVSN_CD="0",
                ORD_DVSN="00",
                CTAC_TLNO=CTAC_TLNO,
                MGCO_APTM_ODNO=MGCO_APTM_ODNO,
                SLL_TYPE=SLL_TYPE,
                START_TIME=START_TIME,
                END_TIME=END_TIME,
                ALGO_ORD_TMD_DVSN_CD=ALGO_ORD_TMD_DVSN_CD,
            )
        except ValidationError as ve:
            self.logger.error(f"[OrderManager] RequestBody 검증 실패: {ve.json()}")
            return None

        # HTTP 요청
        try:
            resp = requests.post(
                self.api_url,
                headers=header_model.dict(by_alias=True, exclude_none=True),
                json=body_model.dict(by_alias=True, exclude_none=True)
            )
            data = resp.json()
        except Exception:
            self.logger.exception("[OrderManager] 주문 생성 중 HTTP 요청 에러 발생")
            return None

        # Response 검증/파싱
        try:
            resp_model = OrderResponseBody.parse_obj(data)
        except ValidationError as ve:
            self.logger.error(f"[OrderManager] 응답 파싱 실패: {ve.json()}")
            return None

        if resp_model.rt_cd == "0":
            # DB 저장
            new_order = OrderList(
                order_id   = order_id,
                code       = PDNO,
                name       = name,
                order_type = order_type,
                qty        = qty,
                remain_qty = qty,
                cum_price  = price * qty,
                order_time = order_time,
                status     = "주문전송완료"
            )
            try:
                self.session.add(new_order)
                self.session.commit()
                self.logger.info(f"[OrderManager] Order created successfully: {order_id}")
                return order_id
            except Exception:
                self.logger.exception("[OrderManager] DB 저장 중 에러 발생")
                return None
        else:
            self.logger.error(f"[OrderManager] Order API Error (rt_cd={resp_model.rt_cd}, msg1={resp_model.msg1})")
            return None

    def modify_order(self, order_id: str, new_qty: int, new_price: int) -> bool:
        order = self.session.query(OrderList).filter(OrderList.order_id == order_id).first()
        if order:
            order.qty = new_qty
            order.cum_price = new_price * new_qty
            self.session.commit()
            return True
        else:
            self.logger.error(f"[OrderManager] Order {order_id} not found")
            return False

    def cancel_order(self, order_id: str) -> bool:
        order = self.session.query(OrderList).filter(OrderList.order_id == order_id).first()
        if order:
            order.status = "취소"
            self.session.commit()
            return True
        else:
            self.logger.error(f"[OrderManager] Order {order_id} not found")
            return False

    def close(self):
        self.session.close()
