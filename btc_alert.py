import requests
import json
from datetime import datetime

# ── Config ───────────────────────────────────────────────────
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1531326785130598401/uHRVHWLLkGsGcFGM21DWYAfVbv1m_M8ajElnJK5187meD6gEhyXOV2AzlbIMOPdfKbmT"
SYMBOL = "BTCUSDT"
INTERVAL = "1d"
LIMIT = 300

# ── Fetch data from Binance ───────────────────────────────────
def get_klines(symbol, interval, limit):
    url = f"https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    res = requests.get(url, params=params, timeout=10)
    res.raise_for_status()
    data = res.json()
    closes = [float(k[4]) for k in data]
    return closes

# ── Indicators ───────────────────────────────────────────────
def calc_ema(closes, period):
    k = 2 / (period + 1)
    ema = closes[0]
    result = []
    for i, price in enumerate(closes):
        ema = price * k + ema * (1 - k) if i > 0 else price
        result.append(ema)
    return result

def calc_rsi(closes, period=14):
    gains, losses = 0, 0
    for i in range(1, period + 1):
        d = closes[i] - closes[i - 1]
        if d >= 0:
            gains += d
        else:
            losses -= d
    avg_gain = gains / period
    avg_loss = losses / period
    rsi_list = [None] * period

    if avg_loss == 0:
        rsi_list.append(100)
    else:
        rsi_list.append(100 - 100 / (1 + avg_gain / avg_loss))

    for i in range(period + 1, len(closes)):
        d = closes[i] - closes[i - 1]
        avg_gain = (avg_gain * (period - 1) + max(d, 0)) / period
        avg_loss = (avg_loss * (period - 1) + max(-d, 0)) / period
        if avg_loss == 0:
            rsi_list.append(100)
        else:
            rsi_list.append(100 - 100 / (1 + avg_gain / avg_loss))
    return rsi_list

# ── Send Discord ──────────────────────────────────────────────
def send_discord(message, color):
    payload = {
        "embeds": [{
            "description": message,
            "color": color,
            "timestamp": datetime.utcnow().isoformat()
        }]
    }
    res = requests.post(DISCORD_WEBHOOK, json=payload, timeout=10)
    if res.status_code == 204:
        print("✅ ส่ง Discord สำเร็จ")
    else:
        print(f"❌ Discord error: {res.status_code} {res.text}")

# ── Main ──────────────────────────────────────────────────────
def main():
    print(f"🔍 ตรวจสัญญาณ {SYMBOL} [{INTERVAL}] — {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    closes = get_klines(SYMBOL, INTERVAL, LIMIT)
    ema7  = calc_ema(closes, 7)
    ema30 = calc_ema(closes, 30)
    rsi   = calc_rsi(closes, 14)

    # ตรวจ 2 แท่งล่าสุด
    i = len(closes) - 1
    price = closes[i]

    cross_up   = ema7[i-1] <= ema30[i-1] and ema7[i] > ema30[i]
    cross_down = ema7[i-1] >= ema30[i-1] and ema7[i] < ema30[i]
    rsi_now = rsi[i]

    print(f"💰 ราคา: ${price:,.2f}")
    print(f"📊 EMA7: {ema7[i]:,.2f} | EMA30: {ema30[i]:,.2f}")
    print(f"📈 RSI: {rsi_now:.2f}")

    if cross_up and rsi_now and rsi_now < 65:
        msg = (
            f"🟢 **BUY Signal — {SYMBOL}**\n\n"
            f"💰 ราคา: **${price:,.2f}**\n"
            f"📊 EMA7: {ema7[i]:,.2f} | EMA30: {ema30[i]:,.2f}\n"
            f"📈 RSI: {rsi_now:.2f}\n"
            f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            f"⚡ EMA7 ตัด EMA30 ขึ้น + RSI ยืนยัน"
        )
        print("🟢 BUY Signal!")
        send_discord(msg, 3066993)

    elif cross_down and rsi_now and rsi_now > 35:
        msg = (
            f"🔴 **SELL Signal — {SYMBOL}**\n\n"
            f"💰 ราคา: **${price:,.2f}**\n"
            f"📊 EMA7: {ema7[i]:,.2f} | EMA30: {ema30[i]:,.2f}\n"
            f"📈 RSI: {rsi_now:.2f}\n"
            f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            f"⚡ EMA7 ตัด EMA30 ลง + RSI ยืนยัน"
        )
        print("🔴 SELL Signal!")
        send_discord(msg, 15158332)

    else:
        print("⏳ ไม่มีสัญญาณวันนี้")

if __name__ == "__main__":
    main()
