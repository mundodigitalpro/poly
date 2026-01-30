"""
Gamma API Client for Polymarket.

Provides access to market volume, liquidity, and trending data
that is not available in the CLOB API.

API Base: https://gamma-api.polymarket.com
"""

import requests
from typing import Any, Dict, List, Optional


class GammaClient:
    """Client for Polymarket Gamma API (market data and volume)."""

    BASE_URL = "https://gamma-api.polymarket.com"
    TIMEOUT = 10

    def __init__(self, logger=None):
        """
        Initialize the Gamma client.

        Args:
            logger: Optional logger instance for debug output.
        """
        self.logger = logger
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "User-Agent": "PolyBot/0.12.0",
        })

    def _log(self, level: str, msg: str):
        """Log a message if logger is available."""
        if self.logger:
            log_fn = getattr(self.logger, level, None)
            if log_fn:
                log_fn(msg)

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Optional[Any]:
        """
        Make a GET request to the Gamma API.

        Args:
            endpoint: API endpoint (e.g., "/markets")
            params: Optional query parameters

        Returns:
            JSON response or None on error.
        """
        url = f"{self.BASE_URL}{endpoint}"
        try:
            self._log("debug", f"Gamma API GET {endpoint}")
            resp = self.session.get(url, params=params, timeout=self.TIMEOUT)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.Timeout:
            self._log("warn", f"Gamma API timeout: {endpoint}")
            return None
        except requests.exceptions.HTTPError as e:
            self._log("warn", f"Gamma API HTTP error: {e}")
            return None
        except requests.exceptions.RequestException as e:
            self._log("warn", f"Gamma API request failed: {e}")
            return None
        except ValueError as e:
            self._log("warn", f"Gamma API invalid JSON: {e}")
            return None

    def get_markets(
        self,
        active: bool = True,
        closed: bool = False,
        limit: int = 100,
        order: str = "volume24hr",
        ascending: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Fetch markets with volume and liquidity data.

        Args:
            active: Only return active markets.
            closed: Include closed markets.
            limit: Maximum number of markets to return.
            order: Field to order by (volume24hr, volumeNum, liquidityNum).
            ascending: Sort ascending if True, descending if False.

        Returns:
            List of market dictionaries with volume data.
        """
        params = {
            "limit": limit,
            "order": order,
            "ascending": str(ascending).lower(),
        }
        if active:
            params["active"] = "true"
        if not closed:
            params["closed"] = "false"

        data = self._get("/markets", params)

        if not data:
            return []

        # Handle both list and paginated response formats
        if isinstance(data, list):
            markets = data
        elif isinstance(data, dict):
            markets = data.get("data", data.get("markets", []))
        else:
            return []

        return self._normalize_markets(markets)

    def get_market_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a single market by its slug.

        Args:
            slug: Market slug (URL-friendly name).

        Returns:
            Market dictionary or None if not found.
        """
        data = self._get(f"/markets/{slug}")
        if not data:
            return None

        markets = self._normalize_markets([data])
        return markets[0] if markets else None

    def get_market_by_condition(self, condition_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch a single market by its condition ID.

        Args:
            condition_id: The market's condition ID from CLOB API.

        Returns:
            Market dictionary or None if not found.
        """
        # Gamma API uses condition_id as a query param
        params = {"condition_id": condition_id}
        data = self._get("/markets", params)

        if not data:
            return None

        if isinstance(data, list) and len(data) > 0:
            markets = self._normalize_markets(data)
            return markets[0] if markets else None

        return None

    def _normalize_markets(self, markets: List[Dict]) -> List[Dict[str, Any]]:
        """
        Normalize market data to a consistent format.

        Extracts key fields and ensures consistent naming.
        """
        normalized = []

        for m in markets:
            if not isinstance(m, dict):
                continue

            # Extract CLOB token IDs
            clob_token_ids = []
            if "clobTokenIds" in m:
                raw_ids = m["clobTokenIds"]
                if isinstance(raw_ids, str):
                    # Sometimes it's a JSON string
                    try:
                        import json
                        clob_token_ids = json.loads(raw_ids)
                    except (json.JSONDecodeError, TypeError):
                        clob_token_ids = [raw_ids] if raw_ids else []
                elif isinstance(raw_ids, list):
                    clob_token_ids = raw_ids

            normalized.append({
                # Identifiers
                "condition_id": m.get("conditionId") or m.get("condition_id"),
                "slug": m.get("slug"),
                "question": m.get("question") or m.get("title"),
                "clob_token_ids": clob_token_ids,

                # Volume data (key differentiator from CLOB API)
                "volume_total": self._safe_float(m.get("volumeNum")),
                "volume_24h": self._safe_float(m.get("volume24hr")),
                "volume_1w": self._safe_float(m.get("volume1wk")),
                "volume_1m": self._safe_float(m.get("volume1mo")),

                # Liquidity
                "liquidity": self._safe_float(m.get("liquidityNum")),

                # Prices
                "best_bid": self._safe_float(m.get("bestBid")),
                "best_ask": self._safe_float(m.get("bestAsk")),
                "spread": self._safe_float(m.get("spread")),
                "last_price": self._safe_float(m.get("lastTradePrice")),

                # Price changes
                "price_change_24h": self._safe_float(m.get("oneDayPriceChange")),
                "price_change_1w": self._safe_float(m.get("oneWeekPriceChange")),

                # Status
                "active": m.get("active", True),
                "closed": m.get("closed", False),

                # Timestamps
                "end_date": m.get("endDate") or m.get("end_date_iso"),

                # Raw data for debugging
                "_raw": m,
            })

        return normalized

    def _safe_float(self, value, default: float = 0.0) -> float:
        """Safely convert a value to float."""
        if value is None:
            return default
        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def get_top_volume_markets(
        self,
        min_volume_24h: float = 500.0,
        min_liquidity: float = 1000.0,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get top markets by 24h volume with minimum thresholds.

        Convenience method for market discovery.

        Args:
            min_volume_24h: Minimum 24h volume in USD.
            min_liquidity: Minimum liquidity in USD.
            limit: Maximum markets to fetch before filtering.

        Returns:
            Filtered list of high-volume markets.
        """
        markets = self.get_markets(
            active=True,
            closed=False,
            limit=limit,
            order="volume24hr",
            ascending=False,
        )

        return [
            m for m in markets
            if m["volume_24h"] >= min_volume_24h
            and m["liquidity"] >= min_liquidity
            and m["clob_token_ids"]  # Must have CLOB token IDs for trading
        ]
