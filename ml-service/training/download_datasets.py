from __future__ import annotations

import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "raw"
DATASETS = {
    "phiusiil.zip": "https://archive.ics.uci.edu/static/public/967/phiusiil+phishing+url+dataset.zip",
    "sms-spam.zip": "https://archive.ics.uci.edu/static/public/228/sms+spam+collection.zip",
}


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for filename, url in DATASETS.items():
        destination = DATA_DIR / filename
        request = urllib.request.Request(
            url,
            headers={"User-Agent": "ScamShieldAI-educational-project/1.0"},
        )
        print(f"Downloading {filename} from the official UCI repository...")
        try:
            with urllib.request.urlopen(request, timeout=60) as response, destination.open("wb") as output:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
        except Exception:
            destination.unlink(missing_ok=True)
            raise
        if not zipfile.is_zipfile(destination):
            destination.unlink(missing_ok=True)
            raise RuntimeError(f"Downloaded file is not a valid ZIP archive: {filename}")
        with zipfile.ZipFile(destination) as archive:
            if archive.testzip() is not None:
                destination.unlink(missing_ok=True)
                raise RuntimeError(f"ZIP integrity check failed: {filename}")
        print(f"Verified {filename} ({destination.stat().st_size:,} bytes).")


if __name__ == "__main__":
    main()
