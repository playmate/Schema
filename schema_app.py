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
    width: 3em !important;
    height: 2em !important;
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

if "people" not in st.session_state:
    st.session_state.people = [f"P{i+1}" for i in range(9)]

if "dag_tillgang" not in st.session_state:
    st.session_state.dag_tillgang = {n: {dag: True for dag in veckodagar} for n in st.session_state.people}
if "start_tid" not in st.session_state:
    st.session_state.start_tid = {n: pd.to_datetime("08:00").time() for n in st.session_state.people}
if "slut_tid" not in st.session_state:
    st.session_state.slut_tid = {n: pd.to_datetime("16:00").time() for n in st.session_state.people}

dag_tillgang = st.session_state.dag_tillgang
start_tid = st.session_state.start_tid
slut_tid = st.session_state.slut_tid

# --- Personal med borttagning alltid synlig ---
with st.expander("👤 Personal", expanded=True):
    # Lägg till ny person
    col_add = st.columns([3,1])
    with col_add[0]:
        ny_person_namn = st.text_input("Lägg till person", "")
    with col_add[1]:
        if st.button("Lägg till"):
            if ny_person_namn and ny_person_namn not in st.session_state.people:
                st.session_state.people.append(ny_person_namn)
                st.session_state.dag_tillgang[ny_person_namn] = {dag: True for dag in veckodagar}
                st.session_state.start_tid[ny_person_namn] = pd.to_datetime("08:00").time()
                st.session_state.slut_tid[ny_person_namn] = pd.to_datetime("16:00").time()

    st.markdown("**Nuvarande personal:**")

    # Temporär variabel för borttagning
    if "remove_person" not in st.session_state:
        st.session_state.remove_person = None

    for n in st.session_state.people:
        # Rad med namn + röd knapp alltid synlig
        cols = st.columns([6,1])
        with cols[0]:
            st.markdown(f"**{n}**")
        with cols[1]:
            if st.button("✖", key=f"remove_{n}", help="Ta bort person"):
                st.session_state.remove_person = n

        # Expander under raden för redigering
        with st.expander(f"Ändra {n}", expanded=False):
            for dag in veckodagar:
                cols_day = st.columns([0.2,0.5,0.5,0.5])
                with cols_day[0]:
                    tillgang = st.checkbox("", value=st.session_state.dag_tillgang[n][dag], key=f"available_{n}_{dag}")
                    st.session_state.dag_tillgang[n][dag] = tillgang
                with cols_day[1]:
                    st.markdown(f"**{dag}**" if tillgang else f"<span class='strike'>{dag}</span>", unsafe_allow_html=True)
                with cols_day[2]:
                    st.time_input("Start", value=st.session_state.start_tid[n], key=f"start_{n}_{dag}", disabled=not tillgang)
                    if tillgang:
                        st.session_state.start_tid[n] = st.session_state[f"start_{n}_{dag}"]
                with cols_day[3]:
                    st.time_input("Slut", value=st.session_state.slut_tid[n], key=f"end_{n}_{dag}", disabled=not tillgang)
                    if tillgang:
                        st.session_state.slut_tid[n] = st.session_state[f"end_{n}_{dag}"]
            st.markdown("<div class='day-separator'></div>", unsafe_allow_html=True)

    # Ta bort markerad person
    if st.session_state.remove_person:
        person_to_remove = st.session_state.remove_person
        if person_to_remove in st.session_state.people:
            st.session_state.people.remove(person_to_remove)
            st.session_state.dag_tillgang.pop(person_to_remove, None)
            st.session_state.start_tid.pop(person_to_remove, None)
            st.session_state.slut_tid.pop(person_to_remove, None)
        st.session_state.remove_person = None
        st.experimental_rerun()
