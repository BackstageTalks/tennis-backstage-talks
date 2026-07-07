import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


RAW_DIR = Path("data/elo/raw")
HISTORY_DIR = Path("data/elo/raw_history")
META_DIR = Path("data/elo/meta")

USER_AGENT = "Mozilla/5.0 (compatible; backstage-talks-elo-cache/1.0)"
REQUEST_TIMEOUT_SECONDS = 45
REQUEST_SLEEP_SECONDS = 2

# Local filename -> Tennis Abstract source URL
SOURCE_MAP = {
    "atp_elo.html": "https://tennisabstract.com/reports/atp_elo_ratings.html",
    "wta_yelo.html": "https://tennisabstract.com/reports/wta_season_yelo_ratings.html",
    "wta_elo.html": "https://tennisabstract.com/reports/wta_elo_ratings.html",
    "atp_yelo.html": "https://tennisabstract.com/reports/atp_season_yelo_ratings.html",
}


def ensure_dirs():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    META_DIR.mkdir(parents=True, exist_ok=True)


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def today_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def fetch_url(url):
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )

    with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace")


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def copy_to_history(filename, html_text):
    date_dir = HISTORY_DIR / today_utc()
    date_dir.mkdir(parents=True, exist_ok=True)
    write_text(date_dir / filename, html_text)


def write_meta(filename, url, html_text, changed):
    meta_text = (
        f"filename={filename}\n"
        f"url={url}\n"
        f"downloaded_at_utc={utc_now_iso()}\n"
        f"sha256={sha256_text(html_text)}\n"
        f"changed={str(changed).lower()}\n"
        f"bytes={len(html_text.encode('utf-8', errors='replace'))}\n"
    )
    write_text(META_DIR / f"{filename}.meta", meta_text)


def validate_html(filename, html_text):
    lowered = html_text.lower()

    if "<html" not in lowered and "<table" not in lowered:
        raise RuntimeError(
            f"Downloaded content does not look like an HTML ratings page: {filename}"
        )

    if "tennis abstract" not in lowered and "elo" not in lowered:
        raise RuntimeError(
            f"Downloaded content does not look like Tennis Abstract Elo content: {filename}"
        )


def update_one(filename, url):
    destination = RAW_DIR / filename
    previous = destination.read_text(encoding="utf-8", errors="replace") if destination.exists() else None

    print("ELO DOWNLOAD START:", filename, url)
    html_text = fetch_url(url)
    validate_html(filename, html_text)

    changed = previous != html_text

    write_text(destination, html_text)
    copy_to_history(filename, html_text)
    write_meta(filename, url, html_text, changed)

    print(
        "ELO DOWNLOAD DONE:",
        filename,
        "changed=",
        changed,
        "bytes=",
        len(html_text.encode("utf-8", errors="replace")),
    )

    return changed


def main():
    ensure_dirs()

    any_changed = False
    failures = []

    for index, (filename, url) in enumerate(SOURCE_MAP.items(), start=1):
        try:
            changed = update_one(filename, url)
            any_changed = any_changed or changed
        except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
            print("ELO DOWNLOAD ERROR:", filename, url, repr(exc))
            failures.append((filename, url, repr(exc)))
        except Exception as exc:
            print("ELO DOWNLOAD UNEXPECTED ERROR:", filename, url, repr(exc))
            failures.append((filename, url, repr(exc)))

        if index < len(SOURCE_MAP):
            time.sleep(REQUEST_SLEEP_SECONDS)

    if failures:
        print("")
        print("ELO DOWNLOAD FAILURES:")
        for filename, url, error in failures:
            print(filename, url, error)
        raise SystemExit(1)

    print("")
    print("ELO DOWNLOAD SUMMARY:")
    print("any_changed=", any_changed)
    print("raw_dir=", RAW_DIR)
    print("history_dir=", HISTORY_DIR / today_utc())
    print("meta_dir=", META_DIR)


if __name__ == "__main__":
    main()
