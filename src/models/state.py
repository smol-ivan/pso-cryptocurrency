from dataclasses import dataclass

import numpy as np
import pandas as pd

from src.experiments import ExperimentResult


@dataclass
class ExperimentsPayload:
    assets: list[str]
    start_date: str
    end_date: str
    interval: str
    alpha: float
    returns_matrix: np.ndarray
    returns_index: pd.Index
    experiments: list[ExperimentResult]
    metrics_by_config: dict[str, pd.DataFrame]
    bt_returns_matrix: np.ndarray | None = None
    bt_returns_index: pd.Index | None = None

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "ExperimentsPayload":
        return cls(
            assets=payload["assets"],
            start_date=payload["start_date"],
            end_date=payload["end_date"],
            interval=payload["interval"],
            alpha=payload["alpha"],
            returns_matrix=payload["returns_matrix"],
            returns_index=payload["returns_index"],
            experiments=payload["experiments"],
            metrics_by_config=payload["metrics_by_config"],
            bt_returns_matrix=payload.get("bt_returns_matrix"),
            bt_returns_index=payload.get("bt_returns_index"),
        )
