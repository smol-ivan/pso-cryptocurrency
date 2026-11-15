mod config;
mod fitness;
mod particle;
mod recorder;
mod velocity;

pub use config::{FitnessConfig, RiskConfig, VelocityConfig};
pub use fitness::{FitnessFunction, PenalizedFitness, PenaltyParams, RiskMeasure, VarianceRisk};
pub use particle::Particle;
pub use recorder::{
    IterationRecord, IterationSnapshot, MemoryRecorder, NoopRecorder, ParticleRecord, RunRecorder,
    Summary, finite_or_none,
};
pub use velocity::{InertiaM, InertiaParams, VelocityModel};

mod pso;
pub use pso::{Pso, RunResult, StopReason};
