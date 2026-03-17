import streamlit as st
import pandas as pd
import random
from io import BytesIO

st.set_page_config(page_title="Schemagenerator", layout="wide")
st.title("📅 Generera schema")

# --- CSS ---
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
</style>
""", unsafe_allow_html=True)

veckodagar = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag"]

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
            "Max pass per person/dag",
            min_value=1,
            value=2
        )

    antal_veckor = st.number_input("Antal veckor", min_value=1, value=4)

    start_day = pd.to_datetime(start_day_time.strftime("%H:%M"))
    end_day = pd.to_datetime(end_day_time.strftime("%H:%M"))

    total_minutes = int((end_day - start_day).total_seconds() / 60)
    pass_langd = total_minutes // pass_per_day

    st.text(f"Passlängd: {pass_langd} min")

    pass_times = [
        (
            start_day + pd.Timedelta(minutes=i * pass_langd),
            start_day + pd.Timedelta(minutes=(i + 1) * pass_langd)
        )
        for i in range(pass_per_day)
    ]

    st.session_state.pass_times_display = [
        f"{s.strftime('%H:%M')}–{e.strftime('%H:%M')}"
        for s, e in pass_times
    ]

# --- PERSONAL ---
with st.expander("👤 Personal"):

    if "people" not in st.session_state:
        st.session_state.people = [f"P{i+1}" for i in range(9)]

    namn = st.session_state.people

    start_tid = {}
    slut_tid = {}
    arbetsdagar = {}

    for i, n in enumerate(namn):

        cols = st.columns(4)

        with cols[0]:
            name_input = st.text_input("Namn", value=n, key=f"name_{i}")

        with cols[1]:
            start = st.time_input("Börjar", value=pd.to_datetime("08:00").time(), key=f"start_{i}")

        with cols[2]:
            end = st.time_input("Slutar", value=pd.to_datetime("16:00").time(), key=f"end_{i}")

        with cols[3]:
            dagar_val = []
            for dag in veckodagar:
                if st.checkbox(dag, value=True, key=f"{i}_{dag}"):
                    dagar_val.append(dag)

        namn[i] = name_input
        start_tid[name_input] = start
        slut_tid[name_input] = end
        arbetsdagar[name_input] = dagar_val

    if st.button("Lägg till person"):
        st.session_state.people.append(f"P{len(namn)+1}")

# --- COLORS ---
default_colors = [
"#FF9999","#99CCFF","#FFCC99","#99FF99","#FFCCFF",
"#CCCCFF","#FFFF99","#FF9966","#66CC99"
]

farger = {n: default_colors[i % len(default_colors)] for i, n in enumerate(namn)}
farger["Ingen tillgänglig"] = "#E0E0E0"

# --- SMART SCHEDULER ---
def skapa_schema():

    schema = {f"Vecka {v+1}": {dag:{} for dag in veckodagar} for v in range(antal_veckor)}

    pass_raknare = {n: 0 for n in namn}
    total_minutes_person = {n: 0 for n in namn}

    for vecka in range(antal_veckor):

        for dag in veckodagar:

            daily_count = {n: 0 for n in namn}

            for p_idx in range(pass_per_day):

                pass_time = st.session_state.pass_times_display[p_idx].split("–")[0]

                tillgangliga = [
                    n for n in namn
                    if daily_count[n] < max_pass_per_person_per_day
                    and start_tid[n] <= pd.to_datetime(pass_time).time() < slut_tid[n]
                    and dag in arbetsdagar.get(n, veckodagar)
                ]

                if tillgangliga:

                    scores = {}

                    for n in tillgangliga:

                        availability = len(arbetsdagar[n]) or 1

                        score = (
                            pass_raknare[n] * 10 +
                            total_minutes_person[n]
                        ) / availability

                        scores[n] = score

                    min_score = min(scores.values())
                    candidates = [n for n in tillgangliga if scores[n] == min_score]

                    vald = random.choice(candidates)

                    # uppdatera
                    daily_count[vald] += 1
                    pass_raknare[vald] += 1

                    start = pd.to_datetime(st.session_state.pass_times_display[p_idx].split("–")[0])
                    end = pd.to_datetime(st.session_state.pass_times_display[p_idx].split("–")[1])

                    minutes = int((end - start).total_seconds() / 60)
                    total_minutes_person[vald] += minutes

                else:
                    vald = "Ingen tillgänglig"

                schema[f"Vecka {vecka+1}"][dag][f"Pass {p_idx+1}"] = vald

    return schema

# --- GENERATE ---
if st.button("Generera schema"):

    schema = skapa_schema()

    for vecka, dagar in schema.items():

        st.subheader(vecka)

        week_pass = {n:0 for n in namn}
        week_min = {n:0 for n in namn}

        for dag, passes in dagar.items():

            html = f"<h5>{dag}</h5><table style='width:100%;table-layout:fixed;border-collapse:collapse;'>"

            html += "<tr>"
            for pt in st.session_state.pass_times_display:
                html += f"<td style='border:1px solid black;background:#28a745;color:white;text-align:center'>{pt}</td>"
            html += "</tr><tr>"

            for i in range(pass_per_day):

                person = passes[f"Pass {i+1}"]
                color = farger.get(person,"white")

                html += f"<td style='border:1px solid black;background:{color};height:60px;text-align:center'>{person}</td>"

                if person != "Ingen tillgänglig":

                    start = pd.to_datetime(st.session_state.pass_times_display[i].split("–")[0])
                    end = pd.to_datetime(st.session_state.pass_times_display[i].split("–")[1])

                    minutes = int((end - start).total_seconds() / 60)

                    week_pass[person] += 1
                    week_min[person] += minutes

            html += "</tr></table>"
            st.markdown(html, unsafe_allow_html=True)

        st.markdown("### 📊 Veckosummering")

        summary = "<table style='width:60%;border-collapse:collapse;'>"
        summary += "<tr><th>Person</th><th>Pass</th><th>Tid</th></tr>"

        for n in namn:
            h, m = divmod(week_min[n], 60)
            summary += f"<tr><td>{n}</td><td>{week_pass[n]}</td><td>{h:02d}:{m:02d}</td></tr>"

        summary += "</table>"
        st.markdown(summary, unsafe_allow_html=True)

    # --- EXPORT ---
    output = BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:

        workbook = writer.book
        ws = workbook.add_worksheet("Schema")
        writer.sheets["Schema"] = ws

        header = workbook.add_format({"bold":True,"border":1,"align":"center"})

        formats = {
            p: workbook.add_format({"bg_color":c,"border":1,"align":"center"})
            for p,c in farger.items()
        }

        ws.write(0,0,"Dag",header)

        for i in range(pass_per_day):
            ws.write(0,i+1,st.session_state.pass_times_display[i],header)

        row = 1

        for vecka, dagar in schema.items():

            ws.write(row,0,vecka)
            row += 1

            for dag, passes in dagar.items():

                ws.write(row,0,dag)

                for i in range(pass_per_day):
                    p = passes[f"Pass {i+1}"]
                    ws.write(row,i+1,p,formats.get(p))

                row += 1

            row += 1

    st.download_button(
        "⬇️ Ladda ner Excel",
        data=output.getvalue(),
        file_name="schema.xlsx"
    )