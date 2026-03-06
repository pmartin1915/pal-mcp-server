# How to Create a Gemini API Key (Step-by-Step)

> This guide ensures you create a properly configured key that works with PAL MCP

---

## Prerequisites

- Google account with $300 Gemini credit
- The credit is tied to a **project**, not the account itself
- You may have multiple projects with separate credits

---

## Step 1: Go to Google AI Studio

1. Open: https://aistudio.google.com/apikey
2. Sign in with the Google account that has the $300 credit

---

## Step 2: Identify Your Project

Before creating a key, verify which project has your credit:

1. Look at the project dropdown (top of page or in key creation dialog)
2. Your $300 credit projects typically have names like:
   - `gen-lang-client-XXXXXXXXXX`
   - Or a custom name you set

**How to check credit:**
1. Go to: https://console.cloud.google.com/billing
2. Select your project
3. Look for "Credits" or "Free trial" balance

---

## Step 3: Create the API Key

1. Click **"Create API key"**
2. Select **"Create API key in existing project"**
3. **IMPORTANT**: Choose the project with your $300 credit
4. Click **"Create API key in existing project"**

You'll see a key like: `AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX`

---

## Step 4: Restrict the Key (Recommended)

Restricting the key prevents misuse and ensures it only works for Gemini:

1. Click on the key you just created (or click "Edit API key")
2. Scroll to **"API restrictions"**
3. Select **"Restrict key"**
4. In the dropdown, select: **"Generative Language API"**
5. Click **"Save"**

**Why restrict?**
- Limits what the key can access if leaked
- Ensures billing only goes to Gemini usage
- Cleaner audit trail

---

## Step 5: Enable Generative Language API (If Not Already)

Sometimes the API needs to be explicitly enabled on the project:

1. Go to: https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com
2. Make sure your project is selected (top dropdown)
3. Click **"Enable"** if it shows that option
4. If it says "API Enabled", you're good

**Direct link for your project:**
```
https://console.developers.google.com/apis/api/generativelanguage.googleapis.com/overview?project=YOUR_PROJECT_NUMBER
```

---

## Step 6: Test the Key

Before using in PAL, verify the key works:

### Option A: PowerShell (Windows)
```powershell
Invoke-RestMethod -Uri 'https://generativelanguage.googleapis.com/v1beta/models?key=YOUR_KEY_HERE' -Method Get
```

If successful, you'll see a list of models including `gemini-3-pro-preview`.

### Option B: Browser
Paste this URL (with your key):
```
https://generativelanguage.googleapis.com/v1beta/models?key=YOUR_KEY_HERE
```

You should see JSON with model definitions.

### Option C: curl
```bash
curl "https://generativelanguage.googleapis.com/v1beta/models?key=YOUR_KEY_HERE"
```

---

## Step 7: Save Key Details

Record these for future reference:

| Field | Value |
|-------|-------|
| API Key | `AIza...` |
| Key Name | (whatever you named it) |
| Project Name | |
| Project Number | |
| Account Email | |
| Created Date | |

Add this to the account table in `PAL-MCP-SETUP.md`.

---

## Step 8: Apply to PAL MCP

Run the switch script:
```powershell
cd C:\Users\perry\pal-mcp-server
.\Switch-GeminiKey.ps1 -ApiKey "AIzaYourNewKey" -ProjectNumber "123456789"
```

Or manually update:
1. `.env` file
2. `mcp.json`
3. System env vars

Then restart VSCode.

---

## Troubleshooting

### "API has not been used in project X"
- The project number in the error tells you which key is being used
- Go to that project and enable Generative Language API
- Or: You're using the wrong API key

### "API key not valid"
- Key was deleted or regenerated
- Key has IP/referrer restrictions blocking your request
- Typo in the key

### "Quota exceeded"
- $300 credit exhausted on this project
- Switch to another account/project

### Key works in browser but not in PAL
- PAL is using a different key (check system env vars)
- Add `PAL_MCP_FORCE_ENV_OVERRIDE=true` to .env

---

## Common Mistakes to Avoid

1. **Wrong project** - Creating key in a project without credit
2. **Not enabling API** - The Generative Language API must be enabled
3. **Over-restricting** - If you restrict to wrong API, calls fail
4. **Old keys in system env** - System variables override .env without FORCE_ENV_OVERRIDE
5. **Not restarting VSCode** - MCP server needs full restart to pick up changes

---

## Quick Reference

| Step | Action |
|------|--------|
| 1 | Go to aistudio.google.com/apikey |
| 2 | Sign in with credited account |
| 3 | Create key in correct project |
| 4 | Restrict to Generative Language API |
| 5 | Enable API on project if needed |
| 6 | Test with PowerShell/browser |
| 7 | Run Switch-GeminiKey.ps1 |
| 8 | Restart VSCode |
| 9 | Test in Claude |
