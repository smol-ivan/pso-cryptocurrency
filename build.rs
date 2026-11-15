use std::process::Command;

fn command_output(command: &str, args: &[&str]) -> Option<String> {
    let output = Command::new(command).args(args).output().ok()?;
    output
        .status
        .success()
        .then(|| String::from_utf8_lossy(&output.stdout).trim().to_owned())
}

fn main() {
    println!("cargo:rerun-if-changed=.git/HEAD");
    println!("cargo:rerun-if-changed=.git/index");
    println!("cargo:rerun-if-changed=.git/refs");
    println!("cargo:rerun-if-changed=src");
    // Dirty-state detection is evaluated when build.rs runs and can be stale
    // if files change without triggering one of the paths above.

    let git_hash = command_output("git", &["rev-parse", "--short=7", "HEAD"])
        .filter(|hash| !hash.is_empty())
        .or_else(|| std::env::var("GIT_HASH").ok())
        .unwrap_or_else(|| "unknown".to_owned());
    let git_dirty = command_output("git", &["status", "--porcelain"])
        .map(|status| !status.is_empty())
        .or_else(|| {
            std::env::var("GIT_DIRTY")
                .ok()
                .map(|value| value == "true" || value == "1")
        })
        .unwrap_or(false);

    println!("cargo:rustc-env=GIT_HASH={git_hash}");
    println!("cargo:rustc-env=GIT_DIRTY={git_dirty}");
}
