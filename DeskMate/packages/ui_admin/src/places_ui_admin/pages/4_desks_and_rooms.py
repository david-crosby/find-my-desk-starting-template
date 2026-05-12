import pandas as pd
import streamlit as st
from places_core.streamlit_auth import require_login

from places_ui_admin.api_client import (
    add_desk_monitor,
    get_desk_monitors,
    list_buildings,
    list_desks,
    list_floors,
    list_places_sensor_devices,
    list_rooms,
    list_sections,
    remove_desk_monitor,
    sync_monitor_to_places,
    toggle_desk,
)

st.set_page_config(page_title="Desks & Rooms — DeskMate Admin", layout="wide")
require_login()
st.title("Desks & Rooms")

tab1, tab2, tab3 = st.tabs(["Desks", "Rooms", "Peripheral Monitors"])

# ── Tab 1: Desks ──────────────────────────────────────────────────────────────

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

# ── Tab 2: Rooms ──────────────────────────────────────────────────────────────

with tab2:
    rooms = list_rooms()
    if not rooms:
        st.info("No rooms configured.")
    else:
        df = pd.DataFrame(rooms)[["id", "name", "capacity", "floor_id", "is_active"]]
        st.dataframe(df, use_container_width=True, hide_index=True)

# ── Tab 3: Peripheral Monitors ────────────────────────────────────────────────

with tab3:
    st.subheader("Peripheral Monitor Registration")
    st.caption(
        "Register the Microsoft Places device IDs of monitors attached to desks. "
        "When a user connects to a registered monitor, DeskMate automatically checks "
        "them in and handles wrong-desk situations. Each desk supports up to 2 monitors."
    )

    try:
        buildings = list_buildings()
    except Exception as exc:
        st.error(f"Could not load buildings. ({exc})")
        st.stop()

    if not buildings:
        st.info("No buildings configured.")
        st.stop()

    # ── Desk selector ─────────────────────────────────────────────────────────
    sel_col1, sel_col2, sel_col3 = st.columns(3)

    with sel_col1:
        selected_building = st.selectbox(
            "Building",
            buildings,
            format_func=lambda b: b["name"],
            key="mon_building",
        )

    floors = list_floors(building_id=selected_building["id"]) if selected_building else []
    with sel_col2:
        selected_floor = st.selectbox(
            "Floor",
            floors,
            format_func=lambda f: f.get("name") or f"Floor {f['number']}",
            key="mon_floor",
        )

    sections = list_sections(floor_id=selected_floor["id"]) if selected_floor else []
    with sel_col3:
        selected_section = st.selectbox(
            "Section",
            sections,
            format_func=lambda s: s.get("zone_label") or s["name"],
            key="mon_section",
        )

    # Desks in selected section
    section_desks = (
        [d for d in list_desks() if d["section_id"] == selected_section["id"]]
        if selected_section else []
    )

    if not section_desks:
        st.info("No desks in this section.")
    else:
        st.divider()
        for desk in section_desks:
            with st.container(border=True):
                h1, h2 = st.columns([3, 1])
                with h1:
                    st.markdown(f"**{desk['label']}**")

                try:
                    monitors = get_desk_monitors(desk["id"])
                except Exception:
                    monitors = []

                # Show existing monitors
                _SENSOR_TYPES = ["badge", "occupancy", "peopleCount", "heartbeat", "infrared", "ipAddress", "wifi"]

                if monitors:
                    for mon in monitors:
                        m1, m2, m3, m4 = st.columns([1, 3, 1, 1])
                        m1.caption(f"Monitor {mon['position']}")
                        m2.code(mon["device_id"], language=None)
                        meta = []
                        if mon.get("label"):
                            meta.append(mon["label"])
                        if mon.get("sensor_type"):
                            meta.append(mon["sensor_type"])
                        if mon.get("manufacturer"):
                            meta.append(mon["manufacturer"])
                        if meta:
                            m2.caption("  ·  ".join(meta))
                        synced = mon.get("places_synced", False)
                        if synced:
                            m3.success("Synced", icon="✅")
                        else:
                            if m3.button("Sync →\nPlaces", key=f"sync_mon_{mon['id']}"):
                                try:
                                    result = sync_monitor_to_places(mon["id"])
                                    if result.get("success"):
                                        st.success("Registered in MS Places.")
                                    elif result.get("demo_mode"):
                                        st.info(result.get("message", "Demo mode — sync skipped."))
                                    else:
                                        st.error(f"Sync failed: {result.get('error')}")
                                    st.rerun()
                                except Exception as exc:
                                    st.error(f"Could not sync. ({exc})")
                        if m4.button("Remove", key=f"rm_mon_{mon['id']}", type="secondary"):
                            try:
                                remove_desk_monitor(mon["id"])
                                st.rerun()
                            except Exception as exc:
                                st.error(f"Could not remove monitor. ({exc})")
                else:
                    st.caption("No monitors registered.")

                # Add monitor form (only if < 2 registered)
                if len(monitors) < 2:
                    with st.expander(f"Add monitor to {desk['label']}"):
                        fa1, fa2 = st.columns(2)
                        new_device_id = fa1.text_input(
                            "Device ID",
                            key=f"dev_id_{desk['id']}",
                            help="The serial number or device ID. Must match what MS Places uses for this device.",
                            placeholder="e.g. MON-SERIAL-12345",
                        )
                        new_label = fa2.text_input(
                            "Label (optional)",
                            key=f"dev_lbl_{desk['id']}",
                            placeholder="e.g. Left monitor",
                        )
                        fb1, fb2, fb3 = st.columns(3)
                        new_sensor_type = fb1.selectbox(
                            "Sensor type",
                            _SENSOR_TYPES,
                            key=f"dev_stype_{desk['id']}",
                            help="'badge' is correct for monitor/peripheral check-in.",
                        )
                        new_mac = fb2.text_input(
                            "MAC address (optional)",
                            key=f"dev_mac_{desk['id']}",
                            placeholder="AA:BB:CC:DD:EE:FF",
                        )
                        new_manufacturer = fb3.text_input(
                            "Manufacturer (optional)",
                            key=f"dev_mfr_{desk['id']}",
                            placeholder="e.g. Dell, LG",
                        )
                        reg_col, sync_col = st.columns(2)
                        if reg_col.button("Register in DeskMate", key=f"add_mon_{desk['id']}"):
                            if not new_device_id.strip():
                                st.warning("Device ID is required.")
                            else:
                                try:
                                    add_desk_monitor(
                                        desk["id"],
                                        new_device_id.strip(),
                                        new_label.strip() or None,
                                        sensor_type=new_sensor_type,
                                        mac_address=new_mac.strip() or None,
                                        manufacturer=new_manufacturer.strip() or None,
                                    )
                                    st.success(f"Monitor registered for {desk['label']}.")
                                    st.rerun()
                                except Exception as exc:
                                    st.error(f"Could not register monitor. ({exc})")
                        sync_col.caption("After registering, use the **Sync → Places** button to push to MS Places.")

    # ── Browse MS Places registered devices ──────────────────────────────────
    st.divider()
    with st.expander("Browse MS Places registered devices"):
        st.caption(
            "Devices already registered in the Microsoft Places workplace sensor database. "
            "Use this to discover existing hardware and cross-check with DeskMate registrations."
        )
        if st.button("Load from MS Places", key="load_places_devices"):
            try:
                result = list_places_sensor_devices()
                if result.get("demo_mode"):
                    st.info(result.get("message", "MS Places integration is disabled."))
                elif result.get("success"):
                    devices = result.get("devices", [])
                    if not devices:
                        st.info("No devices registered in MS Places.")
                    else:
                        import pandas as pd
                        rows = [
                            {
                                "Device ID": d.get("deviceId", ""),
                                "Display Name": d.get("displayName", ""),
                                "Sensor Type": d.get("sensorType", ""),
                                "MAC": d.get("macAddress", ""),
                                "Manufacturer": (d.get("manufacturer") or {}).get("displayName", ""),
                            }
                            for d in devices
                        ]
                        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
                else:
                    st.error(f"Could not load: {result.get('error')}")
            except Exception as exc:
                st.error(f"Error loading MS Places devices. ({exc})")
