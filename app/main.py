from typing import List

import numpy as np
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict

app = FastAPI(
    title="ML Prediction API Demo",
    description="DevOps 강의를 위한 간단한 예측 API",
    version="1.0.0",
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
    """헬스 체크 엔드포인트"""
    return {"status": "healthy", "service": "ml-api"}


@app.post("/predict", response_model=PredictionOutput)
def predict(input_data: PredictionInput):
    """
    예측 엔드포인트

    현재는 간단한 계산을 수행하지만,
    나중에 실제 ML 모델(scikit-learn, TensorFlow 등)로 대체 가능
    """
    try:
        # 빈 features 배열 검증
        if not input_data.features:
            raise HTTPException(
                status_code=400,
                detail="features list cannot be empty",
            )

        # 간단한 예측 로직 (실제로는 ML 모델 추론)
        features = np.array(input_data.features)

        # 예시: 단순 가중 평균 계산
        # 실제 환경에서는 model.predict(features)로 대체
        prediction_value = float(np.mean(features) * 1.5)

        # NaN 체크 (혹시 모를 경우를 대비)
        if np.isnan(prediction_value):
            raise HTTPException(
                status_code=400,
                detail="invalid input: cannot compute prediction",
            )

        return PredictionOutput(
            prediction=prediction_value, model_version="v1.0-simple"
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"prediction failed: {str(e)}",
        )


@app.get("/model/info")
def model_info():
    """모델 정보 엔드포인트"""
    return {
        "model_name": "SimplePredictor",
        "model_version": "v1.0",
        "framework": "numpy",
        "input_features": 4,
        "description": "간단한 예측 모델 (추후 실제 ML 모델로 교체 예정)",
    }
