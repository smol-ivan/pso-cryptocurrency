pub fn algorithm_version() -> String {
    let dirty_suffix = if env!("GIT_DIRTY") == "true" {
        ".dirty"
    } else {
        ""
    };
    format!(
        "{}+{}{}",
        env!("CARGO_PKG_VERSION"),
        env!("GIT_HASH"),
        dirty_suffix
    )
}

#[cfg(test)]
mod tests {
    use super::algorithm_version;

    #[test]
    fn version_has_package_and_git_components() {
        let version = algorithm_version();
        let (package, revision) = version.split_once('+').expect("version separator");
        assert_eq!(package, env!("CARGO_PKG_VERSION"));
        assert!(!revision.is_empty());
        let hash = revision.strip_suffix(".dirty").unwrap_or(revision);
        assert!(!hash.is_empty());
        assert!(hash == "unknown" || hash.chars().all(|character| character.is_ascii_hexdigit()));
    }
}
