# Kubernetes 기반 MLOps 환경 분리

이 문서는 ops_demo 프로젝트를 Kubernetes 환경으로 마이그레이션하는 가이드입니다.

## 🎯 목표

기존 모놀리식 Docker 구조를 Kubernetes 기반 마이크로서비스로 전환하여:
- ✅ 훈련 환경과 서빙 환경 완전 분리
- ✅ 독립적인 리소스 관리 및 스케일링
- ✅ MLflow를 통한 중앙화된 실험 관리
- ✅ 무중단 배포 (롤링 업데이트)

---

## 📐 아키텍처 비교

### Before: 모놀리식 구조

```
┌─────────────────────────────────┐
│     Single Docker Container      │
│                                  │
│  ┌────────────────────────────┐ │
│  │  FastAPI (Serving)         │ │
│  │  + Training Scripts        │ │
│  │  + MLflow                  │ │
│  │                            │ │
│  │  ⚠️  리소스 경합            │ │
│  │  ⚠️  배포 시 전체 중단      │ │
│  └────────────────────────────┘ │
└─────────────────────────────────┘
```

**문제점:**
- 훈련 중 API 성능 저하
- 모델 업데이트 시 서비스 중단
- 리소스 최적화 어려움
- 확장성 제한

### After: Kubernetes 마이크로서비스

```
┌──────────────────────────────────────────────────┐
│        Kubernetes Cluster (k3s)                   │
│                                                   │
│  ┌──────────────────┐    ┌────────────────────┐ │
│  │ mlops-training   │    │  mlops-serving     │ │
│  │ ────────────────│    │  ──────────────────│ │
│  │                  │    │                    │ │
│  │ MLflow Server    │◄───┤  API Server x2     │ │
│  │ (1 replica)      │    │  (2 replicas)      │ │
│  │                  │    │                    │ │
│  │ Training Job     │    │  LoadBalancer      │ │
│  │ (필요 시 실행)   │    │  (외부 접근)       │ │
│  │                  │    │                    │ │
│  │ 📊 2 CPU, 4GB   │    │  📊 0.1 CPU, 256MB │ │
│  └────────┬─────────┘    └─────────┬──────────┘ │
│           │                        │             │
│           └────────┬───────────────┘             │
│                    │                             │
│          ┌─────────▼─────────┐                   │
│          │  Shared Storage   │                   │
│          │  ─────────────────│                   │
│          │  • models/        │                   │
│          │  • mlruns/        │                   │
│          │  • mlflow.db      │                   │
│          └───────────────────┘                   │
└──────────────────────────────────────────────────┘
```

**이점:**
- ✅ 독립적인 리소스 할당
- ✅ 무중단 롤링 업데이트
- ✅ 자동 복구 (Self-healing)
- ✅ 수평 확장 (Horizontal Scaling)

---

## 🚀 빠른 시작

### 1. 전제 조건

```bash
# k3s 설치 (아직 설치 안 했다면)
curl -sfL https://get.k3s.io | sh -

# kubectl 설정
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $USER ~/.kube/config

# 확인
kubectl get nodes
```

### 2. 전체 배포 (원스텝)

```bash
# 프로젝트 루트에서 실행
cd /app

# 배포 스크립트 실행
./k8s/deploy.sh
```

이 명령어로 다음이 자동으로 실행됩니다:
1. Docker 이미지 빌드 (training, serving)
2. 네임스페이스 생성
3. 공유 스토리지 설정
4. MLflow 서버 배포
5. 서빙 API 배포

### 3. 모델 훈련 실행

```bash
# 기본 설정으로 훈련
./k8s/train.sh

# 커스텀 하이퍼파라미터로 훈련
./k8s/train.sh \
  --n-estimators 200 \
  --max-depth 20 \
  --run-name "experiment-001"
```

### 4. 서비스 접속

#### Training Controller UI (추천! 웹에서 훈련 시작)

```bash
# 터미널 1: 포트포워딩
kubectl port-forward -n mlops-training svc/training-controller-service 8080:8080

# 브라우저에서 http://localhost:8080 접속
# → 클릭만으로 훈련 시작!
```

#### MLflow UI

```bash
# 터미널 2: 포트포워딩
kubectl port-forward -n mlops-training svc/mlflow-service 5000:5000

# 브라우저에서 http://localhost:5000 접속
```

#### 서빙 API

```bash
# 터미널 3: 포트포워딩
kubectl port-forward -n mlops-serving svc/iris-serving-service 8000:80

# API 테스트
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"features": [5.1, 3.5, 1.4, 0.2]}'

# Swagger UI: http://localhost:8000/docs
```

---

## 📊 리소스 구성

### Training 환경 (mlops-training)

| 리소스 | 사양 | 설명 |
|--------|------|------|
| **Training Controller** | 0.1-0.2 CPU<br/>256-512MB | 웹 UI (훈련 트리거) |
| **MLflow Server** | 0.2-0.5 CPU<br/>512MB-1GB | 실험 추적 서버 (항상 실행) |
| **Training Job** | 1-2 CPU<br/>2-4GB | 모델 훈련 (필요 시 실행) |
| **Storage** | 2GB | 모델 및 MLflow 데이터 |

### Serving 환경 (mlops-serving)

| 리소스 | 사양 | 설명 |
|--------|------|------|
| **API Server** | 0.1-0.3 CPU<br/>256-512MB | 추론 서버 (2개 복제본) |
| **Load Balancer** | k3s 내장 | 트래픽 분산 |
| **Storage** | 2GB (읽기 전용) | 모델 로딩 |

---

## 🔄 일반 작업 흐름

### 실험 → 훈련 → 배포 사이클

**방법 1: 웹 UI 사용 (추천!)**

```bash
# 1. Training Controller UI 접속
kubectl port-forward -n mlops-training svc/training-controller-service 8080:8080
# → http://localhost:8080

# 2. 브라우저에서:
#    - n_estimators: 150
#    - run_name: "exp-v2"
#    - "훈련 시작" 버튼 클릭

# 3. 실시간으로 Job 상태 확인 (자동 새로고침)

# 4. MLflow에서 결과 확인
# http://localhost:5000

# 5. API 테스트
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"features": [5.1, 3.5, 1.4, 0.2]}'
```

**방법 2: 명령어 사용**

```bash
# 1. 새로운 실험 실행
./k8s/train.sh --n-estimators 150 --run-name "exp-v2"

# 2. MLflow에서 결과 확인
# http://localhost:5000

# 3. 모델이 자동으로 저장됨 (/data/mlops/models/)

# 4. 서빙 API가 자동으로 최신 모델 로드
# (또는 API 재시작으로 강제 로드)
kubectl rollout restart deployment/iris-serving -n mlops-serving

# 5. API 테스트
curl -X POST http://localhost:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"features": [5.1, 3.5, 1.4, 0.2]}'
```

---

## 📁 파일 구조

```
ops_demo/
├── app/                          # FastAPI 서빙 코드
├── scripts/                      # 훈련 스크립트
│   └── train_pipeline_mlflow.py
├── k8s/                          # Kubernetes 매니페스트
│   ├── 01-namespaces.yaml        # 네임스페이스 정의
│   ├── 02-storage.yaml           # 공유 스토리지
│   ├── 03-mlflow.yaml            # MLflow 서버
│   ├── 04-training-job.yaml      # 훈련 Job 템플릿
│   ├── 05-serving.yaml           # 서빙 API
│   ├── deploy.sh                 # 전체 배포 스크립트
│   ├── train.sh                  # 훈련 실행 스크립트
│   ├── cleanup.sh                # 환경 정리
│   └── README.md                 # 상세 가이드
├── Dockerfile.training           # 훈련용 이미지
├── Dockerfile.serving            # 서빙용 이미지 (경량)
├── requirements-training.txt     # 훈련 의존성
├── requirements-serving.txt      # 서빙 의존성 (최소화)
└── KUBERNETES.md                 # 이 문서
```

---

## 🔍 모니터링 및 디버깅

### 상태 확인

```bash
# 전체 상태 확인
kubectl get all -A | grep mlops

# Training 환경
kubectl get pods,svc,jobs -n mlops-training

# Serving 환경
kubectl get pods,svc,deployment -n mlops-serving
```

### 로그 확인

```bash
# MLflow 로그
kubectl logs -f deployment/mlflow-server -n mlops-training

# 훈련 로그
kubectl logs -f job/iris-training -n mlops-training

# 서빙 로그
kubectl logs -f deployment/iris-serving -n mlops-serving
```

### 리소스 사용량

```bash
# Pod별 리소스
kubectl top pods -n mlops-training
kubectl top pods -n mlops-serving

# 노드 전체
kubectl top nodes
```

---

## 🔧 고급 사용법

### 병렬 실험 실행

```bash
# 여러 실험을 동시에 실행
for i in {1..5}; do
  ./k8s/train.sh \
    --n-estimators $((50 * i)) \
    --run-name "parallel-exp-$i" &
done

# 모든 Job 상태 확인
kubectl get jobs -n mlops-training
```

### 서빙 API 스케일링

```bash
# 복제본 수 증가
kubectl scale deployment/iris-serving --replicas=5 -n mlops-serving

# 확인
kubectl get pods -n mlops-serving
```

### 이미지 업데이트 및 무중단 배포

```bash
# 1. 새 이미지 빌드
docker build -f Dockerfile.serving -t ops-demo:serving:v2 .

# 2. k3s에 import
docker save ops-demo:serving:v2 | sudo k3s ctr images import -

# 3. 롤링 업데이트
kubectl set image deployment/iris-serving \
  serving=ops-demo:serving:v2 -n mlops-serving

# 4. 롤아웃 진행 상황 확인
kubectl rollout status deployment/iris-serving -n mlops-serving
```

---

## 🧹 정리

### 전체 환경 삭제

```bash
./k8s/cleanup.sh
```

### 호스트 데이터 삭제

```bash
sudo rm -rf /data/mlops
```

---

## 🆚 기존 vs Kubernetes 명령어 비교

| 작업 | 기존 (Docker Compose) | Kubernetes |
|------|----------------------|------------|
| **환경 시작** | `docker-compose up -d` | `./k8s/deploy.sh` |
| **훈련 실행** | `docker exec ops_demo python scripts/train_pipeline_mlflow.py --n-estimators 200` | `./k8s/train.sh --n-estimators 200` |
| **로그 확인** | `docker logs -f ops_demo` | `kubectl logs -f deployment/iris-serving -n mlops-serving` |
| **재시작** | `docker-compose restart` | `kubectl rollout restart deployment/iris-serving -n mlops-serving` |
| **정리** | `docker-compose down` | `./k8s/cleanup.sh` |

---

## 📈 실무 확장 로드맵

### Phase 1: 기본 환경 (현재)
- ✅ 훈련/서빙 분리
- ✅ MLflow 통합
- ✅ 수동 스케일링

### Phase 2: 자동화
- ⬜ Horizontal Pod Autoscaler (HPA)
- ⬜ CI/CD 파이프라인 (GitHub Actions)
- ⬜ Helm Charts로 패키징

### Phase 3: 고급 기능
- ⬜ GPU 지원
- ⬜ Kubeflow 통합
- ⬜ A/B 테스트 배포
- ⬜ 카나리 배포

### Phase 4: 프로덕션
- ⬜ Prometheus/Grafana 모니터링
- ⬜ Istio 서비스 메시
- ⬜ 멀티 클러스터 배포
- ⬜ 재해 복구 (DR)

---

## 🐛 문제 해결

### Q: Pod가 Pending 상태로 남아있습니다

```bash
# 원인 확인
kubectl describe pod <pod-name> -n mlops-training

# 일반적인 원인:
# 1. PVC가 바인딩되지 않음 → kubectl get pvc -A
# 2. 리소스 부족 → kubectl top nodes
# 3. 노드 선택자 불일치 → Pod spec 확인
```

### Q: 이미지를 찾을 수 없습니다 (ImagePullBackOff)

```bash
# k3s는 로컬 Docker 이미지를 자동으로 사용하지 않음
# 수동으로 import 필요:
docker save ops-demo:training | sudo k3s ctr images import -
docker save ops-demo:serving | sudo k3s ctr images import -
```

### Q: MLflow 서버에 연결할 수 없습니다

```bash
# DNS 확인
kubectl run -it --rm debug --image=busybox --restart=Never -- \
  nslookup mlflow-service.mlops-training.svc.cluster.local

# MLflow 서버 로그 확인
kubectl logs deployment/mlflow-server -n mlops-training

# 포트포워딩으로 직접 접속 테스트
kubectl port-forward -n mlops-training svc/mlflow-service 5000:5000
```

### Q: 스토리지 접근 권한 오류

```bash
# 호스트 디렉토리 권한 확인
sudo chmod 777 /data/mlops

# Pod에서 실제 마운트 확인
kubectl exec -it <pod-name> -n mlops-training -- ls -la /data
```

---

## 📚 추가 자료

- **상세 가이드**: [k8s/README.md](k8s/README.md)
- **Kubernetes 문서**: https://kubernetes.io/docs/
- **k3s 문서**: https://k3s.io/
- **MLflow 문서**: https://mlflow.org/docs/

---

## 💡 팁

1. **개발 시**: 로컬에서 Docker Compose 사용
2. **테스트 시**: k3s로 Kubernetes 환경 검증
3. **프로덕션**: 클라우드 Kubernetes (EKS/GKE/AKS) 사용

이렇게 하면 개발 속도와 운영 안정성을 모두 확보할 수 있습니다!

---

**Happy MLOps! 🚀**

