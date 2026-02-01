"""
Market scanner for the Polymarket trading bot.

Fetches markets, applies filters, and ranks candidates using the strategy score.
Optionally integrates with Gamma API for volume and liquidity data.
"""

from datetime import datetime
import time
from typing import Any, Dict, List, Optional, Tuple

from py_clob_client.constants import END_CURSOR

from bot.gamma_client import GammaClient


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
            position_manager: PositionManager instance
            strategy: TradingStrategy instance
            verbose_filters: Whether to log all rejections at INFO level
        """
        self.client = client
        self.config = config
        self.logger = logger
        self.position_manager = position_manager
        self.strategy = strategy
        self.verbose_filters = False

        self.filters = config.get("market_filters", {})
        self.market_source = self.filters.get("source", "sampling")
        self.max_markets = self.filters.get("max_markets", 200)
        self.allow_missing_resolution = self.filters.get(
            "allow_missing_resolution_date", False
        )
        self.treat_inactive_as_closed = self.filters.get(
            "treat_inactive_as_closed", True
        )
        self.max_detail_fetch = self.filters.get("max_market_detail_fetch", 50)
        self._detail_fetch_count = 0
        api_cfg = config.get("api", {})
        self.max_calls_per_minute = api_cfg.get("max_calls_per_minute", 20)
        self.min_call_interval = 60.0 / max(1, self.max_calls_per_minute)
        self._last_call_ts = 0.0

        # Gamma API integration for volume/liquidity data
        gamma_cfg = config.get("gamma_api", {})
        self.gamma_enabled = gamma_cfg.get("enabled", False)
        self.gamma_client = None
        self._gamma_cache: Dict[str, Dict] = {}  # condition_id -> gamma data

        if self.gamma_enabled:
            try:
                self.gamma_client = GammaClient(logger=self.logger)
                self.logger.info("Gamma API client initialized")
            except Exception as exc:
                self.logger.warn(f"Failed to init Gamma client: {exc}")
                self.gamma_enabled = False

        # Whale tracking integration for sentiment-based scoring
        whale_cfg = config.get("whale_tracking", {})
        self.whale_enabled = whale_cfg.get("enabled", False)
        self.whale_weight = whale_cfg.get("score_weight", 0.2)
        self.whale_service = None
        if self.whale_enabled:
            try:
                from bot.whale_service import WhaleService
                self.whale_service = WhaleService(
                    min_whale_size=whale_cfg.get("min_size", 500)
                )
                self.logger.info("Whale tracking service initialized")
            except Exception as exc:
                self.logger.warn(f"Failed to init WhaleService: {exc}")
                self.whale_enabled = False

    def scan_markets(self, max_markets: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Scan markets and return ranked candidates.

        Args:
            max_markets: Maximum number of markets to analyze

        Returns:
            List of candidate dicts sorted by score desc
        """
        if max_markets is None:
            max_markets = self.max_markets
        self._detail_fetch_count = 0

        # Use Gamma API as primary source if enabled (has volume data)
        # Fall back to CLOB API if Gamma disabled or fails
        if self.gamma_enabled and self.gamma_client:
            markets = self._fetch_gamma_markets(max_markets)
            if not markets:
                self.logger.warn("Gamma fetch failed, falling back to CLOB")
                markets = self._fetch_markets(max_markets)
        else:
            markets = self._fetch_markets(max_markets)
        candidates: List[Dict[str, Any]] = []
        stats = {
            "closed": 0,
            "closed_status": 0,
            "closed_flag": 0,
            "inactive_flag": 0,
            "missing_token": 0,
            "blacklisted": 0,
            "has_position": 0,
            "metadata_filtered": 0,
            "no_orderbook": 0,
            "price_filtered": 0,
            "errors": 0,
        }

        for i, market in enumerate(markets):
            if i % 5 == 0:
                self.logger.info(f"Scanning market {i+1}/{len(markets)}...")
            try:
                if i < 3:
                    self._log_market_status(market)
                candidate, reason = self._analyze_market(market)
                if candidate:
                    candidates.append(candidate)
                else:
                    stats[reason] = stats.get(reason, 0) + 1
            except Exception as exc:
                stats["errors"] += 1
                self.logger.warn(f"Market skipped due to error: {exc}")

        candidates.sort(key=lambda c: c["score"], reverse=True)
        self.logger.info(
            "Scan summary: "
            f"candidates={len(candidates)} "
            f"closed={stats['closed']} "
            f"closed_status={stats['closed_status']} "
            f"closed_flag={stats['closed_flag']} "
            f"inactive_flag={stats['inactive_flag']} "
            f"missing_token={stats['missing_token']} "
            f"has_position={stats['has_position']} "
            f"blacklisted={stats['blacklisted']} "
            f"metadata_filtered={stats['metadata_filtered']} "
            f"no_orderbook={stats['no_orderbook']} "
            f"price_filtered={stats['price_filtered']} "
            f"errors={stats['errors']}"
        )
        return candidates

    def pick_best_candidate(
        self, max_markets: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """Return the best candidate market or None."""
        candidates = self.scan_markets(max_markets=max_markets)
        return candidates[0] if candidates else None

    def _fetch_markets(self, max_markets: int) -> List[Dict[str, Any]]:
        """Fetch markets from the API."""
        self.logger.info("Fetching markets for scan...")
        fetch_fn = self._select_market_source()

        results: List[Dict[str, Any]] = []
        next_cursor = "MA=="

        while next_cursor != END_CURSOR and len(results) < max_markets:
            try:
                resp = self._call_api(fetch_fn, next_cursor=next_cursor)
            except Exception as exc:
                self.logger.warn(f"Market fetch failed: {exc}")
                return results
            if isinstance(resp, dict):
                data = resp.get("data", [])
                next_cursor = resp.get("next_cursor", END_CURSOR)
            elif isinstance(resp, list):
                data = resp
                next_cursor = END_CURSOR
            else:
                data = []
                next_cursor = END_CURSOR

            if not data:
                break

            remaining = max_markets - len(results)
            results.extend(data[:remaining])

        if not results:
            self.logger.warn("No markets returned by API.")
        return results

    def _analyze_market(
        self, market: Dict[str, Any]
    ) -> Tuple[Optional[Dict[str, Any]], str]:
        """Analyze a market and return a candidate dict + reason."""
        closed, reason = self._is_closed(market)
        if closed:
            return None, reason

        token_candidates = self._extract_token_candidates(market)
        if not token_candidates:
            return None, "missing_token"

        question = market.get("question") or market.get("title") or "Unknown Market"
        volume_usd = self._extract_volume_usd(market)
        liquidity = self._extract_liquidity(market)
        days_to_resolve = self._days_to_resolve(market)

        if not self._passes_metadata_filters(
            volume_usd, liquidity, days_to_resolve, token_candidates[0]
        ):
            return None, "metadata_filtered"

        best_bid = best_ask = 0.0
        token_id = None
        for candidate_id in token_candidates:
            if self.position_manager.has_position(candidate_id):
                continue
            if self.position_manager.is_blacklisted(candidate_id):
                continue
            best_bid, best_ask = self._get_best_prices(candidate_id)
            if best_bid > 0 and best_ask > 0:
                token_id = candidate_id
                break

        if not token_id or best_bid <= 0 or best_ask <= 0:
            return None, "no_orderbook"

        odds = (best_bid + best_ask) / 2
        spread_percent = self._spread_percent(best_bid, best_ask)

        if not self._passes_price_filters(odds, spread_percent, token_id, days_to_resolve):
            msg = (
                f"Rejected {token_id[:8]}: odds={odds:.2f} spread={spread_percent:.1f}% "
                f"days={days_to_resolve}"
            )
            if self.verbose_filters:
                self.logger.info(msg)
            else:
                self.logger.debug(msg)
            return None, "price_filtered"

        score = self.strategy.calculate_market_score(
            spread_percent=spread_percent,
            volume_usd=volume_usd,
            odds=odds,
            days_to_resolve=days_to_resolve,
        )

        # Apply whale sentiment modifier if enabled
        if self.whale_enabled and self.whale_service:
            sentiment = self.whale_service.get_sentiment(token_id)
            score *= (1 + sentiment * self.whale_weight)
            if abs(sentiment) > 0.3:
                self.logger.info(
                    f"Whale sentiment for {token_id[:8]}: {sentiment:+.2f} "
                    f"(score adjusted: {score:.2f})"
                )

        # Log accepted candidate with key metrics
        self.logger.info(
            f"✓ Candidate: {question[:60]}... | "
            f"token={token_id[:8]}... | odds={odds:.2f} | "
            f"spread={spread_percent:.1f}% | days={days_to_resolve} | "
            f"score={score:.1f}"
        )

        return {
            "token_id": token_id,
            "question": question,
            "odds": round(odds, 4),
            "best_bid": round(best_bid, 4),
            "best_ask": round(best_ask, 4),
            "spread_percent": round(spread_percent, 2),
            "volume_usd": round(volume_usd, 2),
            "liquidity": round(liquidity, 2),
            "days_to_resolve": days_to_resolve,
            "score": score,
        }, "ok"

    def _passes_metadata_filters(
        self,
        volume_usd: float,
        liquidity: float,
        days_to_resolve: int,
        token_id: str,
    ) -> bool:
        """Apply filters that do not require orderbook calls."""
        min_odds = self.filters.get("min_odds", 0.30)
        max_odds = self.filters.get("max_odds", 0.70)
        max_spread = self.filters.get("max_spread_percent", 5.0)
        min_volume = self.filters.get("min_volume_usd", 100.0)
        min_volume_24h = self.filters.get("min_volume_24h", 0)
        min_liquidity = self.filters.get("min_liquidity", 0)
        min_days = self.filters.get("min_days_to_resolve", 2)
        max_days = self.filters.get("max_days_to_resolve", 30)
        _ = (min_odds, max_odds, max_spread)

        # Volume check (use min_volume_24h if set, else min_volume_usd)
        effective_min_vol = min_volume_24h if min_volume_24h > 0 else min_volume
        if volume_usd > 0 and volume_usd < effective_min_vol:
            msg = f"Rejected {token_id[:8]}: volume={volume_usd:.2f} < {effective_min_vol}"
            if self.verbose_filters:
                self.logger.info(msg)
            else:
                self.logger.debug(msg)
            return False

        # Liquidity check (only if Gamma data available and filter set)
        if min_liquidity > 0 and liquidity > 0 and liquidity < min_liquidity:
            msg = f"Rejected {token_id[:8]}: liquidity={liquidity:.2f} < {min_liquidity}"
            if self.verbose_filters:
                self.logger.info(msg)
            else:
                self.logger.debug(msg)
            return False

        # Resolution date checks
        if days_to_resolve == 9999 and self.allow_missing_resolution:
            return True

        # CRITICAL: Reject markets resolving too soon (avoid resolved markets)
        if days_to_resolve < min_days:
            self.logger.info(
                f"Rejected {token_id[:8]}: resolves too soon (days={days_to_resolve} < {min_days})"
            )
            return False

        if days_to_resolve > max_days:
            msg = f"Rejected {token_id[:8]}: days={days_to_resolve} > {max_days}"
            if self.verbose_filters:
                self.logger.info(msg)
            else:
                self.logger.debug(msg)
            return False

        return True

    def _passes_price_filters(
        self, odds: float, spread_percent: float, token_id: str, days_to_resolve: int
    ) -> bool:
        """Apply filters that require orderbook data."""
        min_odds = self.filters.get("min_odds", 0.30)
        max_odds = self.filters.get("max_odds", 0.70)
        max_spread = self.filters.get("max_spread_percent", 5.0)

        if not (min_odds <= odds <= max_odds):
            msg = f"Rejected {token_id[:8]}: odds={odds:.2f} outside [{min_odds}, {max_odds}]"
            if self.verbose_filters:
                self.logger.info(msg)
            else:
                self.logger.debug(msg)
            return False
        if spread_percent > max_spread:
            msg = f"Rejected {token_id[:8]}: spread={spread_percent:.1f}% > {max_spread}"
            if self.verbose_filters:
                self.logger.info(msg)
            else:
                self.logger.debug(msg)
            return False
        return True

    def _select_market_source(self):
        """Select which API endpoint to use for market discovery."""
        source = str(self.market_source).lower()
        if source in ("markets", "full"):
            return self.client.get_markets
        if source in ("simplified", "markets_simplified"):
            return self.client.get_simplified_markets
        if source in ("sampling_simplified", "sampling-simplified"):
            return self.client.get_sampling_simplified_markets
        return self.client.get_sampling_markets

    def _get_best_prices(self, token_id: str) -> Tuple[float, float]:
        """Fetch orderbook and return best bid/ask prices."""
        try:
            order_book = self._call_api(self.client.get_order_book, token_id)
        except Exception as exc:
            msg = str(exc).lower()
            if "no orderbook exists" in msg or "404" in msg:
                return 0.0, 0.0
            raise
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

        # Best bid = highest bid price, best ask = lowest ask price
        best_bid = self._extract_best_bid(bids)
        best_ask = self._extract_best_ask(asks)
        return best_bid, best_ask

    def _extract_best_bid(self, orders: Any) -> float:
        """Extract the highest bid price from order list."""
        if not orders:
            return 0.0
        prices = []
        for order in orders:
            price = self._get_order_price(order)
            if price > 0:
                prices.append(price)
        return max(prices) if prices else 0.0

    def _extract_best_ask(self, orders: Any) -> float:
        """Extract the lowest ask price from order list."""
        if not orders:
            return 0.0
        prices = []
        for order in orders:
            price = self._get_order_price(order)
            if price > 0:
                prices.append(price)
        return min(prices) if prices else 0.0

    def _get_order_price(self, order: Any) -> float:
        """Extract price from an order object or dict."""
        if hasattr(order, "price"):
            try:
                return float(order.price)
            except (TypeError, ValueError):
                return 0.0
        if isinstance(order, dict) and "price" in order:
            try:
                return float(order["price"])
            except (TypeError, ValueError):
                return 0.0
        return 0.0

    def _spread_percent(self, bid: float, ask: float) -> float:
        """Calculate spread percent using mid price."""
        if bid <= 0 or ask <= 0 or ask <= bid:
            return 0.0
        mid = (bid + ask) / 2
        return ((ask - bid) / mid) * 100

    # ========================================================================
    # WALK THE BOOK (VWAP) - Slippage calculation
    # ========================================================================

    def walk_the_book(
        self, token_id: str, size: float, side: str = "buy"
    ) -> Tuple[float, float, float]:
        """
        Calculate VWAP (Volume Weighted Average Price) for a given order size.

        "Walks" through the orderbook to determine the actual average price
        you'd pay/receive when filling an order of the specified size.

        Args:
            token_id: Token to analyze
            size: Order size in shares
            side: "buy" (walk asks) or "sell" (walk bids)

        Returns:
            Tuple of (vwap, filled_size, slippage_percent)
            - vwap: Volume weighted average price
            - filled_size: How much of the order could be filled
            - slippage_percent: Slippage vs best price (0 = no slippage)
        """
        try:
            order_book = self._call_api(self.client.get_order_book, token_id)
        except Exception as exc:
            self.logger.warn(f"Failed to get orderbook for VWAP: {exc}")
            return 0.0, 0.0, 0.0

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

        if side == "buy":
            # Walking asks (lowest to highest)
            orders = self._parse_orders(asks, ascending=True)
            best_price = min(o[0] for o in orders) if orders else 0.0
        else:
            # Walking bids (highest to lowest)
            orders = self._parse_orders(bids, ascending=False)
            best_price = max(o[0] for o in orders) if orders else 0.0

        if not orders or best_price <= 0:
            return 0.0, 0.0, 0.0

        vwap, filled = self._calculate_vwap(orders, size)

        if vwap <= 0 or best_price <= 0:
            slippage = 0.0
        elif side == "buy":
            # For buys, slippage is how much more we pay vs best ask
            slippage = ((vwap - best_price) / best_price) * 100
        else:
            # For sells, slippage is how much less we receive vs best bid
            slippage = ((best_price - vwap) / best_price) * 100

        return vwap, filled, max(0.0, slippage)

    def _parse_orders(self, orders: Any, ascending: bool = True) -> List[Tuple[float, float]]:
        """
        Parse orderbook orders into (price, size) tuples.

        Args:
            orders: Raw orders from API
            ascending: Sort by price ascending (for asks) or descending (for bids)

        Returns:
            List of (price, size) tuples sorted appropriately
        """
        parsed = []
        for order in orders:
            price = self._get_order_price(order)
            size = self._get_order_size(order)
            if price > 0 and size > 0:
                parsed.append((price, size))

        # Sort: asks ascending (best = lowest), bids descending (best = highest)
        parsed.sort(key=lambda x: x[0], reverse=not ascending)
        return parsed

    def _get_order_size(self, order: Any) -> float:
        """Extract size from an order object or dict."""
        if hasattr(order, "size"):
            try:
                return float(order.size)
            except (TypeError, ValueError):
                return 0.0
        if isinstance(order, dict) and "size" in order:
            try:
                return float(order["size"])
            except (TypeError, ValueError):
                return 0.0
        return 0.0

    def _calculate_vwap(
        self, orders: List[Tuple[float, float]], target_size: float
    ) -> Tuple[float, float]:
        """
        Calculate Volume Weighted Average Price by walking through orders.

        Args:
            orders: List of (price, size) tuples, sorted by price
            target_size: Target order size to fill

        Returns:
            Tuple of (vwap, filled_size)
        """
        if not orders or target_size <= 0:
            return 0.0, 0.0

        filled = 0.0
        total_cost = 0.0

        for price, available_size in orders:
            take = min(available_size, target_size - filled)
            total_cost += take * price
            filled += take

            if filled >= target_size:
                break

        if filled <= 0:
            return 0.0, 0.0

        vwap = total_cost / filled
        return round(vwap, 6), round(filled, 6)

    def get_orderbook_depth(self, token_id: str) -> Dict[str, Any]:
        """
        Get full orderbook depth analysis for a token.

        Returns:
            Dict with bid/ask depth, total liquidity, and price levels
        """
        try:
            order_book = self._call_api(self.client.get_order_book, token_id)
        except Exception as exc:
            self.logger.warn(f"Failed to get orderbook depth: {exc}")
            return {"error": str(exc)}

        bids = getattr(order_book, "bids", []) or []
        asks = getattr(order_book, "asks", []) or []

        if hasattr(order_book, "to_dict"):
            book_dict = order_book.to_dict()
            bids = book_dict.get("bids", [])
            asks = book_dict.get("asks", [])

        bid_orders = self._parse_orders(bids, ascending=False)
        ask_orders = self._parse_orders(asks, ascending=True)

        total_bid_size = sum(size for _, size in bid_orders)
        total_ask_size = sum(size for _, size in ask_orders)
        total_bid_value = sum(price * size for price, size in bid_orders)
        total_ask_value = sum(price * size for price, size in ask_orders)

        return {
            "token_id": token_id,
            "bid_levels": len(bid_orders),
            "ask_levels": len(ask_orders),
            "total_bid_size": round(total_bid_size, 2),
            "total_ask_size": round(total_ask_size, 2),
            "total_bid_value_usd": round(total_bid_value, 2),
            "total_ask_value_usd": round(total_ask_value, 2),
            "best_bid": bid_orders[0][0] if bid_orders else 0.0,
            "best_ask": ask_orders[0][0] if ask_orders else 0.0,
            "imbalance": round(
                (total_bid_size - total_ask_size) / max(total_bid_size + total_ask_size, 1), 2
            ),
        }

    def _extract_token_candidates(self, market: Dict[str, Any]) -> List[str]:
        """Extract candidate token IDs from market data."""
        token_ids: List[str] = []

        tokens = market.get("tokens") or []
        if isinstance(tokens, dict):
            tokens = list(tokens.values())

        if isinstance(tokens, list):
            token_keys = ("clob_token_id", "clobTokenId", "token_id", "tokenId")
            # Prefer YES outcome when present
            for token in tokens:
                outcome = (token.get("outcome") or token.get("name") or "").lower()
                if outcome in ("yes", "true"):
                    token_id = self._first_key(token, token_keys)
                    if token_id and self._is_valid_token_id(str(token_id)):
                        token_ids.append(str(token_id))
            if tokens:
                token = tokens[0]
                token_id = self._first_key(token, token_keys)
                if token_id and self._is_valid_token_id(str(token_id)):
                    token_ids.append(str(token_id))

        # Fallback to top-level token_id only if tokens list is missing
        if not token_ids:
            for key in ("clob_token_id", "clobTokenId", "token_id", "tokenId"):
                if key in market:
                    value = str(market[key])
                    if self._is_valid_token_id(value):
                        token_ids.append(value)

        condition_id = market.get("condition_id") or market.get("conditionId")
        if condition_id and self._detail_fetch_count < self.max_detail_fetch:
            self._detail_fetch_count += 1
            try:
                detail = self._call_api(self.client.get_market, condition_id)
            except Exception as exc:
                self.logger.debug(
                    f"Detail fetch failed for {condition_id}: {exc}"
                )
                detail = None
            if isinstance(detail, dict):
                detail_tokens = detail.get("tokens") or []
                if isinstance(detail_tokens, list):
                    token_keys = (
                        "clob_token_id",
                        "clobTokenId",
                        "token_id",
                        "tokenId",
                    )
                    for token in detail_tokens:
                        outcome = (token.get("outcome") or token.get("name") or "").lower()
                        if outcome in ("yes", "true"):
                            token_id = self._first_key(token, token_keys)
                            if token_id and self._is_valid_token_id(str(token_id)):
                                token_ids.append(str(token_id))
                    if detail_tokens:
                        token_id = self._first_key(detail_tokens[0], token_keys)
                        if token_id and self._is_valid_token_id(str(token_id)):
                            token_ids.append(str(token_id))

        # De-duplicate while preserving order
        seen = set()
        unique_ids = []
        for token_id in token_ids:
            if token_id not in seen:
                seen.add(token_id)
                unique_ids.append(token_id)
        return unique_ids

    def _is_valid_token_id(self, value: str) -> bool:
        """Heuristic check for CLOB token IDs."""
        if not value:
            return False
        # CLOB token IDs are large integers; filter out small IDs.
        if value.isdigit() and len(value) < 20:
            return False
        return True

    def _first_key(self, data: Dict[str, Any], keys: Tuple[str, ...]) -> Optional[Any]:
        """Return the first available key value from a dict."""
        for key in keys:
            if key in data and data[key]:
                return data[key]
        return None

    def _fetch_gamma_markets(self, max_markets: int) -> List[Dict[str, Any]]:
        """Fetch markets from Gamma API as primary source."""
        self.logger.info("Fetching markets from Gamma API (primary source)...")
        try:
            min_vol = self.filters.get("min_volume_24h", 0)
            min_liq = self.filters.get("min_liquidity", 0)

            gamma_markets = self.gamma_client.get_top_volume_markets(
                min_volume_24h=min_vol,
                min_liquidity=min_liq,
                limit=max_markets * 2,  # Fetch more, some will be filtered
            )

            # Convert Gamma format to scanner format
            markets = []
            for gm in gamma_markets[:max_markets]:
                # Build token list from clob_token_ids
                tokens = []
                for i, token_id in enumerate(gm.get("clob_token_ids", [])):
                    tokens.append({
                        "token_id": str(token_id),
                        "outcome": "Yes" if i == 0 else "No",
                    })

                markets.append({
                    "condition_id": gm.get("condition_id"),
                    "question": gm.get("question"),
                    "tokens": tokens,
                    "end_date_iso": gm.get("end_date"),
                    "active": gm.get("active", True),
                    "closed": gm.get("closed", False),
                    # Include Gamma volume data directly
                    "volume_24h": gm.get("volume_24h", 0),
                    "volume_usd": gm.get("volume_total", 0),
                    "liquidity": gm.get("liquidity", 0),
                    "_gamma_data": gm,  # Keep full Gamma data for reference
                })

            self.logger.info(f"Gamma returned {len(markets)} markets with volume data")
            return markets

        except Exception as exc:
            self.logger.warn(f"Gamma market fetch failed: {exc}")
            return []

    def _prefetch_gamma_data(self) -> None:
        """Pre-fetch Gamma API data for volume enrichment."""
        if not self.gamma_client:
            return

        try:
            min_vol = self.filters.get("min_volume_24h", 0)
            min_liq = self.filters.get("min_liquidity", 0)

            gamma_markets = self.gamma_client.get_top_volume_markets(
                min_volume_24h=min_vol,
                min_liquidity=min_liq,
                limit=100,
            )

            self._gamma_cache.clear()
            for gm in gamma_markets:
                condition_id = gm.get("condition_id")
                if condition_id:
                    self._gamma_cache[condition_id] = gm
                # Also index by token IDs for direct lookup
                for token_id in gm.get("clob_token_ids", []):
                    if token_id:
                        self._gamma_cache[f"token:{token_id}"] = gm

            self.logger.info(
                f"Gamma cache loaded: {len(gamma_markets)} markets with volume data"
            )
        except Exception as exc:
            self.logger.warn(f"Gamma prefetch failed: {exc}")

    def _get_gamma_data(self, market: Dict[str, Any]) -> Optional[Dict]:
        """Look up Gamma data for a market."""
        if not self._gamma_cache:
            return None

        # Try condition_id first
        condition_id = market.get("condition_id") or market.get("conditionId")
        if condition_id and condition_id in self._gamma_cache:
            return self._gamma_cache[condition_id]

        # Try token IDs
        token_candidates = self._extract_token_candidates(market)
        for token_id in token_candidates:
            cache_key = f"token:{token_id}"
            if cache_key in self._gamma_cache:
                return self._gamma_cache[cache_key]

        return None

    def _extract_volume_usd(self, market: Dict[str, Any]) -> float:
        """Extract volume in USD from market data, preferring Gamma API data."""
        # Check for direct Gamma data embedded in market (from _fetch_gamma_markets)
        if "volume_24h" in market and market["volume_24h"] > 0:
            return self._safe_float(market["volume_24h"])

        # Try Gamma cache lookup (for CLOB-sourced markets)
        gamma_data = self._get_gamma_data(market)
        if gamma_data:
            vol_24h = gamma_data.get("volume_24h", 0)
            if vol_24h > 0:
                return vol_24h

        # Fallback to CLOB API data
        volume_keys = [
            "volume_usd",
            "volumeUSD",
            "volume",
            "volume24h",
            "volume24h_usd",
        ]
        for key in volume_keys:
            if key in market:
                return self._safe_float(market[key])
        return 0.0

    def _extract_liquidity(self, market: Dict[str, Any]) -> float:
        """Extract liquidity from Gamma API data."""
        # Check for direct Gamma data embedded in market
        if "liquidity" in market and market["liquidity"] > 0:
            return self._safe_float(market["liquidity"])

        # Try Gamma cache lookup
        gamma_data = self._get_gamma_data(market)
        if gamma_data:
            return gamma_data.get("liquidity", 0.0)
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

    def _is_closed(self, market: Dict[str, Any]) -> Tuple[bool, str]:
        """Detect closed/resolved markets."""
        status = str(market.get("status", "")).lower()
        if status in ("closed", "resolved", "settled", "finalized"):
            return True, "closed_status"

        # Check explicit closed flag
        closed = market.get("closed")
        if closed is True:
            return True, "closed_flag"

        # Check active flag
        active = market.get("active")
        active_normalized = active
        if isinstance(active, str):
            active_normalized = active.strip().lower()
            if active_normalized in ("true", "1", "yes"):
                active_normalized = True
            elif active_normalized in ("false", "0", "no"):
                active_normalized = False

        # Market is closed if both closed=True and active=False
        if closed is True and active_normalized is False:
            return True, "closed_flag"

        # Treat inactive markets as closed (configurable)
        if self.treat_inactive_as_closed and active_normalized is False:
            return True, "inactive_flag"

        # CRITICAL: Check if market is past its resolution date
        # This catches markets that resolved but aren't marked as closed yet
        days_to_resolve = self._days_to_resolve(market)
        if days_to_resolve < 0:  # Negative = past resolution date
            self.logger.info(
                f"Rejected market: past resolution date (days={days_to_resolve})"
            )
            return True, "closed_status"

        return False, "ok"

    def _log_market_status(self, market: Dict[str, Any]) -> None:
        """Log a short sample of market status fields (debug aid)."""
        status = market.get("status")
        active = market.get("active")
        closed = market.get("closed")
        condition_id = market.get("condition_id") or market.get("conditionId")
        self.logger.debug(
            f"Market status sample: status={status} active={active} closed={closed} "
            f"condition_id={condition_id}"
        )

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
        now = time.monotonic()
        elapsed = now - self._last_call_ts
        if elapsed < self.min_call_interval:
            delay = self.min_call_interval - elapsed
            self.logger.debug(f"Rate limit sleep: {delay:.2f}s")
            time.sleep(delay)
        self._last_call_ts = time.monotonic()
