import discord
from discord import app_commands
from discord.ext import commands

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(
        name="ping",
        description="verifies if the bot is answering"
    )
    async def ping(self, interaction: discord.Interaction):
        time=round(self.bot.latency * 1000)
        await interaction.response.send_message(f"pong! {time} ms")

async def setup(bot):
    await bot.add_cog(General(bot))