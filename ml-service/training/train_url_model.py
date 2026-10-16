from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
)
from sklearn.model_selection import GroupShuffleSplit

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.url_features import URL_FEATURES, extract_url_features, parse_url  # noqa: E402


def _feature_frame(urls: list[str]) -> pd.DataFrame:
    return pd.DataFrame(
        [extract_url_features(url) for url in urls],
        columns=URL_FEATURES,
    )


def _host_group(url: str) -> str:
    try:
        hostname = parse_url(url)[1].strip("[]")
        try:
            import ipaddress

            ipaddress.ip_address(hostname)
            return hostname
        except ValueError:
            labels = hostname.split(".")
            two_label_suffixes = {
                "co.uk",
                "com.au",
                "co.in",
                "co.jp",
                "com.br",
                "com.cn",
                "co.nz",
            }
            suffix = ".".join(labels[-2:]) if len(labels) >= 2 else hostname
            count = 3 if suffix in two_label_suffixes and len(labels) >= 3 else 2
            return ".".join(labels[-count:])
    except ValueError:
        return ""


def _best_f1_threshold(labels: np.ndarray, scores: np.ndarray) -> tuple[float, float]:
    precision, recall, thresholds = precision_recall_curve(labels, scores)
    if len(thresholds) == 0:
        raise ValueError("Cannot select a threshold from an empty validation set.")
    f1_values = (
        2 * precision[:-1] * recall[:-1] / np.maximum(precision[:-1] + recall[:-1], 1e-12)
    )
    best_index = int(np.nanargmax(f1_values))
    return float(thresholds[best_index]), float(f1_values[best_index])


def _metrics(labels: np.ndarray, scores: np.ndarray, threshold: float) -> dict:
    predicted = (scores >= threshold).astype(int)
    return {
        "precision": float(precision_score(labels, predicted, zero_division=0)),
        "recall": float(recall_score(labels, predicted, zero_division=0)),
        "f1": float(f1_score(labels, predicted, zero_division=0)),
        "pr_auc": float(average_precision_score(labels, scores)),
        "brier_score": float(brier_score_loss(labels, scores)),
        "confusion_matrix": confusion_matrix(labels, predicted, labels=[0, 1]).tolist(),
        "threshold": float(threshold),
        "sample_count": int(len(labels)),
    }


def _split_by_host(frame: pd.DataFrame, labels: np.ndarray) -> tuple[np.ndarray, ...]:
    groups = frame["URL"].map(_host_group).to_numpy()
    first = GroupShuffleSplit(n_splits=1, test_size=0.30, random_state=41)
    train_idx, remainder_idx = next(first.split(frame, labels, groups))
    remainder = frame.iloc[remainder_idx].reset_index(drop=True)
    remainder_labels = labels[remainder_idx]
    remainder_groups = remainder["URL"].map(_host_group).to_numpy()
    second = GroupShuffleSplit(n_splits=1, test_size=0.50, random_state=42)
    valid_rel, test_rel = next(second.split(remainder, remainder_labels, remainder_groups))
    return (
        train_idx,
        remainder_idx[valid_rel],
        remainder_idx[test_rel],
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train URL-only phishing baselines from the UCI PhiUSIIL dataset."
    )
    parser.add_argument("--input", default="data/raw/phiusiil.zip")
    parser.add_argument("--models-dir", default="models")
    parser.add_argument("--reports-dir", default="training/reports")
    args = parser.parse_args()
    input_path = ROOT / args.input
    if not input_path.is_file():
        raise SystemExit(
            f"Dataset not found: {input_path}. Follow docs/dataset.md to download it."
        )

    frame = pd.read_csv(input_path, usecols=["URL", "label"])
    if frame["URL"].isna().any() or frame["label"].isna().any():
        raise ValueError("URL dataset contains missing URL or label values.")
    unexpected = set(frame["label"].unique()) - {0, 1}
    if unexpected:
        raise ValueError(f"Unexpected PhiUSIIL label values: {sorted(unexpected)}")

    original_rows = len(frame)
    duplicate_count = int(frame["URL"].duplicated().sum())
    frame = frame.drop_duplicates(subset=["URL"]).reset_index(drop=True)
    frame["URL"] = frame["URL"].astype(str)
    frame = frame[frame["URL"].map(lambda item: bool(_host_group(item)))].reset_index(drop=True)
    # UCI label 0 is phishing, 1 is legitimate.
    labels = (frame["label"].astype(int) == 0).astype(int).to_numpy()
    if set(np.unique(labels)) != {0, 1}:
        raise ValueError("Training requires both legitimate and phishing labels.")

    train_idx, valid_idx, test_idx = _split_by_host(frame, labels)
    train = frame.iloc[train_idx]
    valid = frame.iloc[valid_idx]
    test = frame.iloc[test_idx]
    y_train, y_valid, y_test = labels[train_idx], labels[valid_idx], labels[test_idx]
    if any(len(np.unique(y)) != 2 for y in (y_train, y_valid, y_test)):
        raise ValueError(
            "A host-grouped split did not contain both classes. Inspect domain grouping before retraining."
        )

    x_train = _feature_frame(train["URL"].tolist())
    x_valid = _feature_frame(valid["URL"].tolist())
    x_test = _feature_frame(test["URL"].tolist())

    candidates = {
        "logistic_regression": LogisticRegression(
            max_iter=1500,
            class_weight="balanced",
            solver="liblinear",
            random_state=41,
        ),
        "random_forest": RandomForestClassifier(
            n_estimators=160,
            max_depth=20,
            min_samples_leaf=2,
            class_weight="balanced_subsample",
            n_jobs=-1,
            random_state=41,
        ),
    }
    validation_results: dict[str, dict] = {}
    fitted: dict[str, object] = {}
    for name, model in candidates.items():
        model.fit(x_train, y_train)
        scores = model.predict_proba(x_valid)[:, list(model.classes_).index(1)]
        threshold, best_f1 = _best_f1_threshold(y_valid, scores)
        validation_results[name] = {
            **_metrics(y_valid, scores, threshold),
            "best_f1": best_f1,
        }
        fitted[name] = model

    selected_name = max(validation_results, key=lambda name: validation_results[name]["best_f1"])
    selected = fitted[selected_name]
    selected_threshold = float(validation_results[selected_name]["threshold"])
    valid_scores = selected.predict_proba(x_valid)[:, list(selected.classes_).index(1)]
    # The warning band begins at the validation 95th percentile of legitimate
    # examples, capped below the high-risk decision threshold.
    legitimate_scores = valid_scores[y_valid == 0]
    suspicious_threshold = min(
        selected_threshold,
        float(np.quantile(legitimate_scores, 0.95)),
    )
    test_scores = selected.predict_proba(x_test)[:, list(selected.classes_).index(1)]
    test_metrics = _metrics(y_test, test_scores, selected_threshold)

    metadata = {
        "model_type": "url",
        "model_version": "phiusiil-url-lexical-v1",
        "dataset": {
            "name": "PhiUSIIL Phishing URL Dataset",
            "uci_dataset_id": 967,
            "source": "https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset",
            "license": "CC BY 4.0",
            "label_column": "label",
            "label_mapping": {"0": "phishing", "1": "legitimate"},
            "live_training_input": ["URL"],
            "dropped_exact_duplicate_urls": duplicate_count,
            "input_rows": original_rows,
            "rows_after_dedup_and_url_validation": int(len(frame)),
        },
        "feature_names": URL_FEATURES,
        "feature_contract": "Lexical features extracted from the URL string only; the service never visits the destination.",
        "training_config": {
            "split": "70/15/15 GroupShuffleSplit by an approximate registrable domain (final 2 labels, with a short common two-label suffix list); exact duplicate URLs removed first",
            "random_seed": 41,
            "candidate_models": list(candidates),
            "selected_model": selected_name,
            "class_weight": "balanced",
        },
        "label_mapping": {"0": "legitimate", "1": "phishing"},
        "high_threshold": selected_threshold,
        "suspicious_threshold": suspicious_threshold,
        "validation_metrics": validation_results,
        "test_metrics": test_metrics,
        "probability_calibration": {
            "evaluated_with_brier_score": True,
            "exposed_as_probability": False,
            "reason": "A held-out Brier score alone is not a calibration study; model_probability remains null.",
        },
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "python_model_class": type(selected).__name__,
    }

    models_dir = ROOT / args.models_dir
    reports_dir = ROOT / args.reports_dir
    models_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": selected, "metadata": metadata}, models_dir / "url_model.joblib")
    (reports_dir / "url_evaluation.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(metadata, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
