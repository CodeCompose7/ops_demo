from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

import joblib
import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict

# 전역 변수
MODEL = None
MODEL_INFO = None


def load_model():
    """앱 시작 시 모델 로드"""
    global MODEL, MODEL_INFO

    model_path = Path("models/model.pkl")
    model_artifact = joblib.load(model_path)

    MODEL = model_artifact["model"]
    MODEL_INFO = {
        "version": model_artifact["version"],
        "metrics": model_artifact["metrics"],
        "feature_names": model_artifact["feature_names"],
        "target_names": model_artifact["target_names"],
        "created_at": model_artifact["created_at"],
    }

    # MLflow run_id가 있으면 추가
    if "mlflow_run_id" in model_artifact:
        MODEL_INFO["mlflow_run_id"] = model_artifact["mlflow_run_id"]
    if "params" in model_artifact:
        MODEL_INFO["params"] = model_artifact["params"]

    print(f"✅ 모델 로드: {MODEL_INFO['version']}")
    if "mlflow_run_id" in MODEL_INFO:
        print(f"   MLflow Run ID: {MODEL_INFO['mlflow_run_id']}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    # Startup: 앱 시작 시 실행
    load_model()
    yield
    # Shutdown: 앱 종료 시 실행 (필요시 정리 작업)


app = FastAPI(
    title="ML Prediction API Demo",
    description="DevOps 강의를 위한 간단한 예측 API",
    version="1.0.0",
    lifespan=lifespan,
)


class PredictionInput(BaseModel):
    """예측 입력 데이터 모델"""

    features: List[float]

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"features": [5.1, 3.5, 1.4, 0.2]},
        }
    )


class PredictionOutput(BaseModel):
    """예측 결과 모델"""

    prediction: float
    prediction_name: str
    probability: List[float]
    model_version: str

    model_config = {"protected_namespaces": ()}


@app.get("/")
def read_root():
    """API 루트 엔드포인트"""
    return {
        "message": "ML Prediction API",
        "status": "running",
        "version": "1.0.0",
    }


@app.get("/health")
def health_check():
    """헬스 체크 - 모델 로드 상태 확인"""
    model_healthy = MODEL is not None

    return {
        "status": "healthy" if model_healthy else "degraded",
        "service": "ml-api",
        "model_loaded": model_healthy,
    }


@app.get("/model/info")
def model_info():
    """모델 정보 조회 - 버전, 메트릭, 특성"""
    if MODEL is None:
        return {"model_loaded": False}

    response = {
        "model_loaded": True,
        "model_version": MODEL_INFO["version"],
        "framework": "scikit-learn",
        "feature_names": MODEL_INFO["feature_names"],
        "metrics": MODEL_INFO["metrics"],
        "created_at": MODEL_INFO["created_at"],
    }

    # MLflow 정보가 있으면 추가
    if "mlflow_run_id" in MODEL_INFO:
        response["mlflow_run_id"] = MODEL_INFO["mlflow_run_id"]
        response["mlflow_ui_url"] = "http://localhost:5000"
    if "params" in MODEL_INFO:
        response["hyperparameters"] = MODEL_INFO["params"]

    return response


@app.post("/predict", response_model=PredictionOutput)
def predict(input_data: PredictionInput):
    """실제 ML 모델로 예측"""

    # 입력 검증
    if len(input_data.features) != 4:
        raise HTTPException(400, "4개 특성 필요")

    # 예측
    features = np.array(input_data.features).reshape(1, -1)
    prediction = MODEL.predict(features)[0]
    probabilities = MODEL.predict_proba(features)[0]

    return PredictionOutput(
        prediction=int(prediction),
        prediction_name=MODEL_INFO["target_names"][prediction],
        probability=probabilities.tolist(),
        model_version=MODEL_INFO["version"],
    )
