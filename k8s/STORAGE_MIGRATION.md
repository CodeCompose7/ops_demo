# 📦 스토리지 경로 변경 가이드

## 🎯 변경 사항

### 이전 (Old)
```bash
/data/mlops  # 루트 디렉토리 (sudo 필요)
```

### 이후 (New)
```bash
$HOME/ops-demo-data/mlops  # 사용자 홈 디렉토리 (sudo 불필요)
```

---

## 🔍 변경 이유

1. **권한 문제 해결** 🔐
   - 루트 폴더(`/data/*`)는 sudo 권한 필요
   - 사용자 홈 디렉토리는 자동으로 접근 가능

2. **보안 향상** 🛡️
   - sudo 사용 최소화
   - 사용자별 격리된 환경

3. **배포 간소화** 🚀
   - GitHub Actions에서 권한 문제 없이 배포 가능
   - 임시 프로젝트에 적합

---

## 🔄 마이그레이션 방법

### 기존 데이터가 있는 경우

```bash
# 1. 기존 데이터 백업 (선택)
sudo cp -r /data/mlops $HOME/ops-demo-data/mlops-backup

# 2. 새 디렉토리로 이동
mkdir -p $HOME/ops-demo-data/mlops
sudo cp -r /data/mlops/* $HOME/ops-demo-data/mlops/ 2>/dev/null || true

# 3. 권한 확인
ls -la $HOME/ops-demo-data/mlops

# 4. Kubernetes 리소스 재배포
kubectl delete -f k8s/02-storage.yaml
STORAGE_DIR="$HOME/ops-demo-data/mlops"
sed "s|/data/mlops|$STORAGE_DIR|g" k8s/02-storage.yaml | kubectl apply -f -

# 5. Pod 재시작
kubectl rollout restart deployment/mlflow-server -n mlops-training
kubectl rollout restart deployment/iris-serving -n mlops-serving

# 6. 구 데이터 삭제 (확인 후)
# sudo rm -rf /data/mlops
```

### 신규 배포

```bash
# 자동으로 처리됨 - 수동 작업 불필요!
cd ~/ops-demo/k8s
./auto-deploy.sh latest
```

---

## 📝 배포 스크립트 자동 처리

모든 배포 스크립트는 자동으로 경로를 치환합니다:

```bash
# 스토리지 디렉토리 생성
STORAGE_DIR="$HOME/ops-demo-data/mlops"
mkdir -p $STORAGE_DIR

# PersistentVolume 경로 치환
sed "s|/data/mlops|$STORAGE_DIR|g" 02-storage.yaml | kubectl apply -f -
```

### 적용된 스크립트
- ✅ `k8s/deploy.sh`
- ✅ `k8s/quick-deploy.sh`
- ✅ `k8s/auto-deploy.sh`
- ✅ `.github/workflows/cd-webhook.yml`
- ✅ `k8s/setup-project.sh`

---

## 🔧 수동 배포 시 주의사항

`kubectl apply`를 직접 사용하는 경우:

```bash
# ❌ 직접 적용하지 마세요
kubectl apply -f 02-storage.yaml

# ✅ sed로 치환 후 적용하세요
STORAGE_DIR="$HOME/ops-demo-data/mlops"
sed "s|/data/mlops|$STORAGE_DIR|g" 02-storage.yaml | kubectl apply -f -
```

---

## 📊 스토리지 구조

```
$HOME/
└── ops-demo-data/
    └── mlops/
        ├── mlruns/              # MLflow 실험 데이터
        │   ├── 0/
        │   └── 1/
        └── models/              # 저장된 모델
            └── iris_model.pkl
```

---

## 🔍 문제 해결

### Q: 기존 데이터가 보이지 않아요

**확인:**
```bash
# 구 디렉토리
sudo ls -la /data/mlops

# 신 디렉토리
ls -la $HOME/ops-demo-data/mlops
```

**해결:** 위의 "마이그레이션 방법" 참고

### Q: Permission denied 에러

```bash
# 권한 확인
ls -la $HOME/ops-demo-data/

# 권한 수정 (필요 시)
chmod 755 $HOME/ops-demo-data/mlops
```

### Q: Pod가 Pending 상태

```bash
# PV 상태 확인
kubectl get pv mlops-shared-pv

# hostPath 확인
kubectl describe pv mlops-shared-pv | grep Path

# 디렉토리 존재 확인
ls -la $(kubectl get pv mlops-shared-pv -o jsonpath='{.spec.hostPath.path}')
```

---

## 🎉 장점 요약

| 항목 | 이전 (/data/mlops) | 이후 ($HOME/ops-demo-data/mlops) |
|------|-------------------|----------------------------------|
| **권한** | sudo 필요 | sudo 불필요 |
| **보안** | 전역 접근 | 사용자별 격리 |
| **배포** | 수동 권한 설정 필요 | 자동 처리 |
| **CI/CD** | 권한 문제 발생 가능 | 원활한 자동화 |
| **관리** | 시스템 관리자 필요 | 개발자가 직접 관리 |

---

## 📚 관련 문서

- [배포 가이드](./DEPLOYMENT_GUIDE.md)
- [초기 설정](./SETUP.md)
- [문제 해결](./TROUBLESHOOTING.md)

---

**✨ 이제 sudo 없이 편리하게 배포하세요!** 🚀

