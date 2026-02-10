# Streamlit Community Cloud 배포 가이드

## 현재 상황

✅ **완료된 항목:**
- GitHub 원격 저장소 연결됨 (`https://github.com/psych3ma/audit_demo.git`)
- `requirements.txt` 파일 존재
- `frontend/main.py` 파일 존재
- README.md 변경사항 커밋 완료

⚠️ **필요한 작업:**
1. GitHub에 코드 push (인증 필요)
2. Streamlit Community Cloud에서 환경변수 설정
3. 배포 설정 확인

---

## 1단계: GitHub에 코드 Push

터미널에서 다음 명령어를 실행하세요:

```bash
cd /Users/coruscatio/Desktop/demo/audit_demo
git push origin main
```

인증이 필요하면:
- Personal Access Token 사용 또는
- SSH 키 설정 또는
- GitHub CLI (`gh auth login`) 사용

---

## 2단계: Streamlit Community Cloud 배포 설정

### 2-1. Streamlit Cloud 접속
1. https://share.streamlit.io 접속
2. GitHub 계정으로 로그인
3. "New app" 클릭

### 2-2. 저장소 선택
- Repository: `psych3ma/audit_demo` 선택
- Branch: `main` 선택
- Main file path: `frontend/main.py` 입력

### 2-3. 환경변수 설정 (중요!)
**Settings > Secrets**에서 다음 환경변수를 추가:

```
OPENAI_API_KEY=sk-...당신의키...
OPENAI_MODEL_GRAPH=gpt-4.1-mini
OPENAI_MODEL_ANALYSIS=gpt-4.1-mini
BACKEND_URL=https://your-backend-url.herokuapp.com
```

⚠️ **주의사항:**
- `.env` 파일은 GitHub에 올리지 마세요 (`.gitignore`에 포함되어 있음)
- 환경변수는 Streamlit Cloud의 Secrets에서만 설정하세요

---

## 3단계: 백엔드 배포 (선택사항)

현재 구조는 FastAPI 백엔드와 Streamlit 프론트엔드가 분리되어 있습니다.

### 옵션 1: 백엔드도 함께 배포
- **Heroku**: `backend/app.py`를 별도 앱으로 배포
- **Railway**: FastAPI 앱 배포
- **Render**: 무료 플랜으로 FastAPI 배포

배포 후 `BACKEND_URL` 환경변수를 업데이트하세요.

### 옵션 2: Streamlit만 배포 (프론트엔드만)
- 백엔드 없이 Streamlit만 배포할 경우, `frontend/main.py`에서 백엔드 호출 부분을 수정해야 합니다.
- 또는 로컬에서만 백엔드를 실행하고, Streamlit Cloud는 프론트엔드만 배포

---

## 4단계: 배포 확인

배포 후:
1. Streamlit Cloud에서 제공하는 URL로 접속
2. 환경변수가 제대로 로드되었는지 확인
3. API 호출이 정상 작동하는지 테스트

---

## 문제 해결

### 문제: "The app's code is not connected to a remote GitHub repository"
**해결:**
- GitHub에 코드가 push되어 있는지 확인
- Streamlit Cloud에서 올바른 저장소를 선택했는지 확인

### 문제: "ModuleNotFoundError"
**해결:**
- `requirements.txt`에 모든 의존성이 포함되어 있는지 확인
- Streamlit Cloud가 자동으로 설치하지만, 누락된 패키지가 있을 수 있음

### 문제: "API Key not found"
**해결:**
- Streamlit Cloud의 Secrets에 `OPENAI_API_KEY`가 설정되어 있는지 확인
- 환경변수 이름이 정확한지 확인 (대소문자 구분)

### 문제: "Backend connection failed"
**해결:**
- 백엔드가 배포되어 있고 접근 가능한지 확인
- `BACKEND_URL` 환경변수가 올바른지 확인
- CORS 설정이 올바른지 확인 (`backend/app.py`의 CORS 설정)

---

## 현재 프로젝트 구조 확인

```
audit_demo/
├── backend/
│   ├── app.py          # FastAPI 백엔드
│   └── services/
│       └── engine.py   # 비즈니스 로직
├── frontend/
│   └── main.py         # Streamlit 프론트엔드 ⭐ 배포 대상
├── common/
│   └── config.py       # 공통 설정
├── requirements.txt    # Python 의존성
└── README.md
```

**Streamlit Cloud 배포 시:**
- Main file: `frontend/main.py`
- Python version: 3.9+ (자동 감지)

---

## 다음 단계

1. ✅ GitHub에 push 완료
2. ⏳ Streamlit Cloud에서 앱 생성
3. ⏳ 환경변수 설정
4. ⏳ 배포 확인

배포 중 문제가 있으면 알려주세요!
