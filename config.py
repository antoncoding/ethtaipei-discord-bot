import os
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Discord Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# Get allowed channels as a list
DISCORD_CHANNEL_IDS = os.getenv('DISCORD_CHANNEL_IDS', '').strip()
ALLOWED_CHANNELS = [int(channel_id.strip()) for channel_id in DISCORD_CHANNEL_IDS.split(',') if channel_id.strip()]

# OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Typefully Configuration
TYPEFULLY_API_KEY = os.getenv('TYPEFULLY_API_KEY')

# Bot Configuration
COMMAND_PREFIX = '/'

# List of user IDs that can use admin commands
ADMIN_IDS = ['your_discord_user_id']  # Replace with your Discord user ID

# Log loaded configuration (without sensitive values)
logger.info("Configuration loaded:")
logger.info(f"DISCORD_TOKEN: {'Set' if DISCORD_TOKEN else 'Not set'}")

logger.info(f"ALLOWED_CHANNELS: {ALLOWED_CHANNELS if ALLOWED_CHANNELS else 'Not set (all channels allowed)'}")
logger.info(f"OPENAI_API_KEY: {'Set' if OPENAI_API_KEY else 'Not set'}")
logger.info(f"TYPEFULLY_API_KEY: {'Set' if TYPEFULLY_API_KEY else 'Not set'}")
logger.info(f"COMMAND_PREFIX: {COMMAND_PREFIX}")

# Validate required configuration
if not DISCORD_TOKEN:
    raise ValueError("DISCORD_TOKEN is not set in environment variables")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY is not set in environment variables")
if not TYPEFULLY_API_KEY:
    raise ValueError("TYPEFULLY_API_KEY is not set in environment variables")
