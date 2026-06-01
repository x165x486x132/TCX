import discord
from discord import app_commands
import yfinance as yf
import os

from heatmap_engine import generate_market_dashboard

# La liste des géants à surveiller (exactement 8 pour le design)
WATCHLIST = ["NVDA", "AAPL", "MSFT", "TSLA", "AMZN", "META", "GOOGL", "AMD"]

class MarketBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

bot = MarketBot()

def get_market_data():
    """Récupère les prix et pourcentages actuels sur Yahoo Finance."""
    data = []
    for sym in WATCHLIST:
        try:
            tkr = yf.Ticker(sym)
            hist = tkr.history(period="2d")
            if len(hist) >= 2:
                close_prev = hist['Close'].iloc[-2]
                close_curr = hist['Close'].iloc[-1]
                pct = ((close_curr - close_prev) / close_prev) * 100
                data.append({"symbol": sym, "price": close_curr, "change": pct})
        except Exception:
            pass
    # Trier du plus grand gagnant au plus grand perdant
    data.sort(key=lambda x: x['change'], reverse=True)
    return data

class RefreshButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None) # Le bouton ne désactive jamais

    @discord.ui.button(label="🔄 Actualiser les prix", style=discord.ButtonStyle.blurple)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Discord a besoin de savoir qu'on traite la demande
        await interaction.response.defer()
        
        # 1. On re-télécharge les données
        data = get_market_data()
        
        # 2. On regénère la nouvelle image esthétique
        image_path = generate_market_dashboard(data)
        
        # 3. On reconstruit l'Embed
        embed = discord.Embed(title="🌐 WALL STREET - TOP TECH", color=0x2b2d31)
        embed.description = "État actuel des actions les plus suivies."
        
        # 4. On modifie (edit) le message avec la nouvelle image !
        file = discord.File(image_path, filename="dashboard.png")
        embed.set_image(url="attachment://dashboard.png")
        
        await interaction.edit_original_response(embed=embed, attachments=[file], view=self)

@bot.event
async def on_ready():
    print(f'✅ Bot {bot.user} en ligne !')
    await bot.change_presence(activity=discord.Game(name="/market"))

@bot.tree.command(name="market", description="Affiche le tableau de bord esthétique des géants de Wall Street.")
async def market(interaction: discord.Interaction):
    await interaction.response.defer() # Fait patienter Discord
    
    # Récupérer les data et générer l'image
    data = get_market_data()
    image_path = generate_market_dashboard(data)
    
    # Créer l'embed Discord
    embed = discord.Embed(title="🌐 WALL STREET - TOP TECH", color=0x2b2d31)
    embed.description = "Cliquez sur actualiser pour rafraîchir les cours en direct."
    
    # Attacher l'image à l'embed
    file = discord.File(image_path, filename="dashboard.png")
    embed.set_image(url="attachment://dashboard.png")
    
    # Envoyer le message avec le bouton
    await interaction.followup.send(embed=embed, file=file, view=RefreshButton())

if __name__ == "__main__":
    TOKEN = os.getenv('DISCORD_TOKEN')
    if not TOKEN:
        print("❌ ERREUR : DISCORD_TOKEN introuvable.")
    else:
        bot.run(TOKEN)
