# BetScout SDKs (`/sdk`)

Official standalone client SDKs for the BetScout Sports Data, Player/Team Historical Analytics, Match Center Dossiers, and Multi-Bookmaker Odds platform:

- **[`sdk/typescript`](./typescript/README.md)** (`@betscout/sdk` v1.1.0): Standalone TypeScript / Node.js SDK with 60+ methods, full TypeScript interfaces, interactive 8-tab Web Showcase (`examples/showcase.html`), 1:1 Match Center Replica (`examples/match-center.html` for `/match/76034538`), and Vitest test suite.
- **[`sdk/python`](./python/README.md)** (`betscout-sdk` / `betscout_sdk` v1.1.0): Standalone Python SDK with 1:1 method parity (supporting both `snake_case` and `camelCase` method signatures), zero external runtime dependencies, CLI quickstart (`examples/quickstart.py`), Web Showcase server (`examples/showcase_server.py`), and Pytest test suite.

> **Synchronization Rule:** Any new endpoint, interface, or analytical workflow added to `@betscout/sdk` (`sdk/typescript`) must be maintained in lockstep in `betscout_sdk` (`sdk/python`) and vice versa.
