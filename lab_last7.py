for match in grouped```

Najbezpečnejšie teraz nie je celý súbor ručne lepiť, ale **prepísať iba spodnú časť od `def run()` až po koniec**.

---

## ✅ Sprav toto v repozitári

Spusti alebo vlož do terminálu v Codespaces / lokálne:

```bash
python - <<'PY'
from pathlib import Path

path = Path("lab_last7.py")
text = path.read_text(encoding="utf-8")

# Oprav prípadné HTML entity, ak sa dostali do súboru
text = (
    text
    .replace("&lt;=", "<=")
    .replace("&gt;=", ">=")
    .replace("&lt;", "<")
    .replace("&gt;", ">")
)

marker = "def run():"
if marker not in text:
    raise SystemExit("ERROR: def run() not found in lab_last7.py")

head = text.split(marker)[0]

tail = r'''def run():
    os.makedirs(OUT_DIR, exist_ok=True)

    start_date, end_date = date_range_last_7_completed_days()

    print("LAST 7 LAB PERIOD:", start_date, end_date)

    all_history = load_all_matches(2018, 2030)

    test_matches = filter_matches_between(all_history, start_date, end_date)

    print("TEST MATCHES:", len(test_matches))

    grouped = group_matches_by_date(test_matches)

    elo_rows = []
    form_rows = []

    for date in sorted(grouped.keys()):
        print("PROCESSING DATE:", date, "MATCHES:", len(grouped[date]))

        training_matches = filter_matches_before(all_history, date)

        elo_store = build_elo(training_matches)
        form_store = build_form_store(training_matches)

        for match in groupedelo_rows.append(
                make_elo_only_prediction(match, elo_store)
            )

            form_rows.append(
                make_elo_form_prediction(match, elo_store, form_store)
            )

    elo_rows.sort(key=lambda x: x["probability"], reverse=True)
    form_rows.sort(key=lambda x: x["probability"], reverse=True)

    elo_summary = summarize(elo_rows)
    form_summary = summarize(form_rows)

    output = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "period_start": start_date,
        "period_end": end_date,
        "mode": "rolling_last_7_completed_days_retro_lab",
        "note": "Odds-based PLAY profitability requires stored daily odds snapshots.",
        "elo_only_summary": elo_summary,
        "elo_form_summary": form_summary,
        "elo_only_rows": elo_rows,
        "elo_form_rows": form_rows,
    }

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(render_html(
            start_date=start_date,
            end_date=end_date,
            elo_rows=elo_rows,
            form_rows=form_rows,
            elo_summary=elo_summary,
            form_summary=form_summary,
        ))

    print("WROTE", OUT_JSON)
    print("WROTE", OUT_HTML)
    print("ELO SUMMARY:", elo_summary)
    print("FORM SUMMARY:", form_summary)


if __name__ == "__main__":
    run()
'''

path.write_text(head + tail, encoding="utf-8")
print("lab_last7.py fixed")
PY
