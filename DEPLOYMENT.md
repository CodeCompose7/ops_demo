# GitHub Actions를 통한 Kubernetes 자동 배포

이 문서는 GitHub Actions CD 파이프라인을 통해 Kubernetes 환경으로 자동 배포하는 방법을 설명합니다.

## 🎯 배포 워크플로우

```
GitHub Release 생성
    ↓
Docker 이미지 빌드 (Training & Serving)
    ↓
서버로 이미지 전송 (SSH/SCP)
    ↓
Kubernetes에 무중단 배포
    ↓
배포 상태 확인
```

---

## 🔧 사전 준비

### 1. 서버에 k3s 설치

```bash
# SSH로 배포 서버 접속
ssh user@your-server

# k3s 설치
curl -sfL https://get.k3s.io | sh -

# kubectl 설정
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $USER ~/.kube/config

# 확인
kubectl get nodes
```

### 2. GitHub Secrets 설정

GitHub 저장소 → Settings → Secrets and variables → Actions에서 다음 Secrets를 추가:

| Secret 이름 | 설명 | 예시 |
|-------------|------|------|
| `SSH_PRIVATE_KEY` | 서버 접속용 SSH 개인키 | `-----BEGIN OPENSSH PRIVATE KEY-----...` |
| `DEPLOY_USER` | 서버 사용자명 | `ubuntu` 또는 `root` |
| `DEPLOY_HOST` | 서버 IP 또는 도메인 | `123.456.789.0` 또는 `example.com` |
| `DEPLOY_PORT` | SSH 포트 (선택) | `22` (기본값) |

### 3. SSH 키 설정

**로컬에서:**

```bash
# SSH 키 생성 (없으면)
ssh-keygen -t ed25519 -C "github-actions@deploy"

# 공개키 확인 (GitHub Secret에 등록할 내용)
cat ~/.ssh/id_ed25519
```

**서버에서:**

```bash
# 공개키를 authorized_keys에 추가
echo "your-public-key-here" >> ~/.ssh/authorized_keys

# 권한 설정
chmod 700 ~/.ssh
chmod 600 ~/.ssh/authorized_keys
```

---

## 🚀 배포 실행

### 방법 1: GitHub UI에서 Release 생성

1. GitHub 저장소 → Releases → **Create a new release**
2. **Tag version** 입력 (예: `v1.0.0`)
3. **Release title** 입력
4. **Release notes** 작성
5. **Publish release** 클릭

→ CD 파이프라인이 자동으로 실행됩니다!

### 방법 2: GitHub CLI로 Release 생성

```bash
# GitHub CLI 설치 (없으면)
# https://cli.github.com/

# Release 생성
gh release create v1.0.0 \
  --title "v1.0.0 - Kubernetes 배포" \
  --notes "
  ## 변경사항
  - Kubernetes 기반 환경 분리
  - Training/Serving 독립 배포
  - MLflow 통합
  "
```

### 방법 3: Git 태그로 Release 생성

```bash
# 태그 생성
git tag -a v1.0.0 -m "Release v1.0.0"

# 태그 푸시
git push origin v1.0.0

# GitHub에서 Release로 변환
gh release create v1.0.0 --generate-notes
```

---

## 📊 배포 프로세스 상세

### Step 1: Docker 이미지 빌드

```yaml
# Training 이미지 (완전한 ML 환경)
docker build -f Dockerfile.training -t ops-demo:training-v1.0.0 .

# Serving 이미지 (경량화된 추론 전용)
docker build -f Dockerfile.serving -t ops-demo:serving-v1.0.0 .
```

**이미지 크기 비교:**
- Training: ~2.5GB (Jupyter, MLflow, 전체 라이브러리)
- Serving: ~1.2GB (FastAPI, 추론용 최소 라이브러리)

### Step 2: 서버로 전송

```bash
# 이미지를 tar.gz로 압축하여 전송
scp training-image.tar.gz user@server:/tmp/
scp serving-image.tar.gz user@server:/tmp/

# Kubernetes 매니페스트도 전송
scp -r k8s/ user@server:/tmp/
```

### Step 3: Kubernetes 배포

서버에서 자동으로 실행되는 단계:

```bash
# 1. 이미지를 k3s에 import
docker load < /tmp/training-image.tar.gz
sudo k3s ctr images import /tmp/training-image.tar.gz

docker load < /tmp/serving-image.tar.gz
sudo k3s ctr images import /tmp/serving-image.tar.gz

# 2. 네임스페이스 생성/확인
kubectl apply -f /tmp/k8s/01-namespaces.yaml

# 3. 스토리지 설정
sudo mkdir -p /data/mlops
kubectl apply -f /tmp/k8s/02-storage.yaml

# 4. MLflow 서버 배포
kubectl apply -f /tmp/k8s/03-mlflow.yaml

# 5. 서빙 API 무중단 배포 (롤링 업데이트)
kubectl apply -f /tmp/k8s/05-serving.yaml
kubectl rollout status deployment/iris-serving -n mlops-serving
```

### Step 4: 배포 검증

```bash
# Pod 상태 확인
kubectl get pods -n mlops-training
kubectl get pods -n mlops-serving

# 서비스 확인
kubectl get svc -n mlops-serving

# 로그 확인
kubectl logs -f deployment/iris-serving -n mlops-serving
```

---

## 🔍 배포 모니터링

### GitHub Actions에서 확인

1. GitHub 저장소 → **Actions** 탭
2. **CD Pipeline** 워크플로우 선택
3. 최근 실행 결과 확인

**배포 요약 예시:**

```
🎉 Kubernetes 배포 성공!

📦 배포 정보
- 버전: v1.0.0
- 서버: 123.456.789.0
- 커밋: abc1234

🐳 배포된 이미지
- ops-demo:training-v1.0.0 (훈련용)
- ops-demo:serving-v1.0.0 (서빙용)

🚀 배포된 리소스
- MLflow Server (mlops-training)
- Serving API x2 (mlops-serving)
```

### 서버에서 직접 확인

```bash
# SSH로 서버 접속
ssh user@your-server

# 전체 상태 확인
kubectl get all -A | grep mlops

# Training 환경
kubectl get pods,svc -n mlops-training

# Serving 환경
kubectl get pods,svc -n mlops-serving

# 실시간 로그
kubectl logs -f deployment/iris-serving -n mlops-serving
```

---

## 🔄 무중단 배포 (Zero Downtime)

CD 파이프라인은 **롤링 업데이트**를 사용하여 무중단 배포를 구현합니다:

```yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxUnavailable: 1  # 최대 1개 Pod만 중단
    maxSurge: 1        # 최대 1개 추가 Pod 생성
```

### 배포 프로세스

```
기존 상태: [Pod-1] [Pod-2]  ← 2개 실행 중

Step 1:   [Pod-1] [Pod-2] [Pod-3-new] ← 새 Pod 생성
          
Step 2:   [Pod-1] [Pod-3-new] ← Pod-2 종료
          
Step 3:   [Pod-1] [Pod-3-new] [Pod-4-new] ← 새 Pod 생성
          
Step 4:   [Pod-3-new] [Pod-4-new] ← Pod-1 종료

최종 상태: [Pod-3-new] [Pod-4-new]  ← 2개 새 버전 실행 중
```

**장점:**
- ✅ 서비스 중단 없음
- ✅ 문제 발생 시 자동 롤백
- ✅ 헬스체크로 안전성 보장

---

## 🔧 고급 설정

### 1. 배포 전략 커스터마이징

```yaml
# k8s/05-serving.yaml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxUnavailable: 0   # 무조건 가용성 유지
    maxSurge: 2         # 더 빠른 배포
```

### 2. 특정 버전으로 롤백

```bash
# 배포 히스토리 확인
kubectl rollout history deployment/iris-serving -n mlops-serving

# 이전 버전으로 롤백
kubectl rollout undo deployment/iris-serving -n mlops-serving

# 특정 리비전으로 롤백
kubectl rollout undo deployment/iris-serving \
  --to-revision=2 -n mlops-serving
```

### 3. 배포 일시 중지/재개

```bash
# 배포 일시 중지
kubectl rollout pause deployment/iris-serving -n mlops-serving

# 배포 재개
kubectl rollout resume deployment/iris-serving -n mlops-serving
```

---

## 🐛 문제 해결

### Q1: CD 파이프라인이 실패합니다

**확인 사항:**

1. **GitHub Secrets 설정 확인**
   ```bash
   # 서버에 SSH 접속이 되는지 확인
   ssh -i ~/.ssh/id_ed25519 user@your-server
   ```

2. **서버에 k3s가 설치되어 있는지 확인**
   ```bash
   ssh user@your-server "kubectl version"
   ```

3. **서버 디스크 공간 확인**
   ```bash
   ssh user@your-server "df -h"
   ```

### Q2: 이미지 Pull 실패 (ImagePullBackOff)

```bash
# 서버에서 이미지 확인
sudo k3s crictl images | grep ops-demo

# 없으면 수동으로 import
docker load < /path/to/image.tar.gz
sudo k3s ctr images import /path/to/image.tar.gz
```

### Q3: Pod가 Pending 상태로 남아있습니다

```bash
# 이벤트 확인
kubectl describe pod <pod-name> -n mlops-serving

# 일반적인 원인:
# - 리소스 부족: kubectl top nodes
# - PVC 바인딩 실패: kubectl get pvc -A
# - 노드 선택자 불일치: Pod spec 확인
```

### Q4: 무중단 배포가 작동하지 않습니다

**헬스체크 설정 확인:**

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 5
```

---

## 📈 배포 모범 사례

### 1. 시맨틱 버저닝 사용

```
v1.0.0  ← 메이저.마이너.패치
  │ │ │
  │ │ └─ 버그 수정 (호환성 유지)
  │ └─── 새 기능 추가 (호환성 유지)
  └───── 호환성 없는 변경
```

### 2. Release Notes 작성

```markdown
## v1.2.0 (2025-01-15)

### 새 기능
- Kubernetes 기반 환경 분리 (#123)
- MLflow 실험 추적 개선 (#124)

### 버그 수정
- API 응답 시간 개선 (#125)

### Breaking Changes
- 없음
```

### 3. 단계적 배포

```bash
# 1. 개발 환경에서 테스트
./k8s/deploy.sh

# 2. 스테이징 환경에 배포
gh release create v1.2.0-rc.1 --prerelease

# 3. 프로덕션 배포
gh release create v1.2.0
```

### 4. 모니터링 및 알림

```yaml
# 추가 가능한 단계
- name: Slack 알림
  if: always()
  uses: 8398a7/action-slack@v3
  with:
    status: ${{ job.status }}
    text: 'Kubernetes 배포 완료!'
```

---

## 🔗 관련 문서

- **[KUBERNETES.md](KUBERNETES.md)** - Kubernetes 환경 개요
- **[k8s/README.md](k8s/README.md)** - 상세 운영 가이드
- **[.github/workflows/cd.yml](.github/workflows/cd.yml)** - CD 파이프라인 코드

---

## 📊 배포 체크리스트

배포 전 확인사항:

- [ ] 로컬에서 테스트 완료
- [ ] CI 파이프라인 통과
- [ ] GitHub Secrets 설정 완료
- [ ] 서버에 k3s 설치 및 실행 중
- [ ] 서버 리소스 확인 (CPU, 메모리, 디스크)
- [ ] Release notes 작성 완료
- [ ] 버전 태그 규칙 준수

배포 후 확인사항:

- [ ] Pod 정상 실행 확인
- [ ] API 응답 테스트
- [ ] MLflow UI 접속 확인
- [ ] 로그 확인 (에러 없음)
- [ ] 리소스 사용량 모니터링

---

**Happy Deploying! 🚀**

