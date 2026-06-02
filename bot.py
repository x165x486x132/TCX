import discord
from discord import app_commands
import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
import pandas as pd
import os

from heatmap_engine import generate_market_dashboard

WATCHLIST = ["NVDA", "AAPL", "MSFT", "TSLA", "AMZN", "META", "GOOGL", "AMD"]

class MarketBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

bot = MarketBot()
analyzer = SentimentIntensityAnalyzer()

def calculate_rsi(data, periods=14):
    """Calcule le Relative Strength Index (Indicateur Technique)."""
    if len(data) < periods: return 50
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=periods).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=periods).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1]

def get_market_data():
    """Récupère les données, le RSI et le Volume."""
    data = []
    for sym in WATCHLIST:
        try:
            tkr = yf.Ticker(sym)
            hist = tkr.history(period="1mo") # Besoin d'un mois pour le RSI
            if len(hist) >= 2:
                close_prev = hist['Close'].iloc[-2]
                close_curr = hist['Close'].iloc[-1]
                pct = ((close_curr - close_prev) / close_prev) * 100
                
                # 7 jours pour la sparkline
                hist_7d = hist['Close'].tail(7).tolist() 
                volume = hist['Volume'].iloc[-1]
                rsi = calculate_rsi(hist)

                data.append({
                    "symbol": sym, 
                    "price": close_curr, 
                    "change": pct, 
                    "history": hist_7d,
                    "volume": volume,
                    "rsi": rsi
                })
        except Exception as e:
            print(f"Erreur data {sym}: {e}")
            pass
            
    data.sort(key=lambda x: x['change'], reverse=True)
    return data

class RefreshButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔄 Actualiser les data quantitatives", style=discord.ButtonStyle.blurple)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        data = get_market_data()
        image_path = generate_market_dashboard(data)
        
        embed = discord.Embed(title="🌐 TERMINAL WALL STREET", color=0x13141C)
        file = discord.File(image_path, filename="dashboard.png")
        embed.set_image(url="attachment://dashboard.png")
        
        await interaction.edit_original_response(embed=embed, attachments=[file], view=self)

@bot.event
async def on_ready():
    print(f'✅ Bot {bot.user} en ligne (Mode Institutionnel) !')
    await bot.change_presence(activity=discord.Game(name="/market | /intel"))

@bot.tree.command(name="market", description="Affiche le dashboard quantitatif du marché.")
async def market(interaction: discord.Interaction):
    await interaction.response.defer()
    data = get_market_data()
    image_path = generate_market_dashboard(data)
    
    embed = discord.Embed(title="🌐 TERMINAL WALL STREET", color=0x13141C)
    file = discord.File(image_path, filename="dashboard.png")
    embed.set_image(url="attachment://dashboard.png")
    
    await interaction.followup.send(embed=embed, file=file, view=RefreshButton())

@bot.tree.command(name="intel", description="Rapport complet: Fondamental, Technique, Sentiment IA et News.")
@app_commands.describe(ticker="Symbole (ex: NVDA, AAPL)")
async def intel(interaction: discord.Interaction, ticker: str):
    ticker = ticker.upper()
    await interaction.response.defer()
    
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        hist = stock.history(period="1mo")
        
        # --- 1. Données Fondamentales ---
        company_name = info.get('shortName', ticker)
        current_price = info.get('currentPrice', info.get('regularMarketPrice', 'N/A'))
        target_price = info.get('targetMeanPrice', 'N/A')
        mcap = info.get('marketCap', 0)
        mcap_str = f"${mcap/1e9:.1f}B" if mcap > 0 else "N/A"
        pe_ratio = info.get('trailingPE', 'N/A')
        fifty_two_high = info.get('fiftyTwoWeekHigh', 'N/A')
        recommendation = str(info.get('recommendationKey', 'N/A')).replace('_', ' ').upper()
        
        # --- 2. Données Techniques ---
        rsi_val = calculate_rsi(hist) if len(hist) > 14 else 50
        rsi_status = "🔴 SURACHETÉ" if rsi_val > 70 else ("🟢 SURVENDU" if rsi_val < 30 else "⚪ NEUTRE")
        
        # --- 3. Analyse des News (Correction du bug des sources) ---
        news = stock.news
        news_text = ""
        overall_sentiment = 0
        
        if news:
            for i, article in enumerate(news[:3]):
                title = article.get('title', 'Titre non disponible')
                link = article.get('link', '#')
                # YFinance change souvent la clé du publisher. On tente plusieurs clés.
                publisher = article.get('publisher', article.get('provider', 'Financial Press'))
                
                # IA Sentiment sur le titre
                score = analyzer.polarity_scores(title)['compound']
                overall_sentiment += score
                emoji = "🟢" if score > 0.05 else ("🔴" if score < -0.05 else "⚪")
                
                news_text += f"{emoji} **[{publisher}]** [{title}]({link})\n"
        else:
            news_text = "*Aucune actualité récente (ou API YFinance bloquée).* \n"
            
        # Sentiment Global
        trend_ia = "BULLISH 🚀" if overall_sentiment > 0.1 else ("BEARISH 📉" if overall_sentiment < -0.1 else "NEUTRAL ⚖️")

        # --- 4. Création de l'Embed Discord ---
        color = 0x00E676 if "BUY" in recommendation else (0xFF3B30 if "SELL" in recommendation else 0x7A7E93)
        embed = discord.Embed(title=f"🧠 INTELLIGENCE REPORT : {company_name} ({ticker})", color=color)
        
        # Ligne 1: Prix & Technique
        embed.add_field(name="💵 Prix Actuel", value=f"**${current_price}**\n(52W High: ${fifty_two_high})", inline=True)
        embed.add_field(name="📊 Indicateur RSI (14j)", value=f"**{rsi_val:.1f}**\n{rsi_status}", inline=True)
        embed.add_field(name="🤖 Sentiment IA (News)", value=f"**{trend_ia}**", inline=True)
        
        # Ligne 2: Fondamental
        embed.add_field(name="🏛️ Market Cap", value=f"**{mcap_str}**", inline=True)
        embed.add_field(name="📈 Ratio P/E", value=f"**{pe_ratio}**", inline=True)
        embed.add_field(name="🎯 Consensus (1 an)", value=f"Target: **${target_price}**\n({recommendation})", inline=True)
        
        # Ligne 3: News (Liens cliquables)
        embed.add_field(name="📰 Dernières Annonces Institutionnelles", value=news_text, inline=False)
        
        embed.set_footer(text="Quant Trading Algo • Données fournies à titre indicatif")
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(f"⚠️ Erreur système pour `{ticker}`. L'API financière refuse peut-être la connexion. Erreur: `{e}`")

if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        print("❌ ERREUR : DISCORD_TOKEN introuvable.")
    else:
        bot.run(TOKEN)
