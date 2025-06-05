import logging
import requests
from typing import Optional

from pydantic import ValidationError

from src.orders.margin_models import MarginResponse
from src.orders.order_models import RequestHeader
from src.orders.base_manager import BaseManager


class MarginManager(BaseManager):
    """
    해외증거금 통화별조회 (v1_해외주식-035) 기능.
    """

    def __init__(self):
        super().__init__()  # BaseManager 초기화

        # TR ID 및 API URL 설정 (모의투자 미지원)
        self.MARGIN_TR_ID    = "TTTC2101R"
        margin_path = "/uapi/overseas-stock/v1/trading/foreign-margin"
        base = self.DOMAIN_MOCK if self.use_mock else self.DOMAIN_REAL
        self.margin_api_url = f"{base}{margin_path}"

        self.logger = logging.getLogger(__name__)

    def _build_header(self, tr_id: str) -> Optional[dict]:
        """
        RequestHeader 모델을 통해 헤더 검증 및 dict 형태 반환
        """
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
            self.logger.error(f"[MarginManager] RequestHeader 검증 실패: {ve.json()}")
            return None

        return header_model.dict(by_alias=True, exclude_none=True)

    def get_foreign_margin(
        self,
        CANO: str = None,
        ACNT_PRDT_CD: str = None
    ) -> Optional[MarginResponse]:
        """
        해외증거금 통화별조회 (v1_해외주식-035) 호출 후 응답 파싱하여 반환.
        config.yaml의 account 값을 기본으로 사용.
        """
        CANO         = CANO or self.cfg["account"]["CANO"]
        ACNT_PRDT_CD = ACNT_PRDT_CD or self.cfg["account"]["ACNT_PRDT_CD"]

        headers = self._build_header(self.MARGIN_TR_ID)
        if headers is None:
            return None

        params = {
            "CANO": CANO,
            "ACNT_PRDT_CD": ACNT_PRDT_CD
        }

        try:
            resp = requests.get(self.margin_api_url, headers=headers, params=params)
            data = resp.json()
        except Exception:
            self.logger.exception("[MarginManager] 증거금 조회 중 HTTP 요청 에러 발생")
            return None

        try:
            parsed = MarginResponse.parse_obj(data)
        except ValidationError as ve:
            self.logger.error(f"[MarginManager] 증거금 조회 응답 파싱 실패: {ve.json()}")
            return None

        if parsed.rt_cd != "0":
            self.logger.error(f"[MarginManager] 증거금 조회 실패 (rt_cd={parsed.rt_cd}, msg1={parsed.msg1})")
            return None

        return parsed

    def get_usd_available_cash(self, CANO: str = None, ACNT_PRDT_CD: str = None) -> float:
        """
        USD 외화일반주문가능금액 반환.
        """
        resp = self.get_foreign_margin(CANO, ACNT_PRDT_CD)
        if resp is None:
            self.logger.error("[MarginManager] foreign-margin 응답 없거나 파싱 실패로 USD 주문가능금액 반환 불가, 0.0 반환")
            return 0.0

        for item in resp.output:
            if item.crcy_cd.upper() == "USD":
                try:
                    return float(item.frcr_gnrl_ord_psbl_amt)
                except Exception:
                    self.logger.error(f"[MarginManager] USD 주문가능금액 파싱 오류: {item.frcr_gnrl_ord_psbl_amt}")
                    return 0.0

        self.logger.warning("[MarginManager] USD 통화 정보가 응답에 없습니다. 0.0 반환")
        return 0.0
