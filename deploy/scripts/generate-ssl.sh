#!/usr/bin/env bash
set -euo pipefail

# Generate a self-signed TLS certificate for nginx.
#
# Usage:
#   sudo ./deploy/scripts/generate-ssl.sh [CN]
#
# Examples:
#   sudo ./deploy/scripts/generate-ssl.sh 203.0.113.10
#   sudo ./deploy/scripts/generate-ssl.sh qg.example.com

SSL_DIR="${MCQ_SSL_DIR:-/etc/nginx/ssl}"
CERT_DAYS="${MCQ_SSL_DAYS:-3650}"
CN="${1:-questions-generator}"

if [[ "${EUID}" -ne 0 ]]; then
    echo "Run as root: sudo $0 [CN]" >&2
    exit 1
fi

mkdir -p "${SSL_DIR}"
chmod 700 "${SSL_DIR}"

KEY_FILE="${SSL_DIR}/selfsigned.key"
CRT_FILE="${SSL_DIR}/selfsigned.crt"

if [[ -f "${KEY_FILE}" || -f "${CRT_FILE}" ]]; then
    echo "Certificate files already exist in ${SSL_DIR}."
    read -r -p "Overwrite? [y/N] " answer
    if [[ "${answer}" != "y" && "${answer}" != "Y" ]]; then
        echo "Skipped."
        exit 0
    fi
fi

openssl req -x509 -nodes -days "${CERT_DAYS}" -newkey rsa:2048 \
    -keyout "${KEY_FILE}" \
    -out "${CRT_FILE}" \
    -subj "/CN=${CN}"

chmod 600 "${KEY_FILE}"
chmod 644 "${CRT_FILE}"

echo "Created:"
echo "  ${CRT_FILE}"
echo "  ${KEY_FILE}"
echo
echo "Browsers will show a certificate warning — accept it manually or import the cert."
