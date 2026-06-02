import discord
from discord import app_commands
import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import os

from ui_engine import generate_dashboard_image, generate_intel_image

WATCHLIST_MARKET = ["NVDA", "AAPL", "MSFT", "TSLA", "AMZN", "META", "GOOGL", "AMD"]
WATCHLIST_CRYPTO = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "ADA-USD", "AVAX-USD", "DOGE-USD"]

class TradingBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

bot = TradingBot()
analyzer = SentimentIntensityAnalyzer()

def get_live_data(watchlist):
    """Télécharge les données pour un tableau de bord."""
    data = []
    for sym in watchlist:
        try:
            tkr = yf.Ticker(sym)
            hist = tkr.history(period="7d")
            if len(hist) >= 2:
                close_prev = hist['Close'].iloc[-2]
                close_curr = hist['Close'].iloc[-1]
                pct = ((close_curr - close_prev) / close_prev) * 100
                hist_7d = hist['Close'].tolist()
                
                # Formater les cryptos sans le "-USD" pour l'UI
                display_sym = sym.replace("-USD", "")
                data.append({"symbol": display_sym, "price": close_curr, "change": pct, "history": hist_7d})
        except:
            pass
    data.sort(key=lambda x: x['change'], reverse=True)
    return data

@bot.event
async def on_ready():
    print(f'✅ Bot {bot.user} en ligne (Revolut UI Mode) !')
    await bot.change_presence(activity=discord.Game(name="/intel | /market"))

# ====================================================
# 1. COMMANDE /MARKET
# ====================================================
@bot.tree.command(name="market", description="Dashboard des géants de Wall Street.")
async def market(interaction: discord.Interaction):
    await interaction.response.defer()
    data = get_live_data(WATCHLIST_MARKET)
    img_path = generate_dashboard_image(data, "US MARKET OVERVIEW", "market_dash.png")
    
    file = discord.File(img_path, filename="dash.png")
    await interaction.followup.send(file=file)

# ====================================================
# 2. COMMANDE /CRYPTO
# ====================================================
@bot.tree.command(name="crypto", description="Dashboard du marché Crypto.")
async def crypto(interaction: discord.Interaction):
    await interaction.response.defer()
    data = get_live_data(WATCHLIST_CRYPTO)
    img_path = generate_dashboard_image(data, "CRYPTO OVERVIEW", "crypto_dash.png")
    
    file = discord.File(img_path, filename="dash.png")
    await interaction.followup.send(file=file)

# ====================================================
# 3. COMMANDE /MOVERS (Meilleurs & Pires)
# ====================================================
@bot.tree.command(name="movers", description="Les actions les plus volatiles aujourd'hui.")
async def movers(interaction: discord.Interaction):
    await interaction.response.defer()
    # On mixe les watchlists pour trouver les extremes
    data = get_live_data(WATCHLIST_MARKET + ["COIN", "PLTR", "INTC", "SMCI"])
    top_4 = data[:4] # Les 4 meilleurs
    bottom_4 = data[-4:] # Les 4 pires
    movers_data = top_4 + bottom_4
    
    img_path = generate_dashboard_image(movers_data, "TOP DAILY MOVERS", "movers_dash.png")
    file = discord.File(img_path, filename="dash.png")
    await interaction.followup.send(file=file)

# ====================================================
# 4. COMMANDE /INTEL (Deep Dive & News fixée)
# ====================================================
@bot.tree.command(name="intel", description="Rapport financier 100% visuel sur un actif.")
@app_commands.describe(ticker="Symbole (ex: NVDA, BTC-USD)")
async def intel(interaction: discord.Interaction, ticker: str):
    ticker = ticker.upper()
    await interaction.response.defer()
    
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="2d")
        
        if len(hist) < 2:
            await interaction.followup.send(f"❌ Données introuvables pour `{ticker}`.")
            return

        # Calcul du % journalier
        c_prev = hist['Close'].iloc[-2]
        c_curr = hist['Close'].iloc[-1]
        pct_change = ((c_curr - c_prev) / c_prev) * 100

        # Données Fondamentales
        mcap = info.get('marketCap', 0)
        mcap_str = f"${mcap/1e9:.1f}B" if mcap > 0 else "N/A"
        
        intel_data = {
            "name": info.get('shortName', ticker),
            "price": c_curr,
            "change": pct_change,
            "mcap": mcap_str,
            "pe": info.get('trailingPE', 'N/A'),
            "high52": f"${info.get('fiftyTwoWeekHigh', 0):.2f}" if info.get('fiftyTwoWeekHigh') else "N/A",
            "recom": str(info.get('recommendationKey', 'N/A')).replace('_', ' ').upper(),
            "target": f"${info.get('targetMeanPrice', 0):.2f}" if info.get('targetMeanPrice') else "N/A",
        }

        # Analyse des News (CORRECTION DU BUG "0 PRESSES")
        news = stock.news
        news_data = []
        overall_sentiment = 0

        if news:
            for article in news[:3]:
                title = article.get('title', 'Titre inconnu')
                
                # Extraction ultra-robuste du journal (Yahoo Finance change souvent)
                publisher = "Financial Press"
                if 'publisher' in article:
                    publisher = article['publisher']
                elif 'provider' in article:
                    # Parfois 'provider' est un dictionnaire, parfois un string
                    provider = article['provider']
                    if isinstance(provider, dict):
                        publisher = provider.get('displayName', 'News')
                    else:
                        publisher = str(provider)
                
                news_data.append({"title": title, "publisher": publisher})
                
                # IA Sentiment
                score = analyzer.polarity_scores(title)['compound']
                overall_sentiment += score
        else:
            news_data.append({"title": "Aucune actualité détectée par l'algorithme aujourd'hui.", "publisher": "SYSTEM"})

        # Sentiment Final
        if overall_sentiment > 0.1: intel_data['sentiment_text'] = "BULLISH 🚀"
        elif overall_sentiment < -0.1: intel_data['sentiment_text'] = "BEARISH 📉"
        else: intel_data['sentiment_text'] = "NEUTRAL ⚖️"

        # Génération de l'image unique
        img_path = generate_intel_image(ticker, intel_data, news_data)
        
        file = discord.File(img_path, filename="intel.png")
        await interaction.followup.send(file=file)
        
    except Exception as e:
        await interaction.followup.send(f"⚠️ Erreur système pour `{ticker}` : {e}")

if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        print("❌ ERREUR : DISCORD_TOKEN introuvable.")
    else:
        bot.run(TOKEN)
