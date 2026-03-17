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

with st.expander("👤 Personal", expanded=True):
    if "people" not in st.session_state:
        st.session_state.people = [f"P{i+1}" for i in range(9)]
    namn = st.session_state.people

    start_tid = {}
    slut_tid = {}
    dag_tillgang = {n: {dag: True for dag in veckodagar} for n in namn}

    remove_indices = []
    for i, n in enumerate(namn):
        st.markdown("<div class='separator'></div>", unsafe_allow_html=True)
        cols = st.columns([3,1])
        with cols[0]:
            name_input = st.text_input("Namn", value=n, key=f"name_{i}")
        with cols[1]:
            if st.button("✖", key=f"remove_{i}", help="Ta bort person"):
                remove_indices.append(i)
        namn[i] = name_input

        st.markdown("**Arbetstider per dag:**")
        for dag in veckodagar:
            cols = st.columns([0.2,0.5,0.5,0.5])
            with cols[0]:
                available = st.checkbox("", value=True, key=f"available_{i}_{dag}")
                dag_tillgang[name_input][dag] = available
            with cols[1]:
                if available:
                    st.markdown(f"**{dag}**")
                else:
                    st.markdown(f"<span class='strike'>{dag}</span>", unsafe_allow_html=True)
            with cols[2]:
                if available:
                    start = st.time_input(f"Arbetstider", value=pd.to_datetime("08:00").time(), key=f"start_{i}_{dag}")
                    start_tid[name_input] = start
                else:
                    st.time_input("Arbetstider", value=pd.to_datetime("08:00").time(), key=f"start_{i}_{dag}", disabled=True)
            with cols[3]:
                if available:
                    end = st.time_input(f"", value=pd.to_datetime("16:00").time(), key=f"end_{i}_{dag}")
                    slut_tid[name_input] = end
                else:
                    st.time_input("", value=pd.to_datetime("16:00").time(), key=f"end_{i}_{dag}", disabled=True)
            st.markdown("<div class='day-separator'></div>", unsafe_allow_html=True)

    for idx in sorted(remove_indices, reverse=True):
        st.session_state.people.pop(idx)
        namn.pop(idx)
        dag_tillgang.pop(namn[idx], None)

# --- COLORS ---
default_colors = [
    "#FF9999","#99CCFF","#FFCC99","#99FF99","#FFCCFF",
    "#CCCCFF","#FFFF99","#FF9966","#66CC99"
]
farger = {n: default_colors[i % len(default_colors)] for i, n in enumerate(namn)}
farger["Ingen tillgänglig"] = "#E0E0E0"

# --- SCHEMA GENERATOR ---
def skapa_schema():
    schema = {f"Vecka {v+1}": {dag:{} for dag in veckodagar} for v in range(antal_veckor)}
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
                    and dag_tillgang[n].get(dag, True)
                    and start_tid[n] <= pd.to_datetime(pass_time).time() < slut_tid[n]
                ]

                if tillgangliga:
                    min_pass = min(pass_raknare[n] for n in tillgangliga)
                    candidates = [n for n in tillgangliga if pass_raknare[n] == min_pass]
                    vald = random.choice(candidates)
                    daily_count[vald] += 1
                    pass_raknare[vald] += 1
                else:
                    vald = "Ingen tillgänglig"

                schema[f"Vecka {vecka+1}"][dag][p] = vald
    return schema

# --- GENERATE SCHEDULE ---
if st.button("Generera schema"):
    schema = skapa_schema()
    cell_width = 100 / pass_per_day

    for vecka, dagar in schema.items():
        st.subheader(vecka)
        week_pass_count = {n:0 for n in namn}
        week_minutes = {n:0 for n in namn}

        for dag, passes in dagar.items():
            html = f"<h5>{dag}</h5><table style='border-collapse:collapse;width:100%;table-layout:fixed;'>"
            html += "<tr>"
            for pt in st.session_state.pass_times_display:
                html += f"<td style='border:1px solid white;background:#28a745;color:black;text-align:center;font-size:12px'>{pt}</td>"
            html += "</tr><tr>"
            for i in range(pass_per_day):
                person = passes[f"Pass {i+1}"]
                color = farger.get(person,"white")
                strike_class = ""
                if person != "Ingen tillgänglig" and not dag_tillgang.get(person, {}).get(dag, True):
                    strike_class = "strike"
                html += f"<td style='border:1px solid white;background:{color};text-align:center;height:60px' class='{strike_class}'>{person}</td>"

                if person != "Ingen tillgänglig" and strike_class == "":
                    start = pd.to_datetime(st.session_state.pass_times_display[i].split("–")[0])
                    end = pd.to_datetime(st.session_state.pass_times_display[i].split("–")[1])
                    week_pass_count[person] += 1
                    week_minutes[person] += int((end-start).total_seconds()/60)

            html += "</tr></table>"
            st.markdown(html, unsafe_allow_html=True)

        with st.expander("📊 Veckosummering", expanded=False):
            summary_html = "<table style='border-collapse:collapse;width:60%;'>"
            summary_html += "<tr><th>Person</th><th>Pass</th><th>Tid</th></tr>"
            for n in namn:
                h, m = divmod(week_minutes[n], 60)
                summary_html += f"<tr><td>{n}</td><td>{week_pass_count[n]}</td><td>{h:02d}:{m:02d}</td></tr>"
            summary_html += "</table>"
            st.markdown(summary_html, unsafe_allow_html=True)

    # --- EXCEL EXPORT ---
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet("Schema")
        writer.sheets["Schema"] = worksheet

        header_format = workbook.add_format({
            "bold": True,
            "border": 1,
            "align": "center"
        })

        format_dict = {
            person: workbook.add_format({
                "bg_color": color,
                "border": 1,
                "align": "center",
                "valign": "vcenter"
            })
            for person, color in farger.items()
        }

        worksheet.write(0,0,"Dag",header_format)
        for i in range(pass_per_day):
            worksheet.write(0,i+1,st.session_state.pass_times_display[i],header_format)
            worksheet.set_column(i+1,i+1,18)

        row = 1
        for vecka, dagar in schema.items():
            worksheet.write(row,0,vecka)
            row += 1
            for dag, passes in dagar.items():
                worksheet.write(row,0,dag)
                for i in range(pass_per_day):
                    person = passes[f"Pass {i+1}"]
                    worksheet.write(
                        row,
                        i+1,
                        person,
                        format_dict.get(person)
                    )
                row += 1
            row += 1

    st.download_button(
        label="⬇️ Ladda ner schemat som Excel",
        data=output.getvalue(),
        file_name="schema.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )