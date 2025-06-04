# rebalancer.py

import os
import yaml
import math
import logging
import requests

from typing import Optional, Dict
from pydantic import BaseModel, Field, ValidationError

from orders.account_manager import AccountManager
from orders.order_manager import OrderManager

from src.db.db import SessionLocal
from src.db.models import HoldList

# ─────────────────────────────────────────────────────────────────────────
# 1) Price API용 Pydantic 모델 (v1_해외주식-009)
# ─────────────────────────────────────────────────────────────────────────
class PriceOutput(BaseModel):
    rsym: str = Field(..., alias="rsym", description="실시간조회종목코드")
    last: str = Field(..., alias="last", description="현재가")

    class Config:
        allow_population_by_field_name = True
        allow_population_by_alias      = True


class PriceResponse(BaseModel):
    rt_cd: str      = Field(..., alias="rt_cd", description="성공 실패 여부 (0: 성공)")
    msg_cd: str     = Field(..., alias="msg_cd", description="응답코드")
    msg1: str       = Field(..., alias="msg1", description="응답메시지")
    output: PriceOutput = Field(..., alias="output", description="응답상세")

    class Config:
        allow_population_by_field_name = True
        allow_population_by_alias      = True


# ─────────────────────────────────────────────────────────────────────────
# 2) Balance API용 Pydantic 모델 (v1_해외주식-006)
# ─────────────────────────────────────────────────────────────────────────
class BalanceOutput1(BaseModel):
    ovrs_pdno: str        = Field(..., alias="ovrs_pdno", description="해외상품번호")
    ovrs_cblc_qty: str    = Field(..., alias="ovrs_cblc_qty", description="해외잔고수량")
    ovrs_stck_evlu_amt: str = Field(..., alias="ovrs_stck_evlu_amt", description="해외주식평가금액")
    # 그 외 필드는 생략

    class Config:
        allow_population_by_field_name = True
        allow_population_by_alias      = True


class BalanceOutput2(BaseModel):
    frcr_pchs_amt1: str      = Field(..., alias="frcr_pchs_amt1", description="외화매입금액1")
    ovrs_rlzt_pfls_amt: str   = Field(..., alias="ovrs_rlzt_pfls_amt", description="해외실현손익금액")
    ovrs_tot_pfls: str        = Field(..., alias="ovrs_tot_pfls", description="해외총손익")
    rlzt_erng_rt: str         = Field(..., alias="rlzt_erng_rt", description="실현수익율")
    tot_evlu_pfls_amt: str    = Field(..., alias="tot_evlu_pfls_amt", description="총평가손익금액")
    tot_pftrt: str            = Field(..., alias="tot_pftrt", description="총수익률")
    frcr_buy_amt_smtl1: str   = Field(..., alias="frcr_buy_amt_smtl1", description="외화매수금액합계1")
    # 그 외 필드는 생략

    class Config:
        allow_population_by_field_name = True
        allow_population_by_alias      = True


class BalanceResponse(BaseModel):
    rt_cd: str                       = Field(..., alias="rt_cd", description="성공 실패 여부 (0: 성공)")
    msg_cd: str                      = Field(..., alias="msg_cd", description="응답코드")
    msg1: str                        = Field(..., alias="msg1", description="응답메시지")
    ctx_area_fk200: str              = Field(..., alias="ctx_area_fk200", description="연속조회검색조건200")
    ctx_area_nk200: str              = Field(..., alias="ctx_area_nk200", description="연속조회키200")
    output1: list[BalanceOutput1]    = Field(..., alias="output1", description="응답상세1 리스트")
    output2: BalanceOutput2          = Field(..., alias="output2", description="응답상세2 객체")

    class Config:
        allow_population_by_field_name = True
        allow_population_by_alias      = True


# ─────────────────────────────────────────────────────────────────────────
# 3) Rebalancer 클래스
# ─────────────────────────────────────────────────────────────────────────
class Rebalancer:
    def __init__(self):
        # config.yaml 로드
        BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
        CONFIG_PATH = os.path.join(BASE_DIR, "config", "config.yaml")
        if not os.path.exists(CONFIG_PATH):
            raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {CONFIG_PATH}")
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)

        trading_cfg = cfg.get("trading", {})
        self.use_mock   = trading_cfg.get("use_mock", False)
        self.api_key    = trading_cfg.get("api_key")
        self.app_secret = trading_cfg.get("app_secret")

        account_cfg = cfg.get("account", {})
        self.CANO         = account_cfg.get("CANO")
        self.ACNT_PRDT_CD = account_cfg.get("ACNT_PRDT_CD")
        self.OVRS_EXCG_CD = account_cfg.get("OVRS_EXCG_CD")
        self.TR_CRCY_CD   = account_cfg.get("TR_CRCY_CD")

        strategy_cfg = cfg.get("strategy", {})
        self.weights = strategy_cfg.get("weights", {})

        # 매니저 인스턴스 생성
        self.acct_mgr  = AccountManager(self.api_key, self.app_secret, token="", use_mock=self.use_mock)
        self.order_mgr = OrderManager(self.api_key, self.app_secret, token="", use_mock=self.use_mock)

        path_cfg = cfg.get("path", {})
        self.DOMAIN_REAL   = path_cfg.get("real", "https://openapi.koreainvestment.com:9443")
        self.DOMAIN_MOCK   = path_cfg.get("mock", "https://openapivts.koreainvestment.com:29443")
        self.BALANCE_PATH  = path_cfg.get("api_balance", "/uapi/overseas-stock/v1/trading/inquire-balance")
        self.PRICE_PATH    = path_cfg.get("api_price", "/uapi/overseas-price/v1/quotations/price")

        self.logger = logging.getLogger(__name__)

    def _get_token(self) -> str:
        """
        OAuth 토큰 발급 로직 (실제 APIClient.get_oauth_token() 호출 필요)
        """
        # TODO: 실제 구현으로 교체
        return "YOUR_BEARER_TOKEN"

    def _build_header(self, tr_id: str) -> Optional[dict]:
        """
        GET 공통 헤더 생성 (주문/잔고/가격 API 모두 같은 RequestHeader 사용)
        """
        from src.orders.order_models import RequestHeader

        try:
            header_model = RequestHeader(
                **{
                    "content-type": "application/json; charset=UTF-8",
                    "authorization": f"Bearer {self.acct_mgr.token}",
                    "appkey": self.api_key,
                    "appsecret": self.app_secret,
                    "tr_id": tr_id,
                }
            )
        except ValidationError as ve:
            self.logger.error(f"Header 검증 실패 (TR ID={tr_id}): {ve.json()}")
            return None

        return header_model.dict(by_alias=True, exclude_none=True)

    def _get_balance_response(self) -> Optional[BalanceResponse]:
        """
        v1_해외주식-006 잔고 조회 API 호출
        """
        tr_id = "VTTS3012R" if self.use_mock else "TTTS3012R"
        headers = self._build_header(tr_id)
        if headers is None:
            return None

        params = {
            "CANO": self.CANO,
            "ACNT_PRDT_CD": self.ACNT_PRDT_CD,
            "OVRS_EXCG_CD": self.OVRS_EXCG_CD,
            "TR_CRCY_CD": self.TR_CRCY_CD,
            "CTX_AREA_FK200": "",
            "CTX_AREA_NK200": "",
        }

        base = self.DOMAIN_MOCK if self.use_mock else self.DOMAIN_REAL
        url = f"{base}{self.BALANCE_PATH}"
        try:
            resp = requests.get(url, headers=headers, params=params)
            data = resp.json()
        except Exception as e:
            self.logger.exception("잔고 조회 중 HTTP 에러 발생")
            return None

        try:
            parsed = BalanceResponse.parse_obj(data)
        except ValidationError as ve:
            self.logger.error(f"잔고 응답 파싱 실패: {ve.json()}")
            return None

        if parsed.rt_cd != "0":
            self.logger.error(f"잔고 조회 실패 (rt_cd={parsed.rt_cd}, msg1={parsed.msg1})")
            return None

        return parsed

    def _get_cash_balance(self) -> float:
        """
        잔고 조회 결과를 통해 '현금 잔액'을 추출.
        해당 API(v1_해외주식-006)에는 현금 잔액이 직접 제공되지 않으므로,
        output2.frcr_buy_amt_smtl1 (외화매수금액합계1)와
        output1 항목들의 market_value(현재가×수량)을 이용하여
        대략적 '사용 가능한 현금'을 추정할 수 있습니다.

        여기서는 간단히 'output2.frcr_buy_amt_smtl1 - sum(output1.market_value)' 로 계산합니다.
        (이 방식은 실제 잔고와 다를 수 있으므로, 정밀한 현금 조회가 필요할 땐 별도 API 사용 권장)
        """
        bal_resp = self._get_balance_response()
        if bal_resp is None:
            return 0.0

        # 1) output1: 각 종목의 ovrs_stck_evlu_amt 합산 → total_stock_value
        total_stock_value = 0.0
        for item in bal_resp.output1:
            try:
                market_val = float(item.ovrs_stck_evlu_amt)
            except Exception:
                market_val = 0.0
            total_stock_value += market_val

        # 2) output2.frcr_buy_amt_smtl1: 외화매수금액합계1 (총매입원금)
        try:
            total_cost = float(bal_resp.output2.frcr_buy_amt_smtl1)
        except Exception:
            total_cost = 0.0

        # 3) 단순 추정: (총매입원금 - 주식평가금액)이 현금 잔액에 가깝다고 가정
        cash_estimate = total_cost - total_stock_value
        return max(cash_estimate, 0.0)

    def _get_price(self, symbol: str) -> Optional[float]:
        """
        v1_해외주식-009 (현재체결가) API 호출
        """
        tr_id = "HHDFS00000300"
        headers = self._build_header(tr_id)
        if headers is None:
            return None

        exch_map = {
            "NASD": "NAS",  # 나스닥(주간)
            "NYSE": "NYS",
            "AMEX": "AMS",
            "TKSE": "TSE",
            "SEHK": "HKS",
            "SHAA": "SHS",
            "SZAA": "SZS",
            "HASE": "HNX",
            "VNSE": "HSX",
        }
        EXCD = exch_map.get(self.OVRS_EXCG_CD, self.OVRS_EXCG_CD)

        params = {
            "AUTH": "",
            "EXCD": EXCD,
            "SYMB": symbol
        }

        base = self.DOMAIN_MOCK if self.use_mock else self.DOMAIN_REAL
        url = f"{base}{self.PRICE_PATH}"
        try:
            resp = requests.get(url, headers=headers, params=params)
            data = resp.json()
        except Exception as e:
            self.logger.exception(f"{symbol} 현재가 조회 중 HTTP 에러 발생")
            return None

        try:
            parsed = PriceResponse.parse_obj(data)
        except ValidationError as ve:
            self.logger.error(f"{symbol} 현재가 응답 파싱 실패: {ve.json()}")
            return None

        if parsed.rt_cd != "0":
            self.logger.error(f"{symbol} 현재가 조회 실패 (rt_cd={parsed.rt_cd}, msg1={parsed.msg1})")
            return None

        try:
            return float(parsed.output.last)
        except Exception:
            self.logger.error(f"{symbol} 현재가 변환 오류: {parsed.output.last}")
            return None

    def _get_current_holdings(self) -> Dict[str, dict]:
        """
        현재 보유 중인 종목과 수량, 가격, 평가금액 반환 + 현금 잔액 포함
        """
        bal_resp = self._get_balance_response()
        if not bal_resp:
            self.logger.error("잔고 조회 실패, 리밸런싱 중단")
            return {}

        holdings: Dict[str, dict] = {}
        stock_total = 0.0

        for item in bal_resp.output1:
            code = item.ovrs_pdno
            qty = int(item.ovrs_cblc_qty)
            if qty <= 0:
                continue

            current_price = self._get_price(code)
            if current_price is None:
                self.logger.warning(f"{code} 현재가 조회 실패, 해당 종목 제외")
                continue

            market_value = current_price * qty
            holdings[code] = {
                "qty": qty,
                "market_value": market_value,
                "current_price": current_price
            }
            stock_total += market_value

        # 현금 잔액 추정
        cash = self._get_cash_balance()

        holdings["__cash__"] = cash
        holdings["__total_value__"] = stock_total + cash
        return holdings

    def _compute_trade_orders(self, holdings: Dict[str, dict]) -> list[dict]:
        """
        목표 비율(self.weights)과 현재 보유 비율 비교 → 매수/매도 주문 목록 생성
        """
        total_value = holdings.get("__total_value__", 0.0)
        orders: list[dict] = []

        for code, weight in self.weights.items():
            target_value = total_value * weight
            current = holdings.get(code, {"qty": 0, "market_value": 0.0, "current_price": 0.0})
            current_value = current["market_value"]
            current_price = current["current_price"]

            delta_value = target_value - current_value

            if current_price <= 0:
                continue

            delta_qty = math.floor(abs(delta_value) / current_price)
            if delta_qty < 1:
                continue

            if delta_value > 0:
                max_affordable = math.floor(holdings["__cash__"] / current_price)
                buy_qty = min(delta_qty, max_affordable)
                if buy_qty > 0:
                    orders.append({
                        "code": code,
                        "side": "BUY",
                        "qty": buy_qty,
                        "price": int(current_price)
                    })
            else:
                sell_qty = min(delta_qty, current["qty"])
                if sell_qty > 0:
                    orders.append({
                        "code": code,
                        "side": "SELL",
                        "qty": sell_qty,
                        "price": int(current_price)
                    })

        return orders

    def rebalance(self):
        """
        1) 토큰 발급 → acct_mgr.token, order_mgr.token 설정
        2) 현재 보유 및 현금 조회 → holdings dict
        3) 주문 목록 계산 → orders list
        4) 주문 전송
        """
        token = self._get_token()
        self.acct_mgr.token  = token
        self.order_mgr.token = token

        holdings = self._get_current_holdings()
        if not holdings:
            return

        orders_to_send = self._compute_trade_orders(holdings)

        for order in orders_to_send:
            code = order["code"]
            side = order["side"]
            qty = order["qty"]
            price = order["price"]

            is_buy = (side == "BUY")
            self.logger.info(f"{side} 주문 → 종목: {code}, 수량: {qty}, 가격: {price}")

            order_id = self.order_mgr.create_order(
                is_buy=is_buy,
                CANO=self.CANO,
                ACNT_PRDT_CD=self.ACNT_PRDT_CD,
                OVRS_EXCG_CD=self.OVRS_EXCG_CD,
                PDNO=code,
                ORD_QTY=qty,
                OVRS_ORD_UNPR=price,
                order_type="리밸런싱" + ("매수" if is_buy else "매도"),
                name=code,
                qty=qty,
                price=price
            )
            if order_id:
                self.logger.info(f"{side} 주문 전송 성공: {order_id}")
            else:
                self.logger.error(f"{side} 주문 전송 실패: {code}")

    def close(self):
        """
        매니저 정리
        """
        self.acct_mgr.close()
        self.order_mgr.close()


# ─────────────────────────────────────────────────────────────────────────
# 직접 실행 시 리밸런싱 수행
# ─────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    logger = logging.getLogger("rebalancer")

    reb = Rebalancer()
    try:
        reb.rebalance()
        logger.info("리밸런싱 완료")
    except Exception:
        logger.exception("리밸런싱 중 예외 발생")
    finally:
        reb.close()
        logger.info("리밸런서 종료")
