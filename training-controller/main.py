"""
Training Controller API
MLflow UI에서 훈련 Job을 트리거할 수 있는 웹 인터페이스
"""

from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from kubernetes import client, config
from pydantic import BaseModel, Field

app = FastAPI(
    title="Training Controller",
    description="Kubernetes에서 ML 훈련 Job을 관리하는 API",
    version="1.0.0",
)

# Kubernetes 설정
try:
    config.load_incluster_config()  # Pod 내부에서 실행
except:
    config.load_kube_config()  # 로컬 개발용


class TrainingRequest(BaseModel):
    """훈련 요청 모델"""

    n_estimators: int = Field(default=100, ge=10, le=1000, description="트리 개수")
    max_depth: int = Field(default=5, ge=1, le=50, description="트리 최대 깊이")
    run_name: Optional[str] = Field(
        default=None, description="MLflow run 이름 (자동 생성 가능)"
    )


class JobStatus(BaseModel):
    """Job 상태 모델"""

    job_name: str
    status: str
    created_at: str
    pods: list


@app.get("/", response_class=HTMLResponse)
async def root():
    """웹 UI 제공"""
    return """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ML Training Controller</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
        }
        .header {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            margin-bottom: 30px;
            text-align: center;
        }
        .header h1 {
            color: #667eea;
            font-size: 2.5em;
            margin-bottom: 10px;
        }
        .header p {
            color: #666;
            font-size: 1.1em;
        }
        .grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 20px;
            margin-bottom: 20px;
        }
        .card {
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
        }
        .card h2 {
            color: #333;
            margin-bottom: 20px;
            font-size: 1.5em;
            border-bottom: 3px solid #667eea;
            padding-bottom: 10px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        .form-group label {
            display: block;
            color: #555;
            font-weight: 600;
            margin-bottom: 8px;
            font-size: 0.95em;
        }
        .form-group input {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 1em;
            transition: all 0.3s;
        }
        .form-group input:focus {
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }
        .form-group small {
            display: block;
            color: #888;
            margin-top: 5px;
            font-size: 0.85em;
        }
        button {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 1.1em;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s, box-shadow 0.2s;
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }
        button:active {
            transform: translateY(0);
        }
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
            transform: none;
        }
        .jobs-list {
            margin-top: 20px;
        }
        .job-item {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            border-left: 4px solid #667eea;
        }
        .job-item.running {
            border-left-color: #ffc107;
            animation: pulse 2s infinite;
        }
        .job-item.succeeded {
            border-left-color: #28a745;
        }
        .job-item.failed {
            border-left-color: #dc3545;
        }
        .job-name {
            font-weight: 600;
            color: #333;
            margin-bottom: 5px;
        }
        .job-status {
            display: inline-block;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
        }
        .job-status.running { background: #fff3cd; color: #856404; }
        .job-status.succeeded { background: #d4edda; color: #155724; }
        .job-status.failed { background: #f8d7da; color: #721c24; }
        .job-status.pending { background: #e7f3ff; color: #004085; }
        .message {
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            font-weight: 500;
        }
        .message.success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .message.error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        .refresh-btn {
            background: #6c757d;
            margin-bottom: 15px;
        }
        .links {
            display: flex;
            gap: 15px;
            justify-content: center;
            flex-wrap: wrap;
        }
        .link-btn {
            padding: 10px 20px;
            background: white;
            color: #667eea;
            text-decoration: none;
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.3s;
            border: 2px solid #667eea;
        }
        .link-btn:hover {
            background: #667eea;
            color: white;
            transform: translateY(-2px);
        }
        @media (max-width: 768px) {
            .grid {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 ML Training Controller</h1>
            <p>Kubernetes에서 모델 훈련을 쉽게 시작하고 관리하세요</p>
            <br>
            <div class="links">
                <a href="http://localhost:5000" class="link-btn" target="_blank">📊 MLflow UI</a>
                <a href="http://localhost:8000/docs" class="link-btn" target="_blank">🔥 Serving API</a>
                <a href="/docs" class="link-btn">📖 API Docs</a>
            </div>
        </div>

        <div class="grid">
            <div class="card">
                <h2>🎯 새로운 훈련 시작</h2>
                <div id="message"></div>
                <form id="trainingForm">
                    <div class="form-group">
                        <label for="n_estimators">🌳 트리 개수 (n_estimators)</label>
                        <input type="number" id="n_estimators" value="100" min="10" max="1000" required>
                        <small>RandomForest의 결정 트리 개수 (권장: 100-300)</small>
                    </div>
                    <div class="form-group">
                        <label for="max_depth">📏 최대 깊이 (max_depth)</label>
                        <input type="number" id="max_depth" value="5" min="1" max="50" required>
                        <small>트리의 최대 깊이 (권장: 5-20)</small>
                    </div>
                    <div class="form-group">
                        <label for="run_name">🏷️ 실험 이름 (선택)</label>
                        <input type="text" id="run_name" placeholder="예: experiment-001">
                        <small>비워두면 자동으로 생성됩니다</small>
                    </div>
                    <button type="submit" id="submitBtn">
                        🚀 훈련 시작
                    </button>
                </form>
            </div>

            <div class="card">
                <h2>📋 실행 중인 Job</h2>
                <button onclick="loadJobs()" class="refresh-btn" style="width: auto;">
                    🔄 새로고침
                </button>
                <div id="jobsList" class="jobs-list">
                    <p style="color: #888; text-align: center;">로딩 중...</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        // 훈련 시작
        document.getElementById('trainingForm').addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const submitBtn = document.getElementById('submitBtn');
            const messageDiv = document.getElementById('message');
            
            submitBtn.disabled = true;
            submitBtn.textContent = '⏳ 시작 중...';
            
            const data = {
                n_estimators: parseInt(document.getElementById('n_estimators').value),
                max_depth: parseInt(document.getElementById('max_depth').value),
                run_name: document.getElementById('run_name').value || null
            };
            
            try {
                const response = await fetch('/jobs/train', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    messageDiv.innerHTML = `
                        <div class="message success">
                            ✅ 훈련 Job이 시작되었습니다!<br>
                            <strong>Job 이름:</strong> ${result.job_name}<br>
                            <strong>상태:</strong> ${result.status}
                        </div>
                    `;
                    // 폼 초기화
                    document.getElementById('run_name').value = '';
                    // Job 목록 새로고침
                    loadJobs();
                } else {
                    messageDiv.innerHTML = `
                        <div class="message error">
                            ❌ 오류: ${result.detail}
                        </div>
                    `;
                }
            } catch (error) {
                messageDiv.innerHTML = `
                    <div class="message error">
                        ❌ 네트워크 오류: ${error.message}
                    </div>
                `;
            } finally {
                submitBtn.disabled = false;
                submitBtn.textContent = '🚀 훈련 시작';
            }
        });

        // Job 목록 로드
        async function loadJobs() {
            const jobsList = document.getElementById('jobsList');
            jobsList.innerHTML = '<p style="color: #888; text-align: center;">로딩 중...</p>';
            
            try {
                const response = await fetch('/jobs');
                const jobs = await response.json();
                
                if (jobs.length === 0) {
                    jobsList.innerHTML = '<p style="color: #888; text-align: center;">실행 중인 Job이 없습니다</p>';
                    return;
                }
                
                jobsList.innerHTML = jobs.map(job => {
                    let statusClass = 'pending';
                    if (job.status.includes('Running')) statusClass = 'running';
                    else if (job.status.includes('Succeeded')) statusClass = 'succeeded';
                    else if (job.status.includes('Failed')) statusClass = 'failed';
                    
                    return `
                        <div class="job-item ${statusClass}">
                            <div class="job-name">📦 ${job.job_name}</div>
                            <span class="job-status ${statusClass}">${job.status}</span>
                            <div style="color: #666; font-size: 0.9em; margin-top: 5px;">
                                생성: ${job.created_at}
                            </div>
                        </div>
                    `;
                }).join('');
            } catch (error) {
                jobsList.innerHTML = `<p style="color: #dc3545;">오류: ${error.message}</p>`;
            }
        }

        // 초기 로드 및 자동 새로고침
        loadJobs();
        setInterval(loadJobs, 5000); // 5초마다 자동 새로고침
    </script>
</body>
</html>
"""


@app.get("/health")
async def health():
    """헬스체크"""
    return {"status": "healthy"}


@app.get("/jobs", response_model=list[JobStatus])
async def list_jobs():
    """실행 중인 훈련 Job 목록 조회"""
    try:
        batch_v1 = client.BatchV1Api()
        jobs = batch_v1.list_namespaced_job(
            namespace="mlops-training", label_selector="app=iris-training"
        )

        result = []
        for job in jobs.items:
            status = "Pending"
            if job.status.active:
                status = "Running"
            elif job.status.succeeded:
                status = "Succeeded"
            elif job.status.failed:
                status = "Failed"

            result.append(
                {
                    "job_name": job.metadata.name,
                    "status": status,
                    "created_at": job.metadata.creation_timestamp.strftime(
                        "%Y-%m-%d %H:%M:%S"
                    ),
                    "pods": [],
                }
            )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Job 목록 조회 실패: {str(e)}")


@app.post("/jobs/train")
async def create_training_job(request: TrainingRequest):
    """새로운 훈련 Job 생성"""

    # Run name 생성 (없으면 자동)
    run_name = request.run_name or f"training-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    # Job 이름 생성 (Kubernetes 규칙 준수)
    job_name = f"iris-training-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

    try:
        # Job 매니페스트 생성
        job = client.V1Job(
            api_version="batch/v1",
            kind="Job",
            metadata=client.V1ObjectMeta(
                name=job_name,
                namespace="mlops-training",
                labels={"app": "iris-training", "component": "training"},
            ),
            spec=client.V1JobSpec(
                backoff_limit=3,
                ttl_seconds_after_finished=3600,
                template=client.V1PodTemplateSpec(
                    metadata=client.V1ObjectMeta(
                        labels={"app": "iris-training", "component": "training"}
                    ),
                    spec=client.V1PodSpec(
                        restart_policy="Never",
                        containers=[
                            client.V1Container(
                                name="training",
                                image="ops-demo:training",
                                command=["python", "scripts/train_pipeline_mlflow.py"],
                                args=[
                                    "--n-estimators",
                                    str(request.n_estimators),
                                    "--max-depth",
                                    str(request.max_depth),
                                    "--run-name",
                                    run_name,
                                ],
                                env=[
                                    client.V1EnvVar(
                                        name="MLFLOW_TRACKING_URI",
                                        value="http://mlflow-service:5000",
                                    ),
                                    client.V1EnvVar(
                                        name="PYTHONUNBUFFERED", value="1"
                                    ),
                                ],
                                volume_mounts=[
                                    client.V1VolumeMount(
                                        name="mlops-storage", mount_path="/data"
                                    )
                                ],
                                resources=client.V1ResourceRequirements(
                                    requests={"cpu": "1000m", "memory": "2Gi"},
                                    limits={"cpu": "2000m", "memory": "4Gi"},
                                ),
                            )
                        ],
                        volumes=[
                            client.V1Volume(
                                name="mlops-storage",
                                persistent_volume_claim=client.V1PersistentVolumeClaimVolumeSource(
                                    claim_name="mlops-pvc"
                                ),
                            )
                        ],
                    ),
                ),
            ),
        )

        # Job 생성
        batch_v1 = client.BatchV1Api()
        batch_v1.create_namespaced_job(namespace="mlops-training", body=job)

        return {
            "job_name": job_name,
            "run_name": run_name,
            "status": "Created",
            "parameters": {
                "n_estimators": request.n_estimators,
                "max_depth": request.max_depth,
            },
            "message": "훈련 Job이 성공적으로 생성되었습니다",
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Job 생성 실패: {str(e)}")


@app.delete("/jobs/{job_name}")
async def delete_job(job_name: str):
    """훈련 Job 삭제"""
    try:
        batch_v1 = client.BatchV1Api()
        batch_v1.delete_namespaced_job(
            name=job_name,
            namespace="mlops-training",
            propagation_policy="Background",
        )
        return {"message": f"Job '{job_name}'이(가) 삭제되었습니다"}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Job 삭제 실패: {str(e)}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)

