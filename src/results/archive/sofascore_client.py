import json
import os
from datetime import datetime, timezone


DEBUG_PATH = "public/sofascore_debug.json"


def write_debug(data):
    os.makedirs(
        "public",
        exist_ok=True,
    )

    with open(
        DEBUG_PATH,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            data,
            file,
            indent=2,
            ensure_ascii=False,
        )


def load_sofascore_client():
    """
    Safely load ScraperFC SofaScore client.

    This is optional infrastructure.
    If ScraperFC is unavailable or SofaScore changes,
    TBT must not crash.
    """

    try:
        from ScraperFC.sofascore import Sofascore

        return Sofascore(), None

    except Exception as exc:

        try:
            from ScraperFC import Sofascore

            return Sofascore(), None

        except Exception as inner_exc:

            return None, f"{exc} | {inner_exc}"


def get_match_dict(match_id_or_url):
    """
    Return SofaScore match dictionary for a match id or URL.

    Input can be:
    - SofaScore numeric match id
    - SofaScore match URL
    """

    client, error = load_sofascore_client()

    if error:
        return {
            "ok": False,
            "error": error,
            "data": None,
        }

    try:
        data = client.get_match_dict(
            match_id_or_url
        )

        return {
            "ok": True,
            "error": None,
            "data": data,
        }

    except Exception as exc:

        return {
            "ok": False,
            "error": str(exc),
            "data": None,
        }


def get_match_id_from_url(match_url):
    """
    Extract SofaScore match id from URL.
    """

    client, error = load_sofascore_client()

    if error:
        return {
            "ok": False,
            "error": error,
            "match_id": None,
        }

    try:
        match_id = client.get_match_id_from_url(
            match_url
        )

        return {
            "ok": True,
            "error": None,
            "match_id": match_id,
        }

    except Exception as exc:

        return {
            "ok": False,
            "error": str(exc),
            "match_id": None,
        }


def get_match_url_from_id(match_id):
    """
    Build SofaScore URL from match id.
    """

    client, error = load_sofascore_client()

    if error:
        return {
            "ok": False,
            "error": error,
            "url": None,
        }

    try:
        url = client.get_match_url_from_id(
            match_id
        )

        return {
            "ok": True,
            "error": None,
            "url": url,
        }

    except Exception as exc:

        return {
            "ok": False,
            "error": str(exc),
            "url": None,
        }


def get_match_player_ids(match_id_or_url):
    """
    Return SofaScore player ids for a match.
    """

    client, error = load_sofascore_client()

    if error:
        return {
            "ok": False,
            "error": error,
            "players": {},
        }

    try:
        players = client.get_match_player_ids(
            match_id_or_url
        )

        return {
            "ok": True,
            "error": None,
            "players": players,
        }

    except Exception as exc:

        return {
            "ok": False,
            "error": str(exc),
            "players": {},
        }


def get_team_names(match_id_or_url):
    """
    For tennis this may still return home/away participant names
    depending on SofaScore match structure.
    """

    client, error = load_sofascore_client()

    if error:
        return {
            "ok": False,
            "error": error,
            "home": None,
            "away": None,
        }

    try:
        home, away = client.get_team_names(
            match_id_or_url
        )

        return {
            "ok": True,
            "error": None,
            "home": home,
            "away": away,
        }

    except Exception as exc:

        return {
            "ok": False,
            "error": str(exc),
            "home": None,
            "away": None,
        }


def sanity_check():
    """
    Lightweight diagnostic.
    Does not require a match id.
    Does not fail deploy.
    """

    client, error = load_sofascore_client()

    debug = {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "provider": "SofaScore via ScraperFC",

        "installed": client is not None,

        "error": error,

        "purpose": [
            "results verification",
            "match id lookup",
            "player id mapping",
            "future name matching support",
        ],

        "used_for_odds": False,
    }

    write_debug(debug)

    return debug


if __name__ == "__main__":
    data = sanity_check()

    print(
        json.dumps(
            data,
            indent=2,
            ensure_ascii=False,
        )
    )
