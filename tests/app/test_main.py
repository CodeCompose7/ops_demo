import numpy as np
import pytest
from fastapi.testclient import TestClient
from sklearn.ensemble import RandomForestClassifier

from app import main

client = TestClient(main.app)


@pytest.fixture(autouse=True)
def setup_test_model():
    """각 테스트 전에 테스트용 모델 생성"""
    # 테스트용 간단한 모델 생성
    test_model = RandomForestClassifier(n_estimators=10, random_state=42)
    # 더미 데이터로 학습 (3개 클래스 모두 포함)
    X_dummy = np.array(
        [
            [5.1, 3.5, 1.4, 0.2],  # setosa (0)
            [6.2, 3.4, 5.4, 2.3],  # virginica (2)
            [4.9, 3.0, 1.4, 0.2],  # setosa (0)
            [5.7, 2.8, 4.1, 1.3],  # versicolor (1)
        ]
    )
    y_dummy = np.array([0, 2, 0, 1])  # 3개 클래스 모두 포함
    test_model.fit(X_dummy, y_dummy)

    # 모듈의 전역 변수 직접 설정
    main.MODEL = test_model
    main.MODEL_INFO = {
        "version": "v1.0",
        "metrics": {"accuracy": 0.95, "f1_score": 0.94},
        "source": "test",
        "feature_names": [
            "sepal_length",
            "sepal_width",
            "petal_length",
            "petal_width",
        ],
        "target_names": ["setosa", "versicolor", "virginica"],
    }

    yield

    # 테스트 후 정리
    main.MODEL = None
    main.MODEL_INFO = None


def test_read_root():
    """루트 엔드포인트 테스트"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_health_check():
    """헬스 체크 테스트"""
    response = client.get("/health")
    assert response.status_code == 200
    result = response.json()
    assert "status" in result
    assert "service" in result
    assert "model_loaded" in result
    # 모델이 로드된 경우 healthy, 로드되지 않은 경우 degraded
    if result["model_loaded"]:
        assert result["status"] == "healthy"
    else:
        assert result["status"] == "degraded"


def test_predict_success():
    """정상적인 예측 테스트"""
    test_input = {"features": [5.1, 3.5, 1.4, 0.2]}
    response = client.post("/predict", json=test_input)
    assert response.status_code == 200

    result = response.json()
    assert "prediction" in result
    assert "prediction_name" in result
    assert "probability" in result
    assert "model_version" in result
    # JSON 직렬화로 인해 float로 변환될 수 있으므로 정수 값인지 확인
    assert isinstance(result["prediction"], (int, float))
    assert result["prediction"] in [0, 1, 2]  # 분류 모델이므로 0, 1, 2 중 하나
    assert isinstance(result["probability"], list)


def test_predict_invalid_input():
    """잘못된 입력에 대한 테스트"""
    test_input = {"features": "invalid"}  # 리스트가 아닌 문자열
    response = client.post("/predict", json=test_input)
    assert response.status_code == 422  # Validation Error


def test_predict_empty_features():
    """빈 features에 대한 테스트"""
    test_input = {"features": []}
    response = client.post("/predict", json=test_input)
    # 빈 배열은 400 Bad Request를 반환해야 함
    assert response.status_code == 400
    assert "4개 특성 필요" in response.json()["detail"]


def test_model_info():
    """모델 정보 엔드포인트 테스트"""
    response = client.get("/model/info")
    assert response.status_code == 200

    info = response.json()
    if info.get("model_loaded"):
        assert "model_version" in info
        assert "framework" in info
        assert "source" in info
        assert "feature_names" in info
        assert "metrics" in info
    else:
        assert info["model_loaded"] is False


@pytest.mark.parametrize(
    "features",
    [
        [1.0, 2.0, 3.0, 4.0],
        [0.0, 0.0, 0.0, 0.0],
        [10.0, 10.0, 10.0, 10.0],
        [5.1, 3.5, 1.4, 0.2],
        [6.2, 3.4, 5.4, 2.3],
    ],
)
def test_predict_various_inputs(features):
    """다양한 입력값에 대한 테스트"""
    test_input = {"features": features}
    response = client.post("/predict", json=test_input)
    assert response.status_code == 200

    result = response.json()
    prediction = result["prediction"]
    # 분류 모델이므로 0, 1, 2 중 하나여야 함
    assert prediction in [0, 1, 2]
    assert result["prediction_name"] in ["setosa", "versicolor", "virginica"]
    assert len(result["probability"]) == 3  # 3개 클래스

