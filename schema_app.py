import streamlit as st
import pandas as pd
import random
from io import BytesIO

st.title("Generera schema")

# --- Settings ---
st.subheader("Schemainställningar:")

# --- Schematider ---
st.markdown("**Schematider**")

start_day_time = st.time_input(
    "Starttid",
    value=pd.to_datetime("08:00").time(),
    key="schematid_start"
)
end_day_time = st.time_input(
    "Sluttid",
    value=pd.to_datetime("16:00").time(),
    key="schematid_slut"
)

start_day = pd.to_datetime(start_day_time.strftime("%H:%M"))
end_day = pd.to_datetime(end_day_time.strftime("%H:%M"))

total_minutes = int((end_day - start_day).total_seconds() / 60)

# --- Pass per dag ---
pass_per_day = st.number_input(
    "Pass per dag",
    min_value=1,
    value=8,
    step=1
)

# --- Passlängd (calculated automatically) ---
pass_langd = total_minutes // pass_per_day
st.write(f"Passlängd per pass: **{pass_langd} minuter**")

# --- Max pass per person per day ---
max_pass_per_person_per_day = st.number_input(
    "Max antal pass per person per dag:",
    min_value=1,
    value=2,
    step=1
)

# --- Editable list of people ---
if "people" not in st.session_state:
    st.session_state.people = [
        "P1","P2","P3","P4",
        "P5","P6","P7","P8","P9"
    ]

st.subheader("Hantera personer:")

new_people_list = []

for i,n in enumerate(st.session_state.people):

    cols = st.columns([4,1])

    name_input = cols[0].text_input(
        f"Person {i+1}",
        value=n,
        key=f"name_{i}"
    )

    remove = cols[1].button("X", key=f"remove_{i}")

    if not remove:
        new_people_list.append(name_input)

st.session_state.people = new_people_list

if st.button("Lägg till person"):
    st.session_state.people.append(
        f"Namn {len(st.session_state.people)+1}"
    )

namn = st.session_state.people

# --- Work percentage + hours ---
st.subheader("Arbetsprocent och arbetstider")

arbetsandel = {}
start_tid = {}
slut_tid = {}

for n in namn:

    st.markdown(f"**{n}**")

    arbetsandel[n] = st.slider(
        f"{n} (%)",
        0,
        100,
        100,
        key=f"slider_{n}"
    )

    start_tid[n] = st.time_input(
        f"{n} börjar jobba",
        value=pd.to_datetime("08:00").time(),
        key=f"start_{n}"
    )

    slut_tid[n] = st.time_input(
        f"{n} slutar jobba",
        value=pd.to_datetime("16:00").time(),
        key=f"slut_{n}"
    )

# --- General parameters ---
veckodagar = ["Måndag","Tisdag","Onsdag","Torsdag","Fredag"]
antal_veckor = 4

totalt_pass_per_person = len(veckodagar) * pass_per_day * antal_veckor

# --- Colors ---
default_colors = [
"#FF9999","#99CCFF","#FFCC99","#99FF99",
"#FFCCFF","#CCCCFF","#FFFF99","#FF9966","#66CC99"
]

farger = {n: default_colors[i % len(default_colors)] for i,n in enumerate(namn)}
farger["Ingen tillgänglig"] = "#E0E0E0"

# --- Schedule generator ---
def skapa_schema():

    schema = {
        f"Vecka {v+1}": {dag:{} for dag in veckodagar}
        for v in range(antal_veckor)
    }

    max_pass_per_person = {
        n: round(arbetsandel[n]/100 * totalt_pass_per_person)
        for n in namn
    }

    pass_raknare = {n:0 for n in namn}

    pass_start_times = [
        start_day + pd.Timedelta(minutes=i*pass_langd)
        for i in range(pass_per_day)
    ]

    for vecka in range(antal_veckor):

        used_passes_per_person = {n:set() for n in namn}

        for dag in veckodagar:

            daily_count = {n:0 for n in namn}
            tidigare_pass = schema[f"Vecka {vecka+1}"][dag]

            for p_idx in range(pass_per_day):

                p = f"Pass {p_idx+1}"
                last_person = list(tidigare_pass.values())[-1] if tidigare_pass else None
                pass_time = pass_start_times[p_idx].time()

                tillgangliga = [

                    n for n in namn

                    if daily_count[n] < max_pass_per_person_per_day
                    and n != last_person
                    and p not in used_passes_per_person[n]
                    and pass_raknare[n] < max_pass_per_person[n]
                    and start_tid[n] <= pass_time < slut_tid[n]

                ]

                if tillgangliga:

                    vald = random.choice(tillgangliga)

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
                    f"<td style='"
                    f"border:1px solid white;"
                    f"width:{cell_width}%;"
                    f"height:60px;"
                    f"padding:4px;"
                    f"background-color:{color};"
                    f"color:black;"
                    f"text-align:center;"
                    f"vertical-align:middle;"
                    f"word-wrap:break-word;"
                    f"overflow:hidden;"
                    f"font-size:14px;'>"
                    f"{person}"
                    f"</td>"
                )

            html += "</tr></table>"

            st.markdown(html, unsafe_allow_html=True)

        # Weekly sorted counts
        person_count = {n:0 for n in namn}

        for dag,passes in dagar.items():
            for person in passes.values():
                if person in person_count:
                    person_count[person] += 1

        sorted_counts = sorted(
            person_count.items(),
            key=lambda x:x[1],
            reverse=True
        )

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
                "bg_color": color,
                "align": "center",
                "valign": "vcenter",
                "border": 1,
                "text_wrap": True
            })

        header_format = workbook.add_format({
            "bold": True,
            "border": 1,
            "align": "center"
        })

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