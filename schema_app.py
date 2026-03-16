import streamlit as st
import pandas as pd
import random
from io import BytesIO

st.set_page_config(page_title="Schemagenerator", layout="wide")
st.title("📅 Generera schema")

# --- BUTTON CSS ---
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
}
</style>
""", unsafe_allow_html=True)

# --- SETTINGS ---
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

    antal_veckor = st.number_input("Schema veckor", min_value=1, value=4)

    start_day = pd.to_datetime(start_day_time.strftime("%H:%M"))
    end_day = pd.to_datetime(end_day_time.strftime("%H:%M"))

    total_minutes = int((end_day - start_day).total_seconds()/60)
    pass_langd = total_minutes // pass_per_day

    st.text(f"Passlängd: {pass_langd} min")

    manual_times = st.checkbox("Justera pass manuellt")

    # --- PASS TIMES ---
    if manual_times:

        pass_times = []

        prev_end = start_day

        for i in range(pass_per_day):

            col1, col2 = st.columns(2)

            with col1:
                pt_start = st.time_input(
                    f"Pass {i+1} start",
                    value=prev_end.time()
                )

            with col2:
                pt_end = st.time_input(
                    f"Pass {i+1} slut",
                    value=(prev_end + pd.Timedelta(minutes=pass_langd)).time()
                )

            start_dt = pd.to_datetime(pt_start.strftime("%H:%M"))
            end_dt = pd.to_datetime(pt_end.strftime("%H:%M"))

            if start_dt < prev_end:
                start_dt = prev_end

            if end_dt <= start_dt:
                end_dt = start_dt + pd.Timedelta(minutes=pass_langd)

            prev_end = end_dt

            pass_times.append((start_dt,end_dt))

        st.session_state.pass_times_display = [
            f"{s.time().strftime('%H:%M')}–{e.time().strftime('%H:%M')}"
            for s,e in pass_times
        ]

    else:

        st.session_state.pass_times_display = [
            f"{(start_day + pd.Timedelta(minutes=i*pass_langd)).time().strftime('%H:%M')}–"
            f"{(start_day + pd.Timedelta(minutes=(i+1)*pass_langd)).time().strftime('%H:%M')}"
            for i in range(pass_per_day)
        ]

# --- STAFF ---
with st.expander("👤 Personal"):

    if "people" not in st.session_state:
        st.session_state.people = [f"P{i+1}" for i in range(9)]

    namn = st.session_state.people

    start_tid = {}
    slut_tid = {}

    for i,n in enumerate(namn):

        col1,col2,col3 = st.columns(3)

        with col1:
            new_name = st.text_input("Namn", value=n, key=f"name{i}")

        with col2:
            start = st.time_input("Start", value=pd.to_datetime("08:00").time(), key=f"s{i}")

        with col3:
            end = st.time_input("Slut", value=pd.to_datetime("16:00").time(), key=f"e{i}")

        namn[i] = new_name
        start_tid[new_name] = start
        slut_tid[new_name] = end

    if st.button("Lägg till person"):
        st.session_state.people.append(f"P{len(namn)+1}")

veckodagar = ["Måndag","Tisdag","Onsdag","Torsdag","Fredag"]

# --- COLORS ---
default_colors = ["#FF9999","#99CCFF","#FFCC99","#99FF99","#FFCCFF","#CCCCFF","#FFFF99","#FF9966","#66CC99"]
farger = {n:default_colors[i % len(default_colors)] for i,n in enumerate(namn)}
farger["Ingen tillgänglig"] = "#E0E0E0"

# --- SCHEDULE GENERATOR ---
def skapa_schema():

    schema = {f"Vecka {v+1}":{d:{} for d in veckodagar} for v in range(antal_veckor)}

    pass_raknare = {n:0 for n in namn}

    for vecka in range(antal_veckor):

        for dag in veckodagar:

            daily_count = {n:0 for n in namn}

            for p_idx in range(pass_per_day):

                p = f"Pass {p_idx+1}"

                pass_time = st.session_state.pass_times_display[p_idx].split("–")[0]

                tillgangliga = [
                    n for n in namn
                    if daily_count[n] < max_pass_per_person_per_day
                    and start_tid[n] <= pd.to_datetime(pass_time).time() < slut_tid[n]
                ]

                if tillgangliga:

                    min_pass = min(pass_raknare[n] for n in tillgangliga)

                    candidates = [n for n in tillgangliga if pass_raknare[n]==min_pass]

                    vald = random.choice(candidates)

                    daily_count[vald]+=1
                    pass_raknare[vald]+=1

                else:
                    vald="Ingen tillgänglig"

                schema[f"Vecka {vecka+1}"][dag][p]=vald

    return schema

# --- GENERATE ---
if st.button("Generera schema"):

    schema = skapa_schema()

    cell_width = 100/pass_per_day

    for vecka,dagar in schema.items():

        st.subheader(vecka)

        week_pass_count={n:0 for n in namn}
        week_minutes={n:0 for n in namn}

        for dag,passes in dagar.items():

            html=f"<h5>{dag}</h5><table style='border-collapse:collapse;width:100%;'>"

            html+="<tr>"

            for pt in st.session_state.pass_times_display:

                html+=f"<td style='border:1px solid black;background:#28a745;color:white;text-align:center'>{pt}</td>"

            html+="</tr><tr>"

            for i in range(pass_per_day):

                p=f"Pass {i+1}"

                person=passes[p]

                color=farger.get(person,"white")

                html+=f"<td style='border:1px solid black;background:{color};text-align:center'>{person}</td>"

                if person!="Ingen tillgänglig":

                    start=pd.to_datetime(st.session_state.pass_times_display[i].split("–")[0])
                    end=pd.to_datetime(st.session_state.pass_times_display[i].split("–")[1])

                    week_pass_count[person]+=1
                    week_minutes[person]+=int((end-start).total_seconds()/60)

            html+="</tr></table>"

            st.markdown(html,unsafe_allow_html=True)

        st.markdown("### 📊 Veckosummering")

        summary="<table style='border-collapse:collapse;width:50%'>"
        summary+="<tr><th>Person</th><th>Pass</th><th>Tid</th></tr>"

        for n in namn:

            h,m=divmod(week_minutes[n],60)

            summary+=f"<tr><td>{n}</td><td>{week_pass_count[n]}</td><td>{h:02d}:{m:02d}</td></tr>"

        summary+="</table>"

        st.markdown(summary,unsafe_allow_html=True)