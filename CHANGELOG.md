# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]
### Planned
- **Market Filtering**: Fetch specific markets.
- **Execution**: Ability to place Limit and Market orders.
- **Wallet**: Check USDC and CTF balances.

## [0.2.0] - 2026-01-27
### Added
- **Market Filtering**: Filter markets by text using `--filter` argument.
- **Enhanced Data**: Switched to `get_sampling_markets` for full metadata.

## [0.1.0] - 2026-01-27
### Added
- **Initial Release**: Basic Python client structure.
- **Connection**: Authentication using `py_clob_client` with API Keys.
- **Docker**: Containerization support (`Dockerfile`, `docker-compose.yml`).
- **Config**: Environment variable management via `.env`.
- **Docs**: Comprehensive `README.md` in Spanish.
- **Fixes**: Graceful handling of missing/invalid Private Key (Read-Only mode).
