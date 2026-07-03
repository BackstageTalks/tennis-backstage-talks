from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.tennisabstract.com"

OUTPUT_HTML_DIR = Path("public/bst_ai")
OUTPUT_DATA_DIR = Path("data/bst_ai")

REQUEST_TIMEOUT = 60

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Referer": "https://www.tennisabstract.com/",
}


@dataclass(frozen=True)
class TAReport:
    report_id: str
    tour: str
    report_type: str
    urls: list
    html_file: str
    json_file: str


REPORTS = [
    TAReport(
        report_id="atp_elo",
        tour="ATP",
        report_type="elo",
        urls=[
            "https://www.tennisabstract.com/reports/atp_elo_ratings.html",
            "https://tennisabstract.com/reports/atp_elo_ratings.html",
            "http://www.tennisabstract.com/reports/atp_elo_ratings.html",
            "http://tennisabstract.com/reports/atp_elo_ratings.html",
        ],
        html_file="atp_elo.html",
        json_file="atp_elo.json",
    ),
    TAReport(
        report_id="atp_yelo",
        tour="ATP",
        report_type="yelo",
        urls=[
            "https://www.tennisabstract.com/reports/atp_season_yelo_ratings.html",
            "https://tennisabstract.com/reports/atp_season_yelo_ratings.html",
            "http://www.tennisabstract.com/reports/atp_season_yelo_ratings.html",
            "http://tennisabstract.com/reports/atp_season_yelo_ratings.html",
        ],
        html_file="atp_yelo.html",
        json_file="atp_yelo.json",
    ),
    TAReport(
        report_id="wta_elo",
        tour="WTA",
        report_type="elo",
        urls=[
            "https://www.tennisabstract.com/reports/wta_elo_ratings.html",
            "https://tennisabstract.com/reports/wta_elo_ratings.html",
            "http://www.tennisabstract.com/reports/wta_elo_ratings.html",
            "http://tennisabstract.com/reports/wta_elo_ratings.html",
        ],
        html_file="wta_elo.html",
        json_file="wta_elo.json",
    ),
    TAReport(
        report_id="wta_yelo",
        tour="WTA",
        report_type="yelo",
        urls=[
            "https://www.tennisabstract.com/reports/wta_season_yelo_ratings.html",
            "https://tennisabstract.com/reports/wta_season_yelo_ratings.html",
            "http://www.tennisabstract.com/reports/wta_season_yelo_ratings.html",
            "http://tennisabstract.com/reports/wta_season_yelo_ratings.html",
        ],
        html_file="wta_yelo.html",
        json_file="wta_yelo.json",
    ),
]


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_dirs():
    OUTPUT_HTML_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DATA_DIR.mkdir(parents=True, exist_ok=True)


def clean_text(value):
    if value is None:
        return ""

    text = str(value)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_name(name):
    text = clean_text(name).lower()
    text = re.sub(r"[^a-z0-9]+", "", text)

    return text


def to_float(value):
    text = clean_text(value)

    if not text:
        return None

    text = text.replace(",", "")

    try:
        return float(text)
    except Exception:
        return None


def to_int(value):
    number = to_float(value)

    if number is None:
        return None

    return int(number)


def extract_player_id_from_href(href):
    if not href:
        return None

    absolute_url = urljoin(BASE_URL, href)
    parsed = urlparse(absolute_url)
    params = parse_qs(parsed.query)

    player_ids = params.get("p")

    if not player_ids:
        return None

    player_id = clean_text(player_ids[0])

    if not player_id:
        return None

    return player_id


def parse_player_cell(cell):
    player_name = clean_text(cell.get_text(" "))

    player_id = None
    player_url = None

    link = cell.find("a", href=True)

    if link:
        player_id = extract_player_id_from_href(
            link.get("href", "")
        )

        if player_id:
            player_url = f"{BASE_URL}/cgi-bin/player.cgi?p={player_id}"

    return {
        "player_name": player_name,
        "player_id": player_id,
        "player_url": player_url,
    }


def normalize_table_cells(raw_cells):
    """
    TA Elo tables include visual spacer cells between column groups.
    Those empty cells break fixed-index parsing.

    This helper removes only visually empty cells before mapping:
    Rank, Player, Age, Elo, hElo Rank, hElo,
    cElo Rank, cElo, gElo Rank, gElo,
    Peak Elo, Peak Month, ATP/WTA Rank, Log diff.
    """
    return [
        cell
        for cell in raw_cells
        if clean_text(cell.get_text(" "))
    ]


def download_html(report):
    errors = []

    for url in report.urls:
        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
            )

            if response.status_code == 403:
                errors.append(f"403 Forbidden: {url}")
                continue

            response.raise_for_status()

            html_text = response.text

            if "Player" not in html_text and "Elo" not in html_text and "yElo" not in html_text:
                errors.append(f"Unexpected HTML content: {url}")
                continue

            output_file = OUTPUT_HTML_DIR / report.html_file
            output_file.write_text(
                html_text,
                encoding="utf-8",
            )

            return html_text, url, errors

        except Exception as exc:
            errors.append(f"{url}: {exc}")

    return None, None, errors


def load_existing_report(report):
    path = OUTPUT_DATA_DIR / report.json_file

    if not path.exists():
        return None

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, dict) and data.get("records"):
            data["source_status"] = "CACHE_USED"
            data.setdefault("warnings", [])
            data["warnings"].append(
                "Live TA source unavailable; using previously stored real TA data."
            )
            return data

    except Exception:
        return None

    return None


def find_main_table(soup):
    tables = soup.find_all("table")

    if not tables:
        return None

    best_table = None
    best_score = -1

    for table in tables:
        text = clean_text(
            table.get_text(" ")
        )

        rows = table.find_all("tr")

        score = len(rows)

        if "Player" in text:
            score += 1000

        if "Elo" in text or "yElo" in text:
            score += 1000

        if score > best_score:
            best_score = score
            best_table = table

    return best_table


def parse_last_update(soup):
    text = clean_text(
        soup.get_text(" ")
    )

    match = re.search(
        r"Last update:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})",
        text,
    )

    if not match:
        return None

    return match.group(1)


def get_cells(row):
    return row.find_all(["td", "th"])


def looks_like_elo_rating(value):
    number = to_float(value)

    if number is None:
        return False

    return 1000 <= number <= 3000


def parse_standard_elo_row(cells, report, player_info):
    cells = normalize_table_cells(cells)

    if len(cells) < 10:
        return None

    h_elo = to_float(cells[5].get_text(" ")) if len(cells) > 5 else None
    c_elo = to_float(cells[7].get_text(" ")) if len(cells) > 7 else None
    g_elo = to_float(cells[9].get_text(" ")) if len(cells) > 9 else None

    warnings = []

    if h_elo is not None and not looks_like_elo_rating(h_elo):
        warnings.append(f"Invalid hElo parsed for {player_info.get('player_name')}: {h_elo}")
        h_elo = None

    if c_elo is not None and not looks_like_elo_rating(c_elo):
        warnings.append(f"Invalid cElo parsed for {player_info.get('player_name')}: {c_elo}")
        c_elo = None

    if g_elo is not None and not looks_like_elo_rating(g_elo):
        warnings.append(f"Invalid gElo parsed for {player_info.get('player_name')}: {g_elo}")
        g_elo = None

    record = {
        "tour": report.tour,
        "source": report.report_id,
        "report_type": "elo",
        "player_id": player_info.get("player_id"),
        "player_name": player_info.get("player_name"),
        "player_name_key": normalize_name(
            player_info.get("player_name") or ""
        ),
        "player_url": player_info.get("player_url"),
        "rank": to_int(cells[0].get_text(" ")) if len(cells) > 0 else None,
        "age": to_float(cells[2].get_text(" ")) if len(cells) > 2 else None,
        "elo": to_float(cells[3].get_text(" ")) if len(cells) > 3 else None,
        "h_elo_rank": to_int(cells[4].get_text(" ")) if len(cells) > 4 else None,
        "h_elo": h_elo,
        "c_elo_rank": to_int(cells[6].get_text(" ")) if len(cells) > 6 else None,
        "c_elo": c_elo,
        "g_elo_rank": to_int(cells[8].get_text(" ")) if len(cells) > 8 else None,
        "g_elo": g_elo,
        "peak_elo": to_float(cells[10].get_text(" ")) if len(cells) > 10 else None,
        "peak_month": clean_text(cells[11].get_text(" ")) if len(cells) > 11 else None,
        "official_rank": to_int(cells[12].get_text(" ")) if len(cells) > 12 else None,
        "log_diff": to_float(cells[13].get_text(" ")) if len(cells) > 13 else None,
    }

    if warnings:
        record["parse_warnings"] = warnings

    return record


def parse_yelo_row(cells, report, player_info):
    cells = normalize_table_cells(cells)

    if len(cells) < 5:
        return None

    return {
        "tour": report.tour,
        "source": report.report_id,
        "report_type": "yelo",
        "player_id": player_info.get("player_id"),
        "player_name": player_info.get("player_name"),
        "player_name_key": normalize_name(
            player_info.get("player_name") or ""
        ),
        "player_url": player_info.get("player_url"),
        "rank": to_int(cells[0].get_text(" ")),
        "wins": to_int(cells[2].get_text(" ")),
        "losses": to_int(cells[3].get_text(" ")),
        "yelo": to_float(cells[4].get_text(" ")),
    }


def parse_report(html_text, report, source_url):
    soup = BeautifulSoup(
        html_text,
        "html.parser",
    )

    table = find_main_table(
        soup,
    )

    parsed_at = utc_now_iso()
    last_update = parse_last_update(
        soup,
    )

    records = []
    warnings = []

    if table is None:
        return {
            "schema": "bst_ai_report_v1",
            "report_id": report.report_id,
            "tour": report.tour,
            "type": report.report_type,
            "source_url": source_url,
            "last_update": last_update,
            "parsed_at": parsed_at,
            "status": "NO_TABLE_FOUND",
            "source_status": "LIVE_OK",
            "record_count": 0,
            "records": [],
            "warnings": ["Main ratings table was not found."],
        }

    rows = table.find_all("tr")

    for row in rows:
        raw_cells = get_cells(row)
        cells = normalize_table_cells(raw_cells)

        if len(cells) < 4:
            continue

        rank_text = clean_text(
            cells[0].get_text(" ")
        )

        if not rank_text:
            continue

        if not rank_text[0].isdigit():
            continue

        player_info = parse_player_cell(
            cells[1],
        )

        if not player_info.get("player_name"):
            continue

        if report.report_type == "elo":
            record = parse_standard_elo_row(
                raw_cells,
                report,
                player_info,
            )

        elif report.report_type == "yelo":
            record = parse_yelo_row(
                raw_cells,
                report,
                player_info,
            )

        else:
            record = None

        if record:
            if record.get("parse_warnings"):
                warnings.extend(record.get("parse_warnings"))
            records.append(record)

    if not records:
        warnings.append(
            "No records parsed from table."
        )

    return {
        "schema": "bst_ai_report_v1",
        "report_id": report.report_id,
        "tour": report.tour,
        "type": report.report_type,
        "source_url": source_url,
        "last_update": last_update,
        "parsed_at": parsed_at,
        "status": "OK" if records else "NO_RECORDS",
        "source_status": "LIVE_OK",
        "record_count": len(records),
        "records": records,
        "warnings": warnings,
    }


def failed_report(report, errors):
    return {
        "schema": "bst_ai_report_v1",
        "report_id": report.report_id,
        "tour": report.tour,
        "type": report.report_type,
        "source_url": None,
        "last_update": None,
        "parsed_at": utc_now_iso(),
        "status": "SOURCE_UNAVAILABLE",
        "source_status": "LIVE_FAILED",
        "record_count": 0,
        "records": [],
        "warnings": errors,
    }


def merge_players(report_outputs):
    players = {}
    warnings = []

    for report_output in report_outputs:
        report_id = report_output.get("report_id")

        for warning in report_output.get("warnings", []):
            if "Invalid" in str(warning):
                warnings.append(warning)

        for record in report_output.get("records", []):
            player_id = record.get("player_id")
            player_name = record.get("player_name")
            player_name_key = record.get("player_name_key")
            tour = record.get("tour")

            if not player_id:
                warnings.append(
                    f"Missing player_id in {report_id}: {player_name}"
                )
                continue

            key = f"{tour}:{player_id}"

            if key not in players:
                players[key] = {
                    "player_key": key,
                    "player_id": player_id,
                    "player_name": player_name,
                    "player_name_key": player_name_key,
                    "player_url": record.get("player_url"),
                    "tour": tour,
                    "sources": [],
                    "elo": None,
                    "yelo": None,
                    "surface_elo": {
                        "hard": None,
                        "clay": None,
                        "grass": None,
                    },
                    "surface_elo_rank": {
                        "hard": None,
                        "clay": None,
                        "grass": None,
                    },
                    "ranking": {},
                    "season": {},
                    "status": "OK",
                }

            player = players[key]

            if report_id not in player["sources"]:
                player["sources"].append(report_id)

            if record.get("report_type") == "elo":
                player["elo"] = record.get("elo")
                player["surface_elo"]["hard"] = record.get("h_elo")
                player["surface_elo"]["clay"] = record.get("c_elo")
                player["surface_elo"]["grass"] = record.get("g_elo")
                player["surface_elo_rank"]["hard"] = record.get("h_elo_rank")
                player["surface_elo_rank"]["clay"] = record.get("c_elo_rank")
                player["surface_elo_rank"]["grass"] = record.get("g_elo_rank")
                player["ranking"]["elo_rank"] = record.get("rank")
                player["ranking"]["official_rank"] = record.get("official_rank")
                player["ranking"]["peak_elo"] = record.get("peak_elo")
                player["ranking"]["peak_month"] = record.get("peak_month")

            elif record.get("report_type") == "yelo":
                player["yelo"] = record.get("yelo")
                player["season"]["yelo_rank"] = record.get("rank")
                player["season"]["wins"] = record.get("wins")
                player["season"]["losses"] = record.get("losses")

    players_list = sorted(
        players.values(),
        key=lambda item: (
            item.get("tour") or "",
            item.get("player_name") or "",
        ),
    )

    return {
        "schema": "bst_ai_players_v2",
        "created_at": utc_now_iso(),
        "status": "OK" if players_list else "NO_DATA",
        "player_count": len(players_list),
        "players": players_list,
        "warnings": warnings,
        "rules": {
            "real_data_only": True,
            "no_fallback_probability": True,
            "never_use_bst_ai_50_percent": True,
            "missing_data_output": "No data",
            "surface_elo_must_be_rating_not_rank": True,
        },
    }


def write_json(path, data):
    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def write_status(report_outputs, players_index):
    live_failed_count = sum(
        1
        for report in report_outputs
        if report.get("source_status") == "LIVE_FAILED"
    )

    cache_used_count = sum(
        1
        for report in report_outputs
        if report.get("source_status") == "CACHE_USED"
    )

    if live_failed_count == len(report_outputs):
        status_value = "SOURCE_UNAVAILABLE"

    elif live_failed_count > 0 or cache_used_count > 0:
        status_value = "PARTIAL_OK"

    else:
        status_value = "OK"

    status = {
        "schema": "bst_ai_status_v2",
        "created_at": utc_now_iso(),
        "status": status_value,
        "reports": [
            {
                "report_id": report.get("report_id"),
                "tour": report.get("tour"),
                "type": report.get("type"),
                "source_url": report.get("source_url"),
                "last_update": report.get("last_update"),
                "parsed_at": report.get("parsed_at"),
                "status": report.get("status"),
                "source_status": report.get("source_status"),
                "record_count": report.get("record_count", 0),
                "warnings": report.get("warnings", []),
            }
            for report in report_outputs
        ],
        "player_count": players_index.get("player_count", 0),
        "warnings": players_index.get("warnings", []),
        "rules": {
            "real_data_only": True,
            "bst_ai_fallback_50_percent": False,
            "if_missing_data": "No data",
            "surface_elo_must_be_rating_not_rank": True,
        },
    }

    write_json(
        OUTPUT_DATA_DIR / "status.json",
        status,
    )


def main():
    ensure_dirs()

    report_outputs = []

    for report in REPORTS:
        print(
            f"Downloading {report.report_id}"
        )

        html_text, source_url, errors = download_html(
            report,
        )

        if html_text and source_url:
            parsed = parse_report(
                html_text,
                report,
                source_url,
            )

            write_json(
                OUTPUT_DATA_DIR / report.json_file,
                parsed,
            )

            print(
                f"Saved {report.report_id}: "
                f"{parsed.get('record_count', 0)} records"
            )

            report_outputs.append(
                parsed,
            )
            continue

        cached = load_existing_report(
            report,
        )

        if cached:
            print(
                f"Live source failed for {report.report_id}; using cached real data."
            )

            report_outputs.append(
                cached,
            )
            continue

        failed = failed_report(
            report,
            errors,
        )

        write_json(
            OUTPUT_DATA_DIR / report.json_file,
            failed,
        )

        print(
            f"Failed {report.report_id}: SOURCE_UNAVAILABLE"
        )

        report_outputs.append(
            failed,
        )

    players_index = merge_players(
        report_outputs,
    )

    write_json(
        OUTPUT_DATA_DIR / "players.json",
        players_index,
    )

    write_status(
        report_outputs,
        players_index,
    )

    print(
        "BsT AI sync completed."
    )


if __name__ == "__main__":
    main()
