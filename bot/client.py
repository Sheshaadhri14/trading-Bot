
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

BASE_URL = "https://testnet.binancefuture.com"

_RETRY = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET", "POST"],
)


class BinanceAPIError(Exception):
    
    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"Binance API Error {code}: {message}")


class BinanceFuturesClient:
    

    def __init__(self, api_key: str, api_secret: str, timeout: int = 10) -> None:
        if not api_key or not api_secret:
            raise ValueError("api_key and api_secret must not be empty.")

        self._api_key    = api_key
        self._api_secret = api_secret.encode()   # bytes needed for HMAC
        self._timeout    = timeout
        self._session    = self._build_session()

        logger.debug("BinanceFuturesClient initialised (testnet=%s)", BASE_URL)


    @staticmethod
    def _build_session() -> requests.Session:
        session = requests.Session()
        adapter = HTTPAdapter(max_retries=_RETRY)
        session.mount("https://", adapter)
        return session

    def _sign(self, params: dict) -> dict:
        
        server_time = self._get("/fapi/v1/time")["serverTime"]
        params["timestamp"] = server_time
        params["recvWindow"] = 10000

        query_string         = urllib.parse.urlencode(params)
        signature            = hmac.new(
            self._api_secret, query_string.encode(), hashlib.sha256
        ).hexdigest()
        params["signature"]  = signature
        return params

    def _headers(self) -> dict:
        return {"X-MBX-APIKEY": self._api_key}

    def _post(self, endpoint: str, params: dict) -> dict:
        
        signed_params = self._sign(params.copy())
        url           = BASE_URL + endpoint

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

        logger.debug("Response HTTP %s | body=%s", response.status_code, response.text)

        try:
            data = response.json()
        except ValueError:
            logger.error("Non-JSON response (HTTP %s): %s", response.status_code, response.text)
            raise BinanceAPIError(-1, f"Non-JSON response: {response.text}")

        if not response.ok or "code" in data and data["code"] != 200:
            code = data.get("code", response.status_code)
            msg  = data.get("msg", response.text)
            logger.error("API error %s: %s", code, msg)
            raise BinanceAPIError(code, msg)

        return data

    def _get(self, endpoint: str, params: Optional[dict] = None) -> dict:
        url = BASE_URL + endpoint
        try:
            resp = self._session.get(url, params=params or {}, timeout=self._timeout)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as exc:
            raise ConnectionError(f"GET {endpoint} failed: {exc}") from exc


    def get_server_time(self) -> int:
        
        data = self._get("/fapi/v1/time")
        return data["serverTime"]

    def send_order(self, params: dict) -> dict:
        
        return self._post("/fapi/v1/order", params)
