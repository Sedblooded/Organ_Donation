import datetime
import streamlit as st
import pandas as pd
from utils.ui import render_sidebar, require_role, show_success, show_db_error, select_from_rows
from utils.rules import TRANSPLANT_OUTCOME
from queries.transplants import record_transplant, get_transplants, get_transplant_details
from queries.recovery import get_recoveries_for_transplant
from queries.staff import get_transplant_centres, get_doctors_affiliated_with_hospital
from queries.organs import get_available_organs
from queries.waitlist import get_active_recipients

st.set_page_config(page_title="Transplants | Organ Donation", layout="wide")
render_sidebar()
require_role(["Admin", "Doctor", "Hospital Staff"])

is_readonly = (st.session_state.get("role") == "Hospital Staff")

st.title("Surgical Transplants")
st.caption("Perform transactional organ allocations and audit surgical outcome trajectories.")

if is_readonly:
    st.info("You are logged in as **Hospital Staff** (Read-Only Mode). Surgical recording is restricted to Doctors and Admins.")

tabs = ["Transplant History"]
if not is_readonly:
    tabs = ["Record Transplant Procedure", "Transplant History"]

tab_objs = st.tabs(tabs)

# -----------------------------------------------------------------------------
# TAB: Record Transplant
# -----------------------------------------------------------------------------
if not is_readonly:
    with tab_objs[0]:
        st.subheader("Record Surgical Transplant")
        st.caption("Performs atomic database update: locks organ, records surgery, sets organ to 'transplanted', and marks waitlist as 'fulfilled'.")

        prefill_organ_id = st.session_state.get("selected_organ_id")
        prefill_rec_id = st.session_state.get("selected_recipient_id")

        if prefill_organ_id:
            st.info(f"Pre-filled from Matching workflow: Organ #{prefill_organ_id} for Recipient #{prefill_rec_id}")

        available_organs = get_available_organs()
        recipients = get_active_recipients()
        centres = get_transplant_centres()

        if not centres:
            st.error("No registered transplant centres found. Transplants can only be conducted at licensed transplant centres.")
        else:
            c1, c2 = st.columns(2)
            with c1:
                # Select Operating Hospital (must be a transplant centre)
                centre_names = [f"{c['name']} (Reg: {c['reg_id']})" for c in centres]
                sel_centre_idx = st.selectbox(
                    "Transplant Centre Hospital*",
                    range(len(centres)),
                    format_func=lambda i: centre_names[i],
                    key="tx_centre_select"
                )
                operating_hosp_id = centres[sel_centre_idx]["hosp_id"]

                # Lead Doctor: Only doctors affiliated with the selected hospital
                affiliated_doctors = get_doctors_affiliated_with_hospital(operating_hosp_id)
                if not affiliated_doctors:
                    st.warning(f"No doctors are currently affiliated with {centres[sel_centre_idx]['name']}. Please assign doctors in Doctors & Hospitals.")
                    lead_doc_id = None
                else:
                    doc_options = [f"Dr. {d['name']} (Bar ID: {d['med_bar_id']}) — Role: {d['role']}" for d in affiliated_doctors]
                    sel_doc_idx = st.selectbox(
                        "Lead Surgeon (Affiliated Doctor)*",
                        range(len(affiliated_doctors)),
                        format_func=lambda i: doc_options[i],
                        key="tx_doctor_select"
                    )
                    lead_doc_id = affiliated_doctors[sel_doc_idx]["doctor_id"]

            with c2:
                # Organ selection
                organ_opts = [{"organ_id": None, "label": "-- Select Available Organ --"}]
                default_org_idx = 0
                for idx, o in enumerate(available_organs):
                    label = f"Organ #{o['organ_id']} — {o['organ_name']} ({o['full_or_part']}) | Donor: {o['donor_name']} ({o['blood_group']})"
                    organ_opts.append({"organ_id": o["organ_id"], "label": label})
                    if prefill_organ_id and o["organ_id"] == prefill_organ_id:
                        default_org_idx = idx + 1

                chosen_org_idx = st.selectbox("Organ Specimen*", range(len(organ_opts)), index=default_org_idx, format_func=lambda i: organ_opts[i]["label"])
                chosen_organ_id = organ_opts[chosen_org_idx]["organ_id"]

                # Recipient selection
                rec_opts = [{"recipient_id": None, "label": "-- Select Recipient --"}]
                default_rec_idx = 0
                for idx, r in enumerate(recipients):
                    label = f"Recipient #{r['patient_id']} — {r['name']} (BG: {r['blood_group']}, Urgency: {r['urgency_level']})"
                    rec_opts.append({"recipient_id": r["patient_id"], "label": label})
                    if prefill_rec_id and r["patient_id"] == prefill_rec_id:
                        default_rec_idx = idx + 1

                chosen_rec_idx = st.selectbox("Recipient Patient*", range(len(rec_opts)), index=default_rec_idx, format_func=lambda i: rec_opts[i]["label"])
                chosen_rec_id = rec_opts[chosen_rec_idx]["recipient_id"]

            st.divider()

            with st.form("perform_transplant_form"):
                fc1, fc2 = st.columns(2)
                with fc1:
                    tx_date = st.date_input("Transplant Date*", value=datetime.date.today(), max_value=datetime.date.today())
                    tx_time = st.time_input("Transplant Time*", value=datetime.datetime.now().time())
                    tx_datetime = datetime.datetime.combine(tx_date, tx_time)
                with fc2:
                    outcome = st.selectbox("Initial Outcome Status*", TRANSPLANT_OUTCOME, index=TRANSPLANT_OUTCOME.index("successful"))

                submitted = st.form_submit_button("Execute Surgical Transplant Transaction", use_container_width=True)
                if submitted:
                    if not chosen_organ_id:
                        st.error("Please select an available organ.")
                    elif not chosen_rec_id:
                        st.error("Please select a recipient.")
                    elif not operating_hosp_id:
                        st.error("Please select an operating transplant centre.")
                    elif not lead_doc_id:
                        st.error("Please select an affiliated lead surgeon.")
                    else:
                        try:
                            tx_id = record_transplant(
                                organ_id=chosen_organ_id,
                                recipient_id=chosen_rec_id,
                                hosp_id=operating_hosp_id,
                                lead_doctor_id=lead_doc_id,
                                transplant_date=tx_datetime,
                                outcome=outcome
                            )
                            show_success(f"Transplant #{tx_id} successfully executed! Organ and Waitlist statuses updated atomically.")
                            # Clear prefill
                            st.session_state["selected_organ_id"] = None
                            st.session_state["selected_recipient_id"] = None
                            st.session_state["selected_waitlist_id"] = None
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            show_db_error(e)

# -----------------------------------------------------------------------------
# TAB: Transplant History
# -----------------------------------------------------------------------------
hist_idx = 0 if is_readonly else 1
with tab_objs[hist_idx]:
    st.subheader("Transplant Surgical History")

    fc1, fc2 = st.columns(2)
    with fc1:
        centres = get_transplant_centres()
        hosp_filter_opts = [{"hosp_id": None, "name": "All Transplant Centres"}] + centres
        sel_hosp_filter = select_from_rows("Filter Hospital", hosp_filter_opts, "hosp_id", lambda r: r["name"])
    with fc2:
        sel_outcome_filter = st.selectbox("Filter Outcome", ["All"] + TRANSPLANT_OUTCOME)

    history = get_transplants(hosp_id=sel_hosp_filter, outcome_filter=sel_outcome_filter)

    if history:
        st.caption(f"Found **{len(history)}** completed surgical record(s):")
        df_hist = pd.DataFrame(history)

        display_cols = [
            "transplant_id", "organ_name", "donor_name", "donor_blood_group",
            "recipient_name", "recipient_blood_group", "hospital_name",
            "lead_doctor_name", "transplant_date", "outcome"
        ]
        df_disp = df_hist[display_cols].rename(columns={
            "transplant_id": "Tx ID",
            "organ_name": "Organ",
            "donor_name": "Donor",
            "donor_blood_group": "Donor BG",
            "recipient_name": "Recipient",
            "recipient_blood_group": "Recip BG",
            "hospital_name": "Centre",
            "lead_doctor_name": "Lead Surgeon",
            "transplant_date": "Date & Time",
            "outcome": "Outcome"
        })
        st.dataframe(df_disp, use_container_width=True, hide_index=True)

        st.divider()
        st.markdown("#### Surgical Record Deep Dive & Post-Op Monitoring")

        sel_tx_id = select_from_rows(
            "Select Transplant to View Detail and Recovery Trajectory",
            history,
            "transplant_id",
            lambda r: f"Tx #{r['transplant_id']}: {r['organ_name']} ➔ {r['recipient_name']} ({r['hospital_name']}, {r['outcome']})"
        )

        if sel_tx_id:
            tx_detail = get_transplant_details(sel_tx_id)
            rec_checkups = get_recoveries_for_transplant(sel_tx_id)

            with st.container(border=True):
                dc1, dc2, dc3, dc4 = st.columns(4)
                with dc1:
                    st.caption("TRANSPLANT ID")
                    st.markdown(f"##### #{tx_detail['transplant_id']}")
                with dc2:
                    st.caption("ORGAN SPECIMEN")
                    st.markdown(f"##### {tx_detail['organ_name']} ({tx_detail['full_or_part']})")
                with dc3:
                    st.caption("COMPATIBILITY")
                    st.markdown(f"##### {tx_detail['donor_blood_group']} ➔ {tx_detail['recipient_blood_group']}")
                with dc4:
                    st.caption("CURRENT OUTCOME")
                    st.markdown(f"##### {tx_detail['outcome'].title()}")

            st.markdown("##### Post-Operative Recovery Logs")
            if rec_checkups:
                df_recs = pd.DataFrame(rec_checkups).rename(columns={
                    "recovery_id": "Log ID",
                    "doctor_name": "Attending Doctor",
                    "checkup_date": "Checkup Date",
                    "status": "Patient Status",
                    "description": "Clinical Notes"
                })
                st.dataframe(df_recs[["Log ID", "Attending Doctor", "Checkup Date", "Patient Status", "Clinical Notes"]], use_container_width=True, hide_index=True)
            else:
                st.info("No recovery checkups logged for this transplant yet. Checkups can be entered on the Recovery page.")
    else:
        st.info("No transplant records found matching the filters.")
