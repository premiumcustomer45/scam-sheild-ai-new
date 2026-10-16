from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Inspect the UCI PhiUSIIL dataset schema and target distribution."
    )
    parser.add_argument(
        "--input",
        default="data/raw/phiusiil.zip",
        help="Path to the downloaded UCI CSV or one-file ZIP archive.",
    )
    args = parser.parse_args()
    path = Path(args.input)
    if not path.is_file():
        raise SystemExit(
            f"Dataset not found: {path}. Follow docs/dataset.md to download it."
        )

    sample = pd.read_csv(path, nrows=1000)
    if "label" not in sample.columns or "URL" not in sample.columns:
        raise SystemExit("Expected the UCI columns 'URL' and 'label' were not found.")
    target = pd.read_csv(path, usecols=["label"])["label"]
    report = {
        "source": "UCI PhiUSIIL Phishing URL Dataset (dataset ID 967)",
        "sample_rows_read_for_schema": int(len(sample)),
        "columns": [{"name": name, "dtype": str(dtype)} for name, dtype in sample.dtypes.items()],
        "target_column": "label",
        "label_mapping": {"0": "phishing", "1": "legitimate"},
        "target_counts": {
            str(label): int(count) for label, count in target.value_counts(dropna=False).items()
        },
        "missing_target_values": int(target.isna().sum()),
        "duplicate_url_rows": int(
            pd.read_csv(path, usecols=["URL"])["URL"].duplicated().sum()
        ),
        "live_inference_columns": ["URL"],
        "ignored_non-live_features": [
            "Features requiring webpage content, page title, redirects, or historical/domain reputation are excluded from the live classifier.",
            "The training and live inference feature contract is derived only from the URL string.",
        ],
    }
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
