# Job Application Email Tracker

A Python app that scans your email for job-application-related messages, uses Google's Gemini API to interpret them, and records the results in a Google Sheet. It is designed to run automatically every day, so your tracker stays up to date without any manual work. Currently requires additional work to setup automatic runs, hopefully to be improved upon in future versions.


## How it works

1. The app connects to your Google account using OAuth credentials.
2. It reads relevant emails, specifically ones that are related to your job applications.
3. `gemini_interactor.py` sends the email content to Gemini to extract details such as company, role, and application status.
4. `spreadsheet_interactor.py` writes or updates rows in your Google Sheet.

## Project structure

| File | Purpose |
| --- | --- |
| `app.py` | Main entry point. Run this to execute the tracker. |
| `refresh_credentials.py` | Reauthorizes Google access when the saved token has expired or been revoked. |
| `gemini_interactor.py` | Handles requests to the Gemini API. |
| `spreadsheet_interactor.py` | Reads from and writes to the Google Sheet. |
| `requirements.txt` | Python dependencies. |
| `.github/workflows/python-app.yml` | GitHub Actions workflow that runs the tracker. |
| `.github/workflows/create-sheet.yml` | One-time workflow that creates the Google Spreadsheet and prints its ID in the Actions log. |

## Requirements

- Python 3.12
- A Google account and a Google Cloud project with the APIs you use enabled (Gmail API, Sheets API, Gemini API)
- A Gemini API key

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/dkucz/JobApplicationEmails.git
cd JobApplicationEmails
pip install -r requirements.txt
```

### 2. Create Google credentials

1. In the [Google Cloud Console](https://console.cloud.google.com/), create a project and enable the APIs the app uses.
2. Create an OAuth client ID (desktop app) and download it as `credentials.json`.
3. Run the app once locally and complete the sign-in. This creates `token.json`.

If the saved Google token is revoked or cannot be refreshed, run the credential refresh script from the project directory:

```bash
python refresh_credentials.py
```

It attempts to refresh the saved token. If Google rejects it with `invalid_grant`, the script removes `token.json` and starts the OAuth sign-in flow again using `credentials.json`. Complete sign-in in the browser; the new token is saved to `token.json`. You may then need to update the `GOOGLE_TOKEN_JSON` GitHub Actions secret with the new file contents. The current script also raises a `RuntimeError` after running because of its `finally` block, even if token refresh or sign-in succeeded; verify that `token.json` was updated before treating that error as a failed authorization.

> **Important:** if your OAuth consent screen is in **Testing** status, Google expires refresh tokens after 7 days. Set the app to **In production** to avoid your automated runs failing after a week.

Never commit `credentials.json` or `token.json`. Both should be listed in `.gitignore`.

### 3. Get a Gemini API key

Create one in [Google AI Studio](https://aistudio.google.com/).

### 4. Set environment variables (local runs)

| Variable | Description |
| --- | --- |
| `GEMINI_API_KEY` | Your Gemini API key |
| `GEMINI_MODEL` | Use `gemini-3.5-flash-lite` |
| `SPREADSHEET_ID` | The ID of your Google Sheet (the long string in its URL) |

### 5. Run locally

```bash
python app.py
```

## Running automatically on GitHub Actions

The workflow in `.github/workflows/python-app.yml` installs dependencies, restores your Google credentials from secrets, and runs `app.py`.

### Step 1: Add the Google and Gemini secrets

Go to **Settings → Secrets and variables → Actions → New repository secret** and add:

| Secret | Value |
| --- | --- |
| `GOOGLE_TOKEN_JSON` | Full contents of `token.json` |
| `GOOGLE_CREDENTIALS_JSON` | Full contents of `credentials.json` |
| `GEMINI_API_KEY` | Your Gemini API key |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` |

### Step 2: Create the spreadsheet

You don't need to create the Google Sheet by hand. Use the **Creates Google Spreadsheet** workflow instead:

1. Go to the **Actions** tab and select **Creates Google Spreadsheet**.
2. Click **Run workflow**.
3. When the run finishes, open it and expand the step that prints the spreadsheet ID in the log.
4. Copy the ID and save it as a new repository secret named `SPREADSHEET_ID`.

You only need to do this once. The spreadsheet is created in the Google account you authorized with `token.json`.

> **Note:** the spreadsheet ID on its own doesn't give anyone access to your sheet, since access is controlled by your Google account's sharing settings. Still, run logs on a public repository can be seen by other GitHub users, so don't share the sheet publicly or by link.

### Step 3: Run the tracker

The main workflow reads `SPREADSHEET_ID` along with the other secrets and runs `app.py`. Run it once from the **Actions** tab to confirm everything works, then set up the daily automatic run as described below.

### Triggering the workflow

Make sure the workflow's `on:` block includes `workflow_dispatch:` so it can be run manually and triggered externally:

```yaml
on:
  workflow_dispatch:
```

You can then run it from the **Actions** tab with **Run workflow**.

### Scheduling

GitHub's built-in `schedule:` trigger is best-effort. Runs can be delayed by an hour or more, and new schedules sometimes don't fire for a day or two. Cron times are in **UTC** unless you use the optional `timezone:` field.

For a dependable daily run, trigger the workflow from an external scheduler using the Google Apps Script below. Remove the `schedule:` block from the workflow once the script is working so it doesn't run twice.

## Automatic daily run with Google Apps Script

This script calls GitHub's API to start the workflow on a schedule you control.

1. Make sure your workflow has `workflow_dispatch:` in its `on:` block.
2. Create a **fine-grained personal access token** in GitHub (Settings → Developer settings → Personal access tokens). Limit it to this repository only, grant only **Actions: Read and write**, and set an expiration date.
3. Go to [script.google.com](https://script.google.com) and create a new project. Paste in the script below.
4. In **Project Settings → Script Properties**, add:
   - `GH_TOKEN`: your token
   - `GH_REPO`: `yourname/yourrepo`
   - `GH_WORKFLOW` (optional): defaults to `python-app.yml`
   - `GH_REF` (optional): defaults to `main`
5. Set the project's time zone in Project Settings.
6. Run `triggerWorkflow` once to authorize it. Google will show an "unverified app" warning, which is normal for personal scripts: click **Advanced → Go to (project name)**.
7. Under **Triggers**, add a time-driven **day timer** for `triggerWorkflow` and set failure notifications to notify you immediately.

```javascript
function triggerWorkflow() {
  const props = PropertiesService.getScriptProperties();
  const token = props.getProperty('GH_TOKEN');
  const repo = props.getProperty('GH_REPO');
  const workflow = props.getProperty('GH_WORKFLOW') || 'python-app.yml';
  const ref = props.getProperty('GH_REF') || 'main';

  if (!token || !repo) {
    throw new Error('Set GH_TOKEN and GH_REPO in Project Settings > Script Properties.');
  }

  const res = UrlFetchApp.fetch(
    'https://api.github.com/repos/' + repo + '/actions/workflows/' + workflow + '/dispatches',
    {
      method: 'post',
      contentType: 'application/json',
      headers: {
        Authorization: 'Bearer ' + token,
        Accept: 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28'
      },
      payload: JSON.stringify({ ref: ref }),
      muteHttpExceptions: true
    }
  );

  const code = res.getResponseCode();
  Logger.log(code);
  if (code !== 204) {
    throw new Error('GitHub dispatch failed: ' + code + ' ' + res.getContentText());
  }
}
```

A response code of `204` means success, and a new run appears in your Actions tab. Apps Script runs time-driven triggers at some point within the hour you choose, not at an exact minute.

## Troubleshooting

- **No scheduled runs appear:** GitHub's scheduler is best-effort. Use the Apps Script trigger above.
- **Auth errors after about a week:** your Google OAuth app is probably in Testing mode. Switch it to In production and regenerate `token.json`.
- **`invalid_grant: Token has been expired or revoked`:** run `python refresh_credentials.py` locally and complete Google sign-in. The script currently raises a `RuntimeError` unconditionally at exit, so check whether `token.json` was refreshed; if it was, update the `GOOGLE_TOKEN_JSON` secret if you use GitHub Actions.
- **Apps Script returns 401 or 403:** check the token's permissions and expiration.
- **Apps Script returns 404:** check `GH_REPO` and `GH_WORKFLOW` for typos.
- **Node.js deprecation warnings:** update the `actions/checkout` and `actions/setup-python` versions in the workflow.

## Security notes

- Keep `credentials.json`, `token.json`, and all API keys out of the repository. Use GitHub Secrets.
- Use a narrowly scoped, expiring token for the Apps Script trigger, and revoke it if it is ever exposed.

## License
