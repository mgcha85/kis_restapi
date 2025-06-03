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

# 1) 방금 작성한 Pydantic 모델 import
from src.models import RequestHeader, RequestBody, ResponseBody

# ─────────────────────────────────────────────────────────────────────────
# 2) YAML 설정 파일 로드 (config.yaml)
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
        f"config.yaml 로드 실패 ({e}), 기본값으로 실전 도메인 및 API 경로 사용"
    )
    use_mock_default = False
    DOMAIN_REAL = "https://openapi.koreainvestment.com:9443"
    DOMAIN_MOCK = "https://openapivts.koreainvestment.com:29443"
    API_PATH    = "/uapi/overseas-stock/v1/trading/order"


# ─────────────────────────────────────────────────────────────────────────
# 3) OrderManager 클래스 (Pydantic을 사용하도록 변경)
# ─────────────────────────────────────────────────────────────────────────
class OrderManager:
    def __init__(self,
                 api_key: str,
                 app_secret: str,
                 token: str,
                 use_mock: bool = None):
        """
        api_key    : KIS에서 발급받은 appkey
        app_secret : KIS에서 발급받은 appsecret
        token      : OAuth2.0 토큰 (Bearer 토큰)
        use_mock   : None이면 config.yaml의 trading.use_mock 사용
                     True → mock 서버, False → real 서버
        """
        self.api_key    = api_key
        self.app_secret = app_secret
        self.token      = token

        # use_mock 인자가 None 이면 YAML의 값을, 그렇지 않으면 인자로 넘어온 값을 사용
        self.use_mock = use_mock_default if use_mock is None else use_mock

        # path.real / path.mock 중 하나 선택
        self.base_url = DOMAIN_MOCK if self.use_mock else DOMAIN_REAL

        # 최종 API URL = 선택된 base_url + path.api
        self.api_url = f"{self.base_url}{API_PATH}"

        self.session = SessionLocal()
        self.logger  = logging.getLogger(__name__)

    # ─────────────────────────────────────────────────────────────────────
    # 4) 미국주식 전용 TR ID 생성 함수 (dataclass 버전과 동일)
    # ─────────────────────────────────────────────────────────────────────
    def _build_tr_id(self, is_buy: bool) -> str:
        """
        미국주식 전용 TR ID 생성
          - 실전 매수: "TTTT1002U"
          - 실전 매도: "TTTT1006U"
          - 모의 매수: "VTTT1002U"
          - 모의 매도: "VTTT1001U"
        """
        if self.use_mock:
            return "VTTT1002U" if is_buy else "VTTT1001U"
        else:
            return "TTTT1002U" if is_buy else "TTTT1006U"

    # ─────────────────────────────────────────────────────────────────────
    # 5) 주문 생성 메서드 (Pydantic 모델로 검증 + 파싱)
    # ─────────────────────────────────────────────────────────────────────
    def create_order(
        self,
        is_buy: bool,
        CANO: str,
        ACNT_PRDT_CD: str,
        OVRS_EXCG_CD: str,
        PDNO: str,
        ORD_QTY: int,
        OVRS_ORD_UNPR: int,
        # DB 저장용 필드
        order_type: str,
        name: str,
        qty: int,
        price: int,
        # 선택적 필드 (필요 시 인자로 넘겨주세요)
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
        """
        미국주식 지정가 주문 예시 (Pydantic 모델로 RequestHeader, RequestBody를 생성하여
        자동으로 타입 검증을 수행하고, 실패 시 예외를 띄웁니다.)
        """
        # ─────────────────────────────────────────────────────────────────
        # 1) TR ID 생성
        tr_id = self._build_tr_id(is_buy)

        # ─────────────────────────────────────────────────────────────────
        # 2) RequestHeader 인스턴스 생성 (검증 포함)
        try:
            header_model = RequestHeader(
                **{
                    "content-type": "application/json; charset=UTF-8",
                    "authorization": f"Bearer {self.token}",
                    "appkey": self.api_key,
                    "appsecret": self.app_secret,
                    "tr_id": tr_id,
                    # 필요 시 아래 필드를 추가하세요
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

        # ─────────────────────────────────────────────────────────────────
        # 3) RequestBody 인스턴스 생성 (검증 포함)
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

        # ─────────────────────────────────────────────────────────────────
        # 4) 실제 API 호출 (Pydantic이 검증해 준 dict/JSON을 사용)
        try:
            response = requests.post(
                self.api_url,
                headers=header_model.dict(by_alias=True, exclude_none=True),
                json=body_model.dict(by_alias=True, exclude_none=True)
            )
            # Pydantic 모델을 사용했기 때문에 "headers"와 "json" payload는
            # 모두 대문자/alias가 맞춘 상태로 넘어갑니다.
            response_data = response.json()
        except Exception as e:
            self.logger.exception("주문 생성 중 HTTP 요청 예외 발생")
            return None

        # ─────────────────────────────────────────────────────────────────
        # 5) 응답 파싱 (ResponseBody 모델 사용 가능)
        try:
            resp_model = ResponseBody.parse_obj(response_data)
        except ValidationError as ve:
            # API에서 예기치 않은 응답 스키마가 왔을 때 오류
            self.logger.error(f"응답 파싱 오류: {ve.json()}")
            return None

        # ─────────────────────────────────────────────────────────────────
        # 6) rt_cd == "0"이면 성공, 그 외에는 실패
        if resp_model.rt_cd == "0":
            # DB 저장
            new_order = OrderList(
                order_id  = str(uuid.uuid4()),
                code      = PDNO,
                name      = name,
                order_type=order_type,
                qty       = qty,
                remain_qty=qty,
                cum_price = price * qty,
                order_time= datetime.now(),
                status    = "주문전송완료"
            )
            try:
                self.session.add(new_order)
                self.session.commit()
                self.logger.info(f"Order created successfully: {new_order.order_id}")
                return new_order.order_id
            except Exception as db_e:
                self.logger.exception("DB에 주문 정보 저장 중 예외 발생")
                return None
        else:
            # 주문 실패 (msg1에 실패 원인이 나옵니다)
            self.logger.error(f"Order API Error (rt_cd={resp_model.rt_cd}): {resp_model.msg1}")
            return None

    # ─────────────────────────────────────────────────────────────────────
    # 7) 주문 수정 / 취소 메서드는 기존 로직 유지
    # ─────────────────────────────────────────────────────────────────────
    def modify_order(self, order_id: str, new_qty: int, new_price: int) -> bool:
        self.logger.info(f"Modifying order {order_id}: new_qty={new_qty}, new_price={new_price}")
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

    def cancel_order(self, order_id: str) -> bool:
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
        """세션 종료"""
        self.session.close()
