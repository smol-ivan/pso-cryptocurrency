import pickle
from pathlib import Path
from typing import Any


ARTIFACTS_DIR = Path("artifacts")
EXPERIMENTS_FILE = ARTIFACTS_DIR / "experiments.pkl"


def save_experiments(payload: dict[str, Any]) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with EXPERIMENTS_FILE.open("wb") as file:
        pickle.dump(payload, file)


def load_experiments() -> dict[str, Any] | None:
    if not EXPERIMENTS_FILE.exists():
        return None
    with EXPERIMENTS_FILE.open("rb") as file:
        return pickle.load(file)
