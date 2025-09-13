# backend/app/database.py
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base
from google.cloud.sql.connector import Connector
import os
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./thefasthire.db")
GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT")
CLOUD_SQL_INSTANCE = os.getenv("CLOUD_SQL_INSTANCE")  # project:region:instance
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_NAME = os.getenv("DB_NAME")

Base = declarative_base()

def create_cloud_sql_engine():
    """Google Cloud SQL 연결 엔진 생성"""
    connector = Connector()
    
    def getconn():
        try:
            conn = connector.connect(
                CLOUD_SQL_INSTANCE,
                "pg8000",
                user=DB_USER,
                password=DB_PASSWORD,
                db=DB_NAME,
                enable_iam_auth=False  # 비밀번호 인증 사용
            )
            logger.info("Cloud SQL 연결 성공")
            return conn
        except Exception as e:
            logger.error(f"Cloud SQL 연결 실패: {e}")
            raise
    
    return create_engine(
        "postgresql+pg8000://",
        creator=getconn,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=300
    )

def create_local_engine():
    """로컬 데이터베이스 연결 엔진 생성"""
    if DATABASE_URL.startswith("sqlite"):
        return create_engine(
            DATABASE_URL, 
            connect_args={"check_same_thread": False}
        )
    else:
        # PostgreSQL 연결 (SSL 포함)
        connect_args = {}
        if "sslmode" not in DATABASE_URL:
            connect_args["sslmode"] = "require"
        
        return create_engine(
            DATABASE_URL,
            pool_pre_ping=True,
            pool_recycle=300,
            pool_size=10,
            max_overflow=20,
            connect_args=connect_args
        )

# 환경에 따른 엔진 선택
if CLOUD_SQL_INSTANCE and GOOGLE_CLOUD_PROJECT:
    logger.info("Google Cloud SQL 모드로 연결")
    engine = create_cloud_sql_engine()
else:
    logger.info("로컬 데이터베이스 모드로 연결")
    engine = create_local_engine()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    """데이터베이스 세션 의존성"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def test_db_connection():
    """데이터베이스 연결 테스트"""
    try:
        with engine.connect() as connection:
            result = connection.execute(text("SELECT 1"))
            logger.info("데이터베이스 연결 테스트 성공")
            return True
    except Exception as e:
        logger.error(f"데이터베이스 연결 테스트 실패: {e}")
        return False

def create_tables():
    """테이블 생성"""
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("테이블 생성 완료")
    except Exception as e:
        logger.error(f"테이블 생성 실패: {e}")
        raise
