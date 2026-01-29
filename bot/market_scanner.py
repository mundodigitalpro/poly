"""
Market scanner for the Polymarket trading bot.

Fetches markets, applies filters, and ranks candidates using the strategy score.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


class MarketScanner:
    """Fetch, filter, and rank markets for potential trades."""

    def __init__(self, client, config, logger, position_manager, strategy):
        """
        Initialize scanner dependencies.

        Args:
            client: Initialized ClobClient
            config: BotConfig instance
            logger: BotLogger instance
            position_manager: PositionManager instance
            strategy: TradingStrategy instance
        """
        self.client = client
        self.config = config
        self.logger = logger
        self.position_manager = position_manager
        self.strategy = strategy

        self.filters = config.get("market_filters", {})
        api_cfg = config.get("api", {})
        self.max_calls_per_minute = api_cfg.get("max_calls_per_minute", 20)
        self.min_call_interval = 60.0 / max(1, self.max_calls_per_minute)
        self._last_call_ts = 0.0

    def scan_markets(self, max_markets: int = 20) -> List[Dict[str, Any]]:
        """
        Scan markets and return ranked candidates.

        Args:
            max_markets: Maximum number of markets to analyze

        Returns:
            List of candidate dicts sorted by score desc
        """
        markets = self._fetch_markets(max_markets)
        candidates: List[Dict[str, Any]] = []

        for i, market in enumerate(markets):
            if i % 5 == 0:
                self.logger.info(f"Scanning market {i+1}/{len(markets)}...")
            try:
                candidate = self._analyze_market(market)
                if candidate:
                    candidates.append(candidate)
            except Exception as exc:
                self.logger.warn(f"Market skipped due to error: {exc}")

        candidates.sort(key=lambda c: c["score"], reverse=True)
        return candidates

    def pick_best_candidate(self, max_markets: int = 20) -> Optional[Dict[str, Any]]:
        """Return the best candidate market or None."""
        candidates = self.scan_markets(max_markets=max_markets)
        return candidates[0] if candidates else None

    def _fetch_markets(self, max_markets: int) -> List[Dict[str, Any]]:
        """Fetch markets from the API."""
        self.logger.info("Fetching markets for scan...")
        resp = self._call_api(self.client.get_sampling_markets, next_cursor="")

        data: List[Dict[str, Any]] = []
        if isinstance(resp, dict):
            data = resp.get("data", [])
        elif isinstance(resp, list):
            data = resp

        if not data:
            self.logger.warn("No markets returned by API.")
            return []

        return data[:max_markets]

    def _analyze_market(self, market: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Analyze a market and return a candidate dict if it passes filters."""
        if self._is_closed(market):
            return None

        token_id = self._extract_token_id(market)
        if not token_id:
            return None

        if self.position_manager.has_position(token_id):
            return None
        if self.position_manager.is_blacklisted(token_id):
            return None

        question = market.get("question") or market.get("title") or "Unknown Market"
        volume_usd = self._extract_volume_usd(market)
        days_to_resolve = self._days_to_resolve(market)

        best_bid, best_ask = self._get_best_prices(token_id)
        if best_bid <= 0 or best_ask <= 0:
            return None

        odds = (best_bid + best_ask) / 2
        spread_percent = self._spread_percent(best_bid, best_ask)

        if not self._passes_filters(odds, spread_percent, volume_usd, days_to_resolve):
            return None

        score = self.strategy.calculate_market_score(
            spread_percent=spread_percent,
            volume_usd=volume_usd,
            odds=odds,
            days_to_resolve=days_to_resolve,
        )

        return {
            "token_id": token_id,
            "question": question,
            "odds": round(odds, 4),
            "best_bid": round(best_bid, 4),
            "best_ask": round(best_ask, 4),
            "spread_percent": round(spread_percent, 2),
            "volume_usd": round(volume_usd, 2),
            "days_to_resolve": days_to_resolve,
            "score": score,
        }

    def _passes_filters(
        self,
        odds: float,
        spread_percent: float,
        volume_usd: float,
        days_to_resolve: int,
    ) -> bool:
        """Apply configured filters."""
        min_odds = self.filters.get("min_odds", 0.30)
        max_odds = self.filters.get("max_odds", 0.70)
        max_spread = self.filters.get("max_spread_percent", 5.0)
        min_volume = self.filters.get("min_volume_usd", 100.0)
        max_days = self.filters.get("max_days_to_resolve", 30)

        if not (min_odds <= odds <= max_odds):
            return False
        if spread_percent > max_spread:
            return False
        if volume_usd < min_volume:
            return False
        if days_to_resolve > max_days:
            return False
        return True

    def _get_best_prices(self, token_id: str) -> Tuple[float, float]:
        """Fetch orderbook and return best bid/ask prices."""
        order_book = self._call_api(self.client.get_order_book, token_id)
        bids = getattr(order_book, "bids", None)
        asks = getattr(order_book, "asks", None)

        if bids is None or asks is None:
            if hasattr(order_book, "to_dict"):
                book_dict = order_book.to_dict()
                bids = book_dict.get("bids", [])
                asks = book_dict.get("asks", [])
            else:
                bids = []
                asks = []

        best_bid = self._extract_price(bids, default=0.0)
        best_ask = self._extract_price(asks, default=0.0)
        return best_bid, best_ask

    def _extract_price(self, orders: Any, default: float = 0.0) -> float:
        """Extract best price from order list."""
        if not orders:
            return default
        top = orders[0]
        if hasattr(top, "price"):
            return float(top.price)
        if isinstance(top, dict) and "price" in top:
            return float(top["price"])
        return default

    def _spread_percent(self, bid: float, ask: float) -> float:
        """Calculate spread percent using mid price."""
        if bid <= 0 or ask <= 0 or ask <= bid:
            return 0.0
        mid = (bid + ask) / 2
        return ((ask - bid) / mid) * 100

    def _extract_token_id(self, market: Dict[str, Any]) -> Optional[str]:
        """Extract a token_id from market data."""
        for key in ("token_id", "tokenId"):
            if key in market:
                return str(market[key])

        tokens = market.get("tokens") or []
        if isinstance(tokens, dict):
            tokens = list(tokens.values())

        if isinstance(tokens, list):
            # Prefer YES outcome when present
            for token in tokens:
                outcome = (token.get("outcome") or token.get("name") or "").lower()
                if outcome in ("yes", "true"):
                    return str(token.get("token_id") or token.get("tokenId") or "")
            if tokens:
                token = tokens[0]
                return str(token.get("token_id") or token.get("tokenId") or "")
        return None

    def _extract_volume_usd(self, market: Dict[str, Any]) -> float:
        """Extract volume in USD from market data."""
        volume_keys = [
            "volume_usd",
            "volumeUSD",
            "volume",
            "volume_24h",
            "volume24h",
            "volume24h_usd",
        ]
        for key in volume_keys:
            if key in market:
                return self._safe_float(market[key])
        return 0.0

    def _days_to_resolve(self, market: Dict[str, Any]) -> int:
        """Estimate days to resolve from market date fields."""
        date_keys = [
            "end_date_iso",
            "end_date",
            "end_time",
            "resolution_date",
            "resolution_time",
        ]
        for key in date_keys:
            if key in market and market[key]:
                parsed = self._parse_date(market[key])
                if parsed:
                    delta = parsed - datetime.utcnow()
                    days = max(0, int(delta.total_seconds() / 86400))
                    return days
        return 9999

    def _parse_date(self, value: Any) -> Optional[datetime]:
        """Parse datetime from string or timestamp."""
        if isinstance(value, (int, float)):
            try:
                return datetime.utcfromtimestamp(float(value))
            except (ValueError, OSError):
                return None
        if isinstance(value, str):
            try:
                return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(
                    tzinfo=None
                )
            except ValueError:
                return None
        return None

    def _is_closed(self, market: Dict[str, Any]) -> bool:
        """Detect closed/resolved markets."""
        status = str(market.get("status", "")).lower()
        if status in ("closed", "resolved", "settled"):
            return True
        if market.get("closed") is True:
            return True
        if market.get("active") is False:
            return True
        return False

    def _safe_float(self, value: Any) -> float:
        """Convert value to float safely."""
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _call_api(self, func, *args, **kwargs):
        """Rate-limit API calls."""
        self._rate_limit()
        return func(*args, **kwargs)

    def _rate_limit(self):
        """Simple client-side rate limiter."""
        if self.min_call_interval <= 0:
            return
        now = datetime.utcnow().timestamp()
        elapsed = now - self._last_call_ts
        if elapsed < self.min_call_interval:
            delay = self.min_call_interval - elapsed
            self.logger.debug(f"Rate limit sleep: {delay:.2f}s")
            from time import sleep

            sleep(delay)
        self._last_call_ts = datetime.utcnow().timestamp()
