# 서버 초기 설정 가이드

GitHub Actions를 통한 자동 배포를 위한 서버 설정 방법

---

## 🎯 목표

사용자 홈 디렉토리에서 모든 작업 수행 (sudo 최소화)

```
$HOME/ops-demo/  ← 모든 작업은 여기서!
```

---

## 📋 사전 요구사항

- Ubuntu/Debian 서버
- SSH 접속 가능
- sudo 권한

---

## 🚀 자동 설정 (추천)

### 1. 서버에 SSH 접속

```bash
ssh user@your-server
```

### 2. 초기 설정 스크립트 실행

```bash
# 스크립트 다운로드
curl -O https://raw.githubusercontent.com/your-username/ops-demo/main/k8s/setup-project.sh
chmod +x setup-project.sh

# 실행 (GitHub 저장소 주소 입력)
./setup-project.sh your-username/ops-demo
```

이 스크립트가 자동으로:
1. ✅ 홈 디렉토리에 프로젝트 clone
2. ✅ Docker 권한 확인
3. ✅ k3s 권한 확인
4. ✅ 스토리지 디렉토리 생성

---

## 🔧 수동 설정

### 1. k3s 설치

```bash
# k3s 설치
curl -sfL https://get.k3s.io | sh -

# kubectl 설정
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $USER ~/.kube/config
export KUBECONFIG=~/.kube/config

# 확인
kubectl get nodes
```

### 2. Docker 권한 설정

```bash
# docker 그룹에 사용자 추가
sudo usermod -aG docker $USER

# 로그아웃 후 다시 로그인
exit
ssh user@your-server

# 확인
docker ps
```

### 3. k3s 권한 설정

```bash
# k3s.yaml 권한 설정
sudo chmod 644 /etc/rancher/k3s/k3s.yaml

# 또는 사용자별 설정
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $USER ~/.kube/config
export KUBECONFIG=~/.kube/config

# ~/.bashrc에 추가
echo 'export KUBECONFIG=~/.kube/config' >> ~/.bashrc
source ~/.bashrc

# 확인
kubectl get pods -A
k3s ctr images ls  # sudo 없이 실행 가능해야 함
```

### 4. 프로젝트 Clone

```bash
# 홈 디렉토리에 clone
cd ~
git clone https://github.com/your-username/ops-demo.git

# 확인
cd ~/ops-demo
ls -la
```

### 5. 스토리지 디렉토리 생성

```bash
# 한 번만 실행 (사용자 홈 디렉토리)
mkdir -p $HOME/ops-demo-data/mlops
```

---

## 🔑 GitHub Actions 설정

### 1. SSH 키 생성 (로컬)

```bash
# ED25519 키 생성
ssh-keygen -t ed25519 -C "github-actions@deploy" -f ~/.ssh/github_deploy

# Private Key 확인 (GitHub Secret에 등록)
cat ~/.ssh/github_deploy

# Public Key를 서버에 추가
cat ~/.ssh/github_deploy.pub
```

### 2. 서버에 Public Key 추가

```bash
# 서버에서 실행
echo "your-public-key-here" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

### 3. GitHub Secrets 설정

Repository → Settings → Secrets → Actions

| Secret 이름 | 값 | 설명 |
|-------------|-----|------|
| `SSH_PRIVATE_KEY` | `~/.ssh/github_deploy` 내용 | Private Key 전체 |
| `DEPLOY_USER` | `ubuntu` (또는 사용자명) | SSH 사용자명 |
| `DEPLOY_HOST` | `123.456.789.0` | 서버 IP |
| `DEPLOY_PORT` | `22` | SSH 포트 (선택) |

---

## 📂 디렉토리 구조

```
$HOME/
├── ops-demo/                    ← 프로젝트 디렉토리
│   ├── .git/
│   ├── app/
│   ├── scripts/
│   ├── k8s/
│   │   ├── 01-namespaces.yaml
│   │   ├── 02-storage.yaml
│   │   ├── 03-mlflow.yaml
│   │   ├── 05-serving.yaml
│   │   ├── 06-training-controller.yaml
│   │   ├── auto-deploy.sh
│   │   └── ...
│   ├── Dockerfile.training
│   ├── Dockerfile.serving
│   └── ...
└── .kube/
    └── config                   ← kubectl 설정

/data/
└── mlops/                       ← 공유 스토리지
    ├── models/
    └── mlruns/
```

---

## ✅ 설정 확인

### 모든 권한 테스트

```bash
# Docker 권한
docker ps

# k3s 권한 (sudo 없이)
kubectl get nodes
k3s ctr images ls

# 프로젝트 디렉토리
cd ~/ops-demo
git pull

# 스토리지 접근
ls -la $HOME/ops-demo-data/mlops
```

**모두 정상 작동하면 준비 완료!** ✅

---

## 🎯 첫 배포 테스트

### 수동 배포 (테스트)

```bash
cd ~/ops-demo/k8s
./auto-deploy.sh latest
```

### GitHub Actions 배포

```bash
# 로컬에서
git add .
git commit -m "feat: cd-webhook 설정 완료"
git push

# Release 생성
gh release create v1.0.0 --generate-notes
```

GitHub Actions 탭에서 배포 진행 상황 확인!

---

## 🐛 문제 해결

### Q: docker: permission denied

**해결:**
```bash
sudo usermod -aG docker $USER
# 로그아웃 후 다시 로그인
```

### Q: k3s ctr: permission denied

**해결:**
```bash
# 방법 1: k3s.yaml 권한
sudo chmod 644 /etc/rancher/k3s/k3s.yaml

# 방법 2: 사용자별 설정
mkdir -p ~/.kube
sudo cp /etc/rancher/k3s/k3s.yaml ~/.kube/config
sudo chown $USER ~/.kube/config
```

### Q: Git: Permission denied (publickey)

**해결:**
```bash
# HTTPS 사용 (Private repo는 Personal Access Token 필요)
git clone https://github.com/username/ops-demo.git

# 또는 SSH 키 설정
ssh-keygen -t ed25519 -C "your_email@example.com"
cat ~/.ssh/id_ed25519.pub
# → GitHub Settings → SSH keys에 추가
```

### Q: $HOME/ops-demo-data/mlops: Permission denied

**해결:**
```bash
chmod 777 $HOME/ops-demo-data/mlops
# 또는
chown $USER:$USER $HOME/ops-demo-data/mlops
```

---

## 📊 환경 변수 설정 (선택)

```bash
# ~/.bashrc에 추가
echo 'export PROJECT_DIR="$HOME/ops-demo"' >> ~/.bashrc
echo 'export KUBECONFIG="$HOME/.kube/config"' >> ~/.bashrc
source ~/.bashrc

# 사용
cd $PROJECT_DIR
```

---

## 🎉 완료!

이제 다음이 가능합니다:

1. ✅ GitHub Release → 자동 배포
2. ✅ sudo 없이 Docker 사용
3. ✅ sudo 없이 kubectl 사용
4. ✅ 사용자 홈에서 모든 작업

**접속 확인:**
- 🎯 http://localhost:30081 - Training Controller
- 📊 http://localhost:30501 - MLflow UI
- 🚀 http://localhost:30801 - Serving API

