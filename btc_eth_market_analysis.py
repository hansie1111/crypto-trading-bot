import requests
import pandas as pd
import numpy as np
import time
import smtplib
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# ========================================
# EMAIL INSTELLINGEN
# ========================================

EMAIL_ADDRESS = os.environ.get('EMAIL_ADDRESS', 'hansiepansie007@gmail.com')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', 'dmdlcwbhagykoucs')
RECEIVER_EMAIL = os.environ.get('RECEIVER_EMAIL', 'hansiepansie007@gmail.com')
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# ========================================
# ALLE COINS OM TE ANALYSEREN
# ========================================

COINS_TO_ANALYZE = {
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
# ANALYSEER ÉÉN COIN
# ========================================

def analyze_coin(coin_id):
    """Analyseer één coin en return data"""
    
    df = get_historical_data(coin_id, days=90)
    
    if df is None or len(df) < 14:
        return None
    
    price = df['price'].iloc[-1]
    rsi = calculate_rsi(df)
    trend = get_trend(df)
    
    # Veranderingen
    change_24h = ((price - df['price'].iloc[-2]) / df['price'].iloc[-2]) * 100 if len(df) >= 2 else 0
    change_7d = ((price - df['price'].iloc[-7]) / df['price'].iloc[-7]) * 100 if len(df) >= 7 else 0
    change_30d = ((price - df['price'].iloc[-30]) / df['price'].iloc[-30]) * 100 if len(df) >= 30 else 0
    
    return {
        'price': price,
        'rsi': rsi,
        'trend': trend,
        'change_24h': change_24h,
        'change_7d': change
