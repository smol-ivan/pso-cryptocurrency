use std::fs;

use anyhow::Result;
use config::Environment;
use pso_cryptocurrency::config::Settings;

pub const MINIMAL_TOML: &str = r#"
[dataset]
tickers = ["BTC"]
start = 2024-01-01T00:00:00Z
end = 2024-01-02T00:00:00Z

[pso]
swarm_size = 2
iterations = 1
seed = 42

[single_test]
target_return = 0.01
"#;

pub const FULL_TOML: &str = r#"
[database]
max_connections = 5

[dataset]
tickers = ["AAPL", "NVDA"]
start = 2024-01-01T00:00:00Z
end = 2024-01-10T23:59:59Z

[pso]
swarm_size = 45
iterations = 125
seed = 42

[pso.fitness]
penalty = 75.0
eps = 0.00001

[pso.fitness.risk]
kind = "variance"

[pso.velocity]
kind = "inertia"
c1 = 0.6
c2 = 1.1
inertia = 0.7

[single_test]
target_return = 0.01
"#;

/// Writes a temporary TOML file so tests exercise the same file loader as the CLI.
pub fn load_toml(
    contents: &str,
    environment: Environment,
    database_url: Option<&str>,
) -> Result<Settings> {
    let path = std::env::temp_dir().join(format!(
        "pso-config-{}-{}.toml",
        std::process::id(),
        unique_suffix()
    ));
    fs::write(&path, contents)?;
    let result = Settings::from_sources(
        path.to_str().expect("temporary path must be valid UTF-8"),
        environment,
        database_url.map(str::to_owned),
    );
    fs::remove_file(path)?;
    result
}

fn unique_suffix() -> u128 {
    std::time::SystemTime::now()
        .duration_since(std::time::UNIX_EPOCH)
        .expect("system clock must be after UNIX epoch")
        .as_nanos()
}
