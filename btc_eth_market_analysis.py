import requests
import pandas as pd
import numpy as np
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

# Jouw portfolio coins
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

# Top coins om te scannen op breakouts (extra coins)
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
    
    for i in range(3):
        try:
            time.sleep(3)
            r = requests.get(url, params=params, timeout=15)
            
            if r.status_code == 429:
                time.sleep(15)
                continue
            
            if r.status_code == 200:
                data = r.json()
                if 'prices' in data and len(data['prices']) >= 7:
                    df = pd.DataFrame(data['prices'], columns=['time', 'price'])
                    df['time'] = pd.to_datetime(df['time'], unit='ms')
                    df.set_index('time', inplace=True)
                    return df
        except Exception as e:
            time.sleep(5)
    
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

def detect_breakout_potential(df, coin_name):
    """Detecteer breakout potentieel"""
    
    if df is None or len(df) < 14:
        return None
    
    current_price = df['price'].iloc[-1]
    
    # Bereken hoge/lage van laatste 14 dagen
    high_14d = df['price'].rolling(window=14).max().iloc[-1]
    low_14d = df['price'].rolling(window=14).min().iloc[-1]
    
    # Hoe dicht bij resistance?
    distance_to_resistance = ((high_14d - current_price) / high_14d) * 100
    
    # Prijs veranderingen
    ch_3d = ((current_price - df['price'].iloc[-3]) / df['price'].iloc[-3]) * 100 if len(df) >= 3 else 0
    ch_7d = ((current_price - df['price'].iloc[-7]) / df['price'].iloc[-7]) * 100 if len(df) >= 7 else 0
    ch_14d = ((current_price - df['price'].iloc[-14]) / df['price'].iloc[-14]) * 100 if len(df) >= 14 else 0
    
    # RSI
    rsi = calc_rsi(df)
    
    # Trend
    trend = get_trend(df)
    
    # Volume analyse (eenvoudig - prijs momentum)
    momentum_score = 0
    if ch_3d > ch_7d:
        momentum_score += 1  # Versnellend
    if ch_7d > 0:
        momentum_score += 1  # Positief
    if rsi > 40 and rsi < 70:
        momentum_score += 1  # Gezonde RSI
    
    # Breakout score
    breakout_score = 0
    signals = []
    
    # 1. Nabij resistance (binnen 5%)
    if distance_to_resistance < 5 and distance_to_resistance >= 0:
        breakout_score += 3
        signals.append("Nabij resistance")
    
    # 2. Opwaartse momentum
    if ch_3d > 0 and ch_7d > 0:
        breakout_score += 2
        signals.append("Opwaarts momentum")
    
    # 3. RSI in gezond gebied
    if 45 <= rsi <= 65:
        breakout_score += 2
        signals.append("Gezonde RSI")
    
    # 4. Bullish trend
    if trend == "BULLISH":
        breakout_score += 2
        signals.append("Bullish trend")
    
    # 5. Versnellend
    if ch_3d > ch_7d > ch_14d:
        breakout_score += 2
        signals.append("Versnellend")
    
    # 6. Net boven moving averages
    if len(df) >= 20:
        ema20 = df['price'].ewm(span=20, adjust=False).mean().iloc[-1]
        if current_price > ema20 and (current_price - ema20) / ema20 < 0.05:
            breakout_score += 1
            signals.append("Boven EMA20")
    
    return {
        'name': coin_name,
        'price': current_price,
        'rsi': rsi,
        'trend': trend,
        'ch_3d': ch_3d,
        'ch_7d': ch_7d,
        'ch_14d': ch_14d,
        'distance_to_res': distance_to_resistance,
        'breakout_score': breakout_score,
        'signals': signals,
        'momentum_score': momentum_score
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
        print("Email verstuurd!")
        return True
    except Exception as e:
        print("Fout: " + str(e))
        return False

if __name__ == "__main__":
    print("Crypto analyse + Breakout Scanner gestart...")
    
    subject = "🎯 Crypto Dagrapport + Breakouts - " + datetime.now().strftime('%d-%m-%Y')
    body = " CRYPTO DAGRAPPORT\n"
    body += "Datum: " + datetime.now().strftime('%d-%m-%Y') + "\n"
    body += "=" * 80 + "\n\n"
    
    results = {}
    failed_coins = []
    btc_change = 0
    
    # === DEEL 1: JOUW PORTFOLIO ANALYSE ===
    print("\n📊 Analyseer jouw portfolio...")
    for coin_id, coin_name in MY_COINS.items():
        print("  " + coin_name + "...")
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
        else:
            failed_coins.append(coin_name)
    
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
    
    # === DEEL 2: BREAKOUT SCANNER ===
    print("\n🎯 Scan naar breakouts...")
    body += "=" * 80 + "\n"
    body += "🎯 BREAKOUT SCANNER (Top 20 coins)\n"
    body += "=" * 80 + "\n\n"
    
    breakout_candidates = []
    
    # Scan watchlist coins
    for coin_id, coin_name in WATCHLIST_COINS.items():
        print("  Scan " + coin_name + "...")
        df = get_data(coin_id, 30)
        
        if df is not None:
            breakout_data = detect_breakout_potential(df, coin_name)
            
            if breakout_data and breakout_data['breakout_score'] >= 3:
                breakout_candidates.append(breakout_data)
    
    # Sorteer op breakout score
    breakout_candidates.sort(key=lambda x: x['breakout_score'], reverse=True)
    
    # Top breakouts
    body += "🔥 TOP BREAKOUT KANDIDATEN:\n"
    body += "-" * 80 + "\n"
    
    if breakout_candidates:
        top_breakouts = breakout_candidates[:10]  # Top 10
        
        for i, coin in enumerate(top_breakouts, 1):
            body += "\n" + str(i) + ". " + coin['name'].upper() + " - Score: " + str(coin['breakout_score']) + "/10\n"
            body += "   Prijs: $" + str(round(coin['price'], 4))
            body += " | 3d: " + str(round(coin['ch_3d'], 2)) + "%"
            body += " | 7d: " + str(round(coin['ch_7d'], 2)) + "%\n"
            body += "   RSI: " + str(round(coin['rsi'], 1))
            body += " | Trend: " + coin['trend']
            body += " | Distance to Resistance: " + str(round(coin['distance_to_res'], 2)) + "%\n"
            
            if coin['signals']:
                body += "   Signalen: " + ", ".join(coin['signals']) + "\n"
    else:
        body += "Geen sterke breakout kandidaten vandaag.\n"
    
    body += "\n"
    
    # Watchlist
    body += "👁️  WATCHLIST (Score 3-5):\n"
    body += "-" * 80 + "\n"
    
    medium_candidates = [c for c in breakout_candidates if 3 <= c['breakout_score'] <= 5]
    
    if medium_candidates:
        for coin in medium_candidates[:5]:
            body += coin['name'].upper() + ": $" + str(round(coin['price'], 4))
            body += " | 7d: " + str(round(coin['ch_7d'], 2)) + "%"
            body += " | Score: " + str(coin['breakout_score']) + "\n"
    else:
        body += "Geen.\n"
    
    body += "\n"
    
    # === DEEL 3: JOUW PORTFOLIO DETAILS ===
    body += "=" * 80 + "\n"
    body += "📊 JOUW PORTFOLIO (" + str(len(results)) + " coins)\n"
    body += "=" * 80 + "\n\n"
    
    all_coins = []
    for name, data in results.items():
        if name in ['BTC', 'ETH']:
            continue
        
        vs_btc = data['ch7'] - btc_change
        
        if data['rsi'] < 30 and vs_btc > 0:
            advies = "🟢 KOOP"
        elif data['rsi'] > 70:
            advies = "🔴 VERKOOP"
        elif data['trend'] == "BEARISH" and vs_btc < -5:
            advies = "⚠️  ZWAK"
        elif data['trend'] == "BULLISH" and vs_btc > 5:
            advies = "💪 STERK"
        else:
            advies = "⚪ HOUDEN"
        
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
    
    body += "🟢 KOOP: " + str(len(koop_coins)) + "\n"
    if koop_coins:
        for c in koop_coins:
            body += c['name'] + ": $" + str(round(c['price'], 4)) + " | " + str(round(c['ch7'], 2)) + "%\n"
    
    body += "\n🔴 VERKOOP: " + str(len(verkoop_coins)) + "\n"
    if verkoop_coins:
        for c in verkoop_coins:
            body += c['name'] + ": $" + str(round(c['price'], 4)) + " | " + str(round(c['ch7'], 2)) + "%\n"
    
    body += "\n💪 STERK: " + str(len(sterk_coins)) + "\n"
    if sterk_coins:
        for c in sterk_coins:
            body += c['name'] + ": $" + str(round(c['price'], 4)) + " | " + str(round(c['ch7'], 2)) + "%\n"
    
    body += "\n⚠️  ZWAK: " + str(len(zwak_coins)) + "\n"
    if zwak_coins:
        for c in zwak_coins:
            body += c['name'] + ": $" + str(round(c['price'], 4)) + " | " + str(round(c['ch7'], 2)) + "%\n"
    
    body += "\n⚪ HOUDEN: " + str(len(houd_coins)) + "\n"
    if houd_coins:
        for c in houd_coins:
            body += c['name'] + ": $" + str(round(c['price'], 4)) + " | " + str(round(c['ch7'], 2)) + "%\n"
    
    body += "\n" + "=" * 80 + "\n"
    body += "Automatisch rapport van je Crypto Trading Bot.\n"
    body += "Breakout Scanner scant 20+ coins op kansen!\n"
    
    send_email(subject, body)
    
    print("\nKLAAR! Email verstuurd.")
    print("Breakout kandidaten gevonden: " + str(len(breakout_candidates)))
