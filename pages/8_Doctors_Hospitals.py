import datetime
import streamlit as st
import pandas as pd
from utils.ui import render_sidebar, require_role, show_success, show_db_error, select_from_rows
from utils.rules import FACILITY_TYPES
from queries.staff import (
    get_hospitals,
    add_hospital,
    get_doctors,
    add_doctor,
    get_specializations,
    add_specialization,
    get_doctor_specializations,
    set_doctor_specializations,
    get_affiliations,
    add_affiliation
)
from queries.patients import get_all_pincodes

st.set_page_config(page_title="Medical Staff & Hospitals | Organ Donation", layout="wide")
render_sidebar()
require_role(["Admin", "Doctor"])

is_readonly = (st.session_state.get("role") == "Doctor")

st.title("Medical Staff, Facilities & Affiliations")
st.caption("Manage healthcare institutions, licensed physicians, clinical specialties, and institutional affiliations.")

if is_readonly:
    st.info("You are logged in as a **Doctor** (Read-Only Mode). Facility administration is restricted to Admins.")

hospitals = get_hospitals()
doctors = get_doctors()
specializations = get_specializations()
pincodes = get_all_pincodes()

t1, t2, t3, t4 = st.tabs(["Doctors", "Specializations", "Hospitals", "Affiliations"])

# -----------------------------------------------------------------------------
# TAB 1: DOCTORS
# -----------------------------------------------------------------------------
with t1:
    st.subheader("Physicians & Surgeons")

    if not is_readonly:
        with st.expander("Register New Physician"):
            with st.form("add_doc_form"):
                dc1, dc2 = st.columns(2)
                with dc1:
                    d_name = st.text_input("Doctor Name*", placeholder="e.g. Dr. Rajesh Khanna")
                    d_contact = st.text_input("10-Digit Mobile Contact", placeholder="9876543210", max_chars=10)
                with dc2:
                    d_med_bar = st.text_input("Medical Council Bar ID*", placeholder="e.g. MCI-90812")
                    d_gen_id = st.text_input("National General ID*", placeholder="e.g. GEN-44123")

                if st.form_submit_button("Register Doctor", use_container_width=True):
                    if not d_name.strip() or not d_med_bar.strip() or not d_gen_id.strip():
                        st.error("Name, Medical Bar ID, and General ID are mandatory.")
                    elif d_contact and (len(d_contact) != 10 or not d_contact.isdigit() or d_contact[0] not in "6789"):
                        st.error("Contact must be a valid 10-digit Indian phone number starting with 6-9.")
                    else:
                        try:
                            doc_id = add_doctor(d_med_bar.strip(), d_gen_id.strip(), d_name.strip(), d_contact.strip() or None)
                            show_success(f"Doctor registered with ID #{doc_id}.")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            show_db_error(e)

    if doctors:
        df_docs = pd.DataFrame(doctors).rename(columns={
            "doctor_id": "ID",
            "name": "Doctor Name",
            "med_bar_id": "Bar Registration ID",
            "general_id": "General ID",
            "contact": "Contact",
            "specializations": "Specializations",
            "affiliated_hospitals": "Affiliated Hospitals"
        })
        st.dataframe(df_docs, use_container_width=True, hide_index=True)
    else:
        st.info("No doctors registered yet.")

# -----------------------------------------------------------------------------
# TAB 2: SPECIALIZATIONS
# -----------------------------------------------------------------------------
with t2:
    st.subheader("Clinical Specializations")

    col_s1, col_s2 = st.columns([1, 1])

    with col_s1:
        st.markdown("##### Specialization Registry")
        if specializations:
            df_specs = pd.DataFrame(specializations).rename(columns={"spec_id": "ID", "spec_name": "Specialization"})
            st.dataframe(df_specs, use_container_width=True, hide_index=True)

        if not is_readonly:
            with st.form("add_spec_form"):
                new_spec = st.text_input("New Specialization Name", placeholder="e.g. Cardiothoracic Surgery")
                if st.form_submit_button("Add Specialization"):
                    if new_spec.strip():
                        try:
                            add_specialization(new_spec.strip())
                            show_success(f"Specialization '{new_spec}' added.")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            show_db_error(e)

    with col_s2:
        st.markdown("##### Assign Specializations to Doctor")
        if not is_readonly and doctors and specializations:
            chosen_doc_id = select_from_rows(
                "Select Doctor",
                doctors,
                "doctor_id",
                lambda r: f"Dr. {r['name']} (#{r['doctor_id']})"
            )

            if chosen_doc_id:
                current_spec_ids = get_doctor_specializations(chosen_doc_id)
                spec_dict = {s["spec_id"]: s["spec_name"] for s in specializations}

                selected_specs = st.multiselect(
                    "Assign Specializations",
                    options=list(spec_dict.keys()),
                    default=current_spec_ids,
                    format_func=lambda s_id: spec_dict[s_id]
                )

                if st.button("Update Specializations", type="primary"):
                    try:
                        set_doctor_specializations(chosen_doc_id, selected_specs)
                        show_success("Doctor specializations updated successfully.")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        show_db_error(e)
        else:
            st.info("Assigning specializations requires registered doctors and specializations.")

# -----------------------------------------------------------------------------
# TAB 3: HOSPITALS
# -----------------------------------------------------------------------------
with t3:
    st.subheader("Hospitals & Healthcare Facilities")

    if not is_readonly:
        with st.expander("Register New Hospital Facility"):
            with st.form("add_hosp_form"):
                hc1, hc2 = st.columns(2)
                with hc1:
                    h_reg = st.text_input("Facility Registration ID*", placeholder="e.g. HOSP-BLR-004")
                    h_name = st.text_input("Hospital Name*", placeholder="e.g. Apollo Super Speciality")
                    h_type = st.selectbox("Facility Classification*", FACILITY_TYPES)
                with hc2:
                    h_street = st.text_input("Street Address", placeholder="e.g. Bannerghatta Road")

                    # Pincode Dropdown
                    pin_opts = [f"{p['pincode']} — {p['city']}, {p['state']}" for p in pincodes]
                    h_pin_idx = st.selectbox(
                        "Pincode Area*",
                        range(len(pincodes)) if pincodes else [0],
                        format_func=lambda i: pin_opts[i] if pincodes else "No Pincodes"
                    )
                    h_pincode = pincodes[h_pin_idx]["pincode"] if pincodes else None

                    h_contact = st.text_input("Contact Mobile", placeholder="9876543210", max_chars=10)

                if st.form_submit_button("Register Hospital", use_container_width=True):
                    if not h_reg.strip() or not h_name.strip() or not h_pincode:
                        st.error("Registration ID, Name, and Pincode are mandatory.")
                    elif h_contact and (len(h_contact) != 10 or not h_contact.isdigit() or h_contact[0] not in "6789"):
                        st.error("Contact must be a valid 10-digit Indian phone number starting with 6-9.")
                    else:
                        try:
                            hosp_id = add_hospital(h_reg.strip(), h_name.strip(), h_type, h_street.strip(), h_pincode, h_contact.strip() or None)
                            show_success(f"Hospital registered with ID #{hosp_id}.")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            show_db_error(e)

    if hospitals:
        df_hosps = pd.DataFrame(hospitals).rename(columns={
            "hosp_id": "ID",
            "reg_id": "Reg ID",
            "name": "Facility Name",
            "facility_type": "Facility Type",
            "street": "Street",
            "pincode": "Pincode",
            "city": "City",
            "state": "State",
            "contact": "Contact"
        })
        st.dataframe(df_hosps, use_container_width=True, hide_index=True)
    else:
        st.info("No hospitals registered yet.")

# -----------------------------------------------------------------------------
# TAB 4: AFFILIATIONS
# -----------------------------------------------------------------------------
with t4:
    st.subheader("Doctor-Hospital Affiliations")
    st.caption("Regulates which physicians can serve as lead surgeons or medical personnel at each medical centre.")

    if not is_readonly:
        with st.expander("Link Doctor to Hospital"):
            with st.form("add_affil_form"):
                ac1, ac2 = st.columns(2)
                with ac1:
                    aff_doc_id = select_from_rows(
                        "Doctor*",
                        doctors,
                        "doctor_id",
                        lambda r: f"Dr. {r['name']} (Bar ID: {r['med_bar_id']})"
                    )

                    aff_hosp_id = select_from_rows(
                        "Hospital*",
                        hospitals,
                        "hosp_id",
                        lambda r: f"{r['name']} ({r['facility_type']})"
                    )

                with ac2:
                    aff_role = st.text_input("Clinical Role*", placeholder="e.g. Senior Transplant Surgeon, Nephrologist")
                    aff_date = st.date_input("Affiliation Join Date*", value=datetime.date.today(), max_value=datetime.date.today())

                if st.form_submit_button("Link Affiliation", use_container_width=True):
                    if not aff_doc_id or not aff_hosp_id or not aff_role.strip():
                        st.error("Please fill in Doctor, Hospital, and Clinical Role.")
                    else:
                        try:
                            add_affiliation(aff_doc_id, aff_hosp_id, aff_role.strip(), aff_date)
                            show_success("Affiliation recorded.")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            show_db_error(e)

    affiliations = get_affiliations()
    if affiliations:
        df_aff = pd.DataFrame(affiliations).rename(columns={
            "doctor_id": "Doctor ID",
            "doctor_name": "Doctor Name",
            "med_bar_id": "Medical Bar ID",
            "hosp_id": "Hospital ID",
            "hospital_name": "Hospital Facility",
            "role": "Role",
            "join_date": "Join Date"
        })
        st.dataframe(df_aff, use_container_width=True, hide_index=True)
    else:
        st.info("No affiliations linked yet.")
