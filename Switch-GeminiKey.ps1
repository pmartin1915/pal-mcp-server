<#
.SYNOPSIS
    Switch Gemini API key for PAL MCP Server

.DESCRIPTION
    Updates the Gemini API key in all required locations:
    - .env file
    - mcp.json (Claude Code config)
    - System environment variables

.PARAMETER ApiKey
    The new Gemini API key (starts with AIza...)

.PARAMETER ProjectNumber
    Optional: Project number for documentation

.EXAMPLE
    .\Switch-GeminiKey.ps1 -ApiKey "AIzaSyNewKeyHere"

.EXAMPLE
    .\Switch-GeminiKey.ps1 -ApiKey "AIzaSyNewKeyHere" -ProjectNumber "430531890862"
#>

param(
    [Parameter(Mandatory=$true)]
    [ValidatePattern("^AIza")]
    [string]$ApiKey,

    [Parameter(Mandatory=$false)]
    [string]$ProjectNumber = ""
)

$ErrorActionPreference = "Stop"

Write-Host "`n=== Gemini API Key Switcher ===" -ForegroundColor Cyan
Write-Host "New Key: $($ApiKey.Substring(0,10))..." -ForegroundColor Yellow

# Paths
$envPath = "C:\Users\perry\pal-mcp-server\.env"
$mcpJsonPath = "C:\Users\perry\AppData\Roaming\Code\User\mcp.json"

# Step 1: Test the new key first
Write-Host "`n[1/4] Testing API key..." -ForegroundColor Cyan
try {
    $response = Invoke-RestMethod -Uri "https://generativelanguage.googleapis.com/v1beta/models?key=$ApiKey" -Method Get -ErrorAction Stop
    $modelCount = $response.models.Count
    Write-Host "  OK - Key valid, $modelCount models available" -ForegroundColor Green
} catch {
    Write-Host "  FAILED - Key is invalid or API not enabled" -ForegroundColor Red
    Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "`nPlease verify:" -ForegroundColor Yellow
    Write-Host "  1. The API key is correct (starts with AIza)"
    Write-Host "  2. Generative Language API is enabled on the project"
    Write-Host "  3. API key restrictions allow generativelanguage.googleapis.com"
    exit 1
}

# Step 2: Update .env file
Write-Host "`n[2/4] Updating .env file..." -ForegroundColor Cyan
$envContent = Get-Content $envPath -Raw
$envContent = $envContent -replace "GEMINI_API_KEY=AIza[^\r\n]+", "GEMINI_API_KEY=$ApiKey"
$envContent = $envContent -replace "GOOGLE_API_KEY=AIza[^\r\n]+", "GOOGLE_API_KEY=$ApiKey"
Set-Content $envPath $envContent -NoNewline
Write-Host "  OK - .env updated" -ForegroundColor Green

# Step 3: Update mcp.json
Write-Host "`n[3/4] Updating mcp.json..." -ForegroundColor Cyan
$mcpJson = Get-Content $mcpJsonPath -Raw | ConvertFrom-Json
$mcpJson.servers.pal.env.GEMINI_API_KEY = $ApiKey
$mcpJson.servers.pal.env.GOOGLE_API_KEY = $ApiKey
$mcpJson | ConvertTo-Json -Depth 10 | Set-Content $mcpJsonPath
Write-Host "  OK - mcp.json updated" -ForegroundColor Green

# Step 4: Update system environment variables
Write-Host "`n[4/4] Updating system environment variables..." -ForegroundColor Cyan
[System.Environment]::SetEnvironmentVariable('GEMINI_API_KEY', $ApiKey, 'User')
[System.Environment]::SetEnvironmentVariable('GOOGLE_API_KEY', $ApiKey, 'User')
Write-Host "  OK - System env vars updated" -ForegroundColor Green

# Summary
Write-Host "`n=== Complete ===" -ForegroundColor Green
Write-Host "All locations updated with new API key."
if ($ProjectNumber) {
    Write-Host "Project Number: $ProjectNumber"
}

Write-Host "`n" -NoNewline
Write-Host "NEXT STEP: " -ForegroundColor Yellow -NoNewline
Write-Host "Restart VSCode completely (Ctrl+Shift+Q)"
Write-Host "           Then test with: 'Test Gemini 3 Pro with PAL MCP'"

# Log the change
$logEntry = "$(Get-Date -Format 'yyyy-MM-dd HH:mm') - Switched to key $($ApiKey.Substring(0,15))... (Project: $ProjectNumber)"
Add-Content "C:\Users\perry\pal-mcp-server\key-changes.log" $logEntry
Write-Host "`nChange logged to key-changes.log" -ForegroundColor Gray
