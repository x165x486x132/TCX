import discord
from discord import app_commands
import yfinance as yf
import os
import asyncio
import time
from functools import lru_cache

from ui_engine import (
    generate_dashboard_image,
    generate_intel_image,
    generate_compare_image,
    generate_scan_image,
)

# ============================================================
# WATCHLISTS
# ============================================================
WATCHLIST_MARKET      = ["NVDA", "AAPL", "MSFT", "TSLA", "AMZN", "META", "GOOGL", "BRK-B"]
WATCHLIST_CRYPTO      = ["BTC-USD", "ETH-USD", "SOL-USD", "BNB-USD", "XRP-USD", "DOGE-USD", "ADA-USD", "AVAX-USD"]
WATCHLIST_FOREX       = ["EURUSD=X", "GBPUSD=X", "JPY=X", "CHF=X", "AUDUSD=X", "USDCAD=X", "NZDUSD=X", "EURGBP=X"]
WATCHLIST_COMMODITIES = ["GC=F", "SI=F", "CL=F", "NG=F", "ZC=F", "HG=F", "CC=F", "KC=F"]
WATCHLIST_INDICES     = ["^GSPC", "^IXIC", "^DJI", "^VIX", "^RUT", "^FTSE", "^N225", "^FCHI"]
WATCHLIST_SCAN        = WATCHLIST_MARKET + ["COIN", "PLTR", "INTC", "SMCI", "MSTR", "AMD", "NFLX", "DIS"]

RENAME_MAP = {
    "^GSPC": "S&P 500",      "^IXIC": "NASDAQ",        "^DJI": "DOW JONES",  "^VIX": "VIX",
    "^RUT":  "RUSSELL 2000", "^FTSE": "FTSE 100",       "^N225": "NIKKEI 225","^FCHI": "CAC 40",
    "GC=F":  "GOLD",         "SI=F":  "SILVER",         "CL=F":  "CRUDE OIL", "NG=F":  "NAT GAS",
    "ZC=F":  "CORN",         "HG=F":  "COPPER",         "CC=F":  "COCOA",     "KC=F":  "COFFEE",
    "EURUSD=X":"EUR/USD",    "GBPUSD=X":"GBP/USD",      "JPY=X": "USD/JPY",   "CHF=X": "USD/CHF",
    "AUDUSD=X":"AUD/USD",    "USDCAD=X":"USD/CAD",      "NZDUSD=X":"NZD/USD", "EURGBP=X":"EUR/GBP",
    "BTC-USD":"BITCOIN",     "ETH-USD":"ETHEREUM",      "SOL-USD":"SOLANA",   "BNB-USD":"BINANCE",
    "XRP-USD":"XRP",         "DOGE-USD":"DOGECOIN",     "ADA-USD":"CARDANO",  "AVAX-USD":"AVALANCHE",
}

# ============================================================
# CACHE SIMPLE (évite de re-fetcher les données trop souvent)
# ============================================================
_cache: dict = {}
CACHE_TTL = 300  # 5 minutes

def _cache_get(key):
    entry = _cache.get(key)
    if entry and (time.time() - entry["ts"] < CACHE_TTL):
        return entry["data"]
    return None

def _cache_set(key, data):
    _cache[key] = {"ts": time.time(), "data": data}

# ============================================================
# CALCUL DES INDICATEURS TECHNIQUES
# ============================================================
def compute_indicators(closes: list) -> dict:
    """
    Calcule RSI, MACD, Bollinger Bands, EMA20/50/200, ATR proxy,
    Stochastique, momentum et signal de tendance.
    Nécessite au minimum 2 valeurs ; plus = meilleur.
    """
    if not closes or len(closes) < 2:
        return {}

    n = len(closes)

    # --- EMA helper ---
    def ema(data, period):
        if len(data) < period:
            return [sum(data) / len(data)] * len(data)
        k = 2 / (period + 1)
        ema_vals = [sum(data[:period]) / period]
        for price in data[period:]:
            ema_vals.append(price * k + ema_vals[-1] * (1 - k))
        # Pad début pour aligner avec data
        pad = len(data) - len(ema_vals)
        return [ema_vals[0]] * pad + ema_vals

    # --- RSI (14) ---
    def rsi(data, period=14):
        if len(data) < period + 1:
            return 50.0
        gains, losses = [], []
        for i in range(1, len(data)):
            d = data[i] - data[i - 1]
            gains.append(max(d, 0))
            losses.append(max(-d, 0))
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return round(100 - (100 / (1 + rs)), 2)

    # --- Bollinger Bands (20) ---
    def bollinger(data, period=20):
        if len(data) < period:
            period = len(data)
        window = data[-period:]
        mean = sum(window) / len(window)
        variance = sum((x - mean) ** 2 for x in window) / len(window)
        std = variance ** 0.5
        return round(mean + 2 * std, 4), round(mean, 4), round(mean - 2 * std, 4)

    # --- MACD (12, 26, 9) ---
    ema12 = ema(closes, 12)
    ema26 = ema(closes, 26)
    macd_line = [a - b for a, b in zip(ema12, ema26)]
    signal_line = ema(macd_line, 9)
    macd_val   = round(macd_line[-1], 4)
    signal_val = round(signal_line[-1], 4)
    histogram  = round(macd_val - signal_val, 4)

    # --- EMAs actuelles ---
    ema20_val  = round(ema(closes, 20)[-1], 4)
    ema50_val  = round(ema(closes, 50)[-1], 4) if n >= 50 else None
    ema200_val = round(ema(closes, 200)[-1], 4) if n >= 200 else None

    # --- Stochastique K (14) ---
    def stoch_k(data, period=14):
        if len(data) < period:
            period = len(data)
        window = data[-period:]
        low, high = min(window), max(window)
        if high == low:
            return 50.0
        return round((data[-1] - low) / (high - low) * 100, 2)

    # --- Momentum (10 périodes) ---
    momentum = round((closes[-1] / closes[-min(10, n)]) * 100 - 100, 2) if n >= 2 else 0.0

    rsi_val = rsi(closes)
    bb_upper, bb_mid, bb_lower = bollinger(closes)
    stoch_val = stoch_k(closes)
    curr_price = closes[-1]

    # --- Signal global ---
    bullish_signals = 0
    bearish_signals = 0

    if rsi_val < 35:   bullish_signals += 1
    elif rsi_val > 65: bearish_signals += 1

    if macd_val > signal_val:  bullish_signals += 1
    else:                       bearish_signals += 1

    if curr_price > ema20_val:  bullish_signals += 1
    else:                        bearish_signals += 1

    if ema50_val and curr_price > ema50_val:  bullish_signals += 1
    elif ema50_val:                            bearish_signals += 1

    if stoch_val < 25:  bullish_signals += 1
    elif stoch_val > 75: bearish_signals += 1

    if histogram > 0:  bullish_signals += 1
    else:               bearish_signals += 1

    if bullish_signals >= 4:   signal = "STRONG BUY"
    elif bullish_signals >= 3: signal = "BUY"
    elif bearish_signals >= 4: signal = "STRONG SELL"
    elif bearish_signals >= 3: signal = "SELL"
    else:                       signal = "NEUTRAL"

    return {
        "rsi":       rsi_val,
        "macd":      macd_val,
        "macd_sig":  signal_val,
        "macd_hist": histogram,
        "bb_upper":  bb_upper,
        "bb_mid":    bb_mid,
        "bb_lower":  bb_lower,
        "ema20":     ema20_val,
        "ema50":     ema50_val,
        "ema200":    ema200_val,
        "stoch":     stoch_val,
        "momentum":  momentum,
        "signal":    signal,
        "bull_count": bullish_signals,
        "bear_count": bearish_signals,
    }

# ============================================================
# FETCH DATA
# ============================================================
def get_live_data(watchlist: list, period: str = "30d") -> list:
    """Récupère les données de marché avec cache et indicateurs."""
    cache_key = f"live_{'-'.join(watchlist)}_{period}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    data = []
    for sym in watchlist:
        try:
            tkr = yf.Ticker(sym)
            hist = tkr.history(period=period)
            if hist.empty or len(hist) < 2:
                continue

            closes = [float(x) for x in hist["Close"].dropna().tolist()]
            if len(closes) < 2:
                continue

            close_prev = closes[-2]
            close_curr = closes[-1]
            pct = ((close_curr - close_prev) / close_prev) * 100

            indicators = compute_indicators(closes)

            data.append({
                "raw_symbol":   sym,
                "display_name": RENAME_MAP.get(sym, sym),
                "price":        close_curr,
                "change":       pct,
                "history":      closes,
                "volume":       int(hist["Volume"].iloc[-1]) if "Volume" in hist.columns else 0,
                **indicators,
            })
        except Exception as e:
            print(f"[WARN] {sym}: {e}")

    data.sort(key=lambda x: x["change"], reverse=True)
    _cache_set(cache_key, data)
    return data


def get_deep_data(ticker: str) -> dict | None:
    """Fetch complet pour /intel : 1 an d'historique + info fondamentales."""
    cache_key = f"deep_{ticker}"
    cached = _cache_get(cache_key)
    if cached:
        return cached

    try:
        tkr  = yf.Ticker(ticker)
        info = tkr.info
        hist = tkr.history(period="1y")

        if hist.empty or len(hist) < 2:
            return None

        closes  = [float(x) for x in hist["Close"].dropna().tolist()]
        volumes = [int(x)   for x in hist["Volume"].dropna().tolist()] if "Volume" in hist.columns else []

        close_prev = closes[-2]
        close_curr = closes[-1]
        pct        = ((close_curr - close_prev) / close_prev) * 100

        # Variations court terme
        w1  = ((close_curr / closes[-6])  - 1) * 100 if len(closes) >= 6  else None
        m1  = ((close_curr / closes[-22]) - 1) * 100 if len(closes) >= 22 else None
        m3  = ((close_curr / closes[-66]) - 1) * 100 if len(closes) >= 66 else None
        ytd = ((close_curr / closes[0])   - 1) * 100

        mcap = info.get("marketCap", 0)
        indicators = compute_indicators(closes)

        # News + sentiment VADER (importé localement pour ne pas crasher si absent)
        news_data      = []
        overall_sent   = 0.0
        try:
            from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
            _vader = SentimentIntensityAnalyzer()
            raw_news = tkr.news or []
            for article in raw_news[:5]:
                title = article.get("title", "No title")
                pub   = article.get("publisher", "")
                if isinstance(pub, dict):
                    pub = pub.get("displayName", "Press")
                news_data.append({"title": title, "publisher": pub or "Financial Press"})
                overall_sent += _vader.polarity_scores(title)["compound"]
        except Exception:
            pass

        if overall_sent > 0.15:   sent_label = "BULLISH 🚀"
        elif overall_sent < -0.15: sent_label = "BEARISH 📉"
        else:                       sent_label = "NEUTRAL ⚖️"

        result = {
            "raw_symbol":   ticker,
            "display_name": RENAME_MAP.get(ticker, info.get("shortName", ticker)),
            "price":        close_curr,
            "change":       pct,
            "history":      closes,
            "volumes":      volumes,
            "mcap":         f"${mcap/1e9:.1f}B" if mcap > 1e9 else (f"${mcap/1e6:.0f}M" if mcap > 0 else "N/A"),
            "pe":           info.get("trailingPE", "N/A"),
            "high52":       info.get("fiftyTwoWeekHigh"),
            "low52":        info.get("fiftyTwoWeekLow"),
            "recom":        str(info.get("recommendationKey", "N/A")).replace("_", " ").upper(),
            "target":       info.get("targetMeanPrice"),
            "sentiment":    sent_label,
            "news":         news_data,
            "perf_1w":      w1,
            "perf_1m":      m1,
            "perf_3m":      m3,
            "perf_ytd":     ytd,
            **indicators,
        }
        _cache_set(cache_key, result)
        return result
    except Exception as e:
        print(f"[ERROR] get_deep_data({ticker}): {e}")
        return None

# ============================================================
# BOT
# ============================================================
class TradingBot(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        await self.tree.sync()

bot = TradingBot()

@bot.event
async def on_ready():
    print(f"✅ TCX Bot [{bot.user}] en ligne !")
    await bot.change_presence(
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="/market /forex /intel /scan /compare"
        )
    )

# ---- Helper générique dashboard ----
async def _send_dashboard(interaction, watchlist, title, filename, period="7d"):
    await interaction.response.defer()
    data = get_live_data(watchlist, period)
    if not data:
        await interaction.followup.send("❌ Impossible de joindre les serveurs financiers. Réessaie dans quelques instants.")
        return
    img_path = generate_dashboard_image(data, title, filename)
    await interaction.followup.send(file=discord.File(img_path, filename="dash.png"))

# ============================================================
# COMMANDES DASHBOARDS
# ============================================================
@bot.tree.command(name="market", description="Dashboard des géants de Wall Street avec indicateurs techniques.")
async def market(interaction: discord.Interaction):
    await _send_dashboard(interaction, WATCHLIST_MARKET, "US MARKET OVERVIEW", "market_dash.png")

@bot.tree.command(name="crypto", description="Dashboard des cryptomonnaies avec indicateurs techniques.")
async def crypto(interaction: discord.Interaction):
    await _send_dashboard(interaction, WATCHLIST_CRYPTO, "CRYPTO OVERVIEW", "crypto_dash.png")

@bot.tree.command(name="forex", description="Dashboard des devises mondiales avec indicateurs techniques.")
async def forex(interaction: discord.Interaction):
    await _send_dashboard(interaction, WATCHLIST_FOREX, "FOREX OVERVIEW", "forex_dash.png")

@bot.tree.command(name="commodities", description="Dashboard des matières premières (Or, Pétrole...)")
async def commodities(interaction: discord.Interaction):
    await _send_dashboard(interaction, WATCHLIST_COMMODITIES, "COMMODITIES OVERVIEW", "comm_dash.png")

@bot.tree.command(name="indices", description="Dashboard des indices mondiaux (S&P500, CAC40...)")
async def indices(interaction: discord.Interaction):
    await _send_dashboard(interaction, WATCHLIST_INDICES, "GLOBAL INDICES", "indices_dash.png")

# ============================================================
# /MOVERS
# ============================================================
@bot.tree.command(name="movers", description="Les actifs les plus volatils du jour.")
async def movers(interaction: discord.Interaction):
    await interaction.response.defer()
    extra = ["COIN", "PLTR", "INTC", "SMCI", "MSTR", "AMD", "NFLX", "DIS"]
    data = get_live_data(WATCHLIST_MARKET + extra, "7d")
    if len(data) >= 8:
        movers_data = data[:4] + data[-4:]
    else:
        movers_data = data
    img_path = generate_dashboard_image(movers_data, "TOP DAILY MOVERS", "movers_dash.png")
    await interaction.followup.send(file=discord.File(img_path, filename="dash.png"))

# ============================================================
# /INTEL — Deep Dive
# ============================================================
@bot.tree.command(name="intel", description="Rapport complet (indicateurs techniques + fondamentaux + news) sur un actif.")
@app_commands.describe(ticker="Symbole Yahoo Finance (ex: NVDA, BTC-USD, EURUSD=X, GC=F)")
async def intel(interaction: discord.Interaction, ticker: str):
    ticker = ticker.upper().strip()
    await interaction.response.defer()

    data = get_deep_data(ticker)
    if not data:
        await interaction.followup.send(
            f"❌ Données introuvables pour `{ticker}`.\n"
            "Vérifie le symbole Yahoo Finance (ex: `NVDA`, `BTC-USD`, `EURUSD=X`, `GC=F`)."
        )
        return

    img_path = generate_intel_image(data)
    await interaction.followup.send(file=discord.File(img_path, filename="intel.png"))

# ============================================================
# /SCAN — Détection de setups techniques
# ============================================================
@bot.tree.command(name="scan", description="Scanne le marché et détecte les meilleurs setups techniques en temps réel.")
@app_commands.describe(
    marche="Marché à scanner",
    filtre="Type de signal recherché"
)
@app_commands.choices(
    marche=[
        app_commands.Choice(name="Actions US", value="market"),
        app_commands.Choice(name="Crypto", value="crypto"),
        app_commands.Choice(name="Forex", value="forex"),
        app_commands.Choice(name="Matières Premières", value="commodities"),
        app_commands.Choice(name="Indices", value="indices"),
    ],
    filtre=[
        app_commands.Choice(name="Tous les signaux", value="all"),
        app_commands.Choice(name="Buy / Strong Buy", value="buy"),
        app_commands.Choice(name="Sell / Strong Sell", value="sell"),
        app_commands.Choice(name="RSI suracheté (>70)", value="overbought"),
        app_commands.Choice(name="RSI survendu (<30)", value="oversold"),
        app_commands.Choice(name="Croisement MACD haussier", value="macd_bull"),
        app_commands.Choice(name="Croisement MACD baissier", value="macd_bear"),
    ]
)
async def scan(
    interaction: discord.Interaction,
    marche: str = "market",
    filtre: str = "all"
):
    await interaction.response.defer()
    wl_map = {
        "market": WATCHLIST_MARKET + ["COIN", "PLTR", "AMD", "NFLX", "INTC", "SMCI"],
        "crypto": WATCHLIST_CRYPTO,
        "forex":  WATCHLIST_FOREX,
        "commodities": WATCHLIST_COMMODITIES,
        "indices": WATCHLIST_INDICES,
    }
    watchlist = wl_map.get(marche, WATCHLIST_MARKET)
    data = get_live_data(watchlist, "30d")

    if not data:
        await interaction.followup.send("❌ Aucune donnée disponible.")
        return

    # Filtrage
    def match(item):
        sig = item.get("signal", "NEUTRAL")
        rsi = item.get("rsi", 50)
        hist = item.get("macd_hist", 0)
        if filtre == "all":          return True
        if filtre == "buy":          return sig in ("BUY", "STRONG BUY")
        if filtre == "sell":         return sig in ("SELL", "STRONG SELL")
        if filtre == "overbought":   return rsi > 70
        if filtre == "oversold":     return rsi < 30
        if filtre == "macd_bull":    return hist > 0
        if filtre == "macd_bear":    return hist < 0
        return True

    filtered = [x for x in data if match(x)]
    if not filtered:
        await interaction.followup.send(f"🔍 Aucun actif ne correspond au filtre **{filtre}** sur ce marché.")
        return

    img_path = generate_scan_image(filtered[:12], filtre)
    await interaction.followup.send(file=discord.File(img_path, filename="scan.png"))

# ============================================================
# /COMPARE — Comparaison de 2 actifs
# ============================================================
@bot.tree.command(name="compare", description="Compare deux actifs côte à côte (prix, indicateurs, performance).")
@app_commands.describe(
    ticker1="Premier symbole (ex: AAPL)",
    ticker2="Deuxième symbole (ex: MSFT)"
)
async def compare(interaction: discord.Interaction, ticker1: str, ticker2: str):
    ticker1 = ticker1.upper().strip()
    ticker2 = ticker2.upper().strip()
    await interaction.response.defer()

    d1 = get_deep_data(ticker1)
    d2 = get_deep_data(ticker2)

    if not d1:
        await interaction.followup.send(f"❌ Données introuvables pour `{ticker1}`.")
        return
    if not d2:
        await interaction.followup.send(f"❌ Données introuvables pour `{ticker2}`.")
        return

    img_path = generate_compare_image(d1, d2)
    await interaction.followup.send(file=discord.File(img_path, filename="compare.png"))

# ============================================================
# LANCEMENT
# ============================================================
if __name__ == "__main__":
    TOKEN = os.getenv("DISCORD_TOKEN")
    if not TOKEN:
        print("❌ ERREUR : Variable d'environnement DISCORD_TOKEN introuvable.")
    else:
        bot.run(TOKEN)
