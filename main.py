import discord
from discord import app_commands
from typing import Optional
import config
from services.tweet_generator import TweetGenerator
from services.scheduler import TweetScheduler

class TweetBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)
        self.tweet_generator = TweetGenerator()
        self.scheduler = TweetScheduler()

    async def setup_hook(self):
        await self.tree.sync()

client = TweetBot()

@client.tree.command(name="create", description="Create and schedule a tweet thread")
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

        # Schedule tweets
        typefully_url = client.scheduler.schedule_thread(tweets, deadline)

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

    except Exception as e:
        await interaction.followup.send(
            f"Error occurred: {str(e)}",
            ephemeral=True
        )

def main():
    client.run(config.DISCORD_TOKEN)

if __name__ == "__main__":
    main()
