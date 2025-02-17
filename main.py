import logging
import discord
from discord import app_commands
from typing import Optional
import config
from services.tweet_generator import TweetGenerator
from services.scheduler import TweetScheduler
from aiohttp import web
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def check_channel():
    """Decorator to check if command is used in the allowed channels"""
    async def predicate(interaction: discord.Interaction):
        allowed_channels = list(map(int, config.DISCORD_CHANNEL_IDS.split(',')))
        if interaction.channel_id not in allowed_channels:
            await interaction.response.send_message(
                "❌ This command can only be used in designated channels.",
                ephemeral=True
            )
            return False
        return True
    return app_commands.check(predicate)

class TweetBot(discord.Client):
    def __init__(self):
        # Set up all required intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.guild_messages = True
        intents.message_content = True
        intents.guilds = True
        super().__init__(intents=intents)
        
        self.tree = app_commands.CommandTree(self)
        self.tweet_generator = TweetGenerator()
        self.scheduler = TweetScheduler()
        
        # Set up error handler for the command tree
        self.tree.on_error = self.on_tree_error
        
        # Add web app
        self.web_app = web.Application()
        self.web_app.router.add_get('/', self.handle_healthcheck)
        logger.info("TweetBot initialized")

    async def setup_hook(self):
        """Register commands globally"""
        logger.info("Registering commands...")
        
        try:
            # Sync commands globally
            await self.tree.sync()
            logger.info("Commands registered globally")
        except Exception as e:
            logger.error(f"Failed to register commands: {str(e)}")
            
        logger.info("Command registration completed")

    async def on_ready(self):
        logger.info(f'Logged in as {self.user} (ID: {self.user.id})')
        logger.info('------')

    async def on_tree_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handle command errors gracefully"""
        logger.error(f"Error in {interaction.command.name} command: {str(error)}", exc_info=True)
        
        if isinstance(error, app_commands.errors.CheckFailure):
            # This is handled by the check_channel decorator
            return
            
        error_embed = discord.Embed(
            title="❌ Error",
            description="An unexpected error occurred while processing your command. Please try again later.",
            color=discord.Color.red()
        )
        
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(embed=error_embed, ephemeral=True)
            else:
                await interaction.followup.send(embed=error_embed, ephemeral=True)
        except discord.errors.NotFound:
            # If interaction is no longer valid, log it but don't try to respond
            logger.warning("Could not respond to interaction - interaction token may have expired")
        except Exception as e:
            logger.error(f"Error while sending error message: {str(e)}", exc_info=True)

    async def handle_healthcheck(self, request):
        """Handle healthcheck requests"""
        return web.Response(text="OK", status=200)

    async def start_web_server(self):
        """Start the web server"""
        runner = web.AppRunner(self.web_app)
        await runner.setup()
        site = web.TCPSite(runner, '0.0.0.0', 8000)
        await site.start()
        logger.info("Health check endpoint started on port 8000")

def main():
    # Create the client
    bot = TweetBot()
    
    # Set up the event loop
    loop = asyncio.get_event_loop()
    
    # Start both the Discord bot and web server
    loop.create_task(bot.start_web_server())
    loop.run_until_complete(bot.start(config.DISCORD_TOKEN))

if __name__ == '__main__':
    main()
