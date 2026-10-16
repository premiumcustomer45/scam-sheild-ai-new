from __future__ import annotations

import re
from typing import Any

import pandas as pd

from app.schemas import Indicator, Prediction, UrlAssessment
from app.services.url_features import extract_url_features, safe_url_preview

URL_LIMITATIONS = [
    "This assessment uses URL text only. ScamShield did not visit the destination or inspect its page.",
    "The risk score is a model signal on a 0–100 scale, not a calibrated probability or proof of maliciousness.",
    "New or altered phishing techniques may not be represented in the training data.",
]
TEXT_LIMITATIONS = [
    "The text baseline was trained on the UCI SMS Spam Collection (spam versus ham), not a phishing-specific message corpus.",
    "Spam-like wording is not proof of phishing, and legitimate messages may be incorrectly flagged.",
    "The risk score is a model signal on a 0–100 scale, not a calibrated probability.",
]
COMBINED_LIMITATIONS = [
    *TEXT_LIMITATIONS,
    "The combined policy preserves conflicting signals as uncertain; it has not been validated on a dedicated combined-message test set.",
]

_URL_PATTERN = re.compile(
    r"(?i)\b(?:https?://|www\.)[^\s<>\"']+|\b[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9-]+)+(?:/[^\s<>\"']*)?"
)
_TRAILING_PUNCTUATION = ".,;:!?)]}"
_URGENCY_TERMS = ("urgent", "immediately", "act now", "expires today", "final notice")
_CREDENTIAL_TERMS = ("password", "verify your account", "sign in", "login", "one-time code")
_PAYMENT_TERMS = ("payment", "invoice", "gift card", "wire transfer", "crypto")


def _classify(score: float, metadata: dict[str, Any]) -> str:
    high = float(metadata["high_threshold"])
    suspicious = float(metadata["suspicious_threshold"])
    if score >= high:
        return "high-risk"
    if score >= suspicious:
        return "suspicious"
    return "lower-risk"


def _indicators_from_url(url: str, features: dict[str, float]) -> list[Indicator]:
    indicators: list[Indicator] = []
    candidates = (
        (
            "userinfo",
            features["has_userinfo"] > 0,
            "The URL contains user information before its hostname.",
            "high",
        ),
        (
            "ip-host",
            features["is_ip_host"] > 0,
            "The hostname is an IP address rather than a conventional domain name.",
            "warning",
        ),
        (
            "subdomain-depth",
            features["subdomain_count"] >= 3,
            "The hostname has several subdomain levels, which can make the registered domain harder to spot.",
            "warning",
        ),
        (
            "nonstandard-port",
            features["has_nonstandard_port"] > 0,
            "The URL uses a non-standard web port.",
            "warning",
        ),
        (
            "encoded-url",
            features["percent_escape_count"] >= 3,
            "The URL includes multiple percent-encoded characters.",
            "warning",
        ),
        (
            "credential-language",
            features["suspicious_token_count"] >= 2,
            "The URL contains multiple account or credential-related terms.",
            "warning",
        ),
        (
            "punycode",
            features["has_punycode_label"] > 0,
            "The hostname contains an IDN punycode label; check that the displayed domain is the one you expect.",
            "info",
        ),
        (
            "long-url",
            features["url_length"] > 100,
            "The URL is unusually long; length alone does not establish maliciousness.",
            "info",
        ),
    )
    for code, present, detail, severity in candidates:
        if present:
            indicators.append(
                Indicator(
                    code=code,
                    title={
                        "userinfo": "Hostname ambiguity",
                        "ip-host": "IP address hostname",
                        "subdomain-depth": "Deep subdomain structure",
                        "nonstandard-port": "Non-standard port",
                        "encoded-url": "Encoded characters",
                        "credential-language": "Account-related URL terms",
                        "punycode": "Internationalized hostname",
                        "long-url": "Long URL",
                    }[code],
                    detail=detail,
                    severity=severity,
                )
            )
    return indicators


def _score_url(url: str, bundle: dict[str, Any]) -> UrlAssessment:
    features = extract_url_features(url)
    model = bundle["model"]
    metadata = bundle["metadata"]
    frame = pd.DataFrame([features], columns=metadata["feature_names"])
    score = float(model.predict_proba(frame)[0][list(model.classes_).index(1)])
    verdict = _classify(score, metadata)
    return UrlAssessment(
        url=safe_url_preview(url),
        verdict=verdict,
        riskScore=max(0, min(100, round(score * 100))),
        indicators=_indicators_from_url(url, features),
    )


def _text_indicators(text: str, model_verdict: str) -> list[Indicator]:
    normalized = text.casefold()
    indicators: list[Indicator] = []
    phrases = (
        ("urgency-language", _URGENCY_TERMS, "Urgency or time pressure"),
        ("credential-request-language", _CREDENTIAL_TERMS, "Account or credential language"),
        ("payment-language", _PAYMENT_TERMS, "Payment-related language"),
    )
    for code, terms, title in phrases:
        if any(term in normalized for term in terms):
            indicators.append(
                Indicator(
                    code=code,
                    title=title,
                    detail="This phrase can appear in both legitimate and scam messages; treat it as a cue to verify the sender independently.",
                    severity="warning",
                )
            )
    if model_verdict in {"suspicious", "high-risk"}:
        indicators.append(
            Indicator(
                code="spam-model-signal",
                title="Spam-like language signal",
                detail="The SMS spam-versus-ham model found a pattern more associated with unsolicited spam in its training set. This is not a phishing determination.",
                severity="warning",
            )
        )
    return indicators


def extract_urls(text: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for match in _URL_PATTERN.finditer(text):
        candidate = match.group(0).rstrip(_TRAILING_PUNCTUATION)
        if candidate.casefold().startswith("www."):
            candidate = f"http://{candidate}"
        try:
            # Parsing validates the candidate without making a network request.
            extract_url_features(candidate)
        except ValueError:
            continue
        key = candidate.casefold()
        if key not in seen:
            seen.add(key)
            urls.append(candidate)
    return urls[:10]


def predict_url(url: str, bundle: dict[str, Any]) -> Prediction:
    assessment = _score_url(url, bundle)
    return Prediction(
        verdict=assessment.verdict,
        riskScore=assessment.riskScore,
        model_probability=None,
        indicators=assessment.indicators,
        recommendations=[
            "Do not enter passwords or payment details unless you independently confirm the domain.",
            "If this link claims to be from an organization, open its official app or type its known address yourself.",
        ],
        model_version=bundle["metadata"]["model_version"],
        limitations=URL_LIMITATIONS,
        urls=[assessment],
    )


def predict_text(text: str, bundle: dict[str, Any]) -> Prediction:
    model = bundle["model"]
    metadata = bundle["metadata"]
    score = float(model.predict_proba([text])[0][list(model.classes_).index(1)])
    verdict = _classify(score, metadata)
    return Prediction(
        verdict=verdict,
        riskScore=max(0, min(100, round(score * 100))),
        model_probability=None,
        indicators=_text_indicators(text, verdict),
        recommendations=[
            "Verify the sender through a known phone number, app, or website before following instructions.",
            "Do not share one-time codes, passwords, or payment details in response to an unexpected message.",
        ],
        model_version=metadata["model_version"],
        limitations=TEXT_LIMITATIONS,
    )


def predict_combined(text: str, text_bundle: dict[str, Any], url_bundle: dict[str, Any]) -> Prediction:
    text_result = predict_text(text, text_bundle)
    assessments = [_score_url(url, url_bundle) for url in extract_urls(text)]
    url_result_verdicts = [assessment.verdict for assessment in assessments]

    if not assessments:
        result = text_result
        result.limitations = COMBINED_LIMITATIONS
        return result

    # A high-risk URL is not diluted by the message text. Conflicting strong
    # message and URL signals are reported as uncertain instead of averaged.
    url_high = "high-risk" in url_result_verdicts
    text_high = text_result.verdict == "high-risk"
    urls_all_lower = all(verdict == "lower-risk" for verdict in url_result_verdicts)
    text_signal = text_result.verdict in {"suspicious", "high-risk"}
    url_signal = any(verdict in {"suspicious", "high-risk"} for verdict in url_result_verdicts)

    if url_high:
        verdict = "high-risk"
        score = max(assessment.riskScore for assessment in assessments)
    elif text_signal and urls_all_lower:
        verdict = "uncertain"
        score = max(text_result.riskScore, max(item.riskScore for item in assessments))
    elif text_high and url_signal:
        verdict = "uncertain"
        score = max(text_result.riskScore, max(item.riskScore for item in assessments))
    elif url_signal:
        verdict = max(assessments, key=lambda item: item.riskScore).verdict
        score = max(assessment.riskScore for assessment in assessments)
    else:
        verdict = text_result.verdict
        score = text_result.riskScore

    combined_indicators = list(text_result.indicators)
    for assessment in assessments:
        combined_indicators.extend(assessment.indicators)
    if verdict == "uncertain":
        combined_indicators.append(
            Indicator(
                code="conflicting-evidence",
                title="Signals do not agree",
                detail="The message and URL signals differ. The result is uncertain; verify the sender and destination through an independent channel.",
                severity="warning",
            )
        )

    return Prediction(
        verdict=verdict,
        riskScore=max(0, min(100, score)),
        model_probability=None,
        indicators=combined_indicators,
        recommendations=[
            "Do not use contact details or links supplied in an unexpected message to verify its claims.",
            "Open the organization's known app or type its official address yourself.",
        ],
        model_version=f"{text_bundle['metadata']['model_version']} + {url_bundle['metadata']['model_version']}",
        limitations=COMBINED_LIMITATIONS,
        urls=assessments,
    )
