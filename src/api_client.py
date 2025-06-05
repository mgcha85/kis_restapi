import requests
import logging
import os
import yaml
from dotenv import load_dotenv

load_dotenv()  


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

def update_env_token(env_path: str, new_token: str) -> None:
    """
    .env 파일에서 KIS_OAUTH_TOKEN 항목을 찾아 new_token으로 갱신합니다.
    없다면 맨 끝에 추가합니다.
    """
    if not os.path.exists(env_path):
        # .env 파일이 없으면 생성하고 토큰만 추가
        with open(env_path, "w", encoding="utf-8") as f:
            f.write(f'KIS_OAUTH_TOKEN="{new_token}"\n')
        return

    # 기존 .env 내용을 읽어서 교체 혹은 추가
    lines = []
    found = False
    with open(env_path, "r", encoding="utf-8") as f:
        for raw in f.readlines():
            line = raw.rstrip("\n")
            if line.startswith("KIS_OAUTH_TOKEN="):
                lines.append(f'KIS_OAUTH_TOKEN="{new_token}"')
                found = True
            else:
                lines.append(line)
    if not found:
        # 토큰 항목이 없으면 맨 끝에 추가
        lines.append(f'KIS_OAUTH_TOKEN="{new_token}"')

    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    # 로깅 설정
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )
    logger = logging.getLogger("api_client_test")

    # config.yaml에서 api_key, app_secret 읽기
    BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
    CONFIG_PATH = os.path.join(BASE_DIR, "..", "config", "config.yaml")
    ENV_PATH = os.path.join(BASE_DIR, "..", ".env")

    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        trading_cfg = cfg.get("trading", {})

        # .env에서 api_key, app_secret 읽기
        api_key    = os.getenv("KIS_API_KEY")
        app_secret = os.getenv("KIS_APP_SECRET")
    except Exception as e:
        logger.exception(f"설정 로드 실패: {e}")
        exit(1)

    # APIClient 인스턴스 생성
    client = APIClient(api_key=api_key, app_secret=app_secret)

    logger.info("OAuth 토큰 발급 테스트 시작")
    token = client.get_oauth_token()
    if token:
        logger.info(f"발급된 토큰: {token}")
        update_env_token(ENV_PATH, token)
        logger.info(f".env 파일에 KIS_OAUTH_TOKEN 갱신 완료: {ENV_PATH}")

    else:
        logger.error("토큰 발급 실패")
