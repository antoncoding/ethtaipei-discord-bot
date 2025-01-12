import discord
from discord import app_commands
from typing import Optional
import config
from services.tweet_generator import TweetGenerator
from services.scheduler import TweetScheduler
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TweetBot(discord.Client):
    def __init__(self):
        # Initialize with necessary intents
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        
        self.tree = app_commands.CommandTree(self)
        self.tweet_generator = TweetGenerator()
        self.scheduler = TweetScheduler()
        logger.info("TweetBot initialized")

    async def setup_hook(self):
        # This is called when the bot starts
        logger.info("Registering commands...")
        # If you have a specific guild/server, use this line (replace YOUR_GUILD_ID):
        if hasattr(config, 'DISCORD_GUILD_ID'):
            guild = discord.Object(id=int(config.DISCORD_GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info(f"Commands registered for guild ID: {config.DISCORD_GUILD_ID}")
        else:
            # This will sync commands globally
            await self.tree.sync()
            logger.info("Commands registered globally")
        logger.info("Command registration complete!")

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info('------')

client = TweetBot()

@client.tree.command(
    name="create",
    description="Create and schedule a tweet thread"
)
@app_commands.describe(
    main="TLDR of what to introduce (partnership, sponsorship, etc.)",
    context="Special requirements, information dump, or partner intro",
    keywords="Key words that must be mentioned (comma-separated)",
    tag="X accounts to be mentioned (comma-separated)",
    deadline="Latest time to post (e.g., 2025-01-13T10:00:00+08:00)",
    length="Approximate number of tweets in thread"
)
async def create(
    interaction: discord.Interaction,
    main: str,
    context: str,
    keywords: str,
    tag: str,
    deadline: str,
    length: int
):
    await interaction.response.defer()
    logger.info(f"Received /create command from {interaction.user} (ID: {interaction.user.id})")
    logger.info(f"Parameters: main='{main}', keywords='{keywords}', length={length}")

    try:
        # Prepare request data
        request = {
            'main': main,
            'context': context,
            'keywords': [k.strip() for k in keywords.split(',')],
            'tag': [t.strip() for t in tag.split(',')],
            'deadline': deadline,
            'length': length
        }
        
        # Generate tweets
        tweets = client.tweet_generator.generate_thread(request)
        logger.info(f"Generated {len(tweets)} tweets successfully")

        # Schedule tweets
        logger.info("Scheduling tweets on Typefully...")
        typefully_url = client.scheduler.schedule_thread(tweets, deadline)
        logger.info(f"Tweets scheduled successfully: {typefully_url}")

        # Create response embed
        embed = discord.Embed(
            title="Tweet Thread Scheduled!",
            color=discord.Color.green()
        )
        embed.add_field(name="Main Topic", value=main, inline=False)
        embed.add_field(name="Deadline", value=deadline, inline=True)
        embed.add_field(name="Thread Length", value=str(len(tweets)), inline=True)
        embed.add_field(name="Preview Link", value=typefully_url, inline=False)

        # Add preview of first tweet
        if tweets:
            embed.add_field(name="First Tweet Preview", value=tweets[0], inline=False)

        await interaction.followup.send(embed=embed)
        logger.info("Response sent to user")

    except Exception as e:
        logger.error(f"Error processing /create command: {str(e)}", exc_info=True)
        await interaction.followup.send(
            f"Error occurred: {str(e)}",
            ephemeral=True
        )

def main():
    logger.info("Bot is starting...")
    client.run(config.DISCORD_TOKEN)

if __name__ == "__main__":
    main()
