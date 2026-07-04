import os
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from tennisapi_client import TennisApiClient, normalize_event


logger = logging.getLogger(__name__)


def parse_category_ids() -> List"""
    Default zatiaľ ATP = 3, potvrdené zo screenshotu.
    Ďalšie category ID doplníme po overení:
    napr. TENNISAPI_CATEGORY_IDS=3,6,12
    """
    raw = os.getenv("TENNISAPI_CATEGORY_IDS", "3").strip()

    category_ids = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue

        try:
            category_ids.append(int(part))
        except ValueError:
            logger.warning("Invalid TennisApi category id ignored: %s", part)

    return category_ids or [3]


def fetch_tennisapi_events_for_date(
    target_date: datetime,
    category_ids: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    client = TennisApiClient()
    category_ids = category_ids or parse_category_ids()

    raw_events = client.get_events_by_date(
        target_date=target_date,
        category_ids=category_ids,
    )

    normalized_events = []

    for event in raw_events:
        try:
            normalized = normalize_event(event)

            if not normalized.get("match_id"):
                continue

            if not normalized.get("player1") or not normalized.get("player2"):
                continue

            normalized_events.append(normalized)

        except Exception as exc:
            logger.warning("Failed to normalize TennisApi event: %s", exc)

    return normalized_events


def fetch_daily_fixtures(
    target_date: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    Primary fixtures datasource:
    TennisApi / REcodeX PRO

    Fallbacky SofaScore/SportScore sa môžu dopojiť nižšie, ale TennisApi
    je odteraz primárny zdroj.
    """
    target_date = target_date or datetime.now()

    tennisapi_events = fetch_tennisapi_events_for_date(target_date)

    if tennisapi_events:
        logger.info(
            "Fetched %s fixtures from TennisApi for %s",
            len(tennisapi_events),
            target_date.date(),
        )
        return tennisapi_events

    logger.warning("TennisApi returned no fixtures for %s", target_date.date())

    # Tu môžu ostať existujúce fallbacky, ak ich v projekte máš.
    # return fetch_sofascore_fixtures(target_date) or fetch_sportscore_fixtures(target_date)

    return []


def get_matches_for_snapshot(
    target_date: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    Použi túto funkciu v dennom workflow po 06:00 SK/CZ.
    """
    return fetch_daily_fixtures(target_date)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    today = datetime.now()
    matches = get_matches_for_snapshot(today)

    print(f"Matches found: {len(matches)}")

    for match in matches[:10]:
        print(
            match.get("match_id"),
            match.get("player1"),
            "vs",
            match.get("player2"),
            "|",
            match.get("tournament"),
            "|",
            match.get("status"),
        )
