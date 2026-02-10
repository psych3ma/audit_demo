"""프로젝트 전역 설정 모듈.

- OpenAI 모델명
- 백엔드 API 주소 (Streamlit → FastAPI 호출용)
- .env 파일에서 OPENAI_API_KEY 등 환경변수 불러오기
"""

import os

from dotenv import load_dotenv


# 프로젝트 루트의 .env 파일을 자동으로 읽어옵니다.
# (.env 파일이 없어도 에러는 나지 않습니다.)
load_dotenv()


# === OpenAI 모델 설정 =====================================================

# 그래프 추출(단계 1)에 사용할 모델
DEFAULT_MODEL_GRAPH = "gpt-4.1-mini"

# 전문가 리포트(단계 3)에 사용할 모델
DEFAULT_MODEL_ANALYSIS = "gpt-4.1-mini"

OPENAI_MODEL_GRAPH = os.getenv("OPENAI_MODEL_GRAPH", DEFAULT_MODEL_GRAPH)
OPENAI_MODEL_ANALYSIS = os.getenv("OPENAI_MODEL_ANALYSIS", DEFAULT_MODEL_ANALYSIS)


# === 백엔드 API 주소 (Streamlit → FastAPI) ==================================

# 기본 개발용 주소: 로컬에서 uvicorn 실행 시
DEFAULT_BACKEND_URL = "http://127.0.0.1:8000"

BACKEND_URL = os.getenv("BACKEND_URL", DEFAULT_BACKEND_URL)

