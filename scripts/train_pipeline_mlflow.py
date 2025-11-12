import argparse
import os
from datetime import datetime
from pathlib import Path

import joblib
import mlflow
import mlflow.sklearn
import pandas as pd
from sklearn.model_selection import train_test_split


class IrisMLPipelineWithMLflow:
    """MLflow 추적이 포함된 ML 파이프라인"""

    def __init__(self):
        """MLflow 실험 설정"""
        # MLflow Tracking URI 설정 (Remote Tracking Server 사용)
        tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "http://mlflow-service:5000")
        mlflow.set_tracking_uri(tracking_uri)
        print(f"  → MLflow Tracking URI: {tracking_uri}")
        
        mlflow.set_experiment("iris-classification")

    def preprocess_data(self, X):
        """Iris 데이터셋 전처리: 이상치 탐지 및 선택적 스케일링"""
        # DataFrame으로 변환 (이상치 탐지용)
        df = pd.DataFrame(
            X,
            columns=[
                "sepal_length",
                "sepal_width",
                "petal_length",
                "petal_width",
            ],
        )

        # 이상치 탐지 (IQR 방법)
        print("  → 이상치 탐지 중...")
        Q1 = df.quantile(0.25)
        Q3 = df.quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR

        # 이상치가 있는 행 찾기
        outliers = ((df < lower_bound) | (df > upper_bound)).any(axis=1)
        outlier_count = outliers.sum()

        if outlier_count > 0:
            print(
                f"  → 이상치 {outlier_count}개 발견 "
                "(제거하지 않음 - Iris 데이터는 정상 범위)"
            )
        else:
            print("  → 이상치 없음")

        # Iris 데이터는 이미 정규화가 잘 되어있으므로 스케일링 생략
        print("  → 전처리 완료 (Iris 데이터는 추가 스케일링 불필요)")

        return X

    def data_pipeline(self):
        """데이터 파이프라인: 수집 → 검증 → 전처리 → 분할"""

        # 데이터 수집 (sklearn 내장 데이터셋)
        from sklearn.datasets import load_iris

        iris = load_iris()
        X, y = iris.data, iris.target

        print("  → 데이터 수집 (Iris dataset)")
        print(f"  → 데이터 검증: {X.shape[0]}개 샘플, {X.shape[1]}개 특성")
        assert X.shape[0] > 0, "데이터가 비어있습니다"
        assert not pd.DataFrame(X).isnull().any().any(), "결측치 발견"

        # 전처리
        print("  → 데이터 전처리")
        X = self.preprocess_data(X)

        # 데이터 분할
        print("  → 데이터 분할 (Train: 80%, Test: 20%)")
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        print(f"     Train: {X_train.shape[0]}개, Test: {X_test.shape[0]}개")
        return X_train, X_test, y_train, y_test

    def training_pipeline_with_tracking(
        self, X_train, y_train, n_estimators=100, max_depth=5
    ):
        """MLflow 추적이 포함된 훈련 파이프라인"""
        from sklearn.ensemble import RandomForestClassifier

        # 하이퍼파라미터 정의
        params = {
            "n_estimators": n_estimators,
            "max_depth": max_depth,
            "random_state": 42,
            "n_jobs": -1,
        }

        # MLflow에 파라미터 기록
        mlflow.log_params(params)

        print("  → 모델 훈련 (RandomForestClassifier)")
        print(f"  → 하이퍼파라미터: {params}")

        model = RandomForestClassifier(**params)
        print("  → 학습 시작...")
        model.fit(X_train, y_train)
        print("  → 학습 완료! (MLflow에 파라미터 기록됨)")

        return model, params

    def evaluate_model_with_tracking(self, model, X_test, y_test):
        """MLflow 추적이 포함된 모델 평가"""
        from sklearn.metrics import (
            accuracy_score,
            f1_score,
            precision_score,
            recall_score,
        )

        y_pred = model.predict(X_test)

        # 다양한 메트릭 계산
        metrics = {
            "accuracy": accuracy_score(y_test, y_pred),
            "f1_score": f1_score(y_test, y_pred, average="weighted"),
            "precision": precision_score(y_test, y_pred, average="weighted"),
            "recall": recall_score(y_test, y_pred, average="weighted"),
        }

        # MLflow에 메트릭 기록
        for metric_name, value in metrics.items():
            mlflow.log_metric(metric_name, value)
            print(f"  → {metric_name.capitalize()}: {value:.4f}")

        # 모델 검증
        if metrics["accuracy"] < 0.85:
            mlflow.set_tag("validation", "failed")
            print("  ⚠️  경고: 정확도가 85% 미만!")
            print("  → 재훈련 또는 하이퍼파라미터 조정 필요")
        else:
            mlflow.set_tag("validation", "passed")
            print("  ✅ 모델 검증 통과 (정확도 >= 85%)")

        return metrics

    def register_model_with_mlflow(self, model, params, metrics):
        """MLflow 모델 레지스트리에 등록"""

        model_name = "iris-classifier"

        # 모델 저장 및 등록
        mlflow.sklearn.log_model(
            sk_model=model,
            artifact_path="model",
            registered_model_name=model_name,
        )

        # 추가 메타데이터
        mlflow.set_tags(
            {
                "framework": "scikit-learn",
                "algorithm": "RandomForest",
                "dataset": "iris",
                "feature_count": 4,
                "target_classes": 3,
            }
        )

        print(f"  → 모델 '{model_name}'로 MLflow 레지스트리에 등록")
        print("  → 실험 추적 URL: http://localhost:5000")

        # 로컬 파일도 백업 저장 (기존 호환성)
        model_artifact = {
            "model": model,
            "version": datetime.now().strftime("v%Y%m%d-%H%M%S"),
            "metrics": metrics,
            "params": params,
            "mlflow_run_id": mlflow.active_run().info.run_id,
            "feature_names": [
                "sepal_length",
                "sepal_width",
                "petal_length",
                "petal_width",
            ],
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "target_names": ["setosa", "versicolor", "virginica"],
            "framework": "scikit-learn",
        }

        model_dir = Path("models")
        model_dir.mkdir(exist_ok=True)
        joblib.dump(model_artifact, model_dir / "model.pkl")

        print("  → 로컬 백업: models/model.pkl")

    def run_pipeline(self, n_estimators=100, max_depth=5, run_name=None):
        """MLflow 추적이 포함된 파이프라인 실행"""
        with mlflow.start_run(run_name=run_name):
            print("=" * 60)
            print("MLflow 추적이 포함된 ML Pipeline 시작")
            if run_name:
                print(f"Run Name: {run_name}")
            print("=" * 60)

            # 1. Data Pipeline (동일)
            print("\n[1/4] 📊 Data Pipeline")
            X_train, X_test, y_train, y_test = self.data_pipeline()

            # 2. Training Pipeline (MLflow 추적 추가)
            print("\n[2/4] 🤖 Training Pipeline with MLflow")
            model, params = self.training_pipeline_with_tracking(
                X_train,
                y_train,
                n_estimators=n_estimators,
                max_depth=max_depth,
            )

            # 3. Evaluation (메트릭 자동 기록)
            print("\n[3/4] 📈 Model Evaluation with MLflow")
            metrics = self.evaluate_model_with_tracking(model, X_test, y_test)

            # 4. Model Registry (자동 버전 관리)
            print("\n[4/4] 🏪 MLflow Model Registry")
            self.register_model_with_mlflow(model, params, metrics)

            run_id = mlflow.active_run().info.run_id
            print(f"\n✅ Pipeline 완료! MLflow Run ID: {run_id}")
            print("=" * 60)

            return model, metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="MLflow 추적이 포함된 Iris 분류 모델 훈련"
    )
    parser.add_argument(
        "--n-estimators",
        type=int,
        default=100,
        help="RandomForest의 n_estimators 하이퍼파라미터 (기본값: 100)",
    )
    parser.add_argument(
        "--max-depth",
        type=int,
        default=5,
        help="RandomForest의 max_depth 하이퍼파라미터 (기본값: 5)",
    )
    parser.add_argument(
        "--run-name",
        type=str,
        default=None,
        help="MLflow run 이름 (기본값: 자동 생성)",
    )
    parser.add_argument(
        "--run-all",
        action="store_true",
        help="여러 하이퍼파라미터 조합으로 자동 실행",
    )

    args = parser.parse_args()

    pipeline = IrisMLPipelineWithMLflow()

    if args.run_all:
        # 여러 하이퍼파라미터 조합으로 자동 실행
        param_combinations = [
            {"n_estimators": 100, "max_depth": 5, "run_name": "run_001"},
            {"n_estimators": 50, "max_depth": 3, "run_name": "run_002"},
            {"n_estimators": 200, "max_depth": 10, "run_name": "run_003"},
        ]

        print("=" * 60)
        print(f"총 {len(param_combinations)}개의 실험을 실행합니다")
        print("=" * 60)

        for i, params in enumerate(param_combinations, 1):
            print(f"\n{'='*60}")
            print(f"실험 {i}/{len(param_combinations)}: {params['run_name']}")
            print(f"{'='*60}")
            pipeline.run_pipeline(
                n_estimators=params["n_estimators"],
                max_depth=params["max_depth"],
                run_name=params["run_name"],
            )

        print("\n" + "=" * 60)
        print("모든 실험 완료!")
        print("MLflow UI에서 결과를 확인하세요: http://localhost:5000")
        print("=" * 60)
    else:
        # 단일 실험 실행
        pipeline.run_pipeline(
            n_estimators=args.n_estimators,
            max_depth=args.max_depth,
            run_name=args.run_name,
        )
