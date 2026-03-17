import streamlit as st 
import pandas as pd
import random
from io import BytesIO

st.set_page_config(page_title="Schemagenerator", layout="wide")
st.title("📅 Generera schema")

# --- BUTTON CSS STYLING ---
st.markdown("""
<style>
div.stButton > button:first-child {
    background-color: #28a745 !important;
    color: white !important;
    font-size: 18px !important;
    font-weight: bold !important;
    height: 3.5em !important;
    width: 100% !important;
    border-radius: 10px !important;
    margin-top: 10px !important;
    margin-bottom: 20px !important;
}
.delete-button {
    color: white !important;
    background-color: #ff4d4d !important;
    font-weight: bold !important;
    border-radius: 5px !important;
    width: 2em !important;
    height: 2em !important;
    padding: 0 !important;
    font-size: 12px !important;
    margin-left: 5px !important;
}
.separator {
    border-top: 1px solid #cccccc;
    margin: 10px 0;
}
.strike {
    text-decoration: line-through;
    color: gray;
}
.day-separator {
    border-top: 1px solid #e0e0e0;
    margin: 4px 0;
}
</style>
""", unsafe_allow_html=True)

# --- SCHEDULE SETTINGS ---
with st.expander("⚙️ Schemainställningar", expanded=True):
    col1, col2 = st.columns(2)
    with col1:
        start_day_time = st.time_input("Starttid", value=pd.to_datetime("08:00").time())
    with col2:
        end_day_time = st.time_input("Sluttid", value=pd.to_datetime("16:00").time())

    col3, col4 = st.columns(2)
    with col3:
        pass_per_day = st.number_input("Pass per dag", min_value=1, value=8)
    with col4:
        max_pass_per_person_per_day = st.number_input(
            "Max antal pass per person per dag",
            min_value=1,
            value=2
        )

    antal_veckor = st.number_input("Schema för antal veckor", min_value=1, value=4)

    start_day = pd.to_datetime(start_day_time.strftime("%H:%M"))
    end_day = pd.to_datetime(end_day_time.strftime("%H:%M"))

    total_minutes = int((end_day - start_day).total_seconds() / 60)
    pass_langd = total_minutes // pass_per_day
    st.text(f"Passlängd: {pass_langd} min")

    manual_times = st.checkbox("Justera passens tider manuellt")
    pass_times = []
    prev_end = start_day

    if manual_times:
        for i in range(pass_per_day):
            cols = st.columns(2)
            with cols[0]:
                start_input = st.time_input(
                    f"Pass {i+1} start",
                    value=prev_end.time(),
                    key=f"start_pass_{i}"
                )
            with cols[1]:
                end_input = st.time_input(
                    f"Pass {i+1} slut",
                    value=(prev_end + pd.Timedelta(minutes=pass_langd)).time(),
                    key=f"end_pass_{i}"
                )
            start_dt = pd.to_datetime(start_input.strftime("%H:%M"))
            end_dt = pd.to_datetime(end_input.strftime("%H:%M"))
            if start_dt < prev_end:
                start_dt = prev_end
            if end_dt <= start_dt:
                end_dt = start_dt + pd.Timedelta(minutes=pass_langd)
            prev_end = end_dt
            pass_times.append((start_dt, end_dt))
    else:
        for i in range(pass_per_day):
            start_dt = start_day + pd.Timedelta(minutes=i * pass_langd)
            end_dt = start_day + pd.Timedelta(minutes=(i + 1) * pass_langd)
            pass_times.append((start_dt, end_dt))

    st.session_state.pass_times_display = [
        f"{s.time().strftime('%H:%M')}–{e.time().strftime('%H:%M')}"
        for s, e in pass_times
    ]

# --- PERSONAL ---
veckodagar = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag"]

# Initiera session_state om inte redan gjort
if "people" not in st.session_state:
    st.session_state.people = [f"P{i+1}" for i in range(9)]
if "dag_tillgang" not in st.session_state:
    st.session_state.dag_tillgang = {n: {dag: True for dag in veckodagar} for n in st.session_state.people}
if "work_times" not in st.session_state:
    # Nu lagras start och sluttid som tuple per dag
    st.session_state.work_times = {
        n: {dag: (pd.to_datetime("08:00").time(), pd.to_datetime("16:00").time()) for dag in veckodagar}
        for n in st.session_state.people
    }

dag_tillgang = st.session_state.dag_tillgang
work_times = st.session_state.work_times

with st.expander("👤 Personal", expanded=True):
    col_add = st.columns([3,1])
    with col_add[0]:
        ny_person_namn = st.text_input("Lägg till person", "")
    with col_add[1]:
        if st.button("Lägg till"):
            if ny_person_namn and ny_person_namn not in st.session_state.people:
                st.session_state.people.append(ny_person_namn)
                st.session_state.dag_tillgang[ny_person_namn] = {dag: True for dag in veckodagar}
                st.session_state.work_times[ny_person_namn] = {dag: (pd.to_datetime("08:00").time(), pd.to_datetime("16:00").time()) for dag in veckodagar}

    st.markdown("**Nuvarande personal:**")
    if "remove_person" not in st.session_state:
        st.session_state.remove_person = None

    for n in st.session_state.people:
        cols = st.columns([5,1])
        with cols[0]:
            nytt_namn = st.text_input("", value=n, key=f"edit_name_{n}")
            if nytt_namn != n and nytt_namn not in st.session_state.people:
                st.session_state.people[st.session_state.people.index(n)] = nytt_namn
                st.session_state.dag_tillgang[nytt_namn] = st.session_state.dag_tillgang.pop(n)
                st.session_state.work_times[nytt_namn] = st.session_state.work_times.pop(n)
                n = nytt_namn
        with cols[1]:
            if st.button("✖", key=f"remove_{n}", help="Ta bort person"):
                st.session_state.remove_person = n

        with st.expander("Arbetstider", expanded=False):
            for dag in veckodagar:
                cols_day = st.columns([0.2,1,1])
                with cols_day[0]:
                    tillgang = st.checkbox("", value=dag_tillgang[n][dag], key=f"available_{n}_{dag}")
                    dag_tillgang[n][dag] = tillgang
                with cols_day[1]:
                    st.markdown(f"**{dag}**" if tillgang else f"<span class='strike'>{dag}</span>", unsafe_allow_html=True)
                with cols_day[2]:
                    if tillgang:
                        start_prev, end_prev = work_times[n][dag]
                        times = st.time_input(f"{dag} tider", value=(start_prev, end_prev), key=f"time_{n}_{dag}")
                        work_times[n][dag] = times
            st.markdown("<div class='day-separator'></div>", unsafe_allow_html=True)

    if st.session_state.remove_person:
        person_to_remove = st.session_state.remove_person
        if person_to_remove in st.session_state.people:
            st.session_state.people.remove(person_to_remove)
            st.session_state.dag_tillgang.pop(person_to_remove, None)
            st.session_state.work_times.pop(person_to_remove, None)
        st.session_state.remove_person = None
        st.experimental_rerun()

# --- COLORS ---
default_colors = [
    "#FF9999","#99CCFF","#FFCC99","#99FF99","#FFCCFF",
    "#CCCCFF","#FFFF99","#FF9966","#66CC99"
]
farger = {n: default_colors[i % len(default_colors)] for i, n in enumerate(st.session_state.people)}
farger["Ingen tillgänglig"] = "#E0E0E0"

# --- SCHEMA GENERATOR ---
def skapa_schema():
    schema = {f"Vecka {v+1}": {dag:{} for dag in veckodagar} for v in range(antal_veckor)}
    pass_raknare = {n:0 for n in st.session_state.people}
    prev_day_assignments = {dag: {f"Pass {i+1}": None for i in range(pass_per_day)} for dag in veckodagar}

    for vecka in range(antal_veckor):
        for dag_idx, dag in enumerate(veckodagar):
            daily_count = {n:0 for n in st.session_state.people}
            prev_person = None

            for p_idx in range(pass_per_day):
                p = f"Pass {p_idx+1}"
                pass_time = st.session_state.pass_times_display[p_idx].split("–")[0]

                tillgangliga = [
                    n for n in st.session_state.people
                    if daily_count[n] < max_pass_per_person_per_day
                    and dag_tillgang[n].get(dag, True)
                    and work_times[n][dag][0] <= pd.to_datetime(pass_time).time() < work_times[n][dag][1]
                ]

                if prev_person in tillgangliga and len(tillgangliga) > 1:
                    tillgangliga.remove(prev_person)

                if dag_idx > 0:
                    prev_day_person = prev_day_assignments[veckodagar[dag_idx-1]][p]
                    if prev_day_person in tillgangliga and len(tillgangliga) > 1:
                        tillgangliga.remove(prev_day_person)

                if tillgangliga:
                    min_pass = min(pass_raknare[n] for n in tillgangliga)
                    candidates = [n for n in tillgangliga if pass_raknare[n] == min_pass]
                    vald = random.choice(candidates)
                    daily_count[vald] += 1
                    pass_raknare[vald] += 1
                else:
                    vald = "Ingen tillgänglig"

                schema[f"Vecka {vecka+1}"][dag][p] = vald
                prev_person = vald

            prev_day_assignments[dag] = schema[f"Vecka {vecka+1}"][dag]

    return schema

# --- GENERATE SCHEDULE ---
if st.button("Generera schema"):
    schema = skapa_schema()
    # ... Resten av koden för visning och Excel-export som tidigare ...
