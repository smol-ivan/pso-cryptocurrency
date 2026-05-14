import pickle
from pathlib import Path

from src.models.state import ExperimentsPayload


ARTIFACTS_DIR = Path("artifacts")
EXPERIMENTS_FILE = ARTIFACTS_DIR / "experiments.pkl"


def save_experiments(payload: ExperimentsPayload) -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    with EXPERIMENTS_FILE.open("wb") as file:
        pickle.dump(payload, file)


def load_experiments() -> ExperimentsPayload | None:
    if not EXPERIMENTS_FILE.exists():
        return None
    with EXPERIMENTS_FILE.open("rb") as file:
        payload = pickle.load(file)

    if isinstance(payload, ExperimentsPayload):
        return payload
    if isinstance(payload, dict):
        return ExperimentsPayload.from_dict(payload)
    raise TypeError(f"Unsupported experiments payload type: {type(payload)!r}")
