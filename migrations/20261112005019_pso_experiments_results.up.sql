CREATE TABLE experiments (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    tickers TEXT[] NOT NULL,
    dataset_start TIMESTAMPTZ NOT NULL,
    dataset_end TIMESTAMPTZ NOT NULL,
    n_observations INTEGER NOT NULL,
    dataset_stats JSONB NOT NULL,
    config JSONB NOT NULL,
    algorithm_version TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),

    CONSTRAINT experiments_tickers_not_empty CHECK (cardinality(tickers) > 0),
    CONSTRAINT experiments_date_range_valid CHECK (dataset_start < dataset_end),
    CONSTRAINT experiments_n_observations_valid CHECK (n_observations > 0)
);

CREATE TABLE runs (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    experiment_id BIGINT NOT NULL REFERENCES experiments (id) ON DELETE CASCADE,
    seed BIGINT NOT NULL,
    target_return DOUBLE PRECISION NOT NULL,
    status TEXT NOT NULL DEFAULT 'running',
    started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    finished_at TIMESTAMPTZ,
    iterations_requested INTEGER NOT NULL,
    iterations_completed INTEGER NOT NULL DEFAULT 0,
    total_evaluations BIGINT NOT NULL DEFAULT 0,
    duration_us BIGINT,
    stop_reason TEXT,
    error_message TEXT,

    final_fitness DOUBLE PRECISION,
    final_expected_return DOUBLE PRECISION,
    final_risk DOUBLE PRECISION,
    final_penalty DOUBLE PRECISION,
    final_shortfall DOUBLE PRECISION,
    final_feasible BOOLEAN,
    final_weights DOUBLE PRECISION[],

    CONSTRAINT runs_status_valid CHECK (
        status IN ('running', 'completed', 'failed')
    ),
    CONSTRAINT runs_iterations_requested_valid CHECK (iterations_requested > 0),
    CONSTRAINT runs_iterations_completed_valid CHECK (
        iterations_completed >= 0
        AND iterations_completed <= iterations_requested
    ),
    CONSTRAINT runs_total_evaluations_valid CHECK (total_evaluations >= 0),
    CONSTRAINT runs_finished_when_not_running CHECK (
        status = 'running' OR finished_at IS NOT NULL
    ),
    CONSTRAINT runs_result_when_completed CHECK (
        status <> 'completed'
        OR (
            final_fitness IS NOT NULL
            AND final_expected_return IS NOT NULL
            AND final_risk IS NOT NULL
            AND final_penalty IS NOT NULL
            AND final_shortfall IS NOT NULL
            AND final_feasible IS NOT NULL
            AND final_weights IS NOT NULL
        )
    ),
    CONSTRAINT runs_completed_finite_results CHECK (
        status <> 'completed'
        OR (
            final_fitness NOT IN ('NaN', 'Infinity', '-Infinity')
            AND final_risk NOT IN ('NaN', 'Infinity', '-Infinity')
            AND final_expected_return NOT IN ('NaN', 'Infinity', '-Infinity')
            AND final_penalty NOT IN ('NaN', 'Infinity', '-Infinity')
            AND final_shortfall NOT IN ('NaN', 'Infinity', '-Infinity')
        )
    ),
    CONSTRAINT runs_failed_requires_error CHECK (
        status <> 'failed' OR error_message IS NOT NULL
    )
);

CREATE INDEX runs_experiment_id_idx ON runs (experiment_id);
CREATE INDEX runs_experiment_target_return_idx
    ON runs (experiment_id, target_return);

CREATE TABLE run_iterations (
    run_id BIGINT NOT NULL REFERENCES runs (id) ON DELETE CASCADE,
    iteration INTEGER NOT NULL,
    gbest_fitness DOUBLE PRECISION,
    gbest_return DOUBLE PRECISION,
    gbest_risk DOUBLE PRECISION,
    gbest_shortfall DOUBLE PRECISION,
    gbest_penalty DOUBLE PRECISION,
    gbest_feasible BOOLEAN NOT NULL,
    gbest_position DOUBLE PRECISION[] NOT NULL,
    gbest_improved BOOLEAN NOT NULL,

    fitness_min DOUBLE PRECISION,
    fitness_p25 DOUBLE PRECISION,
    fitness_median DOUBLE PRECISION,
    fitness_mean DOUBLE PRECISION,
    fitness_std DOUBLE PRECISION,
    fitness_p75 DOUBLE PRECISION,
    fitness_max DOUBLE PRECISION,
    pbest_fitness_mean DOUBLE PRECISION,

    dist_to_centroid_mean DOUBLE PRECISION NOT NULL,
    pairwise_dist_mean DOUBLE PRECISION NOT NULL,
    position_std_per_dim DOUBLE PRECISION[] NOT NULL,

    velocity_norm_mean DOUBLE PRECISION NOT NULL,
    velocity_norm_max DOUBLE PRECISION NOT NULL,
    feasible_count INTEGER NOT NULL,
    pbest_improved INTEGER NOT NULL,
    non_finite_count INTEGER NOT NULL,
    elapsed_us BIGINT NOT NULL,

    PRIMARY KEY (run_id, iteration),
    CONSTRAINT run_iterations_iteration_valid CHECK (iteration >= 0),
    CONSTRAINT run_iterations_counts_valid CHECK (
        feasible_count >= 0
        AND pbest_improved >= 0
        AND non_finite_count >= 0
    ),
    CONSTRAINT run_iterations_elapsed_valid CHECK (elapsed_us >= 0)
);

CREATE TABLE run_particle_iterations (
    run_id BIGINT NOT NULL,
    iteration INTEGER NOT NULL,
    particle_id INTEGER NOT NULL,
    position DOUBLE PRECISION[] NOT NULL,
    velocity DOUBLE PRECISION[] NOT NULL,
    fitness DOUBLE PRECISION,
    expected_return DOUBLE PRECISION,
    risk DOUBLE PRECISION,
    penalty DOUBLE PRECISION,
    shortfall DOUBLE PRECISION,
    feasible BOOLEAN NOT NULL,
    pbest_fitness DOUBLE PRECISION,

    PRIMARY KEY (run_id, iteration, particle_id),
    FOREIGN KEY (run_id, iteration)
        REFERENCES run_iterations (run_id, iteration)
        ON DELETE CASCADE,
    CONSTRAINT run_particle_iterations_iteration_valid CHECK (iteration >= 0),
    CONSTRAINT run_particle_iterations_particle_valid CHECK (particle_id >= 0)
);

CREATE VIEW run_particle_weights AS
SELECT p.run_id, p.iteration, p.particle_id, u.ticker, u.weight
FROM run_particle_iterations p
JOIN runs r ON r.id = p.run_id
JOIN experiments e ON e.id = r.experiment_id
CROSS JOIN LATERAL unnest(e.tickers, p.position) AS u(ticker, weight);

COMMENT ON TABLE experiments IS 'Immutable configuration and dataset snapshot for an experiment.';
COMMENT ON COLUMN experiments.tickers IS 'Asset tickers in the same order as dataset return columns and portfolio weights.';
COMMENT ON COLUMN experiments.n_observations IS 'Number of observations in the dataset snapshot; must be positive.';
COMMENT ON COLUMN experiments.dataset_stats IS 'Dataset statistics snapshot, including population covariance (ddof=0).';
COMMENT ON COLUMN experiments.config IS 'Effective non-secret configuration used by the experiment.';
COMMENT ON TABLE runs IS 'One execution of an experiment.';
COMMENT ON COLUMN runs.seed IS 'Unsigned application seed stored as BIGINT; values must be <= i64::MAX.';
COMMENT ON COLUMN runs.status IS 'Run lifecycle state: running, completed, or failed.';
COMMENT ON COLUMN runs.final_weights IS 'Final global-best allocation snapshot taken when the run completed.';
COMMENT ON COLUMN runs.error_message IS 'Failure detail; required when status is failed.';
COMMENT ON TABLE run_iterations IS 'Global-best and swarm statistics snapshot after evaluation and before particles move.';
COMMENT ON COLUMN run_iterations.gbest_position IS 'Global-best position at this iteration snapshot.';
COMMENT ON COLUMN run_iterations.fitness_std IS 'Population standard deviation (ddof=0) of finite particle fitness values.';
COMMENT ON COLUMN run_iterations.fitness_min IS 'Minimum finite particle fitness; NULL when no finite values exist.';
COMMENT ON COLUMN run_iterations.fitness_p25 IS '25th percentile of finite particle fitness; NULL when no finite values exist.';
COMMENT ON COLUMN run_iterations.fitness_median IS 'Median of finite particle fitness; NULL when no finite values exist.';
COMMENT ON COLUMN run_iterations.fitness_mean IS 'Mean of finite particle fitness; NULL when no finite values exist.';
COMMENT ON COLUMN run_iterations.fitness_p75 IS '75th percentile of finite particle fitness; NULL when no finite values exist.';
COMMENT ON COLUMN run_iterations.fitness_max IS 'Maximum finite particle fitness; NULL when no finite values exist.';
COMMENT ON COLUMN run_iterations.pbest_fitness_mean IS 'Mean of finite personal-best fitness values; NULL when no finite values exist.';
COMMENT ON TABLE run_particle_iterations IS 'Particle state snapshot after evaluation and before movement.';
COMMENT ON COLUMN run_particle_iterations.fitness IS 'Current fitness; NULL when it is not finite.';
COMMENT ON COLUMN run_particle_iterations.expected_return IS 'Current expected return; NULL when it is not finite.';
COMMENT ON COLUMN run_particle_iterations.risk IS 'Current risk; NULL when it is not finite.';
COMMENT ON COLUMN run_particle_iterations.penalty IS 'Current target shortfall penalty; NULL when it is not finite.';
COMMENT ON COLUMN run_particle_iterations.shortfall IS 'Current target-return shortfall; NULL when it is not finite.';
COMMENT ON COLUMN run_particle_iterations.pbest_fitness IS 'Personal-best fitness; NULL when the particle has not obtained a finite improvement.';
COMMENT ON VIEW run_particle_weights IS 'Portfolio weights expanded in the experiment ticker order.';
