#!/bin/bash

set -e

echo "requirements files generation..."

# Проверяем наличие pyproject.toml
if [ ! -f "pyproject.toml" ]; then
    echo "File pyproject.toml not found!"
    exit 1
fi

# Генерация requirements-dev.txt
echo "requirements-dev.txt generation..."
uv pip compile pyproject.toml --group dev -o requirements-dev.txt

# Генерация requirements.txt
echo "requirements.txt generation..."
uv pip compile pyproject.toml -o requirements.txt

echo "requirements files generated!"
