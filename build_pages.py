import glob
import json
import os

from render_site import (
    write_page,
    write_rss,
)


BASE_URL = "https://backstagetalks.github.io/tennis-backstage-talks"


def load_json(path, default):
    try:
        if not path:
            return default

        if not os.path.exists(path):
            return default

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    except Exception as exc:
        print(
            "BUILD PAGES JSON LOAD ERROR:",
            path,
            str(exc),
        )

        return default


def latest_file(pattern):
    files = glob.glob(pattern)

    if not files:
        return None

    files.sort(
        key=os.path.getmtime,
        reverse=True,
    )

    return files[0]


def ensure_public_dirs():
    os.makedirs(
        "public",
        exist_ok=True,
    )

    os.makedirs(
        "public/all",
        exist_ok=True,
    )


def build_pages():
    ensure_public_dirs()

    top_json = latest_file(
        "public/predictions_*.json",
    )

    all_json = latest_file(
        "public/all_predictions_*.json",
    )

    print(
        "BUILD PAGES TOP JSON:",
        top_json,
    )

    print(
        "BUILD PAGES ALL JSON:",
        all_json,
    )

    top_predictions = load_json(
        top_json,
        [],
    )

    all_predictions = load_json(
        all_json,
        [],
    )

    write_page(
        predictions=top_predictions,
        title="TBT Tennis Intelligence",
        subtitle="Top tennis picks",
        destination="public/index.html",
    )

    write_rss(
        predictions=top_predictions,
        title="TBT Tennis Intelligence",
        link=f"{BASE_URL}/",
        destination="public/tennis.xml",
    )

    write_page(
        predictions=all_predictions,
        title="TBT Tennis Intelligence - ALL",
        subtitle="All available tennis predictions",
        destination="public/all/index.html",
    )

    write_rss(
        predictions=all_predictions,
        title="TBT Tennis Intelligence - ALL",
        link=f"{BASE_URL}/all/",
        destination="public/tennis_all.xml",
    )

    print(
        "BUILD PAGES WRITTEN:",
        "public/index.html",
        "public/tennis.xml",
        "public/all/index.html",
        "public/tennis_all.xml",
    )


if __name__ == "__main__":
    build_pages()
