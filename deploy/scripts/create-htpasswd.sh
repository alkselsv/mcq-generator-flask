#!/usr/bin/env bash
set -euo pipefail

# Create or update nginx Basic Auth credentials.
#
# Usage:
#   sudo ./deploy/scripts/create-htpasswd.sh [username]
#
# The file is stored at /etc/nginx/.htpasswd (not in the git repo).

HTPASSWD_FILE="${MCQ_HTPASSWD_FILE:-/etc/nginx/.htpasswd}"
USERNAME="${1:-}"

if [[ "${EUID}" -ne 0 ]]; then
    echo "Run as root: sudo $0 [username]" >&2
    exit 1
fi

if ! command -v htpasswd >/dev/null 2>&1; then
    echo "Installing apache2-utils for htpasswd..."
    apt-get update -qq
    apt-get install -y apache2-utils
fi

if [[ -z "${USERNAME}" ]]; then
    read -r -p "Username: " USERNAME
fi

if [[ -z "${USERNAME}" ]]; then
    echo "Username is required." >&2
    exit 1
fi

if [[ -f "${HTPASSWD_FILE}" ]]; then
    htpasswd "${HTPASSWD_FILE}" "${USERNAME}"
else
    htpasswd -c "${HTPASSWD_FILE}" "${USERNAME}"
fi

chmod 640 "${HTPASSWD_FILE}"
if getent group www-data >/dev/null 2>&1; then
    chown root:www-data "${HTPASSWD_FILE}"
fi

echo "Saved credentials to ${HTPASSWD_FILE}"
echo "Add more users with: sudo htpasswd ${HTPASSWD_FILE} another_user"
