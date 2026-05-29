# ANTS Production Deploy Script
# Usage: .\scripts\deploy_production.ps1
# Requires: gh CLI authenticated, lushito SSH key at ~/lushito

param(
    [string]$VpsHost = "173.212.232.176",
    [string]$VpsUser = "root",
    [string]$VpsPath = "~/ants-apps/ants-ai-gateway",
    [string]$SshKey  = "$env:USERPROFILE\lushito"
)

$ErrorActionPreference = "Stop"

Write-Host "ANTS Production Deploy" -ForegroundColor Cyan
Write-Host "======================" -ForegroundColor Cyan

# 1. Set VPS_SSH_KEY secret
Write-Host "`n[1/3] Configuring GitHub Secret VPS_SSH_KEY..." -ForegroundColor Yellow
$keyContent = Get-Content $SshKey -Raw
gh secret set VPS_SSH_KEY --body $keyContent --repo mhgutie/ants-ai-gateway
Write-Host "  Secret set." -ForegroundColor Green

# 2. Trigger GitHub Actions deploy workflow
Write-Host "`n[2/3] Triggering GitHub Actions deploy..." -ForegroundColor Yellow
gh workflow run deploy.yml --repo mhgutie/ants-ai-gateway
Start-Sleep -Seconds 5

# Wait for deploy run to complete
$maxWait = 120
$elapsed = 0
do {
    Start-Sleep -Seconds 10
    $elapsed += 10
    $run = gh run list --repo mhgutie/ants-ai-gateway --workflow deploy.yml --limit 1 --json status,conclusion | ConvertFrom-Json
    $status = $run[0].status
    $conclusion = $run[0].conclusion
    Write-Host "  Deploy status: $status ($elapsed s)" -ForegroundColor Gray
} while ($status -ne "completed" -and $elapsed -lt $maxWait)

if ($conclusion -eq "success") {
    Write-Host "  Deploy succeeded!" -ForegroundColor Green
} else {
    Write-Host "  Deploy conclusion: $conclusion — check GitHub Actions for details." -ForegroundColor Yellow
}

# 3. Smoke test /proposal/generate
Write-Host "`n[3/3] Smoke testing /proposal/generate..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

$body = @{
    licitacion_id = "smoke-deploy-$(Get-Date -Format 'yyyyMMddHHmm')"
    title         = "Sistema de gestion documental municipal"
    description   = "Automatizar recepcion y derivacion de documentos internos de la municipalidad."
} | ConvertTo-Json

$envPath = Join-Path $PSScriptRoot ".." ".env"
$apiKey = (Get-Content $envPath | Where-Object { $_ -match "^ANTS_GATEWAY_API_KEY=" }) -replace "^ANTS_GATEWAY_API_KEY=", ""

try {
    $resp = Invoke-RestMethod -Uri "https://gateway.fullants.com/proposal/generate" `
        -Method POST `
        -Headers @{ "X-ANTS-API-Key" = $apiKey; "Content-Type" = "application/json" } `
        -Body $body
    Write-Host "  allowed=$($resp.allowed) | rag_total=$($resp.rag_total) | model=$($resp.model_used)" -ForegroundColor Green
    Write-Host "  cost=`$$($resp.real_cost_usd)" -ForegroundColor Green
    Write-Host "`nDeploy complete. ANTS is live at https://gateway.fullants.com" -ForegroundColor Cyan
} catch {
    Write-Host "  Smoke test failed: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "  Check: https://gateway.fullants.com/health" -ForegroundColor Yellow
}
