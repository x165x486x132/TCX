# 📈 Aesthetic Trading Alert Bot

Un bot Discord professionnel qui analyse les annonces financières (News Sentiment Analysis) et génère automatiquement des images esthétiques calquées sur l'interface de **TradingView**.

## 🚀 Fonctionnalités
- **Analyse de sentiment via l'IA** (VaderSentiment) pour déterminer si une annonce est *BULLISH* ou *BEARISH*.
- **Génération d'images à la volée** (Matplotlib/Pillow) avec le thème Dark Mode de TradingView.
- **Récupération des marchés en direct** via Yahoo Finance (`yfinance`).
- **Serveur web intégré (`keep_alive.py`)** permettant un hébergement cloud gratuit (Render.com + UptimeRobot) 24h/24 et 7j/7.

## 🛠️ Installation & Utilisation
1. Clonez ce repository.
2. Créez un dossier `assets/` et placez-y les polices `Roboto-Bold.ttf` et `Roboto-Medium.ttf` (Google Fonts).
3. Ajoutez votre token Discord dans un fichier `.env` (`DISCORD_TOKEN=votre_token`).
4. Installez les dépendances :
   ```bash
   pip install -r requirements.txt
