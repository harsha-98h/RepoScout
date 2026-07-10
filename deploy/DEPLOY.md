# RepoScout — AWS Deployment Guide

This guide deploys the RepoScout Streamlit app to **AWS App Runner** (recommended — fully managed, HTTPS auto-configured, auto-scaling).

> **Estimated cost**: ~$5–15/month for a hobby/portfolio project (scales to zero when idle on the free tier).

---

## Prerequisites

- [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html) installed & configured (`aws configure`)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installed and running
- AWS account with permissions for: ECR, App Runner, IAM

---

## Step 1 — Build & Test Docker Image Locally

```bash
cd /path/to/github_agent

# Build the image
docker build -t reposcout:latest .

# Test it locally (passes your .env secrets at runtime, NOT baked in)
docker run -p 8501:8501 \
  -e OPENAI_API_KEY="your_openai_key_here" \
  -e GITHUB_TOKEN="your_github_token_here" \
  reposcout:latest

# Visit http://localhost:8501 to verify it works
```

---

## Step 2 — Create an Amazon ECR Repository

Amazon ECR (Elastic Container Registry) stores your Docker images.

```bash
# Set your AWS region and account ID
export AWS_REGION="us-east-1"          # change to your region
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)

# Create the ECR repository (one-time setup)
aws ecr create-repository \
  --repository-name reposcout \
  --region $AWS_REGION
```

---

## Step 3 — Push Image to ECR

```bash
# Log in to ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS \
  --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Tag your image
docker tag reposcout:latest \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/reposcout:latest

# Push to ECR
docker push \
  $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/reposcout:latest

echo "✅ Image pushed: $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/reposcout:latest"
```

---

## Step 4 — Deploy to AWS App Runner (Console)

1. Go to [AWS App Runner Console](https://console.aws.amazon.com/apprunner)
2. Click **Create service**
3. **Source**: Choose **Container registry** → **Amazon ECR**
4. **Image URI**: `<your-account-id>.dkr.ecr.<region>.amazonaws.com/reposcout:latest`
5. **Deployment trigger**: Automatic (re-deploys when you push a new image)
6. **Port**: `8501`
7. **Environment variables** — Add these (⚠️ DO NOT use a .env file):
   | Key | Value |
   |-----|-------|
   | `OPENAI_API_KEY` | `sk-proj-...` |
   | `GITHUB_TOKEN` | `ghp_...` |
   | `DEBUG` | `False` |
   | `MAX_ITERATIONS` | `10` |
   | `TEMPERATURE` | `0.7` |
   | `OPENAI_MODEL` | `gpt-4o-mini` |
8. **Health check path**: `/_stcore/health`
9. Click **Create & deploy**

App Runner will give you a public HTTPS URL like:
`https://abcdefgh12.us-east-1.awsapprunner.com`

---

## Step 5 — Deploy via CLI (Alternative to Console)

```bash
# Create App Runner service via CLI
aws apprunner create-service \
  --service-name reposcout \
  --source-configuration '{
    "ImageRepository": {
      "ImageIdentifier": "'"$AWS_ACCOUNT_ID"'.dkr.ecr.'"$AWS_REGION"'.amazonaws.com/reposcout:latest",
      "ImageConfiguration": {
        "Port": "8501",
        "RuntimeEnvironmentVariables": {
          "OPENAI_API_KEY": "YOUR_KEY_HERE",
          "GITHUB_TOKEN": "YOUR_TOKEN_HERE",
          "DEBUG": "False",
          "OPENAI_MODEL": "gpt-4o-mini"
        }
      },
      "ImageRepositoryType": "ECR"
    },
    "AutoDeploymentsEnabled": true
  }' \
  --instance-configuration '{"Cpu": "1 vCPU", "Memory": "2 GB"}' \
  --region $AWS_REGION
```

---

## Updating the App

Every time you make changes, just rebuild and push — App Runner auto-deploys:

```bash
docker build -t reposcout:latest .
docker tag reposcout:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/reposcout:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/reposcout:latest
# App Runner detects the new image and re-deploys automatically ✅
```

---

## Alternative: EC2 Deployment (Simpler, More Control)

If you prefer EC2 over App Runner:

```bash
# 1. Launch an EC2 instance (Ubuntu 22.04, t3.small recommended)
# 2. SSH into the instance
ssh -i your-key.pem ubuntu@<ec2-public-ip>

# 3. Install Docker on EC2
sudo apt update && sudo apt install -y docker.io
sudo usermod -aG docker ubuntu && newgrp docker

# 4. Pull image from ECR
aws ecr get-login-password --region us-east-1 | \
  docker login --username AWS \
  --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

docker pull <account-id>.dkr.ecr.us-east-1.amazonaws.com/reposcout:latest

# 5. Run with environment variables
docker run -d -p 8501:8501 \
  -e OPENAI_API_KEY="sk-..." \
  -e GITHUB_TOKEN="ghp_..." \
  --restart always \
  --name reposcout \
  <account-id>.dkr.ecr.us-east-1.amazonaws.com/reposcout:latest

# 6. Open port 8501 in the EC2 Security Group
# Then visit: http://<ec2-public-ip>:8501
```

---

## Security Best Practices

| ✅ Do | ❌ Don't |
|-------|----------|
| Store secrets in App Runner env vars or AWS Secrets Manager | Commit `.env` to git |
| Use IAM roles with least-privilege access | Hardcode API keys in Dockerfile or source code |
| Enable HTTPS (App Runner does this automatically) | Expose port 8501 publicly without a firewall on EC2 |
| Use ECR image scanning | Pull images from untrusted registries |

---

## Estimated Costs

| Service | Cost |
|---------|------|
| App Runner (0.25 vCPU, 0.5 GB) | ~$5–10/month |
| ECR storage (< 1 GB image) | ~$0.10/month |
| Data transfer | ~$0–2/month |
| **Total** | **~$5–12/month** |

> App Runner has a **free tier**: 100 build minutes + 100 compute hours/month for the first year.
