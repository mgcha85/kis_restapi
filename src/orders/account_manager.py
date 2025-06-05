import logging
import requests
from typing import Optional

from pydantic import ValidationError

from src.db.db import SessionLocal
from src.orders.account_models import BalanceInquiryResponse
from src.orders.order_models import RequestHeader
from src.orders.base_manager import BaseManager


class AccountManager(BaseManager):
    """
    해외주식 잔고 조회 (v1_해외주식-006) 기능.
    """

    def __init__(self):
        super().__init__()  # BaseManager 초기화

        # config.yaml의 account 섹션에서 계좌 정보 불러오기
        account_cfg = self.cfg.get("account", {})
        self.CANO         = account_cfg.get("CANO")
        self.ACNT_PRDT_CD = account_cfg.get("ACNT_PRDT_CD")
        self.OVRS_EXCG_CD = account_cfg.get("OVRS_EXCG_CD")
        self.TR_CRCY_CD   = account_cfg.get("TR_CRCY_CD")

        # TR ID 및 API URL 설정
        self.BALANCE_TR_ID = "VTTS3012R" if self.use_mock else "TTTS3012R"
        balance_path = "/uapi/overseas-stock/v1/trading/inquire-balance"
        base = self.DOMAIN_MOCK if self.use_mock else self.DOMAIN_REAL
        self.balance_api_url = f"{base}{balance_path}"

        self.session = SessionLocal()
        self.logger  = logging.getLogger(__name__)

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
            self.logger.error(f"[AccountManager] RequestHeader 검증 실패: {ve.json()}")
            return None

        return header_model.model_dump(by_alias=True, exclude_none=True)

    def get_balance(
        self,
        CANO: str = None,
        ACNT_PRDT_CD: str = None,
        OVRS_EXCG_CD: str = None,
        TR_CRCY_CD: str = None,
        CTX_AREA_FK200: str = "",
        CTX_AREA_NK200: str = ""
    ) -> Optional[BalanceInquiryResponse]:
        """
        해외주식 잔고(v1_해외주식-006) API 호출 후 응답 파싱하여 반환.
        인자가 없으면 config.yaml의 값을 사용.
        """
        CANO         = CANO or self.CANO
        ACNT_PRDT_CD = ACNT_PRDT_CD or self.ACNT_PRDT_CD
        OVRS_EXCG_CD = OVRS_EXCG_CD or self.OVRS_EXCG_CD
        TR_CRCY_CD   = TR_CRCY_CD or self.TR_CRCY_CD

        headers = self._build_header(self.BALANCE_TR_ID)
        if headers is None:
            return None

        params = {
            "CANO": CANO,
            "ACNT_PRDT_CD": ACNT_PRDT_CD,
            "OVRS_EXCG_CD": OVRS_EXCG_CD,
            "TR_CRCY_CD": TR_CRCY_CD,
            "CTX_AREA_FK200": CTX_AREA_FK200,
            "CTX_AREA_NK200": CTX_AREA_NK200,
        }

        try:
            resp = requests.get(self.balance_api_url, headers=headers, params=params)
            data = resp.json()
        except Exception:
            self.logger.exception("[AccountManager] 잔고 조회 중 HTTP 요청 에러 발생")
            return None

        try:
            parsed = BalanceInquiryResponse.parse_obj(data)
        except ValidationError as ve:
            self.logger.error(f"[AccountManager] 잔고 조회 응답 파싱 실패: {ve.json()}")
            return None

        if parsed.rt_cd != "0":
            self.logger.error(f"[AccountManager] 잔고 조회 실패 (rt_cd={parsed.rt_cd}, msg1={parsed.msg1})")
            return None

        return parsed

    def get_cash_balance(
        self,
        CANO: str = None,
        ACNT_PRDT_CD: str = None,
        OVRS_EXCG_CD: str = None,
        TR_CRCY_CD: str = None
    ) -> float:
        """
        예수금(현금) 조회. 잔고 조회 결과에서
        output1의 ovrs_stck_evlu_amt(평가금액) 합계와 output2.frcr_buy_amt_smtl1(총매입원금)을
        사용해 추정 계산을 수행.
        """
        resp = self.get_balance(CANO, ACNT_PRDT_CD, OVRS_EXCG_CD, TR_CRCY_CD)
        if resp is None:
            self.logger.error("[AccountManager] 잔고 조회 실패로 인한 예수금 반환 불가, 0.0 반환")
            return 0.0

        total_stock_value = 0.0
        for item in resp.output1:
            try:
                total_stock_value += float(item.ovrs_stck_evlu_amt)
            except Exception:
                continue

        try:
            total_cost = float(resp.output2.frcr_buy_amt_smtl1)
        except Exception:
            total_cost = 0.0

        cash_estimate = total_cost - total_stock_value
        return max(cash_estimate, 0.0)

    def close(self):
        self.session.close()
