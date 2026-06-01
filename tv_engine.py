import matplotlib
matplotlib.use('Agg') # Essentiel pour GitHub Actions (sans écran)

import yfinance as yf
import mplfinance as mpf
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import os
import requests
import textwrap

# Couleurs Dark Mode TradingView
TV_BG = '#131722'
TV_GRID = '#1F2933'
TV_TEXT = '#B2B5BE'
TV_GREEN = '#26A69A'
TV_RED = '#EF5350'

def download_font(font_name, url):
    """Télécharge la police automatiquement si elle n'existe pas."""
    os.makedirs("assets", exist_ok=True)
    font_path = f"assets/{font_name}"
    if not os.path.exists(font_path):
        print(f"Téléchargement de la police {font_name}...")
        response = requests.get(url)
        with open(font_path, 'wb') as f:
            f.write(response.content)
    return font_path

def generate_tradingview_alert(ticker, company_name, trend, news_headline):
    # 1. Télécharger les polices automatiquement
    font_bold_url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Bold.ttf"
    font_med_url = "https://github.com/googlefonts/roboto/raw/main/src/hinted/Roboto-Medium.ttf"
    
    path_bold = download_font("Roboto-Bold.ttf", font_bold_url)
    path_med = download_font("Roboto-Medium.ttf", font_med_url)

    # 2. Télécharger les données de l'action
    df = yf.download(ticker, period="1mo", interval="1d", progress=False)
    
    market_colors = mpf.make_marketcolors(up=TV_GREEN, down=TV_RED, edge='inherit', wick='inherit', volume='in', ohlc='inherit')
    tv_style = mpf.make_mpf_style(marketcolors=market_colors, facecolor=TV_BG, edgecolor=TV_GRID, figcolor=TV_BG, gridcolor=TV_GRID, gridstyle='--')
    
    os.makedirs("output", exist_ok=True)
    chart_path = f"output/temp_chart_{ticker}.png"
    
    mpf.plot(
        df, type='candle', style=tv_style, volume=False, axisoff=True, 
        savefig=dict(fname=chart_path, dpi=150, bbox_inches='tight', pad_inches=0),
        figsize=(10, 4)
    )
    
    # 3. Créer l'interface (Background)
    final_img = Image.new("RGB", (1200, 800), TV_BG)
    draw = ImageDraw.Draw(final_img)
    
    # Coller le graphique
    chart_img = Image.open(chart_path).resize((1100, 450))
    final_img.paste(chart_img, (50, 150))
    
    # Dessiner les séparateurs
    draw.line([(50, 130), (1150, 130)], fill=TV_GRID, width=3)
    draw.line([(50, 620), (1150, 620)], fill=TV_GRID, width=3)
    
    # 4. Ajouter Textes & Polices
    font_title = ImageFont.truetype(path_bold, 60)
    font_ticker = ImageFont.truetype(path_med, 30)
    font_news = ImageFont.truetype(path_med, 28)

    draw.text((50, 40), f"{company_name}", fill="white", font=font_title)
    draw.text((50, 100), f"{ticker} • 1D • ALGO ALERT", fill=TV_TEXT, font=font_ticker)
    
    # Pastille de Tendance
    if trend == "BULLISH":
        trend_color = TV_GREEN
        trend_text = "🟢 BULLISH ALERT"
    else:
        trend_color = TV_RED
        trend_text = "🔴 BEARISH ALERT"
        
    draw.rectangle([880, 50, 1150, 110], fill=trend_color, outline=trend_color, radius=10)
    draw.text((905, 65), trend_text, fill=TV_BG, font=font_ticker)
    
    draw.text((50, 650), "LATEST NEWS:", fill=TV_TEXT, font=font_ticker)
    wrapped_news = textwrap.fill(news_headline, width=70)
    draw.text((50, 690), wrapped_news, fill="white", font=font_news)
    
    # 5. Exporter
    final_output = f"output/{ticker}_alert.png"
    final_img.save(final_output)
    os.remove(chart_path)
    
    return final_output
