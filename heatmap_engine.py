from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
import requests

def download_font(font_name, url):
    os.makedirs("assets", exist_ok=True)
    font_path = f"assets/{font_name}"
    if not os.path.exists(font_path):
        response = requests.get(url)
        with open(font_path, 'wb') as f:
            f.write(response.content)
    return font_path

def draw_sparkline(img, data_points, x, y, w, h, color):
    """Dessine une mini-courbe avec un effet de lueur (Glow) style Revolut."""
    if not data_points or len(data_points) < 2:
        return
        
    min_val, max_val = min(data_points), max(data_points)
    if max_val == min_val:
        max_val += 0.01

    coords = []
    for i, val in enumerate(data_points):
        px = x + (i / (len(data_points) - 1)) * w
        py = y + h - ((val - min_val) / (max_val - min_val)) * h
        coords.append((px, py))

    # 1. Créer le calque de Glow (Flou)
    glow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    glow_draw.line(coords, fill=color, width=12, joint="curve")
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(12)) # Effet Néon

    # 2. Fusionner le Glow avec l'image principale
    img.paste(glow_layer, (0, 0), glow_layer)

    # 3. Dessiner la ligne nette par-dessus
    draw = ImageDraw.Draw(img)
    draw.line(coords, fill=color, width=4, joint="curve")

def generate_market_dashboard(data):
    """Génère un dashboard Fintech Premium avec Sparklines et effets Glow."""
    url_bold = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"
    url_reg = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf"
    
    path_bold = download_font("Roboto-Bold.ttf", url_bold)
    path_reg = download_font("Roboto-Regular.ttf", url_reg)
    
    try:
        font_header = ImageFont.truetype(path_bold, 45)
        font_sub = ImageFont.truetype(path_reg, 22)
        font_symbol = ImageFont.truetype(path_bold, 34)
        font_price = ImageFont.truetype(path_bold, 38)
        font_pct = ImageFont.truetype(path_bold, 22)
    except:
        font_header = font_sub = font_symbol = font_price = font_pct = ImageFont.load_default()

    # Couleurs Premium Fintech
    BG_COLOR = "#0B0C10"       # Fond très sombre
    CARD_COLOR = "#15161C"     # Cartes gris bleuté profond
    TEXT_MAIN = "#FFFFFF"
    TEXT_MUTED = "#6C7080"
    
    # Couleurs RGBA pour l'effet Glow (R, G, B, Opacité)
    GREEN_GLOW = (0, 230, 118, 180)  # Vert fluo
    RED_GLOW = (255, 59, 48, 180)    # Rouge vif
    GREEN_HEX = "#00E676"
    RED_HEX = "#FF3B30"

    width, height = 1200, 650
    img = Image.new("RGBA", (width, height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # En-tête
    draw.text((50, 40), "Market Overview", fill=TEXT_MAIN, font=font_header)
    draw.text((50, 100), "Top Tech Stocks • 7-Day Sparklines", fill=TEXT_MUTED, font=font_sub)

    # Grille 4x2
    cols, rows = 4, 2
    margin_x, margin_y = 50, 160
    gap = 25
    block_w = (width - (2 * margin_x) - (cols - 1) * gap) // cols
    block_h = (height - margin_y - 50 - (rows - 1) * gap) // rows

    for i, item in enumerate(data):
        x = margin_x + (i % cols) * (block_w + gap)
        y = margin_y + (i // cols) * (block_h + gap)
        
        # Dessin de la carte
        draw.rounded_rectangle([x, y, x + block_w, y + block_h], radius=20, fill=CARD_COLOR)
        
        # Tendance et Couleurs
        if item['change'] >= 0:
            glow_color = GREEN_GLOW
            hex_color = GREEN_HEX
            sign = "+"
        else:
            glow_color = RED_GLOW
            hex_color = RED_HEX
            sign = ""

        # Textes
        draw.text((x + 20, y + 20), item['symbol'], fill=TEXT_MAIN, font=font_symbol)
        draw.text((x + 20, y + 65), f"${item['price']:,.2f}", fill=TEXT_MAIN, font=font_price)
        draw.text((x + 20, y + 110), f"{sign}{item['change']:.2f}%", fill=hex_color, font=font_pct)

        # Dessiner le mini-graphique (Sparkline) avec Glow sur le côté droit de la carte
        spark_x = x + 120
        spark_y = y + 70
        spark_w = block_w - 140
        spark_h = 60
        draw_sparkline(img, item['history'], spark_x, spark_y, spark_w, spark_h, glow_color)

    # Export en RGB normal pour sauver en PNG
    final_img = img.convert("RGB")
    os.makedirs("output", exist_ok=True)
    output_path = "output/market_dashboard.png"
    final_img.save(output_path)
    
    return output_path
