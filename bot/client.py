"""
client.py
---------
Low-level Binance Futures Testnet REST client.

Responsibilities:
  - Builds and signs every request with HMAC-SHA256
  - Handles HTTP-level errors (timeouts, 4xx, 5xx)
  - Logs every outgoing request and incoming response at DEBUG level
  - Raises BinanceAPIError for any API-level failure so callers never
    have to inspect raw HTTP responses

Only one public method is needed for order placement:
    client.send_order(params) -> dict

But a small helper (get_server_time) is included to verify connectivity.
"""

import hashlib
import hmac
import time
import urllib.parse
from decimal import Decimal
from typing import Any, Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from bot.logging_config import get_logger

logger = get_logger(__name__)

# ── Testnet base URL (USDT-M Futures) ────────────────────────────────────────
BASE_URL = "https://testnet.binancefuture.com"

# ── Retry strategy (network hiccups) ─────────────────────────────────────────
_RETRY = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "POST"],
)


class BinanceAPIError(Exception):
    """
    Raised when the Binance API returns a non-200 status or an error payload.

    Attributes
    ----------
    code    : Binance error code (int), e.g. -1102
    message : Human-readable error description from Binance
    """

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"Binance API Error {code}: {message}")


class BinanceFuturesClient:
    """
    Thin wrapper around the Binance USDT-M Futures REST API.

    Parameters
    ----------
    api_key    : Your Binance Futures Testnet API key
    api_secret : Your Binance Futures Testnet secret key
    timeout    : HTTP request timeout in seconds (default 10)
    """

    def __init__(self, api_key: str, api_secret: str, timeout: int = 10) -> None:
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret must not be empty.")

        self._api_key    = api_key
        self._api_secret = api_secret.encode()   # bytes needed for HMAC
        self._timeout    = timeout
        self._session    = self._build_session()

        logger.debug("BinanceFuturesClient initialised (testnet=%s)", BASE_URL)

    # ── Private helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _build_session() -> requests.Session:
        """Return a requests.Session with retry logic pre-configured."""
        session = requests.Session()
        adapter = HTTPAdapter(max_retries=_RETRY)
        session.mount("https://", adapter)
        return session

    def _sign(self, params: dict) -> dict:
        """
        Add a HMAC-SHA256 signature and current timestamp to *params*.

        Binance requires:
          - recvWindow  : how long (ms) the request is valid
          - timestamp   : current epoch time in ms
          - signature   : HMAC-SHA256 of the query string
        """
        params["recvWindow"] = 5000
        params["timestamp"]  = int(time.time() * 1000)
        query_string         = urllib.parse.urlencode(params)
        signature            = hmac.new(
            self._api_secret, query_string.encode(), hashlib.sha256
        ).hexdigest()
        params["signature"]  = signature
        return params

    def _headers(self) -> dict:
        """Return HTTP headers including the API key."""
        return {"X-MBX-APIKEY": self._api_key}

    def _post(self, endpoint: str, params: dict) -> dict:
        """
        Sign and POST to *endpoint*.

        Logs the sanitised request (no secret/signature) and full response.
        Raises BinanceAPIError on API errors, ConnectionError on network issues.
        """
        signed_params = self._sign(params.copy())
        url           = BASE_URL + endpoint

        # Log what we're sending (hide signature to avoid leaking it)
        safe_log = {k: v for k, v in signed_params.items() if k != "signature"}
        logger.debug("POST %s | params=%s", endpoint, safe_log)

        try:
            response = self._session.post(
                url,
                params=signed_params,
                headers=self._headers(),
                timeout=self._timeout,
            )
        except requests.exceptions.Timeout:
            logger.error("Request to %s timed out after %ss", endpoint, self._timeout)
            raise ConnectionError(f"Request timed out after {self._timeout}s.")
        except requests.exceptions.ConnectionError as exc:
            logger.error("Network error reaching %s: %s", endpoint, exc)
            raise ConnectionError(f"Network error: {exc}") from exc

        # ── Parse response ────────────────────────────────────────────────────
        logger.debug("Response HTTP %s | body=%s", response.status_code, response.text)

        try:
            data = response.json()
        except ValueError:
            logger.error("Non-JSON response (HTTP %s): %s", response.status_code, response.text)
            raise BinanceAPIError(-1, f"Non-JSON response: {response.text}")

        if not response.ok or "code" in data and data["code"] != 200:
            # Binance error responses look like: {"code": -1102, "msg": "..."}
            code = data.get("code", response.status_code)
            msg  = data.get("msg", response.text)
            logger.error("API error %s: %s", code, msg)
            raise BinanceAPIError(code, msg)

        return data

    def _get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        """Unsigned GET (used only for server time check)."""
        url = BASE_URL + endpoint
        try:
            resp = self._session.get(url, params=params or {}, timeout=self._timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as exc:
            raise ConnectionError(f"GET {endpoint} failed: {exc}") from exc

    # ── Public API ────────────────────────────────────────────────────────────

    def get_server_time(self) -> int:
        """
        Return the Binance server time in milliseconds.
        Useful to verify connectivity before placing orders.
        """
        data = self._get("/fapi/v1/time")
        return data["serverTime"]

    def send_order(self, params: dict) -> dict:
        """
        Place an order on Binance Futures Testnet.

        Parameters
        ----------
        params : dict
            Must contain at minimum: symbol, side, type, quantity.
            For LIMIT orders also: price, timeInForce.

        Returns
        -------
        dict : Raw API response with orderId, status, etc.
        """
        return self._post("/fapi/v1/order", params)
