from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
import requests
import textwrap

# --- CONSTANTES DESIGN (STYLE REVOLUT / INSTITUTIONNEL) ---
BG_COLOR = "#000000"       
CARD_COLOR = "#1C1C1E"     
TEXT_MAIN = "#FFFFFF"
TEXT_MUTED = "#8E8E93"
GREEN_HEX = "#34C759"
RED_HEX = "#FF3B30"

def download_font(font_name, url):
    os.makedirs("assets", exist_ok=True)
    font_path = f"assets/{font_name}"
    if not os.path.exists(font_path):
        response = requests.get(url)
        with open(font_path, 'wb') as f:
            f.write(response.content)
    return font_path

def get_fonts():
    url_bold = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"
    url_med = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Medium.ttf"
    url_reg = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf"
    
    pb = download_font("Roboto-Bold.ttf", url_bold)
    pm = download_font("Roboto-Medium.ttf", url_med)
    pr = download_font("Roboto-Regular.ttf", url_reg)
    
    try:
        return {
            "title": ImageFont.truetype(pb, 45),
            "sub": ImageFont.truetype(pr, 22),
            "sym": ImageFont.truetype(pb, 32),
            "price": ImageFont.truetype(pb, 36),
            "pct": ImageFont.truetype(pb, 22),
            "mini": ImageFont.truetype(pm, 18),
            "news_title": ImageFont.truetype(pm, 20),
            "news_src": ImageFont.truetype(pb, 18)
        }
    except:
        default = ImageFont.load_default()
        return {k: default for k in ["title", "sub", "sym", "price", "pct", "mini", "news_title", "news_src"]}

def format_price(symbol, price):
    """Adapte l'affichage du prix selon l'actif."""
    if "^" in symbol: # Indices (S&P500, Nasdaq...)
        return f"{price:,.2f} pts"
    elif "=X" in symbol: # Forex (Devises)
        return f"{price:,.4f}"
    elif price < 1: # Petites Cryptos
        return f"${price:,.4f}"
    else: # Actions et grosses Cryptos
        return f"${price:,.2f}"

def draw_sparkline(img, data_points, x, y, w, h, color_hex):
    # SÉCURITÉ ANTI-CRASH (Vérifie que data_points est bien une liste valide)
    if not isinstance(data_points, list) or len(data_points) < 2: 
        return
        
    min_val, max_val = min(data_points), max(data_points)
    if max_val == min_val: max_val += 0.01

    coords = []
    for i, val in enumerate(data_points):
        px = x + (i / (len(data_points) - 1)) * w
        py = y + h - ((val - min_val) / (max_val - min_val)) * h
        coords.append((px, py))

    # Convertir Hex en RGBA pour le glow
    h_color = color_hex.lstrip('#')
    r, g, b = tuple(int(h_color[i:i+2], 16) for i in (0, 2, 4))
    glow_color = (r, g, b, 100)

    glow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    glow_draw.line(coords, fill=glow_color, width=8, joint="curve")
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(8))
    img.paste(glow_layer, (0, 0), glow_layer)

    draw = ImageDraw.Draw(img)
    draw.line(coords, fill=color_hex, width=3, joint="curve")

# ==========================================
# 1. GÉNÉRATEUR DASHBOARD GLOBAL
# ==========================================
def generate_dashboard_image(data, title, filename):
    fonts = get_fonts()
    width, height = 1200, 650
    img = Image.new("RGBA", (width, height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    draw.text((50, 40), title, fill=TEXT_MAIN, font=fonts['title'])
    draw.text((50, 100), "Algorithmic Tracking • Real-Time Market Data", fill=TEXT_MUTED, font=fonts['sub'])

    cols, rows = 4, 2
    margin_x, margin_y = 50, 160
    gap = 25
    block_w = (width - (2 * margin_x) - (cols - 1) * gap) // cols
    block_h = (height - margin_y - 50 - (rows - 1) * gap) // rows

    for i, item in enumerate(data[:8]): 
        x = margin_x + (i % cols) * (block_w + gap)
        y = margin_y + (i // cols) * (block_h + gap)
        
        draw.rounded_rectangle([x, y, x + block_w, y + block_h], radius=20, fill=CARD_COLOR)
        
        is_up = item['change'] >= 0
        hex_color = GREEN_HEX if is_up else RED_HEX
        sign = "+" if is_up else ""

        # Nom de l'actif
        draw.text((x + 20, y + 20), item['display_name'], fill=TEXT_MAIN, font=fonts['sym'])
        
        # Prix Formaté
        price_str = format_price(item['raw_symbol'], item['price'])
        draw.text((x + 20, y + 65), price_str, fill=TEXT_MAIN, font=fonts['price'])
        
        # Pourcentage
        draw.text((x + 20, y + 115), f"{sign}{item['change']:.2f}%", fill=hex_color, font=fonts['pct'])

        # Sparkline
        draw_sparkline(img, item['history'], x + 120, y + 70, block_w - 140, 60, hex_color)

    final_img = img.convert("RGB")
    os.makedirs("output", exist_ok=True)
    out_path = f"output/{filename}"
    final_img.save(out_path)
    return out_path

# ==========================================
# 2. GÉNÉRATEUR REPORT INTEL
# ==========================================
def generate_intel_image(ticker, intel_data, news_data):
    fonts = get_fonts()
    width, height = 1000, 800
    img = Image.new("RGBA", (width, height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    draw.text((50, 40), f"{intel_data['name']} ({ticker})", fill=TEXT_MAIN, font=fonts['title'])
    draw.text((50, 100), "AI Quantitative Report • Live Snapshot", fill=TEXT_MUTED, font=fonts['sub'])

    is_up = intel_data['change'] >= 0
    main_color = GREEN_HEX if is_up else RED_HEX
    sign = "+" if is_up else ""
    
    price_str = format_price(ticker, intel_data['price'])
    draw.text((800, 40), price_str, fill=TEXT_MAIN, font=fonts['title'])
    draw.text((800, 100), f"{sign}{intel_data['change']:.2f}% Today", fill=main_color, font=fonts['sub'])

    draw.line([(50, 150), (950, 150)], fill=CARD_COLOR, width=3)

    stats = [
        ("MARKET CAP", intel_data['mcap']),
        ("P/E RATIO", intel_data['pe']),
        ("52W HIGH", intel_data['high52']),
        ("WALL ST CONSENSUS", intel_data['recom']),
        ("1Y TARGET PRICE", intel_data['target']),
        ("AI SENTIMENT (NEWS)", intel_data['sentiment_text'])
    ]

    stat_y = 180
    for i, (label, val) in enumerate(stats):
        col = i % 3
        row = i // 3
        x = 50 + col * 300
        y = stat_y + row * 90
        
        val_color = TEXT_MAIN
        if "BULLISH" in val or "BUY" in val: val_color = GREEN_HEX
        elif "BEARISH" in val or "SELL" in val or "UNDER" in val: val_color = RED_HEX
            
        draw.text((x, y), label, fill=TEXT_MUTED, font=fonts['mini'])
        draw.text((x, y + 25), str(val), fill=val_color, font=fonts['sym'])

    draw.line([(50, 380), (950, 380)], fill=CARD_COLOR, width=3)
    draw.text((50, 410), "LATEST FINANCIAL INTELLIGENCE", fill=TEXT_MUTED, font=fonts['sub'])

    news_y = 460
    for article in news_data[:3]:
        draw.rounded_rectangle([50, news_y, 950, news_y + 90], radius=15, fill=CARD_COLOR)
        draw.text((70, news_y + 15), f"📰 {article['publisher'].upper()}", fill=TEXT_MUTED, font=fonts['news_src'])
        wrapped_title = textwrap.shorten(article['title'], width=85, placeholder="...")
        draw.text((70, news_y + 45), wrapped_title, fill=TEXT_MAIN, font=fonts['news_title'])
        news_y += 105

    final_img = img.convert("RGB")
    os.makedirs("output", exist_ok=True)
    out_path = f"output/intel_{ticker}.png"
    final_img.save(out_path)
    return out_path
