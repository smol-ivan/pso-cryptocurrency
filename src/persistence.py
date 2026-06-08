import io
import json
import zipfile
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from src.models.state import ExperimentsPayload
from src.experiments import ExperimentConfig, ExperimentResult
from src.run_pso import EfficientFrontier

ARTIFACTS_DIR = Path("artifacts")
EXPERIMENTS_FILE = ARTIFACTS_DIR / "experiments.psodata"
LEGACY_PICKLE = ARTIFACTS_DIR / "experiments.pkl"


def _ensure_dir() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)


def _isoify(value: Any) -> Any:
    """Convert dates to ISO strings for JSON encoding."""
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def _serialize_config(config: ExperimentConfig) -> dict:
    return {
        "name": config.name,
        "objective_name": config.objective_name,
        "velocity_name": config.velocity_name,
        "topology_name": config.topology_name,
        "num_points": config.num_points,
        "n_swarm": config.n_swarm,
        "epsilon": config.epsilon,
        "seed": config.seed,
        "fitness_function": {"__class__": config.fitness_function.__class__.__name__, **vars(config.fitness_function)},
        "velocity_model": {"__class__": config.velocity_model.__class__.__name__, **vars(config.velocity_model)},
        "topology": {"__class__": config.topology.__class__.__name__, **vars(config.topology)},
    }


def _deserialize_config(d: dict) -> ExperimentConfig:
    # Import concrete classes lazily to avoid circular imports on module load.
    from src.pso import CVaR, VaR, Variance, Semivariance, MaxDrawdown, Inertia, Constriction, RingTopology, GlobalTopology

    ff = d.get("fitness_function", {})
    vm = d.get("velocity_model", {})
    tp = d.get("topology", {})

    # map class name to constructor and kwargs
    def build(obj: dict):
        cls_name = obj.get("__class__")
        kwargs = {k: v for k, v in obj.items() if k != "__class__"}
        # Handle known classes and any attribute-name mismatches
        if cls_name == "CVaR":
            return CVaR(**kwargs)
        if cls_name == "VaR":
            return VaR(**kwargs)
        if cls_name == "Variance":
            return Variance(**kwargs)
        if cls_name == "Semivariance":
            return Semivariance(**kwargs)
        if cls_name == "MaxDrawdown":
            return MaxDrawdown(**kwargs)
        if cls_name == "Inertia":
            return Inertia(**kwargs)
        if cls_name == "Constriction":
            return Constriction(**kwargs)
        if cls_name == "RingTopology":
            # Older serialization used attribute name 'neighbors'; constructor expects 'k_neighbors'
            if "neighbors" in kwargs and "k_neighbors" not in kwargs:
                kwargs["k_neighbors"] = kwargs.pop("neighbors")
            return RingTopology(**kwargs)
        if cls_name == "GlobalTopology":
            return GlobalTopology(**kwargs)
        # Unknown: leave as raw dict
        return obj

    fitness_function = build(ff) if ff else None
    velocity_model = build(vm) if vm else None
    topology = build(tp) if tp else None

    return ExperimentConfig(
        name=d["name"],
        objective_name=d["objective_name"],
        velocity_name=d["velocity_name"],
        topology_name=d["topology_name"],
        fitness_function=fitness_function,
        velocity_model=velocity_model,
        topology=topology,
        num_points=d.get("num_points", 30),
        n_swarm=d.get("n_swarm", 100),
        epsilon=d.get("epsilon", 1e-5),
        seed=d.get("seed"),
    )


def export_payload_to_bytes(payload: dict) -> bytes:
    """Serialize payload into a .psodata (zip) in-memory and return bytes.

    Expected payload keys: assets, start_date, end_date, interval, alpha,
    returns_matrix (np.ndarray), returns_index (pd.Index), experiments (list),
    metrics_by_config (dict[str, pd.DataFrame]), bt_returns_matrix, bt_returns_index
    """
    bio = io.BytesIO()
    with zipfile.ZipFile(bio, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        metadata: dict[str, Any] = {}

        # Simple fields
        for key in ("assets", "start_date", "end_date", "interval", "alpha"):
            val = getattr(payload, key, None) if not isinstance(payload, dict) else payload.get(key)
            if val is None:
                continue
            if hasattr(val, "isoformat"):
                metadata[key] = val.isoformat()
            else:
                metadata[key] = val

        # Numpy arrays
        def _write_array(name: str, arr: Any):
            if arr is None:
                return
            buf = io.BytesIO()
            np.save(buf, arr, allow_pickle=False)
            zf.writestr(f"arrays/{name}.npy", buf.getvalue())
            metadata[f"arrays/{name}"] = f"arrays/{name}.npy"

        returns_matrix = getattr(payload, "returns_matrix", None) if not isinstance(payload, dict) else payload.get("returns_matrix")
        _write_array("returns_matrix", returns_matrix)

        bt_returns_matrix = getattr(payload, "bt_returns_matrix", None) if not isinstance(payload, dict) else payload.get("bt_returns_matrix")
        _write_array("bt_returns_matrix", bt_returns_matrix)

        # Indexes
        def _serialize_index(idx: Any) -> Any:
            if idx is None:
                return None
            if isinstance(idx, pd.Index):
                lst = idx.to_list()
            else:
                lst = list(idx)
            return [i.isoformat() if hasattr(i, "isoformat") else i for i in lst]

        returns_index = getattr(payload, "returns_index", None) if not isinstance(payload, dict) else payload.get("returns_index")
        metadata["returns_index"] = _serialize_index(returns_index)

        bt_returns_index = getattr(payload, "bt_returns_index", None) if not isinstance(payload, dict) else payload.get("bt_returns_index")
        metadata["bt_returns_index"] = _serialize_index(bt_returns_index)

        # DataFrames
        metrics = getattr(payload, "metrics_by_config", None) if not isinstance(payload, dict) else payload.get("metrics_by_config")
        metadata["metrics_by_config"] = {}
        if metrics:
            for name, df in metrics.items():
                buf = io.BytesIO()
                df.to_parquet(buf, index=True)
                zf.writestr(f"dataframes/{name}.parquet", buf.getvalue())
                metadata["metrics_by_config"][name] = f"dataframes/{name}.parquet"

        # Experiments (configs + frontiers)
        experiments = getattr(payload, "experiments", None) if not isinstance(payload, dict) else payload.get("experiments")
        metadata["experiments"] = []
        if experiments:
            for i, exp in enumerate(experiments):
                # exp may be ExperimentResult or dict-like
                if isinstance(exp, ExperimentResult):
                    config = exp.config
                    frontier = exp.frontier
                else:
                    # assume dict with 'config' and 'frontier'
                    config = exp.get("config")
                    frontier = exp.get("frontier")

                cfg_dict = _serialize_config(config) if isinstance(config, ExperimentConfig) else config

                # save frontier arrays
                fr_base = f"experiments/{i}"
                # target_values
                if hasattr(frontier, "target_values"):
                    buf = io.BytesIO()
                    np.save(buf, frontier.target_values, allow_pickle=False)
                    zf.writestr(f"{fr_base}/target_values.npy", buf.getvalue())
                # best_fitnesses
                if hasattr(frontier, "best_fitnesses"):
                    buf = io.BytesIO()
                    np.save(buf, frontier.best_fitnesses, allow_pickle=False)
                    zf.writestr(f"{fr_base}/best_fitnesses.npy", buf.getvalue())
                # weights (list of arrays) -> save as npz
                if hasattr(frontier, "weights") and frontier.weights is not None:
                    buf = io.BytesIO()
                    # convert list of arrays into a single 2D array if possible
                    try:
                        stacked = np.vstack(frontier.weights)
                        np.save(buf, stacked, allow_pickle=False)
                        zf.writestr(f"{fr_base}/weights.npy", buf.getvalue())
                    except Exception:
                        # fallback to npz with numbered entries
                        buf = io.BytesIO()
                        np.savez(buf, *frontier.weights)
                        zf.writestr(f"{fr_base}/weights.npz", buf.getvalue())

                # write experiment metadata
                zf.writestr(f"{fr_base}/config.json", json.dumps(cfg_dict, default=_isoify))
                metadata["experiments"].append({"config": f"{fr_base}/config.json", "frontier": fr_base})

        # Write metadata
        zf.writestr("metadata.json", json.dumps(metadata, ensure_ascii=False))

    return bio.getvalue()


def import_payload_from_bytes(data: bytes) -> dict:
    bio = io.BytesIO(data)
    payload: dict[str, Any] = {}
    with zipfile.ZipFile(bio, mode="r") as zf:
        raw_meta = zf.read("metadata.json")
        metadata = json.loads(raw_meta)

        # simple fields
        for key in ("assets", "start_date", "end_date", "interval", "alpha"):
            if key in metadata:
                payload[key] = metadata[key]

        # arrays
        def _read_array(path: str):
            try:
                b = zf.read(path)
            except KeyError:
                return None
            return np.load(io.BytesIO(b), allow_pickle=False)

        payload["returns_matrix"] = _read_array(metadata.get("arrays/returns_matrix")) if metadata.get("arrays/returns_matrix") else None
        payload["bt_returns_matrix"] = _read_array(metadata.get("arrays/bt_returns_matrix")) if metadata.get("arrays/bt_returns_matrix") else None

        # indexes
        def _read_index(lst):
            if lst is None:
                return None
            return pd.Index([pd.to_datetime(x).date() if isinstance(x, str) and "T" not in x and "-" in x else x for x in lst])

        payload["returns_index"] = _read_index(metadata.get("returns_index"))
        payload["bt_returns_index"] = _read_index(metadata.get("bt_returns_index"))

        # dataframes
        payload["metrics_by_config"] = {}
        for name, path in metadata.get("metrics_by_config", {}).items():
            b = zf.read(path)
            payload["metrics_by_config"][name] = pd.read_parquet(io.BytesIO(b))

        # experiments
        exps_meta = metadata.get("experiments", [])
        exps: list[ExperimentResult] = []
        for item in exps_meta:
            cfg_path = item.get("config")
            fr_base = item.get("frontier")
            cfg_bytes = zf.read(cfg_path)
            cfg_dict = json.loads(cfg_bytes)
            config = _deserialize_config(cfg_dict)

            # load frontier
            target = None
            best = None
            weights = None
            try:
                target = np.load(io.BytesIO(zf.read(f"{fr_base}/target_values.npy")), allow_pickle=False)
            except KeyError:
                target = None
            try:
                best = np.load(io.BytesIO(zf.read(f"{fr_base}/best_fitnesses.npy")), allow_pickle=False)
            except KeyError:
                best = None
            try:
                weights = np.load(io.BytesIO(zf.read(f"{fr_base}/weights.npy")), allow_pickle=False)
                # if stacked, each row is a weight vector -> convert to list
                weights = [row for row in weights]
            except KeyError:
                try:
                    npz = np.load(io.BytesIO(zf.read(f"{fr_base}/weights.npz")))
                    weights = [npz[f] for f in npz.files]
                except KeyError:
                    weights = None

            frontier = EfficientFrontier(target_values=target, weights=weights, best_fitnesses=best)
            exps.append(ExperimentResult(config=config, frontier=frontier))

        payload["experiments"] = exps

    return payload


def save_experiments(payload: ExperimentsPayload) -> None:
    _ensure_dir()
    # Accept both ExperimentsPayload instances and plain dicts
    if isinstance(payload, ExperimentsPayload):
        # convert to dict-like structure expected by exporter
        pld = {
            "assets": payload.assets,
            "start_date": payload.start_date,
            "end_date": payload.end_date,
            "interval": payload.interval,
            "alpha": payload.alpha,
            "returns_matrix": payload.returns_matrix,
            "returns_index": payload.returns_index,
            "experiments": payload.experiments,
            "metrics_by_config": payload.metrics_by_config,
            "bt_returns_matrix": payload.bt_returns_matrix,
            "bt_returns_index": payload.bt_returns_index,
        }
    else:
        pld = payload

    data = export_payload_to_bytes(pld)
    with EXPERIMENTS_FILE.open("wb") as f:
        f.write(data)


def load_experiments() -> ExperimentsPayload | None:
    # Prefer new format, fall back to legacy pickle for compatibility
    if EXPERIMENTS_FILE.exists():
        with EXPERIMENTS_FILE.open("rb") as f:
            data = f.read()
        payload_dict = import_payload_from_bytes(data)
        return ExperimentsPayload.from_dict(payload_dict)

    if LEGACY_PICKLE.exists():
        import pickle as _p

        with LEGACY_PICKLE.open("rb") as file:
            payload = _p.load(file)

        if isinstance(payload, ExperimentsPayload):
            return payload
        if isinstance(payload, dict):
            return ExperimentsPayload.from_dict(payload)
        raise TypeError(f"Unsupported experiments payload type: {type(payload)!r}")

    return None
