# main.py

import logging
from rebalancer import Rebalancer

if __name__ == "__main__":
    # 로깅 설정 (원하는 포맷/레벨로 조정하세요)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    )

    logger = logging.getLogger("main")
    logger.info("리밸런서 시작")

    reb = Rebalancer()
    try:
        reb.rebalance()
        logger.info("리밸런싱 완료")
    except Exception as e:
        logger.exception("리밸런싱 중 예외 발생")
    finally:
        reb.close()
        logger.info("리밸런서 종료")
