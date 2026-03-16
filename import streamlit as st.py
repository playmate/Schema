import streamlit as st
import pandas as pd
import random

st.title("Schemaläggning – Rättvist och färgkodat schema")

# Lista med namn
namn = ["Amanda", "Anna-Karin", "Cecilia", "Elisabeth", 
        "Frida", "Hanna", "Lena", "Marie", "Marja"]

# Definiera färger för varje person
farger = {
    "Amanda": "#FF9999",
    "Anna-Karin": "#99CCFF",
    "Cecilia": "#FFCC99",
    "Elisabeth": "#99FF99",
    "Frida": "#FFCCFF",
    "Hanna": "#CCCCFF",
    "Lena": "#FFFF99",
    "Marie": "#FF9966",
    "Marja": "#66CC99",
    "Ingen tillgänglig": "#E0E0E0"
}

# Låt användaren ange arbetsprocent för varje person
st.subheader("Ange arbetsprocent för varje person:")
arbetsandel = {}
for n in namn:
    arbetsandel[n] = st.slider(f"{n} (%)", 0, 100, 100)

# Veckodagar och pass
veckodagar = ["Måndag", "Tisdag", "Onsdag", "Torsdag", "Fredag"]
pass_per_dag = ["Pass 1", "Pass 2", "Pass 3", "Pass 4"]
totalt_pass = len(veckodagar) * len(pass_per_dag)

# Funktion för att skapa schema rättvist
def skapa_schema():
    schema = {dag: {} for dag in veckodagar}
    
    # Beräkna max antal pass per person baserat på procent
    max_pass_per_person = {n: round(arbetsandel[n]/100 * totalt_pass) for n in namn}
    pass_räknare = {n: 0 for n in namn}

    # Skapa en lista med alla pass
    alla_pass = [(dag, p) for dag in veckodagar for p in pass_per_dag]
    random.shuffle(alla_pass)

    for dag, p in alla_pass:
        # Lista personer som fortfarande kan ta fler pass
        tillgangliga = [n for n in namn if pass_räknare[n] < max_pass_per_person[n]]
        if tillgangliga:
            vald = random.choice(tillgangliga)
            schema[dag][p] = vald
            pass_räknare[vald] += 1
        else:
            schema[dag][p] = "Ingen tillgänglig"
    
    return schema

# Generera schema
if st.button("Generera schema"):
    schema = skapa_schema()
    
    # Visa schemat med färger
    for dag in veckodagar:
        st.subheader(dag)
        # Skapa HTML-tabell med färger
        html = "<table style='border-collapse: collapse; width: 50%;'>"
        html += "<tr><th style='border: 1px solid black; padding:5px;'>Pass</th><th style='border: 1px solid black; padding:5px;'>Person</th></tr>"
        for p, person in schema[dag].items():
            color = farger.get(person, "#FFFFFF")
            html += f"<tr><td style='border: 1px solid black; padding:5px;'>{p}</td>"
            html += f"<td style='border: 1px solid black; padding:5px; background-color:{color};'>{person}</td></tr>"
        html += "</table>"
        st.markdown(html, unsafe_allow_html=True)