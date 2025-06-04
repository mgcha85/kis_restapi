# orders/order_manager.py

import logging
import uuid
from datetime import datetime
import requests
import os
import yaml

from pydantic import ValidationError

from src.db.db import SessionLocal
from src.db.models import OrderList

# ▶ 분리된 Pydantic 모델 import
from src.orders.order_models import RequestHeader, RequestBody, ResponseBody as OrderResponseBody

# ─────────────────────────────────────────────────────────────────────────
# config.yaml 로드
# ─────────────────────────────────────────────────────────────────────────
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.yaml")


def _load_config() -> dict:
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {CONFIG_PATH}")
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


try:
    cfg = _load_config()
    trading_cfg      = cfg.get("trading", {})
    use_mock_default = trading_cfg.get("use_mock", False)

    path_cfg    = cfg.get("path", {})
    DOMAIN_REAL = path_cfg.get("real", "https://openapi.koreainvestment.com:9443")
    DOMAIN_MOCK = path_cfg.get("mock", "https://openapivts.koreainvestment.com:29443")
    API_PATH    = path_cfg.get("api", "/uapi/overseas-stock/v1/trading/order")

except Exception as e:
    logging.getLogger(__name__).warning(
        f"config.yaml 로드 실패 ({e}), 기본값으로 실전 도메인 및 주문 API 경로 사용"
    )
    use_mock_default = False
    DOMAIN_REAL = "https://openapi.koreainvestment.com:9443"
    DOMAIN_MOCK = "https://openapivts.koreainvestment.com:29443"
    API_PATH    = "/uapi/overseas-stock/v1/trading/order"


class OrderManager:
    def __init__(self, api_key: str, app_secret: str, token: str, use_mock: bool = None):
        self.api_key    = api_key
        self.app_secret = app_secret
        self.token      = token
        self.use_mock   = use_mock_default if use_mock is None else use_mock

        self.base_url = DOMAIN_MOCK if self.use_mock else DOMAIN_REAL
        self.api_url  = f"{self.base_url}{API_PATH}"

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
    ) -> str:
        order_id = str(uuid.uuid4())
        order_time = datetime.now()

        # 1) TR ID 결정
        tr_id = self._build_tr_id(is_buy)

        # 2) 헤더 검증용 Pydantic 모델 생성
        try:
            header_model = RequestHeader(
                **{
                    "content-type": "application/json; charset=UTF-8",
                    "authorization": f"Bearer {self.token}",
                    "appkey": self.api_key,
                    "appsecret": self.app_secret,
                    "tr_id": tr_id,
                    # 필요 시 추가 가능
                    # "custtype": custtype,
                    # "seq_no": seq_no,
                    # "mac_address": mac_address,
                    # "phone_number": phone_number,
                    # "ip_addr": ip_addr,
                    # "gt_uid": gt_uid,
                }
            )
        except ValidationError as ve:
            self.logger.error(f"RequestHeader 검증 실패: {ve.json()}")
            return None

        # 3) 바디 검증용 Pydantic 모델 생성
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
            self.logger.error(f"RequestBody 검증 실패: {ve.json()}")
            return None

        # 4) 실제 API 호출
        try:
            resp = requests.post(
                self.api_url,
                headers=header_model.dict(by_alias=True, exclude_none=True),
                json=body_model.dict(by_alias=True, exclude_none=True)
            )
            data = resp.json()
        except Exception as e:
            self.logger.exception("주문 생성 중 HTTP 요청 에러 발생")
            return None

        # 5) 응답 검증 및 파싱
        try:
            resp_model = OrderResponseBody.parse_obj(data)
        except ValidationError as ve:
            self.logger.error(f"응답 파싱 실패: {ve.json()}")
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
                self.logger.info(f"Order created successfully: {order_id}")
                return order_id
            except Exception as db_e:
                self.logger.exception("DB 저장 중 에러 발생")
                return None
        else:
            self.logger.error(f"Order API Error (rt_cd={resp_model.rt_cd}, msg1={resp_model.msg1})")
            return None

    def modify_order(self, order_id: str, new_qty: int, new_price: int) -> bool:
        order = self.session.query(OrderList).filter(OrderList.order_id == order_id).first()
        if order:
            order.qty = new_qty
            order.cum_price = new_price * new_qty
            self.session.commit()
            return True
        else:
            self.logger.error(f"Order {order_id} not found")
            return False

    def cancel_order(self, order_id: str) -> bool:
        order = self.session.query(OrderList).filter(OrderList.order_id == order_id).first()
        if order:
            order.status = "취소"
            self.session.commit()
            return True
        else:
            self.logger.error(f"Order {order_id} not found")
            return False

    def close(self):
        self.session.close()
