Set-Location -Path "$(Split-Path -Parent $MyInvocation.MyCommand.Path)\.."

Get-ChildItem -Path "./app" -Directory -Recurse | Where-Object { $_.Name -eq "__pycache__" } | Remove-Item -Force -Recurse

Write-Output "All __pycache__ directories have been removed."
