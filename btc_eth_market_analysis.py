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

COINS = {
    'bitcoin': 'BTC',
    'ethereum': 'ETH',
    'render-token': 'RENDER',
    'avalanche-2': 'AVAX',
    'wormhole': 'W',
    'litecoin': 'LTC',
    'near': 'NEAR',
    'renzo': 'REZ',
    'injective-protocol': 'INJ',
    'centrifuge': 'CFG',
    'fetch-ai': 'FET',
    'dash': 'DASH',
    'filecoin': 'FIL',
    'ethereum-name-service': 'ENS'
}

def get_data(coin_id, days=30):
    url = "https://api.coingecko.com/api/v3/coins/" + coin_id + "/market_chart"
    params = {'vs_currency': 'usd', 'days': days, 'interval': 'daily'}
    
    # 3 pogingen om de data op te halen
    for attempt in range(3):
        try:
            time.sleep(5)  # Normaal 5 seconden wachten (snel!)
            
            r = requests.get(url, params=params, timeout=20)
            
            # 🚨 RATE LIMIT DETECTIE
            if r.status_code == 429:
                print("    ⚠️ Rate limit! Wacht 60 seconden en probeer opnieuw...")
                time.sleep(60)  # Lang wachten om de limiet te resetten
                continue
            
            if r.status_code == 200:
                data = r.json()
                if 'prices' in data and len(data['prices']) >= 14:
                    df = pd.DataFrame(data['prices'], columns=['time', 'price'])
                    df['time'] = pd.to_datetime(df['time'], unit='ms')
                    df.set_index('time', inplace=True)
                    return df
                else:
                    return None
            else:
                return None
                
        except Exception as e:
            print("    ✗ Fout: " + str(e))
            time.sleep(10)
    
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
    if len(df) < 20:  # Minder data nodig (was 50)
        return "NEUTRAAL"
    
    price = df['price'].iloc[-1]
    ema20 = df['price'].ewm(span=20, adjust=False).mean().iloc[-1]
    ema50 = df['price'].ewm(span=50, adjust=False).mean().iloc[-1] if len(df) >= 50 else ema20
    
    # Bereken recente momentum
    ch_24h = ((price - df['price'].iloc[-2]) / df['price'].iloc[-2]) * 100 if len(df) >= 2 else 0
    ch_3d = ((price - df['price'].iloc[-3]) / df['price'].iloc[-3]) * 100 if len(df) >= 3 else 0
    
    # Sterke 24u stijging = BULLISH (belangrijk!)
    if ch_24h > 10:
        return "BULLISH"  # +10% of meer = sterk bullish
    elif ch_24h > 5 and ch_3d > 0:
        return "BULLISH"  # +5% vandaag EN positief 3d
    
    # Traditionele EMA logica
    if price > ema20 > ema50:
        return "BULLISH"
    elif price < ema20 < ema50:
        return "BEARISH"
    
    return "NEUTRAAL"

def get_advies(rsi, vs_btc, trend):
    if rsi < 30 and vs_btc > 0:
        return "🟢 KOOP"
    elif rsi > 70:
        return "🔴 VERKOOP"
    elif trend == "BEARISH" and vs_btc < -5:
        return "⚠️  ZWAK"
    elif trend == "BULLISH" and vs_btc > 5:
        return "💪 STERK"
    return "⚪ HOUDEN"

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
    print("Totaal aantal coins: " + str(len(COINS)))
    
    subject = "Crypto Dagrapport - " + datetime.now().strftime('%d-%m-%Y')
    body = "📊 CRYPTO DAGRAPPORT\n"
    body += "Datum: " + datetime.now().strftime('%d-%m-%Y') + "\n"
    body += "=" * 80 + "\n\n"
    
    results = {}
    failed_coins = []
    btc_change = 0
    
    for coin_id, coin_name in COINS.items():
        print("Analyseren: " + coin_name + "...")
        df = get_data(coin_id, 90)
        
        if df is not None:
            price = df['price'].iloc[-1]
            rsi = calc_rsi(df)
            trend = get_trend(df)
            ch24 = ((price - df['price'].iloc[-2]) / df['price'].iloc[-2]) * 100 if len(df) >= 2 else 0
            ch7 = ((price - df['price'].iloc[-7]) / df['price'].iloc[-7]) * 100 if len(df) >= 7 else 0
            
            results[coin_name] = {
                'price': price, 
                'rsi': rsi, 
                'trend': trend, 
                'ch24': ch24, 
                'ch7': ch7
            }
            
            if coin_id == 'bitcoin':
                btc_change = ch7
            
            print("  ✓ " + coin_name + ": $" + str(round(price, 4)))
        else:
            failed_coins.append(coin_name)
            print("  ✗ " + coin_name + ": GEEN DATA")
    
    # Toon gefaalde coins
    if failed_coins:
        body += "⚠️  NIET BESCHIKBAAR:\n"
        body += "-" * 80 + "\n"
        for coin in failed_coins:
            body += coin + "\n"
        body += "\n"
    
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
        
        if score >= 3:
            sent = "🚀 ZEER BULLISH"
            adv = "Sterke bull market!"
        elif score >= 1:
            sent = "📈 BULLISH"
            adv = "Positieve markt."
        elif score <= -3:
            sent = "📉 ZEER BEARISH"
            adv = "Gevaarlijk!"
        elif score <= -1:
            sent = "⚠️  BEARISH"
            adv = "Voorzichtig."
        else:
            sent = "⚪ NEUTRAAL"
            adv = "Zijwaarts."
        
        body += "MARKT: " + sent + "\n"
        body += "ADVIES: " + adv + "\n\n"
    
    # ALLE ALTCOINS
    body += "=" * 80 + "\n"
    body += "📊 ALLE ALTCOINS (" + str(len(results) - 2) + " coins)\n"
    body += "=" * 80 + "\n\n"
    
    all_coins = []
    for name, data in results.items():
        if name in ['BTC', 'ETH']:
            continue
        
        vs_btc = data['ch7'] - btc_change
        advies = get_advies(data['rsi'], vs_btc, data['trend'])
        
        all_coins.append({
            'name': name,
            'price': data['price'],
            'rsi': data['rsi'],
            'ch7': data['ch7'],
            'vs_btc': vs_btc,
            'trend': data['trend'],
            'advies': advies
        })
    
    koop_coins = [c for c in all_coins if "KOOP" in c['advies']]
    verkoop_coins = [c for c in all_coins if "VERKOOP" in c['advies']]
    sterk_coins = [c for c in all_coins if "STERK" in c['advies']]
    zwak_coins = [c for c in all_coins if "ZWAK" in c['advies']]
    houd_coins = [c for c in all_coins if "HOUDEN" in c['advies']]
    
    body += "🟢 KOOP: " + str(len(koop_coins)) + " coins\n"
    body += "-" * 80 + "\n"
    if koop_coins:
        for c in koop_coins:
            body += c['name'] + ": $" + str(round(c['price'], 4))
            body += " | RSI: " + str(round(c['rsi'], 1))
            body += " | 7d: " + str(round(c['ch7'], 2)) + "%"
            body += " | " + c['trend'] + "\n"
    else:
        body += "Geen koop signalen.\n"
    
    body += "\n🔴 VERKOOP: " + str(len(verkoop_coins)) + " coins\n"
    body += "-" * 80 + "\n"
    if verkoop_coins:
        for c in verkoop_coins:
            body += c['name'] + ": $" + str(round(c['price'], 4))
            body += " | RSI: " + str(round(c['rsi'], 1))
            body += " | 7d: " + str(round(c['ch7'], 2)) + "%"
            body += " | " + c['trend'] + "\n"
    else:
        body += "Geen verkoop signalen.\n"
    
    body += "\n💪 STERK: " + str(len(sterk_coins)) + " coins\n"
    body += "-" * 80 + "\n"
    if sterk_coins:
        for c in sterk_coins:
            body += c['name'] + ": $" + str(round(c['price'], 4))
            body += " | RSI: " + str(round(c['rsi'], 1))
            body += " | 7d: " + str(round(c['ch7'], 2)) + "%"
            body += " | " + c['trend'] + "\n"
    else:
        body += "Geen.\n"
    
    body += "\n⚠️  ZWAK: " + str(len(zwak_coins)) + " coins\n"
    body += "-" * 80 + "\n"
    if zwak_coins:
        for c in zwak_coins:
            body += c['name'] + ": $" + str(round(c['price'], 4))
            body += " | RSI: " + str(round(c['rsi'], 1))
            body += " | 7d: " + str(round(c['ch7'], 2)) + "%"
            body += " | " + c['trend'] + "\n"
    else:
        body += "Geen.\n"
    
    body += "\n⚪ HOUDEN: " + str(len(houd_coins)) + " coins\n"
    body += "-" * 80 + "\n"
    if houd_coins:
        for c in houd_coins:
            body += c['name'] + ": $" + str(round(c['price'], 4))
            body += " | RSI: " + str(round(c['rsi'], 1))
            body += " | 7d: " + str(round(c['ch7'], 2)) + "%"
            body += " | " + c['trend'] + "\n"
    else:
        body += "Geen.\n"
    
    body += "\n" + "=" * 80 + "\n"
    body += "Totaal geanalyseerd: " + str(len(results)) + " van " + str(len(COINS)) + " coins\n"
    body += "Automatisch rapport van je Crypto Trading Bot.\n"
    
    send_email(subject, body)
    print("\nKLAAR! Email verstuurd.")
    print("Succes: " + str(len(results)) + "/" + str(len(COINS)) + " coins")
