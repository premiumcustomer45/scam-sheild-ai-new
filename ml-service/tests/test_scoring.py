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


def codes(result) -> set[str]:
    return {item.code for item in result.indicators}


def test_trusted_domain_is_lower_risk_even_with_a_high_model_score():
    result = predict_url("https://chatgpt.com/", url_bundle(0.99))
    assert result.verdict == "lower-risk"
    assert result.riskScore <= 10
    assert {"trusted-domain", "https"} <= codes(result)
    assert result.model_probability is None


def test_bare_domain_is_treated_as_https():
    result = predict_url("chatgpt.com", url_bundle(0.5))
    assert "no-https" not in codes(result)
    assert result.urls[0].url == "https://chatgpt.com"


def test_unknown_domain_without_warning_signs_stays_lower_risk():
    result = predict_url("https://example.com/a", url_bundle(0.99))
    assert result.verdict == "lower-risk"
    assert "unknown-domain" in codes(result)
    assert result.urls[0].url == "https://example.com/…"
    assert any("did not open" in limitation for limitation in result.limitations)


def test_brand_impersonation_on_risky_tld_is_high_risk():
    result = predict_url("http://paypa1-secure-login.xyz/verify-account", url_bundle(0.1))
    assert result.verdict == "high-risk"
    assert {"brand-impersonation", "risky-tld", "no-https"} <= codes(result)


def test_lookalike_and_userinfo_and_downloads_are_flagged():
    assert "lookalike-domain" in codes(predict_url("https://paypai.com", url_bundle(0.1)))
    assert "userinfo" in codes(predict_url("https://google.com@evil.ru/login", url_bundle(0.1)))
    assert "dangerous-download" in codes(predict_url("https://example.org/sbi-yono.apk", url_bundle(0.1)))
    assert "lookalike-domain" not in codes(predict_url("https://cooking.com", url_bundle(0.1)))


def test_shortener_is_suspicious():
    result = predict_url("https://bit.ly/3abc", url_bundle(0.1))
    assert result.verdict == "suspicious"
    assert "url-shortener" in codes(result)


def test_otp_request_is_high_risk_but_otp_notice_is_not():
    scam = predict_text("Please share the OTP you just received", text_bundle(0.1))
    assert scam.verdict == "high-risk"
    assert "otp-request" in codes(scam)
    notice = predict_text("Your OTP is 482913. Do not share it with anyone. -HDFC Bank", text_bundle(0.4))
    assert notice.verdict == "lower-risk"
    assert "otp-notice" in codes(notice)


def test_upi_pin_to_receive_money_is_high_risk():
    result = predict_text("Enter your UPI PIN to receive Rs 5000 cashback", text_bundle(0.2))
    assert result.verdict == "high-risk"
    assert any("1930" in item for item in result.recommendations)


def test_ordinary_message_is_lower_risk():
    result = predict_text("Are we meeting for lunch tomorrow?", text_bundle(0.05))
    assert result.verdict == "lower-risk"
    assert "no-scam-patterns" in codes(result)
    assert any("UCI SMS Spam" in limitation for limitation in result.limitations)


def test_combined_scan_extracts_urls_without_visiting_them():
    text = "Please review https://example.com/login?token=secret."
    assert extract_urls(text) == ["https://example.com/login?token=secret"]
    result = predict_combined(text, text_bundle(0.1), url_bundle(0.05))
    assert result.urls[0].url == "https://example.com/…"


def test_combined_scam_message_with_bad_link_is_high_risk():
    text = "Your SBI account will be blocked today. Update KYC: http://sbi-kyc.xyz"
    result = predict_combined(text, text_bundle(0.5), url_bundle(0.5))
    assert result.verdict == "high-risk"
    assert {"kyc-account-block", "brand-impersonation"} <= codes(result)
    assert result.recommendations[0] == "Do not open the link in this message."


def test_scam_text_is_not_made_safe_by_a_genuine_link():
    text = "Congratulations you won the lottery! Pay processing fee at https://www.google.com"
    result = predict_combined(text, text_bundle(0.5), url_bundle(0.99))
    assert result.verdict == "high-risk"
    assert result.urls[0].verdict == "lower-risk"
