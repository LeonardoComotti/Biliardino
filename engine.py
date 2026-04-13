import random
from database import get_players
from collections import defaultdict


# =========================
# CONFIG
# =========================
TENTATIVI = 200

# =========================
# SELEZIONE GIOCATORI
# =========================
def select_players_from_db(n_players):
    all_players = get_players()

    if len(all_players) < n_players:
        print("❌ Non ci sono abbastanza giocatori nel database")
        return None

    while True:
        print("\nGIOCATORI DISPONIBILI:")
        for i, p in enumerate(all_players):
            print(f"{i}: {p}")

        selected = []

        while len(selected) < n_players:
            try:
                idx = int(input(f"Seleziona giocatore {len(selected)+1}: "))

                if idx < 0 or idx >= len(all_players):
                    print("❌ Indice non valido")
                    continue

                player = all_players[idx]

                if player in selected:
                    print("❌ Già selezionato")
                    continue

                selected.append(player)

            except ValueError:
                print("❌ Inserisci un numero")

        print("\nSelezione:")
        for p in selected:
            print("-", p)

        if input("Confermi? (y/n): ").lower() == "y":
            return selected
        
# =========================
# K EQUILIBRATO
# =========================
def suggest_matches_per_player(n_players, min_matches_per_player):
    k = min_matches_per_player
    while (n_players * k) % 4 != 0:
        k += 1
    return k


# =========================
# VALIDAZIONE RISULTATO
# =========================
def valid_score(s1, s2):
    if s1 == 4 and s2 == 4:
        return True
    if (s1 == 5 and s2 <= 3) or (s2 == 5 and s1 <= 3):
        return True
    return False


# =========================
# VALUTAZIONE GRUPPO
# =========================
def evaluate_group(group, games_played, teammates, opponents):

    pairings = [
        ((group[0], group[1]), (group[2], group[3])),
        ((group[0], group[2]), (group[1], group[3])),
        ((group[0], group[3]), (group[1], group[2]))
    ]

    best_match = None
    best_score = float("inf")

    for team1, team2 in pairings:

        score = 0

        # coesione squadra
        score += teammates[tuple(sorted(team1))] * 50
        score += teammates[tuple(sorted(team2))] * 50

        # rivalità
        for p1 in team1:
            for p2 in team2:
                score += opponents[tuple(sorted((p1, p2)))] * 10

        # bilanciamento partite
        for p in group:
            score += games_played[p]

        # bonus nuove coppie
        if teammates[tuple(sorted(team1))] == 0:
            score -= 20
        if teammates[tuple(sorted(team2))] == 0:
            score -= 20

        if score < best_score:
            best_score = score
            best_match = (team1, team2)

    return best_match, best_score


# =========================
# GENERATORE TORNEO
# =========================
def generate_schedule(players, matches_per_player):

    games_played = {p: 0 for p in players}
    teammates = defaultdict(int)
    opponents = defaultdict(int)

    matches = []

    total_matches = (len(players) * matches_per_player) // 4

    while len(matches) < total_matches:

        available = [p for p in players if games_played[p] < matches_per_player]

        if len(available) < 4:
            break

        players_sorted = sorted(available, key=lambda x: games_played[x])

        best_match = None
        best_score = float("inf")

        for _ in range(TENTATIVI):

            pool = players_sorted[:min(8, len(players_sorted))]
            group = random.sample(pool, 4)

            match, score = evaluate_group(group, games_played, teammates, opponents)

            if score < best_score:
                best_score = score
                best_match = match

        if best_match is None:
            break

        team1, team2 = best_match

        # update presenze
        for p in team1 + team2:
            games_played[p] += 1

        # update relazioni
        teammates[tuple(sorted(team1))] += 1
        teammates[tuple(sorted(team2))] += 1

        for p1 in team1:
            for p2 in team2:
                opponents[tuple(sorted((p1, p2)))] += 1

        matches.append(best_match)

    return matches, games_played, teammates, opponents


# =========================
# MATRICE RELAZIONI (DATA)
# =========================
def build_relationship_matrix(players, teammates, opponents):

    matrix = {
        p: {q: {"teammates": 0, "opponents": 0} for q in players}
        for p in players
    }

    for i in players:
        for j in players:
            if i == j:
                continue

            pair = tuple(sorted((i, j)))
            matrix[i][j]["teammates"] = teammates.get(pair, 0)
            matrix[i][j]["opponents"] = opponents.get(pair, 0)

    return matrix


# =========================
# CALCOLO STANDINGS
# =========================
def update_standings(match, s1, s2, standings):
    team1, team2 = match

    for p in team1:
        standings[p]["p"] += 1
        standings[p]["gf"] += s1
        standings[p]["gs"] += s2

    for p in team2:
        standings[p]["p"] += 1
        standings[p]["gf"] += s2
        standings[p]["gs"] += s1

    # pareggio
    if s1 == 4 and s2 == 4:
        for p in team1 + team2:
            standings[p]["pt"] += 1
            standings[p]["n"] += 1
        return

    # cappotti
    if s1 == 5 and s2 == 0:
        for p in team1:
            standings[p]["pt"] += 4
            standings[p]["v"] += 1
            standings[p]["cf"] += 1
        for p in team2:
            standings[p]["pt"] -= 1
            standings[p]["s"] += 1
            standings[p]["cs"] += 1
        return

    if s2 == 5 and s1 == 0:
        for p in team2:
            standings[p]["pt"] += 4
            standings[p]["v"] += 1
            standings[p]["cf"] += 1
        for p in team1:
            standings[p]["pt"] -= 1
            standings[p]["s"] += 1
            standings[p]["cs"] += 1
        return

    # vittoria normale
    if s1 == 5:
        for p in team1:
            standings[p]["pt"] += 3
            standings[p]["v"] += 1
        for p in team2:
            standings[p]["s"] += 1

    elif s2 == 5:
        for p in team2:
            standings[p]["pt"] += 3
            standings[p]["v"] += 1
        for p in team1:
            standings[p]["s"] += 1

def compute_standings(schedule, results):
    standings = {}

    # inizializza
    players = set()
    for t1, t2 in schedule:
        players.update(t1)
        players.update(t2)

    for p in players:
        standings[p] = {
            "pt": 0, "p": 0, "v": 0, "n": 0, "s": 0,
            "gf": 0, "gs": 0, "cf": 0, "cs": 0
        }

    # calcolo
    for (t1, t2), (s1, s2) in zip(schedule, results):

        for p in t1:
            standings[p]["p"] += 1
            standings[p]["gf"] += s1
            standings[p]["gs"] += s2

        for p in t2:
            standings[p]["p"] += 1
            standings[p]["gf"] += s2
            standings[p]["gs"] += s1

        if s1 == 4 and s2 == 4:
            for p in t1 + t2:
                standings[p]["pt"] += 1
                standings[p]["n"] += 1

        elif s1 == 5 and s2 == 0:
            for p in t1:
                standings[p]["pt"] += 4
                standings[p]["v"] += 1
                standings[p]["cf"] += 1
            for p in t2:
                standings[p]["pt"] -= 1
                standings[p]["s"] += 1
                standings[p]["cs"] += 1

        elif s2 == 5 and s1 == 0:
            for p in t2:
                standings[p]["pt"] += 4
                standings[p]["v"] += 1
                standings[p]["cf"] += 1
            for p in t1:
                standings[p]["pt"] -= 1
                standings[p]["s"] += 1
                standings[p]["cs"] += 1

        elif s1 == 5:
            for p in t1:
                standings[p]["pt"] += 3
                standings[p]["v"] += 1
            for p in t2:
                standings[p]["s"] += 1

        else:
            for p in t2:
                standings[p]["pt"] += 3
                standings[p]["v"] += 1
            for p in t1:
                standings[p]["s"] += 1

    return standings

# =========================
# CLASSIFICA
# =========================
def print_standings(st):
    print("\nCLASSIFICA:\n")

    sorted_players = sorted(st.items(), key=lambda x: x[1]["pt"], reverse=True)

    print("Giocatore | Pt | P | V | N | S | GF | GS | CF | CS")

    for p, s in sorted_players:
        print(
            f"{p:10} {s['pt']:3} {s['p']:2} {s['v']:2} {s['n']:2} {s['s']:2} "
            f"{s['gf']:3} {s['gs']:3} {s['cf']:3} {s['cs']:3}"
        )

# =========================
# INIT STANDINGS
# =========================
def init_standings(players):
    return {
        p: {
            "pt": 0,
            "p": 0,
            "v": 0,
            "n": 0,
            "s": 0,
            "gf": 0,
            "gs": 0,
            "cf": 0,
            "cs": 0
        }
        for p in players
    }


# =========================
# PROCESS FULL TOURNAMENT
# =========================
def run_tournament(players, matches_per_player):
    schedule, _, teammates, opponents = generate_schedule(players, matches_per_player)
    standings = init_standings(players)

    return schedule, teammates, opponents, standings