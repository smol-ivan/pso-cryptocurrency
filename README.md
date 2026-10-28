# PSO cryptocurrency
## Essential commands
### Environment setup
```sh
$ uv sync
```

### Run

```sh
# Legacy dashboard
uv run streamlit run dashboards/legacy/app.py

# Revamp / v2.0 dashboard (entry point reserved for its implementation)
# uv run streamlit run dashboards/v2/app.py

# Independent validation dashboard
uv run streamlit run dashboards/validation/validation_dashboard.py
```

`src/` contains the dashboard-independent PSO algorithm, experiment services,
portfolio metrics, persistence and data-loading logic. `dashboards/` contains
independent interface code: `legacy/` is the current dashboard, `v2/` is
reserved for the new main version, and `validation/` contains the diagnostic
dashboard.
