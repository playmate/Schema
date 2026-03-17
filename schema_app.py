pass_times = []
prev_end = start_day

if manual_times:
    st.markdown("**Justera passens tider manuellt:**")
    
    # För varje pass: inputfält för start och slut
    for i in range(pass_per_day):
        cols = st.columns([0.2, 0.4, 0.4])  # Passnamn, start, slut
        with cols[0]:
            st.markdown(f"**Pass {i+1}**")
        with cols[1]:
            start_input = st.time_input(
                "", value=prev_end.time(), key=f"start_pass_{i}"
            )
        with cols[2]:
            end_input = st.time_input(
                "", value=(prev_end + pd.Timedelta(minutes=pass_langd)).time(), key=f"end_pass_{i}"
            )

        start_dt = pd.to_datetime(start_input.strftime("%H:%M"))
        end_dt = pd.to_datetime(end_input.strftime("%H:%M"))

        # Säkerställ att tiderna är i ordning
        if start_dt < prev_end:
            start_dt = prev_end
        if end_dt <= start_dt:
            end_dt = start_dt + pd.Timedelta(minutes=pass_langd)

        prev_end = end_dt
        pass_times.append((start_dt, end_dt))

    # Skapa passnamn + klockslag i en flexbox-tabell, med samma höjd
    st.markdown("<div style='display:flex; gap:2px;'>", unsafe_allow_html=True)
    for i, (s, e) in enumerate(pass_times):
        st.markdown(f"""
        <div style='flex:1; border:1px solid #ccc; text-align:center; padding:5px;'>
            <div style='font-weight:bold;'>{f"Pass {i+1}"}</div>
            <div>{s.time().strftime('%H:%M')}–{e.time().strftime('%H:%M')}</div>
        </div>
        """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
