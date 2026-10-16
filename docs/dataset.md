# Datasets and label definitions

## URL classifier: UCI PhiUSIIL

- **Source:** [PhiUSIIL Phishing URL Dataset (UCI ID 967)](https://archive.ics.uci.edu/dataset/967/phiusiil+phishing+url+dataset)
- **License:** Creative Commons Attribution 4.0 International (CC BY 4.0); cite Prasad and Chandra.
- **Documented size:** 235,795 instances and 54 features; no missing values.
- **Target:** `label`; UCI documents `0` as phishing and `1` as legitimate.
- **Observed target counts:** 100,945 phishing and 134,850 legitimate.
- **Observed exact duplicate URLs:** 425 before de-duplication.
- `FILENAME` is not used. Page title, HTML, redirect, and reputation-derived features are unavailable to this scanner and are excluded.
- Training reads only `URL` and `label`, removes exact duplicate URL values, validates URL strings, and creates an approximate registrable-domain group for split isolation.
- Both model training and inference call the same 19-feature lexical extractor. It uses only the submitted URL string.
- No outbound requests or domain lookups are made.

Citation: Prasad, A. & Chandra, S. (2024). “PhiUSIIL: A diverse security profile empowered phishing URL detection framework based on similarity index and incremental learning.” *Computers & Security*. https://doi.org/10.1016/j.cose.2023.103545

## Text classifier: UCI SMS Spam Collection

- **Source:** [SMS Spam Collection (UCI ID 228)](https://archive.ics.uci.edu/dataset/228/sms+spam+collection)
- **License:** CC BY 4.0 as listed by UCI; cite Almeida, Hidalgo, and Yamakami.
- **Documented size:** 5,574 SMS messages. The labels are `ham` and `spam`; the corpus is not chronologically sorted.
- **Label mapping:** `ham` → non-spam (`0`), `spam` → spam (`1`).
- These labels indicate spam filtering, not phishing detection. ScamShield describes the text model as a spam-like signal and does not relabel the dataset as phishing.
- Normalized exact duplicate messages are removed before a stratified 70/15/15 train/validation/test split.
- TF-IDF uses word unigrams and bigrams. The full fitted vectorizer and classifier are saved together in a scikit-learn Pipeline.

Citation: Almeida, T. A., Hidalgo, J. M. G., & Yamakami, A. (2011). “Contributions to the study of SMS spam filtering: new collection and results.” *ACM Symposium on Document Engineering*.

## Download and reproducibility

From `ml-service/`:

```bash
uv sync --all-groups
uv run python training/download_datasets.py
uv run python training/inspect_url_dataset.py
uv run python training/train_url_model.py
uv run python training/train_text_model.py
```

The downloader uses only fixed official UCI URLs. Raw ZIP files are written to `data/raw/` and ignored by Git and deployment. If network access is unavailable, download each archive from the linked UCI dataset page and place it in `data/raw/` using the names shown above. Check the UCI pages for current license and dataset documentation before redistributing.
