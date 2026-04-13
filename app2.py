import streamlit as st
from datetime import datetime
from datetime import date
import matplotlib.pyplot as plt
from engine import (
    suggest_matches_per_player,
    generate_schedule,
    valid_score,
    compute_standings
)
from database import (
    create_tables, save_tournament, get_players, 
    add_player, get_player_info, delete_player, update_player,
    list_tournaments, get_tournament_stats, get_player_overall_stats, get_player_stats,
    get_player_ranking_stats, get_tournament_progressive_standings, delete_tournament
)

# ======================
# INIT
# =========================
create_tables()

st.set_page_config(page_title="Biliardino", layout="wide")

st.title("⚽ Biliardino Manager")

# =========================
# SIDEBAR NAVIGATION
# =========================
with st.sidebar:
    st.header("📋 Menu")
    page = st.radio(
        "Seleziona sezione:",
        ["🏆 Torneo", "👥 Gestisci Giocatori", "📊 Storico Tornei"],
        label_visibility="collapsed"
    )

# =========================
# SESSION STATE INIT
# =========================
if "players" not in st.session_state:
    st.session_state.players = []

if "schedule" not in st.session_state:
    st.session_state.schedule = []

if "results" not in st.session_state:
    st.session_state.results = []

if "standings" not in st.session_state:
    st.session_state.standings = None

if "step" not in st.session_state:
    st.session_state.step = 1

if "match_results" not in st.session_state:
    st.session_state.match_results = []

# =========================
# PAGE: TORNEO
# =========================
if page == "🏆 Torneo":
    
    # STEP 1 - SELEZIONE GIOCATORI
    if st.session_state.step == 1:
        st.subheader("1️⃣ Selezione giocatori")

        # Get all available players from database
        all_players = get_players()

        if not all_players:
            st.error("❌ Nessun giocatore nel database. Aggiungi giocatori prima di iniziare.")
        else:
            n_players = st.number_input("Numero giocatori", min_value=4, max_value=len(all_players), step=1)
            min_matches = st.number_input("Partite minime per giocatore", min_value=1, step=1)

            selected_players = st.multiselect(
                "Seleziona i giocatori",
                options=all_players,
                max_selections=n_players,
                help=f"Seleziona esattamente {int(n_players)} giocatori"
            )

            if len(selected_players) == int(n_players) and st.button("➡️ Avanti"):
                st.session_state.players = selected_players
                
                k = suggest_matches_per_player(len(selected_players), int(min_matches))
                st.session_state.k_matches = k
                
                st.info(f"✅ Giocatori selezionati: {', '.join(selected_players)}")
                st.info(f"📊 Numero partite per giocatore: {k}")
                
                st.session_state.schedule, _, _, _ = generate_schedule(selected_players, k)
                st.session_state.step = 2
                st.session_state.match_results = [None] * len(st.session_state.schedule)
                st.rerun()
            elif len(selected_players) < int(n_players):
                st.warning(f"⏳ Seleziona ancora {int(n_players) - len(selected_players)} giocatori")

    # STEP 2 - CALENDARIO + RISULTATI + CLASSIFICA LIVE
    if st.session_state.step == 2:
        st.subheader("2️⃣ Inserimento risultati")
        
        st.write(f"**Totale partite:** {len(st.session_state.schedule)}")

        schedule = st.session_state.schedule

        col_input, col_standings = st.columns([1, 1])

        # Input results in left column
        with col_input:
            st.markdown("### 📝 Risultati")
            
            all_valid = True
            
            for i, match in enumerate(schedule):
                t1, t2 = match

                st.markdown(f"**Partita {i+1}**")
                st.text(f"{t1[0]} + {t1[1]} vs {t2[0]} + {t2[1]}")

                c1, c2 = st.columns(2)

                s1 = c1.number_input(
                    f"Gol",
                    min_value=0,
                    max_value=5,
                    key=f"s1_{i}",
                    label_visibility="collapsed"
                )

                s2 = c2.number_input(
                    f"Gol",
                    min_value=0,
                    max_value=5,
                    key=f"s2_{i}",
                    label_visibility="collapsed"
                )

                is_valid = valid_score(s1, s2)
                
                if is_valid:
                    st.session_state.match_results[i] = (s1, s2)
                    st.caption("✅ Valido")
                else:
                    st.session_state.match_results[i] = None
                    st.caption("❌ Non valido")
                    all_valid = False

                st.divider()

        # Display live standings in right column
        with col_standings:
            st.markdown("### 🏆 Classifica Live")
            
            valid_results = [r for r in st.session_state.match_results if r is not None]
            
            if len(valid_results) > 0:
                # Calculate standings from current valid results
                partial_standings = compute_standings(
                    schedule[:len(valid_results)],
                    valid_results
                )
                
                sorted_players = sorted(
                    partial_standings.items(),
                    key=lambda x: x[1]["pt"],
                    reverse=True
                )

                st.dataframe(
                    [
                        {
                            "Giocatore": p,
                            "Pt": s["pt"],
                            "P": s["p"],
                            "V": s["v"],
                            "N": s["n"],
                            "S": s["s"],
                        }
                        for p, s in sorted_players
                    ],
                    width='stretch',
                    hide_index=True
                )
                st.caption(f"Aggiornata dopo {len(valid_results)} partite")
            else:
                st.info("Inserisci i risultati per vedere la classifica live...")

        st.session_state.results = [r for r in st.session_state.match_results if r is not None]

        col_btn1, col_btn2 = st.columns(2)
        
        with col_btn1:
            if all_valid and len(st.session_state.results) == len(schedule):
                if st.button("📊 Finalizza classifica", width='stretch'):
                    st.session_state.standings = compute_standings(
                        st.session_state.schedule,
                        st.session_state.results
                    )
                    st.session_state.step = 3
                    st.rerun()
        
        with col_btn2:
            if st.button("↩️ Indietro", width='stretch'):
                st.session_state.step = 1
                st.rerun()

        if not (all_valid and len(st.session_state.results) == len(schedule)):
            st.warning(f"⏳ Inserisci tutti i risultati in modo valido ({len(st.session_state.results)}/{len(schedule)})")

    # STEP 3 - CLASSIFICA FINALE
    if st.session_state.step == 3:
        st.subheader("3️⃣ Classifica finale")

        standings = st.session_state.standings

        if standings:
            sorted_players = sorted(
                standings.items(),
                key=lambda x: x[1]["pt"],
                reverse=True
            )

            # Display standings as table
            st.dataframe(
                [
                    {
                        "🏆 Giocatore": p,
                        "Pt": s["pt"],
                        "P": s["p"],
                        "V": s["v"],
                        "N": s["n"],
                        "S": s["s"],
                        "GF": s["gf"],
                        "GS": s["gs"],
                        "CF": s["cf"],
                        "CS": s["cs"],
                    }
                    for p, s in sorted_players
                ],
                width='stretch',
                hide_index=True
            )

            # Buttons for actions
            col1, col2, col3 = st.columns(3)

            with col1:
                nome_torneo = st.text_input("Nome torneo", key="nome_torneo")

                if st.button("💾 Salva torneo", width='stretch'):
                    if not nome_torneo:
                        st.error("❌ Inserisci un nome per il torneo")
                    else:
                        tid = save_tournament(
                            st.session_state.players,
                            st.session_state.schedule,
                            st.session_state.results,
                            st.session_state.standings,
                            nome=nome_torneo
                        )
                        st.success(f"✅ Torneo '{nome_torneo}' salvato con ID: {tid}")
            
            with col2:
                if st.button("📝 Modifica risultati", width='stretch'):
                    st.session_state.step = 2
                    st.rerun()

            with col3:
                if st.button("🔄 Nuovo torneo", width='stretch'):
                    st.session_state.clear()
                    st.rerun()


# =========================
# PAGE: DATABASE MANAGEMENT
# =========================
if page == "👥 Gestisci Giocatori":
    st.subheader("👥 Gestione Giocatori")
    
    tab1, tab2, tab3, tab4 = st.tabs(["➕ Aggiungi", "📋 Visualizza", "✏️ Modifica", "❌ Elimina"])
    
    # TAB 1 - ADD PLAYER
    with tab1:
        st.markdown("### Aggiungi nuovo giocatore")
        
        col_nome, col_cognome = st.columns(2)
        with col_nome:
            nome = st.text_input("Nome", key="add_nome")
        with col_cognome:
            cognome = st.text_input("Cognome", key="add_cognome")
        
        col_soprannome, col_data = st.columns(2)
        with col_soprannome:
            soprannome = st.text_input("Soprannome (univoco)", key="add_soprannome")
        with col_data:
            data_nascita = st.date_input("Data di nascita", key="add_data")
        
        descrizione = st.text_area("Descrizione", placeholder="Inserisci una descrizione per il giocatore", key="add_descrizione")
        
        if st.button("✅ Aggiungi giocatore", type="primary", width='stretch'):
            if nome and cognome and soprannome:
                try:
                    add_player(nome, cognome, soprannome, str(data_nascita), descrizione)
                    st.success(f"✅ Giocatore '{soprannome}' aggiunto con successo!")
                except Exception as e:
                    st.error(f"❌ Errore: {e}")
            else:
                st.error("❌ Compila tutti i campi obbligatori")
    
    # TAB 2 - VIEW PLAYERS
    with tab2:
        st.markdown("### Elenco giocatori")
        all_players = get_players()
        
        if all_players:
            # Player selector for detailed view
            if "player_detail_select" not in st.session_state:
                st.session_state.player_detail_select = ""

            selected_player = st.selectbox(
                "Seleziona giocatore per dettagli:",
                [""] + all_players,
                key="player_detail_select"
)
            
            # Main players table
            players_info = []
            for p in all_players:
                info = get_player_info(p)
                overall = get_player_overall_stats(p)
                ranking = get_player_ranking_stats(p)
                
                if info:
                    nome, cognome, soprannome, data_nascita, descrizione = info
                    
                    # Get overall stats if available
                    if overall and overall[0] > 0:
                        tornei, punti_tot, partite_tot, vittorie_tot, pareggi_tot, sconfitte_tot, gf_tot, gs_tot, cf_tot, cs_tot, _, _, _ = overall
                        first_place, second_place, third_place = ranking
                        players_info.append({
                            "Nome": nome,
                            "Cognome": cognome,
                            "Soprannome": soprannome,
                            "Data nascita": data_nascita or "N/A",
                            "🥇 1°": first_place,
                            "🥈 2°": second_place,
                            "🥉 3°": third_place,
                            "✅ Vittorie": vittorie_tot,
                            "🤝 Pareggi": pareggi_tot,
                            "❌ Sconfitte": sconfitte_tot,
                            "🎯 Tornei": tornei
                        })
                    else:
                        players_info.append({
                            "Nome": nome,
                            "Cognome": cognome,
                            "Soprannome": soprannome,
                            "Data nascita": data_nascita or "N/A",
                            "✅ Vittorie": 0,
                            "🤝 Pareggi": 0,
                            "❌ Sconfitte": 0,
                            "🎯 Tornei": 0,
                            "🥇 1°": 0,
                            "🥈 2°": 0,
                            "🥉 3°": 0
                        })
            
            if selected_player == "":
                st.dataframe(
                    players_info, 
                    width='stretch', 
                    hide_index=True,
                    column_config={
                        "🥇 1°": st.column_config.NumberColumn("🥇 1°", help="Primi posti"),
                        "🥈 2°": st.column_config.NumberColumn("🥈 2°", help="Secondi posti"),
                        "🥉 3°": st.column_config.NumberColumn("🥉 3°", help="Terzi posti"),
                        "✅ Vittorie": st.column_config.NumberColumn("✅ Vittorie", help="Vittorie totali"),
                        "🤝 Pareggi": st.column_config.NumberColumn("🤝 Pareggi", help="Pareggi totali"),
                        "❌ Sconfitte": st.column_config.NumberColumn("❌ Sconfitte", help="Sconfitte totali"),
                        "🎯 Tornei": st.column_config.NumberColumn("🎯 Tornei", help="Tornei giocati")
                    }
                )
                st.caption(f"Totale giocatori: {len(all_players)}")

            # Detailed player view
            if selected_player:
                def reset_player_selection():
                    if "player_detail_select" in st.session_state:
                        st.session_state.player_detail_select = ""

                st.button("◀ Torna all'elenco", width='stretch', key="back_to_list", on_click=reset_player_selection)  
                st.markdown("---")
                st.markdown(f"### 📊 Statistiche Dettagliate: **{selected_player}**")
                
                player_info = get_player_info(selected_player)
                overall_stats = get_player_overall_stats(selected_player)
                player_tournament_stats = get_player_stats(selected_player)
                ranking_stats = get_player_ranking_stats(selected_player)
                
                if player_info:
                    nome, cognome, _, data_nascita, descrizione = player_info
                    
                    st.markdown(f"**Nome completo:** {nome} {cognome}")
                    st.markdown(f"**Data di nascita:** {data_nascita or 'N/A'}")
                    if descrizione:
                        st.markdown(f"**Descrizione:** {descrizione}")
                    
                    # Statistics cards and ranking - moved after graphs
                    if overall_stats and overall_stats[0] > 0:
                        tornei, punti_tot, partite_tot, vittorie_tot, pareggi_tot, sconfitte_tot, gf_tot, gs_tot, cf_tot, cs_tot, punti_med, partite_med, vittorie_med = overall_stats
                        first_place, second_place, third_place = ranking_stats
                        
                        # Performance graphs - moved here under birth date and reduced size
                        st.markdown("#### 📈 Prestazioni Complessive")
                        
                        # Row 1: Goals and Cappotti
                        col1, col2 = st.columns(2)
                        
                        # Goals graph
                        with col1:
                            fig1, ax1 = plt.subplots(figsize=(2.8, 2), dpi=60)
                            categories_goals = ['Gol Fatti', 'Gol Subiti']
                            values_goals = [gf_tot, gs_tot]
                            colors_goals = ['#4CAF50', '#F44336']
                            bars = ax1.bar(categories_goals, values_goals, color=colors_goals, width=0.6)
                            ax1.set_title('Statistiche Gol', fontsize=10, fontweight='bold', pad=8)
                            ax1.set_ylabel('Totale', fontsize=9)
                            ax1.tick_params(axis='both', which='major', labelsize=8)
                            ax1.grid(True, alpha=0.3, axis='y')
                            
                            for bar in bars:
                                height = bar.get_height()
                                ax1.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                                         f'{int(height)}', ha='center', va='bottom', fontsize=8, fontweight='bold')
                            
                            # Add margin at top for labels
                            max_height = max(values_goals) if values_goals else 1
                            ax1.set_ylim(0, max_height * 1.15)
                            
                            st.pyplot(fig1)
                        
                        # Cappotti graph
                        with col2:
                            fig2, ax2 = plt.subplots(figsize=(2.8, 2), dpi=60)
                            categories_cappotti = ['Cappotti Fatti', 'Cappotti Subiti']
                            values_cappotti = [cf_tot, cs_tot]
                            colors_cappotti = ['#9C27B0', '#FF5722']
                            bars2 = ax2.bar(categories_cappotti, values_cappotti, color=colors_cappotti, width=0.6)
                            ax2.set_title('Statistiche Cappotti', fontsize=10, fontweight='bold', pad=8)
                            ax2.set_ylabel('Totale', fontsize=9)
                            ax2.tick_params(axis='both', which='major', labelsize=8)
                            ax2.grid(True, alpha=0.3, axis='y')
                            
                            for bar in bars2:
                                height = bar.get_height()
                                ax2.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                                         f'{int(height)}', ha='center', va='bottom', fontsize=8, fontweight='bold')
                            
                            # Add margin at top for labels
                            max_height = max(values_cappotti) if values_cappotti else 1
                            ax2.set_ylim(0, max_height * 1.15)
                            
                            st.pyplot(fig2)
                        
                        # Row 2: Results pie chart - wrap in column to constrain width
                        col_pie, col_empty = st.columns(2)
                        with col_pie:
                            fig3, ax3 = plt.subplots(figsize=(2.8, 2), dpi=60)
                            labels = ['Vittorie', 'Pareggi', 'Sconfitte']
                            sizes = [vittorie_tot, pareggi_tot, sconfitte_tot]
                            colors = ['#4CAF50', '#FF9800', '#F44336']
                            wedges, texts, autotexts = ax3.pie(
                                sizes,
                                labels=labels,
                                colors=colors,
                                autopct='%1.1f%%',
                                startangle=90,
                                textprops={'fontsize': 8, 'fontweight': 'bold'}
                            )
                            ax3.set_title('Risultati Partite', fontsize=10, fontweight='bold', pad=8)
                            ax3.axis('equal')
                            
                            for autotext in autotexts:
                                autotext.set_fontsize(8)
                                autotext.set_fontweight('bold')
                            
                            st.pyplot(fig3)
                    
                    if overall_stats and overall_stats[0] > 0:
                        tornei, punti_tot, partite_tot, vittorie_tot, pareggi_tot, sconfitte_tot, gf_tot, gs_tot, cf_tot, cs_tot, punti_med, partite_med, vittorie_med = overall_stats
                        first_place, second_place, third_place = ranking_stats
                        
                        # Overall statistics cards
                        col_a, col_b, col_c, col_d = st.columns(4)
                        with col_a:
                            st.metric("🏆 Punti Totali", punti_tot)
                        with col_b:
                            st.metric("⚽ Partite", partite_tot)
                        with col_c:
                            st.metric("✅ Vittorie", vittorie_tot)
                        with col_d:
                            st.metric("🎯 Tornei", tornei)
                        
                        # Ranking statistics
                        st.markdown("#### 🏅 Classifiche Ottenute")
                        rank_col1, rank_col2, rank_col3 = st.columns(3)
                        with rank_col1:
                            st.metric("🥇 Primi Posti", first_place)
                        with rank_col2:
                            st.metric("🥈 Secondi Posti", second_place)
                        with rank_col3:
                            st.metric("🥉 Terzi Posti", third_place)
                        
                        # Tournament history
                        st.markdown("#### 🏆 Storico Tornei")
                        
                        if player_tournament_stats:
                            tournament_history = []
                            for stat in player_tournament_stats:
                                tid, punti, partite, vittorie, pareggi, sconfitte, gf, gs, cf, cs = stat
                                tournament_history.append({
                                    "Torneo ID": tid,
                                    "Pt": punti,
                                    "P": partite,
                                    "V": vittorie,
                                    "N": pareggi,
                                    "S": sconfitte,
                                    "GF": gf,
                                    "GS": gs,
                                    "CF": cf,
                                    "CS": cs
                                })
                            
                            st.dataframe(
                                tournament_history,
                                width='stretch',
                                hide_index=True
                            )
                            
                            # Performance trend charts side by side
                            st.markdown("#### 📊 Prestazioni per Torneo")
                            
                            col_trend, col_media = st.columns(2)
                            
                            # Trend Prestazioni
                            with col_trend:
                                fig2, ax = plt.subplots(figsize=(2.8, 2), dpi=60)
                                tournaments_ids = [str(stat[0]) for stat in player_tournament_stats]
                                gf_trend = [stat[6] for stat in player_tournament_stats]  # goals scored
                                gs_trend = [stat[7] for stat in player_tournament_stats]  # goals conceded
                                
                                x = range(len(tournaments_ids))
                                ax.bar(x, gf_trend, width=0.35, label='Gol Fatti', color='#2196F3', align='center')
                                ax.bar([i + 0.35 for i in x], gs_trend, width=0.35, label='Gol Subiti', color='#F44336', align='center')
                                ax.set_title('Gol Fatti vs Gol Subiti per Torneo', fontsize=10, fontweight='bold')
                                ax.set_xlabel('ID Torneo', fontsize=9)
                                ax.set_ylabel('Gol', fontsize=9)
                                ax.set_xticks([i + 0.175 for i in x])
                                ax.set_xticklabels(tournaments_ids, fontsize=8)
                                ax.tick_params(axis='both', which='major', labelsize=8)
                                ax.legend(fontsize=8)
                                ax.grid(True, alpha=0.3)
                                
                                # Add margin at top for labels
                                all_values = gf_trend + gs_trend
                                max_height = max(all_values) if all_values else 1
                                ax.set_ylim(0, max_height * 1.15)
                                
                                st.pyplot(fig2)
                            
                            # Media Punti graph
                            with col_media:
                                fig3, ax3 = plt.subplots(figsize=(2.8, 2), dpi=60)
                                tournament_ids = [str(stat[0]) for stat in player_tournament_stats]
                                avg_points = [stat[1] / stat[2] if stat[2] > 0 else 0 for stat in player_tournament_stats]  # points/games
                                
                                x_vals = list(range(len(tournament_ids)))
                                ax3.plot(x_vals, avg_points, 'o-', linewidth=2, markersize=6, 
                                        color='#FF9800', markerfacecolor='#FF5722', markeredgecolor='white', markeredgewidth=1.5)
                                
                                ax3.set_title('Media Punti per Partita', fontsize=10, fontweight='bold', pad=8)
                                ax3.set_xlabel('ID Torneo', fontsize=9)
                                ax3.set_ylabel('Punti Medi', fontsize=9)
                                ax3.set_xticks(x_vals)
                                ax3.set_xticklabels(tournament_ids, fontsize=8)
                                ax3.tick_params(axis='both', which='major', labelsize=8)
                                ax3.grid(True, alpha=0.3)
                                
                                for i, y_val in enumerate(avg_points):
                                    ax3.text(i, y_val + 0.05, f'{y_val:.2f}', ha='center', va='bottom', 
                                            fontsize=8, fontweight='bold')
                                
                                # Add margin at top for labels
                                max_height = max(avg_points) if avg_points else 1
                                ax3.set_ylim(0, max_height * 1.15)
                                
                                # Add margin on right side for labels
                                if x_vals:
                                    ax3.set_xlim(-0.5, max(x_vals) + 0.5)
                                
                                st.pyplot(fig3)
                    else:
                            st.info("Nessuna partecipazione ai tornei")
    
    def load_player_data():
        selected = st.session_state.edit_select
        if selected:
            info = get_player_info(selected)
            if info:
                nome, cognome, soprannome, data_nascita, descrizione = info

                st.session_state.edit_nome = nome
                st.session_state.edit_cognome = cognome
                st.session_state.edit_soprannome = soprannome
                st.session_state.original_soprannome = soprannome
                st.session_state.edit_descrizione = descrizione

                if data_nascita:
                    try:
                        st.session_state.edit_data = datetime.strptime(data_nascita, "%Y-%m-%d").date()
                    except:
                        st.session_state.edit_data = None
                else:
                    st.session_state.edit_data = None
            else:
                st.session_state.edit_data = None

    # TAB 3 - EDIT PLAYER
    with tab3:
        st.markdown("### Modifica giocatore")
        all_players = get_players()
        
        if all_players:
            selected_player = st.selectbox("Seleziona giocatore", all_players, key="edit_select", on_change=load_player_data)
            
            if selected_player:
                info = get_player_info(selected_player)
                if info:
                    nome, cognome, soprannome, data_nascita, descrizione = info
                    
                    col_nome, col_cognome = st.columns(2)
                    with col_nome:
                        new_nome = st.text_input("Nome", key="edit_nome")
                    with col_cognome:
                        new_cognome = st.text_input("Cognome", key="edit_cognome")
                    
                    col_soprannome, col_data = st.columns(2)
                    with col_soprannome:
                        new_soprannome = st.text_input("Soprannome",  key="edit_soprannome")
                    with col_data:
                        new_data = st.date_input(
                                "Data di nascita",
                                key="edit_data",
                                min_value=date(1900, 1, 1),
                                max_value=date.today()
                            )
                    
                    new_descrizione = st.text_area("Descrizione", key="edit_descrizione")
                    
                    if st.button("✅ Salva modifiche", type="primary", width='stretch'):
                        try:
                            update_player(st.session_state.original_soprannome, new_nome, new_cognome, new_soprannome, str(new_data), new_descrizione)
                            st.success(f"✅ Giocatore aggiornato con successo!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Errore: {e}")
        else:
            st.info("ℹ️ Nessun giocatore nel database")
    
    # TAB 4 - DELETE PLAYER
    with tab4:
        st.markdown("### Elimina giocatore")
        all_players = get_players()
        
        if all_players:
            selected_player = st.selectbox("Seleziona giocatore", all_players, key="delete_select")
            
            info = get_player_info(selected_player)
            if info:
                nome, cognome, soprannome, data_nascita, descrizione = info
                st.warning(f"⚠️ Stai per eliminare: **{nome} {cognome}** ({soprannome})")
                
                if st.button("❌ Elimina permanentemente", type="secondary", width='stretch'):
                    try:
                        delete_player(soprannome)
                        st.success(f"✅ Giocatore eliminato con successo!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Errore: {e}")
        else:
            st.info("ℹ️ Nessun giocatore nel database")


# =========================
# PAGE: TOURNAMENT HISTORY
# =========================
if page == "📊 Storico Tornei":
    st.subheader("📊 Storico Tornei")
    
    tab1, tab2 = st.tabs(["🏆 Tornei Salvati", "📈 Statistiche Globali"])
    
    # TAB 1 - TOURNAMENT HISTORY
    with tab1:
        st.markdown("### 🏆 Tornei Salvati")
        
        tournaments = list_tournaments()
        
        if tournaments:
            # Display tournaments list
            tournament_data = []
            for t in tournaments:
                tid, nome_torneo, date, n_players = t
                tournament_data.append({
                    "ID": tid,
                    "Nome": nome_torneo,
                    "Data": date,
                    "Giocatori": n_players
                })
            
            st.dataframe(tournament_data, width='stretch', hide_index=True)
            
            # Tournament selector
            selected_tournament = st.selectbox(
                "Seleziona torneo per vedere i dettagli:",
                options=[t[0] for t in tournaments],
                format_func=lambda x: f"Torneo {x} - {next((t[1] for t in tournaments if t[0] == x), '')}"
            )
            

            if selected_tournament:
                st.markdown(f"### 📊 Risultati Torneo {selected_tournament}")
                
                stats = get_tournament_stats(selected_tournament)
                
                if stats:
                    # Format tournament stats
                    formatted_stats = []
                    for stat in stats:
                        soprannome, punti, partite, vittorie, pareggi, sconfitte, gf, gs, cf, cs = stat
                        formatted_stats.append({
                            "🏆 Giocatore": soprannome,
                            "Pt": punti,
                            "P": partite,
                            "V": vittorie,
                            "N": pareggi,
                            "S": sconfitte,
                            "GF": gf,
                            "GS": gs,
                            "CF": cf,
                            "CS": cs
                        })
                    
                    st.dataframe(
                        formatted_stats,
                        width='stretch',
                        hide_index=True
                    )
                    
                    st.markdown("#### 📊 Andamento Punti (Progressivo)")
                    progressive_standings = get_tournament_progressive_standings(selected_tournament)

                    if progressive_standings:
                        fig, ax = plt.subplots(figsize=(12, 8))
                        match_numbers = list(progressive_standings.keys())

                        # prendo tutti i giocatori
                        final_state = progressive_standings[max(match_numbers)]
                        players = list(final_state.keys())

                        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7',
                         '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9']

                        for i, player in enumerate(players):

                            points_progression = []

                            for m in match_numbers:
                                match_state = progressive_standings[m]
                                points_progression.append(match_state[player]["pt"])

                            ax.plot(
                                match_numbers,
                                points_progression,
                                marker='o',
                                linewidth=2,
                                label=player,
                                color=colors[i % len(colors)]
                            )

                            # valore sopra gli ultimi punti
                            ax.text(
                                match_numbers[-1],
                                points_progression[-1],
                                f"{points_progression[-1]}",
                                fontsize=10
                                )

                        ax.set_title("Andamento Punti nel Torneo", fontsize=16, fontweight='bold', pad=15)
                        ax.set_xlabel("Partita", fontsize=13)
                        ax.set_ylabel("Punti Totali", fontsize=13)
                        ax.set_xticks(match_numbers)
                        ax.grid(True, alpha=0.4, linestyle='--')
                        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
                        ax.tick_params(axis='both', which='major', labelsize=11)
                    
                        plt.tight_layout()
                        st.pyplot(fig)
                    else:
                        st.info("ℹ️ Impossibile calcolare l'andamento per questo torneo")
                else:
                    st.info("ℹ️ Nessuna statistica disponibile per questo torneo")

                st.markdown("---")
                st.markdown("### 🗑️ Eliminazione torneo")

                with st.expander("❌ Elimina torneo"):
                    st.warning("⚠️ Questa operazione è irreversibile")

                    st.write("Sei sicuro di voler eliminare questo torneo?")

                    col1, col2 = st.columns(2)

                    with col1:
                        if st.button("✅ Sì, elimina"):
                            delete_tournament(selected_tournament)
                            st.success("Torneo eliminato con successo!")
                            st.rerun()

                    with col2:
                        if st.button("❌ No, annulla"):
                           st.info("Operazione annullata")
        else:
            st.info("ℹ️ Nessun torneo salvato")
    
    # TAB 2 - GLOBAL PLAYER STATISTICS
    with tab2:
        st.markdown("### 📈 Statistiche Globali Giocatori")
        
        all_players = get_players()
        
        if all_players:
            global_stats = []
            
            for player in all_players:
                overall = get_player_overall_stats(player)
                ranking = get_player_ranking_stats(player)

                if overall and overall[0] > 0:  # Only show players who played tournaments
                    tornei, punti_tot, partite_tot, vittorie_tot, pareggi_tot, sconfitte_tot, gf_tot, gs_tot, cf_tot, cs_tot, punti_med, partite_med, vittorie_med = overall
                    first_place, second_place, third_place = get_player_ranking_stats(player)

                    global_stats.append({
                        "👤 Giocatore": player,
                        "🎯 Tornei": tornei,
                        "🥇 1°": first_place,
                        "🥈 2°": second_place,
                        "🥉 3°": third_place,
                        "🏆 Punti Totali": punti_tot,
                        "⚽ Partite": partite_tot,
                        "✅ Vittorie": vittorie_tot,
                        "🤝 Pareggi": pareggi_tot,
                        "❌ Sconfitte": sconfitte_tot,
                        "🎯 GF": gf_tot,
                        "🛡️ GS": gs_tot,
                        "💥 Cappotti Fatti": cf_tot,
                        "😵 Cappotti Subiti": cs_tot,
                        "📊 Punti per Partita": round(punti_tot / partite_tot, 2) if partite_tot > 0 else 0,
                    })
            
            if global_stats:
                # Sort by total points
                global_stats.sort(key=lambda x: (x["🥇 1°"], x["🥈 2°"],x["🥉 3°"],x["🏆 Punti Totali"]), reverse = True)
                
                st.dataframe(
                    global_stats,
                    width='stretch',
                    hide_index=True
                )
                
                st.caption(f"Statistiche complessive di {len(global_stats)} giocatori che hanno partecipato ai tornei")
            else:
                st.info("ℹ️ Nessuna statistica globale disponibile")
        else:
            st.info("ℹ️ Nessun giocatore nel database")