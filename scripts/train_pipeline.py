from datetime import datetime
from pathlib import Path

import joblib
import pandas as pd
from sklearn.model_selection import train_test_split


class IrisMLPipeline:
    """간단하지만 완전한 ML 파이프라인"""

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

        # 특성 스케일링 (선택사항 - RandomForest는 스케일링이 필요 없지만 일반적인 파이프라인)
        # 주석 처리: RandomForest는 스케일링이 필요 없으므로 생략
        # scaler = StandardScaler()
        # X_scaled = scaler.fit_transform(X)
        # print("  → 특성 스케일링 완료 (StandardScaler)")

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

    def training_pipeline(self, X_train, y_train):
        """훈련 파이프라인"""
        from sklearn.ensemble import RandomForestClassifier

        print("  → 모델 훈련 (RandomForestClassifier)")

        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=5,
            random_state=42,
            n_jobs=-1,  # 모든 CPU 코어 사용
        )

        print("  → 학습 시작...")
        model.fit(X_train, y_train)
        print("  → 학습 완료!")

        return model

    def evaluate_model(self, model, X_test, y_test):
        """모델 평가"""
        from sklearn.metrics import accuracy_score, f1_score

        y_pred = model.predict(X_test)

        accuracy = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average="weighted")

        print(f"  → Accuracy: {accuracy:.4f}")
        print(f"  → F1 Score: {f1:.4f}")

        # 모델 검증
        if accuracy < 0.85:
            print("  ⚠️  경고: 정확도가 85% 미만!")
            print("  → 재훈련 또는 하이퍼파라미터 조정 필요")
        else:
            print("  ✅ 모델 검증 통과 (정확도 >= 85%)")

        return {"accuracy": accuracy, "f1_score": f1}

    def save_model(self, model, metrics):
        """모델 + 메타데이터 패키징"""

        model_artifact = {
            "model": model,
            "version": datetime.now().strftime("v%Y%m%d-%H%M%S"),
            "metrics": metrics,
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

        # models 디렉토리 생성
        model_dir = Path("models")
        model_dir.mkdir(exist_ok=True)

        # 저장
        model_path = model_dir / "model.pkl"
        joblib.dump(model_artifact, model_path)

        print(f"  → 모델 버전: {model_artifact['version']}")
        print(f"  → 저장 경로: {model_path}")

    def run_pipeline(self):
        print("=" * 60)
        print("ML Pipeline 시작")
        print("=" * 60)

        # 1. Data Pipeline
        print("\n[1/4] 📊 Data Pipeline")
        X_train, X_test, y_train, y_test = self.data_pipeline()

        # 2. Training Pipeline
        print("\n[2/4] 🤖 Training Pipeline")
        model = self.training_pipeline(X_train, y_train)

        # 3. Evaluation
        print("\n[3/4] 📈 Model Evaluation")
        metrics = self.evaluate_model(model, X_test, y_test)

        # 4. Serving Pipeline
        print("\n[4/4] 💾 Serving Pipeline - 모델 저장")
        self.save_model(model, metrics)

        print("\n✅ Pipeline 완료!")
        print("=" * 60)

        return model, metrics


if __name__ == "__main__":
    pipeline = IrisMLPipeline()
    pipeline.run_pipeline()
