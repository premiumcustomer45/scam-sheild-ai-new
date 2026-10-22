"""Domain reputation helpers used alongside the lexical URL model.

All checks work on the URL text only; nothing here performs a network request.
The lists are intentionally small and curated: they cover widely used global
and Indian services that scam campaigns most often imitate.
"""
from __future__ import annotations

# Registrable domains of well-known services. A URL is "trusted" only when its
# registrable domain matches exactly (so login.microsoftonline.com is trusted,
# but microsoft-login.xyz is not).
TRUSTED_DOMAINS = frozenset(
    {
        # Search, AI, productivity
        "google.com", "google.co.in", "youtube.com", "youtu.be", "gmail.com",
        "chatgpt.com", "openai.com", "claude.ai", "anthropic.com", "gemini.google.com",
        "bing.com", "microsoft.com", "microsoftonline.com", "live.com", "office.com",
        "outlook.com", "apple.com", "icloud.com", "wikipedia.org", "github.com",
        "stackoverflow.com", "notion.so", "zoom.us", "dropbox.com", "adobe.com",
        "canva.com", "medium.com", "mozilla.org", "cloudflare.com", "vercel.com",
        # Social and messaging
        "facebook.com", "instagram.com", "whatsapp.com", "x.com", "twitter.com",
        "linkedin.com", "reddit.com", "telegram.org", "discord.com", "snapchat.com",
        "pinterest.com", "quora.com", "threads.net",
        # Shopping, payments, travel (global + India)
        "amazon.com", "amazon.in", "flipkart.com", "myntra.com", "meesho.com",
        "ajio.com", "nykaa.com", "snapdeal.com", "swiggy.com", "zomato.com",
        "bigbasket.com", "blinkit.com", "zeptonow.com", "paypal.com", "paytm.com",
        "phonepe.com", "razorpay.com", "bhimupi.org.in", "npci.org.in", "makemytrip.com",
        "irctc.co.in", "booking.com", "airbnb.com", "uber.com", "olacabs.com",
        "netflix.com", "hotstar.com", "primevideo.com", "spotify.com", "jio.com",
        "airtel.in", "bsnl.co.in", "vi.in",
        # Banks and financial services (India)
        "onlinesbi.sbi", "sbi.co.in", "hdfcbank.com", "icicibank.com", "axisbank.com",
        "kotak.com", "pnbindia.in", "bankofbaroda.in", "canarabank.com",
        "unionbankofindia.co.in", "idfcfirstbank.com", "yesbank.in", "indusind.com",
        "rbi.org.in", "sebi.gov.in", "licindia.in", "zerodha.com", "groww.in",
        # Government and education (India)
        "india.gov.in", "uidai.gov.in", "incometax.gov.in", "gst.gov.in",
        "epfindia.gov.in", "digilocker.gov.in", "passportindia.gov.in",
        "parivahan.gov.in", "cybercrime.gov.in", "mygov.in", "nic.in",
        "indiapost.gov.in",
        # Couriers
        "dhl.com", "dhl.co.in", "fedex.com", "bluedart.com", "delhivery.com",
    }
)

# Suffixes under which registrations happen one level deeper.
_MULTI_PART_SUFFIXES = frozenset(
    {
        "co.in", "org.in", "net.in", "gov.in", "ac.in", "edu.in", "res.in", "nic.in",
        "co.uk", "org.uk", "gov.uk", "ac.uk", "com.au", "net.au", "co.jp", "com.br",
        "co.nz", "co.za", "com.sg", "com.my",
    }
)

# Brand keyword -> registrable domains that legitimately use it.
BRANDS: dict[str, frozenset[str]] = {
    "paypal": frozenset({"paypal.com"}),
    "google": frozenset({"google.com", "google.co.in", "youtube.com"}),
    "gmail": frozenset({"gmail.com", "google.com"}),
    "apple": frozenset({"apple.com", "icloud.com"}),
    "icloud": frozenset({"icloud.com", "apple.com"}),
    "microsoft": frozenset({"microsoft.com", "microsoftonline.com", "live.com", "office.com"}),
    "outlook": frozenset({"outlook.com", "microsoft.com", "live.com", "office.com"}),
    "office365": frozenset({"office.com", "microsoft.com"}),
    "amazon": frozenset({"amazon.com", "amazon.in", "primevideo.com"}),
    "flipkart": frozenset({"flipkart.com"}),
    "netflix": frozenset({"netflix.com"}),
    "facebook": frozenset({"facebook.com"}),
    "instagram": frozenset({"instagram.com"}),
    "whatsapp": frozenset({"whatsapp.com"}),
    "telegram": frozenset({"telegram.org"}),
    "chatgpt": frozenset({"chatgpt.com", "openai.com"}),
    "openai": frozenset({"openai.com", "chatgpt.com"}),
    "paytm": frozenset({"paytm.com"}),
    "phonepe": frozenset({"phonepe.com"}),
    "sbi": frozenset({"onlinesbi.sbi", "sbi.co.in"}),
    "onlinesbi": frozenset({"onlinesbi.sbi"}),
    "hdfc": frozenset({"hdfcbank.com"}),
    "icici": frozenset({"icicibank.com"}),
    "axisbank": frozenset({"axisbank.com"}),
    "kotak": frozenset({"kotak.com"}),
    "irctc": frozenset({"irctc.co.in"}),
    "aadhaar": frozenset({"uidai.gov.in"}),
    "uidai": frozenset({"uidai.gov.in"}),
    "incometax": frozenset({"incometax.gov.in"}),
    "epfo": frozenset({"epfindia.gov.in"}),
    "digilocker": frozenset({"digilocker.gov.in"}),
    "airtel": frozenset({"airtel.in"}),
    "jio": frozenset({"jio.com"}),
    "linkedin": frozenset({"linkedin.com"}),
    "dhl": frozenset({"dhl.com", "dhl.co.in"}),
    "fedex": frozenset({"fedex.com"}),
    "indiapost": frozenset({"indiapost.gov.in"}),
}

# TLDs that are cheap or free to register and are heavily used in phishing.
RISKY_TLDS = frozenset(
    {
        "xyz", "top", "tk", "ml", "ga", "cf", "gq", "zip", "mov", "click", "link",
        "loan", "work", "rest", "country", "kim", "men", "date", "racing", "win",
        "bid", "review", "stream", "download", "cam", "icu", "buzz", "monster",
        "cyou", "sbs", "cfd", "lol", "quest", "shop", "live", "online", "site",
        "website", "space", "fun", "info", "support", "help", "best",
    }
)

URL_SHORTENERS = frozenset(
    {
        "bit.ly", "tinyurl.com", "t.co", "goo.gl", "is.gd", "cutt.ly", "rb.gy",
        "ow.ly", "shorturl.at", "tiny.cc", "rebrand.ly", "buff.ly", "s.id",
        "v.gd", "shorte.st", "adf.ly", "t.ly", "bl.ink", "short.io", "surl.li",
    }
)

# Free hosting / tunnelling platforms where anyone can publish a page.
FREE_HOSTING_SUFFIXES = (
    "000webhostapp.com", "ngrok-free.app", "ngrok.io", "ngrok.app",
    "trycloudflare.com", "duckdns.org", "glitch.me", "repl.co", "replit.app",
    "weebly.com", "wixsite.com", "blogspot.com", "firebaseapp.com", "web.app",
    "netlify.app", "pages.dev", "workers.dev", "github.io", "herokuapp.com",
    "vercel.app", "onrender.com", "sites.google.com", "forms.gle", "webflow.io",
    "carrd.co", "square.site", "godaddysites.com", "mystrikingly.com",
)

DANGEROUS_EXTENSIONS = (
    ".apk", ".exe", ".msi", ".scr", ".bat", ".cmd", ".ps1", ".vbs", ".jar", ".dmg",
)

_HOMOGLYPHS = str.maketrans({"0": "o", "1": "l", "3": "e", "4": "a", "5": "s", "7": "t", "8": "b", "@": "a"})


def registrable_domain(hostname: str) -> str:
    labels = [label for label in hostname.lower().rstrip(".").split(".") if label]
    if len(labels) <= 2:
        return ".".join(labels)
    if ".".join(labels[-2:]) in _MULTI_PART_SUFFIXES:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def tld(hostname: str) -> str:
    return hostname.lower().rstrip(".").rsplit(".", 1)[-1]


def is_trusted(hostname: str) -> bool:
    host = hostname.lower().rstrip(".")
    return registrable_domain(host) in TRUSTED_DOMAINS or host in TRUSTED_DOMAINS


def is_shortener(hostname: str) -> bool:
    return registrable_domain(hostname) in URL_SHORTENERS or hostname.lower() in URL_SHORTENERS


def free_hosting_platform(hostname: str) -> str | None:
    host = hostname.lower().rstrip(".")
    for suffix in FREE_HOSTING_SUFFIXES:
        if host.endswith("." + suffix):
            return suffix
    return None


def impersonated_brand(hostname: str, path: str) -> str | None:
    """Return a brand named in the hostname or path of a URL that is not one of its official domains."""
    domain = registrable_domain(hostname)
    if domain in TRUSTED_DOMAINS:
        return None
    host = hostname.lower()
    normalized_host = host.translate(_HOMOGLYPHS).replace("rn", "m").replace("vv", "w")
    for brand, official in BRANDS.items():
        if domain in official:
            continue
        # Short brand names (sbi, jio) only count as whole hostname tokens to
        # avoid matching unrelated words.
        tokens = set(normalized_host.replace("-", ".").split("."))
        in_host = brand in tokens if len(brand) <= 4 else brand in normalized_host
        in_path = len(brand) > 4 and brand in path.lower()
        if in_host or in_path:
            return brand
    return None


_SIMILAR_CHARS = {frozenset(pair) for pair in ("il", "lj", "oq", "uv", "nm", "ce", "gq")}


def _is_typo_of(name: str, target: str) -> bool:
    """True for one inserted/deleted character, or one swap to a similar-looking character."""
    if len(name) == len(target):
        diffs = [(a, b) for a, b in zip(name, target) if a != b]
        if len(diffs) == 1:
            return frozenset(diffs[0]) in _SIMILAR_CHARS
        # Adjacent transposition, e.g. "amzaon".
        return (
            len(diffs) == 2
            and sorted(name) == sorted(target)
            and any(name[i:i + 2] == target[i:i + 2][::-1] for i in range(len(name) - 1))
        )
    if abs(len(name) - len(target)) != 1:
        return False
    shorter, longer = sorted((name, target), key=len)
    return any(longer[:i] + longer[i + 1:] == shorter for i in range(len(longer)))


def lookalike_of(hostname: str) -> str | None:
    """Return a trusted domain that this hostname imitates by a small spelling change."""
    domain = registrable_domain(hostname)
    if domain in TRUSTED_DOMAINS:
        return None
    name = domain.split(".", 1)[0]
    if len(name) < 4:
        return None
    normalized = name.translate(_HOMOGLYPHS).replace("rn", "m").replace("vv", "w")
    for trusted in TRUSTED_DOMAINS:
        trusted_name = trusted.split(".", 1)[0]
        if len(trusted_name) < 5 or trusted_name == name:
            continue
        if normalized == trusted_name or (len(trusted_name) >= 6 and _is_typo_of(name, trusted_name)):
            return trusted
    return None
