"""
WebSocket-based position monitoring.

Provides async version of position monitoring using WebSocket instead of polling.
Reduces latency from 10s to <100ms.
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional

from bot.position_manager import Position, PositionManager
from bot.strategy import TradingStrategy
from bot.trader import BotTrader
from bot.websocket_client import OrderbookSnapshot, PolymarketWebSocket


async def monitor_positions_websocket(
    ws: PolymarketWebSocket,
    position_manager: PositionManager,
    trader: BotTrader,
    strategy: TradingStrategy,
    blacklist_cfg: dict,
    logger,
):
    """
    Monitor positions using WebSocket for instant price updates.

    This replaces polling with real-time callbacks, reducing latency from 10s to <100ms.

    Args:
        ws: Connected WebSocket client
        position_manager: Position manager instance
        trader: Bot trader instance
        strategy: Trading strategy instance
        blacklist_cfg: Blacklist configuration
        logger: Logger instance
    """

    # Get all open positions
    positions = position_manager.get_all_positions()
    if not positions:
        logger.debug("No positions to monitor via WebSocket")
        return

    # Subscribe to all position tokens
    token_ids = [pos.token_id for pos in positions]
    await ws.subscribe(token_ids)

    logger.info(f"Monitoring {len(positions)} positions via WebSocket")

    # Register callback for orderbook updates
    @ws.on_book_update
    async def on_price_update(snapshot: OrderbookSnapshot):
        """Handle real-time price updates."""
        position = position_manager.get_position(snapshot.token_id)
        if not position:
            # Position no longer exists, unsubscribe
            await ws.unsubscribe([snapshot.token_id])
            return

        # Route to appropriate handler
        if position.exit_mode == "limit_orders":
            await _check_limit_order_fills(
                position, trader, position_manager, strategy, blacklist_cfg, logger
            )
        else:
            await _check_tp_sl_websocket(
                position, snapshot, trader, position_manager, strategy, blacklist_cfg, logger
            )


async def _check_limit_order_fills(
    position: Position,
    trader: BotTrader,
    position_manager: PositionManager,
    strategy: TradingStrategy,
    blacklist_cfg: dict,
    logger,
):
    """Check if limit orders (TP/SL) have filled."""
    # This is the same logic from main_bot.py _update_position_with_limit_orders
    # but async-safe

    tp_status = trader.check_order_status(position.tp_order_id)
    sl_status = trader.check_order_status(position.sl_order_id)

    # TP filled
    if tp_status['status'] in ('filled', 'partial'):
        logger.info(
            f"TAKE PROFIT filled for {position.token_id[:8]}... "
            f"@ {tp_status['avg_price']:.4f}"
        )

        trader.cancel_order(position.sl_order_id)

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

        trader.cancel_order(position.tp_order_id)

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


async def _check_tp_sl_websocket(
    position: Position,
    snapshot: OrderbookSnapshot,
    trader: BotTrader,
    position_manager: PositionManager,
    strategy: TradingStrategy,
    blacklist_cfg: dict,
    logger,
):
    """Check TP/SL using WebSocket snapshot (legacy monitoring mode)."""
    best_bid = snapshot.best_bid

    if best_bid <= 0:
        logger.debug(f"No bids for {position.token_id[:8]}..., skipping")
        return

    action = None
    if best_bid >= position.tp:
        action = "take_profit"
    elif best_bid <= position.sl:
        action = "stop_loss"

    if not action:
        logger.debug(
            f"Position {position.token_id[:8]}... price={best_bid:.4f} "
            f"tp={position.tp:.4f} sl={position.sl:.4f}"
        )
        return

    logger.info(f"{action.upper()} for {position.token_id[:8]}... bid={best_bid:.4f}")

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


async def update_websocket_subscriptions(
    ws: PolymarketWebSocket, position_manager: PositionManager, logger
):
    """
    Update WebSocket subscriptions to match current positions.

    Call this after opening/closing positions to ensure WebSocket is subscribed
    to all active positions and unsubscribed from closed ones.

    Args:
        ws: WebSocket client
        position_manager: Position manager instance
        logger: Logger instance
    """
    current_positions = {pos.token_id for pos in position_manager.get_all_positions()}
    current_subscriptions = set(ws.subscribed_tokens)

    # Tokens to subscribe (new positions)
    to_subscribe = list(current_positions - current_subscriptions)
    if to_subscribe:
        await ws.subscribe(to_subscribe)
        logger.debug(f"Subscribed to {len(to_subscribe)} new positions")

    # Tokens to unsubscribe (closed positions)
    to_unsubscribe = list(current_subscriptions - current_positions)
    if to_unsubscribe:
        await ws.unsubscribe(to_unsubscribe)
        logger.debug(f"Unsubscribed from {len(to_unsubscribe)} closed positions")
