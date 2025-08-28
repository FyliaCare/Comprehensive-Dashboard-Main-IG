import streamlit as st
from app_modules import db
from app_modules.utils import df_from_records
from app_modules.charts import (
    status_funnel,
    tasks_histogram,
    workload_by_industry,
    on_time_completion,
    overdue_trend
)
import plotly.express as px

st.set_page_config(page_title="Analytics & Reports", page_icon="📈", layout="wide")
db.init_db()

st.title("📈 Executive Analytics & Reports")
st.markdown(
    "This dashboard provides a **visual overview of task performance**, workload distribution, "
    "and trends over time. The goal is to highlight **progress, risks, and opportunities** at a glance."
)

# ------------------------------------------------
# Load Data
# ------------------------------------------------
tasks = df_from_records(db.list_table("tasks"))
clients = df_from_records(db.list_table("clients"))
industries = df_from_records(db.list_table("industries"))

# ------------------------------------------------
# KPI Cards
# ------------------------------------------------
if not tasks.empty:
    total = len(tasks)
    completed = len(tasks[tasks["status"] == "Completed"])
    overdue = len(tasks[(tasks["due_date"].notna()) &
                        (tasks["status"] != "Completed")])
    in_progress = len(tasks[tasks["status"] == "In Progress"])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📌 Total Tasks", total)
    c2.metric("✅ Completed", completed)
    c3.metric("🚧 In Progress", in_progress)
    c4.metric("⚠️ Overdue", overdue)
else:
    st.info("No tasks available yet. Add tasks to see analytics.")

st.markdown("---")

# ------------------------------------------------
# Filters
# ------------------------------------------------
with st.expander("🔍 Filters", expanded=True):
    c1, c2 = st.columns(2)
    with c1:
        owner_filter = st.text_input("Filter by Owner (contains)")
    with c2:
        status_filter = st.multiselect(
            "Filter by Status",
            options=sorted(set(tasks["status"])) if not tasks.empty else [],
            default=None
        )

    if not tasks.empty:
        f = tasks.copy()
        if owner_filter:
            f = f[f["owner"].fillna("").str.contains(owner_filter, case=False)]
        if status_filter:
            f = f[f["status"].isin(status_filter)]
    else:
        f = tasks

st.markdown("---")

# ------------------------------------------------
# Section 1: Task Progress
# ------------------------------------------------
st.subheader("📌 Task Status & Completion Performance")

c1, c2 = st.columns(2)
with c1:
    fig1 = status_funnel(f)
    fig1.update_traces(marker=dict(color=["#4CAF50", "#2196F3", "#FFC107", "#F44336"]))  # green, blue, amber, red
    st.plotly_chart(fig1, use_container_width=True)
    st.caption("**Task Status Funnel** – Visualizes the flow of tasks across statuses. "
               "Green = Completed, Red = Overdue, Blue = In Progress, Amber = Pending.")

with c2:
    fig2 = on_time_completion(f)
    fig2.update_traces(marker_colors=["#4CAF50", "#F44336"])  # green vs red
    st.plotly_chart(fig2, use_container_width=True)
    st.caption("**On-Time Completion** – Proportion of tasks finished on time (green) vs late (red). "
               "A higher green share means better discipline and accountability.")

st.markdown("---")

# ------------------------------------------------
# Section 2: Timeline Distribution
# ------------------------------------------------
st.subheader("📅 Task Timelines")

c3, c4 = st.columns(2)
with c3:
    fig3 = tasks_histogram(f, field="start_date")
    fig3.update_traces(marker_color="#2196F3")  # blue
    st.plotly_chart(fig3, use_container_width=True)
    st.caption("**Start Dates** – When tasks are typically launched. "
               "Helps spot project kickoff spikes.")

with c4:
    fig4 = tasks_histogram(f, field="due_date")
    fig4.update_traces(marker_color="#FF9800")  # orange
    st.plotly_chart(fig4, use_container_width=True)
    st.caption("**Due Dates** – Task deadlines over time. "
               "Orange peaks signal heavy delivery periods that may need extra resources.")

st.markdown("---")

# ------------------------------------------------
# Section 3: Trends
# ------------------------------------------------
st.subheader("📈 Performance Trends")

fig5 = overdue_trend(f)
fig5.update_traces(line_color="red", line=dict(width=3))
st.plotly_chart(fig5, use_container_width=True)
st.caption("**Overdue Task Trend** – Red line tracks overdue tasks over time. "
           "A downward trend = improved performance. An upward spike = risk building up.")

st.markdown("---")

# ------------------------------------------------
# Section 4: Workload Distribution
# ------------------------------------------------
st.subheader("🏭 Workload by Industry")

fig6 = workload_by_industry(f, clients, industries)
fig6.update_traces(marker=dict(color=px.colors.qualitative.Set2))  # soft pastel palette
st.plotly_chart(fig6, use_container_width=True)
st.caption("**Workload Distribution** – How tasks are spread across industries. "
           "This helps identify sectors with the heaviest workload and where focus is needed.")
