# Ollama Setup - 100% FREE Vision AI

## 🎯 Overview

This guide shows you how to replace AWS Bedrock Vision with **Ollama + Llama 3.2 Vision** for **100% FREE** diagram analysis.

## 💰 Cost Savings

| Approach | Cost per Diagram | Cost per 1,000 Diagrams | Annual Cost (10K/month) |
|----------|------------------|-------------------------|-------------------------|
| **AWS Bedrock** | $0.03 | $30.00 | $3,600 |
| **Ollama (FREE)** | $0.00 | $0.00 | **$0** ✨ |
| **Savings** | **$0.03 (100%)** | **$30.00 (100%)** | **$3,600 (100%)** |

## 🚀 Quick Start

### Option 1: Automated Setup (Recommended)

```bash
# Run the automated setup script
./setup-ollama.sh
```

That's it! The script will:
1. Install Ollama
2. Start the Ollama service
3. Download Llama 3.2 Vision model (~7GB)
4. Configure DevGenius to use Ollama
5. Install Python dependencies

### Option 2: Manual Setup

#### Step 1: Install Ollama

**macOS:**
```bash
brew install ollama
# OR
curl -fsSL https://ollama.com/install.sh | sh
```

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**Windows:**
Download from [https://ollama.com/download](https://ollama.com/download)

#### Step 2: Start Ollama Service

```bash
ollama serve
```

Leave this running in a terminal, or run in background:
```bash
# macOS/Linux
nohup ollama serve > /tmp/ollama.log 2>&1 &

# Or use systemd (Linux)
sudo systemctl enable ollama
sudo systemctl start ollama
```

#### Step 3: Download Llama 3.2 Vision Model

```bash
ollama pull llama3.2-vision
```

This downloads the ~7GB model. First pull takes a few minutes.

#### Step 4: Verify Installation

```bash
# Check Ollama is running
curl http://localhost:11434/api/tags

# List installed models
ollama list

# Test the model
ollama run llama3.2-vision "Hello!"
```

### Option 3: Docker Setup

```bash
# Start Ollama in Docker
docker-compose -f docker-compose.ollama.yml up -d

# Wait for model to download
docker logs devgenius-ollama-pull -f

# Verify
docker exec -it devgenius-ollama ollama list
```

## 🔧 Configuration

### Environment Variables

Create `chatbot/.env`:

```bash
# Vision AI Provider Configuration
VISION_PROVIDER=ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_VISION_MODEL=llama3.2-vision

# AWS (optional - only for Bedrock fallback)
# AWS_REGION=us-east-1
```

### Vision Provider Selection

The orchestrator auto-detects the best available provider:

1. **Auto (default)**: Tries Ollama first, falls back to Bedrock
2. **Ollama**: Forces use of Ollama (fails if not available)
3. **Bedrock**: Forces use of AWS Bedrock

```python
# In code
from iac_orchestrator import IaCOrchestrator

# Auto-detect (Ollama if available, else Bedrock)
orchestrator = IaCOrchestrator(vision_provider="auto")

# Force Ollama
orchestrator = IaCOrchestrator(vision_provider="ollama")

# Force Bedrock
orchestrator = IaCOrchestrator(vision_provider="bedrock")
```

```bash
# CLI
python iac_orchestrator.py --vision-provider auto     # default
python iac_orchestrator.py --vision-provider ollama   # force Ollama
python iac_orchestrator.py --vision-provider bedrock  # force Bedrock
```

## 🧪 Testing

### Test 1: Direct Vision AI Test

```bash
cd chatbot

# Test Ollama vision directly
python vision_ai_ollama.py

# With an image
python vision_ai_ollama.py path/to/diagram.png
```

### Test 2: Full Pipeline Test

```bash
# Generate Terraform from a diagram
python iac_orchestrator.py \
  --image tests/sample_diagrams/web_app.png \
  --name test-architecture \
  --env dev \
  --vision-provider ollama
```

### Test 3: Cost Comparison

```bash
# See cost savings
python iac_orchestrator.py --cost-comparison
```

Expected output:
```
💰 Cost Comparison: LLM-based vs Template-based (Bedrock vs Ollama)
================================================================================

📊 OLD APPROACH (LLM-based generation):
  Per diagram: $0.53
  100 diagrams: $53.0

📊 NEW APPROACH - BEDROCK (Template-based + Bedrock Vision):
  Per diagram: $0.03
  100 diagrams: $3.0
  💵 Savings: $0.5 (94.3%)

📊 NEW APPROACH - OLLAMA (Template-based + Ollama (FREE)):
  Per diagram: $0.0 🎉 FREE!
  100 diagrams: $0.0
  💵 Savings: $0.53 (100.0%)
  ℹ️  Runs on your infrastructure (local/EC2 ~$0.08/hour)

💡 Recommendation:
  Use Ollama for 100% cost savings. Fall back to Bedrock only if Ollama is
  unavailable or you need absolute highest accuracy.
================================================================================
```

## 📊 Performance Comparison

| Metric | AWS Bedrock | Ollama (Local) | Ollama (EC2 GPU) |
|--------|-------------|----------------|------------------|
| **Cost per diagram** | $0.03 | $0.00 | $0.00 |
| **Latency** | 2-3s | 10-15s (CPU) | 3-5s (GPU) |
| **Accuracy** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Privacy** | ❌ Sends to AWS | ✅ Runs locally | ✅ Your VPC |
| **Offline** | ❌ No | ✅ Yes | ❌ No |

## 🖥️ Hardware Requirements

### Minimum (CPU):
- 8GB RAM
- 10GB disk space
- Processing time: ~10-15 seconds per diagram

### Recommended (GPU):
- 16GB RAM
- NVIDIA GPU with 8GB+ VRAM
- 10GB disk space
- Processing time: ~3-5 seconds per diagram

### Cloud Options:

**AWS EC2:**
- **CPU**: `t3.large` ($0.08/hour) - Process ~200 diagrams/hour = $0.0004 per diagram
- **GPU**: `g4dn.xlarge` ($0.526/hour) - Process ~1000 diagrams/hour = $0.0005 per diagram

**Still 98%+ cheaper than Bedrock!**

## 🐳 Docker Deployment

### Local Development

```bash
# Start Ollama
docker-compose -f docker-compose.ollama.yml up -d

# Check logs
docker logs devgenius-ollama -f

# Use in your app
OLLAMA_HOST=http://localhost:11434 python iac_orchestrator.py ...
```

### Production (EC2/ECS)

```yaml
# docker-compose.ollama.yml
services:
  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia  # GPU support
              count: 1
              capabilities: [gpu]
```

## 🔄 Migration from Bedrock to Ollama

### Step 1: Install Ollama

```bash
./setup-ollama.sh
```

### Step 2: Update Configuration

```bash
# chatbot/.env
VISION_PROVIDER=ollama  # Change from 'bedrock' to 'ollama'
```

### Step 3: Test

```bash
python iac_orchestrator.py --cost-comparison
```

### Step 4: Deploy

No code changes needed! The orchestrator auto-detects Ollama.

## 🛠️ Troubleshooting

### Issue: "Ollama server not available"

**Solution:**
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not, start it
ollama serve

# Or restart Docker container
docker restart devgenius-ollama
```

### Issue: "Model not found"

**Solution:**
```bash
# Pull the model
ollama pull llama3.2-vision

# Verify
ollama list
```

### Issue: "Connection timeout"

**Solution:**
```bash
# Increase timeout in vision_ai_ollama.py
# Default is 120 seconds

# Or check if model is still downloading
ollama list  # Shows download progress
```

### Issue: "Out of memory"

**Solution:**
```bash
# Use smaller model (if available)
ollama pull llama3.2-vision:7b

# Or upgrade hardware
# - Add more RAM
# - Use GPU instance
```

### Issue: "Slow performance"

**Solutions:**
1. **Use GPU**: Deploy on EC2 `g4dn.xlarge` with GPU support
2. **Batch processing**: Process multiple diagrams together
3. **Model caching**: Keep Ollama service running (models stay in memory)

## 📈 Production Best Practices

### 1. High Availability

```bash
# Run multiple Ollama instances behind a load balancer
# Load balancer → Ollama1, Ollama2, Ollama3
```

### 2. Monitoring

```bash
# Add health checks
curl http://localhost:11434/api/tags

# Monitor response times
# Set up CloudWatch/Prometheus alerts
```

### 3. Scaling

```yaml
# Kubernetes deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ollama
spec:
  replicas: 3  # Scale horizontally
  selector:
    matchLabels:
      app: ollama
  template:
    metadata:
      labels:
        app: ollama
    spec:
      containers:
      - name: ollama
        image: ollama/ollama:latest
        resources:
          requests:
            memory: "8Gi"
            cpu: "2"
          limits:
            nvidia.com/gpu: 1
```

### 4. Caching

```python
# Add response caching for repeated diagrams
from functools import lru_cache
import hashlib

@lru_cache(maxsize=1000)
def analyze_diagram_cached(image_hash):
    return vision_ai.analyze_diagram(image_data)
```

## 🔒 Security & Privacy

### Benefits of Ollama:

1. **Data Privacy**: Diagrams never leave your infrastructure
2. **No API Keys**: No AWS credentials needed
3. **Compliance**: Easier HIPAA/GDPR compliance
4. **Audit**: Full control over model and data

### Recommended Setup:

```bash
# Run Ollama in private VPC
# No public internet access required
# Use VPC endpoints for AWS services if needed
```

## 💡 Advanced Usage

### Custom Models

```bash
# Use different vision models
ollama pull llava
ollama pull bakllava

# Configure in .env
OLLAMA_VISION_MODEL=llava
```

### GPU Optimization

```bash
# Enable GPU acceleration
docker run --gpus all ollama/ollama
```

### API Integration

```python
# Direct API usage
import requests

response = requests.post('http://localhost:11434/api/generate', json={
    'model': 'llama3.2-vision',
    'prompt': 'Analyze this architecture diagram',
    'images': [base64_image]
})
```

## 📚 Resources

- **Ollama**: https://ollama.com
- **Llama 3.2**: https://ollama.com/library/llama3.2-vision
- **DevGenius Docs**: `COST_OPTIMIZATION.md`
- **Docker Hub**: https://hub.docker.com/r/ollama/ollama

## 🆘 Support

For issues or questions:
1. Check this document
2. Check `COST_OPTIMIZATION.md`
3. Open GitHub issue with tag `ollama`

---

**Congratulations!** You now have a 100% FREE vision AI system that saves $0.03 per diagram! 🎉
