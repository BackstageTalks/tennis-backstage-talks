import os

import requests


RAPID_API_HOST = (
    "tennis-api-atp-wta-itf.p.rapidapi.com"
)

BASE_URL = (
    f"https://{RAPID_API_HOST}"
)

TIMEOUT = 20


def _headers():

    return {
        "Content-Type": "application/json",
        "x-rapidapi-host": RAPID_API_HOST,
        "x-rapidapi-key": os.getenv(
            "RAPIDAPI_KEY",
            ""
        ),
    }


def get_event_id(
    player1: str,
    player2: str,
    date_only: str,
):
    url = (
        f"{BASE_URL}"
        f"/tennis/v2/extend/api/event/get"
        f"/{player1}"
        f"/{player2}"
        f"/{date_only}"
    )

    try:

        response = requests.get(
            url,
            headers=_headers(),
            timeout=TIMEOUT,
        )

        response.raise_for_status()

        payload = response.json()

        result = payload.get(
            "result",
            {}
        )

        event_id = result.get(
            "id"
        )

        if not event_id:
            return None

        return str(event_id)

    except Exception as exc:

        print(
            "MARQ EVENT ID ERROR:",
            str(exc),
        )

        return None


def get_odds_summary(
    event_id: str,
):
    url = (
        f"{BASE_URL}"
        f"/tennis/v2/extend/api/odds/summary"
        f"/{event_id}"
    )

    try:

        response = requests.get(
            url,
            headers=_headers(),
            timeout=TIMEOUT,
        )

        response.raise_for_status()

        return response.json()

    except Exception as exc:

        print(
            "MARQ ODDS SUMMARY ERROR:",
            str(exc),
        )

        return None


def get_recent_odds(
    event_id: str,
):
    url = (
        f"{BASE_URL}"
        f"/tennis/v2/extend/api/event/recent-odds/get"
        f"/{event_id}"
    )

    try:

        response = requests.get(
            url,
            headers=_headers(),
            timeout=TIMEOUT,
        )

        response.raise_for_status()

        return response.json()

    except Exception as exc:

        print(
            "MARQ RECENT ODDS ERROR:",
            str(exc),
        )

        return None
