# AI Governance Server — VM Deployment Guide

## Prerequisites

| Requirement | Minimum | Recommended |
|-------------|---------|-------------|
| **OS** | Ubuntu 20.04+ / RHEL 8+ / any Linux with Docker | Ubuntu 22.04 LTS |
| **CPU** | 4 cores | 8+ cores (more cores = faster LLM) |
| **RAM** | 8 GB | 16 GB+ (LLM uses ~4 GB) |
| **Disk** | 20 GB | 40 GB+ (LLM model ~2 GB, Docker images ~5 GB) |
| **GPU** | Not required | NVIDIA GPU with CUDA (10x faster LLM) |
| **Docker** | Docker 24+ with Compose v2 | Latest stable |
| **Network** | Outbound HTTPS for first-time model pull | Same |

---

## Step 1: Install Docker

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo systemctl enable docker --now
sudo usermod -aG docker $USER
# Log out and back in for group change to take effect
```

```bash
# RHEL/CentOS
sudo dnf install -y docker docker-compose-plugin
sudo systemctl enable docker --now
sudo usermod -aG docker $USER
```

Verify:
```bash
docker --version        # Should be 24+
docker compose version  # Should be v2+
```

---

## Step 2: Copy Project to VM

### Option A: Git clone
```bash
git clone <your-repo-url>
cd Hackathon-master/governance-server
```

### Option B: SCP/SFTP from dev machine
```bash
# From your dev machine:
scp -r governance-server/ user@<VM_IP>:~/governance-server/

# On the VM:
cd ~/governance-server
```

### Option C: Copy tarball
```bash
# On dev machine:
tar czf governance-server.tar.gz governance-server/
scp governance-server.tar.gz user@<VM_IP>:~/

# On VM:
tar xzf governance-server.tar.gz
cd governance-server
```

---

## Step 3: Corporate TLS Certificate (if behind corporate proxy)

If your VM is behind a corporate proxy/firewall with TLS inspection, you need to install the corporate CA certificate so Docker containers can make HTTPS requests (e.g., pull Ollama models).

```bash
# Copy your corporate CA cert to the standard location
sudo cp your-corporate-ca.crt /usr/local/share/ca-certificates/
sudo update-ca-certificates
```

The `docker-compose.yml` is already configured to mount this cert into the Ollama container. If your cert path differs from `/usr/local/share/ca-certificates/Corp_CA_bundle.crt`, update the volume mount in `docker-compose.yml`:

```yaml
# In docker-compose.yml, under ollama -> volumes:
- /path/to/your/ca-cert.crt:/usr/local/share/ca-certificates/Corp_CA_bundle.crt:ro
```

**If NOT behind a corporate proxy**, you can remove the CA cert volume mounts from the `ollama` and `mitm-proxy` services.

---

## Step 4: Configure Environment (Optional)

Default settings work out of the box. To customize, edit `docker-compose.yml`:

```yaml
# Key environment variables (in the 'api' service):
- OLLAMA_MODEL=llama3.2:3b        # LLM model (see Performance section)
- LLM_TEMPERATURE=0.1             # Lower = more deterministic
- LLM_MAX_TOKENS=1500             # Max output tokens per LLM call
- LLM_REQUEST_TIMEOUT_SECONDS=120 # Timeout for LLM calls
- CORS_ORIGINS=http://localhost:4200  # Add your frontend URL if different
```

---

## Step 5: Launch

```bash
cd governance-server
docker compose up -d
```

**First-time startup** will:
1. Build the backend and frontend Docker images (~3-5 min)
2. Pull Ollama LLM model `llama3.2:3b` (~2 GB download, 2-5 min)
3. Initialize PostgreSQL, Redis, ChromaDB
4. Seed default policies, classification rules, and RAG documents
5. Start all 7 services

Monitor startup:
```bash
# Watch all logs
docker compose logs -f

# Check Ollama model pull progress
docker logs governance-server-ollama-1 -f

# Check API readiness
docker compose logs api -f
```

---

## Step 6: Verify

```bash
# 1. Check all containers are running
docker compose ps

# Expected: all services "Up" or "Up (healthy)"
# governance-server-api-1         Up
# governance-server-frontend-1    Up
# governance-server-ollama-1      Up (healthy)
# governance-server-postgres-1    Up
# governance-server-redis-1       Up
# governance-server-chromadb-1    Up
# governance-server-mitm-proxy-1  Up

# 2. Health check
curl http://localhost:8000/health
# Should return: {"status": "healthy", "llm_healthy": true, ...}

# 3. Frontend
curl -o /dev/null -w "%{http_code}" http://localhost:4200/
# Should return: 200

# 4. API docs
# Open in browser: http://<VM_IP>:8000/docs
```

---

## Step 7: Apply Database Schema (First Time Only)

If this is a fresh deployment, apply the database schema for agent blocking:

```bash
docker exec governance-server-postgres-1 psql -U aigp -d aigp_db -c "
  ALTER TABLE agent_requests ADD COLUMN IF NOT EXISTS user_name VARCHAR(200) DEFAULT '';
  ALTER TABLE agent_requests ADD COLUMN IF NOT EXISTS industry VARCHAR(100) DEFAULT '';
  CREATE TABLE IF NOT EXISTS blocked_agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_app VARCHAR(100) NOT NULL UNIQUE,
    reason TEXT DEFAULT '',
    blocked_request_id VARCHAR(100) DEFAULT '',
    blocked_at TIMESTAMPTZ DEFAULT NOW()
  );
  CREATE INDEX IF NOT EXISTS idx_blocked_agents_source ON blocked_agents(source_app);
"
```

---

## Step 8: Test End-to-End

```bash
# Submit a test request
curl -s -X POST http://localhost:8000/api/v1/agent-requests \
  -H 'Content-Type: application/json' \
  -d '{
    "request_id": "DEPLOY-TEST-001",
    "title": "Deployment Verification Test",
    "source_app": "deploy-test",
    "user_name": "Admin",
    "user_input": "Patient SSN 123-45-6789 needs medication review",
    "tool_chain": [{
      "tool_name": "test_tool",
      "description": "Test tool",
      "sequence": 1,
      "input": {"test": true},
      "output": {"summary": "Patient record with SSN 123-45-6789 retrieved"},
      "reasoning": "Testing",
      "duration_ms": 100,
      "status": "SUCCESS"
    }],
    "final_output": {"summary": "Test complete"},
    "metadata": {}
  }' | python3 -m json.tool

# Expected: compliance_status = "VIOLATION", industry = "Healthcare"
# remediation should be LLM-generated (not hardcoded)

# Clean up test block
curl -s -X DELETE http://localhost:8000/api/v1/agent-requests/blocked/deploy-test
```

---

## Access URLs

| Service | URL | Purpose |
|---------|-----|---------|
| **Frontend UI** | `http://<VM_IP>:4200` | Admin dashboard |
| **API Docs** | `http://<VM_IP>:8000/docs` | Swagger API documentation |
| **MCP Server** | `http://<VM_IP>:8000/mcp` | MCP endpoint for AI agents |
| **Health Check** | `http://<VM_IP>:8000/health` | API health status |
| **MITM Proxy** | `<VM_IP>:8080` | Proxy for intercepting AI traffic |

---

## Management Commands

```bash
# Stop all services
docker compose down

# Restart a single service
docker compose restart api

# Rebuild after code changes
docker compose build api frontend
docker compose up -d api frontend

# View logs
docker compose logs -f api          # Backend logs
docker compose logs -f ollama       # LLM logs
docker compose logs -f frontend     # Frontend logs

# Reset database (WARNING: deletes all data)
docker compose down -v
docker compose up -d
```

---

## LLM Performance Tuning

The LLM (Ollama) runs on CPU by default. Response times vary by hardware:

| Hardware | Model | Expected Response Time |
|----------|-------|----------------------|
| 4-core CPU, 8 GB RAM | llama3.2:3b | 60-120s |
| 8-core CPU, 16 GB RAM | llama3.2:3b | 30-60s |
| 16-core CPU, 32 GB RAM | llama3.2:3b | 15-30s |
| NVIDIA GPU (any CUDA) | llama3.2:3b | **3-8s** |

### Option 1: Use GPU (Recommended — 10x faster)

If the VM has an NVIDIA GPU:

```bash
# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release; echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt update && sudo apt install -y nvidia-container-toolkit
sudo systemctl restart docker
```

Then update `docker-compose.yml` for the ollama service:

```yaml
ollama:
  image: ollama/ollama:latest
  deploy:
    resources:
      reservations:
        devices:
          - driver: nvidia
            count: 1
            capabilities: [gpu]
  # ... rest of config
```

### Option 2: Use a Smaller/Faster Model

```yaml
# In docker-compose.yml, change both:
# Under 'api' environment:
- OLLAMA_MODEL=llama3.2:1b    # 1B params — 2-3x faster, slightly less accurate

# Under 'ollama' environment:
- OLLAMA_MODEL=llama3.2:1b
```

### Option 3: Increase CPU Threads for Ollama

```yaml
ollama:
  environment:
    - OLLAMA_HOST=0.0.0.0
    - OLLAMA_NUM_PARALLEL=2        # Parallel request handling
    - OLLAMA_MAX_LOADED_MODELS=1   # Keep model in memory
```

### Option 4: Use External LLM API (Fastest)

For production, you can point to an external LLM API instead of local Ollama:
- Replace `ChatOllama` with `ChatOpenAI` in `llm_service.py`
- Set `OPENAI_API_KEY` and `OPENAI_BASE_URL` env vars
- Response times: **1-3 seconds**

### Performance Summary After Optimization

| Before (v1) | After (v2) | Improvement |
|-------------|-----------|-------------|
| 9 sequential LLM calls | 2 batched LLM calls | **4.5x fewer calls** |
| 137s on CPU | ~50-60s on CPU | **~2x faster** |
| 4000 max tokens | 512-800 max tokens | **Faster generation** |
| No RAG context | RAG-grounded remediation | **Better quality** |

---

## Firewall / Network

Open these ports on the VM firewall:

| Port | Service | Required |
|------|---------|----------|
| 4200 | Frontend UI | Yes |
| 8000 | Backend API + MCP | Yes |
| 8080 | MITM Proxy | Only if intercepting traffic |
| 5432 | PostgreSQL | Only for external DB access |

```bash
# Example (Ubuntu UFW)
sudo ufw allow 4200/tcp
sudo ufw allow 8000/tcp
sudo ufw allow 8080/tcp
```

---

## Troubleshooting

| Issue | Solution |
|-------|---------|
| Ollama model not pulling | Check CA cert mount, run `docker exec governance-server-ollama-1 ollama pull llama3.2:3b` manually |
| `llm_healthy: false` | Check `docker logs governance-server-ollama-1`, ensure model is pulled |
| API won't start | Check `docker compose logs api`, ensure Ollama is healthy first |
| Frontend 502/503 | API may still be starting — wait 30s, check `docker compose logs api` |
| Slow LLM responses | See Performance Tuning section above — GPU is the best fix |
| Database errors | Run the schema migration in Step 7 |
