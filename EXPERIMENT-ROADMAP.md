# Experiment roadmap

This is the working order for turning the current single PSO run into a
reproducible experiment system. Keep each step small and verify it before
starting the next one.

## Current state

- The PSO accepts a `RunRecorder`.
- `MemoryRecorder` stores one record per iteration and, optionally, one record
  per particle per iteration.
- `RunResult` contains the best particle, iteration count, evaluation count,
  duration, and stop reason.
- `optimize-single-test` runs one optimization and prints a small result.
- Nothing from the recorder or `RunResult` is stored in PostgreSQL yet.

## Phase 1: Make one run reliable

Goal: run the optimizer once and have a result that can be inspected and
reproduced.

- [x] Confirm the configured data exists in PostgreSQL.
- [x] Run `just dev-update`.
- [x] Run `just dev-bound` and record the available target-return range.
- [x] Run `just dev-single` with a known seed and target return.
- [x] Confirm that the run completes with the expected number of iterations.
- [x] Confirm the best portfolio weights are non-negative and sum to one.
- [x] Confirm the same seed and configuration produce the same optimization
  result.
- [x] Decide which values are required in the final run result:
  expected return, risk, fitness, penalty, feasibility, and weights.

Useful checks:

```sh
cargo test
cargo fmt --check
cargo clippy --all-targets --all-features
just dev-bound
just dev-single
```

Do not start frontier execution until this phase is understood and repeatable.

## Phase 2: Store one complete run

Goal: persist one execution and all data needed to inspect it later.

Add a database migration for a minimal hierarchy:

```text
run
├── run_iterations
└── run_particle_iterations
```

The run row should have an ID and contain:

- seed
- target return
- dataset/config information used by the run
- start and finish timestamps
- requested and completed iterations
- total evaluations
- duration
- stop reason
- final fitness, expected return, risk, penalty, feasibility, and weights

The iteration table should use `(run_id, iteration)` as its identity and store
the fields from `IterationRecord`.

The particle table should use
`(run_id, iteration, particle_id)` as its identity and store the fields from
`ParticleRecord`.

For the first version, store vectors such as weights, positions, velocities,
and per-dimension standard deviations as PostgreSQL `DOUBLE PRECISION[]`.
The asset order must be stored with the run or its dataset because vector
indexes only have meaning relative to that order.

Implementation order:

1. Define the migration and reversible down migration.
2. Add repository functions to create a run and update its final status.
3. Add repository functions to insert iteration and particle records.
4. Connect `MemoryRecorder` output and `RunResult` to those functions.
5. Mark a run as completed only after all records are stored successfully.
6. If execution or persistence fails, mark the run as failed or return the
   error without presenting it as successful.

Acceptance check:

```text
one CLI execution
→ one run ID
→ one final run row
→ N iteration rows
→ N × swarm_size particle rows
```

## Phase 3: Inspect and validate persisted data

Goal: prove that database data matches the in-memory run.

- [ ] Retrieve a run by ID.
- [ ] Compare its final result with the values printed by the CLI.
- [ ] Confirm iteration indexes start at zero and are consecutive.
- [ ] Confirm every iteration has the expected number of particle rows.
- [ ] Confirm the final global best is represented in the run result.
- [ ] Confirm a run can be inspected after restarting the program.
- [ ] Add focused tests for repository inserts and run completion.

At this point, the system should support reliable single-run analysis without
any frontier-specific tables or orchestration.

## Phase 4: Add experiment grouping

Goal: group related runs without changing the PSO algorithm.

Add an `experiment` row above `run`:

```text
experiment
└── many runs
```

An experiment should identify the shared study configuration:

- name or description
- asset list and date range
- PSO configuration
- fitness and velocity configuration
- algorithm/application version
- creation time

Each run keeps its own seed and target return. Do not rely only on the current
configuration file, because it may change after the run is created.

The application-level experiment runner should:

1. Create an experiment.
2. Generate target-return values.
3. Generate one or more seeds for each target.
4. Execute and persist each run.
5. Leave frontier selection as a separate final step.

The `Pso` type should remain responsible only for one optimization. It should
not create experiment IDs or decide how multiple runs are selected.

## Phase 5: Run a target-return sweep

Goal: generate candidate solutions across the expected-return range.

For the first frontier version:

- Calculate minimum and maximum target returns.
- Generate a fixed number of target-return points between those bounds.
- Run one seed per point first.
- Persist every run under the same experiment.
- Review the results before adding multiple seeds.

After that works:

- Add a configurable number of seeds per target point.
- Keep every run.
- Select the best feasible run for each target point, usually the lowest-risk
  result.

## Phase 6: Store derived frontier points

Goal: make the selected frontier easy to query without losing raw runs.

Add a derived `frontier_points` table containing:

- experiment ID
- target return
- selected run ID
- expected return
- risk
- fitness
- feasibility
- weights
- selection method

Frontier points should be recomputable from stored runs. Never use them as a
replacement for raw run data.

Start with a target-return sweep. Later, if needed, add Pareto-frontier
filtering across all feasible run results.

## Stop conditions

Pause and inspect the design if any of these become unclear:

- A run cannot be reproduced from its stored configuration and seed.
- The asset order is not known when reading stored weight vectors.
- The recorder snapshot timing no longer matches the meaning of its fields.
- A failed run can appear as completed.
- Frontier selection requires deleting or overwriting raw runs.

The priority is: **one correct persisted run first, then many runs, then
frontier selection**.
