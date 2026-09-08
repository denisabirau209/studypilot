import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv() #looks for the .env file and accesses the variables
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))

intents = discord.Intents.default()
intents.members = True

class StudyPilot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        #loads all the features from the cogs/ file
        #runs once before the bot connects
        for file in os.listdir("./cogs"):
            if file.endswith(".py") and not file.startswith("_"):
                await self.load_extension(f"cogs.{file[:-3]}")
        #command sync
        guild = discord.Object(id=GUILD_ID)
        self.tree.copy_global_to(guild=guild)
        await self.tree.sync(guild=guild)
        print("[sync] commands synced")


    async def on_ready(self):
        print(f"[ready] {self.user} has connected to Discord!")

bot = StudyPilot()
bot.run(TOKEN)
