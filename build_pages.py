name: Daily Tennis Predictions

on:
  workflow_dispatch:

  schedule:
    - cron: "10 4 * * *"

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: tennis-pages
  cancel-in-progress: true

jobs:
  build:
    runs-on: ubuntu-latest
    timeout-minutes: 10

    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}

    env:
      ODDS_API_KEY: ${{ secrets.ODDS_API_KEY }}
      LOCAL_TZ_OFFSET_HOURS: "2"
      BET_WINDOW_START_HOUR: "6"
      BET_WINDOW_END_NEXT_DAY_HOUR: "6"

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          fetch-depth: 1

      - name: Check SK/CZ betting window
        id: betting_window
        run: |
          python - <<'PY' >> "$GITHUB_OUTPUT"
          from datetime import datetime
          from zoneinfo import ZoneInfo

          now = datetime.now(ZoneInfo("Europe/Bratislava"))

          print(f"local_time={now.isoformat()}")

          if now.hour < 6:
              print("should_run=false")
          else:
              print("should_run=true")
          PY

      - name: Stop before 06:00 SK/CZ
        if: steps.betting_window.outputs.should_run != 'true'
        run: |
          echo "Current SK/CZ local time: ${{ steps.betting_window.outputs.local_time }}"
          echo "It is before 06:00 SK/CZ. Daily prediction snapshot will not be generated."
          echo "This is intentional to avoid empty 06-06 betting-window output."

      - name: Setup Python
        if: steps.betting_window.outputs.should_run == 'true'
        uses: actions/setup-python@v5
        with:
          python-version: "3.11"
          cache: "pip"

      - name: Install dependencies
        if: steps.betting_window.outputs.should_run == 'true'
        run: |
          python -m pip install --upgrade pip

          if [ -f requirements.txt ]; then
            pip install -r requirements.txt
          else
            pip install requests beautifulsoup4 pandas openpyxl
          fi

      - name: Prepare folders
        if: steps.betting_window.outputs.should_run == 'true'
        run: |
          mkdir -p public
          mkdir -p public/all
          mkdir -p public/results
          mkdir -p data
          mkdir -p data/play_history

      - name: Run predictions
        if: steps.betting_window.outputs.should_run == 'true'
        run: |
          python update.py

      - name: Build TOP and ALL pages
        if: steps.betting_window.outputs.should_run == 'true'
        run: |
          python build_pages.py

      - name: Build lightweight results page
        if: steps.betting_window.outputs.should_run == 'true'
        run: |
          mkdir -p public
          mkdir -p public/results

          if [ ! -f public/results_data.json ]; then
            python - <<'PY'
          import json
          import os
          from datetime import datetime, timezone

          os.makedirs("public", exist_ok=True)

          empty_summary = {
              "picks": 0,
              "won": 0,
              "lost": 0,
              "void": 0,
              "pending": 0,
              "unknown": 0,
              "units": 0.0,
              "win_rate": None
          }

          payload = {
              "generated_at": datetime.now(timezone.utc).isoformat(),
              "today": empty_summary,
              "last_7_days": empty_summary,
              "current_month": empty_summary,
              "all_time": empty_summary,
              "items": [],
              "note": "Lightweight results page. Full results checker is handled by a separate workflow."
          }

          with open("public/results_data.json", "w", encoding="utf-8") as file:
              json.dump(payload, file, indent=2, ensure_ascii=False)
          PY
          fi

          python rss_results.py

      - name: Remove production debug artifacts
        if: steps.betting_window.outputs.should_run == 'true'
        run: |
          rm -f public/elo_debug.json || true
          rm -f public/odds_debug.json || true
          rm -f public/sportscore_debug.json || true
          rm -f public/match_debug.json || true
          rm -f public/results_debug.json || true
          rm -f public/source_audit.json || true
          rm -f public/source_manifest.json || true

      - name: Verify generated public files
        if: steps.betting_window.outputs.should_run == 'true'
        run: |
          echo "=== PUBLIC FILES ==="
          find public -maxdepth 4 -type f | sort

          echo "=== REQUIRED TOP / ALL FILES ==="
          test -f public/index.html
          test -f public/all/index.html
          test -f public/tennis.xml
          test -f public/tennis_all.xml

          echo "=== REQUIRED RESULTS FILES ==="
          test -f public/results/index.html
          test -f public/results.xml
          test -f public/results_data.json

          echo "All required public files exist."

      - name: Setup GitHub Pages
        if: steps.betting_window.outputs.should_run == 'true'
        uses: actions/configure-pages@v5

      - name: Upload GitHub Pages artifact
        if: steps.betting_window.outputs.should_run == 'true'
        uses: actions/upload-pages-artifact@v3
        with:
          path: public

      - name: Deploy GitHub Pages
        if: steps.betting_window.outputs.should_run == 'true'
        id: deployment
        uses: actions/deploy-pages@v4
