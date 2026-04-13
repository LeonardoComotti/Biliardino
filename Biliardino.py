import random
from database import (
    get_players,
    create_tables,
    save_tournament
)
from collections import defaultdict


TENTATIVI = 200


# =========================
# INIT DB
# =========================
create_tables()


# =========================
# TROVA K EQUILIBRATO
# =========================
def suggest_matches_per_player(n_players, min_matches_per_player):
    k = min_matches_per_player
    while (n_players * k) % 4 != 0:
        k += 1
    return k


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

        score += teammates[tuple(sorted(team1))] * 50
        score += teammates[tuple(sorted(team2))] * 50

        for p1 in team1:
            for p2 in team2:
                score += opponents[tuple(sorted((p1, p2)))] * 10

        for p in group:
            score += games_played[p]

        if teammates[tuple(sorted(team1))] == 0:
            score -= 20
        if teammates[tuple(sorted(team2))] == 0:
            score -= 20

        if score < best_score:
            best_score = score
            best_match = (team1, team2)

    return best_match


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

            match = evaluate_group(group, games_played, teammates, opponents)

            score = sum(games_played[p] for p in group)

            if score < best_score:
                best_score = score
                best_match = match

        if best_match is None:
            break

        team1, team2 = best_match

        for p in team1 + team2:
            games_played[p] += 1

        teammates[tuple(sorted(team1))] += 1
        teammates[tuple(sorted(team2))] += 1

        for p1 in team1:
            for p2 in team2:
                opponents[tuple(sorted((p1, p2)))] += 1

        matches.append(best_match)

    return matches, games_played, teammates, opponents


# =========================
# MATRICE
# =========================
def print_matrix(players, teammates, opponents):

    print("\nMATRICE RELAZIONI:\n")

    max_len = max(len(p) for p in players) + 2

    header = " " * max_len
    for p in players:
        header += p.ljust(max_len)
    print(header)

    for i in players:
        row = i.ljust(max_len)

        for j in players:
            if i == j:
                row += "-".ljust(max_len)
            else:
                pair = tuple(sorted((i, j)))
                row += f"{teammates[pair]}/{opponents[pair]}".ljust(max_len)

        print(row)


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
# MAIN
# =========================
n_players = int(input("Numero giocatori: "))

players = select_players_from_db(n_players)

if players is None:
    exit()

min_matches = int(input("Partite minime per giocatore: "))

k = suggest_matches_per_player(n_players, min_matches)

print(f"\nServe k = {k}")

if k != min_matches:
    if input("Usare k ottimale? (y/n): ") == "y":
        min_matches = k


# =========================
# GENERAZIONE
# =========================
schedule, _, teammates, opponents = generate_schedule(players, min_matches)

print("\nCALENDARIO:\n")
for i, m in enumerate(schedule, 1):
    t1, t2 = m
    print(f"{i}: {t1[0]} + {t1[1]} vs {t2[0]} + {t2[1]}")


print_matrix(players, teammates, opponents)


# =========================
# STANDINGS INIT
# =========================
standings = {
    p: {"pt": 0, "p": 0, "v": 0, "n": 0, "s": 0,
        "gf": 0, "gs": 0, "cf": 0, "cs": 0}
    for p in players
}

results = []

print("\nINSERIMENTO RISULTATI:\n")

for i, match in enumerate(schedule, 1):
    t1, t2 = match

    print(f"\nMatch {i}: {t1[0]} + {t1[1]} vs {t2[0]} + {t2[1]}")

    while True:
        s1 = int(input("Gol squadra 1: "))
        s2 = int(input("Gol squadra 2: "))

        if valid_score(s1, s2):
            break
        print("❌ Risultato non valido")

    results.append((s1, s2))

    # update stats
    for p in t1:
        standings[p]["p"] += 1
        standings[p]["gf"] += s1
        standings[p]["gs"] += s2

    for p in t2:
        standings[p]["p"] += 1
        standings[p]["gf"] += s2
        standings[p]["gs"] += s1

    if s1 == 4 and s2 == 4:
        for p in players:
            if p in t1 + t2:
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


# =========================
# OUTPUT
# =========================
print_standings(standings)


# =========================
# SALVATAGGIO TORNEO
# =========================
if input("\nSalvare torneo? (y/n): ").lower() == "y":
    save_tournament(players, schedule, results, standings)
    print("💾 Torneo salvato")
else:
    print("❌ Torneo non salvato")