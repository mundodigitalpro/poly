# Repository Guidelines

## Multi-Agent Development Team
This repository employs three AI agents with complementary roles:
- **AGENTS.md** (Codex, this file): Process guidelines, development workflows, commit standards, coding conventions, and testing procedures.
- **CLAUDE.md** (Claude): Technical architecture, authentication flows, implementation patterns, and deep technical details.
- **GEMINI.md** (Gemini): Current project state, progress tracking, quick command reference, and contextual memory.

When contributing, consult the relevant memory file for your needs. Maintain consistency across all three files when updating shared information (auth, commands, bot status).

## Project Structure & Module Organization
- Root-level Python scripts implement the client and automation: `poly_client.py` (CLI), `place_order.py` (manual orders), `auto_sell.py` (TP/SL safety bot), and `generate_user_api_keys.py` (API creds). Supporting utilities include `verify_wallet.py`, `diagnose_config.py`, and `test_all_sig_types.py`.
- Documentation and plans live in `README.md`, `CLAUDE.md`, `bot_plan.md` (design only), and `implementation_plan.md`. The bot plan references planned state files like `positions.json`, `blacklist.json`, and `stats.json`.
- Docker assets are in `Dockerfile` and `docker-compose.yml`. Secrets live in `.env` (see `.env.example`).

## Build, Test, and Development Commands
- Create a venv and install deps:
  - `python3 -m venv venv` and `source venv/bin/activate`
  - `pip install -r requirements.txt`
- Configure credentials: `cp .env.example .env`, then edit values.
- Generate API keys: `python generate_user_api_keys.py`.
- Common workflows:
  - `python poly_client.py --balance` (account status; orders/trades)
  - `python poly_client.py --filter "Trump" --limit 10` (market discovery)
  - `python poly_client.py --book <TOKEN_ID>` (orderbook)
  - `python poly_client.py --book <TOKEN_ID> --monitor --interval 5` (live book)
  - `python place_order.py` (manual order; edit constants first)
  - `python auto_sell.py` (auto-sell bot; review config)
  - `python verify_wallet.py` and `python diagnose_config.py` (config checks)
  - `python test_all_sig_types.py` (auth matrix test)
- Docker: `docker-compose up --build -d` and `docker-compose logs -f`.

## Coding Style & Naming Conventions
- Use standard Python style: 4-space indentation, snake_case for functions/variables, and UPPER_SNAKE_CASE for constants.
- Keep scripts small and focused; prefer new helpers over inline duplication.
- Environment variables are uppercase with `POLY_` prefix (see `.env.example`).

## Testing Guidelines
- No automated test suite is configured. Use `python test_all_sig_types.py` for auth verification and run CLI flows manually with small amounts.
- When touching auth or signing code, validate both Magic Link (`signature_type=1`) and EOA (`signature_type=0`) paths.

## Multi-Agent Collaboration
- Three agent memories guide work: `AGENTS.md` (Codex) for process/quality gates, `GEMINI.md` for current state and quick commands, and `CLAUDE.md` for architecture/auth details.
- Update `GEMINI.md` when project status changes (features completed, blockers, or verification notes).
- Update `AGENTS.md` when workflows, conventions, or contributor guidance change.
- Update `CLAUDE.md` when authentication patterns or core component behavior changes.

## Authentication & Signature Types
- Magic Link (email/Gmail) uses `signature_type=1` and requires `POLY_FUNDER_ADDRESS`; EOA wallets use `signature_type=0` without the funder address. `signature_type=2` is rare.
- `poly_client.py` auto-detects the signature type based on `POLY_FUNDER_ADDRESS`, but `place_order.py` may be hardcoded—keep these consistent.

## Commit & Pull Request Guidelines
- Commit messages follow Conventional Commits (e.g., `feat: add orderbook fetching`, `fix(auth): resolve Magic Link issues`, `docs: update README`).
- PRs should describe what changed, how it was verified (commands run), and any config assumptions. Include screenshots or logs for user-facing or CLI output changes.

## Security & Configuration Tips
- Never commit `.env` or private keys. Regenerate credentials with `python generate_user_api_keys.py` if a 401 occurs.
- For “Invalid Signature,” re-check `signature_type` and funder/key pairing (see `CLAUDE.md`).
