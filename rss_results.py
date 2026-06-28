import os
import json
import datetime
import html
import requests
from datetime import timezone, timedelta

BASE = "https://backstagetalks.github.io/tennis-backstage-talks/"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json,text/html,*/*",
}

LOCAL_TZ_OFFSET_HOURS = int(os.getenv("LOCAL_TZ_OFFSET_HOURS", "2"))
LOCAL_TZ = timezone(timedelta(hours=LOCAL_TZ_OFFSET_HOURS))


def esc(value):
    return html.escape(str(value if value is not None else ""))


def pct(value):
    try:
        return round(float(value) * 100, 1)
    except Exception:
        return 0


def signed_units(value):
    try:
        number = round(float(value), 2)
    except Exception:
        number = 0.0

    if number > 0:
        return f"+{number:.2f}u"

    if number < 0:
        return f"{number:.2f}u"

    return "0.00u"


def format_match_time(value):
    if not value:
        return ""

    try:
        dt = datetime.datetime.fromisoformat(str(value))
        return dt.strftime("%d.%m.%Y %H:%M CET")
    except Exception:
        return str(value)


def date_range_last_days(days):
    today = datetime.datetime.now(LOCAL_TZ).date()

    return [
        today - datetime.timedelta(days=i)
        for i in range(0, days)
    ]


def current_month_dates():
    today = datetime.datetime.now(LOCAL_TZ).date()
    first = today.replace(day=1)

    dates = []
    current = today

    while current >= first:
        dates.append(current)
        current -= datetime.timedelta(days=1)

    return dates


def load_local_results():
    os.makedirs("public", exist_ok=True)

    files = [
        f for f in os.listdir("public")
        if f.startswith("results_") and f.endswith(".json")
    ]

    print("LOCAL RESULT files found:", files)

    payloads = []

    for file_name in sorted(files):
        path = os.path.join("public", file_name)

        try:
            with open(path, "r", encoding="utf-8") as f:
                payloads.append(json.load(f))
