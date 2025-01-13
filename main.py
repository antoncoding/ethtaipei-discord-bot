import logging
import discord
from discord import app_commands
from typing import Optional
import config
from services.tweet_generator import TweetGenerator
from services.scheduler import TweetScheduler

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

client = TweetBot()

@client.tree.command(
    name="draft",
    description="Create a tweet thread draft with interactive preview"
)
@app_commands.describe(
    main="TLDR of what to introduce (partnership, sponsorship, etc.)",
    context="Special requirements, information dump, or partner intro",
    keywords="Key words that must be mentioned (comma-separated)",
    tag="Optional: X accounts to be mentioned (comma-separated)",
    length="Approximate number of tweets in thread (1-10)",
    tone="Optional: Tone of the tweets (default: normal)",
    link="Optional: Link to attach to the last tweet"
)
@app_commands.choices(tone=[
    app_commands.Choice(name="Intern Style", value="intern"),
    app_commands.Choice(name="Normal", value="normal"),
    app_commands.Choice(name="Marketing", value="marketing"),
])
@check_channel()
async def draft(
    interaction: discord.Interaction,
    main: str,
    context: str,
    keywords: str,
    length: int,
    tag: Optional[str] = None,
    tone: Optional[str] = "normal",
    link: Optional[str] = None
):
    try:
        # Validate inputs before deferring
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

        # Now that inputs are validated, defer the response
        await interaction.response.defer(thinking=True)
        
        logger.info(f"Received /draft command from {interaction.user} (ID: {interaction.user.id})")
        logger.info(f"Parameters: main='{main}', keywords='{keywords}', length={length}, tag={tag}, tone={tone}, link={link}")

        # Generate initial thread
        request = {
            "main": main,
            "context": context,
            "keywords": keywords,
            "tag": tag,
            "length": length,
            "tone": tone,
            "link": link
        }
        
        # Generate the tweets
        tweets = client.tweet_generator.generate_thread(request)
        
        # Create the preview message with buttons
        preview = discord.Embed(
            title="Tweet Thread Preview",
            description="Here's your draft tweet thread. Use the buttons below to provide feedback or finalize.",
            color=discord.Color.blue()
        )
        
        # Add tweets to the preview
        for i, tweet in enumerate(tweets, 1):
            preview.add_field(
                name=f"Tweet {i}",
                value=tweet,
                inline=False
            )
            
        # Create buttons
        view = TweetPreviewView(tweets, request, interaction.user.id, client.tweet_generator, client.scheduler)
        
        # Edit the original response with the preview
        await interaction.edit_original_response(embed=preview, view=view)
        
    except Exception as e:
        logger.error(f"Error in /draft command: {str(e)}", exc_info=True)
        error_msg = "Sorry, something went wrong while creating your tweet thread. Please try again."
        
        try:
            # If we haven't responded yet, send an ephemeral message
            if not interaction.response.is_done():
                await interaction.response.send_message(error_msg, ephemeral=True)
            else:
                # If we've already responded, use followup
                await interaction.followup.send(error_msg, ephemeral=True)
        except:
            # Last resort: try to send a message to the channel
            if interaction.channel:
                await interaction.channel.send(
                    f"{interaction.user.mention} {error_msg}",
                    delete_after=10
                )

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
        # Create modal for feedback
        modal = TweetFeedbackModal(self.tweets, self.request, self.tweet_generator)
        await interaction.response.send_modal(modal)
        
    @discord.ui.button(label="Finalize & Post to Typefully", style=discord.ButtonStyle.success)
    async def finalize_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        try:
            # Post to Typefully
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
            # Acknowledge the interaction first and show loading state
            await interaction.response.defer(thinking=True)
            
            # Add feedback to the context and regenerate
            new_context = f"{self.request['context']}\n\nFeedback: {self.feedback.value}"
            self.request['context'] = new_context
            
            # Generate new thread
            new_tweets = self.tweet_generator.generate_thread(self.request)
            
            # Create a completely new embed
            new_preview = discord.Embed(
                title="Updated Tweet Thread Preview",
                description="Thread has been updated based on your feedback. Use the buttons below to provide more feedback or finalize.",
                color=discord.Color.green()
            )
            
            # Add new tweets to the fresh embed
            for i, tweet in enumerate(new_tweets, 1):
                new_preview.add_field(
                    name=f"Tweet {i}",
                    value=tweet,
                    inline=False
                )
            
            # Create new view with fresh buttons
            new_view = TweetPreviewView(new_tweets, self.request, interaction.user.id, self.tweet_generator, client.scheduler)
            
            # Use interaction.followup.edit_message to edit the original message
            original_message = await interaction.original_response()
            await interaction.followup.edit_message(message_id=original_message.id, embed=new_preview, view=new_view)
            
        except Exception as e:
            logger.error(f"Error processing feedback: {str(e)}", exc_info=True)
            await interaction.followup.send(
                "Sorry, something went wrong while processing your feedback. Please try again.",
                ephemeral=True
            )

def main():
    client.run(config.DISCORD_TOKEN)

if __name__ == '__main__':
    main()
