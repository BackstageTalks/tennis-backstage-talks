from pathlib import Path
import py_compile

path = Path("render_site.py")
text = path.read_text(encoding="utf-8")
lines = text.splitlines()

# 1) Remove accidental mapping lines that may have been pasted/written into render_site.py.
# These look like:  'format_pct_points(metrics.get('blenq_pct'))': ...
bad_prefixes = (
    "'format_pct_points(metrics.get(",
    '"format_pct_points(metrics.get(',
    "'pct(prediction.get(",
    '"pct(prediction.get(',
    "'format_edge(prediction.get(",
    '"format_edge(prediction.get(',
    "'edge_pct(prediction.get(",
    '"edge_pct(prediction.get(',
    "'safe(prediction.get(",
    '"safe(prediction.get(',
    "'prediction.get(",
    '"prediction.get(',
)
cleaned = []
for line in lines:
    stripped = line.strip()
    if stripped.startswith(bad_prefixes) and stripped.endswith(","):
        continue
    cleaned.append(line)
text = "\n".join(cleaned) + "\n"

# 2) Fix nested-quote f-string expressions inside render_site.py RSS description block.
replacements = {
    'format_pct_points(metrics.get("blenq_pct"))': "format_pct_points(metrics.get('blenq_pct'))",
    'pct(prediction.get("market_fair_pick"))': "pct(prediction.get('market_fair_pick'))",
    'pct(prediction.get("market_gap"))': "pct(prediction.get('market_gap'))",
    'format_edge(prediction.get("edge_pp"))': "format_edge(prediction.get('edge_pp'))",
    'edge_pct(prediction.get("edge_pp"))': "edge_pct(prediction.get('edge_pp'))",
    'safe(prediction.get("blenq_tier"))': "safe(prediction.get('blenq_tier'))",
    'safe(prediction.get("blenq_risk"))': "safe(prediction.get('blenq_risk'))",
}
for old, new in replacements.items():
    text = text.replace(old, new)

path.write_text(text, encoding="utf-8")
py_compile.compile(str(path), doraise=True)
print("OK: render_site.py syntax check passed")
