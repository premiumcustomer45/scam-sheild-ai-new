import pytest

from app.services.url_features import URL_FEATURES, extract_url_features, parse_url, safe_url_preview


def test_normal_url_returns_exact_feature_contract():
    features = extract_url_features("https://example.com/news?id=3#top")
    assert list(features) == URL_FEATURES
    assert features["uses_https"] == 1
    assert features["query_parameter_count"] == 1
    assert features["has_fragment"] == 1


@pytest.mark.parametrize(
    "value",
    ["", "not a url", "ftp://example.com", "https://example.com:99999/path"],
)
def test_malformed_or_unsupported_urls_are_rejected(value):
    with pytest.raises(ValueError):
        extract_url_features(value)


def test_unicode_hostname_is_converted_for_feature_extraction():
    parsed, hostname, _ = parse_url("https://bücher.example/angebot")
    assert parsed.scheme == "https"
    assert hostname.startswith("xn--")
    assert extract_url_features("https://bücher.example/angebot")["has_punycode_label"] == 1


@pytest.mark.parametrize(
    ("value", "is_ip"),
    [
        ("http://192.0.2.4/path", 1),
        ("https://[2001:db8::1]:8443/path", 1),
        ("https://example.com/path", 0),
    ],
)
def test_ipv4_ipv6_and_domain_hosts(value, is_ip):
    assert extract_url_features(value)["is_ip_host"] == is_ip


def test_encoded_query_fragment_and_nonstandard_port_are_counted():
    features = extract_url_features("https://example.com:8443/a%2Fb?x=1&y=2#part")
    assert features["has_nonstandard_port"] == 1
    assert features["percent_escape_count"] == 1
    assert features["query_parameter_count"] == 2
    assert features["has_fragment"] == 1


def test_deceptive_hostname_does_not_treat_brand_text_as_registered_domain():
    features = extract_url_features("https://paypal.com.signin.evil.example/login")
    assert features["subdomain_count"] >= 2
    assert features["suspicious_token_count"] >= 2


def test_safe_preview_removes_user_info_path_query_and_fragment():
    preview = safe_url_preview("https://user:secret@example.com/reset?token=private#account")
    assert preview == "https://example.com/…"
    assert "secret" not in preview
    assert "reset" not in preview
    assert "token" not in preview
