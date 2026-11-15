//! Observer pattern for recording PSO runs.
//!
//! The PSO engine does not know where data goes. At a fixed point of each
//! iteration it hands a read-only [`IterationSnapshot`] to a [`RunRecorder`].
//! Swapping the recorder changes what is stored without touching the algorithm.

use std::time::Duration;

use ndarray::Array1;

use super::particle::Particle;

/// Converts a metric to the database representation convention.
///
/// The recorder retains non-finite values as `f64`; persistence can map them
/// to SQL NULL with this helper.
pub fn finite_or_none(value: f64) -> Option<f64> {
    value.is_finite().then_some(value)
}

/// Read-only view of the swarm at a single iteration.
///
/// The snapshot is taken **after** fitness evaluation and global-best update,
/// and **before** particles move. Therefore, for every particle:
///
/// * `position` is the position that was just evaluated.
/// * `eval` is the evaluation of that position.
/// * `velocity` is the velocity that produced that position
///   (all zeros at iteration 0).
///
/// It borrows the swarm, so building it allocates nothing.
pub struct IterationSnapshot<'a> {
    /// Zero-based iteration index.
    pub iter: usize,
    /// Whole swarm. Index in the slice is the stable `particle_id`.
    pub swarm: &'a [Particle],
    /// Global best particle after this iteration's update.
    pub gbest: &'a Particle,
    /// Whether the global best improved in this iteration.
    /// Always `true` at iteration 0 if any evaluation is finite.
    pub gbest_improved: bool,
    /// Number of particles that improved their personal best.
    pub pbest_improved: usize,
    /// Time spent evaluating the swarm and updating the global best.
    pub elapsed: Duration,
}

/// Receives one snapshot per iteration.
pub trait RunRecorder {
    fn on_iteration(&mut self, snapshot: &IterationSnapshot<'_>);
}

/// Recorder that discards everything.
pub struct NoopRecorder;

impl RunRecorder for NoopRecorder {
    fn on_iteration(&mut self, _: &IterationSnapshot<'_>) {}
}

/// Distribution summary of a set of values.
///
/// Fields are `NaN` when the input is empty.
#[derive(Debug, Clone)]
pub struct Summary {
    pub min: f64,
    pub p25: f64,
    pub median: f64,
    pub mean: f64,
    pub std: f64,
    pub p75: f64,
    pub max: f64,
}

impl Summary {
    /// Population statistics (divides by n, like the fitness function).
    pub fn of(values: &[f64]) -> Self {
        if values.is_empty() {
            return Self {
                min: f64::NAN,
                p25: f64::NAN,
                median: f64::NAN,
                mean: f64::NAN,
                std: f64::NAN,
                p75: f64::NAN,
                max: f64::NAN,
            };
        }
        let mut v = values.to_vec();
        v.sort_by(|a, b| a.total_cmp(b));

        let n = v.len() as f64;
        let mean = v.iter().sum::<f64>() / n;
        let var = v.iter().map(|x| (x - mean).powi(2)).sum::<f64>() / n;

        Self {
            min: v[0],
            p25: percentile(&v, 0.25),
            median: percentile(&v, 0.5),
            mean,
            std: var.sqrt(),
            p75: percentile(&v, 0.75),
            max: v[v.len() - 1],
        }
    }
}

/// Percentile with linear interpolation. `sorted` must be non-empty and sorted.
fn percentile(sorted: &[f64], q: f64) -> f64 {
    let pos = q * (sorted.len() - 1) as f64;
    let lo = pos.floor() as usize;
    let hi = pos.ceil() as usize;
    sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo as f64)
}

/// One row per iteration of a run.
#[derive(Debug, Clone)]
pub struct IterationRecord {
    pub iter: usize,

    // Global best
    pub gbest_fitness: f64,
    pub gbest_return: f64,
    pub gbest_risk: f64,
    pub gbest_shortfall: f64,
    pub gbest_penalty: f64,
    pub gbest_feasible: bool,
    pub gbest_position: Vec<f64>,
    pub gbest_improved: bool,

    // Swarm fitness distribution (finite values only)
    pub fitness: Summary,
    pub pbest_fitness_mean: f64,

    // Diversity
    pub dist_to_centroid_mean: f64,
    pub pairwise_dist_mean: f64,
    pub position_std_per_dim: Vec<f64>,

    // Velocity
    pub velocity_norm_mean: f64,
    pub velocity_norm_max: f64,

    // Counts
    pub feasible_count: usize,
    pub pbest_improved: usize,
    pub non_finite_count: usize,

    pub elapsed_us: u64,
}

/// One row per particle per iteration.
#[derive(Debug, Clone)]
pub struct ParticleRecord {
    pub iter: usize,
    pub particle_id: usize,
    pub position: Vec<f64>,
    pub velocity: Vec<f64>,
    pub fitness: f64,
    pub expected_return: f64,
    pub risk: f64,
    pub penalty: f64,
    pub shortfall: f64,
    pub feasible: bool,
    pub pbest_fitness: f64,
}

/// Recorder that accumulates everything in memory.
///
/// The caller writes the records to storage once the run is finished.
pub struct MemoryRecorder {
    pub iterations: Vec<IterationRecord>,
    pub particles: Vec<ParticleRecord>,
    record_particles: bool,
}

impl MemoryRecorder {
    /// `record_particles = false` keeps only the per-iteration rows.
    pub fn new(record_particles: bool) -> Self {
        Self {
            iterations: Vec::new(),
            particles: Vec::new(),
            record_particles,
        }
    }
}

impl RunRecorder for MemoryRecorder {
    fn on_iteration(&mut self, snap: &IterationSnapshot<'_>) {
        let swarm = snap.swarm;
        let n = swarm.len();
        if n == 0 {
            return;
        }

        // Fitness distribution; non-finite evaluations are counted apart.
        let finite: Vec<f64> = swarm
            .iter()
            .map(|p| p.eval.fitness)
            .filter(|f| f.is_finite())
            .collect();
        let non_finite_count = n - finite.len();

        let pbest_finite: Vec<f64> = swarm
            .iter()
            .map(|p| p.best_eval.fitness)
            .filter(|f| f.is_finite())
            .collect();
        let pbest_fitness_mean = Summary::of(&pbest_finite).mean;

        let (dist_to_centroid_mean, pairwise_dist_mean, position_std_per_dim) = diversity(swarm);

        let norms: Vec<f64> = swarm
            .iter()
            .map(|p| p.velocity.dot(&p.velocity).sqrt())
            .collect();

        self.iterations.push(IterationRecord {
            iter: snap.iter,
            gbest_fitness: snap.gbest.best_eval.fitness,
            gbest_return: snap.gbest.best_eval.expected_return,
            gbest_risk: snap.gbest.best_eval.risk,
            gbest_shortfall: snap.gbest.best_eval.shortfall,
            gbest_penalty: snap.gbest.best_eval.penalty,
            gbest_feasible: snap.gbest.best_eval.feasible,
            gbest_position: snap.gbest.best_position.to_vec(),
            gbest_improved: snap.gbest_improved,
            fitness: Summary::of(&finite),
            pbest_fitness_mean,
            dist_to_centroid_mean,
            pairwise_dist_mean,
            position_std_per_dim,
            velocity_norm_mean: norms.iter().sum::<f64>() / n as f64,
            velocity_norm_max: norms.iter().copied().fold(f64::NAN, f64::max),
            feasible_count: swarm.iter().filter(|p| p.eval.feasible).count(),
            pbest_improved: snap.pbest_improved,
            non_finite_count,
            elapsed_us: snap.elapsed.as_micros() as u64,
        });

        if self.record_particles {
            self.particles
                .extend(swarm.iter().enumerate().map(|(id, p)| ParticleRecord {
                    iter: snap.iter,
                    particle_id: id,
                    position: p.position.to_vec(),
                    velocity: p.velocity.to_vec(),
                    fitness: p.eval.fitness,
                    expected_return: p.eval.expected_return,
                    risk: p.eval.risk,
                    penalty: p.eval.penalty,
                    shortfall: p.eval.shortfall,
                    feasible: p.eval.feasible,
                    pbest_fitness: p.best_eval.fitness,
                }));
        }
    }
}

/// Returns (mean distance to centroid, mean pairwise distance, std per dimension).
fn diversity(swarm: &[Particle]) -> (f64, f64, Vec<f64>) {
    let n = swarm.len();
    let dim = swarm[0].position.len();
    let nf = n as f64;

    let mut centroid = Array1::<f64>::zeros(dim);
    for p in swarm {
        centroid += &p.position;
    }
    centroid /= nf;

    let dist = |a: &Array1<f64>, b: &Array1<f64>| -> f64 {
        let d = a - b;
        d.dot(&d).sqrt()
    };

    let to_centroid = swarm
        .iter()
        .map(|p| dist(&p.position, &centroid))
        .sum::<f64>()
        / nf;

    let mut pair_sum = 0.0;
    let mut pairs = 0usize;
    for i in 0..n {
        for j in (i + 1)..n {
            pair_sum += dist(&swarm[i].position, &swarm[j].position);
            pairs += 1;
        }
    }
    let pairwise = if pairs > 0 {
        pair_sum / pairs as f64
    } else {
        0.0
    };

    let std_per_dim = (0..dim)
        .map(|d| {
            let var = swarm
                .iter()
                .map(|p| (p.position[d] - centroid[d]).powi(2))
                .sum::<f64>()
                / nf;
            var.sqrt()
        })
        .collect();

    (to_centroid, pairwise, std_per_dim)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn summary_matches_hand_computation() {
        let s = Summary::of(&[1.0, 2.0, 3.0, 4.0, 5.0]);
        assert_eq!(s.min, 1.0);
        assert_eq!(s.median, 3.0);
        assert_eq!(s.max, 5.0);
        assert_eq!(s.mean, 3.0);
        assert!((s.p25 - 2.0).abs() < 1e-12);
        assert!((s.p75 - 4.0).abs() < 1e-12);
        // population std of 1..5 is sqrt(2)
        assert!((s.std - 2f64.sqrt()).abs() < 1e-12);
    }

    #[test]
    fn summary_of_empty_is_nan() {
        assert!(Summary::of(&[]).mean.is_nan());
    }

    #[test]
    fn finite_or_none_maps_only_non_finite_values_to_none() {
        assert_eq!(finite_or_none(1.5), Some(1.5));
        assert_eq!(finite_or_none(f64::NAN), None);
        assert_eq!(finite_or_none(f64::INFINITY), None);
        assert_eq!(finite_or_none(f64::NEG_INFINITY), None);
    }
}
