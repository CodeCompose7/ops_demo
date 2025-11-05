# ML Prediction API Demo

DevOps/MLOps 강의를 위한 간단한 예측 API 데모 프로젝트입니다.
Docker 기반으로 구성되어 어디서나 동일하게 실행됩니다.

## 🎯 프로젝트 목적

이 프로젝트는 다음을 시연합니다:
- ✅ Docker를 활용한 일관된 실행 환경
- ✅ CI/CD 파이프라인 구성
- ✅ 자동화된 테스트 및 빌드
- ✅ 컨테이너 이미지 레지스트리 배포
- ✅ ML 모델 서빙을 위한 API 구조

## 🐳 Docker를 사용하는 이유

**"내 컴퓨터에서는 잘 되는데..."** 문제 해결!

개발자 A: Python 3.8, macOS
개발자 B: Python 3.11, Windows
서버: Python 3.9, Ubuntu
→ Docker 사용 시: 모두 동일한 환경! 🎉

## 🚀 빠른 시작

### 사전 요구사항
- Docker 설치 (https://www.docker.com/get-started)
- Docker Compose 설치 (Docker Desktop에 포함)

### 1. Docker Compose로 실행 (가장 간단!)
```bash
# 저장소 클론
git clone <repository-url>
cd ops_demo

# 애플리케이션 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f

# 종료
docker-compose down
```

서비스 접속: http://localhost:8000

### 2. Docker로 직접 실행
```bash
# 이미지 빌드
docker build -t ops_demo .

# 컨테이너 실행
docker run -d \
  --name ops \
  -p 8000:8000 \
  ops_demo

# 로그 확인
docker logs -f ops

# 종료
docker stop ops
docker rm ops
```

### 3. 개발 모드로 실행 (코드 변경 시 자동 반영)
```bash
docker-compose up
```

코드 수정 시 자동으로 서버가 재시작됩니다.

## 🧪 테스트 실행

### Docker Compose로 테스트
```bash
# 테스트만 실행
docker-compose --profile test run --rm test

# 결과 예시:
# ============================== test session starts ==============================
# collected 8 items
# tests/test_main.py ........                                              [100%]
# ============================== 8 passed in 0.45s ===============================
```

### 수동으로 테스트
```bash
# 테스트 컨테이너 실행
docker run --rm \
  -v $(pwd)/tests:/app/tests \
  -v $(pwd)/app:/app/app \
  ops_demo \
  sh -c "pip install pytest httpx pytest-cov && \
         pytest tests/ -v"
```

## 📊 API 엔드포인트

### GET /
API 정보 조회
```bash
curl http://localhost:8000/
```

### GET /health
헬스 체크
```bash
curl http://localhost:8000/health
```

### POST /predict
예측 수행
```bash
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"features": [5.1, 3.5, 1.4, 0.2]}'
```

**응답 예시:**
```json
{
  "prediction": 3.75,
  "model_version": "v1.0-simple"
}
```

### GET /model/info
모델 정보 조회
```bash
curl http://localhost:8000/model/info
```

### API 문서

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## 🔄 CI/CD 파이프라인

이 프로젝트는 GitHub Actions를 사용하여 완전 자동화된 CI/CD를 구현합니다:

### 파이프라인 단계

```
코드 푸시/PR
↓
[1] 테스트 Job
├─ Docker 이미지 빌드
├─ 컨테이너에서 테스트 실행
└─ 커버리지 리포트 생성
↓
[2] 린트 Job
├─ 코드 스타일 검사
└─ 정적 분석
↓
[3] 빌드 & 배포 Job (main 브랜치만)
├─ Docker 이미지 빌드
├─ Docker Hub에 푸시
└─ 보안 스캔 (Trivy)
```

### 파이프라인 확인하기

1. GitHub 저장소의 **"Actions"** 탭 방문
2. 최근 실행된 워크플로우 확인
3. 각 Job별 상세 로그 확인 가능

### Docker Hub 배포

main 브랜치에 푸시하면 자동으로:
- Docker 이미지 빌드
- Docker Hub에 푸시
- `latest` 태그와 커밋 SHA 태그 생성

```bash
# 배포된 이미지 사용
docker pull <your-dockerhub-username>/ops_demo:latest
docker run -p 8000:8000 <your-dockerhub-username>/ops_demo:latest
```

## 🎓 MLOps로 확장하기

### 현재 구조의 장점

✅ **컨테이너화**: 어디서나 동일하게 실행
✅ **API 기반**: 모델을 서비스로 제공
✅ **자동화된 테스트**: 품질 보장
✅ **CI/CD 파이프라인**: 빠른 배포

### 실제 ML 모델로 확장하기

```python
# app/main.py에 추가

import joblib
from pathlib import Path

# 모델 로드 (컨테이너 빌드 시 포함)
MODEL_PATH = Path("models/model.pkl")
model = joblib.load(MODEL_PATH) if MODEL_PATH.exists() else None

@app.post("/predict")
def predict(input_data: PredictionInput):
    if model is None:
        raise HTTPException(500, "Model not loaded")
    
    features = np.array(input_data.features).reshape(1, -1)
    prediction = model.predict(features)
    
    return PredictionOutput(
        prediction=float(prediction[0]),
        model_version="v2.0-sklearn"
    )
```

### Dockerfile 수정 (모델 포함)
```dockerfile
# 모델 파일 복사
COPY ./models ./models

# 또는 빌드 시 다운로드
RUN curl -o /app/models/model.pkl https://your-model-storage.com/model.pkl
```

### MLOps 도구 통합 예시

**1. MLflow로 모델 관리**
```python
import mlflow

# 모델 로드
model = mlflow.pyfunc.load_model(f"models:/{MODEL_NAME}/Production")
```

**2. Prometheus로 모니터링**
```python
from prometheus_client import Counter, Histogram

prediction_counter = Counter('predictions_total', 'Total predictions')
prediction_latency = Histogram('prediction_latency_seconds', 'Prediction latency')
```

**3. 모델 버전 관리**
```yaml
# docker-compose.yml
environment:
  - MODEL_VERSION=v2.1.0
  - MODEL_URI=s3://models/iris-classifier-v2.1.0.pkl
```

## 🛠️ 개발 팁

### 로컬에서 개발하기
```bash
# 개발 모드로 실행 (코드 변경 시 자동 재시작)
docker-compose up

# 컨테이너 내부 접속
docker-compose exec ops bash

# 로그 실시간 확인
docker-compose logs -f ops
```

### 이미지 최적화

현재 이미지 크기 확인:
```bash
docker images ops_demo
```

최적화 방법:
- ✅ Multi-stage build 사용
- ✅ slim 이미지 사용
- ✅ 불필요한 파일 제외 (.dockerignore)
- ✅ pip 캐시 제거 (--no-cache-dir)

### 보안 스캔
```bash
# Trivy로 취약점 스캔
docker run --rm \
  -v /var/run/docker.sock:/var/run/docker.sock \
  aquasec/trivy image ops_demo:latest
```

## 📚 학습 리소스

### Docker
- [Docker 공식 문서](https://docs.docker.com/)
- [Docker Compose 문서](https://docs.docker.com/compose/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)

### FastAPI
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [Deploying FastAPI with Docker](https://fastapi.tiangolo.com/deployment/docker/)

### CI/CD
- [GitHub Actions 문서](https://docs.github.com/en/actions)
- [Docker Build Push Action](https://github.com/docker/build-push-action)

## 📝 라이선스

MIT License

## 🙋‍♂️ 문의

Issues 탭에서 질문이나 제안을 남겨주세요!