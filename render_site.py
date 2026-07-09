from pathlib import Path
import py_compile

path = Path("render_site.py")
text = path.read_text(encoding="utf-8")

replacements = {
    'format_pct_points(metrics.get("blenq_pct"))': "format_pct_points(metrics.get('blenq_pct'))",
    'pct(prediction.get("market_fair_pick"))': "pct(prediction.get('market_fair_pick'))",
    'pct(prediction.get("market_gap"))': "pct(prediction.get('market_gap'))",
    'format_edge(prediction.get("edge_pp"))': "format_edge(prediction.get('edge_pp'))",
    'edge_pct(prediction.get("edge_pp"))': "edge_pct(prediction.get('edge_pp'))",
    'safe(prediction.get("blenq_tier"))': "safe(prediction.get('blenq_tier'))",
    'safe(prediction.get("blenq_risk"))': "safe(prediction.get('blenq_risk'))",
    'prediction.get("market_fair_pick")': "prediction.get('market_fair_pick')",
    'prediction.get("market_gap")': "prediction.get('market_gap')",
    'prediction.get("edge_pp")': "prediction.get('edge_pp')",
    'prediction.get("blenq_tier")': "prediction.get('blenq_tier')",
    'prediction.get("blenq_risk")': "prediction.get('blenq_risk')",
}

for old, new in replacements.items():
    text = text.replace(old, new)

path.write_text(text, encoding="utf-8")
py_compile.compile(str(path), doraise=True)
print("OK: render_site.py syntax check passed")
