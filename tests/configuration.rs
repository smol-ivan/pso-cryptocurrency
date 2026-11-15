mod support;

use std::collections::HashMap;

use config::Environment;
use pso_cryptocurrency::config::Settings;
use pso_cryptocurrency::optimizer::pso::{
    FitnessConfig, InertiaParams, RiskConfig, VelocityConfig,
};

use support::{FULL_TOML, MINIMAL_TOML, load_toml};

/// The complete TOML shape maps to the expected values and tagged variants.
#[test]
fn deserializes_full_configuration() {
    let settings = load_toml(FULL_TOML, Environment::default(), Some("postgres://secret")).unwrap();

    assert_eq!(settings.database.max_connections, 5);
    assert_eq!(settings.database.url, "postgres://secret");
    assert_eq!(settings.dataset.tickers, ["AAPL", "NVDA"]);
    assert_eq!(settings.dataset.periods_per_year, 365.0);
    assert_eq!(settings.pso.swarm_size, 45);
    assert_eq!(settings.pso.fitness.penalty, 75.0);
    assert_eq!(settings.pso.fitness.risk, RiskConfig::Variance);
    assert_eq!(
        settings.pso.velocity,
        VelocityConfig::Inertia(InertiaParams {
            c1: 0.6,
            c2: 1.1,
            inertia: 0.7,
        })
    );
}

/// Omitting optional component sections uses each component's documented defaults.
#[test]
fn uses_defaults_for_minimal_configuration() {
    let settings = load_toml(MINIMAL_TOML, Environment::default(), Some("postgres://db")).unwrap();

    assert_eq!(settings.database.max_connections, 2);
    assert_eq!(settings.pso.fitness, FitnessConfig::default());
    assert_eq!(settings.pso.velocity, VelocityConfig::default());
}

/// Tagged enums reject unsupported component kinds instead of silently falling back.
#[test]
fn rejects_unknown_kind() {
    let text = MINIMAL_TOML.replace(
        "[single_test]",
        "[pso.velocity]\nkind = \"unknown\"\n\n[single_test]",
    );
    let error = load_toml(&text, Environment::default(), Some("postgres://db")).unwrap_err();

    assert!(error.to_string().contains("deserialize"));
}

/// Explicit environment sources make this test deterministic and avoid unsafe `set_var`.
#[test]
fn applies_environment_overrides_without_process_mutation() {
    let mut values = HashMap::new();
    values.insert("APP__PSO__SWARM_SIZE".to_owned(), "50".to_owned());
    values.insert(
        "APP__PSO__FITNESS__RISK__KIND".to_owned(),
        "variance".to_owned(),
    );
    let environment = Environment::with_prefix("APP")
        .separator("__")
        .try_parsing(true)
        .source(Some(values));

    let settings = load_toml(MINIMAL_TOML, environment, Some("postgres://db")).unwrap();
    assert_eq!(settings.pso.swarm_size, 50);
    assert_eq!(settings.pso.fitness.risk, RiskConfig::Variance);
}

/// Effective-run JSON excludes database credentials, while Debug redacts them.
#[test]
fn effective_json_and_debug_redact_database() {
    let settings = load_toml(FULL_TOML, Environment::default(), Some("postgres://secret")).unwrap();
    let json = settings.effective_config_json();

    assert!(json.get("database").is_none());
    assert!(!json.to_string().contains("postgres://secret"));
    assert!(!format!("{settings:?}").contains("postgres://secret"));
    assert!(format!("{settings:?}").contains("<redacted>"));
}

/// Loading a temporary file proves the configured path is not hardcoded to `config.toml`.
#[test]
fn loads_a_non_default_path() {
    assert!(load_toml(MINIMAL_TOML, Environment::default(), Some("postgres://db")).is_ok());
}

/// Every validation rule has a focused invalid mutation.
#[test]
fn validates_all_required_constraints() {
    let cases: Vec<(&str, fn(&mut Settings))> = vec![
        ("empty tickers", |s| s.dataset.tickers.clear()),
        ("empty ticker", |s| s.dataset.tickers[0].clear()),
        ("duplicate ticker", |s| s.dataset.tickers.push("BTC".into())),
        ("invalid dates", |s| s.dataset.end = s.dataset.start),
        ("invalid periods per year", |s| {
            s.dataset.periods_per_year = 0.0
        }),
        ("small swarm", |s| s.pso.swarm_size = 1),
        ("zero iterations", |s| s.pso.iterations = 0),
        ("zero connections", |s| s.database.max_connections = 0),
        ("negative penalty", |s| s.pso.fitness.penalty = -1.0),
        ("non-finite penalty", |s| s.pso.fitness.penalty = f64::NAN),
        ("negative eps", |s| s.pso.fitness.eps = -1.0),
        ("non-finite eps", |s| s.pso.fitness.eps = f64::INFINITY),
        ("non-finite c1", |s| velocity_params_mut(s).c1 = f64::NAN),
        ("non-finite c2", |s| {
            velocity_params_mut(s).c2 = f64::INFINITY
        }),
        ("non-finite inertia", |s| {
            velocity_params_mut(s).inertia = f64::NEG_INFINITY
        }),
        ("non-finite target", |s| {
            s.single_test.target_return = f64::NAN
        }),
    ];

    for (name, mutate) in cases {
        let mut settings =
            load_toml(MINIMAL_TOML, Environment::default(), Some("postgres://db")).unwrap();
        mutate(&mut settings);
        assert!(settings.validate().is_err(), "{name} should be rejected");
    }
}

fn velocity_params_mut(settings: &mut Settings) -> &mut InertiaParams {
    match &mut settings.pso.velocity {
        VelocityConfig::Inertia(params) => params,
    }
}
