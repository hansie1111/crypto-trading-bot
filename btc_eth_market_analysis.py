import requests
import pandas as pd
import time
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# EMAIL INSTELLINGEN
EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS', 'hansiepansie007@gmail.com')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', 'dmdlcwbhagykoucs')
RECEIVER_EMAIL = os.environ.get('RECEIVER_EMAIL', 'hansiepansie007@gmail.com')
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# COINS OM TE ANALYSEREN
COINS = {
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

def get_data(coin_id, days=60):
    url = "https://api.coingecko.com/api/v3/coins/" + coin_id + "/market_chart"
    params = {'vs_currency': 'usd', 'days': days, 'interval': 'daily'}
    
    for i in range(2):
        try:
            time.sleep(1)
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if 'prices' in data and len(data['prices']) >= 14:
                    df = pd.DataFrame(data['prices'], columns=['time', 'price'])
                    df['time'] = pd.to_datetime(df['time'], unit='ms')
                    df.set_index('time', inplace=True)
                    return df
        except:
            time.sleep(2)
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
    if len(df) < 50:
        return "NEUTRAAL"
    price = df['price'].iloc[-1]
    ema20 = df['price'].ewm(span=20, adjust=False).mean().iloc[-1]
    ema50 = df['price'].ewm(span=50, adjust=False).mean().iloc[-1]
    if price > ema20 > ema50:
        return "BULLISH"
    elif price < ema20 < ema50:
        return "BEARISH"
    return "NEUTRAAL"

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
        print("Email verstuurd!")
        return True
    except Exception as e:
        print("Fout: " + str(e))
        return False

if __name__ == "__main__":
    print("Crypto analyse gestart...")
    
    subject = "Crypto Dagrapport - " + datetime.now().strftime('%d-%m-%Y')
    body = "CRYPTO DAGRAPPORT\n"
    body += "Datum: " + datetime.now().strftime('%d-%m-%Y') + "\n"
    body += "=" * 80 + "\n\n"
    
    results = {}
    btc_change = 0
    
    for coin_id, coin_name in COINS.items():
        print("Analyseren: " + coin_name)
        df = get_data(coin_id, 90)
        
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
        
        body += "BITCOIN & ETHEREUM\n"
        body += "-" * 80 + "\n"
        body += "BTC: $" + str(round(btc['price'], 2))
        body += " | 24u: " + str(round(btc['ch24'], 2)) + "%"
        body += " | 7d: " + str(round(btc['ch7'], 2)) + "%"
        body += " | RSI: " + str(round(btc['rsi'], 1))
        body += " | Trend: " + btc['trend'] + "\n"
        
        body += "ETH: $" + str(round(eth['price'], 2))
        body += " | 24u: " + str(round(eth['ch24'], 2)) + "%"
        body += " | 7d: " + str(round(eth['ch7'], 2)) + "%"
        body += " | RSI: " + str(round(eth['rsi'], 1))
        body += " | Trend: " + eth['trend'] + "\n\n"
        
        # Sentiment
        score = 0
        if btc['trend'] == "BULLISH": score += 1
        elif btc['trend'] == "BEARISH": score -= 1
        if btc['rsi'] < 30: score += 1
        elif btc['rsi'] > 70: score -= 1
        if eth['trend'] == "BULLISH": score += 1
        elif eth['trend'] == "BEARISH": score -= 1
        if eth['rsi'] < 30: score += 1
        elif eth['rsi'] > 70: score -= 1
        
        if score >= 3:
            sent = "ZEER BULLISH"
            adv = "Sterke bull market!"
        elif score >= 1:
            sent = "BULLISH"
            adv = "Positieve markt."
        elif score <= -3:
            sent = "ZEER BEARISH"
            adv = "Gevaarlijk!"
        elif score <= -1:
            sent = "BEARISH"
            adv = "Voorzichtig."
        else:
            sent = "NEUTRAAL"
            adv = "Zijwaarts."
        
        body += "MARKT: " + sent + "\n"
        body += "ADVIES: " + adv + "\n\n"
    
    # Altcoins
    body += "=" * 80 + "\n"
    body += "ALTCOINS\n"
    body += "=" * 80 + "\n\n"
    
    koop = []
    verkoop = []
    houd = []
    
    for name, data in results.items():
        if name in ['BTC', 'ETH']:
            continue
        
        vs_btc = data['ch7'] - btc_change
        
        if data['rsi'] < 30 and vs_btc > 0:
            koop.append((name, data, vs_btc))
        elif data['rsi'] > 70:
            verkoop.append((name, data, vs_btc))
        else:
            houd.append((name, data, vs_btc))
    
    body += "KOOP:\n"
    body += "-" * 80 + "\n"
    if koop:
        for n, d, v in koop:
            body += n + ": $" + str(round(d['price'], 4))
            body += " | RSI: " + str(round(d['rsi'], 1))
            body += " | 7d: " + str(round(d['ch7'], 2)) + "%"
            body += " | vs BTC: " + ("+" if v > 0 else "") + str(round(v, 2)) + "%"
            body += " | " + d['trend'] + "\n"
    else:
        body += "Geen koop signalen.\n"
    
    body += "\nVERKOOP:\n"
    body += "-" * 80 + "\n"
    if verkoop:
        for n, d, v in verkoop:
            body += n + ": $" + str(round(d['price'], 4))
            body += " | RSI: " + str(round(d['rsi'], 1))
            body += " | 7d: " + str(round(d['ch7'], 2)) + "%"
            body += " | vs BTC: " + ("+" if v > 0 else "") + str(round(v, 2)) + "%"
            body += " | " + d['trend'] + "\n"
    else:
        body += "Geen verkoop signalen.\n"
    
    body += "\nHOUDEN:\n"
    body += "-" * 80 + "\n"
    if houd:
        for n, d, v in houd:
            body += n + ": $" + str(round(d['price'], 4))
            body += " | RSI: " + str(round(d['rsi'], 1))
            body += " | 7d: " + str(round(d['ch7'], 2)) + "%"
            body += " | vs BTC: " + ("+" if v > 0 else "") + str(round(v, 2)) + "%"
            body += " | " + d['trend'] + "\n"
    else:
        body += "Geen.\n"
    
    body += "\n" + "=" * 80 + "\n"
    body += "Automatisch rapport van je Crypto Trading Bot.\n"
    
    send_email(subject, body)
    print("KLAAR!")
