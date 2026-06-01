import discord
from discord.ext import commands
import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import os
from dotenv import load_dotenv

# Imports de nos propres fichiers
from tv_engine import generate_tradingview_alert
from keep_alive import keep_alive

# Charger l'environnement
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Configuration Discord
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)
analyzer = SentimentIntensityAnalyzer()

@bot.event
async def on_ready():
    print(f'✅ Bot en ligne ! Connecté en tant que {bot.user}')
    await bot.change_presence(activity=discord.Game(name="!analyze <ticker>"))

@bot.command()
async def analyze(ctx, ticker: str):
    ticker = ticker.upper()
    await ctx.send(f"🔍 *Analyse algorithmique en cours pour **{ticker}**...*")
    
    try:
        # Récupérer l'action
        stock = yf.Ticker(ticker)
        info = stock.info
        company_name = info.get('shortName', ticker)
        
        # Analyser les news
        news_list = stock.news
        if not news_list:
            await ctx.send(f"❌ Aucune actualité pertinente trouvée pour {ticker}.")
            return
            
        latest_news = news_list[0]['title']
        
        # IA Sentiment (Vader)
        sentiment_score = analyzer.polarity_scores(latest_news)['compound']
        trend = "BULLISH" if sentiment_score >= 0.05 else "BEARISH"
        
        # Générer l'image
        image_path = generate_tradingview_alert(ticker, company_name, trend, latest_news)
        
        # Envoyer sur Discord
        with open(image_path, 'rb') as f:
            picture = discord.File(f, filename=f"{ticker}_alert.png")
            embed_msg = f"📊 **ANALYSE COMPLÈTE : {company_name} ({ticker})**\n> 🗞️ *{latest_news}*"
            await ctx.send(content=embed_msg, file=picture)
            
    except Exception as e:
        await ctx.send(f"⚠️ Erreur lors de l'analyse : `{e}`")

if __name__ == "__main__":
    if not TOKEN:
        print("❌ ERREUR : DISCORD_TOKEN introuvable. Configure les variables d'environnement.")
    else:
        keep_alive() # Démarre le serveur anti-sommeil
        bot.run(TOKEN)
