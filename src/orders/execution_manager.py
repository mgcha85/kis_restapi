# orders/execution_manager.py

import logging
import os
import yaml
import requests

from typing import Optional
from pydantic import ValidationError

from src.db.db import create_hold_from_order, create_trade_from_hold_and_delete, SessionLocal
from src.db.models import OrderList, HoldList
from src.order_execution_models import ExecutionInquiryResponse

# Header 검증을 위해 RequestHeader 모델 재사용
from src.order_models import RequestHeader  


# ─────────────────────────────────────────────────────────────────────────
# config.yaml 로드 (trading.use_mock, path.real, path.mock, execution api path)
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
    EXEC_PATH   = path_cfg.get("execution_api", "/uapi/overseas-stock/v1/trading/inquire-ccnl")
except Exception as e:
    logging.getLogger(__name__).warning(
        f"config.yaml 로드 실패 ({e}), 기본값으로 실전 도메인 및 주문체결조회 API 경로 사용"
    )
    use_mock_default = False
    DOMAIN_REAL      = "https://openapi.koreainvestment.com:9443"
    DOMAIN_MOCK      = "https://openapivts.koreainvestment.com:29443"
    EXEC_PATH        = "/uapi/overseas-stock/v1/trading/inquire-ccnl"


# ─────────────────────────────────────────────────────────────────────────
#  TR ID (실전/모의) 상수
# ─────────────────────────────────────────────────────────────────────────
EXEC_TR_ID_REAL = "TTTS3035R"
EXEC_TR_ID_MOCK = "VTTS3035R"


class ExecutionManager:
    def __init__(self, api_key: str, app_secret: str, token: str, use_mock: bool = None):
        """
        api_key    : KIS appkey
        app_secret : KIS appsecret
        token      : OAuth 토큰 (Bearer <token>)
        use_mock   : None 이면 config.yaml 읽은 값 사용, 아니면 인자로 받은 값
        """
        self.api_key    = api_key
        self.app_secret = app_secret
        self.token      = token
        self.use_mock   = use_mock_default if use_mock is None else use_mock

        base = DOMAIN_MOCK if self.use_mock else DOMAIN_REAL
        self.exec_url = f"{base}{EXEC_PATH}"

        self.session = SessionLocal()
        self.logger  = logging.getLogger(__name__)

    def _build_header(self, tr_id: str) -> Optional[dict]:
        """
        RequestHeader 모델로 헤더를 생성 및 검증
        """
        try:
            header_model = RequestHeader(
                **{
                    "content-type": "application/json; charset=UTF-8",
                    "authorization": f"Bearer {self.token}",
                    "appkey": self.api_key,
                    "appsecret": self.app_secret,
                    "tr_id": tr_id,
                    # 필요한 경우 연속조회나 법인/개인용 필드 추가
                }
            )
        except ValidationError as ve:
            self.logger.error(f"RequestHeader 검증 실패: {ve.json()}")
            return None

        return header_model.dict(by_alias=True, exclude_none=True)

    def inquire_executions(
        self,
        CANO: str,
        ACNT_PRDT_CD: str,
        PDNO: str,
        ORD_STRT_DT: str,
        ORD_END_DT: str,
        SLL_BUY_DVSN: str,
        CCLD_NCCS_DVSN: str,
        OVRS_EXCG_CD: str,
        SORT_SQN: str,
        ORD_DT: str = "",
        ORD_GNO_BRNO: str = "",
        ODNO: str = "",
        CTX_AREA_NK200: str = "",
        CTX_AREA_FK200: str = ""
    ) -> Optional[ExecutionInquiryResponse]:
        """
        해외주식 주문 체결내역 조회(v1_해외주식-007)

        - Method: GET
        - URL   : {DOMAIN}{EXEC_PATH}
        - Headers: authorization, appkey, appsecret, tr_id
        - QueryParams:
            CANO, ACNT_PRDT_CD, PDNO, ORD_STRT_DT, ORD_END_DT, SLL_BUY_DVSN,
            CCLD_NCCS_DVSN, OVRS_EXCG_CD, SORT_SQN, ORD_DT, ORD_GNO_BRNO, ODNO,
            CTX_AREA_NK200, CTX_AREA_FK200
        """
        tr_id = EXEC_TR_ID_MOCK if self.use_mock else EXEC_TR_ID_REAL

        headers = self._build_header(tr_id)
        if headers is None:
            return None

        params = {
            "CANO": CANO,
            "ACNT_PRDT_CD": ACNT_PRDT_CD,
            "PDNO": PDNO,
            "ORD_STRT_DT": ORD_STRT_DT,
            "ORD_END_DT": ORD_END_DT,
            "SLL_BUY_DVSN": SLL_BUY_DVSN,
            "CCLD_NCCS_DVSN": CCLD_NCCS_DVSN,
            "OVRS_EXCG_CD": OVRS_EXCG_CD,
            "SORT_SQN": SORT_SQN,
            "ORD_DT": ORD_DT,
            "ORD_GNO_BRNO": ORD_GNO_BRNO,
            "ODNO": ODNO,
            "CTX_AREA_NK200": CTX_AREA_NK200,
            "CTX_AREA_FK200": CTX_AREA_FK200,
        }

        try:
            resp = requests.get(self.exec_url, headers=headers, params=params)
            data = resp.json()
        except Exception as e:
            self.logger.exception("주문체결내역 조회 중 HTTP 요청 에러 발생")
            return None

        try:
            parsed = ExecutionInquiryResponse.parse_obj(data)
        except ValidationError as ve:
            self.logger.error(f"주문체결내역 응답 파싱 실패: {ve.json()}")
            return None

        if parsed.rt_cd != "0":
            self.logger.error(f"주문체결내역 조회 실패 (rt_cd={parsed.rt_cd}, msg1={parsed.msg1})")
            return None

        return parsed

    def process_executions(self, execution_response: ExecutionInquiryResponse):
        """
        Pydantic으로 파싱된 ExecutionInquiryResponse를 받아,
        각 output 레코드마다 다음을 수행:

        - sll_buy_dvsn_cd == "02" (매수 체결):
            1) OrderList에서 해당 주문번호(orgn_odno)로 주문을 조회
            2) create_hold_from_order(order) 호출 → hold_list 생성 + order.status="체결"
        - sll_buy_dvsn_cd == "01" (매도 체결):
            1) HoldList에서 pdno(종목코드)로 보유 조회
            2) create_trade_from_hold_and_delete(hold, sell_price) 호출 → trade_history 생성 + hold_list 삭제 + order.status="매도완료"
        """
        for item in execution_response.output:
            # 1) 매수 체결
            if item.sll_buy_dvsn_cd == "02":
                session = SessionLocal()
                try:
                    order = session.query(OrderList).filter(OrderList.order_id == item.orgn_odno).first()
                    if order:
                        create_hold_from_order(order)
                    else:
                        self.logger.warning(f"매수 체결: OrderList에서 주문번호 {item.orgn_odno}를 찾을 수 없음")
                except Exception:
                    session.rollback()
                    self.logger.exception("매수 체결 처리 중 DB 에러 발생")
                finally:
                    session.close()

            # 2) 매도 체결
            elif item.sll_buy_dvsn_cd == "01":
                session = SessionLocal()
                try:
                    hold = session.query(HoldList).filter(HoldList.code == item.pdno).first()
                    if hold:
                        sell_price = int(item.ft_ccld_unpr3)
                        create_trade_from_hold_and_delete(hold, sell_price)
                    else:
                        self.logger.warning(f"매도 체결: HoldList에서 종목 {item.pdno}를 찾을 수 없음")
                except Exception:
                    session.rollback()
                    self.logger.exception("매도 체결 처리 중 DB 에러 발생")
                finally:
                    session.close()

            else:
                # 기타(예: SLL_BUY_DVSN="00" 전체 조회 시도)
                continue

    def close(self):
        self.session.close()
