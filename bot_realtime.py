import logging
import math
import re
from datetime import datetime, timedelta
import requests
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from scipy.stats import norm
import os

# Black-Scholes formula for European options
def black_scholes_price(S, K, T, r, sigma, option_type="call"):
    if T <= 0 or sigma <= 0:
        return max(0.0, S - K) if option_type == "call" else max(0.0, K - S)

    d1 = (math.log(S / K) + (r + sigma ** 2 / 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    if option_type == "call":
        price = S * norm.cdf(d1) - K * math.exp(-r * T) * norm.cdf(d2)
    else:
        price = K * math.exp(-r * T) * norm.cdf(-d2) - S * norm.cdf(-d1)

    return round(price, 2)

# Get current stock price from Yahoo Finance
def get_stock_price(symbol):
    url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbol}"
    response = requests.get(url).json()
    try:
        return float(response["quoteResponse"]["result"][0]["regularMarketPrice"])
    except:
        return None

# Parse user message
def parse_message(text):
    pattern = re.compile(
        r"(\b[A-Z]+\b).*?(?:price\s*(\d+(?:\.\d+)?))?.*?(?:strike\s*(\d+(?:\.\d+)?)).*?(?:(?:exp(?:ire)?\s*(\d+)\s*(days?|weeks?|months?))|(?:exp\s*in\s*(\d+)\s*days?))?.*?(call|put)?",
        re.IGNORECASE,
    )
    match = pattern.search(text)
    if match:
        symbol = match.group(1).upper()
        price = float(match.group(2)) if match.group(2) else None
        strike = float(match.group(3))
        exp_num = match.group(4) or match.group(6)
        exp_unit = (match.group(5) or "days").lower()
        option_type = match.group(7).lower() if match.group(7) else "call"

        if exp_num:
            exp_num = int(exp_num)
            if "week" in exp_unit:
                days = exp_num * 7
            elif "month" in exp_unit:
                days = exp_num * 30
            else:
                days = exp_num
        else:
            days = 30  # default expiration

        return symbol, price, strike, days, option_type
    return None, None, None, None, None

# Estimate implied volatility (stub: return fixed value for now)
def get_iv(symbol):
    return 0.55  # example implied volatility

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    symbol, price, strike, days, option_type = parse_message(text)

    if symbol and strike and days and option_type:
        current_price = get_stock_price(symbol) if not price else price
        if not current_price:
            await update.message.reply_text("❌ 获取股价失败，请检查股票代码")
            return

        r = 0.05  # risk-free rate
        T = days / 365
        sigma = get_iv(symbol)

        option_price = black_scholes_price(current_price, strike, T, r, sigma, option_type)
        await update.message.reply_text(
            f"📈 If price = {current_price}, strike = {strike}, {option_type.upper()} = ${option_price} (exp in {days} days)"
        )
    else:
        await update.message.reply_text("请发送格式类似的消息：\nSOXL price 25.5, strike 22, exp 3 weeks, put value?")

def main():
    token = os.environ.get("TELEGRAM_TOKEN")
    if not token:
        raise ValueError("Missing TELEGRAM_TOKEN env variable")

    app = ApplicationBuilder().token(token).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
