# Quick Setup: GitHub Secrets

## Required Secrets

Go to your repository → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

Add these 4 secrets:

### 1. TQQQ_EMAIL_ENABLED
```
true
```

### 2. TQQQ_EMAIL_SENDER
```
jiazhongchen8341@gmail.com
```

### 3. TQQQ_EMAIL_PASSWORD

**⚠️ Important: This is NOT your Gmail password!**

You need a Gmail App Password:
1. Go to https://myaccount.google.com/security
2. Enable **2-Step Verification** (if not already enabled)
3. Scroll to **App passwords**
4. Click **Select app** → **Other (Custom name)**
5. Enter "TQQQ Bot" → **Generate**
6. Copy the 16-character password (format: `xxxx xxxx xxxx xxxx`)
7. Paste it here (without spaces):

```
tgotrypwvpelkhks
```

### 4. TQQQ_EMAIL_RECIPIENTS
```
jiazhong.chen@gmail.com
```

---

## Verification Checklist

- [ ] All 4 secrets added in GitHub repository settings
- [ ] Email password is the Gmail App Password (16 characters)
- [ ] Workflow file pushed to `.github/workflows/daily-trading-bot.yml`
- [ ] Test run triggered manually from Actions tab
- [ ] Email notification received successfully

## Test the Setup

After adding secrets, manually trigger the workflow:

1. Go to **Actions** tab
2. Click **Daily Trading Bot**
3. Click **Run workflow** → **Run workflow**
4. Wait ~2-3 minutes
5. Check your email for notifications

## Current Configuration

- **Tickers**: TQQQ, YINN
- **Schedule**: Mon-Fri at 9:00 AM ET (14:00 UTC)
- **Sender**: jiazhongchen8341@gmail.com
- **Recipient**: jiazhong.chen@gmail.com
- **Signal Types**: Golden Cross (🟢), Dead Cross (🔴)
