from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"


DATASETS = {
    "dataset_001": {
        "id": "dataset_001",
        "name": "demo",
        "type": "sqlite",
        "path": DATA_DIR / "demo.db",
    }
}


def get_dataset(dataset_id: str) -> dict:
    dataset = DATASETS.get(dataset_id)

    if dataset is None:
        raise ValueError(f"Unknown dataset: {dataset_id}")

    path = Path(dataset["path"])

    if not path.exists():
        raise FileNotFoundError(f"Dataset file does not exist: {path}")

    return dataset


def list_datasets() -> list[dict]:
    return [
        {
            "id": dataset["id"],
            "name": dataset["name"],
            "type": dataset["type"],
        }
        for dataset in DATASETS.values()
    ]