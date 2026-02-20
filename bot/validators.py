"""
validators.py
-------------
Pure-function input validation for order parameters.

All validators raise ValueError with a descriptive message on failure,
so the CLI layer can catch them and print a clean error instead of a
raw traceback.
"""

from decimal import Decimal, InvalidOperation
from typing import Optional

# ── Allowed values ───────────────────────────────────────────────────────────
VALID_SIDES      = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_MARKET"}   # STOP_MARKET = bonus
SYMBOL_MIN_LEN   = 3
SYMBOL_MAX_LEN   = 20


def validate_symbol(symbol: str) -> str:
    """
    Return the uppercased symbol if valid, else raise ValueError.

    Rules:
      - Non-empty string
      - 3–20 alphabetic characters (e.g. BTCUSDT, ETHUSDT)
    """
    if not symbol or not symbol.strip():
        raise ValueError("Symbol must not be empty.")
    sym = symbol.strip().upper()
    if not sym.isalpha():
        raise ValueError(f"Symbol '{sym}' must contain only letters (e.g. BTCUSDT).")
    if not (SYMBOL_MIN_LEN <= len(sym) <= SYMBOL_MAX_LEN):
        raise ValueError(
            f"Symbol '{sym}' length must be between {SYMBOL_MIN_LEN} and {SYMBOL_MAX_LEN}."
        )
    return sym


def validate_side(side: str) -> str:
    """Return uppercased side (BUY/SELL) or raise ValueError."""
    s = side.strip().upper()
    if s not in VALID_SIDES:
        raise ValueError(f"Side '{side}' is invalid. Choose from: {', '.join(sorted(VALID_SIDES))}.")
    return s


def validate_order_type(order_type: str) -> str:
    """Return uppercased order type or raise ValueError."""
    t = order_type.strip().upper()
    if t not in VALID_ORDER_TYPES:
        raise ValueError(
            f"Order type '{order_type}' is invalid. "
            f"Choose from: {', '.join(sorted(VALID_ORDER_TYPES))}."
        )
    return t


def validate_quantity(quantity: str) -> Decimal:
    """
    Parse and validate quantity.

    Rules:
      - Must be a valid positive number
      - Cannot be zero
    """
    try:
        qty = Decimal(str(quantity))
    except InvalidOperation:
        raise ValueError(f"Quantity '{quantity}' is not a valid number.")
    if qty <= 0:
        raise ValueError(f"Quantity must be greater than zero, got {qty}.")
    return qty


def validate_price(price: Optional[str], order_type: str) -> Optional[Decimal]:
    """
    Parse and validate price.

    Rules:
      - Required and positive for LIMIT orders
      - Ignored (None) for MARKET orders
      - Required and positive for STOP_MARKET orders
    """
    if order_type == "MARKET":
        # Price is irrelevant; warn if mistakenly supplied but don't fail
        return None

    if price is None or str(price).strip() == "":
        raise ValueError(
            f"Price is required for {order_type} orders. Supply it with --price."
        )
    try:
        p = Decimal(str(price))
    except InvalidOperation:
        raise ValueError(f"Price '{price}' is not a valid number.")
    if p <= 0:
        raise ValueError(f"Price must be greater than zero, got {p}.")
    return p


def validate_all(
    symbol: str,
    side: str,
    order_type: str,
    quantity: str,
    price: Optional[str] = None,
) -> dict:
    """
    Convenience function: validate all fields and return a clean dict.

    Returns
    -------
    dict with keys: symbol, side, order_type, quantity, price (Decimal or None)
    """
    sym  = validate_symbol(symbol)
    s    = validate_side(side)
    ot   = validate_order_type(order_type)
    qty  = validate_quantity(quantity)
    p    = validate_price(price, ot)

    return {"symbol": sym, "side": s, "order_type": ot, "quantity": qty, "price": p}
