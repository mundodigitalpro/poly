# Gemini CLI Context Memory

This file serves as the long-term memory for the Gemini CLI agent working on the Polymarket Python Client project.

## Multi-Agent Team Setup
Four AI agents collaborate on this project:
- **GEMINI.md** (this file): Current state tracking, quick commands, contextual memory.
- **AGENTS.md** (Codex): Process guidelines, commit/PR standards, testing workflows.
- **CLAUDE.md** (Claude): Technical architecture, auth details, implementation patterns.
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

## Current State (as of 2026-02-01)
- **Version**: 0.15.0 (Whale Copy Integrated)
- **Latest Change**: Integrated Whale Copy Engine into `main_bot.py`, added `/whales` command, and Telegram alerts.
- **Bot Status**: STOPPED (Ready for manual restart with Whale Copy active)
- **Tests**: 35+ passing (including new VWAP tests)
- **Active Proposals**: `docs/ESTRATEGIAS_VIABLES_2026.md`

### Phase History
- **Phase 0-2.8**: COMPLETED (Core, Integration, Gamma API, Whale Tracking)
- **Phase 3**: IN PROGRESS (Whale Copy Integration & Dry Run)

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
python -m pytest                           # Run tests
```

## Inter-Agent Communication
| Agent | How to Contact | Example |
|-------|----------------|---------|
| **Claude** | Running in separate terminal | Direct conversation |
| **Codex** | `codex exec "msg" --full-auto` | `codex exec "Review this PR" --full-auto` |
| **Gemini** | `gemini -p "msg" -o text` | `gemini -p "What's the project status?" -o text` |

## Inter-Agent Communication (Pair Programming)
The three AI agents can communicate programmatically:

| Agent | How to Contact | Example |
|-------|----------------|---------|
| **Claude** | Running in separate terminal | Direct conversation |
| **Codex** | `codex exec "msg" --full-auto` | `codex exec "Review this PR" --full-auto` |
| **Gemini** | `gemini -p "msg" -o text` | `gemini -p "What's the project status?" -o text` |

### When Another Agent Contacts You
- You may receive messages from Claude or Codex via the `-p` prompt flag
- Acknowledge receipt and provide requested information
- Update this file (GEMINI.md) with any state changes from the collaboration
- Report completion status back to the requesting agent

### Communication Protocol
1. **Task Assignment**: Another agent sends a prompt with a specific task
2. **Execution**: Complete the task using available tools
3. **Response**: Return results via stdout (captured by calling agent)
4. **Documentation**: Update relevant memory files if state changed
