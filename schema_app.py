import streamlit as st
import pandas as pd
import random
from io import BytesIO

st.set_page_config(page_title="Schemagenerator", layout="wide")
st.title("📅 Generera schema")

# --- BUTTON STYLING ---
st.markdown("""
<style>
div.stButton > button:first-child {
    background-color: #4CAF50;
    color: white;
    height: 3em;
    width: 100%;
    font-size: 16px;
    font-weight: bold;
    border-radius: 8px;
    margin-bottom: 10px;
}
button.remove-btn {
    background-color:#f44336 !important;
    color:white !important;
    border-radius:50%;
}
</style>
""", unsafe_allow_html=True)

# --- SCHEM SETTINGS ---
with st.expander("⚙️ Schemainställningar", expanded=True):
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        start_day_time = st.time_input("Starttid", value=pd.to_datetime("08:00").time(),
                                       help="När arbetsdagen börjar")
    with col2:
        end_day_time = st.time_input("Sluttid", value=pd.to_datetime("16:00").time(),
                                     help="När arbetsdagen slutar")
    with col3:
        pass_per_day = st.number_input("Pass per dag", min_value=1, value=8, step=1,
                                       help="Antal pass som ska schemaläggas varje dag")
    start_day = pd.to_datetime(start_day_time.strftime("%H:%M"))
    end_day = pd.to_datetime(end_day_time.strftime("%H:%M"))
    total_minutes = int((end_day - start_day).total_seconds() / 60)
    pass_langd = total_minutes // pass_per_day
    with col4:
        st.text(f"Passlängd: {pass_langd} min")

    max_pass_per_person_per_day = st.number_input(
        "Max antal pass per person per dag:",
        min_value=1,
        value=2,
        step=1
    )

    # --- Manual pass times ---
    manual_times = st.checkbox("Edit pass times manually")
    if manual_times:
        if "pass_times_manual" not in st.session_state:
            st.session_state.pass_times_manual = [start_day + pd.Timedelta(minutes=i*pass_langd) for i in range(pass_per_day)]
        pass_time_inputs = []
        for i in range(pass_per_day):
            pt_start = st.time_input(f"Pass {i+1} start", value=st.session_state.pass_times_manual[i].time())
            pt_end = st.time_input(f"Pass {i+1} end", value=(st.session_state.pass_times_manual[i]+pd.Timedelta(minutes=pass_langd)).time())
            st.session_state.pass_times_manual[i] = pd.to_datetime(pt_start.strftime("%H:%M"))
            pass_time_inputs.append(f"{pt_start.strftime('%H:%M')}–{pt_end.strftime('%H:%M')}")
        st.session_state.pass_times_display = pass_time_inputs
    else:
        st.session_state.pass_times_display = [f"{(start_day + pd.Timedelta(minutes=i*pass_langd)).time().strftime('%H:%M')}–{(start_day + pd.Timedelta(minutes=(i+1)*pass_langd)).time().strftime('%H:%M')}" for i in range(pass_per_day)]

# --- PERSONAL SECTION ---
with st.expander("👤 Personal", expanded=True):
    if "people" not in st.session_state:
        st.session_state.people = [f"P{i+1}" for i in range(9)]

    new_people_list = []
    for i, n in enumerate(st.session_state.people):
        st.markdown(f"**Person {i+1}**")
        cols = st.columns([3, 1, 2, 2])
        name_input = cols[0].text_input(f"Namn", value=n, key=f"name_{i}")
        remove = cols[1].button("❌", key=f"remove_{i}", help="Ta bort person")
        start_time = cols[2].time_input("Börjar jobba", value=pd.to_datetime("08:00").time(), key=f"start_{i}")
        end_time = cols[3].time_input("Slutar jobba", value=pd.to_datetime("16:00").time(), key=f"slut_{i}")
        if not remove:
            new_people_list.append(name_input)

    st.session_state.people = new_people_list
    namn = st.session_state.people

    # Store start/end times
    if "start_tid" not in st.session_state:
        st.session_state.start_tid = {n: pd.to_datetime("08:00").time() for n in namn}
    if "slut_tid" not in st.session_state:
        st.session_state.slut_tid = {n: pd.to_datetime("16:00").time() for n in namn}

    for n in namn:
        st.session_state.start_tid[n] = st.session_state.start_tid.get(n, pd.to_datetime("08:00").time())
        st.session_state.slut_tid[n] = st.session_state.slut_tid.get(n, pd.to_datetime("16:00").time())

    start_tid = st.session_state.start_tid
    slut_tid = st.session_state.slut_tid

    # Add person button
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Lägg till person"):
        st.session_state.people.append(f"Namn {len(st.session_state.people)+1}")

# --- General params ---
veckodagar = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag"]
antal_veckor = 4
totalt_pass_per_person = len(veckodagar) * pass_per_day * antal_veckor

# --- Colors ---
default_colors = ["#FF9999","#99CCFF","#FFCC99","#99FF99","#FFCCFF","#CCCCFF","#FFFF99","#FF9966","#66CC99"]
farger = {n: default_colors[i % len(default_colors)] for i, n in enumerate(namn)}
farger["Ingen tillgänglig"] = "#E0E0E0"

# --- FAIR SCHEDULE GENERATOR ---
def skapa_schema():
    schema = {f"Vecka {v+1}": {dag:{} for dag in veckodagar} for v in range(antal_veckor)}
    pass_raknare = {n:0 for n in namn}  
    for vecka in range(antal_veckor):
        used_passes_per_person = {n:set() for n in namn}
        for dag in veckodagar:
            daily_count = {n:0 for n in namn}
            tidigare_pass = schema[f"Vecka {vecka+1}"][dag]
            for p_idx in range(pass_per_day):
                p = f"Pass {p_idx+1}"
                last_person = list(tidigare_pass.values())[-1] if tidigare_pass else None
                pass_time = st.session_state.pass_times_display[p_idx].split("–")[0]
                tillgangliga = [
                    n for n in namn
                    if daily_count[n] < max_pass_per_person_per_day
                    and n != last_person
                    and p not in used_passes_per_person[n]
                    and start_tid[n] <= pd.to_datetime(pass_time).time() < slut_tid[n]
                ]
                if tillgangliga:
                    min_passes = min(pass_raknare[n] for n in tillgangliga)
                    candidates = [n for n in tillgangliga if pass_raknare[n] == min_passes]
                    vald = random.choice(candidates)
                    daily_count[vald] += 1
                    used_passes_per_person[vald].add(p)
                    pass_raknare[vald] += 1
                else:
                    vald = "Ingen tillgänglig"
                schema[f"Vecka {vecka+1}"][dag][p] = vald
    return schema

# --- GENERATE SCHEDULE ---
with st.expander("📊 Genererat schema", expanded=True):
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Generera schema"):
        schema = skapa_schema()
        cell_width = 100 / pass_per_day

        for vecka, dagar in schema.items():
            st.subheader(vecka)
            for dag, passes in dagar.items():
                html = f"<h5>{dag}</h5><table style='border-collapse:collapse;width:100%;table-layout:fixed;'>"
                # Pass times row
                html += "<tr>"
                for pt in st.session_state.pass_times_display:
                    html += f"<td style='border:1px solid white;width:{cell_width}%;height:20px;padding:2px;text-align:center;font-size:12px;background-color:#f0f0f0;'>{pt}</td>"
                html += "</tr>"
                # Person row
                html += "<tr>"
                for p_idx in range(pass_per_day):
                    p = f"Pass {p_idx+1}"
                    person = passes[p]
                    color = farger.get(person, "#FFFFFF")
                    html += (
                        f"<td style='border:1px solid white;width:{cell_width}%;height:60px;padding:4px;"
                        f"background-color:{color};color:black;text-align:center;vertical-align:middle;"
                        f"word-wrap:break-word;overflow:hidden;font-size:14px;'>{person}</td>"
                    )
                html += "</tr></table>"
                st.markdown(html, unsafe_allow_html=True)