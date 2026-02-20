# 🤖 Binance Futures Testnet — Trading Bot

A clean, production-structured Python trading bot that places **MARKET**, **LIMIT**, and **STOP_MARKET** orders on the [Binance Futures Testnet](https://testnet.binancefuture.com) via REST API.

---

## 📋 Table of Contents

1. [Features](#features)
2. [Project Structure](#project-structure)
3. [Prerequisites](#prerequisites)
4. [Setup](#setup)
5. [Running the Bot](#running-the-bot)
6. [CLI Reference](#cli-reference)
7. [Examples](#examples)
8. [Logging](#logging)
9. [Error Handling](#error-handling)
10. [Assumptions & Design Decisions](#assumptions--design-decisions)

---

## ✨ Features

| Feature | Details |
|---|---|
| Order types | MARKET, LIMIT, STOP_MARKET (bonus) |
| Sides | BUY and SELL |
| Input validation | Symbol format, side, quantity > 0, price required for LIMIT |
| Structured code | Separate client, orders, validators, and CLI layers |
| Logging | Console (INFO) + rotating log file (DEBUG), no noise |
| Error handling | Validation errors, API errors, network timeouts |
| Credentials | Loaded from environment variables or `.env` file |
| Retries | Automatic retry on 429 / 5xx HTTP responses |

---

## 🗂️ Project Structure

```
trading_bot/
├── bot/
│   ├── __init__.py          # Package marker
│   ├── client.py            # Binance REST client (signing, HTTP, retries)
│   ├── orders.py            # Order placement logic + pretty-print output
│   ├── validators.py        # Pure-function input validation
│   └── logging_config.py   # Logging setup (console + rotating file)
├── logs/
│   └── trading_bot.log      # Auto-created; rotates at 5 MB
├── cli.py                   # CLI entry point (argparse)
├── requirements.txt
└── README.md
```

---

## ✅ Prerequisites

- Python **3.10+** (uses `tuple[str, str]` type hints)
- A [Binance Futures Testnet](https://testnet.binancefuture.com) account with API credentials

> **Testnet account is separate from your real Binance account.**  
> Register at https://testnet.binancefuture.com — it gives you free paper funds.

---

## 🛠️ Setup

### Step 1 — Clone / unzip the project

```bash
git clone https://github.com/your-username/trading-bot.git
cd trading-bot
```

### Step 2 — Create a virtual environment

```bash
python -m venv .venv

# Activate on macOS / Linux
source .venv/bin/activate

# Activate on Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4 — Get Binance Futures Testnet API credentials

1. Go to https://testnet.binancefuture.com
2. Log in (create an account if needed — no real money required)
3. Click your profile icon → **API Management**
4. Create a new API key pair
5. Copy the **API Key** and **Secret Key** — you only see the secret once

### Step 5 — Set your credentials

**Option A — `.env` file (recommended for local development)**

Create a file named `.env` in the project root:

```dotenv
BINANCE_API_KEY=paste_your_api_key_here
BINANCE_API_SECRET=paste_your_secret_key_here
```

> ⚠️ Never commit `.env` to Git. Add it to `.gitignore`.

**Option B — Export as environment variables**

```bash
export BINANCE_API_KEY="paste_your_api_key_here"
export BINANCE_API_SECRET="paste_your_secret_key_here"
```

On Windows (PowerShell):

```powershell
$env:BINANCE_API_KEY = "paste_your_api_key_here"
$env:BINANCE_API_SECRET = "paste_your_secret_key_here"
```

---

## 🚀 Running the Bot

All commands are run from the **project root** directory (where `cli.py` lives).

### Verify connectivity first (optional)

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 --check-connection
```

### Place a MARKET order

```bash
# Buy 0.01 BTC at current market price
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

# Sell 0.1 ETH at current market price
python cli.py --symbol ETHUSDT --side SELL --type MARKET --quantity 0.1
```

### Place a LIMIT order

```bash
# Sell 0.01 BTC when price reaches $65,000
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 65000

# Buy 0.1 ETH if price drops to $3,000
python cli.py --symbol ETHUSDT --side BUY --type LIMIT --quantity 0.1 --price 3000
```

### Place a STOP_MARKET order (bonus)

A Stop-Market order triggers a market order once the mark price crosses your stop price.

```bash
# Trigger a BUY market order if BTCUSDT rises above $60,000 (breakout entry)
python cli.py --symbol BTCUSDT --side BUY --type STOP_MARKET --quantity 0.01 --price 60000

# Trigger a SELL market order if BTCUSDT drops below $55,000 (stop-loss)
python cli.py --symbol BTCUSDT --side SELL --type STOP_MARKET --quantity 0.01 --price 55000
```

### Verbose output (show DEBUG logs in terminal)

```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 --log-level DEBUG
```

---

## 📖 CLI Reference

```
usage: trading_bot [-h] --symbol SYMBOL --side {BUY,SELL}
                   --type {MARKET,LIMIT,STOP_MARKET}
                   --quantity QUANTITY [--price PRICE]
                   [--log-level {DEBUG,INFO,WARNING,ERROR}]
                   [--check-connection]

Order parameters:
  --symbol        Trading pair, e.g. BTCUSDT or ETHUSDT
  --side          BUY or SELL
  --type          MARKET, LIMIT, or STOP_MARKET
  --quantity      Amount of the base asset (e.g. 0.01 for 0.01 BTC)
  --price         Limit price (LIMIT) or stop trigger price (STOP_MARKET)

Miscellaneous:
  --log-level     Console verbosity: DEBUG / INFO / WARNING / ERROR (default: INFO)
  --check-connection  Ping exchange before placing order
```

---

## 🖥️ Example Output

### MARKET order (successful)

```
────────────────────────────────────────────────────────
  📤  ORDER REQUEST SUMMARY
────────────────────────────────────────────────────────
  Symbol:                BTCUSDT
  Side:                  BUY
  Order Type:            MARKET
  Quantity:              0.01
────────────────────────────────────────────────────────

────────────────────────────────────────────────────────
  ✅  ORDER PLACED SUCCESSFULLY
────────────────────────────────────────────────────────
  Order ID:              4751823956
  Client OID:            testnet_abc123
  Symbol:                BTCUSDT
  Side:                  BUY
  Type:                  MARKET
  Status:                FILLED
  Quantity:              0.01
  Executed Qty:          0.01
  Avg / Set Price:       57823.40
────────────────────────────────────────────────────────
```

### Validation error (missing price for LIMIT)

```
❌  Validation Error: Price is required for LIMIT orders. Supply it with --price.
```

### API error (e.g. bad credentials)

```
❌  Binance API Error (code -2014): API-key format invalid.
    Common causes:
      • Invalid API key / secret
      • Insufficient testnet balance
      • Quantity below minimum notional
      • Price too far from mark price (LIMIT)
```

---

## 📝 Logging

Log files are automatically created in `logs/trading_bot.log`.

| Destination | Level | Format |
|---|---|---|
| Console (terminal) | INFO (default) | `LEVEL    \| message` |
| File (`logs/trading_bot.log`) | DEBUG (always) | `timestamp \| LEVEL \| module \| message` |

File logs rotate at **5 MB** and keep **3 backups** (`trading_bot.log.1`, `.2`, `.3`).

### Sample log lines

```
2025-07-14 09:15:01 | INFO     | bot.orders | Placing BUY MARKET order | symbol=BTCUSDT qty=0.01 price=MARKET
2025-07-14 09:15:01 | DEBUG    | bot.client | POST /fapi/v1/order | params={'symbol': 'BTCUSDT', 'side': 'BUY', 'type': 'MARKET', ...}
2025-07-14 09:15:01 | DEBUG    | bot.client | Response HTTP 200 | body={...full JSON response...}
2025-07-14 09:15:01 | INFO     | bot.orders | Order placed | orderId=4751823956 status=FILLED executedQty=0.01
```

> The HMAC signature is **never logged** to avoid leaking credentials.

---

## 🛡️ Error Handling

The bot handles three categories of errors:

| Category | Exception | Example |
|---|---|---|
| Input validation | `ValueError` | Missing price for LIMIT, invalid symbol |
| API errors | `BinanceAPIError` | Wrong credentials, below min notional |
| Network issues | `ConnectionError` | Timeout, no internet, DNS failure |

Each error prints a descriptive message to stderr and exits with code `1`, while logging the full detail to the log file.

---

## 🧠 Assumptions & Design Decisions

| Decision | Reason |
|---|---|
| **Direct REST calls** (no `python-binance`) | Fewer dependencies, full visibility into signing and error handling |
| **`Decimal` for all prices/quantities** | Avoids floating-point precision issues common in financial math |
| **`timeInForce = GTC`** for LIMIT orders | "Good Till Cancelled" is the standard default for most trading scenarios |
| **No order book / balance check** | Out of scope; testnet gives paper funds, exchange validates server-side |
| **Retries on 429 / 5xx** | Handles transient testnet instability; respects Binance rate-limit guidance |
| **Signature never logged** | Security best practice — secrets must not appear in log files |
| **Single log file with rotation** | Simple ops story; file stays bounded in size without manual cleanup |
| **`python-dotenv` optional** | Keeps the mandatory dependency list minimal; `.env` is a convenience |

---

## 🔒 Security Notes

- Never commit `.env` or any file containing your API key/secret to Git
- Add `.env` to `.gitignore`
- Testnet credentials are **separate** from mainnet — they have no real value
- The bot sends only the minimum required data and never logs secrets

---

## 📦 Dependencies

```
requests>=2.31.0       # HTTP client
urllib3>=2.0.0         # Retry adapter (used by requests)
python-dotenv>=1.0.0   # Optional: load .env file
```

Install with:

```bash
pip install -r requirements.txt
```

---

*Built for the Binance Futures Testnet (USDT-M). Not for use with real funds without thorough testing and review.*
