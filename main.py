import discord
from discord import app_commands
from typing import Optional
import config
from services.tweet_generator import TweetGenerator
from services.scheduler import TweetScheduler
import logging
from functools import wraps

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

def check_channel():
    """Decorator to check if command is used in the allowed channels"""
    async def predicate(interaction: discord.Interaction) -> bool:
        if not config.ALLOWED_CHANNELS:
            # If no channels are set, allow the command everywhere
            return True
            
        if interaction.channel_id not in config.ALLOWED_CHANNELS:
            # Format the channel mentions
            allowed_channels = ', '.join(f'<#{channel_id}>' for channel_id in config.ALLOWED_CHANNELS)
            logger.info(
                f"Command attempted in unauthorized channel {interaction.channel_id} "
                f"by user {interaction.user} (ID: {interaction.user.id})"
            )
            await interaction.response.send_message(
                f"This command can only be used in the following channels: {allowed_channels}",
                ephemeral=True
            )
            return False
        return True
    return app_commands.check(predicate)

class TweetBot(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        
        self.tree = app_commands.CommandTree(self)
        self.tweet_generator = TweetGenerator()
        self.scheduler = TweetScheduler()
        
        # Set up error handler for the command tree
        self.tree.on_error = self.on_tree_error
        logger.info("TweetBot initialized")

    async def setup_hook(self):
        logger.info("Registering commands...")
        if hasattr(config, 'DISCORD_GUILD_ID'):
            guild = discord.Object(id=int(config.DISCORD_GUILD_ID))
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            logger.info(f"Commands registered for guild ID: {config.DISCORD_GUILD_ID}")
        else:
            await self.tree.sync()
            logger.info("Commands registered globally")

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        if config.ALLOWED_CHANNELS:
            logger.info(f'Commands restricted to channels: {config.ALLOWED_CHANNELS}')
        logger.info('------')

    async def on_tree_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handle command errors gracefully"""
        if isinstance(error, app_commands.errors.CheckFailure):
            # This error is already handled in the check_channel decorator
            logger.info(
                f"CheckFailure handled: User {interaction.user} "
                f"attempted to use command in channel {interaction.channel_id}"
            )
            return
            
        # Handle other errors
        logger.error(f"Command error: {str(error)}", exc_info=True)
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(
                    "An error occurred while processing your command.",
                    ephemeral=True
                )
        except Exception as e:
            logger.error(f"Error sending error message: {str(e)}")

client = TweetBot()

@client.tree.command(
    name="create",
    description="Create a tweet thread draft"
)
@app_commands.describe(
    main="TLDR of what to introduce (partnership, sponsorship, etc.)",
    context="Special requirements, information dump, or partner intro",
    keywords="Key words that must be mentioned (comma-separated)",
    tag="Optional: X accounts to be mentioned (comma-separated)",
    length="Approximate number of tweets in thread"
)
@check_channel()
async def create(
    interaction: discord.Interaction,
    main: str,
    context: str,
    keywords: str,
    length: int,
    tag: Optional[str] = None
):
    await interaction.response.defer()
    logger.info(f"Received /create command from {interaction.user} (ID: {interaction.user.id})")
    logger.info(f"Parameters: main='{main}', keywords='{keywords}', length={length}, tag={tag}")

    try:
        # Prepare request data
        request = {
            'main': main,
            'context': context,
            'keywords': [k.strip() for k in keywords.split(',')],
            'tag': [t.strip() for t in tag.split(',')] if tag else [],
            'length': length
        }
        
        # Generate tweets
        tweets = client.tweet_generator.generate_thread(request)
        logger.info(f"Generated {len(tweets)} tweets successfully")

        # Create draft on Typefully
        logger.info("Creating draft on Typefully...")
        typefully_url = client.scheduler.schedule_thread(tweets)
        logger.info(f"Draft created successfully: {typefully_url}")

        # Create response embed
        embed = discord.Embed(
            title="Tweet Thread Draft Created!",
            description="Your tweet thread has been generated and saved as a draft.",
            color=discord.Color.green()
        )
        embed.add_field(name="Number of Tweets", value=str(len(tweets)), inline=True)
        embed.add_field(name="View on Typefully", value=typefully_url, inline=False)
        embed.set_footer(text="You can edit and schedule this draft on Typefully")

        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        logger.error(f"Error processing /create command: {str(e)}")
        error_embed = discord.Embed(
            title="Error",
            description=f"Failed to create tweet thread: {str(e)}",
            color=discord.Color.red()
        )
        await interaction.followup.send(embed=error_embed)

def main():
    client.run(config.DISCORD_TOKEN)

if __name__ == "__main__":
    main()
