# src/models.py

from typing import Optional
from pydantic import BaseModel, Field


# -------------------------------------------
# 1) 요청 헤더 모델 (RequestHeader)
# -------------------------------------------
class RequestHeader(BaseModel):
    content_type: Optional[str] = Field(
        default=None,
        alias="content-type",
        description="컨텐츠타입 (예: application/json; charset=UTF-8)"
    )
    authorization: str = Field(
        ...,
        description="OAuth 토큰 (Bearer <token>)"
    )
    appkey: str = Field(
        ...,
        description="한국투자증권에서 발급받은 appkey"
    )
    appsecret: str = Field(
        ...,
        description="한국투자증권에서 발급받은 appsecret"
    )
    personalseckey: Optional[str] = Field(
        default=None,
        description="법인고객 전용 고객식별키"
    )
    tr_id: str = Field(
        ...,
        description="거래 ID (예: 실전 미국 매수: TTTT1002U, 모의: VTTT1002U)"
    )
    tr_cont: Optional[str] = Field(
        default=None,
        description="연속 거래 여부 (F, M, D, E 등)"
    )
    custtype: Optional[str] = Field(
        default=None,
        description="고객 타입 (P: 개인, B: 법인)"
    )
    seq_no: Optional[str] = Field(
        default=None,
        description="일련번호 (법인 전용)"
    )
    mac_address: Optional[str] = Field(
        default=None,
        description="Mac 주소 (법인·개인)"
    )
    phone_number: Optional[str] = Field(
        default=None,
        description="핸드폰번호 (법인 전용, 하이픈 제외)"
    )
    ip_addr: Optional[str] = Field(
        default=None,
        description="접속 단말 공인 IP (법인 전용)"
    )
    hashkey: Optional[str] = Field(
        default=None,
        description="HashKey (옵션)"
    )
    gt_uid: Optional[str] = Field(
        default=None,
        description="법인 전용 거래고유번호 (Unique)"
    )

    class Config:
        allow_population_by_field_name = True
        # alias를 “content-type”으로 썼을 때 .dict(by_alias=True)로 JSON 직렬화 가능
        # ex) header_model.dict(by_alias=True, exclude_none=True)


# -------------------------------------------
# 2) 요청 바디 모델 (RequestBody)
# -------------------------------------------
class RequestBody(BaseModel):
    CANO: str = Field(..., description="종합계좌번호 (8자리)")
    ACNT_PRDT_CD: str = Field(..., description="계좌상품코드 (뒤 2자리)")
    OVRS_EXCG_CD: str = Field(..., description="해외거래소코드 (예: NASD, NYSE)")
    PDNO: str = Field(..., description="상품번호 (종목코드, 예: AAPL)")
    ORD_QTY: str = Field(..., description="주문수량 (실수는 허용되지 않음)")
    OVRS_ORD_UNPR: str = Field(..., description="해외주문단가 (지정가 주문 시 1주당 가격)")
    CTAC_TLNO: Optional[str] = Field(
        default=None,
        description="연락전화번호 (옵션)"
    )
    MGCO_APTM_ODNO: Optional[str] = Field(
        default=None,
        description="운용사지정주문번호 (옵션)"
    )
    SLL_TYPE: Optional[str] = Field(
        default=None,
        description="판매유형 (제거: 매수, 00: 매도 등)"
    )
    ORD_SVR_DVSN_CD: str = Field(..., description="주문서버구분코드 (항상 '0')")
    ORD_DVSN: str = Field(..., description="주문구분 (예: '00' 지정가)")
    START_TIME: Optional[str] = Field(
        default=None,
        description="TWAP/VWAP 시작시간 (YYMMDDHHMMSS)"
    )
    END_TIME: Optional[str] = Field(
        default=None,
        description="TWAP/VWAP 종료시간 (YYMMDDHHMMSS)"
    )
    ALGO_ORD_TMD_DVSN_CD: Optional[str] = Field(
        default=None,
        description="알고리즘 주문 시간 구분코드 (00, 02 등)"
    )

    class Config:
        # JSON을 그대로 모델로 넣을 때 대문자 필드명이 그대로 매핑되도록 함
        allow_population_by_field_name = True
        # Pydantic이 JSON key를 CamelCase나 대문자 형식으로 쓸 수 있도록 허용


# -------------------------------------------
# 3) 응답 헤더 모델 (ResponseHeader)
# -------------------------------------------
class ResponseHeader(BaseModel):
    content_type: str = Field(
        ..., alias="content-type", description="컨텐츠타입 (application/json; charset=UTF-8)"
    )
    tr_id: str = Field(..., description="거래ID")
    tr_cont: str = Field(..., description="연속 거래 여부")
    gt_uid: str = Field(..., description="법인 전용 거래고유번호")

    class Config:
        allow_population_by_field_name = True


# -------------------------------------------
# 4) 응답 바디 중첩 모델 (ResponseBodyOutput)
# -------------------------------------------
class ResponseBodyOutput(BaseModel):
    KRX_FWDG_ORD_ORGNO: str = Field(..., description="한국거래소 전송주문조직번호")
    ODNO: str = Field(..., description="주문번호")
    ORD_TMD: str = Field(..., description="주문시각 (HHMMSS)")

    class Config:
        allow_population_by_field_name = True


# -------------------------------------------
# 5) 응답 바디 모델 (ResponseBody)
# -------------------------------------------
class ResponseBody(BaseModel):
    rt_cd: str = Field(..., description="성공 실패 여부 (0: 성공, 그 외: 실패)")
    msg_cd: str = Field(..., description="응답코드")
    msg1: str = Field(..., description="응답메시지")
    output: ResponseBodyOutput = Field(..., description="응답 상세 데이터")

    class Config:
        allow_population_by_field_name = True
