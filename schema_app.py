import streamlit as st
import pandas as pd
import random
from io import BytesIO

st.set_page_config(page_title="Schemagenerator", layout="wide")
st.title("📅 Generera schema")

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
        max_pass_per_person_per_day = st.number_input("Max pass/person/dag", min_value=1, value=2)

    antal_veckor = st.number_input("Antal veckor", min_value=1, value=4)

    start_day = pd.to_datetime(start_day_time.strftime("%H:%M"))
    end_day = pd.to_datetime(end_day_time.strftime("%H:%M"))

    total_minutes = int((end_day - start_day).total_seconds() / 60)
    pass_langd = total_minutes // pass_per_day

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
        st.session_state.people = [f"P{i+1}" for i in range(5)]

    namn = st.session_state.people

    start_tid = {}
    slut_tid = {}
    arbetsdagar = {}

    remove_index = None

    for i, n in enumerate(namn):

        col_card, col_delete = st.columns([10,1])

        with col_card:
            st.markdown(f"""
            <div style='padding:12px;border:1px solid #ddd;border-radius:10px;background:#fafafa'>
            <b>Person {i+1}</b>
            </div>
            """, unsafe_allow_html=True)

        with col_delete:
            if len(namn) > 1:
                if st.button("❌", key=f"delete_{i}"):
                    remove_index = i

        col1, col2, col3 = st.columns([2,1,1])

        with col1:
            name_input = st.text_input("Namn", value=n, key=f"name_{i}")

        with col2:
            start = st.time_input("Börjar", value=pd.to_datetime("08:00").time(), key=f"start_{i}")

        with col3:
            end = st.time_input("Slutar", value=pd.to_datetime("16:00").time(), key=f"end_{i}")

        dag_cols = st.columns(len(veckodagar))
        dagar_val = []

        for d_idx, dag in enumerate(veckodagar):
            with dag_cols[d_idx]:
                if st.checkbox(dag[:3], value=True, key=f"{i}_{dag}"):
                    dagar_val.append(dag)

        namn[i] = name_input
        start_tid[name_input] = start
        slut_tid[name_input] = end
        arbetsdagar[name_input] = dagar_val

        st.markdown("---")

    if remove_index is not None:
        st.session_state.people.pop(remove_index)
        st.rerun()

    if st.button("➕ Lägg till person"):
        st.session_state.people.append(f"P{len(namn)+1}")
        st.rerun()

# --- COLORS ---
colors = ["#FF9999","#99CCFF","#FFCC99","#99FF99","#FFCCFF"]
farger = {n: colors[i % len(colors)] for i, n in enumerate(namn)}
farger["Ingen tillgänglig"] = "#E0E0E0"

# --- ROTATION SCHEMA ---
def skapa_schema():

    schema = {f"Vecka {v+1}": {dag:{} for dag in veckodagar} for v in range(antal_veckor)}

    rotation_index = 0

    for vecka in range(antal_veckor):

        for dag in veckodagar:

            daily_count = {n: 0 for n in namn}

            rotated = namn[rotation_index:] + namn[:rotation_index]

            for p_idx in range(pass_per_day):

                pass_time = st.session_state.pass_times_display[p_idx].split("–")[0]

                tillgangliga = [
                    n for n in rotated
                    if daily_count[n] < max_pass_per_person_per_day
                    and start_tid[n] <= pd.to_datetime(pass_time).time() < slut_tid[n]
                    and dag in arbetsdagar.get(n, veckodagar)
                ]

                if tillgangliga:
                    vald = tillgangliga[0]
                    daily_count[vald] += 1
                else:
                    vald = "Ingen tillgänglig"

                schema[f"Vecka {vecka+1}"][dag][f"Pass {p_idx+1}"] = vald

            rotation_index = (rotation_index + 1) % len(namn)

    return schema

# --- GENERATE ---
if st.button("Generera schema"):

    schema = skapa_schema()

    for vecka, dagar in schema.items():

        st.subheader(vecka)

        for dag, passes in dagar.items():

            html = f"<h5>{dag}</h5><table style='width:100%;border-collapse:collapse;'>"

            html += "<tr>"
            for pt in st.session_state.pass_times_display:
                html += f"<td style='border:1px solid black;background:#28a745;color:white;text-align:center'>{pt}</td>"
            html += "</tr><tr>"

            for i in range(pass_per_day):

                p = passes[f"Pass {i+1}"]
                color = farger.get(p,"white")

                html += f"<td style='border:1px solid black;background:{color};height:60px;text-align:center'>{p}</td>"

            html += "</tr></table>"

            st.markdown(html, unsafe_allow_html=True)

    # --- EXPORT ---
    output = BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:

        workbook = writer.book
        ws = workbook.add_worksheet("Schema")
        writer.sheets["Schema"] = ws

        ws.write(0,0,"Dag")

        for i in range(pass_per_day):
            ws.write(0,i+1,st.session_state.pass_times_display[i])

        row = 1

        for vecka, dagar in schema.items():

            ws.write(row,0,vecka)
            row += 1

            for dag, passes in dagar.items():

                ws.write(row,0,dag)

                for i in range(pass_per_day):
                    ws.write(row,i+1,passes[f"Pass {i+1}"])

                row += 1

            row += 1

    st.download_button("⬇️ Ladda ner Excel", data=output.getvalue(), file_name="schema.xlsx")