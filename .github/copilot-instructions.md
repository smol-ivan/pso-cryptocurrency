# Copilot instructions

## Project overview

This is a Rust 2024 command-line application for cryptocurrency/asset portfolio optimization using particle swarm optimization (PSO). The executable is `pso-crypto`; the library is exposed from `src/lib.rs`.

The main runtime pipeline is:

1. `src/config.rs` loads a TOML file, applies `APP__...` environment overrides, injects `DATABASE_URL`, and validates the resulting settings.
2. `src/market_data/provider/yahoo.rs` downloads historical quotes from Yahoo Finance.
3. `src/market_data/repository/postgres.rs` persists quotes to PostgreSQL using a transaction and `(symbol, timestamp)` upserts.
4. `src/market_data/dataset/builder.rs` reads prices for the requested assets, keeps only timestamps shared by every asset, and converts prices into a return matrix. Matrix rows are observations and columns follow the input asset order.
5. `src/optimizer/pso/` evaluates portfolio weights, tracks personal/global bests, and updates particles through configurable fitness, risk, and velocity strategies. Fitness is minimized; positions are repaired to non-negative weights summing to one.

The CLI connects to PostgreSQL before dispatching any subcommand. `update-db` refreshes stored market data; `target-bounds` inspects dataset return bounds; `optimize-single-test` builds a dataset and runs the seeded PSO optimization. Database schema changes live in `migrations/`.

## Build, test, and lint

Use the Nix development shell when available; `flake.nix` provides Rust, Cargo, rustfmt, Clippy, PostgreSQL, SQLx CLI, Docker Compose, and `just`.

```sh
nix develop
cp .env.example .env       # set real PostgreSQL values locally
cargo build
cargo test
cargo fmt --check
cargo clippy --all-targets --all-features
```

Run one integration test by test name, or target a specific integration-test file:

```sh
cargo test deserializes_full_configuration
cargo test --test configuration validates_all_required_constraints
cargo test --test optimizer replacement_preserves_seeded_optimization_result
```

The `justfile` is the canonical command shortcut list:

```sh
just up             # start PostgreSQL and Metabase
just migrate        # apply SQLx migrations
just dev-update     # download configured Yahoo data and save it
just dev-bound      # print minimum/maximum target-return bounds
just dev-single     # run the configured single optimization
just down
just logs
just psql
```

The executable accepts `--config <path>` to use a TOML file other than `config.toml`; `optimize-single-test` also accepts `--target-return` and `--seed`. `DATABASE_URL` is intentionally supplied through the environment rather than committed configuration.

## Configuration conventions

- Keep the TOML shape in sync with `config.example.toml` and the typed structs in `src/config.rs`.
- Configuration precedence is file, then `APP__...` environment variables, with `DATABASE_URL` explicitly overriding `database.url`.
- Tagged component enums use `kind = "..."` and `snake_case` values. Unknown kinds should fail deserialization rather than silently selecting a default.
- Optional database settings and PSO component sections use typed defaults. Add validation in `Settings::validate()` for new invariants.
- Do not expose database credentials in debug output or effective-run JSON. `DatabaseConfig` redacts its URL and `effective_config_json()` deliberately excludes the database section.

## Domain and optimizer conventions

- Preserve the asset ordering invariant: `Dataset.assets[i]` corresponds to return-matrix column `i`, and particle position dimension `i` is that asset's portfolio weight.
- Dataset construction requires common timestamps across all requested assets and calculates simple returns from consecutive prices. Changes to alignment or return semantics must be reflected in the dataset tests.
- `FitnessFunction`, `RiskMeasure`, and `VelocityModel` are strategy interfaces. Runtime configuration should construct implementations through the `build()` methods in `src/optimizer/pso/config.rs`, not by duplicating matching logic in the CLI.
- A particle's `eval` is its current position; `best_eval` and `best_position` are its personal best. A lower fitness is better, and personal bests update only on a strict improvement.
- PSO uses a caller-provided seeded `StdRng`; preserve deterministic behavior when changing the optimization loop or adding tests.
- Velocity updates must leave positions as valid portfolio allocations. The inertia implementation clips negative weights and normalizes them, falling back to a uniform allocation if all weights are zero.

## Persistence and error handling

- Use SQLx with PostgreSQL and keep schema changes as timestamped reversible migrations (`.up.sql` and `.down.sql`).
- Market-data writes are transactional and use conflict updates for existing `(symbol, timestamp)` rows; preserve atomicity when changing persistence code.
- Prefer `anyhow::Context`/`ensure!` at I/O and validation boundaries so failures identify the operation that failed. Do not silently substitute data when provider, database, or configuration operations fail.
