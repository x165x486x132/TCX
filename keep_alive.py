from flask import Flask
from threading import Thread

app = Flask('')

@app.route('/')
def home():
    return "Le Bot de Trading est en ligne et surveille le marché ! 📈"

def run():
    # Le port 8080 est standard pour Render
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()
