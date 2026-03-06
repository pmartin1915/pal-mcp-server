# PAL MCP Server Setup & Troubleshooting Guide

> Last Updated: 2025-12-25
> Purpose: Single source of truth for PAL MCP configuration with Gemini API

---

## Quick Reference

### Current Working Configuration

| Setting | Value |
|---------|-------|
| API Key Location | `.env` file in this directory |
| Force Override | `PAL_MCP_FORCE_ENV_OVERRIDE=true` |
| Project | 430531890862 (gen-lang-client-0141782195) |
| Credit | $300 free tier |

### Files That Matter

| File | Purpose |
|------|---------|
| `C:\Users\perry\pal-mcp-server\.env` | API keys (PRIMARY SOURCE) |
| `C:\Users\perry\AppData\Roaming\Code\User\mcp.json` | Claude Code MCP config |
| `C:\Users\perry\AppData\Roaming\Code\User\globalStorage\rooveterinaryinc.roo-cline\settings\mcp_settings.json` | Roo Cline MCP config (separate) |

---

## Gemini API Key Accounts

Track your $300 credit accounts here:

| Account Email | Project ID | Project Number | Status | Notes |
|---------------|------------|----------------|--------|-------|
| pmartin1915@gmail.com | gen-lang-client-0141782195 | 430531890862 | ACTIVE | Current |
| (add more) | | | UNUSED | |
| (add more) | | | UNUSED | |

---

## How to Switch API Keys (When Credit Exhausted)

### Step 1: Create New API Key

1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Sign in with your account that has $300 credit
3. Click **"Create API key"**
4. Select the correct project (check Project Number matches your credit account)
5. **IMPORTANT**: Restrict the key to "Generative Language API" only
6. Copy the new `AIza...` key

### Step 2: Update .env File

Edit `C:\Users\perry\pal-mcp-server\.env`:

```env
# API Keys
PAL_MCP_FORCE_ENV_OVERRIDE=true
GEMINI_API_KEY=AIzaYourNewKeyHere
GOOGLE_API_KEY=AIzaYourNewKeyHere
```

### Step 3: Update mcp.json (Belt & Suspenders)

Edit `C:\Users\perry\AppData\Roaming\Code\User\mcp.json`:

```json
{
  "servers": {
    "pal": {
      "command": "C:\\Users\\perry\\.local\\bin\\uv.exe",
      "args": [
        "--directory",
        "C:\\Users\\perry\\pal-mcp-server",
        "run",
        "pal-mcp-server"
      ],
      "type": "stdio",
      "env": {
        "GEMINI_API_KEY": "AIzaYourNewKeyHere",
        "GOOGLE_API_KEY": "AIzaYourNewKeyHere",
        "PAL_MCP_FORCE_ENV_OVERRIDE": "true"
      }
    }
  },
  "inputs": []
}
```

### Step 4: Clear System Environment Variables (If Set)

Run in PowerShell:
```powershell
# Check current values
[System.Environment]::GetEnvironmentVariable('GEMINI_API_KEY', 'User')
[System.Environment]::GetEnvironmentVariable('GOOGLE_API_KEY', 'User')

# Update to new key
[System.Environment]::SetEnvironmentVariable('GEMINI_API_KEY', 'AIzaYourNewKeyHere', 'User')
[System.Environment]::SetEnvironmentVariable('GOOGLE_API_KEY', 'AIzaYourNewKeyHere', 'User')
```

### Step 5: Restart VSCode

**Full restart required** (Ctrl+Shift+Q or File > Exit), not just reload window.

### Step 6: Test

Ask Claude to run:
```
Test Gemini 3 Pro with PAL MCP
```

---

## Troubleshooting

### Error: "Generative Language API has not been used in project X"

**Root Cause**: Wrong API key being used. The project number in the error tells you which key is active.

**Diagnosis**:
1. Note the project number in the error (e.g., `690101294622`)
2. This does NOT match your intended project
3. An old/wrong API key is being picked up

**Fix Checklist**:
- [ ] Check `.env` has correct key
- [ ] Check `mcp.json` has correct key in `env` section
- [ ] Check system env vars: `[System.Environment]::GetEnvironmentVariable('GEMINI_API_KEY', 'User')`
- [ ] Ensure `PAL_MCP_FORCE_ENV_OVERRIDE=true` is in `.env`
- [ ] Full VSCode restart (not reload)

**Test API Key Directly**:
```powershell
Invoke-RestMethod -Uri 'https://generativelanguage.googleapis.com/v1beta/models?key=YOUR_KEY_HERE' -Method Get
```
If this returns models, the key works. If 403, wrong project or API not enabled.

### Error: 403 PERMISSION_DENIED

**Possible Causes**:
1. API key is for wrong project
2. Generative Language API not enabled on project
3. API key restrictions blocking the call

**Fix**:
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Select your project
3. Go to APIs & Services > Enabled APIs
4. Ensure "Generative Language API" is enabled
5. Check API key restrictions allow generativelanguage.googleapis.com

### PAL Shows "Configured" But Calls Fail

**Root Cause**: PAL validates keys exist but doesn't verify they work until called.

**Fix**: The `PAL_MCP_FORCE_ENV_OVERRIDE=true` setting ensures `.env` takes priority over:
- System environment variables
- Other cached values

---

## Architecture Overview

```
Claude Code (Opus)
       |
       v
   mcp.json (launches PAL with env vars)
       |
       v
   PAL MCP Server
       |
       +-- reads .env file
       +-- PAL_MCP_FORCE_ENV_OVERRIDE=true forces .env priority
       |
       v
   Gemini API (gemini-3-pro-preview, gemini-2.5-flash, etc.)
```

### Priority Order (with FORCE_ENV_OVERRIDE=true)

1. `.env` file values (WINS)
2. ~~mcp.json env vars~~ (ignored)
3. ~~System environment variables~~ (ignored)

### Priority Order (without FORCE_ENV_OVERRIDE)

1. System environment variables (can cause stale key issues!)
2. mcp.json env vars
3. .env file values

---

## Available Gemini Models

| Model | Context | Best For |
|-------|---------|----------|
| `gemini-3-pro-preview` | 1M | Deep reasoning, complex code, architecture |
| `gemini-2.5-pro` | 1M | Complex problems, analysis |
| `gemini-2.5-flash` | 1M | Fast iterations, quick tasks |
| `gemini-2.0-flash` | 1M | General purpose fast model |
| `gemini-2.0-flash-lite` | 1M | Lightweight, text-only |

**Aliases**: `pro` = gemini-3-pro-preview, `flash` = gemini-2.5-flash

---

## Workflow: Opus + Gemini

Use Claude Opus (via Claude Max) as your primary agent, with Gemini for:
- Heavy coding tasks (large context window)
- Second opinions on architecture
- Code review from different perspective
- Parallel analysis

Example prompts:
```
Use PAL to have Gemini 3 Pro review this code for security issues
Ask Gemini for a second opinion on this architecture
Have Gemini analyze the performance implications of this change
```

---

## Maintenance

### Monthly Check
- [ ] Verify API credit remaining at [AI Studio](https://aistudio.google.com)
- [ ] Test Gemini calls still work
- [ ] Update this doc if accounts change

### When Adding New Account
1. Add to "Gemini API Key Accounts" table above
2. Note project ID and number
3. Enable Generative Language API on new project
4. Create restricted API key

---

## Quick Commands

```powershell
# Check current system env var
[System.Environment]::GetEnvironmentVariable('GEMINI_API_KEY', 'User')

# Test API key works
Invoke-RestMethod -Uri 'https://generativelanguage.googleapis.com/v1beta/models?key=YOUR_KEY' -Method Get | Select-Object -First 1

# View .env file
Get-Content "C:\Users\perry\pal-mcp-server\.env" | Select-Object -First 5

# View mcp.json
Get-Content "C:\Users\perry\AppData\Roaming\Code\User\mcp.json"
```
