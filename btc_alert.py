import requests
import json
from datetime import datetime

# ── Config ───────────────────────────────────────────────────
DISCORD_WEBHOOK = "https://discord.com/api/webhooks/1531326785130598401/uHRVHWLLkGsGcFGM21DWYAfVbv1m_M8ajElnJK5187meD6gEhyXOV2AzlbIMOPdfKbmT"
LIMIT = 300

SYMBOLS = [
    {"name": "BTC/USDT", "coingecko_id": "bitcoin"},
    {"name": "ETH/USDT", "coingecko_id": "ethereum"},
    {"name": "SOL/USDT", "coingecko_id": "solana"},
]

# ── Fetch data from CoinGecko ────────────────────────────────
def get_klines(coingecko_id, interval="daily"):
    import time
    url = f"https://api.coingecko.com/api/v3/coins/{coingecko_id}/market_chart"
    params = {"vs_currency": "usd", "days": 365, "interval": "daily"}
    # retry สูงสุด 3 ครั้ง ถ้าเจอ 429
    for attempt in range(3):
        res = requests.get(url, params=params, timeout=15)
        if res.status_code == 429:
            wait = 30 * (attempt + 1)
            print(f"⏳ Rate limit — รอ {wait} วินาที แล้วลองใหม่...")
            time.sleep(wait)
            continue
        res.raise_for_status()
        data = res.json()
        prices = [float(p[1]) for p in data["prices"]]
        if interval == "weekly":
            prices = prices[::7]
        return prices
    raise Exception(f"Failed after 3 retries for {coingecko_id}")

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
def check_symbol(name, coingecko_id, interval="daily"):
    tf_label = "1W" if interval == "weekly" else "1D"
    print(f"\n🔍 ตรวจสัญญาณ {name} [{tf_label}] — {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    closes = get_klines(coingecko_id, interval)
    ema7  = calc_ema(closes, 7)
    ema30 = calc_ema(closes, 30)
    rsi   = calc_rsi(closes, 14)

    i = len(closes) - 1
    price = closes[i]
    cross_up   = ema7[i-1] <= ema30[i-1] and ema7[i] > ema30[i]
    cross_down = ema7[i-1] >= ema30[i-1] and ema7[i] < ema30[i]
    rsi_now = rsi[i]

    print(f"💰 ราคา: ${price:,.2f} | EMA7: {ema7[i]:,.2f} | EMA30: {ema30[i]:,.2f} | RSI: {rsi_now:.2f}")

    if cross_up and rsi_now and rsi_now < 65:
        msg = (
            f"🟢 **BUY Signal — {name}**\n\n"
            f"💰 ราคา: **${price:,.2f}**\n"
            f"📊 EMA7: {ema7[i]:,.2f} | EMA30: {ema30[i]:,.2f}\n"
            f"📈 RSI: {rsi_now:.2f}\n"
            f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            f"📅 Timeframe: {tf_label}\n⚡ EMA7 ตัด EMA30 ขึ้น + RSI ยืนยัน"
        )
        print(f"🟢 BUY Signal!")
        send_discord(msg, 3066993)
    elif cross_down and rsi_now and rsi_now > 35:
        msg = (
            f"🔴 **SELL Signal — {name}**\n\n"
            f"💰 ราคา: **${price:,.2f}**\n"
            f"📊 EMA7: {ema7[i]:,.2f} | EMA30: {ema30[i]:,.2f}\n"
            f"📈 RSI: {rsi_now:.2f}\n"
            f"🕐 {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"
            f"📅 Timeframe: {tf_label}\n⚡ EMA7 ตัด EMA30 ลง + RSI ยืนยัน"
        )
        print(f"🔴 SELL Signal!")
        send_discord(msg, 15158332)
    else:
        print(f"⏳ ไม่มีสัญญาณวันนี้")

def main():
    import time
    print("=" * 50)
    print("📅 Daily Signals")
    print("=" * 50)
    for sym in SYMBOLS:
        check_symbol(sym["name"], sym["coingecko_id"], "daily")
        time.sleep(2)

    time.sleep(10)  # หน่วงระหว่าง daily และ weekly
    print("\n" + "=" * 50)
    print("📅 Weekly Signals")
    print("=" * 50)
    for sym in SYMBOLS:
        check_symbol(sym["name"], sym["coingecko_id"], "weekly")
        time.sleep(8)

if __name__ == "__main__":
    main()
