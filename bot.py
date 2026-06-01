import discord
from discord import app_commands
import yfinance as yf
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

def get_market_data():
    """Récupère l'historique sur 7 jours pour faire les Sparklines."""
    data = []
    for sym in WATCHLIST:
        try:
            tkr = yf.Ticker(sym)
            hist = tkr.history(period="7d")
            if len(hist) >= 2:
                close_prev = hist['Close'].iloc[-2]
                close_curr = hist['Close'].iloc[-1]
                pct = ((close_curr - close_prev) / close_prev) * 100
                history_list = hist['Close'].tolist() # Les 7 derniers prix
                data.append({"symbol": sym, "price": close_curr, "change": pct, "history": history_list})
        except Exception:
            pass
    data.sort(key=lambda x: x['change'], reverse=True)
    return data

class RefreshButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🔄 Actualiser les prix en direct", style=discord.ButtonStyle.blurple)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        data = get_market_data()
        image_path = generate_market_dashboard(data)
        
        embed = discord.Embed(title="🌐 WALL STREET - TOP TECH", color=0x15161C)
        file = discord.File(image_path, filename="dashboard.png")
        embed.set_image(url="attachment://dashboard.png")
        
        await interaction.edit_original_response(embed=embed, attachments=[file], view=self)

@bot.event
async def on_ready():
    print(f'✅ Bot {bot.user} en ligne !')
    await bot.change_presence(activity=discord.Game(name="/market | /intel"))

# ====================================================
# COMMANDE 1 : LE DASHBOARD VISUEL
# ====================================================
@bot.tree.command(name="market", description="Affiche le dashboard Fintech avec Sparklines et effets Glow.")
async def market(interaction: discord.Interaction):
    await interaction.response.defer()
    data = get_market_data()
    image_path = generate_market_dashboard(data)
    
    embed = discord.Embed(title="🌐 WALL STREET - TOP TECH", color=0x15161C)
    file = discord.File(image_path, filename="dashboard.png")
    embed.set_image(url="attachment://dashboard.png")
    
    await interaction.followup.send(embed=embed, file=file, view=RefreshButton())

# ====================================================
# COMMANDE 2 : LE RAPPORT D'INTELLIGENCE FINANCIÈRE
# ====================================================
@bot.tree.command(name="intel", description="Rapport complet: Objectifs analystes, recommandations et résumés des news.")
@app_commands.describe(ticker="Symbole (ex: NVDA, AAPL)")
async def intel(interaction: discord.Interaction, ticker: str):
    ticker = ticker.upper()
    await interaction.response.defer()
    
    try:
        stock = yf.Ticker(ticker)
        info = stock.info
        
        company_name = info.get('shortName', ticker)
        current_price = info.get('currentPrice', info.get('regularMarketPrice', 'N/A'))
        target_price = info.get('targetMeanPrice', 'N/A')
        recommendation = str(info.get('recommendationKey', 'N/A')).replace('_', ' ').upper()
        
        # Déterminer la couleur de l'Embed en fonction de la recommandation
        color = 0x6C7080 # Gris par défaut
        if "BUY" in recommendation:
            color = 0x00E676 # Vert
        elif "SELL" in recommendation or "UNDERPERFORM" in recommendation:
            color = 0xFF3B30 # Rouge
            
        embed = discord.Embed(title=f"📈 REPORTING INTEL : {company_name} ({ticker})", color=color)
        
        # Statistiques Financières
        embed.add_field(name="💵 Prix Actuel", value=f"**${current_price}**", inline=True)
        embed.add_field(name="🎯 Objectif Analystes (1 an)", value=f"**${target_price}**", inline=True)
        embed.add_field(name="⚖️ Consensus Wall Street", value=f"**{recommendation}**", inline=True)
        
        # Récupération des dernières annonces / News
        news = stock.news
        if news:
            news_text = ""
            for i, article in enumerate(news[:3]): # Prend les 3 dernières news
                title = article.get('title', 'Titre non disponible')
                publisher = article.get('publisher', 'Presse')
                news_text += f"**{i+1}. {publisher}**\n> {title}\n\n"
            
            embed.add_field(name="📰 Dernières Annonces & Conférences", value=news_text, inline=False)
        else:
            embed.add_field(name="📰 Dernières Annonces", value="*Aucune actualité récente trouvée.*", inline=False)
            
        embed.set_footer(text="Data provided by Yahoo Finance Algo")
        await interaction.followup.send(embed=embed)
        
    except Exception as e:
        await interaction.followup.send(f"⚠️ Impossible de récupérer les données pour `{ticker}`. Vérifie le symbole.")

if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        print("❌ ERREUR : DISCORD_TOKEN introuvable.")
    else:
        bot.run(TOKEN)
