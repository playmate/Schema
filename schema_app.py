import streamlit as st
import pandas as pd
import random
from io import BytesIO

st.title("Generera schema")

# --- Settings ---
st.subheader("Schemainställningar:")

# --- Compact row for schedule settings ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    start_day_time = st.time_input("Starttid", value=pd.to_datetime("08:00").time())

with col2:
    end_day_time = st.time_input("Sluttid", value=pd.to_datetime("16:00").time())

with col3:
    pass_per_day = st.number_input("Pass per dag", min_value=1, value=8, step=1)

# Calculate pass length automatically
start_day = pd.to_datetime(start_day_time.strftime("%H:%M"))
end_day = pd.to_datetime(end_day_time.strftime("%H:%M"))
total_minutes = int((end_day - start_day).total_seconds() / 60)
pass_langd = total_minutes // pass_per_day

with col4:
    st.text(f"Passlängd: {pass_langd} min")

# --- Max pass per person per day ---
max_pass_per_person_per_day = st.number_input(
    "Max antal pass per person per dag:",
    min_value=1,
    value=2,
    step=1
)

# --- Personal section (names + working hours) ---
st.subheader("Personal")

if "people" not in st.session_state:
    st.session_state.people = [f"P{i+1}" for i in range(9)]

new_people_list = []

for i, n in enumerate(st.session_state.people):
    st.markdown(f"**Person {i+1}**")
    cols = st.columns([4, 1])
    name_input = cols[0].text_input(f"Namn", value=n, key=f"name_{i}")
    remove = cols[1].button("X", key=f"remove_{i}")

    start_tid = st.time_input(f"{name_input} börjar jobba", value=pd.to_datetime("08:00").time(), key=f"start_{i}")
    slut_tid = st.time_input(f"{name_input} slutar jobba", value=pd.to_datetime("16:00").time(), key=f"slut_{i}")

    if not remove:
        new_people_list.append(name_input)

st.session_state.people = new_people_list
namn = st.session_state.people

if st.button("Lägg till person"):
    st.session_state.people.append(f"Namn {len(st.session_state.people)+1}")

# Store personal start/end times
if "start_tid" not in st.session_state:
    st.session_state.start_tid = {n: pd.to_datetime("08:00").time() for n in namn}
if "slut_tid" not in st.session_state:
    st.session_state.slut_tid = {n: pd.to_datetime("16:00").time() for n in namn}

for n in namn:
    st.session_state.start_tid[n] = st.session_state.start_tid.get(n, pd.to_datetime("08:00").time())
    st.session_state.slut_tid[n] = st.session_state.slut_tid.get(n, pd.to_datetime("16:00").time())

start_tid = st.session_state.start_tid
slut_tid = st.session_state.slut_tid

# --- General parameters ---
veckodagar = ["Måndag","Tisdag","Onsdag","Torsdag","Fredag"]
antal_veckor = 4
totalt_pass_per_person = len(veckodagar) * pass_per_day * antal_veckor

# --- Colors ---
default_colors = [
    "#FF9999","#99CCFF","#FFCC99","#99FF99",
    "#FFCCFF","#CCCCFF","#FFFF99","#FF9966","#66CC99"
]
farger = {n: default_colors[i % len(default_colors)] for i, n in enumerate(namn)}
farger["Ingen tillgänglig"] = "#E0E0E0"

# --- Fair schedule generator ---
def skapa_schema():
    schema = {f"Vecka {v+1}": {dag:{} for dag in veckodagar} for v in range(antal_veckor)}
    pass_raknare = {n:0 for n in namn}  # total assigned passes
    pass_start_times = [start_day + pd.Timedelta(minutes=i*pass_langd) for i in range(pass_per_day)]

    for vecka in range(antal_veckor):
        used_passes_per_person = {n:set() for n in namn}

        for dag in veckodagar:
            daily_count = {n:0 for n in namn}
            tidigare_pass = schema[f"Vecka {vecka+1}"][dag]

            for p_idx in range(pass_per_day):
                p = f"Pass {p_idx+1}"
                last_person = list(tidigare_pass.values())[-1] if tidigare_pass else None
                pass_time = pass_start_times[p_idx].time()

                # Available people based on personal start/end
                tillgangliga = [
                    n for n in namn
                    if daily_count[n] < max_pass_per_person_per_day
                    and n != last_person
                    and p not in used_passes_per_person[n]
                    and start_tid[n] <= pass_time < slut_tid[n]
                ]

                if tillgangliga:
                    # Fair selection: choose person with fewest total passes
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

# --- Generate schedule ---
if st.button("Generera schema"):

    schema = skapa_schema()
    cell_width = 100 / pass_per_day

    for vecka, dagar in schema.items():
        st.subheader(vecka)
        for dag, passes in dagar.items():
            html = f"<h5>{dag}</h5>"
            html += "<table style='border-collapse:collapse;width:100%;table-layout:fixed;'><tr>"

            for p in sorted(passes.keys(), key=lambda x: int(x.split()[1])):
                person = passes[p]
                color = farger.get(person, "#FFFFFF")
                html += (
                    f"<td style='border:1px solid white;width:{cell_width}%;height:60px;"
                    f"padding:4px;background-color:{color};color:black;"
                    f"text-align:center;vertical-align:middle;word-wrap:break-word;"
                    f"overflow:hidden;font-size:14px;'>{person}</td>"
                )

            html += "</tr></table>"
            st.markdown(html, unsafe_allow_html=True)

        # Weekly sorted counts
        person_count = {n:0 for n in namn}
        for dag, passes in dagar.items():
            for person in passes.values():
                if person in person_count:
                    person_count[person] += 1

        sorted_counts = sorted(person_count.items(), key=lambda x:x[1], reverse=True)
        count_html = "<h6>Antal pass per person denna vecka:</h6><table><tr>"
        for name,_ in sorted_counts:
            count_html += f"<th style='border:1px solid black;padding:5px;'>{name}</th>"
        count_html += "</tr><tr>"
        for _,count in sorted_counts:
            count_html += f"<td style='border:1px solid black;padding:5px;text-align:center;'>{count}</td>"
        count_html += "</tr></table>"
        st.markdown(count_html, unsafe_allow_html=True)

    # --- Excel export with colors ---
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        workbook = writer.book
        worksheet = workbook.add_worksheet("Schema")
        writer.sheets["Schema"] = worksheet

        format_dict = {}
        for person, color in farger.items():
            format_dict[person] = workbook.add_format({
                "bg_color": color, "align":"center","valign":"vcenter",
                "border":1,"text_wrap":True
            })

        header_format = workbook.add_format({"bold":True,"border":1,"align":"center"})
        worksheet.write(0,0,"Dag",header_format)
        for i in range(pass_per_day):
            worksheet.write(0,i+1,f"Pass {i+1}",header_format)
            worksheet.set_column(i+1,i+1,18)

        row = 1
        for vecka, dagar in schema.items():
            worksheet.write(row,0,vecka)
            row += 1
            for dag, passes in dagar.items():
                worksheet.write(row,0,dag)
                for i in range(pass_per_day):
                    person = passes[f"Pass {i+1}"]
                    cell_format = format_dict.get(person)
                    worksheet.write(row,i+1,person,cell_format)
                row += 1
            row += 1

    st.download_button(
        label="Ladda ner schemat som Excel",
        data=output.getvalue(),
        file_name="schema.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )