"""
Trade execution module for the Polymarket bot.

Handles:
- Order placement (buy/sell)
- Partial fill verification
- Retry/backoff for transient API errors
"""

import time
from dataclasses import dataclass
from typing import Any, Optional, Tuple

from py_clob_client.clob_types import OrderArgs, PartialCreateOrderOptions
from py_clob_client.order_builder.constants import BUY, SELL


@dataclass
class TradeFill:
    """Represents the executed portion of an order."""

    order_id: Optional[str]
    filled_size: float
    avg_price: float
    fees_paid: float
    side: str
    dry_run: bool = False


class BotTrader:
    """Executes trades with safety and fill verification."""

    def __init__(self, client, config, logger):
        """
        Initialize trader dependencies.

        Args:
            client: Initialized ClobClient
            config: BotConfig instance
            logger: BotLogger instance
        """
        self.client = client
        self.config = config
        self.logger = logger

        self.dry_run = config.get("bot.dry_run", True)
        self.order_timeout = config.get("bot.order_timeout_seconds", 30)
        self.min_sell_ratio = config.get("risk.min_sell_price_ratio", 0.5)

        api_cfg = config.get("api", {})
        self.retry_attempts = api_cfg.get("retry_attempts", 3)
        self.retry_backoff = api_cfg.get("retry_backoff_seconds", 5)
        self.max_calls_per_minute = api_cfg.get("max_calls_per_minute", 20)
        self.min_call_interval = 60.0 / max(1, self.max_calls_per_minute)
        self._last_call_ts = 0.0

    def execute_buy(self, token_id: str, price: float, size: float) -> TradeFill:
        """Place a BUY order and verify fills."""
        return self._execute_order(token_id, price, size, BUY)

    def execute_sell(
        self, token_id: str, price: float, size: float, entry_price: Optional[float] = None
    ) -> TradeFill:
        """Place a SELL order with safety checks and verify fills."""
        if entry_price is not None:
            min_price = entry_price * self.min_sell_ratio
            if price < min_price:
                raise ValueError(
                    f"Sell price {price:.4f} below minimum allowed {min_price:.4f}"
                )
        return self._execute_order(token_id, price, size, SELL)

    def _execute_order(self, token_id: str, price: float, size: float, side: str) -> TradeFill:
        """Create and submit order, then confirm fills."""
        if self.dry_run:
            self.logger.info(
                f"DRY RUN - {side} {size} @ {price:.4f} (token {token_id[:8]}...)"
            )
            return TradeFill(
                order_id=None,
                filled_size=size,
                avg_price=price,
                fees_paid=0.0,
                side=side,
                dry_run=True,
            )

        order_args = OrderArgs(
            token_id=token_id,
            price=price,
            size=size,
            side=side,
        )

        options = PartialCreateOrderOptions(
            tick_size="0.01",
            neg_risk=False,
        )

        result = self._call_api_with_retries(
            self.client.create_and_post_order, order_args, options
        )
        order_id = self._extract_order_id(result)

        filled_size, avg_price, fees = self._resolve_fill(
            order_id=order_id,
            expected_size=size,
            expected_price=price,
        )

        return TradeFill(
            order_id=order_id,
            filled_size=filled_size,
            avg_price=avg_price,
            fees_paid=fees,
            side=side,
        )

    def _resolve_fill(
        self, order_id: Optional[str], expected_size: float, expected_price: float
    ) -> Tuple[float, float, float]:
        """Resolve actual fill size and price, handling partial fills."""
        if not order_id:
            return expected_size, expected_price, 0.0

        deadline = time.time() + self.order_timeout
        last_order = None

        while time.time() < deadline:
            try:
                last_order = self._call_api_with_retries(self.client.get_order, order_id)
                filled_size, avg_price, fees = self._parse_order_fill(
                    last_order, expected_size, expected_price
                )
                status = self._extract_order_status(last_order)

                if filled_size >= expected_size or status in ("filled", "canceled"):
                    return filled_size, avg_price, fees
            except Exception as exc:
                self.logger.warn(f"Order fetch failed: {exc}")

            time.sleep(2)

        if last_order:
            return self._parse_order_fill(last_order, expected_size, expected_price)

        self.logger.warn("Order fill not verified; assuming expected fill.")
        return expected_size, expected_price, 0.0

    def _parse_order_fill(
        self, order: Any, expected_size: float, expected_price: float
    ) -> Tuple[float, float, float]:
        """Extract filled size, average price, and fees from an order object."""
        filled_size = self._get_attr(order, ["filled_size", "filledSize", "size"], None)
        avg_price = self._get_attr(order, ["avg_price", "avgPrice", "price"], None)
        fees = self._get_attr(order, ["fees", "fee"], 0.0)

        if filled_size is None:
            filled_size = expected_size
        if avg_price is None:
            avg_price = expected_price

        return float(filled_size), float(avg_price), float(fees or 0.0)

    def _extract_order_status(self, order: Any) -> str:
        """Extract order status as lowercase string."""
        status = self._get_attr(order, ["status", "state"], "")
        return str(status).lower()

    def _extract_order_id(self, result: Any) -> Optional[str]:
        """Extract order ID from create_and_post_order response."""
        return self._get_attr(result, ["order_id", "orderId", "id", "orderID"], None)

    def _get_attr(self, obj: Any, keys: list, default: Any) -> Any:
        """Get attribute from object or dict."""
        for key in keys:
            if isinstance(obj, dict) and key in obj:
                return obj[key]
            if hasattr(obj, key):
                return getattr(obj, key)
        return default

    def _call_api_with_retries(self, func, *args, **kwargs):
        """Call API with simple retry/backoff and rate limiting."""
        last_exc = None
        for attempt in range(1, self.retry_attempts + 1):
            try:
                self._rate_limit()
                return func(*args, **kwargs)
            except Exception as exc:
                last_exc = exc
                msg = str(exc).lower()
                if attempt >= self.retry_attempts:
                    break
                if "429" in msg or "rate" in msg:
                    backoff = self.retry_backoff * attempt
                else:
                    backoff = max(1, self.retry_backoff)
                self.logger.warn(f"API error, retrying in {backoff}s: {exc}")
                time.sleep(backoff)
        raise last_exc

    def _rate_limit(self):
        """Simple client-side rate limiter."""
        if self.min_call_interval <= 0:
            return
        now = time.time()
        elapsed = now - self._last_call_ts
        if elapsed < self.min_call_interval:
            time.sleep(self.min_call_interval - elapsed)
        self._last_call_ts = time.time()
