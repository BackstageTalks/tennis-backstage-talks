import pandas as pd

# ---------------------------
# CONFIG
# ---------------------------
BASE = "https://raw.githubusercontent.com/JeffSackmann/tennis_MatchChartingProject/master/"


# ---------------------------
# LOAD MCP DATA (LIVE)
# ---------------------------
def load_mcp_overview():
    url = BASE + "charting-m-stats-Overview.csv"
    try:
        df = pd.read_csv(url)
        return df
    except Exception:
        return pd.DataFrame()


# ---------------------------
# NAME NORMALIZATION
# ---------------------------
def normalize(name):
    if not name:
        return ""
    return str(name).lower().replace("-", " ").strip()


# ---------------------------
# BUILD PLAYER STATS
# ---------------------------
def build_mcp_player_stats():
    df = load_mcp_overview()

    stats = {}

    if df.empty:
        return stats

    for _, row in df.iterrows():
        try:
            p1 = normalize(row.get("player1"))
            p2 = normalize(row.get("player2"))

            if not p1 or not p2:
                continue

            if p1 not in stats:
                stats[p1] = {"matches": 0, "wins": 0}

            if p2 not in stats:
                stats[p2] = {"matches": 0, "wins": 0}

            stats[p1]["matches"] += 1
            stats[p2]["matches"] += 1

            winner = normalize(row.get("winner"))

            if winner == p1:
                stats[p1]["wins"] += 1
            elif winner == p2:
                stats[p2]["wins"] += 1

        except Exception:
            continue

    for p in stats:
        m = stats[p]["matches"]
        w = stats[p]["wins"]
        stats[p]["win_rate"] = (w / m) if m > 0 else 0

    return stats


# ---------------------------
# MCP ADJUSTMENT
# ---------------------------
def mcp_adjustment(player_name, mcp_stats):
    p = normalize(player_name)
    data = mcp_stats.get(p)

    if not data:
        return 0.0

    matches = data.get("matches", 0)
    win_rate = data.get("win_rate", 0)

    adj = 0.0

    # experience
    if matches > 30:
        adj += 0.02
    elif matches < 5:
        adj -= 0.02

    # performance
    if win_rate > 0.65:
        adj += 0.02
    elif win_rate < 0.45:
        adj -= 0.02

    return adj
