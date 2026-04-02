#!/usr/bin/env bash
# deploy.sh — DjangoPlay Web App (Backend) Deployment
#
# PURPOSE:
#   This script automates the production deployment of the DjangoPlay Web App.
#   It handles code synchronization, Python dependency management via PEP 621,
#   database migrations, and service restarts.
#
# USAGE:
#   This script is designed to be triggered by GitLab CI, but can be run manually:
#   ssh ubuntu@server 'bash ~path/to/scripts/deploy.sh'
#
# WHERE TO RUN:
#   Production Server within the application root.
#
# PREREQUISITES:
#   - Provide [deploy_paths] webapp_dir and venv_path.
#   - NOPASSWD sudoers entry for 'systemctl restart {service_name}'.
#   - SSH key for GitLab configured

set -euo pipefail

CONFIG_FILE="$HOME/.dplay/config.yaml"

# Helper to read YAML values via Python
get_config() {
    python3 -c "import yaml; print(yaml.safe_load(open('$CONFIG_FILE'))['deploy_paths']['$1'])"
}

echo "🚀 Starting DjangoPlay Web App Deploy"

# 1. Environment Guard
if [ ! -f "$CONFIG_FILE" ]; then
    echo "❌ Error: Configuration file $CONFIG_FILE not found."
    exit 1
fi

# 2. Dynamic Path Resolution
APP_ROOT=$(get_config "webapp_dir")
VENV_PATH=$(get_config "venv_path")

if [ ! -d "$APP_ROOT" ]; then
    echo "❌ Error: Resolved App root $APP_ROOT does not exist."
    exit 1
fi

cd "$APP_ROOT"

# 3. Code Sync
echo "→ Syncing source code..."
git fetch origin
git reset --hard origin/main

# 4. Environment Sync (PEP 621 / pyproject.toml)
echo "→ Syncing Python environment (pip install .)..."
"$VENV_PATH/bin/pip" install .

# 5. Database & Assets
echo "→ Running migrations..."
cd backend
"$VENV_PATH/bin/python" manage.py migrate --no-input

echo "→ Refreshing static assets..."
"$VENV_PATH/bin/python" manage.py collectstatic --no-input

# 6. Service Restart
echo "→ Restarting Gunicorn & Celery..."
sudo systemctl restart djangoplay djangoplay-celery

echo "─────────────────────────────────────────────────────────"
COMMIT=$(git log -1 --format="%h  %s  (%ar)")
echo "  Success: Web App deployed at $COMMIT"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"