# 포트 정보

## 🔌 MLOps 서비스 포트

| 서비스 | NodePort | 용도 | 접속 URL |
|--------|----------|------|----------|
| **Training Controller** | 30081 | 웹 UI에서 훈련 시작 | http://localhost:30081 |
| **MLflow** | 30501 | 실험 추적 및 모델 관리 | http://localhost:30501 |
| **Serving API** | 30801 | 모델 추론 API | http://localhost:30801 |

## ⚠️ 포트 충돌 회피

다음 포트들은 이미 사용 중이므로 피했습니다:

| 포트 | 서비스 | 네임스페이스 |
|------|--------|-------------|
| 30080 | control-service | control-pool |
| 30030 | grafana | monitoring |
| 30090 | prometheus | monitoring |
| 32559, 32627 | traefik | kube-system |

## 🔄 포트 변경이 필요한 경우

```bash
# k8s/03-mlflow.yaml
nodePort: 30501  # 다른 포트로 변경

# k8s/06-training-controller.yaml
nodePort: 30081  # 다른 포트로 변경

# k8s/05-serving.yaml
nodePort: 30801  # 다른 포트로 변경
```

변경 후:
```bash
kubectl apply -f k8s/03-mlflow.yaml
kubectl apply -f k8s/06-training-controller.yaml
kubectl apply -f k8s/05-serving.yaml
```

## 📊 현재 모든 서비스 포트 확인

```bash
kubectl get svc -A
```

## 🎯 빠른 접속

```bash
# Training Controller UI
open http://localhost:30081  # Mac
xdg-open http://localhost:30081  # Linux
start http://localhost:30081  # Windows

# MLflow UI
open http://localhost:30501

# Serving API Swagger
open http://localhost:30801/docs
```

