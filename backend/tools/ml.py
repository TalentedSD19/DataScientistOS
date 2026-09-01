from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from backend.tools.registry import get_dataset


def _load_dataframe(dataset: str) -> pd.DataFrame:
    import sqlite3

    dataset_info = get_dataset(dataset)

    if dataset_info["type"] != "sqlite":
        raise ValueError(
            "Only sqlite datasets are supported currently"
        )

    connection = sqlite3.connect(
        dataset_info["path"]
    )

    try:
        tables = pd.read_sql_query(
            """
            SELECT name
            FROM sqlite_master
            WHERE type = 'table'
            ORDER BY name
            """,
            connection,
        )

        if tables.empty:
            raise ValueError("No tables found")

        table_name = tables.iloc[0]["name"]

        return pd.read_sql_query(
            f'SELECT * FROM "{table_name}"',
            connection,
        )

    finally:
        connection.close()


def train_model(
    dataset: str,
    target: str,
    features: list[str],
    model_type: str,
) -> dict[str, Any]:
    dataframe = _load_dataframe(dataset)

    if target not in dataframe.columns:
        raise ValueError(
            f"Unknown target column: {target}"
        )

    missing_features = [
        feature
        for feature in features
        if feature not in dataframe.columns
    ]

    if missing_features:
        raise ValueError(
            f"Unknown feature columns: {missing_features}"
        )

    leakage_warnings: list[str] = []

    target_lower = target.lower()

    for feature in features:
        feature_lower = feature.lower()

        if feature_lower == target_lower:
            leakage_warnings.append(
                f"Feature '{feature}' is identical to target"
            )

        if target_lower in feature_lower:
            leakage_warnings.append(
                f"Feature '{feature}' may be target-derived"
            )

    x = dataframe[features].copy()
    y = dataframe[target].copy()

    if y.nunique(dropna=True) < 2:
        raise ValueError(
            "Target must contain at least two classes"
        )

    numeric_features = x.select_dtypes(
        include=["number"]
    ).columns.tolist()

    categorical_features = [
        column
        for column in x.columns
        if column not in numeric_features
    ]

    numeric_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="median"),
            ),
            (
                "scaler",
                StandardScaler(),
            ),
        ]
    )

    categorical_pipeline = Pipeline(
        steps=[
            (
                "imputer",
                SimpleImputer(strategy="most_frequent"),
            ),
            (
                "onehot",
                OneHotEncoder(
                    handle_unknown="ignore"
                ),
            ),
        ]
    )

    preprocessing = ColumnTransformer(
        transformers=[
            (
                "num",
                numeric_pipeline,
                numeric_features,
            ),
            (
                "cat",
                categorical_pipeline,
                categorical_features,
            ),
        ]
    )

    x_train, x_test, y_train, y_test = train_test_split(
        x,
        y,
        test_size=0.25,
        random_state=42,
        stratify=y,
    )

    majority_class = y_train.mode().iloc[0]

    baseline_predictions = np.repeat(
        majority_class,
        len(y_test),
    )

    baseline_accuracy = accuracy_score(
        y_test,
        baseline_predictions,
    )

    baseline_f1 = f1_score(
        y_test,
        baseline_predictions,
        average="weighted",
        zero_division=0,
    )

    baseline_metrics = {
        "accuracy": float(baseline_accuracy),
        "f1_weighted": float(baseline_f1),
    }

    if model_type == "logistic_regression":
        estimator = LogisticRegression(
            max_iter=1000,
        )

    elif model_type == "random_forest":
        estimator = RandomForestClassifier(
            n_estimators=100,
            random_state=42,
        )

    else:
        raise ValueError(
            "model_type must be "
            "'logistic_regression' or 'random_forest'"
        )

    pipeline = Pipeline(
        steps=[
            ("preprocess", preprocessing),
            ("model", estimator),
        ]
    )

    pipeline.fit(
        x_train,
        y_train,
    )

    predictions = pipeline.predict(x_test)

    metrics = {
        "accuracy": float(
            accuracy_score(
                y_test,
                predictions,
            )
        ),
        "f1_weighted": float(
            f1_score(
                y_test,
                predictions,
                average="weighted",
                zero_division=0,
            )
        ),
    }

    beats_baseline = (
        metrics["accuracy"]
        > baseline_metrics["accuracy"]
    )

    return {
        "model": model_type,
        "metrics": metrics,
        "baseline_metrics": baseline_metrics,
        "beats_baseline": bool(beats_baseline),
        "train_size": int(len(x_train)),
        "test_size": int(len(x_test)),
        "features": features,
        "leakage_warnings": leakage_warnings,
    }