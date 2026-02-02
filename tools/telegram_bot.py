#!/usr/bin/env python3
"""
Telegram bot with command support for Polymarket bot.

Listens for commands and executes actions:
  /status    - Show bot status
  /positions - List current positions
  /simulate  - Run TP/SL simulation
  /summary   - Send daily summary
  /balance   - Check account balance
  /help      - Show available commands

Usage:
    python tools/telegram_bot.py
"""

import json
import os
import sys
import time
import subprocess
from datetime import datetime
from html import escape as html_escape
from pathlib import Path
from typing import Optional, Tuple
import urllib.request
import urllib.parse

from dotenv import load_dotenv
from py_clob_client.client import ClobClient
from py_clob_client.clob_types import ApiCreds, BalanceAllowanceParams, AssetType

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class TelegramCommandBot:
    """Telegram bot that listens for commands and executes actions."""

    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.last_update_id = 0
        self.running = True
        self.project_dir = Path(__file__).parent.parent
        self.market_cache_path = self.project_dir / "data" / "market_cache.json"
        self.market_cache_ttl = 24 * 60 * 60

    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """Send a message to the configured chat."""
        try:
            url = f"{self.base_url}/sendMessage"
            data = urllib.parse.urlencode({
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
            }).encode()

            req = urllib.request.Request(url, data=data)
            with urllib.request.urlopen(req, timeout=10) as response:
                result = json.loads(response.read())
                return result.get("ok", False)

        except Exception as e:
            print(f"Send error: {e}")
            return False

    def get_updates(self, timeout: int = 30) -> list:
        """Get new messages via long polling."""
        try:
            url = f"{self.base_url}/getUpdates"
            params = {
                "timeout": timeout,
                "offset": self.last_update_id + 1,
            }
            url_with_params = f"{url}?{urllib.parse.urlencode(params)}"

            req = urllib.request.Request(url_with_params)
            with urllib.request.urlopen(req, timeout=timeout + 10) as response:
                result = json.loads(response.read())
                if result.get("ok"):
                    return result.get("result", [])
                return []

        except Exception as e:
            print(f"Poll error: {e}")
            return []

    def process_command(self, text: str, from_user: str) -> str:
        """Process a command and return response."""
        text = text.strip().lower()

        # Extract command (remove @botname if present)
        if "@" in text:
            text = text.split("@")[0]

        if text == "/start" or text == "/help":
            return self.cmd_help()
        elif text == "/status":
            return self.cmd_status()
        elif text == "/positions" or text == "/pos":
            return self.cmd_positions()
        elif text == "/simulate" or text == "/sim":
            return self.cmd_simulate()
        elif text == "/summary":
            return self.cmd_summary()
        elif text == "/balance" or text == "/bal":
            return self.cmd_balance()
        elif text == "/logs":
            return self.cmd_logs()
        elif text == "/stop":
            return self.cmd_stop()
        elif text == "/whales":
            return self.cmd_whales()
        else:
            return f"❓ Comando desconocido: {text}\n\nUsa /help para ver comandos disponibles."

    def cmd_help(self) -> str:
        """Show available commands."""
        return """🤖 <b>Polymarket Bot Commands</b>

<b>Información:</b>
/status - Estado del bot
/positions - Posiciones abiertas
/balance - Balance de cuenta
/logs - Últimas líneas del log
/whales - Estado Copy Trading 🐳

<b>Acciones:</b>
/simulate - Ejecutar simulación TP/SL
/summary - Resumen del día

<b>Control:</b>
/stop - Detener el bot (requiere confirmación)
/help - Mostrar esta ayuda"""

    def _create_clob_client(self) -> Tuple[Optional[ClobClient], Optional[str]]:
        """Create authenticated CLOB client for balance checks."""
        load_dotenv()

        host = "https://clob.polymarket.com"
        chain_id = 137

        private_key = os.getenv("POLY_PRIVATE_KEY", "").strip()
        if not private_key or not private_key.startswith("0x"):
            return None, "POLY_PRIVATE_KEY no configurada o inválida"

        funder = os.getenv("POLY_FUNDER_ADDRESS", "").strip() or None
        api_key = os.getenv("POLY_API_KEY", "").strip()
        api_secret = os.getenv("POLY_API_SECRET", "").strip()
        api_passphrase = os.getenv("POLY_API_PASSPHRASE", "").strip()

        sig_type = 1 if funder else 0
        client = ClobClient(
            host=host,
            key=private_key,
            chain_id=chain_id,
            funder=funder,
            signature_type=sig_type,
        )

        if api_key and api_secret and api_passphrase:
            client.set_api_creds(ApiCreds(
                api_key=api_key,
                api_secret=api_secret,
                api_passphrase=api_passphrase,
            ))

        return client, None

    def cmd_status(self) -> str:
        """Get bot status."""
        # Check if main bot is running
        try:
            result = subprocess.run(
                ["pgrep", "-f", "python main_bot.py"],
                capture_output=True, text=True
            )
            bot_running = bool(result.stdout.strip())
        except:
            bot_running = False

        # Get log info
        log_files = list(self.project_dir.glob("logs/bot_monitor_*.log"))
        if log_files:
            latest_log = max(log_files, key=lambda x: x.stat().st_mtime)
            log_lines = sum(1 for _ in open(latest_log))
            log_age = time.time() - latest_log.stat().st_mtime
        else:
            log_lines = 0
            log_age = 0

        # Count positions
        positions_file = self.project_dir / "data" / "positions.json"
        if positions_file.exists():
            with open(positions_file) as f:
                positions = json.load(f)
            num_positions = len(positions)
        else:
            num_positions = 0

        status_emoji = "🟢" if bot_running else "🔴"

        return f"""📊 <b>Bot Status</b>

{status_emoji} Bot: {"Running" if bot_running else "Stopped"}
📈 Positions: {num_positions}
📝 Log lines: {log_lines}
⏱ Last activity: {int(log_age)}s ago

<i>Updated: {datetime.now().strftime('%H:%M:%S')}</i>"""

    def cmd_positions(self) -> str:
        """List current positions."""
        positions_file = self.project_dir / "data" / "positions.json"

        if not positions_file.exists():
            return "📭 No hay archivo de posiciones."

        with open(positions_file) as f:
            positions = json.load(f)

        if not positions:
            return "📭 No hay posiciones abiertas."

        client, _ = self._create_clob_client()
        use_live = client is not None

        lines = ["📈 <b>Posiciones Abiertas</b>\n"]
        if use_live:
            lines.append("📡 Precio actual: mejor bid (sellable)\n")

        total_value = 0.0
        total_pnl = 0.0

        for i, (token_id, pos) in enumerate(positions.items(), 1):
            entry = pos["entry_price"]
            size = pos.get("filled_size", pos.get("size", 0))
            tp = pos["tp"]
            sl = pos["sl"]
            value = entry * size
            total_value += value

            current_price = None
            condition_id = None
            if use_live:
                current_price, condition_id = self._get_best_bid_and_market(client, token_id)

            question = pos.get("question")
            if not question:
                question = self._get_market_question(token_id, condition_id=condition_id, client=client)
            if question and len(question) > 90:
                question = question[:87] + "..."
            title = question or f"Token {token_id[:10]}..."
            title = html_escape(title)

            pnl_line = "   Now: N/A"
            if current_price is not None:
                pnl = (current_price - entry) * size
                total_pnl += pnl
                pnl_pct = (current_price - entry) / entry * 100 if entry else 0.0
                pnl_sign = "+" if pnl >= 0 else ""
                pct_sign = "+" if pnl_pct >= 0 else ""
                pnl_line = (
                    f"   Now: ${current_price:.4f} | "
                    f"PnL: {pnl_sign}${pnl:.4f} ({pct_sign}{pnl_pct:.2f}%)"
                )

            lines.append(
                f"<b>{i}.</b> {title}\n"
                f"<code>{token_id[:10]}...</code>\n"
                f"   Entry: ${entry:.4f} | Size: {size:.4f}\n"
                f"   TP: ${tp:.4f} | SL: ${sl:.4f}\n"
                f"{pnl_line}\n"
            )

        lines.append(f"\n💰 <b>Total invertido: ${total_value:.2f}</b>")
        if use_live:
            pnl_sign = "+" if total_pnl >= 0 else ""
            lines.append(f"📊 <b>PNL total: {pnl_sign}${total_pnl:.4f}</b>")
        return "\n".join(lines)

    def _get_best_bid_and_market(self, client, token_id: str) -> Tuple[Optional[float], Optional[str]]:
        """Fetch best bid and condition/market id for a token."""
        try:
            book = client.get_order_book(token_id)
            bids = None
            market_id = None
            if isinstance(book, dict):
                bids = book.get("bids")
                market_id = book.get("market") or book.get("market_id") or book.get("condition_id")
            else:
                bids = getattr(book, "bids", None)
                market_id = (
                    getattr(book, "market", None)
                    or getattr(book, "market_id", None)
                    or getattr(book, "condition_id", None)
                )
                if not bids and hasattr(book, "to_dict"):
                    data = book.to_dict()
                    bids = data.get("bids")
                    market_id = market_id or data.get("market") or data.get("market_id") or data.get("condition_id")

            if not bids:
                return None, market_id

            prices = []
            for bid in bids:
                price = getattr(bid, "price", None)
                if price is None and isinstance(bid, dict):
                    price = bid.get("price")
                if price is not None:
                    prices.append(float(price))
            best_bid = max(prices) if prices else None
            return best_bid, market_id
        except Exception:
            return None, None

    def _get_best_bid(self, client, token_id: str) -> Optional[float]:
        """Fetch best bid price for a token (sellable price)."""
        try:
            book = client.get_order_book(token_id)
            bids = None
            if isinstance(book, dict):
                bids = book.get("bids")
            else:
                bids = getattr(book, "bids", None)
                if not bids and hasattr(book, "to_dict"):
                    bids = book.to_dict().get("bids")

            if not bids:
                return None

            prices = []
            for bid in bids:
                price = getattr(bid, "price", None)
                if price is None and isinstance(bid, dict):
                    price = bid.get("price")
                if price is not None:
                    prices.append(float(price))
            return max(prices) if prices else None
        except Exception:
            return None

    def _load_market_cache(self) -> dict:
        if not self.market_cache_path.exists():
            return {}
        try:
            with open(self.market_cache_path, "r") as f:
                data = json.load(f)
            if isinstance(data, dict):
                return data
        except Exception:
            return {}
        return {}

    def _save_market_cache(self, cache: dict) -> None:
        try:
            with open(self.market_cache_path, "w") as f:
                json.dump(cache, f)
        except Exception:
            pass

    def _get_market_question(
        self,
        token_id: str,
        condition_id: Optional[str] = None,
        client: Optional[ClobClient] = None,
    ) -> Optional[str]:
        cache = self._load_market_cache()
        entry = cache.get(token_id)
        now = int(time.time())
        if entry and isinstance(entry, dict):
            ts = entry.get("ts", 0)
            if now - ts < self.market_cache_ttl:
                return entry.get("question")

        question = None
        if condition_id:
            question = self._fetch_question_by_condition(condition_id, client)
        if not question:
            question = self._fetch_question_from_gamma(token_id)
        if question:
            cache[token_id] = {"question": question, "ts": now}
            self._save_market_cache(cache)
        return question

    def _fetch_question_by_condition(
        self, condition_id: str, client: Optional[ClobClient] = None
    ) -> Optional[str]:
        def _extract_question(data):
            if not data:
                return None
            markets = None
            if isinstance(data, dict):
                markets = data.get("data") or data.get("markets") or [data]
            elif isinstance(data, list):
                markets = data
            if not markets:
                return None
            for m in markets:
                if not isinstance(m, dict):
                    continue
                question = m.get("question") or m.get("title")
                if question:
                    return question
            return None

        data = None
        try:
            params = {"condition_id": condition_id}
            base = "https://gamma-api.polymarket.com/markets"
            url = f"{base}?{urllib.parse.urlencode(params)}"
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read())
        except Exception:
            data = None

        question = _extract_question(data)
        if question:
            return question

        if client:
            try:
                market = client.get_market(condition_id)
                if isinstance(market, dict):
                    for key in ("question", "title", "name"):
                        if market.get(key):
                            return market.get(key)
            except Exception:
                pass
        return None

    def _fetch_question_from_gamma(self, token_id: str) -> Optional[str]:
        def _extract_question(data):
            if not data:
                return None
            if isinstance(data, dict):
                markets = data.get("data") or data.get("markets") or []
            elif isinstance(data, list):
                markets = data
            else:
                return None

            for m in markets:
                if not isinstance(m, dict):
                    continue
                question = m.get("question") or m.get("title")
                raw_ids = m.get("clobTokenIds") or m.get("clob_token_ids")
                ids = []
                if isinstance(raw_ids, str):
                    try:
                        ids = json.loads(raw_ids)
                    except (json.JSONDecodeError, TypeError):
                        ids = [raw_ids] if raw_ids else []
                elif isinstance(raw_ids, list):
                    ids = raw_ids
                ids = [str(x) for x in ids]
                if token_id in ids:
                    return question
            return None

        def _gamma_get(params):
            base = "https://gamma-api.polymarket.com/markets"
            url = f"{base}?{urllib.parse.urlencode(params)}"
            try:
                with urllib.request.urlopen(url, timeout=10) as resp:
                    return json.loads(resp.read())
            except Exception:
                return None

        # Try direct token filters first (best-effort).
        for key in ("clobTokenId", "clob_token_id", "token_id", "clobTokenIds"):
            data = _gamma_get({key: token_id})
            question = _extract_question(data)
            if question:
                return question

        # Fallback: scan top markets by different orderings.
        for order in ("volume24hr", "volumeNum", "liquidityNum"):
            data = _gamma_get({
                "limit": 1000,
                "order": order,
                "ascending": "false",
                "active": "true",
                "closed": "false",
            })
            question = _extract_question(data)
            if question:
                return question
        return None

    def cmd_simulate(self) -> str:
        """Run TP/SL simulation."""
        self.send_message("⏳ Ejecutando simulación...")

        try:
            result = subprocess.run(
                ["python", str(self.project_dir / "tools" / "simulate_fills.py")],
                capture_output=True, text=True, timeout=120,
                cwd=str(self.project_dir)
            )

            output = result.stdout

            # Parse summary from output
            if "SUMMARY" in output:
                summary_part = output.split("SUMMARY")[1]
                lines = summary_part.strip().split("\n")

                tp_line = next((l for l in lines if "Take Profits" in l), "Take Profits: 0")
                sl_line = next((l for l in lines if "Stop Losses" in l), "Stop Losses: 0")
                pnl_line = next((l for l in lines if "P&L" in l), "")

                return f"""✅ <b>Simulación Completada</b>

{tp_line}
{sl_line}
{pnl_line}

<i>{datetime.now().strftime('%H:%M:%S')}</i>"""
            else:
                return "✅ Simulación ejecutada. Sin fills detectados."

        except subprocess.TimeoutExpired:
            return "⚠️ Simulación timeout (>2min)"
        except Exception as e:
            return f"❌ Error: {e}"

    def cmd_summary(self) -> str:
        """Send daily summary."""
        positions_file = self.project_dir / "data" / "positions.json"
        results_file = self.project_dir / "data" / "simulation_results.json"

        # Load positions
        positions = {}
        if positions_file.exists():
            with open(positions_file) as f:
                positions = json.load(f)

        # Load results
        results = []
        if results_file.exists():
            with open(results_file) as f:
                results = json.load(f)

        # Calculate stats
        total_positions = len(positions)
        total_value = sum(p["size"] * p["entry_price"] for p in positions.values())

        tp_hits = [r for r in results if r.get("type") == "take_profit"]
        sl_hits = [r for r in results if r.get("type") == "stop_loss"]
        total_pnl = sum(r.get("pnl_usd", 0) for r in results)

        return f"""📊 <b>Daily Summary</b>

<b>Posiciones:</b>
  Open: {total_positions}
  Value: ${total_value:.2f}

<b>Resultados Simulados:</b>
  ✅ Take Profits: {len(tp_hits)}
  ❌ Stop Losses: {len(sl_hits)}
  💰 P&L: ${total_pnl:+.4f}

<i>{datetime.now().strftime('%Y-%m-%d %H:%M')}</i>"""

    def cmd_balance(self) -> str:
        """Check account balance."""
        try:
            client, error = self._create_clob_client()
            if error:
                return f"⚠️ {error}"

            result = client.get_balance_allowance(
                params=BalanceAllowanceParams(asset_type=AssetType.COLLATERAL)
            )

            def _extract_values(payload):
                if isinstance(payload, dict):
                    return payload.get("balance"), payload.get("allowance")
                return getattr(payload, "balance", None), getattr(payload, "allowance", None)

            def _to_float(value):
                if value is None:
                    return None
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return None

            def _format_usdc(value):
                num = _to_float(value)
                if num is None:
                    return None, None

                raw_str = str(value)
                # Heuristic: if integer-like and >= 1e6, treat as micro-USDC.
                if ("." not in raw_str and "e" not in raw_str.lower()) and num >= 1_000_000 and num.is_integer():
                    return f"{num / 1_000_000:.6f}", "micro-USDC (1e-6)"
                return f"{num:.6f}", "USDC"

            balance_value, allowance_value = _extract_values(result)
            if balance_value is None:
                return "⚠️ No se pudo leer el balance (respuesta vacía)"

            balance_usdc, balance_unit = _format_usdc(balance_value)
            allowance_usdc, allowance_unit = _format_usdc(allowance_value)

            lines = [
                f"💰 <b>Balance (raw): {balance_value}</b>",
            ]
            if balance_usdc is not None:
                lines.append(f"💵 Balance (USDC): {balance_usdc}")
                if balance_unit:
                    lines.append(f"ℹ️ Unidad estimada: {balance_unit}")

            if allowance_value is not None:
                lines.append(f"🔓 Allowance (raw): {allowance_value}")
                if allowance_usdc is not None:
                    lines.append(f"🔓 Allowance (USDC): {allowance_usdc}")
                    if allowance_unit:
                        lines.append(f"ℹ️ Unidad estimada: {allowance_unit}")

            return "\n".join(lines)

        except Exception as e:
            return f"❌ Error: {e}"

    def cmd_logs(self) -> str:
        """Get last log lines."""
        log_files = list(self.project_dir.glob("logs/bot_monitor_*.log"))

        if not log_files:
            return "📭 No hay logs disponibles."

        latest_log = max(log_files, key=lambda x: x.stat().st_mtime)

        with open(latest_log) as f:
            lines = f.readlines()

        last_lines = lines[-10:]

        # Truncate long lines
        truncated = []
        for line in last_lines:
            line = line.strip()
            if len(line) > 60:
                line = line[:60] + "..."
            truncated.append(line)

        return f"""📝 <b>Últimas 10 líneas</b>

<code>{"".join(truncated[-10:])}</code>"""

    def cmd_stop(self) -> str:
        """Stop the bot (returns warning, actual stop requires confirmation)."""
        return """⚠️ <b>¿Detener el bot?</b>

Para confirmar, ejecuta en terminal:
<code>pkill -f "python main_bot.py"</code>

O usa: /status para verificar estado."""

    def cmd_whales(self) -> str:
        """Show whale copy trading stats."""
        stats_file = self.project_dir / "data" / "whale_copy_stats.json"
        profiles_file = self.project_dir / "data" / "whale_profiles.json"
        
        # Load stats
        stats = {}
        if stats_file.exists():
            try:
                with open(stats_file) as f:
                    stats = json.load(f)
            except: pass
            
        # Load profiles
        top_whales = []
        if profiles_file.exists():
            try:
                with open(profiles_file) as f:
                    data = json.load(f)
                    profiles = list(data.get("profiles", {}).values())
                    # Sort by score
                    profiles.sort(key=lambda x: x.get("score", 0), reverse=True)
                    top_whales = profiles[:3]
            except: pass

        copied = stats.get("signals_copied", 0)
        rejected = stats.get("signals_rejected", 0)
        pnl = stats.get("total_pnl", 0.0)
        
        msg = [f"🐳 <b>Whale Copy Status</b>\n"]
        msg.append(f"📡 Signals: {stats.get('signals_evaluated', 0)}")
        msg.append(f"✅ Copied: {copied}")
        msg.append(f"🛡️ Rejected: {rejected}")
        msg.append(f"💰 P&L: ${pnl:+.2f}\n")
        
        if top_whales:
            msg.append("🏆 <b>Top Whales:</b>")
            for i, w in enumerate(top_whales, 1):
                name = w.get("name", "Anon")[:15]
                score = w.get("score", 0)
                vol = w.get("stats", {}).get("total_volume", 0)
                msg.append(f"{i}. <b>{name}</b> ({score}) ${vol/1000:.1f}k")
                
        return "\n".join(msg)

    def run(self):
        """Main loop to listen for commands."""
        print(f"🤖 Telegram bot started")
        print(f"   Listening for commands from chat_id: {self.chat_id}")
        print(f"   Press Ctrl+C to stop\n")

        self.send_message("🤖 <b>Bot Iniciado</b>\n\nEscribí /help para ver comandos.")

        while self.running:
            try:
                updates = self.get_updates(timeout=30)

                for update in updates:
                    self.last_update_id = update.get("update_id", 0)

                    message = update.get("message", {})
                    chat = message.get("chat", {})
                    from_user = message.get("from", {})
                    text = message.get("text", "")

                    # Only respond to configured chat
                    if str(chat.get("id")) != self.chat_id:
                        continue

                    if not text:
                        continue

                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Command: {text}")

                    # Process command
                    if text.startswith("/"):
                        response = self.process_command(text, from_user.get("username", ""))
                        self.send_message(response)

            except KeyboardInterrupt:
                print("\nShutting down...")
                self.running = False
                self.send_message("🛑 Bot detenido.")
                break

            except Exception as e:
                print(f"Error: {e}")
                time.sleep(5)


def main():
    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "").strip()

    if not token or not chat_id:
        print("❌ Telegram not configured. Add to .env:")
        print("   TELEGRAM_BOT_TOKEN=your_token")
        print("   TELEGRAM_CHAT_ID=your_id")
        sys.exit(1)

    bot = TelegramCommandBot(token, chat_id)
    bot.run()


if __name__ == "__main__":
    main()
