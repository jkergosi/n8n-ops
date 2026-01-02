# GitHub Secrets Configuration

This document lists all secrets required for the GitHub Actions deployment workflows.

## How to Set Up

1. Go to your repository on GitHub
2. Navigate to **Settings** → **Secrets and variables** → **Actions**
3. Add each secret listed below

## Required Secrets

### VPS Access

| Secret | Description | Example |
|--------|-------------|---------|
| `VPS_HOST` | VPS hostname or IP | `deploy.example.com` |
| `VPS_USERNAME` | SSH username | `deploy` |
| `VPS_SSH_KEY` | Private SSH key for deployment | `-----BEGIN OPENSSH PRIVATE KEY-----...` |

### Staging Environment

| Secret | Description | Notes |
|--------|-------------|-------|
| `STAGING_DATABASE_URL` | PostgreSQL connection string | From Supabase Dashboard |
| `STAGING_SUPABASE_URL` | Supabase project URL | `https://xxx.supabase.co` |
| `STAGING_SUPABASE_KEY` | Supabase anon key | For client-side access |
| `STAGING_SUPABASE_SERVICE_KEY` | Supabase service role key | For admin operations |
| `STAGING_API_URL` | Backend API URL | `https://api.staging.example.com` |
| `STAGING_BACKEND_PATH` | Path on VPS to backend code | `/var/www/staging/backend` |
| `STAGING_FRONTEND_PATH` | Path on VPS to frontend dist | `/var/www/staging/frontend` |

### Production Environment

| Secret | Description | Notes |
|--------|-------------|-------|
| `PROD_DATABASE_URL` | PostgreSQL connection string | From Supabase Dashboard |
| `PROD_SUPABASE_URL` | Supabase project URL | `https://xxx.supabase.co` |
| `PROD_SUPABASE_KEY` | Supabase anon key | For client-side access |
| `PROD_SUPABASE_SERVICE_KEY` | Supabase service role key | For admin operations |
| `PROD_API_URL` | Backend API URL | `https://api.example.com` |
| `PROD_BACKEND_PATH` | Path on VPS to backend code | `/var/www/prod/backend` |
| `PROD_FRONTEND_PATH` | Path on VPS to frontend dist | `/var/www/prod/frontend` |

## GitHub Environments

You also need to configure GitHub Environments for deployment protection:

### Staging Environment
1. Go to **Settings** → **Environments** → **New environment**
2. Name: `staging`
3. No protection rules required (auto-deploy on push to main)

### Production Environment
1. Go to **Settings** → **Environments** → **New environment**
2. Name: `production`
3. **Required reviewers**: Add team members who can approve production deploys
4. **Wait timer**: Optional, e.g., 5 minutes for additional review time
5. **Deployment branches**: Limit to `main` branch only

## VPS Setup Requirements

The deployment workflows expect the following on your VPS:

### Directory Structure
```
/var/www/
├── staging/
│   ├── backend/           # Git clone of repo
│   │   ├── .venv/         # Python virtual environment
│   │   └── n8n-ops-backend/
│   └── frontend/          # Built frontend files
└── prod/
    ├── backend/
    │   ├── .venv/
    │   └── n8n-ops-backend/
    └── frontend/
```

### Systemd Services
Create systemd services for each environment:

```ini
# /etc/systemd/system/n8n-ops-staging-backend.service
[Unit]
Description=N8N Ops Staging Backend
After=network.target

[Service]
Type=simple
User=deploy
WorkingDirectory=/var/www/staging/backend/n8n-ops-backend
Environment="PATH=/var/www/staging/backend/.venv/bin"
EnvironmentFile=/var/www/staging/backend/.env
ExecStart=/var/www/staging/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 4001
Restart=always

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/n8n-ops-prod-backend.service
[Unit]
Description=N8N Ops Production Backend
After=network.target

[Service]
Type=simple
User=deploy
WorkingDirectory=/var/www/prod/backend/n8n-ops-backend
Environment="PATH=/var/www/prod/backend/.venv/bin"
EnvironmentFile=/var/www/prod/backend/.env
ExecStart=/var/www/prod/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 4000 --workers 4
Restart=always

[Install]
WantedBy=multi-user.target
```

### Nginx Configuration
Configure Nginx to proxy to the backend services and serve frontend files.

## Obtaining Secrets

### Supabase
1. Go to your Supabase project dashboard
2. Navigate to **Settings** → **API**
3. Copy the **URL**, **anon key**, and **service_role key**
4. Navigate to **Settings** → **Database**
5. Copy the **Connection string** (use the URI format)

### VPS SSH Key
1. Generate a deploy key: `ssh-keygen -t ed25519 -C "github-deploy"`
2. Add the public key to `~/.ssh/authorized_keys` on the VPS
3. Add the private key as the `VPS_SSH_KEY` secret

## Security Notes

- Never commit secrets to version control
- Rotate secrets periodically
- Use separate Supabase projects for staging and production
- Production environment should require approval for deploys
- Consider using a dedicated deploy user on the VPS with limited sudo access
