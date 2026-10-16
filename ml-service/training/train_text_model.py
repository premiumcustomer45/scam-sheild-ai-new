from __future__ import annotations

import argparse
import json
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
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
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline

ROOT = Path(__file__).resolve().parents[1]


def _load_messages(path: Path) -> tuple[list[str], np.ndarray]:
    if not path.is_file():
        raise SystemExit(
            f"Dataset not found: {path}. Follow docs/dataset.md to download it."
        )
    if zipfile.is_zipfile(path):
        with zipfile.ZipFile(path) as archive:
            names = archive.namelist()
            data_name = next(
                (name for name in names if name.rsplit("/", 1)[-1] == "SMSSpamCollection"),
                None,
            )
            if data_name is None:
                raise ValueError("SMS dataset archive does not contain SMSSpamCollection.")
            raw = archive.read(data_name).decode("utf-8", errors="replace").splitlines()
    else:
        raw = path.read_text(encoding="utf-8", errors="replace").splitlines()

    texts: list[str] = []
    labels: list[int] = []
    for line_number, line in enumerate(raw, start=1):
        label, separator, text = line.partition("\t")
        if not separator or label not in {"ham", "spam"}:
            raise ValueError(f"Invalid SMS dataset row at line {line_number}.")
        text = text.strip()
        if text:
            texts.append(text)
            labels.append(1 if label == "spam" else 0)
    if not texts or set(labels) != {0, 1}:
        raise ValueError("SMS dataset must include both ham and spam messages.")
    return texts, np.asarray(labels, dtype=int)


def _best_f1_threshold(labels: np.ndarray, scores: np.ndarray) -> tuple[float, float]:
    precision, recall, thresholds = precision_recall_curve(labels, scores)
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Train spam-versus-ham text baselines; this is not a phishing-labelled dataset."
    )
    parser.add_argument("--input", default="data/raw/sms-spam.zip")
    parser.add_argument("--models-dir", default="models")
    parser.add_argument("--reports-dir", default="training/reports")
    args = parser.parse_args()
    input_path = ROOT / args.input
    texts, labels = _load_messages(input_path)

    unique_by_text: dict[str, int] = {}
    for text, label in zip(texts, labels, strict=True):
        normalized = " ".join(text.casefold().split())
        if normalized in unique_by_text and unique_by_text[normalized] != int(label):
            raise ValueError("A duplicate message has conflicting ham/spam labels.")
        unique_by_text[normalized] = int(label)
    deduplicated = list(unique_by_text.items())
    normalized_texts = [text for text, _ in deduplicated]
    normalized_labels = np.asarray([label for _, label in deduplicated], dtype=int)
    if set(np.unique(normalized_labels)) != {0, 1}:
        raise ValueError("Training requires both ham and spam labels after deduplication.")

    x_train, x_remainder, y_train, y_remainder = train_test_split(
        normalized_texts,
        normalized_labels,
        test_size=0.30,
        random_state=41,
        stratify=normalized_labels,
    )
    x_valid, x_test, y_valid, y_test = train_test_split(
        x_remainder,
        y_remainder,
        test_size=0.50,
        random_state=42,
        stratify=y_remainder,
    )

    vectorizer = TfidfVectorizer(
        lowercase=True,
        strip_accents="unicode",
        ngram_range=(1, 2),
        min_df=2,
        max_features=50000,
        sublinear_tf=True,
        token_pattern=r"(?u)\b\w[\w'’-]*\b",
    )
    candidates = {
        "logistic_regression": Pipeline(
            [
                ("tfidf", TfidfVectorizer(**vectorizer.get_params())),
                ("classifier", LogisticRegression(max_iter=1500, class_weight="balanced")),
            ]
        ),
        "multinomial_nb": Pipeline(
            [
                ("tfidf", TfidfVectorizer(**vectorizer.get_params())),
                ("classifier", MultinomialNB(alpha=0.3)),
            ]
        ),
    }
    validation: dict[str, dict] = {}
    models: dict[str, Pipeline] = {}
    for name, model in candidates.items():
        model.fit(x_train, y_train)
        scores = model.predict_proba(x_valid)[:, list(model.classes_).index(1)]
        threshold, best_f1 = _best_f1_threshold(y_valid, scores)
        validation[name] = {
            **_metrics(y_valid, scores, threshold),
            "best_f1": best_f1,
        }
        models[name] = model

    selected_name = max(validation, key=lambda name: validation[name]["best_f1"])
    selected = models[selected_name]
    high_threshold = float(validation[selected_name]["threshold"])
    valid_scores = selected.predict_proba(x_valid)[:, list(selected.classes_).index(1)]
    ham_scores = valid_scores[y_valid == 0]
    suspicious_threshold = min(high_threshold, float(np.quantile(ham_scores, 0.95)))
    test_scores = selected.predict_proba(x_test)[:, list(selected.classes_).index(1)]
    metadata = {
        "model_type": "text",
        "model_version": "uci-sms-spam-tfidf-v1",
        "dataset": {
            "name": "SMS Spam Collection",
            "uci_dataset_id": 228,
            "source": "https://archive.ics.uci.edu/dataset/228/sms+spam+collection",
            "license": "CC BY 4.0",
            "label_mapping": {"ham": "non-spam", "spam": "spam"},
            "label_scope": "Spam versus ham only; labels do not mean phishing versus legitimate.",
            "input_rows": int(len(texts)),
            "rows_after_exact_normalized_deduplication": int(len(normalized_texts)),
        },
        "training_config": {
            "split": "70/15/15 stratified random split after exact normalized-message deduplication",
            "random_seed": 41,
            "tfidf": {
                "ngram_range": [1, 2],
                "min_df": 2,
                "max_features": 50000,
                "lowercase": True,
                "sublinear_tf": True,
            },
            "candidate_models": list(candidates),
            "selected_model": selected_name,
        },
        "label_mapping": {"0": "ham", "1": "spam"},
        "high_threshold": high_threshold,
        "suspicious_threshold": suspicious_threshold,
        "validation_metrics": validation,
        "test_metrics": _metrics(y_test, test_scores, high_threshold),
        "probability_calibration": {
            "evaluated_with_brier_score": True,
            "exposed_as_probability": False,
            "reason": "A held-out Brier score alone is not a calibration study; model_probability remains null.",
        },
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "false_positive_examples": [],
        "false_negative_examples": [],
    }

    models_dir = ROOT / args.models_dir
    reports_dir = ROOT / args.reports_dir
    models_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)
    joblib.dump({"model": selected, "metadata": metadata}, models_dir / "text_model.joblib")
    (reports_dir / "text_evaluation.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    predictions = (test_scores >= high_threshold).astype(int)
    false_positives = np.flatnonzero((predictions == 1) & (y_test == 0))[:10]
    false_negatives = np.flatnonzero((predictions == 0) & (y_test == 1))[:10]
    def redact_example(text: str) -> str:
        import re

        redacted = re.sub(r"https?://\S+", "[URL]", text, flags=re.IGNORECASE)
        redacted = re.sub(r"(?<!\w)\+?\d[\d ()-]{5,}\d(?!\w)", "[NUMBER]", redacted)
        return redacted[:200]

    error_examples = {
        "false_positives": [redact_example(x_test[int(index)]) for index in false_positives],
        "false_negatives": [redact_example(x_test[int(index)]) for index in false_negatives],
    }
    metadata["false_positive_examples"] = error_examples["false_positives"]
    metadata["false_negative_examples"] = error_examples["false_negatives"]
    (reports_dir / "text_evaluation.json").write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    # Keep error examples in the report for research, not in the serving artifact.
    print(json.dumps(metadata, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
