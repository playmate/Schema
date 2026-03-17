import streamlit as st 
import pandas as pd
import random
from io import BytesIO

st.set_page_config(page_title="Schemagenerator", layout="wide")
st.title("📅 Generera schema")

# --- CSS Styling ---
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
.lunch-cell {
    background-color: #E0E0E0 !important;
    background-image: repeating-linear-gradient(
        45deg,
        #E0E0E0,
        #E0E0E0 5px,
        #C0C0C0 5px,
        #C0C0C0 10px
    );
    color: black !important;
    font-weight: bold;
    text-align: center;
    height: 60px;
}
</style>
""", unsafe_allow_html=True)

# --- SCHEDULE SETTINGS ---
with st.expander("⚙️ Schemainställningar", expanded=True):

    # --- Arbetstid ---
    st.markdown("""<div style='font-weight:bold;margin-bottom:0px;'>Arbetstid</div>""", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        start_day_time = st.time_input("", value=pd.to_datetime("08:00").time(), step=900)
    with col2:
        end_day_time = st.time_input("", value=pd.to_datetime("16:00").time(), step=900)

    # --- Lunch ---
    lunch_enabled = st.checkbox("Lunchrast - (obemannad tid)")
    lunch_start = lunch_end = None
    if lunch_enabled:
        col3, col4 = st.columns(2)
        with col3:
            lunch_start = st.time_input("Start", value=pd.to_datetime("12:00").time(), step=900)
        with col4:
            lunch_end = st.time_input("Slut", value=pd.to_datetime("12:30").time(), step=900)
            
    st.markdown("<hr style='border:1px solid #e0e0e0;margin-top:8px;margin-bottom:8px;'>", unsafe_allow_html=True)

    # --- Manual passtid direkt under lunch ---
    manual_times = st.checkbox("Justera passens tider manuellt")

    # --- Diskret linje efter lunchtid ---
    st.markdown("<hr style='border:1px solid #e0e0e0;margin-top:8px;margin-bottom:8px;'>", unsafe_allow_html=True)

    # --- Passinställningar ---
    col5, col6 = st.columns(2)
    with col5:
        pass_per_day = st.number_input("Pass per dag", min_value=1, value=8)
    with col6:
        max_pass_per_person_per_day = st.number_input(
            "Max antal pass per person per dag",
            min_value=1,
            value=2
        )

    antal_veckor = st.number_input("Schema för antal veckor", min_value=1, value=4)

    start_day = pd.to_datetime(start_day_time.strftime("%H:%M"))
    end_day = pd.to_datetime(end_day_time.strftime("%H:%M"))

    # --- Beräkna pass före och efter lunch ---
    segments = []
    if lunch_enabled:
        lunch_start_dt = pd.to_datetime(lunch_start.strftime("%H:%M"))
        lunch_end_dt = pd.to_datetime(lunch_end.strftime("%H:%M"))
        pre_lunch_minutes = int((lunch_start_dt - start_day).total_seconds() / 60)
        post_lunch_minutes = int((end_day - lunch_end_dt).total_seconds() / 60)
        pre_pass = max(1, round(pass_per_day * pre_lunch_minutes / (pre_lunch_minutes + post_lunch_minutes)))
        post_pass = pass_per_day - pre_pass
        segments.append((start_day, lunch_start_dt, pre_pass))
        segments.append((lunch_start_dt, lunch_end_dt, 0))  # lunch
        segments.append((lunch_end_dt, end_day, post_pass))
    else:
        segments.append((start_day, end_day, pass_per_day))

    # --- Beräkna initiala pass-tider ---
    pass_times = []
    pass_index = 0
    for seg_start, seg_end, seg_pass in segments:
        if seg_pass == 0:
            pass_times.append(("Lunch", seg_start, seg_end))
            continue
        total_minutes = int((seg_end - seg_start).total_seconds() / 60)
        pass_length = total_minutes // seg_pass
        current_start = seg_start
        for i in range(seg_pass):
            current_end = current_start + pd.Timedelta(minutes=pass_length)
            pass_times.append((f"Pass {pass_index+1}", current_start, current_end))
            current_start = current_end
            pass_index += 1

    # --- Manuell justering ---
    if manual_times:
        st.markdown("### Manuella passtider")
        new_pass_times = []
        for i, (name, s, e) in enumerate(pass_times):
            cols = st.columns([1,1])
            with cols[0]:
                new_start = st.time_input(f"{name} start", value=s.time(), key=f"manual_start_{i}", step=900)
            with cols[1]:
                new_end = st.time_input(f"{name} slut", value=e.time(), key=f"manual_end_{i}", step=900)
            new_pass_times.append((name, pd.to_datetime(new_start.strftime("%H:%M")), pd.to_datetime(new_end.strftime("%H:%M"))))
        pass_times = new_pass_times

    # --- Endast klockslag i display ---
    st.session_state.pass_times_display = [
        f"{s.time().strftime('%H:%M')}–{e.time().strftime('%H:%M')}" for name, s, e in pass_times
    ]

# --- PERSONAL ---
veckodagar = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag"]

if "people" not in st.session_state:
    st.session_state.people = [f"P{i+1}" for i in range(9)]
if "dag_tillgang" not in st.session_state:
    st.session_state.dag_tillgang = {n: {dag: True for dag in veckodagar} for n in st.session_state.people}
if "work_times" not in st.session_state:
    st.session_state.work_times = {n: {dag: (pd.to_datetime("08:00").time(),
                                             pd.to_datetime("16:00").time())
                                      for dag in veckodagar} for n in st.session_state.people}

dag_tillgang = st.session_state.dag_tillgang
work_times = st.session_state.work_times

with st.expander("👤 Personal", expanded=False):
    col_add = st.columns([3,1])
    with col_add[0]:
        ny_person_namn = st.text_input("Lägg till person", "")
    with col_add[1]:
        if st.button("Lägg till"):
            if ny_person_namn and ny_person_namn not in st.session_state.people:
                st.session_state.people.append(ny_person_namn)
                st.session_state.dag_tillgang[ny_person_namn] = {dag: True for dag in veckodagar}
                st.session_state.work_times[ny_person_namn] = {dag: (pd.to_datetime("08:00").time(),
                                                                    pd.to_datetime("16:00").time())
                                                               for dag in veckodagar}
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
                cols_day = st.columns([0.1, 1, 0.5, 0.5])
                with cols_day[0]:
                    tillgang = st.checkbox("", value=dag_tillgang[n][dag], key=f"available_{n}_{dag}")
                    dag_tillgang[n][dag] = tillgang
                with cols_day[1]:
                    st.markdown(f"**{dag}**" if tillgang else f"<span class='strike'>{dag}</span>", unsafe_allow_html=True)
                start_prev, end_prev = work_times[n][dag]
                with cols_day[2]:
                    start_time = st.time_input("", value=start_prev, key=f"start_{n}_{dag}", disabled=not tillgang, step=900)
                with cols_day[3]:
                    end_time = st.time_input("", value=end_prev, key=f"end_{n}_{dag}", disabled=not tillgang, step=900)
                if tillgang:
                    work_times[n][dag] = (start_time, end_time)

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
farger["Lunch"] = "#E0E0E0"

# --- SCHEMA GENERATOR ---
def skapa_schema():
    schema = {f"Vecka {v+1}": {dag:{} for dag in veckodagar} for v in range(antal_veckor)}
    pass_raknare = {n:0 for n in st.session_state.people}

    for vecka in range(antal_veckor):
        for dag in veckodagar:
            daily_count = {n:0 for n in st.session_state.people}
            prev_person = None

            for name, start_dt, end_dt in pass_times:
                if name == "Lunch":
                    schema[f"Vecka {vecka+1}"][dag][name] = "Lunch"
                    continue

                tillgangliga = [
                    n for n in st.session_state.people
                    if daily_count[n] < max_pass_per_person_per_day
                    and dag_tillgang[n].get(dag, True)
                    and work_times[n][dag][0] <= start_dt.time() < work_times[n][dag][1]
                ]

                if prev_person in tillgangliga and len(tillgangliga) > 1:
                    tillgangliga.remove(prev_person)

                if tillgangliga:
                    min_pass = min(pass_raknare[n] for n in tillgangliga)
                    candidates = [n for n in tillgangliga if pass_raknare[n] == min_pass]
                    vald = random.choice(candidates)
                    daily_count[vald] += 1
                    pass_raknare[vald] += 1
                else:
                    vald = "Ingen tillgänglig"

                schema[f"Vecka {vecka+1}"][dag][name] = vald
                prev_person = vald

    return schema

# --- GENERATE SCHEDULE ---
if st.button("Generera schema"):
    schema = skapa_schema()

    total_week_pass_count = {n:0 for n in st.session_state.people}
    total_week_minutes = {n:0 for n in st.session_state.people}

    for vecka, dagar in schema.items():
        st.subheader(vecka)
        week_pass_count = {n:0 for n in st.session_state.people}
        week_minutes = {n:0 for n in st.session_state.people}

        for dag, passes in dagar.items():
            html = f"<h5>{dag}</h5><table style='border-collapse:collapse;width:100%;table-layout:fixed;'>"
            html += "<tr>"
            for pt in st.session_state.pass_times_display:
                html += f"<td style='border:1px solid white;background:#28a745;color:black;text-align:center;font-size:12px'>{pt}</td>"
            html += "</tr><tr>"
            for name, start_dt, end_dt in pass_times:
                person = passes[name if name != "Lunch" else "Lunch"]
                if name == "Lunch":
                    html += f"<td class='lunch-cell'>{person}</td>"
                else:
                    color = farger.get(person,"white")
                    strike_class = ""
                    if person != "Ingen tillgänglig" and not dag_tillgang.get(person, {}).get(dag, True):
                        strike_class = "strike"
                    html += f"<td style='border:1px solid white;background:{color};color:black;text-align:center;height:60px;font-weight:bold;' class='{strike_class}'>{person}</td>"

                    if person != "Ingen tillgänglig" and strike_class == "":
                        week_pass_count[person] += 1
                        week_minutes[person] += int((end_dt - start_dt).total_seconds()/60)

            html += "</tr></table>"
            st.markdown(html, unsafe_allow_html=True)

        with st.expander("📊 Veckosummering", expanded=False):
            summary_html = "<table style='border-collapse:collapse;width:60%;'>"
            summary_html += "<tr><th>Person</th><th>Pass</th><th>Tid</th></tr>"
            for n in st.session_state.people:
                h, m = divmod(week_minutes[n], 60)
                summary_html += f"<tr><td>{n}</td><td>{week_pass_count[n]}</td><td>{h:02d}:{m:02d}</td></tr>"
                total_week_pass_count[n] += week_pass_count[n]
                total_week_minutes[n] += week_minutes[n]
            summary_html += "</table>"
            st.markdown(summary_html, unsafe_allow_html=True)

    if antal_veckor > 1:
        st.markdown("### 📊 Totalsummering över alla veckor")
        total_html = "<table style='border-collapse:collapse;width:60%;'>"
        total_html += "<tr><th>Person</th><th>Pass</th><th>Tid</th></tr>"
        for n in st.session_state.people:
            h, m = divmod(total_week_minutes[n], 60)
            total_html += f"<tr><td>{n}</td><td>{total_week_pass_count[n]}</td><td>{h:02d}:{m:02d}</td></tr>"
        total_html += "</table>"
        st.markdown(total_html, unsafe_allow_html=True)

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
        for i, (name, s, e) in enumerate(pass_times):
            if name != "Lunch":
                worksheet.write(0,i+1,f"{s.time().strftime('%H:%M')}–{e.time().strftime('%H:%M')}",header_format)
            else:
                worksheet.write(0,i+1,f"Lunch {s.time().strftime('%H:%M')}–{e.time().strftime('%H:%M')}",header_format)
            worksheet.set_column(i+1,i+1,18)

        row = 1
        for vecka, dagar in schema.items():
            worksheet.write(row,0,vecka)
            row += 1
            for dag, passes in dagar.items():
                worksheet.write(row,0,dag)
                for i, (name, s, e) in enumerate(pass_times):
                    person = passes[name if name != "Lunch" else "Lunch"]
                    worksheet.write(row,i+1,person,format_dict.get(person))
                row += 1
            row += 1

    st.download_button(
        label="⬇️ Ladda ner schemat som Excel",
        data=output.getvalue(),
        file_name="schema.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
