# Repository Guidelines

## Multi-Agent Development Team
This repository employs four AI agents with complementary roles:
- **AGENTS.md** (Codex, this file): Process guidelines, development workflows, commit standards, coding conventions, and testing procedures.
- **CLAUDE.md** (Claude): Technical architecture, authentication flows, implementation patterns, and deep technical details.
- **GEMINI.md** (Gemini): Current project state, progress tracking, quick command reference, and contextual memory.
- **AMP** (Trial): Substitute Architect role during evaluation. Instructions in `AMP_INSTRUCTIONS.md`. Interactive mode only.

When contributing, consult the relevant memory file for your needs. Maintain consistency across all three files when updating shared information (auth, commands, bot status).

## Project Structure & Module Organization

The project is organized into logical directories:

- **Root-level entry points**: `poly_client.py` (CLI), `main_bot.py` (bot), `place_order.py` (manual orders), `auto_sell.py` (TP/SL bot).
- **`bot/`**: Core bot modules (`market_scanner.py`, `strategy.py`, `position_manager.py`, `trader.py`, `gamma_client.py`, `whale_service.py`).
- **`scripts/`**: Setup utilities (`generate_user_api_keys.py`, `verify_wallet.py`, `diagnose_config.py`, `test_all_sig_types.py`).
- **`tools/`**: Research & analysis (`whale_tracker.py`, `dutch_book_scanner.py`, `negrisk_scanner.py`, `analyze_positions.py`).
- **`docs/`**: Documentation (`bot_plan.md`, `PLAN.md`, `HANDOFF.md`). Subdirectories: `proposals/` for feature proposals, `team/` for AI team docs.
- **`tests/`**: Unit tests (pytest). **`data/`**: Runtime JSON files. **`logs/`**: Daily logs.
- **Configuration**: `config.json` (bot params), `.env` (secrets), `.env.example` (template).
- **Memory files**: `AGENTS.md` (Codex), `CLAUDE.md` (Claude), `GEMINI.md` (Gemini).

## Build, Test, and Development Commands
- Create a venv and install deps:
  - `python3 -m venv venv` and `source venv/bin/activate`
  - `pip install -r requirements.txt`
- Configure credentials: `cp .env.example .env`, then edit values.
- Generate API keys: `python scripts/generate_user_api_keys.py`.
- Common workflows:
  - `python poly_client.py --balance` (account status; orders/trades)
  - `python poly_client.py --filter "Trump" --limit 10` (market discovery)
  - `python poly_client.py --book <TOKEN_ID>` (orderbook)
  - `python poly_client.py --book <TOKEN_ID> --monitor --interval 5` (live book)
  - `python place_order.py` (manual order; edit constants first)
  - `python auto_sell.py` (auto-sell bot; review config)
  - `python scripts/verify_wallet.py` and `python scripts/diagnose_config.py` (config checks)
  - `python scripts/test_all_sig_types.py` (auth matrix test)
  - `python tools/find_whale_wallet.py` (whale discovery)
  - `python tools/whale_tracker.py` (whale tracking)
  - `python tools/analyze_positions.py` (position risk analysis)
  - `bash scripts/start_telegram_bot.sh` (Telegram bot; auto-uses venv + installs deps if missing)
  - `bash scripts/restart_bot.sh` (restarts main bot and stops any duplicate Telegram bots)
- Docker: `docker-compose up --build -d` and `docker-compose logs -f`.

## Coding Style & Naming Conventions
- Use standard Python style: 4-space indentation, snake_case for functions/variables, and UPPER_SNAKE_CASE for constants.
- Keep scripts small and focused; prefer new helpers over inline duplication.
- Environment variables are uppercase with `POLY_` prefix (see `.env.example`).

## Testing Guidelines
- **Automated Test Suite**: Run `python -m pytest` to execute unit tests (strategy, position manager). Use `scripts/test_all_sig_types.py` for full auth matrix verification.
- When touching auth or signing code, validate both Magic Link (`signature_type=1`) and EOA (`signature_type=0`) paths.

## Multi-Agent Collaboration
- Three agent memories guide work: `AGENTS.md` (Codex) for process/quality gates, `GEMINI.md` for current state and quick commands, and `CLAUDE.md` for architecture/auth details.
- Update `GEMINI.md` when project status changes (features completed, blockers, or verification notes).
- Update `AGENTS.md` when workflows, conventions, or contributor guidance change.
- Update `CLAUDE.md` when authentication patterns or core component behavior changes.

## Inter-Agent Communication (Pair Programming)
The three AI agents can communicate programmatically via terminal commands:

| Agent | CLI Tool | Non-Interactive Command | Version |
|-------|----------|------------------------|---------|
| **Claude** | `claude` | Already in session | Opus 4.5 |
| **Codex** | `codex` | `codex exec "message" --full-auto` | 0.92.0 |
| **Gemini** | `gemini` | `gemini -p "message" -o text` | 0.26.0 |

### How It Works
- Each agent can invoke another agent's CLI in non-interactive mode
- Responses are returned as stdout text
- Use `--full-auto` (Codex) or `-y` (Gemini) for auto-approval of actions
- Save responses to file: `-o file.txt` (Codex) or redirect stdout (Gemini)

### Communication Examples
```bash
# Claude asking Codex to review code
codex exec "Review the changes in market_scanner.py for code quality" --full-auto

# Claude asking Gemini about project state
gemini -p "What is the current phase and next task?" -o text

# Codex asking Gemini for context
gemini -p "Summarize recent changes to the bot" -o text
```

### Coordination Guidelines
- Use inter-agent communication for: code reviews, task delegation, status checks
- Each agent should update its memory file after completing significant work
- When receiving a task from another agent, acknowledge and report results
- Prefer async communication (file-based) for long-running tasks

## Authentication & Signature Types
- Magic Link (email/Gmail) uses `signature_type=1` and requires `POLY_FUNDER_ADDRESS`; EOA wallets use `signature_type=0` without the funder address. `signature_type=2` is rare.
- `poly_client.py` auto-detects the signature type based on `POLY_FUNDER_ADDRESS`, but `place_order.py` may be hardcoded—keep these consistent.

## Commit & Pull Request Guidelines
- Commit messages follow Conventional Commits (e.g., `feat: add orderbook fetching`, `fix(auth): resolve Magic Link issues`, `docs: update README`).
- PRs should describe what changed, how it was verified (commands run), and any config assumptions. Include screenshots or logs for user-facing or CLI output changes.

## Security & Configuration Tips
- Never commit `.env` or private keys. Regenerate credentials with `python generate_user_api_keys.py` if a 401 occurs.
- For “Invalid Signature,” re-check `signature_type` and funder/key pairing (see `CLAUDE.md`).
