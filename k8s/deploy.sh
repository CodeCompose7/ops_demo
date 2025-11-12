#!/bin/bash

# Kubernetes 기반 MLOps 환경 배포 스크립트
set -e

echo "======================================"
echo "MLOps Kubernetes 환경 배포 시작"
echo "======================================"

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 1. Docker 이미지 빌드
echo ""
echo -e "${YELLOW}[1/6] Docker 이미지 빌드${NC}"
echo "----------------------------------------"

echo "  → 훈련용 이미지 빌드 중..."
docker build -f Dockerfile.training -t ops-demo:training . --quiet
echo -e "  ${GREEN}✓${NC} ops-demo:training 빌드 완료"

echo "  → 서빙용 이미지 빌드 중..."
docker build -f Dockerfile.serving -t ops-demo:serving . --quiet
echo -e "  ${GREEN}✓${NC} ops-demo:serving 빌드 완료"

echo "  → Training Controller 이미지 빌드 중..."
docker build -f training-controller/Dockerfile -t ops-demo:training-controller training-controller/ --quiet
echo -e "  ${GREEN}✓${NC} ops-demo:training-controller 빌드 완료"

# 이미지 크기 확인
echo ""
echo "  이미지 크기:"
docker images | grep "ops-demo" | awk '{print "    - " $1 ":" $2 " → " $7 $8}'

# 2. k3s에 이미지 import (필요 시)
if command -v k3s &> /dev/null; then
    echo ""
    echo -e "${YELLOW}[2/6] k3s에 이미지 import${NC}"
    echo "----------------------------------------"
    
    docker save ops-demo:training | sudo k3s ctr images import - 2>/dev/null || true
    echo -e "  ${GREEN}✓${NC} training 이미지 import 완료"
    
    docker save ops-demo:serving | sudo k3s ctr images import - 2>/dev/null || true
    echo -e "  ${GREEN}✓${NC} serving 이미지 import 완료"
    
    docker save ops-demo:training-controller | sudo k3s ctr images import - 2>/dev/null || true
    echo -e "  ${GREEN}✓${NC} training-controller 이미지 import 완료"
else
    echo ""
    echo -e "${YELLOW}[2/6] k3s 감지 안됨 - 이미지 import 건너뛰기${NC}"
fi

# 3. 네임스페이스 생성
echo ""
echo -e "${YELLOW}[3/6] 네임스페이스 생성${NC}"
echo "----------------------------------------"
kubectl apply -f k8s/01-namespaces.yaml
echo -e "  ${GREEN}✓${NC} mlops-training, mlops-serving 네임스페이스 생성"

# 4. 공유 스토리지 설정
echo ""
echo -e "${YELLOW}[4/6] 공유 스토리지 설정${NC}"
echo "----------------------------------------"

# 호스트 디렉토리 생성
sudo mkdir -p /data/mlops
sudo chmod 777 /data/mlops
echo -e "  ${GREEN}✓${NC} 호스트 디렉토리 생성: /data/mlops"

kubectl apply -f k8s/02-storage.yaml
echo -e "  ${GREEN}✓${NC} PersistentVolume 및 PVC 생성"

# PVC 상태 확인
sleep 2
kubectl get pvc -n mlops-training
kubectl get pvc -n mlops-serving

# 5. MLflow 서버 배포
echo ""
echo -e "${YELLOW}[5/7] MLflow 서버 배포${NC}"
echo "----------------------------------------"
kubectl apply -f k8s/03-mlflow.yaml
echo -e "  ${GREEN}✓${NC} MLflow 서버 배포 완료"

# MLflow 서버 준비 대기
echo "  → MLflow 서버 준비 대기 중..."
kubectl wait --for=condition=ready pod -l app=mlflow-server -n mlops-training --timeout=120s
echo -e "  ${GREEN}✓${NC} MLflow 서버 준비 완료"

# 6. Training Controller 배포
echo ""
echo -e "${YELLOW}[6/7] Training Controller 배포${NC}"
echo "----------------------------------------"
kubectl apply -f k8s/06-training-controller.yaml
echo -e "  ${GREEN}✓${NC} Training Controller 배포 완료"

# Training Controller 준비 대기
echo "  → Training Controller 준비 대기 중..."
kubectl wait --for=condition=ready pod -l app=training-controller -n mlops-training --timeout=120s
echo -e "  ${GREEN}✓${NC} Training Controller 준비 완료"

# 7. 서빙 API 배포
echo ""
echo -e "${YELLOW}[7/7] 서빙 API 배포${NC}"
echo "----------------------------------------"
kubectl apply -f k8s/05-serving.yaml
echo -e "  ${GREEN}✓${NC} 서빙 API 배포 완료"

# 서빙 Pod 준비 대기
echo "  → 서빙 Pod 준비 대기 중..."
kubectl wait --for=condition=ready pod -l app=iris-serving -n mlops-serving --timeout=120s
echo -e "  ${GREEN}✓${NC} 서빙 API 준비 완료"

# 배포 완료
echo ""
echo "======================================"
echo -e "${GREEN}MLOps 환경 배포 완료!${NC}"
echo "======================================"
echo ""

# 상태 확인
echo "현재 배포 상태:"
echo ""
echo "📊 Training 네임스페이스:"
kubectl get pods,svc -n mlops-training
echo ""
echo "🚀 Serving 네임스페이스:"
kubectl get pods,svc -n mlops-serving

# 접속 정보
echo ""
echo "======================================"
echo "접속 정보"
echo "======================================"

# 접속 정보 (NodePort 사용)
echo ""
echo "🎯 Training Controller UI (웹에서 훈련 시작):"
echo "   http://localhost:30081"

echo ""
echo "📊 MLflow UI (실험 추적):"
echo "   http://localhost:30501"

echo ""
echo "🚀 Serving API:"
echo "   http://localhost:30801"
echo "   Swagger UI: http://localhost:30801/docs"

echo ""
echo "======================================"
echo "다음 단계"
echo "======================================"
echo ""
echo "1. 웹 UI에서 모델 훈련 (추천!):"
echo "   브라우저에서 http://localhost:30081 접속"
echo ""
echo "2. 또는 명령어로 훈련:"
echo "   ./k8s/train.sh --n-estimators 200 --max-depth 20 --run-name 'my-experiment'"
echo ""
echo "3. API 테스트:"
echo "   curl -X POST http://localhost:30801/predict \\"
echo "     -H 'Content-Type: application/json' \\"
echo "     -d '{\"features\": [5.1, 3.5, 1.4, 0.2]}'"
echo ""

