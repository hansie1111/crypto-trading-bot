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
        time.sleep(2.5)  # Iets langzamer voor betere success rate
        r = requests.get(url, params=params, timeout=15)
        
        if r.status_code == 200:
            data = r.json()
            if 'prices' in data and len(data['prices']) >= 7:
                df = pd.DataFrame(data['prices'], columns=['time', 'price'])
                df['time'] = pd.to_datetime(df['time'], unit='ms')
                df.set_index('time', inplace=True)
                return df
    except Exception as e:
        print("    Fout bij " + coin_id + ": " + str(e))
    
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
    
    subject = "🎯 Crypto Rapport - " + datetime.now().strftime('%d-%m-%Y')
    body = "📊 CRYPTO DAGRAPPORT\n"
    body += "Datum: " + datetime.now().strftime('%d-%m-%Y') + "\n"
    body += "=" * 80 + "\n\n"
    
    portfolio_data = {}
    watchlist_data = {}
    failed_coins = []
    btc_change = 0
    
    # === PORTFOLIO ===
    print("\n📊 Jouw Portfolio:")
    for coin_id, coin_name in MY_COINS.items():
        print("  " + coin_name + "...")
        df = get_data(coin_id, 60)
        
        if df is not None:
            price = df['price'].iloc[-1]
            rsi = calc_rsi(df)
            trend = get_trend(df)
            ch24 = ((price - df['price'].iloc[-2]) / df['price'].iloc[-2]) * 100 if len(df) >= 2 else 0
            ch7 = ((price - df['price'].iloc[-7]) / df['price'].iloc[-7]) * 100 if len(df) >= 7 else 0
            
            portfolio_data[coin_name] = {
                'price': price, 'rsi': rsi, 'trend': trend, 
                'ch24': ch24, 'ch7': ch7
            }
            
            if coin_id == 'bitcoin':
                btc_change = ch7
            
            print("    ✓ $" + str(round(price, 4)))
        else:
            failed_coins.append(coin_name)
            print("    ✗ GEEN DATA")
    
    # === WATCHLIST ===
    print("\n🎯 Watchlist:")
    for coin_id, coin_name in WATCHLIST.items():
        print("  " + coin_name + "...")
        df = get_data(coin_id, 30)
        
        if df is not None:
            price = df['price'].iloc[-1]
            rsi = calc_rsi(df)
            trend = get_trend(df)
            ch7 = ((price - df['price'].iloc[-7]) / df['price'].iloc[-7]) * 100 if len(df) >= 7 else 0
            high_14d = df['price'].rolling(window=14).max().iloc[-1] if len(df) >= 14 else price
            distance = ((high_14d - price) / high_14d) * 100
            
            # Bereken breakout score
            score = 0
            if 0 <= distance < 5: score += 3
            if ch7 > 0: score += 2
            if 45 <= rsi <= 65: score += 2
            if trend == "BULLISH": score += 2
            
            watchlist_data[coin_name] = {
                'price': price, 'rsi': rsi, 'trend': trend,
                'ch7': ch7, 'distance': distance, 'score': score
            }
            
            print("    ✓ $" + str(round(price, 4)) + " | Score: " + str(score))
        else:
            failed_coins.append(coin_name)
            print("    ✗ GEEN DATA")
    
    # === BTC & ETH ===
    if 'BTC' in portfolio_data and 'ETH' in portfolio_data:
        btc = portfolio_data['BTC']
        eth = portfolio_data['ETH']
        
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
        
        sent = "🚀 ZEER BULLISH" if score >= 3 else "📈 BULLISH" if score >= 1 else "📉 BEARISH" if score <= -1 else "⚪ NEUTRAAL"
        body += "MARKT: " + sent + "\n\n"
    
    # === BREAKOUT WATCHLIST ===
    body += "=" * 80 + "\n"
    body += "🎯 BREAKOUT WATCHLIST\n"
    body += "=" * 80 + "\n\n"
    
    # Sorteer op score
    sorted_watchlist = sorted(watchlist_data.items(), key=lambda x: x[1]['score'], reverse=True)
    
    # 🟢 POTENTIËLE BREAKOUTS
    body += "🟢 POTENTIËLE BREAKOUTS (Score 6+):\n"
    body += "-" * 80 + "\n"
    
    high_score = [(n, d) for n, d in sorted_watchlist if d['score'] >= 6]
    
    if high_score:
        for name, data in high_score:
            body += "\n🔥 " + name + " - Score: " + str(data['score']) + "/10\n"
            body += "💰 $" + str(round(data['price'], 4))
            body += " | 7d: " + str(round(data['ch7'], 2)) + "%"
            body += " | RSI: " + str(round(data['rsi'], 1)) + "\n"
            body += "📊 " + data['trend']
            body += " | Distance: " + str(round(data['distance'], 2)) + "%\n"
    else:
        body += "Geen sterke breakouts vandaag.\n"
        body += "💡 Markt is bearish - wacht op betere signalen.\n"
    
    body += "\n"
    
    # 👁️ ALLE WATCHLIST COINS
    body += "👁️  ALLE WATCHLIST COINS:\n"
    body += "-" * 80 + "\n"
    
    if sorted_watchlist:
        for name, data in sorted_watchlist:
            icon = "🟢" if data['score'] >= 6 else "⚪"
            body += icon + " " + name + ": $" + str(round(data['price'], 4))
            body += " | 7d: " + str(round(data['ch7'], 2)) + "%"
            body += " | RSI: " + str(round(data['rsi'], 1))
            body += " | Score: " + str(data['score'])
            body += " | " + data['trend'] + "\n"
    else:
        body += "Geen data beschikbaar.\n"
    
    body += "\n"
    
    # === PORTFOLIO ===
    body += "=" * 80 + "\n"
    body += "📊 JOUW PORTFOLIO (" + str(len(portfolio_data)) + " van " + str(len(MY_COINS)) + " coins)\n"
    body += "=" * 80 + "\n\n"
    
    if portfolio_data:
        # Sorteer op performance
        sorted_portfolio = sorted(portfolio_data.items(), key=lambda x: x[1]['ch7'], reverse=True)
        
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
    else:
        body += "Geen portfolio data beschikbaar.\n"
    
    # Gefaalde coins
    if failed_coins:
        body += "\n⚠️  NIET BESCHIKBAAR (" + str(len(failed_coins)) + "):\n"
        body += "-" * 80 + "\n"
        body += ", ".join(failed_coins) + "\n"
    
    body += "\n" + "=" * 80 + "\n"
    body += "Automatisch rapport.\n"
    body += "Volgende update: 17:20\n"
    
    send_email(subject, body)
    print("\n✅ KLAAR! Email verstuurd.")
    print("Succes: " + str(len(portfolio_data) + len(watchlist_data)) + " coins")
    if failed_coins:
        print("Gefaald: " + str(len(failed_coins)) + " coins")
