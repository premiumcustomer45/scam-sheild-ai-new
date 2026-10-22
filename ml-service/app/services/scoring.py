"""Risk scoring: the trained models plus explainable scam-pattern rules.

The lexical URL model (PhiUSIIL) and the SMS spam model are useful signals but
have dataset biases (for example, short well-known domains can score high), so
the final score is driven by concrete, explainable evidence and the models only
contribute a bounded share of it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import pandas as pd

from app.schemas import Indicator, Prediction, UrlAssessment
from app.services import reputation
from app.services.url_features import extract_url_features, parse_url, safe_url_preview

SUSPICIOUS_AT = 30
HIGH_RISK_AT = 60
RULES_VERSION = "rules-v2"

URL_LIMITATIONS = [
    "ScamShield checked the link text and domain reputation only. It did not open the website.",
    "A well-known domain can still host harmful content, such as shared files or redirects.",
    "The risk score is an estimate on a 0–100 scale, not a guarantee.",
]
TEXT_LIMITATIONS = [
    "Message analysis combines scam-pattern rules with a spam model trained on the UCI SMS Spam Collection.",
    "Legitimate messages are occasionally flagged; verify through the organization's official app or number.",
    "The risk score is an estimate on a 0–100 scale, not a guarantee.",
]
COMBINED_LIMITATIONS = [
    *TEXT_LIMITATIONS,
    "Links inside the message were assessed from their text and domain only; none were opened.",
]

_URL_PATTERN = re.compile(
    r"(?i)\b(?:https?://|www\.)[^\s<>\"']+|\b[a-z0-9](?:[a-z0-9-]*[a-z0-9])?(?:\.[a-z0-9-]+)+(?:/[^\s<>\"']*)?"
)
_TRAILING_PUNCTUATION = ".,;:!?)]}"


@dataclass
class Signal:
    code: str
    title: str
    detail: str
    severity: str
    points: int = 0

    def indicator(self) -> Indicator:
        return Indicator(code=self.code, title=self.title, detail=self.detail, severity=self.severity)


def _verdict(score: int) -> str:
    if score >= HIGH_RISK_AT:
        return "high-risk"
    if score >= SUSPICIOUS_AT:
        return "suspicious"
    return "lower-risk"


def _clamp(score: float) -> int:
    return max(0, min(100, round(score)))


def _model_score(model: Any, payload: Any) -> float:
    return float(model.predict_proba(payload)[0][list(model.classes_).index(1)])


# ---------------------------------------------------------------------------
# URLs
# ---------------------------------------------------------------------------


def _url_signals(url: str, features: dict[str, float]) -> tuple[list[Signal], bool, str]:
    parsed, host, _port = parse_url(url)
    domain = reputation.registrable_domain(host)
    path = parsed.path or ""
    trusted = reputation.is_trusted(host)
    https = features["uses_https"] > 0
    signals: list[Signal] = []

    if features["has_userinfo"] > 0:
        signals.append(Signal(
            "userinfo", "Hidden real destination",
            f"Text before the “@” is a disguise; the browser would actually open {host}.",
            "high", 45,
        ))
    if features["is_ip_host"] > 0:
        signals.append(Signal(
            "ip-host", "IP address instead of a domain",
            "Genuine services use a domain name. Raw IP addresses are common in phishing links.",
            "high", 35,
        ))

    brand = reputation.impersonated_brand(host, path)
    if brand:
        signals.append(Signal(
            "brand-impersonation", "Brand impersonation",
            f"The link mentions “{brand}”, but {domain} is not an official {brand} website.",
            "high", 55,
        ))
    else:
        lookalike = reputation.lookalike_of(host)
        if lookalike:
            signals.append(Signal(
                "lookalike-domain", "Lookalike domain",
                f"{domain} is spelled to look like {lookalike}. This is a common phishing trick.",
                "high", 60,
            ))

    if path.lower().endswith(reputation.DANGEROUS_EXTENSIONS):
        signals.append(Signal(
            "dangerous-download", "Downloads an app or program",
            "The link points to an installable file (such as an APK). Fake apps are used to steal OTPs and bank data.",
            "high", 50,
        ))
    if reputation.is_shortener(host):
        signals.append(Signal(
            "url-shortener", "Shortened link",
            f"{domain} is a link shortener, so the real destination is hidden.",
            "warning", 30,
        ))

    platform = reputation.free_hosting_platform(host)
    if platform and not trusted:
        signals.append(Signal(
            "free-hosting", "Free hosting platform",
            f"The page is hosted on {platform}, where anyone can publish a site in minutes.",
            "warning", 20,
        ))
    if reputation.tld(host) in reputation.RISKY_TLDS and not trusted:
        signals.append(Signal(
            "risky-tld", "High-risk domain ending",
            f"Domains ending in “.{reputation.tld(host)}” are cheap to register and frequently used in scams.",
            "warning", 20,
        ))
    if not https:
        signals.append(Signal(
            "no-https", "No HTTPS encryption",
            "The link uses plain HTTP, so anything typed on the page could be intercepted.",
            "warning", 10 if trusted else 15,
        ))
    if features["has_punycode_label"] > 0:
        signals.append(Signal(
            "punycode", "Internationalized characters",
            "The domain uses special characters that can imitate normal letters.",
            "warning", 25,
        ))

    if not trusted:
        if features["suspicious_token_count"] >= 1:
            count = int(features["suspicious_token_count"])
            signals.append(Signal(
                "credential-language", "Login or account wording",
                "The address contains words like “login”, “verify” or “account”, often used to lure victims.",
                "warning", 12 * min(count, 2),
            ))
        if features["subdomain_count"] >= 3:
            signals.append(Signal(
                "subdomain-depth", "Many subdomains",
                "Long chains of subdomains can make the real domain harder to spot.",
                "warning", 12,
            ))
        if domain.count("-") >= 2:
            signals.append(Signal(
                "hyphenated-domain", "Heavily hyphenated domain",
                "Domains with several hyphens are typical of throwaway scam sites.",
                "warning", 10,
            ))
        if sum(char.isdigit() for char in domain.split(".")[0]) >= 3:
            signals.append(Signal(
                "digits-in-domain", "Numbers in the domain name",
                "Random-looking numbers in a domain are common in auto-generated scam sites.",
                "warning", 10,
            ))
    if features["has_nonstandard_port"] > 0:
        signals.append(Signal(
            "nonstandard-port", "Unusual port",
            "The link uses a non-standard port, which ordinary websites rarely do.",
            "warning", 12,
        ))
    if features["percent_escape_count"] >= 3:
        signals.append(Signal(
            "encoded-url", "Encoded characters",
            "The address contains many encoded characters that can hide its real content.",
            "warning", 10,
        ))
    if features["url_length"] > 100:
        signals.append(Signal(
            "long-url", "Very long link",
            "Very long links can hide the important part of the address.",
            "info", 3,
        ))
    return signals, trusted, domain


def _score_url(url: str, bundle: dict[str, Any]) -> UrlAssessment:
    features = extract_url_features(url)
    metadata = bundle["metadata"]
    frame = pd.DataFrame([features], columns=metadata["feature_names"])
    model_score = _model_score(bundle["model"], frame)

    signals, trusted, domain = _url_signals(url, features)
    https = features["uses_https"] > 0
    serious = any(signal.severity == "high" for signal in signals)
    rule_points = sum(signal.points for signal in signals)

    if trusted and not serious:
        score = 3 + rule_points
        signals.insert(0, Signal(
            "trusted-domain", "Recognised, well-known website",
            f"{domain} is an established website on ScamShield's trusted list.",
            "safe",
        ))
    elif rule_points == 0:
        # No concrete warning sign: the model only nudges the score within the lower band.
        score = 5 + model_score * 20
        signals.append(Signal(
            "unknown-domain", "Not a widely known website",
            f"{domain} is not on ScamShield's list of well-known sites, but its address shows no warning signs.",
            "info",
        ))
    else:
        score = rule_points + model_score * 15

    if https and not serious:
        signals.append(Signal(
            "https", "Encrypted connection (HTTPS)",
            "The connection is encrypted. Note that scam sites can use HTTPS too.",
            "safe",
        ))

    risk_score = min(99, _clamp(score))
    return UrlAssessment(
        url=safe_url_preview(url),
        verdict=_verdict(risk_score),
        riskScore=risk_score,
        indicators=[signal.indicator() for signal in signals],
    )


def _url_recommendations(assessment: UrlAssessment) -> list[str]:
    trusted = any(item.code == "trusted-domain" for item in assessment.indicators)
    if assessment.verdict == "high-risk":
        return [
            "Do not open this link or download anything from it.",
            "Never enter an OTP, UPI PIN, password or card details on this page.",
            "If you already entered details, change your password, contact your bank, and report it at cybercrime.gov.in or by calling 1930.",
        ]
    if assessment.verdict == "suspicious":
        return [
            "Avoid entering passwords, OTPs or payment details on this page.",
            "Open the organization's official app, or type its known address yourself, instead of using this link.",
        ]
    if trusted:
        return [
            "This is a recognised official website. Check the address bar shows the same domain before signing in.",
            "Even on genuine sites, never share an OTP or PIN with anyone who contacts you.",
        ]
    return [
        "No warning signs were found, but this site is not widely known. Check reviews before paying or sharing personal details.",
        "Never share an OTP or PIN, even if the site looks legitimate.",
    ]


def extract_urls(text: str) -> list[str]:
    urls: list[str] = []
    seen: set[str] = set()
    for match in _URL_PATTERN.finditer(text):
        candidate = match.group(0).rstrip(_TRAILING_PUNCTUATION)
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
        recommendations=_url_recommendations(assessment),
        model_version=f"{bundle['metadata']['model_version']}+{RULES_VERSION}",
        limitations=URL_LIMITATIONS,
        urls=[assessment],
    )


# ---------------------------------------------------------------------------
# Messages
# ---------------------------------------------------------------------------

_NEGATION = re.compile(r"(?i)\b(do not|don't|dont|never|not to|mat|kabhi bhi|kisi ko bhi)\b")

# (code, title, severity, points, pattern, detail). Patterns include common
# Hinglish phrasing because many Indian scam messages are written that way.
_TEXT_RULES: tuple[tuple[str, str, str, int, str, str], ...] = (
    (
        "upi-pin-to-receive", "UPI PIN requested to receive money", "high", 60,
        r"(upi\s*pin|mpin|enter (your )?pin).{0,60}(receive|get|credit|claim|refund|cashback|prapt)"
        r"|(receive|get|credit|claim|refund|cashback).{0,60}(upi\s*pin|mpin|enter (your )?pin)",
        "A UPI PIN is only ever needed to send money, never to receive it. This is a classic payment scam.",
    ),
    (
        "card-secrets", "Asks for card or bank secrets", "high", 45,
        r"\b(cvv|atm pin|card number|expiry date|net ?banking (password|id)|mpin)\b",
        "No bank or company asks for CVV, PIN or net-banking credentials by message.",
    ),
    (
        "remote-access", "Asks you to install an app", "high", 45,
        r"\b(anydesk|teamviewer|quick ?support|rustdesk|airdroid|screen ?shar\w*|"
        r"(install|download) (this|the|our) app|\.apk)\b",
        "Scammers use screen-sharing or fake apps to take over phones and read OTPs.",
    ),
    (
        "digital-arrest", "Threat from “police” or officials", "high", 40,
        r"\b(digital arrest|arrest warrant|cbi|narcotics|money laundering|illegal (items|drugs|parcel)|"
        r"customs (officer|department)|cyber ?cell)\b",
        "Real police or agencies never threaten arrest over calls or messages, or ask for money to settle a case.",
    ),
    (
        "kyc-account-block", "KYC update or account-block threat", "high", 35,
        r"\b(kyc|pan\s*(card)?\s*(update|link)|aadhaa?r\s*(update|link)|"
        r"account (will be|has been|is|was) (blocked|suspended|closed|deactivated|frozen|on hold)|"
        r"(block|suspend|band|bandh) ho (jayega|jaega|jaayega)|khata band|sim (will be )?(blocked|deactivated))\b",
        "Banks and telecom companies do not block accounts through SMS links. KYC is done in-branch or in the official app.",
    ),
    (
        "utility-disconnection", "Electricity or utility disconnection threat", "high", 35,
        r"(electricity|bijli|power|light|gas)\b.{0,50}\b(disconnect\w*|cut|kat|band)",
        "Fake electricity-disconnection messages are a widespread scam. Check with your provider's official app.",
    ),
    (
        "prize-lottery", "Prize, lottery or reward offer", "warning", 30,
        r"\b(congratulations|congrats|you (have )?won|winner|lottery|lucky draw|jackpot|"
        r"kbc|reward points? (expir|redeem)|claim your (prize|reward|gift)|free gift|inaam)\b",
        "Unexpected prizes are the most common bait. You cannot win a contest you never entered.",
    ),
    (
        "job-task-scam", "Easy-money job or task offer", "warning", 40,
        r"\b(work from home|part[- ]time (job|work)|daily (income|earning)|earn (rs\.?|₹|inr|\d)|"
        r"per day|like (youtube )?videos|task[- ]based|prepaid task|ghar baithe)\b",
        "“Earn daily from home” offers usually end with you paying a deposit that is never returned.",
    ),
    (
        "money-request", "Payment or fee requested", "warning", 25,
        r"\b(processing fee|registration fee|pay (rs\.?|₹|inr)|send (rs\.?|₹|money)|gift ?card|wire transfer|"
        r"bitcoin|crypto|usdt|(double|guaranteed) (return|profit|money))\b",
        "Being asked to pay first, or promised guaranteed returns, is a strong scam signal.",
    ),
    (
        "credential-request", "Asks you to log in or verify", "warning", 20,
        r"\b(verify your (account|identity|details)|update your (details|account)|"
        r"(log ?in|sign ?in) (now|here|to)|confirm your (account|details|password)|password)\b",
        "Messages pushing you to log in through a link are the main route to stolen accounts.",
    ),
    (
        "parcel-issue", "Parcel or delivery problem", "warning", 15,
        r"\b(parcel|package|shipment|courier|delivery)\b.{0,50}\b(held|pending|failed|on hold|"
        r"address (incomplete|incorrect|update)|re-?deliver|customs)\b",
        "Fake delivery notices lure people to pay small “fees” on phishing pages.",
    ),
    (
        "urgency", "Urgency or pressure", "warning", 15,
        r"\b(urgent\w*|immediately|within \d+ ?(hours?|hrs|minutes?|mins)|act now|expires? (today|soon|tonight)|"
        r"final (notice|warning|reminder)|last (chance|date|warning)|today itself|turant|jaldi)\b",
        "Scammers create time pressure so you act before thinking.",
    ),
    (
        "moves-to-chat-app", "Moves the conversation to a chat app", "warning", 15,
        r"\b(contact|message|join|dm|ping|connect)\b.{0,25}\b(telegram|whatsapp|signal app)\b",
        "Scammers move victims to Telegram or WhatsApp to avoid platform safety checks.",
    ),
    (
        "call-this-number", "Asks you to call or reply", "warning", 10,
        r"\b(call (us|now|immediately|on|this number)|call\s*\+?\d{6,}|whatsapp (us|on)|contact (us )?(on|at)?\s*\+?\d{6,})",
        "Calling a number from an unknown message connects you to the scammer, not the real organization.",
    ),
)

_COMPILED_RULES = [
    (code, title, severity, points, re.compile(pattern, re.IGNORECASE), detail)
    for code, title, severity, points, pattern, detail in _TEXT_RULES
]

_OTP_REQUEST = re.compile(
    r"(?i)\b(share|send|tell|give|provide|forward|batao|bhejo|bata do|read out)\b.{0,40}\b(otp|one[- ]time (password|code)|verification code|code)\b"
    r"|\b(otp|one[- ]time (password|code)|verification code)\b.{0,40}\b(share|send|tell|batao|bhejo|bata do|reply)\b"
)
_OTP_NOTICE = re.compile(
    r"(?i)\b(otp|one[- ]time (password|code)|verification code)\b.{0,80}\b(do not|don't|never)\s+(share|disclose)"
    r"|\b(do not|don't|never)\s+(share|disclose)\b.{0,60}\b(otp|code)\b"
)


def _otp_signal(text: str) -> Signal | None:
    for match in _OTP_REQUEST.finditer(text):
        before = text[max(0, match.start() - 20):match.start() + 15]
        if not _NEGATION.search(before) and not _NEGATION.search(match.group(0)):
            return Signal(
                "otp-request", "Asks you to share an OTP",
                "An OTP authorises a payment or login. No bank, delivery company or official will ever ask for it.",
                "high", 60,
            )
    return None


def _assess_text(text: str, bundle: dict[str, Any]) -> tuple[int, list[Signal], float]:
    model_score = _model_score(bundle["model"], [text])
    signals: list[Signal] = []
    otp = _otp_signal(text)
    if otp:
        signals.append(otp)
    for code, title, severity, points, pattern, detail in _COMPILED_RULES:
        if pattern.search(text):
            signals.append(Signal(code, title, detail, severity, points))

    rule_points = sum(signal.points for signal in signals)
    if rule_points == 0:
        # Without a concrete scam pattern the spam model alone can reach "suspicious" only when very confident.
        score = model_score * 35
    else:
        score = rule_points + model_score * 20
    if model_score >= 0.7:
        signals.append(Signal(
            "spam-model-signal", "Spam-like wording",
            "The machine-learning model found wording typical of unsolicited spam messages.",
            "warning",
        ))

    if not otp and _OTP_NOTICE.search(text):
        score -= 25
        signals.insert(0, Signal(
            "otp-notice", "Standard OTP notice",
            "This reads like a genuine one-time-password message that warns you not to share the code. Never share it with anyone.",
            "safe",
        ))
    if not any(signal.severity in {"warning", "high"} for signal in signals):
        signals.append(Signal(
            "no-scam-patterns", "No common scam patterns",
            "No requests for OTPs, PINs, payments, or urgent action were found.",
            "safe",
        ))
    return min(99, _clamp(score)), signals, model_score


def _text_recommendations(verdict: str, signals: list[Signal]) -> list[str]:
    codes = {signal.code for signal in signals}
    if verdict == "lower-risk":
        return [
            "No common scam patterns were found. If the message asks for anything unusual, confirm with the sender directly.",
            "Never share an OTP, UPI PIN or password, even with someone who says they are from your bank.",
        ]
    advice = []
    if codes & {"otp-request", "upi-pin-to-receive", "card-secrets"}:
        advice.append("Do not share any OTP, UPI PIN, CVV or password. Genuine organizations never ask for them.")
    if "remote-access" in codes:
        advice.append("Do not install any app or start screen sharing at the sender's request.")
    if codes & {"money-request", "prize-lottery", "job-task-scam"}:
        advice.append("Do not pay any fee or deposit to claim a prize, job or refund.")
    advice.append("Contact the organization through its official app, website or the number on your card, not the details in this message.")
    if verdict == "high-risk":
        advice.append("Report the message at cybercrime.gov.in or call 1930 (India's cyber-fraud helpline), then block the sender.")
    return advice


def predict_text(text: str, bundle: dict[str, Any]) -> Prediction:
    score, signals, _ = _assess_text(text, bundle)
    verdict = _verdict(score)
    return Prediction(
        verdict=verdict,
        riskScore=score,
        model_probability=None,
        indicators=[signal.indicator() for signal in signals],
        recommendations=_text_recommendations(verdict, signals),
        model_version=f"{bundle['metadata']['model_version']}+{RULES_VERSION}",
        limitations=TEXT_LIMITATIONS,
    )


def predict_combined(text: str, text_bundle: dict[str, Any], url_bundle: dict[str, Any]) -> Prediction:
    text_score, signals, _ = _assess_text(text, text_bundle)
    assessments = [_score_url(url, url_bundle) for url in extract_urls(text)]
    url_score = max((item.riskScore for item in assessments), default=0)

    # A dangerous link is never diluted by harmless wording, and a scam message
    # is not made safe by a genuine link. Both together raise the score.
    score = max(text_score, url_score)
    if text_score >= SUSPICIOUS_AT and url_score >= SUSPICIOUS_AT:
        score += 10
    score = min(99, score)
    verdict = _verdict(score)

    indicators = [signal.indicator() for signal in signals]
    # Per-link details are listed under each URL; only their warnings are repeated here.
    for assessment in assessments:
        indicators.extend(
            item for item in assessment.indicators if item.severity in {"warning", "high"}
        )
    recommendations = _text_recommendations(verdict, signals)
    if url_score >= SUSPICIOUS_AT:
        recommendations.insert(0, "Do not open the link in this message.")

    return Prediction(
        verdict=verdict,
        riskScore=score,
        model_probability=None,
        indicators=indicators,
        recommendations=recommendations,
        model_version=(
            f"{text_bundle['metadata']['model_version']} + "
            f"{url_bundle['metadata']['model_version']}+{RULES_VERSION}"
        ),
        limitations=COMBINED_LIMITATIONS,
        urls=assessments,
    )
