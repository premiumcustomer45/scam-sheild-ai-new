from __future__ import annotations

import ipaddress
import re
from urllib.parse import parse_qsl, urlsplit

URL_FEATURES = [
    "url_length",
    "hostname_length",
    "subdomain_count",
    "is_ip_host",
    "has_userinfo",
    "percent_escape_count",
    "path_length",
    "query_length",
    "query_parameter_count",
    "has_fragment",
    "has_nonstandard_port",
    "digit_ratio",
    "dot_count",
    "hyphen_count",
    "at_sign_count",
    "suspicious_token_count",
    "uses_https",
    "has_punycode_label",
    "path_depth",
]

SUSPICIOUS_TERMS = (
    "account",
    "auth",
    "bank",
    "billing",
    "confirm",
    "credential",
    "login",
    "password",
    "recover",
    "secure",
    "signin",
    "support",
    "update",
    "verify",
    "wallet",
)
_TOKEN_PATTERN = re.compile(
    r"(?i)(?<![a-z0-9])(" + "|".join(map(re.escape, SUSPICIOUS_TERMS)) + r")(?![a-z0-9])"
)
_PERCENT_PATTERN = re.compile(r"%[0-9a-fA-F]{2}")


def parse_url(value: str):
    raw = value.strip()
    if not raw:
        raise ValueError("Enter a URL to scan.")
    candidate = raw if "://" in raw else f"http://{raw}"
    try:
        parsed = urlsplit(candidate)
        # Accessing .port validates invalid and out-of-range ports.
        port = parsed.port
    except ValueError as exc:
        raise ValueError("The URL has an invalid hostname or port.") from exc
    if parsed.scheme.lower() not in {"http", "https"}:
        raise ValueError("Only HTTP and HTTPS URLs can be analyzed.")
    if not parsed.hostname:
        raise ValueError("The URL must include a hostname.")
    if any(ord(char) <= 32 or ord(char) == 127 for char in parsed.netloc):
        raise ValueError("The URL hostname contains whitespace or control characters.")
    try:
        ascii_host = parsed.hostname.encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise ValueError("The URL hostname is not valid.") from exc
    try:
        ipaddress.ip_address(ascii_host.strip("[]"))
    except ValueError:
        labels = ascii_host.rstrip(".").split(".")
        if len(ascii_host) > 253 or any(
            not label
            or len(label) > 63
            or re.fullmatch(r"[a-z0-9](?:[a-z0-9-]*[a-z0-9])?", label) is None
            for label in labels
        ):
            raise ValueError("The URL hostname is not valid.")
    return parsed, ascii_host, port


def extract_url_features(value: str) -> dict[str, float]:
    parsed, hostname, port = parse_url(value)
    host_labels = [label for label in hostname.rstrip(".").split(".") if label]
    try:
        ipaddress.ip_address(hostname.strip("[]"))
        is_ip_host = 1.0
    except ValueError:
        is_ip_host = 0.0

    # Use the same scheme-normalized form for both training and live inference.
    full_url = parsed.geturl()
    path = parsed.path or ""
    query = parsed.query or ""
    digits = sum(char.isdigit() for char in full_url)
    standard_port = port is None or (
        parsed.scheme.lower() == "http" and port == 80
    ) or (parsed.scheme.lower() == "https" and port == 443)

    return {
        "url_length": float(len(full_url)),
        "hostname_length": float(len(hostname)),
        "subdomain_count": float(max(0, len(host_labels) - 2)),
        "is_ip_host": is_ip_host,
        "has_userinfo": float(parsed.username is not None or parsed.password is not None),
        "percent_escape_count": float(len(_PERCENT_PATTERN.findall(full_url))),
        "path_length": float(len(path)),
        "query_length": float(len(query)),
        "query_parameter_count": float(len(parse_qsl(query, keep_blank_values=True))),
        "has_fragment": float(bool(parsed.fragment)),
        "has_nonstandard_port": float(not standard_port),
        "digit_ratio": float(digits / max(1, len(full_url))),
        "dot_count": float(full_url.count(".")),
        "hyphen_count": float(full_url.count("-")),
        "at_sign_count": float(full_url.count("@")),
        "suspicious_token_count": float(len(_TOKEN_PATTERN.findall(full_url))),
        "uses_https": float(parsed.scheme.lower() == "https"),
        "has_punycode_label": float(any(label.startswith("xn--") for label in host_labels)),
        "path_depth": float(len([part for part in path.split("/") if part])),
    }


def safe_url_preview(value: str) -> str:
    """Return an origin-only preview; paths may contain private reset tokens."""
    parsed, hostname, port = parse_url(value)
    host = f"[{hostname}]" if ":" in hostname and not hostname.startswith("[") else hostname
    netloc = host if port is None else f"{host}:{port}"
    path_marker = "/…" if parsed.path not in {"", "/"} else ""
    return f"{parsed.scheme.lower()}://{netloc}{path_marker}"
