import json
import os
import glob

from render_site import (
    write_page,
    write_rss,
    BASE_URL,
)


def latest_file(pattern):
    files = glob.glob(pattern)

    if not files:
        return None

    files.sort(
        key=os.path.getmtime,
        reverse=True,
    )

    return files[0]


def load_predictions(path):
    if not path:
        return []

    if not os.path.exists(path):
        return []

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def main():
    path = latest_file(
        "public/all_predictions_*.json"
    )

    predictions = load_predictions(path)

    write_page(
        predictions=predictions,
        title="TBT ALL Picks",
        subtitle="All tennis matches analysed by TBT AI",
        destination="public/all/index.html",
    )

    write_rss(
        predictions=predictions,
        title="TBT ALL Picks RSS",
        link=f"{BASE_URL}/all/",
        destination="public/tennis_all.xml",
    )

    print(
        "Generated ALL page:",
        "public/all/index.html",
        "items:",
        len(predictions),
    )

    print(
        "Generated ALL RSS:",
        "public/tennis_all.xml",
    )


if __name__ == "__main__":
    main()
