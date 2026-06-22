$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (-not (Test-Path ".\node_modules")) {
    npm.cmd install
}

npm.cmd run dev
