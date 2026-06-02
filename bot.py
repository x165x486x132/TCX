import discord
from discord import app_commands
import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import os

from ui_engine import generate_dashboard_image, generate_intel_image

# --- LES WATCHLISTS COMPLÈTES ---
WATCHLIST_MARKET = ["NVDA", "AAPL", "MSFT", "TSLA", "AMZN", "META", "GOOGL", "BRK-B"]
WATCHLIST_CRYPTO = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "DOGE-USD", "ADA-USD", "AVAX-USD"]
WATCHLIST_FOREX = ["EURUSD=X", "GBPUSD=X", "JPY=X", "CHF=X", "AUDUSD=X", "USDCAD=X", "NZDUSD=X", "EURGBP=X"]
WATCHLIST_COMMODITIES = ["GC=F", "SI=F", "CL=F", "NG=F", "ZC=F", "HG=F", "CC=F", "KC=F"]
WATCHLIST_INDICES = ["^GSPC", "^IXIC", "^DJI", "^VIX", "^RUT", "^FTSE", "^N225", "^FCHI"] # FCHI = CAC40

# --- TRADUCTION DES SYMBOLES POUR UN DESIGN PROPRE ---
RENAME_MAP = {
    "^GSPC": "S&P 500", "^IXIC": "NASDAQ", "^DJI": "DOW JONES", "^VIX": "VIX VOLATILITY",
    "^RUT": "RUSSELL 2000", "^FTSE": "FTSE 100", "^N225": "NIKKEI 225", "^FCHI": "CAC 40",
    "GC=F": "GOLD", "SI=F": "SILVER", "CL=F": "CRUDE OIL", "NG=F": "NATURAL GAS",
    "ZC=F": "CORN", "HG=F": "COPPER", "CC=F": "COCOA", "KC=F": "COFFEE",
    "EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "JPY=X": "USD/JPY", "CHF=X": "USD/CHF",
    "AUDUSD=X": "AUD/USD", "USDCAD=X": "USD/CAD", "NZDUSD=X": "NZD/USD", "EURGBP=X": "EUR/GBP",
    "BTC-USD": "BITCOIN", "ETH-USD": "ETHEREUM", "SOL-USD": "SOLANA", "BNB-USD": "BINANCE",
    "XRP-USD": "XRP", "DOGE-USD": "DOGECOIN", "ADA-USD": "CARDANO", "AVAX-USD": "AVALANCHE"
}

class TradingBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

bot = TradingBot()
analyzer = SentimentIntensityAnalyzer()

def get_live_data(watchlist):
    """Télécharge et blinde les données de Yahoo Finance."""
    data = []
    for sym in watchlist:
        try:
            tkr = yf.Ticker(sym)
            hist = tkr.history(period="7d")
            
            # Blindage complet : on s'assure qu'on a bien des données valides
            if not hist.empty and len(hist) >= 2:
                # Nettoyage des NaN et conversion forcée en liste de floats
                clean_history = [float(x) for x in hist['Close'].dropna().tolist()]
                
                if len(clean_history) >= 2:
                    close_prev = clean_history[-2]
                    close_curr = clean_history[-1]
                    pct = ((close_curr - close_prev) / close_prev) * 100
                    
                    display_name = RENAME_MAP.get(sym, sym)
                    
                    data.append({
                        "raw_symbol": sym,
                        "display_name": display_name, 
                        "price": close_curr, 
                        "change": pct, 
                        "history": clean_history
                    })
        except Exception as e:
            print(f"Erreur API pour {sym} : {e}")
            pass
            
    data.sort(key=lambda x: x['change'], reverse=True)
    return data

@bot.event
async def on_ready():
    print(f'✅ Bot {bot.user} en ligne (Global Market Mode) !')
    await bot.change_presence(activity=discord.Game(name="/market | /crypto | /forex"))

# ====================================================
# COMMANDES DASHBOARDS (MARKET, CRYPTO, FOREX, COMMODITIES, INDICES)
# ====================================================

async def send_dashboard(interaction, watchlist, title, filename):
    await interaction.response.defer()
    data = get_live_data(watchlist)
    if not data:
        await interaction.followup.send("❌ Impossible de joindre les serveurs financiers.")
        return
        
    img_path = generate_dashboard_image(data, title, filename)
    file = discord.File(img_path, filename="dash.png")
    await interaction.followup.send(file=file)

@bot.tree.command(name="market", description="Dashboard des géants de Wall Street.")
async def market(interaction: discord.Interaction):
    await send_dashboard(interaction, WATCHLIST_MARKET, "US MARKET OVERVIEW", "market_dash.png")

@bot.tree.command(name="crypto", description="Dashboard des Cryptomonnaies.")
async def crypto(interaction: discord.Interaction):
    await send_dashboard(interaction, WATCHLIST_CRYPTO, "CRYPTO OVERVIEW", "crypto_dash.png")

@bot.tree.command(name="forex", description="Dashboard des Devises Mondiales.")
async def forex(interaction: discord.Interaction):
    await send_dashboard(interaction, WATCHLIST_FOREX, "FOREX OVERVIEW", "forex_dash.png")

@bot.tree.command(name="commodities", description="Dashboard des Matières Premières (Or, Pétrole...).")
async def commodities(interaction: discord.Interaction):
    await send_dashboard(interaction, WATCHLIST_COMMODITIES, "COMMODITIES OVERVIEW", "comm_dash.png")

@bot.tree.command(name="indices", description="Dashboard des Indices Mondiaux (S&P500, CAC40...).")
async def indices(interaction: discord.Interaction):
    await send_dashboard(interaction, WATCHLIST_INDICES, "GLOBAL INDICES", "indices_dash.png")

# ====================================================
# COMMANDE /MOVERS (Meilleurs & Pires)
# ====================================================
@bot.tree.command(name="movers", description="Les actifs les plus volatils aujourd'hui.")
async def movers(interaction: discord.Interaction):
    await interaction.response.defer()
    data = get_live_data(WATCHLIST_MARKET + ["COIN", "PLTR", "INTC", "SMCI", "MSTR", "DJT"])
    if len(data) >= 8:
        top_4 = data[:4]
        bottom_4 = data[-4:]
        movers_data = top_4 + bottom_4
    else:
        movers_data = data
        
    img_path = generate_dashboard_image(movers_data, "TOP DAILY MOVERS", "movers_dash.png")
    file = discord.File(img_path, filename="dash.png")
    await interaction.followup.send(file=file)

# ====================================================
# COMMANDE /INTEL (Deep Dive)
# ====================================================
@bot.tree.command(name="intel", description="Rapport financier 100% visuel sur un actif.")
@app_commands.describe(ticker="Symbole (ex: NVDA, BTC-USD, GC=F)")
async def intel(interaction: discord.Interaction, ticker: str):
    ticker = ticker.upper()
    await interaction.response.defer()
    
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="2d")
        
        if hist.empty or len(hist) < 2:
            await interaction.followup.send(f"❌ Données introuvables pour `{ticker}`.")
            return

        c_prev = float(hist['Close'].iloc[-2])
        c_curr = float(hist['Close'].iloc[-1])
        pct_change = ((c_curr - c_prev) / c_prev) * 100

        mcap = info.get('marketCap', 0)
        mcap_str = f"${mcap/1e9:.1f}B" if mcap > 0 else "N/A"
        
        intel_data = {
            "name": RENAME_MAP.get(ticker, info.get('shortName', ticker)),
            "price": c_curr,
            "change": pct_change,
            "mcap": mcap_str,
            "pe": info.get('trailingPE', 'N/A'),
            "high52": f"${info.get('fiftyTwoWeekHigh', 0):.2f}" if info.get('fiftyTwoWeekHigh') else "N/A",
            "recom": str(info.get('recommendationKey', 'N/A')).replace('_', ' ').upper(),
            "target": f"${info.get('targetMeanPrice', 0):.2f}" if info.get('targetMeanPrice') else "N/A",
        }

        # Analyse des News avec Blindage
        news = stock.news
        news_data = []
        overall_sentiment = 0

        if news:
            for article in news[:3]:
                title = article.get('title', 'Titre inconnu')
                
                # Extraction du Publisher
                publisher = "Financial Press"
                if 'publisher' in article:
                    publisher = article['publisher']
                elif 'provider' in article:
                    provider = article['provider']
                    if isinstance(provider, dict):
                        publisher = provider.get('displayName', 'News')
                    else:
                        publisher = str(provider)
                
                news_data.append({"title": title, "publisher": publisher})
                score = analyzer.polarity_scores(title)['compound']
                overall_sentiment += score
        else:
            news_data.append({"title": "Aucune actualité détectée par l'algorithme aujourd'hui.", "publisher": "SYSTEM"})

        if overall_sentiment > 0.1: intel_data['sentiment_text'] = "BULLISH 🚀"
        elif overall_sentiment < -0.1: intel_data['sentiment_text'] = "BEARISH 📉"
        else: intel_data['sentiment_text'] = "NEUTRAL ⚖️"

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
