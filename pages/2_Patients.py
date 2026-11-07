import datetime
import calendar
import streamlit as st
import pandas as pd
from utils.ui import render_sidebar, require_role, show_success, show_db_error, select_from_rows
from utils.rules import BLOOD_GROUPS, GENDERS, DONOR_TYPE, ALIVE_STATUS, DONOR_CONSENT_STATUS
from queries.patients import (
    get_all_pincodes,
    insert_pincode,
    add_patient,
    make_donor,
    make_recipient,
    register_full_patient,
    get_patients_not_donors,
    get_patients_not_recipients,
    search_patients,
    update_patient,
    delete_patient
)
from queries.staff import get_hospitals

st.set_page_config(page_title="Patients | Organ Donation", layout="wide")
render_sidebar()
require_role(["Admin", "Doctor", "Hospital Staff"])

is_readonly = (st.session_state.get("role") == "Doctor")

st.title("Patient Management")
st.caption("Register patients, designate donors/recipients, and maintain complete health records.")

if is_readonly:
    st.info("You are logged in as a **Doctor** (Read-Only Mode). Modifications are disabled.")

# Load hospitals and pincodes for dropdowns
hospitals = get_hospitals()
pincodes = get_all_pincodes()

tabs = ["Search & Directory"]
if not is_readonly:
    tabs = ["Register Patient", "Designate Donor", "Designate Recipient"] + tabs

tab_objs = st.tabs(tabs)

# -----------------------------------------------------------------------------
# TAB: Register Patient (Combined Form)
# -----------------------------------------------------------------------------
if not is_readonly:
    with tab_objs[0]:
        st.subheader("New Patient Registration")
        st.caption("Enroll a new individual and optionally register their donor/recipient classification.")

        # Quick expander to add a new pincode area if not present in the dropdown
        with st.expander("Can't find a pincode? Add a new Pincode Area"):
            with st.form("add_pincode_form"):
                new_pin = st.text_input("6-Digit Pincode", max_chars=6)
                new_city = st.text_input("City")
                new_state = st.text_input("State")
                if st.form_submit_button("Save Pincode"):
                    if len(new_pin) == 6 and new_pin.isdigit() and new_city and new_state:
                        try:
                            insert_pincode(new_pin, new_city, new_state)
                            show_success(f"Pincode {new_pin} added successfully.")
                            st.rerun()
                        except Exception as e:
                            show_db_error(e)
                    else:
                        st.error("Please enter a valid 6-digit numeric pincode, city, and state.")

        with st.form("register_patient_form"):
            c1, c2, c3 = st.columns(3)
            with c1:
                name = st.text_input("Full Name*", placeholder="e.g. John Doe")
                st.markdown("<label style='font-size: 14px;'>Date of Birth* (Year / Month / Day)</label>", unsafe_allow_html=True)
                dob_y, dob_m, dob_d = st.columns(3)
                current_year = datetime.date.today().year
                with dob_y:
                    birth_year = st.selectbox(
                        "Birth Year",
                        range(current_year, 1920, -1),
                        index=current_year - 2000,
                        label_visibility="collapsed",
                        key="reg_dob_y"
                    )
                with dob_m:
                    birth_month = st.selectbox(
                        "Birth Month",
                        range(1, 13),
                        index=0,
                        format_func=lambda m: datetime.date(2000, m, 1).strftime('%B (%m)'),
                        label_visibility="collapsed",
                        key="reg_dob_m"
                    )
                with dob_d:
                    _, max_d = calendar.monthrange(birth_year, birth_month)
                    birth_day = st.selectbox(
                        "Birth Day",
                        range(1, max_d + 1),
                        index=0,
                        label_visibility="collapsed",
                        key="reg_dob_d"
                    )
                dob = datetime.date(birth_year, birth_month, birth_day)
                gender = st.selectbox("Gender*", GENDERS)
            with c2:
                blood_group = st.selectbox("Blood Group*", BLOOD_GROUPS)
                street = st.text_input("Street / Area", placeholder="123 Hospital Lane")

                # Pincode Dropdown
                pincode_options = [f"{p['pincode']} — {p['city']}, {p['state']}" for p in pincodes]
                selected_pin_idx = st.selectbox(
                    "Pincode Area*",
                    range(len(pincodes)) if pincodes else [0],
                    format_func=lambda i: pincode_options[i] if pincodes else "No Pincodes Found"
                )
                selected_pincode = pincodes[selected_pin_idx]["pincode"] if pincodes else None

            with c3:
                hosp_names = [h["name"] for h in hospitals]
                selected_hosp_idx = st.selectbox(
                    "Registered Hospital*",
                    range(len(hospitals)) if hospitals else [0],
                    format_func=lambda i: hosp_names[i] if hospitals else "No Hospitals Found"
                )
                selected_hosp_id = hospitals[selected_hosp_idx]["hosp_id"] if hospitals else None
                notes = st.text_area("General Notes", placeholder="Medical history, allergies, notes...")

            st.markdown("#### Initial Classification (ISA Roles)")
            role_choice = st.radio(
                "Enroll as Donor or Recipient immediately?",
                ["None (General Patient)", "Donor", "Recipient", "Both"],
                horizontal=True
            )

            donor_type = "deceased"
            alive_status = "deceased"
            consent_status = "pending"
            donor_notes = ""
            urgency_level = 3
            recipient_notes = ""

            if role_choice in ["Donor", "Both"]:
                st.markdown("##### Donor Details")
                cd1, cd2, cd3 = st.columns(3)
                with cd1:
                    donor_type = st.selectbox("Donor Type", DONOR_TYPE, key="reg_donor_type")
                with cd2:
                    # Enforce constraint: If donor_type is deceased, alive_status must be deceased
                    if donor_type == "deceased":
                        alive_status = "deceased"
                        st.text_input("Alive Status", value="deceased", disabled=True)
                    else:
                        alive_status = st.selectbox("Alive Status", ALIVE_STATUS, key="reg_alive_status")
                with cd3:
                    consent_status = st.selectbox("Consent Status", DONOR_CONSENT_STATUS, key="reg_consent_status")
                donor_notes = st.text_input("Donor Medical Notes", placeholder="Organ pledges, cause of death if applicable")

            if role_choice in ["Recipient", "Both"]:
                st.markdown("##### Recipient Details")
                cr1, cr2 = st.columns([1, 2])
                with cr1:
                    urgency_level = st.slider("Urgency Level (1 = Most Critical, 5 = Stable)*", 1, 5, 3)
                with cr2:
                    recipient_notes = st.text_input("Recipient Medical Notes", placeholder="Primary diagnosis, urgency justification")

            submitted = st.form_submit_button("Register Patient", use_container_width=True)
            if submitted:
                if not name.strip():
                    st.error("Patient name cannot be empty.")
                elif not selected_pincode:
                    st.error("Please select a valid pincode.")
                elif not selected_hosp_id:
                    st.error("Please select a hospital.")
                else:
                    role_type_str = "None"
                    if role_choice == "Donor":
                        role_type_str = "Donor"
                    elif role_choice == "Recipient":
                        role_type_str = "Recipient"
                    elif role_choice == "Both":
                        role_type_str = "Both"

                    try:
                        pid = register_full_patient(
                            name=name.strip(),
                            dob=dob,
                            gender=gender,
                            blood_group=blood_group,
                            street=street.strip(),
                            pincode=selected_pincode,
                            notes=notes.strip(),
                            hosp_id=selected_hosp_id,
                            role_type=role_type_str,
                            donor_type=donor_type,
                            alive_status=alive_status,
                            consent_status=consent_status,
                            donor_notes=donor_notes.strip(),
                            urgency_level=urgency_level,
                            recipient_notes=recipient_notes.strip()
                        )
                        show_success(f"Patient '{name}' successfully registered with ID #{pid}!")
                        st.cache_data.clear()
                    except Exception as e:
                        show_db_error(e)

    # -------------------------------------------------------------------------
    # TAB: Designate Donor
    # -------------------------------------------------------------------------
    with tab_objs[1]:
        st.subheader("Designate Existing Patient as Donor")
        candidates = get_patients_not_donors()
        if not candidates:
            st.info("All registered patients are currently enrolled as donors, or no patients exist.")
        else:
            with st.form("make_donor_form"):
                donor_pid = select_from_rows(
                    "Select Patient",
                    candidates,
                    "patient_id",
                    lambda r: f"#{r['patient_id']} - {r['name']} ({r['blood_group']}, Born {r['dob']}) - {r['hospital_name']}"
                )
                cd1, cd2, cd3 = st.columns(3)
                with cd1:
                    d_type = st.selectbox("Donor Type", DONOR_TYPE, key="tab_donor_type")
                with cd2:
                    if d_type == "deceased":
                        a_status = "deceased"
                        st.text_input("Alive Status", value="deceased", disabled=True, key="tab_a_status_disp")
                    else:
                        a_status = st.selectbox("Alive Status", ALIVE_STATUS, key="tab_alive_status")
                with cd3:
                    c_status = st.selectbox("Consent Status", DONOR_CONSENT_STATUS, key="tab_consent_status")
                d_notes = st.text_area("Medical / Consent Notes")

                if st.form_submit_button("Designate as Donor", use_container_width=True):
                    if donor_pid:
                        try:
                            make_donor(donor_pid, d_type, a_status, c_status, d_notes)
                            show_success(f"Patient #{donor_pid} has been registered as a donor.")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            show_db_error(e)

    # -------------------------------------------------------------------------
    # TAB: Designate Recipient
    # -------------------------------------------------------------------------
    with tab_objs[2]:
        st.subheader("Designate Existing Patient as Recipient")
        rec_candidates = get_patients_not_recipients()
        if not rec_candidates:
            st.info("All registered patients are already enrolled as recipients, or no patients exist.")
        else:
            with st.form("make_recipient_form"):
                rec_pid = select_from_rows(
                    "Select Patient",
                    rec_candidates,
                    "patient_id",
                    lambda r: f"#{r['patient_id']} - {r['name']} ({r['blood_group']}, Born {r['dob']}) - {r['hospital_name']}"
                )
                urgency = st.slider("Urgency Level (1 = Highest / Critical, 5 = Stable)", 1, 5, 3)
                r_notes = st.text_area("Clinical Notes & Diagnosis")

                if st.form_submit_button("Designate as Recipient", use_container_width=True):
                    if rec_pid:
                        try:
                            make_recipient(rec_pid, urgency, r_notes)
                            show_success(f"Patient #{rec_pid} has been registered as a recipient.")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            show_db_error(e)

# -----------------------------------------------------------------------------
# TAB: Search & Directory
# -----------------------------------------------------------------------------
search_tab_idx = 0 if is_readonly else 3
with tab_objs[search_tab_idx]:
    st.subheader("Patient Directory")

    fc1, fc2, fc3, fc4 = st.columns(4)
    with fc1:
        s_name = st.text_input("Search Name", placeholder="e.g. Sharma")
    with fc2:
        s_bg = st.selectbox("Blood Group Filter", ["All"] + BLOOD_GROUPS)
    with fc3:
        hosp_options = [{"hosp_id": None, "name": "All Hospitals"}] + hospitals
        s_hosp_id = select_from_rows(
            "Hospital Filter",
            hosp_options,
            "hosp_id",
            lambda r: r["name"]
        )
    with fc4:
        s_role = st.selectbox("Role Filter", ["All", "Donor", "Recipient"])

    results = search_patients(
        name_search=s_name,
        blood_group=s_bg,
        hosp_id=s_hosp_id,
        role_filter=s_role
    )

    if results:
        st.caption(f"Showing **{len(results)}** patient records:")
        df = pd.DataFrame(results)

        display_cols = [
            "patient_id", "name", "dob", "gender", "blood_group",
            "hospital_name", "city", "is_donor", "is_recipient"
        ]
        st.dataframe(df[display_cols], use_container_width=True, hide_index=True)

        if not is_readonly:
            st.divider()
            st.markdown("#### Patient Details & Actions")
            sel_pid = select_from_rows(
                "Select Patient to Edit or Delete",
                results,
                "patient_id",
                lambda r: f"#{r['patient_id']} - {r['name']} ({r['blood_group']})"
            )
            selected_patient = next((r for r in results if r["patient_id"] == sel_pid), None)

            if selected_patient:
                with st.expander(f"Edit Patient Details: #{selected_patient['patient_id']} - {selected_patient['name']}"):
                    with st.form("edit_patient_form"):
                        ec1, ec2 = st.columns(2)
                        with ec1:
                            en = st.text_input("Name", value=selected_patient["name"])
                            st.markdown("<label style='font-size: 14px;'>Date of Birth (Year / Month / Day)</label>", unsafe_allow_html=True)
                            edob_y, edob_m, edob_d = st.columns(3)
                            cur_pat_dob = selected_patient["dob"]
                            current_year = datetime.date.today().year
                            year_opts = list(range(current_year, 1920, -1))
                            y_idx = year_opts.index(cur_pat_dob.year) if cur_pat_dob.year in year_opts else 0
                            with edob_y:
                                e_year = st.selectbox("Year", year_opts, index=y_idx, label_visibility="collapsed", key="edit_dob_y")
                            with edob_m:
                                e_month = st.selectbox("Month", range(1, 13), index=cur_pat_dob.month - 1, format_func=lambda m: datetime.date(2000, m, 1).strftime('%B (%m)'), label_visibility="collapsed", key="edit_dob_m")
                            with edob_d:
                                _, max_d = calendar.monthrange(e_year, e_month)
                                d_opts = list(range(1, max_d + 1))
                                d_idx = d_opts.index(cur_pat_dob.day) if cur_pat_dob.day in d_opts else 0
                                e_day = st.selectbox("Day", d_opts, index=d_idx, label_visibility="collapsed", key="edit_dob_d")
                            edob = datetime.date(e_year, e_month, e_day)
                            eg = st.selectbox("Gender", GENDERS, index=GENDERS.index(selected_patient["gender"]))
                            ebg = st.selectbox("Blood Group", BLOOD_GROUPS, index=BLOOD_GROUPS.index(selected_patient["blood_group"]))
                        with ec2:
                            estreet = st.text_input("Street", value=selected_patient["street"] or "")
                            cur_pin = selected_patient["pincode"]
                            pin_idx = 0
                            for idx, p in enumerate(pincodes):
                                if p["pincode"] == cur_pin:
                                    pin_idx = idx
                                    break
                            epin_idx = st.selectbox(
                                "Pincode",
                                range(len(pincodes)),
                                format_func=lambda i: f"{pincodes[i]['pincode']} — {pincodes[i]['city']}",
                                index=pin_idx
                            )
                            epin = pincodes[epin_idx]["pincode"]
                            cur_hosp = selected_patient["hosp_id"]
                            hosp_idx = 0
                            for idx, h in enumerate(hospitals):
                                if h["hosp_id"] == cur_hosp:
                                    hosp_idx = idx
                                    break
                            ehosp_idx = st.selectbox(
                                "Hospital",
                                range(len(hospitals)),
                                format_func=lambda i: hospitals[i]["name"],
                                index=hosp_idx
                            )
                            ehosp_id = hospitals[ehosp_idx]["hosp_id"]
                            enotes = st.text_area("Notes", value=selected_patient["notes"] or "")

                        if st.form_submit_button("Update Patient Details"):
                            try:
                                update_patient(selected_patient["patient_id"], en, edob, eg, ebg, estreet, epin, enotes, ehosp_id)
                                show_success("Patient record updated.")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                show_db_error(e)

                st.markdown("##### Danger Zone")
                del_confirm = st.checkbox(f"Confirm deletion of Patient #{selected_patient['patient_id']} - {selected_patient['name']}")
                if st.button("Delete Patient", type="primary", disabled=not del_confirm):
                    try:
                        delete_patient(selected_patient["patient_id"])
                        show_success("Patient deleted.")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        show_db_error(e)
    else:
        st.info("No patients found matching the selected criteria.")
