from fastapi.testclient import TestClient
from app.main import app
import pytest

client = TestClient(app)


def test_read_root():
    """루트 엔드포인트 테스트"""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["status"] == "running"


def test_health_check():
    """헬스 체크 테스트"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_predict_success():
    """정상적인 예측 테스트"""
    test_input = {"features": [5.1, 3.5, 1.4, 0.2]}
    response = client.post("/predict", json=test_input)
    assert response.status_code == 200

    result = response.json()
    assert "prediction" in result
    assert "model_version" in result
    assert isinstance(result["prediction"], float)


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
    assert "cannot be empty" in response.json()["detail"].lower()


def test_model_info():
    """모델 정보 엔드포인트 테스트"""
    response = client.get("/model/info")
    assert response.status_code == 200

    info = response.json()
    assert "model_name" in info
    assert "model_version" in info
    assert info["model_version"] == "v1.0"


@pytest.mark.parametrize(
    "features,expected_range",
    [
        ([1.0, 2.0, 3.0, 4.0], (1.0, 10.0)),
        ([0.0, 0.0, 0.0, 0.0], (-1.0, 1.0)),
        ([10.0, 10.0, 10.0, 10.0], (10.0, 20.0)),
    ],
)
def test_predict_various_inputs(features, expected_range):
    """다양한 입력값에 대한 테스트"""
    test_input = {"features": features}
    response = client.post("/predict", json=test_input)
    assert response.status_code == 200

    result = response.json()
    prediction = result["prediction"]
    assert expected_range[0] <= prediction <= expected_range[1]
