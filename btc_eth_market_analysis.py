import requests
import pandas as pd
import numpy as np
import config
import time
from datetime import datetime

# ========================================
# COIN IDs MAPPING (CORRECTE IDs)
# ========================================

COIN_IDS = {
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

# ========================================
# DATA OPHALEN MET RETRIES
# ========================================

def get_historical_data(coin_id, days=60, max_retries=3):
    """Haal historische data op met retries"""
    
    # Check voor handmatige prijs
    if coin_id in config.PORTFOLIO and 'manual_price' in config.PORTFOLIO[coin_id]:
        print("  (Handmatige prijs - skip analyse)")
        return None
    
    url = "https://api.coingecko.com/api/v3/coins/" + coin_id + "/market_chart"
    params = {
        'vs_currency': 'usd',
        'days': days,
        'interval': 'daily'
    }
    
    for attempt in range(max_retries):
        try:
            print("  Poging " + str(attempt + 1) + "/" + str(max_retries) + "...")
            time.sleep(3)  # Wacht 3 seconden (rate limit)
            
            response = requests.get(url, params=params, timeout=15)
            
            if response.status_code == 429:
                print("  Rate limit! Wacht 10 seconden...")
                time.sleep(10)
                continue
            
            if response.status_code != 200:
                print("  HTTP error: " + str(response.status_code))
                time.sleep(5)
                continue
            
            data = response.json()
            
            if 'prices' not in data or len(data['prices']) < 14:
                print("  Onvoldoende data ontvangen")
                return None
            
            prices = data['prices']
            df = pd.DataFrame(prices, columns=['timestamp', 'price'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except requests.exceptions.Timeout:
            print("  Time-out!")
            time.sleep(5)
        except requests.exceptions.RequestException as e:
            print("  Netwerkfout: " + str(e))
            time.sleep(5)
        except Exception as e:
            print("  Fout: " + str(e))
            time.sleep(5)
    
    return None

def calculate_rsi(df, period=14):
    if len(df) < period:
        return 50
    delta = df['price'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi.iloc[-1] if not rsi.empty else 50

def calculate_ema(df, period):
    if len(df) >= period:
        return df['price'].ewm(span=period, adjust=False).mean().iloc[-1]
    return None

def get_trend(df):
    if len(df) < 50:
        return "NEUTRAAL"
    
    current_price = df['price'].iloc[-1]
    ema_20 = df['price'].ewm(span=20, adjust=False).mean().iloc[-1]
    ema_50 = df['price'].ewm(span=50, adjust=False).mean().iloc[-1]
    ema_200 = df['price'].ewm(span=200, adjust=False).mean().iloc[-1] if len(df) >= 200 else None
    
    if ema_200 and current_price > ema_200 and ema_20 > ema_50:
        return "BULLISH"
    elif ema_200 and current_price < ema_200 and ema_20 < ema_50:
        return "BEARISH"
    else:
        return "NEUTRAAL"

# ========================================
# BTC & ETH ANALYSE
# ========================================

def analyze_btc_eth():
    print("=" * 80)
    print("BITCOIN & ETHEREUM MARKT ANALYSE")
    print("=" * 80)
    print("Tijd: " + datetime.now().strftime('%H:%M:%S'))
    print("Datum: " + datetime.now().strftime('%d-%m-%Y'))
    print("=" * 80)
    print("")
    
    print("BTC data ophalen...")
    btc_df = get_historical_data('bitcoin', days=90)
    
    print("ETH data ophalen...")
    eth_df = get_historical_data('ethereum', days=90)
    
    if btc_df is None or eth_df is None:
        print("Fout: Kon geen BTC/ETH data ophalen!")
        return None, None, None
    
    # BTC Analyse
    print("")
    print("=" * 80)
    print("BITCOIN (BTC)")
    print("=" * 80)
    
    btc_price = btc_df['price'].iloc[-1]
    btc_rsi = calculate_rsi(btc_df)
    btc_trend = get_trend(btc_df)
    btc_change_24h = ((btc_price - btc_df['price'].iloc[-2]) / btc_df['price'].iloc[-2]) * 100
    btc_change_7d = ((btc_price - btc_df['price'].iloc[-7]) / btc_df['price'].iloc[-7]) * 100
    btc_change_30d = ((btc_price - btc_df['price'].iloc[-30]) / btc_df['price'].iloc[-30]) * 100 if len(btc_df) >= 30 else 0
    
    print("Prijs: $" + str(round(btc_price, 2)))
    print("24u: " + str(round(btc_change_24h, 2)) + "%")
    print("7d: " + str(round(btc_change_7d, 2)) + "%")
    print("30d: " + str(round(btc_change_30d, 2)) + "%")
    print("RSI: " + str(round(btc_rsi, 1)))
    print("Trend: " + btc_trend)
    
    # ETH Analyse
    print("")
    print("=" * 80)
    print("ETHEREUM (ETH)")
    print("=" * 80)
    
    eth_price = eth_df['price'].iloc[-1]
    eth_rsi = calculate_rsi(eth_df)
    eth_trend = get_trend(eth_df)
    eth_change_24h = ((eth_price - eth_df['price'].iloc[-2]) / eth_df['price'].iloc[-2]) * 100
    eth_change_7d = ((eth_price - eth_df['price'].iloc[-7]) / eth_df['price'].iloc[-7]) * 100
    eth_change_30d = ((eth_price - eth_df['price'].iloc[-30]) / eth_df['price'].iloc[-30]) * 100 if len(eth_df) >= 30 else 0
    
    print("Prijs: $" + str(round(eth_price, 2)))
    print("24u: " + str(round(eth_change_24h, 2)) + "%")
    print("7d: " + str(round(eth_change_7d, 2)) + "%")
    print("30d: " + str(round(eth_change_30d, 2)) + "%")
    print("RSI: " + str(round(eth_rsi, 1)))
    print("Trend: " + eth_trend)
    
    # Markt Sentiment
    print("")
    print("=" * 80)
    print("MARKT SENTIMENT")
    print("=" * 80)
    
    sentiment_score = 0
    if btc_trend == "BULLISH": sentiment_score += 1
    elif btc_trend == "BEARISH": sentiment_score -= 1
    if btc_rsi < 30: sentiment_score += 1
    elif btc_rsi > 70: sentiment_score -= 1
    if eth_trend == "BULLISH": sentiment_score += 1
    elif eth_trend == "BEARISH": sentiment_score -= 1
    if eth_rsi < 30: sentiment_score += 1
    elif eth_rsi > 70: sentiment_score -= 1
    
    if sentiment_score >= 3:
        sentiment = "ZEER BULLISH"
        emoji = "🚀"
        advice = "Sterke bull market! Durf long posities te nemen."
    elif sentiment_score >= 1:
        sentiment = "BULLISH"
        emoji = "📈"
        advice = "Positieve markt. Goede kansen."
    elif sentiment_score <= -3:
        sentiment = "ZEER BEARISH"
        emoji = "📉"
        advice = "Gevaarlijk! Neem winst, houd stablecoins."
    elif sentiment_score <= -1:
        sentiment = "BEARISH"
        emoji = "⚠️"
        advice = "Voorzichtig. Wees selectief."
    else:
        sentiment = "NEUTRAAL"
        emoji = "⚪"
        advice = "Zijwaarts. Wacht op richting."
    
    print("Sentiment: " + sentiment + " " + emoji)
    print("Advies: " + advice)
    
    market_data = {
        'btc_price': btc_price,
        'btc_rsi': btc_rsi,
        'btc_trend': btc_trend,
        'btc_change_7d': btc_change_7d,
        'eth_price': eth_price,
        'eth_rsi': eth_rsi,
        'eth_trend': eth_trend,
        'eth_change_7d': eth_change_7d,
        'sentiment': sentiment,
        'sentiment_score': sentiment_score,
        'advice': advice
    }
    
    return btc_df, eth_df, market_data

def analyze_altcoins(market_data):
    print("")
    print("=" * 80)
    print("ALTCOIN ANALYSE")
    print("=" * 80)
    print("")
    
    # Alleen coins met amounts > 0
    for coin_id, coin_data in config.PORTFOLIO.items():
        if coin_data['amount'] <= 0:
            continue
        
        naam = coin_data['name']
        amount = coin_data['amount']
        
        print("-" * 80)
        print(naam)
        print("-" * 80)
        
        # Check handmatige prijs
        if 'manual_price' in coin_data and coin_data['manual_price'] > 0:
            price = coin_data['manual_price']
            print("Prijs: $" + str(round(price, 6)) + " (handmatig)")
            print("Jouw positie: " + str(amount) + " = $" + str(round(price * amount, 2)))
            print("Geen technische analyse mogelijk met handmatige prijs")
            print("")
            continue
        
        # Haal data op
        df = get_historical_data(coin_id, days=60)
        
        if df is None or len(df) < 14:
            print("Geen data beschikbaar - skip")
            print("")
            continue
        
        # Analyse
        price = df['price'].iloc[-1]
        rsi = calculate_rsi(df)
        change_7d = ((price - df['price'].iloc[-7]) / df['price'].iloc[-7]) * 100 if len(df) >= 7 else 0
        
        vs_btc = change_7d - market_data['btc_change_7d']
        
        print("Prijs: $" + str(round(price, 6)))
        print("7d: " + str(round(change_7d, 2)) + "%")
        print("RSI: " + str(round(rsi, 1)))
        print("vs BTC: " + ("+" if vs_btc > 0 else "") + str(round(vs_btc, 2)) + "%")
        print("")
        
        # Advies
        print("Advies:")
        if rsi < 30 and vs_btc > 0:
            print("  🟢 KOOP - Oversold + sterker dan BTC")
        elif rsi > 70:
            print("  🔴 VERKOOP - Overbought")
        elif vs_btc < -10:
            print("  ⚠️  ZWAK - Veel slechter dan BTC")
        else:
            print("  ⚪ HOUDEN")
        
        print("")

if __name__ == "__main__":
    print("")
    print("🚀 BTC/ETH/ALTCOIN ANALYSE")
    print("⏳ Dit duurt even...")
    print("")
    
    btc_df, eth_df, market_data = analyze_btc_eth()
    
    if market_data:
        analyze_altcoins(market_data)
        
        print("=" * 80)
        print("VOLTOOID")
        print("=" * 80)
