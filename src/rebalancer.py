import requests
import logging

class APIClient:
    def __init__(self, api_key, app_secret, token_url="https://openapi.koreainvestment.com:9443/oauth2/tokenP"):
        self.api_key = api_key
        self.app_secret = app_secret
        self.token_url = token_url
        self.logger = logging.getLogger(__name__)
    
    def get_oauth_token(self):
        """
        OAuth2.0 클라이언트 크레덴셜 방식을 이용해 접근 토큰을 발급받습니다.
        """
        payload = {
            "grant_type": "client_credentials",
            "appkey": self.api_key,
            "appsecret": self.app_secret
        }
        headers = {
            "Content-Type": "application/json; charset=UTF-8"
        }
        try:
            response = requests.post(self.token_url, json=payload, headers=headers)
            data = response.json()
            token = data.get("access_token")
            if token:
                self.logger.info("OAuth 토큰 발급 성공")
                return token
            else:
                self.logger.error("토큰 발급 실패: " + data.get("msg1", "응답 메시지 없음"))
                return None
        except Exception as e:
            self.logger.exception("토큰 발급 중 예외 발생")
            return None
