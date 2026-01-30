#!/usr/bin/env python3
"""
Main loop for the Polymarket autonomous trading bot.
"""

import argparse
import os
import time
from datetime import datetime, timezone
from typing import Optional, Tuple

from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, BalanceAllowanceParams, AssetType

from bot.config import load_bot_config
from bot.logger import get_logger
from bot.market_scanner import MarketScanner
from bot.position_manager import Position, PositionManager
from bot.strategy import TradingStrategy
from bot.trader import BotTrader, TradeFill


def _best_bid_ask(order_book) -> Tuple[float, float]:
    """Extract best bid and ask from an order book object."""
    bids = getattr(order_book, "bids", None)
    asks = getattr(order_book, "asks", None)
    if (bids is None or asks is None) and hasattr(order_book, "to_dict"):
        book_dict = order_book.to_dict()
        bids = book_dict.get("bids", [])
        asks = book_dict.get("asks", [])

    best_bid = _extract_best_bid(bids)
    best_ask = _extract_best_ask(asks)
    return best_bid, best_ask


def _extract_best_bid(orders, default: float = 0.0) -> float:
    """Extract highest bid price (bids are sorted ascending, so best is last or max)."""
    if not orders:
        return default
    prices = []
    for order in orders:
        if hasattr(order, "price"):
            prices.append(float(order.price))
        elif isinstance(order, dict) and "price" in order:
            prices.append(float(order["price"]))
    return max(prices) if prices else default


def _extract_best_ask(orders, default: float = 0.0) -> float:
    """Extract lowest ask price (asks may be sorted descending, so best is min)."""
    if not orders:
        return default
    prices = []
    for order in orders:
        if hasattr(order, "price"):
            prices.append(float(order.price))
        elif isinstance(order, dict) and "price" in order:
            prices.append(float(order["price"]))
    return min(prices) if prices else default


def _derive_funder(private_key: str) -> Optional[str]:
    """Derive wallet address from private key for EOA usage."""
    try:
        from eth_account import Account
    except ImportError as exc:
        raise RuntimeError(
            "eth_account is required to derive wallet address for EOA wallets."
        ) from exc
    return Account.from_key(private_key).address


def _fetch_balance(client, logger) -> Optional[float]:
    """Attempt to fetch collateral balance; returns None if unavailable."""
    try:
        balance = client.get_balance_allowance(
            params=BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
        )
        if hasattr(balance, "balance"):
            return float(balance.balance)
        if isinstance(balance, dict):
            for key in ("balance", "available", "allowance", "collateral"):
                if key in balance:
                    return float(balance[key])
    except Exception as exc:
        logger.warn(f"Balance fetch failed, using config capital: {exc}")
    return None


def _init_client(logger):
    """Initialize ClobClient from .env."""
    load_dotenv()

    host = "https://clob.polymarket.com"
    chain_id = 137
    private_key = os.getenv("POLY_PRIVATE_KEY")
    api_key = os.getenv("POLY_API_KEY")
    api_secret = os.getenv("POLY_API_SECRET")
    api_passphrase = os.getenv("POLY_API_PASSPHRASE")
    funder = os.getenv("POLY_FUNDER_ADDRESS")

    if not private_key or not api_key or not api_secret or not api_passphrase:
        raise RuntimeError("Missing required POLY_* credentials in .env")

    private_key = private_key.strip()
    api_key = api_key.strip()
    api_secret = api_secret.strip()
    api_passphrase = api_passphrase.strip()
    funder = funder.strip() if funder else None

    sig_type = 1 if funder else 0
    if not funder:
        funder = _derive_funder(private_key)

    creds = ApiCreds(
        api_key=api_key,
        api_secret=api_secret,
        api_passphrase=api_passphrase,
    )

    logger.info(f"Initializing CLOB client (sig_type={sig_type})")
    client = ClobClient(
        host=host,
        chain_id=chain_id,
        key=private_key,
        creds=creds,
        signature_type=sig_type,
        funder=funder,
    )
    return client


def _update_positions(
    client,
    logger,
    position_manager: PositionManager,
    trader: BotTrader,
    strategy: TradingStrategy,
    blacklist_cfg: dict,
):
    """Check open positions for TP/SL conditions (supports both modes)."""
    positions = position_manager.get_all_positions()
    if not positions:
        return

    for position in positions:
        # Route to appropriate handler based on exit_mode
        if position.exit_mode == "limit_orders":
            _update_position_with_limit_orders(
                position, logger, trader, position_manager, strategy, blacklist_cfg
            )
        else:
            _update_position_legacy_monitoring(
                position, client, logger, trader, position_manager, strategy, blacklist_cfg
            )


def _update_position_with_limit_orders(
    position: Position,
    logger,
    trader: BotTrader,
    position_manager: PositionManager,
    strategy: TradingStrategy,
    blacklist_cfg: dict,
):
    """Monitor limit order fills for TP/SL."""
    # Check TP order status
    tp_status = trader.check_order_status(position.tp_order_id)
    sl_status = trader.check_order_status(position.sl_order_id)

    # TP filled
    if tp_status['status'] in ('filled', 'partial'):
        logger.info(
            f"TAKE PROFIT filled for {position.token_id[:8]}... "
            f"@ {tp_status['avg_price']:.4f}"
        )

        # Cancel SL order
        trader.cancel_order(position.sl_order_id)

        # Record trade
        exit_time = datetime.now(timezone.utc).isoformat()
        odds_range = strategy.get_odds_range(position.entry_price)
        position_manager.record_trade(
            entry_price=position.entry_price,
            exit_price=tp_status['avg_price'],
            size=tp_status['filled_size'],
            fees=tp_status['fees'],
            entry_time=position.entry_time,
            exit_time=exit_time,
            odds_range=odds_range,
        )

        position_manager.remove_position(position.token_id)
        logger.info(
            f"Position closed (TP) {position.token_id[:8]}... "
            f"size={tp_status['filled_size']} @ {tp_status['avg_price']:.4f}"
        )
        return

    # SL filled
    if sl_status['status'] in ('filled', 'partial'):
        logger.info(
            f"STOP LOSS filled for {position.token_id[:8]}... "
            f"@ {sl_status['avg_price']:.4f}"
        )

        # Cancel TP order
        trader.cancel_order(position.tp_order_id)

        # Record trade
        exit_time = datetime.now(timezone.utc).isoformat()
        odds_range = strategy.get_odds_range(position.entry_price)
        position_manager.record_trade(
            entry_price=position.entry_price,
            exit_price=sl_status['avg_price'],
            size=sl_status['filled_size'],
            fees=sl_status['fees'],
            entry_time=position.entry_time,
            exit_time=exit_time,
            odds_range=odds_range,
        )

        # Blacklist after SL
        duration = blacklist_cfg.get("duration_days", 3)
        max_attempts = blacklist_cfg.get("max_attempts", 2)
        position_manager.add_to_blacklist(
            position.token_id, "stop_loss", duration, max_attempts
        )

        position_manager.remove_position(position.token_id)
        logger.info(
            f"Position closed (SL) {position.token_id[:8]}... "
            f"size={sl_status['filled_size']} @ {sl_status['avg_price']:.4f}"
        )
        return

    # Both orders still open (normal case)
    logger.debug(
        f"Position {position.token_id[:8]}... "
        f"TP={tp_status['status']} SL={sl_status['status']}"
    )


def _update_position_legacy_monitoring(
    position: Position,
    client,
    logger,
    trader: BotTrader,
    position_manager: PositionManager,
    strategy: TradingStrategy,
    blacklist_cfg: dict,
):
    """Legacy monitoring mode: check orderbook prices and execute market sells."""
    try:
        book = client.get_order_book(position.token_id)
        best_bid, best_ask = _best_bid_ask(book)
    except Exception as exc:
        logger.warn(f"Orderbook error for {position.token_id[:8]}...: {exc}")
        return

    if best_bid <= 0:
        logger.warn(f"No bids for {position.token_id[:8]}..., skipping.")
        return

    action = None
    if best_bid >= position.tp:
        action = "take_profit"
    elif best_bid <= position.sl:
        action = "stop_loss"

    if not action:
        logger.info(
            f"Position {position.token_id[:8]}... price={best_bid:.4f} "
            f"tp={position.tp:.4f} sl={position.sl:.4f}"
        )
        return

    logger.info(
        f"{action.upper()} for {position.token_id[:8]}... "
        f"bid={best_bid:.4f}"
    )

    try:
        fill = trader.execute_sell(
            token_id=position.token_id,
            price=best_bid,
            size=position.filled_size,
            entry_price=position.entry_price,
            is_emergency_exit=action == "stop_loss",
        )
    except Exception as exc:
        logger.error(f"Sell failed for {position.token_id[:8]}...: {exc}")
        return

    exit_time = datetime.now(timezone.utc).isoformat()
    odds_range = strategy.get_odds_range(position.entry_price)
    position_manager.record_trade(
        entry_price=position.entry_price,
        exit_price=fill.avg_price,
        size=fill.filled_size,
        fees=fill.fees_paid,
        entry_time=position.entry_time,
        exit_time=exit_time,
        odds_range=odds_range,
    )

    if action == "stop_loss":
        duration = blacklist_cfg.get("duration_days", 3)
        max_attempts = blacklist_cfg.get("max_attempts", 2)
        position_manager.add_to_blacklist(
            position.token_id, "stop_loss", duration, max_attempts
        )

    position_manager.remove_position(position.token_id)
    logger.info(
        f"Position closed {position.token_id[:8]}... "
        f"size={fill.filled_size} @ {fill.avg_price:.4f}"
    )


def _can_open_new_position(
    logger,
    position_manager: PositionManager,
    config,
    last_buy_ts: float,
) -> Tuple[bool, str]:
    """Check risk constraints before opening a new trade."""
    max_positions = config.get("risk.max_positions", 5)
    cooldown = config.get("risk.cooldown_seconds", 300)
    daily_loss_limit = config.get("risk.daily_loss_limit", 3.0)

    if position_manager.position_count() >= max_positions:
        return False, "max_positions reached"

    if time.time() - last_buy_ts < cooldown:
        return False, "cooldown active"

    daily_pnl = position_manager.get_daily_pnl()
    if daily_pnl <= -abs(daily_loss_limit):
        return False, "daily loss limit reached"

    return True, "ok"


def _place_new_trade(
    client,
    logger,
    scanner: MarketScanner,
    trader: BotTrader,
    position_manager: PositionManager,
    strategy: TradingStrategy,
    config,
) -> Optional[TradeFill]:
    """Scan markets and place a new trade if a candidate exists."""
    candidate = scanner.pick_best_candidate()
    if not candidate:
        logger.info("No suitable market candidate found.")
        return None

    price = candidate["best_ask"]
    available_capital = _calculate_available_capital(config, position_manager, client, logger)
    max_trade_size = config.get("capital.max_trade_size", 1.0)
    max_positions = config.get("risk.max_positions", 5)

    size_usd = strategy.calculate_position_size(
        available_capital,
        max_trade_size,
        position_manager.position_count(),
        max_positions,
    )
    if size_usd <= 0:
        logger.info("No available capital for new trade.")
        return None

    size_shares = round(size_usd / price, 4)
    if size_shares <= 0:
        logger.info("Calculated size too small; skipping trade.")
        return None

    tp, sl = strategy.calculate_tp_sl(price)
    logger.info(
        f"New candidate score={candidate['score']} odds={candidate['odds']} "
        f"spread={candidate['spread_percent']}% volume={candidate['volume_usd']}"
    )

    # Check if concurrent orders are enabled
    use_concurrent = config.get("trading.use_concurrent_orders", False)

    if use_concurrent:
        logger.info(
            f"Placing BUY {size_shares} @ {price:.4f} with concurrent TP/SL "
            f"(TP={tp:.4f} SL={sl:.4f})"
        )

        # Execute buy with concurrent limit orders for TP/SL
        result = trader.execute_buy_with_exits(
            token_id=candidate["token_id"],
            entry_price=price,
            size=size_shares,
            tp_price=tp,
            sl_price=sl,
        )

        fill = result['buy_fill']
        entry_time = datetime.now(timezone.utc).isoformat()
        position = Position(
            token_id=candidate["token_id"],
            entry_price=fill.avg_price,
            size=size_shares,
            filled_size=fill.filled_size,
            entry_time=entry_time,
            tp=tp,
            sl=sl,
            fees_paid=fill.fees_paid,
            order_id=fill.order_id,
            # Concurrent order fields
            tp_order_id=result['tp_order_id'],
            sl_order_id=result['sl_order_id'],
            exit_mode="limit_orders" if result['tp_order_id'] else "monitor",
        )

        position_manager.add_position(position)

        if result['tp_order_id']:
            logger.info(
                f"Position opened with limit orders: "
                f"size={fill.filled_size} @ {fill.avg_price:.4f} "
                f"TP={result['tp_order_id'][:8]}... SL={result['sl_order_id'][:8]}..."
            )
        else:
            logger.warn(
                f"Limit orders failed, using legacy monitoring for {candidate['token_id'][:8]}..."
            )
    else:
        logger.info(
            f"Placing BUY {size_shares} @ {price:.4f} "
            f"TP={tp:.4f} SL={sl:.4f}"
        )

        # Legacy mode: market buy + monitoring
        fill = trader.execute_buy(
            token_id=candidate["token_id"],
            price=price,
            size=size_shares,
        )

        entry_time = datetime.now(timezone.utc).isoformat()
        position = Position(
            token_id=candidate["token_id"],
            entry_price=fill.avg_price,
            size=size_shares,
            filled_size=fill.filled_size,
            entry_time=entry_time,
            tp=tp,
            sl=sl,
            fees_paid=fill.fees_paid,
            order_id=fill.order_id,
            exit_mode="monitor",
        )
        position_manager.add_position(position)
        logger.info(
            f"Position opened {candidate['token_id'][:8]}... "
            f"size={fill.filled_size} @ {fill.avg_price:.4f}"
        )

    return fill


def _calculate_available_capital(config, position_manager, client, logger) -> float:
    """Compute available capital considering safety reserve and open positions."""
    total = config.get("capital.total", 0.0)
    safety = config.get("capital.safety_reserve", 0.0)
    committed = sum(
        pos.filled_size * pos.entry_price for pos in position_manager.get_all_positions()
    )
    available = max(0.0, total - safety - committed)

    real_balance = _fetch_balance(client, logger)
    if real_balance is not None:
        available = min(available, real_balance - safety)

    return max(0.0, available)


def run_loop():
    parser = argparse.ArgumentParser(description="Polymarket Autonomous Bot")
    parser.add_argument("--once", action="store_true", help="Run a single loop")
    args = parser.parse_args()

    config = load_bot_config()
    logger = get_logger("PolyBot", config.log_level)

    client = _init_client(logger)
    position_manager = PositionManager()
    strategy = TradingStrategy(config)
    scanner = MarketScanner(client, config, logger, position_manager, strategy)
    trader = BotTrader(client, config, logger)

    scan_interval = config.get("bot.loop_interval_seconds", 120)
    position_check_interval = config.get("bot.position_check_interval_seconds", 10)
    blacklist_cfg = config.get("blacklist", {})

    last_buy_ts = 0.0
    last_scan_ts = 0.0

    logger.section("BOT STARTED")

    while True:
        logger.info("Loop start")
        position_manager.clean_blacklist()

        _update_positions(
            client,
            logger,
            position_manager,
            trader,
            strategy,
            blacklist_cfg,
        )

        now = time.time()
        time_since_scan = now - last_scan_ts
        can_trade, reason = _can_open_new_position(
            logger, position_manager, config, last_buy_ts
        )

        should_scan = can_trade and time_since_scan >= scan_interval

        if not can_trade:
            logger.info(f"Skipping new trade: {reason}")
        elif not should_scan:
            logger.info(f"Waiting for scan interval ({int(scan_interval - time_since_scan)}s remaining)")
        else:
            fill = _place_new_trade(
                client,
                logger,
                scanner,
                trader,
                position_manager,
                strategy,
                config,
            )
            last_scan_ts = time.time()
            if fill:
                last_buy_ts = time.time()

        if args.once:
            break

        logger.info(f"Checking positions in {position_check_interval}s")
        time.sleep(position_check_interval)


if __name__ == "__main__":
    run_loop()
