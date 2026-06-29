#!/usr/bin/env bash
set -euo pipefail

BASE="https://backstagetalks.github.io/tennis-backstage-talks"
LINKS="H4V34N1C3D4Y177"

mkdir -p "public/$LINKS"

latest_file () {
  PATTERN="$1"
  FOUND=$(ls public/$PATTERN 2>/dev/null | sort | tail -n 1 || true)

  if [ -n "$FOUND" ]; then
    basename "$FOUND"
  else
    echo ""
  fi
}

TOP_JSON=$(latest_file "predictions_*.json")
ALL_JSON=$(latest_file "all_predictions_*.json")
RESULTS_JSON=$(latest_file "results_*.json")
ALL_RESULTS_JSON=$(latest_file "all_results_*.json")

HUB_FILE="public/$LINKS/index.html"

cat > "$HUB_FILE" <<EOF
<!DOCTYPE html>
<html lang="sk">
<head>
<meta charset="UTF-8">
<title>BackstageTalks Tennis Links</title>
<meta name="robots" content="noindex,nofollow,noarchive">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
* {
  box-sizing: border-box;
}

body {
  font-family: Arial, sans-serif;
  background: #160f0f;
  color: #f4f4f4;
  margin: 0;
  padding: 22px;
}

.container {
  max-width: 900px;
  margin: 0 auto;
}

h1 {
  font-size: 42px;
  line-height: 1.1;
  margin: 26px 0 24px;
}

.section-title {
  color: #cfcfcf;
  font-size: 14px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  margin: 28px 0 10px;
}

.grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 14px;
}

.card {
  background: #211818;
  border: 1px solid #352727;
  border-radius: 16px;
  padding: 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.label {
  font-weight: 700;
  font-size: 18px;
  color: #ffffff;
}

.icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  border-radius: 999px;
  background: #2d3f66;
  color: #ffffff;
  font-size: 20px;
  text-decoration: none;
  flex: 0 0 auto;
}

.icon:hover {
  background: #4162a3;
  text-decoration: none;
}

.footer {
  color: #888;
  margin-top: 26px;
  font-size: 14px;
}

@media (min-width: 760px) {
  .grid {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
</head>
<body>
<div class="container">
<h1>BackstageTalks Tennis Links</h1>

<div class="section-title">Main</div>
<div class="grid">

<div class="card">
  <div class="label">TOP 7 web</div>
  <a class="icon" href="$BASE/" target="_blank" rel="noopener noreferrer">🔗</a>
</div>

<div class="card">
  <div class="label">TOP 7 RSS</div>
  <a class="icon" href="$BASE/tennis.xml" target="_blank" rel="noopener noreferrer">🔗</a>
</div>

<div class="card">
  <div class="label">ALL web</div>
  <a class="icon" href="$BASE/all/" target="_blank" rel="noopener noreferrer">🔗</a>
</div>

<div class="card">
  <div class="label">ALL RSS</div>
  <a class="icon" href="$BASE/tennis_all.xml" target="_blank" rel="noopener noreferrer">🔗</a>
</div>

</div>

<div class="section-title">Results</div>
<div class="grid">

<div class="card">
  <div class="label">TOP 7 výsledky web</div>
  <a class="icon" href="$BASE/results/" target="_blank" rel="noopener noreferrer">🔗</a>
</div>

<div class="card">
  <div class="label">TOP 7 výsledky RSS</div>
  <a class="icon" href="$BASE/results.xml" target="_blank" rel="noopener noreferrer">🔗</a>
</div>

<div class="card">
  <div class="label">ALL výsledky web</div>
  <a class="icon" href="$BASE/all_results/" target="_blank" rel="noopener noreferrer">🔗</a>
</div>

<div class="card">
  <div class="label">ALL výsledky RSS</div>
  <a class="icon" href="$BASE/all_results.xml" target="_blank" rel="noopener noreferrer">🔗</a>
</div>

</div>

<div class="section-title">Audit</div>
<div class="grid">

<div class="card">
  <div class="label">Source manifest</div>
  <a class="icon" href="$BASE/source_manifest.json" target="_blank" rel="noopener noreferrer">🔗</a>
</div>

<div class="card">
  <div class="label">Source audit</div>
  <a class="icon" href="$BASE/source_audit.json" target="_blank" rel="noopener noreferrer">🔗</a>
</div>

</div>
EOF

if [ -n "$TOP_JSON" ] || [ -n "$ALL_JSON" ] || [ -n "$RESULTS_JSON" ] || [ -n "$ALL_RESULTS_JSON" ]; then
cat >> "$HUB_FILE" <<EOF

<div class="section-title">Latest JSON</div>
<div class="grid">
EOF

if [ -n "$TOP_JSON" ]; then
cat >> "$HUB_FILE" <<EOF
<div class="card">
  <div class="label">Latest TOP JSON</div>
  <a class="icon" href="$BASE/$TOP_JSON" target="_blank" rel="noopener noreferrer">🔗</a>
</div>
EOF
fi

if [ -n "$ALL_JSON" ]; then
cat >> "$HUB_FILE" <<EOF
<div class="card">
  <div class="label">Latest ALL JSON</div>
  <a class="icon" href="$BASE/$ALL_JSON" target="_blank" rel="noopener noreferrer">🔗</a>
</div>
EOF
fi

if [ -n "$RESULTS_JSON" ]; then
cat >> "$HUB_FILE" <<EOF
<div class="card">
  <div class="label">Latest TOP results JSON</div>
  <a class="icon" href="$BASE/$RESULTS_JSON" target="_blank" rel="noopener noreferrer">🔗</a>
</div>
EOF
fi

if [ -n "$ALL_RESULTS_JSON" ]; then
cat >> "$HUB_FILE" <<EOF
<div class="card">
  <div class="label">Latest ALL results JSON</div>
  <a class="icon" href="$BASE/$ALL_RESULTS_JSON" target="_blank" rel="noopener noreferrer">🔗</a>
</div>
EOF
fi

cat >> "$HUB_FILE" <<EOF
</div>
EOF
fi

cat >> "$HUB_FILE" <<EOF

<div class="footer">Generated by BackstageTalks Tennis workflow.</div>
</div>
</body>
</html>
EOF

echo "LINK HUB CREATED: $HUB_FILE"

echo "===== LINK HUB PREVIEW ====="
head -n 80 "$HUB_FILE"
