import pandas as pd


BASE = "https://raw.githubusercontent.com/JeffSackmann/tennis_MatchChartingProject/master/"


def load_mcp_matches():
    url = BASE + "charting-m-matches.csv"
    df = pd.read_csv(url)
    return df


def load_mcp_overview():
    url = BASE + "charting-m-stats-Overview.csv"
    df = pd.read_csv(url)
    return df


def load_mcp_rally():
    url = BASE + "charting-m-stats-Rally.csv"
    df = pd.read_csv(url)
    return df


def load_mcp_serve():
    url = BASE + "charting-m-stats-ServeBasics.csv"
    df = pd.read_csv(url)
    return df
