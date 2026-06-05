"""
ui_engine.py — TCX Visual Engine
Style : Bloomberg Terminal / Institutional Dark
Polices : Space Mono (monospace terminal) + Inter pour le body
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
import requests
import textwrap
import math

# ============================================================
# PALETTE BLOOMBERG-INSPIRED
# ============================================================
BG          = "#0A0A0F"        # Noir quasi-total
PANEL       = "#12121A"        # Panneau légèrement plus clair
CARD        = "#1A1A26"        # Carte
BORDER      = "#2A2A3E"        # Bordures subtiles
TEXT_MAIN   = "#E8E8F0"        # Blanc cassé
TEXT_MUTED  = "#6B6B8A"        # Gris bleuté
TEXT_DIM    = "#3A3A56"        # Ultra discret
ACCENT      = "#00D4FF"        # Cyan TCX
GREEN       = "#00FF88"        # Vert néon
RED         = "#FF3355"        # Rouge vif
YELLOW      = "#FFB800"        # Ambre signal
PURPLE      = "#9B6DFF"        # Signal neutre
ORANGE      = "#FF6B35"        # Strong sell

SIGNAL_COLORS = {
    "STRONG BUY":  GREEN,
    "BUY":         "#00CC66",
    "NEUTRAL":     YELLOW,
    "SELL":        "#FF6677",
    "STRONG SELL": RED,
}

# ============================================================
# POLICES
# ============================================================
FONTS_CACHE = {}

def _dl(name, url):
    os.makedirs("assets", exist_ok=True)
    path = f"assets/{name}"
    if not os.path.exists(path):
        try:
            r = requests.get(url, timeout=10)
            with open(path, "wb") as f:
                f.write(r.content)
        except Exception as e:
            print(f"[FONT] Impossible de télécharger {name}: {e}")
    return path

def get_fonts():
    global FONTS_CACHE
    if FONTS_CACHE:
        return FONTS_CACHE

    # Space Mono — monospace institutionnel
    sm_bold = _dl("SpaceMono-Bold.ttf",
                  "https://github.com/googlefonts/spacemono/raw/main/fonts/SpaceMono-Bold.ttf")
    sm_reg  = _dl("SpaceMono-Regular.ttf",
                  "https://github.com/googlefonts/spacemono/raw/main/fonts/SpaceMono-Regular.ttf")
    # Inter — lisibilité
    inter_b = _dl("Inter-Bold.ttf",
                  "https://github.com/rsms/inter/raw/master/docs/font-files/Inter-Bold.ttf")
    inter_r = _dl("Inter-Regular.ttf",
                  "https://github.com/rsms/inter/raw/master/docs/font-files/Inter-Regular.ttf")
    inter_m = _dl("Inter-Medium.ttf",
                  "https://github.com/rsms/inter/raw/master/docs/font-files/Inter-Medium.ttf")

    def tf(path, size):
        try:
            return ImageFont.truetype(path, size)
        except Exception:
            return ImageFont.load_default()

    FONTS_CACHE = {
        "header":     tf(sm_bold,  42),
        "header_sm":  tf(sm_bold,  28),
        "subheader":  tf(inter_r,  20),
        "label":      tf(sm_reg,   16),
        "label_sm":   tf(sm_reg,   13),
        "symbol":     tf(sm_bold,  26),
        "price_lg":   tf(sm_bold,  38),
        "price_md":   tf(sm_bold,  28),
        "price_sm":   tf(sm_bold,  20),
        "pct_lg":     tf(inter_b,  22),
        "pct_sm":     tf(inter_b,  16),
        "body":       tf(inter_r,  18),
        "body_sm":    tf(inter_r,  15),
        "body_xs":    tf(inter_r,  13),
        "tag":        tf(inter_b,  14),
        "mono_sm":    tf(sm_reg,   14),
        "news_title": tf(inter_m,  17),
        "news_pub":   tf(inter_b,  14),
    }
    return FONTS_CACHE

# ============================================================
# HELPERS VISUELS
# ============================================================
def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def draw_rounded_rect(draw, xy, radius, fill=None, outline=None, width=1):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill, outline=outline, width=width)

def draw_sparkline(img, data_points, x, y, w, h, color_hex, filled=False):
    if not data_points or len(data_points) < 2:
        return
    min_v, max_v = min(data_points), max(data_points)
    if max_v == min_v:
        max_v += 0.001

    coords = []
    for i, v in enumerate(data_points):
        px = x + (i / (len(data_points) - 1)) * w
        py = y + h - ((v - min_v) / (max_v - min_v)) * h
        coords.append((px, py))

    r, g, b = hex_to_rgb(color_hex)

    if filled:
        # Zone remplie sous la courbe
        fill_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        fd = ImageDraw.Draw(fill_layer)
        poly = coords + [(coords[-1][0], y + h), (coords[0][0], y + h)]
        fd.polygon(poly, fill=(r, g, b, 30))
        img.paste(fill_layer, (0, 0), fill_layer)

    # Glow
    glow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow_layer)
    gd.line(coords, fill=(r, g, b, 80), width=6)
    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(4))
    img.paste(glow_layer, (0, 0), glow_layer)

    # Ligne principale
    draw = ImageDraw.Draw(img)
    draw.line(coords, fill=color_hex, width=2)

def draw_rsi_bar(draw, x, y, w, h, rsi_val, fonts):
    """Barre RSI avec zones colorées."""
    # Background
    draw_rounded_rect(draw, [x, y, x + w, y + h], 4, fill=BORDER)
    # Zone de progression
    pct = min(max(rsi_val / 100, 0), 1)
    fill_w = int((w - 2) * pct)
    if rsi_val < 30:    bar_col = GREEN
    elif rsi_val > 70:  bar_col = RED
    else:               bar_col = YELLOW
    if fill_w > 0:
        draw_rounded_rect(draw, [x + 1, y + 1, x + 1 + fill_w, y + h - 1], 3, fill=bar_col)
    # Labels zones
    draw.text((x + int(w * 0.28) - 4, y + h + 4), "30", fill=TEXT_DIM, font=fonts["label_sm"])
    draw.text((x + int(w * 0.70) - 4, y + h + 4), "70", fill=TEXT_DIM, font=fonts["label_sm"])

def draw_signal_badge(draw, x, y, signal_text, fonts):
    """Badge coloré pour le signal."""
    col = SIGNAL_COLORS.get(signal_text, YELLOW)
    r, g, b = hex_to_rgb(col)
    # Fond semi-transparent simulé
    draw_rounded_rect(draw, [x, y, x + 130, y + 26], 5, fill=f"#{r//3:02x}{g//3:02x}{b//3:02x}")
    draw_rounded_rect(draw, [x, y, x + 130, y + 26], 5, outline=col, width=1)
    # Centrer le texte
    draw.text((x + 8, y + 4), signal_text, fill=col, font=fonts["tag"])

def format_price(symbol, price):
    if "=X" in symbol:
        return f"{price:,.4f}"
    elif price < 0.01:
        return f"${price:,.6f}"
    elif price < 1:
        return f"${price:,.4f}"
    elif "^" in symbol:
        return f"{price:,.2f} pts"
    else:
        return f"${price:,.2f}"

def format_num(v):
    if v is None or v == "N/A": return "N/A"
    try:
        f = float(v)
        return f"{f:.2f}"
    except Exception:
        return str(v)

def perf_str(v):
    if v is None: return "N/A"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.2f}%"

def perf_col(v):
    if v is None: return TEXT_MUTED
    return GREEN if v >= 0 else RED

# ============================================================
# WATERMARK / FOOTER
# ============================================================
def draw_footer(draw, img_w, img_h, fonts):
    import datetime
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%d  %H:%M UTC")
    draw.text((30, img_h - 30), f"TCX TRADING SYSTEM  •  {ts}  •  Data: Yahoo Finance", fill=TEXT_DIM, font=fonts["label_sm"])
    draw.text((img_w - 220, img_h - 30), "NOT FINANCIAL ADVICE", fill=TEXT_DIM, font=fonts["label_sm"])


# ============================================================
# 1. DASHBOARD GLOBAL
# ============================================================
def generate_dashboard_image(data, title, filename):
    fonts  = get_fonts()
    W, H   = 1300, 720
    img    = Image.new("RGBA", (W, H), BG)
    draw   = ImageDraw.Draw(img)

    # Ligne décorative haut
    draw.rectangle([0, 0, W, 3], fill=ACCENT)

    # Header
    draw.text((30, 22), title, fill=TEXT_MAIN, font=fonts["header"])
    draw.text((30, 76), "Real-Time Market Intelligence  •  Technical Indicators Included", fill=TEXT_MUTED, font=fonts["subheader"])

    # Ligne séparatrice
    draw.line([(30, 108), (W - 30, 108)], fill=BORDER, width=1)

    cols, rows = 4, 2
    mx, my    = 30, 128
    gap       = 18
    bw        = (W - 2 * mx - (cols - 1) * gap) // cols
    bh        = (H - my - 50 - (rows - 1) * gap) // rows

    items = data[:8]
    for i, item in enumerate(items):
        cx = mx + (i % cols) * (bw + gap)
        cy = my + (i // cols) * (bh + gap)

        is_up     = item["change"] >= 0
        col_main  = GREEN if is_up else RED
        sign      = "+" if is_up else ""

        # Carte
        draw_rounded_rect(draw, [cx, cy, cx + bw, cy + bh], 12, fill=CARD)
        draw_rounded_rect(draw, [cx, cy, cx + bw, cy + bh], 12, outline=BORDER, width=1)

        # Barre gauche couleur
        draw.rectangle([cx, cy + 12, cx + 3, cy + bh - 12], fill=col_main)

        # Nom
        name = item["display_name"]
        if len(name) > 14: name = name[:13] + "…"
        draw.text((cx + 16, cy + 14), name, fill=TEXT_MAIN, font=fonts["symbol"])

        # Signal badge (si disponible)
        sig = item.get("signal")
        if sig:
            badge_col = SIGNAL_COLORS.get(sig, YELLOW)
            draw.text((cx + bw - 85, cy + 16), sig, fill=badge_col, font=fonts["label_sm"])

        # Prix
        price_str = format_price(item["raw_symbol"], item["price"])
        draw.text((cx + 16, cy + 50), price_str, fill=TEXT_MAIN, font=fonts["price_sm"])

        # % change
        draw.text((cx + 16, cy + 80), f"{sign}{item['change']:.2f}%", fill=col_main, font=fonts["pct_sm"])

        # Indicateurs condensés
        rsi = item.get("rsi")
        if rsi is not None:
            rsi_col = GREEN if rsi < 35 else (RED if rsi > 65 else TEXT_MUTED)
            draw.text((cx + bw - 80, cy + 52), f"RSI", fill=TEXT_DIM, font=fonts["label_sm"])
            draw.text((cx + bw - 80, cy + 66), f"{rsi:.0f}", fill=rsi_col, font=fonts["label"])

        macd_h = item.get("macd_hist")
        if macd_h is not None:
            mh_col = GREEN if macd_h > 0 else RED
            draw.text((cx + bw - 80, cy + 90), f"MACD", fill=TEXT_DIM, font=fonts["label_sm"])
            draw.text((cx + bw - 80, cy + 104), ("▲" if macd_h > 0 else "▼"), fill=mh_col, font=fonts["label"])

        # Sparkline
        spark_x = cx + 16
        spark_y = cy + bh - 72
        spark_w = bw - 32
        spark_h = 55
        draw_sparkline(img, item["history"][-30:], spark_x, spark_y, spark_w, spark_h, col_main, filled=True)

    draw_footer(draw, W, H, fonts)

    out = img.convert("RGB")
    os.makedirs("output", exist_ok=True)
    path = f"output/{filename}"
    out.save(path, quality=95)
    return path


# ============================================================
# 2. INTEL — Deep Report
# ============================================================
def generate_intel_image(data: dict):
    fonts  = get_fonts()
    W, H   = 1100, 1000
    ticker = data["raw_symbol"]
    img    = Image.new("RGBA", (W, H), BG)
    draw   = ImageDraw.Draw(img)

    is_up    = data["change"] >= 0
    col_main = GREEN if is_up else RED
    sign     = "+" if is_up else ""

    # Barre haut
    draw.rectangle([0, 0, W, 4], fill=col_main)

    # --- HEADER ---
    name_str = data["display_name"]
    draw.text((30, 22), name_str, fill=TEXT_MAIN, font=fonts["header"])
    draw.text((30, 76), f"{ticker}  •  AI Quantitative Report  •  1 Year History", fill=TEXT_MUTED, font=fonts["subheader"])

    # Prix + % top droite
    price_str = format_price(ticker, data["price"])
    pw = draw.textlength(price_str, font=fonts["price_lg"])
    draw.text((W - pw - 30, 20), price_str, fill=TEXT_MAIN, font=fonts["price_lg"])
    pct_str = f"{sign}{data['change']:.2f}%  Today"
    draw.text((W - 220, 78), pct_str, fill=col_main, font=fonts["pct_sm"])

    draw.line([(30, 115), (W - 30, 115)], fill=BORDER, width=1)

    # --- GRAPHIQUE 1 AN ---
    chart_x, chart_y, chart_w, chart_h = 30, 130, W - 60, 200
    draw_rounded_rect(draw, [chart_x, chart_y, chart_x + chart_w, chart_y + chart_h], 10, fill=PANEL)
    draw_sparkline(img, data["history"], chart_x + 10, chart_y + 10, chart_w - 20, chart_h - 20, col_main, filled=True)

    # EMA lines sur le graphique (overlay visuel simplifié)
    draw.text((chart_x + 10, chart_y + 8), "1Y PRICE HISTORY", fill=TEXT_DIM, font=fonts["label_sm"])

    # --- PERFORMANCES ---
    perf_y = chart_y + chart_h + 18
    draw.text((30, perf_y), "PERFORMANCE", fill=TEXT_MUTED, font=fonts["label"])
    draw.line([(30, perf_y + 22), (W - 30, perf_y + 22)], fill=BORDER, width=1)

    perfs = [
        ("1 DAY",  data["change"]),
        ("1 WEEK", data.get("perf_1w")),
        ("1 MONTH",data.get("perf_1m")),
        ("3 MONTHS",data.get("perf_3m")),
        ("YTD",    data.get("perf_ytd")),
    ]
    p_block_w = (W - 60) // len(perfs)
    for i, (label, val) in enumerate(perfs):
        px = 30 + i * p_block_w
        py = perf_y + 30
        draw_rounded_rect(draw, [px + 5, py, px + p_block_w - 5, py + 65], 8, fill=CARD)
        draw.text((px + 14, py + 8), label, fill=TEXT_MUTED, font=fonts["label_sm"])
        draw.text((px + 14, py + 30), perf_str(val), fill=perf_col(val), font=fonts["price_sm"])

    # --- INDICATEURS TECHNIQUES ---
    ind_y = perf_y + 120
    draw.text((30, ind_y), "TECHNICAL INDICATORS", fill=TEXT_MUTED, font=fonts["label"])
    draw.line([(30, ind_y + 22), (W - 30, ind_y + 22)], fill=BORDER, width=1)

    # Bloc RSI
    ri_x, ri_y = 30, ind_y + 35
    draw_rounded_rect(draw, [ri_x, ri_y, ri_x + 320, ri_y + 90], 10, fill=CARD)
    rsi_v = data.get("rsi", 50)
    rsi_c = GREEN if rsi_v < 30 else (RED if rsi_v > 70 else YELLOW)
    draw.text((ri_x + 12, ri_y + 8),  "RSI (14)", fill=TEXT_MUTED, font=fonts["label_sm"])
    draw.text((ri_x + 12, ri_y + 28), f"{rsi_v:.1f}", fill=rsi_c, font=fonts["header_sm"])
    status = "OVERSOLD" if rsi_v < 30 else ("OVERBOUGHT" if rsi_v > 70 else "NORMAL")
    draw.text((ri_x + 100, ri_y + 38), status, fill=rsi_c, font=fonts["label_sm"])
    draw_rsi_bar(draw, ri_x + 12, ri_y + 68, 296, 12, rsi_v, fonts)

    # Bloc MACD
    mac_x = ri_x + 340
    draw_rounded_rect(draw, [mac_x, ri_y, mac_x + 320, ri_y + 90], 10, fill=CARD)
    macd_v  = data.get("macd", 0)
    sig_v   = data.get("macd_sig", 0)
    hist_v  = data.get("macd_hist", 0)
    hist_c  = GREEN if hist_v > 0 else RED
    draw.text((mac_x + 12, ri_y + 8),  "MACD (12,26,9)", fill=TEXT_MUTED, font=fonts["label_sm"])
    draw.text((mac_x + 12, ri_y + 28), f"{macd_v:+.4f}", fill=hist_c, font=fonts["price_sm"])
    draw.text((mac_x + 12, ri_y + 55), f"Signal : {sig_v:.4f}", fill=TEXT_MUTED, font=fonts["body_sm"])
    draw.text((mac_x + 12, ri_y + 74), f"Hist : {hist_v:+.4f}", fill=hist_c, font=fonts["body_sm"])
    cross = "BULLISH CROSS ▲" if hist_v > 0 else "BEARISH CROSS ▼"
    draw.text((mac_x + 160, ri_y + 74), cross, fill=hist_c, font=fonts["label_sm"])

    # Bloc Stochastique
    st_x = mac_x + 340
    draw_rounded_rect(draw, [st_x, ri_y, st_x + 300, ri_y + 90], 10, fill=CARD)
    stoch_v = data.get("stoch", 50)
    stoch_c = GREEN if stoch_v < 25 else (RED if stoch_v > 75 else YELLOW)
    draw.text((st_x + 12, ri_y + 8),  "STOCHASTIC (14)", fill=TEXT_MUTED, font=fonts["label_sm"])
    draw.text((st_x + 12, ri_y + 28), f"{stoch_v:.1f}", fill=stoch_c, font=fonts["header_sm"])
    s_status = "OVERSOLD" if stoch_v < 25 else ("OVERBOUGHT" if stoch_v > 75 else "NEUTRAL")
    draw.text((st_x + 100, ri_y + 38), s_status, fill=stoch_c, font=fonts["label_sm"])

    # Bloc EMAs
    ema_y = ri_y + 108
    draw_rounded_rect(draw, [30, ema_y, W - 30, ema_y + 75], 10, fill=CARD)
    draw.text((42, ema_y + 10), "MOVING AVERAGES", fill=TEXT_MUTED, font=fonts["label_sm"])
    curr = data["price"]
    emas = [
        ("EMA 20",  data.get("ema20")),
        ("EMA 50",  data.get("ema50")),
        ("EMA 200", data.get("ema200")),
        ("BB UPPER",data.get("bb_upper")),
        ("BB MID",  data.get("bb_mid")),
        ("BB LOWER",data.get("bb_lower")),
    ]
    ema_bw = (W - 80) // len(emas)
    for j, (lbl, val) in enumerate(emas):
        ex = 40 + j * ema_bw
        ey = ema_y + 28
        draw.text((ex, ey), lbl, fill=TEXT_DIM, font=fonts["label_sm"])
        if val:
            vc = GREEN if curr > val else RED
            draw.text((ex, ey + 18), format_price(ticker, val), fill=vc, font=fonts["label"])
            arrow = " ▲" if curr > val else " ▼"
            draw.text((ex + 80, ey + 18), arrow, fill=vc, font=fonts["label_sm"])
        else:
            draw.text((ex, ey + 18), "N/A", fill=TEXT_DIM, font=fonts["label"])

    # Bloc Momentum + Signal Global
    sig_y = ema_y + 93
    draw_rounded_rect(draw, [30, sig_y, W // 2 - 20, sig_y + 70], 10, fill=CARD)
    mom_v = data.get("momentum", 0)
    draw.text((42, sig_y + 8),  "MOMENTUM (10p)", fill=TEXT_MUTED, font=fonts["label_sm"])
    draw.text((42, sig_y + 28), f"{mom_v:+.2f}%", fill=(GREEN if mom_v > 0 else RED), font=fonts["price_md"])

    sig_txt = data.get("signal", "NEUTRAL")
    sig_col = SIGNAL_COLORS.get(sig_txt, YELLOW)
    bc = data.get("bull_count", 0)
    bear_c = data.get("bear_count", 0)
    draw_rounded_rect(draw, [W // 2 + 20, sig_y, W - 30, sig_y + 70], 10, fill=CARD)
    draw.text((W // 2 + 32, sig_y + 8), "GLOBAL SIGNAL", fill=TEXT_MUTED, font=fonts["label_sm"])
    draw.text((W // 2 + 32, sig_y + 28), sig_txt, fill=sig_col, font=fonts["price_md"])
    draw.text((W // 2 + 280, sig_y + 32), f"▲{bc} / ▼{bear_c}", fill=TEXT_DIM, font=fonts["label_sm"])

    # --- FONDAMENTAUX ---
    fund_y = sig_y + 88
    draw.text((30, fund_y), "FUNDAMENTALS", fill=TEXT_MUTED, font=fonts["label"])
    draw.line([(30, fund_y + 22), (W - 30, fund_y + 22)], fill=BORDER, width=1)

    stats = [
        ("MARKET CAP",  data.get("mcap",   "N/A")),
        ("P/E RATIO",   format_num(data.get("pe"))),
        ("52W HIGH",    f"${data['high52']:.2f}" if data.get("high52") else "N/A"),
        ("52W LOW",     f"${data['low52']:.2f}"  if data.get("low52")  else "N/A"),
        ("CONSENSUS",   data.get("recom", "N/A")),
        ("1Y TARGET",   f"${data['target']:.2f}" if data.get("target") else "N/A"),
    ]
    sb_w = (W - 60) // 6
    for k, (lbl, val) in enumerate(stats):
        fx = 30 + k * sb_w
        fy = fund_y + 30
        draw_rounded_rect(draw, [fx + 4, fy, fx + sb_w - 4, fy + 60], 8, fill=CARD)
        draw.text((fx + 12, fy + 8), lbl, fill=TEXT_DIM, font=fonts["label_sm"])
        vc = TEXT_MAIN
        if "BUY" in str(val) or "BULL" in str(val): vc = GREEN
        elif "SELL" in str(val) or "BEAR" in str(val): vc = RED
        draw.text((fx + 12, fy + 28), str(val), fill=vc, font=fonts["label"])

    # Sentiment
    sent_y = fund_y + 110
    draw.text((30, sent_y), "AI NEWS SENTIMENT", fill=TEXT_MUTED, font=fonts["label"])
    sc = GREEN if "BULLISH" in data.get("sentiment","") else (RED if "BEARISH" in data.get("sentiment","") else YELLOW)
    draw.text((240, sent_y), data.get("sentiment", "N/A"), fill=sc, font=fonts["label"])

    # News
    news_y = sent_y + 30
    draw.line([(30, news_y), (W - 30, news_y)], fill=BORDER, width=1)
    news_y += 10

    for article in data.get("news", [])[:3]:
        draw_rounded_rect(draw, [30, news_y, W - 30, news_y + 72], 10, fill=CARD)
        draw.text((46, news_y + 8),  f"▌ {article.get('publisher','').upper()}", fill=ACCENT, font=fonts["news_pub"])
        title = textwrap.shorten(article.get("title",""), width=88, placeholder="…")
        draw.text((46, news_y + 34), title, fill=TEXT_MAIN, font=fonts["news_title"])
        news_y += 82

    draw_footer(draw, W, H, fonts)

    out = img.convert("RGB")
    os.makedirs("output", exist_ok=True)
    path = f"output/intel_{ticker}.png"
    out.save(path, quality=95)
    return path


# ============================================================
# 3. SCAN
# ============================================================
def generate_scan_image(data: list, filtre: str):
    fonts = get_fonts()
    rows  = len(data)
    W     = 1100
    H     = 80 + rows * 72 + 60
    img   = Image.new("RGBA", (W, H), BG)
    draw  = ImageDraw.Draw(img)

    draw.rectangle([0, 0, W, 4], fill=PURPLE)
    draw.text((30, 16), "MARKET SCANNER", fill=TEXT_MAIN, font=fonts["header"])
    draw.text((30, 66), f"Filter : {filtre.upper()}  •  {rows} signal(s) detected", fill=TEXT_MUTED, font=fonts["subheader"])
    draw.line([(30, 98), (W - 30, 98)], fill=BORDER, width=1)

    # Colonnes header
    cols_x = [30, 200, 340, 440, 540, 640, 740, 860, 980]
    headers = ["ASSET", "PRICE", "CHANGE", "RSI", "MACD▲▼", "STOCH", "EMA20", "SIGNAL", "SPARK"]
    for i, (hx, ht) in enumerate(zip(cols_x, headers)):
        draw.text((hx, 108), ht, fill=TEXT_DIM, font=fonts["mono_sm"])

    draw.line([(30, 126), (W - 30, 126)], fill=BORDER, width=1)

    for row_i, item in enumerate(data):
        ry    = 134 + row_i * 72
        is_up = item["change"] >= 0
        col_c = GREEN if is_up else RED
        sign  = "+" if is_up else ""

        # Alternance fond
        if row_i % 2 == 0:
            draw.rectangle([30, ry - 4, W - 30, ry + 60], fill="#0F0F18")

        # Asset
        nm = item["display_name"]
        if len(nm) > 12: nm = nm[:11] + "…"
        draw.text((cols_x[0], ry + 8), nm, fill=TEXT_MAIN, font=fonts["symbol"])

        # Prix
        draw.text((cols_x[1], ry + 8), format_price(item["raw_symbol"], item["price"]), fill=TEXT_MAIN, font=fonts["label"])

        # Change
        draw.text((cols_x[2], ry + 8), f"{sign}{item['change']:.2f}%", fill=col_c, font=fonts["label"])

        # RSI
        rsi_v = item.get("rsi")
        if rsi_v is not None:
            rc = GREEN if rsi_v < 30 else (RED if rsi_v > 70 else YELLOW)
            draw.text((cols_x[3], ry + 8), f"{rsi_v:.0f}", fill=rc, font=fonts["label"])

        # MACD hist
        mh = item.get("macd_hist")
        if mh is not None:
            mc = GREEN if mh > 0 else RED
            sym = "▲" if mh > 0 else "▼"
            draw.text((cols_x[4], ry + 8), f"{sym} {abs(mh):.4f}", fill=mc, font=fonts["label_sm"])

        # Stoch
        st = item.get("stoch")
        if st is not None:
            sc_col = GREEN if st < 25 else (RED if st > 75 else YELLOW)
            draw.text((cols_x[5], ry + 8), f"{st:.0f}", fill=sc_col, font=fonts["label"])

        # EMA20 vs prix
        ema20 = item.get("ema20")
        if ema20:
            above = item["price"] > ema20
            draw.text((cols_x[6], ry + 8), "ABOVE" if above else "BELOW", fill=(GREEN if above else RED), font=fonts["label_sm"])

        # Signal badge
        sig = item.get("signal", "NEUTRAL")
        sig_col = SIGNAL_COLORS.get(sig, YELLOW)
        draw_rounded_rect(draw, [cols_x[7] - 4, ry + 2, cols_x[7] + 128, ry + 26], 5, fill=CARD, outline=sig_col, width=1)
        draw.text((cols_x[7] + 2, ry + 5), sig, fill=sig_col, font=fonts["tag"])

        # Mini Sparkline
        hist = item.get("history", [])[-20:]
        draw_sparkline(img, hist, cols_x[8], ry + 4, W - cols_x[8] - 30, 50, col_c)

    draw_footer(draw, W, H, fonts)
    out = img.convert("RGB")
    os.makedirs("output", exist_ok=True)
    path = "output/scan_result.png"
    out.save(path, quality=95)
    return path


# ============================================================
# 4. COMPARE
# ============================================================
def generate_compare_image(d1: dict, d2: dict):
    fonts = get_fonts()
    W, H  = 1200, 860
    img   = Image.new("RGBA", (W, H), BG)
    draw  = ImageDraw.Draw(img)

    # En-tête
    draw.rectangle([0, 0, W, 4], fill=ACCENT)
    n1 = d1["display_name"]
    n2 = d2["display_name"]
    draw.text((30, 18), f"{n1}  vs  {n2}", fill=TEXT_MAIN, font=fonts["header"])
    draw.text((30, 72), "Side-by-Side Comparison  •  Technical + Fundamental Analysis", fill=TEXT_MUTED, font=fonts["subheader"])
    draw.line([(30, 108), (W - 30, 108)], fill=BORDER, width=1)

    col_w  = (W - 90) // 2
    starts = [30, 30 + col_w + 30]
    datas  = [d1, d2]
    accent_cols = [ACCENT, PURPLE]

    for side, (dx, data, ac) in enumerate(zip(starts, datas, accent_cols)):
        ticker  = data["raw_symbol"]
        is_up   = data["change"] >= 0
        col_c   = GREEN if is_up else RED
        sign    = "+" if is_up else ""

        # Carte principale
        draw_rounded_rect(draw, [dx, 116, dx + col_w, H - 50], 14, fill=PANEL, outline=ac, width=2)

        # Nom + prix
        draw.text((dx + 20, 128), data["display_name"], fill=TEXT_MAIN, font=fonts["header_sm"])
        draw.text((dx + 20, 162), ticker, fill=TEXT_MUTED, font=fonts["subheader"])
        ps = format_price(ticker, data["price"])
        pw = draw.textlength(ps, font=fonts["price_md"])
        draw.text((dx + col_w - pw - 20, 128), ps, fill=TEXT_MAIN, font=fonts["price_md"])
        draw.text((dx + col_w - 120, 164), f"{sign}{data['change']:.2f}%", fill=col_c, font=fonts["pct_sm"])

        draw.line([(dx + 16, 194), (dx + col_w - 16, 194)], fill=BORDER, width=1)

        # Graphique 6 mois
        draw_rounded_rect(draw, [dx + 16, 202, dx + col_w - 16, 302], 8, fill=CARD)
        draw_sparkline(img, data["history"][-120:], dx + 24, 210, col_w - 56, 84, col_c, filled=True)
        draw.text((dx + 22, 205), "6M CHART", fill=TEXT_DIM, font=fonts["label_sm"])

        # Perfs
        py = 312
        draw.text((dx + 20, py), "PERFORMANCE", fill=TEXT_MUTED, font=fonts["label_sm"])
        perfs = [("1D", data["change"]), ("1W", data.get("perf_1w")), ("1M", data.get("perf_1m")), ("YTD", data.get("perf_ytd"))]
        for pi, (pl, pv) in enumerate(perfs):
            px2 = dx + 20 + pi * (col_w // 4)
            draw.text((px2, py + 20), pl, fill=TEXT_DIM, font=fonts["mono_sm"])
            draw.text((px2, py + 36), perf_str(pv), fill=perf_col(pv), font=fonts["label"])

        # Indicateurs techniques
        ty = py + 75
        draw.line([(dx + 16, ty), (dx + col_w - 16, ty)], fill=BORDER, width=1)
        draw.text((dx + 20, ty + 8), "TECHNICAL", fill=TEXT_MUTED, font=fonts["label_sm"])

        tech = [
            ("RSI (14)",    f"{data.get('rsi', 'N/A'):.0f}" if data.get("rsi") else "N/A",
             GREEN if (data.get("rsi") or 50) < 35 else (RED if (data.get("rsi") or 50) > 65 else TEXT_MAIN)),
            ("MACD HIST",   f"{data.get('macd_hist', 0):+.4f}",
             GREEN if (data.get("macd_hist") or 0) > 0 else RED),
            ("STOCH",       f"{data.get('stoch', 50):.0f}",
             GREEN if (data.get("stoch") or 50) < 25 else (RED if (data.get("stoch") or 50) > 75 else TEXT_MAIN)),
            ("MOMENTUM",    f"{data.get('momentum', 0):+.2f}%",
             GREEN if (data.get("momentum") or 0) > 0 else RED),
        ]
        for ti, (tl, tv, tc) in enumerate(tech):
            tx2 = dx + 20 + (ti % 2) * (col_w // 2)
            ty2 = ty + 26 + (ti // 2) * 42
            draw.text((tx2, ty2), tl, fill=TEXT_DIM, font=fonts["mono_sm"])
            draw.text((tx2, ty2 + 16), tv, fill=tc, font=fonts["label"])

        # EMA status
        emy = ty + 120
        draw.line([(dx + 16, emy), (dx + col_w - 16, emy)], fill=BORDER, width=1)
        draw.text((dx + 20, emy + 8), "PRICE vs EMAs", fill=TEXT_MUTED, font=fonts["label_sm"])
        curr = data["price"]
        for ei, (el, ev) in enumerate([("EMA20", data.get("ema20")), ("EMA50", data.get("ema50")), ("EMA200", data.get("ema200"))]):
            ex2 = dx + 20 + ei * (col_w // 3)
            draw.text((ex2, emy + 26), el, fill=TEXT_DIM, font=fonts["mono_sm"])
            if ev:
                ec = GREEN if curr > ev else RED
                ar = "▲" if curr > ev else "▼"
                draw.text((ex2, emy + 42), ar, fill=ec, font=fonts["label"])
            else:
                draw.text((ex2, emy + 42), "N/A", fill=TEXT_DIM, font=fonts["label_sm"])

        # Signal global
        sig_y2 = emy + 82
        draw.line([(dx + 16, sig_y2), (dx + col_w - 16, sig_y2)], fill=BORDER, width=1)
        sig  = data.get("signal", "NEUTRAL")
        sc   = SIGNAL_COLORS.get(sig, YELLOW)
        draw.text((dx + 20, sig_y2 + 10), "GLOBAL SIGNAL", fill=TEXT_MUTED, font=fonts["label_sm"])
        draw.text((dx + 20, sig_y2 + 30), sig, fill=sc, font=fonts["price_md"])
        bc   = data.get("bull_count", 0)
        berc = data.get("bear_count", 0)
        draw.text((dx + 20, sig_y2 + 66), f"▲ {bc} Bullish signals  /  ▼ {berc} Bearish signals", fill=TEXT_DIM, font=fonts["label_sm"])

        # Fondamentaux
        fy2 = sig_y2 + 100
        draw.line([(dx + 16, fy2), (dx + col_w - 16, fy2)], fill=BORDER, width=1)
        draw.text((dx + 20, fy2 + 8), "FUNDAMENTALS", fill=TEXT_MUTED, font=fonts["label_sm"])
        fund_items = [
            ("MKT CAP", data.get("mcap", "N/A")),
            ("P/E",     format_num(data.get("pe"))),
            ("52W H",   f"${data['high52']:.2f}" if data.get("high52") else "N/A"),
            ("TARGET",  f"${data['target']:.2f}" if data.get("target") else "N/A"),
        ]
        for fi, (fl, fv) in enumerate(fund_items):
            fx2 = dx + 20 + (fi % 2) * (col_w // 2)
            fy3 = fy2 + 28 + (fi // 2) * 36
            draw.text((fx2, fy3), fl, fill=TEXT_DIM, font=fonts["mono_sm"])
            draw.text((fx2, fy3 + 14), str(fv), fill=TEXT_MAIN, font=fonts["label"])

    draw_footer(draw, W, H, fonts)

    # Séparateur central
    cx_sep = 30 + col_w + 15
    draw.line([(cx_sep, 116), (cx_sep, H - 50)], fill=BORDER, width=1)

    # Verdict final
    b1 = d1.get("bull_count", 0)
    b2 = d2.get("bull_count", 0)
    verdict_y = H - 92
    draw.line([(30, verdict_y - 10), (W - 30, verdict_y - 10)], fill=BORDER, width=1)
    draw.text((W // 2 - 100, verdict_y), "ALGORITHMIC EDGE", fill=TEXT_DIM, font=fonts["mono_sm"])
    if b1 > b2:
        winner = d1["display_name"]
        wc = accent_cols[0]
    elif b2 > b1:
        winner = d2["display_name"]
        wc = accent_cols[1]
    else:
        winner = "TIED"
        wc = YELLOW
    wstr = f"▶  {winner}  has stronger technical signals  ({max(b1,b2)}/6)"
    ww = draw.textlength(wstr, font=fonts["label"])
    draw.text((W // 2 - ww // 2, verdict_y + 18), wstr, fill=wc, font=fonts["label"])

    out = img.convert("RGB")
    os.makedirs("output", exist_ok=True)
    path = "output/compare_result.png"
    out.save(path, quality=95)
    return path
