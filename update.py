from welo import WElo
from api import get_recent_matches

w = WElo()

matches = get_recent_matches(tour="ATP", limit=200)

for m in matches:
    winner = m["winner"]
    loser = m["loser"]

    gw_winner = m["winner_games"]
    gw_loser = m["loser_games"]

    surface = m["surface"]

    w.update(winner, loser, gw_winner, gw_loser, surface)

# Test predikcie
print("Nadal vs Djokovic (Grass):", w.predict("Nadal", "Djokovic", "Grass"))
print("Ruud vs Alcaraz (Clay):", w.predict("Ruud", "Alcaraz", "Clay"))
