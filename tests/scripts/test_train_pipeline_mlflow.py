"""train_pipeline_mlflow.py에 대한 테스트"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np


class TestIrisMLPipelineWithMLflow:
    """IrisMLPipelineWithMLflow 클래스 테스트"""

    @patch("scripts.train_pipeline_mlflow.mlflow")
    def test_preprocess_data(self, mock_mlflow):
        """전처리 메서드 테스트"""
        from scripts.train_pipeline_mlflow import IrisMLPipelineWithMLflow

        pipeline = IrisMLPipelineWithMLflow()
        X = np.array([[5.1, 3.5, 1.4, 0.2], [6.2, 3.4, 5.4, 2.3]])
        result = pipeline.preprocess_data(X)

        assert result.shape == X.shape
        assert np.array_equal(result, X)

    @patch("scripts.train_pipeline_mlflow.mlflow")
    def test_data_pipeline(self, mock_mlflow):
        """데이터 파이프라인 테스트"""
        from scripts.train_pipeline_mlflow import IrisMLPipelineWithMLflow

        pipeline = IrisMLPipelineWithMLflow()
        X_train, X_test, y_train, y_test = pipeline.data_pipeline()

        assert X_train.shape[0] > 0
        assert X_test.shape[0] > 0
        assert len(y_train) == X_train.shape[0]
        assert len(y_test) == X_test.shape[0]
        assert X_train.shape[1] == 4
        assert X_test.shape[1] == 4

    @patch("scripts.train_pipeline_mlflow.mlflow")
    def test_training_pipeline_with_tracking(self, mock_mlflow):
        """MLflow 추적이 포함된 훈련 파이프라인 테스트"""
        from scripts.train_pipeline_mlflow import IrisMLPipelineWithMLflow

        pipeline = IrisMLPipelineWithMLflow()
        X_train, X_test, y_train, y_test = pipeline.data_pipeline()
        model, params = pipeline.training_pipeline_with_tracking(
            X_train, y_train, n_estimators=50, max_depth=3
        )

        assert model is not None
        assert hasattr(model, "predict")
        assert "n_estimators" in params
        assert "max_depth" in params
        assert params["n_estimators"] == 50
        assert params["max_depth"] == 3
        # MLflow에 파라미터가 기록되었는지 확인
        mock_mlflow.log_params.assert_called()

    @patch("scripts.train_pipeline_mlflow.mlflow")
    def test_evaluate_model_with_tracking(self, mock_mlflow):
        """MLflow 추적이 포함된 모델 평가 테스트"""
        from scripts.train_pipeline_mlflow import IrisMLPipelineWithMLflow

        pipeline = IrisMLPipelineWithMLflow()
        X_train, X_test, y_train, y_test = pipeline.data_pipeline()
        model, params = pipeline.training_pipeline_with_tracking(
            X_train,
            y_train,
        )
        metrics = pipeline.evaluate_model_with_tracking(model, X_test, y_test)

        assert "accuracy" in metrics
        assert "f1_score" in metrics
        assert "precision" in metrics
        assert "recall" in metrics
        assert 0 <= metrics["accuracy"] <= 1
        # MLflow에 메트릭이 기록되었는지 확인
        assert mock_mlflow.log_metric.call_count >= 4

    @patch("scripts.train_pipeline_mlflow.mlflow")
    def test_register_model_with_mlflow(self, mock_mlflow):
        """MLflow 모델 등록 테스트"""
        import joblib

        from scripts.train_pipeline_mlflow import IrisMLPipelineWithMLflow

        # MLflow active_run 모킹
        mock_run = MagicMock()
        mock_run.info.run_id = "test-run-id-123"
        mock_mlflow.active_run.return_value = mock_run

        pipeline = IrisMLPipelineWithMLflow()
        X_train, X_test, y_train, y_test = pipeline.data_pipeline()
        model, params = pipeline.training_pipeline_with_tracking(
            X_train,
            y_train,
        )
        metrics = pipeline.evaluate_model_with_tracking(model, X_test, y_test)

        # 임시 디렉토리 사용
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = Path.cwd()
            try:
                import os

                os.chdir(tmpdir)

                pipeline.register_model_with_mlflow(model, params, metrics)

                # MLflow에 모델이 등록되었는지 확인
                mock_mlflow.sklearn.log_model.assert_called_once()
                mock_mlflow.set_tags.assert_called_once()

                # 로컬 백업 파일이 생성되었는지 확인
                model_path = Path("models/model.pkl")
                assert model_path.exists()

                # 모델 로드 확인
                loaded = joblib.load(model_path)
                assert "model" in loaded
                assert "mlflow_run_id" in loaded
                assert loaded["mlflow_run_id"] == "test-run-id-123"
            finally:
                os.chdir(original_cwd)

    @patch("scripts.train_pipeline_mlflow.mlflow")
    def test_run_pipeline(self, mock_mlflow):
        """전체 MLflow 파이프라인 실행 테스트"""
        from scripts.train_pipeline_mlflow import IrisMLPipelineWithMLflow

        # MLflow context manager 모킹
        mock_context = MagicMock()
        mock_context.__enter__ = MagicMock(return_value=mock_context)
        mock_context.__exit__ = MagicMock(return_value=False)
        mock_run = MagicMock()
        mock_run.info.run_id = "test-run-id-456"
        mock_context.info.run_id = "test-run-id-456"
        mock_mlflow.start_run.return_value = mock_context
        mock_mlflow.active_run.return_value = mock_context

        pipeline = IrisMLPipelineWithMLflow()

        # 임시 디렉토리 사용
        with tempfile.TemporaryDirectory() as tmpdir:
            original_cwd = Path.cwd()
            try:
                import os

                os.chdir(tmpdir)

                model, metrics = pipeline.run_pipeline(
                    n_estimators=50, max_depth=3, run_name="test_run"
                )

                assert model is not None
                assert "accuracy" in metrics
                assert "f1_score" in metrics

                # MLflow start_run이 호출되었는지 확인
                mock_mlflow.start_run.assert_called_once()

                # 모델이 저장되었는지 확인
                model_path = Path("models/model.pkl")
                assert model_path.exists()
            finally:
                os.chdir(original_cwd)

