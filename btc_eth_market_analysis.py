import requests
import pandas as pd
import time
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
import os

EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS', 'hansiepansie007@gmail.com')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', 'dmdlcwbhagykoucs')
RECEIVER_EMAIL = os.environ.get('RECEIVER_EMAIL', 'hansiepansie007@gmail.com')
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# Jouw 6 coins
MY_COINS = {
    'bitcoin': 'BTC',
    'ethereum': 'ETH',
    'render-token': 'RENDER',
    'avalanche-2': 'AVAX',
    'wormhole': 'W',
    'peaq': 'PEAQ'
}

def get_data(coin_id, days=30, max_retries=3):
    """Haal data op met retries"""
    url = "https://api.coingecko.com/api/v3/coins/" + coin_id + "/market_chart"
    params = {'vs_currency': 'usd', 'days': days, 'interval': 'daily'}
    
    for attempt in range(max_retries):
        try:
            print("    Poging " + str(attempt + 1) + "/" + str(max_retries) + "...")
            time.sleep(5)  # 5 seconden wachten tussen calls
            
            r = requests.get(url, params=params, timeout=20)  # 20 seconden timeout
            
            if r.status_code == 429:
                print("    Rate limit! Wacht 30 seconden...")
                time.sleep(30)
                continue
            
            if r.status_code == 200:
                data = r.json()
                if 'prices' in data and len(data['prices']) >= 7:
                    df = pd.DataFrame(data['prices'], columns=['time', 'price'])
                    df['time'] = pd.to_datetime(df['time'], unit='ms')
                    df.set_index('time', inplace=True)
                    print("    ✓ Succes!")
                    return df
                else:
                    print("    ✗ Onvoldoende data")
            else:
                print("    ✗ HTTP error: " + str(r.status_code))
                
        except requests.exceptions.Timeout:
            print("    ✗ Time-out!")
            time.sleep(10)
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
        print("Email fout: " + str(e))
        return False

if __name__ == "__main__":
    print("Crypto analyse gestart...")
    print("Aantal coins: " + str(len(MY_COINS)))
    
    subject = "📊 Crypto Rapport - " + datetime.now().strftime('%d-%m-%Y')
    body = "📊 CRYPTO DAGRAPPORT\n"
    body += "Datum: " + datetime.now().strftime('%d-%m-%Y') + "\n"
    body += "=" * 80 + "\n\n"
    
    results = {}
    failed = []
    btc_change = 0
    
    print("\nAnalyseer coins...")
    for coin_id, coin_name in MY_COINS.items():
        print("\n  " + coin_name + "...")
        df = get_data(coin_id, days=30, max_retries=2)
        
        if df is not None:
            price = df['price'].iloc[-1]
            rsi = calc_rsi(df)
            trend = get_trend(df)
            ch24 = ((price - df['price'].iloc[-2]) / df['price'].iloc[-2]) * 100 if len(df) >= 2 else 0
            ch7 = ((price - df['price'].iloc[-7]) / df['price'].iloc[-7]) * 100 if len(df) >= 7 else 0
            
            results[coin_name] = {
                'price': price, 'rsi': rsi, 'trend': trend,
                'ch24': ch24, 'ch7': ch7
            }
            
            if coin_id == 'bitcoin':
                btc_change = ch7
            
            print("    $" + str(round(price, 4)))
        else:
            failed.append(coin_name)
            print("    ✗ GEEN DATA")
    
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
    
    # PORTFOLIO
    body += "=" * 80 + "\n"
    body += "📊 JOUW PORTFOLIO (" + str(len(results)) + " coins)\n"
    body += "=" * 80 + "\n\n"
    
    if results:
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
    
    # Gefaalde coins
    if failed:
        body += "\n⚠️  NIET BESCHIKBAAR (" + str(len(failed)) + "):\n"
        body += "-" * 80 + "\n"
        body += ", ".join(failed) + "\n"
    
    body += "\n" + "=" * 80 + "\n"
    body += "Automatisch rapport.\n"
    body += "Volgende update: 17:20\n"
    
    send_email(subject, body)
    print("\n✅ KLAAR! Email verstuurd.")
    print("Succes: " + str(len(results)) + "/" + str(len(MY_COINS)) + " coins")
    if failed:
        print("Gefaald: " + ", ".join(failed))
