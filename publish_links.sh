#!/usr/bin/env bash
set -euo pipefail

echo "===== GENERATE RANDOM-LOOKING LINK HUB 177 ====="

BASE_URL="https://backstagetalks.github.io/tennis-backstage-talks"
PUBLIC_DIR="public"
HUB_DIR="${PUBLIC_DIR}/H4V34N1C3D4Y177"

ALIAS_TOP_PAGE="a7Kp4VzQ9Lm2R8xYa6Td0Hs3BcQw9F"
ALIAS_ALL_PAGE="b8Lm5QaR0Xn3V7tYp2Ks6Hd9CzW4EJ"
ALIAS_TOP_RESULTS="c9Nq6WrS1Yp4K8vLa3Td7Hx0BzF2MQ"
ALIAS_ALL_RESULTS="d0Pr7XsT2Zq5L9vMb4Yh8Kc1WnF6AR"
ALIAS_STATS="k9Mx2Qa7BpL4Vz0TcY8Rn3Hd6Ws1Ef"

ALIAS_TOP_RSS="e1Qs8XtU3Ar6M0vNc5Zp9Ld2YhW7KR"
ALIAS_ALL_RSS="f2Rt9YuV4Bs7N1wOd6Aq0Me3ZiX8LS"
ALIAS_TOP_RESULTS_RSS="g3Sv0ZwW5Ct8O2xPe7Br1Nf4AjY9MT"
ALIAS_ALL_RESULTS_RSS="h4Tw1AxX6Du9P3yQf8Cs2Og5BkZ0NU"

mkdir -p "$HUB_DIR"

GENERATED_AT="$(date -u +"%Y-%m-%d %H:%M:%S UTC")"


copy_page_alias() {
  local source_file="$1"
  local alias_dir="$2"
  local title="$3"

  local target_dir="${PUBLIC_DIR}/${alias_dir}"

  mkdir -p "$target_dir"

  if [ -f "$source_file" ]; then
    cp "$source_file" "${target_dir}/index.html"
    echo "Alias page created: ${target_dir}/index.html from ${source_file}"
  else
    cat > "${target_dir}/index.html" <<EOF
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>${title}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <style>
    body {
      background: #130d0d;
      color: #ffffff;
      font-family: Arial, Helvetica, sans-serif;
      padding: 18px;
    }

    a {
      color: #ffd29b;
      font-weight: 700;
    }

    .muted {
      color: #c9b8ad;
    }
  </style>
</head>
<body>
  <h1>${title}</h1>
  <p class="muted">This output is not available yet.</p>
  <p><a href="${BASE_URL}/H4V34N1C3D4Y177/">Back to Hub 177</a></p>
</body>
</html>
EOF
    echo "Alias placeholder created: ${target_dir}/index.html"
  fi
}


copy_xml_alias() {
  local source_file="$1"
  local alias_file="$2"

  local target_file="${PUBLIC_DIR}/${alias_file}.xml"

  if [ -f "$source_file" ]; then
    cp "$source_file" "$target_file"
    echo "Alias XML created: ${target_file} from ${source_file}"
  else
    cat > "$target_file" <<EOF
<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
  <title>Backstage Talks Tennis Feed</title>
  <link>${BASE_URL}/H4V34N1C3D4Y177/</link>
  <description>Feed not available yet.</description>
  <item>
    <title>Feed not available yet</title>
    <description>This feed has not been generated yet.</description>
  </item>
</channel>
</rss>
EOF
    echo "Alias XML placeholder created: ${target_file}"
  fi
}


copy_page_alias "${PUBLIC_DIR}/index.html" "${ALIAS_TOP_PAGE}" "TOP5 Tennis Picks"
copy_page_alias "${PUBLIC_DIR}/all/index.html" "${ALIAS_ALL_PAGE}" "All Tennis Predictions"
copy_page_alias "${PUBLIC_DIR}/results/index.html" "${ALIAS_TOP_RESULTS}" "TOP5 Tennis Results"
copy_page_alias "${PUBLIC_DIR}/all_results/index.html" "${ALIAS_ALL_RESULTS}" "All Tennis Results"
copy_page_alias "${PUBLIC_DIR}/stats/index.html" "${ALIAS_STATS}" "Model Stats"

copy_xml_alias "${PUBLIC_DIR}/tennis.xml" "${ALIAS_TOP_RSS}"
copy_xml_alias "${PUBLIC_DIR}/tennis_all.xml" "${ALIAS_ALL_RSS}"
copy_xml_alias "${PUBLIC_DIR}/results.xml" "${ALIAS_TOP_RESULTS_RSS}"
copy_xml_alias "${PUBLIC_DIR}/all_results.xml" "${ALIAS_ALL_RESULTS_RSS}"


cat > "${HUB_DIR}/index.html" <<EOF
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Backstage Talks Tennis Hub 177</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">

  <style>
    body {
      margin: 0;
      padding: 18px;
      background: #130d0d;
      color: #ffffff;
      font-family: Arial, Helvetica, sans-serif;
    }

    h1 {
      font-size: 42px;
      line-height: 1.05;
      margin: 0 0 10px 0;
    }

    .disclaimer {
      color: #c9b8ad;
      font-size: 14px;
      margin-bottom: 24px;
      line-height: 1.5;
    }

    .section {
      background: #211717;
      border: 1px solid #3a2929;
      border-radius: 18px;
      padding: 18px;
      margin-bottom: 18px;
    }

    .section h2 {
      margin: 0 0 14px 0;
      font-size: 25px;
      color: #fff3e8;
    }

    .grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(270px, 1fr));
      gap: 14px;
    }

    .card {
      background: #2a1e1e;
      border: 1px solid #463232;
      border-radius: 16px;
      padding: 16px;
      min-height: 128px;
    }

    .card h3 {
      margin: 0 0 8px 0;
      font-size: 19px;
      color: #ffffff;
    }

    .card p {
      margin: 0 0 12px 0;
      color: #cbb8ae;
      font-size: 14px;
      line-height: 1.4;
    }

    .icon {
      font-size: 30px;
      margin-bottom: 10px;
    }

    a {
      color: #ffd29b;
      text-decoration: none;
      font-weight: 700;
      word-break: break-all;
    }

    a:hover {
      text-decoration: underline;
    }

    .badge {
      display: inline-block;
      background: #573a24;
      color: #ffd29b;
      border: 1px solid #805a36;
      border-radius: 999px;
      padding: 3px 9px;
      font-size: 12px;
      margin-bottom: 8px;
    }

    .note {
      color: #a99790;
      font-size: 13px;
      margin-top: 22px;
      line-height: 1.5;
    }

    .small {
      color: #c9b8ad;
      font-size: 13px;
      line-height: 1.4;
    }
  </style>
</head>

<body>
  <h1>🎾 Backstage Talks Tennis Hub 177</h1>

  <div class="disclaimer">
    The data generated by the Backstage Talks STAT model is for statistical and informational purposes only.
  </div>

  <div class="section">
    <h2>⭐ Main Picks</h2>

    <div class="grid">
      <div class="card">
        <div class="icon">⭐</div>
        <div class="badge">TOP5</div>
        <h3>TOP5 Tennis Picks</h3>
        <p>Five highest ELO+ winner predictions where selected player odds are above 1.50.</p>
        <a href="${BASE_URL}/${ALIAS_TOP_PAGE}/">Open TOP5 Picks</a>
      </div>

      <div class="card">
        <div class="icon">📡</div>
        <div class="badge">RSS</div>
        <h3>TOP5 Picks RSS</h3>
        <p>RSS feed for the selected TOP5 picks. Future Telegram bot input.</p>
        <a href="${BASE_URL}/${ALIAS_TOP_RSS}.xml">Open TOP5 RSS</a>
      </div>
    </div>
  </div>

  <div class="section">
    <h2>📋 All Predictions</h2>

    <div class="grid">
      <div class="card">
        <div class="icon">📋</div>
        <div class="badge">ALL</div>
        <h3>All Tennis Predictions</h3>
        <p>All matches from the daily window. Every match gets an ELO+ winner prediction.</p>
        <a href="${BASE_URL}/${ALIAS_ALL_PAGE}/">Open All Predictions</a>
      </div>

      <div class="card">
        <div class="icon">🛰️</div>
        <div class="badge">RSS</div>
        <h3>All Predictions RSS</h3>
        <p>RSS feed containing all ELO+ predictions, not only TOP5.</p>
        <a href="${BASE_URL}/${ALIAS_ALL_RSS}.xml">Open All RSS</a>
      </div>
    </div>
  </div>

  <div class="section">
    <h2>📊 Results</h2>

    <div class="grid">
      <div class="card">
        <div class="icon">🏁</div>
        <div class="badge">TOP5 Results</div>
        <h3>TOP5 Results</h3>
        <p>Results tracking for the selected TOP5 picks.</p>
        <a href="${BASE_URL}/${ALIAS_TOP_RESULTS}/">Open TOP5 Results</a>
      </div>

      <div class="card">
        <div class="icon">✅</div>
        <div class="badge">RSS</div>
        <h3>TOP5 Results RSS</h3>
        <p>RSS feed for TOP5 results.</p>
        <a href="${BASE_URL}/${ALIAS_TOP_RESULTS_RSS}.xml">Open TOP5 Results RSS</a>
      </div>

      <div class="card">
        <div class="icon">📊</div>
        <div class="badge">ALL Results</div>
        <h3>All Results</h3>
        <p>Results tracking for all predicted matches.</p>
        <a href="${BASE_URL}/${ALIAS_ALL_RESULTS}/">Open All Results</a>
      </div>

      <div class="card">
        <div class="icon">🧾</div>
        <div class="badge">RSS</div>
     ${BASE_URL}/${ALIAS_ALL_RESULTS_RSS}.xmlOpen All Results RSS</a>
      </div>
    </div>
  </div>

  <div class="section">
    <h2>📈 Model Stats</h2>

    <div class="grid">
      <div class="card">
        <div class="icon">📈</div>
        <div class="badge">STATS</div>
        <h3>Model Statistics</h3>
        <p>Last 7 days, current month, previous month and all-time performance.</p>
        ${BASE_URL}/${ALIAS_STATS}/Open Model Stats</a>
      </div>

      <div class="card">
        <div class="icon">🗂️</div>
        <div class="badge">JSON</div>
        <h3>Stats JSON</h3>
        <p>Machine-readable statistics output.</p>
        ${BASE_URL}/stats.jsonOpen Stats JSON</a>
      </div>
    </div>
  </div>

  <div class="section">
    <h2>🧭 Model Logic</h2>

    <div class="grid">
      <div class="card">
        <div class="icon">🎯</div>
        <h3>TOP5 Selection</h3>
        <p>
          TOP5 contains the five highest ELO+ win probabilities where selected player odds are above 1.50.
        </p>
      </div>

      <div class="card">
        <div class="icon">📋</div>
        <h3>All Predictions</h3>
        <p>
          All available daily matches receive an ELO+ predicted winner.
        </p>
      </div>

      <div class="card">
        <div class="icon">ℹ️</div>
        <h3>Sets / Games</h3>
        <p>
          Sets and games estimates are informational only and do not affect winner selection.
        </p>
      </div>

      <div class="card">
        <div class="icon">🚫</div>
        <h3>Not Used</h3>
        <p>
          EV, edge and market consensus are not used in the current TOP5 selection.
        </p>
      </div>
    </div>
  </div>

  <div class="note">
    Generated: ${GENERATED_AT}<br>
    Hub URL: ${BASE_URL}/H4V34N1C3D4Y177/
  </div>
</body>
</html>
EOF

echo "Generated ${HUB_DIR}/index.html"
echo "===== RANDOM-LOOKING LINK HUB 177 DONE ====="
