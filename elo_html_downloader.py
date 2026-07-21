import csv
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


RAW_DIR = Path("data/elo/raw")
HISTORY_DIR = Path("data/elo/raw_history")
META_DIR = Path("data/elo/meta")
ELO_STORE_PATH = Path("data/elo/elo_store.json")

USER_AGENT = "Mozilla/5.0 (compatible; backstage-talks-elo-cache/1.0)"
REQUEST_TIMEOUT_SECONDS = 45
REQUEST_SLEEP_SECONDS = 2

# Local filename -> Tennis Abstract source URL
SOURCE_MAP = {
    "atp_elo.html": "https://tennisabstract.com/reports/atp_elo_ratings.html",
    "wta_elo.html": "https://tennisabstract.com/reports/wta_elo_ratings.html",
    "atp_yelo.html": "https://tennisabstract.com/reports/atp_season_yelo_ratings.html",
    "wta_yelo.html": "https://tennisabstract.com/reports/wta_season_yelo_ratings.html",
}

LATEST_CSV_MAP = {
    "atp_elo.html": "atp_elo_latest.csv",
    "wta_elo.html": "wta_elo_latest.csv",
    "atp_yelo.html": "atp_yelo_latest.csv",
    "wta_yelo.html": "wta_yelo_latest.csv",
}


class TableParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.current_cell = []
        self.current_row = []
        self.tables = []
        self.current_table = []

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == "table":
            self.in_table = True
            self.current_table = []
        elif tag == "tr" and self.in_table:
            self.in_row = True
            self.current_row = []
        elif tag in {"td", "th"} and self.in_row:
            self.in_cell = True
            self.current_cell = []

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in {"td", "th"} and self.in_cell:
            text = clean_text(" ".join(self.current_cell))
            self.current_row.append(text)
            self.in_cell = False
            self.current_cell = []
        elif tag == "tr" and self.in_row:
            row = [cell for cell in self.current_row if cell != ""]
            if row:
                self.current_table.append(row)
            self.in_row = False
            self.current_row = []
        elif tag == "table" and self.in_table:
            if self.current_table:
                self.tables.append(self.current_table)
            self.in_table = False
            self.current_table = []

    def handle_data(self, data):
        if self.in_cell:
            self.current_cell.append(data)


def ensure_dirs():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    META_DIR.mkdir(parents=True, exist_ok=True)
    ELO_STORE_PATH.parent.mkdir(parents=True, exist_ok=True)


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def today_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def clean_text(value):
    value = re.sub(r"\s+", " ", str(value or "")).strip()
    return value.replace("\xa0", " ").strip()


def safe_float(value):
    try:
        if value is None:
            return None
        text = str(value).replace(",", "").replace("%", "").strip()
        if text == "" or text.lower() in {"nan", "none", "null", "-"}:
            return None
        return float(text)
    except Exception:
        return None


def normalize_header(value):
    text = clean_text(value).lower()
    text = text.replace(".", "").replace("_", " ").replace("-", " ")
    return re.sub(r"\s+", " ", text).strip()


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
        raise RuntimeError(f"Downloaded content does not look like an HTML ratings page: {filename}")
    if "tennis abstract" not in lowered and "elo" not in lowered:
        raise RuntimeError(f"Downloaded content does not look like Tennis Abstract Elo content: {filename}")


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
    print("ELO DOWNLOAD DONE:", filename, "changed=", changed, "bytes=", len(html_text.encode("utf-8", errors="replace")))
    return changed


def parse_tables(html_text):
    parser = TableParser()
    parser.feed(html_text)
    return parser.tables


def looks_like_header(row):
    normalized = [normalize_header(cell) for cell in row]
    joined = " ".join(normalized)
    return "player" in normalized or "player" in joined or "elo" in joined or "rank" in joined


def pick_rating_table(tables):
    best = []
    best_score = -1
    for table in tables:
        if len(table) < 5:
            continue
        header_index = None
        for i, row in enumerate(table[:8]):
            if looks_like_header(row):
                header_index = i
                break
        if header_index is None:
            continue
        header = table[header_index]
        data_rows = table[header_index + 1:]
        normalized_header = [normalize_header(cell) for cell in header]
        score = len(data_rows)
        if any("player" == cell for cell in normalized_header):
            score += 200
        if any("elo" in cell for cell in normalized_header):
            score += 100
        if score > best_score:
            best_score = score
            best = [header] + data_rows
    return best


def column_index(headers, candidates, contains=False):
    normalized = [normalize_header(h) for h in headers]
    candidate_set = [normalize_header(c) for c in candidates]
    for candidate in candidate_set:
        for i, header in enumerate(normalized):
            if header == candidate:
                return i
    if contains:
        for candidate in candidate_set:
            for i, header in enumerate(normalized):
                if candidate in header:
                    return i
    return None


def value_at(row, index):
    if index is None or index >= len(row):
        return None
    return clean_text(row[index])


def parse_rating_html(html_text, source_name, tour, rating_type):
    tables = parse_tables(html_text)
    table = pick_rating_table(tables)
    if not table:
        raise RuntimeError(f"No rating table found for {source_name}")

    headers = table[0]
    rows = table[1:]

    player_idx = column_index(headers, ["player", "name", "Player"])
    rank_idx = column_index(headers, ["elo rank", "yelo rank", "rank"])

    if rating_type == "elo":
        rating_idx = column_index(headers, ["elo", "rating", "overall elo", "overall"])
    else:
        rating_idx = column_index(headers, ["yelo", "year elo", "season elo", "seasonal elo", "elo", "rating"])

    hard_idx = column_index(headers, ["helo", "h elo", "hard elo", "hard"])
    clay_idx = column_index(headers, ["celo", "c elo", "clay elo", "clay"])
    grass_idx = column_index(headers, ["gelo", "g elo", "grass elo", "grass"])

    if player_idx is None:
        raise RuntimeError(f"Player column not found for {source_name}. headers={headers}")
    if rating_idx is None:
        raise RuntimeError(f"Rating column not found for {source_name}. headers={headers}")

    parsed = []
    for row in rows:
        if len(row) <= max(player_idx, rating_idx):
            continue
        player = value_at(row, player_idx)
        rating = safe_float(value_at(row, rating_idx))
        if not player or rating is None:
            continue
        item = {
            "player": player,
            "tour": tour,
            "source_file": source_name,
            "updated_at_utc": utc_now_iso(),
        }
        rank_value = safe_float(value_at(row, rank_idx))
        if rank_value is not None:
            item["rank"] = int(rank_value)
        if rating_type == "elo":
            item["elo"] = rating
            hard = safe_float(value_at(row, hard_idx))
            clay = safe_float(value_at(row, clay_idx))
            grass = safe_float(value_at(row, grass_idx))
            if hard is not None:
                item["hard_elo"] = hard
            if clay is not None:
                item["clay_elo"] = clay
            if grass is not None:
                item["grass_elo"] = grass
        else:
            item["yelo"] = rating
        parsed.append(item)

    if len(parsed) < 20:
        raise RuntimeError(f"Too few rows parsed for {source_name}: {len(parsed)}")
    return parsed


def write_csv(path, rows, rating_type):
    if rating_type == "elo":
        fieldnames = ["player", "tour", "rank", "elo", "hard_elo", "clay_elo", "grass_elo", "source_file", "updated_at_utc"]
    else:
        fieldnames = ["player", "tour", "rank", "yelo", "source_file", "updated_at_utc"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def merge_player_store(csv_payloads):
    players = {}
    for source_name, rows in csv_payloads.items():
        for row in rows:
            player = row.get("player")
            if not player:
                continue
            record = players.setdefault(
                player,
                {
                    "elo": DEFAULT_ELO_FALLBACK,
                    "yelo": DEFAULT_ELO_FALLBACK,
                    "surfaces": {},
                    "tour": row.get("tour"),
                    "sources": [],
                },
            )
            if row.get("tour"):
                record["tour"] = row.get("tour")
            if row.get("elo") is not None:
                record["elo"] = row.get("elo")
            if row.get("yelo") is not None:
                record["yelo"] = row.get("yelo")
            for surface_key, field in [("hard", "hard_elo"), ("clay", "clay_elo"), ("grass", "grass_elo")]:
                if row.get(field) is not None:
                    record["surfaces"][surface_key] = row.get(field)
            record["sources"].append(source_name)
    return {
        "generated_at_utc": utc_now_iso(),
        "players": players,
    }


DEFAULT_ELO_FALLBACK = 1500.0


def parse_latest_files():
    payloads = {}
    for filename in SOURCE_MAP:
        html_path = RAW_DIR / filename
        if not html_path.exists():
            raise RuntimeError(f"Raw HTML missing: {html_path}")
        html_text = html_path.read_text(encoding="utf-8", errors="replace")
        tour = "ATP" if filename.startswith("atp_") else "WTA"
        rating_type = "yelo" if "yelo" in filename else "elo"
        rows = parse_rating_html(html_text, filename, tour, rating_type)
        csv_name = LATEST_CSV_MAP[filename]
        csv_path = Path("data/elo") / csv_name
        write_csv(csv_path, rows, rating_type)
        payloads[filename] = rows
        print("ELO PARSE DONE:", filename, "->", csv_path, "rows=", len(rows))
    store = merge_player_store(payloads)
    write_text(ELO_STORE_PATH, json.dumps(store, indent=2, ensure_ascii=False))
    print("ELO STORE WRITTEN:", ELO_STORE_PATH, "players=", len(store.get("players", {})))
    return payloads


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

    payloads = parse_latest_files()

    print("")
    print("ELO DOWNLOAD SUMMARY:")
    print("any_changed=", any_changed)
    print("raw_dir=", RAW_DIR)
    print("history_dir=", HISTORY_DIR / today_utc())
    print("meta_dir=", META_DIR)
    print("latest_csv_files=", ", ".join(str(Path("data/elo") / LATEST_CSV_MAP[name]) for name in SOURCE_MAP))
    print("elo_store=", ELO_STORE_PATH)
    print("parsed_rows=", {name: len(rows) for name, rows in payloads.items()})


if __name__ == "__main__":
    main()
