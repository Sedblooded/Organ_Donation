import streamlit as st
import pandas as pd
import plotly.express as px
from utils.ui import render_sidebar, require_role
from queries.dashboard import (
    get_summary_metrics,
    get_waitlist_by_organ_type,
    get_transplants_by_hospital,
    get_transplant_outcomes,
    get_transplants_per_month,
    get_expiring_organs,
    get_latest_transplants,
    get_latest_recoveries
)

st.set_page_config(page_title="Dashboard | Organ Donation", layout="wide")
render_sidebar()
require_role(["Admin", "Doctor", "Hospital Staff"])

st.title("Executive Dashboard")
st.caption("Live monitoring of organ inventory, waiting lists, surgical outcomes, and alerts.")

# Top 6 Metrics Row
metrics = get_summary_metrics()
m1, m2, m3, m4, m5, m6 = st.columns(6)
m1.metric("Total Donors", metrics["total_donors"])
m2.metric("Total Recipients", metrics["total_recipients"])
m3.metric("Available Organs", metrics["available_organs"])
m4.metric("Active Waitlist", metrics["active_waitlist"])
m5.metric("Transplants Done", metrics["total_transplants"])
m6.metric("Success Rate", f"{metrics['success_rate']}%")

st.divider()

# Alerts: Expiring Organs Panel
st.subheader("Urgent Alerts: Expiring Organs")
col_slider, _ = st.columns([1, 2])
with col_slider:
    exp_window = st.slider("Viability Threshold (Hours)", min_value=1, max_value=48, value=24, step=1)

expiring_organs = get_expiring_organs(max_hours=exp_window)
if expiring_organs:
    st.warning(f"**{len(expiring_organs)} available organ(s)** are nearing their viability limit within the next {exp_window} hours!")
    df_exp = pd.DataFrame(expiring_organs)
    df_exp = df_exp.rename(columns={
        "organ_id": "Organ ID",
        "organ_name": "Organ",
        "donor_name": "Donor",
        "blood_group": "Blood Group",
        "harvest_datetime": "Harvest Time",
        "hours_left": "Hours Left"
    })
    st.dataframe(df_exp, use_container_width=True, hide_index=True)
else:
    st.success(f"No available organs are expiring within the next {exp_window} hours.")

st.divider()

# Charts (2 Columns)
st.subheader("Network Visualizations")
col_c1, col_c2 = st.columns(2)

with col_c1:
    waitlist_data = get_waitlist_by_organ_type()
    if waitlist_data:
        df_wl = pd.DataFrame(waitlist_data)
        fig_wl = px.bar(
            df_wl,
            x="organ_name",
            y="count",
            labels={"organ_name": "Organ Type", "count": "Waitlist Candidates"},
            title="Active Waitlist Candidates by Organ Type",
            color="count",
            color_continuous_scale="Teal"
        )
        st.plotly_chart(fig_wl, use_container_width=True)
    else:
        st.info("No active waitlist data to chart.")

    outcomes_data = get_transplant_outcomes()
    if outcomes_data:
        df_out = pd.DataFrame(outcomes_data)
        fig_out = px.pie(
            df_out,
            names="outcome",
            values="count",
            title="Transplant Surgical Outcomes",
            hole=0.4,
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        st.plotly_chart(fig_out, use_container_width=True)
    else:
        st.info("No transplant outcome data.")

with col_c2:
    tx_hosp = get_transplants_by_hospital()
    if tx_hosp:
        df_th = pd.DataFrame(tx_hosp)
        fig_th = px.bar(
            df_th,
            x="hospital_name",
            y="transplant_count",
            labels={"hospital_name": "Hospital", "transplant_count": "Transplants Completed"},
            title="Transplants Completed by Hospital",
            color="transplant_count",
            color_continuous_scale="Blues"
        )
        st.plotly_chart(fig_th, use_container_width=True)
    else:
        st.info("No hospital transplant data.")

    tx_month = get_transplants_per_month()
    if tx_month:
        df_tm = pd.DataFrame(tx_month)
        fig_tm = px.line(
            df_tm,
            x="month",
            y="count",
            labels={"month": "Month", "count": "Transplants"},
            title="Transplant Volume Over Time",
            markers=True
        )
        st.plotly_chart(fig_tm, use_container_width=True)
    else:
        st.info("No monthly timeline data.")

st.divider()

# Recent Activity Tables
t1, t2 = st.tabs(["Latest 10 Transplants", "Latest 10 Recovery Checkups"])

with t1:
    txs = get_latest_transplants(limit=10)
    if txs:
        df_tx = pd.DataFrame(txs)
        st.dataframe(df_tx, use_container_width=True, hide_index=True)
    else:
        st.info("No transplants recorded yet.")

with t2:
    recs = get_latest_recoveries(limit=10)
    if recs:
        df_rc = pd.DataFrame(recs)
        st.dataframe(df_rc, use_container_width=True, hide_index=True)
    else:
        st.info("No recovery checkups logged yet.")
