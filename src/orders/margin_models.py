from typing import List, Optional
from pydantic import BaseModel, Field


class MarginOutput(BaseModel):
    natn_name: str                    = Field(..., alias="natn_name", description="국가명")
    crcy_cd: str                      = Field(..., alias="crcy_cd", description="통화코드")
    frcr_dncl_amt1: str               = Field(..., alias="frcr_dncl_amt1", description="외화예수금액")
    ustl_buy_amt: str                 = Field(..., alias="ustl_buy_amt", description="미결제매수금액")
    ustl_sll_amt: str                 = Field(..., alias="ustl_sll_amt", description="미결제매도금액")
    frcr_rcvb_amt: str                = Field(..., alias="frcr_rcvb_amt", description="외화미수금액")
    frcr_mgn_amt: str                 = Field(..., alias="frcr_mgn_amt", description="외화증거금액")
    frcr_gnrl_ord_psbl_amt: str       = Field(..., alias="frcr_gnrl_ord_psbl_amt", description="외화일반주문가능금액")
    frcr_ord_psbl_amt1: str           = Field(..., alias="frcr_ord_psbl_amt1", description="외화주문가능금액")
    itgr_ord_psbl_amt: str            = Field(..., alias="itgr_ord_psbl_amt", description="통합주문가능금액")
    bass_exrt: str                    = Field(..., alias="bass_exrt", description="기준환율")

    class Config:
        allow_population_by_field_name = True
        allow_population_by_alias      = True


class MarginResponse(BaseModel):
    rt_cd: str                        = Field(..., alias="rt_cd", description="성공 실패 여부 (0: 성공)")
    msg_cd: str                       = Field(..., alias="msg_cd", description="응답코드")
    msg1: str                         = Field(..., alias="msg1", description="응답메시지")
    output: List[MarginOutput]        = Field(..., alias="output", description="응답상세 리스트")

    class Config:
        allow_population_by_field_name = True
        allow_population_by_alias      = True
