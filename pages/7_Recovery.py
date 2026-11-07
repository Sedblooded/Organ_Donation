import datetime
import streamlit as st
import pandas as pd
import plotly.express as px
from utils.ui import render_sidebar, require_role, show_success, show_db_error, select_from_rows
from utils.rules import RECOVERY_STATUS
from queries.recovery import add_recovery_checkup, get_recoveries_for_transplant, get_all_recoveries
from queries.transplants import get_transplants, get_transplant_details
from queries.staff import get_doctors

st.set_page_config(page_title="Recovery | Organ Donation", layout="wide")
render_sidebar()
require_role(["Admin", "Doctor", "Hospital Staff"])

is_readonly = (st.session_state.get("role") == "Hospital Staff")

st.title("Post-Transplant Recovery Monitoring")
st.caption("Track post-operative milestones, organ acceptance, patient status trajectories, and clinical checkups.")

if is_readonly:
    st.info("You are logged in as **Hospital Staff** (Read-Only Mode). Checkup logs can only be created by Doctors or Admins.")

transplants = get_transplants()
doctors = get_doctors()

tabs = ["Recovery Timelines & Directory"]
if not is_readonly:
    tabs = ["Add Recovery Checkup", "Recovery Timelines & Directory"]

tab_objs = st.tabs(tabs)

# -----------------------------------------------------------------------------
# TAB: Add Checkup
# -----------------------------------------------------------------------------
if not is_readonly:
    with tab_objs[0]:
        st.subheader("Log Post-Operative Checkup")

        if not transplants:
            st.warning("No transplants have been performed yet. Record a transplant procedure first.")
        else:
            with st.form("add_recovery_form"):
                c1, c2 = st.columns(2)
                with c1:
                    sel_tx_id = select_from_rows(
                        "Transplant Event*",
                        transplants,
                        "transplant_id",
                        lambda r: f"Tx #{r['transplant_id']}: {r['organ_name']} ➔ {r['recipient_name']} ({r['hospital_name']}, Date: {r['transplant_date'].strftime('%Y-%m-%d')})"
                    )

                    chosen_tx = next((t for t in transplants if t["transplant_id"] == sel_tx_id), None)
                    default_doc_id = chosen_tx["lead_doctor_id"] if chosen_tx else None

                    sel_doc_id = select_from_rows(
                        "Attending Physician*",
                        doctors,
                        "doctor_id",
                        lambda r: f"Dr. {r['name']} ({r['specializations']})",
                        default_id=default_doc_id
                    )

                with c2:
                    min_date = chosen_tx["transplant_date"].date() if chosen_tx else datetime.date(2020, 1, 1)
                    checkup_date = st.date_input(
                        "Checkup Date*",
                        value=datetime.date.today(),
                        min_value=min_date,
                        max_value=datetime.date.today()
                    )

                    rec_status = st.selectbox("Current Recovery Status*", RECOVERY_STATUS)

                description = st.text_area(
                    "Clinical Observations & Notes",
                    placeholder="Immunosuppressive dosage, graft function markers, ultrasound findings, complications..."
                )

                if st.form_submit_button("Submit Recovery Checkup", use_container_width=True):
                    if not sel_tx_id:
                        st.error("Please select a valid transplant.")
                    elif not sel_doc_id:
                        st.error("Please select a doctor.")
                    else:
                        try:
                            rec_id = add_recovery_checkup(sel_tx_id, sel_doc_id, checkup_date, rec_status, description)
                            show_success(f"Checkup #{rec_id} successfully logged for Transplant #{sel_tx_id}.")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            show_db_error(e)

# -----------------------------------------------------------------------------
# TAB: Timelines & Directory
# -----------------------------------------------------------------------------
timeline_idx = 0 if is_readonly else 1
with tab_objs[timeline_idx]:
    st.subheader("Patient Recovery Trajectories")

    if not transplants:
        st.info("No transplants to display.")
    else:
        sel_tx_view_id = select_from_rows(
            "Select Transplant Patient",
            transplants,
            "transplant_id",
            lambda r: f"Tx #{r['transplant_id']}: {r['recipient_name']} — {r['organ_name']} ({r['hospital_name']})"
        )

        if sel_tx_view_id:
            tx_info = get_transplant_details(sel_tx_view_id)
            logs = get_recoveries_for_transplant(sel_tx_view_id)

            with st.container(border=True):
                tc1, tc2, tc3 = st.columns(3)
                with tc1:
                    st.caption("RECIPIENT")
                    st.markdown(f"##### {tx_info['recipient_name']} ({tx_info['recipient_blood_group']})")
                with tc2:
                    st.caption("ORGAN SPECIMEN")
                    st.markdown(f"##### {tx_info['organ_name']} ({tx_info['full_or_part']})")
                with tc3:
                    st.caption("SURGERY DATE")
                    st.markdown(f"##### {tx_info['transplant_date'].strftime('%Y-%m-%d')}")

            st.divider()

            if logs:
                st.markdown(f"#### Checkup History ({len(logs)} logs)")

                # Chronological expanders
                for idx, log in enumerate(logs, start=1):
                    with st.expander(f"Checkup #{idx} — Date: {log['checkup_date']} | Status: {log['status'].upper()} (Dr. {log['doctor_name']})", expanded=(idx == len(logs))):
                        st.write(f"**Attending Physician:** Dr. {log['doctor_name']}")
                        st.write(f"**Status Evaluation:** `{log['status']}`")
                        st.write(f"**Clinical Notes:** {log['description'] or 'No detailed description entered.'}")

                # Status Progression Table
                st.divider()
                st.markdown("#### Tabular Timeline")
                df_logs = pd.DataFrame(logs)[["checkup_date", "status", "doctor_name", "description"]].rename(columns={
                    "checkup_date": "Date",
                    "status": "Status",
                    "doctor_name": "Physician",
                    "description": "Notes"
                })
                st.dataframe(df_logs, use_container_width=True, hide_index=True)
            else:
                st.info("No checkups logged for this transplant yet.")

    st.divider()
    st.subheader("All System Recovery Logs")
    all_recs = get_all_recoveries()
    if all_recs:
        df_all = pd.DataFrame(all_recs).rename(columns={
            "recovery_id": "Log ID",
            "transplant_id": "Tx ID",
            "organ_name": "Organ",
            "recipient_name": "Recipient",
            "hospital_name": "Hospital",
            "doctor_name": "Doctor",
            "checkup_date": "Checkup Date",
            "status": "Status",
            "description": "Notes"
        })
        st.dataframe(df_all, use_container_width=True, hide_index=True)
