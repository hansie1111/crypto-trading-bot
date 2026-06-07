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

# Jouw 11 coins
COINS_TO_SCAN = {
    'polkadot': 'DOT',
    'chainlink': 'LINK',
    'litecoin': 'LTC',
    'arbitrum': 'ARB',
    'optimism': 'OP',
    'sui': 'SUI',
    'celestia': 'TIA',
    'algorand': 'ALGO',
    'cosmos': 'ATOM',
    'stellar': 'XLM'
}

def get_data(coin_id, days=30):
    url = "https://api.coingecko.com/api/v3/coins/" + coin_id + "/market_chart"
    params = {'vs_currency': 'usd', 'days': days, 'interval': 'daily'}
    
    for attempt in range(2):
        try:
            time.sleep(8)  # 8 seconden tussen elke request
            print("    Wacht 8 seconden...")
            
            r = requests.get(url, params=params, timeout=20)
            
            if r.status_code == 429:
                print("    Rate limit! Wacht 30 seconden...")
                time.sleep(30)
                continue
            
            if r.status_code == 200:
                data = r.json()
                if 'prices' in data and len(data['prices']) >= 14:
                    df = pd.DataFrame(data['prices'], columns=['time', 'price'])
                    df['time'] = pd.to_datetime(df['time'], unit='ms')
                    df.set_index('time', inplace=True)
                    print("    ✓ Succes!")
                    return df
                else:
                    print("    ✗ Onvoldoende data")
            else:
                print("     HTTP error: " + str(r.status_code))
                
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
    
    # Bereken korte-termijn momentum
    ch_24h = ((price - df['price'].iloc[-2]) / df['price'].iloc[-2]) * 100 if len(df) >= 2 else 0
    ch_3d = ((price - df['price'].iloc[-3]) / df['price'].iloc[-3]) * 100 if len(df) >= 3 else 0
    
    # Sterke 24u stijging = minstens NEUTRAAL
    if ch_24h > 10:
        return "BULLISH"  # Sterke stijging!
    elif ch_24h > 5:
        if price > ema20:
            return "BULLISH"
        else:
            return "NEUTRAAL"  # Herstel maar nog niet boven EMA
    
    # Traditionele EMA logica
    if price > ema20 > ema50:
        return "BULLISH"
    elif price < ema20 < ema50:
        return "BEARISH"
    else:
        return "NEUTRAAL"

def detect_breakout(df, coin_name):
    if df is None or len(df) < 14:
        return None
    
    price = df['price'].iloc[-1]
    high_14d = df['price'].rolling(window=14).max().iloc[-1]
    low_14d = df['price'].rolling(window=14).min().iloc[-1]
    high_7d = df['price'].rolling(window=7).max().iloc[-1]
    
    # Bereken veranderingen
    ch_1d = ((price - df['price'].iloc[-2]) / df['price'].iloc[-2]) * 100 if len(df) >= 2 else 0
    ch_3d = ((price - df['price'].iloc[-3]) / df['price'].iloc[-3]) * 100 if len(df) >= 3 else 0
    ch_7d = ((price - df['price'].iloc[-7]) / df['price'].iloc[-7]) * 100 if len(df) >= 7 else 0
    ch_14d = ((price - df['price'].iloc[-14]) / df['price'].iloc[-14]) * 100 if len(df) >= 14 else 0
    
    rsi = calc_rsi(df)
    trend = get_trend(df)
    
    # Distance calculations
    distance_to_resistance = ((high_14d - price) / high_14d) * 100
    distance_from_support = ((price - low_14d) / low_14d) * 100
    
    # Consolidatie detectie (lage volatiliteit)
    if len(df) >= 14:
        price_range = (high_14d - low_14d) / low_14d * 100
        is_consolidating = price_range < 15  # Minder dan 15% range = consolidatie
    else:
        is_consolidating = False
    
    # Breakout score berekenen
    score = 0
    signals = []
    
    # 1. Nabij resistance (binnen 5%) = IMMEDIATE BREAKOUT
    if 0 <= distance_to_resistance < 5:
        score += 5
        signals.append("🔥 Nabij resistance")
    # 2. Dichtbij resistance (5-10%) = NEAR BREAKOUT
    elif 5 <= distance_to_resistance < 10:
        score += 3
        signals.append("🟡 Dichtbij resistance")
    # 3. Binnen bereik (10-15%) = WATCH
    elif 10 <= distance_to_resistance < 15:
        score += 2
        signals.append("⚠️  Binnen bereik")
    
    # 4. Opwaarts momentum
    if ch_3d > 0 and ch_7d > 0:
        score += 2
        signals.append("Opwaarts momentum")
    
    # 5. Versnellend
    if ch_3d > ch_7d > ch_14d:
        score += 3
        signals.append("Versnellend")
    
    # 6. Gezonde RSI
    if 45 <= rsi <= 65:
        score += 2
        signals.append("Gezonde RSI")
    elif 30 <= rsi < 45:
        score += 1
        signals.append("RSI herstelt")
    
    # 7. Bullish trend
    if trend == "BULLISH":
        score += 3
        signals.append("Bullish trend")
    
    # 8. Boven EMA20
    if len(df) >= 20:
        ema20 = df['price'].ewm(span=20, adjust=False).mean().iloc[-1]
        if price > ema20 and (price - ema20) / ema20 < 0.05:
            score += 2
            signals.append("Boven EMA20")
    
    # 9. Consolidatie fase (grote move komt eraan!)
    if is_consolidating and distance_to_resistance < 15:
        score += 3
        signals.append("📊 Consolidatie - breakout mogelijk!")
    
    # 10. Sterke 24u beweging
    if ch_1d > 5:
        score += 2
        signals.append(f"Sterke 24u (+{ch_1d:.1f}%)")
    
    return {
        'name': coin_name,
        'price': price,
        'rsi': rsi,
        'trend': trend,
        'ch_1d': ch_1d,
        'ch_3d': ch_3d,
        'ch_7d': ch_7d,
        'ch_14d': ch_14d,
        'distance_to_res': distance_to_resistance,
        'distance_from_support': distance_from_support,
        'high_14d': high_14d,
        'low_14d': low_14d,
        'score': score,
        'signals': signals,
        'is_consolidating': is_consolidating
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
    print(" BREAKOUT SCANNER GESTART...")
    print("Scan " + str(len(COINS_TO_SCAN)) + " coins...")
    
    subject = "🔥 BREAKOUT ALERT - " + datetime.now().strftime('%d-%m-%Y %H:%M')
    body = "🔥 BREAKOUT SCANNER\n"
    body += "Tijd: " + datetime.now().strftime('%d-%m-%Y %H:%M') + "\n"
    body += "=" * 80 + "\n\n"
    
    all_results = []
    failed = []
    
    print("\nScannen...")
    for coin_id, coin_name in COINS_TO_SCAN.items():
        print("\n  " + coin_name + "...")
        df = get_data(coin_id, 30)
        
        if df is not None:
            data = detect_breakout(df, coin_name)
            if data:
                all_results.append(data)
                print("    ✓ Score: " + str(data['score']))
        else:
            failed.append(coin_name)
            print("    ✗ Geen data")
    
    # Sorteer op score
all_results.sort(key=lambda x: x['score'], reverse=True)

# 🟢 TOP BREAKOUTS (Score 8+)
body += "🟢 TOP BREAKOUT KANDIDATEN (Score 8+):\n"
body += "-" * 80 + "\n\n"

top_breakouts = [r for r in all_results if r['score'] >= 8]

if top_breakouts:
    for i, coin in enumerate(top_breakouts[:10], 1):
        body += str(i) + ". 🔥 " + coin['name'].upper() + " - Score: " + str(coin['score']) + "/15\n"
        body += "   💰 Prijs: $" + str(round(coin['price'], 4)) + "\n"
        body += "   📊 1d: " + str(round(coin['ch_1d'], 2)) + "%"
        body += " | 3d: " + str(round(coin['ch_3d'], 2)) + "%"
        body += " | 7d: " + str(round(coin['ch_7d'], 2)) + "%\n"
        body += "   📈 RSI: " + str(round(coin['rsi'], 1))
        body += " | " + coin['trend']
        body += " | Distance: " + str(round(coin['distance_to_res'], 2)) + "%\n"
        
        if coin.get('is_consolidating', False):
            body += "   📊 CONSOLIDATIE - Grote move komt eraan!\n"
        
        if coin['signals']:
            body += "   ✅ Signalen: " + ", ".join(coin['signals']) + "\n"
        
        body += "\n"
else:
    body += "Geen sterke breakouts gevonden.\n"
    body += "💡 De markt is rustig - wacht op betere kansen.\n\n"

# 🟡 NEAR BREAKOUT WATCHLIST (Score 5-7)
body += "\n🟡 NEAR BREAKOUT WATCHLIST (Score 5-7):\n"
body += "-" * 80 + "\n\n"
body += "💡 Deze coins komen DICHTBIJ een breakout - houd in de gaten!\n\n"

near_breakouts = [r for r in all_results if 5 <= r['score'] < 8]

if near_breakouts:
    for coin in near_breakouts:
        body += "⚡ " + coin['name'].upper() + ": $" + str(round(coin['price'], 4))
        body += " | 7d: " + str(round(coin['ch_7d'], 2)) + "%"
        body += " | RSI: " + str(round(coin['rsi'], 1))
        body += " | Distance: " + str(round(coin['distance_to_res'], 2)) + "%\n"
        
        if coin.get('is_consolidating', False):
            body += "   📊 Consolidatie fase - breakout kan elk moment komen!\n"
        
        if coin['signals']:
            body += "   Signalen: " + ", ".join(coin['signals'][:2]) + "\n"
        
        body += "\n"
else:
    body += "Geen.\n"

# 👁️ MONITORING (Score 3-4)
body += "\n👁️  MONITORING (Score 3-4):\n"
body += "-" * 80 + "\n\n"
body += "🔍 Deze coins zijn interessant maar nog niet klaar voor breakout.\n\n"

monitoring = [r for r in all_results if 3 <= r['score'] < 5]

if monitoring:
    for coin in monitoring:
        body += "⚪ " + coin['name'].upper() + ": $" + str(round(coin['price'], 4))
        body += " | 7d: " + str(round(coin['ch_7d'], 2)) + "%"
        body += " | Score: " + str(coin['score']) + "\n"
else:
    body += "Geen.\n"

# 📊 STATISTIEKEN
body += "\n" + "=" * 80 + "\n"
body += "📊 SCAN STATISTIEKEN\n"
body += "=" * 80 + "\n\n"

body += "Totaal gescand: " + str(len(COINS_TO_SCAN)) + " coins\n"
body += "Succesvol: " + str(len(all_results)) + " coins\n"
body += "Gefaald: " + str(len(failed)) + " coins\n"
body += "Top breakouts (8+): " + str(len(top_breakouts)) + "\n"
body += "Near breakouts (5-7): " + str(len(near_breakouts)) + "\n"
body += "Monitoring (3-4): " + str(len(monitoring)) + "\n"

if failed:
    body += "\n⚠️  Niet beschikbaar: " + ", ".join(failed)

body += "\n\n" + "=" * 80 + "\n"
body += "💡 TIP: Houd Near Breakout coins in de gaten!\n"
body += "Volgende scan: over 12 uur.\n"

send_email(subject, body)

print("\n✅ KLAAR! Email verstuurd.")
print("Top breakouts: " + str(len(top_breakouts)))
print("Near breakouts: " + str(len(near_breakouts)))
print("Monitoring: " + str(len(monitoring)))
if failed:
    print("Gefaald: " + ", ".join(failed))
