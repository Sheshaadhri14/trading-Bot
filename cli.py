
import argparse
import os
import sys



sys.path.insert(0, os.path.dirname(__file__))

from bot.logging_config import setup_logging, get_logger, LOG_FILE
from bot.validators import validate_all
from bot.client import BinanceFuturesClient, BinanceAPIError
from bot.orders import place_order


try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass   


def build_parser() -> argparse.ArgumentParser:
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
    
    api_key    = os.getenv("BINANCE_API_KEY",    "")
    api_secret = os.getenv("BINANCE_API_SECRET", "")

    if not api_key or not api_secret:
        print(
            "\n  Missing credentials.\n"
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

    setup_logging(args.log_level)
    logger = get_logger(__name__)
    logger.info("Trading bot started | log file: %s", LOG_FILE)

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
        print(f"\n  Validation Error: {exc}\n", file=sys.stderr)
        sys.exit(1)

    logger.debug("Validated inputs: %s", validated)

    api_key, api_secret = get_credentials()

    try:
        client = BinanceFuturesClient(api_key=api_key, api_secret=api_secret)
    except ValueError as exc:
        logger.error("Client initialisation failed: %s", exc)
        print(f"\n❌  Configuration Error: {exc}\n", file=sys.stderr)
        sys.exit(1)

    if args.check_connection:
        try:
            server_time = client.get_server_time()
            logger.info("Connectivity OK | server time ms=%s", server_time)
            print(f"  🌐  Connected to Binance Testnet (server time: {server_time})")
        except ConnectionError as exc:
            logger.error("Connectivity check failed: %s", exc)
            print(f"\n  Cannot reach Binance Testnet: {exc}\n", file=sys.stderr)
            sys.exit(1)

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
        print(f"\n  Order Error: {exc}\n", file=sys.stderr)
        sys.exit(1)

    except BinanceAPIError as exc:
        logger.error("Binance API error %s: %s", exc.code, exc.message)
        print(
            f"\n  Binance API Error (code {exc.code}): {exc.message}\n"
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
        print(f"\n  Network Error: {exc}\n", file=sys.stderr)
        sys.exit(1)

    except Exception as exc:
        logger.exception("Unexpected error: %s", exc)
        print(f"\n  Unexpected Error: {exc}\n", file=sys.stderr)
        sys.exit(1)

    logger.info("Trading bot finished successfully.")


if __name__ == "__main__":
    main()
