# Gemini CLI Context Memory

This file serves as the long-term memory for the Gemini CLI agent working on the Polymarket Python Client project.

## Multi-Agent Team Setup
Three AI agents collaborate on this project:
- **GEMINI.md** (this file): Current state tracking, quick commands, contextual memory.
- **AGENTS.md** (Codex): Process guidelines, commit/PR standards, testing workflows.
- **CLAUDE.md** (Claude): Technical architecture, auth details, implementation patterns.

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

## Current State (as of 2026-01-29)
- **Version**: 0.10.0 (Beta)
- **Phase 0 (Prep)**: Completed.
- **Phase 1 (Core Modules)**: COMPLETED.
- **Phase 2 (Integration & Testing)**: COMPLETED.
  - `main_bot.py`: Implemented and verified via dry run (`python main_bot.py --once`).
  - **Unit Tests**: `tests/` added (strategy, position manager).
  - **Optimization**: MarketScanner includes client-side rate limiting to avoid API throttling.
- **Next Step**: Phase 3 (Extended Dry Run).
  - Task #13: Run bot for 7 days in dry-run mode.
- Basic CLI (`poly_client.py`) functional.
- Autonomous Bot is fully operational in dry-run mode.

**Technical Report: Market Discovery Challenges**
- **Issue (RESOLVED)**: Spread calculation was broken - orderbook returns bids sorted ascending and asks sorted descending, but code was taking first element (worst price).
- **Fix Applied**: `market_scanner.py` now uses `max(bids)` and `min(asks)` to get correct best prices.
- **Result**: Scanner now finds candidates with correct spreads (1-5%) instead of rejecting all with 196% spread.

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
