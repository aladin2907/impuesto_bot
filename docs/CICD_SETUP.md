# CI/CD Setup Guide

## Overview

Automated deployment pipeline using GitHub Actions:
- ✅ Build Docker image in GitHub (не нагружает сервер!)
- ✅ Push to GitHub Container Registry (бесплатно)
- ✅ Auto-deploy на production сервер
- ✅ Zero downtime deployment

## Setup Steps

### 1. Enable GitHub Container Registry

1. Go to your GitHub repo → Settings → Actions → General
2. Scroll to "Workflow permissions"
3. Select: **"Read and write permissions"**
4. Save

### 2. Add GitHub Secrets

Go to: **Settings → Secrets and variables → Actions → New repository secret**

Add these secrets:

| Secret Name | Value | Description |
|------------|-------|-------------|
| `SSH_HOST` | `63.180.170.54` | Your server IP |
| `SSH_USER` | `ubuntu` | SSH username |
| `SSH_PRIVATE_KEY` | `<your private key>` | Content of MyKeyPairN8Nserver.pem |

**How to get SSH_PRIVATE_KEY:**
```bash
cat /Users/macbook/credy/myown/AWS/MyKeyPairN8Nserver.pem
```
Copy the ENTIRE content including:
```
-----BEGIN RSA PRIVATE KEY-----
...all lines...
-----END RSA PRIVATE KEY-----
```

### 3. Update docker-compose.yml on Server

SSH to server and update the image name:
```bash
ssh -i /Users/macbook/credy/myown/AWS/MyKeyPairN8Nserver.pem ubuntu@63.180.170.54

cd /home/ubuntu/impuesto_bot
nano docker-compose.yml
```

Change line 5 to match your GitHub username:
```yaml
image: ghcr.io/YOUR_GITHUB_USERNAME/impuesto_bot:latest
```

### 4. First Deployment

Push to main branch:
```bash
git add .
git commit -m "feat: setup CI/CD with GitHub Actions"
git push origin main
```

Watch the deployment:
- Go to GitHub repo → Actions tab
- You'll see the workflow running
- Build takes ~5 mins
- Deploy takes ~1 min

### 5. Verify Deployment

```bash
# Check containers
docker ps

# Check logs
docker logs impuesto-bot-api --tail 50

# Test API
curl http://63.180.170.54/health
```

## Workflow Details

### Trigger Events
- ✅ `push` to `main` branch (automatic)
- ✅ Manual trigger via Actions tab

### Jobs

**1. build-and-push**
- Runs on GitHub servers (FREE!)
- Builds Docker image
- Pushes to `ghcr.io/YOUR_USERNAME/impuesto_bot:latest`

**2. deploy**
- SSH to production server
- Pulls latest code from git
- Pulls new Docker image
- Restarts containers
- Cleans up old images

### Benefits

1. **No server overload** - Build happens on GitHub, not on your 1GB RAM server
2. **Fast deploys** - Just pull image, no compilation
3. **Rollback ready** - Previous images kept in registry
4. **Automated** - Push to main = auto deploy
5. **Free** - GitHub Actions free for public repos

### Manual Deployment (если нужно)

```bash
# Go to GitHub repo → Actions → Build and Deploy → Run workflow
```

### Troubleshooting

**Image pull fails:**
```bash
# On server, login to GitHub Container Registry
echo YOUR_GITHUB_TOKEN | docker login ghcr.io -u YOUR_USERNAME --password-stdin
```

**SSH fails in Actions:**
- Check SSH_PRIVATE_KEY secret (must include BEGIN/END lines)
- Check server security group allows GitHub Actions IPs

**Container won't start:**
```bash
# Check logs
docker logs impuesto-bot-api

# Check .env file
cat /home/ubuntu/impuesto_bot/.env
```

## Next Steps

- [ ] Enable Slack/Telegram notifications on deploy
- [ ] Add staging environment
- [ ] Add automated tests before deploy
- [ ] Setup monitoring and alerts

## Rollback

```bash
# On server
docker pull ghcr.io/YOUR_USERNAME/impuesto_bot:main-PREVIOUS_SHA
docker-compose down
docker-compose up -d
```

