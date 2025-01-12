# Tweet Scheduler Discord Bot

A Discord bot that generates and schedules tweet threads using OpenAI and Typefully.

## Features

- Generate tweet threads with GPT-4
- Automatic scheduling via Typefully
- Customizable parameters (keywords, mentions, deadline)
- Easy-to-use Discord slash commands

## Setup

1. Clone this repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with the following variables:
```
DISCORD_TOKEN=your_discord_bot_token
OPENAI_API_KEY=your_openai_api_key
TYPEFULLY_API_KEY=your_typefully_api_key
```

4. Run the bot:
```bash
python main.py
```

## Usage

Use the `/create` command with the following parameters:
- `main`: Main topic/TLDR
- `context`: Additional context/requirements
- `keywords`: Must-mention keywords (comma-separated)
- `tag`: X accounts to mention (comma-separated)
- `deadline`: When to post (e.g., "2024-01-15T14:30:00+08:00")
- `length`: Approximate number of tweets in thread

## Deployment

For production deployment:

1. Set up a server (e.g., AWS EC2, DigitalOcean Droplet)
2. Install Python 3.8+ and required dependencies
3. Set up environment variables
4. Use a process manager like PM2 or systemd to keep the bot running:

Example systemd service file (`/etc/systemd/system/tweetbot.service`):
```ini
[Unit]
Description=Tweet Scheduler Discord Bot
After=network.target

[Service]
Type=simple
User=your_user
WorkingDirectory=/path/to/bot
Environment=PYTHONUNBUFFERED=1
ExecStart=/usr/bin/python3 main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

Then enable and start the service:
```bash
sudo systemctl enable tweetbot
sudo systemctl start tweetbot
```
