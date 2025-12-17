#Requires -Version 5.1

Write-Host "requirements files generation..."

# Проверяем наличие pyproject.toml
if (-not (Test-Path "pyproject.toml")) {
    Write-Host "File pyproject.toml not found!"
    exit 1
}

# Генерация requirements-dev.txt
Write-Host "requirements-dev.txt generation..."
uv pip compile pyproject.toml --group dev -o requirements-dev.txt

# Генерация requirements.txt
Write-Host "requirements.txt generation..."
uv pip compile pyproject.toml -o requirements.txt

Write-Host "requirements files generated!"
