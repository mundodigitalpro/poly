"""
WebSocket client for real-time Polymarket orderbook data.

Provides low-latency market data updates via WebSocket connection instead
of polling, reducing latency from 10s to <100ms.
"""

import asyncio
import json
import time
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional


@dataclass
class OrderbookSnapshot:
    """Snapshot of orderbook at a point in time."""

    token_id: str
    timestamp: float
    bids: List[tuple]  # [(price, size), ...]
    asks: List[tuple]  # [(price, size), ...]

    @property
    def best_bid(self) -> float:
        """Get highest bid price."""
        return max(self.bids, key=lambda x: x[0])[0] if self.bids else 0.0

    @property
    def best_ask(self) -> float:
        """Get lowest ask price."""
        return min(self.asks, key=lambda x: x[0])[0] if self.asks else 0.0

    @property
    def mid_price(self) -> float:
        """Calculate mid-market price."""
        if self.best_bid and self.best_ask:
            return (self.best_bid + self.best_ask) / 2
        return 0.0

    @property
    def spread(self) -> float:
        """Calculate bid-ask spread."""
        if self.best_bid and self.best_ask:
            return self.best_ask - self.best_bid
        return 0.0

    @property
    def spread_percent(self) -> float:
        """Calculate spread as percentage of mid price."""
        if self.mid_price > 0:
            return (self.spread / self.mid_price) * 100
        return 0.0


class PolymarketWebSocket:
    """
    WebSocket client for Polymarket CLOB real-time data.

    Connects to Polymarket WebSocket endpoint and subscribes to orderbook
    updates for specified tokens. Provides callbacks for real-time price
    updates with <100ms latency.

    Example:
        ws = PolymarketWebSocket(logger)
        await ws.connect()
        await ws.subscribe(["token_id_1", "token_id_2"])

        @ws.on_book_update
        async def handle_update(snapshot):
            print(f"Price: {snapshot.mid_price}")

        await ws.run()
    """

    # Polymarket WebSocket endpoint
    WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"

    def __init__(self, logger, config: Optional[dict] = None):
        """
        Initialize WebSocket client.

        Args:
            logger: Logger instance for debug/info/error messages
            config: Optional config dict with reconnect_delay, ping_interval
        """
        self.logger = logger
        self.config = config or {}

        self.ws = None
        self.subscribed_tokens: List[str] = []
        self.orderbooks: Dict[str, OrderbookSnapshot] = {}
        self.callbacks: List[Callable] = []
        self.running = False

        # Config
        self.reconnect_delay = self.config.get("websocket_reconnect_delay", 5)
        self.ping_interval = self.config.get("websocket_ping_interval", 30)
        self.max_reconnects = self.config.get("websocket_max_reconnects", 10)

        # Stats
        self.reconnect_count = 0
        self.messages_received = 0
        self.last_message_time = 0

    async def connect(self):
        """Establish WebSocket connection to Polymarket."""
        try:
            # Import websockets here to avoid import error if not installed
            import websockets

            self.ws = await websockets.connect(
                self.WS_URL,
                ping_interval=self.ping_interval,
                ping_timeout=10,
            )
            self.logger.info("WebSocket connected to Polymarket")
            self.reconnect_count = 0
            return True

        except ImportError:
            self.logger.error(
                "websockets library not installed. Run: pip install websockets"
            )
            return False
        except Exception as exc:
            self.logger.error(f"Failed to connect WebSocket: {exc}")
            return False

    async def subscribe(self, token_ids: List[str]):
        """
        Subscribe to orderbook updates for specified tokens.

        Args:
            token_ids: List of token IDs to subscribe to
        """
        if not self.ws:
            self.logger.error("WebSocket not connected. Call connect() first.")
            return

        self.subscribed_tokens.extend(token_ids)
        unique_tokens = list(set(self.subscribed_tokens))
        self.subscribed_tokens = unique_tokens

        # Send single message with all token IDs (Polymarket format)
        message = {"assets_ids": token_ids, "type": "market"}

        try:
            await self.ws.send(json.dumps(message))
            for token_id in token_ids:
                self.logger.info(f"Subscribed to {token_id[:8]}...")
        except Exception as exc:
            self.logger.error(f"Failed to subscribe: {exc}")

    async def unsubscribe(self, token_ids: List[str]):
        """
        Unsubscribe from orderbook updates.

        Args:
            token_ids: List of token IDs to unsubscribe from
        """
        if not self.ws:
            return

        # Note: Polymarket WebSocket doesn't seem to support unsubscribe
        # Instead, we just remove from our tracking
        for token_id in token_ids:
            if token_id in self.subscribed_tokens:
                self.subscribed_tokens.remove(token_id)
            if token_id in self.orderbooks:
                del self.orderbooks[token_id]
            self.logger.info(f"Unsubscribed from {token_id[:8]}... (local only)")

    async def run(self, auto_reconnect: bool = True):
        """
        Main loop to receive and process WebSocket messages.

        Args:
            auto_reconnect: Whether to automatically reconnect on disconnect
        """
        import websockets

        self.running = True
        self.logger.info("WebSocket message loop started")

        while self.running:
            try:
                if not self.ws:
                    if not await self.connect():
                        await asyncio.sleep(self.reconnect_delay)
                        continue

                message = await self.ws.recv()
                self.messages_received += 1
                self.last_message_time = time.time()
                await self._handle_message(message)

            except websockets.ConnectionClosed:
                self.logger.warn("WebSocket connection closed")

                if auto_reconnect and self.reconnect_count < self.max_reconnects:
                    await self._reconnect()
                else:
                    self.logger.error("Max reconnects reached, stopping WebSocket")
                    break

            except asyncio.CancelledError:
                self.logger.info("WebSocket task cancelled")
                break

            except Exception as exc:
                self.logger.error(f"WebSocket error: {exc}")
                await asyncio.sleep(1)

        self.logger.info("WebSocket message loop stopped")

    async def _handle_message(self, message: str):
        """
        Parse and process incoming WebSocket messages.

        Args:
            message: Raw JSON message from WebSocket
        """
        # Skip empty messages (pings, pongs, keepalives)
        if not message or not message.strip():
            return

        try:
            data = json.loads(message)
        except json.JSONDecodeError as exc:
            self.logger.debug(f"Non-JSON message received: {message[:50] if message else '(empty)'}")
            return

        try:
            # Handle list responses (Polymarket sometimes sends arrays)
            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        await self._process_message_dict(item)
                return

            # Handle single dict response
            if isinstance(data, dict):
                await self._process_message_dict(data)

        except Exception as exc:
            self.logger.error(f"Failed to handle message: {exc}")

    async def _process_message_dict(self, data: dict):
        """Process a single message dictionary."""
        msg_type = data.get("type")

        if msg_type == "book":
            # Orderbook update
            snapshot = self._parse_orderbook(data)
            self.orderbooks[snapshot.token_id] = snapshot

            # Trigger all registered callbacks
            for callback in self.callbacks:
                try:
                    await callback(snapshot)
                except Exception as exc:
                    self.logger.error(f"Callback error: {exc}")

        elif msg_type == "subscribed":
            market = data.get("market")
            self.logger.debug(f"Confirmed subscription to {market}")

        elif msg_type == "error":
            error = data.get("message", "Unknown error")
            self.logger.error(f"WebSocket error message: {error}")

        elif msg_type == "price_change":
            # Price change notification - process as lightweight update
            await self._handle_price_change(data)

        elif msg_type in ("connected", "pong", "heartbeat"):
            # Connection/keepalive messages - ignore silently
            pass

        else:
            # Log unknown types at debug level to investigate
            self.logger.debug(f"Unknown message type: {msg_type}, keys: {list(data.keys())}")

    async def _handle_price_change(self, data: dict):
        """Handle price_change messages as lightweight orderbook updates."""
        token_id = data.get("asset_id") or data.get("market")
        if not token_id:
            return

        # Update cached orderbook if we have one
        if token_id in self.orderbooks:
            snapshot = self.orderbooks[token_id]
            # Price change messages might have price/side info
            # For now, just mark as recently updated
            snapshot.timestamp = time.time()

    def _parse_orderbook(self, data: dict) -> OrderbookSnapshot:
        """
        Convert WebSocket message to OrderbookSnapshot.

        Args:
            data: Parsed JSON data from WebSocket

        Returns:
            OrderbookSnapshot with bids/asks
        """
        token_id = data.get("market", "")
        timestamp = data.get("timestamp", time.time())

        # Parse bids (buy orders)
        bids = []
        for bid in data.get("bids", []):
            try:
                price = float(bid.get("price", 0))
                size = float(bid.get("size", 0))
                if price > 0 and size > 0:
                    bids.append((price, size))
            except (ValueError, TypeError):
                continue

        # Parse asks (sell orders)
        asks = []
        for ask in data.get("asks", []):
            try:
                price = float(ask.get("price", 0))
                size = float(ask.get("size", 0))
                if price > 0 and size > 0:
                    asks.append((price, size))
            except (ValueError, TypeError):
                continue

        return OrderbookSnapshot(
            token_id=token_id, timestamp=timestamp, bids=bids, asks=asks
        )

    async def _reconnect(self):
        """Reconnect WebSocket and resubscribe to all tokens."""
        self.reconnect_count += 1
        delay = self.reconnect_delay * (2 ** (self.reconnect_count - 1))  # Exponential backoff
        delay = min(delay, 60)  # Cap at 60 seconds

        self.logger.info(
            f"Reconnecting WebSocket in {delay}s (attempt {self.reconnect_count})"
        )
        await asyncio.sleep(delay)

        if await self.connect():
            # Resubscribe to all tokens
            if self.subscribed_tokens:
                await self.subscribe(self.subscribed_tokens.copy())

    def on_book_update(self, callback: Callable):
        """
        Register callback for orderbook updates.

        Args:
            callback: Async function that receives OrderbookSnapshot

        Example:
            @ws.on_book_update
            async def handler(snapshot):
                print(f"Price: {snapshot.mid_price}")
        """
        self.callbacks.append(callback)
        return callback  # Allow use as decorator

    def get_orderbook(self, token_id: str) -> Optional[OrderbookSnapshot]:
        """
        Get cached orderbook snapshot for a token.

        Args:
            token_id: Token ID to look up

        Returns:
            OrderbookSnapshot if available, None otherwise
        """
        return self.orderbooks.get(token_id)

    def get_stats(self) -> dict:
        """
        Get WebSocket connection statistics.

        Returns:
            Dict with messages_received, reconnect_count, etc.
        """
        return {
            "connected": self.ws is not None and not self.ws.closed,
            "subscribed_tokens": len(self.subscribed_tokens),
            "cached_orderbooks": len(self.orderbooks),
            "messages_received": self.messages_received,
            "reconnect_count": self.reconnect_count,
            "last_message_age": time.time() - self.last_message_time
            if self.last_message_time
            else None,
        }

    async def close(self):
        """Close WebSocket connection gracefully."""
        self.running = False

        if self.ws:
            try:
                await self.ws.close()
                self.logger.info("WebSocket closed")
            except Exception as exc:
                self.logger.error(f"Error closing WebSocket: {exc}")

        self.ws = None
        self.orderbooks.clear()
        self.callbacks.clear()


# Example usage
if __name__ == "__main__":

    class SimpleLogger:
        def info(self, msg):
            print(f"[INFO] {msg}")

        def warn(self, msg):
            print(f"[WARN] {msg}")

        def error(self, msg):
            print(f"[ERROR] {msg}")

        def debug(self, msg):
            pass

    async def main():
        logger = SimpleLogger()
        ws = PolymarketWebSocket(logger)

        # Connect
        await ws.connect()

        # Subscribe to a token (replace with real token ID)
        await ws.subscribe(["example_token_id"])

        # Register callback
        @ws.on_book_update
        async def on_update(snapshot: OrderbookSnapshot):
            print(f"Token: {snapshot.token_id[:8]}...")
            print(f"  Best Bid: {snapshot.best_bid:.4f}")
            print(f"  Best Ask: {snapshot.best_ask:.4f}")
            print(f"  Mid Price: {snapshot.mid_price:.4f}")
            print(f"  Spread: {snapshot.spread_percent:.2f}%")
            print()

        # Run for 60 seconds
        try:
            await asyncio.wait_for(ws.run(), timeout=60)
        except asyncio.TimeoutError:
            print("Demo complete")

        # Close
        await ws.close()

    asyncio.run(main())
