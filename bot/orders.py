

from decimal import Decimal
from typing import Optional

from bot.client import BinanceFuturesClient, BinanceAPIError
from bot.logging_config import get_logger

logger = get_logger(__name__)


_DIVIDER = "─" * 52


def _fmt(label: str, value: str) -> str:
    return f"  {label:<22} {value}"


def print_request_summary(params: dict) -> None:
    print(f"\n{'─'*52}")
    print("    ORDER REQUEST SUMMARY")
    print(_DIVIDER)
    print(_fmt("Symbol:",     params.get("symbol", "—")))
    print(_fmt("Side:",       params.get("side",   "—")))
    print(_fmt("Order Type:", params.get("type",   "—")))
    print(_fmt("Quantity:",   str(params.get("quantity", "—"))))
    if params.get("type") in ("LIMIT", "STOP_MARKET"):
        print(_fmt("Price / Stop:", str(params.get("price") or params.get("stopPrice", "—"))))
    if params.get("timeInForce"):
        print(_fmt("Time In Force:", params["timeInForce"]))
    print(_DIVIDER)


def print_response_summary(response: dict) -> None:
    print(f"\n{'─'*52}")
    print("   ORDER PLACED SUCCESSFULLY")
    print(_DIVIDER)
    print(_fmt("Order ID:",     str(response.get("orderId",     "—"))))
    print(_fmt("Client OID:",   str(response.get("clientOrderId", "—"))))
    print(_fmt("Symbol:",       response.get("symbol",          "—")))
    print(_fmt("Side:",         response.get("side",            "—")))
    print(_fmt("Type:",         response.get("type",            "—")))
    print(_fmt("Status:",       response.get("status",          "—")))
    print(_fmt("Quantity:",     str(response.get("origQty",     "—"))))
    print(_fmt("Executed Qty:", str(response.get("executedQty", "—"))))

    avg_price = response.get("avgPrice") or response.get("price")
    if avg_price and float(avg_price) > 0:
        print(_fmt("Avg / Set Price:", avg_price))

    print(_DIVIDER)
    print()



def place_order(
    client: BinanceFuturesClient,
    symbol: str,
    side: str,
    order_type: str,
    quantity: Decimal,
    price: Optional[Decimal] = None,
) -> dict:
    
    payload: dict = {
        "symbol":   symbol,
        "side":     side,
        "type":     order_type,
        "quantity": str(quantity),
    }

    if order_type == "LIMIT":
        if price is None:
            raise ValueError("LIMIT orders require a price.")
        payload["price"]       = str(price)
        payload["timeInForce"] = "GTC"   

    elif order_type == "STOP_MARKET":
        if price is None:
            raise ValueError("STOP_MARKET orders require a stop price (--price).")
        payload["stopPrice"] = str(price)

    print_request_summary(payload)
    logger.info(
        "Placing %s %s order | symbol=%s qty=%s price=%s",
        side, order_type, symbol, quantity, price or "MARKET",
    )

    response = client.send_order(payload)

    logger.info(
        "Order placed | orderId=%s status=%s executedQty=%s",
        response.get("orderId"),
        response.get("status"),
        response.get("executedQty"),
    )

    print_response_summary(response)
    return response
