import streamlit as st

from places_ui_admin.api_client import list_buildings, list_desks, list_floors, list_rooms

st.set_page_config(page_title="Floor Plan", page_icon="🗺️", layout="wide")
from places_core.streamlit_auth import require_login
require_login()
st.title("Floor Plan")

locations = list_buildings()
if not locations:
    st.info("No buildings configured. Add one via the API or seed script.")
    st.stop()

loc_map = {loc["name"]: loc["id"] for loc in locations}
selected_loc = st.selectbox("Building", list(loc_map.keys()))
loc_id = loc_map[selected_loc]

floors = list_floors(building_id=loc_id)
if not floors:
    st.info("No floors for this location.")
    st.stop()

floor_labels = {
    f"Floor {f['number']}{' — ' + f['name'] if f.get('name') else ''}": f["id"] for f in floors
}
selected_floor = st.selectbox("Floor", list(floor_labels.keys()))
floor_id = floor_labels[selected_floor]

col1, col2 = st.columns(2)

with col1:
    st.subheader("Desks")
    desks = list_desks(floor_id=floor_id)
    if desks:
        for d in desks:
            status = "Active" if d["is_active"] else "Inactive"
            st.write(f"- **{d['label']}** — {status}")
    else:
        st.info("No desks on this floor.")

with col2:
    st.subheader("Rooms")
    rooms = list_rooms(floor_id=floor_id)
    if rooms:
        for r in rooms:
            st.write(f"- **{r['name']}** — capacity {r['capacity']}")
    else:
        st.info("No rooms on this floor.")
