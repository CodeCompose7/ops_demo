"""train_pipeline.py에 대한 테스트"""

import tempfile
from pathlib import Path

import joblib
import numpy as np

from scripts.train_pipeline import IrisMLPipeline


class TestIrisMLPipeline:
    """IrisMLPipeline 클래스 테스트"""

    def test_preprocess_data(self):
        """전처리 메서드 테스트"""
        pipeline = IrisMLPipeline()
        X = np.array([[5.1, 3.5, 1.4, 0.2], [6.2, 3.4, 5.4, 2.3]])
        result = pipeline.preprocess_data(X)

        assert result.shape == X.shape
        assert np.array_equal(result, X)

    def test_data_pipeline(self):
        """데이터 파이프라인 테스트"""
        pipeline = IrisMLPipeline()
        X_train, X_test, y_train, y_test = pipeline.data_pipeline()

        assert X_train.shape[0] > 0
        assert X_test.shape[0] > 0
        assert len(y_train) == X_train.shape[0]
        assert len(y_test) == X_test.shape[0]
        assert X_train.shape[1] == 4  # 4개 특성
        assert X_test.shape[1] == 4

    def test_training_pipeline(self):
        """훈련 파이프라인 테스트"""
        pipeline = IrisMLPipeline()
        X_train, X_test, y_train, y_test = pipeline.data_pipeline()
        model = pipeline.training_pipeline(X_train, y_train)

        assert model is not None
        assert hasattr(model, "predict")
        assert hasattr(model, "predict_proba")

    def test_evaluate_model(self):
        """모델 평가 테스트"""
        pipeline = IrisMLPipeline()
        X_train, X_test, y_train, y_test = pipeline.data_pipeline()
        model = pipeline.training_pipeline(X_train, y_train)
        metrics = pipeline.evaluate_model(model, X_test, y_test)

        assert "accuracy" in metrics
        assert "f1_score" in metrics
        assert 0 <= metrics["accuracy"] <= 1
        assert 0 <= metrics["f1_score"] <= 1

    def test_save_model(self):
        """모델 저장 테스트"""
        pipeline = IrisMLPipeline()
        X_train, X_test, y_train, y_test = pipeline.data_pipeline()
        model = pipeline.training_pipeline(X_train, y_train)
        metrics = pipeline.evaluate_model(model, X_test, y_test)

        # 임시 디렉토리 사용
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = Path.cwd()
            try:
                # 임시 디렉토리로 이동
                import os

                os.chdir(tmpdir)

                pipeline.save_model(model, metrics)

                model_path = Path("models/model.pkl")
                assert model_path.exists()

                # 모델 로드 확인
                loaded = joblib.load(model_path)
                assert "model" in loaded
                assert "version" in loaded
                assert "metrics" in loaded
                assert "feature_names" in loaded
                assert "target_names" in loaded
            finally:
                os.chdir(original_cwd)

    def test_run_pipeline(self):
        """전체 파이프라인 실행 테스트"""
        pipeline = IrisMLPipeline()

        # 임시 디렉토리 사용
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = Path.cwd()
            try:
                import os

                os.chdir(tmpdir)

                model, metrics = pipeline.run_pipeline()

                assert model is not None
                assert "accuracy" in metrics
                assert "f1_score" in metrics

                # 모델이 저장되었는지 확인
                model_path = Path("models/model.pkl")
                assert model_path.exists()
            finally:
                os.chdir(original_cwd)

