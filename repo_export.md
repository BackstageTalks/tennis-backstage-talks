# Repository Export For Audit

Repository: BackstageTalks/tennis-backstage-talks
Branch: main
Commit: a1d1350fd20ebaf544c2661e43a88e20fde6cc4b
Generated at UTC: 2026-07-08T12:21:28Z

Excluded directories: .git, data, public, __pycache__, .venv, node_modules



## FILE: .github/workflows/daily-tennis-predictions.yml

```
name: Daily Tennis Predictions

on:
  schedule:
    - cron: '45 7 * * *'
  workflow_dispatch:

permissions:
  contents: write
  pages: write
  id-token: ***REDACTED***

concurrency:
  group: daily-tennis-predictions
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest

    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

      - name: Syntax check project files
        run: |
          python -m py_compile tennisapi_client.py
          python -m py_compile tennisapi_cache.py
          python -m py_compile fetch_matches.py
          python -m py_compile results_fetcher.py
          python -m py_compile results_checker.py
          python -m py_compile odds_api.py
          python -m py_compile prediction_engine_core.py
          python -m py_compile prediction_engine_top.py
          python -m py_compile update.py
          python -m py_compile build_pages.py
          python -m py_compile render_site.py
          python -m py_compile random_paths.py
          if [ -f fix_navigation.py ]; then python -m py_compile fix_navigation.py; fi

      - name: Prepare directories
        run: |
          mkdir -p public
          mkdir -p public/results
          mkdir -p public/BsT
          mkdir -p public/Blend
          mkdir -p data
          mkdir -p data/pick_history/all
          mkdir -p data/pick_history/top5
          mkdir -p data/results
          mkdir -p data/marq_ai
          mkdir -p data/tennisapi_cache

      - name: Warm TennisApi cache
        env:
          ODDS_API_KEY: ***REDACTED*** secrets.ODDS_API_KEY }}
          RAPIDAPI_KEY: ***REDACTED*** secrets.RAPIDAPI_KEY }}
          TENNISAPI_RAPIDAPI_KEY: ***REDACTED*** secrets.RAPIDAPI_KEY }}
          SGOAPI: ${{ secrets.SGOAPI }}
          TENNISAPI_CATEGORY_IDS: "3,6,871"
          TENNISAPI_PROVIDER_ID: "1"
          RESULTS_LOOKBACK_DAYS: "90"
          ODDS_SCAN_DAYS_AHEAD: "1"
          ODDS_SCAN_DAYS_BACK: "0"
        run: |
          python tennisapi_cache.py

      - name: Run predictions
        env:
          ODDS_API_KEY: ***REDACTED*** secrets.ODDS_API_KEY }}
          RAPIDAPI_KEY: ***REDACTED*** secrets.RAPIDAPI_KEY }}
          TENNISAPI_RAPIDAPI_KEY: ***REDACTED*** secrets.RAPIDAPI_KEY }}
          SGOAPI: ${{ secrets.SGOAPI }}
          TENNISAPI_CATEGORY_IDS: "3,6,871"
          TENNISAPI_PROVIDER_ID: "1"
          RESULTS_LOOKBACK_DAYS: "90"
          ODDS_SCAN_DAYS_AHEAD: "1"
          ODDS_SCAN_DAYS_BACK: "0"
        run: |
          python update.py

      - name: Build Corq, Thinq, Blend and ALL pages
        env:
          ODDS_API_KEY: ***REDACTED*** secrets.ODDS_API_KEY }}
          RAPIDAPI_KEY: ***REDACTED*** secrets.RAPIDAPI_KEY }}
          TENNISAPI_RAPIDAPI_KEY: ***REDACTED*** secrets.RAPIDAPI_KEY }}
          SGOAPI: ${{ secrets.SGOAPI }}
          TENNISAPI_CATEGORY_IDS: "3,6,871"
          TENNISAPI_PROVIDER_ID: "1"
          RESULTS_LOOKBACK_DAYS: "90"
          ODDS_SCAN_DAYS_AHEAD: "1"
          ODDS_SCAN_DAYS_BACK: "0"
        run: |
          python build_pages.py

      - name: Run results checker
        env:
          ODDS_API_KEY: ***REDACTED*** secrets.ODDS_API_KEY }}
          RAPIDAPI_KEY: ***REDACTED*** secrets.RAPIDAPI_KEY }}
          TENNISAPI_RAPIDAPI_KEY: ***REDACTED*** secrets.RAPIDAPI_KEY }}
          SGOAPI: ${{ secrets.SGOAPI }}
          TENNISAPI_CATEGORY_IDS: "3,6,871"
          TENNISAPI_PROVIDER_ID: "1"
          RESULTS_LOOKBACK_DAYS: "90"
          ODDS_SCAN_DAYS_AHEAD: "1"
          ODDS_SCAN_DAYS_BACK: "0"
        run: |
          python results_checker.py

      - name: Build results page
        env:
          ODDS_API_KEY: ***REDACTED*** secrets.ODDS_API_KEY }}
          RAPIDAPI_KEY: ***REDACTED*** secrets.RAPIDAPI_KEY }}
          TENNISAPI_RAPIDAPI_KEY: ***REDACTED*** secrets.RAPIDAPI_KEY }}
          SGOAPI: ${{ secrets.SGOAPI }}
          TENNISAPI_CATEGORY_IDS: "3,6,871"
          TENNISAPI_PROVIDER_ID: "1"
          RESULTS_LOOKBACK_DAYS: "90"
          ODDS_SCAN_DAYS_AHEAD: "1"
          ODDS_SCAN_DAYS_BACK: "0"
        run: |
          python rss_results.py

      - name: Ensure results page exists
        run: |
          if [ ! -f public/results/index.html ]; then
            printf '%s\n' '<!doctype html>' '<html>' '<head>' '<meta charset="utf-8">' '<title>Results</title>' '</head>' '<body>' '<h1>Results</h1>' '<p>No results available yet.</p>' '</body>' '</html>' > public/results/index.html
          fi

      - name: Apply random public paths
        run: |
          python random_paths.py

      - name: Verify random public files
        run: |
          echo "=== VERIFY RANDOM PUBLIC FILES ==="
          test -f public/index.html
          test -f public/h4v34n1c3d4y180/index.html
          test -f public/h4v34n1c3d4y181/index.html
          test -f public/h4v34n1c3d4y182/index.html
          test -f public/h4v34n1c3d4y183/index.html
          test -f public/h4v34n1c3d4y184/index.html
          test -f public/h4v34n1c3d4y185.xml
          test -f public/h4v34n1c3d4y186.xml
          test -f public/h4v34n1c3d4y187.xml
          echo "All required random public files exist."

      - name: Commit generated data and public files
        run: |
          git config user.name "github-actions"
          git config user.email "github-actions@github.com"

          echo "=== GIT STATUS BEFORE ADD ==="
          git status --short

          git add -A public data || true

          echo "=== GIT STATUS AFTER ADD ==="
          git status --short

          if git diff --cached --quiet; then
            echo "No generated changes to commit."
            exit 0
          fi

          git commit -m "Update tennis predictions data"

          echo "=== REBASE WITH AUTOSTASH ==="
          git pull --rebase --autostash

          echo "=== PUSH ==="
          git push

      - name: Setup Pages
        uses: actions/configure-pages@v5

      - name: Upload Pages artifact
        uses: actions/upload-pages-artifact@v3
        with:
          path: public

      - name: Deploy GitHub Pages
        id: deployment
        uses: actions/deploy-pages@v4
```


## FILE: .github/workflows/export-repo-for-audit.yml

```
name: Export Repository For Audit

on:
  workflow_dispatch:
    inputs:
      commit_to_repo:
        description: "Commit repo_export.md back to repository"
        required: true
        default: "true"
        type: choice
        options:
          - "true"
          - "false"

permissions:
  contents: write

jobs:
  export-repo:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Generate repo_export.md
        shell: bash
        run: |
          set -e

          OUTPUT="repo_export.md"
          rm -f "$OUTPUT"

          echo "# Repository Export For Audit" >> "$OUTPUT"
          echo "" >> "$OUTPUT"
          echo "Repository: $GITHUB_REPOSITORY" >> "$OUTPUT"
          echo "Branch: ${GITHUB_REF_NAME}" >> "$OUTPUT"
          echo "Commit: ${GITHUB_SHA}" >> "$OUTPUT"
          echo "Generated at UTC: $(date -u +"%Y-%m-%dT%H:%M:%SZ")" >> "$OUTPUT"
          echo "" >> "$OUTPUT"
          echo "Excluded directories: .git, data, public, __pycache__, .venv, node_modules" >> "$OUTPUT"
          echo "" >> "$OUTPUT"

          find . -type f \
            ! -path "./.git/*" \
            ! -path "./data/*" \
            ! -path "./public/*" \
            ! -path "./__pycache__/*" \
            ! -path "./.venv/*" \
            ! -path "./venv/*" \
            ! -path "./node_modules/*" \
            ! -path "./repo_export.md" \
            ! -name "*.pyc" \
            ! -name "*.pyo" \
            ! -name "*.log" \
            ! -name "*.sqlite" \
            ! -name "*.db" \
            \( \
              -name "*.py" -o \
              -name "*.yml" -o \
              -name "*.yaml" -o \
              -name "*.md" -o \
              -name "*.txt" -o \
              -name "*.json" -o \
              -name "*.toml" -o \
              -name "*.ini" \
            \) | sort > files_to_export.txt

          while IFS= read -r file; do
            echo "" >> "$OUTPUT"
            echo "" >> "$OUTPUT"
            echo "## FILE: ${file#./}" >> "$OUTPUT"
            echo "" >> "$OUTPUT"
            echo '```' >> "$OUTPUT"

            # Basic secret redaction for safety
            sed -E \
              -e 's/(RAPIDAPI_KEY[[:space:]]*[:=][[:space:]]*)[^[:space:]]+/\1***REDACTED***/Ig' \
              -e 's/(TELEGRAM_BOT_TOKEN[[:space:]]*[:=][[:space:]]*)[^[:space:]]+/\1***REDACTED***/Ig' \
              -e 's/(TELEGRAM_CHAT_ID[[:space:]]*[:=][[:space:]]*)[^[:space:]]+/\1***REDACTED***/Ig' \
              -e 's/(API_KEY[[:space:]]*[:=][[:space:]]*)[^[:space:]]+/\1***REDACTED***/Ig' \
              -e 's/(TOKEN[[:space:]]*[:=][[:space:]]*)[^[:space:]]+/\1***REDACTED***/Ig' \
              -e 's/(PASSWORD[[:space:]]*[:=][[:space:]]*)[^[:space:]]+/\1***REDACTED***/Ig' \
              "$file" >> "$OUTPUT" || true

            echo '```' >> "$OUTPUT"
          done < files_to_export.txt

          echo "Generated export:"
          ls -lh "$OUTPUT"

      - name: Upload repo export artifact
        uses: actions/upload-artifact@v4
        with:
          name: repo_export
          path: repo_export.md
          retention-days: 7

      - name: Commit repo_export.md to repository
        if: ${{ github.event.inputs.commit_to_repo == 'true' }}
        shell: bash
        run: |
          set -e

          git config user.name "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"

          git add repo_export.md

          if git diff --cached --quiet; then
            echo "No changes to commit."
          else
            git commit -m "Add repository export for audit"
            git push
          fi
```


## FILE: .github/workflows/telegram-rss-feed.yml

```
name: Telegram RSS Feed

on:
  # Optional automatic send after daily deploy should usually be finished.
  # GitHub cron is UTC. 08:55 UTC = 10:55 SK/CZ during summer time.
  schedule:
    - cron: '55 8 * * *'
  workflow_dispatch:
    inputs:
      feed:
        description: 'Feed to send: all, corq, thinq, blenq'
        required: false
        default: 'all'
        type: choice
        options:
          - all
          - corq
          - thinq
          - blenq
      limit:
        description: 'How many picks per feed'
        required: false
        default: '5'

permissions:
  contents: read

concurrency:
  group: telegram-rss-feed
  cancel-in-progress: false

jobs:
  send-telegram-feed:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install feed dependencies
        run: |
          python -m pip install --upgrade pip
          pip install feedparser requests

      - name: Syntax check Telegram feed script
        run: |
          python -m py_compile telegram_rss_feed.py

      - name: Send Telegram RSS feed
        env:
          TG_BOT_BTLKR: ${{ secrets.TG_BOT_BTLKR }}
          TG_CHAT_ID: ${{ secrets.TG_CHAT_ID }}
          TG_FEED: ${{ github.event.inputs.feed || 'all' }}
          TG_FEED_LIMIT: ${{ github.event.inputs.limit || '5' }}
        run: |
          python telegram_rss_feed.py
```


## FILE: .github/workflows/weekly-elo-html-download.yml

```
name: Weekly ELO HTML Download

on:
  schedule:
    # Tuesday around 03:00 SK/CZ during summer time.
    # GitHub Actions cron is UTC, so 01:00 UTC = 03:00 CEST.
    - cron: '0 1 * * 2'
  workflow_dispatch:

permissions:
  contents: write

concurrency:
  group: weekly-elo-html-download
  cancel-in-progress: false

jobs:
  download-elo-html:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"

      - name: Syntax check downloader
        run: |
          python -m py_compile elo_html_downloader.py

      - name: Download ELO HTML pages
        run: |
          python elo_html_downloader.py

      - name: Commit downloaded ELO HTML files
        run: |
          git config user.name "github-actions"
          git config user.email "github-actions@github.com"

          echo "=== GIT STATUS BEFORE ADD ==="
          git status --short

          git add -A data/elo/raw data/elo/raw_history data/elo/meta || true

          echo "=== GIT STATUS AFTER ADD ==="
          git status --short

          if git diff --cached --quiet; then
            echo "No ELO HTML changes to commit."
            exit 0
          fi

          git commit -m "Update weekly ELO HTML cache"

          echo "=== REBASE WITH AUTOSTASH ==="
          git pull --rebase --autostash

          echo "=== PUSH ==="
          git push
```


## FILE: all.py

```
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
```


## FILE: analytics.py

```
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
```


## FILE: bst_ai_refresher.py

```
import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.bst_ai.service import build_bst_ai_comparison

PUBLIC_DIR = Path("public")
PICK_HISTORY_DIRS = [Path("data/pick_history/all"), Path("data/pick_history/top5")]

BST_KEYS = [
    "corq_ai_probability",
    "bst_ai_probability",
    "ai_match",
    "ai_gap",
    "ai_signed_gap",
    "ai_lean",
    "ai_direction_match",
    "ai_match_color",
    "bst_ai_status",
    "bst_ai_reason",
    "bst_ai_rating_type",
    "bst_player1_found",
    "bst_player2_found",
]


def load_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print("BST REFRESH LOAD ERROR:", path, exc)
        return default


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_status(value: Any) -> str:
    return str(value or "").upper().strip()


def is_bst_ok(item: Dict[str, Any]) -> bool:
    return normalize_status(item.get("bst_ai_status")) == "OK"


def strip_accents(value: Any) -> str:
    text = str(value or "")
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def cleanup_name(value: Any) -> str:
    text = strip_accents(value)
    text = text.replace(".", " ").replace("-", " ").replace("_", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def reversed_name(value: Any) -> str:
    text = cleanup_name(value)
    parts = text.split()
    if len(parts) < 2:
        return text
    return " ".join(parts[::-1])


def infer_tour(item: Dict[str, Any]) -> Optional[str]:
    fields = " ".join(str(item.get(k) or "") for k in ["gender", "category", "tournament", "match"])
    lower = fields.lower()
    if "wta" in lower or "women" in lower or "woman" in lower:
        return "WTA"
    if "atp" in lower or "challenger" in lower or "men" in lower or "man" in lower:
        return "ATP"
    return item.get("gender") or None


def candidate_name_pairs(item: Dict[str, Any]) -> List[Tuple[str, str]]:
    p1 = item.get("player1")
    p2 = item.get("player2")
    match = str(item.get("match") or "")
    if (not p1 or not p2) and " vs " in match:
        left, right = match.split(" vs ", 1)
        p1 = p1 or left.strip()
        p2 = p2 or right.strip()

    pairs = []
    if p1 and p2:
        base = (str(p1), str(p2))
        pairs.append(base)
        pairs.append((cleanup_name(p1), cleanup_name(p2)))
        pairs.append((reversed_name(p1), reversed_name(p2)))
        # Reverse event order as a last attempt; pick remains unchanged.
        pairs.append((str(p2), str(p1)))
        pairs.append((cleanup_name(p2), cleanup_name(p1)))

    # Deduplicate while preserving order.
    seen = set()
    out = []
    for a, b in pairs:
        key = (a.lower(), b.lower())
        if not a or not b or key in seen:
            continue
        seen.add(key)
        out.append((a, b))
    return out


def candidate_tours(item: Dict[str, Any]) -> List[Optional[str]]:
    inferred = infer_tour(item)
    tours = [inferred, item.get("gender"), "WTA", "ATP", None]
    out = []
    seen = set()
    for t in tours:
        key = str(t or "NONE")
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out


def try_refresh_item(item: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    if is_bst_ok(item):
        return item, False

    pick = item.get("pick")
    surface = item.get("surface") or "Hard"
    corq_probability = item.get("corq_ai_probability") or item.get("probability")

    if not pick or corq_probability is None:
        return item, False

    for player1, player2 in candidate_name_pairs(item):
        for tour in candidate_tours(item):
            try:
                result = build_bst_ai_comparison(
                    player1=player1,
                    player2=player2,
                    pick=pick,
                    surface=surface,
                    corq_probability=corq_probability,
                    tour=tour,
                )
            except Exception as exc:
                print("BST REFRESH TRY ERROR:", item.get("match"), player1, player2, tour, exc)
                continue

            if isinstance(result, dict) and normalize_status(result.get("bst_ai_status")) == "OK":
                updated = dict(item)
                for key in BST_KEYS:
                    if key in result:
                        updated[key] = result.get(key)
                updated["bst_ai_refreshed"] = True
                updated["bst_ai_refresh_player1"] = player1
                updated["bst_ai_refresh_player2"] = player2
                updated["bst_ai_refresh_tour"] = tour
                return updated, True

    return item, False


def refresh_list(items: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    refreshed = []
    hits = 0
    for item in items:
        if not isinstance(item, dict):
            refreshed.append(item)
            continue
        updated, changed = try_refresh_item(item)
        if changed:
            hits += 1
            print("BST REFRESH HIT:", updated.get("match"), "pick:", updated.get("pick"), "ai_match:", updated.get("ai_match"))
        refreshed.append(updated)
    return refreshed, hits


def refresh_file(path: Path) -> int:
    data = load_json(path, None)
    if data is None:
        return 0

    if isinstance(data, list):
        data, hits = refresh_list(data)
        save_json(path, data)
        return hits

    if isinstance(data, dict):
        total_hits = 0
        for key in ["items", "picks", "matches", "results"]:
            if isinstance(data.get(key), list):
                data[key], hits = refresh_list(data[key])
                total_hits += hits
        if total_hits:
            save_json(path, data)
        return total_hits

    return 0


def prediction_files() -> List[Path]:
    files = []
    files.extend(PUBLIC_DIR.glob("predictions_*.json"))
    files.extend(PUBLIC_DIR.glob("all_predictions_*.json"))
    for directory in PICK_HISTORY_DIRS:
        files.extend(directory.glob("*.json"))
    # newest first, only JSON files
    return sorted(set(files), key=lambda p: str(p), reverse=True)


def main() -> None:
    files = prediction_files()
    total = 0
    for path in files:
        hits = refresh_file(path)
        total += hits
        if hits:
            print("BST REFRESH FILE:", path, "hits:", hits)
    print("BST REFRESH TOTAL HITS:", total)


if __name__ == "__main__":
    main()
```


## FILE: build_elo.py

```
from datetime import datetime
from zoneinfo import ZoneInfo

from sackmann_loader import load_all_matches
from elo_engine import build_and_save
from form_engine import build_and_save_form


LOCAL_TZ = ZoneInfo("Europe/Bratislava")


def today_cutoff_yyyymmdd():
    return datetime.now(LOCAL_TZ).strftime("%Y%m%d")


def filter_matches_before_today(matches):
    cutoff = today_cutoff_yyyymmdd()

    filtered = []

    for match in matches:
        date = str(match.get("date") or "0")

        if date != "0" and date < cutoff:
            filtered.append(match)

    print("TODAY CUTOFF:", cutoff)
    print("MATCHES BEFORE TODAY:", len(filtered))

    return filtered


def run():
    print("LOADING MATCHES FOR ADVANCED ELO + FORM...")

    matches = load_all_matches(2018, 2030)

    if not matches:
        raise Exception("NO MATCHES LOADED FOR ELO")

    print("MATCHES LOADED:", len(matches))

    historical_matches = filter_matches_before_today(matches)

    if len(historical_matches) < 1000:
        raise Exception(
            f"TOO FEW HISTORICAL MATCHES LOADED: {len(historical_matches)}"
        )

    print("BUILDING ADVANCED ELO STORE...")
    elo_store = build_and_save(historical_matches)

    print("ELO STORE PLAYERS:", len(elo_store))

    if len(elo_store) < 200:
        raise Exception(f"TOO FEW ELO PLAYERS: {len(elo_store)}")

    print("BUILDING FORM STORE...")
    form_store = build_and_save_form(historical_matches)

    print("FORM STORE PLAYERS:", len(form_store))

    if len(form_store) < 200:
        raise Exception(f"TOO FEW FORM PLAYERS: {len(form_store)}")

    print("ADVANCED ELO + FORM BUILD DONE")


if __name__ == "__main__":
    run()
```


## FILE: build_pages.py

```
import copy
import glob
import json
import os
import re
from datetime import datetime, timezone

from render_site import (
    write_page,
    write_rss,
)


BASE_URL = "https://backstagetalks.github.io/tennis-backstage-talks"
SITE_TITLE = "BackstageTalks Statistic Model"

CORQ_MIN_WIN = 0.55
THINQ_MIN_WIN = 0.55
BLEND_MIN_WIN = 0.55
MIN_PAGE_ODDS = 1.33


# -----------------------------------------------------------------------------
# JSON / file helpers
# -----------------------------------------------------------------------------


def extract_date_from_filename(path):
    filename = os.path.basename(path or "")
    match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)

    if not match:
        return ""

    return match.group(1)


def sorted_files_newest_first(pattern):
    files = glob.glob(pattern)
    files.sort(
        key=lambda path: (
            extract_date_from_filename(path),
            os.path.getmtime(path),
        ),
        reverse=True,
    )
    return files


def load_json(path, default):
    try:
        if not path:
            return default

        if not os.path.exists(path):
            return default

        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    except Exception as exc:
        print("BUILD PAGES JSON LOAD ERROR:", path, str(exc))
        return default


def load_json_required(path):
    if not path:
        raise FileNotFoundError("Missing JSON path.")

    if not os.path.exists(path):
        raise FileNotFoundError(f"JSON file does not exist: {path}")

    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(f"Expected list in JSON file: {path}")

    return data


def find_latest_non_empty_file(pattern, label):
    files = sorted_files_newest_first(pattern)

    print("")
    print(f"=== SEARCHING {label} FILES ===")

    for path in files:
        data = load_json(path, [])
        count = len(data) if isinstance(data, list) else 0

        print(label, "candidate:", path, "count:", count)

        if isinstance(data, list) and count > 0:
            print(label, "selected:", path)
            print(f"=== END SEARCHING {label} FILES ===")
            print("")
            return path

    print(label, "selected:", None)
    print(f"=== END SEARCHING {label} FILES ===")
    print("")
    return None


def ensure_public_dirs():
    os.makedirs("public", exist_ok=True)
    os.makedirs("public/all", exist_ok=True)
    os.makedirs("public/BsT", exist_ok=True)
    os.makedirs("public/Blend", exist_ok=True)


# -----------------------------------------------------------------------------
# Numeric / probability / odds helpers
# -----------------------------------------------------------------------------


def safe_float(value):
    try:
        if value is None:
            return None

        if value == "":
            return None

        return float(value)

    except Exception:
        return None


def normalize_probability_decimal(value):
    """
    Returns probability as decimal.

    Accepted inputs:
    - 0.65  -> 0.65
    - 65.0  -> 0.65
    - None  -> None
    """
    number = safe_float(value)

    if number is None:
        return None

    if number > 1.0:
        return number / 100.0

    return number


def get_corq_probability(prediction):
    return normalize_probability_decimal(
        prediction.get("corq_ai_probability")
        or prediction.get("corq_display_probability")
        or prediction.get("probability")
    )


def get_thinq_probability(prediction):
    return normalize_probability_decimal(
        prediction.get("bst_ai_probability")
    )


def get_prediction_odds(prediction):
    return safe_float(
        prediction.get("odds")
    )


def has_required_page_odds(prediction):
    odds = get_prediction_odds(prediction)

    if odds is None:
        return False

    # Strictly greater than 1.33.
    # This excludes odds 1.33 and lower.
    return odds > MIN_PAGE_ODDS


def is_thinq_ok(prediction):
    return str(prediction.get("bst_ai_status") or "").upper().strip() == "OK"


# -----------------------------------------------------------------------------
# Prediction mutation helpers
# -----------------------------------------------------------------------------


def clone_prediction(prediction):
    return copy.deepcopy(prediction)


def unique_key(prediction):
    return (
        str(
            prediction.get("match_id")
            or prediction.get("event_id")
            or prediction.get("match")
            or ""
        ),
        str(prediction.get("pick") or ""),
    )


def dedupe_predictions(predictions):
    selected = []
    seen = set()

    for prediction in predictions:
        key = unique_key(prediction)

        if key in seen:
            continue

        seen.add(key)
        selected.append(prediction)

    return selected


def mark_corq_view(prediction, corq_probability):
    updated = clone_prediction(prediction)
    updated["probability"] = corq_probability
    updated["corq_display_probability"] = corq_probability
    updated["top_mode"] = "CORQ_THRESHOLD_55_ODDS_GT_1_33"
    updated["top_reason"] = "Corq AI probability >= 55% and odds > 1.33"
    return updated


def mark_thinq_view(prediction, thinq_probability, corq_probability):
    updated = clone_prediction(prediction)
    updated["probability"] = thinq_probability
    updated["corq_display_probability"] = corq_probability
    updated["top_mode"] = "THINQ_THRESHOLD_55_ODDS_GT_1_33"
    updated["top_reason"] = "Thinq AI probability >= 55%, bst_ai_status == OK, and odds > 1.33"
    return updated


def mark_blend_view(prediction, blend_probability, corq_probability, thinq_probability):
    updated = clone_prediction(prediction)
    updated["probability"] = blend_probability
    updated["blend_probability"] = blend_probability
    updated["corq_display_probability"] = corq_probability
    updated["bst_ai_probability"] = thinq_probability
    updated["top_mode"] = "BLEND_50_50_THRESHOLD_55_ODDS_GT_1_33"
    updated["top_reason"] = "50% Corq AI + 50% Thinq AI; Blend probability >= 55%, bst_ai_status == OK, and odds > 1.33"
    return updated


# -----------------------------------------------------------------------------
# Page derivation logic
# -----------------------------------------------------------------------------


def derive_corq_predictions(all_predictions):
    eligible = []

    for prediction in all_predictions or []:
        if not has_required_page_odds(prediction):
            continue

        corq_probability = get_corq_probability(prediction)

        if corq_probability is None:
            continue

        if corq_probability < CORQ_MIN_WIN:
            continue

        eligible.append(
            mark_corq_view(
                prediction,
                corq_probability,
            )
        )

    eligible.sort(
        key=lambda item: get_corq_probability(item) or 0.0,
        reverse=True,
    )

    selected = dedupe_predictions(eligible)

    print("CORQ THRESHOLD COUNT:", len(selected))
    return selected


def derive_thinq_predictions(all_predictions):
    eligible = []

    for prediction in all_predictions or []:
        if not has_required_page_odds(prediction):
            continue

        if not is_thinq_ok(prediction):
            continue

        thinq_probability = get_thinq_probability(prediction)
        corq_probability = get_corq_probability(prediction)

        if thinq_probability is None:
            continue

        if thinq_probability < THINQ_MIN_WIN:
            continue

        eligible.append(
            mark_thinq_view(
                prediction,
                thinq_probability,
                corq_probability,
            )
        )

    eligible.sort(
        key=lambda item: get_thinq_probability(item) or 0.0,
        reverse=True,
    )

    selected = dedupe_predictions(eligible)

    print("THINQ THRESHOLD COUNT:", len(selected))
    return selected


def derive_blend_predictions(all_predictions):
    eligible = []

    for prediction in all_predictions or []:
        if not has_required_page_odds(prediction):
            continue

        if not is_thinq_ok(prediction):
            continue

        corq_probability = get_corq_probability(prediction)
        thinq_probability = get_thinq_probability(prediction)

        if corq_probability is None:
            continue

        if thinq_probability is None:
            continue

        blend_probability = (corq_probability + thinq_probability) / 2.0

        if blend_probability < BLEND_MIN_WIN:
            continue

        eligible.append(
            mark_blend_view(
                prediction,
                blend_probability,
                corq_probability,
                thinq_probability,
            )
        )

    eligible.sort(
        key=lambda item: safe_float(item.get("blend_probability")) or 0.0,
        reverse=True,
    )

    selected = dedupe_predictions(eligible)

    print("BLEND THRESHOLD COUNT:", len(selected))
    return selected


# -----------------------------------------------------------------------------
# Logging / validation
# -----------------------------------------------------------------------------


def print_prediction_sample(label, predictions):
    print("")
    print(f"=== {label} SAMPLE ===")
    print("COUNT:", len(predictions))

    for index, prediction in enumerate(predictions[:10], start=1):
        print(
            json.dumps(
                {
                    "index": index,
                    "match": prediction.get("match"),
                    "pick": prediction.get("pick"),
                    "opponent": prediction.get("opponent"),
                    "probability": prediction.get("probability"),
                    "corq_display_probability": prediction.get("corq_display_probability"),
                    "bst_ai_probability": prediction.get("bst_ai_probability"),
                    "blend_probability": prediction.get("blend_probability"),
                    "ai_match": prediction.get("ai_match"),
                    "bst_ai_status": prediction.get("bst_ai_status"),
                    "odds": prediction.get("odds"),
                    "top_mode": prediction.get("top_mode"),
                    "top_reason": prediction.get("top_reason"),
                },
                ensure_ascii=False,
            )
        )

    print(f"=== END {label} SAMPLE ===")
    print("")


def validate_predictions(all_predictions):
    if not all_predictions:
        raise ValueError("ALL predictions are empty. Refusing to deploy empty ALL page.")

    all_with_pick = [
        prediction
        for prediction in all_predictions
        if prediction.get("pick")
    ]

    if not all_with_pick:
        raise ValueError("ALL predictions exist, but none contain a pick. Refusing deploy.")


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------


def build_pages():
    ensure_public_dirs()

    all_json = find_latest_non_empty_file(
        "public/all_predictions_*.json",
        "ALL",
    )

    print("")
    print("=== BUILD PAGES INPUTS ===")
    print("BUILD TIME UTC:", datetime.now(timezone.utc).isoformat())
    print("BUILD PAGES ALL JSON:", all_json)
    print("MIN PAGE ODDS:", MIN_PAGE_ODDS)
    print("=== END BUILD PAGES INPUTS ===")
    print("")

    all_predictions = load_json_required(all_json)

    validate_predictions(all_predictions)

    corq_predictions = derive_corq_predictions(all_predictions)
    thinq_predictions = derive_thinq_predictions(all_predictions)
    blend_predictions = derive_blend_predictions(all_predictions)

    print_prediction_sample("CORQ PREDICTIONS", corq_predictions)
    print_prediction_sample("THINQ PREDICTIONS", thinq_predictions)
    print_prediction_sample("BLEND PREDICTIONS", blend_predictions)
    print_prediction_sample("ALL PREDICTIONS", all_predictions)

    write_page(
        predictions=corq_predictions,
        title=SITE_TITLE,
        subtitle="Corq AI predictions >= 55% and odds > 1.33",
        destination="public/index.html",
    )

    write_rss(
        predictions=corq_predictions,
        title=f"{SITE_TITLE} - Corq",
        link=f"{BASE_URL}/",
        destination="public/tennis.xml",
    )

    write_page(
        predictions=thinq_predictions,
        title=SITE_TITLE,
        subtitle="Thinq AI predictions >= 55%, OK status and odds > 1.33",
        destination="public/BsT/index.html",
    )

    write_rss(
        predictions=thinq_predictions,
        title=f"{SITE_TITLE} - Thinq",
        link=f"{BASE_URL}/BsT/",
        destination="public/tennis_bst.xml",
    )

    write_page(
        predictions=blend_predictions,
        title=SITE_TITLE,
        subtitle="Blend 50/50 Corq and Thinq predictions >= 55%, OK status and odds > 1.33",
        destination="public/Blend/index.html",
    )

    write_rss(
        predictions=blend_predictions,
        title=f"{SITE_TITLE} - Blend",
        link=f"{BASE_URL}/Blend/",
        destination="public/tennis_blend.xml",
    )

    write_page(
        predictions=all_predictions,
        title=SITE_TITLE,
        subtitle="All available tennis predictions",
        destination="public/all/index.html",
    )

    write_rss(
        predictions=all_predictions,
        title=f"{SITE_TITLE} - ALL",
        link=f"{BASE_URL}/all/",
        destination="public/tennis_all.xml",
    )

    print("")
    print("=== BUILD PAGES WRITTEN ===")
    print("public/index.html")
    print("public/tennis.xml")
    print("public/BsT/index.html")
    print("public/tennis_bst.xml")
    print("public/Blend/index.html")
    print("public/tennis_blend.xml")
    print("public/all/index.html")
    print("public/tennis_all.xml")
    print("CORQ COUNT:", len(corq_predictions))
    print("THINQ COUNT:", len(thinq_predictions))
    print("BLEND COUNT:", len(blend_predictions))
    print("ALL COUNT:", len(all_predictions))
    print("=== END BUILD PAGES WRITTEN ===")
    print("")


if __name__ == "__main__":
    build_pages()
```


## FILE: elo_engine.py

```
import os
import csv
import json
import unicodedata
from difflib import SequenceMatcher


DEFAULT_ELO = 1500.0

ALIASES_PATH = "data/player_aliases.json"
ELO_DEBUG_PATH = "public/elo_debug.json"


#
# IMPORTANT:
# elo_history.csv is intentionally NOT used here.
# It is history, not current rating store.
#

ELO_CANDIDATE_FILES = [
    "data/elo/elo_store.json",
    "data/elo/elo.json",
    "data/elo/atp_elo_latest.csv",
    "data/elo/wta_elo_latest.csv",
    "data/elo/latest_elo.csv",
    "data/elo/elo_latest.csv",
    "elo_store.json",
    "elo.json",
]


_DEBUG = {
    "provider": "elo_engine_v2_safe_matcher",
    "loaded_files": [],
    "players_loaded": 0,

    "lookup_count": 0,
    "found_count": 0,
    "missing_count": 0,

    "examples_found": [],
    "examples_missing": [],
    "rating_samples": [],
}


def write_debug():
    os.makedirs(
        "public",
        exist_ok=True,
    )

    with open(
        ELO_DEBUG_PATH,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            _DEBUG,
            file,
            indent=2,
            ensure_ascii=False,
        )


def normalize_name(name):
    if not name:
        return ""

    value = str(name)

    value = unicodedata.normalize(
        "NFKD",
        value,
    )

    value = "".join(
        char
        for char in value
        if not unicodedata.combining(char)
    )

    value = value.lower()

    value = value.replace("-", " ")
    value = value.replace(".", " ")
    value = value.replace(",", " ")
    value = value.replace("'", "")
    value = value.replace("’", "")
    value = value.replace("`", "")

    return " ".join(value.split())


#
# Backward compatibility for form_engine.py
#

def normalize(name):
    return normalize_name(name)


def surface_key(surface):
    normalized = normalize_name(surface)

    if not normalized:
        return "hard"

    if "clay" in normalized:
        return "clay"

    if "grass" in normalized:
        return "grass"

    if "indoor" in normalized:
        return "indoor"

    if "hard" in normalized:
        return "hard"

    return normalized


def similarity(a, b):
    return SequenceMatcher(
        None,
        normalize_name(a),
        normalize_name(b),
    ).ratio()


def last_name(name):
    normalized = normalize_name(name)

    if not normalized:
        return ""

    parts = normalized.split()

    return parts[-1]


def first_token(name):
    normalized = normalize_name(name)

    if not normalized:
        return ""

    parts = normalized.split()

    return parts[0]


def safe_float(value, default=None):
    try:
        if value is None:
            return default

        if value == "":
            return default

        return float(value)

    except Exception:
        return default


def load_aliases():
    if not os.path.exists(ALIASES_PATH):
        return {}

    try:
        with open(
            ALIASES_PATH,
            "r",
            encoding="utf-8",
        ) as file:
            raw_aliases = json.load(file)

    except Exception:
        return {}

    aliases = {}

    for alias, canonical in raw_aliases.items():
        aliases[
            normalize_name(alias)
        ] = canonical

    return aliases


def detect_name(row):
    for key in [
        "player",
        "Player",
        "name",
        "Name",
        "player_name",
        "Player Name",
    ]:
        if key in row and row.get(key):
            return row.get(key)

    return None


def detect_elo(row):
    for key in [
        "elo",
        "Elo",
        "ELO",
        "rating",
        "Rating",
        "overall_elo",
        "overall",
        "Overall",
        "current_elo",
        "elo_rating",
        "latest_elo",
    ]:
        if key in row:
            value = safe_float(row.get(key))

            if value is not None:
                return value

    return None


def detect_yelo(row):
    for key in [
        "yelo",
        "Yelo",
        "YELO",
        "year_elo",
        "season_elo",
        "seasonal_elo",
    ]:
        if key in row:
            value = safe_float(row.get(key))

            if value is not None:
                return value

    return None


def detect_surface_elos(row):
    surfaces = {}

    mapping = {
        "hard": [
            "hard_elo",
            "Hard Elo",
            "hard",
            "Hard",
        ],
        "clay": [
            "clay_elo",
            "Clay Elo",
            "clay",
            "Clay",
        ],
        "grass": [
            "grass_elo",
            "Grass Elo",
            "grass",
            "Grass",
        ],
        "indoor": [
            "indoor_elo",
            "Indoor Elo",
            "indoor",
            "Indoor",
        ],
    }

    for surface, keys in mapping.items():
        for key in keys:
            if key in row:
                value = safe_float(row.get(key))

                if value is not None:
                    surfaces[surface] = value
                    break

    return surfaces


def add_record(store, name, record):
    if not name:
        return

    normalized = normalize_name(name)

    if not normalized:
        return

    record["name"] = name
    record["normalized_name"] = normalized

    store[normalized] = record


def load_json_file(path):
    store = {}

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if isinstance(data, dict):

        if "players" in data:
            players = data.get("players")

            if isinstance(players, dict):
                for name, value in players.items():
                    if not isinstance(value, dict):
                        continue

                    elo = safe_float(
                        value.get("elo")
                        or value.get("rating")
                        or value.get("overall_elo")
                        or value.get("latest_elo"),
                        DEFAULT_ELO,
                    )

                    yelo = safe_float(
                        value.get("yelo")
                        or value.get("year_elo")
                        or value.get("season_elo"),
                        elo,
                    )

                    record = {
                        "elo": elo,
                        "yelo": yelo,
                        "surfaces": value.get("surfaces") or {},
                        "source": path,
                        "raw": value,
                    }

                    add_record(
                        store,
                        name,
                        record,
                    )

            elif isinstance(players, list):
                for value in players:
                    if not isinstance(value, dict):
                        continue

                    name = detect_name(value)

                    if not name:
                        continue

                    elo = detect_elo(value)

                    if elo is None:
                        elo = DEFAULT_ELO

                    yelo = detect_yelo(value)

                    if yelo is None:
                        yelo = elo

                    record = {
                        "elo": elo,
                        "yelo": yelo,
                        "surfaces": detect_surface_elos(value),
                        "source": path,
                        "raw": value,
                    }

                    add_record(
                        store,
                        name,
                        record,
                    )

        else:
            for name, value in data.items():
                if isinstance(value, dict):
                    elo = safe_float(
                        value.get("elo")
                        or value.get("rating")
                        or value.get("overall_elo")
                        or value.get("latest_elo"),
                        DEFAULT_ELO,
                    )

                    yelo = safe_float(
                        value.get("yelo")
                        or value.get("year_elo")
                        or value.get("season_elo"),
                        elo,
                    )

                    record = {
                        "elo": elo,
                        "yelo": yelo,
                        "surfaces": value.get("surfaces") or {},
                        "source": path,
                        "raw": value,
                    }

                    add_record(
                        store,
                        name,
                        record,
                    )

                else:
                    elo = safe_float(value)

                    if elo is not None:
                        record = {
                            "elo": elo,
                            "yelo": elo,
                            "surfaces": {},
                            "source": path,
                            "raw": value,
                        }

                        add_record(
                            store,
                            name,
                            record,
                        )

    elif isinstance(data, list):
        for value in data:
            if not isinstance(value, dict):
                continue

            name = detect_name(value)

            if not name:
                continue

            elo = detect_elo(value)

            if elo is None:
                elo = DEFAULT_ELO

            yelo = detect_yelo(value)

            if yelo is None:
                yelo = elo

            record = {
                "elo": elo,
                "yelo": yelo,
                "surfaces": detect_surface_elos(value),
                "source": path,
                "raw": value,
            }

            add_record(
                store,
                name,
                record,
            )

    return store


def load_csv_file(path):
    store = {}

    with open(
        path,
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            name = detect_name(row)

            if not name:
                continue

            elo = detect_elo(row)

            if elo is None:
                elo = DEFAULT_ELO

            yelo = detect_yelo(row)

            if yelo is None:
                yelo = elo

            record = {
                "elo": elo,
                "yelo": yelo,
                "surfaces": detect_surface_elos(row),
                "source": path,
                "raw": row,
            }

            add_record(
                store,
                name,
                record,
            )

    return store


def load():
    """
    Existing prediction engines call this function.

    Returns:
        dict normalized_name -> player ELO record
    """

    store = {}

    _DEBUG["loaded_files"] = []
    _DEBUG["players_loaded"] = 0
    _DEBUG["rating_samples"] = []

    for path in ELO_CANDIDATE_FILES:
        if not os.path.exists(path):
            continue

        try:
            if path.endswith(".json"):
                loaded = load_json_file(path)

            elif path.endswith(".csv"):
                loaded = load_csv_file(path)

            else:
                loaded = {}

            if loaded:
                for key, record in loaded.items():
                    if key not in store:
                        store[key] = record

                _DEBUG["loaded_files"].append({
                    "path": path,
                    "players": len(loaded),
                })

        except Exception as exc:
            _DEBUG["loaded_files"].append({
                "path": path,
                "error": str(exc),
            })

    _DEBUG["players_loaded"] = len(store)

    for key, record in list(store.items())[:20]:
        _DEBUG["rating_samples"].append({
            "name": record.get("name"),
            "elo": record.get("elo"),
            "yelo": record.get("yelo"),
            "source": record.get("source"),
        })

    write_debug()

    return store


def candidate_matches_by_initial(player_name, store):
    normalized = normalize_name(player_name)
    parts = normalized.split()

    if len(parts) < 2:
        return []

    first = parts[0]
    last = parts[-1]

    if len(first) != 1:
        return []

    matches = []

    for key, record in store.items():
        record_name = record.get("name", key)
        record_first = first_token(record_name)
        record_last = last_name(record_name)

        if record_last == last and record_first.startswith(first):
            matches.append(
                (key, record, 1.0)
            )

    return matches


def find_player_record(player_name, store):
    _DEBUG["lookup_count"] += 1

    aliases = load_aliases()
    normalized = normalize_name(player_name)

    if not normalized:
        _DEBUG["missing_count"] += 1

        return {
            "found": False,
            "record": None,
            "matched_name": None,
            "match_method": "empty",
            "match_score": 0.0,
        }

    if normalized in store:
        record = store[normalized]

        _DEBUG["found_count"] += 1

        if len(_DEBUG["examples_found"]) < 30:
            _DEBUG["examples_found"].append({
                "input": player_name,
                "matched": record.get("name"),
                "method": "exact",
                "score": 1.0,
                "elo": record.get("elo"),
                "source": record.get("source"),
            })

        return {
            "found": True,
            "record": record,
            "matched_name": record.get("name"),
            "match_method": "exact",
            "match_score": 1.0,
        }

    alias_target = aliases.get(normalized)

    if alias_target:
        alias_normalized = normalize_name(alias_target)

        if alias_normalized in store:
            record = store[alias_normalized]

            _DEBUG["found_count"] += 1

            if len(_DEBUG["examples_found"]) < 30:
                _DEBUG["examples_found"].append({
                    "input": player_name,
                    "matched": record.get("name"),
                    "method": "alias",
                    "score": 1.0,
                    "elo": record.get("elo"),
                    "source": record.get("source"),
                })

            return {
                "found": True,
                "record": record,
                "matched_name": record.get("name"),
                "match_method": "alias",
                "match_score": 1.0,
            }

    initial_matches = candidate_matches_by_initial(
        player_name,
        store,
    )

    if len(initial_matches) == 1:
        key, record, score = initial_matches[0]

        _DEBUG["found_count"] += 1

        if len(_DEBUG["examples_found"]) < 30:
            _DEBUG["examples_found"].append({
                "input": player_name,
                "matched": record.get("name"),
                "method": "initial_last_name",
                "score": score,
                "elo": record.get("elo"),
                "source": record.get("source"),
            })

        return {
            "found": True,
            "record": record,
            "matched_name": record.get("name"),
            "match_method": "initial_last_name",
            "match_score": score,
        }

    input_last = last_name(player_name)

    candidates = []

    for key, record in store.items():
        record_name = record.get("name", key)
        record_last = last_name(record_name)

        last_score = similarity(
            input_last,
            record_last,
        )

        if last_score < 0.92:
            continue

        full_score = similarity(
            player_name,
            record_name,
        )

        if full_score >= 0.90:
            candidates.append({
                "key": key,
                "record": record,
                "score": full_score,
                "last_score": last_score,
            })

    candidates.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    if candidates:
        best = candidates[0]
        ambiguous = False

        if len(candidates) > 1:
            second = candidates[1]

            if (
                best["score"]
                - second["score"]
            ) < 0.03:
                ambiguous = True

        if not ambiguous:
            record = best["record"]

            _DEBUG["found_count"] += 1

            if len(_DEBUG["examples_found"]) < 30:
                _DEBUG["examples_found"].append({
                    "input": player_name,
                    "matched": record.get("name"),
                    "method": "fuzzy_safe",
                    "score": round(
                        best["score"],
                        3,
                    ),
                    "elo": record.get("elo"),
                    "source": record.get("source"),
                })

            return {
                "found": True,
                "record": record,
                "matched_name": record.get("name"),
                "match_method": "fuzzy_safe",
                "match_score": round(
                    best["score"],
                    3,
                ),
            }

    _DEBUG["missing_count"] += 1

    if len(_DEBUG["examples_missing"]) < 50:
        _DEBUG["examples_missing"].append({
            "input": player_name,
            "normalized": normalized,
            "reason": "no_safe_match",
        })

    return {
        "found": False,
        "record": None,
        "matched_name": None,
        "match_method": "missing",
        "match_score": 0.0,
    }


def find_player_key(*args):
    if len(args) != 2:
        return None

    first = args[0]
    second = args[1]

    if isinstance(first, dict):
        store = first
        player_name = second

    else:
        player_name = first
        store = second

    if not isinstance(store, dict):
        return None

    normalized = normalize_name(player_name)

    if normalized in store:
        return normalized

    aliases = load_aliases()

    alias_target = aliases.get(normalized)

    if alias_target:
        alias_normalized = normalize_name(alias_target)

        if alias_normalized in store:
            return alias_normalized

    input_last = last_name(player_name)

    candidates = []

    for key in store.keys():
        key_last = last_name(key)

        last_score = similarity(
            input_last,
            key_last,
        )

        if last_score < 0.92:
            continue

        full_score = similarity(
            player_name,
            key,
        )

        if full_score >= 0.90:
            candidates.append({
                "key": key,
                "score": full_score,
            })

    candidates.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    if candidates:
        if len(candidates) == 1:
            return candidates[0]["key"]

        if (
            candidates[0]["score"]
            - candidates[1]["score"]
        ) >= 0.03:
            return candidates[0]["key"]

    return None


def get_rating_from_record(record, surface=None):
    if not record:
        return DEFAULT_ELO

    if surface:
        surface_key_value = surface_key(surface)

        surfaces = record.get("surfaces") or {}

        if isinstance(surfaces, dict):
            for key, value in surfaces.items():
                if surface_key(key) == surface_key_value:
                    detected = safe_float(value)

                    if detected is not None:
                        return detected

    elo = safe_float(
        record.get("elo"),
        DEFAULT_ELO,
    )

    return elo


def get_yelo_from_record(record):
    if not record:
        return DEFAULT_ELO

    yelo = safe_float(
        record.get("yelo"),
        None,
    )

    if yelo is not None:
        return yelo

    return safe_float(
        record.get("elo"),
        DEFAULT_ELO,
    )


def win_probability(rating_a, rating_b):
    return 1 / (
        1 + 10 ** (
            (rating_b - rating_a) / 400
        )
    )


def predict(
    player1,
    player2,
    surface=None,
    elo_store=None,
):
    if elo_store is None:
        elo_store = load()

    lookup1 = find_player_record(
        player1,
        elo_store,
    )

    lookup2 = find_player_record(
        player2,
        elo_store,
    )

    rating1 = get_rating_from_record(
        lookup1.get("record"),
        surface=surface,
    )

    rating2 = get_rating_from_record(
        lookup2.get("record"),
        surface=surface,
    )

    yelo1 = get_yelo_from_record(
        lookup1.get("record"),
    )

    yelo2 = get_yelo_from_record(
        lookup2.get("record"),
    )

    probability1 = win_probability(
        rating1,
        rating2,
    )

    probability2 = 1 - probability1

    write_debug()

    return {
        "probability_player1": probability1,
        "probability_player2": probability2,

        "elo_player1": rating1,
        "elo_player2": rating2,

        "yelo_player1": yelo1,
        "yelo_player2": yelo2,

        "elo_found_player1": lookup1.get("found"),
        "elo_found_player2": lookup2.get("found"),

        "elo_match_player1": lookup1.get("matched_name"),
        "elo_match_player2": lookup2.get("matched_name"),

        "elo_match_method_player1": lookup1.get("match_method"),
        "elo_match_method_player2": lookup2.get("match_method"),

        "elo_match_score_player1": lookup1.get("match_score"),
        "elo_match_score_player2": lookup2.get("match_score"),
    }
```


## FILE: elo_html_downloader.py

```
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


RAW_DIR = Path("data/elo/raw")
HISTORY_DIR = Path("data/elo/raw_history")
META_DIR = Path("data/elo/meta")

USER_AGENT = "Mozilla/5.0 (compatible; backstage-talks-elo-cache/1.0)"
REQUEST_TIMEOUT_SECONDS = 45
REQUEST_SLEEP_SECONDS = 2

# Local filename -> Tennis Abstract source URL
SOURCE_MAP = {
    "atp_elo.html": "https://tennisabstract.com/reports/atp_elo_ratings.html",
    "wta_yelo.html": "https://tennisabstract.com/reports/wta_season_yelo_ratings.html",
    "wta_elo.html": "https://tennisabstract.com/reports/wta_elo_ratings.html",
    "atp_yelo.html": "https://tennisabstract.com/reports/atp_season_yelo_ratings.html",
}


def ensure_dirs():
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)
    META_DIR.mkdir(parents=True, exist_ok=True)


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def today_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def sha256_text(text):
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def fetch_url(url):
    request = Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        },
    )

    with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
        raw = response.read()
        charset = response.headers.get_content_charset() or "utf-8"
        return raw.decode(charset, errors="replace")


def write_text(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def copy_to_history(filename, html_text):
    date_dir = HISTORY_DIR / today_utc()
    date_dir.mkdir(parents=True, exist_ok=True)
    write_text(date_dir / filename, html_text)


def write_meta(filename, url, html_text, changed):
    meta_text = (
        f"filename={filename}\n"
        f"url={url}\n"
        f"downloaded_at_utc={utc_now_iso()}\n"
        f"sha256={sha256_text(html_text)}\n"
        f"changed={str(changed).lower()}\n"
        f"bytes={len(html_text.encode('utf-8', errors='replace'))}\n"
    )
    write_text(META_DIR / f"{filename}.meta", meta_text)


def validate_html(filename, html_text):
    lowered = html_text.lower()

    if "<html" not in lowered and "<table" not in lowered:
        raise RuntimeError(
            f"Downloaded content does not look like an HTML ratings page: {filename}"
        )

    if "tennis abstract" not in lowered and "elo" not in lowered:
        raise RuntimeError(
            f"Downloaded content does not look like Tennis Abstract Elo content: {filename}"
        )


def update_one(filename, url):
    destination = RAW_DIR / filename
    previous = destination.read_text(encoding="utf-8", errors="replace") if destination.exists() else None

    print("ELO DOWNLOAD START:", filename, url)
    html_text = fetch_url(url)
    validate_html(filename, html_text)

    changed = previous != html_text

    write_text(destination, html_text)
    copy_to_history(filename, html_text)
    write_meta(filename, url, html_text, changed)

    print(
        "ELO DOWNLOAD DONE:",
        filename,
        "changed=",
        changed,
        "bytes=",
        len(html_text.encode("utf-8", errors="replace")),
    )

    return changed


def main():
    ensure_dirs()

    any_changed = False
    failures = []

    for index, (filename, url) in enumerate(SOURCE_MAP.items(), start=1):
        try:
            changed = update_one(filename, url)
            any_changed = any_changed or changed
        except (HTTPError, URLError, TimeoutError, RuntimeError) as exc:
            print("ELO DOWNLOAD ERROR:", filename, url, repr(exc))
            failures.append((filename, url, repr(exc)))
        except Exception as exc:
            print("ELO DOWNLOAD UNEXPECTED ERROR:", filename, url, repr(exc))
            failures.append((filename, url, repr(exc)))

        if index < len(SOURCE_MAP):
            time.sleep(REQUEST_SLEEP_SECONDS)

    if failures:
        print("")
        print("ELO DOWNLOAD FAILURES:")
        for filename, url, error in failures:
            print(filename, url, error)
        raise SystemExit(1)

    print("")
    print("ELO DOWNLOAD SUMMARY:")
    print("any_changed=", any_changed)
    print("raw_dir=", RAW_DIR)
    print("history_dir=", HISTORY_DIR / today_utc())
    print("meta_dir=", META_DIR)


if __name__ == "__main__":
    main()
```


## FILE: fetch_matches.py

```
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from tennisapi_client import TennisApiClient, normalize_event


logger = logging.getLogger(__name__)

LOCAL_TZ = ZoneInfo("Europe/Bratislava")


# ----------------------------------------------------------------------
# Config
# ----------------------------------------------------------------------


def parse_category_ids() -> List[int]:
    """
    TennisApi categories used for fixtures.

    Current working set:
    - 3   = ATP / ATP events confirmed earlier
    - 6   = likely WTA / main women's tennis category candidate
    - 871 = WTA 125 confirmed from API response
    """
    raw = os.getenv("TENNISAPI_CATEGORY_IDS", "3,6,871").strip()
    category_ids: List[int] = []

    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            category_ids.append(int(part))
        except Exception:
            logger.warning("Invalid TENNISAPI_CATEGORY_IDS item ignored: %s", part)

    return category_ids or [3]


def parse_min_minutes_before_start() -> int:
    """
    Do not publish picks for matches that already started or are too close to start.

    Default 5 minutes: if workflow runs late, matches already in progress/finished are skipped.
    Override with:
        MIN_MINUTES_BEFORE_MATCH_START=0
    """
    try:
        return int(os.getenv("MIN_MINUTES_BEFORE_MATCH_START", "5"))
    except Exception:
        return 5


def betting_day(date_time: Optional[datetime] = None) -> datetime:
    """
    Snapshot day logic aligned with project rule:
    before 06:00 SK/CZ treat as previous betting day.
    """
    if date_time is None:
        date_time = datetime.now(LOCAL_TZ)

    if date_time.tzinfo is None:
        date_time = date_time.replace(tzinfo=LOCAL_TZ)
    else:
        date_time = date_time.astimezone(LOCAL_TZ)

    if date_time.hour < 6:
        date_time = date_time - timedelta(days=1)

    return date_time


# ----------------------------------------------------------------------
# Public API consumed by prediction_engine_core.py
# ----------------------------------------------------------------------


def get_today_matches() -> List[Dict[str, Any]]:
    """
    Main fixture entrypoint used by prediction_engine_core.py.

    TennisApi is primary and every returned match keeps:
        match_id / event_id / id

    Important safety fix:
        Finished, cancelled, retired, walkover, live/in-progress and already-started
        matches are excluded from prediction snapshots.
    """
    target_dt = betting_day()
    matches = get_matches_for_date(target_dt)

    print("FETCH_MATCHES TENNISAPI COUNT:", len(matches))
    if matches[:5]:
        for item in matches[:5]:
            print(
                "FETCH_MATCHES SAMPLE:",
                item.get("match_id"),
                item.get("player1"),
                "vs",
                item.get("player2"),
                item.get("tournament"),
                item.get("category"),
                item.get("match_start"),
            )

    return matches


def get_matches_for_date(target_date: datetime) -> List[Dict[str, Any]]:
    client = TennisApiClient()
    category_ids = parse_category_ids()

    all_matches: List[Dict[str, Any]] = []
    seen = set()
    skipped = {
        "invalid": 0,
        "duplicate": 0,
        "not_playable_status": 0,
        "wrong_local_date": 0,
        "already_started": 0,
    }

    for category_id in category_ids:
        try:
            events = client.get_events_by_category_date(
                category_id=category_id,
                day=target_date.day,
                month=target_date.month,
                year=target_date.year,
            )
        except Exception as exc:
            logger.warning(
                "TennisApi fixture fetch failed. category_id=%s date=%s error=%s",
                category_id,
                target_date.date(),
                exc,
            )
            continue

        for event in events:
            match = normalize_tennisapi_event_for_model(event, target_date=target_date, skipped=skipped)
            if not match:
                continue

            match_id = match.get("match_id")
            if match_id in seen:
                skipped["duplicate"] += 1
                continue
            seen.add(match_id)
            all_matches.append(match)

    all_matches.sort(key=lambda item: item.get("start_timestamp") or 0)

    print("FETCH_MATCHES SKIPPED:", skipped)
    return all_matches


# ----------------------------------------------------------------------
# Normalization + filtering
# ----------------------------------------------------------------------


def normalize_tennisapi_event_for_model(
    event: Dict[str, Any],
    target_date: datetime,
    skipped: Optional[Dict[str, int]] = None,
) -> Optional[Dict[str, Any]]:
    normalized = normalize_event(event)

    match_id = normalized.get("match_id")
    player1 = normalized.get("player1")
    player2 = normalized.get("player2")

    if not match_id or not player1 or not player2:
        increment(skipped, "invalid")
        return None

    status = str(normalized.get("status") or "UNKNOWN").upper()

    # Only future scheduled/not-started matches can enter prediction snapshot.
    # This prevents yesterday/already-played matches from appearing in TOP5.
    if status not in {"NOT_STARTED", "UNKNOWN"}:
        increment(skipped, "not_playable_status")
        return None

    start_timestamp = normalized.get("start_timestamp")
    start_dt_utc = timestamp_to_datetime_utc(start_timestamp)

    if start_dt_utc is not None:
        start_dt_local = start_dt_utc.astimezone(LOCAL_TZ)
        target_local_date = target_date.astimezone(LOCAL_TZ).date()

        # Defensive guard: only keep matches from the selected betting date.
        if start_dt_local.date() != target_local_date:
            increment(skipped, "wrong_local_date")
            return None

        min_minutes = parse_min_minutes_before_start()
        earliest_allowed_start = datetime.now(timezone.utc) + timedelta(minutes=min_minutes)
        if start_dt_utc <= earliest_allowed_start:
            increment(skipped, "already_started")
            return None

    category = normalized.get("category")
    tournament = normalized.get("tournament")
    surface = infer_surface_from_event(normalized)
    gender = infer_gender_from_category(category)
    best_of = infer_best_of(normalized)
    match_start = timestamp_to_iso_utc(start_timestamp)

    return {
        # Critical identity fields for odds/results pairing
        "match_id": match_id,
        "event_id": match_id,
        "id": match_id,
        "source": "TennisApi",

        # Core model fields
        "player1": player1,
        "player2": player2,
        "match": f"{player1} vs {player2}",
        "surface": surface,
        "tournament": tournament,
        "category": category,
        "gender": gender,
        "best_of": best_of,

        # Time fields consumed by prediction_engine_core.py
        "match_start": match_start,
        "start_time": match_start,
        "commence_time": match_start,
        "start_timestamp": start_timestamp,

        # Extra metadata
        "status": normalized.get("status"),
        "round": normalized.get("round"),
        "home_seed": normalized.get("home_seed"),
        "away_seed": normalized.get("away_seed"),
        "raw": normalized.get("raw"),
    }


def increment(counter: Optional[Dict[str, int]], key: str) -> None:
    if isinstance(counter, dict):
        counter[key] = int(counter.get(key, 0)) + 1


def timestamp_to_datetime_utc(timestamp: Any) -> Optional[datetime]:
    if not timestamp:
        return None
    try:
        return datetime.fromtimestamp(int(timestamp), tz=timezone.utc)
    except Exception:
        return None


def timestamp_to_iso_utc(timestamp: Any) -> Optional[str]:
    dt = timestamp_to_datetime_utc(timestamp)
    return dt.isoformat() if dt else None


def infer_gender_from_category(category: Any) -> Optional[str]:
    text = str(category or "").lower()
    if "wta" in text or "women" in text:
        return "WTA"
    if "atp" in text or "challenger" in text:
        return "ATP"
    return str(category) if category else None


def infer_best_of(event: Dict[str, Any]) -> int:
    tournament = str(event.get("tournament") or "").lower()
    category = str(event.get("category") or "").lower()

    # Doubles should not be inferred as classic BO5 for set model.
    if "doubles" in tournament:
        return 3

    if "atp" in category and any(
        slam in tournament
        for slam in ["wimbledon", "roland garros", "australian open", "us open"]
    ):
        return 5

    return 3


def infer_surface_from_event(event: Dict[str, Any]) -> str:
    tournament = str(event.get("tournament") or "").lower()

    if "wimbledon" in tournament or "grass" in tournament:
        return "Grass"
    if "roland garros" in tournament or "clay" in tournament:
        return "Clay"
    if "hard" in tournament:
        return "Hard"

    return "Hard"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    matches = get_today_matches()
    print("Matches found:", len(matches))
    for match in matches[:30]:
        print(
            match.get("match_id"),
            match.get("player1"),
            "vs",
            match.get("player2"),
            "|",
            match.get("tournament"),
            "|",
            match.get("category"),
            "|",
            match.get("status"),
            "|",
            match.get("match_start"),
        )
```


## FILE: files_to_export.txt

```
./.github/workflows/daily-tennis-predictions.yml
./.github/workflows/export-repo-for-audit.yml
./.github/workflows/telegram-rss-feed.yml
./.github/workflows/weekly-elo-html-download.yml
./all.py
./analytics.py
./bst_ai_refresher.py
./build_elo.py
./build_pages.py
./elo_engine.py
./elo_html_downloader.py
./fetch_matches.py
./files_to_export.txt
./fix_navigation.py
./form_engine.py
./mcp_loader.py
./mcp_module.py
./model_diagnostics.py
./odds_api.py
./play_history.py
./player_matcher.py
./prediction_engine_all.py
./prediction_engine_core.py
./prediction_engine_top.py
./random_paths.py
./render_site.py
./render_site_ready.py
./requirements.txt
./results_checker.py
./results_fetcher.py
./results_fetcher_sofa.py
./rss_results.py
./sackmann_loader.py
./sets_model.py
./src/__init__.py
./src/bst_ai/__init__.py
./src/bst_ai/matching.py
./src/bst_ai/probability.py
./src/bst_ai/rules.py
./src/bst_ai/service.py
./src/bst_ai/ta_sync.py
./src/elo/README.md
./src/elo/__init__.py
./src/elo/clean.py
./src/elo/consensus.py
./src/elo/elo_engine.py
./src/elo/features.py
./src/elo/fetch.py
./src/elo/probability.py
./src/elo/service.py
./src/elo/store.py
./src/elo/tbt_predict.py
./src/elo/test_store.py
./src/elo/update_elo.py
./src/marq_ai/__init__.py
./src/marq_ai/adapters.py
./src/marq_ai/engine.py
./src/marq_ai/models.py
./src/marq_ai/movements.py
./src/marq_ai/pipeline.py
./src/marq_ai/provider.py
./src/marq_ai/rapid_api.py
./src/marq_ai/service.py
./src/marq_ai/signals.py
./src/marq_ai/storage.py
./src/marq_ai/transformer-4.py
./src/marq_ai/transformer.py
./src/models/match_intelligence.py
./src/results/__init__.py
./stats_engine.py
./telegram_feed.py
./telegram_rss_feed.py
./tennisapi_cache.py
./tennisapi_client.py
./tennisapi_set_markets.py
./tests/test_marq_ai.py
./tests/test_marq_provider.py
./update.py
```


## FILE: fix_navigation.py

```
from pathlib import Path
import re

PUBLIC_DIR = Path("public")

LAYOUT_TUNE_CSS = r"""
<style id="bt-layout-tune-style">
  /* Match Intelligence layout tuning */
  .intel {
    min-width: 490px !important;
  }

  .intel-layout {
    display: grid !important;
    grid-template-columns: 138px 138px 172px !important;
    gap: 10px !important;
    align-items: stretch !important;
  }

  .intel-box {
    min-height: 108px !important;
    padding: 10px 10px !important;
    overflow: visible !important;
  }

  .data-ai-box,
  .marq-ai-box {
    min-width: 138px !important;
  }

  .sets-box {
    min-width: 172px !important;
  }

  .sets-box .intel-row {
    grid-template-columns: 62px minmax(82px, 1fr) !important;
    column-gap: 8px !important;
  }

  .sets-box .intel-row span:first-child,
  .sets-box .intel-row span:last-child {
    white-space: nowrap !important;
  }

  .ai-diff {
    margin-top: 6px !important;
    padding-top: 5px !important;
    border-top: 1px solid rgba(148, 163, 184, .25) !important;
    font-size: 10px !important;
    line-height: 1.2 !important;
    text-align: right !important;
    font-weight: 900 !important;
    white-space: nowrap !important;
  }

  .marq-signal {
    min-height: 38px !important;
  }

  @media (max-width: 1200px) {
    .intel {
      min-width: 230px !important;
    }

    .intel-layout {
      grid-template-columns: 1fr !important;
    }

    .data-ai-box,
    .marq-ai-box,
    .sets-box {
      min-width: 0 !important;
    }
  }
</style>
"""


def inject_layout_css(html: str) -> str:
    html = re.sub(
        r'<style[^>]*id=["\']bt-layout-tune-style["\'][\s\S]*?</style>',
        '',
        html,
        flags=re.I,
    )

    if "</head>" in html:
        return html.replace("</head>", LAYOUT_TUNE_CSS + "\n</head>", 1)

    return LAYOUT_TUNE_CSS + "\n" + html


def fix_file(path: Path) -> bool:
    original = path.read_text(encoding="utf-8", errors="replace")
    fixed = inject_layout_css(original)
    if fixed != original:
        path.write_text(fixed, encoding="utf-8")
        return True
    return False


def main() -> None:
    if not PUBLIC_DIR.exists():
        print("public directory does not exist, layout tune skipped")
        return

    changed = []
    for html_file in PUBLIC_DIR.rglob("*.html"):
        if fix_file(html_file):
            changed.append(str(html_file))

    print(f"Layout tune updated {len(changed)} HTML files")
    for item in changed:
        print(f"- {item}")


if __name__ == "__main__":
    main()
```


## FILE: form_engine.py

```
import json
import os
from datetime import datetime

from elo_engine import normalize, find_player_key, surface_key


DATA_PATH = "data/form_stats.json"


def parse_date(value):
    text = str(value or "")

    if not text or text == "0":
        return None

    for fmt in ["%Y%m%d", "%Y-%m-%d"]:
        try:
            return datetime.strptime(text[:10], fmt)
        except Exception:
            continue

    return None


def ensure_player(store, player):
    key = normalize(player)

    if key not in store:
        store[key] = {
            "player": player,
            "results": [],
            "surface_results": {
                "hard": [],
                "clay": [],
                "grass": [],
                "carpet": [],
            },
        }

    return key


def trim_results(results, keep=80):
    if len(results) <= keep:
        return results

    return results[-keep:]


def add_match(store, player, surface, won, date):
    key = ensure_player(store, player)
    s_key = surface_key(surface)

    item = {
        "date": str(date or "0"),
        "result": 1 if won else 0,
    }

    store[key]["results"].append(item)
    store[key]["results"] = trim_results(store[key]["results"])

    if s_key not in store[key]["surface_results"]:
        store[key]["surface_results"][s_key] = []

    store[key]["surface_results"][s_key].append(item)
    store[key]["surface_results"][s_key] = trim_results(
        store[key]["surface_results"][s_key]
    )


def build_form_store(matches):
    store = {}

    sorted_matches = sorted(
        matches,
        key=lambda x: str(x.get("date") or "0")
    )

    for match in sorted_matches:
        try:
            player1 = match.get("player1")
            player2 = match.get("player2")
            winner = match.get("winner")
            surface = match.get("surface", "Hard")
            date = str(match.get("date") or "0")

            if not player1 or not player2 or not winner:
                continue

            winner_key = normalize(winner)
            p1_key = normalize(player1)
            p2_key = normalize(player2)

            add_match(
                store=store,
                player=player1,
                surface=surface,
                won=(winner_key == p1_key),
                date=date,
            )

            add_match(
                store=store,
                player=player2,
                surface=surface,
                won=(winner_key == p2_key),
                date=date,
            )

        except Exception:
            continue

    return store


def save_form_store(store):
    os.makedirs("data", exist_ok=True)

    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(store, f, ensure_ascii=False, indent=2)


def load_form_store():
    if not os.path.exists(DATA_PATH):
        return {}

    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_and_save_form(matches):
    store = build_form_store(matches)
    save_form_store(store)
    return store


def latest_date_in_items(items):
    dates = []

    for item in items:
        dt = parse_date(item.get("date"))

        if dt:
            dates.append(dt)

    if not dates:
        return None

    return max(dates)


def filter_by_horizon(items, horizon_days):
    if not items:
        return []

    reference_date = latest_date_in_items(items)

    if not reference_date:
        return items

    output = []

    for item in items:
        dt = parse_date(item.get("date"))

        if not dt:
            continue

        age = max(0, (reference_date - dt).days)

        if age <= horizon_days:
            output.append(item)

    return output


def rate(items, n):
    if not items:
        return None

    subset = items[-n:]

    if not subset:
        return None

    return sum(item.get("result", 0) for item in subset) / len(subset)


def safe_rate(value):
    if value is None:
        return None

    try:
        return round(float(value), 3)
    except Exception:
        return None


def get_player_form(store, player, surface):
    player_key = find_player_key(store, player)

    if not player_key:
        return {
            "found": False,
            "matched_key": None,
            "last_5": None,
            "last_10": None,
            "surface_last_5": None,
            "surface_last_10": None,
            "matches": 0,
            "surface_matches": 0,
            "recent_horizon_days": 180,
            "surface_horizon_days": 730 if surface_key(surface) == "grass" else 365,
        }

    record = store[player_key]
    s_key = surface_key(surface)

    all_results = record.get("results", [])
    surface_results = record.get("surface_results", {}).get(s_key, [])

    recent_results = filter_by_horizon(all_results, 180)

    if s_key == "grass":
        surface_horizon = 730
    else:
        surface_horizon = 365

    recent_surface_results = filter_by_horizon(surface_results, surface_horizon)

    return {
        "found": True,
        "matched_key": player_key,
        "last_5": safe_rate(rate(recent_results, 5)),
        "last_10": safe_rate(rate(recent_results, 10)),
        "surface_last_5": safe_rate(rate(recent_surface_results, 5)),
        "surface_last_10": safe_rate(rate(recent_surface_results, 10)),
        "matches": len(recent_results),
        "surface_matches": len(recent_surface_results),
        "recent_horizon_days": 180,
        "surface_horizon_days": surface_horizon,
    }


def usable_rate(value):
    if value is None:
        return 0.5

    try:
        return float(value)
    except Exception:
        return 0.5


def clamp(value, low, high):
    return max(low, min(high, value))


def calculate_form_adjustment(pick_form, opponent_form):
    """
    Small correction only.
    ELO remains the main model.

    Max total adjustment: +/- 3.5 percentage points.
    """
    pick_last10 = usable_rate(pick_form.get("last_10"))
    opp_last10 = usable_rate(opponent_form.get("last_10"))

    recent_diff = pick_last10 - opp_last10

    recent_adjustment = clamp(
        recent_diff * 0.05,
        -0.025,
        0.025,
    )

    surface_adjustment = 0.0

    pick_surface_matches = pick_form.get("surface_matches") or 0
    opp_surface_matches = opponent_form.get("surface_matches") or 0

    if pick_surface_matches >= 3 and opp_surface_matches >= 3:
        pick_surface = usable_rate(pick_form.get("surface_last_10"))
        opp_surface = usable_rate(opponent_form.get("surface_last_10"))

        surface_diff = pick_surface - opp_surface

        surface_adjustment = clamp(
            surface_diff * 0.035,
            -0.015,
            0.015,
        )

    total_adjustment = clamp(
        recent_adjustment + surface_adjustment,
        -0.035,
        0.035,
    )

    return {
        "recent_adjustment": round(recent_adjustment, 3),
        "surface_adjustment": round(surface_adjustment, 3),
        "total_adjustment": round(total_adjustment, 3),
    }
```


## FILE: mcp_loader.py

```
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
```


## FILE: mcp_module.py

```
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
```


## FILE: model_diagnostics.py

```
import json
import os
from datetime import datetime, timezone

from src.models.match_intelligence import build_match_intelligence


OUTPUT_PATH = "public/model_diagnostics.json"


TEST_PROBABILITIES = [
    0.50,
    0.55,
    0.60,
    0.65,
    0.70,
    0.75,
    0.80,
    0.85,
]


TEST_CASES = [
    {
        "label": "BO3 standard",
        "best_of": 3,
        "tournament": "ATP 250",
    },
    {
        "label": "BO5 Wimbledon Men",
        "best_of": 5,
        "tournament": "Wimbledon Men Singles",
    },
]


def pct(value):
    try:
        return f"{float(value) * 100:.1f}%"
    except Exception:
        return "-"


def fmt(value, digits=3):
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return "-"


def build_case_result(case, probability):
    model = build_match_intelligence(
        probability=probability,
        tournament=case.get("tournament"),
        best_of=case.get("best_of"),
    )

    return {
        "case": case.get("label"),
        "tournament": case.get("tournament"),
        "input_match_probability": probability,
        "input_match_probability_pct": pct(probability),

        "best_of": model.get("best_of"),
        "set_win_probability": model.get("set_win_probability"),
        "set_win_probability_pct": pct(
            model.get("set_win_probability")
        ),

        "expected_sets": model.get("expected_sets"),

        "sets_probability_label": model.get("sets_probability_label"),
        "sets_probability": model.get("sets_probability"),
        "sets_probability_pct": pct(
            model.get("sets_probability")
        ),

        "most_likely_score": model.get("most_likely_score"),
        "score_probabilities": model.get("score_probabilities"),

        "expected_games": model.get("expected_games"),
        "games_pick": model.get("games_pick"),
        "games_line": model.get("games_line"),

        "tag": model.get("tag"),
    }


def print_header(title):
    print("")
    print("=" * 90)
    print(title)
    print("=" * 90)


def print_table(results):
    print(
        f"{'Prob':>8} | "
        f"{'BO':>4} | "
        f"{'SetWin':>8} | "
        f"{'ExpSets':>8} | "
        f"{'SetLabel':>10} | "
        f"{'SetProb':>8} | "
        f"{'Likely':>8}"
    )

    print("-" * 90)

    for row in results:
        print(
            f"{row['input_match_probability_pct']:>8} | "
            f"BO{row['best_of']:<2} | "
            f"{row['set_win_probability_pct']:>8} | "
            f"{fmt(row['expected_sets'], 1):>8} | "
            f"{str(row['sets_probability_label']):>10} | "
            f"{row['sets_probability_pct']:>8} | "
            f"{str(row['most_likely_score']):>8}"
        )


def print_score_distribution(row):
    print("")
    print(
        "Score probabilities for",
        row["case"],
        "at",
        row["input_match_probability_pct"],
    )

    distribution = row.get("score_probabilities") or {}

    for score, probability in distribution.items():
        print(
            f"  {score}: {pct(probability)}"
        )


def sanity_checks(results):
    warnings = []

    for row in results:
        probability = row.get("input_match_probability")
        best_of = row.get("best_of")
        expected_sets = row.get("expected_sets")
        sets_probability = row.get("sets_probability")
        distribution = row.get("score_probabilities") or {}

        total_distribution_probability = sum(
            float(value)
            for value in distribution.values()
        )

        if abs(total_distribution_probability - 1.0) > 0.01:
            warnings.append({
                "case": row.get("case"),
                "probability": probability,
                "issue": "score probability distribution does not sum to 1",
                "sum": total_distribution_probability,
            })

        if best_of == 3:
            if expected_sets < 2.0 or expected_sets > 3.0:
                warnings.append({
                    "case": row.get("case"),
                    "probability": probability,
                    "issue": "BO3 expected sets outside logical range",
                    "expected_sets": expected_sets,
                })

        if best_of == 5:
            if expected_sets < 3.0 or expected_sets > 5.0:
                warnings.append({
                    "case": row.get("case"),
                    "probability": probability,
                    "issue": "BO5 expected sets outside logical range",
                    "expected_sets": expected_sets,
                })

        if sets_probability < 0 or sets_probability > 1:
            warnings.append({
                "case": row.get("case"),
                "probability": probability,
                "issue": "sets probability outside 0-1 range",
                "sets_probability": sets_probability,
            })

    return warnings


def build_diagnostics():
    diagnostics = {
        "generated_at": datetime.now(
            timezone.utc
        ).isoformat(),

        "description": (
            "Internal diagnostics for BackstageTalks Statistic Model. "
            "Tests BO3 and BO5 set-by-set model behavior across selected "
            "match win probabilities."
        ),

        "notes": [
            "Set model is derived from match win probability and best_of.",
            "Expected games and games pick are compatibility placeholders only.",
            "Game/serve model is not yet implemented.",
            "Displayed website metrics should focus on expected sets, deciding-set probability and most likely score.",
        ],

        "cases": [],
        "warnings": [],
    }

    all_rows = []

    for case in TEST_CASES:
        case_rows = []

        for probability in TEST_PROBABILITIES:
            row = build_case_result(
                case,
                probability,
            )

            case_rows.append(row)
            all_rows.append(row)

        diagnostics["cases"].append({
            "label": case.get("label"),
            "tournament": case.get("tournament"),
            "best_of": case.get("best_of"),
            "rows": case_rows,
        })

    diagnostics["warnings"] = sanity_checks(
        all_rows,
    )

    return diagnostics


def save_diagnostics(diagnostics):
    os.makedirs(
        "public",
        exist_ok=True,
    )

    with open(
        OUTPUT_PATH,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            diagnostics,
            file,
            indent=2,
            ensure_ascii=False,
        )


def print_diagnostics(diagnostics):
    for case in diagnostics.get("cases", []):
        print_header(
            case.get("label")
        )

        print_table(
            case.get("rows", [])
        )

        rows = case.get("rows", [])

        if rows:
            print_score_distribution(
                rows[0]
            )

            print_score_distribution(
                rows[-1]
            )

    warnings = diagnostics.get("warnings", [])

    print_header("SANITY CHECKS")

    if not warnings:
        print("OK - no warnings.")
    else:
        print("WARNINGS FOUND:")

        for warning in warnings:
            print(
                json.dumps(
                    warning,
                    ensure_ascii=False,
                )
            )


def run():
    diagnostics = build_diagnostics()

    print_diagnostics(
        diagnostics,
    )

    save_diagnostics(
        diagnostics,
    )

    print("")
    print("MODEL DIAGNOSTICS SAVED:", OUTPUT_PATH)


if __name__ == "__main__":
    run()
```


## FILE: odds_api.py

```
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Sequence, Tuple

from tennisapi_client import TennisApiClient, normalize_winning_odds
from tennisapi_cache import get_daily_odds_items, betting_day_datetime


logger = logging.getLogger(__name__)

_ODDS_CACHE: Optional[List[Dict[str, Any]]] = None


# ----------------------------------------------------------------------
# Public API expected by prediction_engine_core.py
# ----------------------------------------------------------------------


def fetch_odds(*args: Any, **kwargs: Any) -> List[Dict[str, Any]]:
    """
    TennisApi-primary odds fetcher.

    Existing project call pattern:
        odds_matches = fetch_odds()
        odds_data = find_match_odds(odds_list, match)

    Source priority:
        1) TennisApi daily odds batch cache
        2) TennisApi event winning odds fallback inside tennisapi_cache
        3) empty list / no odds
    """
    global _ODDS_CACHE

    if kwargs.get("force_refresh"):
        _ODDS_CACHE = None

    if _ODDS_CACHE is not None:
        return _ODDS_CACHE

    explicit_match_id = _extract_match_id_from_args_kwargs(args, kwargs)
    if explicit_match_id:
        item = get_tennisapi_odds(int(explicit_match_id))
        _ODDS_CACHE = [_to_legacy_odds_item(item)] if item else []
        return _ODDS_CACHE

    odds_items: List[Dict[str, Any]] = []
    days_ahead = _parse_int_env("ODDS_SCAN_DAYS_AHEAD", 1)
    days_back = _parse_int_env("ODDS_SCAN_DAYS_BACK", 0)
    force_refresh = bool(kwargs.get("force_refresh", False))

    today = betting_day_datetime()
    for delta in range(-days_back, days_ahead + 1):
        target_date = today + timedelta(days=delta)
        try:
            daily_items = get_daily_odds_items(
                target_date=target_date,
                force_refresh=force_refresh,
                include_event_fallback=True,
            )
            odds_items.extend(daily_items)
        except Exception as exc:
            logger.warning("TennisApi daily odds items failed date=%s error=%s", target_date.date(), exc)

    # Deduplicate by event id.
    seen = set()
    unique_items = []
    for item in odds_items:
        key = item.get("event_id") or item.get("match_id") or item.get("match")
        if key in seen:
            continue
        seen.add(key)
        unique_items.append(item)

    _ODDS_CACHE = unique_items
    print("TennisApi odds fetched:", len(_ODDS_CACHE))
    logger.info("TennisApi odds fetched: %s", len(_ODDS_CACHE))
    return _ODDS_CACHE


async def fetch_odds_async(*args: Any, **kwargs: Any) -> List[Dict[str, Any]]:
    return fetch_odds(*args, **kwargs)


def find_match_odds(*args: Any, **kwargs: Any) -> Optional[Dict[str, Any]]:
    """
    Backward-compatible matcher.

    Supported patterns:
        find_match_odds(match)
        find_match_odds(odds_list, match)
        find_match_odds(player1, player2)
        find_match_odds(player1, player2, odds_list)
        find_match_odds(odds_list, player1, player2)
    """
    odds_list, match, player1, player2 = _parse_find_match_odds_args(args, kwargs)

    if not odds_list:
        odds_list = fetch_odds()

    match_id = None
    if isinstance(match, dict):
        match_id = match.get("match_id") or match.get("event_id") or match.get("id")
        player1 = player1 or match.get("player1") or match.get("pick") or match.get("home") or match.get("home_team")
        player2 = player2 or match.get("player2") or match.get("opponent") or match.get("away") or match.get("away_team")

    if match_id:
        for item in odds_list:
            item_id = item.get("match_id") or item.get("event_id") or item.get("id")
            if str(item_id) == str(match_id):
                return dict(item)

        direct = get_tennisapi_odds(int(match_id))
        if direct:
            item = _to_legacy_odds_item(direct)
            if player1:
                item["player1"] = player1
            if player2:
                item["player2"] = player2
            return item

    return _find_in_legacy_odds_list(odds_list, player1, player2)


# ----------------------------------------------------------------------
# TennisApi event odds fallback
# ----------------------------------------------------------------------


def get_tennisapi_odds(match_id: int) -> Optional[Dict[str, Any]]:
    try:
        client = TennisApiClient()
        payload = client.get_match_winning_odds(match_id)
        normalized = normalize_winning_odds(payload)
        if normalized:
            normalized["match_id"] = match_id
            return normalized
    except Exception as exc:
        logger.info("TennisApi odds failed. match_id=%s error=%s", match_id, exc)
    return None


# Compatibility aliases

def get_match_odds(match: Dict[str, Any], prefer_tennisapi: bool = True) -> Optional[Dict[str, Any]]:
    legacy = find_match_odds(match)
    if legacy:
        return _legacy_to_normalized(legacy)
    return None


def enrich_match_with_odds(match: Dict[str, Any]) -> Dict[str, Any]:
    enriched = dict(match)
    odds = get_match_odds(match)
    if not odds:
        enriched["odds_status"] = "NO_ODDS"
        enriched["odds_source"] = None
        enriched["p1_odds"] = None
        enriched["p2_odds"] = None
        enriched["odds"] = None
        return enriched

    p1 = odds.get("odds_player1") or odds.get("p1_odds") or odds.get("home_odds")
    p2 = odds.get("odds_player2") or odds.get("p2_odds") or odds.get("away_odds")
    enriched["odds_status"] = "OK"
    enriched["odds_source"] = odds.get("odds_source") or odds.get("source")
    enriched["odds_player1"] = p1
    enriched["odds_player2"] = p2
    enriched["p1_odds"] = p1
    enriched["p2_odds"] = p2
    enriched["home_odds"] = p1
    enriched["away_odds"] = p2
    enriched["odds"] = p1
    enriched["bookmaker"] = odds.get("bookmaker")
    enriched["odds_raw"] = odds.get("raw")
    return enriched


def get_odds(match: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return get_match_odds(match)


def get_odds_for_match(match: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return get_match_odds(match)


def get_match_odds_for_event(match_id: int) -> Optional[Dict[str, Any]]:
    return get_tennisapi_odds(match_id)


# ----------------------------------------------------------------------
# Internal helpers
# ----------------------------------------------------------------------


def _parse_int_env(name: str, default: int) -> int:
    import os
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def _extract_match_id_from_args_kwargs(args: Sequence[Any], kwargs: Dict[str, Any]) -> Optional[int]:
    for key in ("match_id", "event_id", "id"):
        value = kwargs.get(key)
        if value:
            return int(value)
    for arg in args:
        if isinstance(arg, dict):
            value = arg.get("match_id") or arg.get("event_id") or arg.get("id")
            if value:
                return int(value)
        elif isinstance(arg, int):
            return int(arg)
        elif isinstance(arg, str) and arg.isdigit():
            return int(arg)
    return None


def _parse_find_match_odds_args(
    args: Sequence[Any],
    kwargs: Dict[str, Any],
) -> Tuple[List[Dict[str, Any]], Optional[Dict[str, Any]], Optional[str], Optional[str]]:
    odds_list: List[Dict[str, Any]] = []
    match: Optional[Dict[str, Any]] = None
    player1: Optional[str] = kwargs.get("player1") or kwargs.get("home_player")
    player2: Optional[str] = kwargs.get("player2") or kwargs.get("away_player")

    if isinstance(kwargs.get("match"), dict):
        match = kwargs["match"]
    if isinstance(kwargs.get("odds_list"), list):
        odds_list = kwargs["odds_list"]
    elif isinstance(kwargs.get("odds"), list):
        odds_list = kwargs["odds"]

    non_list_positional: List[Any] = []
    for arg in args:
        if isinstance(arg, list):
            odds_list = arg
        else:
            non_list_positional.append(arg)

    positional = non_list_positional
    if positional and isinstance(positional[0], dict):
        match = positional.pop(0)
    if positional and player1 is None:
        player1 = str(positional.pop(0))
    if positional and player2 is None:
        player2 = str(positional.pop(0))
    return odds_list, match, player1, player2


def _to_legacy_odds_item(odds: Dict[str, Any]) -> Dict[str, Any]:
    p1 = odds.get("p1_odds") or odds.get("home_odds") or odds.get("odds_player1")
    p2 = odds.get("p2_odds") or odds.get("away_odds") or odds.get("odds_player2")
    return {
        "source": odds.get("source", "TennisApi"),
        "odds_source": odds.get("source", "TennisApi"),
        "bookmaker": odds.get("bookmaker") or "TennisApi",
        "match_id": odds.get("match_id"),
        "event_id": odds.get("match_id"),
        "home_odds": p1,
        "away_odds": p2,
        "p1_odds": p1,
        "p2_odds": p2,
        "odds_player1": p1,
        "odds_player2": p2,
        "odds": p1,
        "odds1": p1,
        "odds2": p2,
        "price1": p1,
        "price2": p2,
        "raw": odds.get("raw", odds),
    }


def _legacy_to_normalized(legacy: Dict[str, Any]) -> Dict[str, Any]:
    p1 = legacy.get("odds_player1") or legacy.get("p1_odds") or legacy.get("home_odds") or legacy.get("odds") or legacy.get("odds1") or legacy.get("price1")
    p2 = legacy.get("odds_player2") or legacy.get("p2_odds") or legacy.get("away_odds") or legacy.get("odds2") or legacy.get("price2")
    return {
        "source": legacy.get("source") or legacy.get("odds_source") or "LegacyOdds",
        "odds_source": legacy.get("odds_source") or legacy.get("source") or "LegacyOdds",
        "match_id": legacy.get("match_id") or legacy.get("event_id"),
        "home_odds": _to_float_or_none(p1),
        "away_odds": _to_float_or_none(p2),
        "p1_odds": _to_float_or_none(p1),
        "p2_odds": _to_float_or_none(p2),
        "odds_player1": _to_float_or_none(p1),
        "odds_player2": _to_float_or_none(p2),
        "bookmaker": legacy.get("bookmaker"),
        "raw": legacy.get("raw", legacy),
    }


def _find_in_legacy_odds_list(
    odds_list: List[Dict[str, Any]],
    player1: Optional[str],
    player2: Optional[str],
) -> Optional[Dict[str, Any]]:
    if not player1 or not player2:
        return None
    requested_p1 = _normalize_name(player1)
    requested_p2 = _normalize_name(player2)
    for item in odds_list:
        item_p1 = item.get("player1") or item.get("home_team") or item.get("home")
        item_p2 = item.get("player2") or item.get("away_team") or item.get("away")
        norm_item_p1 = _normalize_name(item_p1)
        norm_item_p2 = _normalize_name(item_p2)
        direct = _names_match_normalized(requested_p1, norm_item_p1) and _names_match_normalized(requested_p2, norm_item_p2)
        reversed_match = _names_match_normalized(requested_p1, norm_item_p2) and _names_match_normalized(requested_p2, norm_item_p1)
        if direct:
            return dict(item)
        if reversed_match:
            swapped = dict(item)
            p1 = item.get("odds_player2") or item.get("p2_odds") or item.get("away_odds") or item.get("odds2") or item.get("price2")
            p2 = item.get("odds_player1") or item.get("p1_odds") or item.get("home_odds") or item.get("odds1") or item.get("price1")
            swapped["player1"] = player1
            swapped["player2"] = player2
            swapped["odds_player1"] = p1
            swapped["odds_player2"] = p2
            swapped["p1_odds"] = p1
            swapped["p2_odds"] = p2
            swapped["home_odds"] = p1
            swapped["away_odds"] = p2
            swapped["odds"] = p1
            swapped["odds1"] = p1
            swapped["odds2"] = p2
            return swapped
    return None


def _normalize_name(name: Any) -> str:
    return (
        str(name or "")
        .lower()
        .replace(".", "")
        .replace("-", " ")
        .replace("_", " ")
        .strip()
    )


def _name_keys(normalized: str) -> set:
    parts = normalized.split()
    keys = set()
    if normalized:
        keys.add(normalized)
    if parts:
        keys.add(parts[-1])
    if len(parts) >= 2:
        keys.add(" ".join(parts[-2:]))
        keys.add(f"{parts[0][0]} {parts[-1]}")
    return keys


def _names_match_normalized(a: str, b: str) -> bool:
    if not a or not b:
        return False
    return bool(_name_keys(a).intersection(_name_keys(b)))


def _to_float_or_none(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    odds = fetch_odds(force_refresh=True)
    print(f"Odds found: {len(odds)}")
    for item in odds[:20]:
        print(item.get("match_id"), item.get("player1"), "vs", item.get("player2"), item.get("odds_player1"), item.get("odds_player2"))
```


## FILE: play_history.py

```
import json
import os
import re
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


BRATISLAVA_TZ = ZoneInfo("Europe/Bratislava")

LEGACY_PLAY_HISTORY_DIR = "data/play_history"

PICK_HISTORY_ROOT = "data/pick_history"
ALL_PICK_HISTORY_DIR = "data/pick_history/all"
TOP5_PICK_HISTORY_DIR = "data/pick_history/top5"

LATEST_ALL_PUBLIC_PATH = "public/play_history_all_latest.json"
LATEST_TOP5_PUBLIC_PATH = "public/play_history_top5_latest.json"
LATEST_LEGACY_PUBLIC_PATH = "public/play_history_latest.json"


def ensure_dirs():
    os.makedirs(LEGACY_PLAY_HISTORY_DIR, exist_ok=True)
    os.makedirs(ALL_PICK_HISTORY_DIR, exist_ok=True)
    os.makedirs(TOP5_PICK_HISTORY_DIR, exist_ok=True)
    os.makedirs("public", exist_ok=True)


def now_utc_iso():
    return datetime.now(timezone.utc).isoformat()


def betting_day(date_time=None):
    """
    Betting day window:
    Europe/Bratislava 06:00 -> next day 06:00

    If local time is before 06:00, the betting day is previous calendar day.
    """
    if date_time is None:
        date_time = datetime.now(BRATISLAVA_TZ)

    if date_time.tzinfo is None:
        date_time = date_time.replace(tzinfo=BRATISLAVA_TZ)
    else:
        date_time = date_time.astimezone(BRATISLAVA_TZ)

    if date_time.hour < 6:
        date_time = date_time - timedelta(days=1)

    return date_time.strftime("%Y-%m-%d")


def today_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def normalize_text(value):
    if value is None:
        return ""

    text = str(value).lower().strip()
    text = re.sub(r"[^a-z0-9à-ž\s\-']", " ", text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def make_pick_id(date, prediction):
    match = normalize_text(prediction.get("match"))
    pick = normalize_text(prediction.get("pick"))
    opponent = normalize_text(prediction.get("opponent"))

    base = f"{date}::{match}::{pick}::{opponent}"

    return re.sub(r"[^a-z0-9]+", "_", base).strip("_")


def safe_float(value):
    try:
        if value in [None, "", "NA", "NaN"]:
            return None

        return float(value)

    except Exception:
        return None


def load_json(path, default):
    try:
        if not os.path.exists(path):
            return default

        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    except Exception:
        return default


def save_json(path, data):
    directory = os.path.dirname(path)

    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def all_snapshot_path(date):
    return os.path.join(ALL_PICK_HISTORY_DIR, f"{date}.json")


def top5_snapshot_path(date):
    return os.path.join(TOP5_PICK_HISTORY_DIR, f"{date}.json")


def legacy_history_path(date):
    return os.path.join(LEGACY_PLAY_HISTORY_DIR, f"{date}.json")


def build_snapshot_record(date, prediction, rank, dataset):
    pick_id = make_pick_id(date, prediction)

    odds = safe_float(prediction.get("odds"))
    probability = safe_float(prediction.get("probability"))

    return {
        "id": pick_id,
        "dataset": dataset,
        "date": date,
        "created_at": now_utc_iso(),

        "rank": rank,

        "match": prediction.get("match"),
        "pick": prediction.get("pick"),
        "opponent": prediction.get("opponent"),

        "probability": probability,
        "odds": odds,

        "time": prediction.get("time"),

        "bookmaker": prediction.get("bookmaker"),
        "odds_source": prediction.get("odds_source"),

        "tournament": prediction.get("tournament"),
        "gender": prediction.get("gender"),
        "surface": prediction.get("surface"),
        "best_of": prediction.get("best_of"),

        "expected_sets": prediction.get("expected_sets"),
        "sets_probability": prediction.get("sets_probability"),
        "sets_probability_label": prediction.get("sets_probability_label"),
        "set_win_probability": prediction.get("set_win_probability"),
        "most_likely_score": prediction.get("most_likely_score"),
        "most_likely_score_probability": prediction.get("most_likely_score_probability"),
        "score_probabilities": prediction.get("score_probabilities"),

        "bet_tag": prediction.get("bet_tag"),
        "top_mode": prediction.get("top_mode"),
        "top_reason": prediction.get("top_reason"),

        "result_status": prediction.get("result_status") or "PENDING",
        "winner": prediction.get("winner"),
        "score": prediction.get("score"),
        "units": safe_float(prediction.get("units")) or 0.0,
        "resolved_at": prediction.get("resolved_at"),
        "result_source": prediction.get("result_source"),
        "result_match_score": prediction.get("result_match_score"),
    }


def build_snapshot(date, predictions, dataset):
    if predictions is None:
        predictions = []

    output = []

    for rank, prediction in enumerate(predictions, start=1):
        if not isinstance(prediction, dict):
            continue

        if not prediction.get("pick"):
            continue

        if not prediction.get("match"):
            continue

        output.append(
            build_snapshot_record(
                date=date,
                prediction=prediction,
                rank=rank,
                dataset=dataset,
            )
        )

    output.sort(
        key=lambda item: (
            item.get("rank") or 9999,
            item.get("match") or "",
        )
    )

    return output


def save_snapshot(date, predictions, dataset, path, latest_public_path, overwrite=False):
    """
    Daily snapshot is immutable.

    Default behavior:
    - if snapshot file already exists and is non-empty, keep it unchanged
    - do not overwrite odds, probability, rank, pick, model fields during the day

    overwrite=True is intentionally available only for manual recovery.
    """
    ensure_dirs()

    if date is None:
        date = betting_day()

    existing = load_json(path, None)

    if (
        existing is not None
        and isinstance(existing, list)
        and len(existing) > 0
        and not overwrite
    ):
        save_json(
            latest_public_path,
            {
                "date": date,
                "dataset": dataset,
                "count": len(existing),
                "immutable_snapshot": True,
                "items": existing,
            },
        )

        print(
            "SNAPSHOT EXISTS - KEEPING IMMUTABLE:",
            dataset,
            path,
            len(existing),
        )

        return existing

    output = build_snapshot(
        date=date,
        predictions=predictions,
        dataset=dataset,
    )

    save_json(path, output)

    save_json(
        latest_public_path,
        {
            "date": date,
            "dataset": dataset,
            "count": len(output),
            "immutable_snapshot": True,
            "items": output,
        },
    )

    print(
        "SNAPSHOT SAVED:",
        dataset,
        path,
        len(output),
    )

    return output


def save_all_snapshot(date=None, all_predictions=None, overwrite=False):
    if date is None:
        date = betting_day()

    return save_snapshot(
        date=date,
        predictions=all_predictions or [],
        dataset="all",
        path=all_snapshot_path(date),
        latest_public_path=LATEST_ALL_PUBLIC_PATH,
        overwrite=overwrite,
    )


def save_top5_snapshot(date=None, top5_predictions=None, overwrite=False):
    if date is None:
        date = betting_day()

    return save_snapshot(
        date=date,
        predictions=top5_predictions or [],
        dataset="top5",
        path=top5_snapshot_path(date),
        latest_public_path=LATEST_TOP5_PUBLIC_PATH,
        overwrite=overwrite,
    )


def save_play_candidates(date=None, predictions=None, overwrite=False):
    """
    Backward-compatible wrapper.

    Old code called:
        save_play_candidates(today, all_predictions)

    New architecture stores this as ALL snapshot:
        data/pick_history/all/YYYY-MM-DD.json

    It also writes legacy data/play_history/YYYY-MM-DD.json only if missing,
    so older local scripts do not immediately break.
    """
    if date is None:
        date = betting_day()

    output = save_all_snapshot(
        date=date,
        all_predictions=predictions or [],
        overwrite=overwrite,
    )

    legacy_path = legacy_history_path(date)

    if not os.path.exists(legacy_path):
        save_json(legacy_path, output)

    save_json(
        LATEST_LEGACY_PUBLIC_PATH,
        {
            "date": date,
            "dataset": "all",
            "count": len(output),
            "items": output,
        },
    )

    return output


def load_all_snapshot_for_date(date):
    return load_json(all_snapshot_path(date), [])


def load_top5_snapshot_for_date(date):
    return load_json(top5_snapshot_path(date), [])


def load_play_history_for_date(date):
    data = load_all_snapshot_for_date(date)

    if data:
        return data

    return load_json(legacy_history_path(date), [])


def load_history_dir(directory):
    ensure_dirs()

    items = []

    if not os.path.exists(directory):
        return items

    for filename in sorted(os.listdir(directory)):
        if not filename.endswith(".json"):
            continue

        path = os.path.join(directory, filename)
        data = load_json(path, [])

        if isinstance(data, list):
            items.extend(data)

    return items


def load_all_pick_history():
    return load_history_dir(ALL_PICK_HISTORY_DIR)


def load_top5_pick_history():
    return load_history_dir(TOP5_PICK_HISTORY_DIR)


def load_all_play_history():
    """
    Backward-compatible loader.

    Prefer new ALL pick history.
    Fall back to old data/play_history if new folder is empty.
    """
    items = load_all_pick_history()

    if items:
        return items

    return load_history_dir(LEGACY_PLAY_HISTORY_DIR)
```


## FILE: player_matcher.py

```
import re
import unicodedata


SUFFIX_TOKENS = {
    "jr",
    "sr",
    "junior",
    "senior",
    "ii",
    "iii",
    "iv",
}


def normalize_name(name):
    if not name:
        return ""

    text = str(name)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))

    text = text.lower().strip()
    text = text.replace("-", " ")
    text = text.replace(".", " ")
    text = text.replace(",", " ")

    text = re.sub(r"[^a-z0-9\s']", " ", text)
    text = re.sub(r"\s+", " ", text)

    tokens = [
        token for token in text.split()
        if token not in SUFFIX_TOKENS
    ]

    return " ".join(tokens).strip()


def name_tokens(name):
    text = normalize_name(name)
    if not text:
        return []
    return text.split()


def last_name(name):
    tokens = name_tokens(name)
    if not tokens:
        return ""
    return tokens[-1]


def first_name(name):
    tokens = name_tokens(name)
    if not tokens:
        return ""
    return tokens[0]


def token_overlap_score(a, b):
    a_tokens = set(name_tokens(a))
    b_tokens = set(name_tokens(b))

    if not a_tokens or not b_tokens:
        return 0.0

    overlap = len(a_tokens.intersection(b_tokens))
    return overlap / max(len(a_tokens), len(b_tokens))


def initial_match_score(a, b):
    a_first = first_name(a)
    b_first = first_name(b)

    if not a_first or not b_first:
        return 0.0

    if a_first == b_first:
        return 1.0

    if a_first[0] == b_first[0]:
        return 0.65

    return 0.0


def compact_name_score(a, b):
    a_tokens = name_tokens(a)
    b_tokens = name_tokens(b)

    if not a_tokens or not b_tokens:
        return 0.0

    if last_name(a) != last_name(b):
        return 0.0

    a_initials = "".join(t[0] for t in a_tokens[:-1] if t)
    b_initials = "".join(t[0] for t in b_tokens[:-1] if t)

    if not a_initials or not b_initials:
        return 0.0

    shorter = min(a_initials, b_initials, key=len)
    longer = max(a_initials, b_initials, key=len)

    if longer.startswith(shorter):
        return 0.75

    return 0.0


def player_name_match_score(query_name, candidate_name):
    q = normalize_name(query_name)
    c = normalize_name(candidate_name)

    if not q or not c:
        return 0.0, "empty"

    if q == c:
        return 1.0, "exact"

    q_last = last_name(q)
    c_last = last_name(c)

    token_score = token_overlap_score(q, c)
    initial_score = initial_match_score(q, c)
    compact_score = compact_name_score(q, c)

    score = token_score * 0.55

    if q_last == c_last:
        score += 0.30

    score += initial_score * 0.10
    score += compact_score * 0.05

    if q_last != c_last:
        score *= 0.45

    score = max(0.0, min(1.0, score))

    return round(score, 3), "fuzzy"


def best_player_match(query_name, candidate_names, auto_threshold=0.60):
    best_key = None
    best_score = 0.0

    query_last = last_name(query_name)

    for candidate in candidate_names:
        score, _ = player_name_match_score(query_name, candidate)

        if score > best_score:
            best_key = candidate
            best_score = score

    if best_key is None:
        return None, 0.0, "none"

    candidate_last = last_name(best_key)

    # HARD FILTER – surname musí sedieť
    if query_last != candidate_last:
        return None, best_score, "rejected_lastname"

    if best_score >= auto_threshold:
        return best_key, best_score, "accepted"

    return None, best_score, "low_score"
```


## FILE: prediction_engine_all.py

```
from prediction_engine_core import (
    TOP_N,
    MIN_ODDS,
    MIN_TOP_PROBABILITY,
    build_all_predictions,
    get_top_predictions,
    get_daily_predictions,
)


def get_all_predictions():
    return build_all_predictions()
```


## FILE: prediction_engine_core.py

```
from datetime import datetime
from zoneinfo import ZoneInfo

from fetch_matches import get_today_matches
from stats_engine import get_stats_context
from elo_engine import load, predict
from odds_api import fetch_odds, find_match_odds
from form_engine import load_form_store, get_player_form, calculate_form_adjustment
from src.bst_ai.service import build_bst_ai_comparison
from src.marq_ai import build_marq_from_match
from mcp_module import build_mcp_player_stats, mcp_adjustment
from tennisapi_set_markets import get_set_markets
from sets_model import build_market_aware_sets


TOP_N = 5
MIN_ODDS = 1.50
MIN_TOP_PROBABILITY = 0.0
LOCAL_TZ = ZoneInfo("Europe/Bratislava")


def clamp(value, low, high):
    return max(low, min(high, value))


def safe_float(value):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def format_match_time(match):
    start_value = match.get("match_start") or match.get("start_time") or match.get("commence_time")
    if start_value:
        try:
            text = str(start_value)
            if text.endswith("Z"):
                text = text.replace("Z", "+00:00")
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=ZoneInfo("UTC"))
            return dt.astimezone(LOCAL_TZ).strftime("%H:%M")
        except Exception:
            pass
    return "TBD"


def format_match_date(match):
    start_value = match.get("match_start") or match.get("start_time") or match.get("commence_time")
    if not start_value:
        return None
    try:
        text = str(start_value)
        if text.endswith("Z"):
            text = text.replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=ZoneInfo("UTC"))
        return dt.astimezone(LOCAL_TZ).strftime("%Y-%m-%d")
    except Exception:
        text = str(start_value)
        if len(text) >= 10:
            return text[:10]
    return None


def normalize_match(match):
    match_id = match.get("match_id") or match.get("event_id") or match.get("id")
    return {
        "match_id": match_id,
        "event_id": match_id,
        "id": match_id,
        "player1": match.get("player1"),
        "player2": match.get("player2"),
        "surface": match.get("surface"),
        "tournament": match.get("tournament"),
        "category": match.get("category"),
        "gender": match.get("gender"),
        "best_of": match.get("best_of"),
        "match_start": match.get("match_start"),
        "start_time": match.get("start_time"),
        "commence_time": match.get("commence_time"),
        "time": format_match_time(match),
    }


def infer_surface(surface_map, player1, player2, match):
    if match.get("surface"):
        return match.get("surface")
    return surface_map.get(f"{player1}::{player2}") or "Hard"


def build_safe_marq_ai(match, player1, player2, pick, odds_player1=None, odds_player2=None):
    match_date = format_match_date(match)
    if not match_date:
        print("MARQ DEBUG: match_date missing", player1, "vs", player2)
        return None
    try:
        return build_marq_from_match(
            player1=player1,
            player2=player2,
            date_only=match_date,
            pick=pick,
            odds_player1=odds_player1,
            odds_player2=odds_player2,
        )
    except Exception as exc:
        print("MARQ AI ERROR:", player1, "vs", player2, "pick:", pick, "date:", match_date, str(exc))
        return None


def build_prediction_record(match, surface, elo_prediction, odds_data, form_store, mcp_stats):
    player1 = match["player1"]
    player2 = match["player2"]
    odds_data = odds_data or {}

    prob1 = safe_float(elo_prediction.get("probability_player1"))
    prob2 = safe_float(elo_prediction.get("probability_player2"))
    if prob1 is None:
        prob1 = 0.5
    if prob2 is None:
        prob2 = 0.5

    odds1 = safe_float(odds_data.get("odds_player1") or odds_data.get("p1_odds") or odds_data.get("home_odds") or odds_data.get("odds1") or odds_data.get("price1"))
    odds2 = safe_float(odds_data.get("odds_player2") or odds_data.get("p2_odds") or odds_data.get("away_odds") or odds_data.get("odds2") or odds_data.get("price2"))

    form1 = get_player_form(form_store, player1, surface)
    form2 = get_player_form(form_store, player2, surface)

    if prob1 >= prob2:
        pick = player1
        opponent = player2
        base_probability = prob1
        pick_odds = odds1
    else:
        pick = player2
        opponent = player1
        base_probability = prob2
        pick_odds = odds2

    form_adjustment = calculate_form_adjustment(pick_form=form1, opponent_form=form2)
    final_probability = base_probability + form_adjustment["total_adjustment"]
    final_probability += mcp_adjustment(pick, mcp_stats)
    final_probability -= mcp_adjustment(opponent, mcp_stats)
    final_probability = clamp(final_probability, 0.15, 0.85)

    bst_ai = build_bst_ai_comparison(
        player1=player1,
        player2=player2,
        pick=pick,
        surface=surface,
        corq_probability=final_probability,
        tour=match.get("gender"),
    )

    marq_ai = build_safe_marq_ai(match=match, player1=player1, player2=player2, pick=pick, odds_player1=odds1, odds_player2=odds2)
    if not isinstance(marq_ai, dict):
        marq_ai = {}

    set_markets = {}
    try:
        event_id = match.get("event_id") or match.get("match_id") or match.get("id")
        if event_id:
            set_markets = get_set_markets(int(event_id))
    except Exception as exc:
        print("SETS MARKET ERROR:", player1, "vs", player2, str(exc))
        set_markets = {}

    sets_info = build_market_aware_sets(
        match=match,
        elo_prediction=elo_prediction,
        odds_data=odds_data,
        set_markets=set_markets,
    )

    # Keep tag simple; TOP5 selection is handled in prediction_engine_top.py.
    bet_tag = "INFO ONLY"

    return {
        "match_id": match.get("match_id"),
        "event_id": match.get("event_id"),
        "match": f"{player1} vs {player2}",
        "pick": pick,
        "opponent": opponent,
        "player1": player1,
        "player2": player2,
        "tournament": match.get("tournament"),
        "gender": match.get("gender"),
        "best_of": match.get("best_of") or 3,
        "surface": surface,
        "probability": round(final_probability, 3),
        "corq_ai_probability": bst_ai.get("corq_ai_probability"),
        "bst_ai_probability": bst_ai.get("bst_ai_probability"),
        "ai_match": bst_ai.get("ai_match"),
        "ai_gap": bst_ai.get("ai_gap"),
        "ai_signed_gap": bst_ai.get("ai_signed_gap"),
        "ai_lean": bst_ai.get("ai_lean"),
        "ai_direction_match": bst_ai.get("ai_direction_match"),
        "ai_match_color": bst_ai.get("ai_match_color"),
        "bst_ai_status": bst_ai.get("bst_ai_status"),
        "bst_ai_reason": bst_ai.get("bst_ai_reason"),
        "bst_ai_rating_type": bst_ai.get("bst_ai_rating_type"),
        "bst_player1_found": bst_ai.get("bst_player1_found"),
        "bst_player2_found": bst_ai.get("bst_player2_found"),
        "marq_ai_score": marq_ai.get("marq_ai_score"),
        "marq_ai_signal": marq_ai.get("marq_ai_signal"),
        "marq_ai_direction": marq_ai.get("marq_ai_direction"),
        "marq_ai_strength": marq_ai.get("marq_ai_strength"),
        "marq_ai_consistency": marq_ai.get("marq_ai_consistency"),
        "marq_ai_reason": marq_ai.get("marq_ai_reason"),
        "marq_event_id": marq_ai.get("marq_event_id"),
        "marq_outcome_key": marq_ai.get("marq_outcome_key"),
        "marq_source": marq_ai.get("marq_source"),
        "marq_market_name": marq_ai.get("marq_market_name"),
        "marq_opening": marq_ai.get("marq_opening"),
        "marq_latest": marq_ai.get("marq_latest"),
        "marq_market_move_pct": marq_ai.get("marq_market_move_pct"),
        "marq_probability_change_pp": marq_ai.get("marq_probability_change_pp"),
        "marq_opponent_move_pct": marq_ai.get("marq_opponent_move_pct"),
        "base_probability": round(base_probability, 3),
        "odds": pick_odds,
        "odds_player1": odds1,
        "odds_player2": odds2,
        "time": match.get("time"),
        "match_start": match.get("match_start"),
        "bookmaker": odds_data.get("bookmaker"),
        "odds_source": odds_data.get("odds_source") or odds_data.get("source"),
        "expected_sets": sets_info.get("expected_sets"),
        "sets_probability": sets_info.get("sets_probability"),
        "sets_probability_label": sets_info.get("sets_probability_label"),
        "set_win_probability": None,
        "most_likely_score": sets_info.get("most_likely_score"),
        "most_likely_score_probability": sets_info.get("most_likely_score_probability"),
        "score_probabilities": sets_info.get("score_probabilities"),
        "expected_games": sets_info.get("expected_games"),
        "games_pick": sets_info.get("games_pick"),
        "games_line": sets_info.get("games_line"),
        "games_over_probability": sets_info.get("games_over_probability"),
        "tie_break_probability": sets_info.get("tie_break_probability"),
        "sets_model_source": sets_info.get("sets_model_source"),
        "bet_tag": bet_tag,
        "form_adjustment": form_adjustment.get("total_adjustment"),
        "top_mode": None,
        "top_reason": None,
    }


def build_all_predictions():
    raw_matches = get_today_matches()
    matches = [normalize_match(match) for match in raw_matches]
    matches = [match for match in matches if match["player1"] and match["player2"]]

    players = []
    for match in matches:
        players.append(match["player1"])
        players.append(match["player2"])

    try:
        stats_map, surface_map = get_stats_context(players, matches)
    except Exception as exc:
        print("STATS CONTEXT ERROR:", str(exc))
        surface_map = {}

    elo_store = load()
    form_store = load_form_store()
    odds_matches = fetch_odds()
    print("PREDICTION ODDS LIST COUNT:", len(odds_matches) if isinstance(odds_matches, list) else "invalid")
    mcp_stats = build_mcp_player_stats()

    all_predictions = []
    odds_hit_count = 0
    odds_miss_count = 0

    for match in matches:
        surface = infer_surface(surface_map, match["player1"], match["player2"], match)
        elo_prediction = predict(match["player1"], match["player2"], surface, elo_store)
        odds_data = find_match_odds(odds_matches, match)

        if odds_data:
            odds_hit_count += 1
        else:
            odds_miss_count += 1
            if odds_miss_count <= 20:
                print("ODDS MATCH MISS:", match.get("player1"), "vs", match.get("player2"), "match_id:", match.get("match_id"))

        prediction = build_prediction_record(match, surface, elo_prediction, odds_data, form_store, mcp_stats)
        all_predictions.append(prediction)

    print("ODDS MATCH HITS:", odds_hit_count)
    print("ODDS MATCH MISSES:", odds_miss_count)

    all_predictions.sort(key=lambda item: item.get("probability", 0), reverse=True)
    return all_predictions


def get_top_predictions(all_predictions=None):
    if all_predictions is None:
        all_predictions = build_all_predictions()
    eligible = [prediction for prediction in all_predictions if prediction.get("odds") is not None and prediction.get("odds") > MIN_ODDS]
    eligible.sort(key=lambda item: item.get("probability", 0), reverse=True)
    return eligible[:TOP_N]


def get_daily_predictions():
    return get_top_predictions()
```


## FILE: prediction_engine_top.py

```
import os
from typing import Any, Dict, List, Optional

from prediction_engine_core import build_all_predictions as build_core_all_predictions


TOP_N = 5


def safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return default


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except Exception:
        return default


def normalize_status(value: Any) -> str:
    return str(value or "").upper().strip()


def has_odds(prediction: Dict[str, Any]) -> bool:
    odds = safe_float(prediction.get("odds"))
    return odds is not None and odds > 1.0


def is_bst_ok(prediction: Dict[str, Any]) -> bool:
    return normalize_status(prediction.get("bst_ai_status")) == "OK"


def has_ai_match(prediction: Dict[str, Any]) -> bool:
    return safe_float(prediction.get("ai_match")) is not None


def apply_top_metadata(prediction: Dict[str, Any], mode: str, reason: str) -> Dict[str, Any]:
    item = dict(prediction)
    item["top_mode"] = mode
    item["top_reason"] = reason
    return item


def top5_score(prediction: Dict[str, Any]) -> float:
    """
    Conservative TOP5 score.

    This intentionally avoids selecting very high odds purely because of market price.
    BsT AI must be OK before a pick can enter TOP5.
    """
    probability = safe_float(prediction.get("probability")) or 0.0
    ai_match = safe_float(prediction.get("ai_match")) or 0.0
    odds = safe_float(prediction.get("odds")) or 0.0

    # Value is useful, but capped so odds 8.00 cannot dominate the list.
    capped_odds = min(odds, env_float("TOP5_SCORE_ODDS_CAP", 3.0))
    value_component = max(capped_odds - 1.0, 0.0) * 0.03

    return probability + (ai_match / 100.0) * 0.15 + value_component


def eligible_primary(prediction: Dict[str, Any]) -> bool:
    min_odds = env_float("TOP5_MIN_ODDS", 1.30)
    max_odds = env_float("TOP5_MAX_ODDS", 5.00)
    min_probability = env_float("TOP5_MIN_PROBABILITY", 0.55)
    min_ai_match = env_float("TOP5_MIN_AI_MATCH", 0.0)

    odds = safe_float(prediction.get("odds"))
    probability = safe_float(prediction.get("probability"))
    ai_match = safe_float(prediction.get("ai_match"))

    if not has_odds(prediction):
        return False
    if not is_bst_ok(prediction):
        return False
    if not has_ai_match(prediction):
        return False
    if odds is None or odds < min_odds or odds > max_odds:
        return False
    if probability is None or probability < min_probability:
        return False
    if ai_match is None or ai_match < min_ai_match:
        return False

    return True


def eligible_bst_relaxed(prediction: Dict[str, Any]) -> bool:
    """
    Secondary safety tier if strict filters return fewer than TOP_N.
    Still requires BsT OK and odds; only relaxes probability/odds thresholds a bit.
    """
    min_odds = env_float("TOP5_RELAXED_MIN_ODDS", 1.15)
    max_odds = env_float("TOP5_RELAXED_MAX_ODDS", 6.00)

    odds = safe_float(prediction.get("odds"))

    if not has_odds(prediction):
        return False
    if not is_bst_ok(prediction):
        return False
    if not has_ai_match(prediction):
        return False
    if odds is None or odds < min_odds or odds > max_odds:
        return False

    return True


def deduplicate_predictions(predictions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    output = []

    for prediction in predictions:
        key = (
            str(prediction.get("match_id") or prediction.get("event_id") or ""),
            str(prediction.get("match") or ""),
            str(prediction.get("pick") or ""),
        )
        if key in seen:
            continue
        seen.add(key)
        output.append(prediction)

    return output


def build_all_predictions() -> List[Dict[str, Any]]:
    return build_core_all_predictions()


def get_top_predictions(all_predictions: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """
    Current TOP5 policy:
    - BsT AI must be OK.
    - AI Match must be available.
    - Odds must be available.
    - Very high odds are capped/filtered so odds 8.00 does not enter TOP5 only because of price.

    The old behavior allowed picks with missing BsT AI and very high odds to enter TOP5.
    This file prevents that while keeping the rest of the Corq AI model unchanged.
    """
    if all_predictions is None:
        all_predictions = build_all_predictions()

    required_count = env_int("TOP_N", TOP_N)

    primary = [
        apply_top_metadata(
            prediction,
            "BST_REQUIRED_PRIMARY",
            "BsT AI OK + AI Match available + usable odds",
        )
        for prediction in all_predictions
        if eligible_primary(prediction)
    ]
    primary.sort(key=top5_score, reverse=True)

    selected = primary[:required_count]

    if len(selected) < required_count:
        selected_keys = {
            (
                item.get("match_id") or item.get("event_id") or item.get("match"),
                item.get("pick"),
            )
            for item in selected
        }

        relaxed = []
        for prediction in all_predictions:
            key = (
                prediction.get("match_id") or prediction.get("event_id") or prediction.get("match"),
                prediction.get("pick"),
            )
            if key in selected_keys:
                continue
            if eligible_bst_relaxed(prediction):
                relaxed.append(
                    apply_top_metadata(
                        prediction,
                        "BST_REQUIRED_RELAXED",
                        "BsT AI OK required; relaxed odds/probability fallback",
                    )
                )

        relaxed.sort(key=top5_score, reverse=True)
        selected.extend(relaxed[: max(required_count - len(selected), 0)])

    selected = deduplicate_predictions(selected)

    print("TOP5 BST REQUIRED COUNT:", len(selected))
    for idx, item in enumerate(selected[:required_count], start=1):
        print(
            "TOP5 BST REQUIRED PICK:",
            idx,
            item.get("pick"),
            "vs",
            item.get("opponent"),
            "prob=",
            item.get("probability"),
            "odds=",
            item.get("odds"),
            "bst=",
            item.get("bst_ai_status"),
            "ai_match=",
            item.get("ai_match"),
            "mode=",
            item.get("top_mode"),
        )

    return selected[:required_count]


def get_daily_predictions() -> List[Dict[str, Any]]:
    return get_top_predictions()
```


## FILE: random_paths.py

```
import re
import shutil
from pathlib import Path


BASE_URL = "https://backstagetalks.github.io/tennis-backstage-talks"

CORQ_PATH = "h4v34n1c3d4y180"
THINQ_PATH = "h4v34n1c3d4y181"
BLEND_PATH = "h4v34n1c3d4y182"
ALL_PATH = "h4v34n1c3d4y183"
RESULTS_PATH = "h4v34n1c3d4y184"

CORQ_RSS_PATH = "h4v34n1c3d4y185.xml"
THINQ_RSS_PATH = "h4v34n1c3d4y186.xml"
BLEND_RSS_PATH = "h4v34n1c3d4y187.xml"


def ensure_dir(path):
    Path(path).mkdir(parents=True, exist_ok=True)


def html_link(url, label, active=False):
    active_attr = ' class="active"' if active else ""
    return f'<a href="{url}"{active_attr}>{label}</a>'


def copy_file(source, destination):
    source_path = Path(source)
    destination_path = Path(destination)

    if not source_path.exists():
        print("SKIP COPY - SOURCE MISSING:", source)
        return False

    ensure_dir(destination_path.parent)
    shutil.copy2(source_path, destination_path)
    print("COPIED:", source, "->", destination)
    return True


def remove_path(path):
    target = Path(path)

    if not target.exists():
        return

    if target.is_dir():
        shutil.rmtree(target)
    else:
        target.unlink()

    print("REMOVED OLD PATH:", path)


def create_root_redirect():
    root_path = Path("public/index.html")
    root_path.write_text(
        f'''<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta http-equiv="refresh" content="0; url=./{CORQ_PATH}/">
  <title>BackstageTalks</title>
  <style>
    body {{ margin:0; min-height:100vh; display:flex; align-items:center; justify-content:center; background:#0f172a; color:#e5e7eb; font-family:Arial,Helvetica,sans-serif; }}
    a {{ color:#38bdf8; font-weight:800; }}
  </style>
</head>
<body><div>Redirecting to <a href="./{CORQ_PATH}/">Corq</a>...</div></body>
</html>
''',
        encoding="utf-8",
    )
    print("ROOT REDIRECT CREATED:", root_path)


def active_key_for_path(path):
    normalized = str(path).replace("\\", "/")

    if normalized == f"public/{CORQ_PATH}/index.html":
        return "corq"
    if normalized == f"public/{THINQ_PATH}/index.html":
        return "thinq"
    if normalized == f"public/{BLEND_PATH}/index.html":
        return "blend"
    if normalized == f"public/{ALL_PATH}/index.html":
        return "all"
    if normalized == f"public/{RESULTS_PATH}/index.html":
        return "results"

    return ""


def build_nav_html(active_key=""):
    links = [
        html_link(f"{BASE_URL}/{CORQ_PATH}/", "Corq", active_key == "corq"),
        html_link(f"{BASE_URL}/{THINQ_PATH}/", "Thinq", active_key == "thinq"),
        html_link(f"{BASE_URL}/{BLEND_PATH}/", "Blend", active_key == "blend"),
        html_link(f"{BASE_URL}/{CORQ_RSS_PATH}", "Corq RSS"),
        html_link(f"{BASE_URL}/{THINQ_RSS_PATH}", "Thinq RSS"),
        html_link(f"{BASE_URL}/{BLEND_RSS_PATH}", "Blend RSS"),
        html_link(f"{BASE_URL}/{ALL_PATH}/", "All", active_key == "all"),
        html_link(f"{BASE_URL}/{RESULTS_PATH}/", "Results", active_key == "results"),
    ]

    return f'''
<nav class="nav" aria-label="Main navigation">
    {" ".join(links)}
</nav>
'''


def ensure_active_nav_css(path):
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8", errors="replace")

    if ".nav a.active" in text:
        return text

    css = ".nav a.active { background:rgba(34,197,94,.18); color:#22c55e; padding:7px 9px; border-radius:3px; }"

    if ".nav a:hover" in text:
        text = re.sub(
            r"(\.nav a:hover\s*\{[^}]*\})",
            r"\1\n" + css,
            text,
            count=1,
            flags=re.DOTALL,
        )
    else:
        text = text.replace("</style>", css + "\n</style>")

    return text


def replace_navigation_in_file(path):
    file_path = Path(path)

    if not file_path.exists():
        print("SKIP NAV FIX - FILE MISSING:", path)
        return False

    text = ensure_active_nav_css(path)
    nav_html = build_nav_html(active_key_for_path(path))

    new_text, count = re.subn(
        r'<nav class="nav" aria-label="Main navigation">.*?</nav>',
        nav_html,
        text,
        count=1,
        flags=re.DOTALL,
    )

    if count == 0:
        print("NAV NOT FOUND:", path)
        return False

    file_path.write_text(new_text, encoding="utf-8")
    print("NAV UPDATED:", path)
    return True


def rewrite_rss_links(path, page_url):
    file_path = Path(path)

    if not file_path.exists():
        print("SKIP RSS LINK FIX - FILE MISSING:", path)
        return False

    text = file_path.read_text(encoding="utf-8", errors="replace")
    text = re.sub(
        r"<link>.*?</link>",
        f"<link>{page_url}</link>",
        text,
        flags=re.DOTALL,
    )
    file_path.write_text(text, encoding="utf-8")
    print("RSS LINKS UPDATED:", path, "->", page_url)
    return True


def create_placeholder_page(destination, title, message):
    destination_path = Path(destination)
    ensure_dir(destination_path.parent)
    nav_html = build_nav_html(active_key_for_path(destination))
    page_html = f'''<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{title}</title>
  <style>
    body {{ background:#0f172a; color:#e5e7eb; font-family:Arial,Helvetica,sans-serif; margin:0; padding:28px; }}
    .wrap {{ max-width:960px; margin:0 auto; }}
    .nav {{ display:flex; gap:18px; align-items:center; flex-wrap:wrap; margin-bottom:28px; }}
    .nav a {{ color:#e5e7eb; text-decoration:none; font-weight:900; font-size:14px; letter-spacing:.04em; }}
    .nav a:hover {{ color:#38bdf8; }}
    .nav a.active {{ background:rgba(34,197,94,.18); color:#22c55e; padding:7px 9px; border-radius:3px; }}
    .card {{ background:#111827; border:1px solid #334155; border-radius:16px; padding:24px; }}
    h1 {{ margin-top:0; }}
    p {{ color:#94a3b8; line-height:1.6; }}
  </style>
</head>
<body>
  <div class="wrap">
    {nav_html}
    <div class="card">
      <h1>{title}</h1>
      <p>{message}</p>
    </div>
  </div>
</body>
</html>
'''
    destination_path.write_text(page_html, encoding="utf-8")
    print("PLACEHOLDER PAGE CREATED:", destination)
    return True


def create_placeholder_rss(destination):
    destination_path = Path(destination)
    rss = f'''<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>BackstageTalks Statistical Engine - Blend</title>
<link>{BASE_URL}/{BLEND_PATH}/</link>
<description>Blend RSS feed is available after Blend predictions are generated.</description>
</channel>
</rss>
'''
    destination_path.write_text(rss, encoding="utf-8")
    print("PLACEHOLDER RSS CREATED:", destination)
    return True


def create_random_page_outputs():
    copied = []

    page_map = [
        ("public/index.html", f"public/{CORQ_PATH}/index.html"),
        ("public/BsT/index.html", f"public/{THINQ_PATH}/index.html"),
        ("public/Blend/index.html", f"public/{BLEND_PATH}/index.html"),
        ("public/all/index.html", f"public/{ALL_PATH}/index.html"),
        ("public/results/index.html", f"public/{RESULTS_PATH}/index.html"),
    ]

    for source, destination in page_map:
        ok = copy_file(source, destination)
        if ok:
            copied.append(destination)

    if f"public/{BLEND_PATH}/index.html" not in copied:
        create_placeholder_page(
            f"public/{BLEND_PATH}/index.html",
            "Blend",
            "Blend page is prepared. Blend predictions will appear here after build_pages.py starts generating public/Blend/index.html.",
        )
        copied.append(f"public/{BLEND_PATH}/index.html")

    return copied


def create_random_rss_outputs():
    rss_map = [
        ("public/tennis.xml", f"public/{CORQ_RSS_PATH}", f"{BASE_URL}/{CORQ_PATH}/"),
        ("public/tennis_bst.xml", f"public/{THINQ_RSS_PATH}", f"{BASE_URL}/{THINQ_PATH}/"),
        ("public/tennis_blend.xml", f"public/{BLEND_RSS_PATH}", f"{BASE_URL}/{BLEND_PATH}/"),
    ]

    for source, destination, page_url in rss_map:
        ok = copy_file(source, destination)
        if ok:
            rewrite_rss_links(destination, page_url)

    if not Path(f"public/{BLEND_RSS_PATH}").exists():
        create_placeholder_rss(f"public/{BLEND_RSS_PATH}")


def remove_old_public_paths():
    old_paths = [
        "public/all",
        "public/BsT",
        "public/Blend",
        "public/results",
        "public/tennis.xml",
        "public/tennis_bst.xml",
        "public/tennis_blend.xml",
        "public/tennis_all.xml",
    ]

    for path in old_paths:
        remove_path(path)


def verify_random_outputs():
    required_files = [
        "public/index.html",
        f"public/{CORQ_PATH}/index.html",
        f"public/{THINQ_PATH}/index.html",
        f"public/{BLEND_PATH}/index.html",
        f"public/{ALL_PATH}/index.html",
        f"public/{RESULTS_PATH}/index.html",
        f"public/{CORQ_RSS_PATH}",
        f"public/{THINQ_RSS_PATH}",
        f"public/{BLEND_RSS_PATH}",
    ]

    missing = []

    for path in required_files:
        if not Path(path).exists():
            missing.append(path)

    if missing:
        print("")
        print("MISSING RANDOM OUTPUTS:")
        for path in missing:
            print(path)
        raise RuntimeError("Random path output verification failed.")

    print("")
    print("RANDOM OUTPUT VERIFICATION OK")


def main():
    print("")
    print("=== RANDOM PATH REMAP START ===")

    copied_pages = create_random_page_outputs()
    create_random_rss_outputs()

    for path in copied_pages:
        replace_navigation_in_file(path)

    remove_old_public_paths()
    create_root_redirect()
    verify_random_outputs()

    print("=== RANDOM PATH REMAP DONE ===")
    print("")


if __name__ == "__main__":
    main()
```


## FILE: render_site.py

```
import os
import html
from datetime import datetime, timezone

SITE_TITLE = "Backstage Talks Statistical Engine"
BASE_URL = "https://backstagetalks.github.io/tennis-backstage-talks"
HEADER_TITLE = "BackstageTalks Statistical Engine"
HEADER_SUBTITLE = "This data is provided for informational and analytical purposes only"
FOOTER_TEXT = "Powered by BackstageTalks Statistical Engine"


def safe(value, default="-"):
    if value is None or value == "":
        return default
    return html.escape(str(value))


def safe_float(value):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def pct(value):
    try:
        return f"{float(value) * 100:.1f}%"
    except Exception:
        return "-"


def pct_plain(value):
    try:
        return f"{float(value):.1f}"
    except Exception:
        return "-"


def odds(value):
    try:
        if value is None or value == "":
            return "-"
        return f"{float(value):.2f}"
    except Exception:
        return "-"


def html_link(url, label):
    return f'<a href="{safe(url)}">{safe(label)}</a>'


def render_nav():
    links = [
        html_link(f"{BASE_URL}/", "Corq"),
        html_link(f"{BASE_URL}/tennis.xml", "Corq RSS"),
        html_link(f"{BASE_URL}/BsT/", "Thinq"),
        html_link(f"{BASE_URL}/tennis_bst.xml", "Thinq RSS"),
        html_link(f"{BASE_URL}/all/", "ALL"),
        html_link(f"{BASE_URL}/results/", "RESULTS"),
    ]
    return f"""
<nav class="nav" aria-label="Main navigation">
    {" ".join(links)}
</nav>
"""


def format_match_meta(prediction):
    parts = []
    for key in ["tournament", "surface"]:
        value = prediction.get(key)
        if value:
            parts.append(str(value))
    if prediction.get("best_of"):
        parts.append(f"BO{prediction.get('best_of')}")
    return " • ".join(parts)


def resolve_sets_label(prediction):
    label = prediction.get("sets_probability_label")
    if label:
        return str(label)
    try:
        if int(prediction.get("best_of")) == 5:
            return "5 Sets"
    except Exception:
        pass
    return "3 Sets"


def normalize_probability_for_display(value):
    number = safe_float(value)
    if number is None:
        return None
    if number <= 1.0:
        return number * 100.0
    return number


def format_pct_points(value):
    if value is None:
        return "-"
    try:
        return f"{float(value):.1f}%"
    except Exception:
        return "-"


def resolve_ai_metrics(prediction):
    corq_pct = normalize_probability_for_display(
        prediction.get("corq_ai_probability")
        or prediction.get("corq_display_probability")
        or prediction.get("probability")
    )
    thinq_pct = normalize_probability_for_display(prediction.get("bst_ai_probability"))
    ai_match = safe_float(prediction.get("ai_match"))
    return {"corq_pct": corq_pct, "thinq_pct": thinq_pct, "ai_match": ai_match}


def resolve_ai_delta(metrics):
    corq_pct = metrics.get("corq_pct")
    thinq_pct = metrics.get("thinq_pct")
    if corq_pct is None or thinq_pct is None:
        return {"label": "Thinq unavailable", "class": "delta-muted"}
    gap = float(thinq_pct) - float(corq_pct)
    if abs(gap) < 0.05:
        return {"label": "Even", "class": "delta-even"}
    if gap > 0:
        return {"label": f"Thinq +{gap:.1f}%", "class": "delta-thinq"}
    return {"label": f"Corq +{abs(gap):.1f}%", "class": "delta-corq"}


def resolve_marq_signal(prediction):
    signal = prediction.get("marq_ai_signal")
    score = prediction.get("marq_ai_score")
    if score is None:
        return "NO MARKET DATA"
    if not signal:
        return "NEUTRAL"
    return str(signal).upper()


def metric_row(label, value):
    return f"""
            <div class="metric-row">
                <span>{safe(label)}</span>
                <strong>{safe(value)}</strong>
            </div>
"""


def resolve_model_view(title, subtitle):
    text = f"{title or ''} {subtitle or ''}".lower()
    if "bst" in text or "thinq" in text:
        return "thinq"
    return "corq"


def render_data_ai_box(prediction, model_view="corq"):
    status = prediction.get("bst_ai_status")
    metrics = resolve_ai_metrics(prediction)
    corq_display = format_pct_points(metrics["corq_pct"])
    thinq_display = format_pct_points(metrics["thinq_pct"])
    ai_match_display = format_pct_points(metrics["ai_match"])

    if status != "OK":
        thinq_display = "No data"
        ai_match_display = "-"
        delta = {"label": "Thinq unavailable", "class": "delta-muted"}
    else:
        delta = resolve_ai_delta(metrics)

    if model_view == "thinq":
        rows = metric_row("Thinq AI", thinq_display) + metric_row("Corq AI", corq_display) + metric_row("AI Match", ai_match_display)
    else:
        rows = metric_row("Corq AI", corq_display) + metric_row("Thinq AI", thinq_display) + metric_row("AI Match", ai_match_display)

    return f"""
        <div class="intel-panel data-ai-panel">
            <div class="panel-title">DATA AI</div>
            {rows}
            <div class="ai-delta {safe(delta['class'])}">{safe(delta['label'])}</div>
        </div>
"""


def render_marq_ai_box(prediction):
    marq_signal = resolve_marq_signal(prediction)
    signal_class_map = {
        "BULLISH": "market-bullish",
        "SUPPORT": "market-support",
        "NEUTRAL": "market-neutral",
        "CAUTION": "market-caution",
        "BEARISH": "market-bearish",
        "NO MARKET DATA": "market-unavailable",
    }
    signal_class = signal_class_map.get(marq_signal, "market-neutral")
    score = prediction.get("marq_ai_score")
    if score is None:
        display_signal = "No market data"
        score_html = ""
    else:
        display_signal = marq_signal
        score_html = metric_row("Score", pct_plain(score))
    return f"""
        <div class="intel-panel marq-panel">
            <div class="panel-title">MARQ AI</div>
            {score_html}
            <div class="market-badge {signal_class}">{safe(display_signal)}</div>
        </div>
"""


def render_sets_box(expected_sets, sets_probability_label, sets_probability, most_likely_html):
    return f"""
        <div class="intel-panel sets-panel">
            <div class="panel-title">SETS</div>
            {metric_row("Sets", expected_sets)}
            {metric_row(sets_probability_label, sets_probability)}
            {most_likely_html}
        </div>
"""


def render_match_intelligence(prediction, expected_sets, sets_probability_label, sets_probability, most_likely_html, model_view="corq"):
    return f"""
        <div class="intel-title">Match Intelligence</div>
        <div class="intel-layout">
            {render_data_ai_box(prediction, model_view=model_view)}
            {render_marq_ai_box(prediction)}
            {render_sets_box(expected_sets, sets_probability_label, sets_probability, most_likely_html)}
        </div>
"""


def render_summary(predictions):
    count = len(predictions)
    probabilities = []
    ai_match_values = []
    for prediction in predictions:
        try:
            if prediction.get("probability") is not None:
                probabilities.append(float(prediction.get("probability")))
        except Exception:
            pass
        try:
            if prediction.get("ai_match") is not None:
                ai_match_values.append(float(prediction.get("ai_match")))
        except Exception:
            pass
    avg_probability = "-"
    avg_ai_match = "-"
    if probabilities:
        avg_probability = f"{sum(probabilities) / len(probabilities) * 100:.1f}%"
    if ai_match_values:
        avg_ai_match = f"{sum(ai_match_values) / len(ai_match_values):.1f}%"
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"""
<div class="summary">
    <div class="summary-card"><div class="summary-label">Picks</div><div class="summary-value">{count}</div></div>
    <div class="summary-card"><div class="summary-label">Average Win %</div><div class="summary-value">{avg_probability}</div></div>
    <div class="summary-card"><div class="summary-label">Average AI Match</div><div class="summary-value">{avg_ai_match}</div></div>
    <div class="summary-card"><div class="summary-label">Updated</div><div class="summary-value small">{updated}</div></div>
</div>
"""


def render_rows(predictions, model_view="corq"):
    if not predictions:
        return '<tr><td colspan="7" class="empty">No picks available.</td></tr>'
    rows = []
    for index, prediction in enumerate(predictions, start=1):
        pick = safe(prediction.get("pick"))
        opponent = safe(prediction.get("opponent"))
        match = safe(prediction.get("match"))
        time = safe(prediction.get("time"))
        probability = pct(prediction.get("probability"))
        odd = odds(prediction.get("odds"))
        expected_sets = safe(prediction.get("expected_sets"))
        sets_probability = pct(prediction.get("sets_probability"))
        sets_probability_label = safe(resolve_sets_label(prediction))
        most_likely_score = safe(prediction.get("most_likely_score"), default="")
        match_meta = safe(format_match_meta(prediction), default="")
        match_meta_html = f'<div class="match-meta">{match_meta}</div>' if match_meta else ""
        most_likely_html = metric_row("Score", most_likely_score) if most_likely_score else ""
        intelligence_html = render_match_intelligence(prediction, expected_sets, sets_probability_label, sets_probability, most_likely_html, model_view=model_view)
        rows.append(f"""
<tr>
    <td class="rank">#{index}</td>
    <td class="pick-cell">
        <div class="pick-name">{pick}</div>
        <div class="pick-sub">to win</div>
        <div class="match-name">{match}</div>
        {match_meta_html}
    </td>
    <td>{opponent}</td>
    <td>{time}</td>
    <td class="probability">{probability}</td>
    <td class="odds">{odd}</td>
    <td class="intel">{intelligence_html}</td>
</tr>
""")
    return "\n".join(rows)


def render_page(predictions, title, subtitle):
    model_view = resolve_model_view(title, subtitle)
    rows = render_rows(predictions, model_view=model_view)
    summary = render_summary(predictions)
    nav = render_nav()
    page_title = safe(title or SITE_TITLE)
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{page_title}</title>
<style>
:root {{ --bg:#0f172a; --panel:#111827; --panel-2:#1e293b; --border:#334155; --text:#e5e7eb; --muted:#94a3b8; --green:#22c55e; --orange:#fb923c; --red:#ef4444; --yellow:#facc15; --blue:#38bdf8; }}
* {{ box-sizing:border-box; }}
html, body {{ margin:0; padding:0; background:var(--bg); color:var(--text); font-family:Arial, Helvetica, sans-serif; }}
.wrapper {{ max-width:1440px; margin:0 auto; padding:28px; }}
.header {{ display:grid; grid-template-columns:minmax(560px,1fr) auto; gap:40px; align-items:start; margin-bottom:24px; }}
.logo {{ font-size:30px; font-weight:900; line-height:1.15; color:var(--text); letter-spacing:.2px; white-space:nowrap; }}
.subtitle {{ color:var(--muted); margin-top:10px; font-size:14px; line-height:1.45; max-width:800px; }}
.nav {{ display:flex; gap:18px; align-items:center; flex-wrap:nowrap; padding-top:8px; white-space:nowrap; }}
.nav a {{ color:var(--text); text-decoration:none; font-weight:900; font-size:14px; letter-spacing:.04em; }}
.nav a:hover {{ color:var(--blue); }}
.summary {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:22px; }}
.summary-card {{ background:var(--panel); border:1px solid var(--border); border-radius:14px; padding:16px; }}
.summary-label {{ color:var(--muted); font-size:13px; margin-bottom:8px; }}
.summary-value {{ font-size:22px; font-weight:800; }}
.summary-value.small {{ font-size:14px; }}
.table-wrap {{ overflow-x:auto; background:var(--panel); border:1px solid var(--border); border-radius:16px; }}
table {{ width:100%; border-collapse:collapse; min-width:1040px; }}
thead {{ background:var(--panel-2); }}
th {{ padding:14px 12px; text-align:left; font-size:13px; color:var(--muted); border-bottom:1px solid var(--border); text-transform:uppercase; letter-spacing:.04em; }}
td {{ padding:16px 12px; border-bottom:1px solid var(--border); vertical-align:top; }}
tr:hover {{ background:rgba(255,255,255,.03); }}
.rank {{ font-weight:800; color:var(--blue); }}
.pick-name {{ font-size:20px; line-height:1.12; font-weight:900; }}
.pick-sub {{ color:var(--green); font-size:14px; line-height:1.1; margin-top:4px; font-weight:900; }}
.match-name {{ color:var(--muted); font-size:12px; line-height:1.18; margin-top:7px; }}
.match-meta {{ color:var(--blue); font-size:12px; line-height:1.18; margin-top:5px; font-weight:700; }}
.probability {{ font-weight:800; color:var(--green); }}
.odds {{ font-weight:800; color:var(--yellow); }}
.intel {{ line-height:1.45; min-width:390px; }}
.intel-title {{ margin-bottom:6px; color:var(--muted); font-size:11px; font-weight:900; letter-spacing:.04em; text-transform:uppercase; }}
.intel-layout {{ display:grid; grid-template-columns:minmax(110px,1fr) minmax(110px,1fr) minmax(130px,1.15fr); gap:8px; align-items:stretch; }}
.intel-panel {{ min-height:92px; padding:8px 9px; border-radius:8px; font-size:11px; line-height:1.35; background:rgba(100,116,139,.14); border:1px solid rgba(100,116,139,.38); }}
.panel-title {{ color:#fff; font-size:10px; font-weight:900; text-transform:uppercase; letter-spacing:.05em; margin-bottom:6px; }}
.metric-row {{ display:grid; grid-template-columns:58px auto; column-gap:7px; align-items:center; margin-top:3px; }}
.metric-row span {{ color:var(--muted); }}
.metric-row strong {{ text-align:right; color:var(--text); font-weight:900; }}
.ai-delta {{ margin-top:7px; text-align:right; font-size:10px; font-weight:900; }}
.delta-thinq {{ color:var(--blue); }} .delta-corq {{ color:var(--orange); }} .delta-even {{ color:var(--muted); }} .delta-muted {{ color:var(--muted); }}
.market-badge {{ display:inline-block; margin-top:8px; padding:5px 10px; border-radius:5px; font-size:10px; font-weight:800; letter-spacing:.05em; text-transform:uppercase; }}
.market-bullish {{ color:#22c55e; border:1px solid rgba(34,197,94,.45); background:rgba(34,197,94,.08); }}
.market-support {{ color:#38bdf8; border:1px solid rgba(56,189,248,.45); background:rgba(56,189,248,.08); }}
.market-neutral {{ color:#94a3b8; border:1px solid rgba(148,163,184,.45); background:rgba(148,163,184,.08); }}
.market-caution {{ color:#fb923c; border:1px solid rgba(251,146,60,.45); background:rgba(251,146,60,.08); }}
.market-bearish {{ color:#ef4444; border:1px solid rgba(239,68,68,.45); background:rgba(239,68,68,.08); }}
.market-unavailable {{ color:#94a3b8; border:1px solid rgba(148,163,184,.35); background:rgba(148,163,184,.05); text-transform:none; }}
.empty {{ text-align:center; color:var(--muted); padding:40px; }}
.footer {{ max-width:900px; margin:38px auto 0; color:var(--muted); font-size:12px; text-align:center; line-height:1.7; }}
@media (max-width:1050px) {{ .header{{display:block;}} .logo{{white-space:normal;}} .nav{{margin-top:16px; padding-top:0; flex-wrap:wrap;}} .summary{{grid-template-columns:1fr 1fr;}} }}
@media (max-width:700px) {{ .wrapper{{padding:16px;}} .summary{{grid-template-columns:1fr;}} .intel-layout{{grid-template-columns:1fr;}} }}
</style>
</head>
<body>
<div class="wrapper">
    <div class="header"><div><div class="logo">{safe(HEADER_TITLE)}</div><div class="subtitle">{safe(HEADER_SUBTITLE)}</div></div>{nav}</div>
    {summary}
    <div class="table-wrap"><table><thead><tr><th>#</th><th>Pick</th><th>Opponent</th><th>Time</th><th>Win %</th><th>Odds</th><th>Match Intelligence</th></tr></thead><tbody>{rows}</tbody></table></div>
    <div class="footer">{safe(FOOTER_TEXT)}</div>
</div>
</body>
</html>
"""


def write_page(predictions, title, subtitle, destination):
    html_text = render_page(predictions=predictions, title=title, subtitle=subtitle)
    directory = os.path.dirname(destination)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(destination, "w", encoding="utf-8") as file:
        file.write(html_text)


def render_rss(predictions, title, link):
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    items = []
    for prediction in predictions:
        pick = safe(prediction.get("pick"))
        opponent = safe(prediction.get("opponent"))
        probability = pct(prediction.get("probability"))
        odd = odds(prediction.get("odds"))
        expected_sets = safe(prediction.get("expected_sets"))
        tournament = safe(prediction.get("tournament"))
        surface = safe(prediction.get("surface"))
        best_of = safe(prediction.get("best_of"))
        sets_label = safe(resolve_sets_label(prediction))
        sets_probability = pct(prediction.get("sets_probability"))
        most_likely_score = safe(prediction.get("most_likely_score"), default="-")
        metrics = resolve_ai_metrics(prediction)
        corq_ai = format_pct_points(metrics["corq_pct"])
        thinq_ai = format_pct_points(metrics["thinq_pct"])
        ai_match = format_pct_points(metrics["ai_match"])
        delta = resolve_ai_delta(metrics)
        marq_signal = resolve_marq_signal(prediction)
        marq_score = pct_plain(prediction.get("marq_ai_score"))
        description_text = (
            f"Pick: {pick}\nOpponent: {opponent}\nTournament: {tournament}\nSurface: {surface}\n"
            f"Best of: {best_of}\nWin probability: {probability}\nOdds: {odd}\n"
            f"Corq AI: {corq_ai}\nThinq AI: {thinq_ai}\nAI Match: {ai_match}\nAI Difference: {delta['label']}\n"
            f"Marq AI: {marq_score}\nMarket Signal: {marq_signal}\nExpected sets: {expected_sets}\n"
            f"{sets_label}: {sets_probability}\nMost likely score: {most_likely_score}\n\n{HEADER_SUBTITLE}\n{FOOTER_TEXT}"
        )
        description = html.escape(description_text)
        items.append(f"""
<item>
<title>{pick} to win vs {opponent}</title>
<link>{link}</link>
<description>{description}</description>
<pubDate>{now}</pubDate>
</item>
""")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>{html.escape(title)}</title>
<link>{link}</link>
<description>{html.escape(HEADER_TITLE)}</description>
{''.join(items)}
</channel>
</rss>
"""


def write_rss(predictions, title, link, destination):
    xml = render_rss(predictions=predictions, title=title, link=link)
    directory = os.path.dirname(destination)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(destination, "w", encoding="utf-8") as file:
        file.write(xml)
```


## FILE: render_site_ready.py

```
import os
import html
from datetime import datetime, timezone


SITE_TITLE = "Backstage Talks Statistical Engine"
BASE_URL = "https://backstagetalks.github.io/tennis-backstage-talks"

HEADER_TITLE = "BackstageTalks Statistical Engine"
HEADER_SUBTITLE = "This data is provided for informational and analytical purposes only"
FOOTER_TEXT = "Powered by BackstageTalks Statistical Engine"


def safe(value, default="-"):
    if value is None:
        return default

    if value == "":
        return default

    return html.escape(str(value))


def pct(value):
    try:
        return f"{float(value) * 100:.1f}%"
    except Exception:
        return "-"


def pct_plain(value):
    try:
        return f"{float(value):.1f}%"
    except Exception:
        return "-"


def signed_pct(value):
    try:
        number = float(value)

        if number > 0:
            return f"+{number:.1f}%"

        if number < 0:
            return f"{number:.1f}%"

        return "0.0%"

    except Exception:
        return "-"


def odds(value):
    try:
        return f"{float(value):.2f}"
    except Exception:
        return "-"


def tag_class(tag):
    tag = str(tag or "").upper()

    if tag == "PLAY":
        return "tag-play"

    if tag == "PLAY SMALL":
        return "tag-small"

    if tag == "WATCH":
        return "tag-watch"

    return "tag-info"


def html_link(url, label):
    lt = chr(60)
    gt = chr(62)

    return (
        f'{lt}a href="{safe(url)}"{gt}'
        f'{safe(label)}'
        f'{lt}/a{gt}'
    )


def render_nav():
    links = [
        html_link(f"{BASE_URL}/", "TOP5"),
        html_link(f"{BASE_URL}/all/", "ALL"),
        html_link(f"{BASE_URL}/results/", "RESULTS"),
    ]

    return f"""
<nav class="nav" aria-label="Main navigation">
    {" ".join(links)}
</nav>
"""


def format_match_meta(prediction):
    tournament = prediction.get("tournament")
    surface = prediction.get("surface")
    best_of = prediction.get("best_of")

    parts = []

    if tournament:
        parts.append(str(tournament))

    if surface:
        parts.append(str(surface))

    if best_of:
        parts.append(f"BO{best_of}")

    if not parts:
        return ""

    return " • ".join(parts)


def resolve_sets_label(prediction):
    label = prediction.get("sets_probability_label")

    if label:
        return str(label)

    best_of = prediction.get("best_of")

    try:
        if int(best_of) == 5:
            return "5 Sets"
    except Exception:
        pass

    return "3 Sets"


def normalize_ai_color(value):
    text = str(value or "").lower().strip()

    if text in ["green", "orange", "red", "gray"]:
        return text

    return "gray"


def render_ai_match(prediction):
    status = prediction.get(
        "bst_ai_status"
    )

    if status != "OK":
        return ""

    corq_probability = (
        prediction.get("corq_ai_probability")
        or prediction.get("probability")
    )

    bst_probability = prediction.get(
        "bst_ai_probability"
    )

    ai_match = prediction.get(
        "ai_match"
    )

    marq_score = prediction.get(
        "marq_ai_score"
    )

    marq_signal = str(
        prediction.get(
            "marq_ai_signal"
        ) or "NEUTRAL"
    ).upper()

    signal_class_map = {
        "BULLISH": "market-bullish",
        "SUPPORT": "market-support",
        "NEUTRAL": "market-neutral",
        "CAUTION": "market-caution",
        "BEARISH": "market-bearish",
    }

    signal_class = signal_class_map.get(
        marq_signal,
        "market-neutral",
    )

    return f"""
        <div class="ai-box ai-match-gray">

            <div class="ai-main">
                AI Match {pct_plain(ai_match)}
            </div>

            <div class="ai-row">
                <span>Corq AI</span>
                <span>{pct(corq_probability)}</span>
            </div>

            <div class="ai-row">
                <span>BsT AI</span>
                <span>{pct(bst_probability)}</span>
            </div>

            <div class="ai-row">
                <span>Marq AI</span>
                <span>{pct_plain(marq_score)}</span>
            </div>

            <div class="market-badge {signal_class}">
                {safe(marq_signal)}
            </div>

        </div>
"""


def render_summary(predictions):
    count = len(predictions)

    probabilities = []

    for prediction in predictions:
        value = prediction.get("probability")

        if value is None:
            continue

        try:
            probabilities.append(float(value))
        except Exception:
            continue

    odds_values = []

    for prediction in predictions:
        value = prediction.get("odds")

        if value is None:
            continue

        try:
            odds_values.append(float(value))
        except Exception:
            continue

    ai_match_values = []

    for prediction in predictions:
        value = prediction.get("ai_match")

        if value is None:
            continue

        try:
            ai_match_values.append(float(value))
        except Exception:
            continue

    avg_probability = "-"
    avg_odds = "-"
    avg_ai_match = "-"

    if probabilities:
        avg_probability = f"{sum(probabilities) / len(probabilities) * 100:.1f}%"

    if odds_values:
        avg_odds = f"{sum(odds_values) / len(odds_values):.2f}"

    if ai_match_values:
        avg_ai_match = f"{sum(ai_match_values) / len(ai_match_values):.1f}%"

    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return f"""
<div class="summary">
    <div class="summary-card">
        <div class="summary-label">Picks</div>
        <div class="summary-value">{count}</div>
    </div>

    <div class="summary-card">
        <div class="summary-label">Average Win %</div>
        <div class="summary-value">{avg_probability}</div>
    </div>

    <div class="summary-card">
        <div class="summary-label">Average AI Match</div>
        <div class="summary-value">{avg_ai_match}</div>
    </div>

    <div class="summary-card">
        <div class="summary-label">Updated</div>
        <div class="summary-value small">{updated}</div>
    </div>
</div>
"""


def render_rows(predictions):
    if not predictions:
        return """
<tr>
    <td colspan="7" class="empty">
        No picks available.
    </td>
</tr>
"""

    rows = []

    for index, prediction in enumerate(predictions, start=1):
        pick = safe(prediction.get("pick"))
        opponent = safe(prediction.get("opponent"))
        match = safe(prediction.get("match"))
        time = safe(prediction.get("time"))

        probability = pct(prediction.get("probability"))
        odd = odds(prediction.get("odds"))

        expected_sets = safe(prediction.get("expected_sets"))
        sets_probability = pct(prediction.get("sets_probability"))
        sets_probability_label = safe(
            resolve_sets_label(prediction)
        )

        most_likely_score = safe(
            prediction.get("most_likely_score"),
            default="",
        )

        match_meta = safe(
            format_match_meta(prediction),
            default="",
        )

        match_meta_html = ""

        if match_meta:
            match_meta_html = f"""
        <div class="match-meta">
            {match_meta}
        </div>
"""

        most_likely_html = ""

        if most_likely_score:
            most_likely_html = f"""
        <div>
            <span class="intel-label">Most likely score:</span>
            {most_likely_score}
        </div>
"""

        ai_match_html = render_ai_match(
            prediction
        )

        rows.append(f"""
<tr>
    <td class="rank">#{index}</td>

    <td class="pick-cell">
        <div class="pick-name">{pick}</div>
        <div class="pick-sub">to win</div>
        <div class="match-name">{match}</div>
        {match_meta_html}
    </td>

    <td>{opponent}</td>

    <td>{time}</td>

    <td class="probability">{probability}</td>

    <td class="odds">{odd}</td>

    <td class="intel">
        <div>
            <span class="intel-label">Sets:</span>
            {expected_sets}
        </div>

        <div>
            <span class="intel-label">{sets_probability_label}:</span>
            {sets_probability}
        </div>

        {most_likely_html}

        {ai_match_html}
    </td>
</tr>
""")

    return "\n".join(rows)


def render_page(predictions, title, subtitle):
    rows = render_rows(predictions)
    summary = render_summary(predictions)
    nav = render_nav()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>{safe(SITE_TITLE)}</title>

<style>
:root {{
    --bg: #0f172a;
    --panel: #111827;
    --panel-2: #1e293b;
    --border: #334155;
    --text: #e5e7eb;
    --muted: #94a3b8;
    --green: #22c55e;
    --orange: #fb923c;
    --red: #ef4444;
    --yellow: #facc15;
    --blue: #38bdf8;
    --gray: #64748b;
}}

* {{
    box-sizing: border-box;
}}

html, body {{
    margin: 0;
    padding: 0;
    background: var(--bg);
    color: var(--text);
    font-family: Arial, Helvetica, sans-serif;
}}

.wrapper {{
    max-width: 1440px;
    margin: 0 auto;
    padding: 28px;
}}

.header {{
    display: grid;
    grid-template-columns: minmax(560px, 1fr) auto;
    gap: 40px;
    align-items: start;
    margin-bottom: 24px;
}}

.logo {{
    font-size: 30px;
    font-weight: 900;
    line-height: 1.15;
    color: var(--text);
    letter-spacing: 0.2px;
    white-space: nowrap;
}}

.subtitle {{
    color: var(--muted);
    margin-top: 10px;
    font-size: 14px;
    line-height: 1.45;
    max-width: 800px;
}}

.nav {{
    display: flex;
    gap: 18px;
    align-items: center;
    flex-wrap: nowrap;
    padding-top: 8px;
    white-space: nowrap;
}}

.nav a {{
    color: var(--text);
    text-decoration: none;
    font-weight: 900;
    font-size: 14px;
    letter-spacing: 0.04em;
}}

.nav a:hover {{
    color: var(--blue);
}}

.summary {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin-bottom: 22px;
}}

.summary-card {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 16px;
}}

.summary-label {{
    color: var(--muted);
    font-size: 13px;
    margin-bottom: 8px;
}}

.summary-value {{
    font-size: 22px;
    font-weight: 800;
}}

.summary-value.small {{
    font-size: 14px;
}}

.table-wrap {{
    overflow-x: auto;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 16px;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    min-width: 1040px;
}}

thead {{
    background: var(--panel-2);
}}

th {{
    padding: 14px 12px;
    text-align: left;
    font-size: 13px;
    color: var(--muted);
    border-bottom: 1px solid var(--border);
    text-transform: uppercase;
    letter-spacing: 0.04em;
}}

td {{
    padding: 16px 12px;
    border-bottom: 1px solid var(--border);
    vertical-align: top;
}}

tr:hover {{
    background: rgba(255, 255, 255, 0.03);
}}

.rank {{
    font-weight: 800;
    color: var(--blue);
}}

.pick-name {{
    font-size: 16px;
    font-weight: 800;
}}

.pick-sub {{
    color: var(--green);
    font-size: 12px;
    margin-top: 4px;
    font-weight: 700;
}}

.match-name {{
    color: var(--muted);
    font-size: 12px;
    margin-top: 8px;
}}

.match-meta {{
    color: var(--blue);
    font-size: 12px;
    margin-top: 6px;
    font-weight: 700;
}}

.probability {{
    font-weight: 800;
    color: var(--green);
}}

.odds {{
    font-weight: 800;
    color: var(--yellow);
}}

.intel {{
    line-height: 1.55;
    min-width: 260px;
}}

.intel-label {{
    color: var(--muted);
    font-size: 12px;
    margin-right: 4px;
}}

.ai-box {{
    margin-top: 10px;
    padding: 9px 10px;
    border-radius: 12px;
    font-size: 12px;
    line-height: 1.45;
}}

.ai-main {{
    font-weight: 900;
    margin-bottom: 6px;
}}

.ai-sub {{
    font-size: 11px;
    color: var(--muted);
}}

.ai-row {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 4px;
    font-size: 12px;
}}

.market-badge {{
    display: inline-block;
    margin-top: 10px;
    padding: 6px 12px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 800;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}}

.market-bullish {{
    color: #22c55e;
    border: 1px solid rgba(34,197,94,.45);
    background: rgba(34,197,94,.08);
}}

.market-support {{
    color: #38bdf8;
    border: 1px solid rgba(56,189,248,.45);
    background: rgba(56,189,248,.08);
}}

.market-neutral {{
    color: #94a3b8;
    border: 1px solid rgba(148,163,184,.45);
    background: rgba(148,163,184,.08);
}}

.market-caution {{
    color: #fb923c;
    border: 1px solid rgba(251,146,60,.45);
    background: rgba(251,146,60,.08);
}}

.market-bearish {{
    color: #ef4444;
    border: 1px solid rgba(239,68,68,.45);
    background: rgba(239,68,68,.08);
}}

.ai-match-green {{
    background: rgba(34, 197, 94, 0.14);
    border: 1px solid rgba(34, 197, 94, 0.45);
}}

.ai-match-green .ai-main {{
    color: var(--green);
}}

.ai-match-orange {{
    background: rgba(251, 146, 60, 0.14);
    border: 1px solid rgba(251, 146, 60, 0.45);
}}

.ai-match-orange .ai-main {{
    color: var(--orange);
}}

.ai-match-red {{
    background: rgba(239, 68, 68, 0.14);
    border: 1px solid rgba(239, 68, 68, 0.45);
}}

.ai-match-red .ai-main {{
    color: var(--red);
}}

.ai-match-gray {{
    background: rgba(100, 116, 139, 0.18);
    border: 1px solid rgba(100, 116, 139, 0.45);
}}

.ai-match-gray .ai-main {{
    color: var(--muted);
}}

.empty {{
    text-align: center;
    color: var(--muted);
    padding: 40px;
}}

.footer {{
    max-width: 900px;
    margin: 38px auto 0;
    color: var(--muted);
    font-size: 12px;
    text-align: center;
    line-height: 1.7;
}}

@media (max-width: 1050px) {{
    .header {{
        display: block;
    }}

    .logo {{
        white-space: normal;
    }}

    .nav {{
        margin-top: 16px;
        padding-top: 0;
        flex-wrap: wrap;
    }}

    .summary {{
        grid-template-columns: 1fr 1fr;
    }}
}}

@media (max-width: 600px) {{
    .wrapper {{
        padding: 16px;
    }}

    .summary {{
        grid-template-columns: 1fr;
    }}
}}
</style>
</head>

<body>
<div class="wrapper">

    <div class="header">
        <div>
            <div class="logo">
                {safe(HEADER_TITLE)}
            </div>

            <div class="subtitle">
                {safe(HEADER_SUBTITLE)}
            </div>
        </div>

        {nav}
    </div>

    {summary}

    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Pick</th>
                    <th>Opponent</th>
                    <th>Time</th>
                    <th>Win %</th>
                    <th>Odds</th>
                    <th>Match Intelligence</th>
                </tr>
            </thead>

            <tbody>
                {rows}
            </tbody>
        </table>
    </div>

    <div class="footer">
        {safe(FOOTER_TEXT)}
    </div>

</div>
</body>
</html>
"""


def write_page(predictions, title, subtitle, destination):
    html_text = render_page(
        predictions=predictions,
        title=title,
        subtitle=subtitle,
    )

    directory = os.path.dirname(destination)

    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(destination, "w", encoding="utf-8") as file:
        file.write(html_text)


def render_rss(predictions, title, link):
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    items = []

    for prediction in predictions:
        pick = safe(prediction.get("pick"))
        opponent = safe(prediction.get("opponent"))
        probability = pct(prediction.get("probability"))
        odd = odds(prediction.get("odds"))
        expected_sets = safe(prediction.get("expected_sets"))

        tournament = safe(prediction.get("tournament"))
        surface = safe(prediction.get("surface"))
        best_of = safe(prediction.get("best_of"))
        sets_label = safe(resolve_sets_label(prediction))
        sets_probability = pct(prediction.get("sets_probability"))

        most_likely_score = safe(
            prediction.get("most_likely_score"),
            default="-",
        )

        bst_status = prediction.get("bst_ai_status")

        if bst_status == "OK":
            corq_ai = pct(
                prediction.get("corq_ai_probability")
                or prediction.get("probability")
            )
            bst_ai = pct(prediction.get("bst_ai_probability"))
            ai_match = pct_plain(prediction.get("ai_match"))
            marq_ai = pct_plain(prediction.get("marq_ai_score"))
            marq_signal = safe(
                prediction.get("marq_ai_signal"),
                default="NEUTRAL",
            )

            ai_text = (
                f"AI Match: {ai_match}\n"
                f"Corq AI: {corq_ai}\n"
                f"BsT AI: {bst_ai}\n"
                f"Marq AI: {marq_ai}\n"
                f"Market Signal: {marq_signal}\n"
            )

        else:
            ai_text = (
                "Corq AI: available\n"
                "BsT AI: No data\n"
                "AI Match: No data\n"
                "Marq AI: No data\n"
            )

        description_text = (
            f"Pick: {pick}\n"
            f"Opponent: {opponent}\n"
            f"Tournament: {tournament}\n"
            f"Surface: {surface}\n"
            f"Best of: {best_of}\n"
            f"Win probability: {probability}\n"
            f"Odds: {odd}\n"
            f"{ai_text}"
            f"Expected sets: {expected_sets}\n"
            f"{sets_label}: {sets_probability}\n"
            f"Most likely score: {most_likely_score}\n\n"
            f"{HEADER_SUBTITLE}\n"
            f"{FOOTER_TEXT}"
        )

        description = html.escape(description_text)

        items.append(f"""
<item>
<title>{pick} to win vs {opponent}</title>
<link>{link}</link>
<description>{description}</description>
<pubDate>{now}</pubDate>
</item>
""")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>{html.escape(title)}</title>
<link>{link}</link>
<description>{html.escape(HEADER_TITLE)}</description>
{''.join(items)}
</channel>
</rss>
"""


def write_rss(predictions, title, link, destination):
    xml = render_rss(
        predictions=predictions,
        title=title,
        link=link,
    )

    directory = os.path.dirname(destination)

    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(destination, "w", encoding="utf-8") as file:
        file.write(xml)
```


## FILE: requirements.txt

```
pandas
requests
beautifulsoup4
feedparser
```


## FILE: results_checker.py

```
import json
import os
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

try:
    from results_fetcher import fetch_finished_results as _external_fetch_finished_results
except Exception:
    _external_fetch_finished_results = None


BRATISLAVA_TZ = ZoneInfo("Europe/Bratislava")
ALL_PICK_HISTORY_DIR = "data/pick_history/all"
TOP5_PICK_HISTORY_DIR = "data/pick_history/top5"
LEGACY_PLAY_HISTORY_DIR = "data/play_history"
RESULTS_DIR = "data/results"
ALL_RESULTS_PATH = "data/results/all_results.json"
TOP5_RESULTS_PATH = "data/results/top5_results.json"
PUBLIC_RESULTS_DATA_PATH = "public/results_data.json"
RESULTS_DEBUG_PATH = "public/results_debug.json"

_DEBUG = {
    "provider": "results_fetcher",
    "fetch_error": None,
    "fetch_debug": {},
    "datasets": {
        "all": {"history_files": [], "history_items_loaded": 0, "resolved_count": 0, "pending_count": 0, "unknown_count": 0},
        "top5": {"history_files": [], "history_items_loaded": 0, "resolved_count": 0, "pending_count": 0, "unknown_count": 0},
    },
    "finished_results_found": 0,
    "examples_results": [],
    "examples_resolved": [],
    "examples_unresolved": [],
    "examples_date_rejected": [],
}


def ensure_dirs():
    os.makedirs("data", exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    os.makedirs(ALL_PICK_HISTORY_DIR, exist_ok=True)
    os.makedirs(TOP5_PICK_HISTORY_DIR, exist_ok=True)
    os.makedirs(LEGACY_PLAY_HISTORY_DIR, exist_ok=True)
    os.makedirs("public", exist_ok=True)


def now_utc_iso():
    return datetime.now(timezone.utc).isoformat()


def betting_day(date_time=None):
    if date_time is None:
        date_time = datetime.now(BRATISLAVA_TZ)
    if isinstance(date_time, str):
        try:
            date_time = datetime.fromisoformat(date_time.replace("Z", "+00:00"))
        except Exception:
            date_time = datetime.now(BRATISLAVA_TZ)
    if date_time.tzinfo is None:
        date_time = date_time.replace(tzinfo=BRATISLAVA_TZ)
    else:
        date_time = date_time.astimezone(BRATISLAVA_TZ)
    if date_time.hour < 6:
        date_time = date_time - timedelta(days=1)
    return date_time.strftime("%Y-%m-%d")


def save_json(path, data):
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


def load_json(path, default):
    try:
        if not os.path.exists(path):
            return default
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as exc:
        print("RESULTS CHECKER JSON LOAD ERROR:", path, str(exc))
        return default


def snapshot_items(data):
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ["items", "picks", "matches", "results"]:
            items = data.get(key)
            if isinstance(items, list):
                return items
    return []


def normalize(value):
    if value is None:
        return ""
    text = str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower()
    text = text.replace("-", " ").replace(".", " ").replace(",", " ")
    text = text.replace("'", "").replace("’", "").replace("`", "")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return " ".join(text.split())


def loose_name_keys(name):
    normalized = normalize(name)
    parts = normalized.split()
    keys = set()
    if normalized:
        keys.add(normalized)
    if parts:
        keys.add(parts[-1])
    if len(parts) >= 2:
        keys.add(" ".join(parts[-2:]))
        first = parts[0]
        last = parts[-1]
        if first and last:
            keys.add(f"{first[0]} {last}")
            keys.add(f"{last} {first[0]}")
    return keys


def names_match(a, b):
    a_keys = loose_name_keys(a)
    b_keys = loose_name_keys(b)
    if not a_keys or not b_keys:
        return False
    return bool(a_keys.intersection(b_keys))


def safe_float(value):
    try:
        if value in [None, "", "NA", "NaN"]:
            return None
        return float(value)
    except Exception:
        return None


def parse_date(value):
    try:
        return datetime.strptime(str(value), "%Y-%m-%d").date()
    except Exception:
        return None


def ids_match(pick, result):
    pick_id = pick.get("match_id") or pick.get("event_id") or pick.get("id")
    result_id = result.get("match_id") or result.get("event_id") or result.get("id")
    if pick_id and result_id and str(pick_id) == str(result_id):
        return True
    return False


def dates_compatible(pick, result):
    pick_date = pick.get("date")
    result_date = result.get("date")
    if not pick_date or not result_date:
        return True
    return str(pick_date) == str(result_date)


def load_history_items(dataset, directory):
    ensure_dirs()
    items = []
    files = []
    if not os.path.exists(directory):
        return items
    for filename in sorted(os.listdir(directory)):
        if not filename.endswith(".json"):
            continue
        path = os.path.join(directory, filename)
        files.append(path)
        data = load_json(path, [])
        for item in snapshot_items(data):
            if isinstance(item, dict):
                updated = dict(item)
                updated["dataset"] = dataset
                items.append(updated)
    _DEBUG["datasets"][dataset]["history_files"] = files
    _DEBUG["datasets"][dataset]["history_items_loaded"] = len(items)
    return items


def load_dataset_history(dataset):
    if dataset == "all":
        items = load_history_items("all", ALL_PICK_HISTORY_DIR)
        if items:
            return items
        return load_history_items("all", LEGACY_PLAY_HISTORY_DIR)
    if dataset == "top5":
        return load_history_items("top5", TOP5_PICK_HISTORY_DIR)
    return []


def item_key(item):
    return "|".join([str(item.get("date") or ""), normalize(item.get("match") or ""), normalize(item.get("pick") or ""), normalize(item.get("opponent") or "")])


def load_previous_items(dataset):
    path = TOP5_RESULTS_PATH if dataset == "top5" else ALL_RESULTS_PATH
    data = load_json(path, {})
    items = snapshot_items(data)
    return {item_key(item): item for item in items if isinstance(item, dict)}


def merge_previous_status(pick, previous_by_key):
    previous = previous_by_key.get(item_key(pick))
    if not previous:
        return pick

    # Never preserve old resolved status for today's betting day.
    # This fixes cases where an earlier broad name-only match wrongly settled a not-yet-played today's pick.
    if str(pick.get("date") or "") == betting_day():
        merged = dict(pick)
        for key in ["result_status", "winner", "score", "units", "resolved_at", "result_source", "result_match_score"]:
            merged.pop(key, None)
        return merged

    previous_status = str(previous.get("result_status") or "").upper()
    if previous_status not in ["WON", "LOST", "VOID", "UNKNOWN"]:
        return pick

    merged = dict(pick)
    for key in ["result_status", "winner", "score", "units", "resolved_at", "result_source", "result_match_score"]:
        if key in previous:
            merged[key] = previous.get(key)
    return merged


def result_score(result):
    if result.get("score"):
        return result.get("score")
    h = result.get("home_score_current")
    a = result.get("away_score_current")
    if h is not None and a is not None:
        return f"{h}-{a}"
    return None


def normalize_finished_result(result):
    if not isinstance(result, dict):
        return None
    player1 = result.get("player1") or result.get("home") or result.get("homeTeam") or result.get("home_player")
    player2 = result.get("player2") or result.get("away") or result.get("awayTeam") or result.get("away_player")
    winner = result.get("winner") or result.get("winner_name")
    status = str(result.get("status") or result.get("result_status") or "").upper()
    if status in ["CANCELLED", "POSTPONED", "WALKOVER", "RETIRED", "VOID"]:
        result_status = "VOID"
    else:
        result_status = "FINISHED"
    if not player1 or not player2:
        return None
    return {
        "match_id": result.get("match_id"),
        "event_id": result.get("event_id") or result.get("match_id"),
        "date": result.get("date"),
        "player1": player1,
        "player2": player2,
        "winner": winner,
        "score": result_score(result),
        "status": "VOID" if result_status == "VOID" else "FINISHED",
        "source": result.get("source") or result.get("result_source") or "results_fetcher",
        "match": result.get("match") or f"{player1} vs {player2}",
        "raw": result,
    }


def fetch_finished_results_safe():
    if _external_fetch_finished_results is None:
        _DEBUG["fetch_error"] = "results_fetcher.fetch_finished_results is not available"
        return []
    try:
        raw_results = _external_fetch_finished_results()
        if raw_results is None:
            raw_results = []
        normalized = []
        for result in raw_results:
            item = normalize_finished_result(result)
            if item:
                normalized.append(item)
        _DEBUG["finished_results_found"] = len(normalized)
        _DEBUG["examples_results"] = normalized[:10]
        return normalized
    except Exception as exc:
        _DEBUG["fetch_error"] = str(exc)
        print("RESULTS CHECKER FETCH ERROR:", str(exc))
        return []


def match_pick_to_result(pick, result):
    # Strong match: same TennisApi event id.
    if ids_match(pick, result):
        return True

    # Safety guard: never match same player names across different dates.
    if not dates_compatible(pick, result):
        if len(_DEBUG["examples_date_rejected"]) < 30:
            _DEBUG["examples_date_rejected"].append({
                "pick_date": pick.get("date"),
                "result_date": result.get("date"),
                "pick": pick.get("pick"),
                "match": pick.get("match"),
                "result_match": result.get("match"),
            })
        return False

    pick_match = pick.get("match") or ""
    pick_player = pick.get("pick") or ""
    opponent = pick.get("opponent") or ""
    r1 = result.get("player1") or ""
    r2 = result.get("player2") or ""

    direct = names_match(pick_player, r1) and names_match(opponent, r2)
    reversed_match = names_match(pick_player, r2) and names_match(opponent, r1)

    if direct or reversed_match:
        return True

    normalized_pick_match = normalize(pick_match)
    return normalize(pick_player) in normalized_pick_match and normalize(opponent) in normalized_pick_match and (normalize(r1) in normalized_pick_match or normalize(r2) in normalized_pick_match)


def find_matching_result(pick, results):
    # Prefer exact id matches first.
    for result in results:
        if ids_match(pick, result):
            return result
    # Then date-safe name matching.
    for result in results:
        if match_pick_to_result(pick, result):
            return result
    return None


def calculate_units(status, odds):
    odds_value = safe_float(odds)
    if status == "WON":
        if odds_value is None:
            return 0.0
        return round(odds_value - 1.0, 2)
    if status == "LOST":
        if odds_value is None:
            return 0.0
        return -1.0
    return 0.0


def evaluate_pick(pick, results, dataset):
    result = find_matching_result(pick, results)
    if not result:
        updated = dict(pick)
        existing_status = str(updated.get("result_status") or "PENDING").upper()
        if existing_status in ["WON", "LOST", "VOID"] and str(updated.get("date") or "") != betting_day():
            updated["dataset"] = dataset
            return updated
        updated["dataset"] = dataset
        updated["result_status"] = "PENDING"
        updated["units"] = 0.0
        updated.pop("winner", None)
        updated.pop("score", None)
        if len(_DEBUG["examples_unresolved"]) < 30:
            _DEBUG["examples_unresolved"].append({"dataset": dataset, "date": pick.get("date"), "match": pick.get("match"), "pick": pick.get("pick"), "reason": "no_date_safe_matching_finished_result"})
        return updated

    updated = dict(pick)
    if result.get("status") == "VOID":
        status = "VOID"
    else:
        winner = result.get("winner")
        if winner and names_match(pick.get("pick"), winner):
            status = "WON"
        elif winner:
            status = "LOST"
        else:
            status = "UNKNOWN"

    updated["dataset"] = dataset
    updated["result_status"] = status
    updated["winner"] = result.get("winner")
    updated["score"] = result.get("score")
    updated["units"] = calculate_units(status, updated.get("odds"))
    updated["resolved_at"] = now_utc_iso()
    updated["result_source"] = result.get("source")
    updated["result_match_score"] = result.get("match")
    updated["result_date"] = result.get("date")

    if len(_DEBUG["examples_resolved"]) < 30:
        _DEBUG["examples_resolved"].append({"dataset": dataset, "date": updated.get("date"), "match": updated.get("match"), "pick": updated.get("pick"), "status": status, "winner": updated.get("winner"), "score": updated.get("score"), "units": updated.get("units"), "result_date": result.get("date")})
    return updated


def summarize(items):
    summary = {"picks": len(items), "won": 0, "lost": 0, "void": 0, "pending": 0, "unknown": 0, "units": 0.0}
    for item in items:
        status = str(item.get("result_status") or "PENDING").upper()
        if status == "WON":
            summary["won"] += 1
        elif status == "LOST":
            summary["lost"] += 1
        elif status == "VOID":
            summary["void"] += 1
        elif status == "UNKNOWN":
            summary["unknown"] += 1
        else:
            summary["pending"] += 1
        summary["units"] += safe_float(item.get("units")) or 0.0
    summary["units"] = round(summary["units"], 2)
    settled = summary["won"] + summary["lost"]
    summary["win_rate"] = round(summary["won"] / settled, 3) if settled > 0 else None
    return summary


def filter_by_days(items, days):
    today_date = parse_date(betting_day()) or datetime.now(timezone.utc).date()
    cutoff = today_date - timedelta(days=days - 1)
    output = []
    for item in items:
        item_date = parse_date(item.get("date"))
        if item_date and item_date >= cutoff:
            output.append(item)
    return output


def filter_current_month(items):
    today_date = parse_date(betting_day()) or datetime.now(timezone.utc).date()
    output = []
    for item in items:
        item_date = parse_date(item.get("date"))
        if item_date and item_date.year == today_date.year and item_date.month == today_date.month:
            output.append(item)
    return output


def sort_items(items):
    return sorted(items, key=lambda item: (item.get("date") or "", -(item.get("rank") or 9999), item.get("match") or ""), reverse=True)


def build_dataset_payload(dataset, evaluated_items):
    today = betting_day()
    sorted_all = sort_items(evaluated_items)
    today_items = [item for item in evaluated_items if item.get("date") == today]
    last_7_items = filter_by_days(evaluated_items, 7)
    month_items = filter_current_month(evaluated_items)
    return {
        "dataset": dataset,
        "updated_at": now_utc_iso(),
        "betting_day": today,
        "summary": summarize(evaluated_items),
        "cards": {"today": summarize(today_items), "last_7_days": summarize(last_7_items), "current_month": summarize(month_items), "all_time": summarize(evaluated_items)},
        "today": summarize(today_items),
        "last_7_days": summarize(last_7_items),
        "current_month": summarize(month_items),
        "all_time": summarize(evaluated_items),
        "items": sorted_all,
        "results": sorted_all,
    }


def evaluate_dataset(dataset, finished_results):
    history_items = load_dataset_history(dataset)
    previous_by_key = load_previous_items(dataset)
    prepared_items = [merge_previous_status(item, previous_by_key) for item in history_items]
    evaluated_items = [evaluate_pick(item, finished_results, dataset) for item in prepared_items]
    resolved = 0
    pending = 0
    unknown = 0
    for item in evaluated_items:
        status = str(item.get("result_status") or "PENDING").upper()
        if status in ["WON", "LOST", "VOID"]:
            resolved += 1
        elif status == "UNKNOWN":
            unknown += 1
        else:
            pending += 1
    _DEBUG["datasets"][dataset]["resolved_count"] = resolved
    _DEBUG["datasets"][dataset]["pending_count"] = pending
    _DEBUG["datasets"][dataset]["unknown_count"] = unknown
    return build_dataset_payload(dataset, evaluated_items)


def main():
    ensure_dirs()
    finished_results = fetch_finished_results_safe()
    all_payload = evaluate_dataset("all", finished_results)
    top5_payload = evaluate_dataset("top5", finished_results)
    combined_public_payload = {"updated_at": now_utc_iso(), "betting_day": betting_day(), "all": all_payload, "top5": top5_payload, "datasets": {"all": all_payload, "top5": top5_payload}}
    save_json(ALL_RESULTS_PATH, all_payload)
    save_json(TOP5_RESULTS_PATH, top5_payload)
    save_json(PUBLIC_RESULTS_DATA_PATH, combined_public_payload)
    save_json(RESULTS_DEBUG_PATH, _DEBUG)
    print("Results checker completed")
    print("ALL picks:", all_payload["summary"]["picks"])
    print("TOP5 picks:", top5_payload["summary"]["picks"])
    print("Finished results found:", len(finished_results))
    if _DEBUG.get("fetch_error"):
        print("Fetch warning:", _DEBUG["fetch_error"])


if __name__ == "__main__":
    main()
```


## FILE: results_fetcher.py

```
import os
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from zoneinfo import ZoneInfo

from tennisapi_client import TennisApiClient, normalize_event


logger = logging.getLogger(__name__)
LOCAL_TZ = ZoneInfo("Europe/Bratislava")


def parse_category_ids() -> List[int]:
    raw = os.getenv("TENNISAPI_CATEGORY_IDS", "3,6,871").strip()
    output: List[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            output.append(int(part))
        except Exception:
            logger.warning("Invalid TennisApi category id ignored: %s", part)
    return output or [3]


def parse_finished_lookback_days() -> int:
    try:
        return int(os.getenv("RESULTS_LOOKBACK_DAYS", "90"))
    except Exception:
        return 90


def unix_to_local_date(timestamp: Any) -> Optional[str]:
    try:
        if not timestamp:
            return None
        return datetime.fromtimestamp(int(timestamp), tz=timezone.utc).astimezone(LOCAL_TZ).strftime("%Y-%m-%d")
    except Exception:
        return None


# ----------------------------------------------------------------------
# Fixtures / snapshot functions
# ----------------------------------------------------------------------


def fetch_tennisapi_events_for_date(
    target_date: datetime,
    category_ids: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    client = TennisApiClient()
    category_ids = category_ids or parse_category_ids()
    raw_events = client.get_events_by_date(target_date=target_date, category_ids=category_ids)
    normalized_events: List[Dict[str, Any]] = []

    for event in raw_events:
        try:
            normalized = normalize_event(event)
            if not normalized.get("match_id"):
                continue
            if not normalized.get("player1") or not normalized.get("player2"):
                continue
            normalized["date"] = unix_to_local_date(normalized.get("start_timestamp"))
            normalized_events.append(normalized)
        except Exception as exc:
            logger.warning("Failed to normalize TennisApi event: %s", exc)

    return normalized_events


def fetch_daily_fixtures(target_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    target_date = target_date or datetime.now(LOCAL_TZ)
    tennisapi_events = fetch_tennisapi_events_for_date(target_date)
    if tennisapi_events:
        logger.info("Fetched %s fixtures from TennisApi for %s", len(tennisapi_events), target_date.date())
        return tennisapi_events
    logger.warning("TennisApi returned no fixtures for %s", target_date.date())
    return []


def get_matches_for_snapshot(target_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    return fetch_daily_fixtures(target_date)


# ----------------------------------------------------------------------
# Finished results for results_checker.py
# ----------------------------------------------------------------------


def fetch_finished_results(
    lookback_days: Optional[int] = None,
    category_ids: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    lookback_days = lookback_days or parse_finished_lookback_days()
    category_ids = category_ids or parse_category_ids()
    today = datetime.now(LOCAL_TZ)
    all_results: List[Dict[str, Any]] = []
    seen = set()

    for offset in range(lookback_days):
        target_date = today - timedelta(days=offset)
        try:
            events = fetch_tennisapi_events_for_date(target_date=target_date, category_ids=category_ids)
        except Exception as exc:
            logger.warning("Finished results fetch failed for %s: %s", target_date.date(), exc)
            continue

        for event in events:
            match_id = event.get("match_id")
            if match_id in seen:
                continue
            seen.add(match_id)
            result = event_to_finished_result(event)
            if result:
                all_results.append(result)

    logger.info("TennisApi finished results found: %s", len(all_results))
    return all_results


def event_to_finished_result(event: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    status = str(event.get("status") or "").upper()
    if status not in ["FINISHED", "WALKOVER", "RETIRED", "CANCELLED", "POSTPONED"]:
        return None

    player1 = event.get("player1")
    player2 = event.get("player2")
    if not player1 or not player2:
        return None

    result_status = "VOID" if status in ["WALKOVER", "RETIRED", "CANCELLED", "POSTPONED"] else "FINISHED"
    result_date = event.get("date") or unix_to_local_date(event.get("start_timestamp"))

    return {
        "source": "TennisApi",
        "match_id": event.get("match_id"),
        "event_id": event.get("event_id") or event.get("match_id"),
        "date": result_date,
        "player1": player1,
        "player2": player2,
        "winner": event.get("winner"),
        "score": build_score(event),
        "status": result_status,
        "match": f"{player1} vs {player2}",
        "tournament": event.get("tournament"),
        "category": event.get("category"),
        "start_time_utc": event.get("start_time_utc"),
        "raw": event.get("raw", event),
    }


def build_score(event: Dict[str, Any]) -> Optional[str]:
    set_parts: List[str] = []
    for idx in range(1, 6):
        h = event.get(f"home_score_period{idx}")
        a = event.get(f"away_score_period{idx}")
        if h is None or a is None:
            continue
        set_parts.append(f"{h}-{a}")
    if set_parts:
        return " ".join(set_parts)

    h_current = event.get("home_score_current")
    a_current = event.get("away_score_current")
    if h_current is not None and a_current is not None:
        return f"{h_current}-{a_current}"
    return None


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Category IDs:", parse_category_ids())
    print("Lookback days:", parse_finished_lookback_days())
    results = fetch_finished_results()
    print(f"Finished results found: {len(results)}")
    for result in results[:20]:
        print(result.get("date"), result.get("match_id"), result.get("player1"), "vs", result.get("player2"), "winner:", result.get("winner"), "score:", result.get("score"), "status:", result.get("status"))
```


## FILE: results_fetcher_sofa.py

```

import json
import os
import re
import unicodedata
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
from zoneinfo import ZoneInfo

import requests
from bs4 import BeautifulSoup


SOFASCORE_BASE_URL = "https://api.sofascore.com/api/v1"
SOFASCORE_TENNIS_EVENTS_URL = SOFASCORE_BASE_URL + "/sport/tennis/scheduled-events/{date}"

SPORTSCORE_URL = "https://sportscore.com/tennis/"

BRATISLAVA_TZ = ZoneInfo("Europe/Bratislava")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json,text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

REQUEST_TIMEOUT_SECONDS = 30
TARGET_CONTEXT_CHARS = 180


DEBUG_TEMPLATE = {
    "generated_at": None,
    "primary_source": "SofaScore",
    "fallback_source": "SportScore",
    "sofascore": {
        "enabled": True,
        "dates_requested": [],
        "http_statuses": {},
        "fetch_errors": {},
        "events_loaded": 0,
        "finished_events": 0,
        "examples": [],
    },
    "sportscore": {
        "enabled": True,
        "http_status": None,
        "fetch_error": None,
        "generic_results_found": 0,
        "targeted_results_found": 0,
        "examples_generic_results": [],
        "examples_targeted_results": [],
        "examples_targeted_contexts": [],
    },
    "combined_results_found": 0,
}


def now_utc_iso():
    return datetime.now(timezone.utc).isoformat()


def betting_day(date_time=None):
    if date_time is None:
        date_time = datetime.now(BRATISLAVA_TZ)

    if isinstance(date_time, str):
        try:
            date_time = datetime.fromisoformat(
                date_time.replace("Z", "+00:00")
            )
        except Exception:
            date_time = datetime.now(BRATISLAVA_TZ)

    if date_time.tzinfo is None:
        date_time = date_time.replace(tzinfo=BRATISLAVA_TZ)
    else:
        date_time = date_time.astimezone(BRATISLAVA_TZ)

    if date_time.hour < 6:
        date_time = date_time - timedelta(days=1)

    return date_time.strftime("%Y-%m-%d")


def clean_text(value):
    if not value:
        return ""

    return re.sub(r"\s+", " ", str(value)).strip()


def normalize(value):
    if value is None:
        return ""

    text = str(value)
    text = unicodedata.normalize("NFKD", text)
    text = "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    )
    text = text.lower()
    text = text.replace("-", " ")
    text = text.replace(".", " ")
    text = text.replace(",", " ")
    text = text.replace("'", "")
    text = text.replace("’", "")
    text = text.replace("`", "")
    text = re.sub(r"[^a-z0-9\s]", " ", text)

    return " ".join(text.split())


def name_parts(name):
    normalized = normalize(name)

    return [
        part
        for part in normalized.split()
        if part
    ]


def player_variants(name):
    parts = name_parts(name)
    variants = set()

    if not parts:
        return []

    full = " ".join(parts)
    variants.add(full)

    last = parts[-1]
    variants.add(last)

    if len(parts) >= 2:
        first = parts[0]
        first_initial = first[0]
        variants.add(f"{last} {first_initial}")
        variants.add(f"{first_initial} {last}")
        variants.add(" ".join(parts[-2:]))

    return sorted(
        variants,
        key=len,
        reverse=True,
    )


def loose_name_keys(name):
    parts = name_parts(name)
    keys = set()

    if parts:
        keys.add(" ".join(parts))
        keys.add(parts[-1])

    if len(parts) >= 2:
        first = parts[0]
        last = parts[-1]
        keys.add(" ".join(parts[-2:]))
        keys.add(f"{last} {first[0]}")
        keys.add(f"{first[0]} {last}")

    return keys


def names_match(a, b):
    a_keys = loose_name_keys(a)
    b_keys = loose_name_keys(b)

    if not a_keys or not b_keys:
        return False

    if a_keys.intersection(b_keys):
        return True

    a_norm = normalize(a)
    b_norm = normalize(b)

    if not a_norm or not b_norm:
        return False

    return SequenceMatcher(None, a_norm, b_norm).ratio() >= 0.88


def safe_int(value):
    try:
        return int(value)
    except Exception:
        return None


def event_date_candidates_from_picks(picks):
    dates = set()

    for pick in picks or []:
        if not isinstance(pick, dict):
            continue

        date = pick.get("date")

        if date and re.match(r"^\d{4}-\d{2}-\d{2}$", str(date)):
            dates.add(str(date))

    today = betting_day()
    dates.add(today)

    try:
        today_date = datetime.strptime(today, "%Y-%m-%d").date()
        dates.add((today_date + timedelta(days=1)).strftime("%Y-%m-%d"))
        dates.add((today_date - timedelta(days=1)).strftime("%Y-%m-%d"))
    except Exception:
        pass

    return sorted(dates)


def http_get_json(url, debug, date):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        debug["sofascore"]["http_statuses"][date] = response.status_code
        response.raise_for_status()

        return response.json()

    except Exception as exc:
        debug["sofascore"]["fetch_errors"][date] = str(exc)
        return None


def get_team_name(team):
    if not isinstance(team, dict):
        return None

    return (
        team.get("name")
        or team.get("shortName")
        or team.get("slug")
    )


def get_status_text(event):
    status = event.get("status") or {}

    if not isinstance(status, dict):
        return ""

    return " ".join(
        str(status.get(key) or "")
        for key in ["type", "description"]
    ).lower()


def is_sofascore_finished(event):
    status = event.get("status") or {}

    if isinstance(status, dict):
        status_type = str(status.get("type") or "").lower()
        status_description = str(status.get("description") or "").lower()
        status_code = status.get("code")

        if status_type == "finished":
            return True

        if status_code in [100, 110, 120]:
            return True

        if "finished" in status_description or "ended" in status_description:
            return True

    if event.get("winnerCode") in [1, 2]:
        return True

    return False


def score_value(score_dict, key):
    if not isinstance(score_dict, dict):
        return None

    return safe_int(score_dict.get(key))


def build_set_score_string(home_score, away_score):
    if not isinstance(home_score, dict) or not isinstance(away_score, dict):
        return None

    set_parts = []

    for index in range(1, 6):
        home_value = score_value(home_score, f"period{index}")
        away_value = score_value(away_score, f"period{index}")

        if home_value is None or away_value is None:
            continue

        set_parts.append(f"{home_value}-{away_value}")

    if set_parts:
        return " ".join(set_parts)

    home_current = score_value(home_score, "current")
    away_current = score_value(away_score, "current")

    if home_current is not None and away_current is not None:
        return f"{home_current}-{away_current}"

    return None


def sofa_winner(event, home_name, away_name):
    winner_code = event.get("winnerCode")

    if winner_code == 1:
        return home_name

    if winner_code == 2:
        return away_name

    home_score = event.get("homeScore") or {}
    away_score = event.get("awayScore") or {}

    home_current = score_value(home_score, "current")
    away_current = score_value(away_score, "current")

    if home_current is None or away_current is None:
        return None

    if home_current > away_current:
        return home_name

    if away_current > home_current:
        return away_name

    return None


def sofa_event_to_result(event, date):
    home_name = get_team_name(event.get("homeTeam"))
    away_name = get_team_name(event.get("awayTeam"))

    if not home_name or not away_name:
        return None

    if not is_sofascore_finished(event):
        return None

    home_score = event.get("homeScore") or {}
    away_score = event.get("awayScore") or {}
    score = build_set_score_string(home_score, away_score)

    winner = sofa_winner(event, home_name, away_name)

    if not winner:
        return None

    tournament = event.get("tournament") or {}
    unique_tournament = event.get("season") or {}

    tournament_name = None

    if isinstance(tournament, dict):
        tournament_name = tournament.get("name")

    if not tournament_name and isinstance(unique_tournament, dict):
        tournament_name = unique_tournament.get("name")

    return {
        "player1": home_name,
        "player2": away_name,
        "match": f"{home_name} vs {away_name}",
        "winner": winner,
        "score": score or "",
        "status": "FINISHED",
        "source": "SofaScore",
        "method": "sofascore_scheduled_events",
        "event_id": event.get("id"),
        "date": date,
        "tournament": tournament_name,
        "start_timestamp": event.get("startTimestamp"),
    }


def fetch_sofascore_results_for_date(date, debug):
    url = SOFASCORE_TENNIS_EVENTS_URL.format(date=date)

    debug["sofascore"]["dates_requested"].append(date)

    data = http_get_json(url, debug, date)

    if not data:
        return []

    events = data.get("events")

    if not isinstance(events, list):
        return []

    debug["sofascore"]["events_loaded"] += len(events)

    results = []

    for event in events:
        if not isinstance(event, dict):
            continue

        result = sofa_event_to_result(event, date)

        if not result:
            continue

        results.append(result)

        if len(debug["sofascore"]["examples"]) < 30:
            debug["sofascore"]["examples"].append(result)

    debug["sofascore"]["finished_events"] += len(results)

    return results


def fetch_sofascore_results(picks, debug):
    all_results = []

    for date in event_date_candidates_from_picks(picks):
        all_results.extend(
            fetch_sofascore_results_for_date(date, debug)
        )

    return all_results


def parse_score_sets(score_text):
    if not score_text:
        return None

    score_text = clean_text(score_text)
    upper = score_text.upper()

    if any(token in upper for token in ["W/O", "WO", "RET", "ABN", "DEF"]):
        return {
            "status": "VOID",
            "winner_side": None,
            "score": score_text,
        }

    chunks = re.findall(
        r"(\d{1,2})-(\d{1,2})",
        score_text,
    )

    if not chunks:
        return None

    p1_sets = 0
    p2_sets = 0

    for a_text, b_text in chunks:
        a = safe_int(a_text)
        b = safe_int(b_text)

        if a is None or b is None:
            continue

        if a > b:
            p1_sets += 1
        elif b > a:
            p2_sets += 1

    if p1_sets == p2_sets:
        return None

    return {
        "status": "FINISHED",
        "winner_side": "player1" if p1_sets > p2_sets else "player2",
        "score": score_text,
        "p1_sets": p1_sets,
        "p2_sets": p2_sets,
    }


def parse_scoreboard_numbers(after_text):
    after_text = clean_text(after_text)
    numbers = re.findall(r"\d{1,3}", after_text)

    if len(numbers) < 2:
        return None

    p1_sets = safe_int(numbers[0])
    p2_sets = safe_int(numbers[1])

    if p1_sets is None or p2_sets is None:
        return None

    if p1_sets == p2_sets:
        return None

    if max(p1_sets, p2_sets) > 3:
        return None

    if min(p1_sets, p2_sets) > 2:
        return None

    if max(p1_sets, p2_sets) < 2:
        return None

    score_preview = " ".join(numbers[:10])

    return {
        "status": "FINISHED",
        "winner_side": "player1" if p1_sets > p2_sets else "player2",
        "score": score_preview,
        "p1_sets": p1_sets,
        "p2_sets": p2_sets,
    }


def finished_text_only(text):
    text = clean_text(text)
    lower = text.lower()

    markers = [
        "finished matches",
        "finished results",
        "finished",
        "results",
    ]

    start_index = -1

    for marker in markers:
        idx = lower.find(marker)

        if idx != -1:
            start_index = idx
            break

    if start_index == -1:
        return text

    return text[start_index:]


def extract_generic_vs_results(text, debug):
    text = finished_text_only(text)
    results = []

    pattern_vs_score = re.compile(
        r"(?P<p1>[A-ZÀ-Ž][A-Za-zÀ-ž\.\-'\s]{2,75}?)"
        r"\s+vs\s+"
        r"(?P<p2>[A-ZÀ-Ž][A-Za-zÀ-ž\.\-'\s]{2,75}?)"
        r"\s+(?P<score>(?:\d{1,2}-\d{1,2}(?:\(\d+\))?\s*){2,5}|W/O|WO|RET|DEF|ABN)",
        re.IGNORECASE,
    )

    for match in pattern_vs_score.finditer(text):
        p1 = clean_text(match.group("p1"))
        p2 = clean_text(match.group("p2"))
        score = clean_text(match.group("score"))
        parsed = parse_score_sets(score)

        if not parsed:
            continue

        if parsed["status"] == "VOID":
            winner = None
            status = "VOID"
        elif parsed["winner_side"] == "player1":
            winner = p1
            status = "FINISHED"
        else:
            winner = p2
            status = "FINISHED"

        result = {
            "player1": p1,
            "player2": p2,
            "match": f"{p1} vs {p2}",
            "winner": winner,
            "score": parsed.get("score") or score,
            "status": status,
            "source": "SportScore",
            "method": "generic_vs_score",
        }

        results.append(result)

        if len(debug["sportscore"]["examples_generic_results"]) < 30:
            debug["sportscore"]["examples_generic_results"].append(result)

    debug["sportscore"]["generic_results_found"] = len(results)

    return results


def find_variant_positions(text, variants):
    positions = []

    for variant in variants:
        if not variant:
            continue

        pattern = re.compile(r"(?<![a-z0-9])" + re.escape(variant) + r"(?![a-z0-9])")

        for match in pattern.finditer(text):
            positions.append(
                {
                    "variant": variant,
                    "start": match.start(),
                    "end": match.end(),
                }
            )

    positions.sort(key=lambda item: item["start"])

    return positions


def build_targeted_result_from_context(pick, text):
    pick_name = pick.get("pick") or ""
    opponent_name = pick.get("opponent") or ""

    if not pick_name or not opponent_name:
        return None

    normalized_text = normalize(text)
    pick_variants = player_variants(pick_name)
    opponent_variants = player_variants(opponent_name)

    pick_positions = find_variant_positions(normalized_text, pick_variants)
    opponent_positions = find_variant_positions(normalized_text, opponent_variants)

    best_candidate = None
    best_distance = None

    for pick_pos in pick_positions:
        for opponent_pos in opponent_positions:
            if pick_pos["start"] == opponent_pos["start"]:
                continue

            left = min(pick_pos, opponent_pos, key=lambda item: item["start"])
            right = max(pick_pos, opponent_pos, key=lambda item: item["start"])
            distance = right["start"] - left["end"]

            if distance < 0 or distance > TARGET_CONTEXT_CHARS:
                continue

            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_candidate = {
                    "left": left,
                    "right": right,
                    "pick_first": pick_pos["start"] < opponent_pos["start"],
                }

    if not best_candidate:
        return None

    right = best_candidate["right"]
    after = normalized_text[right["end"]: right["end"] + TARGET_CONTEXT_CHARS]
    parsed = parse_scoreboard_numbers(after)

    if not parsed:
        return None

    pick_first = best_candidate["pick_first"]

    player1 = pick_name if pick_first else opponent_name
    player2 = opponent_name if pick_first else pick_name

    if parsed["status"] == "VOID":
        winner = None
        status = "VOID"
    elif parsed["winner_side"] == "player1":
        winner = player1
        status = "FINISHED"
    else:
        winner = player2
        status = "FINISHED"

    return {
        "player1": player1,
        "player2": player2,
        "match": f"{player1} vs {player2}",
        "winner": winner,
        "score": parsed.get("score"),
        "status": status,
        "source": "SportScore",
        "method": "targeted_pick_context",
        "context": after[:120],
        "pick_id": pick.get("id"),
        "pick_match": pick.get("match"),
    }


def fetch_sportscore_text(debug):
    try:
        response = requests.get(
            SPORTSCORE_URL,
            headers=HEADERS,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )

        debug["sportscore"]["http_status"] = response.status_code
        response.raise_for_status()

        soup = BeautifulSoup(
            response.text,
            "html.parser",
        )

        return soup.get_text(
            " ",
            strip=True,
        )

    except Exception as exc:
        debug["sportscore"]["fetch_error"] = str(exc)
        return ""


def fetch_sportscore_results(picks, debug):
    text = fetch_sportscore_text(debug)

    if not text:
        return []

    text = finished_text_only(text)
    generic_results = extract_generic_vs_results(text, debug)

    targeted_results = []
    seen = set()

    for pick in picks or []:
        if not isinstance(pick, dict):
            continue

        result = build_targeted_result_from_context(pick, text)

        if not result:
            continue

        key = result_key(result)

        if key in seen:
            continue

        seen.add(key)
        targeted_results.append(result)

        if len(debug["sportscore"]["examples_targeted_results"]) < 30:
            debug["sportscore"]["examples_targeted_results"].append(
                {
                    key: value
                    for key, value in result.items()
                    if key != "context"
                }
            )

        if len(debug["sportscore"]["examples_targeted_contexts"]) < 30:
            debug["sportscore"]["examples_targeted_contexts"].append(
                {
                    "match": result.get("pick_match"),
                    "context": result.get("context"),
                    "winner": result.get("winner"),
                    "score": result.get("score"),
                }
            )

    debug["sportscore"]["targeted_results_found"] = len(targeted_results)

    return targeted_results + generic_results


def result_key(result):
    return "::".join(
        sorted([
            normalize(result.get("player1")),
            normalize(result.get("player2")),
        ])
    )


def combine_results(*result_groups):
    output = []
    seen = set()

    for group in result_groups:
        for result in group or []:
            key = result_key(result)

            if not key:
                continue

            if key in seen:
                continue

            seen.add(key)
            output.append(result)

    return output


def fetch_finished_results(picks=None):
    picks = picks or []
    debug = json.loads(json.dumps(DEBUG_TEMPLATE))
    debug["generated_at"] = now_utc_iso()
    debug["picks_received"] = len(picks)

    sofascore_results = fetch_sofascore_results(picks, debug)
    sportscore_results = fetch_sportscore_results(picks, debug)

    combined = combine_results(
        sofascore_results,
        sportscore_results,
    )

    debug["combined_results_found"] = len(combined)

    return combined, debug
```


## FILE: rss_results.py

```
import html
import json
import os
from datetime import datetime, timezone


RESULTS_DATA_PATHS = [
    "public/results_data.json",
]

RESULTS_PAGE_PATH = "public/results/index.html"
RESULTS_RSS_PATH = "public/results.xml"

SITE_TITLE = "BackstageTalks Statistic Model"
BASE_URL = "https://backstagetalks.github.io/tennis-backstage-talks"

HEADER_TITLE = "BackstageTalks Statistic Model"
HEADER_SUBTITLE = "This data is provided for informational and analytical purposes only"
FOOTER_TEXT = "Powered by BackstageTalks Statistic Model"


def safe(value, default="-"):
    if value is None:
        return default

    if value == "":
        return default

    return html.escape(str(value))


def pct(value):
    try:
        if value is None:
            return "-"

        return f"{float(value) * 100:.1f}%"

    except Exception:
        return "-"


def units(value):
    try:
        number = float(value)

        if number > 0:
            return f"+{number:.2f}u"

        if number < 0:
            return f"{number:.2f}u"

        return "0.00u"

    except Exception:
        return "0.00u"


def odds(value):
    try:
        return f"{float(value):.2f}"

    except Exception:
        return "-"


def load_json(path, default):
    try:
        if not os.path.exists(path):
            return default

        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    except Exception:
        return default


def empty_summary():
    return {
        "picks": 0,
        "won": 0,
        "lost": 0,
        "void": 0,
        "pending": 0,
        "unknown": 0,
        "units": 0.0,
        "win_rate": None,
    }


def empty_dataset(dataset):
    return {
        "dataset": dataset,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "today": empty_summary(),
        "last_7_days": empty_summary(),
        "current_month": empty_summary(),
        "all_time": empty_summary(),
        "items": [],
    }


def normalize_results_payload(data):
    if not isinstance(data, dict):
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "top5": empty_dataset("top5"),
            "all": empty_dataset("all"),
        }

    if "top5" in data and "all" in data:
        return data

    legacy = {
        "dataset": "legacy",
        "generated_at": data.get("generated_at"),
        "today": data.get("today", empty_summary()),
        "last_7_days": data.get("last_7_days", empty_summary()),
        "current_month": data.get("current_month", empty_summary()),
        "all_time": data.get("all_time", empty_summary()),
        "items": data.get("items", []),
    }

    return {
        "generated_at": data.get("generated_at") or datetime.now(timezone.utc).isoformat(),
        "top5": empty_dataset("top5"),
        "all": legacy,
    }


def load_results_data():
    for path in RESULTS_DATA_PATHS:
        data = load_json(path, None)

        if data:
            return normalize_results_payload(data)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "top5": empty_dataset("top5"),
        "all": empty_dataset("all"),
    }


def status_class(status):
    status = str(status or "PENDING").upper()

    if status == "WON":
        return "status-won"

    if status == "LOST":
        return "status-lost"

    if status == "VOID":
        return "status-void"

    if status == "UNKNOWN":
        return "status-unknown"

    return "status-pending"


def html_link(url, label):
    lt = chr(60)
    gt = chr(62)

    return (
        f'{lt}a href="{safe(url)}"{gt}'
        f'{safe(label)}'
        f'{lt}/a{gt}'
    )


def render_nav():
    links = [
        html_link(f"{BASE_URL}/", "TOP5"),
        html_link(f"{BASE_URL}/all/", "ALL"),
        html_link(f"{BASE_URL}/results/", "RESULTS"),
    ]

    return f"""
<nav class="nav" aria-label="Main navigation">
    {" ".join(links)}
</nav>
"""


def render_summary_card(label, summary):
    return f"""
<div class="summary-card">
    <div class="summary-label">{safe(label)}</div>

    <div class="summary-grid">
        <div>
            <span>Picks</span>
            <strong>{safe(summary.get("picks", 0))}</strong>
        </div>

        <div>
            <span>W-L</span>
            <strong>{safe(summary.get("won", 0))}-{safe(summary.get("lost", 0))}</strong>
        </div>

        <div>
            <span>Pending</span>
            <strong>{safe(summary.get("pending", 0))}</strong>
        </div>

        <div>
            <span>Units</span>
            <strong>{units(summary.get("units", 0))}</strong>
        </div>

        <div>
            <span>Win rate</span>
            <strong>{pct(summary.get("win_rate"))}</strong>
        </div>
    </div>
</div>
"""


def render_summary(data):
    return f"""
<div class="summary">
    {render_summary_card("Today", data.get("today", empty_summary()))}
    {render_summary_card("Last 7 days", data.get("last_7_days", empty_summary()))}
    {render_summary_card("Current month", data.get("current_month", empty_summary()))}
    {render_summary_card("All time", data.get("all_time", empty_summary()))}
</div>
"""


def render_rows(items):
    if not items:
        return """
<tr>
    <td colspan="9" class="empty">
        No results available yet.
    </td>
</tr>
"""

    rows = []

    for item in items[:300]:
        status = str(item.get("result_status") or "PENDING").upper()
        css = status_class(status)

        tournament = item.get("tournament")
        surface = item.get("surface")
        best_of = item.get("best_of")

        meta_parts = []

        if tournament:
            meta_parts.append(str(tournament))

        if surface:
            meta_parts.append(str(surface))

        if best_of:
            meta_parts.append(f"BO{best_of}")

        meta = " • ".join(meta_parts)

        rows.append(
            f"""
<tr>
    <td>{safe(item.get("date"))}</td>

    <td>
        <div class="pick">{safe(item.get("pick"))}</div>
        <div class="match">{safe(item.get("match"))}</div>
        <div class="meta">{safe(meta, "")}</div>
    </td>

    <td>{safe(item.get("opponent"))}</td>

    <td>{pct(item.get("probability"))}</td>

    <td>{odds(item.get("odds"))}</td>

    <td>
        <span class="status {css}">
            {safe(status)}
        </span>
    </td>

    <td>{safe(item.get("winner"))}</td>

    <td>{safe(item.get("score"))}</td>

    <td class="units">
        {units(item.get("units"))}
    </td>
</tr>
"""
        )

    return "\n".join(rows)


def render_table(items):
    rows = render_rows(items)

    return f"""
<div class="table-wrap">
    <table>
        <thead>
            <tr>
                <th>Date</th>
                <th>Pick</th>
                <th>Opponent</th>
                <th>Win %</th>
                <th>Odds</th>
                <th>Status</th>
                <th>Winner</th>
                <th>Score</th>
                <th>Units</th>
            </tr>
        </thead>

        <tbody>
            {rows}
        </tbody>
    </table>
</div>
"""


def render_dataset_section(title, subtitle, data):
    return f"""
<section class="dataset-section">
    <div class="section-header">
        <h2>{safe(title)}</h2>
        <p>{safe(subtitle)}</p>
    </div>

    {render_summary(data)}

    {render_table(data.get("items", []))}
</section>
"""


def render_page(data):
    nav = render_nav()

    top5_data = data.get("top5", empty_dataset("top5"))
    all_data = data.get("all", empty_dataset("all"))

    top5_section = render_dataset_section(
        "TOP5 Results",
        "Track record for the daily TOP5 snapshot.",
        top5_data,
    )

    all_section = render_dataset_section(
        "ALL Results",
        "Track record for all model-quality daily snapshot picks.",
        all_data,
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>{safe(SITE_TITLE)}</title>

<style>
:root {{
    --bg: #0f172a;
    --panel: #111827;
    --panel-2: #1e293b;
    --border: #334155;
    --text: #e5e7eb;
    --muted: #94a3b8;
    --green: #22c55e;
    --red: #ef4444;
    --yellow: #facc15;
    --blue: #38bdf8;
    --gray: #64748b;
}}

* {{
    box-sizing: border-box;
}}

html, body {{
    margin: 0;
    padding: 0;
    background: var(--bg);
    color: var(--text);
    font-family: Arial, Helvetica, sans-serif;
}}

.wrapper {{
    max-width: 1440px;
    margin: 0 auto;
    padding: 28px;
}}

.header {{
    display: grid;
    grid-template-columns: minmax(560px, 1fr) auto;
    gap: 40px;
    align-items: start;
    margin-bottom: 24px;
}}

.logo {{
    font-size: 30px;
    font-weight: 900;
    line-height: 1.15;
    color: var(--text);
    letter-spacing: 0.2px;
    white-space: nowrap;
}}

.subtitle {{
    color: var(--muted);
    margin-top: 10px;
    font-size: 14px;
    line-height: 1.45;
    max-width: 800px;
}}

.nav {{
    display: flex;
    gap: 18px;
    align-items: center;
    flex-wrap: nowrap;
    padding-top: 8px;
    white-space: nowrap;
}}

.nav a {{
    color: var(--text);
    text-decoration: none;
    font-weight: 900;
    font-size: 14px;
    letter-spacing: 0.04em;
}}

.nav a:hover {{
    color: var(--blue);
}}

.dataset-section {{
    margin-top: 30px;
}}

.section-header {{
    margin-bottom: 16px;
}}

.section-header h2 {{
    margin: 0;
    font-size: 24px;
    font-weight: 900;
    color: var(--text);
}}

.section-header p {{
    margin: 8px 0 0;
    color: var(--muted);
    font-size: 14px;
}}

.summary {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin-bottom: 22px;
}}

.summary-card {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 16px;
}}

.summary-label {{
    color: var(--blue);
    font-weight: 800;
    margin-bottom: 12px;
}}

.summary-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
}}

.summary-grid span {{
    display: block;
    color: var(--muted);
    font-size: 12px;
}}

.summary-grid strong {{
    display: block;
    font-size: 16px;
    margin-top: 3px;
}}

.table-wrap {{
    overflow-x: auto;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 16px;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    min-width: 1050px;
}}

thead {{
    background: var(--panel-2);
}}

th {{
    padding: 14px 12px;
    text-align: left;
    font-size: 13px;
    color: var(--muted);
    border-bottom: 1px solid var(--border);
    text-transform: uppercase;
    letter-spacing: 0.04em;
}}

td {{
    padding: 15px 12px;
    border-bottom: 1px solid var(--border);
    vertical-align: top;
}}

tr:hover {{
    background: rgba(255, 255, 255, 0.03);
}}

.pick {{
    font-weight: 800;
    color: var(--text);
}}

.match {{
    color: var(--muted);
    font-size: 12px;
    margin-top: 6px;
}}

.meta {{
    color: var(--blue);
    font-size: 12px;
    margin-top: 6px;
    font-weight: 700;
}}

.status {{
    display: inline-block;
    padding: 5px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 800;
}}

.status-won {{
    background: rgba(34, 197, 94, 0.18);
    color: var(--green);
    border: 1px solid rgba(34, 197, 94, 0.45);
}}

.status-lost {{
    background: rgba(239, 68, 68, 0.18);
    color: var(--red);
    border: 1px solid rgba(239, 68, 68, 0.45);
}}

.status-pending {{
    background: rgba(250, 204, 21, 0.16);
    color: var(--yellow);
    border: 1px solid rgba(250, 204, 21, 0.45);
}}

.status-void {{
    background: rgba(100, 116, 139, 0.18);
    color: var(--muted);
    border: 1px solid rgba(100, 116, 139, 0.45);
}}

.status-unknown {{
    background: rgba(56, 189, 248, 0.15);
    color: var(--blue);
    border: 1px solid rgba(56, 189, 248, 0.45);
}}

.units {{
    font-weight: 800;
}}

.empty {{
    text-align: center;
    color: var(--muted);
    padding: 40px;
}}

.footer {{
    max-width: 900px;
    margin: 38px auto 0;
    color: var(--muted);
    font-size: 12px;
    text-align: center;
    line-height: 1.7;
}}

@media (max-width: 1050px) {{
    .header {{
        display: block;
    }}

    .logo {{
        white-space: normal;
    }}

    .nav {{
        margin-top: 16px;
        padding-top: 0;
        flex-wrap: wrap;
    }}

    .summary {{
        grid-template-columns: 1fr 1fr;
    }}
}}

@media (max-width: 600px) {{
    .wrapper {{
        padding: 16px;
    }}

    .summary {{
        grid-template-columns: 1fr;
    }}
}}
</style>
</head>

<body>
<div class="wrapper">

    <div class="header">
        <div>
            <div class="logo">
                {safe(HEADER_TITLE)}
            </div>

            <div class="subtitle">
                {safe(HEADER_SUBTITLE)}
            </div>
        </div>

        {nav}
    </div>

    {top5_section}

    {all_section}

    <div class="footer">
        {safe(FOOTER_TEXT)}
    </div>

</div>
</body>
</html>
"""


def render_rss(data):
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    items = []

    rss_candidates = []

    for dataset_label, dataset_key in [
        ("TOP5", "top5"),
        ("ALL", "all"),
    ]:
        dataset = data.get(dataset_key, empty_dataset(dataset_key))

        for item in dataset.get("items", [])[:50]:
            rss_candidates.append(
                (
                    dataset_label,
                    item,
                )
            )

    for dataset_label, item in rss_candidates[:100]:
        title = (
            f"{dataset_label}: {item.get('pick')} vs {item.get('opponent')} "
            f"— {item.get('result_status', 'PENDING')}"
        )

        description_text = (
            f"Dataset: {dataset_label}\n"
            f"Date: {item.get('date')}\n"
            f"Match: {item.get('match')}\n"
            f"Pick: {item.get('pick')}\n"
            f"Opponent: {item.get('opponent')}\n"
            f"Odds: {odds(item.get('odds'))}\n"
            f"Win probability: {pct(item.get('probability'))}\n"
            f"Tournament: {item.get('tournament')}\n"
            f"Surface: {item.get('surface')}\n"
            f"Best of: {item.get('best_of')}\n"
            f"Status: {item.get('result_status')}\n"
            f"Winner: {item.get('winner')}\n"
            f"Score: {item.get('score')}\n"
            f"Units: {units(item.get('units'))}\n\n"
            f"{HEADER_SUBTITLE}\n"
            f"{FOOTER_TEXT}"
        )

        items.append(
            f"""
<item>
<title>{html.escape(str(title))}</title>
<link>{BASE_URL}/results/</link>
<description>{html.escape(description_text)}</description>
<pubDate>{now}</pubDate>
</item>
"""
        )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>{html.escape(SITE_TITLE)}</title>
<link>{BASE_URL}/results/</link>
<description>{html.escape(HEADER_TITLE)}</description>
{''.join(items)}
</channel>
</rss>
"""


def write_file(path, content):
    directory = os.path.dirname(path)

    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        file.write(content)


def run():
    data = load_results_data()

    page = render_page(data)
    rss = render_rss(data)

    write_file(RESULTS_PAGE_PATH, page)
    write_file(RESULTS_RSS_PATH, rss)

    print("RESULTS PAGE WRITTEN:", RESULTS_PAGE_PATH)
    print("RESULTS RSS WRITTEN:", RESULTS_RSS_PATH)


if __name__ == "__main__":
    run()
```


## FILE: sackmann_loader.py

```
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
        column_map[normalize_col_name(key)] = key

    return column_map


def get_first(row, candidates):
    column_map = build_column_map(row)

    for candidate in candidates:
        normalized = normalize_col_name(candidate)
        original_key = column_map.get(normalized)

        if original_key is not None:
            value = row.get(original_key)
            if value not in [None, ""]:
                return value

    return None


def parse_date(value):
    if not value:
        return "0"

    text = str(value).strip()

    # Sackmann: 20240701
    if re.match(r"^\d{8}$", text):
        return text

    # ISO: 2024-07-01
    try:
        if re.match(r"^\d{4}-\d{2}-\d{2}", text):
            return datetime.fromisoformat(text[:10]).strftime("%Y%m%d")
    except Exception:
        pass

    # Tennis-data style: 01/07/2024
    for fmt in ["%d/%m/%Y", "%m/%d/%Y", "%d.%m.%Y"]:
        try:
            return datetime.strptime(text[:10], fmt).strftime("%Y%m%d")
        except Exception:
            continue

    numbers = re.findall(r"\d+", text)
    if len(numbers) >= 3:
        joined = "".join(numbers[:3])
        if len(joined) >= 8:
            return joined[:8]

    return "0"


def detect_winner_loser(row):
    # Jeff Sackmann
    winner = get_first(row, [
        "winner_name",
        "winner",
        "Winner",
        "match_winner",
    ])

    loser = get_first(row, [
        "loser_name",
        "loser",
        "Loser",
        "match_loser",
    ])

    if winner and loser:
        return winner, loser

    # Home/Away + winner code formats
    home = get_first(row, [
        "home_player",
        "home_name",
        "home",
        "player_home",
        "player1",
        "player_1",
        "home_team",
    ])

    away = get_first(row, [
        "away_player",
        "away_name",
        "away",
        "player_away",
        "player2",
        "player_2",
        "away_team",
    ])

    winner_code = get_first(row, [
        "winner_code",
        "winner_id",
        "winner",
        "result",
        "match_winner_code",
    ])

    if home and away and winner_code is not None:
        code = str(winner_code).strip().lower()

        if code in ["1", "home", "h", "player1", "player_1"]:
            return home, away

        if code in ["2", "away", "a", "player2", "player_2"]:
            return away, home

    return None, None


def get_surface(row):
    return get_first(row, [
        "surface",
        "Surface",
        "court",
        "Court",
    ]) or "Hard"


def get_tournament(row):
    return get_first(row, [
        "tourney_name",
        "tournament",
        "Tournament",
        "event",
        "Event",
    ]) or ""


def get_level(row):
    return get_first(row, [
        "tourney_level",
        "level",
        "Level",
        "category",
        "Category",
    ]) or ""


def get_date(row):
    return parse_date(get_first(row, [
        "tourney_date",
        "date",
        "Date",
        "match_date",
        "start_date",
    ]))


def parse_rows(rows, source_label):
    parsed = []

    for row in rows:
        try:
            winner, loser = detect_winner_loser(row)

            if not winner or not loser:
                continue

            winner = str(winner).strip()
            loser = str(loser).strip()

            if not winner or not loser:
                continue

            # no doubles
            if "/" in winner or "/" in loser:
                continue

            parsed.append({
                "player1": winner,
                "player2": loser,
                "winner": winner,
                "surface": get_surface(row),
                "date": get_date(row),
                "tournament": get_tournament(row),
                "level": get_level(row),
                "source": source_label,
            })

        except Exception:
            continue

    return parsed


def load_github_source_year(source, year):
    url = source["url"].format(year)
    label = source["label"]

    rows = fetch_csv_rows(url)

    if not rows:
        print(label, year, "rows: 0")
        return []

    parsed = parse_rows(rows, label)

    print(label, year, "rows:", len(rows), "parsed:", len(parsed))

    return parsed


def fetch_tml_file_list():
    try:
        response = requests.get(TML_FILES_API, timeout=30)

        if response.status_code != 200:
            print("TML API ERROR:", response.status_code)
            return []

        data = response.json()
        files = data.get("files", [])

        if not isinstance(files, list):
            return []

        return files

    except Exception as e:
        print("TML API FETCH ERROR:", e)
        return []


def tml_file_matches_year(file_obj, year):
    name = str(file_obj.get("name", "")).lower()
    url = str(file_obj.get("url", "")).lower()

    if not name.endswith(".csv") and not url.endswith(".csv"):
        return False

    if str(year) not in name and str(year) not in url:
        return False

    banned = ["rank", "ranking", "player", "database", "ongoing_tourney"]

    for bad in banned:
        if bad in name:
            return False

    keywords = [
        str(year),
        "challenger",
        "qual",
        "atp",
        "wta",
    ]

    return any(keyword in name for keyword in keywords)


def load_tml_years(start_year, end_year):
    file_list = fetch_tml_file_list()

    if not file_list:
        print("TML FILE LIST EMPTY")
        return []

    all_matches = []

    for year in range(start_year, end_year + 1):
        year_files = [
            f for f in file_list
            if tml_file_matches_year(f, year)
        ]

        print("TML YEAR", year, "FILES:", len(year_files))

        for file_obj in year_files:
            name = file_obj.get("name", "")
            url = file_obj.get("url")

            if not url:
                continue

            rows = fetch_csv_rows(url)

            if not rows:
                print("TML", year, name, "rows: 0")
                continue

            label = f"TML_{name}"

            parsed = parse_rows(rows, label)

            print("TML", year, name, "rows:", len(rows), "parsed:", len(parsed))

            all_matches.extend(parsed)

    return all_matches


def load_all_matches(start_year=2018, end_year=2030):
    all_matches = []
    source_counts = {}

    print("LOADING GITHUB / SACKMANN SOURCES...")

    for year in range(start_year, end_year + 1):
        print("LOADING YEAR:", year)

        for source in GITHUB_SOURCES:
            matches = load_github_source_year(source, year)

            if not matches:
                continue

            label = source["label"]
            source_counts[label] = source_counts.get(label, 0) + len(matches)
            all_matches.extend(matches)

    if len(all_matches) < 1000:
        print("GITHUB SOURCES TOO SMALL, TRYING TENNISMYLIFE FALLBACK...")
        tml_matches = load_tml_years(start_year, end_year)

        for match in tml_matches:
            label = match.get("source", "TML")
            source_counts[label] = source_counts.get(label, 0) + 1

        all_matches.extend(tml_matches)

    # deduplicate
    deduped = {}

    for match in all_matches:
        key = (
            match.get("date"),
            match.get("player1"),
            match.get("player2"),
            match.get("winner"),
            match.get("surface"),
        )
        deduped[key] = match

    output = list(deduped.values())
    output.sort(key=lambda x: x.get("date") or "0")

    print("TOTAL MATCHES:", len(output))
    print("SOURCE COUNTS:", source_counts)

    return output
```


## FILE: sets_model.py

```
from typing import Any, Dict, Optional


def safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def normalize_probability(value: Any) -> Optional[float]:
    number = safe_float(value)
    if number is None:
        return None
    if number > 1.0:
        return number / 100.0
    return number


def favorite_side(probability_player1: Any, probability_player2: Any) -> str:
    p1 = normalize_probability(probability_player1) or 0.5
    p2 = normalize_probability(probability_player2) or 0.5
    return "p1" if p1 >= p2 else "p2"


def infer_bo(match: Dict[str, Any]) -> int:
    try:
        best_of = int(match.get("best_of") or 3)
        return 5 if best_of == 5 else 3
    except Exception:
        return 3


def infer_is_doubles(match: Dict[str, Any]) -> bool:
    text = " ".join([
        str(match.get("match") or ""),
        str(match.get("tournament") or ""),
        str(match.get("category") or ""),
    ]).lower()
    return "doubles" in text


def market_set_pressure(best_of: int, total_games: Optional[Dict[str, Any]], tie_break: Optional[Dict[str, Any]]) -> float:
    """
    Returns 0..1 where higher means longer/tighter match.
    Uses total games line, over probability and tie-break probability.
    """
    pressure = 0.50

    if isinstance(total_games, dict):
        line = safe_float(total_games.get("line"))
        over_prob = normalize_probability(total_games.get("over_probability"))

        if best_of == 5:
            if line is not None:
                # 34.5 short, 40.5 medium-long, 44.5 very long.
                pressure += (line - 38.5) / 18.0
        else:
            if line is not None:
                # 19.5 short, 22.5 medium, 24.5 long.
                pressure += (line - 22.0) / 10.0

        if over_prob is not None:
            pressure += (over_prob - 0.50) * 0.60

    if isinstance(tie_break, dict):
        tie_prob = normalize_probability(tie_break.get("yes_probability"))
        if tie_prob is not None:
            # Tie-break likely => tighter sets => longer match.
            pressure += (tie_prob - 0.35) * 0.35

    return clamp(pressure, 0.05, 0.95)


def dominance_score(match_probability: Optional[float], first_set_probability: Optional[float]) -> float:
    """
    0..1 dominance. Higher => cleaner/shorter win.
    """
    p_match = match_probability if match_probability is not None else 0.5
    p_first = first_set_probability if first_set_probability is not None else p_match
    return clamp(((p_match - 0.50) * 1.3) + ((p_first - 0.50) * 0.7), -0.45, 0.45)


def bo3_distribution(winner_side: str, match_prob: float, first_set_prob: Optional[float], pressure: float) -> Dict[str, float]:
    dom = dominance_score(match_prob, first_set_prob)
    three_sets = clamp(0.30 + pressure * 0.34 - max(dom, 0) * 0.20, 0.18, 0.62)
    fav_win = clamp(match_prob, 0.35, 0.85)
    fav_straight = clamp((1 - three_sets) * (0.55 + max(dom, 0) * 0.70), 0.20, 0.70)
    fav_deciding = clamp(three_sets * fav_win, 0.08, 0.45)
    dog_deciding = clamp(three_sets * (1 - fav_win), 0.05, 0.35)
    dog_straight = max(0.02, 1.0 - fav_straight - fav_deciding - dog_deciding)

    if winner_side == "p1":
        dist = {"2-0": fav_straight, "2-1": fav_deciding, "1-2": dog_deciding, "0-2": dog_straight}
    else:
        dist = {"0-2": fav_straight, "1-2": fav_deciding, "2-1": dog_deciding, "2-0": dog_straight}
    return normalize_dist(dist)


def bo5_distribution(winner_side: str, match_prob: float, first_set_prob: Optional[float], pressure: float) -> Dict[str, float]:
    dom = dominance_score(match_prob, first_set_prob)
    five_sets = clamp(0.16 + pressure * 0.28 - max(dom, 0) * 0.10, 0.08, 0.42)
    four_sets = clamp(0.30 + pressure * 0.10 - abs(dom) * 0.05, 0.20, 0.45)
    three_sets = clamp(1.0 - five_sets - four_sets, 0.20, 0.58)

    fav_win = clamp(match_prob, 0.35, 0.88)
    fav_three = three_sets * (0.62 + max(dom, 0) * 0.60)
    dog_three = max(0.01, three_sets - fav_three)
    fav_four = four_sets * fav_win
    dog_four = four_sets * (1 - fav_win)
    fav_five = five_sets * fav_win
    dog_five = five_sets * (1 - fav_win)

    if winner_side == "p1":
        dist = {"3-0": fav_three, "3-1": fav_four, "3-2": fav_five, "2-3": dog_five, "1-3": dog_four, "0-3": dog_three}
    else:
        dist = {"0-3": fav_three, "1-3": fav_four, "2-3": fav_five, "3-2": dog_five, "3-1": dog_four, "3-0": dog_three}
    return normalize_dist(dist)


def normalize_dist(dist: Dict[str, float]) -> Dict[str, float]:
    total = sum(max(v, 0.0) for v in dist.values())
    if total <= 0:
        return dist
    return {k: round(max(v, 0.0) / total, 4) for k, v in dist.items()}


def expected_sets_from_dist(dist: Dict[str, float]) -> float:
    total = 0.0
    for score, prob in dist.items():
        try:
            a, b = score.split("-")
            total += (int(a) + int(b)) * float(prob)
        except Exception:
            pass
    return round(total, 2)


def probability_of_max_sets(dist: Dict[str, float], best_of: int) -> float:
    max_sets = 5 if best_of == 5 else 3
    total = 0.0
    for score, prob in dist.items():
        try:
            a, b = score.split("-")
            if int(a) + int(b) == max_sets:
                total += float(prob)
        except Exception:
            pass
    return round(total, 4)


def most_likely_score(dist: Dict[str, float]) -> str:
    if not dist:
        return "-"
    return max(dist.items(), key=lambda item: item[1])[0]


def build_market_aware_sets(
    match: Dict[str, Any],
    elo_prediction: Dict[str, Any],
    odds_data: Optional[Dict[str, Any]] = None,
    set_markets: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    odds_data = odds_data or {}
    set_markets = set_markets or {}

    best_of = infer_bo(match)
    if infer_is_doubles(match):
        best_of = 3

    p1_model = normalize_probability(elo_prediction.get("probability_player1"))
    p2_model = normalize_probability(elo_prediction.get("probability_player2"))

    mw = set_markets.get("match_winner") if isinstance(set_markets, dict) else None
    fsw = set_markets.get("first_set_winner") if isinstance(set_markets, dict) else None
    tg = set_markets.get("total_games") if isinstance(set_markets, dict) else None
    tb = set_markets.get("tie_break") if isinstance(set_markets, dict) else None

    if isinstance(mw, dict) and mw.get("p1_probability") is not None:
        p1_match = float(mw["p1_probability"])
        p2_match = float(mw["p2_probability"])
    else:
        p1_match = p1_model if p1_model is not None else 0.5
        p2_match = p2_model if p2_model is not None else 1.0 - p1_match

    if p1_match >= p2_match:
        winner_side = "p1"
        match_prob = p1_match
        first_prob = fsw.get("p1_probability") if isinstance(fsw, dict) else None
    else:
        winner_side = "p2"
        match_prob = p2_match
        first_prob = fsw.get("p2_probability") if isinstance(fsw, dict) else None

    pressure = market_set_pressure(best_of, tg, tb)

    if best_of == 5:
        dist = bo5_distribution(winner_side, match_prob, first_prob, pressure)
        max_label = "5 Sets"
    else:
        dist = bo3_distribution(winner_side, match_prob, first_prob, pressure)
        max_label = "3 Sets"

    expected_sets = expected_sets_from_dist(dist)
    max_sets_prob = probability_of_max_sets(dist, best_of)
    score = most_likely_score(dist)

    games_line = tg.get("line") if isinstance(tg, dict) else None
    over_prob = tg.get("over_probability") if isinstance(tg, dict) else None
    games_pick = None
    if games_line is not None and over_prob is not None:
        games_pick = f"Over {games_line}" if over_prob >= 0.50 else f"Under {games_line}"

    return {
        "expected_sets": expected_sets,
        "sets_probability": max_sets_prob,
        "sets_probability_label": max_label,
        "most_likely_score": score,
        "most_likely_score_probability": dist.get(score),
        "score_probabilities": dist,
        "expected_games": games_line,
        "games_line": games_line,
        "games_pick": games_pick,
        "games_over_probability": round(float(over_prob), 4) if over_prob is not None else None,
        "tie_break_probability": tb.get("yes_probability") if isinstance(tb, dict) else None,
        "sets_model_source": "TennisApiMarkets" if set_markets else "ModelFallback",
    }
```


## FILE: src/__init__.py

```
"""
Root package marker for project modules.

This file must stay lightweight. Do not import submodules here, because
project code imports packages such as src.marq_ai and src.models directly.
"""

__all__ = []
```


## FILE: src/bst_ai/__init__.py

```
"""
BsT AI package.

BsT AI is a secondary TA data layer used only for comparison
against Corq AI.

Important rule:
- No fake data.
- No fallback probability.
- Never set BsT AI to 50%.
- If real data is missing, return No data.
"""
```


## FILE: src/bst_ai/matching.py

```
import re


def clean_text(value):
    if value is None:
        return ""

    text = str(value)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_name(name):
    text = clean_text(name).lower()
    text = re.sub(r"[^a-z0-9]+", "", text)

    return text


def normalize_tour(value):
    text = clean_text(value).lower()

    if text in ["atp", "men", "mens", "male", "m"]:
        return "ATP"

    if text in ["wta", "women", "womens", "female", "f"]:
        return "WTA"

    return None


def surface_key(surface):
    text = clean_text(surface).lower()

    if "hard" in text:
        return "hard"

    if "clay" in text:
        return "clay"

    if "grass" in text:
        return "grass"

    return None
```


## FILE: src/bst_ai/probability.py

```
import math


def elo_probability(rating_a, rating_b):
    if rating_a is None:
        return None

    if rating_b is None:
        return None

    try:
        rating_a = float(rating_a)
        rating_b = float(rating_b)

    except Exception:
        return None

    probability = 1.0 / (
        1.0 + math.pow(10.0, (rating_b - rating_a) / 400.0)
    )

    return probability
```


## FILE: src/bst_ai/rules.py

```
def safe_float(value):
    try:
        if value is None:
            return None

        if value == "":
            return None

        return float(value)

    except Exception:
        return None


def round_percent(value):
    if value is None:
        return None

    return round(value, 1)


def no_data_result(status="NO_DATA", reason=None):
    return {
        "corq_ai_probability": None,
        "bst_ai_probability": None,
        "ai_match": None,
        "ai_gap": None,
        "ai_signed_gap": None,
        "ai_lean": None,
        "ai_direction_match": None,
        "ai_match_color": "gray",
        "bst_ai_status": status,
        "bst_ai_reason": reason or status,
    }


def build_ai_match_result(corq_probability, bst_probability):
    corq_probability = safe_float(corq_probability)
    bst_probability = safe_float(bst_probability)

    if corq_probability is None:
        return no_data_result(
            status="NO_DATA",
            reason="Missing Corq AI probability.",
        )

    if bst_probability is None:
        return no_data_result(
            status="NO_DATA",
            reason="Missing BsT AI probability.",
        )

    corq_pct = corq_probability * 100.0
    bst_pct = bst_probability * 100.0

    signed_gap = corq_pct - bst_pct
    gap = abs(signed_gap)
    ai_match = 100.0 - gap

    if ai_match < 0:
        ai_match = 0.0

    corq_side = corq_probability >= 0.5
    bst_side = bst_probability >= 0.5

    direction_match = corq_side == bst_side

    if signed_gap > 0:
        ai_lean = "CORQ"

    elif signed_gap < 0:
        ai_lean = "BST"

    else:
        ai_lean = "TIE"

    if not direction_match:
        color = "red"

    elif signed_gap >= 0:
        color = "green"

    else:
        color = "orange"

    return {
        "corq_ai_probability": round(corq_probability, 3),
        "bst_ai_probability": round(bst_probability, 3),
        "ai_match": round_percent(ai_match),
        "ai_gap": round_percent(gap),
        "ai_signed_gap": round_percent(signed_gap),
        "ai_lean": ai_lean,
        "ai_direction_match": direction_match,
        "ai_match_color": color,
        "bst_ai_status": "OK",
        "bst_ai_reason": "OK",
    }
```


## FILE: src/bst_ai/service.py

```
import json
from functools import lru_cache
from pathlib import Path

from src.bst_ai.matching import (
    normalize_name,
    normalize_tour,
    surface_key,
)

from src.bst_ai.probability import elo_probability

from src.bst_ai.rules import (
    build_ai_match_result,
    no_data_result,
)


DATA_FILE = Path("data/bst_ai/players.json")


@lru_cache(maxsize=1)
def load_bst_ai_players():
    if not DATA_FILE.exists():
        return {
            "status": "NO_DATA",
            "players": [],
            "by_key": {},
            "by_tour_name": {},
        }

    try:
        with open(
            DATA_FILE,
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)

    except Exception:
        return {
            "status": "NO_DATA",
            "players": [],
            "by_key": {},
            "by_tour_name": {},
        }

    players = data.get("players", [])

    by_key = {}
    by_tour_name = {}

    for player in players:
        player_key = player.get("player_key")
        tour = player.get("tour")
        name_key = player.get("player_name_key")

        if player_key:
            by_key[player_key] = player

        if tour and name_key:
            by_tour_name[f"{tour}:{name_key}"] = player

    return {
        "status": data.get("status", "OK"),
        "players": players,
        "by_key": by_key,
        "by_tour_name": by_tour_name,
    }


def find_player(player_name, tour=None):
    data = load_bst_ai_players()

    if data.get("status") != "OK":
        return None

    name_key = normalize_name(player_name)

    if not name_key:
        return None

    normalized_tour = normalize_tour(tour)

    if normalized_tour:
        player = data["by_tour_name"].get(
            f"{normalized_tour}:{name_key}"
        )

        if player:
            return player

    for fallback_tour in ["ATP", "WTA"]:
        player = data["by_tour_name"].get(
            f"{fallback_tour}:{name_key}"
        )

        if player:
            return player

    return None


def get_pair_ratings(player_a, player_b, surface):
    key = surface_key(surface)

    if key:
        rating_a = (
            player_a.get("surface_elo", {})
            .get(key)
        )

        rating_b = (
            player_b.get("surface_elo", {})
            .get(key)
        )

        if rating_a is not None and rating_b is not None:
            return rating_a, rating_b, f"{key}_elo"

    rating_a = player_a.get("elo")
    rating_b = player_b.get("elo")

    if rating_a is not None and rating_b is not None:
        return rating_a, rating_b, "elo"

    rating_a = player_a.get("yelo")
    rating_b = player_b.get("yelo")

    if rating_a is not None and rating_b is not None:
        return rating_a, rating_b, "yelo"

    return None, None, None


def build_bst_ai_probability(
    player1,
    player2,
    pick,
    surface=None,
    tour=None,
):
    data = load_bst_ai_players()

    if data.get("status") != "OK":
        return {
            "status": "NO_DATA",
            "reason": "BsT AI data file is missing or unavailable.",
            "probability": None,
            "rating_type": None,
            "player1_found": False,
            "player2_found": False,
        }

    player1_data = find_player(
        player1,
        tour=tour,
    )

    player2_data = find_player(
        player2,
        tour=tour,
    )

    if not player1_data or not player2_data:
        return {
            "status": "PLAYER_NOT_FOUND",
            "reason": "One or both players were not found in BsT AI data.",
            "probability": None,
            "rating_type": None,
            "player1_found": bool(player1_data),
            "player2_found": bool(player2_data),
        }

    rating1, rating2, rating_type = get_pair_ratings(
        player1_data,
        player2_data,
        surface,
    )

    if rating1 is None or rating2 is None or not rating_type:
        return {
            "status": "INSUFFICIENT_DATA",
            "reason": "Players found, but no complete real rating pair is available.",
            "probability": None,
            "rating_type": None,
            "player1_found": True,
            "player2_found": True,
        }

    probability_player1 = elo_probability(
        rating1,
        rating2,
    )

    if probability_player1 is None:
        return {
            "status": "INSUFFICIENT_DATA",
            "reason": "Could not calculate BsT AI probability from real ratings.",
            "probability": None,
            "rating_type": rating_type,
            "player1_found": True,
            "player2_found": True,
        }

    if pick == player1:
        pick_probability = probability_player1

    elif pick == player2:
        pick_probability = 1.0 - probability_player1

    else:
        return {
            "status": "PLAYER_NOT_FOUND",
            "reason": "Pick player does not match player1 or player2.",
            "probability": None,
            "rating_type": rating_type,
            "player1_found": True,
            "player2_found": True,
        }

    return {
        "status": "OK",
        "reason": "OK",
        "probability": round(pick_probability, 3),
        "rating_type": rating_type,
        "player1_found": True,
        "player2_found": True,
    }


def build_bst_ai_comparison(
    player1,
    player2,
    pick,
    surface,
    corq_probability,
    tour=None,
):
    bst_result = build_bst_ai_probability(
        player1=player1,
        player2=player2,
        pick=pick,
        surface=surface,
        tour=tour,
    )

    if bst_result.get("status") != "OK":
        result = no_data_result(
            status=bst_result.get("status", "NO_DATA"),
            reason=bst_result.get("reason"),
        )

        result["corq_ai_probability"] = (
            round(corq_probability, 3)
            if corq_probability is not None
            else None
        )

        result["bst_ai_rating_type"] = bst_result.get("rating_type")
        result["bst_player1_found"] = bst_result.get("player1_found")
        result["bst_player2_found"] = bst_result.get("player2_found")

        return result

    result = build_ai_match_result(
        corq_probability=corq_probability,
        bst_probability=bst_result.get("probability"),
    )

    result["bst_ai_rating_type"] = bst_result.get("rating_type")
    result["bst_player1_found"] = bst_result.get("player1_found")
    result["bst_player2_found"] = bst_result.get("player2_found")

    return result
```


## FILE: src/bst_ai/ta_sync.py

```
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://www.tennisabstract.com"

OUTPUT_HTML_DIR = Path("public/bst_ai")
OUTPUT_DATA_DIR = Path("data/bst_ai")

REQUEST_TIMEOUT = 60

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/126.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Referer": "https://www.tennisabstract.com/",
}


@dataclass(frozen=True)
class TAReport:
    report_id: str
    tour: str
    report_type: str
    urls: list
    html_file: str
    json_file: str


REPORTS = [
    TAReport(
        report_id="atp_elo",
        tour="ATP",
        report_type="elo",
        urls=[
            "https://www.tennisabstract.com/reports/atp_elo_ratings.html",
            "https://tennisabstract.com/reports/atp_elo_ratings.html",
            "http://www.tennisabstract.com/reports/atp_elo_ratings.html",
            "http://tennisabstract.com/reports/atp_elo_ratings.html",
        ],
        html_file="atp_elo.html",
        json_file="atp_elo.json",
    ),
    TAReport(
        report_id="atp_yelo",
        tour="ATP",
        report_type="yelo",
        urls=[
            "https://www.tennisabstract.com/reports/atp_season_yelo_ratings.html",
            "https://tennisabstract.com/reports/atp_season_yelo_ratings.html",
            "http://www.tennisabstract.com/reports/atp_season_yelo_ratings.html",
            "http://tennisabstract.com/reports/atp_season_yelo_ratings.html",
        ],
        html_file="atp_yelo.html",
        json_file="atp_yelo.json",
    ),
    TAReport(
        report_id="wta_elo",
        tour="WTA",
        report_type="elo",
        urls=[
            "https://www.tennisabstract.com/reports/wta_elo_ratings.html",
            "https://tennisabstract.com/reports/wta_elo_ratings.html",
            "http://www.tennisabstract.com/reports/wta_elo_ratings.html",
            "http://tennisabstract.com/reports/wta_elo_ratings.html",
        ],
        html_file="wta_elo.html",
        json_file="wta_elo.json",
    ),
    TAReport(
        report_id="wta_yelo",
        tour="WTA",
        report_type="yelo",
        urls=[
            "https://www.tennisabstract.com/reports/wta_season_yelo_ratings.html",
            "https://tennisabstract.com/reports/wta_season_yelo_ratings.html",
            "http://www.tennisabstract.com/reports/wta_season_yelo_ratings.html",
            "http://tennisabstract.com/reports/wta_season_yelo_ratings.html",
        ],
        html_file="wta_yelo.html",
        json_file="wta_yelo.json",
    ),
]


def utc_now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def ensure_dirs():
    OUTPUT_HTML_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DATA_DIR.mkdir(parents=True, exist_ok=True)


def clean_text(value):
    if value is None:
        return ""

    text = str(value)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_name(name):
    text = clean_text(name).lower()
    text = re.sub(r"[^a-z0-9]+", "", text)

    return text


def to_float(value):
    text = clean_text(value)

    if not text:
        return None

    text = text.replace(",", "")

    try:
        return float(text)
    except Exception:
        return None


def to_int(value):
    number = to_float(value)

    if number is None:
        return None

    return int(number)


def extract_player_id_from_href(href):
    if not href:
        return None

    absolute_url = urljoin(BASE_URL, href)
    parsed = urlparse(absolute_url)
    params = parse_qs(parsed.query)

    player_ids = params.get("p")

    if not player_ids:
        return None

    player_id = clean_text(player_ids[0])

    if not player_id:
        return None

    return player_id


def parse_player_cell(cell):
    player_name = clean_text(cell.get_text(" "))

    player_id = None
    player_url = None

    link = cell.find("a", href=True)

    if link:
        player_id = extract_player_id_from_href(
            link.get("href", "")
        )

        if player_id:
            player_url = f"{BASE_URL}/cgi-bin/player.cgi?p={player_id}"

    return {
        "player_name": player_name,
        "player_id": player_id,
        "player_url": player_url,
    }


def normalize_table_cells(raw_cells):
    """
    TA Elo tables include visual spacer cells between column groups.
    Those empty cells break fixed-index parsing.

    This helper removes only visually empty cells before mapping:
    Rank, Player, Age, Elo, hElo Rank, hElo,
    cElo Rank, cElo, gElo Rank, gElo,
    Peak Elo, Peak Month, ATP/WTA Rank, Log diff.
    """
    return [
        cell
        for cell in raw_cells
        if clean_text(cell.get_text(" "))
    ]


def download_html(report):
    errors = []

    for url in report.urls:
        try:
            response = requests.get(
                url,
                headers=HEADERS,
                timeout=REQUEST_TIMEOUT,
                allow_redirects=True,
            )

            if response.status_code == 403:
                errors.append(f"403 Forbidden: {url}")
                continue

            response.raise_for_status()

            html_text = response.text

            if "Player" not in html_text and "Elo" not in html_text and "yElo" not in html_text:
                errors.append(f"Unexpected HTML content: {url}")
                continue

            output_file = OUTPUT_HTML_DIR / report.html_file
            output_file.write_text(
                html_text,
                encoding="utf-8",
            )

            return html_text, url, errors

        except Exception as exc:
            errors.append(f"{url}: {exc}")

    return None, None, errors


def load_existing_report(report):
    path = OUTPUT_DATA_DIR / report.json_file

    if not path.exists():
        return None

    try:
        with open(path, "r", encoding="utf-8") as file:
            data = json.load(file)

        if isinstance(data, dict) and data.get("records"):
            data["source_status"] = "CACHE_USED"
            data.setdefault("warnings", [])
            data["warnings"].append(
                "Live TA source unavailable; using previously stored real TA data."
            )
            return data

    except Exception:
        return None

    return None


def find_main_table(soup):
    tables = soup.find_all("table")

    if not tables:
        return None

    best_table = None
    best_score = -1

    for table in tables:
        text = clean_text(
            table.get_text(" ")
        )

        rows = table.find_all("tr")

        score = len(rows)

        if "Player" in text:
            score += 1000

        if "Elo" in text or "yElo" in text:
            score += 1000

        if score > best_score:
            best_score = score
            best_table = table

    return best_table


def parse_last_update(soup):
    text = clean_text(
        soup.get_text(" ")
    )

    match = re.search(
        r"Last update:\s*([0-9]{4}-[0-9]{2}-[0-9]{2})",
        text,
    )

    if not match:
        return None

    return match.group(1)


def get_cells(row):
    return row.find_all(["td", "th"])


def looks_like_elo_rating(value):
    number = to_float(value)

    if number is None:
        return False

    return 1000 <= number <= 3000


def parse_standard_elo_row(cells, report, player_info):
    cells = normalize_table_cells(cells)

    if len(cells) < 10:
        return None

    h_elo = to_float(cells[5].get_text(" ")) if len(cells) > 5 else None
    c_elo = to_float(cells[7].get_text(" ")) if len(cells) > 7 else None
    g_elo = to_float(cells[9].get_text(" ")) if len(cells) > 9 else None

    warnings = []

    if h_elo is not None and not looks_like_elo_rating(h_elo):
        warnings.append(f"Invalid hElo parsed for {player_info.get('player_name')}: {h_elo}")
        h_elo = None

    if c_elo is not None and not looks_like_elo_rating(c_elo):
        warnings.append(f"Invalid cElo parsed for {player_info.get('player_name')}: {c_elo}")
        c_elo = None

    if g_elo is not None and not looks_like_elo_rating(g_elo):
        warnings.append(f"Invalid gElo parsed for {player_info.get('player_name')}: {g_elo}")
        g_elo = None

    record = {
        "tour": report.tour,
        "source": report.report_id,
        "report_type": "elo",
        "player_id": player_info.get("player_id"),
        "player_name": player_info.get("player_name"),
        "player_name_key": normalize_name(
            player_info.get("player_name") or ""
        ),
        "player_url": player_info.get("player_url"),
        "rank": to_int(cells[0].get_text(" ")) if len(cells) > 0 else None,
        "age": to_float(cells[2].get_text(" ")) if len(cells) > 2 else None,
        "elo": to_float(cells[3].get_text(" ")) if len(cells) > 3 else None,
        "h_elo_rank": to_int(cells[4].get_text(" ")) if len(cells) > 4 else None,
        "h_elo": h_elo,
        "c_elo_rank": to_int(cells[6].get_text(" ")) if len(cells) > 6 else None,
        "c_elo": c_elo,
        "g_elo_rank": to_int(cells[8].get_text(" ")) if len(cells) > 8 else None,
        "g_elo": g_elo,
        "peak_elo": to_float(cells[10].get_text(" ")) if len(cells) > 10 else None,
        "peak_month": clean_text(cells[11].get_text(" ")) if len(cells) > 11 else None,
        "official_rank": to_int(cells[12].get_text(" ")) if len(cells) > 12 else None,
        "log_diff": to_float(cells[13].get_text(" ")) if len(cells) > 13 else None,
    }

    if warnings:
        record["parse_warnings"] = warnings

    return record


def parse_yelo_row(cells, report, player_info):
    cells = normalize_table_cells(cells)

    if len(cells) < 5:
        return None

    return {
        "tour": report.tour,
        "source": report.report_id,
        "report_type": "yelo",
        "player_id": player_info.get("player_id"),
        "player_name": player_info.get("player_name"),
        "player_name_key": normalize_name(
            player_info.get("player_name") or ""
        ),
        "player_url": player_info.get("player_url"),
        "rank": to_int(cells[0].get_text(" ")),
        "wins": to_int(cells[2].get_text(" ")),
        "losses": to_int(cells[3].get_text(" ")),
        "yelo": to_float(cells[4].get_text(" ")),
    }


def parse_report(html_text, report, source_url):
    soup = BeautifulSoup(
        html_text,
        "html.parser",
    )

    table = find_main_table(
        soup,
    )

    parsed_at = utc_now_iso()
    last_update = parse_last_update(
        soup,
    )

    records = []
    warnings = []

    if table is None:
        return {
            "schema": "bst_ai_report_v1",
            "report_id": report.report_id,
            "tour": report.tour,
            "type": report.report_type,
            "source_url": source_url,
            "last_update": last_update,
            "parsed_at": parsed_at,
            "status": "NO_TABLE_FOUND",
            "source_status": "LIVE_OK",
            "record_count": 0,
            "records": [],
            "warnings": ["Main ratings table was not found."],
        }

    rows = table.find_all("tr")

    for row in rows:
        raw_cells = get_cells(row)
        cells = normalize_table_cells(raw_cells)

        if len(cells) < 4:
            continue

        rank_text = clean_text(
            cells[0].get_text(" ")
        )

        if not rank_text:
            continue

        if not rank_text[0].isdigit():
            continue

        player_info = parse_player_cell(
            cells[1],
        )

        if not player_info.get("player_name"):
            continue

        if report.report_type == "elo":
            record = parse_standard_elo_row(
                raw_cells,
                report,
                player_info,
            )

        elif report.report_type == "yelo":
            record = parse_yelo_row(
                raw_cells,
                report,
                player_info,
            )

        else:
            record = None

        if record:
            if record.get("parse_warnings"):
                warnings.extend(record.get("parse_warnings"))
            records.append(record)

    if not records:
        warnings.append(
            "No records parsed from table."
        )

    return {
        "schema": "bst_ai_report_v1",
        "report_id": report.report_id,
        "tour": report.tour,
        "type": report.report_type,
        "source_url": source_url,
        "last_update": last_update,
        "parsed_at": parsed_at,
        "status": "OK" if records else "NO_RECORDS",
        "source_status": "LIVE_OK",
        "record_count": len(records),
        "records": records,
        "warnings": warnings,
    }


def failed_report(report, errors):
    return {
        "schema": "bst_ai_report_v1",
        "report_id": report.report_id,
        "tour": report.tour,
        "type": report.report_type,
        "source_url": None,
        "last_update": None,
        "parsed_at": utc_now_iso(),
        "status": "SOURCE_UNAVAILABLE",
        "source_status": "LIVE_FAILED",
        "record_count": 0,
        "records": [],
        "warnings": errors,
    }


def merge_players(report_outputs):
    players = {}
    warnings = []

    for report_output in report_outputs:
        report_id = report_output.get("report_id")

        for warning in report_output.get("warnings", []):
            if "Invalid" in str(warning):
                warnings.append(warning)

        for record in report_output.get("records", []):
            player_id = record.get("player_id")
            player_name = record.get("player_name")
            player_name_key = record.get("player_name_key")
            tour = record.get("tour")

            if not player_id:
                warnings.append(
                    f"Missing player_id in {report_id}: {player_name}"
                )
                continue

            key = f"{tour}:{player_id}"

            if key not in players:
                players[key] = {
                    "player_key": key,
                    "player_id": player_id,
                    "player_name": player_name,
                    "player_name_key": player_name_key,
                    "player_url": record.get("player_url"),
                    "tour": tour,
                    "sources": [],
                    "elo": None,
                    "yelo": None,
                    "surface_elo": {
                        "hard": None,
                        "clay": None,
                        "grass": None,
                    },
                    "surface_elo_rank": {
                        "hard": None,
                        "clay": None,
                        "grass": None,
                    },
                    "ranking": {},
                    "season": {},
                    "status": "OK",
                }

            player = players[key]

            if report_id not in player["sources"]:
                player["sources"].append(report_id)

            if record.get("report_type") == "elo":
                player["elo"] = record.get("elo")
                player["surface_elo"]["hard"] = record.get("h_elo")
                player["surface_elo"]["clay"] = record.get("c_elo")
                player["surface_elo"]["grass"] = record.get("g_elo")
                player["surface_elo_rank"]["hard"] = record.get("h_elo_rank")
                player["surface_elo_rank"]["clay"] = record.get("c_elo_rank")
                player["surface_elo_rank"]["grass"] = record.get("g_elo_rank")
                player["ranking"]["elo_rank"] = record.get("rank")
                player["ranking"]["official_rank"] = record.get("official_rank")
                player["ranking"]["peak_elo"] = record.get("peak_elo")
                player["ranking"]["peak_month"] = record.get("peak_month")

            elif record.get("report_type") == "yelo":
                player["yelo"] = record.get("yelo")
                player["season"]["yelo_rank"] = record.get("rank")
                player["season"]["wins"] = record.get("wins")
                player["season"]["losses"] = record.get("losses")

    players_list = sorted(
        players.values(),
        key=lambda item: (
            item.get("tour") or "",
            item.get("player_name") or "",
        ),
    )

    return {
        "schema": "bst_ai_players_v2",
        "created_at": utc_now_iso(),
        "status": "OK" if players_list else "NO_DATA",
        "player_count": len(players_list),
        "players": players_list,
        "warnings": warnings,
        "rules": {
            "real_data_only": True,
            "no_fallback_probability": True,
            "never_use_bst_ai_50_percent": True,
            "missing_data_output": "No data",
            "surface_elo_must_be_rating_not_rank": True,
        },
    }


def write_json(path, data):
    path.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )


def write_status(report_outputs, players_index):
    live_failed_count = sum(
        1
        for report in report_outputs
        if report.get("source_status") == "LIVE_FAILED"
    )

    cache_used_count = sum(
        1
        for report in report_outputs
        if report.get("source_status") == "CACHE_USED"
    )

    if live_failed_count == len(report_outputs):
        status_value = "SOURCE_UNAVAILABLE"

    elif live_failed_count > 0 or cache_used_count > 0:
        status_value = "PARTIAL_OK"

    else:
        status_value = "OK"

    status = {
        "schema": "bst_ai_status_v2",
        "created_at": utc_now_iso(),
        "status": status_value,
        "reports": [
            {
                "report_id": report.get("report_id"),
                "tour": report.get("tour"),
                "type": report.get("type"),
                "source_url": report.get("source_url"),
                "last_update": report.get("last_update"),
                "parsed_at": report.get("parsed_at"),
                "status": report.get("status"),
                "source_status": report.get("source_status"),
                "record_count": report.get("record_count", 0),
                "warnings": report.get("warnings", []),
            }
            for report in report_outputs
        ],
        "player_count": players_index.get("player_count", 0),
        "warnings": players_index.get("warnings", []),
        "rules": {
            "real_data_only": True,
            "bst_ai_fallback_50_percent": False,
            "if_missing_data": "No data",
            "surface_elo_must_be_rating_not_rank": True,
        },
    }

    write_json(
        OUTPUT_DATA_DIR / "status.json",
        status,
    )


def main():
    ensure_dirs()

    report_outputs = []

    for report in REPORTS:
        print(
            f"Downloading {report.report_id}"
        )

        html_text, source_url, errors = download_html(
            report,
        )

        if html_text and source_url:
            parsed = parse_report(
                html_text,
                report,
                source_url,
            )

            write_json(
                OUTPUT_DATA_DIR / report.json_file,
                parsed,
            )

            print(
                f"Saved {report.report_id}: "
                f"{parsed.get('record_count', 0)} records"
            )

            report_outputs.append(
                parsed,
            )
            continue

        cached = load_existing_report(
            report,
        )

        if cached:
            print(
                f"Live source failed for {report.report_id}; using cached real data."
            )

            report_outputs.append(
                cached,
            )
            continue

        failed = failed_report(
            report,
            errors,
        )

        write_json(
            OUTPUT_DATA_DIR / report.json_file,
            failed,
        )

        print(
            f"Failed {report.report_id}: SOURCE_UNAVAILABLE"
        )

        report_outputs.append(
            failed,
        )

    players_index = merge_players(
        report_outputs,
    )

    write_json(
        OUTPUT_DATA_DIR / "players.json",
        players_index,
    )

    write_status(
        report_outputs,
        players_index,
    )

    print(
        "BsT AI sync completed."
    )


if __name__ == "__main__":
    main()
```


## FILE: src/elo/README.md

```
ELO STORE

Sources:

ATP Elo
https://tennisabstract.com/reports/atp_elo_ratings.html

WTA Elo
https://tennisabstract.com/reports/wta_elo_ratings.html

ATP yElo
https://tennisabstract.com/reports/atp_season_yelo_ratings.html

WTA yElo
https://tennisabstract.com/reports/wta_season_yelo_ratings.html

Files:

atp_elo_latest.csv
wta_elo_latest.csv

atp_yelo_latest.csv
wta_yelo_latest.csv

elo_history.csv

Purpose:

- historical snapshots
- trends
- win probability inputs
- betting statistics
- future backtesting
```


## FILE: src/elo/__init__.py

```
# package marker
```


## FILE: src/elo/clean.py

```
import pandas as pd


def clean_elo(df):

    df = df.copy()

    df.columns = [str(c).strip() for c in df.columns]

    if "Player" in df.columns:
        df["Player"] = (
            df["Player"]
            .astype(str)
            .str.replace("\xa0", " ", regex=False)
            .str.strip()
        )

    return df
```


## FILE: src/elo/consensus.py

```
def clamp(value, low, high):
    return max(low, min(high, value))


def calculate_consensus(
    tbt_ai,
    tbt_elo,
    tbt_yelo,
):
    """
    Inputs:
        0.00 - 1.00

    Example:
        tbt_ai   = 0.72
        tbt_elo  = 0.70
        tbt_yelo = 0.74
    """

    values = [
        float(tbt_ai),
        float(tbt_elo),
        float(tbt_yelo),
    ]

    spread = max(values) - min(values)

    # 0 spread = perfect agreement
    # 0.30 spread = terrible agreement

    normalized = 1.0 - (spread / 0.30)

    score = int(
        round(
            clamp(normalized, 0.0, 1.0) * 100
        )
    )

    if score >= 80:
        label = "HIGH"

    elif score >= 60:
        label = "MEDIUM"

    else:
        label = "LOW"

    return {
        "score": score,
        "label": label,
        "spread": round(spread, 3),
    }
```


## FILE: src/elo/elo_engine.py

```
import os
import csv
import json
import unicodedata
from difflib import SequenceMatcher


DEFAULT_ELO = 1500.0

ALIASES_PATH = "data/player_aliases.json"
ELO_DEBUG_PATH = "public/elo_debug.json"


ELO_CANDIDATE_FILES = [
    "data/elo/elo_store.json",
    "data/elo/elo.json",
    "data/elo/atp_elo_latest.csv",
    "data/elo/wta_elo_latest.csv",
    "data/elo/latest_elo.csv",
    "data/elo/elo_latest.csv",
    "elo_store.json",
    "elo.json",
]


_DEBUG = {
    "provider": "elo_engine_v2_safe_matcher",
    "loaded_files": [],
    "players_loaded": 0,

    "lookup_count": 0,
    "found_count": 0,
    "missing_count": 0,

    "examples_found": [],
    "examples_missing": [],
}


def write_debug():
    os.makedirs(
        "public",
        exist_ok=True,
    )

    with open(
        ELO_DEBUG_PATH,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            _DEBUG,
            file,
            indent=2,
            ensure_ascii=False,
        )


def normalize_name(name):
    if not name:
        return ""

    value = str(name)

    value = unicodedata.normalize(
        "NFKD",
        value,
    )

    value = "".join(
        char
        for char in value
        if not unicodedata.combining(char)
    )

    value = value.lower()

    value = value.replace("-", " ")
    value = value.replace(".", " ")
    value = value.replace(",", " ")
    value = value.replace("'", "")
    value = value.replace("’", "")
    value = value.replace("`", "")

    return " ".join(value.split())


def similarity(a, b):
    return SequenceMatcher(
        None,
        normalize_name(a),
        normalize_name(b),
    ).ratio()


def last_name(name):
    normalized = normalize_name(name)

    if not normalized:
        return ""

    parts = normalized.split()

    return parts[-1]


def first_token(name):
    normalized = normalize_name(name)

    if not normalized:
        return ""

    parts = normalized.split()

    return parts[0]


def load_aliases():
    if not os.path.exists(ALIASES_PATH):
        return {}

    try:
        with open(
            ALIASES_PATH,
            "r",
            encoding="utf-8",
        ) as file:
            raw_aliases = json.load(file)

    except Exception:
        return {}

    aliases = {}

    for alias, canonical in raw_aliases.items():
        aliases[
            normalize_name(alias)
        ] = canonical

    return aliases


def safe_float(value, default=None):
    try:
        if value is None:
            return default

        if value == "":
            return default

        return float(value)

    except Exception:
        return default


def detect_name(row):
    for key in [
        "player",
        "Player",
        "name",
        "Name",
        "player_name",
        "Player Name",
    ]:
        if key in row and row.get(key):
            return row.get(key)

    return None


def detect_elo(row):
    candidates = [
        "elo",
        "Elo",
        "ELO",
        "rating",
        "Rating",
        "overall_elo",
        "overall",
        "Overall",
    ]

    for key in candidates:
        if key in row:
            value = safe_float(row.get(key))

            if value is not None:
                return value

    return None


def detect_yelo(row):
    candidates = [
        "yelo",
        "Yelo",
        "YELO",
        "year_elo",
        "season_elo",
    ]

    for key in candidates:
        if key in row:
            value = safe_float(row.get(key))

            if value is not None:
                return value

    return None


def detect_surface_elos(row):
    surfaces = {}

    mapping = {
        "hard": [
            "hard_elo",
            "Hard Elo",
            "hard",
            "Hard",
        ],
        "clay": [
            "clay_elo",
            "Clay Elo",
            "clay",
            "Clay",
        ],
        "grass": [
            "grass_elo",
            "Grass Elo",
            "grass",
            "Grass",
        ],
        "indoor": [
            "indoor_elo",
            "Indoor Elo",
            "indoor",
            "Indoor",
        ],
    }

    for surface, keys in mapping.items():
        for key in keys:
            if key in row:
                value = safe_float(row.get(key))

                if value is not None:
                    surfaces[surface] = value
                    break

    return surfaces


def add_record(store, name, record):
    if not name:
        return

    normalized = normalize_name(name)

    if not normalized:
        return

    record["name"] = name
    record["normalized_name"] = normalized

    store[normalized] = record


def load_json_file(path):
    store = {}

    with open(
        path,
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    if isinstance(data, dict):

        if "players" in data:
            players = data.get("players")

            if isinstance(players, dict):
                iterable = players.items()

                for name, value in iterable:
                    if isinstance(value, dict):
                        elo = safe_float(
                            value.get("elo")
                            or value.get("rating")
                            or value.get("overall_elo"),
                            DEFAULT_ELO,
                        )

                        yelo = safe_float(
                            value.get("yelo")
                            or value.get("year_elo")
                            or value.get("season_elo"),
                            elo,
                        )

                        surfaces = value.get("surfaces") or {}

                        record = {
                            "elo": elo,
                            "yelo": yelo,
                            "surfaces": surfaces,
                            "source": path,
                            "raw": value,
                        }

                        add_record(
                            store,
                            name,
                            record,
                        )

            elif isinstance(players, list):
                for value in players:
                    if not isinstance(value, dict):
                        continue

                    name = detect_name(value)

                    if not name:
                        continue

                    elo = detect_elo(value)

                    if elo is None:
                        elo = DEFAULT_ELO

                    yelo = detect_yelo(value)

                    if yelo is None:
                        yelo = elo

                    record = {
                        "elo": elo,
                        "yelo": yelo,
                        "surfaces": detect_surface_elos(value),
                        "source": path,
                        "raw": value,
                    }

                    add_record(
                        store,
                        name,
                        record,
                    )

        else:
            for name, value in data.items():
                if isinstance(value, dict):
                    elo = safe_float(
                        value.get("elo")
                        or value.get("rating")
                        or value.get("overall_elo"),
                        DEFAULT_ELO,
                    )

                    yelo = safe_float(
                        value.get("yelo")
                        or value.get("year_elo")
                        or value.get("season_elo"),
                        elo,
                    )

                    record = {
                        "elo": elo,
                        "yelo": yelo,
                        "surfaces": value.get("surfaces") or {},
                        "source": path,
                        "raw": value,
                    }

                    add_record(
                        store,
                        name,
                        record,
                    )

                else:
                    elo = safe_float(value)

                    if elo is not None:
                        record = {
                            "elo": elo,
                            "yelo": elo,
                            "surfaces": {},
                            "source": path,
                            "raw": value,
                        }

                        add_record(
                            store,
                            name,
                            record,
                        )

    elif isinstance(data, list):
        for value in data:
            if not isinstance(value, dict):
                continue

            name = detect_name(value)

            if not name:
                continue

            elo = detect_elo(value)

            if elo is None:
                elo = DEFAULT_ELO

            yelo = detect_yelo(value)

            if yelo is None:
                yelo = elo

            record = {
                "elo": elo,
                "yelo": yelo,
                "surfaces": detect_surface_elos(value),
                "source": path,
                "raw": value,
            }

            add_record(
                store,
                name,
                record,
            )

    return store


def load_csv_file(path):
    store = {}

    with open(
        path,
        "r",
        encoding="utf-8",
        newline="",
    ) as file:
        reader = csv.DictReader(file)

        for row in reader:
            name = detect_name(row)

            if not name:
                continue

            elo = detect_elo(row)

            if elo is None:
                elo = DEFAULT_ELO

            yelo = detect_yelo(row)

            if yelo is None:
                yelo = elo

            record = {
                "elo": elo,
                "yelo": yelo,
                "surfaces": detect_surface_elos(row),
                "source": path,
                "raw": row,
            }

            add_record(
                store,
                name,
                record,
            )

    return store


def load():
    """
    Existing prediction engines call this function.

    Returns:
        dict normalized_name -> player ELO record
    """

    store = {}

    for path in ELO_CANDIDATE_FILES:
        if not os.path.exists(path):
            continue

        try:
            if path.endswith(".json"):
                loaded = load_json_file(path)

            elif path.endswith(".csv"):
                loaded = load_csv_file(path)

            else:
                loaded = {}

            if loaded:
                store.update(loaded)

                _DEBUG["loaded_files"].append({
                    "path": path,
                    "players": len(loaded),
                })

        except Exception as exc:
            _DEBUG["loaded_files"].append({
                "path": path,
                "error": str(exc),
            })

    _DEBUG["players_loaded"] = len(store)

    write_debug()

    return store


def candidate_matches_by_initial(player_name, store):
    normalized = normalize_name(player_name)
    parts = normalized.split()

    if len(parts) < 2:
        return []

    first = parts[0]
    last = parts[-1]

    if len(first) != 1:
        return []

    matches = []

    for key, record in store.items():
        rec_name = record.get("name", key)
        rec_first = first_token(rec_name)
        rec_last = last_name(rec_name)

        if rec_last == last and rec_first.startswith(first):
            matches.append((key, record, 1.0))

    return matches


def find_player_record(player_name, store):
    """
    Safe player lookup.

    Order:
    1. exact normalized match
    2. alias match
    3. initial + last name match
    4. conservative fuzzy match
    """

    _DEBUG["lookup_count"] += 1

    aliases = load_aliases()
    normalized = normalize_name(player_name)

    if not normalized:
        _DEBUG["missing_count"] += 1

        return {
            "found": False,
            "record": None,
            "matched_name": None,
            "match_method": "empty",
            "match_score": 0.0,
        }

    # 1. exact normalized
    if normalized in store:
        record = store[normalized]

        _DEBUG["found_count"] += 1

        if len(_DEBUG["examples_found"]) < 30:
            _DEBUG["examples_found"].append({
                "input": player_name,
                "matched": record.get("name"),
                "method": "exact",
                "score": 1.0,
            })

        return {
            "found": True,
            "record": record,
            "matched_name": record.get("name"),
            "match_method": "exact",
            "match_score": 1.0,
        }

    # 2. alias
    alias_target = aliases.get(normalized)

    if alias_target:
        alias_normalized = normalize_name(alias_target)

        if alias_normalized in store:
            record = store[alias_normalized]

            _DEBUG["found_count"] += 1

            if len(_DEBUG["examples_found"]) < 30:
                _DEBUG["examples_found"].append({
                    "input": player_name,
                    "matched": record.get("name"),
                    "method": "alias",
                    "score": 1.0,
                })

            return {
                "found": True,
                "record": record,
                "matched_name": record.get("name"),
                "match_method": "alias",
                "match_score": 1.0,
            }

    # 3. initial + last name
    initial_matches = candidate_matches_by_initial(
        player_name,
        store,
    )

    if len(initial_matches) == 1:
        key, record, score = initial_matches[0]

        _DEBUG["found_count"] += 1

        if len(_DEBUG["examples_found"]) < 30:
            _DEBUG["examples_found"].append({
                "input": player_name,
                "matched": record.get("name"),
                "method": "initial_last_name",
                "score": score,
            })

        return {
            "found": True,
            "record": record,
            "matched_name": record.get("name"),
            "match_method": "initial_last_name",
            "match_score": score,
        }

    # 4. conservative fuzzy
    input_last = last_name(player_name)

    candidates = []

    for key, record in store.items():
        rec_name = record.get("name", key)
        rec_last = last_name(rec_name)

        last_score = similarity(
            input_last,
            rec_last,
        )

        if last_score < 0.92:
            continue

        full_score = similarity(
            player_name,
            rec_name,
        )

        if full_score >= 0.90:
            candidates.append({
                "key": key,
                "record": record,
                "score": full_score,
                "last_score": last_score,
            })

    candidates.sort(
        key=lambda item: item["score"],
        reverse=True,
    )

    if candidates:
        best = candidates[0]

        ambiguous = False

        if len(candidates) > 1:
            second = candidates[1]

            if (
                best["score"] - second["score"]
            ) < 0.03:
                ambiguous = True

        if not ambiguous:
            record = best["record"]

            _DEBUG["found_count"] += 1

            if len(_DEBUG["examples_found"]) < 30:
                _DEBUG["examples_found"].append({
                    "input": player_name,
                    "matched": record.get("name"),
                    "method": "fuzzy_safe",
                    "score": round(
                        best["score"],
                        3,
                    ),
                })

            return {
                "found": True,
                "record": record,
                "matched_name": record.get("name"),
                "match_method": "fuzzy_safe",
                "match_score": round(
                    best["score"],
                    3,
                ),
            }

    _DEBUG["missing_count"] += 1

    if len(_DEBUG["examples_missing"]) < 50:
        _DEBUG["examples_missing"].append({
            "input": player_name,
            "normalized": normalized,
            "reason": "no_safe_match",
        })

    return {
        "found": False,
        "record": None,
        "matched_name": None,
        "match_method": "missing",
        "match_score": 0.0,
    }


def get_rating_from_record(record, surface=None):
    if not record:
        return DEFAULT_ELO

    if surface:
        surface_key = normalize_name(surface)

        surfaces = record.get("surfaces") or {}

        if isinstance(surfaces, dict):
            for key, value in surfaces.items():
                if normalize_name(key) == surface_key:
                    detected = safe_float(value)

                    if detected is not None:
                        return detected

    elo = safe_float(
        record.get("elo"),
        DEFAULT_ELO,
    )

    return elo


def get_yelo_from_record(record):
    if not record:
        return DEFAULT_ELO

    yelo = safe_float(
        record.get("yelo"),
        None,
    )

    if yelo is not None:
        return yelo

    return safe_float(
        record.get("elo"),
        DEFAULT_ELO,
    )


def win_probability(rating_a, rating_b):
    return 1 / (
        1 + 10 ** (
            (rating_b - rating_a) / 400
        )
    )


def predict(
    player1,
    player2,
    surface=None,
    elo_store=None,
):
    """
    Existing prediction engines call this function.

    Returns:
    {
        "probability_player1": ...,
        "probability_player2": ...
    }

    Plus debug metadata.
    """

    if elo_store is None:
        elo_store = load()

    lookup1 = find_player_record(
        player1,
        elo_store,
    )

    lookup2 = find_player_record(
        player2,
        elo_store,
    )

    rating1 = get_rating_from_record(
        lookup1.get("record"),
        surface=surface,
    )

    rating2 = get_rating_from_record(
        lookup2.get("record"),
        surface=surface,
    )

    yelo1 = get_yelo_from_record(
        lookup1.get("record"),
    )

    yelo2 = get_yelo_from_record(
        lookup2.get("record"),
    )

    probability1 = win_probability(
        rating1,
        rating2,
    )

    probability2 = 1 - probability1

    write_debug()

    return {
        "probability_player1": probability1,
        "probability_player2": probability2,

        "elo_player1": rating1,
        "elo_player2": rating2,

        "yelo_player1": yelo1,
        "yelo_player2": yelo2,

        "elo_found_player1": lookup1.get("found"),
        "elo_found_player2": lookup2.get("found"),

        "elo_match_player1": lookup1.get("matched_name"),
        "elo_match_player2": lookup2.get("matched_name"),

        "elo_match_method_player1": lookup1.get("match_method"),
        "elo_match_method_player2": lookup2.get("match_method"),

        "elo_match_score_player1": lookup1.get("match_score"),
        "elo_match_score_player2": lookup2.get("match_score"),
    }
```


## FILE: src/elo/features.py

```
import pandas as pd


def add_trends(df):
    """
    Add Elo and yElo trend columns.

    Requires:
    - date
    - player
    - elo
    - yelo
    """

    if df.empty:
        return df

    df = df.copy()

    df["date"] = pd.to_datetime(df["date"])

    df = df.sort_values(
        ["player", "date"]
    )

    if "elo" in df.columns:
        df["elo_change"] = (
            df.groupby("player")["elo"]
            .diff()
            .fillna(0)
        )

    if "yelo" in df.columns:
        df["yelo_change"] = (
            df.groupby("player")["yelo"]
            .diff()
            .fillna(0)
        )

    return df


def latest_player_trend(df, player):
    """
    Returns latest trend info for player.
    """

    if df.empty:
        return None

    player_df = df[df["player"] == player]

    if player_df.empty:
        return None

    player_df = player_df.sort_values("date")

    return player_df.iloc[-1].to_dict()
```


## FILE: src/elo/fetch.py

```
import pandas as pd
from pathlib import Path


RAW_DIR = Path("data/elo/raw")

FILES = {
    "atp_elo": RAW_DIR / "atp_elo.html",
    "wta_elo": RAW_DIR / "wta_elo.html",
    "atp_yelo": RAW_DIR / "atp_yelo.html",
    "wta_yelo": RAW_DIR / "wta_yelo.html",
}


def fetch_all():

    data = {}

    for name, file_path in FILES.items():

        if not file_path.exists():
            raise FileNotFoundError(
                f"Missing file: {file_path}"
            )

        tables = pd.read_html(file_path)

        target_table = None

        for table in tables:

            cols = [str(c) for c in table.columns]

            if (
                "Player" in cols
                and (
                    "Elo" in cols
                    or "yElo" in cols
                )
            ):
                target_table = table
                break

        if target_table is None:
            raise RuntimeError(
                f"Could not find Elo table in {file_path}"
            )

        data[name] = target_table

    return data
```


## FILE: src/elo/probability.py

```
def win_probability(rating_a, rating_b):
    return 1 / (
        1 + 10 ** (
            (rating_b - rating_a) / 400
        )
    )
```


## FILE: src/elo/service.py

```
from .store import load_latest


class EloService:

    def __init__(self):
        self.atp_elo = load_latest("atp_elo")
        self.wta_elo = load_latest("wta_elo")

        self.atp_yelo = load_latest("atp_yelo")
        self.wta_yelo = load_latest("wta_yelo")

    def _get_df(self, tour, typ):
        return getattr(self, f"{tour}_{typ}")

    def get_player_record(
        self,
        player_name,
        tour="atp",
        surface=None,
    ):
        elo_df = self._get_df(tour, "elo")
        yelo_df = self._get_df(tour, "yelo")

        elo_row = elo_df[
            elo_df["Player"] == player_name
        ]

        if elo_row.empty:
            return {
                "elo": 1500,
                "yelo": 1500,
                "combined": 1500,
            }

        elo = float(
            elo_row.iloc[0]["elo"]
        )

        # optional surface adjustment
        if surface:

            col = f"{surface}_elo"

            if col in elo_row.columns:

                value = elo_row.iloc[0][col]

                if value is not None:
                    elo = (
                        0.5 * elo +
                        0.5 * float(value)
                    )

        yelo = elo

        yelo_row = yelo_df[
            yelo_df["Player"] == player_name
        ]

        if (
            not yelo_row.empty
            and "yelo" in yelo_row.columns
        ):
            yelo = float(
                yelo_row.iloc[0]["yelo"]
            )

        combined = (
            0.7 * elo +
            0.3 * yelo
        )

        return {
            "elo": round(elo, 2),
            "yelo": round(yelo, 2),
            "combined": round(combined, 2),
        }

    def get_elo(
        self,
        player_name,
        tour="atp",
        surface=None,
    ):
        record = self.get_player_record(
            player_name=player_name,
            tour=tour,
            surface=surface,
        )

        return record["combined"]
```


## FILE: src/elo/store.py

```
import pandas as pd
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("data/elo")
BASE_DIR.mkdir(parents=True, exist_ok=True)

LATEST_FILES = {
    "atp_elo": BASE_DIR / "atp_elo_latest.csv",
    "wta_elo": BASE_DIR / "wta_elo_latest.csv",
    "atp_yelo": BASE_DIR / "atp_yelo_latest.csv",
    "wta_yelo": BASE_DIR / "wta_yelo_latest.csv",
}

HISTORY_FILE = BASE_DIR / "elo_history.csv"


def save_latest(name, df):
    """
    Save newest snapshot.
    """
    df.to_csv(LATEST_FILES[name], index=False)


def load_latest(name):
    """
    Load latest snapshot.
    """
    path = LATEST_FILES[name]

    if not path.exists():
        return pd.DataFrame()

    return pd.read_csv(path)


def load_history():
    """
    Load historical Elo database.
    """
    if not HISTORY_FILE.exists():
        return pd.DataFrame()

    return pd.read_csv(HISTORY_FILE)


def append_history(name, df):
    """
    Store weekly historical snapshots.
    """

    today = datetime.utcnow().strftime("%Y-%m-%d")

    tour = "ATP" if name.startswith("atp") else "WTA"
    rating_type = "yelo" if "yelo" in name else "elo"

    snapshot_rows = []

    for _, row in df.iterrows():

        snapshot_rows.append({
            "snapshot_date": today,
            "tour": tour,
            "rating_type": rating_type,
            "player": row.get("Player", ""),

            "elo": row.get("elo", 0),
            "yelo": row.get("yelo", 0),

            "hard_elo": row.get("hard_elo", 0),
            "clay_elo": row.get("clay_elo", 0),
            "grass_elo": row.get("grass_elo", 0)
        })

    new_df = pd.DataFrame(snapshot_rows)

    if HISTORY_FILE.exists():

        history = pd.read_csv(HISTORY_FILE)

        already_exists = (
            (history["snapshot_date"] == today)
            & (history["tour"] == tour)
            & (history["rating_type"] == rating_type)
        ).any()

        if already_exists:
            return

        new_df = pd.concat(
            [history, new_df],
            ignore_index=True
        )

    new_df.to_csv(HISTORY_FILE, index=False)
```


## FILE: src/elo/tbt_predict.py

```
from .service import EloService
from .probability import win_probability


service = EloService()


def predict(
    player1,
    player2,
    tour="atp",
    surface=None,
):
    p1 = service.get_player_record(
        player1,
        tour=tour,
        surface=surface,
    )

    p2 = service.get_player_record(
        player2,
        tour=tour,
        surface=surface,
    )

    elo_prob = win_probability(
        p1["elo"],
        p2["elo"],
    )

    yelo_prob = win_probability(
        p1["yelo"],
        p2["yelo"],
    )

    return {
        "elo_probability": elo_prob,
        "yelo_probability": yelo_prob,
        "player1": p1,
        "player2": p2,
    }
```


## FILE: src/elo/test_store.py

```
from src.elo.store import load_history


def main():

    df = load_history()

    print(df.head())

    print()
    print("Rows:", len(df))


if __name__ == "__main__":
    main()
```


## FILE: src/elo/update_elo.py

```
from src.elo.fetch import fetch_all
from src.elo.clean import clean_elo
from src.elo.store import save_latest, append_history


def run():

    data = fetch_all()

    for name, df in data.items():

        cleaned = clean_elo(df)

        save_latest(
            name=name,
            df=cleaned
        )

        append_history(
            name=name,
            df=cleaned
        )

    print("ELO database updated")


if __name__ == "__main__":
    run()
```


## FILE: src/marq_ai/__init__.py

```
from .service import build_marq_ai
from .provider import fetch_marq_market_data
from .pipeline import build_marq_from_match

__all__ = [
    "build_marq_ai",
    "fetch_marq_market_data",
    "build_marq_from_match",
]
```


## FILE: src/marq_ai/adapters.py

```
from .models import (
    MarqInput,
    MovementPoint,
)


def build_marq_input(
    opening_odds: float,
    current_odds: float,
    movements: list,
):
    history = []

    for item in movements:
        history.append(
            MovementPoint(
                odds=float(item["od1"]),
                timestamp=int(item["sourceAddTime"]),
            )
        )

    return MarqInput(
        opening_odds=opening_odds,
        current_odds=current_odds,
        movement_history=history,
    )
```


## FILE: src/marq_ai/engine.py

```
from .models import (
    MarqInput,
    MarqOutput,
)

from .movements import (
    calculate_direction,
    calculate_strength,
    calculate_consistency,
    calculate_steam_score,
)

from .signals import classify_signal


def calculate_marq(
    data: MarqInput
) -> MarqOutput:

    odds_history = [
        point.odds
        for point in data.movement_history
    ]

    direction = calculate_direction(
        data.opening_odds,
        data.current_odds,
    )

    strength = calculate_strength(
        data.opening_odds,
        data.current_odds,
    )

    consistency = calculate_consistency(
        odds_history,
    )

    score = calculate_steam_score(
        data.opening_odds,
        data.current_odds,
        odds_history,
    )

    signal = classify_signal(
        score,
    )

    return MarqOutput(
        score=score,
        direction=direction,
        strength=strength,
        consistency=consistency,
        signal=signal,
    )
```


## FILE: src/marq_ai/models.py

```
from dataclasses import dataclass
from typing import List


@dataclass
class MovementPoint:
    odds: float
    timestamp: int


@dataclass
class MarqInput:
    opening_odds: float
    current_odds: float
    movement_history: List[MovementPoint]


@dataclass
class MarqOutput:
    score: float
    direction: float
    strength: float
    consistency: float
    signal: str
```


## FILE: src/marq_ai/movements.py

```
# src/marq_ai/movements.py

from typing import List


def calculate_direction(
    opening_odds: float,
    current_odds: float
) -> float:
    """
    Market direction based on implied probability change.

    Positive = market supports the selection
    Negative = market moves against the selection
    """

    open_prob = 1.0 / opening_odds
    current_prob = 1.0 / current_odds

    return (current_prob - open_prob) * 100.0


def calculate_strength(
    opening_odds: float,
    current_odds: float
) -> float:
    """
    Absolute size of the odds move in %.
    """

    return abs(
        ((current_odds - opening_odds) / opening_odds) * 100.0
    )


def calculate_consistency(
    odds_history: List[float]
) -> float:
    """
    Measures how consistently odds moved in one direction.

    Returns:
        0   = chaotic movement
        50  = mixed movement
        100 = fully consistent movement
    """

    if len(odds_history) < 2:
        return 50.0

    up_moves = 0
    down_moves = 0

    for i in range(1, len(odds_history)):
        diff = odds_history[i] - odds_history[i - 1]

        if diff > 0:
            up_moves += 1
        elif diff < 0:
            down_moves += 1

    total_moves = up_moves + down_moves

    if total_moves == 0:
        return 50.0

    dominant_moves = max(up_moves, down_moves)

    return round(
        (dominant_moves / total_moves) * 100.0,
        2
    )


def calculate_steam_score(
    opening_odds: float,
    current_odds: float,
    odds_history: List[float]
) -> float:
    """
    Core Marq AI metric.

    Combines:
    - Direction
    - Move Strength
    - Movement Consistency

    Returns:
        0-100 score
    """

    direction = calculate_direction(
        opening_odds,
        current_odds
    )

    strength = calculate_strength(
        opening_odds,
        current_odds
    )

    consistency = calculate_consistency(
        odds_history
    )

    score = (
        50.0
        + (direction * 3.0)
        + (strength * 0.8)
        + ((consistency - 50.0) * 0.3)
    )

    return round(
        max(0.0, min(100.0, score)),
        2
    )
```


## FILE: src/marq_ai/pipeline.py

```
from __future__ import annotations

from statistics import median
from typing import Any, Dict, List, Optional

from .provider import fetch_marq_market_data


def _empty_marq(
    reason: str = "missing_data",
    event_id: Optional[str] = None,
    outcome_key: Optional[str] = None,
) -> Dict[str, Any]:
    return {
        "marq_ai_score": None,
        "marq_ai_signal": "NO MARKET DATA",
        "marq_ai_direction": "NO_MARKET_DATA",
        "marq_ai_strength": 0,
        "marq_ai_consistency": 0,
        "marq_ai_reason": reason,
        "marq_event_id": event_id,
        "marq_outcome_key": outcome_key,
        "marq_source": None,
        "marq_provider_count": 0,
        "marq_market_spread_pct": None,
        "marq_market_median_odds": None,
        "marq_outlier_count": 0,
    }


def _as_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        number = float(value)
        return number if number > 1 else None
    except Exception:
        return None


def _quote_pick_odds(quote: Dict[str, Any], outcome_key: str, match_direction: str) -> Optional[float]:
    if match_direction == "direct":
        value = quote.get("odds_1") if outcome_key == "od1" else quote.get("odds_2")
    else:
        value = quote.get("odds_2") if outcome_key == "od1" else quote.get("odds_1")
    return _as_float(value)


def _market_quality_from_odds(pick_odds_values: List[float]) -> Dict[str, Any]:
    values = [float(v) for v in pick_odds_values if _as_float(v) is not None]
    count = len(values)

    if count == 0:
        return {
            "signal": "NO MARKET DATA",
            "score": None,
            "direction": "NO_MARKET_DATA",
            "strength": 0,
            "consistency": 0,
            "provider_count": 0,
            "median_odds": None,
            "spread_pct": None,
            "outlier_count": 0,
        }

    med = float(median(values))
    minimum = min(values)
    maximum = max(values)
    spread_pct = ((maximum - minimum) / med) * 100 if med > 0 else None

    outliers = [v for v in values if med > 0 and abs(v - med) / med >= 0.12]
    outlier_count = len(outliers)

    if count <= 2:
        signal = "THIN MARKET"
        score = 35
        direction = "LIMITED_MARKET_SAMPLE"
        strength = 25
        consistency = 35
    else:
        non_outliers = [v for v in values if v not in outliers]
        non_outlier_spread = None
        if len(non_outliers) >= 2:
            non_med = float(median(non_outliers))
            non_outlier_spread = ((max(non_outliers) - min(non_outliers)) / non_med) * 100 if non_med > 0 else None

        if outlier_count >= 1 and len(non_outliers) >= 3 and (non_outlier_spread is not None and non_outlier_spread <= 6.0):
            signal = "OUTLIER"
            score = 60
            direction = "MARKET_HAS_OUTLIER"
            strength = 55
            consistency = 55
        elif spread_pct is not None and spread_pct <= 6.0:
            signal = "CONSENSUS"
            score = 80
            direction = "MARKET_CONSENSUS"
            strength = 80
            consistency = 85
        elif spread_pct is not None and spread_pct <= 12.0:
            signal = "CONSENSUS"
            score = 70
            direction = "MARKET_SOFT_CONSENSUS"
            strength = 65
            consistency = 70
        else:
            signal = "MIXED MARKET"
            score = 45
            direction = "MARKET_DISAGREEMENT"
            strength = 55
            consistency = 40

    return {
        "signal": signal,
        "score": score,
        "direction": direction,
        "strength": strength,
        "consistency": consistency,
        "provider_count": count,
        "median_odds": round(med, 4),
        "spread_pct": round(spread_pct, 2) if spread_pct is not None else None,
        "outlier_count": outlier_count,
    }


def build_marq_from_match(
    player1: str,
    player2: str,
    date_only: str,
    pick: Optional[str] = None,
    odds_player1: Optional[float] = None,
    odds_player2: Optional[float] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Marq AI = market quality / market agreement layer.

    Signals:
    - CONSENSUS
    - MIXED MARKET
    - OUTLIER
    - THIN MARKET
    - NO MARKET DATA
    """

    try:
        market_data = fetch_marq_market_data(
            player1=player1,
            player2=player2,
            date_only=date_only,
            pick=pick,
            odds_player1=odds_player1,
            odds_player2=odds_player2,
        )
    except Exception as exc:
        print(f"MARQ AI ERROR: provider failed {player1} vs {player2} {date_only}: {exc}")
        return _empty_marq(reason="provider_error")

    if not market_data:
        print(f"MARQ DEBUG: market_data missing {player1} vs {player2} {date_only}")
        return _empty_marq(reason="market_data_missing")

    outcome_key = market_data.get("pick_outcome_key") or "od1"
    match_direction = market_data.get("match_direction") or "direct"
    quotes = market_data.get("market_quotes") or []

    pick_odds_values = []
    for quote in quotes:
        if isinstance(quote, dict):
            value = _quote_pick_odds(quote, outcome_key, match_direction)
            if value is not None:
                pick_odds_values.append(value)

    quality = _market_quality_from_odds(pick_odds_values)

    print(
        "MARQ DEBUG: market quality "
        f"source={market_data.get('source')} event_id={market_data.get('event_id')} "
        f"pick={pick} providers={quality.get('provider_count')} "
        f"median_odds={quality.get('median_odds')} spread_pct={quality.get('spread_pct')} "
        f"outliers={quality.get('outlier_count')} signal={quality.get('signal')}"
    )

    if quality.get("signal") == "NO MARKET DATA":
        return _empty_marq(
            reason="market_quality_unavailable",
            event_id=market_data.get("event_id"),
            outcome_key=outcome_key,
        )

    return {
        "marq_ai_score": quality.get("score"),
        "marq_ai_signal": quality.get("signal"),
        "marq_ai_direction": quality.get("direction"),
        "marq_ai_strength": quality.get("strength"),
        "marq_ai_consistency": quality.get("consistency"),
        "marq_ai_reason": "ok",
        "marq_event_id": market_data.get("event_id"),
        "marq_outcome_key": outcome_key,
        "marq_source": market_data.get("source"),
        "marq_market_name": "market_quality",
        "marq_provider_count": quality.get("provider_count"),
        "marq_market_spread_pct": quality.get("spread_pct"),
        "marq_market_median_odds": quality.get("median_odds"),
        "marq_outlier_count": quality.get("outlier_count"),
        # Backward-compatible fields used by old logs/render/debug.
        "marq_opening": quality.get("median_odds"),
        "marq_latest": quality.get("median_odds"),
        "marq_market_move_pct": None,
        "marq_probability_change_pp": None,
        "marq_opponent_move_pct": None,
    }
```


## FILE: src/marq_ai/provider.py

```
from __future__ import annotations

import json
import os
import time
import unicodedata
from datetime import datetime
from pathlib import Path
from statistics import median
from typing import Any, Dict, List, Optional, Tuple

import requests

TENNISAPI_HOST = "tennisapi1.p.rapidapi.com"
TENNISAPI_BASE_URL = "https://tennisapi1.p.rapidapi.com"
CACHE_DIR = Path("data/marq_ai")
CACHE_TTL_SECONDS = 60 * 60 * 12

# TennisApi provider ids verified from the provider list in RapidAPI Playground.
# Keep it moderate for a smooth run. We can extend later.
DEFAULT_PROVIDER_IDS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

_RUN_EVENTS_ODDS_CACHE: Dict[str, Dict[str, Any]] = {}
_RUN_DETAILS_CACHE: Dict[str, Optional[Dict[str, Any]]] = {}
_RUN_PROVIDER_ODDS_CACHE: Dict[str, Optional[Dict[str, Any]]] = {}
_RUN_FAILED_DATES: set[str] = set()
_RATE_LIMITED = False


def _debug(message: str) -> None:
    print(f"MARQ TENNISAPI DEBUG: {message}")


def _api_key() -> str:
    return os.getenv("RAPIDAPI_KEY", "").strip()


def _headers() -> Dict[str, str]:
    return {
        "Content-Type": "application/json",
        "x-rapidapi-host": TENNISAPI_HOST,
        "x-rapidapi-key": _api_key(),
    }


def _cache_path(name: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_DIR / name


def _read_cache(path: Path, ttl_seconds: int = CACHE_TTL_SECONDS) -> Optional[Any]:
    try:
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        saved_at = float(payload.get("saved_at", 0))
        if time.time() - saved_at > ttl_seconds:
            return None
        return payload.get("data")
    except Exception:
        return None


def _write_cache(path: Path, data: Any) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"saved_at": time.time(), "data": data}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except Exception as exc:
        _debug(f"cache write failed path={path} error={exc}")


def _get_json(path: str, cache_name: Optional[str] = None, force_refresh: bool = False) -> Optional[Any]:
    global _RATE_LIMITED

    if _RATE_LIMITED:
        _debug(f"skip request because rate_limit flag active path={path}")
        return None

    if not _api_key():
        _debug("RAPIDAPI_KEY missing")
        return None

    cache_file = _cache_path(cache_name) if cache_name else None
    if cache_file and not force_refresh:
        cached = _read_cache(cache_file)
        if cached is not None:
            return cached

    url = f"{TENNISAPI_BASE_URL}{path}"

    try:
        response = requests.get(url, headers=_headers(), timeout=25)
        status = response.status_code
        content_type = response.headers.get("content-type", "")
        text_preview = (response.text or "")[:350].replace("\n", " ")
        _debug(f"http status={status} path={path} content_type={content_type} body_preview={text_preview}")

        if status == 204:
            return None
        if status == 429:
            _RATE_LIMITED = True
            _debug(f"rate limited path={path}")
            return None
        if status >= 400:
            return None
        if not response.text or not response.text.strip():
            return None

        try:
            data = response.json()
        except Exception as exc:
            _debug(f"json parse failed path={path} error={exc} body_preview={text_preview}")
            return None

        if cache_file:
            _write_cache(cache_file, data)
        return data

    except Exception as exc:
        _debug(f"request failed path={path} error={exc}")
        return None


def _parse_date(date_only: str) -> Tuple[int, int, int]:
    dt = datetime.strptime(str(date_only)[:10], "%Y-%m-%d").date()
    return dt.day, dt.month, dt.year


def _normalize_name(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    for ch in [".", ",", "'", "`", "’", "-", "_", "(", ")", "[", "]"]:
        text = text.replace(ch, " ")
    return " ".join(text.split())


def _tokens(value: Any) -> set[str]:
    return set(_normalize_name(value).split())


def _name_score(a: str, b: str) -> float:
    na = _normalize_name(a)
    nb = _normalize_name(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 1.0
    if na in nb or nb in na:
        return 0.92
    ta = _tokens(na)
    tb = _tokens(nb)
    if not ta or not tb:
        return 0.0
    score = len(ta & tb) / len(ta | tb)
    if ta and tb:
        # Surname-only / abbreviated-name support. Token order is not reliable after set(),
        # so this just gives a small boost when any last-looking token overlaps.
        ta_sorted = sorted(ta)
        tb_sorted = sorted(tb)
        if ta_sorted[-1] in tb or tb_sorted[-1] in ta:
            score = max(score, 0.60)
    return score


def _team_name(team: Any) -> str:
    if isinstance(team, dict):
        for key in ("name", "shortName", "fullName", "displayName", "slug"):
            value = team.get(key)
            if value:
                return str(value)
    return str(team or "")


def _extract_event(payload: Any) -> Optional[Dict[str, Any]]:
    if isinstance(payload, dict):
        event = payload.get("event")
        if isinstance(event, dict):
            return event
        data = payload.get("data")
        if isinstance(data, dict):
            event = data.get("event")
            if isinstance(event, dict):
                return event
            if data.get("homeTeam") or data.get("awayTeam"):
                return data
        if payload.get("homeTeam") or payload.get("awayTeam"):
            return payload
    return None


def _event_home_away(event: Dict[str, Any]) -> Tuple[str, str]:
    home = _team_name(event.get("homeTeam") or event.get("home") or event.get("participant1"))
    away = _team_name(event.get("awayTeam") or event.get("away") or event.get("participant2"))
    return home, away


def _fractional_to_decimal(value: Any) -> Optional[float]:
    if value in (None, ""):
        return None
    if isinstance(value, (int, float)):
        number = float(value)
        return number if number > 1 else None
    text = str(value).strip().replace(",", ".")
    if not text:
        return None
    if "/" in text:
        left, right = text.split("/", 1)
        try:
            numerator = float(left.strip())
            denominator = float(right.strip())
            if denominator == 0:
                return None
            return round(1.0 + numerator / denominator, 5)
        except Exception:
            return None
    try:
        number = float(text)
        return number if number > 1 else None
    except Exception:
        return None


def _extract_markets(payload: Any) -> List[Dict[str, Any]]:
    if isinstance(payload, dict):
        markets = payload.get("markets")
        if isinstance(markets, list):
            return [m for m in markets if isinstance(m, dict)]
        odds = payload.get("odds")
        if isinstance(odds, list):
            return [m for m in odds if isinstance(m, dict)]
        data = payload.get("data")
        if isinstance(data, dict):
            markets = data.get("markets")
            if isinstance(markets, list):
                return [m for m in markets if isinstance(m, dict)]
        if isinstance(data, list):
            return [m for m in data if isinstance(m, dict)]
    if isinstance(payload, list):
        return [m for m in payload if isinstance(m, dict)]
    return []


def _select_full_time_market(markets: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    for market in markets:
        market_name = str(market.get("marketName") or market.get("name") or "").strip().lower()
        market_group = str(market.get("marketGroup") or "").strip().lower()
        market_period = str(market.get("marketPeriod") or "").strip().lower()
        if market_name == "full time" and ("home" in market_group or market_group == "home/away") and market_period in ("match", ""):
            return market
    for market in markets:
        market_name = str(market.get("marketName") or market.get("name") or "").strip().lower()
        if market_name in ("full time", "match winner", "winner", "to win"):
            return market
    return None


def _extract_choice_odds(market: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    choices = market.get("choices") or market.get("outcomes") or []
    if not isinstance(choices, list):
        return None, None

    odds_1 = None
    odds_2 = None

    for choice in choices:
        if not isinstance(choice, dict):
            continue
        name = str(choice.get("name") or choice.get("choice") or choice.get("label") or "").strip()
        lowered = name.lower()
        if name not in ("1", "2"):
            if lowered in ("home", "player1", "team1"):
                name = "1"
            elif lowered in ("away", "player2", "team2"):
                name = "2"

        decimal = _fractional_to_decimal(
            choice.get("fractionalValue")
            or choice.get("decimalValue")
            or choice.get("value")
            or choice.get("odds")
        )

        if name == "1":
            odds_1 = decimal
        elif name == "2":
            odds_2 = decimal

    return odds_1, odds_2


def fetch_events_odds_by_date(date_only: str, force_refresh: bool = False) -> Dict[str, Any]:
    if date_only in _RUN_EVENTS_ODDS_CACHE and not force_refresh:
        return _RUN_EVENTS_ODDS_CACHE[date_only]
    if date_only in _RUN_FAILED_DATES and not force_refresh:
        return {}

    day, month, year = _parse_date(date_only)
    path = f"/api/tennis/events/odds/{day}/{month}/{year}"
    cache_name = f"tennisapi_events_odds_{year:04d}_{month:02d}_{day:02d}.json"
    payload = _get_json(path, cache_name=cache_name, force_refresh=force_refresh)

    result: Dict[str, Any] = {}
    if isinstance(payload, dict):
        odds = payload.get("odds")
        if isinstance(odds, dict):
            result = odds
        elif isinstance(odds, list):
            for item in odds:
                if isinstance(item, dict):
                    event_id = item.get("id") or item.get("eventId") or item.get("event_id")
                    if event_id:
                        result[str(event_id)] = item
        elif isinstance(payload.get("results"), dict):
            result = payload["results"]

    if not result:
        _RUN_FAILED_DATES.add(date_only)

    _RUN_EVENTS_ODDS_CACHE[date_only] = result
    _debug(f"events odds date={date_only} count={len(result)}")
    return result


def fetch_match_details(event_id: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
    if event_id in _RUN_DETAILS_CACHE and not force_refresh:
        return _RUN_DETAILS_CACHE[event_id]

    # Confirmed by RapidAPI snippet: /api/tennis/event/{id}
    path = f"/api/tennis/event/{event_id}"
    cache_name = f"tennisapi_match_details_{event_id}.json"
    payload = _get_json(path, cache_name=cache_name, force_refresh=force_refresh)
    event = _extract_event(payload)

    if event:
        _RUN_DETAILS_CACHE[event_id] = event
        home, away = _event_home_away(event)
        _debug(f"match details ok event_id={event_id} path={path} home={home} away={away}")
        return event

    _RUN_DETAILS_CACHE[event_id] = None
    _debug(f"match details missing event_id={event_id}")
    return None


def find_tennisapi_event_for_match(player1: str, player2: str, date_only: str, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
    odds_by_event = fetch_events_odds_by_date(date_only, force_refresh=force_refresh)
    if not odds_by_event:
        return None

    best: Optional[Dict[str, Any]] = None
    best_score = 0.0

    # Limit detail lookups to keep workflow smooth.
    for event_id in list(odds_by_event.keys())[:250]:
        event = fetch_match_details(str(event_id), force_refresh=force_refresh)
        if not event:
            continue
        home, away = _event_home_away(event)
        if not home or not away:
            continue

        direct = (_name_score(player1, home) + _name_score(player2, away)) / 2.0
        reverse = (_name_score(player1, away) + _name_score(player2, home)) / 2.0
        score = max(direct, reverse)

        if score > best_score:
            best_score = score
            best = {
                "event_id": str(event_id),
                "event": event,
                "home_name": home,
                "away_name": away,
                "match_direction": "direct" if direct >= reverse else "reverse",
                "match_score": round(score, 4),
                "bulk_odds": odds_by_event.get(str(event_id)),
            }

        if best_score >= 0.98:
            break

    if not best or best_score < 0.58:
        _debug(f"event not matched from odds feed player1={player1} player2={player2} date={date_only} best_score={best_score:.3f}")
        return None

    _debug(
        "event matched from odds feed "
        f"player1={player1} player2={player2} event_id={best['event_id']} "
        f"home={best['home_name']} away={best['away_name']} direction={best['match_direction']} score={best['match_score']}"
    )
    return best


def fetch_provider_odds(event_id: str, provider_id: int, force_refresh: bool = False) -> Optional[Dict[str, Any]]:
    key = f"{event_id}:{provider_id}"
    if key in _RUN_PROVIDER_ODDS_CACHE and not force_refresh:
        return _RUN_PROVIDER_ODDS_CACHE[key]

    # Confirmed TennisApi path for getAllOddsForEvent:
    # /api/tennis/event/{event_id}/odds/{provider_id}/all
    # Keep winning-odds and old odds paths as fallbacks.
    candidates = [
        f"/api/tennis/event/{event_id}/odds/{provider_id}/all",
        f"/api/tennis/event/{event_id}/provider/{provider_id}/winning-odds",
        f"/api/tennis/event/{event_id}/provider/{provider_id}/odds",
    ]

    for idx, path in enumerate(candidates):
        cache_name = f"tennisapi_provider_odds_{event_id}_{provider_id}_{idx}.json"
        payload = _get_json(path, cache_name=cache_name, force_refresh=force_refresh)
        markets = _extract_markets(payload)
        if markets:
            _RUN_PROVIDER_ODDS_CACHE[key] = payload
            _debug(
                f"provider odds ok event_id={event_id} "
                f"provider_id={provider_id} path={path} markets={len(markets)}"
            )
            return payload

    _RUN_PROVIDER_ODDS_CACHE[key] = None
    _debug(f"provider odds missing event_id={event_id} provider_id={provider_id}")
    return None


def _quote_from_payload(payload: Any, event_id: str, provider_id: Optional[int], provider_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
    markets = _extract_markets(payload)
    market = _select_full_time_market(markets)
    if not market:
        return None

    odds_1, odds_2 = _extract_choice_odds(market)
    if odds_1 is None or odds_2 is None:
        return None

    return {
        "event_id": str(event_id),
        "provider_id": provider_id,
        "provider_name": provider_name or (f"provider_{provider_id}" if provider_id is not None else "bulk"),
        "market_name": market.get("marketName") or market.get("name") or "Full time",
        "odds_1": odds_1,
        "odds_2": odds_2,
    }


def collect_market_quotes(event_id: str, bulk_odds: Any = None, provider_ids: Optional[List[int]] = None, force_refresh: bool = False) -> List[Dict[str, Any]]:
    provider_ids = provider_ids or DEFAULT_PROVIDER_IDS
    quotes: List[Dict[str, Any]] = []

    bulk_quote = _quote_from_payload(bulk_odds, event_id=event_id, provider_id=None, provider_name="bulk")
    if bulk_quote:
        quotes.append(bulk_quote)

    for provider_id in provider_ids:
        payload = fetch_provider_odds(event_id, provider_id, force_refresh=force_refresh)
        quote = _quote_from_payload(payload, event_id=event_id, provider_id=provider_id)
        if quote:
            signature = (round(quote["odds_1"], 4), round(quote["odds_2"], 4), quote.get("provider_id"))
            existing = {
                (round(q["odds_1"], 4), round(q["odds_2"], 4), q.get("provider_id"))
                for q in quotes
            }
            if signature not in existing:
                quotes.append(quote)

    _debug(f"market quotes event_id={event_id} count={len(quotes)}")
    return quotes


def _resolve_pick_outcome_key(player1: str, player2: str, pick: Optional[str]) -> str:
    if not pick:
        return "od1"
    p1 = _normalize_name(player1)
    p2 = _normalize_name(player2)
    pk = _normalize_name(pick)
    if pk == p1 or pk in p1 or p1 in pk or (_tokens(pk) & _tokens(p1)):
        return "od1"
    if pk == p2 or pk in p2 or p2 in pk or (_tokens(pk) & _tokens(p2)):
        return "od2"
    return "od1"


def _fallback_existing_odds(player1: str, player2: str, pick: Optional[str], odds_player1: Optional[float], odds_player2: Optional[float]) -> Optional[Dict[str, Any]]:
    try:
        od1 = float(odds_player1) if odds_player1 is not None else None
        od2 = float(odds_player2) if odds_player2 is not None else None
    except Exception:
        return None

    if od1 is None or od2 is None or od1 <= 1 or od2 <= 1:
        return None

    return {
        "source": "fallback_existing_odds_thin_market",
        "event_id": None,
        "player1": player1,
        "player2": player2,
        "home_name": player1,
        "away_name": player2,
        "match_direction": "direct",
        "pick_outcome_key": _resolve_pick_outcome_key(player1, player2, pick),
        "market_quotes": [
            {
                "event_id": None,
                "provider_id": None,
                "provider_name": "existing_odds",
                "market_name": "match_winner",
                "odds_1": od1,
                "odds_2": od2,
            }
        ],
        "odds": {
            "od1": {"opening": od1, "latest": od1, "current": od1, "change": 0},
            "od2": {"opening": od2, "latest": od2, "current": od2, "change": 0},
        },
    }


def fetch_marq_market_data(
    player1: str,
    player2: str,
    date_only: str,
    pick: Optional[str] = None,
    odds_player1: Optional[float] = None,
    odds_player2: Optional[float] = None,
    force_refresh: bool = False,
    **_: Any,
) -> Optional[Dict[str, Any]]:
    event_match = find_tennisapi_event_for_match(player1, player2, date_only, force_refresh=force_refresh)

    if event_match:
        event_id = str(event_match["event_id"])
        quotes = collect_market_quotes(event_id, bulk_odds=event_match.get("bulk_odds"), force_refresh=force_refresh)
        if quotes:
            if event_match["match_direction"] == "direct":
                od1_quotes = [q["odds_1"] for q in quotes if q.get("odds_1")]
                od2_quotes = [q["odds_2"] for q in quotes if q.get("odds_2")]
            else:
                od1_quotes = [q["odds_2"] for q in quotes if q.get("odds_2")]
                od2_quotes = [q["odds_1"] for q in quotes if q.get("odds_1")]

            od1 = float(median(od1_quotes)) if od1_quotes else None
            od2 = float(median(od2_quotes)) if od2_quotes else None

            result = {
                "source": "tennisapi_market_quality",
                "event_id": event_id,
                "player1": player1,
                "player2": player2,
                "home_name": event_match["home_name"],
                "away_name": event_match["away_name"],
                "match_direction": event_match["match_direction"],
                "match_score": event_match["match_score"],
                "pick_outcome_key": _resolve_pick_outcome_key(player1, player2, pick),
                "market_quotes": quotes,
                "odds": {
                    "od1": {"opening": od1, "latest": od1, "current": od1, "change": 0},
                    "od2": {"opening": od2, "latest": od2, "current": od2, "change": 0},
                },
            }
            _debug(f"market quality data ok event_id={event_id} quotes={len(quotes)} od1={od1} od2={od2}")
            return result

        _debug(f"event matched but no provider quotes event_id={event_id}")

    fallback = _fallback_existing_odds(player1, player2, pick, odds_player1, odds_player2)
    if fallback:
        _debug(f"using fallback thin market player1={player1} player2={player2} odds1={odds_player1} odds2={odds_player2}")
        return fallback

    return None
```


## FILE: src/marq_ai/rapid_api.py

```
import os
import re
import unicodedata
from urllib.parse import quote

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


def _participant_slug(name: str) -> str:
    if name is None:
        return ""

    text = str(name).strip()

    text = unicodedata.normalize(
        "NFKD",
        text,
    )

    text = "".join(
        char
        for char in text
        if not unicodedata.combining(char)
    )

    text = re.sub(
        r"[^A-Za-z0-9]",
        "",
        text,
    )

    return text


def _get_event_id_once(
    participant1: str,
    participant2: str,
    date_only: str,
):
    p1 = quote(
        _participant_slug(participant1),
        safe="",
    )

    p2 = quote(
        _participant_slug(participant2),
        safe="",
    )

    url = (
        f"{BASE_URL}"
        f"/tennis/v2/extend/api/event/get"
        f"/{p1}"
        f"/{p2}"
        f"/{date_only}"
    )

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


def get_event_id(
    player1: str,
    player2: str,
    date_only: str,
):
    try:
        event_id = _get_event_id_once(
            player1,
            player2,
            date_only,
        )

        if event_id:
            return event_id

    except Exception as exc:
        print(
            "MARQ EVENT ID PRIMARY ERROR:",
            player1,
            "vs",
            player2,
            str(exc),
        )

    try:
        event_id = _get_event_id_once(
            player2,
            player1,
            date_only,
        )

        if event_id:
            return event_id

    except Exception as exc:
        print(
            "MARQ EVENT ID REVERSE ERROR:",
            player2,
            "vs",
            player1,
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
```


## FILE: src/marq_ai/service.py

```
from .models import (
    MarqInput,
    MovementPoint,
)

from .engine import (
    calculate_marq,
)


def build_marq_ai(
    opening_odds: float,
    current_odds: float,
    movement_history: list,
):
    history = []

    for item in movement_history:
        history.append(
            MovementPoint(
                odds=float(
                    item.get("odds")
                ),
                timestamp=int(
                    item.get(
                        "timestamp",
                        0,
                    )
                ),
            )
        )

    marq_input = MarqInput(
        opening_odds=opening_odds,
        current_odds=current_odds,
        movement_history=history,
    )

    return calculate_marq(
        marq_input
    )
```


## FILE: src/marq_ai/signals.py

```
def classify_signal(score: float) -> str:

    if score >= 80:
        return "BULLISH"

    if score >= 65:
        return "SUPPORT"

    if score >= 45:
        return "NEUTRAL"

    if score >= 30:
        return "CAUTION"

    return "BEARISH"
```


## FILE: src/marq_ai/storage.py

```
import json
import os


MARQ_HISTORY_FILE = (
    "data/marq_ai/history.json"
)


def ensure_storage():
    os.makedirs(
        "data/marq_ai",
        exist_ok=True,
    )

    if not os.path.exists(
        MARQ_HISTORY_FILE
    ):
        with open(
            MARQ_HISTORY_FILE,
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                [],
                file,
                ensure_ascii=False,
                indent=2,
            )


def load_history():
    ensure_storage()

    with open(
        MARQ_HISTORY_FILE,
        "r",
        encoding="utf-8",
    ) as file:
        return json.load(file)


def append_history(
    record: dict
):
    history = load_history()

    history.append(
        record
    )

    with open(
        MARQ_HISTORY_FILE,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            history,
            file,
            ensure_ascii=False,
            indent=2,
        )
```


## FILE: src/marq_ai/transformer-4.py

```
from __future__ import annotations

from typing import Any, Dict, Optional


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _to_float(value: Any) -> Optionalif value is None:
        return None

    if isinstance(value, (int, float)):
        try:
            return float(value)
        except Exception:
            return None

    text = str(value).strip()
    if not text:
        return None

    text = text.replace(",", ".")

    try:
        return float(text)
    except Exception:
        return None


def resolve_outcome_key(
    player1: str,
    player2: str,
    pick: Optional[str] = None,
) -> str:
    """
    Resolve which odds side should be tracked by Marq AI.

    RapidAPI odds mapping:
    - od1 = participant1 / player1
    - od2 = participant2 / player2

    If pick matches player1 -> od1
    If pick matches player2 -> od2
    If pick is missing or cannot be resolved -> od1 fallback
    """

    p1 = _norm(player1)
    p2 = _norm(player2)
    pk = _norm(pick)

    if not pk:
        return "od1"

    if pk == p1:
        return "od1"

    if pk == p2:
        return "od2"

    if pk in p1 or p1 in pk:
        return "od1"

    if pk in p2 or p2 in pk:
        return "od2"

    p1_parts = set(p1.replace("-", " ").split())
    p2_parts = set(p2.replace("-", " ").split())
    pk_parts = set(pk.replace("-", " ").split())

    if p1_parts and pk_parts and p1_parts.intersection(pk_parts):
        return "od1"

    if p2_parts and pk_parts and p2_parts.intersection(pk_parts):
        return "od2"

    return "od1"


def opposite_outcome_key(outcome_key: str) -> str:
    return "od2" if outcome_key == "od1" else "od1"


def _walk_values(obj: Any):
    """
    Recursively walk nested dict/list structures.
    """

    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _walk_values(value)

    elif isinstance(obj, list):
        for item in obj:
            yield from _walk_values(item)


def find_event_id(payload: Any) -> Optional"""
    Best-effort event id resolver for RapidAPI event/get response.
    Tries common keys used by tennis APIs.
    """

    if payload is None:
        return None

    candidate_keys = (
        "eventId",
        "event_id",
        "eventID",
        "id",
        "matchId",
        "match_id",
        "fixtureId",
        "fixture_id",
    )

    for item in _walk_values(payload):
        for key in candidate_keys:
            value = item.get(key)
            if value not in (None, "", 0):
                return str(value)

    return None


def _extract_direct_price(
    item: Dict[str, Any],
    outcome_key: str,
) -> Optional"""
    Extract price from one dict if it contains direct odds fields.
    """

    direct_keys = (
        outcome_key,
        outcome_key.upper(),
        f"{outcome_key}_price",
        f"{outcome_key}Price",
        f"{outcome_key}_odd",
        f"{outcome_key}Odd",
        f"{outcome_key}_odds",
        f"{outcome_key}Odds",
    )

    for key in direct_keys:
        if key in item:
            price = _to_float(item.get(key))
            if price is not None:
                return price

    return None


def _extract_stage_price(
    payload: Any,
    stage: str,
    outcome_key: str,
) -> Optional"""
    Extract odds for a stage:
    - start = opening odds
    - kickoff = pre-match odds
    - end = closing/end odds

    Supports multiple possible JSON shapes.
    """

    if payload is None:
        return None

    stage_norm = _norm(stage)

    for item in _walk_values(payload):
        keys_lower = {_norm(k): k for k in item.keys()}

        # Shape:
        # {
        #   "start": {"od1": 1.55, "od2": 2.40}
        # }
        if stage_norm in keys_lower:
            stage_obj = item.get(keys_lower[stage_norm])
            if isinstance(stage_obj, dict):
                price = _extract_direct_price(stage_obj, outcome_key)
                if price is not None:
                    return price

        # Shape:
        # {
        #   "period": "start",
        #   "od1": 1.55,
        #   "od2": 2.40
        # }
        marker_keys = (
            "type",
            "name",
            "period",
            "stage",
            "moment",
            "phase",
            "oddsType",
            "odds_type",
        )

        marker = ""
        for marker_key in marker_keys:
            if marker_key in item:
                marker = _norm(item.get(marker_key))
                break

        if marker == stage_norm:
            price = _extract_direct_price(item, outcome_key)
            if price is not None:
                return price

    return None


def extract_summary_prices(
    summary_payload: Any,
    outcome_key: str,
) -> Dict[str, Optional[float]]:
    """
    Returns odds prices for selected outcome from summary endpoint.
    """

    return {
        "start": _extract_stage_price(summary_payload, "start", outcome_key),
        "kickoff": _extract_stage_price(summary_payload, "kickoff", outcome_key),
        "end": _extract_stage_price(summary_payload, "end", outcome_key),
    }


def extract_opponent_summary_prices(
    summary_payload: Any,
    outcome_key: str,
) -> Dict[str, Optional[float]]:
    """
    Returns odds prices for opposite outcome from summary endpoint.
    """

    opponent_key = opposite_outcome_key(outcome_key)

    return {
        "start": _extract_stage_price(summary_payload, "start", opponent_key),
        "kickoff": _extract_stage_price(summary_payload, "kickoff", opponent_key),
        "end": _extract_stage_price(summary_payload, "end", opponent_key),
    }


def extract_recent_price(
    recent_payload: Any,
    outcome_key: str,
) -> Optional"""
    Best-effort recent/current odds extractor.
    Looks for latest available selected outcome price.
    """

    if recent_payload is None:
        return None

    prices = []

    for item in _walk_values(recent_payload):
        price = _extract_direct_price(item, outcome_key)
        if price is not None:
            prices.append(price)

    if not prices:
        return None

    return prices[-1]


def build_marq_input(
    summary_payload: Any,
    recent_payload: Any,
    outcome_key: str,
) -> Dict[str, Any]:
    """
    Convert RapidAPI summary/recent odds payloads into normalized Marq AI input.
    """

    selected = extract_summary_prices(summary_payload, outcome_key)
    opponent = extract_opponent_summary_prices(summary_payload, outcome_key)
    recent = extract_recent_price(recent_payload, outcome_key)

    opening = selected.get("start")
    kickoff = selected.get("kickoff")
    closing = selected.get("end")

    latest = recent or closing or kickoff

    return {
        "outcome_key": outcome_key,
        "opening": opening,
        "kickoff": kickoff,
        "closing": closing,
        "recent": recent,
        "latest": latest,
        "opponent_opening": opponent.get("start"),
        "opponent_kickoff": opponent.get("kickoff"),
        "opponent_closing": opponent.get("end"),
    }


def has_usable_marq_input(marq_input: Dict[str, Any]) -> bool:
    """
    Minimal requirement:
    selected opening odds and one later/current odds value.
    """

    if not isinstance(marq_input, dict):
        return False

    opening = marq_input.get("opening")
    latest = marq_input.get("latest")

    return opening is not None and latest is not None


def calculate_market_move_percent(
    opening: Optional[float],
    latest: Optional[float],
) -> Optional"""
    Decimal odds move percentage.

    Negative value = odds shortened = market support.
    Positive value = odds drifted = market against.
    """

    if opening is None or latest is None:
        return None

    if opening <= 0:
        return None

    return ((latest - opening) / opening) * 100.0


def calculate_implied_probability(odds: Optional[float]) -> Optionalif odds is None or odds <= 0:
        return None

    return 1.0 / odds


def calculate_probability_change_pp(
    opening: Optional[float],
    latest: Optional[float],
) -> Optional"""
    Implied probability change in percentage points.
    Positive = selected player became more likely by market movement.
    """

    p_open = calculate_implied_probability(opening)
    p_latest = calculate_implied_probability(latest)

    if p_open is None or p_latest is None:
        return None

    return (p_latest - p_open) * 100.0


def summarize_movement(marq_input: Dict[str, Any]) -> Dict[str, Any]:
    opening = marq_input.get("opening")
    latest = marq_input.get("latest")

    move_pct = calculate_market_move_percent(opening, latest)
    prob_change_pp = calculate_probability_change_pp(opening, latest)

    opponent_opening = marq_input.get("opponent_opening")
    opponent_latest = (
        marq_input.get("opponent_closing")
        or marq_input.get("opponent_kickoff")
    )

    opponent_move_pct = calculate_market_move_percent(
        opponent_opening,
        opponent_latest,
    )

    return {
        "move_pct": move_pct,
        "prob_change_pp": prob_change_pp,
        "opponent_move_pct": opponent_move_pct,
    }
```


## FILE: src/marq_ai/transformer.py

```
from __future__ import annotations

from typing import Any, Dict, Optional


def _norm(value: Any) -> str:
    return str(value or "").strip().lower()


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None

    if isinstance(value, (int, float)):
        try:
            return float(value)
        except Exception:
            return None

    text = str(value).strip()
    if not text:
        return None

    text = text.replace(",", ".")

    try:
        return float(text)
    except Exception:
        return None


def resolve_outcome_key(
    player1: str,
    player2: str,
    pick: Optional[str] = None,
) -> str:
    """
    Resolve which RapidAPI odds side belongs to selected pick.

    RapidAPI mapping:
    - od1 = participant1 / player1
    - od2 = participant2 / player2
    """

    p1 = _norm(player1)
    p2 = _norm(player2)
    pk = _norm(pick)

    if not pk:
        return "od1"

    if pk == p1:
        return "od1"

    if pk == p2:
        return "od2"

    if pk in p1 or p1 in pk:
        return "od1"

    if pk in p2 or p2 in pk:
        return "od2"

    p1_parts = set(p1.replace("-", " ").split())
    p2_parts = set(p2.replace("-", " ").split())
    pk_parts = set(pk.replace("-", " ").split())

    if p1_parts and pk_parts and p1_parts.intersection(pk_parts):
        return "od1"

    if p2_parts and pk_parts and p2_parts.intersection(pk_parts):
        return "od2"

    return "od1"


def opposite_outcome_key(outcome_key: str) -> str:
    return "od2" if outcome_key == "od1" else "od1"


def _walk_values(obj: Any):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values():
            yield from _walk_values(value)

    elif isinstance(obj, list):
        for item in obj:
            yield from _walk_values(item)


def find_event_id(payload: Any) -> Optional[str]:
    """
    Best-effort event id resolver for RapidAPI event/get response.
    """

    if payload is None:
        return None

    candidate_keys = (
        "eventId",
        "event_id",
        "eventID",
        "id",
        "matchId",
        "match_id",
        "fixtureId",
        "fixture_id",
    )

    for item in _walk_values(payload):
        for key in candidate_keys:
            value = item.get(key)
            if value not in (None, "", 0):
                return str(value)

    return None


def _extract_direct_price(
    item: Dict[str, Any],
    outcome_key: str,
) -> Optional[float]:
    """
    Extract selected odds value from one dictionary.
    """

    direct_keys = (
        outcome_key,
        outcome_key.upper(),
        f"{outcome_key}_price",
        f"{outcome_key}Price",
        f"{outcome_key}_odd",
        f"{outcome_key}Odd",
        f"{outcome_key}_odds",
        f"{outcome_key}Odds",
    )

    for key in direct_keys:
        if key in item:
            price = _to_float(item.get(key))
            if price is not None:
                return price

    return None


def _extract_stage_price(
    payload: Any,
    stage: str,
    outcome_key: str,
) -> Optional[float]:
    """
    Extract odds for a stage:
    - start = opening odds
    - kickoff = pre-match odds
    - end = closing/end odds
    """

    if payload is None:
        return None

    stage_norm = _norm(stage)

    for item in _walk_values(payload):
        keys_lower = {_norm(k): k for k in item.keys()}

        # Shape: {"start": {"od1": 1.55, "od2": 2.40}}
        if stage_norm in keys_lower:
            stage_obj = item.get(keys_lower[stage_norm])
            if isinstance(stage_obj, dict):
                price = _extract_direct_price(stage_obj, outcome_key)
                if price is not None:
                    return price

        # Shape: {"period": "start", "od1": 1.55, "od2": 2.40}
        marker_keys = (
            "type",
            "name",
            "period",
            "stage",
            "moment",
            "phase",
            "oddsType",
            "odds_type",
        )

        marker = ""
        for marker_key in marker_keys:
            if marker_key in item:
                marker = _norm(item.get(marker_key))
                break

        if marker == stage_norm:
            price = _extract_direct_price(item, outcome_key)
            if price is not None:
                return price

    return None


def extract_summary_prices(
    summary_payload: Any,
    outcome_key: str,
) -> Dict[str, Optional[float]]:
    return {
        "start": _extract_stage_price(summary_payload, "start", outcome_key),
        "kickoff": _extract_stage_price(summary_payload, "kickoff", outcome_key),
        "end": _extract_stage_price(summary_payload, "end", outcome_key),
    }


def extract_opponent_summary_prices(
    summary_payload: Any,
    outcome_key: str,
) -> Dict[str, Optional[float]]:
    opponent_key = opposite_outcome_key(outcome_key)

    return {
        "start": _extract_stage_price(summary_payload, "start", opponent_key),
        "kickoff": _extract_stage_price(summary_payload, "kickoff", opponent_key),
        "end": _extract_stage_price(summary_payload, "end", opponent_key),
    }


def extract_recent_price(
    recent_payload: Any,
    outcome_key: str,
) -> Optional[float]:
    """
    Extract latest/recent selected odds.
    """

    if recent_payload is None:
        return None

    prices = []

    for item in _walk_values(recent_payload):
        price = _extract_direct_price(item, outcome_key)
        if price is not None:
            prices.append(price)

    if not prices:
        return None

    return prices[-1]


def build_marq_input(
    summary_payload: Any,
    recent_payload: Any,
    outcome_key: str,
) -> Dict[str, Any]:
    """
    Normalize RapidAPI summary/recent odds payloads into Marq AI input.
    """

    selected = extract_summary_prices(summary_payload, outcome_key)
    opponent = extract_opponent_summary_prices(summary_payload, outcome_key)
    recent = extract_recent_price(recent_payload, outcome_key)

    opening = selected.get("start")
    kickoff = selected.get("kickoff")
    closing = selected.get("end")

    latest = recent or closing or kickoff

    return {
        "outcome_key": outcome_key,
        "opening": opening,
        "kickoff": kickoff,
        "closing": closing,
        "recent": recent,
        "latest": latest,
        "opponent_opening": opponent.get("start"),
        "opponent_kickoff": opponent.get("kickoff"),
        "opponent_closing": opponent.get("end"),
    }


def has_usable_marq_input(marq_input: Dict[str, Any]) -> bool:
    if not isinstance(marq_input, dict):
        return False

    opening = marq_input.get("opening")
    latest = marq_input.get("latest")

    return opening is not None and latest is not None


def calculate_market_move_percent(
    opening: Optional[float],
    latest: Optional[float],
) -> Optional[float]:
    """
    Decimal odds move percentage.

    Negative = odds shortened = market support.
    Positive = odds drifted = market against.
    """

    if opening is None or latest is None:
        return None

    if opening <= 0:
        return None

    return ((latest - opening) / opening) * 100.0


def calculate_implied_probability(odds: Optional[float]) -> Optional[float]:
    if odds is None or odds <= 0:
        return None

    return 1.0 / odds


def calculate_probability_change_pp(
    opening: Optional[float],
    latest: Optional[float],
) -> Optional[float]:
    """
    Implied probability change in percentage points.

    Positive = selected player became more likely by market movement.
    """

    p_open = calculate_implied_probability(opening)
    p_latest = calculate_implied_probability(latest)

    if p_open is None or p_latest is None:
        return None

    return (p_latest - p_open) * 100.0


def summarize_movement(marq_input: Dict[str, Any]) -> Dict[str, Any]:
    opening = marq_input.get("opening")
    latest = marq_input.get("latest")

    move_pct = calculate_market_move_percent(opening, latest)
    prob_change_pp = calculate_probability_change_pp(opening, latest)

    opponent_opening = marq_input.get("opponent_opening")
    opponent_latest = (
        marq_input.get("opponent_closing")
        or marq_input.get("opponent_kickoff")
    )

    opponent_move_pct = calculate_market_move_percent(
        opponent_opening,
        opponent_latest,
    )

    return {
        "move_pct": move_pct,
        "prob_change_pp": prob_change_pp,
        "opponent_move_pct": opponent_move_pct,
    }
```


## FILE: src/models/match_intelligence.py

```
def clamp(value, low, high):
    return max(low, min(high, value))


GRAND_SLAMS = [
    "wimbledon",
    "australian open",
    "us open",
    "roland garros",
    "french open",
]


MOST_LIKELY_TIE_TOLERANCE = 0.001


def is_grand_slam(tournament):
    if not tournament:
        return False

    tournament = str(tournament).lower()

    return any(gs in tournament for gs in GRAND_SLAMS)


def infer_best_of_from_tournament(tournament):
    if not tournament:
        return 3

    text = str(tournament).lower()

    is_slam = is_grand_slam(text)

    is_men = (
        "men" in text
        or "atp" in text
    )

    is_women = (
        "women" in text
        or "wta" in text
    )

    if is_slam and is_men and not is_women:
        return 5

    return 3


def normalize_best_of(best_of, tournament=None):
    try:
        value = int(best_of)

        if value == 5:
            return 5

        if value == 3:
            return 3

    except Exception:
        pass

    return infer_best_of_from_tournament(
        tournament
    )


def bo3_match_win_probability(set_win_probability):
    p = float(set_win_probability)
    q = 1.0 - p

    return (
        (p ** 2)
        + (2.0 * (p ** 2) * q)
    )


def bo5_match_win_probability(set_win_probability):
    p = float(set_win_probability)
    q = 1.0 - p

    return (
        (p ** 3)
        + (3.0 * (p ** 3) * q)
        + (6.0 * (p ** 3) * (q ** 2))
    )


def match_win_probability_from_set_probability(
    set_win_probability,
    best_of,
):
    if best_of == 5:
        return bo5_match_win_probability(
            set_win_probability
        )

    return bo3_match_win_probability(
        set_win_probability
    )


def estimate_set_win_probability(
    match_win_probability,
    best_of,
):
    """
    Convert match win probability into implied set win probability.

    BO3:
        P(match win) = p^2 + 2*p^2*(1-p)

    BO5:
        P(match win) = p^3 + 3*p^3*(1-p) + 6*p^3*(1-p)^2

    We solve p by binary search.
    """

    target = clamp(
        float(match_win_probability),
        0.01,
        0.99,
    )

    low = 0.01
    high = 0.99

    for _ in range(70):
        mid = (low + high) / 2.0

        estimated = match_win_probability_from_set_probability(
            mid,
            best_of,
        )

        if estimated < target:
            low = mid

        else:
            high = mid

    return (low + high) / 2.0


def normalize_distribution(distribution):
    total = sum(distribution.values())

    if total <= 0:
        return distribution

    return {
        key: value / total
        for key, value in distribution.items()
    }


def score_distribution_bo3(set_win_probability):
    p = float(set_win_probability)
    q = 1.0 - p

    distribution = {
        "2-0": p * p,
        "2-1": 2.0 * p * p * q,
        "1-2": 2.0 * p * q * q,
        "0-2": q * q,
    }

    return normalize_distribution(
        distribution
    )


def score_distribution_bo5(set_win_probability):
    p = float(set_win_probability)
    q = 1.0 - p

    distribution = {
        "3-0": p ** 3,
        "3-1": 3.0 * (p ** 3) * q,
        "3-2": 6.0 * (p ** 3) * (q ** 2),
        "2-3": 6.0 * (p ** 2) * (q ** 3),
        "1-3": 3.0 * p * (q ** 3),
        "0-3": q ** 3,
    }

    return normalize_distribution(
        distribution
    )


def sets_count_from_score(score):
    try:
        left, right = str(score).split("-")

        return int(left) + int(right)

    except Exception:
        return 0


def expected_sets_from_distribution(distribution):
    total = 0.0

    for score, probability in distribution.items():
        total += (
            sets_count_from_score(score)
            * probability
        )

    return total


def deciding_set_probability(distribution, best_of):
    if best_of == 5:
        return (
            distribution.get("3-2", 0.0)
            + distribution.get("2-3", 0.0)
        )

    return (
        distribution.get("2-1", 0.0)
        + distribution.get("1-2", 0.0)
    )


def most_likely_score(
    distribution,
    tie_tolerance=MOST_LIKELY_TIE_TOLERANCE,
):
    """
    Return the most likely score.

    If multiple scores are effectively tied for highest probability,
    return "Balanced" instead of choosing the first dictionary item.

    Example:
    BO3 at 50%:
        2-0, 2-1, 1-2, 0-2 are all 25%
        -> Balanced

    BO5 at 50%:
        several outcomes are tied
        -> Balanced
    """

    if not distribution:
        return None

    max_probability = max(
        distribution.values()
    )

    top_scores = [
        score
        for score, probability in distribution.items()
        if abs(probability - max_probability) <= tie_tolerance
    ]

    if len(top_scores) > 1:
        return "Balanced"

    return top_scores[0]


def most_likely_score_probability(distribution):
    if not distribution:
        return None

    return max(
        distribution.values()
    )


def rounded_score_probabilities(distribution):
    return {
        score: round(probability, 4)
        for score, probability in distribution.items()
    }


def expected_games_placeholder(
    expected_sets,
    deciding_probability,
    best_of,
):
    """
    Compatibility-only field.

    This is intentionally conservative and should not be treated
    as a final game/serve model.

    The website should not display games recommendation until
    a real game/serve model is implemented.
    """

    if best_of == 5:
        base_games_per_set = 9.6
        deciding_bonus = 2.0

    else:
        base_games_per_set = 9.4
        deciding_bonus = 1.2

    value = (
        expected_sets * base_games_per_set
        + deciding_probability * deciding_bonus
    )

    return round(value, 1)


def games_market_placeholder(expected_games, best_of):
    """
    Compatibility-only field.

    Kept so older render/build code does not crash.
    Do not use as betting recommendation.
    """

    return {
        "games_pick": "INFO ONLY",
        "games_line": None,
    }


def build_score_model(probability, best_of):
    set_win_probability = estimate_set_win_probability(
        probability,
        best_of,
    )

    if best_of == 5:
        distribution = score_distribution_bo5(
            set_win_probability
        )

        sets_probability_label = "5 Sets"

    else:
        distribution = score_distribution_bo3(
            set_win_probability
        )

        sets_probability_label = "3 Sets"

    expected_sets = expected_sets_from_distribution(
        distribution
    )

    sets_probability = deciding_set_probability(
        distribution,
        best_of,
    )

    likely_score = most_likely_score(
        distribution
    )

    likely_score_probability = most_likely_score_probability(
        distribution
    )

    expected_games = expected_games_placeholder(
        expected_sets,
        sets_probability,
        best_of,
    )

    games_market = games_market_placeholder(
        expected_games,
        best_of,
    )

    return {
        "set_win_probability": set_win_probability,
        "score_probabilities": distribution,
        "expected_sets": expected_sets,
        "sets_probability": sets_probability,
        "sets_probability_label": sets_probability_label,
        "most_likely_score": likely_score,
        "most_likely_score_probability": likely_score_probability,
        "expected_games": expected_games,
        "games_pick": games_market["games_pick"],
        "games_line": games_market["games_line"],
    }


def build_consensus_tag(consensus_score):
    tag = "INFO ONLY"

    if consensus_score is not None:

        if consensus_score >= 85:
            tag = "PLAY"

        elif consensus_score >= 70:
            tag = "PLAY SMALL"

        elif consensus_score >= 55:
            tag = "WATCH"

    return tag


def build_match_intelligence(
    probability,
    odds=None,
    consensus_score=None,
    tournament=None,
    best_of=None,
):
    """
    Match Intelligence v2.

    This model uses:
    - final match win probability
    - best_of 3 or 5

    It estimates set win probability and derives:
    - score distribution
    - expected sets
    - deciding set probability
    - most likely score

    It does not yet provide a real game/serve model.
    """

    probability = clamp(
        float(probability),
        0.01,
        0.99,
    )

    best_of = normalize_best_of(
        best_of,
        tournament,
    )

    score_model = build_score_model(
        probability,
        best_of,
    )

    tag = build_consensus_tag(
        consensus_score
    )

    return {
        "expected_sets": round(
            score_model["expected_sets"],
            1,
        ),

        "sets_probability": round(
            score_model["sets_probability"],
            3,
        ),

        "sets_probability_label":
            score_model["sets_probability_label"],

        "expected_games":
            score_model["expected_games"],

        "games_pick":
            score_model["games_pick"],

        "games_line":
            score_model["games_line"],

        "best_of":
            best_of,

        "set_win_probability": round(
            score_model["set_win_probability"],
            4,
        ),

        "most_likely_score":
            score_model["most_likely_score"],

        "most_likely_score_probability": round(
            score_model["most_likely_score_probability"],
            4,
        ) if score_model["most_likely_score_probability"] is not None else None,

        "score_probabilities":
            rounded_score_probabilities(
                score_model["score_probabilities"]
            ),

        "tag":
            tag,
    }
```


## FILE: src/results/__init__.py

```
# results package
```


## FILE: stats_engine.py

```
import re
import csv
import requests
from io import StringIO

DATA_FILES_ENDPOINT = "https://stats.tennismylife.org/api/data-files"


def normalize_name(name):
    if not name:
        return ""

    name = str(name).lower().strip()
    name = re.sub(r"[^a-zA-ZÀ-ž\s\-']", "", name)
    name = re.sub(r"\s+", " ", name)

    return name


def loose_keys(name):
    name = normalize_name(name)
    parts = name.split()

    keys = set()

    if name:
        keys.add(name)

    if parts:
        keys.add(parts[-1])

    if len(parts) >= 2:
        keys.add(" ".join(parts[-2:]))

    return keys


def names_match(a, b):
    a_keys = loose_keys(a)
    b_keys = loose_keys(b)

    if not a_keys or not b_keys:
        return False

    return bool(a_keys.intersection(b_keys))


def safe_float(value):
    try:
        if value in [None, "", "NA", "NaN"]:
            return None
        return float(value)
    except Exception:
        return None


def parse_date(value):
    try:
        value = str(value).strip()

        if len(value) == 8 and value.isdigit():
            return int(value)

        digits = re.sub(r"\D", "", value)

        if len(digits) >= 8:
            return int(digits[:8])
    except Exception:
        pass

    return 0


def parse_sets_from_score(score):
    if not score:
        return {"winner_sets": None, "loser_sets": None, "sets_total": None}

    score = str(score)

    if any(x in score.upper() for x in ["RET", "W/O", "WO", "DEF", "ABN"]):
        return {"winner_sets": None, "loser_sets": None, "sets_total": None}

    chunks = score.split()

    winner_sets = 0
    loser_sets = 0

    for chunk in chunks:
        match = re.match(r"(\d+)-(\d+)", chunk)

        if not match:
            continue

        a = int(match.group(1))
        b = int(match.group(2))

        if a > b:
            winner_sets += 1
        elif b > a:
            loser_sets += 1

    total = winner_sets + loser_sets

    if total == 0:
        return {"winner_sets": None, "loser_sets": None, "sets_total": None}

    return {
        "winner_sets": winner_sets,
        "loser_sets": loser_sets,
        "sets_total": total
    }


def get_data_files():
    try:
        response = requests.get(DATA_FILES_ENDPOINT, timeout=30)

        if response.status_code != 200:
            print("Stats data files error:", response.status_code)
            return []

        data = response.json()
        return data.get("files", [])

    except Exception as e:
        print("Stats data list error:", e)
        return []


def file_priority(file_info):
    name = str(file_info.get("name", "")).lower()

    if "ongoing" in name:
        return 1000

    if "2026" in name and "challenger" in name:
        return 950

    if "2026" in name:
        return 900

    if "2025" in name and "challenger" in name:
        return 850

    if "2025" in name:
        return 800

    if "2024" in name and "challenger" in name:
        return 750

    if "2024" in name:
        return 700

    if "2023" in name and "challenger" in name:
        return 650

    if "2023" in name:
        return 600

    return 0


def choose_relevant_files(files):
    candidates = []

    for f in files:
        name = str(f.get("name", "")).lower()
        url = f.get("url")

        if not url:
            continue

        if not name.endswith(".csv"):
            continue

        prio = file_priority(f)

        if prio > 0:
            candidates.append((prio, f))

    candidates.sort(key=lambda x: x[0], reverse=True)

    return [f for _, f in candidates[:12]]


def fetch_csv_rows(file_info):
    url = file_info.get("url")
    name = file_info.get("name", "unknown.csv")

    try:
        print("Stats fetch:", name)

        response = requests.get(url, timeout=45)

        if response.status_code != 200:
            print("Stats csv error:", response.status_code, name)
            return []

        reader = csv.DictReader(StringIO(response.text))
        return list(reader)

    except Exception as e:
        print("Stats csv fetch error:", name, e)
        return []


def build_player_record(row, player):
    winner = row.get("winner_name", "")
    loser = row.get("loser_name", "")

    is_winner = names_match(player, winner)
    is_loser = names_match(player, loser)

    if not is_winner and not is_loser:
        return None

    parsed = parse_sets_from_score(row.get("score", ""))

    if is_winner:
        aces = safe_float(row.get("w_ace"))
        serve_points = safe_float(row.get("w_svpt"))
        sets_won = parsed["winner_sets"]
        sets_lost = parsed["loser_sets"]
        won_match = True
    else:
        aces = safe_float(row.get("l_ace"))
        serve_points = safe_float(row.get("l_svpt"))
        sets_won = parsed["loser_sets"]
        sets_lost = parsed["winner_sets"]
        won_match = False

    won_set = None

    if sets_won is not None:
        won_set = sets_won >= 1

    return {
        "date": parse_date(row.get("tourney_date")),
        "surface": row.get("surface") or "Unknown",
        "won_match": won_match,
        "aces": aces,
        "serve_points": serve_points,
        "sets_won": sets_won,
        "sets_lost": sets_lost,
        "won_set": won_set
    }


def calc_metrics(records, label):
    records = sorted(records, key=lambda x: x.get("date", 0), reverse=True)

    n = len(records)

    if n == 0:
        return {
            "label": label,
            "sample": 0,
            "wins": 0,
            "losses": 0,
            "win_rate": None,
            "at_least_one_set_rate": None,
            "set_win_rate": None,
            "avg_aces": None,
            "avg_serve_points": None,
            "ace_rate": None
        }

    wins = sum(1 for r in records if r["won_match"])
    losses = n - wins

    score_records = [r for r in records if r.get("won_set") is not None]

    set_rate = None

    if score_records:
        set_rate = sum(1 for r in score_records if r["won_set"]) / len(score_records)

    total_sets_won = sum(
        r["sets_won"] for r in score_records
        if r["sets_won"] is not None
    )

    total_sets_lost = sum(
        r["sets_lost"] for r in score_records
        if r["sets_lost"] is not None
    )

    set_win_rate = None

    if total_sets_won + total_sets_lost > 0:
        set_win_rate = total_sets_won / (total_sets_won + total_sets_lost)

    ace_values = [r["aces"] for r in records if r.get("aces") is not None]
    serve_values = [r["serve_points"] for r in records if r.get("serve_points") is not None]

    avg_aces = None

    if ace_values:
        avg_aces = sum(ace_values) / len(ace_values)

    avg_serve_points = None

    if serve_values:
        avg_serve_points = sum(serve_values) / len(serve_values)

    ace_rate = None

    if avg_aces is not None and avg_serve_points:
        ace_rate = avg_aces / avg_serve_points

    return {
        "label": label,
        "sample": n,
        "wins": wins,
        "losses": losses,
        "win_rate": round(wins / n, 3),
        "at_least_one_set_rate": round(set_rate, 3) if set_rate is not None else None,
        "set_win_rate": round(set_win_rate, 3) if set_win_rate is not None else None,
        "avg_aces": round(avg_aces, 2) if avg_aces is not None else None,
        "avg_serve_points": round(avg_serve_points, 1) if avg_serve_points is not None else None,
        "ace_rate": round(ace_rate, 4) if ace_rate is not None else None
    }


def empty_player_stats(player):
    return {
        "player": player,
        "records_total": 0,
        "career": calc_metrics([], "career"),
        "last10": calc_metrics([], "last10"),
        "surface": {}
    }


def infer_match_surface(match, all_rows):
    p1 = match.get("player1")
    p2 = match.get("player2")

    candidates = []

    for row in all_rows:
        winner = row.get("winner_name", "")
        loser = row.get("loser_name", "")

        both_match = (
            (names_match(p1, winner) and names_match(p2, loser)) or
            (names_match(p1, loser) and names_match(p2, winner))
        )

        if both_match:
            surface = row.get("surface")
            date = parse_date(row.get("tourney_date"))

            if surface:
                candidates.append((date, surface))

    if not candidates:
        return "Unknown"

    candidates.sort(key=lambda x: x[0], reverse=True)

    return candidates[0][1]


def get_stats_context(players, matches):
    stats_map = {
        player: empty_player_stats(player)
        for player in players
    }

    files = choose_relevant_files(get_data_files())

    print("Stats files selected:", [f.get("name") for f in files])

    all_rows = []

    for file_info in files:
        rows = fetch_csv_rows(file_info)
        all_rows.extend(rows)

    player_records = {player: [] for player in players}

    for row in all_rows:
        for player in players:
            rec = build_player_record(row, player)

            if rec:
                player_records[player].append(rec)

    for player in players:
        records = sorted(
            player_records[player],
            key=lambda x: x.get("date", 0),
            reverse=True
        )

        stats_map[player]["records_total"] = len(records)
        stats_map[player]["career"] = calc_metrics(records, "career")
        stats_map[player]["last10"] = calc_metrics(records[:10], "last10")

        surfaces = sorted(set(r.get("surface", "Unknown") for r in records))

        for surface in surfaces:
            s_records = [
                r for r in records
                if r.get("surface") == surface
            ]

            stats_map[player]["surface"][surface] = calc_metrics(
                s_records[:10],
                f"last10_{surface}"
            )

    surface_map = {}

    for match in matches:
        key = f"{match.get('player1')}::{match.get('player2')}"
        surface_map[key] = infer_match_surface(match, all_rows)

    return stats_map, surface_map
```


## FILE: telegram_feed.py

```
import os
import re
from datetime import datetime

import feedparser
import requests


# ============================================================
# TELEGRAM SECRETS
# ============================================================

BOT_TOKEN = ***REDACTED***
CHAT_ID = os.getenv("TG_CHAT_ID")

if not BOT_TOKEN:
    raise ValueError("Missing GitHub secret: TG_BOT_BTLKR")

if not CHAT_ID:
    raise ValueError("Missing GitHub secret: TG_CHAT_ID")


# ============================================================
# RSS FEEDS
# ============================================================

RSS_FEEDS = [
    {
        "url": "https://backstagetalks.github.io/tennis-backstage-talks/h4v34n1c3d4y185.xml",
        "title": "TOP BETS | Corq Model"
    },
    {
        "url": "https://backstagetalks.github.io/tennis-backstage-talks/h4v34n1c3d4y186.xml",
        "title": "TOP BETS | Thinq Model"
    },
    {
        "url": "https://backstagetalks.github.io/tennis-backstage-talks/h4v34n1c3d4y187.xml",
        "title": "TOP BETS | Blenq Model"
    }
]


# ============================================================
# FUNCTIONS
# ============================================================

def extract_player(title):
    if " to win vs " in title:
        return title.split(" to win vs ")[0].strip()
    return title.strip()


def extract_probability(description):
    match = re.search(
        r"Win probability:\s*([0-9.]+)%",
        description,
        re.IGNORECASE
    )
    if match:
        return match.group(1)
    return None


def extract_odds(description):
    match = re.search(
        r"Odds:\s*([0-9.]+)",
        description,
        re.IGNORECASE
    )
    if match:
        return match.group(1)
    return None


def build_message(feed_url, feed_title):
    feed = feedparser.parse(feed_url)

    if feed.bozo:
        raise ValueError(f"RSS parsing error for {feed_url}: {feed.bozo_exception}")

    if not feed.entries:
        raise ValueError(f"No RSS entries found for {feed_url}")

    today = datetime.now().strftime("%d.%m.%Y")

    message = (
        f"📅 {today}\n\n"
        f"🎾 {feed_title}\n\n"
    )

    icons = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣"]

    added = 0

    for item in feed.entries:
        if added >= 5:
            break

        title = item.get("title", "")
        description = item.get("description", "")

        player = extract_player(title)
        probability = extract_probability(description)
        odds = extract_odds(description)

        if not player or not probability or not odds:
            continue

        surname = player.split()[-1]

        message += f"{icons[added]} {surname} | {probability}% | {odds}\n"

        added += 1

    if added == 0:
        raise ValueError(f"No valid TOP5 items parsed from {feed_url}")

    message += (
        "\n"
        "This data is provided for informational and analytical purposes only\n"
        "Powered by BackstageTalks Statistical Engine"
    )

    return message


def send_telegram_message(message):
    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": message
        },
        timeout=30
    )

    response.raise_for_status()


# ============================================================
# MAIN
# ============================================================

for rss_feed in RSS_FEEDS:
    message = build_message(
        feed_url=rss_feed["url"],
        feed_title=rss_feed["title"]
    )

    send_telegram_message(message)

    print(message)
    print("Telegram message sent successfully.")
```


## FILE: telegram_rss_feed.py

```
import html
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

import feedparser
import requests


# ============================================================
# TELEGRAM SECRETS
# ============================================================

BOT_TOKEN = ***REDACTED***
CHAT_ID = os.getenv("TG_CHAT_ID")

if not BOT_TOKEN:
    raise ValueError("Missing GitHub secret: TG_BOT_BTLKR")

if not CHAT_ID:
    raise ValueError("Missing GitHub secret: TG_CHAT_ID")


# ============================================================
# CONFIG
# ============================================================

LOCAL_TZ = ZoneInfo("Europe/Bratislava")

FEED_LIMIT = int(os.getenv("TG_FEED_LIMIT", "5"))
SELECTED_FEED = os.getenv("TG_FEED", "all").strip().lower()

RSS_FEEDS = [
    {
        "key": "corq",
        "url": "https://backstagetalks.github.io/tennis-backstage-talks/h4v34n1c3d4y185.xml",
        "title": "TOP BETS | Corq Model",
    },
    {
        "key": "thinq",
        "url": "https://backstagetalks.github.io/tennis-backstage-talks/h4v34n1c3d4y186.xml",
        "title": "TOP BETS | Thinq Model",
    },
    {
        "key": "blenq",
        "url": "https://backstagetalks.github.io/tennis-backstage-talks/h4v34n1c3d4y187.xml",
        "title": "TOP BETS | Blenq Model",
    },
]


# ============================================================
# TEXT HELPERS
# ============================================================


def clean_text(value):
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def clean_multiline(value):
    text = html.unescape(str(value or ""))
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</p\s*>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s+", "\n", text)
    return text.strip()


# ============================================================
# PARSING HELPERS
# ============================================================


def extract_player(title):
    title = clean_text(title)

    if " to win vs " in title:
        return title.split(" to win vs ", 1)[0].strip()

    return title.strip()


def extract_opponent(title):
    title = clean_text(title)

    if " to win vs " in title:
        return title.split(" to win vs ", 1)[1].strip()

    return ""


def extract_probability(description):
    text = clean_multiline(description)

    match = re.search(
        r"Win probability:\s*([0-9]+(?:\.[0-9]+)?)%",
        text,
        re.IGNORECASE,
    )

    if match:
        return match.group(1)

    return None


def extract_odds(description):
    text = clean_multiline(description)

    match = re.search(
        r"Odds:\s*([0-9]+(?:\.[0-9]+)?)",
        text,
        re.IGNORECASE,
    )

    if match:
        return match.group(1)

    return None


def short_name(player):
    parts = clean_text(player).split()

    if not parts:
        return "-"

    return parts[-1]


# ============================================================
# RSS + TELEGRAM
# ============================================================


def parse_feed_entries(feed_url):
    feed = feedparser.parse(feed_url)

    if feed.bozo:
        raise ValueError(f"RSS parsing error for {feed_url}: {feed.bozo_exception}")

    return feed.entries or []


def build_message(feed_url, feed_title, limit):
    entries = parse_feed_entries(feed_url)
    today = datetime.now(LOCAL_TZ).strftime("%d.%m.%Y")

    message = (
        f"📅 {today}\n\n"
        f"🎾 {feed_title}\n\n"
    )

    icons = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    added = 0

    for item in entries:
        if added >= limit:
            break

        title = item.get("title", "")
        description = item.get("description", "")

        player = extract_player(title)
        opponent = extract_opponent(title)
        win_rate = extract_probability(description)
        odd = extract_odds(description)

        if not player or not win_rate or not odd:
            continue

        icon = icons[added] if added < len(icons) else f"{added + 1}."
        name = short_name(player)

        # IMPORTANT:
        # Telegram feed shows WIN RATE %, not AI Match %.
        line = f"{icon} {name} | WR {win_rate}% | {odd}"

        if opponent:
            line += f"\n   vs {opponent}"

        message += line + "\n"
        added += 1

    if added == 0:
        message += "No valid picks found in RSS feed.\n"

    message += (
        "\n"
        "This data is provided for informational and analytical purposes only\n"
        "Powered by BackstageTalks Statistical Engine"
    )

    return message, added


def send_telegram_message(message):
    response = requests.post(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        json={
            "chat_id": CHAT_ID,
            "text": message,
            "disable_web_page_preview": True,
        },
        timeout=30,
    )

    response.raise_for_status()


# ============================================================
# MAIN
# ============================================================


def selected_feeds():
    if SELECTED_FEED in ("", "all", "*all"):
        return RSS_FEEDS

    output = [feed for feed in RSS_FEEDS if feed["key"] == SELECTED_FEED]

    if not output:
        valid = ", ".join(feed["key"] for feed in RSS_FEEDS)
        raise ValueError(f"Invalid TG_FEED={SELECTED_FEED}. Valid values: all, {valid}")

    return output


def main():
    print("TELEGRAM RSS FEED START")
    print("TG_FEED:", SELECTED_FEED)
    print("TG_FEED_LIMIT:", FEED_LIMIT)

    for rss_feed in selected_feeds():
        message, count = build_message(
            feed_url=rss_feed["url"],
            feed_title=rss_feed["title"],
            limit=FEED_LIMIT,
        )

        send_telegram_message(message)

        print("")
        print("SENT FEED:", rss_feed["key"], rss_feed["url"])
        print("PICKS SENT:", count)
        print(message)
        print("Telegram message sent successfully.")

    print("TELEGRAM RSS FEED DONE")


if __name__ == "__main__":
    main()
```


## FILE: tennisapi_cache.py

```
import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

from tennisapi_client import (
    TennisApiClient,
    fractional_to_decimal,
    normalize_event,
    normalize_winning_odds,
)


logger = logging.getLogger(__name__)

LOCAL_TZ = ZoneInfo("Europe/Bratislava")
CACHE_DIR = Path("data/tennisapi_cache")


# ----------------------------------------------------------------------
# Config helpers
# ----------------------------------------------------------------------


def parse_category_ids() -> List[int]:
    raw = os.getenv("TENNISAPI_CATEGORY_IDS", "3,6,871").strip()
    output: List[int] = []

    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            output.append(int(part))
        except Exception:
            logger.warning("Invalid TennisApi category id ignored: %s", part)

    return output or [3]


def provider_id() -> int:
    try:
        return int(os.getenv("TENNISAPI_PROVIDER_ID", "1"))
    except Exception:
        return 1


def betting_day_datetime(date_time: Optional[datetime] = None) -> datetime:
    if date_time is None:
        date_time = datetime.now(LOCAL_TZ)

    if date_time.tzinfo is None:
        date_time = date_time.replace(tzinfo=LOCAL_TZ)
    else:
        date_time = date_time.astimezone(LOCAL_TZ)

    if date_time.hour < 6:
        date_time = date_time - timedelta(days=1)

    return date_time


def date_key(target_date: Optional[datetime] = None) -> str:
    return betting_day_datetime(target_date).strftime("%Y-%m-%d")


def ensure_cache_dir() -> None:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)


def cache_path(kind: str, target_date: Optional[datetime] = None) -> Path:
    ensure_cache_dir()
    return CACHE_DIR / f"{kind}_{date_key(target_date)}.json"


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def load_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
    except Exception as exc:
        logger.warning("TennisApi cache load failed path=%s error=%s", path, exc)
        return default


# ----------------------------------------------------------------------
# Generic TennisApi extraction helpers
# ----------------------------------------------------------------------


def extract_event_from_payload(payload: Any) -> Optional[Dict[str, Any]]:
    if isinstance(payload, dict):
        event = payload.get("event")
        if isinstance(event, dict):
            return event

        data = payload.get("data")
        if isinstance(data, dict):
            event = data.get("event")
            if isinstance(event, dict):
                return event
            if data.get("homeTeam") or data.get("awayTeam"):
                return data

        if payload.get("homeTeam") or payload.get("awayTeam"):
            return payload

    return None


def event_home_away(event: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    home = event.get("homeTeam") or {}
    away = event.get("awayTeam") or {}

    player1 = home.get("name") or home.get("shortName") or event.get("home")
    player2 = away.get("name") or away.get("shortName") or event.get("away")

    return player1, player2


def extract_markets(raw_odds: Any) -> List[Dict[str, Any]]:
    if not isinstance(raw_odds, dict):
        return []

    markets = raw_odds.get("markets")
    if isinstance(markets, list):
        return [item for item in markets if isinstance(item, dict)]

    odds = raw_odds.get("odds")
    if isinstance(odds, list):
        return [item for item in odds if isinstance(item, dict)]

    data = raw_odds.get("data")
    if isinstance(data, dict):
        markets = data.get("markets")
        if isinstance(markets, list):
            return [item for item in markets if isinstance(item, dict)]

    if raw_odds.get("choices"):
        return [raw_odds]

    return []


def select_full_time_market(raw_odds: Any) -> Optional[Dict[str, Any]]:
    markets = extract_markets(raw_odds)

    for market in markets:
        market_name = str(market.get("marketName") or market.get("name") or "").strip().lower()
        market_group = str(market.get("marketGroup") or "").strip().lower()
        market_period = str(market.get("marketPeriod") or "").strip().lower()

        if (
            market_name == "full time"
            and ("home" in market_group or market_group == "home/away")
            and market_period in ("match", "")
        ):
            return market

    for market in markets:
        market_name = str(market.get("marketName") or market.get("name") or "").strip().lower()
        if market_name in ("full time", "match winner", "winner", "to win"):
            return market

    return markets[0] if markets else None


def choice_to_decimal(choice: Dict[str, Any]) -> Optional[float]:
    if not isinstance(choice, dict):
        return None

    for key in ["fractionalValue", "initialFractionalValue", "value", "decimalValue", "price", "odds"]:
        value = choice.get(key)
        if value is None:
            continue

        if key in ["fractionalValue", "initialFractionalValue"]:
            decimal = fractional_to_decimal(str(value))
        else:
            try:
                decimal = float(value)
            except Exception:
                decimal = None

        if decimal and decimal > 1.0:
            return round(decimal, 4)

    return None


def pick_home_away_choices(choices: List[Dict[str, Any]], player1: str, player2: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    if len(choices) < 2:
        return {}, {}

    p1 = normalize_name(player1)
    p2 = normalize_name(player2)
    choice_for_p1 = None
    choice_for_p2 = None

    for choice in choices:
        text = normalize_choice_text(choice)
        name = str(choice.get("name") or "").strip()

        if name == "1":
            choice_for_p1 = choice_for_p1 or choice
        elif name == "2":
            choice_for_p2 = choice_for_p2 or choice

        if text:
            if p1 and p1 in text:
                choice_for_p1 = choice
            if p2 and p2 in text:
                choice_for_p2 = choice

    if choice_for_p1 and choice_for_p2:
        return choice_for_p1, choice_for_p2

    return choices[0], choices[1]


def normalize_choice_text(choice: Dict[str, Any]) -> str:
    values = []
    for key in ["name", "label", "choiceName", "participantName", "sourceName", "marketName"]:
        value = choice.get(key)
        if value:
            values.append(str(value))
    return normalize_name(" ".join(values))


def normalize_name(value: Any) -> str:
    return (
        str(value or "")
        .lower()
        .replace(".", "")
        .replace("-", " ")
        .replace("_", " ")
        .strip()
    )


# ----------------------------------------------------------------------
# Events cache
# ----------------------------------------------------------------------


def get_events_for_date(
    target_date: Optional[datetime] = None,
    force_refresh: bool = False,
    category_ids: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    target_date = betting_day_datetime(target_date)
    path = cache_path("events", target_date)

    if not force_refresh:
        cached = load_json(path, None)
        if isinstance(cached, list):
            return cached

    client = TennisApiClient()
    category_ids = category_ids or parse_category_ids()
    all_events: List[Dict[str, Any]] = []
    seen = set()

    for category_id in category_ids:
        try:
            events = client.get_events_by_category_date(
                category_id=category_id,
                day=target_date.day,
                month=target_date.month,
                year=target_date.year,
            )
        except Exception as exc:
            logger.warning(
                "TennisApi cached events fetch failed category_id=%s date=%s error=%s",
                category_id,
                target_date.date(),
                exc,
            )
            continue

        for event in events:
            if not isinstance(event, dict):
                continue
            event_id = event.get("id")
            if event_id in seen:
                continue
            seen.add(event_id)
            event["_cache_category_id"] = category_id
            all_events.append(event)

    save_json(path, all_events)
    print("TennisApi cache events:", len(all_events), str(path))
    return all_events


# ----------------------------------------------------------------------
# Daily odds cache
# ----------------------------------------------------------------------


def get_daily_odds_payload(
    target_date: Optional[datetime] = None,
    force_refresh: bool = False,
) -> Dict[str, Any]:
    """
    Batch daily odds endpoint:
        /api/tennis/events/odds/{day}/{month}/{year}
    """
    target_date = betting_day_datetime(target_date)
    path = cache_path("odds_batch", target_date)

    if not force_refresh:
        cached = load_json(path, None)
        if isinstance(cached, dict):
            return cached

    client = TennisApiClient()

    try:
        payload = client.get_events_odds_by_date(
            day=target_date.day,
            month=target_date.month,
            year=target_date.year,
        )
    except Exception as exc:
        api_path = f"/api/tennis/events/odds/{target_date.day}/{target_date.month}/{target_date.year}"
        logger.warning("TennisApi daily odds batch failed path=%s error=%s", api_path, exc)
        payload = {}

    save_json(path, payload)
    odds_obj = payload.get("odds") if isinstance(payload, dict) else None
    count = len(odds_obj) if isinstance(odds_obj, dict) else 0
    print("TennisApi cache daily odds batch:", count, str(path))
    return payload if isinstance(payload, dict) else {}


def get_daily_odds_items(
    target_date: Optional[datetime] = None,
    force_refresh: bool = False,
    include_event_fallback: bool = True,
) -> List[Dict[str, Any]]:
    """
    Returns model-compatible odds list:
        player1, player2, match_id/event_id, odds_player1, odds_player2.

    Important behaviour:
    - Category events are processed first.
    - Then every event_id from /events/odds/date is checked.
    - If an odds event is missing from category events, /api/tennis/event/{event_id}
      is used to fetch match details and build an odds item.
    """
    target_date = betting_day_datetime(target_date)
    path = cache_path("odds_items", target_date)

    if not force_refresh:
        cached = load_json(path, None)
        if isinstance(cached, list):
            return cached

    client = TennisApiClient()
    events = get_events_for_date(target_date, force_refresh=force_refresh)
    batch = get_daily_odds_payload(target_date, force_refresh=force_refresh)
    batch_odds = batch.get("odds") if isinstance(batch, dict) else {}
    if not isinstance(batch_odds, dict):
        batch_odds = {}

    items: List[Dict[str, Any]] = []
    seen_item_ids = set()
    events_by_id: Dict[str, Dict[str, Any]] = {}

    for event in events:
        event_id = event.get("id")
        if not event_id:
            continue
        events_by_id[str(event_id)] = event

    # First pass: category events.
    for event_id, event in events_by_id.items():
        raw_odds = batch_odds.get(str(event_id)) or batch_odds.get(event_id)
        item = normalize_daily_odds_item(event, raw_odds)

        if not item and include_event_fallback:
            item = fetch_event_winning_odds_item(client, event, int(event_id))

        if item:
            seen_item_ids.add(str(event_id))
            items.append(item)

    # Second pass: odds batch events that did not appear in category events.
    # This is key for using the paid TennisApi odds feed properly.
    for event_id_raw, raw_odds in batch_odds.items():
        event_id = str(event_id_raw)
        if event_id in seen_item_ids:
            continue

        event = events_by_id.get(event_id)
        if not event:
            try:
                detail_payload = client.get_match_details(int(event_id))
                event = extract_event_from_payload(detail_payload) or {}
            except Exception as exc:
                logger.debug("TennisApi detail fetch for odds-batch event failed event_id=%s error=%s", event_id, exc)
                event = {}

        if not event:
            continue

        item = normalize_daily_odds_item(event, raw_odds)
        if item:
            seen_item_ids.add(event_id)
            items.append(item)

    save_json(path, items)
    print("TennisApi cache odds items:", len(items), str(path))
    return items


def fetch_event_winning_odds_item(
    client: TennisApiClient,
    event: Dict[str, Any],
    event_id: int,
) -> Optional[Dict[str, Any]]:
    try:
        event_odds_payload = client.get_match_winning_odds(event_id, provider_id())
        normalized = normalize_winning_odds(event_odds_payload)
        if normalized:
            return legacy_item_from_normalized_event_odds(event, normalized)
    except Exception as exc:
        logger.debug("Event odds fallback failed event_id=%s error=%s", event_id, exc)
    return None


def normalize_daily_odds_item(event: Dict[str, Any], raw_odds: Any) -> Optional[Dict[str, Any]]:
    if not isinstance(event, dict):
        return None
    if not isinstance(raw_odds, dict):
        return None

    event = extract_event_from_payload(event) or event
    player1, player2 = event_home_away(event)
    event_id = event.get("id")

    if not player1 or not player2 or not event_id:
        return None

    full_time_market = select_full_time_market(raw_odds)
    if not full_time_market:
        return None

    choices = full_time_market.get("choices")
    if not isinstance(choices, list) or len(choices) < 2:
        return None

    choice1, choice2 = pick_home_away_choices(choices, player1, player2)
    odds1 = choice_to_decimal(choice1)
    odds2 = choice_to_decimal(choice2)

    if odds1 is None or odds2 is None:
        return None

    return {
        "source": "TennisApiDailyOdds",
        "odds_source": "TennisApiDailyOdds",
        "bookmaker": raw_odds.get("sourceName") or raw_odds.get("bookmaker") or "TennisApi",
        "match_id": event_id,
        "event_id": event_id,
        "player1": player1,
        "player2": player2,
        "home_team": player1,
        "away_team": player2,
        "home": player1,
        "away": player2,
        "match": f"{player1} vs {player2}",
        "tournament": (event.get("tournament") or {}).get("name"),
        "category": ((event.get("tournament") or {}).get("category") or {}).get("name"),
        "start_timestamp": event.get("startTimestamp"),
        "start_time_utc": normalize_event(event).get("start_time_utc"),
        "odds_player1": odds1,
        "odds_player2": odds2,
        "p1_odds": odds1,
        "p2_odds": odds2,
        "home_odds": odds1,
        "away_odds": odds2,
        "odds": odds1,
        "odds1": odds1,
        "odds2": odds2,
        "price1": odds1,
        "price2": odds2,
        "market_name": full_time_market.get("marketName") or raw_odds.get("marketName"),
        "market_id": full_time_market.get("marketId") or raw_odds.get("marketId"),
        "raw": raw_odds,
    }


def legacy_item_from_normalized_event_odds(event: Dict[str, Any], normalized: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    event = extract_event_from_payload(event) or event
    player1, player2 = event_home_away(event)
    event_id = event.get("id")

    if not player1 or not player2 or not event_id:
        return None

    p1 = normalized.get("p1_odds") or normalized.get("home_odds")
    p2 = normalized.get("p2_odds") or normalized.get("away_odds")

    if p1 is None or p2 is None:
        return None

    return {
        "source": "TennisApiEventOdds",
        "odds_source": "TennisApiEventOdds",
        "bookmaker": "TennisApi",
        "match_id": event_id,
        "event_id": event_id,
        "player1": player1,
        "player2": player2,
        "home_team": player1,
        "away_team": player2,
        "home": player1,
        "away": player2,
        "match": f"{player1} vs {player2}",
        "tournament": (event.get("tournament") or {}).get("name"),
        "category": ((event.get("tournament") or {}).get("category") or {}).get("name"),
        "start_timestamp": event.get("startTimestamp"),
        "start_time_utc": normalize_event(event).get("start_time_utc"),
        "odds_player1": p1,
        "odds_player2": p2,
        "p1_odds": p1,
        "p2_odds": p2,
        "home_odds": p1,
        "away_odds": p2,
        "odds": p1,
        "odds1": p1,
        "odds2": p2,
        "price1": p1,
        "price2": p2,
        "raw": normalized.get("raw", normalized),
    }


# ----------------------------------------------------------------------
# CLI warmup
# ----------------------------------------------------------------------


def warm_cache(force_refresh: bool = True) -> None:
    target_date = betting_day_datetime()
    print("TennisApi cache warmup date:", target_date.strftime("%Y-%m-%d"))
    events = get_events_for_date(target_date, force_refresh=force_refresh)
    odds_items = get_daily_odds_items(target_date, force_refresh=force_refresh)
    print("TennisApi cache warmup events:", len(events))
    print("TennisApi cache warmup odds_items:", len(odds_items))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    warm_cache(force_refresh=True)
```


## FILE: tennisapi_client.py

```
import os
import json
import time
import logging
import http.client
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


logger = logging.getLogger(__name__)


class TennisApiError(Exception):
    """Generic TennisApi / REcodeX client error."""


class TennisApiClient:
    """
    TennisApi / REcodeX PRO client cez RapidAPI.

    Confirmed paths:
    - /api/tennis/category/{category_id}/events/{day}/{month}/{year}
    - /api/tennis/event/{event_id}
    - /api/tennis/events/odds/{day}/{month}/{year}
    - /api/tennis/event/{event_id}/provider/{provider_id}/winning-odds
    - /api/tennis/event/{event_id}/odds/{provider_id}/all
    """

    BASE_HOST = "tennisapi1.p.rapidapi.com"

    def __init__(
        self,
        api_key: ***REDACTED*** = None,
        rapidapi_host: str = BASE_HOST,
        timeout: int = 30,
        max_retries: int = 2,
        retry_sleep_seconds: float = 0.7,
    ) -> None:
        self.api_key = ***REDACTED***
            api_key
            or os.getenv("TENNISAPI_RAPIDAPI_KEY", "").strip()
            or os.getenv("RAPIDAPI_KEY", "").strip()
        )
        self.rapidapi_host = rapidapi_host
        self.timeout = timeout
        self.max_retries = max_retries
        self.retry_sleep_seconds = retry_sleep_seconds

        if not self.api_key:
            raise TennisApiError(
                "Missing TennisApi key. Set TENNISAPI_RAPIDAPI_KEY or RAPIDAPI_KEY."
            )

    def _headers(self) -> Dict[str, str]:
        return {
            "x-rapidapi-key": self.api_key,
            "x-rapidapi-host": self.rapidapi_host,
            "Content-Type": "application/json",
        }

    def _request_json(self, method: str, path: str) -> Dict[str, Any]:
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                conn = http.client.HTTPSConnection(
                    self.rapidapi_host,
                    timeout=self.timeout,
                )
                conn.request(
                    method.upper(),
                    path,
                    headers=self._headers(),
                )
                res = conn.getresponse()
                raw = res.read().decode("utf-8", errors="replace")

                if res.status >= 400:
                    raise TennisApiError(
                        f"TennisApi HTTP {res.status} for {path}: {raw[:500]}"
                    )

                if not raw:
                    return {}

                try:
                    data = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise TennisApiError(
                        f"TennisApi returned invalid JSON for {path}: {raw[:500]}"
                    ) from exc

                if isinstance(data, dict):
                    return data

                return {"data": data}

            except Exception as exc:
                last_error = exc
                if attempt < self.max_retries:
                    time.sleep(self.retry_sleep_seconds)
                else:
                    break

        raise TennisApiError(f"TennisApi request failed for {path}: {last_error}")

    def _try_paths(self, paths: List[str]) -> Dict[str, Any]:
        errors: List[str] = []

        for path in paths:
            try:
                return self._request_json("GET", path)
            except Exception as exc:
                errors.append(f"{path} -> {exc}")

        raise TennisApiError(
            "All TennisApi candidate paths failed: " + " | ".join(errors)
        )

    # ------------------------------------------------------------------
    # Fixtures / Events
    # ------------------------------------------------------------------

    def get_events_by_category_date(
        self,
        category_id: int,
        day: int,
        month: int,
        year: int,
    ) -> List[Dict[str, Any]]:
        path = f"/api/tennis/category/{category_id}/events/{day}/{month}/{year}"
        data = self._request_json("GET", path)
        events = data.get("events", [])
        return events if isinstance(events, list) else []

    def get_events_by_date(
        self,
        target_date: datetime,
        category_ids: List[int],
    ) -> List[Dict[str, Any]]:
        all_events: List[Dict[str, Any]] = []

        for category_id in category_ids:
            try:
                events = self.get_events_by_category_date(
                    category_id=category_id,
                    day=target_date.day,
                    month=target_date.month,
                    year=target_date.year,
                )
                all_events.extend(events)
            except Exception as exc:
                logger.warning(
                    "TennisApi category fetch failed. category_id=%s date=%s error=%s",
                    category_id,
                    target_date.date(),
                    exc,
                )

        return deduplicate_events(all_events)

    def get_events_odds_by_date(
        self,
        day: int,
        month: int,
        year: int,
    ) -> Dict[str, Any]:
        """
        TennisApi daily odds batch.

        Confirmed path:
            /api/tennis/events/odds/{day}/{month}/{year}
        """
        path = f"/api/tennis/events/odds/{day}/{month}/{year}"
        return self._request_json("GET", path)

    # ------------------------------------------------------------------
    # Match details
    # ------------------------------------------------------------------

    def get_match_details(self, match_id: int) -> Dict[str, Any]:
        """
        TennisApi match/event details.

        Confirmed path:
            /api/tennis/event/{event_id}
        """
        paths = [
            f"/api/tennis/event/{match_id}",
            f"/api/tennis/event/{match_id}/details",
            f"/api/tennis/match/{match_id}",
            f"/api/tennis/matches/{match_id}",
            f"/api/tennis/match/{match_id}/details",
        ]
        return self._try_paths(paths)

    # ------------------------------------------------------------------
    # Live
    # ------------------------------------------------------------------

    def get_live_matches(self) -> List[Dict[str, Any]]:
        paths = [
            "/api/tennis/matches/live",
            "/api/tennis/events/live",
            "/api/tennis/live",
        ]
        data = self._try_paths(paths)

        if isinstance(data.get("events"), list):
            return data["events"]
        if isinstance(data.get("matches"), list):
            return data["matches"]
        if isinstance(data.get("event"), dict):
            return [data["event"]]
        return []

    # ------------------------------------------------------------------
    # Odds
    # ------------------------------------------------------------------

    def get_match_winning_odds(
        self,
        match_id: int,
        provider_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        TennisApi getMatchWinningOdds.

        Confirmed RapidAPI snippet:
            /api/tennis/event/{event_id}/provider/{provider_id}/winning-odds
        """
        provider_id = provider_id or int(os.getenv("TENNISAPI_PROVIDER_ID", "1"))
        path = f"/api/tennis/event/{match_id}/provider/{provider_id}/winning-odds"

        try:
            return self._request_json("GET", path)
        except Exception as exc:
            logger.info(
                "TennisApi winning odds unavailable. match_id=%s provider_id=%s error=%s",
                match_id,
                provider_id,
                exc,
            )
            return None

    def get_all_odds_for_event(
        self,
        match_id: int,
        provider_id: Optional[int] = None,
    ) -> Optional[Dict[str, Any]]:
        """
        TennisApi getAllOddsForEvent.

        Confirmed RapidAPI snippet:
            /api/tennis/event/{event_id}/odds/{provider_id}/all

        Fallback:
            /api/tennis/event/{event_id}/provider/{provider_id}/winning-odds
        """
        provider_id = provider_id or int(os.getenv("TENNISAPI_PROVIDER_ID", "1"))

        paths = [
            f"/api/tennis/event/{match_id}/odds/{provider_id}/all",
            f"/api/tennis/event/{match_id}/provider/{provider_id}/winning-odds",
        ]

        for path in paths:
            try:
                return self._request_json("GET", path)
            except Exception as exc:
                logger.debug(
                    "TennisApi all odds candidate failed. path=%s error=%s",
                    path,
                    exc,
                )

        return None


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------


def safe_get(data: Dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict):
            return default
        cur = cur.get(key)
    return cur if cur is not None else default


def deduplicate_events(events: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    seen = set()
    result: List[Dict[str, Any]] = []

    for event in events:
        event_id = event.get("id")
        if event_id is None:
            result.append(event)
            continue
        if event_id in seen:
            continue
        seen.add(event_id)
        result.append(event)

    return result


def fractional_to_decimal(value: Optional[str]) -> Optional[float]:
    """Convert fractional odds to decimal odds. Example: 73/100 -> 1.73."""
    if not value or not isinstance(value, str):
        return None

    value = value.strip()
    try:
        if "/" in value:
            left, right = value.split("/", 1)
            numerator = float(left)
            denominator = float(right)
            if denominator == 0:
                return None
            return round(1.0 + numerator / denominator, 4)

        return round(float(value), 4)
    except Exception:
        return None


def unix_to_iso(timestamp: Optional[int]) -> Optional[str]:
    if not timestamp:
        return None
    try:
        return datetime.fromtimestamp(int(timestamp), tz=timezone.utc).isoformat()
    except Exception:
        return None


def normalize_status(status: Any) -> str:
    if not isinstance(status, dict):
        return "UNKNOWN"

    status_type = str(status.get("type", "")).lower().strip()
    description = str(status.get("description", "")).lower().strip()
    code = status.get("code")

    if status_type in {"finished", "ended"} or description in {"ended", "finished"} or code == 100:
        return "FINISHED"
    if status_type in {"inprogress", "in_progress", "live"}:
        return "LIVE"
    if status_type in {"notstarted", "not_started", "scheduled"}:
        return "NOT_STARTED"
    if status_type in {"cancelled", "canceled"}:
        return "CANCELLED"
    if status_type == "postponed":
        return "POSTPONED"
    if status_type == "retired":
        return "RETIRED"
    if status_type == "walkover":
        return "WALKOVER"

    return status_type.upper() if status_type else "UNKNOWN"


def extract_event(payload: Dict[str, Any]) -> Dict[str, Any]:
    if isinstance(payload, dict) and isinstance(payload.get("event"), dict):
        return payload["event"]
    return payload if isinstance(payload, dict) else {}


def normalize_event(event: Dict[str, Any]) -> Dict[str, Any]:
    event = extract_event(event)

    home_team = event.get("homeTeam") or {}
    away_team = event.get("awayTeam") or {}
    tournament = event.get("tournament") or {}
    unique_tournament = tournament.get("uniqueTournament") or event.get("uniqueTournament") or {}
    category = tournament.get("category") or event.get("category") or {}
    status = event.get("status") or {}
    home_score = event.get("homeScore") or {}
    away_score = event.get("awayScore") or {}

    winner_code = event.get("winnerCode")
    winner_name = None
    if winner_code == 1:
        winner_name = home_team.get("name")
    elif winner_code == 2:
        winner_name = away_team.get("name")

    return {
        "source": "TennisApi",
        "match_id": event.get("id"),
        "custom_id": event.get("customId"),
        "slug": event.get("slug"),
        "player1": home_team.get("name"),
        "player2": away_team.get("name"),
        "home_team_id": home_team.get("id"),
        "away_team_id": away_team.get("id"),
        "home_seed": event.get("homeTeamSeed"),
        "away_seed": event.get("awayTeamSeed"),
        "tournament": unique_tournament.get("name") or tournament.get("name"),
        "tournament_slug": unique_tournament.get("slug") or tournament.get("slug"),
        "category": category.get("name"),
        "category_id": category.get("id"),
        "round": safe_get(event, "roundInfo", "name"),
        "round_number": safe_get(event, "roundInfo", "round"),
        "start_timestamp": event.get("startTimestamp"),
        "start_time_utc": unix_to_iso(event.get("startTimestamp")),
        "status_raw": status,
        "status": normalize_status(status),
        "winner_code": winner_code,
        "winner": winner_name,
        "home_score_current": home_score.get("current"),
        "away_score_current": away_score.get("current"),
        "home_score_period1": home_score.get("period1"),
        "away_score_period1": away_score.get("period1"),
        "home_score_period2": home_score.get("period2"),
        "away_score_period2": away_score.get("period2"),
        "home_score_period3": home_score.get("period3"),
        "away_score_period3": away_score.get("period3"),
        "home_score_period4": home_score.get("period4"),
        "away_score_period4": away_score.get("period4"),
        "home_score_period5": home_score.get("period5"),
        "away_score_period5": away_score.get("period5"),
        "raw": event,
    }


def normalize_winning_odds(odds_payload: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """
    Normalize TennisApi winning odds.

    Expected payload:
    {
        "home": {"fractionalValue": "73/100", "expected": 58, "actual": 53},
        "away": {"fractionalValue": "11/10", "expected": 48, "actual": 60}
    }

    Some TennisApi responses may wrap the data in "odds" or "data"; both are handled.
    """
    if not isinstance(odds_payload, dict):
        return None

    if isinstance(odds_payload.get("odds"), dict):
        odds_payload = odds_payload["odds"]
    elif isinstance(odds_payload.get("data"), dict):
        odds_payload = odds_payload["data"]

    home = odds_payload.get("home") or {}
    away = odds_payload.get("away") or {}

    if not home or not away:
        return None

    home_fractional = home.get("fractionalValue")
    away_fractional = away.get("fractionalValue")
    home_decimal = fractional_to_decimal(home_fractional)
    away_decimal = fractional_to_decimal(away_fractional)

    if home_decimal is None or away_decimal is None:
        return None

    return {
        "source": "TennisApi",
        "home_odds": home_decimal,
        "away_odds": away_decimal,
        "p1_odds": home_decimal,
        "p2_odds": away_decimal,
        "home_fractional": home_fractional,
        "away_fractional": away_fractional,
        "home_expected": home.get("expected"),
        "away_expected": away.get("expected"),
        "home_actual": home.get("actual"),
        "away_actual": away.get("actual"),
        "home_odds_id": home.get("id"),
        "away_odds_id": away.get("id"),
        "raw": odds_payload,
    }
```


## FILE: tennisapi_set_markets.py

```
import logging
from typing import Any, Dict, List, Optional, Tuple

from tennisapi_client import TennisApiClient, fractional_to_decimal

logger = logging.getLogger(__name__)

_SET_MARKET_CACHE: Dict[int, Dict[str, Any]] = {}


def safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def implied_probability(decimal_odds: Optional[float]) -> Optional[float]:
    if not decimal_odds or decimal_odds <= 1:
        return None
    return 1.0 / decimal_odds


def normalize_pair_probability(p1_odds: Optional[float], p2_odds: Optional[float]) -> Tuple[Optional[float], Optional[float]]:
    p1_raw = implied_probability(p1_odds)
    p2_raw = implied_probability(p2_odds)
    if p1_raw is None or p2_raw is None:
        return None, None
    total = p1_raw + p2_raw
    if total <= 0:
        return None, None
    return p1_raw / total, p2_raw / total


def choice_decimal(choice: Dict[str, Any]) -> Optional[float]:
    if not isinstance(choice, dict):
        return None
    for key in ["fractionalValue", "initialFractionalValue"]:
        value = choice.get(key)
        if value:
            decimal = fractional_to_decimal(str(value))
            if decimal and decimal > 1.0:
                return decimal
    for key in ["decimalValue", "value", "price"]:
        value = choice.get(key)
        if value is None:
            continue
        try:
            decimal = float(value)
            if decimal > 1.0:
                return decimal
        except Exception:
            continue
    return None


def market_choices_pair(market: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    choices = market.get("choices")
    if not isinstance(choices, list) or len(choices) < 2:
        return None, None
    return choice_decimal(choices[0]), choice_decimal(choices[1])


def find_over_under(market: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    choices = market.get("choices")
    if not isinstance(choices, list) or len(choices) < 2:
        return None, None

    over_odds = None
    under_odds = None
    for choice in choices:
        name = str(choice.get("name") or choice.get("choiceName") or "").lower()
        decimal = choice_decimal(choice)
        if "over" in name:
            over_odds = decimal
        elif "under" in name:
            under_odds = decimal

    if over_odds is None or under_odds is None:
        # TennisApi usually returns Over first, Under second for marketId 12.
        over_odds = choice_decimal(choices[0])
        under_odds = choice_decimal(choices[1])

    return over_odds, under_odds


def parse_line(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(str(value).replace(",", "."))
    except Exception:
        return None


def normalize_markets_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("markets"), list):
        return payload["markets"]
    featured = payload.get("featured")
    if isinstance(featured, dict):
        markets = []
        for value in featured.values():
            if isinstance(value, dict):
                markets.append(value)
        return markets
    return []


def parse_set_markets(payload: Dict[str, Any], event_id: Optional[int] = None) -> Dict[str, Any]:
    markets = normalize_markets_payload(payload)
    output: Dict[str, Any] = {
        "event_id": event_id or payload.get("eventId"),
        "match_winner": None,
        "first_set_winner": None,
        "total_games": None,
        "tie_break": None,
        "raw_market_count": len(markets),
    }

    for market in markets:
        if not isinstance(market, dict):
            continue
        market_id = market.get("marketId")
        market_name = str(market.get("marketName") or "").lower()
        market_period = str(market.get("marketPeriod") or "").lower()

        if market_id == 1 or ("full time" in market_name and "match" in market_period):
            p1, p2 = market_choices_pair(market)
            p1_prob, p2_prob = normalize_pair_probability(p1, p2)
            if p1 and p2:
                output["match_winner"] = {
                    "p1_odds": p1,
                    "p2_odds": p2,
                    "p1_probability": p1_prob,
                    "p2_probability": p2_prob,
                    "raw": market,
                }

        elif market_id == 11 or "first set winner" in market_name:
            p1, p2 = market_choices_pair(market)
            p1_prob, p2_prob = normalize_pair_probability(p1, p2)
            if p1 and p2:
                output["first_set_winner"] = {
                    "p1_odds": p1,
                    "p2_odds": p2,
                    "p1_probability": p1_prob,
                    "p2_probability": p2_prob,
                    "raw": market,
                }

        elif market_id == 12 or "total games" in market_name:
            line = parse_line(market.get("choiceGroup"))
            over_odds, under_odds = find_over_under(market)
            over_prob, under_prob = normalize_pair_probability(over_odds, under_odds)
            if line is not None and over_odds and under_odds:
                output["total_games"] = {
                    "line": line,
                    "over_odds": over_odds,
                    "under_odds": under_odds,
                    "over_probability": over_prob,
                    "under_probability": under_prob,
                    "raw": market,
                }

        elif market_id == 13 or "tie break" in market_name:
            yes_odds, no_odds = market_choices_pair(market)
            yes_prob, no_prob = normalize_pair_probability(yes_odds, no_odds)
            if yes_odds and no_odds:
                output["tie_break"] = {
                    "yes_odds": yes_odds,
                    "no_odds": no_odds,
                    "yes_probability": yes_prob,
                    "no_probability": no_prob,
                    "raw": market,
                }

    return output


def get_set_markets(event_id: Optional[int], force_refresh: bool = False) -> Dict[str, Any]:
    if not event_id:
        return {}
    event_id = int(event_id)
    if not force_refresh and event_id in _SET_MARKET_CACHE:
        return _SET_MARKET_CACHE[event_id]

    client = TennisApiClient()
    payload = client.get_all_odds_for_event(event_id) or {}
    parsed = parse_set_markets(payload, event_id=event_id)
    _SET_MARKET_CACHE[event_id] = parsed
    return parsed


if __name__ == "__main__":
    import sys, json
    logging.basicConfig(level=logging.INFO)
    eid = int(sys.argv[1]) if len(sys.argv) > 1 else 14232981
    print(json.dumps(get_set_markets(eid, force_refresh=True), ensure_ascii=False, indent=2))
```


## FILE: tests/test_marq_ai.py

```
from src.marq_ai import build_marq_ai


def main():

    marq = build_marq_ai(
        opening_odds=2.10,
        current_odds=1.85,
        movement_history=[
            {
                "odds": 2.10,
                "timestamp": 1,
            },
            {
                "odds": 2.05,
                "timestamp": 2,
            },
            {
                "odds": 2.00,
                "timestamp": 3,
            },
            {
                "odds": 1.95,
                "timestamp": 4,
            },
            {
                "odds": 1.90,
                "timestamp": 5,
            },
            {
                "odds": 1.85,
                "timestamp": 6,
            },
        ],
    )

    print()
    print("================================")
    print("         MARQ AI TEST")
    print("================================")
    print()

    print(f"Score       : {marq.score}")
    print(f"Signal      : {marq.signal}")
    print(f"Direction   : {marq.direction}")
    print(f"Strength    : {marq.strength}")
    print(f"Consistency : {marq.consistency}")

    print()
    print("================================")
    print()


if __name__ == "__main__":
    main()
```


## FILE: tests/test_marq_provider.py

```
from src.marq_ai import (
    fetch_marq_market_data,
)


def main():

    result = fetch_marq_market_data(
        player1="Daniil Medvedev",
        player2="Kamil Majchrzak",
        date_only="2026-06-13",
    )

    print()
    print("========== MARQ PROVIDER ==========")
    print(result)
    print("===================================")
    print()


if __name__ == "__main__":
    main()
```


## FILE: update.py

```
import glob
import json
import os
import re
from datetime import datetime
from zoneinfo import ZoneInfo

from play_history import (
    betting_day,
    save_all_snapshot,
    save_top5_snapshot,
)

from prediction_engine_top import (
    build_all_predictions,
    get_top_predictions,
)

from src.bst_ai.service import (
    build_bst_ai_comparison,
)

from src.marq_ai import (
    build_marq_from_match,
)


ALL_SNAPSHOT_DIR = "data/pick_history/all"
TOP5_SNAPSHOT_DIR = "data/pick_history/top5"
LOCAL_TZ = ZoneInfo("Europe/Bratislava")


# -----------------------------------------------------------------------------
# Generic JSON helpers
# -----------------------------------------------------------------------------


def save_json(path, data):
    directory = os.path.dirname(path)

    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
        )


def load_json(path, default):
    try:
        if not path:
            return default

        if not os.path.exists(path):
            return default

        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    except Exception as exc:
        print(
            "UPDATE JSON LOAD ERROR:",
            path,
            str(exc),
        )

        return default


def is_non_empty_list(data):
    return isinstance(data, list) and len(data) > 0


def safe_float(value):
    try:
        if value is None:
            return None

        if value == "":
            return None

        return float(value)

    except Exception:
        return None


# -----------------------------------------------------------------------------
# Snapshot helpers
# -----------------------------------------------------------------------------


def snapshot_path(kind, date):
    if kind == "all":
        return os.path.join(
            ALL_SNAPSHOT_DIR,
            f"{date}.json",
        )

    if kind == "top5":
        return os.path.join(
            TOP5_SNAPSHOT_DIR,
            f"{date}.json",
        )

    raise ValueError(
        f"Unsupported snapshot kind: {kind}"
    )


def extract_date_from_filename(path):
    filename = os.path.basename(path or "")

    match = re.search(
        r"(\d{4}-\d{2}-\d{2})",
        filename,
    )

    if not match:
        return ""

    return match.group(1)


def latest_non_empty_snapshot(kind):
    if kind == "all":
        pattern = os.path.join(
            ALL_SNAPSHOT_DIR,
            "*.json",
        )

    elif kind == "top5":
        pattern = os.path.join(
            TOP5_SNAPSHOT_DIR,
            "*.json",
        )

    else:
        raise ValueError(
            f"Unsupported snapshot kind: {kind}"
        )

    files = glob.glob(pattern)

    files.sort(
        key=lambda path: (
            extract_date_from_filename(path),
            os.path.getmtime(path),
        ),
        reverse=True,
    )

    for path in files:
        data = load_json(
            path,
            [],
        )

        if is_non_empty_list(data):
            print(
                "LATEST NON-EMPTY SNAPSHOT:",
                kind,
                path,
                len(data),
            )

            return data

    print(
        "LATEST NON-EMPTY SNAPSHOT:",
        kind,
        None,
    )

    return []


def load_today_snapshot(kind, date):
    path = snapshot_path(
        kind,
        date,
    )

    data = load_json(
        path,
        [],
    )

    if is_non_empty_list(data):
        print(
            "TODAY SNAPSHOT FOUND:",
            kind,
            path,
            len(data),
        )

        return data

    if os.path.exists(path):
        print(
            "TODAY SNAPSHOT EXISTS BUT IS EMPTY - IGNORING:",
            kind,
            path,
        )

    return []


def save_non_empty_all_snapshot(date, all_predictions):
    if not is_non_empty_list(all_predictions):
        print(
            "SKIP ALL SNAPSHOT SAVE:",
            "generated ALL is empty",
        )

        return load_today_snapshot(
            "all",
            date,
        )

    snapshot = save_all_snapshot(
        date=date,
        all_predictions=all_predictions,
    )

    if is_non_empty_list(snapshot):
        return snapshot

    path = snapshot_path(
        "all",
        date,
    )

    print(
        "REPAIR EMPTY ALL SNAPSHOT WITH NON-EMPTY GENERATED DATA:",
        path,
        len(all_predictions),
    )

    save_json(
        path,
        all_predictions,
    )

    return all_predictions


def save_non_empty_top5_snapshot(date, top_predictions):
    if not is_non_empty_list(top_predictions):
        print(
            "SKIP TOP5 SNAPSHOT SAVE:",
            "generated TOP5 is empty",
        )

        return load_today_snapshot(
            "top5",
            date,
        )

    snapshot = save_top5_snapshot(
        date=date,
        top5_predictions=top_predictions,
    )

    if is_non_empty_list(snapshot):
        return snapshot

    path = snapshot_path(
        "top5",
        date,
    )

    print(
        "REPAIR EMPTY TOP5 SNAPSHOT WITH NON-EMPTY GENERATED DATA:",
        path,
        len(top_predictions),
    )

    save_json(
        path,
        top_predictions,
    )

    return top_predictions


# -----------------------------------------------------------------------------
# Public output source selection
# -----------------------------------------------------------------------------


def choose_public_all_predictions(
    generated_all_predictions,
    all_snapshot,
):
    # Rule:
    # If there is any current/generated ALL content, use it.
    # Snapshot is used only when today's generated offer is empty.
    #
    # This prevents mixing current picks with old snapshot picks.

    if is_non_empty_list(generated_all_predictions):
        print(
            "PUBLIC ALL SOURCE:",
            "generated predictions - no snapshot fill",
            len(generated_all_predictions),
        )

        return generated_all_predictions

    if is_non_empty_list(all_snapshot):
        print(
            "PUBLIC ALL SOURCE:",
            "today immutable snapshot fallback",
            len(all_snapshot),
        )

        return all_snapshot

    restored_all = latest_non_empty_snapshot(
        "all"
    )

    if is_non_empty_list(restored_all):
        print(
            "PUBLIC ALL SOURCE:",
            "latest non-empty snapshot fallback",
            len(restored_all),
        )

        return restored_all

    raise RuntimeError(
        "No ALL predictions available. "
        "Generated ALL is empty and no non-empty immutable ALL snapshot exists. "
        "Refusing to write empty public ALL JSON."
    )


def choose_public_top_predictions(
    generated_top_predictions,
    top5_snapshot,
    public_all_predictions,
):
    # Rule:
    # If there is at least one current/generated TOP pick, use only current picks.
    # Do not fill missing positions up to TOP5 from old snapshot.
    # Snapshot is used only when today's generated TOP offer is empty.

    if is_non_empty_list(generated_top_predictions):
        print(
            "PUBLIC TOP5 SOURCE:",
            "generated predictions - no snapshot fill",
            len(generated_top_predictions),
        )

        return generated_top_predictions

    # If generated TOP is empty, but current/generated ALL exists,
    # try deriving TOP from current ALL before falling back to snapshots.
    if is_non_empty_list(public_all_predictions):
        print(
            "PUBLIC TOP5 SOURCE:",
            "trying to derive from public ALL predictions",
        )

        derived_top = get_top_predictions(
            public_all_predictions,
        )

        if is_non_empty_list(derived_top):
            print(
                "PUBLIC TOP5 DERIVED COUNT:",
                len(derived_top),
            )

            return derived_top

    if is_non_empty_list(top5_snapshot):
        print(
            "PUBLIC TOP5 SOURCE:",
            "today immutable snapshot fallback",
            len(top5_snapshot),
        )

        return top5_snapshot

    restored_top5 = latest_non_empty_snapshot(
        "top5"
    )

    if is_non_empty_list(restored_top5):
        print(
            "PUBLIC TOP5 SOURCE:",
            "latest non-empty snapshot fallback",
            len(restored_top5),
        )

        return restored_top5

    print(
        "PUBLIC TOP5 WARNING:",
        "No generated TOP5, no derived TOP5, no TOP5 snapshot, "
        "and no historical TOP5. Writing empty TOP5 public JSON. "
        "build_pages.py can derive TOP5 from ALL."
    )

    return []


# -----------------------------------------------------------------------------
# Match keys / field normalization / enrichment helpers
# -----------------------------------------------------------------------------


def normalize_text(value):
    return str(value or "").strip().lower()


def split_match_players(match_text):
    text = str(match_text or "").strip()

    if not text:
        return None, None

    separators = [
        " vs ",
        " v ",
        " - ",
    ]

    for separator in separators:
        if separator in text:
            parts = text.split(separator, 1)

            if len(parts) == 2:
                player1 = parts[0].strip()
                player2 = parts[1].strip()

                if player1 and player2:
                    return player1, player2

    return None, None


def ensure_player_fields(prediction):
    player1 = prediction.get("player1")
    player2 = prediction.get("player2")

    if player1 and player2:
        return prediction

    derived_player1, derived_player2 = split_match_players(
        prediction.get("match")
    )

    changed = False

    if not player1 and derived_player1:
        prediction["player1"] = derived_player1
        changed = True

    if not player2 and derived_player2:
        prediction["player2"] = derived_player2
        changed = True

    if changed:
        print(
            "ENRICH PLAYER FIELDS:",
            prediction.get("match"),
            "player1=",
            prediction.get("player1"),
            "player2=",
            prediction.get("player2"),
        )

    return prediction


def prediction_key(prediction):
    prediction = ensure_player_fields(
        dict(prediction)
    )

    player1 = normalize_text(
        prediction.get("player1")
    )

    player2 = normalize_text(
        prediction.get("player2")
    )

    pick = normalize_text(
        prediction.get("pick")
    )

    match_start = normalize_text(
        prediction.get("match_start")
    )

    if player1 and player2 and pick and match_start:
        return (
            player1,
            player2,
            pick,
            match_start,
        )

    if player1 and player2 and pick:
        return (
            player1,
            player2,
            pick,
        )

    return (
        normalize_text(prediction.get("match")),
        pick,
    )


def build_fresh_index(fresh_predictions):
    index = {}

    for prediction in fresh_predictions or []:
        key = prediction_key(
            prediction
        )

        index[key] = prediction

    return index


def find_fresh_prediction(prediction, fresh_index):
    key = prediction_key(
        prediction
    )

    fresh = fresh_index.get(key)

    if fresh:
        return fresh

    normalized = ensure_player_fields(
        dict(prediction)
    )

    fallback_key = (
        normalize_text(normalized.get("player1")),
        normalize_text(normalized.get("player2")),
        normalize_text(normalized.get("pick")),
    )

    return fresh_index.get(fallback_key)


def extract_match_date(prediction):
    start_value = prediction.get("match_start")

    if not start_value:
        return None

    try:
        text = str(start_value)

        if text.endswith("Z"):
            text = text.replace("Z", "+00:00")

        dt = datetime.fromisoformat(text)

        if dt.tzinfo is None:
            return text[:10]

        local_dt = dt.astimezone(
            LOCAL_TZ,
        )

        return local_dt.strftime("%Y-%m-%d")

    except Exception:
        text = str(start_value)

        if len(text) >= 10:
            return text[:10]

    return None


def refresh_bst_fields(prediction):
    prediction = ensure_player_fields(
        prediction
    )

    player1 = prediction.get("player1")
    player2 = prediction.get("player2")
    pick = prediction.get("pick")
    surface = prediction.get("surface")

    corq_probability = safe_float(
        prediction.get("corq_ai_probability")
        or prediction.get("corq_display_probability")
        or prediction.get("probability")
    )

    if not player1 or not player2 or not pick:
        print(
            "ENRICH BST SKIP - missing players/pick:",
            prediction.get("match"),
            "player1=",
            player1,
            "player2=",
            player2,
            "pick=",
            pick,
        )

        return prediction

    if corq_probability is None:
        print(
            "ENRICH BST SKIP - missing corq probability:",
            prediction.get("match"),
        )

        return prediction

    try:
        bst_ai = build_bst_ai_comparison(
            player1=player1,
            player2=player2,
            pick=pick,
            surface=surface,
            corq_probability=corq_probability,
            tour=prediction.get("gender"),
        )

        fields = [
            "corq_ai_probability",
            "bst_ai_probability",
            "ai_match",
            "ai_gap",
            "ai_signed_gap",
            "ai_lean",
            "ai_direction_match",
            "ai_match_color",
            "bst_ai_status",
            "bst_ai_reason",
            "bst_ai_rating_type",
            "bst_player1_found",
            "bst_player2_found",
        ]

        for field in fields:
            prediction[field] = bst_ai.get(field)

        print(
            "ENRICH BST:",
            prediction.get("match"),
            "player1=",
            player1,
            "player2=",
            player2,
            "pick=",
            pick,
            "status=",
            prediction.get("bst_ai_status"),
            "bst=",
            prediction.get("bst_ai_probability"),
        )

    except Exception as exc:
        print(
            "ENRICH BST ERROR:",
            prediction.get("match"),
            str(exc),
        )

    return prediction


def refresh_marq_fields(prediction):
    prediction = ensure_player_fields(
        prediction
    )

    player1 = prediction.get("player1")
    player2 = prediction.get("player2")
    pick = prediction.get("pick")

    match_date = extract_match_date(
        prediction
    )

    if not player1 or not player2 or not pick or not match_date:
        print(
            "ENRICH MARQ SKIP:",
            prediction.get("match"),
            "player1=",
            player1,
            "player2=",
            player2,
            "pick=",
            pick,
            "date=",
            match_date,
        )

        return prediction

    try:
        marq_ai = build_marq_from_match(
            player1=player1,
            player2=player2,
            date_only=match_date,
            pick=pick,
        )

        prediction["marq_ai_score"] = getattr(
            marq_ai,
            "score",
            None,
        )

        prediction["marq_ai_signal"] = getattr(
            marq_ai,
            "signal",
            None,
        )

        prediction["marq_ai_direction"] = getattr(
            marq_ai,
            "direction",
            None,
        )

        prediction["marq_ai_strength"] = getattr(
            marq_ai,
            "strength",
            None,
        )

        prediction["marq_ai_consistency"] = getattr(
            marq_ai,
            "consistency",
            None,
        )

        print(
            "ENRICH MARQ:",
            prediction.get("match"),
            "score=",
            prediction.get("marq_ai_score"),
            "signal=",
            prediction.get("marq_ai_signal"),
        )

    except Exception as exc:
        print(
            "ENRICH MARQ ERROR:",
            prediction.get("match"),
            str(exc),
        )

    return prediction


def merge_refreshable_fields(base_prediction, fresh_prediction):
    if not isinstance(fresh_prediction, dict):
        return base_prediction

    refreshable_fields = [
        "player1",
        "player2",
        "bst_ai_probability",
        "ai_match",
        "ai_gap",
        "ai_signed_gap",
        "ai_lean",
        "ai_direction_match",
        "ai_match_color",
        "bst_ai_status",
        "bst_ai_reason",
        "bst_ai_rating_type",
        "bst_player1_found",
        "bst_player2_found",
        "marq_ai_score",
        "marq_ai_signal",
        "marq_ai_direction",
        "marq_ai_strength",
        "marq_ai_consistency",
    ]

    for field in refreshable_fields:
        if field in fresh_prediction:
            base_prediction[field] = fresh_prediction.get(field)

    return base_prediction


def enrich_public_predictions(
    public_predictions,
    fresh_predictions,
    label,
):
    if not is_non_empty_list(public_predictions):
        return public_predictions

    fresh_index = build_fresh_index(
        fresh_predictions
    )

    enriched = []

    print(
        "ENRICH PUBLIC PREDICTIONS:",
        label,
        "count=",
        len(public_predictions),
    )

    for prediction in public_predictions:
        updated = ensure_player_fields(
            dict(prediction)
        )

        fresh = find_fresh_prediction(
            updated,
            fresh_index,
        )

        if fresh:
            updated = merge_refreshable_fields(
                updated,
                fresh,
            )

            print(
                "ENRICH FROM FRESH:",
                label,
                updated.get("match"),
                "bst=",
                updated.get("bst_ai_probability"),
                "status=",
                updated.get("bst_ai_status"),
            )

            if updated.get("bst_ai_status") != "OK":
                updated = refresh_bst_fields(
                    updated
                )

            if updated.get("marq_ai_score") is None:
                updated = refresh_marq_fields(
                    updated
                )

        else:
            print(
                "ENRICH FROM RECOMPUTE:",
                label,
                updated.get("match"),
            )

            updated = refresh_bst_fields(
                updated
            )

            updated = refresh_marq_fields(
                updated
            )

        enriched.append(updated)

    return enriched


# -----------------------------------------------------------------------------
# Main workflow entry
# -----------------------------------------------------------------------------


def run():
    today = betting_day()

    print("BETTING DAY:", today)
    print("BUILDING ALL PREDICTIONS...")

    all_predictions = build_all_predictions()

    print(
        "GENERATED ALL COUNT:",
        len(all_predictions)
        if isinstance(all_predictions, list)
        else "invalid",
    )

    print("BUILDING TOP5 PREDICTIONS...")

    if is_non_empty_list(all_predictions):
        top_predictions = get_top_predictions(
            all_predictions
        )
    else:
        top_predictions = []

    print(
        "GENERATED TOP5 COUNT:",
        len(top_predictions)
        if isinstance(top_predictions, list)
        else "invalid",
    )

    os.makedirs("public", exist_ok=True)
    os.makedirs(ALL_SNAPSHOT_DIR, exist_ok=True)
    os.makedirs(TOP5_SNAPSHOT_DIR, exist_ok=True)

    print("LOADING TODAY IMMUTABLE SNAPSHOTS...")

    existing_all_snapshot = load_today_snapshot(
        "all",
        today,
    )

    existing_top5_snapshot = load_today_snapshot(
        "top5",
        today,
    )

    print("SAVING IMMUTABLE ALL SNAPSHOT IF NON-EMPTY...")

    if is_non_empty_list(existing_all_snapshot):
        all_snapshot = existing_all_snapshot

        print(
            "KEEPING EXISTING NON-EMPTY ALL SNAPSHOT:",
            len(all_snapshot),
        )
    else:
        all_snapshot = save_non_empty_all_snapshot(
            date=today,
            all_predictions=all_predictions,
        )

    print("SAVING IMMUTABLE TOP5 SNAPSHOT IF NON-EMPTY...")

    if is_non_empty_list(existing_top5_snapshot):
        top5_snapshot = existing_top5_snapshot

        print(
            "KEEPING EXISTING NON-EMPTY TOP5 SNAPSHOT:",
            len(top5_snapshot),
        )
    else:
        top5_snapshot = save_non_empty_top5_snapshot(
            date=today,
            top_predictions=top_predictions,
        )

    print(
        "IMMUTABLE ALL SNAPSHOT COUNT:",
        len(all_snapshot)
        if isinstance(all_snapshot, list)
        else "invalid",
    )

    print(
        "IMMUTABLE TOP5 SNAPSHOT COUNT:",
        len(top5_snapshot)
        if isinstance(top5_snapshot, list)
        else "invalid",
    )

    public_all_predictions = choose_public_all_predictions(
        generated_all_predictions=all_predictions,
        all_snapshot=all_snapshot,
    )

    public_top_predictions = choose_public_top_predictions(
        generated_top_predictions=top_predictions,
        top5_snapshot=top5_snapshot,
        public_all_predictions=public_all_predictions,
    )

    public_all_predictions = enrich_public_predictions(
        public_predictions=public_all_predictions,
        fresh_predictions=all_predictions,
        label="ALL",
    )

    public_top_predictions = enrich_public_predictions(
        public_predictions=public_top_predictions,
        fresh_predictions=all_predictions,
        label="TOP5",
    )

    top_path = f"public/predictions_{today}.json"
    all_path = f"public/all_predictions_{today}.json"

    save_json(
        top_path,
        public_top_predictions,
    )

    save_json(
        all_path,
        public_all_predictions,
    )

    print(
        "SAVED TOP PUBLIC JSON:",
        top_path,
        len(public_top_predictions),
    )

    print(
        "SAVED ALL PUBLIC JSON:",
        all_path,
        len(public_all_predictions),
    )

    print(
        "SAVED TOP5 SNAPSHOT:",
        len(top5_snapshot)
        if isinstance(top5_snapshot, list)
        else "invalid",
    )

    print(
        "SAVED ALL SNAPSHOT:",
        len(all_snapshot)
        if isinstance(all_snapshot, list)
        else "invalid",
    )


if __name__ == "__main__":
    run()
```
