from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://tennisabstract.com"

OUTPUT_HTML_DIR = Path("public/bst_ai")
OUTPUT_DATA_DIR = Path("data/bst_ai")

REQUEST_TIMEOUT = 60

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; BackstageTalks-BsT-AI/1.0)"
}


@dataclass(frozen=True)
class TAReport:
    report_id: str
    tour: str
    report_type: str
    url: str
    html_file: str
    json_file: str


REPORTS: List[TAReport] = [
    TAReport(
        report_id="atp_elo",
        tour="ATP",
        report_type="elo",
        url="https://tennisabstract.com/reports/atp_elo_ratings.html",
        html_file="atp_elo.html",
        json_file="atp_elo.json",
    ),
    TAReport(
        report_id="atp_yelo",
        tour="ATP",
        report_type="yelo",
        url="https://tennisabstract.com/reports/atp_season_yelo_ratings.html",
        html_file="atp_yelo.html",
        json_file="atp_yelo.json",
    ),
    TAReport(
        report_id="wta_elo",
        tour="WTA",
        report_type="elo",
        url="https://tennisabstract.com/reports/wta_elo_ratings.html",
        html_file="wta_elo.html",
        json_file="wta_elo.json",
    ),
    TAReport(
        report_id="wta_yelo",
        tour="WTA",
        report_type="yelo",
        url="https://tennisabstract.com/reports/wta_season_yelo_ratings.html",
        html_file="wta_yelo.html",
        json_file="wta_yelo.json",
    ),
]


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_dirs() -> None:
    OUTPUT_HTML_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DATA_DIR.mkdir(parents=True, exist_ok=True)


def clean_text(value: Any) -> str:
    if value is None:
        return ""

    text = str(value)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_name(name: str) -> str:
    text = clean_text(name).lower()
    text = re.sub(r"[^a-z0-9]+", "", text)

    return text


def to_float(value: Any) -> Optionaltext = clean_text(value)

    if not text:
        return None

    text = text.replace(",", "")

    try:
        return float(text)

    except Exception:
        return None


def to_int(value: Any) -> Optionalnumber = to_float(value)

    if number is None:
        return None

    return int(number)


def extract_player_id_from_href(href: str) -> Optionalif not href:
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


def parse_player_cell(cell: Any) -> Dict[str, Optional[str]]:
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


def download_html(report: TAReport) -> str:
    response = requests.get(
        report.url,
        headers=HEADERS,
        timeout=REQUEST_TIMEOUT,
    )

    response.raise_for_status()

    html = response.text

    output_file = OUTPUT_HTML_DIR / report.html_file

    output_file.write_text(
        html,
        encoding="utf-8",
    )

    return html


def find_main_table(soup: BeautifulSoup) -> Optionaltables = soup.find_all("table")

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


def parse_last_update(soup: BeautifulSoup) -> Optionaltext = clean_text(
        soup.get_text(" ")
    )

    match = re.search(
        r"Last update:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})",
        text,
    )

    if not match:
        return None

    return match.group(1)


def get_cells(row: Any) -> Listreturn row.find_all(["td", "th"])


def parse_standard_elo_row(
    cells: List[Any],
    report: TAReport,
    player_info: Dict[str, Optional[str]],
) -> Optional[Dict[str, Any]]:
    if len(cells) < 4:
        return None

    return {
        "tour": report.tour,
        "source": report.report_id,
        "report_type": "elo",
        "player_id": player_info.get("player_id"),
        "player_name": player_info.get("player_name"),
        "player_name_key": normalize_name(
            player_info.get("player_name") or ""
        ),
        "player_url": player_info.get("player_url"),
        "rank": to_int(cells[0].get_text(" ")),
        "age": to_float(cells[2].get_text(" ")) if len(cells) > 2 else None,
        "elo": to_float(cells[3].get_text(" ")) if len(cells) > 3 else None,
        "h_elo_rank": to_int(cells[4].get_text(" ")) if len(cells) > 4 else None,
        "h_elo": to_float(cells[5].get_text(" ")) if len(cells) > 5 else None,
        "c_elo_rank": to_int(cells[6].get_text(" ")) if len(cells) > 6 else None,
        "c_elo": to_float(cells[7].get_text(" ")) if len(cells) > 7 else None,
        "g_elo_rank": to_int(cells[8].get_text(" ")) if len(cells) > 8 else None,
        "g_elo": to_float(cells[9].get_text(" ")) if len(cells) > 9 else None,
        "peak_elo": to_float(cells[10].get_text(" ")) if len(cells) > 10 else None,
        "peak_month": clean_text(cells[11].get_text(" ")) if len(cells) > 11 else None,
        "official_rank": to_int(cells[12].get_text(" ")) if len(cells) > 12 else None,
        "log_diff": to_float(cells[13].get_text(" ")) if len(cells) > 13 else None,
    }


def parse_yelo_row(
    cells: List[Any],
    report: TAReport,
    player_info: Dict[str, Optional[str]],
) -> Optional[Dict[str, Any]]:
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


def parse_report(html: str, report: TAReport) -> Dict[str, Any]:
    soup = BeautifulSoup(
        html,
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
            "source_url": report.url,
            "last_update": last_update,
            "parsed_at": parsed_at,
            "status": "NO_TABLE_FOUND",
            "record_count": 0,
            "records": [],
            "warnings": ["Main ratings table was not found."],
        }

    rows = table.find_all("tr")

    for row in rows:
        cells = get_cells(row)

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
                cells,
                report,
                player_info,
            )

        elif report.report_type == "yelo":
            record = parse_yelo_row(
                cells,
                report,
                player_info,
            )

        else:
            record = None

        if record:
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
        "source_url": report.url,
        "last_update": last_update,
        "parsed_at": parsed_at,
        "status": "OK" if records else "NO_RECORDS",
        "record_count": len(records),
        "records": records,
        "warnings": warnings,
    }


def merge_players(report_outputs: List[Dict[str, Any]]) -> Dict[str, Any]:
    players = {}
    warnings = []

    for report_output in report_outputs:
        report_id = report_output.get("report_id")

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
        "schema": "bst_ai_players_v1",
        "created_at": utc_now_iso(),
        "status": "OK",
        "player_count": len(players_list),
        "players": players_list,
        "warnings": warnings,
        "rules": {
            "real_data_only": True,
            "no_fallback_probability": True,
            "never_use_bst_ai_50_percent": True,
            "missing_data_output": "No data",
        },
    }


def write_json(path: Path, data: Dict[str, Any]) -> None:
    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def write_status(
    report_outputs: List[Dict[str, Any]],
    players_index: Dict[str, Any],
) -> None:
    status = {
        "schema": "bst_ai_status_v1",
        "created_at": utc_now_iso(),
        "status": "OK",
        "reports": [
            {
                "report_id": report.get("report_id"),
                "tour": report.get("tour"),
                "type": report.get("type"),
                "source_url": report.get("source_url"),
                "last_update": report.get("last_update"),
                "parsed_at": report.get("parsed_at"),
                "status": report.get("status"),
                "record_count": report.get("record_count", 0),
                "warnings": report.get("warnings", []),
            }
            for report in report_outputs
        ],
        "player_count": players_index.get("player_count", 0),
        "rules": {
            "real_data_only": True,
            "bst_ai_fallback_50_percent": False,
            "if_missing_data": "No data",
        },
    }

    write_json(
        OUTPUT_DATA_DIR / "status.json",
        status,
    )


def main() -> None:
    ensure_dirs()

    report_outputs = []

    for report in REPORTS:
        print(
            f"Downloading {report.report_id}: {report.url}"
        )

        html = download_html(
            report,
        )

        parsed = parse_report(
            html,
            report,
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
