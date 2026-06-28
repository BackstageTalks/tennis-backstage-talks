import json
import os
import datetime

from sources_manifest import source_summary, SOURCES_MANIFEST


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def run():
    os.makedirs("public", exist_ok=True)

    now = datetime.datetime.utcnow().isoformat() + "Z"

    summary = source_summary()

    audit = {
        "generated_at_utc": now,
        "status": "OK",
        "description": "Source map audit. This does not change model outputs.",
        "source_manifest_version": summary["version"],
        "current_year": summary["current_year"],
        "candidate_years": summary["candidate_years"],
        "candidate_years_with_next": summary["candidate_years_with_next"],
        "active_sources": {
            "fixtures": ["SportScore"],
            "men_stats": [
                "TennisMyLife ATP Tour",
                "TennisMyLife ATP Challenger"
            ],
            "odds": ["SportScore"]
        },
        "planned_sources": {
            "men_stats": [
                "TennisMyLife ATP Qualifying",
                "Jeff Sackmann ATP",
                "Jeff Sackmann Grand Slam point-by-point"
            ],
            "women_stats": [
                "Jeff Sackmann WTA",
                "Jeff Sackmann Grand Slam point-by-point"
            ],
            "odds": [
                "tennis-data.co.uk",
                "The Odds API - future paid optional"
            ],
            "wimbledon": [
                "Wimbledon Official",
                "LTA Wimbledon Preview"
            ]
        },
        "rules": [
            "No hardcoded fixed year lists.",
            "Use current year + lookback period or source file discovery.",
            "Missing optional files must not break the workflow.",
            "TOP and ALL outputs must remain separate.",
            "rss.py must read predictions_*.json only.",
            "rss_all.py must read all_predictions_*.json only.",
            "rss_all.py must never write public/index.html.",
            "Workflow must not copy ALL outputs into TOP outputs."
        ],
        "manifest": SOURCES_MANIFEST,
    }

    save_json("public/source_manifest.json", SOURCES_MANIFEST)
    save_json("public/source_audit.json", audit)

    print("SOURCE AUDIT GENERATED")
    print("Manifest version:", summary["version"])
    print("Current year:", summary["current_year"])
    print("Candidate years:", summary["candidate_years"])
    print("Candidate years with next:", summary["candidate_years_with_next"])
    print("Saved: public/source_manifest.json")
    print("Saved: public/source_audit.json")


if __name__ == "__main__":
    run()
