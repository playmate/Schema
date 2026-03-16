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
</style>
""", unsafe_allow_html=True)

# --- SCHEDULE SETTINGS ---
with st.expander("⚙️ Schemainställningar", expanded=True):
    col1, col2 = st.columns([1,1])
    with col1:
        start_day_time = st.time_input("Starttid", value=pd.to_datetime("08:00").time(),
                                       help="När arbetsdagen börjar")
    with col2:
        end_day_time = st.time_input("Sluttid", value=pd.to_datetime("16:00").time(),
                                     help="När arbetsdagen slutar")

    col3, col4 = st.columns([1,1])
    with col3:
        pass_per_day = st.number_input("Pass per dag", min_value=1, value=8, step=1,
                                       help="Hur många pass ska schemaläggas per dag")
    with col4:
        max_pass_per_person_per_day = st.number_input(
            "Max antal pass per person per dag:", min_value=1, value=2, step=1,
            help="Max antal pass en person kan få per dag"
        )

    antal_veckor = st.number_input("Schema för # antal veckor", min_value=1, value=4, step=1,
                                   help="Hur många veckor schemat ska genereras för")

    start_day = pd.to_datetime(start_day_time.strftime("%H:%M"))
    end_day = pd.to_datetime(end_day_time.strftime("%H:%M"))
    total_minutes = int((end_day - start_day).total_seconds() / 60)
    pass_langd = total_minutes // pass_per_day
    st.text(f"Passlängd: {pass_langd} min")

    manual_times = st.checkbox("Justera passens start & sluttid manuellt",
                               help="Kryssa i om du vill skriva egna tider för varje pass")
    if manual_times:
        if "pass_times_manual" not in st.session_state:
            st.session_state.pass_times_manual = [
                start_day + pd.Timedelta(minutes=i*pass_langd) for i in range(pass_per_day)
            ]
        pass_times_display = []
        for i in range(pass_per_day):
            cols = st.columns([1,1])
            pt_start = cols[0].time_input(f"Pass {i+1} start", value=st.session_state.pass_times_manual[i].time())
            pt_end = cols[1].time_input(
                f"Pass {i+1} end", value=(st.session_state.pass_times_manual[i]+pd.Timedelta(minutes=pass_langd)).time()
            )
            st.session_state.pass_times_manual[i] = pd.to_datetime(pt_start.strftime("%H:%M"))
            pass_times_display.append(f"{pt_start.strftime('%H:%M')}–{pt_end.strftime('%H:%M')}")
        st.session_state.pass_times_display = pass_times_display
    else:
        st.session_state.pass_times_display = [
            f"{(start_day + pd.Timedelta(minutes=i*pass_langd)).time().strftime('%H:%M')}–"
            f"{(start_day + pd.Timedelta(minutes=(i+1)*pass_langd)).time().strftime('%H:%M')}"
            for i in range(pass_per_day)
        ]

# --- PERSONAL SECTION ---
with st.expander("👤 Personal", expanded=False):
    if "people" not in st.session_state:
        st.session_state.people = [f"P{i+1}" for i in range(9)]

    new_people_list = []
    for i, n in enumerate(st.session_state.people):
        cols = st.columns([3,2,2,0.5])
        name_input = cols[0].text_input("Namn", value=n, key=f"name_{i}")
        start_time = cols[1].time_input("Börjar jobba", value=pd.to_datetime("08:00").time(), key=f"start_{i}")
        end_time = cols[2].time_input("Slutar jobba", value=pd.to_datetime("16:00").time(), key=f"slut_{i}")
        with cols[3]:
            remove = st.button("❌", key=f"remove_{i}", help="Ta bort person")
        if not remove:
            new_people_list.append(name_input)

    st.session_state.people = new_people_list
    namn = st.session_state.people

    if "start_tid" not in st.session_state:
        st.session_state.start_tid = {n: pd.to_datetime("08:00").time() for n in namn}
    if "slut_tid" not in st.session_state:
        st.session_state.slut_tid = {n: pd.to_datetime("16:00").time() for n in namn}

    for n in namn:
        st.session_state.start_tid[n] = st.session_state.start_tid.get(n, pd.to_datetime("08:00").time())
        st.session_state.slut_tid[n] = st.session_state.slut_tid.get(n, pd.to_datetime("16:00").time())

    start_tid = st.session_state.start_tid
    slut_tid = st.session_state.slut_tid

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("Lägg till person"):
        st.session_state.people.append(f"Namn {len(st.session_state.people)+1}")

# --- GENERAL PARAMETERS ---
veckodagar = ["Måndag","Tisdag","Onsdag","Torsdag","Fredag"]
totalt_pass_per_person = len(veckodagar) * pass_per_day * antal_veckor

# --- COLORS ---
default_colors = ["#FF9999","#99CCFF","#FFCC99","#99FF99","#FFCCFF","#CCCCFF","#FFFF99","#FF9966","#66CC99"]
farger = {n: default_colors[i % len(default_colors)] for i,n in enumerate(namn)}
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

# --- EXPLANATION SECTION ---
with st.expander("ℹ️ Information", expanded=False):
    st.markdown("""

Genereras för att vara så rättvist som möjligt och efter kriterierna att:  
   - Passet hamnar inom personens arbetstider 
   - Personen inte redan har max antal pass per dag  
   - Personen inte fick samma föregående dag  
   - Försöker att frånkomma för många första/sista-pass på samma person så mycket som möjligt
   - Om flera personer är tillgängliga så väljs en med minst antal pass  

""")

# --- SUMMARY BOX ---
st.markdown("---")
st.markdown(
    f"**📌 Snabbcheck:** {len(namn)} personer, {pass_per_day} pass per dag, "
    f"{antal_veckor} veckor → totalt {totalt_pass_per_person} pass.  \n"
    f"Arbetstid: {start_day_time.strftime('%H:%M')}–{end_day_time.strftime('%H:%M')} "
    f"({pass_langd} min/pass). Max {max_pass_per_person_per_day} pass/person/dag."
)

# --- GENERATE SCHEDULE ---
if st.button("Generera schema", key="generate_schedule"):
    schema = skapa_schema()
    cell_width = 100 / pass_per_day

    # --- DISPLAY SCHEDULE ---
    for vecka, dagar in schema.items():
        st.subheader(vecka)
        for dag, passes in dagar.items():
            html = f"<h5>{dag}</h5><table style='border-collapse:collapse;width:100%;table-layout:fixed;'>"
            html += "<tr>"
            for pt in st.session_state.pass_times_display:
                html += (
                    f"<td style='border:1px solid black;width:{cell_width}%;height:25px;"
                    f"padding:2px;text-align:center;font-size:12px;"
                    f"background-color:#28a745;color:white;vertical-align:middle;'>{pt}</td>"
                )
            html += "</tr>"
            html += "<tr>"
            for p_idx in range(pass_per_day):
                p = f"Pass {p_idx+1}"
                person = passes[p]
                color = farger.get(person, "#FFFFFF")
                html += (
                    f"<td style='border:1px solid black;width:{cell_width}%;height:60px;padding:4px;"
                    f"background-color:{color};color:black;text-align:center;vertical-align:middle;"
                    f"word-wrap:break-word;overflow:hidden;font-size:14px;'>{person}</td>"
                )
            html += "</tr></table>"
            st.markdown(html, unsafe_allow_html=True)

    # --- COLOR LEGEND ---
    legend_html = "<p><b>Färger:</b> "
    for n in namn:
        legend_html += f"<span style='background-color:{farger[n]};padding:3px 6px;margin-right:4px;border-radius:3px;'>{n}</span>"
    st.markdown(legend_html, unsafe_allow_html=True)

    # --- COUNT PASSES PER PERSON ---
    pass_count = {n: 0 for n in namn}
    pass_minutes = {n: 0 for n in namn}

    for vecka, dagar in schema.items():
        for dag, passes in dagar.items():
            for i in range(pass_per_day):
                person = passes[f"Pass {i+1}"]
                if person != "Ingen tillgänglig":
                    pass_count[person] += 1
                    start_min = pd.to_datetime(st.session_state.pass_times_display[i].split("–")[0])
                    end_min = pd.to_datetime(st.session_state.pass_times_display[i].split("–")[1])
                    pass_minutes[person] += int((end_min - start_min).total_seconds() / 60)

    # --- DISPLAY PASS SUMMARY ---
    summary_html = "<p><b>📊 Pass per person:</b> "
    for n in namn:
        hours, minutes = divmod(pass_minutes[n], 60)
        summary_html += f"<span style='margin-right:10px;'>{n} ({pass_count[n]} pass, {hours:02d}:{minutes:02d} h)</span>"
    st.markdown(summary_html, unsafe_allow_html=True)

    # --- EXCEL EXPORT ---
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet("Schema")
        writer.sheets["Schema"] = worksheet
        format_dict = {person: workbook.add_format({
            "bg_color": color, "align":"center","valign":"vcenter",
            "border":1,"text_wrap":True
        }) for person,color in farger.items()}
        header_format = workbook.add_format({"bold":True,"border":1,"align":"center"})
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
                    worksheet.write(row,i+1,person,format_dict.get(person))
                row += 1
            row += 1
    st.download_button(
        label="⬇️ Ladda ner schemat som Excel",
        data=output.getvalue(),
        file_name="schema.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
