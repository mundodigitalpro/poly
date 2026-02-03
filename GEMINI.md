# Gemini CLI Context Memory

This file serves as the long-term memory for the Gemini CLI agent working on the Polymarket Python Client project.

## Multi-Agent Team Setup
Five AI agents collaborate on this project:
- **GEMINI.md** (this file): Current state tracking, quick commands, contextual memory.
- **AGENTS.md** (Codex): Process guidelines, commit/PR standards, testing workflows.
- **CLAUDE.md** (Claude): Technical architecture, auth details, implementation patterns.
- **Kimi** (Moonshot AI): Fast code reviews, security analysis, risk assessment.
- **AMP** (New): Architect role (trial period). See `docs/team/AMP_INSTRUCTIONS.md`.

**Coordination**: Keep state updates here; refer to AGENTS.md for "how to", CLAUDE.md for "how it works".

## Project Overview
A Python client and autonomous trading bot for Polymarket using `py-clob-client`.
- **Repo**: `/home/josejordan/poly`
- **Key Entry Points**: `poly_client.py` (CLI), `main_bot.py` (Bot), `place_order.py` (Manual)

## Project Structure (v0.12.3)
```
poly/
├── poly_client.py, main_bot.py, place_order.py  # Entry points
├── config.json                 # Bot configuration
├── bot/                        # Core modules (scanner, trader, strategy, etc.)
├── legacy/                     # Archived scripts (auto_sell.py)
├── scripts/                    # Utilities (generate_user_api_keys.py, verify_wallet.py, etc.)
├── tools/                      # Analysis (whale_tracker.py, dutch_book_scanner.py, etc.)
├── docs/                       # Documentation (bot_plan.md, proposals/, team/)
├── tests/                      # Unit tests (pytest)
├── data/                       # Runtime JSON (positions, blacklist, stats)
├── logs/                       # Daily logs
└── AGENTS.md, CLAUDE.md, GEMINI.md  # Agent memory files
```

## Authentication & Configuration
- **Magic Link (Gmail)**: Uses `signature_type=1`. Requires `POLY_FUNDER_ADDRESS` + `POLY_PRIVATE_KEY`.
- **EOA (MetaMask)**: Uses `signature_type=0`. Requires only `POLY_PRIVATE_KEY`.
- **Credentials**: Managed via `.env` (never commit!). Generate with `python scripts/generate_user_api_keys.py`.

## Current State (as of 2026-02-03)
- **Version**: 0.16.0 (Strategy Improvements Phase 1)
- **Latest Change**: Implemented IMP-001/002/003 from `docs/strategy_improvement_plan.md`:
  - Expanded odds range: 0.35-0.80 (was 0.60-0.80)
  - Improved TP/SL ratio: 2:1 (was 1.2:1) - breakeven now 33% vs 48%
  - Increased position size: $1.00 (was $0.25), max positions 10 (was 20)
- **Bot Status**: Ready for overnight dry-run testing with new strategy
- **Tests**: 60/61 passing (1 pre-existing failure in tracked_wallets)
- **Active Plan**: `docs/strategy_improvement_plan.md` - Phase 1 complete, Phase 2 next

### Phase History
- **Phase 0-2.8**: COMPLETED (Core, Integration, Gamma API, Whale Tracking)
- **Phase 3**: COMPLETED (Whale Copy Integration & Dry Run Analysis)
- **Phase 4**: IN PROGRESS (Strategy Optimization)
  - ✅ IMP-001: Odds range consistency (DONE)
  - ✅ IMP-002: TP/SL 2:1 ratio (DONE)
  - ✅ IMP-003: Position sizing (DONE)
  - ⏳ IMP-007: 7-day validation (STARTED tonight)

## Useful Commands
```bash
python poly_client.py --balance             # Account status
python poly_client.py --book <TOKEN_ID>     # Orderbook
python main_bot.py --once                   # Single dry-run loop
python main_bot.py                          # Continuous dry run
python scripts/generate_user_api_keys.py   # Fix 401 errors
python scripts/verify_wallet.py            # Verify wallet
python tools/whale_tracker.py              # Whale tracking
python tools/analyze_positions.py          # Position analysis
bash scripts/run_readonly_tests.sh    # Full diagnostic report
bash scripts/start_telegram_bot.sh         # Telegram bot (venv-aware)
python -m pytest                           # Run tests
```

## Inter-Agent Communication
The AI agents can communicate programmatically via CLI or unified wrapper:

| Agent | CLI Command | Wrapper Command | Best Use |
|-------|-------------|-----------------|----------|
| **Claude** | Already in session | N/A (interactive) | Architecture, decisions |
| **Codex** | `codex exec "msg" --full-auto` | `./scripts/ask_agent.sh codex "msg"` | Implementation, refactors |
| **Gemini** | `gemini -p "msg" -o text` | `./scripts/ask_agent.sh gemini "msg"` | Status, context queries |
| **Kimi** | `kimi -p "msg" --print` | `./scripts/ask_agent.sh kimi "msg"` | Fast review, analysis |

### Unified Wrapper Script
```bash
# Recommended approach - normalizes all agent calls
./scripts/ask_agent.sh <agent> "<prompt>" [output_file]

# Examples
./scripts/ask_agent.sh kimi "Review bot/trader.py for security issues"
./scripts/ask_agent.sh gemini "What's the current phase?"
./scripts/ask_agent.sh kimi "Analyze risks" /tmp/analysis.txt

# Test connectivity
./scripts/ask_agent.sh --test kimi
./scripts/ask_agent.sh --test gemini
```

### When Another Agent Contacts You
- You may receive messages from Claude, Codex, or Kimi via the wrapper or `-p` flag
- Acknowledge receipt and provide requested information
- Update this file (GEMINI.md) with any state changes from the collaboration
- Report completion status back to the requesting agent

### Communication Protocol
1. **Task Assignment**: Another agent sends a prompt with a specific task
2. **Execution**: Complete the task using available tools
3. **Response**: Return results via stdout (captured by calling agent)
4. **Documentation**: Update relevant memory files if state changed
