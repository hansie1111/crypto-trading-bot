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

# Email instellingen
EMAIL_ADDRESS = os.environ.get('hansiepansie007@gmail.com', 'jouw_email@gmail.com')
EMAIL_PASSWORD = os.environ.get('asdfg1111!!!!', 'jouw_app_password')
RECEIVER_EMAIL = os.environ.get('hansiepansie009@gmail.com', 'jouw_email@gmail.com')
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

def get_historical_data(coin_id, days=60, max_retries=2):
    """Haal historische data op met retries"""
    
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
            time.sleep(1)
            
            response = requests.get(url, params=params, timeout=10)
            
            if response.status_code == 429:
                print("  Rate limit! Wacht 10 seconden...")
                time.sleep(10)
                continue
            
            if response.status_code != 200:
                print("  HTTP error: " + str(response.status_code))
                time.sleep(2)
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
            time.sleep(2)
        except requests.exceptions.RequestException as e:
            print("  Netwerkfout: " + str(e))
            time.sleep(2)
        except Exception as e:
            print("  Fout: " + str(e))
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

def send_email_report(subject, body):
    """Verstuur email rapport"""
    
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
        print("Email succesvol verstuurd!")
        return True
    except Exception as e:
        print("Fout bij versturen: " + str(e))
        return False

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

def analyze_altcoins_with_email(market_data, email_body):
    """Analyseer altcoins en voeg toe aan email"""
    
    totaal_waarde = 0
    koop_signals = []
    verkoop_signals = []
    hold_signals = []
    
    for coin_id, coin_data in config.PORTFOLIO.items():
        if coin_data['amount'] <= 0:
            continue
        
        naam = coin_data['name']
        amount = coin_data['amount']
        
        if 'manual_price' in coin_data and coin_data['manual_price'] > 0:
            prijs = coin_data['manual_price']
            waarde = prijs * amount
            totaal_waarde += waarde
            hold_signals.append({
                'naam': naam,
                'price': prijs,
                'waarde': waarde,
                'advies': 'Handmatige prijs'
            })
            continue
        
        df = get_historical_data(coin_id, days=60)
        if df is None or len(df) < 14:
            continue
        
        prijs = df['price'].iloc[-1]
        rsi = calculate_rsi(df)
        change_7d = ((prijs - df['price'].iloc[-7]) / df['price'].iloc[-7]) * 100 if len(df) >= 7 else 0
        vs_btc = change_7d - market_data['btc_change_7d']
        waarde = prijs * amount
        totaal_waarde += waarde
        
        if rsi < 30 and vs_btc > 0:
            advies = "KOOP"
            koop_signals.append({
                'naam': naam,
                'price': prijs,
                'rsi': rsi,
                'change_7d': change_7d,
                'waarde': waarde
            })
        elif rsi > 70:
            advies = "VERKOOP"
            verkoop_signals.append({
                'naam': naam,
                'price': prijs,
                'rsi': rsi,
                'change_7d': change_7d,
                'waarde': waarde
            })
        elif vs_btc < -10:
            advies = "ZWAK"
            hold_signals.append({
                'naam': naam,
                'price': prijs,
                'rsi': rsi,
                'advies': advies
            })
        else:
            advies = "HOUDEN"
            hold_signals.append({
                'naam': naam,
                'price': prijs,
                'rsi': rsi,
                'advies': advies
            })
    
    email_body += "Totale Portfolio Waarde: $" + str(round(totaal_waarde, 2)) + "\n\n"
    
    email_body += "-" * 80 + "\n"
    email_body += "KOOP SIGNALEN:\n"
    email_body += "-" * 80 + "\n"
    for coin in koop_signals:
        email_body += coin['naam'] + " - $" + str(round(coin['price'], 4))
        email_body += " | RSI: " + str(round(coin['rsi'], 1))
        email_body += " | 7d: " + str(round(coin['change_7d'], 2)) + "%"
        email_body += " | Waarde: $" + str(round(coin['waarde'], 2)) + "\n"
    
    email_body += "\n"
    email_body += "-" * 80 + "\n"
    email_body += "VERKOOP SIGNALEN:\n"
    email_body += "-" * 80 + "\n"
    for coin in verkoop_signals:
        email_body += coin['naam'] + " - $" + str(round(coin['price'], 4))
        email_body += " | RSI: " + str(round(coin['rsi'], 1))
        email_body += " | 7d: " + str(round(coin['change_7d'], 2)) + "%"
        email_body += " | Waarde: $" + str(round(coin['waarde'], 2)) + "\n"
    
    email_body += "\n"
    email_body += "-" * 80 + "\n"
    email_body += "HOUDEN/ZWAK:\n"
    email_body += "-" * 80 + "\n"
    for coin in hold_signals:
        email_body += coin['naam'] + " - $" + str(round(coin['price'], 4))
        email_body += " | RSI: " + str(round(coin['rsi'], 1))
        email_body += " | Advies: " + coin['advies'] + "\n"
    
    email_body += "\n"
    email_body += "=" * 80 + "\n"
    email_body += "Dit is een automatisch rapport.\n"
    email_body += "Voor vragen: bekijk je scripts in crypto_trading map.\n"
    
    print(email_body)

def analyze_altcoins(market_data):
    """Analyseer altcoins (console versie)"""
    
    print("")
    print("=" * 80)
    print("ALTCOIN ANALYSE")
    print("=" * 80)
    print("")
    
    for coin_id, coin_data in config.PORTFOLIO.items():
        if coin_data['amount'] <= 0:
            continue
        
        naam = coin_data['name']
        amount = coin_data['amount']
        
        print("-" * 80)
        print(naam)
        print("-" * 80)
        
        if 'manual_price' in coin_data and coin_data['manual_price'] > 0:
            price = coin_data['manual_price']
            print("Prijs: $" + str(round(price, 6)) + " (handmatig)")
            print("Jouw positie: " + str(amount) + " = $" + str(round(price * amount, 2)))
            print("Geen technische analyse mogelijk met handmatige prijs")
            print("")
            continue
        
        df = get_historical_data(coin_id, days=60)
        
        if df is None or len(df) < 14:
            print("Geen data beschikbaar - skip")
            print("")
            continue
        
        price = df['price'].iloc[-1]
        rsi = calculate_rsi(df)
        change_7d = ((price - df['price'].iloc[-7]) / df['price'].iloc[-7]) * 100 if len(df) >= 7 else 0
        
        vs_btc = change_7d - market_data['btc_change_7d']
        
        print("Prijs: $" + str(round(price, 6)))
        print("7d: " + str(round(change_7d, 2)) + "%")
        print("RSI: " + str(round(rsi, 1)))
        print("vs BTC: " + ("+" if vs_btc > 0 else "") + str(round(vs_btc, 2)) + "%")
        print("")
        
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
    
    email_subject = "Crypto Dagrapport - " + datetime.now().strftime('%d-%m-%Y')
    email_body = ""
    
    btc_df, eth_df, market_data = analyze_btc_eth()
    
    if market_data:
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
        
        email_body += "\nALTCOIN ANALYSE\n"
        email_body += "=" * 80 + "\n\n"
        
        analyze_altcoins_with_email(market_data, email_body)
        
        send_email_report(email_subject, email_body)
        
        print("=" * 80)
        print("VOLTOOID")
        print("=" * 80)
    else:
        print("Fout: Kon analyse niet voltooien!")
