"""
ui_engine.py — TCX Visual Engine v2
Direction : "Exchange Floor at Night" — institutional terminal redone with
a real signature element instead of generic neon-on-black.

Signature : SENTIMENT PULSE STRIP — a heartbeat-style ribbon of ticks, one
per asset, height = magnitude of move, colour = direction. It turns the
header into a live readout of the whole watchlist instead of decoration.

Palette  : near-black ink (#07080C) + warm signal gold (#F0B429) as the one
bold accent, cyan reserved for secondary/structural use only.
Type     : Space Mono (numbers/labels, terminal cadence) + Inter (prose).
"""

from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os
import requests
import textwrap
import math
import datetime

# ============================================================
# DESIGN TOKENS
# ============================================================
BG       = "#07080C"   # ink — near-black, faint blue undertone
PANEL    = "#0E1016"   # raised panel
CARD     = "#141722"   # card surface
CARD_ALT = "#10131B"   # zebra row
BORDER   = "#222636"   # hairline
TEXT_MAIN  = "#ECEDF3"
TEXT_MUTED = "#767C90"
TEXT_DIM   = "#3C4053"

GOLD   = "#F0B429"   # signature accent — used sparingly, on purpose
CYAN   = "#2DD4FF"   # secondary / structural only
UP     = "#34D399"   # emerald, calmer than neon green
DOWN   = "#FB5C6C"   # coral red
WARN   = "#F0B429"
PURPLE = "#8B7CF6"

SIGNAL_COLORS = {
    "STRONG BUY":  UP,
    "BUY":         "#5EEAA8",
    "NEUTRAL":     GOLD,
    "SELL":        "#FF8C97",
    "STRONG SELL": DOWN,
}

# ============================================================
# FONTS
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

    sm_bold = _dl("SpaceMono-Bold.ttf",
        "https://github.com/googlefonts/spacemono/raw/main/fonts/SpaceMono-Bold.ttf")
    sm_reg = _dl("SpaceMono-Regular.ttf",
        "https://github.com/googlefonts/spacemono/raw/main/fonts/SpaceMono-Regular.ttf")
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
        "wordmark":   tf(sm_bold, 22),
        "header":     tf(sm_bold, 40),
        "header_sm":  tf(sm_bold, 27),
        "subheader":  tf(inter_r, 19),
        "label":      tf(sm_reg, 16),
        "label_sm":   tf(sm_reg, 13),
        "symbol":     tf(sm_bold, 25),
        "price_lg":   tf(sm_bold, 37),
        "price_md":   tf(sm_bold, 27),
        "price_sm":   tf(sm_bold, 19),
        "pct_lg":     tf(inter_b, 21),
        "pct_sm":     tf(inter_b, 15),
        "body":       tf(inter_r, 18),
        "body_sm":    tf(inter_r, 15),
        "body_xs":    tf(inter_r, 13),
        "tag":        tf(inter_b, 13),
        "mono_sm":    tf(sm_reg, 13),
        "news_title": tf(inter_m, 17),
        "news_pub":   tf(inter_b, 14),
    }
    return FONTS_CACHE

# ============================================================
# VISUAL HELPERS
# ============================================================
def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))

def draw_rounded_rect(draw, xy, radius, fill=None, outline=None, width=1):
    x1, y1, x2, y2 = xy
    draw.rounded_rectangle([x1, y1, x2, y2], radius=radius, fill=fill, outline=outline, width=width)

def draw_hairline_grid(img, x, y, w, h, step=28):
    """Very faint vertical hairlines inside a card — terminal texture, not noise."""
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    gx = x + step
    while gx < x + w:
        od.line([(gx, y), (gx, y + h)], fill=(255, 255, 255, 5), width=1)
        gx += step
    img.paste(overlay, (0, 0), overlay)

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
        fill_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        fd = ImageDraw.Draw(fill_layer)
        poly = coords + [(coords[-1][0], y + h), (coords[0][0], y + h)]
        fd.polygon(poly, fill=(r, g, b, 26))
        img.paste(fill_layer, (0, 0), fill_layer)
        glow_layer = Image.new("RGBA", img.size, (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow_layer)
        gd.line(coords, fill=(r, g, b, 70), width=6)
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(4))
        img.paste(glow_layer, (0, 0), glow_layer)
    draw = ImageDraw.Draw(img)
    draw.line(coords, fill=color_hex, width=2)

def draw_pulse_strip(img, items, x, y, w, h):
    """
    SIGNATURE ELEMENT.
    One tick per asset: height encodes |% change| (capped), colour encodes
    direction. A flat gold baseline runs through the middle like a trace
    waiting for a signal. This makes the chrome itself a live readout of
    the whole watchlist, not decoration.
    """
    draw = ImageDraw.Draw(img)
    mid = y + h / 2
    draw.line([(x, mid), (x + w, mid)], fill=BORDER, width=1)
    n = max(len(items), 1)
    slot = w / n
    cap = 4.0  # % move that maxes out the tick
    for i, it in enumerate(items):
        chg = it.get("change", 0.0)
        mag = min(abs(chg) / cap, 1.0)
        tick_h = 3 + mag * (h / 2 - 3)
        col = UP if chg >= 0 else DOWN
        cx = x + slot * i + slot * 0.5
        draw.line([(cx, mid - tick_h), (cx, mid + tick_h)], fill=col, width=3)
    # gold pulse dot signature mark at the very start of the strip
    draw.ellipse([x - 5, mid - 5, x + 5, mid + 5], fill=GOLD)

def draw_rsi_bar(draw, x, y, w, h, rsi_val, fonts):
    draw_rounded_rect(draw, [x, y, x + w, y + h], 4, fill=BORDER)
    pct = min(max(rsi_val / 100, 0), 1)
    fill_w = int((w - 2) * pct)
    if rsi_val < 30: bar_col = UP
    elif rsi_val > 70: bar_col = DOWN
    else: bar_col = GOLD
    if fill_w > 0:
        draw_rounded_rect(draw, [x + 1, y + 1, x + 1 + fill_w, y + h - 1], 3, fill=bar_col)
    draw.text((x + int(w * 0.28) - 4, y + h + 4), "30", fill=TEXT_DIM, font=fonts["label_sm"])
    draw.text((x + int(w * 0.70) - 4, y + h + 4), "70", fill=TEXT_DIM, font=fonts["label_sm"])

def draw_signal_badge(draw, x, y, signal_text, fonts, w=128):
    col = SIGNAL_COLORS.get(signal_text, GOLD)
    r, g, b = hex_to_rgb(col)
    draw_rounded_rect(draw, [x, y, x + w, y + 24], 12, fill=f"#{r//4:02x}{g//4:02x}{b//4:02x}")
    draw_rounded_rect(draw, [x, y, x + w, y + 24], 12, outline=col, width=1)
    tw = draw.textlength(signal_text, font=fonts["tag"])
    draw.text((x + (w - tw) / 2, y + 5), signal_text, fill=col, font=fonts["tag"])

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
        return f"{float(v):.2f}"
    except Exception:
        return str(v)

def perf_str(v):
    if v is None: return "N/A"
    sign = "+" if v >= 0 else ""
    return f"{sign}{v:.2f}%"

def perf_col(v):
    if v is None: return TEXT_MUTED
    return UP if v >= 0 else DOWN

# ============================================================
# WORDMARK / FOOTER
# ============================================================
def draw_wordmark(draw, x, y, fonts):
    draw.rectangle([x, y + 2, x + 4, y + 19], fill=GOLD)
    draw.text((x + 11, y), "TCX", fill=GOLD, font=fonts["wordmark"])

def draw_footer(draw, img_w, img_h, fonts):
    ts = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")
    draw.line([(30, img_h - 44), (img_w - 30, img_h - 44)], fill=BORDER, width=1)
    draw_wordmark(draw, 30, img_h - 32, fonts)
    draw.text((100, img_h - 29), f"TRADING SYSTEM - {ts} - Data: Yahoo Finance",
               fill=TEXT_DIM, font=fonts["label_sm"])
    note = "NOT FINANCIAL ADVICE"
    nw = draw.textlength(note, font=fonts["label_sm"])
    draw.text((img_w - 30 - nw, img_h - 29), note, fill=TEXT_DIM, font=fonts["label_sm"])

# ============================================================
# 1. DASHBOARD GLOBAL
# ============================================================
def generate_dashboard_image(data, title, filename):
    fonts = get_fonts()
    W, H = 1320, 760
    img = Image.new("RGBA", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # Header
    draw_wordmark(draw, 30, 26, fonts)
    draw.text((30, 56), title, fill=TEXT_MAIN, font=fonts["header"])
    draw.text((30, 110), "Real-Time Market Intelligence - Technical Indicators Included",
               fill=TEXT_MUTED, font=fonts["subheader"])

    # Signature pulse strip — one tick per asset shown below
    items = data[:8]
    draw_pulse_strip(img, items, 30, 142, W - 60, 34)
    draw.line([(30, 188), (W - 30, 188)], fill=BORDER, width=1)

    cols, rows = 4, 2
    mx, my = 30, 206
    gap = 18
    bw = (W - 2 * mx - (cols - 1) * gap) // cols
    bh = (H - my - 64 - (rows - 1) * gap) // rows

    for i, item in enumerate(items):
        cx = mx + (i % cols) * (bw + gap)
        cy = my + (i // cols) * (bh + gap)
        is_up = item["change"] >= 0
        col_main = UP if is_up else DOWN
        sign = "+" if is_up else ""

        draw_rounded_rect(draw, [cx, cy, cx + bw, cy + bh], 14, fill=CARD)
        draw_rounded_rect(draw, [cx, cy, cx + bw, cy + bh], 14, outline=BORDER, width=1)
        draw_hairline_grid(img, cx, cy, bw, bh, step=26)
        draw = ImageDraw.Draw(img)

        # top accent edge instead of left bar — quieter, still legible
        draw_rounded_rect(draw, [cx + 14, cy, cx + 14 + 34, cy + 4], 2, fill=col_main)

        name = item["display_name"]
        if len(name) > 14: name = name[:13] + "…"
        draw.text((cx + 16, cy + 16), name, fill=TEXT_MAIN, font=fonts["symbol"])

        sig = item.get("signal")
        if sig:
            badge_col = SIGNAL_COLORS.get(sig, GOLD)
            sw = draw.textlength(sig, font=fonts["label_sm"])
            draw.text((cx + bw - 16 - sw, cy + 19), sig, fill=badge_col, font=fonts["label_sm"])

        price_str = format_price(item["raw_symbol"], item["price"])
        draw.text((cx + 16, cy + 52), price_str, fill=TEXT_MAIN, font=fonts["price_sm"])
        draw.text((cx + 16, cy + 82), f"{sign}{item['change']:.2f}%", fill=col_main, font=fonts["pct_sm"])

        rsi = item.get("rsi")
        if rsi is not None:
            rsi_col = UP if rsi < 35 else (DOWN if rsi > 65 else TEXT_MUTED)
            draw.text((cx + bw - 78, cy + 54), "RSI", fill=TEXT_DIM, font=fonts["label_sm"])
            draw.text((cx + bw - 78, cy + 68), f"{rsi:.0f}", fill=rsi_col, font=fonts["label"])

        macd_h = item.get("macd_hist")
        if macd_h is not None:
            mh_col = UP if macd_h > 0 else DOWN
            draw.text((cx + bw - 78, cy + 92), "MACD", fill=TEXT_DIM, font=fonts["label_sm"])
            draw.text((cx + bw - 78, cy + 106), ("^" if macd_h > 0 else "v"), fill=mh_col, font=fonts["label"])

        spark_x = cx + 16
        spark_y = cy + bh - 70
        spark_w = bw - 32
        spark_h = 52
        draw_sparkline(img, item["history"][-30:], spark_x, spark_y, spark_w, spark_h, col_main, filled=True)
        draw = ImageDraw.Draw(img)

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
    fonts = get_fonts()
    W, H = 1100, 1010
    ticker = data["raw_symbol"]
    img = Image.new("RGBA", (W, H), BG)
    draw = ImageDraw.Draw(img)

    is_up = data["change"] >= 0
    col_main = UP if is_up else DOWN
    sign = "+" if is_up else ""

    draw_wordmark(draw, 30, 24, fonts)
    name_str = data["display_name"]
    draw.text((30, 54), name_str, fill=TEXT_MAIN, font=fonts["header"])
    draw.text((30, 106), f"{ticker} - AI Quantitative Report - 1 Year History",
               fill=TEXT_MUTED, font=fonts["subheader"])

    price_str = format_price(ticker, data["price"])
    pw = draw.textlength(price_str, font=fonts["price_lg"])
    draw.text((W - pw - 30, 30), price_str, fill=TEXT_MAIN, font=fonts["price_lg"])
    pct_str = f"{sign}{data['change']:.2f}% Today"
    psw = draw.textlength(pct_str, font=fonts["pct_sm"])
    draw.text((W - psw - 30, 78), pct_str, fill=col_main, font=fonts["pct_sm"])

    draw.line([(30, 144), (W - 30, 144)], fill=BORDER, width=1)

    chart_x, chart_y, chart_w, chart_h = 30, 158, W - 60, 198
    draw_rounded_rect(draw, [chart_x, chart_y, chart_x + chart_w, chart_y + chart_h], 12, fill=PANEL)
    draw_hairline_grid(img, chart_x, chart_y, chart_w, chart_h, step=60)
    draw = ImageDraw.Draw(img)
    draw_sparkline(img, data["history"], chart_x + 10, chart_y + 10, chart_w - 20, chart_h - 20, col_main, filled=True)
    draw = ImageDraw.Draw(img)
    draw.text((chart_x + 14, chart_y + 10), "1Y PRICE HISTORY", fill=TEXT_DIM, font=fonts["label_sm"])

    perf_y = chart_y + chart_h + 22
    draw.text((30, perf_y), "PERFORMANCE", fill=TEXT_MUTED, font=fonts["label"])
    draw.line([(30, perf_y + 22), (W - 30, perf_y + 22)], fill=BORDER, width=1)
    perfs = [
        ("1 DAY", data["change"]), ("1 WEEK", data.get("perf_1w")),
        ("1 MONTH", data.get("perf_1m")), ("3 MONTHS", data.get("perf_3m")),
        ("YTD", data.get("perf_ytd")),
    ]
    p_block_w = (W - 60) // len(perfs)
    for i, (label, val) in enumerate(perfs):
        px = 30 + i * p_block_w
        py = perf_y + 30
        draw_rounded_rect(draw, [px + 5, py, px + p_block_w - 5, py + 65], 10, fill=CARD)
        draw.text((px + 14, py + 8), label, fill=TEXT_MUTED, font=fonts["label_sm"])
        draw.text((px + 14, py + 30), perf_str(val), fill=perf_col(val), font=fonts["price_sm"])

    ind_y = perf_y + 120
    draw.text((30, ind_y), "TECHNICAL INDICATORS", fill=TEXT_MUTED, font=fonts["label"])
    draw.line([(30, ind_y + 22), (W - 30, ind_y + 22)], fill=BORDER, width=1)

    ri_x, ri_y = 30, ind_y + 35
    draw_rounded_rect(draw, [ri_x, ri_y, ri_x + 320, ri_y + 90], 12, fill=CARD)
    rsi_v = data.get("rsi", 50)
    rsi_c = UP if rsi_v < 30 else (DOWN if rsi_v > 70 else GOLD)
    draw.text((ri_x + 12, ri_y + 8), "RSI (14)", fill=TEXT_MUTED, font=fonts["label_sm"])
    draw.text((ri_x + 12, ri_y + 28), f"{rsi_v:.1f}", fill=rsi_c, font=fonts["header_sm"])
    status = "OVERSOLD" if rsi_v < 30 else ("OVERBOUGHT" if rsi_v > 70 else "NORMAL")
    draw.text((ri_x + 100, ri_y + 38), status, fill=rsi_c, font=fonts["label_sm"])
    draw_rsi_bar(draw, ri_x + 12, ri_y + 68, 296, 12, rsi_v, fonts)

    mac_x = ri_x + 340
    draw_rounded_rect(draw, [mac_x, ri_y, mac_x + 320, ri_y + 90], 12, fill=CARD)
    macd_v = data.get("macd", 0)
    sig_v = data.get("macd_sig", 0)
    hist_v = data.get("macd_hist", 0)
    hist_c = UP if hist_v > 0 else DOWN
    draw.text((mac_x + 12, ri_y + 8), "MACD (12,26,9)", fill=TEXT_MUTED, font=fonts["label_sm"])
    draw.text((mac_x + 12, ri_y + 28), f"{macd_v:+.4f}", fill=hist_c, font=fonts["price_sm"])
    draw.text((mac_x + 12, ri_y + 55), f"Signal : {sig_v:.4f}", fill=TEXT_MUTED, font=fonts["body_sm"])
    draw.text((mac_x + 12, ri_y + 74), f"Hist : {hist_v:+.4f}", fill=hist_c, font=fonts["body_sm"])
    cross = "BULLISH CROSS ^" if hist_v > 0 else "BEARISH CROSS v"
    draw.text((mac_x + 160, ri_y + 74), cross, fill=hist_c, font=fonts["label_sm"])

    st_x = mac_x + 340
    draw_rounded_rect(draw, [st_x, ri_y, st_x + 300, ri_y + 90], 12, fill=CARD)
    stoch_v = data.get("stoch", 50)
    stoch_c = UP if stoch_v < 25 else (DOWN if stoch_v > 75 else GOLD)
    draw.text((st_x + 12, ri_y + 8), "STOCHASTIC (14)", fill=TEXT_MUTED, font=fonts["label_sm"])
    draw.text((st_x + 12, ri_y + 28), f"{stoch_v:.1f}", fill=stoch_c, font=fonts["header_sm"])
    s_status = "OVERSOLD" if stoch_v < 25 else ("OVERBOUGHT" if stoch_v > 75 else "NEUTRAL")
    draw.text((st_x + 100, ri_y + 38), s_status, fill=stoch_c, font=fonts["label_sm"])

    ema_y = ri_y + 108
    draw_rounded_rect(draw, [30, ema_y, W - 30, ema_y + 75], 12, fill=CARD)
    draw.text((42, ema_y + 10), "MOVING AVERAGES", fill=TEXT_MUTED, font=fonts["label_sm"])
    curr = data["price"]
    emas = [
        ("EMA 20", data.get("ema20")), ("EMA 50", data.get("ema50")),
        ("EMA 200", data.get("ema200")), ("BB UPPER", data.get("bb_upper")),
        ("BB MID", data.get("bb_mid")), ("BB LOWER", data.get("bb_lower")),
    ]
    ema_bw = (W - 80) // len(emas)
    for j, (lbl, val) in enumerate(emas):
        ex = 40 + j * ema_bw
        ey = ema_y + 28
        draw.text((ex, ey), lbl, fill=TEXT_DIM, font=fonts["label_sm"])
        if val:
            vc = UP if curr > val else DOWN
            draw.text((ex, ey + 18), format_price(ticker, val), fill=vc, font=fonts["label"])
            arrow = " ^" if curr > val else " v"
            draw.text((ex + 80, ey + 18), arrow, fill=vc, font=fonts["label_sm"])
        else:
            draw.text((ex, ey + 18), "N/A", fill=TEXT_DIM, font=fonts["label"])

    sig_y = ema_y + 93
    draw_rounded_rect(draw, [30, sig_y, W // 2 - 20, sig_y + 70], 12, fill=CARD)
    mom_v = data.get("momentum", 0)
    draw.text((42, sig_y + 8), "MOMENTUM (10p)", fill=TEXT_MUTED, font=fonts["label_sm"])
    draw.text((42, sig_y + 28), f"{mom_v:+.2f}%", fill=(UP if mom_v > 0 else DOWN), font=fonts["price_md"])

    sig_txt = data.get("signal", "NEUTRAL")
    sig_col = SIGNAL_COLORS.get(sig_txt, GOLD)
    bc = data.get("bull_count", 0)
    bear_c = data.get("bear_count", 0)
    draw_rounded_rect(draw, [W // 2 + 20, sig_y, W - 30, sig_y + 70], 12, fill=CARD)
    draw.text((W // 2 + 32, sig_y + 8), "GLOBAL SIGNAL", fill=TEXT_MUTED, font=fonts["label_sm"])
    draw.text((W // 2 + 32, sig_y + 28), sig_txt, fill=sig_col, font=fonts["price_md"])
    draw.text((W // 2 + 280, sig_y + 32), f"^{bc} / v{bear_c}", fill=TEXT_DIM, font=fonts["label_sm"])

    fund_y = sig_y + 88
    draw.text((30, fund_y), "FUNDAMENTALS", fill=TEXT_MUTED, font=fonts["label"])
    draw.line([(30, fund_y + 22), (W - 30, fund_y + 22)], fill=BORDER, width=1)
    stats = [
        ("MARKET CAP", data.get("mcap", "N/A")),
        ("P/E RATIO", format_num(data.get("pe"))),
        ("52W HIGH", f"${data['high52']:.2f}" if data.get("high52") else "N/A"),
        ("52W LOW", f"${data['low52']:.2f}" if data.get("low52") else "N/A"),
        ("CONSENSUS", data.get("recom", "N/A")),
        ("1Y TARGET", f"${data['target']:.2f}" if data.get("target") else "N/A"),
    ]
    sb_w = (W - 60) // 6
    for k, (lbl, val) in enumerate(stats):
        fx = 30 + k * sb_w
        fy = fund_y + 30
        draw_rounded_rect(draw, [fx + 4, fy, fx + sb_w - 4, fy + 60], 10, fill=CARD)
        draw.text((fx + 12, fy + 8), lbl, fill=TEXT_DIM, font=fonts["label_sm"])
        vc = TEXT_MAIN
        if "BUY" in str(val) or "BULL" in str(val): vc = UP
        elif "SELL" in str(val) or "BEAR" in str(val): vc = DOWN
        draw.text((fx + 12, fy + 28), str(val), fill=vc, font=fonts["label"])

    sent_y = fund_y + 110
    draw.text((30, sent_y), "AI NEWS SENTIMENT", fill=TEXT_MUTED, font=fonts["label"])
    sc = UP if "BULLISH" in data.get("sentiment", "") else (DOWN if "BEARISH" in data.get("sentiment", "") else GOLD)
    draw.text((240, sent_y), data.get("sentiment", "N/A"), fill=sc, font=fonts["label"])

    news_y = sent_y + 30
    draw.line([(30, news_y), (W - 30, news_y)], fill=BORDER, width=1)
    news_y += 10
    for article in data.get("news", [])[:3]:
        draw_rounded_rect(draw, [30, news_y, W - 30, news_y + 72], 12, fill=CARD)
        draw.text((46, news_y + 8), f"▌ {article.get('publisher','').upper()}", fill=GOLD, font=fonts["news_pub"])
        title = textwrap.shorten(article.get("title", ""), width=88, placeholder="…")
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
    rows = len(data)
    W = 1100
    H = 150 + rows * 72 + 64
    img = Image.new("RGBA", (W, H), BG)
    draw = ImageDraw.Draw(img)

    draw_wordmark(draw, 30, 20, fonts)
    draw.text((30, 50), "MARKET SCANNER", fill=TEXT_MAIN, font=fonts["header"])
    draw.text((30, 100), f"Filter : {filtre.upper()} - {rows} signal(s) detected",
               fill=TEXT_MUTED, font=fonts["subheader"])

    draw_pulse_strip(img, data, 30, 130, W - 60, 30)
    draw = ImageDraw.Draw(img)
    draw.line([(30, 168), (W - 30, 168)], fill=BORDER, width=1)

    cols_x = [30, 200, 340, 440, 540, 640, 740, 860, 980]
    headers = ["ASSET", "PRICE", "CHANGE", "RSI", "MACD^v", "STOCH", "EMA20", "SIGNAL", "SPARK"]
    for hx, ht in zip(cols_x, headers):
        draw.text((hx, 178), ht, fill=TEXT_DIM, font=fonts["mono_sm"])
    draw.line([(30, 196), (W - 30, 196)], fill=BORDER, width=1)

    for row_i, item in enumerate(data):
        ry = 204 + row_i * 72
        is_up = item["change"] >= 0
        col_c = UP if is_up else DOWN
        sign = "+" if is_up else ""

        if row_i % 2 == 0:
            draw.rectangle([30, ry - 4, W - 30, ry + 60], fill=CARD_ALT)

        nm = item["display_name"]
        if len(nm) > 12: nm = nm[:11] + "…"
        draw.text((cols_x[0], ry + 8), nm, fill=TEXT_MAIN, font=fonts["symbol"])
        draw.text((cols_x[1], ry + 8), format_price(item["raw_symbol"], item["price"]), fill=TEXT_MAIN, font=fonts["label"])
        draw.text((cols_x[2], ry + 8), f"{sign}{item['change']:.2f}%", fill=col_c, font=fonts["label"])

        rsi_v = item.get("rsi")
        if rsi_v is not None:
            rc = UP if rsi_v < 30 else (DOWN if rsi_v > 70 else GOLD)
            draw.text((cols_x[3], ry + 8), f"{rsi_v:.0f}", fill=rc, font=fonts["label"])

        mh = item.get("macd_hist")
        if mh is not None:
            mc = UP if mh > 0 else DOWN
            sym = "^" if mh > 0 else "v"
            draw.text((cols_x[4], ry + 8), f"{sym} {abs(mh):.4f}", fill=mc, font=fonts["label_sm"])

        st = item.get("stoch")
        if st is not None:
            sc_col = UP if st < 25 else (DOWN if st > 75 else GOLD)
            draw.text((cols_x[5], ry + 8), f"{st:.0f}", fill=sc_col, font=fonts["label"])

        ema20 = item.get("ema20")
        if ema20:
            above = item["price"] > ema20
            draw.text((cols_x[6], ry + 8), "ABOVE" if above else "BELOW", fill=(UP if above else DOWN), font=fonts["label_sm"])

        sig = item.get("signal", "NEUTRAL")
        sig_col = SIGNAL_COLORS.get(sig, GOLD)
        draw_rounded_rect(draw, [cols_x[7] - 4, ry + 2, cols_x[7] + 128, ry + 26], 10, fill=CARD, outline=sig_col, width=1)
        draw.text((cols_x[7] + 2, ry + 5), sig, fill=sig_col, font=fonts["tag"])

        hist = item.get("history", [])[-20:]
        draw_sparkline(img, hist, cols_x[8], ry + 4, W - cols_x[8] - 30, 50, col_c)
        draw = ImageDraw.Draw(img)

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
    W, H = 1200, 870
    img = Image.new("RGBA", (W, H), BG)
    draw = ImageDraw.Draw(img)

    draw_wordmark(draw, 30, 18, fonts)
    n1 = d1["display_name"]
    n2 = d2["display_name"]
    draw.text((30, 48), f"{n1} vs {n2}", fill=TEXT_MAIN, font=fonts["header"])
    draw.text((30, 100), "Side-by-Side Comparison - Technical + Fundamental Analysis",
               fill=TEXT_MUTED, font=fonts["subheader"])
    draw.line([(30, 134), (W - 30, 134)], fill=BORDER, width=1)

    col_w = (W - 90) // 2
    starts = [30, 30 + col_w + 30]
    datas = [d1, d2]
    accent_cols = [GOLD, CYAN]

    for dx, data, ac in zip(starts, datas, accent_cols):
        ticker = data["raw_symbol"]
        is_up = data["change"] >= 0
        col_c = UP if is_up else DOWN
        sign = "+" if is_up else ""

        draw_rounded_rect(draw, [dx, 144, dx + col_w, H - 50], 16, fill=PANEL, outline=ac, width=2)

        draw.text((dx + 20, 158), data["display_name"], fill=TEXT_MAIN, font=fonts["header_sm"])
        draw.text((dx + 20, 192), ticker, fill=TEXT_MUTED, font=fonts["subheader"])
        ps = format_price(ticker, data["price"])
        pw = draw.textlength(ps, font=fonts["price_md"])
        draw.text((dx + col_w - pw - 20, 158), ps, fill=TEXT_MAIN, font=fonts["price_md"])
        draw.text((dx + col_w - 120, 194), f"{sign}{data['change']:.2f}%", fill=col_c, font=fonts["pct_sm"])

        draw.line([(dx + 16, 224), (dx + col_w - 16, 224)], fill=BORDER, width=1)

        draw_rounded_rect(draw, [dx + 16, 232, dx + col_w - 16, 332], 10, fill=CARD)
        draw_sparkline(img, data["history"][-120:], dx + 24, 240, col_w - 56, 84, col_c, filled=True)
        draw = ImageDraw.Draw(img)
        draw.text((dx + 22, 235), "6M CHART", fill=TEXT_DIM, font=fonts["label_sm"])

        py = 342
        draw.text((dx + 20, py), "PERFORMANCE", fill=TEXT_MUTED, font=fonts["label_sm"])
        perfs = [("1D", data["change"]), ("1W", data.get("perf_1w")), ("1M", data.get("perf_1m")), ("YTD", data.get("perf_ytd"))]
        for pi, (pl, pv) in enumerate(perfs):
            px2 = dx + 20 + pi * (col_w // 4)
            draw.text((px2, py + 20), pl, fill=TEXT_DIM, font=fonts["mono_sm"])
            draw.text((px2, py + 36), perf_str(pv), fill=perf_col(pv), font=fonts["label"])

        ty = py + 75
        draw.line([(dx + 16, ty), (dx + col_w - 16, ty)], fill=BORDER, width=1)
        draw.text((dx + 20, ty + 8), "TECHNICAL", fill=TEXT_MUTED, font=fonts["label_sm"])
        tech = [
            ("RSI (14)", f"{data.get('rsi', 'N/A'):.0f}" if data.get("rsi") else "N/A",
             UP if (data.get("rsi") or 50) < 35 else (DOWN if (data.get("rsi") or 50) > 65 else TEXT_MAIN)),
            ("MACD HIST", f"{data.get('macd_hist', 0):+.4f}",
             UP if (data.get("macd_hist") or 0) > 0 else DOWN),
            ("STOCH", f"{data.get('stoch', 50):.0f}",
             UP if (data.get("stoch") or 50) < 25 else (DOWN if (data.get("stoch") or 50) > 75 else TEXT_MAIN)),
            ("MOMENTUM", f"{data.get('momentum', 0):+.2f}%",
             UP if (data.get("momentum") or 0) > 0 else DOWN),
        ]
        for ti, (tl, tv, tc) in enumerate(tech):
            tx2 = dx + 20 + (ti % 2) * (col_w // 2)
            ty2 = ty + 26 + (ti // 2) * 42
            draw.text((tx2, ty2), tl, fill=TEXT_DIM, font=fonts["mono_sm"])
            draw.text((tx2, ty2 + 16), tv, fill=tc, font=fonts["label"])

        emy = ty + 120
        draw.line([(dx + 16, emy), (dx + col_w - 16, emy)], fill=BORDER, width=1)
        draw.text((dx + 20, emy + 8), "PRICE vs EMAs", fill=TEXT_MUTED, font=fonts["label_sm"])
        curr = data["price"]
        for ei, (el, ev) in enumerate([("EMA20", data.get("ema20")), ("EMA50", data.get("ema50")), ("EMA200", data.get("ema200"))]):
            ex2 = dx + 20 + ei * (col_w // 3)
            draw.text((ex2, emy + 26), el, fill=TEXT_DIM, font=fonts["mono_sm"])
            if ev:
                ec = UP if curr > ev else DOWN
                ar = "^" if curr > ev else "v"
                draw.text((ex2, emy + 42), ar, fill=ec, font=fonts["label"])
            else:
                draw.text((ex2, emy + 42), "N/A", fill=TEXT_DIM, font=fonts["label_sm"])

        sig_y2 = emy + 82
        draw.line([(dx + 16, sig_y2), (dx + col_w - 16, sig_y2)], fill=BORDER, width=1)
        sig = data.get("signal", "NEUTRAL")
        sc = SIGNAL_COLORS.get(sig, GOLD)
        draw.text((dx + 20, sig_y2 + 10), "GLOBAL SIGNAL", fill=TEXT_MUTED, font=fonts["label_sm"])
        draw.text((dx + 20, sig_y2 + 30), sig, fill=sc, font=fonts["price_md"])
        bc = data.get("bull_count", 0)
        berc = data.get("bear_count", 0)
        draw.text((dx + 20, sig_y2 + 66), f"^ {bc} Bullish signals / v {berc} Bearish signals", fill=TEXT_DIM, font=fonts["label_sm"])

        fy2 = sig_y2 + 100
        draw.line([(dx + 16, fy2), (dx + col_w - 16, fy2)], fill=BORDER, width=1)
        draw.text((dx + 20, fy2 + 8), "FUNDAMENTALS", fill=TEXT_MUTED, font=fonts["label_sm"])
        fund_items = [
            ("MKT CAP", data.get("mcap", "N/A")), ("P/E", format_num(data.get("pe"))),
            ("52W H", f"${data['high52']:.2f}" if data.get("high52") else "N/A"),
            ("TARGET", f"${data['target']:.2f}" if data.get("target") else "N/A"),
        ]
        for fi, (fl, fv) in enumerate(fund_items):
            fx2 = dx + 20 + (fi % 2) * (col_w // 2)
            fy3 = fy2 + 28 + (fi // 2) * 36
            draw.text((fx2, fy3), fl, fill=TEXT_DIM, font=fonts["mono_sm"])
            draw.text((fx2, fy3 + 14), str(fv), fill=TEXT_MAIN, font=fonts["label"])

    draw_footer(draw, W, H, fonts)

    cx_sep = 30 + col_w + 15
    draw.line([(cx_sep, 144), (cx_sep, H - 50)], fill=BORDER, width=1)

    b1 = d1.get("bull_count", 0)
    b2 = d2.get("bull_count", 0)
    verdict_y = H - 100
    draw.line([(30, verdict_y - 10), (W - 30, verdict_y - 10)], fill=BORDER, width=1)
    label = "ALGORITHMIC EDGE"
    lw = draw.textlength(label, font=fonts["mono_sm"])
    draw.text((W // 2 - lw / 2, verdict_y), label, fill=TEXT_DIM, font=fonts["mono_sm"])
    if b1 > b2:
        winner, wc = d1["display_name"], GOLD
    elif b2 > b1:
        winner, wc = d2["display_name"], CYAN
    else:
        winner, wc = "TIED", GOLD
    wstr = f"> {winner} has stronger technical signals ({max(b1, b2)}/6)"
    ww = draw.textlength(wstr, font=fonts["label"])
    draw.text((W // 2 - ww / 2, verdict_y + 18), wstr, fill=wc, font=fonts["label"])

    out = img.convert("RGB")
    os.makedirs("output", exist_ok=True)
    path = "output/compare_result.png"
    out.save(path, quality=95)
    return path
