#C:\Users\user\모든 개발\thefasthire\backend\app\main.py
import os
import logging
import sys
from pathlib import Path

from contextlib import asynccontextmanager
from dotenv import load_dotenv

# 환경변수 먼저 로드
load_dotenv()

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from .database import Base, engine
from .routers import user, interview, payment

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 시작 시 DB 테이블 생성
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    
     # 미디어 디렉토리 생성 - audio_service.py와 일관성 유지
    audio_dir = Path(os.getenv("AUDIO_DIR", "./media/audio"))
    audio_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Audio directory created: {audio_dir}")
    
    # 미디어 루트 디렉토리도 확인
    media_dir = Path(os.getenv("MEDIA_DIR", "./media"))
    media_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Media directory ready: {media_dir}")

    
    yield
    
    # 종료 시 정리 작업
    logger.info("Application shutting down...")


def validate_required_env_vars():
    """필수 환경변수 검증"""
    required_vars = [
        "OPENAI_API_KEY",
        "JWT_SECRET_KEY", 
        "DB_USER",
        "DB_PASSWORD",
        "DB_NAME"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not os.getenv(var):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.error("Please check your .env file or environment settings")
        sys.exit(1)
    
    logger.info("All required environment variables are set ✓")


app = FastAPI(
    title="thefasthire API",
    version="1.0.0",
    description="AI 기반 모의 면접 서비스",
    docs_url="/docs" if os.getenv("ENVIRONMENT") != "production" else None,
    redoc_url="/redoc" if os.getenv("ENVIRONMENT") != "production" else None,
    lifespan=lifespan
)

# CORS 설정 (환경변수 활용)
frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
allowed_origins = [frontend_origin]

# 추가 허용 도메인 (환경변수로 관리)
extra_origins = os.getenv("EXTRA_ORIGINS", "").split(",")
allowed_origins.extend([origin.strip() for origin in extra_origins if origin.strip()])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],  # 필요한 메소드만
    allow_headers=["*"],
)

# 전역 예외 처리
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code}
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": "입력 데이터를 확인해주세요.", "errors": exc.errors()}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "서버 내부 오류가 발생했습니다."}
    )

# 정적 파일 서빙 - 디버깅 로그 추가
media_dir = Path(os.getenv("MEDIA_DIR", "./media"))
logger.info(f"Mounting static files: /media -> {media_dir.absolute()}")

# 디렉토리 존재 확인
if not media_dir.exists():
    logger.error(f"Media directory does not exist: {media_dir}")
    media_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Created media directory: {media_dir}")

app.mount("/media", StaticFiles(directory=str(media_dir)), name="media")

# 라우터 등록
app.include_router(user.router, prefix="/users", tags=["users"])
app.include_router(interview.router, prefix="/interviews", tags=["interviews"])  
app.include_router(payment.router, prefix="/payments", tags=["payments"])

@app.get("/health", tags=["health"])
def health():
    """서버 상태 확인"""
    return {
        "status": "ok",
        "version": "1.0.0",
        "timestamp": "2025-09-02T11:11:00Z",
        "media_dir": str(media_dir.absolute()),  # 디버깅용 추가
        "audio_dir": str(Path(os.getenv("AUDIO_DIR", "./media/audio")).absolute())
    }
@app.get("/", include_in_schema=False)
def root():
    """루트 경로"""
    return {"message": "thefasthire API is running"}

# 디버깅용: 오디오 파일 목록 확인 엔드포인트 (개발 중에만 사용)
@app.get("/debug/audio-files", include_in_schema=False)
def list_audio_files():
    """오디오 파일 목록 확인 (디버깅용)"""
    if os.getenv("ENVIRONMENT") == "production":
        return {"message": "Not available in production"}
    
    audio_dir = Path(os.getenv("AUDIO_DIR", "./media/audio"))
    if not audio_dir.exists():
        return {"error": "Audio directory not found", "path": str(audio_dir.absolute())}
    
    files = list(audio_dir.glob("*.mp3"))
    return {
        "audio_dir": str(audio_dir.absolute()),
        "files": [f.name for f in files],
        "count": len(files)
    }
