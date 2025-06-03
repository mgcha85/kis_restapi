import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
from .models import Base

# .env 파일을 불러옵니다.
load_dotenv()  

# .env에서 개별 변수 읽어오기 (없다면 기본값 사용)
POSTGRES_USER     = os.getenv("POSTGRES_USER", "username")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "password")
POSTGRES_DB       = os.getenv("POSTGRES_DB", "mydatabase")
POSTGRES_HOST     = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT     = os.getenv("POSTGRES_PORT", "5432")

# 만약 DATABASE_URL이 .env나 환경변수로 이미 정의되어 있으면 그것을 우선 사용
default_url = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
DATABASE_URL = os.getenv("DATABASE_URL", default_url)

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """
    데이터베이스에 테이블이 없으면 모두 생성합니다.
    """
    Base.metadata.create_all(bind=engine)