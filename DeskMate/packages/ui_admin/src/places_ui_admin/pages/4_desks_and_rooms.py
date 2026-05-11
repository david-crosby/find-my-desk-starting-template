import pandas as pd
import streamlit as st

from places_ui_admin.api_client import list_desks, list_rooms, toggle_desk

st.set_page_config(page_title="Desks & Rooms", page_icon="🪑", layout="wide")
st.title("Desks & Rooms")

tab1, tab2 = st.tabs(["Desks", "Rooms"])

with tab1:
    desks = list_desks()
    if not desks:
        st.info("No desks configured.")
    else:
        for d in desks:
            col1, col2, col3 = st.columns([3, 2, 1])
            col1.write(f"**{d['label']}** (section {d['section_id']})")
            col2.write("Active" if d["is_active"] else "Inactive")
            if col3.button("Toggle", key=f"desk_{d['id']}"):
                toggle_desk(d["id"])
                st.rerun()

with tab2:
    rooms = list_rooms()
    if not rooms:
        st.info("No rooms configured.")
    else:
        df = pd.DataFrame(rooms)[["id", "name", "capacity", "floor_id", "is_active"]]
        st.dataframe(df, use_container_width=True, hide_index=True)
