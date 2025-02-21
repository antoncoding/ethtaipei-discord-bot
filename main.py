import logging
import discord
from discord import app_commands
from typing import Optional
import config
from services.tweet_generator import TweetGenerator
from services.scheduler import TweetScheduler
from aiohttp import web
import asyncio
import os

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
        # Set up all required intents
        intents = discord.Intents.default()
        intents.message_content = True
        intents.messages = True
        intents.guild_messages = True
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
        
        # Register commands
        self.setup_commands()
        logger.info("TweetBot initialized")
        self.active_previews = {}  # Store active preview sessions

    def setup_commands(self):
        """Setup all bot commands"""
        
        @self.tree.command(name="ping", description="Test if the bot is working")
        @check_channel()
        async def ping(interaction: discord.Interaction):
            await interaction.response.send_message("Pong! 🏓")

        @self.tree.command(
            name="create",
            description="Create a tweet or thread draft"
        )
        @app_commands.describe(
            main="TLDR of what to introduce (partnership, sponsorship, etc.)",
            context="Special requirements, information dump, or partner intro",
            keywords="Key words that must be mentioned (comma-separated)",
            tone="The tone of the tweets",
            tag="Optional: X accounts to be mentioned (comma-separated)",
            length="Number of tweets in thread (use 1 for single tweet)",
            link="Optional: Link to be included in the thread"
        )
        @app_commands.choices(tone=[
            app_commands.Choice(name="Normal", value="normal"),
            app_commands.Choice(name="Intern", value="intern"),
            app_commands.Choice(name="Marketing", value="marketing")
        ])
        @check_channel()
        async def create(
            interaction: discord.Interaction,
            main: str,
            context: str,
            keywords: str,
            length: int,
            tone: app_commands.Choice[str],
            tag: Optional[str] = None,
            link: Optional[str] = None
        ):
            try:
                # Validate inputs
                if not main or not context or not keywords:
                    await interaction.response.send_message(
                        "❌ Please provide all required fields: main topic, context, and keywords.",
                        ephemeral=True
                    )
                    return

                if length < 1 or length > 10:
                    await interaction.response.send_message(
                        "❌ Thread length must be between 1 and 10 tweets.",
                        ephemeral=True
                    )
                    return

                await interaction.response.defer(thinking=True)
                logger.info(f"Received /create command from {interaction.user} (ID: {interaction.user.id})")
                logger.info(f"Parameters: main='{main}', keywords='{keywords}', length={length}, tone={tone.value}, tag={tag}, link={link}")

                # Prepare request data
                request = {
                    'main': main,
                    'context': context,
                    'keywords': [k.strip() for k in keywords.split(',')],
                    'tags': [t.strip() for t in tag.split(',')] if tag else [],
                    'length': length,
                    'tone': tone.value,
                    'link': link
                }

                # Generate tweets
                tweets = self.tweet_generator.generate_thread(request)
                logger.info(f"Generated {len(tweets)} tweets successfully")

                # Create preview embed
                preview = discord.Embed(
                    title="Tweet Thread Preview",
                    description="Here's your draft tweet thread. Use the buttons below to provide feedback or finalize.",
                    color=discord.Color.blue()
                )

                # Add tweets to preview
                for i, tweet in enumerate(tweets, 1):
                    preview.add_field(
                        name=f"Tweet {i}",
                        value=tweet,
                        inline=False
                    )

                # Create buttons view
                view = TweetPreviewView(
                    tweets=tweets,
                    request=request,
                    user_id=interaction.user.id,
                    tweet_generator=self.tweet_generator,
                    scheduler=self.scheduler
                )

                await interaction.followup.send(embed=preview, view=view)

            except Exception as e:
                logger.error(f"Error in /create command: {str(e)}", exc_info=True)
                error_embed = discord.Embed(
                    title="Error",
                    description="Failed to create tweet draft. Please try again.",
                    color=discord.Color.red()
                )
                
                if not interaction.response.is_done():
                    await interaction.response.send_message(embed=error_embed, ephemeral=True)
                else:
                    await interaction.followup.send(embed=error_embed, ephemeral=True)

    async def setup_hook(self):
        """Register commands globally"""
        logger.info("Registering commands...")
        
        try:
            # Clear the commands first
            self.tree.clear_commands(guild=None)
            
            # Register commands
            self.setup_commands()
            
            if hasattr(config, 'DISCORD_GUILD_ID'):
                guild = discord.Object(id=int(config.DISCORD_GUILD_ID))
                self.tree.copy_global_to(guild=guild)
                await self.tree.sync(guild=guild)
                logger.info(f"Commands registered for guild ID: {config.DISCORD_GUILD_ID}")
            else:
                await self.tree.sync()
                logger.info("Commands registered globally")
        except Exception as e:
            logger.error(f"Failed to register commands: {str(e)}", exc_info=True)
            
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
        port = int(os.getenv("PORT", "8000"))
        site = web.TCPSite(runner, '0.0.0.0', port)
        await site.start()
        logger.info(f"Health check endpoint started on port {port}")

class TweetPreviewView(discord.ui.View):
    def __init__(self, tweets, request, user_id, tweet_generator, scheduler):
        super().__init__(timeout=600)  # 10 minute timeout
        self.tweets = tweets
        self.request = request
        self.user_id = user_id
        self.tweet_generator = tweet_generator
        self.scheduler = scheduler
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id
        
    @discord.ui.button(label="Provide Feedback", style=discord.ButtonStyle.primary)
    async def feedback_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = TweetFeedbackModal(self.tweets, self.request, self.tweet_generator)
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="Finalize & Post to Typefully", style=discord.ButtonStyle.success)
    async def finalize_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        try:
            draft_url = self.scheduler.schedule_thread(self.tweets)
            
            await interaction.followup.send(
                f"✅ Thread has been finalized and posted to Typefully!\n📝 Edit your thread here: {draft_url}",
                ephemeral=True
            )
            
            # Disable all buttons
            for child in self.children:
                child.disabled = True
            await interaction.message.edit(view=self)
            
        except Exception as e:
            logger.error(f"Error finalizing thread: {str(e)}", exc_info=True)
            await interaction.followup.send(
                "Sorry, something went wrong while posting to Typefully. Please try again.",
                ephemeral=True
            )

class TweetFeedbackModal(discord.ui.Modal, title="Tweet Thread Feedback"):
    feedback = discord.ui.TextInput(
        label="Your Feedback",
        style=discord.TextStyle.paragraph,
        placeholder="Please provide your feedback or suggestions for the tweet thread...",
        required=True,
        max_length=1000
    )
    
    def __init__(self, tweets, request, tweet_generator):
        super().__init__()
        self.tweets = tweets
        self.request = request
        self.tweet_generator = tweet_generator
        
    async def on_submit(self, interaction: discord.Interaction):
        try:
            await interaction.response.defer(thinking=True)
            
            # Format original tweets for context
            original_tweets = "\n".join([f"Tweet {i+1}: {tweet}" for i, tweet in enumerate(self.tweets)])
            
            # Add feedback to context
            feedback_context = (
                f"Original thread:\n{original_tweets}\n\n"
                f"User feedback: {self.feedback.value}\n\n"
                f"Please improve the thread based on this feedback while maintaining the original message and style."
            )
            
            # Update request with feedback
            self.request['context'] = f"{self.request['context']}\n\n{feedback_context}"
            
            # Generate new thread
            new_tweets = self.tweet_generator.generate_thread(self.request)
            
            # Create new preview
            new_preview = discord.Embed(
                title="Updated Tweet Thread Preview",
                description=f"Thread has been updated based on your feedback:\n> {self.feedback.value}",
                color=discord.Color.green()
            )
            
            for i, tweet in enumerate(new_tweets, 1):
                new_preview.add_field(
                    name=f"Tweet {i}",
                    value=tweet,
                    inline=False
                )
            
            # Create new view
            new_view = TweetPreviewView(
                tweets=new_tweets,
                request=self.request,
                user_id=interaction.user.id,
                tweet_generator=self.tweet_generator,
                scheduler=interaction.client.scheduler
            )
            
            # Update the message
            await interaction.edit_original_response(embed=new_preview, view=new_view)
            
        except Exception as e:
            logger.error(f"Error processing feedback: {str(e)}", exc_info=True)
            await interaction.followup.send(
                "Sorry, something went wrong while processing your feedback. Please try again.",
                ephemeral=True
            )

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
