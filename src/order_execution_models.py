# src/order_execution_models.py

from typing import List, Optional
from pydantic import BaseModel, Field


# -------------------------------------------
# 1) 주문 체결 조회 응답 중첩 모델 (ResponseBodyOutput)
# -------------------------------------------
class ResponseBodyOutput(BaseModel):
    ord_dt: str               = Field(..., alias="ord_dt", description="주문일자 (YYYYMMDD)")
    ord_gno_brno: str         = Field(..., alias="ord_gno_brno", description="주문채번지점번호")
    odno: str                 = Field(..., alias="odno", description="주문번호")
    orgn_odno: str            = Field(..., alias="orgn_odno", description="원주문번호")
    sll_buy_dvsn_cd: str      = Field(..., alias="sll_buy_dvsn_cd", description="매도매수구분코드 (01: 매도 / 02: 매수)")
    sll_buy_dvsn_cd_name: str = Field(..., alias="sll_buy_dvsn_cd_name", description="매도매수구분코드명")
    rvse_cncl_dvsn: str       = Field(..., alias="rvse_cncl_dvsn", description="정정취소구분 (01: 정정 / 02: 취소)")
    rvse_cncl_dvsn_name: str  = Field(..., alias="rvse_cncl_dvsn_name", description="정정취소구분명")
    pdno: str                 = Field(..., alias="pdno", description="상품번호")
    prdt_name: str            = Field(..., alias="prdt_name", description="상품명")
    ft_ord_qty: str           = Field(..., alias="ft_ord_qty", description="FT주문수량")
    ft_ord_unpr3: str         = Field(..., alias="ft_ord_unpr3", description="FT주문단가3")
    ft_ccld_qty: str          = Field(..., alias="ft_ccld_qty", description="FT체결수량")
    ft_ccld_unpr3: str        = Field(..., alias="ft_ccld_unpr3", description="FT체결단가3")
    ft_ccld_amt3: str         = Field(..., alias="ft_ccld_amt3", description="FT체결금액3")
    nccs_qty: str             = Field(..., alias="nccs_qty", description="미체결수량")
    prcs_stat_name: str       = Field(..., alias="prcs_stat_name", description="처리상태명")
    rjct_rson: str            = Field(..., alias="rjct_rson", description="거부사유")
    ord_tmd: str              = Field(..., alias="ord_tmd", description="주문시각 (HHMMSS)")
    tr_mket_name: str         = Field(..., alias="tr_mket_name", description="거래시장명")
    tr_natn: str              = Field(..., alias="tr_natn", description="거래국가 코드")
    tr_natn_name: str         = Field(..., alias="tr_natn_name", description="거래국가명")
    ovrs_excg_cd: str         = Field(..., alias="ovrs_excg_cd", description="해외거래소코드")
    tr_crcy_cd: str           = Field(..., alias="tr_crcy_cd", description="거래통화코드")
    dmst_ord_dt: str          = Field(..., alias="dmst_ord_dt", description="국내주문일자")
    thco_ord_tmd: str         = Field(..., alias="thco_ord_tmd", description="당사주문시각")
    loan_type_cd: str         = Field(..., alias="loan_type_cd", description="대출유형코드")
    loan_dt: str              = Field(..., alias="loan_dt", description="대출일자")
    mdia_dvsn_name: str       = Field(..., alias="mdia_dvsn_name", description="매체구분명")
    usa_amk_exts_rqst_yn: str = Field(..., alias="usa_amk_exts_rqst_yn", description="미국애프터마켓연장신청여부 (Y/N)")
    splt_buy_attr_name: str   = Field(..., alias="splt_buy_attr_name", description="분할매수/매도속성명")

    class Config:
        allow_population_by_field_name = True
        allow_population_by_alias      = True


# -------------------------------------------
# 2) 최상위 주문 체결 조회 응답 모델 (ExecutionInquiryResponse)
# -------------------------------------------
class ExecutionInquiryResponse(BaseModel):
    rt_cd: str                   = Field(..., alias="rt_cd", description="성공 실패 여부 (0: 성공)")
    msg_cd: str                  = Field(..., alias="msg_cd", description="응답코드")
    msg1: str                    = Field(..., alias="msg1", description="응답메시지")
    ctx_area_fk200: str          = Field(..., alias="ctx_area_fk200", description="연속조회검색조건200")
    ctx_area_nk200: str          = Field(..., alias="ctx_area_nk200", description="연속조회키200")
    output: List[ResponseBodyOutput] = Field(..., alias="output", description="응답상세 리스트")

    class Config:
        allow_population_by_field_name = True
        allow_population_by_alias      = True
