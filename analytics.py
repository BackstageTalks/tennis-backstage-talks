from datetime import datetime, timedelta
from history_tracker import load_history


def is_last_7_days(date_str):
    d = datetime.strptime(date_str, "%Y-%m-%d")
    return d >= datetime.utcnow() - timedelta(days=7)


def is_this_month(date_str):
    d = datetime.strptime(date_str, "%Y-%m-%d")
    now = datetime.utcnow()
    return d.year == now.year and d.month == now.month


def is_last_month(date_str):
    d = datetime.strptime(date_str, "%Y-%m-%d")
    now = datetime.utcnow()

    last_month = now.month - 1 or 12
    year = now.year if now.month != 1 else now.year - 1

    return d.year == year and d.month == last_month


def calc_stats(records):
    total = len(records)

    if total == 0:
        return {
            "bets": 0,
            "wins": 0,
            "roi": 0
        }

    wins = 0
    profit = 0

    for r in records:
        if r["result"] == "win":
            wins += 1
            if r["odds"]:
                profit += (r["odds"] - 1)

        elif r["result"] == "loss":
            profit -= 1

    roi = round(profit / total, 3)

    return {
        "bets": total,
        "wins": wins,
        "roi": roi
    }


def build_stats():
    data = load_history()

    return {
        "all": calc_stats(data),

        "last_7_days": calc_stats([
            r for r in data if is_last_7_days(r["date"])
        ]),

        "this_month": calc_stats([
            r for r in data if is_this_month(r["date"])
        ]),

        "last_month": calc_stats([
            r for r in data if is_last_month(r["date"])
        ])
    }
