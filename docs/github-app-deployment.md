# GitHub App deployment

This document describes how to register the GitHub App and run Sentinel as a webhook receiver.

## 1. Create the GitHub App

1. In GitHub: **Settings → Developer settings → GitHub Apps → New GitHub App** (or use an organization’s app settings).
2. Set **Webhook URL** to your public HTTPS endpoint, for example `https://your-host.example.com/api/github/webhook`.
3. Set **Webhook secret** and store the same value in `GITHUB_WEBHOOK_SECRET` on the server.
4. Under **Repository permissions**, grant at least:
   - **Pull requests**: Read and write (to post reviews and read diffs)
   - **Issues**: Read and write (for labels and consolidated comments on the PR thread)
   - **Contents**: Read-only (if you later clone full trees; optional for diff-only flow)
5. Subscribe to events: **Pull request**.
6. After creation, note **App ID** → `GITHUB_APP_ID`.

## 2. Install the app

Install the app on the target account or organization and select repositories. Note the **installation ID** (available from installation webhooks or the GitHub API).

## 3. Private key

Generate a private key for the app (PEM). Either:

- Set `GITHUB_PRIVATE_KEY` to the full PEM contents (including `BEGIN` / `END` lines), or  
- Set `GITHUB_PRIVATE_KEY_PATH` to a file path on the server that contains the PEM.

## 4. Runtime environment

| Variable | Purpose |
| --- | --- |
| `GITHUB_APP_ID` | App identifier |
| `GITHUB_PRIVATE_KEY` or `GITHUB_PRIVATE_KEY_PATH` | PEM for JWT auth |
| `GITHUB_WEBHOOK_SECRET` | Validates `X-Hub-Signature-256` |
| `ANTHROPIC_API_KEY` | Enables LLM specialists and coordinator summary |
| `GITHUB_TOKEN` | Personal token for `harvest` / local tooling only (not the app secret) |

## 5. Verify the webhook

Send a **ping** from the app configuration UI. The server should respond with `{"status":"ok","event":"ping"}`.

Open or synchronize a pull request; the app posts a consolidated comment, applies labels, and adds inline review comments for Critical/High findings when configured.

## 6. Idempotency

Re-processing the same commit is skipped when an existing PR comment already contains the same `Review fingerprint` line as the current run.

## 7. Local development

Use **smee.io** or another tunnel to forward `https://smee.io/your-channel` to `http://127.0.0.1:8080/api/github/webhook`, then set the app’s webhook URL to the smee URL.

Run the API locally:

```bash
sentinel-review ui
```
