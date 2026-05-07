# PAL Billing Protection — Manual Setup Guide

These steps activate the Google Cloud hard cap (Layer A) that protects against overcharges
across all 3 machines. The in-process per-machine soft cap (Layer B) is already live in code —
you just need the Cloud side configured and a billed API key in your `.env`.

**Worst-case charge once this is set up:** ~$2.25/day even if all 3 machines hit maximum usage.

---

## Prerequisites

You need two browser sessions open:

- **Google Cloud Console:** https://console.cloud.google.com
- **Google AI Studio:** https://aistudio.google.com

You'll also need your PAL `.env` file open in a text editor:
`C:\Users\perry\pal-mcp-server\.env`

---

## Step 1 — Create (or reactivate) a billed Google Cloud project

Go to: **https://console.cloud.google.com/projectcreate**

1. Click **"New Project"** in the top-right of Cloud Console (or use the link above directly).
2. **Project name:** something recognizable like `pal-mcp-billing`
3. **Billing account:** Select your billing account. If you don't see one, go to
   https://console.cloud.google.com/billing and add a payment method first.
4. Click **Create** and wait ~30 seconds for the project to provision.
5. Make note of the **Project ID** shown (e.g. `pal-mcp-billing-123456`) — you'll need it.

> **If you want to reactivate your old project instead:** Go to
> https://console.cloud.google.com/billing, find the old project, and re-link it to your
> billing account. Then skip to Step 2.

---

## Step 2 — Enable the Generative Language API in your project

Go to: **https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com**

1. Make sure your **new project** is selected in the dropdown at the very top of the page
   (blue bar — it will show a project name).
2. Click the blue **Enable** button.
3. Wait for the confirmation screen (usually 10–15 seconds).

---

## Step 3 — Set the daily quota cap (the hard stop)

Go to: **https://console.cloud.google.com/iam-admin/quotas**

1. Confirm your new project is selected in the top dropdown.
2. In the **Filter** search box, type: `Generate Content requests per day`
3. You should see a row like:
   - **Service:** Generative Language API
   - **Quota:** Generate Content requests per day per project
4. Click the **checkbox** next to that row, then click **Edit Quotas** (pencil icon in the toolbar).
5. In the panel that opens, set the value to **`200`**.
6. Click **Save**.

> Google may show a confirmation dialog asking for a justification — just type "Daily budget cap"
> and submit. Changes take effect within a few minutes.

---

## Step 4 — Set up a $1 budget alert

Go to: **https://console.cloud.google.com/billing/budgets**

1. Click **Create Budget**.
2. **Scope:** Select your new project from the dropdown.
3. **Amount:** Set to **`$1.00`** (type `1` in the amount field).
4. **Alert thresholds:** Add three rows — **50%**, **90%**, **100%**.
5. Confirm your email (`pmartin1913@gmail.com`) is listed under **Notifications**.
6. Click **Save**.

You'll now receive an email the moment spending hits $0.50, $0.90, and $1.00 — long before
you'd approach the $2.25/day theoretical maximum.

---

## Step 5 — Get a new API key from AI Studio

Go to: **https://aistudio.google.com/apikey**

1. Click **Create API Key**.
2. In the dropdown, select **"Create API key in existing project"** (not a new one).
3. Choose the project you created in Step 1 (`pal-mcp-billing` or whatever you named it).
4. Click **Create API key in existing project**.
5. Copy the key — it starts with `AIza...`. Store it somewhere safe (e.g. your password manager)
   before closing the dialog.

> **Why AI Studio, not Cloud Console?** AI Studio creates keys scoped to the Generative
> Language API automatically. Cloud Console keys need extra IAM configuration.

---

## Step 6 — Update your `.env` file

Open: `C:\Users\perry\pal-mcp-server\.env`

Find the line:
```
GEMINI_API_KEY=your_gemini_api_key_here
```
(or whatever value is currently there — probably the old air-gapped key)

Replace it with:
```
GEMINI_API_KEY=AIza...  ← paste your key from Step 5 here
```

Then confirm (or add) these lines anywhere in the file:
```
PAL_BUDGET_ENABLED=true
```

The per-machine soft limits default to 60 Pro / 150 Flash, which is fine for a single machine.
If you want to change them:
```
PAL_DAILY_BUDGET_GEMINI_25_PRO=60
PAL_DAILY_BUDGET_GEMINI_25_FLASH=150
```

Save the file.

---

## Step 7 — Restart PAL and verify

In your terminal (PAL directory):
```
cd C:\Users\perry\pal-mcp-server
```

Restart your MCP server so it picks up the new `.env` values. Then make a test call — use
PAL `chat` with a short prompt. If it goes through, the key works.

To confirm Layer B (soft cap) is running, check the ledger file after the call:
```powershell
Get-Content C:\Users\perry\pal-mcp-server\.pal-call-log.jsonl
```
You should see a JSON line like:
```json
{"ts": "2026-05-06T14:22:01.123456+00:00", "model": "gemini-2.5-pro"}
```

---

## What happens if something goes wrong

| Symptom | Cause | Fix |
|---------|-------|-----|
| `PAL daily budget reached` error | Layer B soft cap hit | Increase `PAL_DAILY_BUDGET_GEMINI_25_PRO` in `.env` or set `PAL_BUDGET_ENABLED=false` temporarily |
| `Google Cloud daily quota exhausted` error | Layer A hard cap hit (200/day) | Wait until UTC midnight, or raise the quota in Cloud Console (Step 3) |
| `API_KEY_INVALID` error | Wrong key in `.env` | Re-copy from https://aistudio.google.com/apikey |
| No `.pal-call-log.jsonl` created | PAL never ran successfully | Check `.env` has valid key; check `logs/mcp_server.log` for errors |

---

## Repeat for other machines

Steps 1–4 are one-time Cloud Console setup — they apply globally across all machines automatically.

For each additional machine, only Step 6 is needed: copy the same `GEMINI_API_KEY` into
that machine's `.env` at `C:\Users\perry\pal-mcp-server\.env` (or wherever PAL lives on
that machine). Each machine gets its own independent `.pal-call-log.jsonl` ledger.
