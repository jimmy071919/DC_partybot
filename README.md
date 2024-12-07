# Discord Party Bot - Railway Deployment Guide

## Prerequisites
- Railway Account
- GitHub Repository
- Discord Bot Token

## Deployment Steps
1. Connect your GitHub repository to Railway
2. Set the following environment variables in Railway:
   - `DISCORD_TOKEN`: Your Discord Bot Token
   - Other sensitive configuration variables from `.env`

## Local Development
```bash
# Install dependencies
pip install -r requirements.txt

# Run the bot
python main.py
```

## Railway Configuration
- Build: Uses Nixpacks for dependency management
- Runtime: Python 3.11
- Key Dependencies: FFmpeg, Discord.py, yt-dlp

## Troubleshooting
- Ensure all environment variables are correctly set
- Check Railway logs for any deployment issues
- Verify Discord bot permissions and intents
