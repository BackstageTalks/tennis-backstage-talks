def safe_float(value):
    try:
        if value is None:
            return None

        if value == "":
            return None

        return float(value)

    except Exception:
        return None


def round_percent(value):
    if value is None:
        return None

    return round(value, 1)


def no_data_result(status="NO_DATA", reason=None):
    return {
        "corq_ai_probability": None,
        "bst_ai_probability": None,
        "ai_match": None,
        "ai_gap": None,
        "ai_signed_gap": None,
        "ai_lean": None,
        "ai_direction_match": None,
        "ai_match_color": "gray",
        "bst_ai_status": status,
        "bst_ai_reason": reason or status,
    }


def build_ai_match_result(corq_probability, bst_probability):
    corq_probability = safe_float(corq_probability)
    bst_probability = safe_float(bst_probability)

    if corq_probability is None:
        return no_data_result(
            status="NO_DATA",
            reason="Missing Corq AI probability.",
        )

    if bst_probability is None:
        return no_data_result(
            status="NO_DATA",
            reason="Missing BsT AI probability.",
        )

    corq_pct = corq_probability * 100.0
    bst_pct = bst_probability * 100.0

    signed_gap = corq_pct - bst_pct
    gap = abs(signed_gap)
    ai_match = 100.0 - gap

    if ai_match < 0:
        ai_match = 0.0

    corq_side = corq_probability >= 0.5
    bst_side = bst_probability >= 0.5

    direction_match = corq_side == bst_side

    if signed_gap > 0:
        ai_lean = "CORQ"

    elif signed_gap < 0:
        ai_lean = "BST"

    else:
        ai_lean = "TIE"

    if not direction_match:
        color = "red"

    elif signed_gap >= 0:
        color = "green"

    else:
        color = "orange"

    return {
        "corq_ai_probability": round(corq_probability, 3),
        "bst_ai_probability": round(bst_probability, 3),
        "ai_match": round_percent(ai_match),
        "ai_gap": round_percent(gap),
        "ai_signed_gap": round_percent(signed_gap),
        "ai_lean": ai_lean,
        "ai_direction_match": direction_match,
        "ai_match_color": color,
        "bst_ai_status": "OK",
        "bst_ai_reason": "OK",
    }
