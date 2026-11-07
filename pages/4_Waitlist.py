import datetime
import streamlit as st
import pandas as pd
from utils.ui import render_sidebar, require_role, show_success, show_db_error, select_from_rows
from queries.waitlist import (
    get_active_recipients,
    check_active_waitlist_exists,
    add_to_waitlist,
    get_waitlist,
    update_waitlist_priority,
    update_waitlist_status
)
from queries.organs import get_organ_types
from queries.staff import get_hospitals

st.set_page_config(page_title="Waitlist | Organ Donation", layout="wide")
render_sidebar()
require_role(["Admin", "Doctor", "Hospital Staff"])

st.title("National Recipient Waitlist")
st.caption("Manage prioritized organ queues, monitor wait durations, and adjust clinical priorities.")

recipients = get_active_recipients()
organ_types = get_organ_types()
hospitals = get_hospitals()

t1, t2 = st.tabs(["Active Waitlist Directory", "Add to Waitlist"])

# -----------------------------------------------------------------------------
# TAB 1: View Waitlist
# -----------------------------------------------------------------------------
with t1:
    st.subheader("Waitlist Queue")

    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        st_opts = ["active", "matched", "fulfilled", "removed", "All"]
        sel_st = st.selectbox("Status Filter", st_opts, index=0)
    with fc2:
        ot_opts = [{"organ_type_id": None, "organ_name": "All Organ Types"}] + organ_types
        sel_ot = select_from_rows(
            "Organ Needed",
            ot_opts,
            "organ_type_id",
            lambda r: r["organ_name"]
        )
    with fc3:
        hosp_opts = [{"hosp_id": None, "name": "All Hospitals"}] + hospitals
        sel_hosp = select_from_rows(
            "Listing Hospital",
            hosp_opts,
            "hosp_id",
            lambda r: r["name"]
        )

    entries = get_waitlist(status_filter=sel_st, organ_type_id=sel_ot, hosp_id=sel_hosp)

    if entries:
        st.caption(f"Showing **{len(entries)}** waitlist candidate(s) (ordered by Priority, Urgency, and Waiting Duration):")
        df_wl = pd.DataFrame(entries)

        display_cols = [
            "waitlist_id", "recipient_name", "blood_group", "organ_name",
            "priority", "urgency_level", "date_added", "days_waiting", "hospital_name", "status"
        ]
        df_disp = df_wl[display_cols].rename(columns={
            "waitlist_id": "Waitlist ID",
            "recipient_name": "Recipient",
            "blood_group": "Blood Group",
            "organ_name": "Organ Type",
            "priority": "Priority (1=High)",
            "urgency_level": "Urgency (1=Critical)",
            "date_added": "Date Listed",
            "days_waiting": "Days Waiting",
            "hospital_name": "Hospital",
            "status": "Status"
        })
        st.dataframe(df_disp, use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("#### Manage Candidate Entry")
        active_entries = [e for e in entries if e["status"] == "active"]

        if active_entries:
            sel_wid = select_from_rows(
                "Select Active Candidate Entry",
                active_entries,
                "waitlist_id",
                lambda r: f"#{r['waitlist_id']} - {r['recipient_name']} ({r['organ_name']}) | Current Priority: {r['priority']}"
            )

            sel_entry = next((e for e in active_entries if e["waitlist_id"] == sel_wid), None)

            if sel_entry:
                col_act1, col_act2 = st.columns(2)
                with col_act1:
                    with st.form("update_prio_form"):
                        new_prio = st.slider(
                            "Update Clinical Priority (1 = Highest, 5 = Lowest)",
                            min_value=1,
                            max_value=5,
                            value=sel_entry["priority"]
                        )
                        if st.form_submit_button("Update Priority"):
                            try:
                                update_waitlist_priority(sel_entry["waitlist_id"], new_prio)
                                show_success(f"Priority updated to {new_prio} for #{sel_entry['waitlist_id']}.")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                show_db_error(e)

                with col_act2:
                    st.write("##### Cancel Listing")
                    st.caption("Remove recipient from the active queue if no longer eligible or transplanted elsewhere.")
                    cancel_conf = st.checkbox("Confirm cancellation of waitlist listing")
                    if st.button("Cancel & Remove from Waitlist", type="primary", disabled=not cancel_conf):
                        try:
                            update_waitlist_status(sel_entry["waitlist_id"], "removed")
                            show_success(f"Waitlist entry #{sel_entry['waitlist_id']} has been set to 'removed'.")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            show_db_error(e)
    else:
        st.info("No candidates on the waitlist matching the selected criteria.")

# -----------------------------------------------------------------------------
# TAB 2: Add to Waitlist
# -----------------------------------------------------------------------------
with t2:
    st.subheader("Enroll Recipient on Waitlist")

    if not recipients:
        st.warning("No recipients found in the database. Please designate patients as recipients first.")
    elif not organ_types:
        st.warning("No organ types available.")
    else:
        with st.form("add_waitlist_form"):
            c1, c2 = st.columns(2)

            with c1:
                rec_id = select_from_rows(
                    "Recipient*",
                    recipients,
                    "patient_id",
                    lambda r: f"#{r['patient_id']} - {r['name']} ({r['blood_group']}) | Urgency: {r['urgency_level']} ({r['hospital_name']})"
                )

                ot_id = select_from_rows(
                    "Organ Needed*",
                    organ_types,
                    "organ_type_id",
                    lambda r: r["organ_name"]
                )

            with c2:
                # Default hospital to recipient's hospital
                default_hosp_id = None
                if rec_id:
                    matched_r = next((r for r in recipients if r["patient_id"] == rec_id), None)
                    if matched_r:
                        default_hosp_id = matched_r["hosp_id"]

                hosp_id = select_from_rows(
                    "Supervising Hospital*",
                    hospitals,
                    "hosp_id",
                    lambda r: f"{r['name']} ({r['facility_type']})",
                    default_id=default_hosp_id
                )

                priority = st.slider("Clinical Priority (1 = Immediate / Urgent, 5 = Elective / Stable)*", 1, 5, 3)
                date_added = st.date_input("Listing Date*", value=datetime.date.today(), max_value=datetime.date.today())

            if st.form_submit_button("Submit to Waitlist", use_container_width=True):
                if not rec_id:
                    st.error("Please select a recipient.")
                elif not ot_id:
                    st.error("Please select an organ type.")
                elif not hosp_id:
                    st.error("Please select a hospital.")
                elif check_active_waitlist_exists(rec_id, ot_id):
                    st.error("Duplicate Waitlist Entry: This recipient is ALREADY actively waitlisted for this organ type.")
                else:
                    try:
                        wid = add_to_waitlist(rec_id, ot_id, hosp_id, priority, date_added)
                        show_success(f"Recipient successfully placed on waitlist with entry ID #{wid}!")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        show_db_error(e)
