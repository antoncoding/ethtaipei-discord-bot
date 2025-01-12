import os
from dotenv import load_dotenv

load_dotenv()

# Discord Configuration
DISCORD_TOKEN = os.getenv('DISCORD_TOKEN')

# OpenAI Configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Typefully Configuration
TYPEFULLY_API_KEY = os.getenv('TYPEFULLY_API_KEY')

# Bot Configuration
COMMAND_PREFIX = '/'
