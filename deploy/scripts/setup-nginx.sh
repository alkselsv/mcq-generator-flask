#!/usr/bin/env bash
set -euo pipefail

# Install and enable nginx site for MCQ Generator.
#
# Prerequisites:
#   - docker-compose stack running with web on 127.0.0.1:5000
#   - root/sudo access
#
# Usage:
#   sudo ./deploy/scripts/setup-nginx.sh [server_cn]
#
# server_cn — Common Name for self-signed certificate (IP or hostname).

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEPLOY_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
REPO_DIR="$(cd "${DEPLOY_DIR}/.." && pwd)"

NGINX_SITE_NAME="${MCQ_NGINX_SITE_NAME:-mcq-generator}"
NGINX_AVAILABLE="/etc/nginx/sites-available/${NGINX_SITE_NAME}"
NGINX_ENABLED="/etc/nginx/sites-enabled/${NGINX_SITE_NAME}"
BACKEND_URL="${MCQ_BACKEND_URL:-http://127.0.0.1:5000}"
SERVER_CN="${1:-questions-generator}"

if [[ "${EUID}" -ne 0 ]]; then
    echo "Run as root: sudo $0 [server_cn]" >&2
    exit 1
fi

echo "==> Installing packages"
if ! command -v nginx >/dev/null 2>&1; then
    apt-get update -qq
    apt-get install -y nginx
fi

if ! command -v htpasswd >/dev/null 2>&1; then
    apt-get update -qq
    apt-get install -y apache2-utils
fi

echo "==> Generating TLS certificate (CN=${SERVER_CN})"
bash "${SCRIPT_DIR}/generate-ssl.sh" "${SERVER_CN}"

if [[ ! -f /etc/nginx/.htpasswd ]]; then
    echo "==> Creating Basic Auth user"
    bash "${SCRIPT_DIR}/create-htpasswd.sh"
else
    echo "==> Basic Auth file already exists: /etc/nginx/.htpasswd"
    echo "    To add a user: sudo htpasswd /etc/nginx/.htpasswd username"
fi

echo "==> Installing nginx site config"
cp "${DEPLOY_DIR}/nginx/mcq-generator.conf" "${NGINX_AVAILABLE}"

if [[ -L /etc/nginx/sites-enabled/default ]]; then
    echo "==> Disabling default nginx site"
    rm -f /etc/nginx/sites-enabled/default
fi

ln -sf "${NGINX_AVAILABLE}" "${NGINX_ENABLED}"

echo "==> Checking backend at ${BACKEND_URL}"
if ! curl -fsS --max-time 3 "${BACKEND_URL}/health" >/dev/null 2>&1; then
    echo "WARNING: backend is not reachable at ${BACKEND_URL}/health"
    echo "Start the app first:"
    echo "  cd ${REPO_DIR} && docker-compose up -d --build"
fi

echo "==> Testing nginx configuration"
nginx -t

echo "==> Reloading nginx"
systemctl enable nginx
systemctl reload nginx

cat <<EOF

Done.

Open in browser:
  https://<server-ip>/

Notes:
  - Accept the self-signed certificate warning on first visit.
  - Use the Basic Auth login/password from /etc/nginx/.htpasswd.
  - Ensure docker-compose binds web only to 127.0.0.1:5000 (see docker-compose.yml).
  - Logs: /var/log/nginx/qg-access.log, /var/log/nginx/qg-error.log

Optional IP whitelist:
  sudo cp ${DEPLOY_DIR}/nginx/ip-whitelist.conf.example /etc/nginx/snippets/mcq-ip-whitelist.conf
  sudo nano /etc/nginx/snippets/mcq-ip-whitelist.conf
  # uncomment include line in ${NGINX_AVAILABLE}
  sudo nginx -t && sudo systemctl reload nginx

EOF
