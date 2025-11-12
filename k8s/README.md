# Kubernetes 기반 MLOps 환경 가이드

이 디렉토리에는 Kubernetes를 활용한 훈련/서빙 환경 분리 구성이 포함되어 있습니다.

## 📋 목차

1. [아키텍처 개요](#아키텍처-개요)
2. [사전 요구사항](#사전-요구사항)
3. [빠른 시작](#빠른-시작)
4. [상세 가이드](#상세-가이드)
5. [문제 해결](#문제-해결)

---

## 🏗️ 아키텍처 개요

### 환경 분리 전략

```
┌─────────────────────────────────────────────────┐
│           Kubernetes Cluster (k3s)               │
│                                                  │
│  ┌──────────────────┐  ┌────────────────────┐  │
│  │ mlops-training   │  │  mlops-serving     │  │
│  │                  │  │                    │  │
│  │ • MLflow Server  │  │  • API Server x2   │  │
│  │ • Training Jobs  │  │  • Load Balancer   │  │
│  │ • High CPU/Mem   │  │  • Low Resources   │  │
│  └──────────────────┘  └────────────────────┘  │
│           │                      │               │
│           └──────────┬───────────┘               │
│                      │                           │
│            ┌─────────▼─────────┐                 │
│            │  Shared Storage   │                 │
│            │  • Models         │                 │
│            │  • MLflow Data    │                 │
│            └───────────────────┘                 │
└─────────────────────────────────────────────────┘
```

### 주요 이점

| 구분 | 기존 (모놀리식) | 개선 (마이크로서비스) |
|------|----------------|---------------------|
| **리소스** | 경합 발생 | 독립 할당 |
| **배포** | 전체 중단 | 무중단 롤링 |
| **확장** | 제한적 | 자유로운 스케일링 |
| **관리** | 복잡함 | 관심사 분리 |

---

## 🛠️ 사전 요구사항

### 1. Kubernetes 클러스터

**k3s 설치 (권장):**

```bash
# k3s 설치 (1분 소요)
curl -sfL https://get.k3s.io | sh -

# kubectl 설정
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $USER ~/.kube/config
export KUBECONFIG=~/.kube/config

# 확인
kubectl get nodes
```

**대안:**
- Minikube
- Docker Desktop Kubernetes
- 클라우드 Kubernetes (EKS, GKE, AKS)

### 2. Docker

```bash
# Docker 설치 확인
docker --version

# Docker 실행 확인
docker ps
```

### 3. kubectl

```bash
# kubectl 설치 확인
kubectl version --client

# 클러스터 연결 확인
kubectl cluster-info
```

---

## 🚀 빠른 시작

### 1. 전체 환경 배포

```bash
# 실행 권한 부여
chmod +x k8s/*.sh

# 환경 배포 (5분 소요)
./k8s/deploy.sh
```

배포 과정:
1. ✅ Docker 이미지 빌드 (training, serving)
2. ✅ 네임스페이스 생성
3. ✅ 공유 스토리지 설정
4. ✅ MLflow 서버 배포
5. ✅ 서빙 API 배포

### 2. 모델 훈련 실행

```bash
# 기본 파라미터로 훈련
./k8s/train.sh

# 커스텀 파라미터로 훈련
./k8s/train.sh \
  --n-estimators 200 \
  --max-depth 20 \
  --run-name "experiment-001"
```

### 3. MLflow UI 접속

```bash
# 포트포워딩
kubectl port-forward -n mlops-training svc/mlflow-service 5000:5000

# 브라우저에서 접속
# http://localhost:5000
```

### 4. API 테스트

```bash
# 포트포워딩
kubectl port-forward -n mlops-serving svc/iris-serving-service 8000:80

# API 호출
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"features": [5.1, 3.5, 1.4, 0.2]}'
```

---

## 📚 상세 가이드

### 파일 구조

```
k8s/
├── 01-namespaces.yaml    # 네임스페이스 정의
├── 02-storage.yaml       # 공유 스토리지 (PV, PVC)
├── 03-mlflow.yaml        # MLflow 서버 배포
├── 04-training-job.yaml  # 훈련 Job 템플릿
├── 05-serving.yaml       # 서빙 API 배포
├── deploy.sh             # 전체 배포 스크립트
├── train.sh              # 훈련 실행 스크립트
├── cleanup.sh            # 환경 정리 스크립트
└── README.md             # 이 문서
```

### 수동 배포 (단계별)

#### 1. 네임스페이스 생성

```bash
kubectl apply -f k8s/01-namespaces.yaml

# 확인
kubectl get namespaces | grep mlops
```

#### 2. 스토리지 설정

```bash
# 호스트 디렉토리 생성 (사용자 홈 디렉토리)
mkdir -p $HOME/ops-demo-data/mlops

# PV, PVC 생성 (경로 자동 치환)
STORAGE_DIR="$HOME/ops-demo-data/mlops"
sed "s|/data/mlops|$STORAGE_DIR|g" k8s/02-storage.yaml | kubectl apply -f -

# 확인
kubectl get pv,pvc -A
```

#### 3. Docker 이미지 빌드

```bash
# 훈련용 이미지
docker build -f Dockerfile.training -t ops-demo:training .

# 서빙용 이미지
docker build -f Dockerfile.serving -t ops-demo:serving .

# k3s에 import (필요 시)
docker save ops-demo:training | sudo k3s ctr images import -
docker save ops-demo:serving | sudo k3s ctr images import -
```

#### 4. MLflow 서버 배포

```bash
kubectl apply -f k8s/03-mlflow.yaml

# 준비 대기
kubectl wait --for=condition=ready pod \
  -l app=mlflow-server -n mlops-training --timeout=120s

# 확인
kubectl get pods -n mlops-training
```

#### 5. 서빙 API 배포

```bash
kubectl apply -f k8s/05-serving.yaml

# 준비 대기
kubectl wait --for=condition=ready pod \
  -l app=iris-serving -n mlops-serving --timeout=120s

# 확인
kubectl get pods,svc -n mlops-serving
```

#### 6. 훈련 Job 실행

```bash
# train.sh 사용 (권장)
./k8s/train.sh --n-estimators 100 --max-depth 5

# 또는 직접 적용
kubectl apply -f k8s/04-training-job.yaml

# 로그 확인
POD_NAME=$(kubectl get pods -n mlops-training \
  -l app=iris-training -o jsonpath='{.items[0].metadata.name}')
kubectl logs -f $POD_NAME -n mlops-training
```

---

## 🔍 모니터링 및 관리

### 상태 확인

```bash
# 전체 리소스 확인
kubectl get all -A | grep mlops

# Training 네임스페이스
kubectl get pods,svc,jobs -n mlops-training

# Serving 네임스페이스
kubectl get pods,svc,deployment -n mlops-serving

# 스토리지 확인
kubectl get pv,pvc -A
```

### 로그 확인

```bash
# MLflow 로그
kubectl logs -f deployment/mlflow-server -n mlops-training

# 훈련 Job 로그
kubectl logs -f job/iris-training -n mlops-training

# 서빙 API 로그
kubectl logs -f deployment/iris-serving -n mlops-serving
```

### 리소스 사용량

```bash
# Pod별 리소스 사용량
kubectl top pods -n mlops-training
kubectl top pods -n mlops-serving

# 노드 리소스 사용량
kubectl top nodes
```

### 디버깅

```bash
# Pod 내부 접속
kubectl exec -it <pod-name> -n mlops-training -- /bin/bash

# Pod 이벤트 확인
kubectl describe pod <pod-name> -n mlops-training

# 서비스 엔드포인트 확인
kubectl get endpoints -n mlops-training
kubectl get endpoints -n mlops-serving
```

---

## 🔄 업데이트 및 롤백

### 이미지 업데이트

```bash
# 1. 새 이미지 빌드
docker build -f Dockerfile.serving -t ops-demo:serving:v2 .

# 2. k3s에 import
docker save ops-demo:serving:v2 | sudo k3s ctr images import -

# 3. Deployment 업데이트
kubectl set image deployment/iris-serving \
  serving=ops-demo:serving:v2 -n mlops-serving

# 4. 롤아웃 상태 확인
kubectl rollout status deployment/iris-serving -n mlops-serving
```

### 롤백

```bash
# 이전 버전으로 롤백
kubectl rollout undo deployment/iris-serving -n mlops-serving

# 특정 리비전으로 롤백
kubectl rollout undo deployment/iris-serving \
  --to-revision=2 -n mlops-serving

# 롤아웃 히스토리 확인
kubectl rollout history deployment/iris-serving -n mlops-serving
```

---

## 📊 실험 관리

### 다양한 하이퍼파라미터로 실험

```bash
# 실험 1: 기본 설정
./k8s/train.sh --run-name "baseline"

# 실험 2: 더 많은 트리
./k8s/train.sh --n-estimators 200 --run-name "more-trees"

# 실험 3: 더 깊은 트리
./k8s/train.sh --max-depth 20 --run-name "deeper-trees"

# 실험 4: 복합 조정
./k8s/train.sh \
  --n-estimators 300 \
  --max-depth 15 \
  --run-name "optimized"
```

### 병렬 실험 (여러 Job 동시 실행)

```bash
# 백그라운드로 실행
./k8s/train.sh --run-name "exp-1" &
./k8s/train.sh --run-name "exp-2" &
./k8s/train.sh --run-name "exp-3" &

# Job 상태 확인
kubectl get jobs -n mlops-training
```

---

## 🧹 정리

### 전체 환경 삭제

```bash
./k8s/cleanup.sh

# 호스트 데이터도 삭제 (선택)
rm -rf $HOME/ops-demo-data/mlops
```

### 개별 리소스 삭제

```bash
# 서빙만 삭제
kubectl delete -f k8s/05-serving.yaml

# 특정 Job 삭제
kubectl delete job iris-training -n mlops-training

# 네임스페이스 전체 삭제
kubectl delete namespace mlops-training
kubectl delete namespace mlops-serving
```

---

## 🐛 문제 해결

### 1. Pod가 시작되지 않음

```bash
# Pod 상태 확인
kubectl describe pod <pod-name> -n mlops-training

# 일반적인 원인:
# - 이미지를 찾을 수 없음 → k3s에 import 확인
# - PVC가 바인딩되지 않음 → PV 상태 확인
# - 리소스 부족 → kubectl top nodes
```

### 2. 이미지 Pull 오류

```bash
# k3s의 경우 import 필요
docker save ops-demo:training | sudo k3s ctr images import -
docker save ops-demo:serving | sudo k3s ctr images import -

# 또는 imagePullPolicy 변경
# imagePullPolicy: Never
```

### 3. 스토리지 접근 오류

```bash
# 권한 확인
chmod 777 $HOME/ops-demo-data/mlops

# SELinux 비활성화 (필요 시)
sudo setenforce 0
```

### 4. MLflow 연결 실패

```bash
# MLflow 서비스 확인
kubectl get svc -n mlops-training

# DNS 확인
kubectl run -it --rm debug --image=busybox --restart=Never -- \
  nslookup mlflow-service.mlops-training.svc.cluster.local
```

### 5. 서빙 API 접근 안됨

```bash
# LoadBalancer 상태 확인
kubectl get svc iris-serving-service -n mlops-serving

# 포트포워딩 사용 (대안)
kubectl port-forward -n mlops-serving \
  svc/iris-serving-service 8000:80
```

---

## 🚀 실무 확장 방향

### 1. GPU 지원

```yaml
resources:
  limits:
    nvidia.com/gpu: 1
```

### 2. 오토스케일링

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: iris-serving-hpa
  namespace: mlops-serving
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: iris-serving
  minReplicas: 2
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### 3. 모니터링 (Prometheus + Grafana)

```bash
# Prometheus Operator 설치
kubectl apply -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/main/bundle.yaml
```

### 4. CI/CD 통합 (GitLab/GitHub Actions)

```yaml
# .github/workflows/deploy.yml
- name: Deploy to Kubernetes
  run: |
    kubectl apply -f k8s/
```

---

## 📞 참고 자료

- [Kubernetes 공식 문서](https://kubernetes.io/docs/)
- [k3s 공식 문서](https://k3s.io/)
- [MLflow 공식 문서](https://mlflow.org/docs/latest/index.html)
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)

---

## 📝 라이센스

이 프로젝트는 교육 목적으로 제작되었습니다.

