import discord
from discord import app_commands
import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import os

from tv_engine import generate_tradingview_alert

# Initialisation du bot
class MyBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync() # Synchronise les Slash Commands avec Discord

bot = MyBot()
analyzer = SentimentIntensityAnalyzer()

@bot.event
async def on_ready():
    print(f'✅ Bot connecté en tant que {bot.user}')
    await bot.change_presence(activity=discord.Game(name="/analyze <ticker>"))

@bot.tree.command(name="analyze", description="Génère une analyse graphique et sentimentale pour une action (ex: TSLA, AAPL, BTC-USD)")
@app_commands.describe(ticker="Le symbole de l'action ou crypto (ex: TSLA)")
async def analyze(interaction: discord.Interaction, ticker: str):
    ticker = ticker.upper()
    
    # Indique à Discord que le bot "réfléchit" (évite le message d'erreur d'attente)
    await interaction.response.defer()
    
    try:
        # Récupération des données financières
        stock = yf.Ticker(ticker)
        info = stock.info
        company_name = info.get('shortName', ticker)
        
        # Récupération des news
        news_list = stock.news
        if not news_list:
            await interaction.followup.send(f"❌ Aucune actualité récente trouvée pour `{ticker}`.")
            return
            
        latest_news = news_list[0]['title']
        
        # Analyse IA du sentiment
        sentiment_score = analyzer.polarity_scores(latest_news)['compound']
        trend = "BULLISH" if sentiment_score >= 0.05 else "BEARISH"
        
        # Génération de l'image
        image_path = generate_tradingview_alert(ticker, company_name, trend, latest_news)
        
        # Envoi de la réponse finale avec l'image
        with open(image_path, 'rb') as f:
            picture = discord.File(f, filename=f"{ticker}_alert.png")
            embed_msg = f"📊 **ANALYSE : {company_name} ({ticker})**\n> 🗞️ *{latest_news}*"
            await interaction.followup.send(content=embed_msg, file=picture)
            
    except Exception as e:
        await interaction.followup.send(f"⚠️ Erreur lors de l'analyse du ticker `{ticker}`. Existe-t-il vraiment ?")

if __name__ == "__main__":
    # Récupération sécurisée du token via les GitHub Secrets
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        print("❌ ERREUR CRITIQUE : DISCORD_TOKEN introuvable.")
    else:
        bot.run(TOKEN)
