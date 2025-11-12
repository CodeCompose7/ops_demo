#!/bin/bash

# Kubernetes MLOps 환경 정리 스크립트
set -e

RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

echo "======================================"
echo -e "${RED}MLOps 환경 정리${NC}"
echo "======================================"
echo ""
echo -e "${YELLOW}경고: 모든 리소스가 삭제됩니다!${NC}"
echo ""
read -p "계속하시겠습니까? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "취소됨"
    exit 1
fi

echo ""
echo "→ 서빙 API 삭제 중..."
kubectl delete -f k8s/05-serving.yaml --ignore-not-found=true

echo "→ 훈련 Job 삭제 중..."
kubectl delete -f k8s/04-training-job.yaml --ignore-not-found=true
kubectl delete jobs --all -n mlops-training --ignore-not-found=true

echo "→ MLflow 서버 삭제 중..."
kubectl delete -f k8s/03-mlflow.yaml --ignore-not-found=true

echo "→ 스토리지 삭제 중..."
kubectl delete -f k8s/02-storage.yaml --ignore-not-found=true

echo "→ 네임스페이스 삭제 중..."
kubectl delete -f k8s/01-namespaces.yaml --ignore-not-found=true

echo ""
echo -e "${GREEN}✓ 정리 완료${NC}"
echo ""
echo "호스트 데이터도 삭제하려면:"
echo "  sudo rm -rf /data/mlops"
echo ""

