import matplotlib
matplotlib.use('Agg') # TRÈS IMPORTANT POUR LE CLOUD : Empêche le crash sur les serveurs sans écran

import yfinance as yf
import mplfinance as mpf
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import os
import textwrap

# Couleurs exactes du Dark Mode de TradingView
TV_BG = '#131722'
TV_GRID = '#1F2933'
TV_TEXT = '#B2B5BE'
TV_GREEN = '#26A69A'
TV_RED = '#EF5350'

def generate_tradingview_alert(ticker, company_name, trend, news_headline):
    print(f"📊 Génération du graphique pour {ticker}...")
    
    # 1. Télécharger 1 mois de données
    df = yf.download(ticker, period="1mo", interval="1d", progress=False)
    
    # 2. Configurer le style TradingView
    market_colors = mpf.make_marketcolors(
        up=TV_GREEN, down=TV_RED, 
        edge='inherit', wick='inherit', 
        volume='in', ohlc='inherit'
    )
    
    tv_style = mpf.make_mpf_style(
        marketcolors=market_colors,
        facecolor=TV_BG,
        edgecolor=TV_GRID,
        figcolor=TV_BG,
        gridcolor=TV_GRID,
        gridstyle='--'
    )
    
    # 3. Créer les dossiers si manquants
    os.makedirs("assets", exist_ok=True)
    os.makedirs("output", exist_ok=True)
    
    chart_path = f"assets/temp_chart_{ticker}.png"
    
    # 4. Sauvegarder le graphique pur (Bougies)
    mpf.plot(
        df, type='candle', style=tv_style, 
        volume=False, axisoff=True, 
        savefig=dict(fname=chart_path, dpi=150, bbox_inches='tight', pad_inches=0),
        figsize=(10, 4)
    )
    
    # 5. Créer l'interface (Background)
    final_width, final_height = 1200, 800
    final_img = Image.new("RGB", (final_width, final_height), TV_BG)
    draw = ImageDraw.Draw(final_img)
    
    # Coller le graphique
    chart_img = Image.open(chart_path)
    chart_img = chart_img.resize((1100, 450))
    final_img.paste(chart_img, (50, 150))
    
    # Dessiner les séparateurs
    draw.line([(50, 130), (1150, 130)], fill=TV_GRID, width=3)
    draw.line([(50, 620), (1150, 620)], fill=TV_GRID, width=3)
    
    # 6. Ajouter les polices d'écriture (Fallback par défaut si le dossier assets est vide)
    try:
        font_title = ImageFont.truetype("assets/Roboto-Bold.ttf", 60)
        font_ticker = ImageFont.truetype("assets/Roboto-Medium.ttf", 30)
        font_news = ImageFont.truetype("assets/Roboto-Medium.ttf", 28)
    except:
        font_title = ImageFont.load_default()
        font_ticker = ImageFont.load_default()
        font_news = ImageFont.load_default()

    # Textes d'en-tête
    draw.text((50, 40), f"{company_name}", fill="white", font=font_title)
    draw.text((50, 100), f"{ticker} • 1D • TRADINGVIEW ALGO", fill=TV_TEXT, font=font_ticker)
    
    # Pastille de Tendance
    if trend == "BULLISH":
        trend_color = TV_GREEN
        trend_text = "🟢 BULLISH ALERT"
    else:
        trend_color = TV_RED
        trend_text = "🔴 BEARISH ALERT"
        
    draw.rectangle([880, 50, 1150, 110], fill=trend_color, outline=trend_color, radius=10)
    draw.text((905, 65), trend_text, fill=TV_BG, font=font_ticker)
    
    # Texte de la news
    draw.text((50, 650), "LATEST NEWS:", fill=TV_TEXT, font=font_ticker)
    wrapped_news = textwrap.fill(news_headline, width=70)
    draw.text((50, 690), wrapped_news, fill="white", font=font_news)
    
    # 7. Exporter l'image finale
    final_output = f"output/{ticker}_alert.png"
    final_img.save(final_output)
    
    # Nettoyer
    os.remove(chart_path)
    
    return final_output
