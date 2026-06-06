import requests
import pandas as pd
import time
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS', 'hansiepansie007@gmail.com')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', 'dmdlcwbhagykoucs')
RECEIVER_EMAIL = os.environ.get('RECEIVER_EMAIL', 'hansiepansie007@gmail.com')
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

MY_COINS = {
    'bitcoin': 'BTC',
    'ethereum': 'ETH',
    'render-token': 'RENDER',
    'avalanche-2': 'AVAX',
    'wormhole': 'W',
    'peaq': 'PEAQ',
    'renzo': 'REZ',
    'injective-protocol': 'INJ',
    'centrifuge': 'CFG',
    'fetch-ai': 'FET',
    'dash': 'DASH',
    'filecoin': 'FIL',
    'ethereum-name-service': 'ENS'
}

WATCHLIST = {
    'cosmos': 'ATOM',
    'chainlink': 'LINK',
    'polygon': 'MATIC',
    'aptos': 'APT',
    'sui': 'SUI',
    'near': 'NEAR',
    'litecoin': 'LTC',
    'arbitrum': 'ARB',
    'optimism': 'OP',
    'algorand': 'ALGO'
}

def get_data(coin_id, days=30):
    url = "https://api.coingecko.com/api/v3/coins/" + coin_id + "/market_chart"
    params = {'vs_currency': 'usd', 'days': days, 'interval': 'daily'}
    
    try:
        time.sleep(2)
        r = requests.get(url, params=params, timeout=10)
        
        if r.status_code == 200:
            data = r.json()
            if 'prices' in data and len(data['prices']) >= 7:
                df = pd.DataFrame(data['prices'], columns=['time', 'price'])
                df['time'] = pd.to_datetime(df['time'], unit='ms')
                df.set_index('time', inplace=True)
                return df
    except:
        pass
    
    return None

def calc_rsi(df, period=14):
    if len(df) < period:
        return 50
    delta = df['price'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1] if not rsi.empty else 50

def get_trend(df):
    if len(df) < 20:
        return "NEUTRAAL"
    price = df['price'].iloc[-1]
    ema20 = df['price'].ewm(span=20, adjust=False).mean().iloc[-1]
    ema50 = df['price'].ewm(span=50, adjust=False).mean().iloc[-1] if len(df) >= 50 else ema20
    if price > ema20 > ema50:
        return "BULLISH"
    elif price < ema20 < ema50:
        return "BEARISH"
    return "NEUTRAAL"

def detect_breakout(df, coin_name):
    if df is None or len(df) < 14:
        return None
    
    price = df['price'].iloc[-1]
    high_14d = df['price'].rolling(window=14).max().iloc[-1]
    low_14d = df['price'].rolling(window=14).min().iloc[-1]
    ch_3d = ((price - df['price'].iloc[-3]) / df['price'].iloc[-3]) * 100 if len(df) >= 3 else 0
    ch_7d = ((price - df['price'].iloc[-7]) / df['price'].iloc[-7]) * 100 if len(df) >= 7 else 0
    ch_14d = ((price - df['price'].iloc[-14]) / df['price'].iloc[-14]) * 100 if len(df) >= 14 else 0
    rsi = calc_rsi(df)
    trend = get_trend(df)
    
    distance = ((high_14d - price) / high_14d) * 100
    
    score = 0
    signals = []
    
    if 0 <= distance < 5:
        score += 3
        signals.append("Nabij resistance")
    if ch_3d > 0 and ch_7d > 0:
        score += 2
        signals.append("Opwaarts")
    if 45 <= rsi <= 65:
        score += 2
    if trend == "BULLISH":
        score += 2
    if ch_3d > ch_7d:
        score += 1
        signals.append("Versnellend")
    
    return {
        'name': coin_name,
        'price': price,
        'rsi': rsi,
        'trend': trend,
        'ch_3d': ch_3d,
        'ch_7d': ch_7d,
        'ch_14d': ch_14d,
        'distance': distance,
        'score': score,
        'signals': signals,
        'high_14d': high_14d,
        'low_14d': low_14d
    }

def send_email(subject, body):
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print("Fout: " + str(e))
        return False

if __name__ == "__main__":
    print("Crypto analyse gestart...")
    
    subject = "🎯 Crypto Rapport - " + datetime.now().strftime('%d-%m-%Y')
    body = "📊 CRYPTO DAGRAPPORT\n"
    body += "Datum: " + datetime.now().strftime('%d-%m-%Y') + "\n"
    body += "=" * 80 + "\n\n"
    
    results = {}
    btc_change = 0
    
    # PORTFOLIO
    print("Analyseer portfolio...")
    for coin_id, coin_name in MY_COINS.items():
        df = get_data(coin_id, 60)
        
        if df is not None:
            price = df['price'].iloc[-1]
            rsi = calc_rsi(df)
            trend = get_trend(df)
            ch24 = ((price - df['price'].iloc[-2]) / df['price'].iloc[-2]) * 100 if len(df) >= 2 else 0
            ch7 = ((price - df['price'].iloc[-7]) / df['price'].iloc[-7]) * 100 if len(df) >= 7 else 0
            
            results[coin_name] = {'price': price, 'rsi': rsi, 'trend': trend, 'ch24': ch24, 'ch7': ch7}
            
            if coin_id == 'bitcoin':
                btc_change = ch7
    
    # BTC & ETH
    if 'BTC' in results and 'ETH' in results:
        btc = results['BTC']
        eth = results['ETH']
        
        body += "📈 BITCOIN & ETHEREUM\n"
        body += "-" * 80 + "\n"
        body += "BTC: $" + str(round(btc['price'], 2))
        body += " | 24u: " + str(round(btc['ch24'], 2)) + "%"
        body += " | 7d: " + str(round(btc['ch7'], 2)) + "%"
        body += " | RSI: " + str(round(btc['rsi'], 1))
        body += " | " + btc['trend'] + "\n"
        
        body += "ETH: $" + str(round(eth['price'], 2))
        body += " | 24u: " + str(round(eth['ch24'], 2)) + "%"
        body += " | 7d: " + str(round(eth['ch7'], 2)) + "%"
        body += " | RSI: " + str(round(eth['rsi'], 1))
        body += " | " + eth['trend'] + "\n\n"
        
        score = 0
        if btc['trend'] == "BULLISH": score += 1
        elif btc['trend'] == "BEARISH": score -= 1
        if btc['rsi'] < 30: score += 1
        elif btc['rsi'] > 70: score -= 1
        if eth['trend'] == "BULLISH": score += 1
        elif eth['trend'] == "BEARISH": score -= 1
        if eth['rsi'] < 30: score += 1
        elif eth['rsi'] > 70: score -= 1
        
        sent = "🚀 ZEER BULLISH" if score >= 3 else "📈 BULLISH" if score >= 1 else "📉 BEARISH" if score <= -1 else "⚪ NEUTRAAL"
        body += "MARKT: " + sent + "\n\n"
    
    # BREAKOUT SCANNER - TOONT ALLES
    print("Scan breakouts...")
    body += "=" * 80 + "\n"
    body += "🎯 BREAKOUT WATCHLIST (10 coins)\n"
    body += "=" * 80 + "\n\n"
    
    breakouts = []
    for coin_id, coin_name in WATCHLIST.items():
        df = get_data(coin_id, 30)
        if df is not None:
            data = detect_breakout(df, coin_name)
            if data:
                breakouts.append(data)
    
    breakouts.sort(key=lambda x: x['score'], reverse=True)
    
    # 🟢 POTENTIËLE BREAKOUTS
    body += "🟢 POTENTILE BREAKOUTS (Score 6+):\n"
    body += "-" * 80 + "\n"
    
    high_score = [b for b in breakouts if b['score'] >= 6]
    
    if high_score:
        for coin in high_score:
            body += "\n🔥 " + coin['name'].upper() + " - Score: " + str(coin['score']) + "/10\n"
            body += "💰 Prijs: $" + str(round(coin['price'], 4))
            body += " | 3d: " + str(round(coin['ch_3d'], 2)) + "%"
            body += " | 7d: " + str(round(coin['ch_7d'], 2)) + "%"
            body += " | 14d: " + str(round(coin['ch_14d'], 2)) + "%\n"
            body += "📊 RSI: " + str(round(coin['rsi'], 1))
            body += " | " + coin['trend']
            body += " | Distance: " + str(round(coin['distance'], 2)) + "%\n"
            body += "📈 14d Range: $" + str(round(coin['low_14d'], 4)) + " - $" + str(round(coin['high_14d'], 4)) + "\n"
            if coin['signals']:
                body += "✅ Signalen: " + ", ".join(coin['signals']) + "\n"
    else:
        body += "Geen sterke breakouts vandaag (markt is bearish).\n"
        body += "💡 Tip: Houd coins met RSI < 30 in de gaten voor mogelijke bounce.\n"
    
    body += "\n"
    
    # 👁️ WATCHLIST - TOONT ALLE OVERIGE COINS
    body += "👁️  ALLE WATCHLIST COINS:\n"
    body += "-" * 80 + "\n"
    
    for coin in breakouts:
        if coin['score'] < 6:
            status = "⚪" if coin['score'] >= 4 else "🔻"
            body += status + " " + coin['name'].upper() + ": $" + str(round(coin['price'], 4))
            body += " | 7d: " + str(round(coin['ch_7d'], 2)) + "%"
            body += " | RSI: " + str(round(coin['rsi'], 1))
            body += " | Score: " + str(coin['score'])
            body += " | " + coin['trend'] + "\n"
    
    body += "\n"
    
    # PORTFOLIO - TOONT ALLE COINS
    body += "=" * 80 + "\n"
    body += "📊 JOUW PORTFOLIO (" + str(len(results)) + " coins)\n"
    body += "=" * 80 + "\n\n"
    
    # Sorteer op performance
    sorted_portfolio = sorted(results.items(), key=lambda x: x[1]['ch7'], reverse=True)
    
    for name, data in sorted_portfolio:
        if name in ['BTC', 'ETH']:
            continue
        
        vs_btc = data['ch7'] - btc_change
        
        if data['rsi'] < 30 and vs_btc > 0:
            adv = "🟢 KOOP"
        elif data['rsi'] > 70:
            adv = "🔴 VERKOOP"
        elif data['trend'] == "BEARISH" and vs_btc < -5:
            adv = "⚠️  ZWAK"
        elif data['trend'] == "BULLISH" and vs_btc > 5:
            adv = "💪 STERK"
        else:
            adv = "⚪ HOUDEN"
        
        body += name + ": $" + str(round(data['price'], 4))
        body += " | 24u: " + str(round(data['ch24'], 2)) + "%"
        body += " | 7d: " + str(round(data['ch7'], 2)) + "%"
        body += " | RSI: " + str(round(data['rsi'], 1))
        body += " | " + adv + "\n"
    
    body += "\n" + "=" * 80 + "\n"
    body += "Automatisch rapport van je Crypto Trading Bot.\n"
    body += "Volgende update: vanavond 17:20.\n"
    
    send_email(subject, body)
    print("KLAAR! Email verstuurd.")
