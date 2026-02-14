#!/bin/bash

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
KEYS_DIR="$PROJECT_ROOT/keys"
ENV_FILE="$PROJECT_ROOT/.env"
FORCE=false

while [[ $# -gt 0 ]]; do
    case "$1" in
        -f|--force)
            FORCE=true
            shift
            ;;
        *)
            echo "Unknown argument: $1"
            echo "Usage: $(basename "$0") [-f|--force]"
            exit 1
            ;;
    esac
done

echo "Generating EC signature keys"

if [ ! -d "$KEYS_DIR" ]; then
    echo "Creating keys directory: $KEYS_DIR"
    mkdir -p "$KEYS_DIR"
fi

if [ ! -f "$ENV_FILE" ]; then
    echo "Error: File .env not found"
    exit 1
fi

source <(grep -v '^#' "$ENV_FILE" | sed -E 's/^([^=]*)=(.*)$/export \1="\2"/')

if [ -z "$PRIVATE_SIGNATURE_KEY_PASSWORD" ]; then
    echo "Error: There's no PRIVATE_SIGNATURE_KEY_PASSWORD variable in .env"
    exit 1
fi

PRIVATE_KEY="$KEYS_DIR/private_key.pem.enc"
PUBLIC_KEY="$KEYS_DIR/public_key.pem"

if [ -f "$PRIVATE_KEY" ] || [ -f "$PUBLIC_KEY" ]; then
    if [ "$FORCE" = false ]; then
        echo "Keys already exist. Use -f/--force to overwrite."
        exit 0
    fi
    echo "Force flag set — overwriting existing keys..."
fi

cd "$KEYS_DIR" || exit 1

echo "Generating encrypted private signature key..."
openssl ecparam -name prime256v1 -genkey | openssl ec -aes256 -passout pass:"$PRIVATE_SIGNATURE_KEY_PASSWORD" -out private_key.pem.enc

if [ $? -ne 0 ]; then
    echo "Error while generating encrypted private signature key"
    exit 1
fi

echo "Generated private signature key: $PRIVATE_KEY"

echo "Generating public signature verification key..."
openssl ec \
    -passin pass:"$PRIVATE_SIGNATURE_KEY_PASSWORD" \
    -in private_key.pem.enc \
    -pubout \
    -out public_key.pem

if [ $? -ne 0 ]; then
    echo "Error while generating public signature key"
    exit 1
fi

echo "Generated public signature key: $PUBLIC_KEY"
echo "Signature keys generated successfully!"

cd - > /dev/null
