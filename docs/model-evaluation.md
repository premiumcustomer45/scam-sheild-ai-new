# Model training and evaluation

Run `training/inspect_url_dataset.py`, `training/train_url_model.py`, and `training/train_text_model.py` from `ml-service/`. Each trainer writes a JSON report in `training/reports/` and a fitted inference artifact in `models/`.

## Evaluation protocol

- All splits use a fixed random seed.
- The URL dataset is de-duplicated by exact URL and split by an approximate registered-domain group, reducing (but not eliminating) domain leakage.
- The SMS dataset is normalized and de-duplicated by exact normalized message before its stratified split.
- Logistic Regression and Random Forest are compared for URLs; Logistic Regression and Multinomial Naive Bayes are compared for text.
- Model selection and thresholds use validation data. Final precision, recall, F1, confusion matrix, PR-AUC, and Brier score are computed only on the held-out test partition.
- The serving artifacts include model version, source dataset, label mapping, feature names, split/training configuration, validation metrics, and test metrics.
- Raw model output is not exposed as a calibrated probability. A Brier score is reported, but calibration is not established by that one metric; API `model_probability` remains null.

## Results

These are the actual local held-out results from the fixed-seed training run. They describe performance on these UCI test partitions only, not expected real-world accuracy.

| Model | Selected baseline | Test rows | Precision | Recall | F1 | PR-AUC | Brier score |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| URL phishing | Random Forest | 31,453 | 0.9991 | 0.9913 | 0.9952 | 0.9975 | 0.0041 |
| SMS spam-vs-ham | Logistic Regression + TF-IDF | 774 | 0.9890 | 0.9375 | 0.9626 | 0.9745 | 0.0279 |

Confusion matrices use label order `[non-phishing/ham, phishing/spam]`:

- URL: `[[19994, 10], [100, 11349]]`
- SMS text: `[[677, 1], [6, 90]]`

The URL dataset includes page-derived attributes, but this model intentionally uses only its URL column to avoid training/live feature mismatch. Its approximate registrable-domain split is more conservative than a random row split, though the suffix approximation and dataset source still limit generalization. The SMS corpus is small and contains spam filtering labels, not phishing labels.

The reports in `training/reports/url_evaluation.json` and `text_evaluation.json` contain threshold selection, validation comparison, dataset counts, training configuration, and examples from text false positives/negatives. They are excluded from Git/deployment because the text examples may contain contact details. Regenerate them with the model artifacts after retraining.

The combined policy is not evaluated as a classifier because no labeled combined-message dataset was used. Its conflict behavior is a documented heuristic.
