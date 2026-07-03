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
