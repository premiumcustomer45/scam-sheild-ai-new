from app.services.scoring import extract_urls, predict_combined, predict_text, predict_url


class UrlModel:
    classes_ = [0, 1]

    def __init__(self, phishing_score: float):
        self.phishing_score = phishing_score

    def predict_proba(self, _features):
        return [[1 - self.phishing_score, self.phishing_score]]


class TextModel:
    classes_ = [0, 1]

    def __init__(self, spam_score: float):
        self.spam_score = spam_score

    def predict_proba(self, _texts):
        return [[1 - self.spam_score, self.spam_score]]


def url_bundle(score: float) -> dict:
    from app.services.url_features import URL_FEATURES

    return {
        "model": UrlModel(score),
        "metadata": {
            "model_type": "url",
            "model_version": "url-test",
            "feature_names": URL_FEATURES,
            "high_threshold": 0.8,
            "suspicious_threshold": 0.3,
        },
    }


def text_bundle(score: float) -> dict:
    return {
        "model": TextModel(score),
        "metadata": {
            "model_type": "text",
            "model_version": "text-test",
            "high_threshold": 0.8,
            "suspicious_threshold": 0.3,
        },
    }


def test_url_prediction_uses_model_output_and_explicit_limitations():
    result = predict_url("https://example.com/a", url_bundle(0.42))
    assert result.riskScore == 42
    assert result.verdict == "suspicious"
    assert result.model_probability is None
    assert result.urls[0].url == "https://example.com/a"
    assert any("did not visit" in limitation for limitation in result.limitations)


def test_text_prediction_is_described_as_spam_not_phishing():
    result = predict_text("Verify your account now.", text_bundle(0.9))
    assert result.verdict == "high-risk"
    assert result.model_probability is None
    assert any("not a phishing" in limitation for limitation in result.limitations)


def test_combined_scan_extracts_urls_without_visiting_them_and_marks_conflict():
    text = "Please review https://example.com/login?token=secret."
    assert extract_urls(text) == ["https://example.com/login?token=secret"]
    result = predict_combined(text, text_bundle(0.5), url_bundle(0.05))
    assert result.verdict == "uncertain"
    assert result.urls[0].url == "https://example.com/login"
    assert any(item.code == "conflicting-evidence" for item in result.indicators)
