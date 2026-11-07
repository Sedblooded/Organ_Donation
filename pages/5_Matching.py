import streamlit as st
import pandas as pd
from utils.ui import render_sidebar, require_role, select_from_rows, time_remaining_badge
from queries.matching import (
    get_available_organs_for_matching,
    find_matches_for_organ,
    get_organ_summary
)

st.set_page_config(page_title="Matching | Organ Donation", layout="wide")
render_sidebar()
require_role(["Admin", "Doctor"])

st.title("Algorithmic Recipient Matching")
st.caption("Rule-governed matching pipeline: evaluates blood compatibility, clinical urgency, priority tier, and wait times.")

available_organs = get_available_organs_for_matching()

if not available_organs:
    st.info("No organs are currently in 'available' status for matching. Add harvested organs in the Organs page.")
else:
    # 1. Select Available Organ
    st.subheader("1. Select Available Organ")

    selected_organ_id = select_from_rows(
        "Available Organ Pool",
        available_organs,
        "organ_id",
        lambda r: f"Organ #{r['organ_id']} — {r['organ_name']} ({r['full_or_part']}) | Donor BG: {r['donor_blood_group']} | {r['viability_label']} ({r['donor_hospital']})",
        default_id=st.session_state.get("selected_organ_id")
    )

    if selected_organ_id:
        st.session_state["selected_organ_id"] = selected_organ_id
        summary = get_organ_summary(selected_organ_id)

        # 2. Summary Card
        st.subheader("2. Donor & Organ Profile")
        with st.container(border=True):
            sc1, sc2, sc3, sc4 = st.columns(4)
            with sc1:
                st.caption("ORGAN SPECIMEN")
                st.markdown(f"##### {summary['organ_name']} ({summary['full_or_part']})")
            with sc2:
                st.caption("DONOR BLOOD GROUP")
                st.markdown(f"##### {summary['donor_blood_group']}")
            with sc3:
                st.caption("VIABILITY STATUS")
                st.markdown(f"##### {summary['viability_label']}")
            with sc4:
                st.caption("HARVEST HOSPITAL")
                st.markdown(f"##### {summary['donor_hospital']}")

        st.divider()

        # 3. Eligible Matched Candidates Table
        st.subheader("3. Ranked Eligible Candidates")
        st.caption("Filtered by ABO blood compatibility and ranked by Clinical Priority (1=Highest) ➔ Urgency Level ➔ Waiting Duration.")

        matches = find_matches_for_organ(selected_organ_id)

        if not matches:
            st.warning("No compatible active waitlist candidates found for this organ type and blood group.")
        else:
            st.success(f"Found **{len(matches)}** eligible blood-compatible recipient(s)!")
            df_matches = pd.DataFrame(matches)

            disp_cols = [
                "rank", "waitlist_id", "recipient_name", "blood_group",
                "priority", "urgency_level", "days_waiting", "listed_at_hospital"
            ]
            df_disp = df_matches[disp_cols].rename(columns={
                "rank": "Rank",
                "waitlist_id": "Waitlist ID",
                "recipient_name": "Recipient",
                "blood_group": "Blood Group",
                "priority": "Priority",
                "urgency_level": "Urgency",
                "days_waiting": "Days Waiting",
                "listed_at_hospital": "Listed Hospital"
            })
            st.dataframe(df_disp, use_container_width=True, hide_index=True)

            st.divider()

            # 4. Proceed to Transplant Action
            st.subheader("4. Initiate Allocation")

            rec_options = [
                f"Rank #{m['rank']}: {m['recipient_name']} (BG: {m['blood_group']}, Priority: {m['priority']}, Waitlist #{m['waitlist_id']})"
                for m in matches
            ]
            chosen_match_idx = st.selectbox("Select Candidate to Allocate", range(len(matches)), format_func=lambda i: rec_options[i])
            chosen_match = matches[chosen_match_idx]

            col_btn, _ = st.columns([1, 2])
            with col_btn:
                if st.button("Proceed to Transplant Procedure", type="primary", use_container_width=True):
                    # Store selected IDs in session state for pre-filling Transplants page
                    st.session_state["selected_organ_id"] = selected_organ_id
                    st.session_state["selected_recipient_id"] = chosen_match["recipient_id"]
                    st.session_state["selected_waitlist_id"] = chosen_match["waitlist_id"]
                    st.switch_page("pages/6_Transplants.py")
