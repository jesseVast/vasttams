#!/bin/bash
# generate_self_signed_cert.sh
# Generates a self-signed certificate for local development

set -e

CERT_FILE="cert.pem"
KEY_FILE="key.pem"
DAYS=365

openssl req -x509 -nodes -days $DAYS -newkey rsa:2048 \
  -keyout $KEY_FILE -out $CERT_FILE \
  -subj "/CN=localhost"

echo "Self-signed certificate generated: $CERT_FILE, $KEY_FILE" 