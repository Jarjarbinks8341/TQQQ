# GitHub Actions Setup Guide

This guide explains how to set up the daily trading bot to run automatically using GitHub Actions.

## Overview

The GitHub Actions workflow runs daily at **9:00 AM ET (14:00 UTC)** on weekdays (Monday-Friday), right at market open to check for overnight crossover signals based on the previous day's closing prices.

## Workflow Features

- **Automatic Daily Execution**: Runs Mon-Fri at 6 PM ET
- **Multi-Ticker Support**: Fetches data for TQQQ and YINN
- **Crossover Detection**: Calculates MA5/MA30 crossovers
- **Email Notifications**: Sends alerts when signals are detected
- **Database Persistence**: Stores historical data between runs
- **Manual Trigger**: Can be triggered manually for testing

## Required GitHub Secrets

You need to configure the following secrets in your GitHub repository:

### How to Add Secrets

1. Go to your GitHub repository
2. Click **Settings** → **Secrets and variables** → **Actions**
3. Click **New repository secret**
4. Add each of the following secrets:

### Secret Configuration

| Secret Name | Description | Example Value |
|------------|-------------|---------------|
| `TQQQ_EMAIL_ENABLED` | Enable email notifications | `true` |
| `TQQQ_EMAIL_SENDER` | Gmail sender address | `your-email@gmail.com` |
| `TQQQ_EMAIL_PASSWORD` | Gmail app password (NOT your regular password) | `xxxx xxxx xxxx xxxx` |
| `TQQQ_EMAIL_RECIPIENTS` | Comma-separated list of recipients | `recipient@gmail.com` |

### Setting Up Gmail App Password

Gmail requires an "App Password" for automated access:

1. Go to your Google Account: https://myaccount.google.com/
2. Navigate to **Security** → **2-Step Verification** (enable if not already)
3. Scroll down to **App passwords**
4. Click **Select app** → **Other (Custom name)**
5. Enter "TQQQ Trading Bot" and click **Generate**
6. Copy the 16-character password (format: `xxxx xxxx xxxx xxxx`)
7. Use this password for `TQQQ_EMAIL_PASSWORD` secret

**Important**: Use the app password, NOT your regular Gmail password!

## Current Configuration

Based on your `.env` file:

- **Email Enabled**: `true`
- **Sender**: `jiazhongchen8341@gmail.com`
- **Recipient**: `jiazhong.chen@gmail.com`
- **Tickers**: `TQQQ`, `YINN`

## How It Works

### Daily Workflow

1. **Checkout Code**: Gets the latest code from the repository
2. **Setup Python**: Installs Python 3.12 and dependencies
3. **Download Database**: Retrieves database from previous run (artifacts)
4. **Fetch Prices**: Downloads latest prices for TQQQ and YINN from Yahoo Finance
5. **Detect Crossovers**: Calculates MA5 and MA30, detects Golden/Dead Cross signals
6. **Send Notifications**: If crossover detected, sends email notification
7. **Save Database**: Stores updated database for next run
8. **Upload Logs**: Saves execution logs for debugging

### Database Persistence

The workflow uses GitHub Actions **artifacts** to store the database between runs:
- Database is uploaded after each run
- Downloaded at the start of the next run
- Retained for 90 days
- Size: ~500KB (grows slowly over time)

### Manual Trigger

You can manually trigger the workflow for testing:

1. Go to **Actions** tab in GitHub
2. Select **Daily Trading Bot** workflow
3. Click **Run workflow** → **Run workflow**

This is useful for:
- Testing the setup
- Running on weekends/holidays
- Checking for signals outside the normal schedule

## Monitoring

### Check Workflow Status

1. Go to **Actions** tab in your repository
2. View recent workflow runs
3. Click on a run to see detailed logs

### View Logs

Each run uploads logs as artifacts:
- `logs-{run-number}`: Contains `crossover_events.log`
- Available for 30 days after the run

### Check Trading Status

The workflow displays current status at the end of each run:
- Current MA5 and MA30 values
- Bullish/Bearish status
- Recent signals

## Troubleshooting

### Workflow Fails on First Run

**Cause**: No database artifact exists yet.

**Solution**: This is normal. The workflow has `continue-on-error: true` for database download. It will create a new database and work properly on subsequent runs.

### Email Not Sending

**Check**:
1. Verify all email secrets are set correctly
2. Ensure `TQQQ_EMAIL_ENABLED=true`
3. Confirm Gmail app password is correct (16 characters, no spaces)
4. Check if 2-Step Verification is enabled on Gmail account

### Database Growing Too Large

**Current Size**: ~500KB (1,500+ records per ticker)

**If it exceeds artifact limits** (rare):
- Consider committing database to repository instead
- Or use database pruning to keep only recent N months

### Workflow Not Running

**Check**:
1. Verify the workflow file is in `.github/workflows/`
2. Ensure it's pushed to the default branch
3. Check repository settings allow Actions
4. Note: Scheduled workflows only run on default branch

## Schedule Details

- **Run Time**: 9:00 AM ET (14:00 UTC)
- **Days**: Monday-Friday only (no weekends)
- **Timezone**: Converts to UTC for cron schedule
- **Market Hours**: NYSE opens at 9:30 AM ET, this runs at market open

### Adjusting Schedule

To change the run time, edit the cron expression in `.github/workflows/daily-trading-bot.yml`:

```yaml
- cron: '0 14 * * 1-5'  # Format: minute hour day month weekday
```

Examples:
- `0 13 * * 1-5`: 8:00 AM ET (13:00 UTC)
- `0 14 * * 1-5`: 9:00 AM ET (14:00 UTC) - current setting
- `0 15 * * 1-5`: 10:00 AM ET (15:00 UTC)
- `0 21 * * 1-5`: 4:00 PM ET (21:00 UTC) - market close

**Tip**: Use https://crontab.guru/ to help with cron syntax

## Cost

GitHub Actions is **FREE** for public repositories with generous limits:
- 2,000 minutes/month for free accounts
- 3,000 minutes/month for Pro accounts
- This workflow uses ~2-5 minutes per run
- Running Mon-Fri = ~20 runs/month = ~100 minutes/month

**Well within free tier limits!**

## Migration from Local/Server

If you were running this locally or on a server:

1. The database will be rebuilt from Yahoo Finance history
2. Existing signals will be re-detected (no duplicates, see `get_new_signals()`)
3. Email notifications will only be sent for NEW signals
4. You can safely delete the local cron job once GitHub Actions is working

## Next Steps

1. ✓ Push the workflow file to GitHub
2. ✓ Configure GitHub Secrets
3. ✓ Manually trigger the workflow to test
4. ✓ Verify email notification received
5. ✓ Let it run automatically daily

## Support

If you encounter issues:
- Check the **Actions** tab for detailed error logs
- Review the uploaded logs artifacts
- Ensure all secrets are configured correctly
- Test email settings locally first with `./run.sh`
