# 포트포워딩 없이 외부 접근 설정

Training Controller UI에 포트포워딩 없이 바로 접근하는 3가지 방법을 제공합니다.

## 🎯 방법 비교

| 방법 | 복잡도 | 접근 방법 | 추천 환경 |
|------|--------|----------|----------|
| **LoadBalancer** | ⭐ 쉬움 | `http://<EXTERNAL-IP>:8080` | k3s, 클라우드 |
| **NodePort** | ⭐⭐ 보통 | `http://<NODE-IP>:30080` | 모든 환경 |
| **Ingress** | ⭐⭐⭐ 복잡 | `http://training.mlops.local` | 프로덕션 |

---

## 방법 1: LoadBalancer (가장 간단! 추천)

### 특징
- ✅ **가장 간단한 설정**
- ✅ k3s가 자동으로 외부 IP 할당
- ✅ 클라우드 환경에서 완벽 지원
- ⚠️ 로컬 환경에서는 `localhost` 또는 `127.0.0.1`

### 적용 방법

```bash
# 기본 매니페스트를 이미 LoadBalancer로 변경했습니다
kubectl apply -f k8s/06-training-controller.yaml

# 외부 IP 확인
kubectl get svc training-controller-service -n mlops-training
```

**출력 예시:**
```
NAME                           TYPE           EXTERNAL-IP   PORT(S)
training-controller-service    LoadBalancer   192.168.1.100 8080:31234/TCP
```

### 접속

```bash
# 1. EXTERNAL-IP 확인
EXTERNAL_IP=$(kubectl get svc training-controller-service -n mlops-training \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

echo "Training Controller UI: http://${EXTERNAL_IP}:8080"

# 2. 브라우저에서 접속
# http://192.168.1.100:8080  (예시)
```

### 로컬 환경 (k3s)

```bash
# k3s는 localhost로 접근 가능
http://localhost:8080

# 또는
http://127.0.0.1:8080
```

---

## 방법 2: NodePort (모든 환경 호환)

### 특징
- ✅ **모든 Kubernetes 환경 지원**
- ✅ 노드 IP로 직접 접근
- ✅ 고정 포트 지정 가능 (30000-32767)
- ⚠️ 방화벽 설정 필요할 수 있음

### 적용 방법

```bash
# NodePort 버전 적용
kubectl apply -f k8s/06-training-controller-nodeport.yaml

# 서비스 확인
kubectl get svc training-controller-service -n mlops-training
```

**출력 예시:**
```
NAME                           TYPE       PORT(S)
training-controller-service    NodePort   8080:30080/TCP
```

### 접속

```bash
# 1. 노드 IP 확인
NODE_IP=$(kubectl get nodes -o jsonpath='{.items[0].status.addresses[?(@.type=="InternalIP")].address}')

echo "Training Controller UI: http://${NODE_IP}:30080"

# 2. 브라우저에서 접속
# http://192.168.1.50:30080  (예시)
```

### 로컬 환경

```bash
# localhost로 접근 가능
http://localhost:30080
```

### 포트 변경 (선택사항)

```yaml
# k8s/06-training-controller-nodeport.yaml
ports:
- port: 8080
  targetPort: 8080
  nodePort: 30080  # 원하는 포트로 변경 (30000-32767)
```

---

## 방법 3: Ingress (프로덕션 추천)

### 특징
- ✅ **도메인으로 접근** (예: training.mlops.local)
- ✅ **SSL/TLS 지원** (HTTPS)
- ✅ **인증/권한 제어** 가능
- ✅ **여러 서비스를 하나의 IP로** 통합
- ⚠️ Ingress Controller 필요 (k3s는 Traefik 내장)

### 사전 준비

k3s는 Traefik Ingress Controller가 기본 내장되어 있어 별도 설치 불필요!

**다른 환경의 경우:**
```bash
# NGINX Ingress Controller 설치 (필요 시)
kubectl apply -f https://raw.githubusercontent.com/kubernetes/ingress-nginx/main/deploy/static/provider/cloud/deploy.yaml
```

### 적용 방법

```bash
# Ingress 버전 적용
kubectl apply -f k8s/06-training-controller-ingress.yaml

# Ingress 확인
kubectl get ingress training-controller-ingress -n mlops-training
```

**출력 예시:**
```
NAME                          HOSTS                  ADDRESS         PORTS
training-controller-ingress   training.mlops.local   192.168.1.100   80
```

### 로컬 DNS 설정

#### Option 1: /etc/hosts 수정

```bash
# 1. Ingress IP 확인
INGRESS_IP=$(kubectl get ingress training-controller-ingress -n mlops-training \
  -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# 2. /etc/hosts에 추가 (Linux/Mac)
sudo sh -c "echo '${INGRESS_IP} training.mlops.local' >> /etc/hosts"

# Windows (관리자 권한 PowerShell)
# Add-Content -Path C:\Windows\System32\drivers\etc\hosts -Value "${INGRESS_IP} training.mlops.local"
```

#### Option 2: curl로 테스트

```bash
# HOST 헤더 지정하여 접근
curl -H "Host: training.mlops.local" http://<INGRESS-IP>
```

### 접속

```bash
# 브라우저에서 접속
http://training.mlops.local
```

### SSL/TLS 설정 (HTTPS)

```yaml
# k8s/06-training-controller-ingress.yaml에 추가
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - training.mlops.local
    secretName: training-tls
  rules:
  - host: training.mlops.local
    # ... (기존 설정)
```

### 인증 추가 (Basic Auth)

```bash
# 1. 인증 정보 생성
htpasswd -c auth admin
# 비밀번호 입력

# 2. Secret 생성
kubectl create secret generic basic-auth \
  --from-file=auth \
  -n mlops-training

# 3. Ingress에 annotation 추가
# traefik.ingress.kubernetes.io/auth-type: basic
# traefik.ingress.kubernetes.io/auth-secret: basic-auth
```

---

## 🔄 방법 전환하기

### LoadBalancer → NodePort

```bash
kubectl delete -f k8s/06-training-controller.yaml
kubectl apply -f k8s/06-training-controller-nodeport.yaml
```

### NodePort → Ingress

```bash
kubectl delete -f k8s/06-training-controller-nodeport.yaml
kubectl apply -f k8s/06-training-controller-ingress.yaml
```

### Ingress → LoadBalancer

```bash
kubectl delete -f k8s/06-training-controller-ingress.yaml
kubectl apply -f k8s/06-training-controller.yaml
```

---

## 📊 전체 MLOps 서비스 외부 접근 설정

### 모두 외부 접근 가능하게 설정

```bash
# Training Controller (이미 LoadBalancer)
kubectl get svc training-controller-service -n mlops-training

# MLflow (LoadBalancer로 변경)
kubectl patch svc mlflow-service -n mlops-training \
  -p '{"spec": {"type": "LoadBalancer"}}'

# Serving API (이미 LoadBalancer)
kubectl get svc iris-serving-service -n mlops-serving
```

### 접속 정보 한 번에 확인

```bash
echo "=== MLOps Services ==="
echo ""
echo "Training Controller:"
kubectl get svc training-controller-service -n mlops-training \
  -o jsonpath='http://{.status.loadBalancer.ingress[0].ip}:8080'
echo ""
echo ""
echo "MLflow UI:"
kubectl get svc mlflow-service -n mlops-training \
  -o jsonpath='http://{.status.loadBalancer.ingress[0].ip}:5000'
echo ""
echo ""
echo "Serving API:"
kubectl get svc iris-serving-service -n mlops-serving \
  -o jsonpath='http://{.status.loadBalancer.ingress[0].ip}'
echo ""
```

---

## 🔒 보안 고려사항

### 1. 프로덕션 환경

- ✅ Ingress + SSL/TLS 사용
- ✅ 인증/권한 제어 설정
- ✅ 네트워크 정책 적용
- ✅ 방화벽 규칙 설정

### 2. 개발/테스트 환경

- ✅ LoadBalancer 또는 NodePort 사용
- ⚠️ 내부 네트워크만 접근 가능하도록 제한

### 네트워크 정책 예시

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: training-controller-policy
  namespace: mlops-training
spec:
  podSelector:
    matchLabels:
      app: training-controller
  policyTypes:
  - Ingress
  ingress:
  - from:
    - ipBlock:
        cidr: 192.168.0.0/16  # 내부 네트워크만 허용
    ports:
    - protocol: TCP
      port: 8080
```

---

## 🐛 문제 해결

### Q: EXTERNAL-IP가 `<pending>` 상태입니다

**원인:** LoadBalancer를 지원하지 않는 환경

**해결책:**

1. NodePort 사용
```bash
kubectl apply -f k8s/06-training-controller-nodeport.yaml
```

2. 또는 MetalLB 설치 (Bare Metal 환경)
```bash
kubectl apply -f https://raw.githubusercontent.com/metallb/metallb/v0.13.12/config/manifests/metallb-native.yaml
```

### Q: NodePort로 접근이 안 됩니다

**확인사항:**

1. 방화벽 설정
```bash
# Linux (ufw)
sudo ufw allow 30080/tcp

# Linux (firewalld)
sudo firewall-cmd --add-port=30080/tcp --permanent
sudo firewall-cmd --reload
```

2. 서비스 상태 확인
```bash
kubectl describe svc training-controller-service -n mlops-training
```

### Q: Ingress가 작동하지 않습니다

**확인사항:**

1. Ingress Controller 설치 확인
```bash
kubectl get pods -n kube-system | grep traefik
```

2. Ingress 상태 확인
```bash
kubectl describe ingress training-controller-ingress -n mlops-training
```

3. DNS 설정 확인
```bash
# /etc/hosts 확인
cat /etc/hosts | grep training.mlops.local
```

---

## 💡 권장 설정

### 환경별 권장사항

| 환경 | 권장 방법 | 이유 |
|------|----------|------|
| **로컬 개발 (k3s)** | LoadBalancer | 가장 간단, localhost 접근 |
| **회사 내부망** | NodePort | 방화벽 제어 용이 |
| **클라우드 (EKS/GKE/AKS)** | LoadBalancer | 자동 IP 할당 |
| **프로덕션** | Ingress + SSL | 도메인, 인증, 암호화 |

---

## 📚 추가 자료

- [Kubernetes Services](https://kubernetes.io/docs/concepts/services-networking/service/)
- [Kubernetes Ingress](https://kubernetes.io/docs/concepts/services-networking/ingress/)
- [k3s Networking](https://docs.k3s.io/networking)

---

**이제 포트포워딩 없이 어디서나 Training Controller UI에 접근할 수 있습니다! 🚀**

