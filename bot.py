import discord
from discord.ext import commands
import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import os
from dotenv import load_dotenv

# Import du générateur et du système anti-sommeil
from tv_engine import generate_tradingview_alert
from keep_alive import keep_alive  # <-- AJOUT ICI

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
analyzer = SentimentIntensityAnalyzer()

@bot.event
async def on_ready():
    print(f'✅ Bot en ligne ! Connecté en tant que {bot.user}')
    await bot.change_presence(activity=discord.Game(name="Analyser Wall Street 📈"))

# ... (Ici, tu laisses ta commande @bot.command() analyze intacte) ...

if __name__ == "__main__":
    if not TOKEN:
        print("❌ ERREUR : DISCORD_TOKEN introuvable.")
    else:
        keep_alive()  # <-- AJOUT ICI : Démarre le serveur web en arrière-plan
        bot.run(TOKEN)
