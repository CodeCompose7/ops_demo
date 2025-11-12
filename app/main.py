from contextlib import asynccontextmanager
from pathlib import Path
from typing import List

import joblib
import mlflow
import mlflow.sklearn
import numpy as np
from fastapi import FastAPI, HTTPException
from mlflow.tracking import MlflowClient
from pydantic import BaseModel, ConfigDict

# 전역 변수
MODEL = None
MODEL_INFO = None


def load_model():
    """MLflow 또는 로컬 파일에서 모델 로드"""
    global MODEL, MODEL_INFO

    # 1순위: MLflow Registry에서 모델 로드
    # MLflow Tracking Server를 통해 접근 (Training과 동일한 방식)
    # Kubernetes 서비스 디스커버리: service-name.namespace:port
    import os

    tracking_uri = os.getenv(
        "MLFLOW_TRACKING_URI",
        "http://mlflow-service.mlops-training:5000",
    )
    mlflow.set_tracking_uri(tracking_uri)
    client = MlflowClient(tracking_uri=tracking_uri)
    print(f"  → MLflow Tracking URI: {tracking_uri}")

    # 프로덕션 → Staging → 최신 버전 순으로 시도
    stages_to_try = ["Production", "Staging", None]

    for stage in stages_to_try:
        try:
            if stage:
                model_uri = f"models:/iris-classifier/{stage}"
                latest_versions = client.get_latest_versions(
                    "iris-classifier", stages=[stage]
                )
            else:
                # 스테이지가 없으면 최신 버전 사용
                latest_versions = client.get_latest_versions("iris-classifier")
                if not latest_versions:
                    continue
                # 버전 번호가 가장 큰 것 선택
                latest_version = max(
                    latest_versions,
                    key=lambda v: int(v.version),
                )
                model_uri = f"models:/iris-classifier/{latest_version.version}"
                version_info = latest_version
                run = client.get_run(version_info.run_id)
                model = mlflow.sklearn.load_model(model_uri=model_uri)

                MODEL = model
                MODEL_INFO = {
                    "version": f"mlflow-v{version_info.version}",
                    "metrics": run.data.metrics,
                    "source": "mlflow",
                    "run_id": version_info.run_id,
                    "stage": version_info.current_stage or "None",
                    "feature_names": [
                        "sepal_length",
                        "sepal_width",
                        "petal_length",
                        "petal_width",
                    ],
                    "target_names": ["setosa", "versicolor", "virginica"],
                }

                # 파라미터 정보 추가
                if run.data.params:
                    MODEL_INFO["params"] = run.data.params

                print(f"✅ MLflow 모델 로드 (latest): v{version_info.version}")
                print(f"   MLflow Run ID: {version_info.run_id}")
                return

            if not latest_versions:
                continue

            model = mlflow.sklearn.load_model(model_uri=model_uri)
            version_info = latest_versions[0]
            run = client.get_run(version_info.run_id)

            MODEL = model
            MODEL_INFO = {
                "version": f"mlflow-v{version_info.version}",
                "metrics": run.data.metrics,
                "source": "mlflow",
                "run_id": version_info.run_id,
                "stage": version_info.current_stage or "None",
                "feature_names": [
                    "sepal_length",
                    "sepal_width",
                    "petal_length",
                    "petal_width",
                ],
                "target_names": ["setosa", "versicolor", "virginica"],
            }

            # 파라미터 정보 추가
            if run.data.params:
                MODEL_INFO["params"] = run.data.params

            stage_name = stage or "latest"
            print(f"✅ MLflow 모델 로드 ({stage_name}): v{version_info.version}")
            print(f"   MLflow Run ID: {version_info.run_id}")
            return

        except Exception as e:
            if stage == stages_to_try[-1]:  # 마지막 시도에서만 경고 출력
                print(f"⚠️ MLflow 로드 실패: {e}")
            continue

    # 모델을 찾을 수 없으면 에러
    raise FileNotFoundError(
        "모델을 찾을 수 없습니다! MLflow에 모델이 등록되어 있는지 확인하세요. "
        "Training Job을 실행하여 모델을 먼저 학습해야 합니다."
    )


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
        "source": MODEL_INFO.get("source", "unknown"),
        "feature_names": MODEL_INFO["feature_names"],
        "metrics": MODEL_INFO["metrics"],
    }

    # 생성 시간 정보 추가
    if "created_at" in MODEL_INFO:
        response["created_at"] = MODEL_INFO["created_at"]

    # MLflow 정보가 있으면 추가
    if "mlflow_run_id" in MODEL_INFO:
        response["mlflow_run_id"] = MODEL_INFO["mlflow_run_id"]
        response["mlflow_ui_url"] = "http://localhost:5000"
    if "params" in MODEL_INFO:
        response["hyperparameters"] = MODEL_INFO["params"]

    return response


@app.post("/model/reload")
def reload_model():
    """모델 리로드 - MLflow에서 최신 프로덕션 모델 로드"""
    try:
        load_model()
        return {
            "status": "success",
            "message": "모델이 성공적으로 리로드되었습니다",
            "model_version": MODEL_INFO["version"],
            "source": MODEL_INFO.get("source", "unknown"),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"모델 리로드 실패: {str(e)}")


@app.get("/model/experiments")
def list_experiments():
    """MLflow 실험 목록 조회"""
    try:
        client = MlflowClient()
        experiments = client.search_experiments()

        return {
            "experiments": [
                {
                    "experiment_id": exp.experiment_id,
                    "name": exp.name,
                    "lifecycle_stage": exp.lifecycle_stage,
                    "artifact_location": exp.artifact_location,
                }
                for exp in experiments
            ]
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/model/versions")
def list_model_versions():
    """모델 버전 목록 조회"""
    try:
        client = MlflowClient()
        versions = client.get_latest_versions("iris-classifier")

        return {
            "model_name": "iris-classifier",
            "versions": [
                {
                    "version": v.version,
                    "stage": v.current_stage,
                    "run_id": v.run_id,
                    "creation_timestamp": v.creation_timestamp,
                }
                for v in versions
            ],
        }
    except Exception as e:
        return {"error": str(e)}


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
