name: Tennis Sources Probe

on:
  workflow_dispatch:

jobs:
  probe:
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: "3.10"

      - name: Install dependencies
        run: pip install requests beautifulsoup4

      - name: Run no-key tennis source probe
        run: python tennis_sources_probe.py

      - name: Print probe summary
        run: |
          echo "===== PROBE SUMMARY ====="
          cat public/tennis_sources_probe_summary.json || true
          echo ""
          echo "===== FULL OUTPUT ====="
          cat public/tennis_sources_probe_full.json || true

      - name: List generated files
        run: ls -R public || true

      - name: Upload probe output
        uses: actions/upload-artifact@v4
        with:
          name: tennis-sources-probe-output
          path: public/
