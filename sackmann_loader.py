import csv
import re
from io import StringIO
from datetime import datetime
import requests


GITHUB_SOURCES = [
    {
        "label": "ATP_MAIN",
        "url": "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_{}.csv",
    },
    {
        "label": "ATP_QUAL_CHALL",
        "url": "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_qual_chall_{}.csv",
    },
    {
        "label": "WTA_MAIN",
        "url": "https://raw.githubusercontent.com/JeffSackmann/tennis_wta/master/wta_matches_{}.csv",
    },
]

TML_FILES_API = "https://stats.tennismylife.org/api/data-files"


def get_text(url, timeout=30):
    try:
        response = requests.get(url, timeout=timeout)
        if response.status_code != 200:
            return None
        return response.text
    except Exception as e:
        print("GET TEXT ERROR:", url, e)
        return None


def fetch_csv_rows(url):
    text = get_text(url)

    if not text:
        return []

    if "," not in text:
        return []

    try:
        return list(csv.DictReader(StringIO(text)))
    except Exception as e:
        print("CSV READ ERROR:", url, e)
        return []


def normalize_col_name(name):
    if name is None:
        return ""

    value = str(name).strip().lower()
    value = re.sub(r"[^a-z0-9]+", "_", value)
    value = re.sub(r"_+", "_", value)
    return value.strip("_")


def build_column_map(row):
    column_map = {}

    for key in row.keys():
