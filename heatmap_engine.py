from PIL import Image, ImageDraw, ImageFont
import os
import requests

def download_font(font_name, url):
    """Télécharge la police automatiquement si elle n'existe pas."""
    os.makedirs("assets", exist_ok=True)
    font_path = f"assets/{font_name}"
    if not os.path.exists(font_path):
        response = requests.get(url)
        with open(font_path, 'wb') as f:
            f.write(response.content)
    return font_path

def generate_market_dashboard(data):
    """Génère une image ultra-minimaliste style Revolut / iOS Stocks."""
    
    # 1. Téléchargement des polices (Roboto est très proche de San Francisco d'Apple)
    url_bold = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"
    url_reg = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf"
    
    path_bold = download_font("Roboto-Bold.ttf", url_bold)
    path_reg = download_font("Roboto-Regular.ttf", url_reg)
    
    try:
        font_header = ImageFont.truetype(path_bold, 45)
        font_sub = ImageFont.truetype(path_reg, 22)
        font_symbol = ImageFont.truetype(path_bold, 32)
        font_price = ImageFont.truetype(path_bold, 42)
        font_pct = ImageFont.truetype(path_bold, 24)
    except:
        font_header = font_sub = font_symbol = font_price = font_pct = ImageFont.load_default()

    # 2. La palette de couleurs (Style iOS Dark Mode / Revolut)
    BG_COLOR = "#000000"       # Fond noir absolu
    CARD_COLOR = "#1C1C1E"     # Gris sombre typique des widgets Apple
    TEXT_MAIN = "#FFFFFF"      # Blanc pur
    TEXT_MUTED = "#8E8E93"     # Gris secondaire iOS
    GREEN = "#34C759"          # Vert Apple Bourse
    RED = "#FF3B30"            # Rouge Apple Bourse

    width, height = 1200, 650
    img = Image.new("RGB", (width, height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # 3. L'en-tête (Clean & Minimaliste)
    draw.text((50, 40), "Market Overview", fill=TEXT_MAIN, font=font_header)
    draw.text((50, 100), "Top Tech Stocks • Real-time Data", fill=TEXT_MUTED, font=font_sub)

    # 4. Configuration de la grille (4 colonnes, 2 lignes)
    cols, rows = 4, 2
    margin_x, margin_y = 50, 160
    gap = 20
    block_w = (width - (2 * margin_x) - (cols - 1) * gap) // cols
    block_h = (height - margin_y - 50 - (rows - 1) * gap) // rows

    # 5. Dessiner les cartes
    for i, item in enumerate(data):
        x = margin_x + (i % cols) * (block_w + gap)
        y = margin_y + (i // cols) * (block_h + gap)
        
        # Le fond de la carte (avec des bords très arrondis, radius=25)
        draw.rounded_rectangle([x, y, x + block_w, y + block_h], radius=25, fill=CARD_COLOR)
        
        # Attribution de la couleur selon la tendance
        if item['change'] >= 0:
            color = GREEN
            sign = "+"
        else:
            color = RED
            sign = ""

        # Affichage du Symbole (ex: AAPL)
        draw.text((x + 25, y + 25), item['symbol'], fill=TEXT_MAIN, font=font_symbol)
        
        # Affichage du Prix (Au milieu, bien gros)
        draw.text((x + 25, y + 80), f"${item['price']:,.2f}", fill=TEXT_MAIN, font=font_price)
        
        # Affichage du Pourcentage (En bas, coloré)
        pct_text = f"{sign}{item['change']:.2f}%"
        draw.text((x + 25, y + 140), pct_text, fill=color, font=font_pct)

    # 6. Sauvegarder l'image
    os.makedirs("output", exist_ok=True)
    output_path = "output/market_dashboard.png"
    img.save(output_path)
    
    return output_path
