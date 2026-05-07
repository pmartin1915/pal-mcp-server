# PAL Billing Protection Setup

**What this does:** Puts a $2.25/day hard ceiling on Google Cloud charges, with an email alert at $1. Takes about 15 minutes total.

**Do these steps in order.** Keep two browser tabs open: Google Cloud Console and Google AI Studio.

---

## Before you start

Open this file on your computer so you can follow along:

`C:\Users\perry\pal-mcp-server\.env`

---

## Step 1 — Create a project in Google Cloud

**Go to:** <https://console.cloud.google.com/projectcreate>

1. In the **Project name** box, type: `pal-mcp`
2. Under **Billing account**, select your billing account from the dropdown.
   - If it says "No billing account" — go to <https://console.cloud.google.com/billing> first, add a card, then come back.
3. Click **Create**.
4. Wait about 30 seconds. You'll see a notification when it's ready.

> Write down the **Project ID** shown under your project name (looks like `pal-mcp-123456`). You'll need it in Step 5.

---

## Step 2 — Turn on the Gemini API for your project

**Go to:** <https://console.cloud.google.com/apis/library/generativelanguage.googleapis.com>

1. At the very top of the page there's a blue bar with a dropdown showing the current project. Make sure it shows `pal-mcp` (the one you just created).
   - If it shows a different project, click the dropdown and switch to `pal-mcp`.
2. Click the blue **Enable** button.
3. Wait 15 seconds for the confirmation screen.

---

## Step 3 — Set the daily call limit (the hard stop)

**Go to:** <https://console.cloud.google.com/iam-admin/quotas>

1. Confirm `pal-mcp` is selected in the project dropdown at the top.
2. In the **Filter** search box (looks like a search bar near the top of the table), type exactly:

   `Generate Content requests per day`

3. One row should appear. It will say **Generative Language API** in the Service column.
4. Click the **checkbox** on the left of that row.
5. A toolbar appears at the top — click the **pencil icon** (Edit Quotas).
6. A panel opens on the right. Change the number to **200**.
7. Click **Save and continue**, then **Done**.

> This is the actual hard stop. Google will reject all calls above 200/day across all your machines, no matter what.

---

## Step 4 — Set up a $1 spending alert

**Go to:** <https://console.cloud.google.com/billing/budgets>

1. Click **Create Budget**.
2. Under **Projects**, select `pal-mcp`.
3. Under **Amount**, type `1` (one dollar).
4. Under **Alert thresholds**, there will be a default row at 100%. Add two more:
   - Click **Add threshold** → set to `50`%
   - Click **Add threshold** → set to `90`%
5. Under **Notifications**, confirm your email shows up. It should be `pmartin1913@gmail.com`.
6. Click **Save**.

> You'll get an email the moment you hit 50 cents, 90 cents, and $1.00. The absolute max per day is ~$2.25, so you'll always get warned well before hitting it.

---

## Step 5 — Get your API key

**Go to:** <https://aistudio.google.com/apikey>

1. Click **Create API key**.
2. A dialog appears. Click **"Create API key in existing project"** (not the default option).
3. In the dropdown, select `pal-mcp` (the project from Step 1).
4. Click **Create API key in existing project**.
5. A key appears — it starts with `AIza`. **Copy it now.** Click Done.

> Paste it somewhere safe (password manager, note) before closing — you won't be able to see it again.

---

## Step 6 — Put the key in PAL

Open this file in any text editor (Notepad is fine):

`C:\Users\perry\pal-mcp-server\.env`

Find the line that starts with `GEMINI_API_KEY=` and replace everything after the `=` with your new key:

```
GEMINI_API_KEY=AIza...your key here...
```

Then find (or add) this line:

```
PAL_BUDGET_ENABLED=true
```

Save the file.

---

## Step 7 — Test it

Restart the PAL MCP server so it picks up the new key.

Then make one test call through PAL (use the `chat` tool with a short prompt).

After the call, check that the ledger file was created:

`C:\Users\perry\pal-mcp-server\.pal-call-log.jsonl`

If that file exists with a line of JSON in it, everything is working.

---

## You're done

From now on:

- Each machine tracks its own call count in `.pal-call-log.jsonl`
- PAL will warn you before you hit 60 Pro or 150 Flash calls/day per machine
- Google Cloud will hard-stop everything at 200 calls/day total across all machines
- You'll get an email before the bill hits $1

For your other machines, just copy the same `GEMINI_API_KEY` value into the `.env` file on each one. The Cloud Console setup (Steps 1–4) only needs to be done once.

---

## If something goes wrong

| What you see | What it means | Fix |
|---|---|---|
| `PAL daily budget reached` | Per-machine soft limit hit | Open `.env`, increase `PAL_DAILY_BUDGET_GEMINI_25_PRO` to a higher number |
| `Google Cloud daily quota exhausted` | 200-call hard cap hit | Wait until midnight UTC, or raise the quota in Step 3 |
| `API_KEY_INVALID` | Wrong key in `.env` | Go back to <https://aistudio.google.com/apikey> and get a fresh key |
| No `.pal-call-log.jsonl` file | PAL never ran successfully | Check `C:\Users\perry\pal-mcp-server\logs\mcp_server.log` for errors |
