#!/bin/bash

# 빠른 배포 스크립트 (SSH 연결 끊김 방지)
set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo "======================================"
echo "빠른 배포 시작"
echo "======================================"
echo ""

# 1. 이미지 상태 확인
echo -e "${YELLOW}[1/6] Docker 이미지 확인${NC}"
echo "----------------------------------------"
if docker images | grep "ops-demo:training" > /dev/null; then
    echo -e "  ${GREEN}✓${NC} training 이미지 존재"
else
    echo "  ⚠ training 이미지 없음 - 빌드 필요"
fi

if docker images | grep "ops-demo:serving" > /dev/null; then
    echo -e "  ${GREEN}✓${NC} serving 이미지 존재"
else
    echo "  ⚠ serving 이미지 없음 - 빌드 필요"
fi

if docker images | grep "ops-demo:training-controller" > /dev/null; then
    echo -e "  ${GREEN}✓${NC} training-controller 이미지 존재"
else
    echo "  ⚠ training-controller 이미지 없음 - 빌드 필요"
fi

# 2. 네임스페이스
echo ""
echo -e "${YELLOW}[2/6] 네임스페이스 적용${NC}"
echo "----------------------------------------"
kubectl apply -f 01-namespaces.yaml
echo -e "  ${GREEN}✓${NC} 완료"

# 3. 스토리지
echo ""
echo -e "${YELLOW}[3/6] 스토리지 적용${NC}"
echo "----------------------------------------"
sudo mkdir -p /data/mlops
sudo chmod 777 /data/mlops
kubectl apply -f 02-storage.yaml
echo -e "  ${GREEN}✓${NC} 완료"

# 4. MLflow
echo ""
echo -e "${YELLOW}[4/6] MLflow 배포${NC}"
echo "----------------------------------------"
kubectl apply -f 03-mlflow.yaml
echo -e "  ${GREEN}✓${NC} 배포 완료"
echo "  → Pod 상태 확인 중..."
sleep 5
kubectl get pods -n mlops-training -l app=mlflow-server

# 5. Training Controller
echo ""
echo -e "${YELLOW}[5/6] Training Controller 배포${NC}"
echo "----------------------------------------"
kubectl apply -f 06-training-controller.yaml
echo -e "  ${GREEN}✓${NC} 배포 완료"
echo "  → Pod 상태 확인 중..."
sleep 5
kubectl get pods -n mlops-training -l app=training-controller

# 6. Serving API
echo ""
echo -e "${YELLOW}[6/6] Serving API 배포${NC}"
echo "----------------------------------------"
kubectl apply -f 05-serving.yaml
echo -e "  ${GREEN}✓${NC} 배포 완료"
echo "  → Pod 상태 확인 중..."
sleep 5
kubectl get pods -n mlops-serving -l app=iris-serving

echo ""
echo "======================================"
echo -e "${GREEN}배포 완료!${NC}"
echo "======================================"
echo ""

# 서비스 확인
echo "서비스 상태:"
kubectl get svc -n mlops-training
kubectl get svc -n mlops-serving

echo ""
echo "======================================"
echo "접속 정보"
echo "======================================"
echo ""
echo -e "${BLUE}🎯 Training Controller UI:${NC}"
echo "   http://localhost:30080"
echo ""
echo -e "${BLUE}📊 MLflow UI:${NC}"
echo "   http://localhost:30500"
echo ""
echo -e "${BLUE}🚀 Serving API:${NC}"
echo "   http://localhost:30800"
echo "   http://localhost:30800/docs"
echo ""

# Pod 상태 모니터링 (백그라운드)
echo "======================================"
echo "Pod 상태 모니터링 (30초)"
echo "======================================"
echo ""

for i in {1..6}; do
    echo "--- ${i}/6 (5초 간격) ---"
    kubectl get pods -n mlops-training
    kubectl get pods -n mlops-serving
    echo ""
    if [ $i -lt 6 ]; then
        sleep 5
    fi
done

echo "======================================"
echo -e "${GREEN}모든 작업 완료!${NC}"
echo "======================================"

