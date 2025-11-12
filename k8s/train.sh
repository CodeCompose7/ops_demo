#!/bin/bash

# Kubernetes에서 훈련 Job 실행 스크립트
set -e

# 기본값 설정
N_ESTIMATORS=100
MAX_DEPTH=5
RUN_NAME="k8s-training-$(date +%Y%m%d-%H%M%S)"

# 색상 정의
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 사용법 출력
usage() {
    echo "사용법: $0 [옵션]"
    echo ""
    echo "옵션:"
    echo "  --n-estimators NUM    RandomForest의 트리 개수 (기본값: 100)"
    echo "  --max-depth NUM       트리의 최대 깊이 (기본값: 5)"
    echo "  --run-name NAME       MLflow run 이름 (기본값: k8s-training-TIMESTAMP)"
    echo "  -h, --help            도움말 표시"
    echo ""
    echo "예시:"
    echo "  $0 --n-estimators 200 --max-depth 20 --run-name 'experiment-001'"
    exit 1
}

# 인자 파싱
while [[ $# -gt 0 ]]; do
    case $1 in
        --n-estimators)
            N_ESTIMATORS="$2"
            shift 2
            ;;
        --max-depth)
            MAX_DEPTH="$2"
            shift 2
            ;;
        --run-name)
            RUN_NAME="$2"
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            echo "알 수 없는 옵션: $1"
            usage
            ;;
    esac
done

echo "======================================"
echo "Kubernetes 모델 훈련 시작"
echo "======================================"
echo ""
echo "파라미터:"
echo "  - n_estimators: $N_ESTIMATORS"
echo "  - max_depth: $MAX_DEPTH"
echo "  - run_name: $RUN_NAME"
echo ""

# Job 이름 생성 (소문자, 숫자, 하이픈만 허용)
JOB_NAME="iris-training-$(echo $RUN_NAME | tr '[:upper:]' '[:lower:]' | tr '_' '-' | sed 's/[^a-z0-9-]//g')"
JOB_NAME="${JOB_NAME:0:63}"  # Kubernetes 이름 길이 제한

echo -e "${YELLOW}→ Job 이름: $JOB_NAME${NC}"

# 기존 Job 삭제 (있을 경우)
if kubectl get job $JOB_NAME -n mlops-training &>/dev/null; then
    echo -e "${YELLOW}→ 기존 Job 삭제 중...${NC}"
    kubectl delete job $JOB_NAME -n mlops-training --ignore-not-found=true
    sleep 2
fi

# Job YAML 동적 생성
cat > /tmp/training-job.yaml <<EOF
apiVersion: batch/v1
kind: Job
metadata:
  name: $JOB_NAME
  namespace: mlops-training
  labels:
    app: iris-training
    component: training
    run-name: "$RUN_NAME"
spec:
  backoffLimit: 3
  ttlSecondsAfterFinished: 3600
  template:
    metadata:
      labels:
        app: iris-training
        component: training
    spec:
      restartPolicy: Never
      containers:
      - name: training
        image: ops-demo:training
        command:
        - python
        - scripts/train_pipeline_mlflow.py
        args:
        - --n-estimators
        - "$N_ESTIMATORS"
        - --max-depth
        - "$MAX_DEPTH"
        - --run-name
        - "$RUN_NAME"
        env:
        - name: MLFLOW_TRACKING_URI
          value: "http://mlflow-service:5000"
        - name: PYTHONUNBUFFERED
          value: "1"
        volumeMounts:
        - name: mlops-storage
          mountPath: /data
        resources:
          requests:
            cpu: "1000m"
            memory: "2Gi"
          limits:
            cpu: "2000m"
            memory: "4Gi"
      volumes:
      - name: mlops-storage
        persistentVolumeClaim:
          claimName: mlops-pvc
EOF

# Job 실행
echo -e "${YELLOW}→ Job 생성 중...${NC}"
kubectl apply -f /tmp/training-job.yaml

echo -e "${GREEN}✓ Job 생성 완료${NC}"
echo ""

# Pod 이름 가져오기
echo -e "${YELLOW}→ Pod 생성 대기 중...${NC}"
sleep 3

POD_NAME=""
for i in {1..30}; do
    POD_NAME=$(kubectl get pods -n mlops-training -l job-name=$JOB_NAME -o jsonpath='{.items[0].metadata.name}' 2>/dev/null || echo "")
    if [ -n "$POD_NAME" ]; then
        break
    fi
    sleep 1
done

if [ -z "$POD_NAME" ]; then
    echo -e "${RED}오류: Pod를 찾을 수 없습니다${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Pod 생성 완료: $POD_NAME${NC}"
echo ""

# 로그 스트리밍
echo "======================================"
echo -e "${BLUE}훈련 로그 (실시간)${NC}"
echo "======================================"
echo ""

kubectl logs -f $POD_NAME -n mlops-training 2>/dev/null || true

echo ""
echo "======================================"

# Job 상태 확인
JOB_STATUS=$(kubectl get job $JOB_NAME -n mlops-training -o jsonpath='{.status.conditions[0].type}' 2>/dev/null || echo "Unknown")

if [ "$JOB_STATUS" = "Complete" ]; then
    echo -e "${GREEN}✓ 훈련 완료!${NC}"
    echo ""
    echo "MLflow에서 결과 확인:"
    echo "  kubectl port-forward -n mlops-training svc/mlflow-service 5000:5000"
    echo "  → http://localhost:5000"
elif [ "$JOB_STATUS" = "Failed" ]; then
    echo -e "${RED}✗ 훈련 실패${NC}"
    echo ""
    echo "로그 확인:"
    echo "  kubectl logs $POD_NAME -n mlops-training"
else
    echo -e "${YELLOW}훈련 진행 중...${NC}"
    echo ""
    echo "상태 확인:"
    echo "  kubectl get job $JOB_NAME -n mlops-training"
    echo ""
    echo "로그 확인:"
    echo "  kubectl logs -f $POD_NAME -n mlops-training"
fi

echo ""

