import streamlit as st
import db_conn
from utils.ui import render_sidebar, init_session_state
from queries.dashboard import get_summary_metrics

# Configure page
st.set_page_config(
    page_title="Organ Donation System",
    layout="wide"
)

# Render global navigation sidebar
render_sidebar()

# Main Header
st.title("Organ Donation & Transplant Management System")
st.caption("A reliable, BCNF-normalized platform ensuring transparent, compliant organ allocation and transplant tracking.")

st.markdown("""
Welcome to the **Organ Donation & Transplant Network**. This system connects registered transplant centres,
certified medical professionals, organ donors, and waiting recipients to facilitate timely, blood-compatible,
and rule-verified organ allocation while enforcing strict medical compliance constraints.
""")

st.divider()

# Headline Metrics Strip
st.subheader("System Overview")

metrics = get_summary_metrics()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(label="Total Donors", value=metrics["total_donors"])
with col2:
    st.metric(label="Available Organs", value=metrics["available_organs"])
with col3:
    st.metric(label="Active Waitlist", value=metrics["active_waitlist"])
with col4:
    st.metric(label="Transplants Completed", value=metrics["total_transplants"])

st.divider()

# How it works strip
st.subheader("How It Works")

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.info("### 1. Register\nPatients, verified donors (with legal consent), recipients, and medical staff are onboarded.")

with c2:
    st.info("### 2. Harvest & Waitlist\nOrgans are logged with viability countdowns while recipients are listed with urgency priorities.")

with c3:
    st.info("### 3. Match\nCompatible recipients are ranked algorithmically by blood group, urgency, priority, and waiting time.")

with c4:
    st.info("### 4. Transplant & Care\nAtomic execution updates records safely, followed by post-operative recovery monitoring.")

st.divider()

st.markdown("""
**Select a page from the sidebar menu to get started:**
- **Dashboard**: High-level visual metrics, outcome charts, and organ expiry alerts.
- **Patients**: Register and manage donors, recipients, and general patient profiles.
- **Organs**: Add harvested organs and monitor live viability timers.
- **Waitlist**: Manage waiting lists and update candidate priorities.
- **Matching**: Discover blood-compatible matches for available organs.
- **Transplants**: Perform atomic surgical allocation and review historical operations.
- **Recovery**: Document checkups and view patient healing trajectories.
- **Doctors & Hospitals**: Manage centres, licensed physicians, and hospital affiliations.
""")
