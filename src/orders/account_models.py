# src/account_models.py

from typing import List, Optional
from pydantic import BaseModel, Field


# -------------------------------------------
# 1) 계좌 잔고 조회 응답 중첩 모델 (ResponseBodyOutput1)
# -------------------------------------------
class ResponseBodyOutput1(BaseModel):
    cano: str               = Field(..., description="종합계좌번호")
    acnt_prdt_cd: str       = Field(..., description="계좌상품코드")
    prdt_type_cd: str       = Field(..., description="상품유형코드")
    ovrs_pdno: str          = Field(..., description="해외상품번호")
    ovrs_item_name: str     = Field(..., description="해외종목명")
    frcr_evlu_pfls_amt: str = Field(..., description="외화평가손익금액")
    evlu_pfls_rt: str       = Field(..., description="평가손익율")
    pchs_avg_pric: str      = Field(..., description="매입평균가격")
    ovrs_cblc_qty: str      = Field(..., description="해외잔고수량")
    ord_psbl_qty: str       = Field(..., description="주문가능수량")
    frcr_pchs_amt1: str     = Field(..., description="외화매입금액1")
    ovrs_stck_evlu_amt: str = Field(..., description="해외주식평가금액")
    now_pric2: str          = Field(..., description="현재가격2")
    tr_crcy_cd: str         = Field(..., description="거래통화코드")
    ovrs_excg_cd: str       = Field(..., description="해외거래소코드")
    loan_type_cd: str       = Field(..., description="대출유형코드")
    loan_dt: str            = Field(..., description="대출일자")
    expd_dt: str            = Field(..., description="만기일자")

    class Config:
        allow_population_by_field_name = True
        allow_population_by_alias = True


# -------------------------------------------
# 2) 계좌 잔고 조회 응답 중첩 모델 (ResponseBodyOutput2)
# -------------------------------------------
class ResponseBodyOutput2(BaseModel):
    frcr_pchs_amt1: str       = Field(..., description="외화매입금액1")
    ovrs_rlzt_pfls_amt: str    = Field(..., description="해외실현손익금액")
    ovrs_tot_pfls: str         = Field(..., description="해외총손익")
    rlzt_erng_rt: str          = Field(..., description="실현수익율")
    tot_evlu_pfls_amt: str     = Field(..., description="총평가손익금액")
    tot_pftrt: str             = Field(..., description="총수익률")
    frcr_buy_amt_smtl1: str    = Field(..., description="외화매수금액합계1")
    ovrs_rlzt_pfls_amt2: str    = Field(..., description="해외실현손익금액2")
    frcr_buy_amt_smtl2: str    = Field(..., description="외화매수금액합계2")

    class Config:
        allow_population_by_field_name = True
        allow_population_by_alias = True


# -------------------------------------------
# 3) 최상위 잔고 조회 응답 모델 (BalanceInquiryResponse)
# -------------------------------------------
class BalanceInquiryResponse(BaseModel):
    rt_cd: str                            = Field(..., description="성공 실패 여부 (0: 성공)")
    msg_cd: str                           = Field(..., description="응답코드")
    msg1: str                             = Field(..., description="응답메시지")
    ctx_area_fk200: str                   = Field(..., description="연속조회검색조건200")
    ctx_area_nk200: str                   = Field(..., description="연속조회키200")
    output1: List[ResponseBodyOutput1]    = Field(..., description="응답상세1 리스트")
    output2: ResponseBodyOutput2          = Field(..., description="응답상세2 객체")

    class Config:
        allow_population_by_field_name = True
        allow_population_by_alias = True
