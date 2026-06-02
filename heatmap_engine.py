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
    if not data_points or len(data_points) < 2:
        return
    min_val, max_val = min(data_points), max(data_points)
    if max_val == min_val: max_val += 0.01

    coords = []
    for i, val in enumerate(data_points):
        px = x + (i / (len(data_points) - 1)) * w
        py = y + h - ((val - min_val) / (max_val - min_val)) * h
        coords.append((px, py))

    # Glow effect
    glow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    glow_draw = ImageDraw.Draw(glow_layer)
    glow_draw.line(coords, fill=color, width=10, joint="curve")
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(10))
    img.paste(glow_layer, (0, 0), glow_layer)

    # Ligne principale
    draw = ImageDraw.Draw(img)
    draw.line(coords, fill=color, width=3, joint="curve")

def generate_market_dashboard(data):
    """Génère un dashboard Fintech de niveau institutionnel."""
    url_bold = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"
    url_med = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Medium.ttf"
    url_reg = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Regular.ttf"
    
    p_bold = download_font("Roboto-Bold.ttf", url_bold)
    p_med = download_font("Roboto-Medium.ttf", url_med)
    p_reg = download_font("Roboto-Regular.ttf", url_reg)
    
    try:
        f_head = ImageFont.truetype(p_bold, 42)
        f_sub = ImageFont.truetype(p_reg, 20)
        f_sym = ImageFont.truetype(p_bold, 32)
        f_price = ImageFont.truetype(p_bold, 36)
        f_pct = ImageFont.truetype(p_med, 22)
        f_mini = ImageFont.truetype(p_reg, 16)
    except:
        f_head = f_sub = f_sym = f_price = f_pct = f_mini = ImageFont.load_default()

    # Couleurs UI Modernes (Style Terminal)
    BG_COLOR = "#0A0B10"
    CARD_COLOR = "#13141C"
    TEXT_MAIN = "#FFFFFF"
    TEXT_MUTED = "#7A7E93"
    
    GREEN_GLOW = (0, 230, 118, 160)
    RED_GLOW = (255, 59, 48, 160)
    GREEN_HEX = "#00E676"
    RED_HEX = "#FF3B30"

    width, height = 1200, 700
    img = Image.new("RGBA", (width, height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # Header
    draw.text((50, 40), "QUANTITATIVE MARKET DASHBOARD", fill=TEXT_MAIN, font=f_head)
    draw.text((50, 95), "Top Tech Assets • Real-Time AI Tracking • 7D Sparklines", fill=TEXT_MUTED, font=f_sub)

    cols, rows = 4, 2
    margin_x, margin_y = 50, 160
    gap = 25
    block_w = (width - (2 * margin_x) - (cols - 1) * gap) // cols
    block_h = (height - margin_y - 50 - (rows - 1) * gap) // rows

    for i, item in enumerate(data):
        x = margin_x + (i % cols) * (block_w + gap)
        y = margin_y + (i // cols) * (block_h + gap)
        
        draw.rounded_rectangle([x, y, x + block_w, y + block_h], radius=16, fill=CARD_COLOR)
        
        is_up = item['change'] >= 0
        glow_color = GREEN_GLOW if is_up else RED_GLOW
        hex_color = GREEN_HEX if is_up else RED_HEX
        sign = "+" if is_up else ""

        # Infos Principales
        draw.text((x + 20, y + 20), item['symbol'], fill=TEXT_MAIN, font=f_sym)
        draw.text((x + 20, y + 65), f"${item['price']:,.2f}", fill=TEXT_MAIN, font=f_price)
        draw.text((x + 20, y + 115), f"{sign}{item['change']:.2f}%", fill=hex_color, font=f_pct)

        # Indicateurs Techniques (RSI & Volume)
        rsi = item.get('rsi', 50)
        rsi_color = RED_HEX if rsi > 70 else (GREEN_HEX if rsi < 30 else TEXT_MUTED)
        draw.text((x + 20, y + 160), f"RSI: {rsi:.1f}", fill=rsi_color, font=f_mini)
        
        vol_str = f"{item['volume']/1000000:.1f}M" if item['volume'] > 0 else "N/A"
        draw.text((x + 120, y + 160), f"VOL: {vol_str}", fill=TEXT_MUTED, font=f_mini)

        # Sparkline
        draw_sparkline(img, item['history'], x + 120, y + 70, block_w - 140, 60, glow_color)

    final_img = img.convert("RGB")
    os.makedirs("output", exist_ok=True)
    output_path = "output/market_dashboard.png"
    final_img.save(output_path)
    return output_path
