import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base

# 환경변수나 설정파일에서 DATABASE_URL을 읽어오도록 설정할 수 있습니다.
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://username:password@localhost:5432/mydatabase')

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    """
    데이터베이스에 테이블이 없으면 모두 생성합니다.
    """
    Base.metadata.create_all(bind=engine)
