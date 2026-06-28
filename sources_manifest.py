import datetime


PROJECT_SOURCE_VERSION = "source-map-v1"


def current_year():
    return datetime.date.today().year


def candidate_years(lookback_years=3, include_next_year=False):
    """
    Dynamic year selection.

    Example in 2026 with lookback_years=3:
    [2023, 2024, 2025, 2026]

    If include_next_year=True:
    [2023, 2024, 2025, 2026, 2027]

    Important:
    - no hardcoded fixed year lists
    - future years are handled automatically
    - missing optional files should be skipped by loaders
    """
    year = current_year()
    end_year = year + 1 if include_next_year else year

    return list(range(year - lookback_years, end_year + 1))


SOURCES_MANIFEST = {
    "version": PROJECT_SOURCE_VERSION,

    "time_window": {
        "label": "CET",
        "start_hour": 6,
        "end_next_day_hour": 6,
        "description": "Daily tennis window: 06:00 CET current day to 06:00 CET next day."
    },

    "fixtures": {
        "primary": {
            "name": "SportScore",
            "type": "web",
            "url": "https://sportscore.com/tennis/",
            "coverage": [
                "scheduled fixtures",
                "live matches",
                "finished results",
                "match times",
                "current odds when available"
            ],
            "used_for": [
                "daily match list",
                "match start time",
                "current odds",
                "basic tournament text"
            ],
            "status": "active"
        },
        "wimbledon_fallback": {
            "name": "Wimbledon Official",
            "type": "web",
            "url": "https://www.wimbledon.com/en_GB/the_championships/schedule",
            "coverage": [
                "Wimbledon schedule",
                "Order of Play",
                "court information",
                "event schedule"
            ],
            "used_for": [
                "Wimbledon enrichment",
                "surface override: Grass",
                "Grand Slam category",
                "official schedule validation"
            ],
            "status": "planned"
        },
        "wimbledon_secondary": {
            "name": "LTA Wimbledon Preview",
            "type": "web",
            "url": "https://www.lta.org.uk/fan-zone/grand-slam/wimbledon-championships/news/",
            "coverage": [
                "Wimbledon draw overview",
                "men and women matchups",
                "player list",
                "schedule references"
            ],
            "used_for": [
                "Wimbledon draw context",
                "men/women split",
                "seed/wildcard/qualifier context"
            ],
            "status": "planned"
        }
    },

    "men_stats": {
        "atp_main": {
            "name": "TennisMyLife ATP Tour",
            "type": "csv",
            "coverage": [
                "ATP Tour historical matches",
                "ATP ongoing tournaments",
                "surface",
                "score",
                "serve stats where available",
                "tournament date"
            ],
            "used_for": [
                "ATP recent form",
                "ATP surface form",
                "ATP ace profile",
                "ATP set profile"
            ],
            "dynamic_years": True,
            "status": "active"
        },
        "atp_challenger": {
            "name": "TennisMyLife ATP Challenger",
            "type": "csv",
            "coverage": [
                "ATP Challenger historical matches",
                "ATP Challenger ongoing tournaments",
                "surface",
                "score",
                "serve stats where available"
            ],
            "used_for": [
                "Challenger recent form",
                "Challenger surface form",
                "Challenger ace profile",
                "Challenger set profile"
            ],
            "dynamic_years": True,
            "status": "active"
        },
        "atp_qualifying": {
            "name": "TennisMyLife ATP Qualifying",
            "type": "csv",
            "coverage": [
                "ATP Tour qualifying matches",
                "recent seasons"
            ],
            "used_for": [
                "ATP qualifying player context",
                "qualifier form",
                "qualification-level category"
            ],
            "dynamic_years": True,
            "status": "planned"
        },
        "jeff_sackmann_atp": {
            "name": "Jeff Sackmann ATP",
            "type": "csv",
            "coverage": [
                "ATP match results",
                "ATP rankings",
                "ATP players table"
            ],
            "used_for": [
                "ATP backup stats",
                "ranking context",
                "player name mapping",
                "historical enrichment"
            ],
            "dynamic_years": True,
            "status": "planned"
        },
        "grand_slam_men": {
            "name": "Jeff Sackmann Grand Slam point-by-point",
            "type": "csv",
            "coverage": [
                "Australian Open",
                "Roland Garros",
                "Wimbledon",
                "US Open",
                "point-by-point logs"
            ],
            "used_for": [
                "Grand Slam enrichment",
                "Wimbledon support",
                "serve/return profile where useful"
            ],
            "dynamic_years": True,
            "status": "planned"
        }
    },

    "women_stats": {
        "jeff_sackmann_wta": {
            "name": "Jeff Sackmann WTA",
            "type": "csv",
            "coverage": [
                "WTA match results",
                "WTA rankings",
                "WTA players table"
            ],
            "used_for": [
                "WTA recent form",
                "WTA surface form",
                "WTA ranking context",
                "WTA player name mapping"
            ],
            "dynamic_years": True,
            "status": "planned"
        },
        "grand_slam_women": {
            "name": "Jeff Sackmann Grand Slam point-by-point",
            "type": "csv",
            "coverage": [
                "Australian Open women",
                "Roland Garros women",
                "Wimbledon women",
                "US Open women"
            ],
            "used_for": [
                "Grand Slam Women enrichment",
                "Wimbledon Women support",
                "serve/return profile where useful"
            ],
            "dynamic_years": True,
            "status": "planned"
        }
    },

    "odds": {
        "current": {
            "name": "SportScore",
            "type": "web",
            "coverage": [
                "current match winner odds when available"
            ],
            "used_for": [
                "odds_player1",
                "odds_player2",
                "pick odds",
                "market probability",
                "value edge"
            ],
            "status": "active"
        },
        "historical_free": {
            "name": "tennis-data.co.uk",
            "type": "csv/xlsx",
            "coverage": [
                "ATP match results and betting odds",
                "WTA match results and betting odds"
            ],
            "used_for": [
                "historical market calibration",
                "ATP/WTA odds history",
                "model-vs-market backtesting"
            ],
            "dynamic_years": True,
            "status": "planned"
        },
        "future_paid": {
            "name": "The Odds API",
            "type": "api",
            "coverage": [
                "Grand Slams",
                "ATP 1000",
                "ATP 500",
                "WTA 1000",
                "WTA 500",
                "current odds",
                "selected historical odds"
            ],
            "used_for": [
                "multi-bookmaker current odds",
                "future paid odds enrichment",
                "Wimbledon ATP/WTA odds"
            ],
            "status": "future_paid_optional"
        }
    },

    "categories": {
        "tour_group": [
            "MEN",
            "WOMEN",
            "UNKNOWN"
        ],
        "category": [
            "ATP",
            "ATP Challenger",
            "ATP Qualifying",
            "Grand Slam Men",
            "WTA",
            "Grand Slam Women",
            "Unknown"
        ],
        "data_status": [
            "FULL",
            "PARTIAL",
            "FALLBACK",
            "NO_STATS",
            "NO_ODDS",
            "UNKNOWN"
        ]
    },

    "output_channels": {
        "top7": {
            "page": "/",
            "rss": "/tennis.xml",
            "max_items": 7,
            "description": "Main TOP 7 model picks."
        },
        "all": {
            "page": "/all/",
            "rss": "/tennis_all.xml",
            "max_items": None,
            "description": "All available model picks."
        },
        "wtop7": {
            "page": "/wtop7/",
            "rss": "/wtop7.xml",
            "max_items": 7,
            "description": "Women TOP 7 model picks.",
            "status": "planned"
        },
        "wall": {
            "page": "/wall/",
            "rss": "/wall.xml",
            "max_items": None,
            "description": "All women model picks.",
            "status": "planned"
        }
    }
}


def source_summary():
    return {
        "version": PROJECT_SOURCE_VERSION,
        "current_year": current_year(),
        "candidate_years": candidate_years(),
        "candidate_years_with_next": candidate_years(include_next_year=True),
        "manifest": SOURCES_MANIFEST,
    }


def default_match_metadata(
    tour_group="UNKNOWN",
    category="Unknown",
    source_fixtures="SportScore",
    source_stats=None,
    source_odds="SportScore",
    data_status="UNKNOWN",
):
    """
    Metadata fields to attach to each prediction later.
    These should stay internal and do not need to be shown on the public pages.
    """
    return {
        "tour_group": tour_group,
        "category": category,
        "source_fixtures": source_fixtures,
        "source_stats": source_stats,
        "source_odds": source_odds,
        "data_status": data_status,
        "source_manifest_version": PROJECT_SOURCE_VERSION,
    }
