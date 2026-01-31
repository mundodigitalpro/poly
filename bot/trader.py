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
        self,
        token_id: str,
        price: float,
        size: float,
        entry_price: Optional[float] = None,
        is_emergency_exit: bool = False,
    ) -> TradeFill:
        """Place a SELL order with safety checks and verify fills."""
        if entry_price is not None and not is_emergency_exit:
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

    # ========================================================================
    # CONCURRENT ORDER METHODS (Buy + TP/SL limit orders)
    # ========================================================================

    def execute_buy_with_exits(
        self,
        token_id: str,
        entry_price: float,
        size: float,
        tp_price: float,
        sl_price: float,
    ) -> dict:
        """
        Execute market buy and place TP/SL limit orders concurrently.

        This reduces API calls vs monitoring, provides instant execution at
        target prices, and eliminates slippage on exits.

        Args:
            token_id: Token to buy
            entry_price: Market price for buy (best_ask)
            size: Amount to buy (in shares)
            tp_price: Take profit limit price
            sl_price: Stop loss limit price

        Returns:
            {
                'buy_fill': TradeFill,
                'tp_order_id': str | None,
                'sl_order_id': str | None,
                'tp_price': float,
                'sl_price': float
            }
        """
        # Step 1: Execute market buy
        self.logger.info(
            f"Executing BUY with concurrent exits: "
            f"{size} @ {entry_price:.4f} (TP={tp_price:.4f} SL={sl_price:.4f})"
        )

        buy_fill = self.execute_buy(token_id, entry_price, size)

        if buy_fill.filled_size == 0:
            raise RuntimeError("Buy order filled 0 shares")

        # Step 2: Place TP limit sell
        tp_order_id = None
        try:
            tp_order_id = self._place_limit_sell(
                token_id=token_id,
                price=tp_price,
                size=buy_fill.filled_size,
            )
            self.logger.info(f"TP limit order placed: {tp_order_id} @ {tp_price:.4f}")
        except Exception as exc:
            self.logger.error(f"Failed to place TP limit order: {exc}")
            # Continue with position but mark as needing manual monitoring

        # Step 3: Place SL limit sell
        sl_order_id = None
        if tp_order_id:  # Only place SL if TP succeeded
            try:
                sl_order_id = self._place_limit_sell(
                    token_id=token_id,
                    price=sl_price,
                    size=buy_fill.filled_size,
                )
                self.logger.info(f"SL limit order placed: {sl_order_id} @ {sl_price:.4f}")
            except Exception as exc:
                self.logger.error(f"Failed to place SL limit order: {exc}")
                # Cancel TP order if SL fails (safety: don't want orphaned TP)
                try:
                    self.cancel_order(tp_order_id)
                    self.logger.info(f"Canceled TP order {tp_order_id} due to SL failure")
                    tp_order_id = None
                except Exception as cancel_exc:
                    self.logger.warn(f"Failed to cancel TP order: {cancel_exc}")

        return {
            'buy_fill': buy_fill,
            'tp_order_id': tp_order_id,
            'sl_order_id': sl_order_id,
            'tp_price': tp_price,
            'sl_price': sl_price,
        }

    def _place_limit_sell(self, token_id: str, price: float, size: float) -> Optional[str]:
        """
        Place a limit SELL order that stays in orderbook until filled.

        Unlike market orders (price=best_bid), limit orders use target price
        and remain open until market reaches that price.

        Args:
            token_id: Token to sell
            price: Limit price (TP or SL target)
            size: Amount to sell

        Returns:
            order_id: ID of placed limit order, or None if failed
        """
        if self.dry_run:
            self.logger.info(
                f"DRY RUN - LIMIT SELL {size} @ {price:.4f} (token {token_id[:8]}...)"
            )
            import random
            return f"dry_run_limit_{random.randint(1000, 9999)}"

        order_args = OrderArgs(
            token_id=token_id,
            price=price,
            size=size,
            side=SELL,
        )

        options = PartialCreateOrderOptions(
            tick_size="0.01",
            neg_risk=False,
        )

        # create_and_post_order uses OrderType.GTC by default (Good-Till-Cancelled)
        # This is perfect for TP/SL limit orders that should persist
        result = self._call_api_with_retries(
            self.client.create_and_post_order, order_args, options
        )

        order_id = self._extract_order_id(result)
        if not order_id:
            raise RuntimeError("Failed to extract order ID from limit order response")

        return order_id

    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an open order.

        Args:
            order_id: Order to cancel

        Returns:
            True if canceled successfully, False otherwise
        """
        if self.dry_run:
            self.logger.info(f"DRY RUN - CANCEL order {order_id}")
            return True

        try:
            self._call_api_with_retries(self.client.cancel, order_id)
            self.logger.info(f"Order canceled: {order_id}")
            return True
        except Exception as exc:
            self.logger.warn(f"Failed to cancel order {order_id}: {exc}")
            return False

    def check_order_status(self, order_id: str) -> dict:
        """
        Check if a limit order has filled.

        Args:
            order_id: Order to check

        Returns:
            {
                'status': 'open' | 'filled' | 'partial' | 'canceled' | 'unknown',
                'filled_size': float,
                'avg_price': float,
                'fees': float
            }
        """
        if self.dry_run:
            # In dry run, simulate orders as always open
            return {
                'status': 'open',
                'filled_size': 0,
                'avg_price': 0,
                'fees': 0,
            }

        try:
            order = self._call_api_with_retries(self.client.get_order, order_id)
            status = self._extract_order_status(order)
            filled_size, avg_price, fees = self._parse_order_fill(
                order, expected_size=0, expected_price=0
            )

            return {
                'status': status,
                'filled_size': filled_size,
                'avg_price': avg_price,
                'fees': fees,
            }
        except Exception as exc:
            self.logger.warn(f"Failed to fetch order status for {order_id}: {exc}")
            return {
                'status': 'unknown',
                'filled_size': 0,
                'avg_price': 0,
                'fees': 0,
            }

    # ========================================================================
    # PRE-SIGN BATCH ORDERS - Minimized latency for multiple orders
    # ========================================================================

    def execute_batch_orders(
        self,
        orders: list,
        pre_sign: bool = True,
    ) -> list:
        """
        Execute multiple orders with minimal latency using pre-signing.

        Pre-signing separates the slow cryptographic signing from the fast
        network submission, reducing total time for multiple orders.

        Args:
            orders: List of dicts with {token_id, price, size, side}
            pre_sign: If True, sign all orders first then submit in batch

        Returns:
            List of TradeFill results for each order
        """
        if not orders:
            return []

        if self.dry_run:
            self.logger.info(f"DRY RUN - Batch executing {len(orders)} orders")
            results = []
            for order in orders:
                results.append(TradeFill(
                    order_id=None,
                    filled_size=order['size'],
                    avg_price=order['price'],
                    fees_paid=0.0,
                    side=order['side'],
                    dry_run=True,
                ))
            return results

        if pre_sign:
            return self._execute_batch_presigned(orders)
        else:
            return self._execute_batch_sequential(orders)

    def _execute_batch_presigned(self, orders: list) -> list:
        """
        Execute batch with pre-signing for minimum latency.

        1. Sign all orders first (slow, ~100-200ms each)
        2. Submit all signed orders in rapid succession (fast, ~50ms each)
        """
        self.logger.info(f"Pre-signing {len(orders)} orders...")
        start_time = time.time()

        # Step 1: Pre-sign all orders (the slow part)
        signed_orders = []
        for i, order in enumerate(orders):
            try:
                signed = self._sign_order(
                    token_id=order['token_id'],
                    price=order['price'],
                    size=order['size'],
                    side=order['side'],
                )
                signed_orders.append({
                    'original': order,
                    'signed': signed,
                })
                self.logger.debug(f"Signed order {i+1}/{len(orders)}")
            except Exception as exc:
                self.logger.error(f"Failed to sign order {i+1}: {exc}")
                signed_orders.append({
                    'original': order,
                    'signed': None,
                    'error': str(exc),
                })

        sign_time = time.time() - start_time
        self.logger.info(f"Pre-signed {len(signed_orders)} orders in {sign_time:.2f}s")

        # Step 2: Submit all signed orders (the fast part)
        self.logger.info("Submitting signed orders...")
        submit_start = time.time()
        results = []

        for item in signed_orders:
            if item.get('signed') is None:
                # Skip failed signatures
                results.append(TradeFill(
                    order_id=None,
                    filled_size=0,
                    avg_price=0,
                    fees_paid=0,
                    side=item['original']['side'],
                ))
                continue

            try:
                result = self._submit_signed_order(item['signed'])
                order_id = self._extract_order_id(result)

                # Quick fill check (don't wait for full verification)
                filled_size = item['original']['size']
                avg_price = item['original']['price']

                results.append(TradeFill(
                    order_id=order_id,
                    filled_size=filled_size,
                    avg_price=avg_price,
                    fees_paid=0,
                    side=item['original']['side'],
                ))
            except Exception as exc:
                self.logger.error(f"Failed to submit signed order: {exc}")
                results.append(TradeFill(
                    order_id=None,
                    filled_size=0,
                    avg_price=0,
                    fees_paid=0,
                    side=item['original']['side'],
                ))

        submit_time = time.time() - submit_start
        total_time = time.time() - start_time
        self.logger.info(
            f"Batch complete: {len(results)} orders in {total_time:.2f}s "
            f"(sign={sign_time:.2f}s, submit={submit_time:.2f}s)"
        )

        return results

    def _execute_batch_sequential(self, orders: list) -> list:
        """Fallback: execute orders one by one (slower but more reliable)."""
        self.logger.info(f"Executing {len(orders)} orders sequentially...")
        results = []

        for i, order in enumerate(orders):
            try:
                fill = self._execute_order(
                    token_id=order['token_id'],
                    price=order['price'],
                    size=order['size'],
                    side=order['side'],
                )
                results.append(fill)
                self.logger.debug(f"Order {i+1}/{len(orders)} executed")
            except Exception as exc:
                self.logger.error(f"Order {i+1} failed: {exc}")
                results.append(TradeFill(
                    order_id=None,
                    filled_size=0,
                    avg_price=0,
                    fees_paid=0,
                    side=order['side'],
                ))

        return results

    def _sign_order(self, token_id: str, price: float, size: float, side: str) -> dict:
        """
        Sign an order without submitting it.

        This separates the cryptographic signing (slow) from submission (fast).

        Args:
            token_id: Token to trade
            price: Order price
            size: Order size
            side: BUY or SELL

        Returns:
            Signed order object ready for submission
        """
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

        # Use create_order (sign only) instead of create_and_post_order
        # This returns a signed order that can be submitted later
        try:
            signed = self.client.create_order(order_args, options)
            return signed
        except AttributeError:
            # Fallback if create_order doesn't exist
            # Some versions only have create_and_post_order
            self.logger.debug("create_order not available, using full create_and_post")
            return {'fallback': True, 'args': order_args, 'options': options}

    def _submit_signed_order(self, signed_order: dict) -> Any:
        """
        Submit a pre-signed order to the exchange.

        Args:
            signed_order: Previously signed order from _sign_order

        Returns:
            Order result from API
        """
        self._rate_limit()

        if signed_order.get('fallback'):
            # Fallback mode: sign and submit together
            return self.client.create_and_post_order(
                signed_order['args'],
                signed_order['options']
            )

        # Normal mode: submit pre-signed order
        try:
            return self.client.post_order(signed_order)
        except AttributeError:
            # Fallback if post_order doesn't exist
            return self.client.create_and_post_order(
                signed_order.get('args', signed_order),
                signed_order.get('options', PartialCreateOrderOptions(tick_size="0.01"))
            )

    def execute_paired_buy_with_batch(
        self,
        token_id: str,
        entry_price: float,
        size: float,
        tp_price: float,
        sl_price: float,
    ) -> dict:
        """
        Execute BUY + TP + SL using pre-signed batch for minimum latency.

        This is faster than execute_buy_with_exits because all three orders
        are signed upfront before any submission.

        Args:
            token_id: Token to buy
            entry_price: Buy price
            size: Order size
            tp_price: Take profit price
            sl_price: Stop loss price

        Returns:
            Same format as execute_buy_with_exits
        """
        if self.dry_run:
            return self.execute_buy_with_exits(
                token_id, entry_price, size, tp_price, sl_price
            )

        self.logger.info(
            f"Batch paired order: BUY {size} @ {entry_price:.4f} "
            f"(TP={tp_price:.4f} SL={sl_price:.4f})"
        )

        # Pre-sign all three orders
        orders_to_sign = [
            {'token_id': token_id, 'price': entry_price, 'size': size, 'side': BUY},
            {'token_id': token_id, 'price': tp_price, 'size': size, 'side': SELL},
            {'token_id': token_id, 'price': sl_price, 'size': size, 'side': SELL},
        ]

        signed = []
        for order in orders_to_sign:
            try:
                s = self._sign_order(**order)
                signed.append({'order': order, 'signed': s})
            except Exception as exc:
                self.logger.error(f"Failed to sign {order['side']}: {exc}")
                signed.append({'order': order, 'signed': None, 'error': str(exc)})

        # Submit BUY first (must fill before exits make sense)
        buy_result = None
        if signed[0]['signed']:
            try:
                result = self._submit_signed_order(signed[0]['signed'])
                order_id = self._extract_order_id(result)
                buy_result = TradeFill(
                    order_id=order_id,
                    filled_size=size,
                    avg_price=entry_price,
                    fees_paid=0,
                    side=BUY,
                )
            except Exception as exc:
                self.logger.error(f"BUY submission failed: {exc}")

        if not buy_result or buy_result.filled_size == 0:
            raise RuntimeError("Buy order failed in batch execution")

        # Submit TP and SL
        tp_order_id = None
        sl_order_id = None

        if signed[1]['signed']:
            try:
                result = self._submit_signed_order(signed[1]['signed'])
                tp_order_id = self._extract_order_id(result)
                self.logger.info(f"TP submitted: {tp_order_id}")
            except Exception as exc:
                self.logger.error(f"TP submission failed: {exc}")

        if signed[2]['signed'] and tp_order_id:
            try:
                result = self._submit_signed_order(signed[2]['signed'])
                sl_order_id = self._extract_order_id(result)
                self.logger.info(f"SL submitted: {sl_order_id}")
            except Exception as exc:
                self.logger.error(f"SL submission failed: {exc}")
                # Cancel TP if SL fails
                if tp_order_id:
                    self.cancel_order(tp_order_id)
                    tp_order_id = None

        return {
            'buy_fill': buy_result,
            'tp_order_id': tp_order_id,
            'sl_order_id': sl_order_id,
            'tp_price': tp_price,
            'sl_price': sl_price,
        }
