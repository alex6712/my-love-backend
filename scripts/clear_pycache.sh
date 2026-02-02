#!/bin/bash

cd "$(dirname "$0")/../"

find ./app -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

echo "All __pycache__ directories have been removed."
