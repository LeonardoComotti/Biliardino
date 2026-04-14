import copy
import psycopg2
import streamlit as st
from datetime import datetime


# =========================
# CONNESSIONE
# =========================
def connect_db():
    return psycopg2.connect(st.secrets["db_url"])

def get_all_players_full_stats():
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT 
        p.nome,
        p.cognome,
        p.soprannome,
        p.data_nascita,

        COALESCE(COUNT(ps.id), 0) as tornei,
        COALESCE(SUM(ps.vittorie), 0),
        COALESCE(SUM(ps.pareggi), 0),
        COALESCE(SUM(ps.sconfitte), 0)

    FROM players p
    LEFT JOIN player_stats ps 
        ON p.soprannome = ps.soprannome

    GROUP BY p.nome, p.cognome, p.soprannome, p.data_nascita
    ORDER BY p.soprannome
    """)

    res = cur.fetchall()
    conn.close()

    return res
    
@st.cache_data
def cached_all_players_full():
    return get_all_players_full_stats()
    
# =========================
# INIT TABELLE
# =========================
def create_tables():
    conn = connect_db()
    conn.autocommit = True
    cursor = conn.cursor()

    # PLAYERS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS players (
        id SERIAL PRIMARY KEY,
        nome TEXT NOT NULL,
        cognome TEXT NOT NULL,
        soprannome TEXT UNIQUE NOT NULL,
        data_nascita TEXT,
        descrizione TEXT DEFAULT ''
    )
    """)

    # TOURNAMENTS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tournaments (
        id SERIAL PRIMARY KEY,
        nome TEXT DEFAULT '',
        data TEXT,
        n_giocatori INTEGER
    )
    """)


    # MATCHES
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS matches (
        id SERIAL PRIMARY KEY,
        tournament_id INTEGER,
        player1 TEXT,
        player2 TEXT,
        player3 TEXT,
        player4 TEXT,
        score1 INTEGER,
        score2 INTEGER
    )
    """)

    # STATS
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS player_stats (
        id SERIAL PRIMARY KEY,
        tournament_id INTEGER,
        soprannome TEXT,
        punti INTEGER,
        partite INTEGER,
        vittorie INTEGER,
        pareggi INTEGER,
        sconfitte INTEGER,
        gf INTEGER,
        gs INTEGER,
        cf INTEGER,
        cs INTEGER
    )
    """)

    conn.commit()
    conn.close()


# =========================================================
# PLAYERS CRUD (COMPATIBILE COL TUO MAIN)
# =========================================================
def add_player(nome, cognome, soprannome, data_nascita, descrizione=""):
    conn = connect_db()
    cur = conn.cursor()

    try:
        cur.execute("""
        INSERT INTO players (nome, cognome, soprannome, data_nascita, descrizione)
        VALUES (%s, %s, %s, %s, %s)
        """, (nome, cognome, soprannome, data_nascita, descrizione))
        conn.commit()
    except Exception:
        print("❌ Soprannome già esistente")

    conn.close()


def get_players():
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("SELECT soprannome FROM players")
    res = [r[0] for r in cur.fetchall()]

    conn.close()
    return res


def get_player_info(soprannome):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT nome, cognome, soprannome, data_nascita, descrizione
    FROM players
    WHERE soprannome=%s
    """, (soprannome,))

    res = cur.fetchone()
    conn.close()
    return res


def delete_player(soprannome):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM players WHERE soprannome=%s", (soprannome,))
    conn.commit()
    conn.close()


def update_player(old_nick, nome, cognome, new_nick, data_nascita, descrizione=""):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
    UPDATE players
    SET nome=%s, cognome=%s, soprannome=%s, data_nascita=%s, descrizione=%s
    WHERE soprannome=%s
    """, (nome, cognome, new_nick, data_nascita, descrizione, old_nick))

    conn.commit()
    conn.close()


# =========================================================
# TOURNAMENT SAVE (USATO DAL MAIN)
# =========================================================
def save_tournament(players, schedule, results, standings, nome=""):

    conn = connect_db()
    cur = conn.cursor()

    data = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur.execute("""
    INSERT INTO tournaments (nome, data, n_giocatori)
    VALUES (%s, %s, %s)
    RETURNING id
    """, (nome, data, len(players)))

    tournament_id = cur.fetchone()[0]

    # MATCHES
    for i, match in enumerate(schedule):
        t1, t2 = match
        s1, s2 = results[i]

        cur.execute("""
        INSERT INTO matches (
            tournament_id,
            player1, player2, player3, player4,
            score1, score2
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (
            tournament_id,
            t1[0], t1[1], t2[0], t2[1],
            s1, s2
        ))

    # STATS
    for p, s in standings.items():
        cur.execute("""
        INSERT INTO player_stats (
            tournament_id, soprannome,
            punti, partite, vittorie, pareggi, sconfitte,
            gf, gs, cf, cs
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            tournament_id, p,
            s["pt"], s["p"], s["v"], s["n"], s["s"],
            s["gf"], s["gs"], s["cf"], s["cs"]
        ))

    conn.commit()
    conn.close()

    print(f"💾 Torneo salvato ID {tournament_id}")
    return tournament_id


def delete_tournament(tournament_id):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("DELETE FROM matches WHERE tournament_id=%s", (tournament_id,))
    cur.execute("DELETE FROM player_stats WHERE tournament_id=%s", (tournament_id,))
    cur.execute("DELETE FROM tournaments WHERE id=%s", (tournament_id,))

    conn.commit()
    conn.close()


# =========================================================
# QUERY TORNEI
# =========================================================
def list_tournaments():
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("SELECT id, nome, data, n_giocatori FROM tournaments ORDER BY id DESC")
    res = cur.fetchall()

    conn.close()
    return res


def get_tournament_stats(tournament_id):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT soprannome, punti, partite, vittorie, pareggi, sconfitte,
           gf, gs, cf, cs
    FROM player_stats
    WHERE tournament_id=%s
    ORDER BY punti DESC
    """, (tournament_id,))

    res = cur.fetchall()
    conn.close()
    return res

@st.cache_data(ttl=300)
def get_player_overall_stats(soprannome):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT 
        COUNT(*) as tornei_giocati,
        SUM(punti),
        SUM(partite),
        SUM(vittorie),
        SUM(pareggi),
        SUM(sconfitte),
        SUM(gf),
        SUM(gs),
        SUM(cf),
        SUM(cs),
        AVG(punti),
        AVG(partite),
        AVG(vittorie)
    FROM player_stats
    WHERE soprannome=%s
    """, (soprannome,))

    res = cur.fetchone()
    conn.close()
    return res


def get_player_stats(soprannome):
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT tournament_id, punti, partite, vittorie, pareggi, sconfitte,
           gf, gs, cf, cs
    FROM player_stats
    WHERE soprannome=%s
    ORDER BY tournament_id
    """, (soprannome,))

    res = cur.fetchall()
    conn.close()
    return res


def get_tournament_matches(tournament_id):
    """Get all matches for a tournament in order"""
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT player1, player2, player3, player4, score1, score2
    FROM matches
    WHERE tournament_id=%s
    ORDER BY id
    """, (tournament_id,))

    res = cur.fetchall()
    conn.close()
    return res




def get_tournament_progressive_standings(tournament_id):
    """Calculate progressive standings after each match"""
    matches = get_tournament_matches(tournament_id)

    if not matches:
        return {}

    all_players = set()
    for match in matches:
        all_players.update(match[:4])

    progressive_standings = {}

    current_standings = {
        player: {
            "pt": 0, "p": 0, "v": 0, "n": 0, "s": 0,
            "gf": 0, "gs": 0, "cf": 0, "cs": 0
        }
        for player in all_players
    }

    for match_idx, match in enumerate(matches):
        player1, player2, player3, player4, score1, score2 = match

        team1 = (player1, player2)
        team2 = (player3, player4)

        # games played + goals
        for p in team1 + team2:
            current_standings[p]["p"] += 1
            if p in team1:
                current_standings[p]["gf"] += score1
                current_standings[p]["gs"] += score2
            else:
                current_standings[p]["gf"] += score2
                current_standings[p]["gs"] += score1

        # results
        if score1 == 4 and score2 == 4:
            for p in team1 + team2:
                current_standings[p]["pt"] += 1
                current_standings[p]["n"] += 1

        elif score1 == 5 and score2 == 0:
            for p in team1:
                current_standings[p]["pt"] += 4
                current_standings[p]["v"] += 1
                current_standings[p]["cf"] += 1
            for p in team2:
                current_standings[p]["pt"] -= 1
                current_standings[p]["s"] += 1
                current_standings[p]["cs"] += 1

        elif score2 == 5 and score1 == 0:
            for p in team2:
                current_standings[p]["pt"] += 4
                current_standings[p]["v"] += 1
                current_standings[p]["cf"] += 1
            for p in team1:
                current_standings[p]["pt"] -= 1
                current_standings[p]["s"] += 1
                current_standings[p]["cs"] += 1

        elif score1 == 5:
            for p in team1:
                current_standings[p]["pt"] += 3
                current_standings[p]["v"] += 1
            for p in team2:
                current_standings[p]["s"] += 1

        elif score2 == 5:
            for p in team2:
                current_standings[p]["pt"] += 3
                current_standings[p]["v"] += 1
            for p in team1:
                current_standings[p]["s"] += 1

        progressive_standings[match_idx + 1] = copy.deepcopy(current_standings)

    return progressive_standings
    
def get_all_players_stats():
    conn = connect_db()
    cur = conn.cursor()

    cur.execute("""
    SELECT 
        soprannome,
        COUNT(*) as tornei,
        SUM(punti),
        SUM(partite),
        SUM(vittorie),
        SUM(pareggi),
        SUM(sconfitte),
        SUM(gf),
        SUM(gs),
        SUM(cf),
        SUM(cs)
    FROM player_stats
    GROUP BY soprannome
    """)

    res = cur.fetchall()
    conn.close()
    return res

@st.cache_data(ttl=300)
def get_player_ranking_stats(soprannome):
    """Returns count of 1st, 2nd, 3rd place finishes for a player"""
    conn = connect_db()
    cur = conn.cursor()

    # Get all tournaments the player participated in
    cur.execute("""
    SELECT ps.tournament_id, ps.punti
    FROM player_stats ps
    WHERE ps.soprannome = %s
    """, (soprannome,))

    player_tournaments = cur.fetchall()

    first_place = 0
    second_place = 0
    third_place = 0

    for tournament_id, player_points in player_tournaments:
        # Get all players' points for this tournament
        cur.execute("""
        SELECT soprannome, punti
        FROM player_stats
        WHERE tournament_id = %s
        ORDER BY punti DESC
        """, (tournament_id,))

        tournament_results = cur.fetchall()

        # Find player's position
        for position, (player_name, points) in enumerate(tournament_results, 1):
            if player_name == soprannome:
                if position == 1:
                    first_place += 1
                elif position == 2:
                    second_place += 1
                elif position == 3:
                    third_place += 1
                break

    conn.close()
    return first_place, second_place, third_place


# =========================================================
# MAIN
# =========================================================
if __name__ == "__main__":
    create_tables()
    
