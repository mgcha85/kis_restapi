import math
import logging
import requests

from typing import Optional, Dict
from pydantic import BaseModel, Field, ValidationError

from orders.account_manager import AccountManager
from orders.order_manager   import OrderManager
from orders.margin_manager  import MarginManager
from src.orders.order_models import RequestHeader

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
    rt_cd: str         = Field(..., alias="rt_cd", description="성공 실패 여부 (0: 성공)")
    msg_cd: str        = Field(..., alias="msg_cd", description="응답코드")
    msg1: str          = Field(..., alias="msg1", description="응답메시지")
    output: PriceOutput = Field(..., alias="output", description="응답상세")

    class Config:
        allow_population_by_field_name = True
        allow_population_by_alias      = True


# ─────────────────────────────────────────────────────────────────────────
# 2) Rebalancer 클래스 (AccountManager, OrderManager, MarginManager 상속)
# ─────────────────────────────────────────────────────────────────────────
class Rebalancer(AccountManager, OrderManager, MarginManager):
    def __init__(self):
        # 부모 초기화 순서대로 호출
        AccountManager.__init__(self)
        OrderManager.__init__(self)
        MarginManager.__init__(self)

        # config.yaml에서 strategy 섹션 읽기 (weights만)
        strategy_cfg = self.cfg.get("strategy", {})
        self.weights = strategy_cfg.get("weights", {})

        # Price API 엔드포인트 로드 (path 섹션 사용)
        path_cfg        = self.PATH_CFG
        self.DOMAIN_REAL = path_cfg.get("real", "https://openapi.koreainvestment.com:9443")
        self.DOMAIN_MOCK = path_cfg.get("mock", "https://openapivts.koreainvestment.com:29443")
        self.PRICE_PATH  = "/uapi/overseas-price/v1/quotations/price"

        self.logger = logging.getLogger(__name__)

    def _get_token(self) -> str:
        """
        OAuth 토큰 발급 로직.
        실제로는 APIClient.get_oauth_token() 등을 호출하여 반환해야 합니다.
        """
        # TODO: APIClient.get_oauth_token() 호출 후 토큰 반환
        return "YOUR_BEARER_TOKEN"

    def _build_price_header(self, tr_id: str) -> Optional[dict]:
        """
        Price API 호출 시 필요한 헤더 생성
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
            self.logger.error(f"[Rebalancer] Price Header 검증 실패: {ve.json()}")
            return None

        return header_model.dict(by_alias=True, exclude_none=True)

    def _get_price(self, symbol: str) -> Optional[float]:
        """
        v1_해외주식-009 (현재체결가) API 호출하여 해당 종목의 현재가를 반환.
        """
        tr_id = "HHDFS00000300"
        headers = self._build_price_header(tr_id)
        if headers is None:
            return None

        exch_map = {
            "NASD": "NAS",
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
        except Exception:
            self.logger.exception(f"[Rebalancer] {symbol} 현재가 조회 중 HTTP 에러 발생")
            return None

        try:
            parsed = PriceResponse.parse_obj(data)
        except ValidationError as ve:
            self.logger.error(f"[Rebalancer] {symbol} 현재가 응답 파싱 실패: {ve.json()}")
            return None

        if parsed.rt_cd != "0":
            self.logger.error(f"[Rebalancer] {symbol} 현재가 조회 실패 (rt_cd={parsed.rt_cd}, msg1={parsed.msg1})")
            return None

        try:
            return float(parsed.output.last)
        except Exception:
            self.logger.error(f"[Rebalancer] {symbol} 현재가 변환 오류: {parsed.output.last}")
            return None

    def _get_current_holdings(self) -> Dict[str, dict]:
        """
        현재 보유 중인 종목과 수량, 가격, 평가금액을 반환.
        또한, MarginManager.get_usd_available_cash()로 가져온 'USD 예수금'을 현금으로 포함.
        """
        # 1) 잔고 조회 (AccountManager)
        balance_resp = self.get_balance()
        if not balance_resp:
            self.logger.error("[Rebalancer] 잔고 조회 실패, 리밸런싱 중단")
            return {}

        holdings: Dict[str, dict] = {}
        stock_total = 0.0

        for item in balance_resp.output1:
            code = item.ovrs_pdno
            qty = int(item.ovrs_cblc_qty)
            if qty <= 0:
                continue

            current_price = self._get_price(code)
            if current_price is None:
                self.logger.warning(f"[Rebalancer] {code} 현재가 조회 실패, 해당 종목 제외")
                continue

            market_value = current_price * qty
            holdings[code] = {
                "qty": qty,
                "market_value": market_value,
                "current_price": current_price
            }
            stock_total += market_value

        # 2) USD 예수금 조회 (MarginManager)
        usd_cash = self.get_usd_available_cash()

        holdings["__cash__"]       = usd_cash
        holdings["__total_stock__"] = stock_total
        holdings["__total_value__"] = stock_total + usd_cash
        return holdings

    def _compute_and_execute_trades(self, holdings: Dict[str, dict]):
        """
        1) 목표 비율 대비 현재 가치 차이 계산
        2) 매도 주문 실행 → 현금 증가 및 보유량 업데이트
        3) 매수 주문 실행 → 현금 감소
        """
        total_stock = holdings["__total_stock__"]
        cash        = holdings["__cash__"]
        total_value = holdings["__total_value__"]

        # 보유 종목 리스트
        codes = list(self.weights.keys())
        n = len(codes)

        # 1) 목표 가치 계산 (equal weight 혹은 config.yaml의 weight 사용)
        # 총 value 기준으로 각 목표값
        target_values: Dict[str, float] = {}
        for code, weight in self.weights.items():
            target_values[code] = total_value * weight

        # 2) 차이 계산: diff = target - current
        diffs: Dict[str, float] = {}
        for code in codes:
            current = holdings.get(code, {"market_value": 0.0})
            diffs[code] = target_values[code] - current["market_value"]

        # 3) 매도 주문 생성 및 실행 (diff < 0)
        for code, diff in diffs.items():
            if diff >= 0:
                continue
            current_price = holdings[code]["current_price"]
            sell_qty = math.floor(abs(diff) / current_price)
            if sell_qty < 1:
                continue

            self.logger.info(f"[Rebalancer] 매도 주문 → 종목: {code}, 수량: {sell_qty}, 가격(시장가): {current_price}")
            order_id = self.create_order(
                is_buy=False,
                CANO=self.CANO,
                ACNT_PRDT_CD=self.ACNT_PRDT_CD,
                OVRS_EXCG_CD=self.OVRS_EXCG_CD,
                PDNO=code,
                ORD_QTY=sell_qty,
                OVRS_ORD_UNPR=int(current_price),
                order_type="리밸런싱 매도",
                name=code,
                qty=sell_qty,
                price=int(current_price)
            )
            if order_id:
                self.logger.info(f"[Rebalancer] 매도 주문 전송 성공: {order_id}")
            else:
                self.logger.error(f"[Rebalancer] 매도 주문 전송 실패: {code}")
                continue

            # 매도 완료 가정: 현금 증가, 보유량 감소
            cash += sell_qty * current_price
            holdings[code]["qty"] -= sell_qty
            holdings[code]["market_value"] = holdings[code]["qty"] * current_price
            self.logger.info(f"[Rebalancer] 매도 후 예수금: {cash}, {code} 잔여 수량: {holdings[code]['qty']}")

        # 4) 매수 주문 생성 및 실행 (diff > 0)
        for code, diff in diffs.items():
            if diff <= 0:
                continue
            current_price = holdings.get(code, {"current_price": 0.0})["current_price"]
            if current_price <= 0:
                continue

            buy_qty = math.floor(diff / current_price)
            if buy_qty < 1:
                continue

            max_affordable = math.floor(cash / current_price)
            buy_qty = min(buy_qty, max_affordable)
            if buy_qty < 1:
                continue

            self.logger.info(f"[Rebalancer] 매수 주문 → 종목: {code}, 수량: {buy_qty}, 가격(시장가): {current_price}")
            order_id = self.create_order(
                is_buy=True,
                CANO=self.CANO,
                ACNT_PRDT_CD=self.ACNT_PRDT_CD,
                OVRS_EXCG_CD=self.OVRS_EXCG_CD,
                PDNO=code,
                ORD_QTY=buy_qty,
                OVRS_ORD_UNPR=int(current_price),
                order_type="리밸런싱 매수",
                name=code,
                qty=buy_qty,
                price=int(current_price)
            )
            if order_id:
                self.logger.info(f"[Rebalancer] 매수 주문 전송 성공: {order_id}")
            else:
                self.logger.error(f"[Rebalancer] 매수 주문 전송 실패: {code}")
                continue

            # 매수 완료 가정: 현금 감소, 보유량 증가
            cost = buy_qty * current_price
            cash -= cost
            if code in holdings:
                holdings[code]["qty"] += buy_qty
                holdings[code]["market_value"] = holdings[code]["qty"] * current_price
            else:
                holdings[code] = {
                    "qty": buy_qty,
                    "market_value": cost,
                    "current_price": current_price
                }
            self.logger.info(f"[Rebalancer] 매수 후 예수금: {cash}, {code} 보유량: {holdings[code]['qty']}")

        # 최종 예수금 및 포트폴리오 가치를 로그에 남김
        final_stock_value = sum(v["market_value"] for k, v in holdings.items() if k not in ["__cash__", "__total_stock__", "__total_value__"])
        self.logger.info(f"[Rebalancer] 최종 예수금: {cash}, 최종 주식 평가금액 합계: {final_stock_value}")

    def rebalance(self):
        """
        1) 토큰 발급 후 self.token 설정
        2) 현재 보유 조회 (주식 + USD 예수금)
        3) 매도 → 매수 순서로 주문 실행
        """
        # 1) 토큰 발급
        token = self._get_token()
        self.token = token

        # 2) 현재 보유 조회
        holdings = self._get_current_holdings()
        if not holdings:
            return

        # 3) 매도·매수 실행
        self._compute_and_execute_trades(holdings)

    def close(self):
        """
        AccountManager, OrderManager, MarginManager 정리
        """
        self.session.close()  # AccountManager와 OrderManager가 SessionLocal 사용
        # MarginManager는 별도 세션 없음


# ─────────────────────────────────────────────────────────────────────────
# 직접 실행 시 리밸런싱 수행
# ─────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    reb = Rebalancer()
    try:
        reb.rebalance()
        reb.logger.info("리밸런싱 완료")
    except Exception:
        reb.logger.exception("리밸런싱 중 예외 발생")
    finally:
        reb.close()
        reb.logger.info("리밸런서 종료")
