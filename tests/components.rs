use pso_cryptocurrency::optimizer::pso::{FitnessConfig, VelocityConfig};

/// Builders preserve the effective defaults used before configuration was split.
#[test]
fn default_component_builders_preserve_effective_parameters() {
    assert_eq!(
        FitnessConfig::default().build().params(),
        serde_json::json!({
            "penalty": 50.0,
            "eps": 1e-6,
            "risk": {
                "name": "variance",
                "params": {},
            },
        })
    );
    assert_eq!(
        VelocityConfig::default().build().params(),
        serde_json::json!({
            "c1": 0.5,
            "c2": 0.9,
            "inertia": 0.8,
        })
    );
}
