import datetime
import streamlit as st
import pandas as pd
from utils.ui import render_sidebar, require_role, show_success, show_db_error, select_from_rows, time_remaining_badge
from queries.organs import (
    get_organ_types,
    add_organ_type,
    update_organ_type,
    get_consented_donors,
    add_organ,
    get_organs,
    run_expire_organs
)

st.set_page_config(page_title="Organs | Organ Donation", layout="wide")
render_sidebar()
require_role(["Admin", "Doctor", "Hospital Staff"])

is_readonly = (st.session_state.get("role") == "Doctor")

st.title("Organ Management & Live Viability")
st.caption("Log harvested organs, monitor time-sensitive viability countdowns, and manage tissue categories.")

if is_readonly:
    st.info("You are logged in as a **Doctor** (Read-Only Mode). Modifications are disabled.")

# Run automatic expiry check
expired_count = run_expire_organs()
if expired_count > 0:
    st.warning(f"Background sweep: **{expired_count}** perishable organ(s) reached expiration and have been updated to 'expired'.")

organ_types = get_organ_types()
consented_donors = get_consented_donors()

tabs = ["Organ Inventory"]
if not is_readonly:
    tabs = ["Add Harvested Organ", "Organ Inventory", "Organ Types"]

tab_objs = st.tabs(tabs)

# -----------------------------------------------------------------------------
# TAB: Add Organ
# -----------------------------------------------------------------------------
if not is_readonly:
    with tab_objs[0]:
        st.subheader("Register Newly Harvested Organ")
        if not consented_donors:
            st.warning("No donors with legal consent ('given') are available. Please register or update donor consent first.")
        elif not organ_types:
            st.warning("No organ types are defined.")
        else:
            with st.form("add_organ_form"):
                c1, c2 = st.columns(2)
                with c1:
                    donor_id = select_from_rows(
                        "Consented Donor*",
                        consented_donors,
                        "patient_id",
                        lambda r: f"#{r['patient_id']} - {r['name']} ({r['blood_group']}) | Type: {r['donor_type']} ({r['hospital_name']})"
                    )

                    ot_id = select_from_rows(
                        "Organ Type*",
                        organ_types,
                        "organ_type_id",
                        lambda r: f"{r['organ_name']} ({'Storable' if r['viability_hours'] is None else f'Viable: {r['viability_hours']}h'})"
                    )

                    full_or_part = st.selectbox("Specimen Size*", ["full", "part"])

                with c2:
                    h_date = st.date_input("Harvest Date*", value=datetime.date.today(), max_value=datetime.date.today())
                    h_time = st.time_input("Harvest Time*", value=datetime.datetime.now().time())
                    harvest_dt = datetime.datetime.combine(h_date, h_time)

                    description = st.text_area("Specimen Notes", placeholder="Tissue quality, ischemic times, surgeon observations...")

                # Selected organ info badge
                sel_ot = next((ot for ot in organ_types if ot["organ_type_id"] == ot_id), None)
                if sel_ot:
                    if sel_ot["viability_hours"] is not None:
                        st.info(f"**Viability Window:** {sel_ot['viability_hours']} hours from harvest timestamp.")
                    else:
                        st.info("**Cryo / Storable:** No fixed expiration window.")

                if st.form_submit_button("Log Harvested Organ", use_container_width=True):
                    if not donor_id:
                        st.error("Please select a valid donor.")
                    elif not ot_id:
                        st.error("Please select an organ type.")
                    else:
                        try:
                            oid = add_organ(ot_id, donor_id, full_or_part, harvest_dt, description)
                            show_success(f"Organ #{oid} successfully recorded in inventory with status 'available'.")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            show_db_error(e)

# -----------------------------------------------------------------------------
# TAB: Organ Inventory
# -----------------------------------------------------------------------------
inv_idx = 0 if is_readonly else 1
with tab_objs[inv_idx]:
    st.subheader("Organ Inventory & Countdown Monitor")

    fc1, fc2 = st.columns(2)
    with fc1:
        status_opts = ["All", "available", "allocated", "transplanted", "expired"]
        sel_status = st.selectbox("Status Filter", status_opts, index=1)
    with fc2:
        ot_filter_opts = [{"organ_type_id": None, "organ_name": "All Organ Types"}] + organ_types
        sel_ot_filter = select_from_rows(
            "Organ Type Filter",
            ot_filter_opts,
            "organ_type_id",
            lambda r: r["organ_name"]
        )

    organs = get_organs(status_filter=sel_status, organ_type_id=sel_ot_filter)

    if organs:
        st.caption(f"Displaying **{len(organs)}** organ record(s):")
        df_organs = pd.DataFrame(organs)

        # Build clean display view
        view_cols = [
            "organ_id", "organ_name", "donor_name", "blood_group",
            "full_or_part", "harvest_datetime", "viability_label", "status", "hospital_name"
        ]
        df_disp = df_organs[view_cols].rename(columns={
            "organ_id": "ID",
            "organ_name": "Organ",
            "donor_name": "Donor",
            "blood_group": "Blood Group",
            "full_or_part": "Portion",
            "harvest_datetime": "Harvest Time",
            "viability_label": "Viability Remaining",
            "status": "Status",
            "hospital_name": "Source Hospital"
        })
        st.dataframe(df_disp, use_container_width=True, hide_index=True)
    else:
        st.info("No organs matching the criteria.")

# -----------------------------------------------------------------------------
# TAB: Manage Organ Types
# -----------------------------------------------------------------------------
if not is_readonly:
    with tab_objs[2]:
        st.subheader("Manage Organ Classifications")

        st.markdown("##### Existing Organ Types")
        if organ_types:
            df_ot = pd.DataFrame(organ_types).rename(columns={
                "organ_type_id": "ID",
                "organ_name": "Organ Name",
                "viability_hours": "Viability (Hours)",
                "living_donation_allowed": "Living Donation Permitted"
            })
            st.dataframe(df_ot, use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("##### Add New Organ Type")
        with st.form("add_ot_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                new_ot_name = st.text_input("Organ Name*", placeholder="e.g. Pancreas")
            with c2:
                is_storable = st.checkbox("Cryo / Indefinitely Storable (No Expiration)", value=False)
                new_ot_viab = None if is_storable else st.number_input("Viability (Hours)", min_value=1, max_value=720, value=12)
            with c3:
                new_ot_living = st.checkbox("Living Donation Allowed", value=False)

            if st.form_submit_button("Add Organ Type"):
                if not new_ot_name.strip():
                    st.error("Organ name cannot be empty.")
                else:
                    try:
                        add_organ_type(new_ot_name.strip(), new_ot_viab, new_ot_living)
                        show_success(f"Organ type '{new_ot_name}' added.")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        show_db_error(e)
