# Testing Notifications Guide

This guide shows you how to manually test the notification system to ensure it works before deploying to GitHub Actions.

## Quick Test

Run this command to test a mock Golden Cross signal:

```bash
./run.sh && python scripts/test_notification.py --type golden
```

Or test both signal types:

```bash
python scripts/test_notification.py
```

## Test Script Options

```bash
# Test Golden Cross only
python scripts/test_notification.py --type golden --ticker TQQQ

# Test Dead Cross only
python scripts/test_notification.py --type dead --ticker YINN

# Test both signals (default)
python scripts/test_notification.py

# Test with custom ticker
python scripts/test_notification.py --type golden --ticker SPY
```

## Fix: Email Authentication Error

If you see an error like:
```
Email failed: (535, b'Username and Password not accepted')
```

This means your Gmail app password needs to be fixed:

### Step 1: Get Gmail App Password

1. Go to: https://myaccount.google.com/security
2. Enable **2-Step Verification** (if not already enabled)
3. Scroll down to **App passwords**
4. Click **Select app** → **Other (Custom name)**
5. Enter "TQQQ Bot" → Click **Generate**
6. You'll see a 16-character password like: `abcd efgh ijkl mnop`

### Step 2: Update .env File

Open `.env` file and update the password **without spaces**:

```bash
# Change this:
TQQQ_EMAIL_PASSWORD=tgot rypw vpel khks

# To this (remove all spaces):
TQQQ_EMAIL_PASSWORD=tgotrypwvpelkhks
```

Save the file.

### Step 3: Test Again

```bash
python scripts/test_notification.py --type golden
```

You should see:
```
✅ Email sent successfully to: jiazhong.chen@gmail.com
```

And receive an email with:
- Subject: "🟢 TQQQ Golden Cross Alert"
- Body with signal details (price, MA5, MA30)

## What Gets Tested

The test script simulates a crossover signal and tests:

1. ✅ **Console Logging** - Prints alert to terminal
2. ✅ **File Logging** - Writes to `logs/crossover_events.log`
3. ✅ **Email Notification** - Sends email to configured recipients
4. ✅ **Webhook Notifications** - Sends to registered webhooks (if any)

## Expected Output

When the test runs successfully, you'll see:

```
================================================================================
TESTING GOLDEN CROSS NOTIFICATION FOR TQQQ
================================================================================

Mock Signal Details:
  Ticker: TQQQ
  Date: 2026-01-31
  Type: GOLDEN_CROSS
  Close Price: $55.50
  MA5: $54.25
  MA30: $53.80

Sending notifications...

[2026-01-31 10:30:00] *** CROSSOVER ALERT ***
🟢 TQQQ Golden Cross (BULLISH)
Date: 2026-01-31
Close: $55.50
MA5: $54.25
MA30: $53.80

✅ Email sent successfully to: jiazhong.chen@gmail.com
✅ Logged to: logs/crossover_events.log

Email Configuration:
  Email Enabled: True
  Recipients: jiazhong.chen@gmail.com

✅ If email is configured correctly, you should receive an email!
```

## Check Email

You should receive an email like this:

**Subject**: 🟢 TQQQ Golden Cross Alert

**Body**:
```
*** CROSSOVER ALERT ***

🟢 TQQQ Golden Cross (BULLISH)

Date: 2026-01-31
Close: $55.50
MA5: $54.25
MA30: $53.80

The 5-day moving average has crossed ABOVE the 30-day moving average.
This is a BULLISH signal suggesting potential upward momentum.
```

## Check Logs

View the log file to see the alert was recorded:

```bash
tail -20 logs/crossover_events.log
```

## Troubleshooting

### Email Not Sending

**Check 1**: Email enabled in `.env`
```bash
grep EMAIL_ENABLED .env
# Should show: TQQQ_EMAIL_ENABLED=true
```

**Check 2**: Credentials are correct
```bash
grep EMAIL_ .env
# Verify sender, password, and recipients are set
```

**Check 3**: Gmail App Password format
- Must be 16 characters
- No spaces
- Not your regular Gmail password
- Must have 2-Step Verification enabled

**Check 4**: Test with a simple Python script
```python
import smtplib
from email.mime.text import MIMEText

sender = "jiazhongchen8341@gmail.com"
password = "tgotrypwvpelkhks"  # Your app password without spaces
recipient = "jiazhong.chen@gmail.com"

msg = MIMEText("Test email from TQQQ bot")
msg["Subject"] = "Test"
msg["From"] = sender
msg["To"] = recipient

with smtplib.SMTP("smtp.gmail.com", 587) as server:
    server.starttls()
    server.login(sender, password)
    server.send_message(msg)
    print("✅ Email sent!")
```

### No Console Output

If you don't see console output, check:
- Script is running with correct Python environment
- .env file is being loaded (use `./run.sh`)

### Webhook Errors

If you have webhooks configured and they fail:
- Check webhook URLs are HTTPS
- Verify webhook is enabled
- Test webhook URL manually with curl

## Testing Both Signals

To test both Golden Cross (TQQQ) and Dead Cross (YINN):

```bash
python scripts/test_notification.py
```

This will send two emails:
1. 🟢 TQQQ Golden Cross Alert
2. 🔴 YINN Dead Cross Alert

## Before Deploying to GitHub Actions

Once the test passes locally:

1. ✅ Email received successfully
2. ✅ Log file updated in `logs/crossover_events.log`
3. ✅ Console output shows success

Then you can confidently:
1. Add the same credentials to GitHub Secrets
2. Push the workflow to GitHub
3. Test manually from GitHub Actions tab

## GitHub Actions Test

After setting up GitHub Secrets, test the workflow:

1. Go to: https://github.com/Jarjarbinks8341/crossover-trading/actions
2. Click "Daily Trading Bot"
3. Click "Run workflow" → "Run workflow"
4. Wait 2-3 minutes
5. Check your email
6. Review the workflow logs

This will test the actual production workflow without waiting for the scheduled run.

## Summary

```bash
# Quick test (one command)
python scripts/test_notification.py

# Expected result
✅ Console output with signal details
✅ Email received in inbox
✅ Log file updated
✅ Ready for GitHub Actions deployment
```

Once this works, you know the entire notification pipeline is working correctly!
