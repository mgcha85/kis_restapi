# orders/account_manager.py

import logging
import os
import yaml
import requests

from typing import List, Optional
from pydantic import ValidationError

from src.db.db import SessionLocal

# ▶ 분리된 Pydantic 모델 import
from src.orders.account_models import (
    ResponseBodyOutput1,
    ResponseBodyOutput2,
    BalanceInquiryResponse
)
from src.orders.order_models import RequestHeader  # 헤더용 모델만 재사용

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

    BALANCE_TR_ID_REAL = "TTTS3012R"
    BALANCE_TR_ID_MOCK = "VTTS3012R"
    BALANCE_API_PATH   = "/uapi/overseas-stock/v1/trading/inquire-balance"

except Exception as e:
    logging.getLogger(__name__).warning(
        f"config.yaml 로드 실패 ({e}), 기본값으로 실전 도메인 및 잔고조회 TR ID 사용"
    )
    use_mock_default   = False
    DOMAIN_REAL        = "https://openapi.koreainvestment.com:9443"
    DOMAIN_MOCK        = "https://openapivts.koreainvestment.com:29443"
    BALANCE_TR_ID_REAL = "TTTS3012R"
    BALANCE_TR_ID_MOCK = "VTTS3012R"
    BALANCE_API_PATH   = "/uapi/overseas-stock/v1/trading/inquire-balance"


class AccountManager:
    def __init__(self, api_key: str, app_secret: str, token: str, use_mock: bool = None):
        self.api_key    = api_key
        self.app_secret = app_secret
        self.token      = token
        self.use_mock   = use_mock_default if use_mock is None else use_mock

        base = DOMAIN_MOCK if self.use_mock else DOMAIN_REAL
        self.balance_api_url = f"{base}{BALANCE_API_PATH}"

        self.session = SessionLocal()
        self.logger  = logging.getLogger(__name__)

    def _build_header(self, tr_id: str) -> Optional[dict]:
        try:
            header_model = RequestHeader(
                **{
                    "content-type": "application/json; charset=UTF-8",
                    "authorization": f"Bearer {self.token}",
                    "appkey": self.api_key,
                    "appsecret": self.app_secret,
                    "tr_id": tr_id,
                    # 필요 시 추가 가능
                    # "tr_cont": "",
                    # "custtype": None,
                    # "seq_no": None,
                    # "mac_address": None,
                    # "phone_number": None,
                    # "ip_addr": None,
                    # "hashkey": None,
                    # "gt_uid": None,
                }
            )
        except ValidationError as ve:
            self.logger.error(f"RequestHeader 검증 실패: {ve.json()}")
            return None

        return header_model.dict(by_alias=True, exclude_none=True)

    def get_balance(
        self,
        CANO: str,
        ACNT_PRDT_CD: str,
        OVRS_EXCG_CD: str,
        TR_CRCY_CD: str,
        CTX_AREA_FK200: str = "",
        CTX_AREA_NK200: str = ""
    ) -> Optional[BalanceInquiryResponse]:
        tr_id = BALANCE_TR_ID_MOCK if self.use_mock else BALANCE_TR_ID_REAL

        headers = self._build_header(tr_id)
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
        except Exception as e:
            self.logger.exception("잔고 조회 중 HTTP 요청 에러 발생")
            return None

        try:
            parsed = BalanceInquiryResponse.parse_obj(data)
        except ValidationError as ve:
            self.logger.error(f"잔고 조회 응답 파싱 실패: {ve.json()}")
            return None

        if parsed.rt_cd != "0":
            self.logger.error(f"잔고 조회 실패 (rt_cd={parsed.rt_cd}, msg1={parsed.msg1})")
            return None

        return parsed

    def close(self):
        self.session.close()


if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    logger = logging.getLogger("account_manager_test")

    # .env에서 api_key, app_secret, token, use_mock 읽기
    api_key    = os.getenv("KIS_API_KEY")
    app_secret = os.getenv("KIS_APP_SECRET")
    token      = os.getenv("KIS_OAUTH_TOKEN")
    use_mock   = trading_cfg.get("use_mock", False)

    if not api_key or not app_secret or not token:
        logger.error(".env에 KIS_API_KEY, KIS_APP_SECRET, KIS_OAUTH_TOKEN이 모두 설정되어야 합니다.")
        exit(1)

    # config.yaml에서 계좌 정보 로드
    try:
        cfg = _load_config()
        account_cfg = cfg.get("account", {})
        CANO         = account_cfg.get("CANO")
        ACNT_PRDT_CD = account_cfg.get("ACNT_PRDT_CD")
        OVRS_EXCG_CD = account_cfg.get("OVRS_EXCG_CD")
        TR_CRCY_CD   = account_cfg.get("TR_CRCY_CD")
    except Exception as e:
        logger.exception(f"config.yaml에서 계좌 정보 로드 실패: {e}")
        exit(1)

    # AccountManager 인스턴스 생성
    acct_mgr = AccountManager(
        api_key=api_key,
        app_secret=app_secret,
        token=token,
        use_mock=use_mock
    )

    logger.info("잔고 조회 테스트 시작")
    balance_resp = acct_mgr.get_balance(
        CANO=CANO,
        ACNT_PRDT_CD=ACNT_PRDT_CD,
        OVRS_EXCG_CD=OVRS_EXCG_CD,
        TR_CRCY_CD=TR_CRCY_CD
    )

    if balance_resp:
        # output1(종목별 잔고)
        logger.info("=== 종목별 잔고 (output1) ===")
        for item in balance_resp.output1:
            logger.info(
                f"종목코드: {item.ovrs_pdno}, "
                f"잔고수량: {item.ovrs_cblc_qty}, "
                f"평가금액: {item.ovrs_stck_evlu_amt}"
            )

        # output2(요약)
        logger.info("=== 잔고 요약 (output2) ===")
        out2: ResponseBodyOutput2 = balance_resp.output2
        logger.info(
            f"외화매입금액합계1: {out2.frcr_pchs_amt1}, "
            f"해외실현손익금액: {out2.ovrs_rlzt_pfls_amt}, "
            f"해외총손익: {out2.ovrs_tot_pfls}, "
            f"총평가손익금액: {out2.tot_evlu_pfls_amt}"
        )
    else:
        logger.error("잔고 조회 실패")

    acct_mgr.close()