# 문제 해결 가이드

## 🔴 ImagePullBackOff 에러

### 증상
```
mlops-training   mlflow-server-xxx              0/1   ImagePullBackOff
mlops-training   training-controller-xxx        0/1   ImagePullBackOff
mlops-serving    iris-serving-xxx               0/1   ImagePullBackOff
```

### 원인
Docker 이미지가 k3s에 import되지 않음

### 해결 방법

#### 자동 해결 (권장)
```bash
cd /app/k8s
./fix-images.sh
```

#### 수동 해결
```bash
# 1. 이미지 빌드
cd /app
docker build -f Dockerfile.training -t ops-demo:training .
docker build -f Dockerfile.serving -t ops-demo:serving .
docker build -f training-controller/Dockerfile -t ops-demo:training-controller training-controller/

# 2. k3s에 import
docker save ops-demo:training | sudo k3s ctr images import -
docker save ops-demo:serving | sudo k3s ctr images import -
docker save ops-demo:training-controller | sudo k3s ctr images import -

# 3. Pod 재시작
kubectl rollout restart deployment/mlflow-server -n mlops-training
kubectl rollout restart deployment/training-controller -n mlops-training
kubectl rollout restart deployment/iris-serving -n mlops-serving

# 4. 상태 확인
kubectl get pods -n mlops-training
kubectl get pods -n mlops-serving
```

---

## 🟡 Pending 상태

### 증상
```
mlops-serving    iris-serving-xxx               0/1   Pending
```

### 원인 1: 리소스 부족

**확인:**
```bash
kubectl describe pod <pod-name> -n mlops-serving
# Events 섹션에서 "Insufficient cpu" 또는 "Insufficient memory" 확인
```

**해결:**
```bash
# 리소스 요구사항 줄이기
# k8s/05-serving.yaml 수정
resources:
  requests:
    cpu: "50m"      # 100m → 50m
    memory: "128Mi" # 256Mi → 128Mi
  limits:
    cpu: "200m"     # 300m → 200m
    memory: "256Mi" # 512Mi → 256Mi

# 적용
kubectl apply -f k8s/05-serving.yaml
```

### 원인 2: PVC 바인딩 실패

**확인:**
```bash
kubectl get pvc -A
# STATUS가 Bound가 아니면 문제
```

**해결:**
```bash
# PV, PVC 재생성
kubectl delete -f k8s/02-storage.yaml
mkdir -p $HOME/ops-demo-data/mlops
STORAGE_DIR="$HOME/ops-demo-data/mlops"
sed "s|/data/mlops|$STORAGE_DIR|g" k8s/02-storage.yaml | kubectl apply -f -
```

### 원인 3: 이미지 문제

Pending 상태가 오래 지속되면 이미지 문제일 수 있음 → ImagePullBackOff 해결 방법 참고

---

## 🔵 CrashLoopBackOff 에러

### 증상
```
mlops-training   mlflow-server-xxx              0/1   CrashLoopBackOff
```

### 해결
```bash
# 로그 확인
kubectl logs <pod-name> -n mlops-training

# 일반적인 문제:
# 1. 스토리지 권한 문제
chmod 777 $HOME/ops-demo-data/mlops

# 2. 환경변수 문제 - Deployment 확인
kubectl describe deployment mlflow-server -n mlops-training

# 3. 재시작
kubectl rollout restart deployment/mlflow-server -n mlops-training
```

---

## 🟢 연결 거부 (Connection Refused)

### 증상
```bash
curl http://localhost:30081
# curl: (7) Failed to connect to localhost port 30081: Connection refused
```

### 원인 1: Pod가 실행되지 않음

**확인:**
```bash
kubectl get pods -n mlops-training
# STATUS가 Running이 아니면 위의 문제 해결 먼저
```

### 원인 2: 서비스 포트 확인

**확인:**
```bash
kubectl get svc -n mlops-training
# NodePort 확인: 8080:30081/TCP
```

### 원인 3: 방화벽

**해결:**
```bash
# 포트 열기 (필요 시)
sudo ufw allow 30081/tcp
sudo ufw allow 30501/tcp
sudo ufw allow 30801/tcp

# 또는 firewalld
sudo firewall-cmd --add-port=30081/tcp --permanent
sudo firewall-cmd --add-port=30501/tcp --permanent
sudo firewall-cmd --add-port=30801/tcp --permanent
sudo firewall-cmd --reload
```

---

## 🔍 진단 명령어 모음

### 전체 상태 확인
```bash
# Pod 상태
kubectl get pods -A

# 서비스 상태
kubectl get svc -A

# Deployment 상태
kubectl get deployments -A

# PVC 상태
kubectl get pvc -A
```

### 상세 정보
```bash
# Pod 상세 정보
kubectl describe pod <pod-name> -n <namespace>

# Deployment 상세 정보
kubectl describe deployment <deployment-name> -n <namespace>

# 서비스 상세 정보
kubectl describe svc <service-name> -n <namespace>
```

### 로그 확인
```bash
# 실시간 로그
kubectl logs -f <pod-name> -n <namespace>

# 이전 로그 (재시작된 경우)
kubectl logs <pod-name> -n <namespace> --previous

# 마지막 100줄
kubectl logs <pod-name> -n <namespace> --tail=100
```

### 이미지 확인
```bash
# Docker 이미지
docker images | grep ops-demo

# k3s 이미지
sudo k3s crictl images | grep ops-demo
```

---

## 🔧 완전 재설치

모든 것을 처음부터 다시 시작:

```bash
# 1. 모든 리소스 삭제
kubectl delete namespace mlops-training
kubectl delete namespace mlops-serving
rm -rf $HOME/ops-demo-data/mlops

# 2. 이미지 재빌드
cd $HOME/ops-demo
docker build -f Dockerfile.training -t ops-demo:training .
docker build -f Dockerfile.serving -t ops-demo:serving .
docker build -f training-controller/Dockerfile -t ops-demo:training-controller training-controller/

# 3. k3s에 import
docker save ops-demo:training | sudo k3s ctr images import -
docker save ops-demo:serving | sudo k3s ctr images import -
docker save ops-demo:training-controller | sudo k3s ctr images import -

# 4. 재배포
cd k8s
./quick-deploy.sh
```

---

## 📊 헬스체크

모든 것이 정상인지 확인:

```bash
# Pod 상태 (모두 Running이어야 함)
kubectl get pods -n mlops-training
kubectl get pods -n mlops-serving

# 서비스 접근 테스트
curl http://localhost:30081/health  # Training Controller
curl http://localhost:30501          # MLflow
curl http://localhost:30801/health  # Serving API

# 모두 200 OK 또는 정상 응답이면 성공!
```

---

## 🆘 추가 도움

위의 방법으로 해결되지 않으면:

1. **로그 수집:**
```bash
kubectl logs <pod-name> -n <namespace> > pod.log
kubectl describe pod <pod-name> -n <namespace> > pod-describe.log
```

2. **시스템 리소스 확인:**
```bash
kubectl top nodes
kubectl top pods -A
df -h  # 디스크 공간
free -h  # 메모리
```

3. **k3s 상태 확인:**
```bash
sudo systemctl status k3s
sudo journalctl -u k3s -f
```

