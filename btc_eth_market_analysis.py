import requests
import pandas as pd
import numpy as np
import config
import time
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# ========================================
# EMAIL INSTELLINGEN (uit GitHub Secrets)
# ========================================

EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS', 'hansiepansie007@gmail.com')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', 'dmdlcwbhagykoucs')
RECEIVER_EMAIL = os.environ.get('RECEIVER_EMAIL', 'hansiepansie007@gmail.com')
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# ========================================
# COIN IDs MAPPING
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
# DATA OPHALEN
# ========================================

def get_historical_data(coin_id, days=60, max_retries=2):
    """Haal historische data op met retries"""
    
    if coin_id in config.PORTFOLIO and 'manual_price' in config.PORTFOLIO[coin_id]:
        return None
    
    url = "https://api.coingecko.com/api/v3/coins/" + coin_id + "/market_chart"
    params = {
        'vs_currency': 'usd',
        'days': days,
        'interval': 'daily'
    }
    
    for attempt in range(max_retries):
        try:
            time.sleep(1)
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 429:
                time.sleep(10)
                continue
            
            if response.status_code != 200:
                time.sleep(2)
                continue
            
            data = response.json()
            
            if 'prices' not in data or len(data['prices']) < 14:
                return None
            
            prices = data['prices']
            df = pd.DataFrame(prices, columns=['timestamp', 'price'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df.set_index('timestamp', inplace=True)
            
            return df
            
        except Exception as e:
            time.sleep(2)
    
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

def get_trend(df):
    if len(df) < 50:
        return "NEUTRAAL"
    
    current_price = df['price'].iloc[-1]
    ema_20 = df['price'].ewm(span=20, adjust=False).mean().iloc[-1]
    ema_50 = df['price'].ewm(span=50, adjust=False).mean().iloc[-1]
    
    if current_price > ema_20 > ema_50:
        return "BULLISH"
    elif current_price < ema_20 < ema_50:
        return "BEARISH"
    else:
        return "NEUTRAAL"

# ========================================
# EMAIL VERSTUREN
# ========================================

def send_email(subject, body):
    """Verstuur email rapport"""
    
    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = subject
    
    msg.attach(MIMEText(body, 'plain'))
    
    try:
        print("Verbinden met email server...")
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        print("Inloggen...")
        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
        print("Email versturen...")
        server.send_message(msg)
        server.quit()
        print("Email succesvol verstuurd!")
        return True
    except Exception as e:
        print("Fout bij versturen: " + str(e))
        return False

# ========================================
# BTC & ETH ANALYSE
# ========================================

def analyze_btc_eth():
    print("BTC data ophalen...")
    btc_df = get_historical_data('bitcoin', days=90)
    
    print("ETH data ophalen...")
    eth_df = get_historical_data('ethereum', days=90)
    
    if btc_df is None or eth_df is None:
        return None, None, None
    
    # BTC
    btc_price = btc_df['price'].iloc[-1]
    btc_rsi = calculate_rsi(btc_df)
    btc_trend = get_trend(btc_df)
    btc_change_7d = ((btc_price - btc_df['price'].iloc[-7]) / btc_df['price'].iloc[-7]) * 100
    
    # ETH
    eth_price = eth_df['price'].iloc[-1]
    eth_rsi = calculate_rsi(eth_df)
    eth_trend = get_trend(eth_df)
    eth_change_7d = ((eth_price - eth_df['price'].iloc[-7]) / eth_df['price'].iloc[-7]) * 100
    
    # Sentiment
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
        advice = "Sterke bull market! Durf long posities te nemen."
    elif sentiment_score >= 1:
        sentiment = "BULLISH"
        advice = "Positieve markt. Goede kansen."
    elif sentiment_score <= -3:
        sentiment = "ZEER BEARISH"
        advice = "Gevaarlijk! Neem winst, houd stablecoins."
    elif sentiment_score <= -1:
        sentiment = "BEARISH"
        advice = "Voorzichtig. Wees selectief."
    else:
        sentiment = "NEUTRAAL"
        advice = "Zijwaarts. Wacht op richting."
    
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
        'advice': advice
    }
    
    return btc_df, eth_df, market_data

# ========================================
# HOOFDPROGRAMMA
# ========================================

if __name__ == "__main__":
    print("BTC/ETH/ALTCOIN ANALYSE")
    print("=" * 80)
    
    # Bouw email
    email_subject = "Crypto Dagrapport - " + datetime.now().strftime('%d-%m-%Y')
    email_body = ""
    
    # Analyse
    btc_df, eth_df, market_data = analyze_btc_eth()
    
    if market_data:
        # BTC info
        email_body += "BITCOIN & ETHEREUM ANALYSE\n"
        email_body += "=" * 80 + "\n\n"
        email_body += "BTC: $" + str(round(market_data['btc_price'], 2))
        email_body += " | 7d: " + str(round(market_data['btc_change_7d'], 2)) + "%"
        email_body += " | RSI: " + str(round(market_data['btc_rsi'], 1))
        email_body += " | Trend: " + market_data['btc_trend'] + "\n\n"
        
        email_body += "ETH: $" + str(round(market_data['eth_price'], 2))
        email_body += " | 7d: " + str(round(market_data['eth_change_7d'], 2)) + "%"
        email_body += " | RSI: " + str(round(market_data['eth_rsi'], 1))
        email_body += " | Trend: " + market_data['eth_trend'] + "\n\n"
        
        email_body += "MARKT SENTIMENT: " + market_data['sentiment'] + "\n"
        email_body += "ADVIES: " + market_data['advice'] + "\n\n"
        
        email_body += "=" * 80 + "\n"
        email_body += "Dit is een automatisch rapport van je Crypto Trading Bot.\n"
        
        # Verstuur email
        send_email(email_subject, email_body)
        
        print("VOLTOOID")
    else:
        print("Fout: Kon analyse niet voltooien!")
