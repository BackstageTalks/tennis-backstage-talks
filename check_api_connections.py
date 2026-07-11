import json
import os
import http.client

RAPIDAPI_KEY = (os.getenv("RAPIDAPI_KEY", "").strip() or os.getenv("TENNISAPI_RAPIDAPI_KEY", "").strip())

TESTS = [
    {
        "name": "TennisApi PRO / primary",
        "host": "tennisapi1.p.rapidapi.com",
        "path": "/api/tennis/event/14232981/odds",
    },
    {
        "name": "Tennis API - ATP WTA ITF / fallback",
        "host": "tennis-api-atp-wta-itf.p.rapidapi.com",
        "path": "/tennis/v2/extend/api/odds/arbitrage/3700653",
    },
    {
        "name": "All Sports API / final fallback",
        "host": "allsportsapi2.p.rapidapi.com",
        "path": "/api/tennis/event/14243166/provider/1/winning-odds",
    },
]


def request(host, path):
    headers = {
        "x-rapidapi-key": RAPIDAPI_KEY,
        "x-rapidapi-host": host,
        "Content-Type": "application/json",
    }
    conn = http.client.HTTPSConnection(host, timeout=25)
    conn.request("GET", path, headers=headers)
    res = conn.getresponse()
    raw = res.read().decode("utf-8", errors="replace")
    return res.status, raw


def main():
    print("RAPIDAPI_KEY:", "SET" if RAPIDAPI_KEY else "MISSING")
    if not RAPIDAPI_KEY:
        raise SystemExit(1)

    for test in TESTS:
        print("\n===", test["name"], "===")
        print("host:", test["host"])
        print("path:", test["path"])
        try:
            status, raw = request(test["host"], test["path"])
            print("status:", status)
            print("body_preview:", raw[:800])
            try:
                data = json.loads(raw) if raw else None
                if isinstance(data, dict):
                    print("top_level_keys:", sorted(list(data.keys()))[:20])
            except Exception:
                pass
        except Exception as exc:
            print("ERROR:", type(exc).__name__, str(exc))


if __name__ == "__main__":
    main()
