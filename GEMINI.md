# Gemini CLI Context Memory

This file serves as the long-term memory for the Gemini CLI agent working on the Polymarket Python Client project.

## Multi-Agent Team Setup
Four AI agents collaborate on this project:
- **GEMINI.md** (this file): Current state tracking, quick commands, contextual memory.
- **AGENTS.md** (Codex): Process guidelines, commit/PR standards, testing workflows.
- **CLAUDE.md** (Claude): Technical architecture, auth details, implementation patterns.
- **AMP** (New): Architect role (trial period). See `AMP_INSTRUCTIONS.md`.

**Note**: AMP is in trial as substitute Architect. Runs in interactive mode only (no `-x` credits).

**Coordination**: Keep state updates here; refer to AGENTS.md for "how to", CLAUDE.md for "how it works".

## Project Overview
A Python client and autonomous trading bot for Polymarket using `py-clob-client`.
- **Repo**: `/home/josejordan/poly`
- **Key Files**: `poly_client.py` (CLI), `bot_plan.md` (Bot Design), `place_order.py` (Manual Trading).

## Agent Ecosystem
This repository is managed by a triad of agent contexts. **Consult these before acting**:
1. **CODEX (`AGENTS.md`)**: The **Legislator**. Defines the "Law" of the repo: project structure, coding standards, and build/test commands.
2. **CLAUDE (`CLAUDE.md`)**: The **Architect**. Holds deep technical knowledge: Auth flows (`signature_type`), API quirks, and the `bot_plan.md` architecture.
3. **GEMINI (`GEMINI.md`)**: The **Operator** (You). Maintains active execution context, tracks progress, and implements solutions adhering to CODEX's rules and CLAUDE's designs.

## Authentication & Configuration
- **Magic Link (Gmail)**: Uses `signature_type=1`. Requires `POLY_FUNDER_ADDRESS` + `POLY_PRIVATE_KEY`.
- **EOA (MetaMask)**: Uses `signature_type=0`. Requires only `POLY_PRIVATE_KEY`.
- **Credentials**: Managed via `.env` (never commit!). Generate with `python generate_user_api_keys.py`.

## Development Guidelines (from AGENTS.md & CLAUDE.md)
- **Style**: Python 4-space indent, snake_case.
- **Commits**: Conventional Commits (feat, fix, docs).
- **Safety**: 
  - Never commit secrets.
  - Verify `signature_type` matches wallet.
  - Test with small amounts.
- **Bot Plan**:
  - Located in `bot_plan.md`.
  - Phased rollout: Dry run -> Paper -> Micro -> Normal.
  - 10+ safety protections.

## Current State (as of 2026-01-30 Evening)
- **Version**: 0.12.1 (Beta)
- **Phase 0-2.6**: COMPLETED (see history below)
- **Phase 2.7 (Arbitrage Research)**: COMPLETED (2026-01-30)
  - Dutch Book: NOT VIABLE (HFT dominates)
  - NegRisk Multi-outcome: NOT VIABLE (efficient markets)
  - Whale Tracking: ✅ IMPLEMENTED
- **Bot Status**: Running in dry-run, 10/10 positions active
- **Tests**: 20/20 passing

### New Tools Added (2026-01-30)
| Tool | Purpose | Status |
|------|---------|--------|
| `dutch_book_scanner.py` | YES/NO arbitrage detection | Research complete |
| `negrisk_scanner.py` | Multi-outcome arbitrage | Research complete |
| `whale_tracker.py` | Whale trade tracking & copy signals | ✅ Production ready |

### Phase History
- **Phase 0 (Prep)**: Completed
- **Phase 1 (Core Modules)**: Completed
- **Phase 2 (Integration)**: Completed
- **Phase 2.5 (Scanner Hardening)**: Completed
- **Phase 2.6 (Gamma API)**: Completed
- **Phase 2.7 (Arbitrage Research)**: Completed
- **Next**: Phase 3 (Extended Dry Run) + Phase 2.8 (Whale Integration)

**Implemented Proposals:**
- `PROPOSAL_TRENDING_VOLUME.md`: Gamma API integration
  - Status: ✅ IMPLEMENTED (v0.12.0)
  - Author: AMP (proposed), CLAUDE (implemented)
  - Files: `bot/gamma_client.py`, `bot/market_scanner.py`, `config.json`

**Incident Report: Stop Loss Bug (2026-01-30)**
- **Issue (RESOLVED)**: Stop Loss orders were blocked when price dropped >50% from entry due to `min_sell_ratio` safety check.
- **Root Cause**: `execute_sell()` applied same price floor to all sells, including emergency exits.
- **Fix Applied**: Added `is_emergency_exit` flag to bypass check for Stop Loss orders.
- **Test**: `tests/test_stop_loss_emergency_exit.py` - PASSED.
- **Coordination**: Claude (architecture) → Codex (implementation) → Gemini (verification).

**Technical Report: Market Discovery Challenges**
- **Issue (RESOLVED)**: Spread calculation was broken - orderbook returns bids sorted ascending and asks sorted descending, but code was taking first element (worst price).
- **Fix Applied**: `market_scanner.py` now uses `max(bids)` and `min(asks)` to get correct best prices.
- **Result**: Scanner now finds candidates with correct spreads (1-5%) instead of rejecting all with 196% spread.

**Open Positions (5 active)**
- All positions have reasonable entry prices (0.302 - 0.7)
- No "toxic" positions detected at extreme low prices
- Ready for dry-run verification with fixed Stop Loss logic

## Useful Commands
- `python poly_client.py --balance`
- `python poly_client.py --book <TOKEN_ID> --monitor`
- `python generate_user_api_keys.py` (Fixes 401 errors)
- `python main_bot.py --once` (single dry-run loop)
- `python main_bot.py` (continuous dry run)
- `python -m pytest` (requires `pip install pytest`)

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
