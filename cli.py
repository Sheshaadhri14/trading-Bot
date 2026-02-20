#!/usr/bin/env python3
"""
cli.py
------
Command-line entry point for the Binance Futures Testnet trading bot.

Usage examples
--------------
# Market BUY 0.01 BTC
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

# Limit SELL 0.01 ETH at $2,000
python cli.py --symbol ETHUSDT --side SELL --type LIMIT --quantity 0.01 --price 2000

# Stop-Market BUY 0.01 BTC (triggers when price hits 30,000)  [bonus]
python cli.py --symbol BTCUSDT --side BUY --type STOP_MARKET --quantity 0.01 --price 30000

# Verbose console logging (show DEBUG messages too)
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 --log-level DEBUG

Credentials are read from environment variables:
    BINANCE_API_KEY
    BINANCE_API_SECRET

Or you may hard-code them in a .env file (see README.md).
"""

import argparse
import os
import sys

# ── Allow running from the project root without installing the package ────────
sys.path.insert(0, os.path.dirname(__file__))

from bot.logging_config import setup_logging, get_logger, LOG_FILE
from bot.validators import validate_all
from bot.client import BinanceFuturesClient, BinanceAPIError
from bot.orders import place_order


# ── Try to load a .env file if python-dotenv is installed ────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass   # dotenv is optional; credentials can come from real env vars


def build_parser() -> argparse.ArgumentParser:
    """Define and return the CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="trading_bot",
        description=(
            "Binance Futures Testnet – Order Placement Bot\n"
            "─────────────────────────────────────────────\n"
            "Supports MARKET, LIMIT, and STOP_MARKET orders.\n"
            "Credentials are read from BINANCE_API_KEY / BINANCE_API_SECRET env vars."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python cli.py --symbol BTCUSDT --side BUY  --type MARKET --quantity 0.01\n"
            "  python cli.py --symbol ETHUSDT --side SELL --type LIMIT  --quantity 0.01 --price 2000\n"
            "  python cli.py --symbol BTCUSDT --side BUY  --type STOP_MARKET --quantity 0.01 --price 30000\n"
        ),
    )

    # ── Order parameters ──────────────────────────────────────────────────────
    order_group = parser.add_argument_group("Order parameters")
    order_group.add_argument(
        "--symbol", required=True,
        help="Trading pair, e.g. BTCUSDT or ETHUSDT",
    )
    order_group.add_argument(
        "--side", required=True, choices=["BUY", "SELL"],
        help="Direction of the trade",
    )
    order_group.add_argument(
        "--type", required=True,
        choices=["MARKET", "LIMIT", "STOP_MARKET"],
        dest="order_type",
        help="Order type (STOP_MARKET is a bonus type)",
    )
    order_group.add_argument(
        "--quantity", required=True,
        help="Amount of the base asset to trade (e.g. 0.01 for 0.01 BTC)",
    )
    order_group.add_argument(
        "--price",
        help="Limit price (LIMIT) or stop trigger price (STOP_MARKET). Not used for MARKET.",
    )

    # ── Misc ──────────────────────────────────────────────────────────────────
    misc_group = parser.add_argument_group("Miscellaneous")
    misc_group.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Console log verbosity (file always logs at DEBUG). Default: INFO",
    )
    misc_group.add_argument(
        "--check-connection",
        action="store_true",
        help="Ping the exchange to verify connectivity before placing the order",
    )

    return parser


def get_credentials() -> tuple[str, str]:
    """
    Read API credentials from environment variables.

    Returns
    -------
    (api_key, api_secret) tuple

    Raises
    ------
    SystemExit if either variable is missing.
    """
    api_key    = os.getenv("BINANCE_API_KEY",    "")
    api_secret = os.getenv("BINANCE_API_SECRET", "")

    if not api_key or not api_secret:
        print(
            "\n❌  Missing credentials.\n"
            "    Set the following environment variables before running:\n\n"
            "        export BINANCE_API_KEY='your_key'\n"
            "        export BINANCE_API_SECRET='your_secret'\n\n"
            "    Or create a .env file in the project root (see README.md).\n",
            file=sys.stderr,
        )
        sys.exit(1)

    return api_key, api_secret


def main() -> None:
    parser = build_parser()
    args   = parser.parse_args()

    # ── 1. Configure logging ──────────────────────────────────────────────────
    setup_logging(args.log_level)
    logger = get_logger(__name__)
    logger.info("Trading bot started | log file: %s", LOG_FILE)

    # ── 2. Validate all user inputs up-front ─────────────────────────────────
    try:
        validated = validate_all(
            symbol     = args.symbol,
            side       = args.side,
            order_type = args.order_type,
            quantity   = args.quantity,
            price      = args.price,
        )
    except ValueError as exc:
        logger.error("Input validation failed: %s", exc)
        print(f"\n❌  Validation Error: {exc}\n", file=sys.stderr)
        sys.exit(1)

    logger.debug("Validated inputs: %s", validated)

    # ── 3. Build the API client ───────────────────────────────────────────────
    api_key, api_secret = get_credentials()

    try:
        client = BinanceFuturesClient(api_key=api_key, api_secret=api_secret)
    except ValueError as exc:
        logger.error("Client initialisation failed: %s", exc)
        print(f"\n❌  Configuration Error: {exc}\n", file=sys.stderr)
        sys.exit(1)

    # ── 4. Optional connectivity check ───────────────────────────────────────
    if args.check_connection:
        try:
            server_time = client.get_server_time()
            logger.info("Connectivity OK | server time ms=%s", server_time)
            print(f"  🌐  Connected to Binance Testnet (server time: {server_time})")
        except ConnectionError as exc:
            logger.error("Connectivity check failed: %s", exc)
            print(f"\n❌  Cannot reach Binance Testnet: {exc}\n", file=sys.stderr)
            sys.exit(1)

    # ── 5. Place the order ────────────────────────────────────────────────────
    try:
        place_order(
            client     = client,
            symbol     = validated["symbol"],
            side       = validated["side"],
            order_type = validated["order_type"],
            quantity   = validated["quantity"],
            price      = validated["price"],
        )
    except ValueError as exc:
        # Validation-level error (e.g. price missing for LIMIT)
        logger.error("Order parameter error: %s", exc)
        print(f"\n❌  Order Error: {exc}\n", file=sys.stderr)
        sys.exit(1)

    except BinanceAPIError as exc:
        logger.error("Binance API error %s: %s", exc.code, exc.message)
        print(
            f"\n❌  Binance API Error (code {exc.code}): {exc.message}\n"
            "    Common causes:\n"
            "      • Invalid API key / secret\n"
            "      • Insufficient testnet balance\n"
            "      • Quantity below minimum notional\n"
            "      • Price too far from mark price (LIMIT)\n",
            file=sys.stderr,
        )
        sys.exit(1)

    except ConnectionError as exc:
        logger.error("Network error: %s", exc)
        print(f"\n❌  Network Error: {exc}\n", file=sys.stderr)
        sys.exit(1)

    except Exception as exc:
        logger.exception("Unexpected error: %s", exc)
        print(f"\n❌  Unexpected Error: {exc}\n", file=sys.stderr)
        sys.exit(1)

    logger.info("Trading bot finished successfully.")


if __name__ == "__main__":
    main()
