#!/bin/bash

# localhost 접근을 위한 서비스 타입 변경 스크립트
set -e

echo "======================================"
echo "localhost 접근 설정"
echo "======================================"
echo ""

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 현재 서비스 타입 확인
echo "현재 서비스 타입:"
kubectl get svc -n mlops-training
kubectl get svc -n mlops-serving
echo ""

# 서비스 타입을 NodePort로 변경
echo -e "${YELLOW}→ 서비스 타입을 NodePort로 변경 중...${NC}"
echo ""

# Training Controller
echo "1. Training Controller (port 30081)"
kubectl patch svc training-controller-service -n mlops-training \
  -p '{"spec": {"type": "NodePort", "ports": [{"port": 8080, "targetPort": 8080, "nodePort": 30081, "protocol": "TCP", "name": "http"}]}}'
echo -e "   ${GREEN}✓${NC} 완료"

# MLflow
echo "2. MLflow (port 30501)"
kubectl patch svc mlflow-service -n mlops-training \
  -p '{"spec": {"type": "NodePort", "ports": [{"port": 5000, "targetPort": 5000, "nodePort": 30501, "protocol": "TCP", "name": "http"}]}}'
echo -e "   ${GREEN}✓${NC} 완료"

# Serving API
echo "3. Serving API (port 30801)"
kubectl patch svc iris-serving-service -n mlops-serving \
  -p '{"spec": {"type": "NodePort", "ports": [{"port": 80, "targetPort": 8000, "nodePort": 30801, "protocol": "TCP", "name": "http"}]}}'
echo -e "   ${GREEN}✓${NC} 완료"

echo ""
echo "======================================"
echo -e "${GREEN}설정 완료!${NC}"
echo "======================================"
echo ""

# 변경된 서비스 확인
echo "변경된 서비스:"
kubectl get svc -n mlops-training
kubectl get svc -n mlops-serving
echo ""

echo "======================================"
echo "접속 정보 (localhost)"
echo "======================================"
echo ""
echo "🎯 Training Controller UI:"
echo "   http://localhost:30081"
echo ""
echo "📊 MLflow UI:"
echo "   http://localhost:30501"
echo ""
echo "🚀 Serving API:"
echo "   http://localhost:30801"
echo "   Swagger UI: http://localhost:30801/docs"
echo ""
echo "======================================"
echo ""

