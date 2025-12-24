#!/bin/bash

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KEYS_DIR="$PROJECT_ROOT/keys"
ENV_FILE="$PROJECT_ROOT/.env"

echo "Generating AES-256 signing keys"

if [ ! -d "$KEYS_DIR" ]; then
    echo "Creating keys directory: $KEYS_DIR"
    mkdir -p "$KEYS_DIR"
fi

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: File .env not found"
    exit 1
fi

source <(grep -v '^#' "$ENV_FILE" | sed -E 's/^([^=]*)=(.*)$/export \1="\2"/')

if [ -z "$PRIVATE_KEY_PASSWORD" ]; then
    echo "Error: There's no PRIVATE_KEY_PASSWORD variable in .env"
    exit 1
fi

cd "$KEYS_DIR" || exit 1

echo "Generating encrypted private key..."
openssl genrsa -aes256 \
    -passout pass:"$PRIVATE_KEY_PASSWORD" \
    -out private_key.pem.enc 2048

if [ $? -ne 0 ]; then
    echo "Error while generating encrypted private key"
    exit 1
fi

echo "Generated private key: $KEYS_DIR/private_key.pem.enc"

echo "generated public key..."
openssl rsa \
    -passin pass:"$PRIVATE_KEY_PASSWORD" \
    -in private_key.pem.enc \
    -pubout \
    -out public_key.pem

if [ $? -ne 0 ]; then
    echo "Error while generating public key"
    exit 1
fi

echo "Generated public key: $KEYS_DIR/public_key.pem"
echo "Signing keys generated successfully!"

cd - > /dev/null
