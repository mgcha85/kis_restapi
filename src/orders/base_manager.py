import os
import yaml


class BaseManager:
    """
    공통 설정 로드 및 기본 속성을 초기화하는 부모 클래스.
    모든 매니저는 이 클래스를 상속하여 config.yaml을 한 번만 읽도록 합니다.
    """

    def __init__(self):
        # 1) 환경변수에서 API 자격증명 읽기
        self._load_env_vars()

        # 2) config.yaml 로드
        self.cfg = self._load_config()

        # 3) trading 설정 읽기 (use_mock 등)
        self.use_mock = self._load_trading_config()

        # 4) path 설정 (domain, api path 등)
        self.DOMAIN_REAL, self.DOMAIN_MOCK, self.PATH_CFG = self._load_path_config()


    def _load_env_vars(self):
        """
        환경변수에서 API 키, 시크릿, 토큰을 읽어와 속성에 저장.
        """
        try:
            self.api_key    = os.getenv("KIS_API_KEY")
            self.app_secret = os.getenv("KIS_APP_SECRET")
            self.token      = os.getenv("KIS_OAUTH_TOKEN")
        except Exception as e:
            print(f"[BaseManager] 환경변수 로드 실패: {e}")
            exit(1)

    def _load_config(self) -> dict:
        """
        프로젝트 루트의 config/config.yaml 파일을 읽어와 파싱한 딕셔너리를 반환.
        """
        base_dir    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        config_path = os.path.join(base_dir, "config", "config.yaml")

        if not os.path.exists(config_path):
            raise FileNotFoundError(f"설정 파일을 찾을 수 없습니다: {config_path}")

        with open(config_path, "r", encoding="utf-8") as f:
            try:
                return yaml.safe_load(f)
            except Exception as e:
                print(f"[BaseManager] config.yaml 파싱 실패: {e}")
                exit(1)

    def _load_trading_config(self) -> bool:
        """
        config 딕셔너리의 'trading' 섹션에서 use_mock 플래그를 읽거나,
        외부 인자로 받은 use_mock_param이 우선 적용됨.
        """
        trading_cfg = self.cfg.get("trading", {})
        return trading_cfg.get("use_mock", False)

    def _load_path_config(self):
        """
        config 딕셔너리의 'path' 섹션에서 실전/모의 도메인과 API 경로 설정을 읽어 반환.
        """
        path_cfg     = self.cfg.get("path", {})
        domain_real  = path_cfg.get("real", "https://openapi.koreainvestment.com:9443")
        domain_mock  = path_cfg.get("mock", "https://openapivts.koreainvestment.com:29443")
        return domain_real, domain_mock, path_cfg
