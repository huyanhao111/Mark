import traceback

try:
    import requests
    import math
    import datetime
    import os
    from telegram import Update
    from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler

    # 获取环境变量
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Hello! I'm your option bot.")

    def get_option_price(underlying_price, strike_price, days_to_expiration, volatility, option_type="call"):
        risk_free_rate = 0.01
        d1 = (math.log(underlying_price / strike_price) + (risk_free_rate + 0.5 * volatility ** 2) * (days_to_expiration / 365)) / (volatility * math.sqrt(days_to_expiration / 365))
        d2 = d1 - volatility * math.sqrt(days_to_expiration / 365)
        if option_type == "call":
            return underlying_price * normal_cdf(d1) - strike_price * math.exp(-risk_free_rate * days_to_expiration / 365) * normal_cdf(d2)
        else:
            return strike_price * math.exp(-risk_free_rate * days_to_expiration / 365) * normal_cdf(-d2) - underlying_price * normal_cdf(-d1)

    def normal_cdf(x):
        return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

    def fetch_price(symbol):
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?interval=1m"
        response = requests.get(url)
        data = response.json()
        return data["chart"]["result"][0]["meta"]["regularMarketPrice"]

    async def option(update: Update, context: ContextTypes.DEFAULT_TYPE):
        try:
            text = update.message.text.lower()
            if "call" in text or "put" in text:
                option_type = "call" if "call" in text else "put"
                text = text.replace(option_type, "").strip()

                parts = text.split(" ")
                target_price = float(parts[0].replace("涨到", "").replace("跌到", ""))
                strike_price = float(parts[1].replace("行权价", "").replace("的", ""))
                days = 30
                for i, part in enumerate(parts):
                    if part.startswith("exp"):
                        if "day" in part:
                            days = int(part.replace("exp", "").replace("days", "").strip())
                        elif "week" in part:
                            days = int(part.replace("exp", "").replace("weeks", "").strip()) * 7
                        elif "month" in part:
                            days = int(part.replace("exp", "").replace("months", "").strip()) * 30

                symbol = "SOXL"
                if "tsla" in text: symbol = "TSLA"
                elif "nvda" in text: symbol = "NVDA"
                elif "amd" in text: symbol = "AMD"
                elif "msft" in text: symbol = "MSFT"
                elif "baba" in text: symbol = "BABA"

                current_price = fetch_price(symbol)
                iv = 0.6
                price = get_option_price(current_price, strike_price, days, iv, option_type)

                await context.bot.send_message(chat_id=update.effective_chat.id, text=(
                    f"{symbol} 当前价：{current_price:.2f}\n"
                    f"期权类型：{option_type.upper()}\n"
                    f"行权价：{strike_price}\n"
                    f"剩余天数：{days}\n"
                    f"估算价格：${price:.2f}"
                ))
            else:
                await context.bot.send_message(chat_id=update.effective_chat.id, text="请输入格式如：SOXL 涨到25 行权价23 的 call value")
        except Exception as e:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=f"错误：{e}")

    if __name__ == '__main__':
        app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("option", option))
        app.run_polling()

except Exception as e:
    print("❌ ERROR on startup:", e)
    traceback.print_exc()
