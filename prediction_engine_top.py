def build_prediction_record(
    match,
    surface,
    elo_prediction,
    odds_data,
    form_store,
    mcp_stats,
):
    player1 = match["player1"]
    player2 = match["player2"]

    prob1 = elo_prediction["probability_player1"]
    prob2 = elo_prediction["probability_player2"]

    odds1 = safe_float(
        odds_data.get("odds_player1")
    )

    odds2 = safe_float(
        odds_data.get("odds_player2")
    )

    form1 = get_player_form(
        form_store,
        player1,
        surface,
    )

    form2 = get_player_form(
        form_store,
        player2,
        surface,
    )

    if prob1 >= prob2:

        pick = player1
        opponent = player2

        base_probability = prob1
        odds = odds1

    else:

        pick = player2
        opponent = player1

        base_probability = prob2
        odds = odds2

    form_adjustment = calculate_form_adjustment(
        pick_form=form1,
        opponent_form=form2,
    )

    final_probability = (
        base_probability +
        form_adjustment["total_adjustment"]
    )

    # MCP boost

    final_probability += mcp_adjustment(
        pick,
        mcp_stats,
    )

    final_probability -= mcp_adjustment(
        opponent,
        mcp_stats,
    )

    final_probability = clamp(
        final_probability,
        0.15,
        0.85,
    )

    #
    # TBT Elo / TBT yElo
    #

    tbt = tbt_predict(
        player1,
        player2,
        surface=surface,
    )

    if pick == player1:

        tbt_elo_probability = (
            tbt["elo_probability"]
        )

        tbt_yelo_probability = (
            tbt["yelo_probability"]
        )

    else:

        tbt_elo_probability = (
            1 - tbt["elo_probability"]
        )

        tbt_yelo_probability = (
            1 - tbt["yelo_probability"]
        )

    consensus = calculate_consensus(
        tbt_ai=final_probability,
        tbt_elo=tbt_elo_probability,
        tbt_yelo=tbt_yelo_probability,
    )

    return {
        "match": f"{player1} vs {player2}",

        "pick": pick,
        "opponent": opponent,

        "probability": round(
            final_probability,
            3,
        ),

        "odds": odds,

        "time": match.get("time"),

        #
        # TBT v2
        #

        "tbt_ai": round(
            final_probability,
            3,
        ),

        "tbt_elo": round(
            tbt_elo_probability,
            3,
        ),

        "tbt_yelo": round(
            tbt_yelo_probability,
            3,
        ),

        "consensus": consensus["label"],

        "consensus_score": consensus["score"],

        "consensus_spread": consensus["spread"],
    }
