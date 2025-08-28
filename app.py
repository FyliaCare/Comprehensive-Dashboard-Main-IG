import os
import streamlit as st
from app_modules import db
from app_modules.utils import df_from_records
from datetime import datetime

st.set_page_config(page_title="Intertek Executive Insights", page_icon="📊", layout="wide")

db.init_db()

with open(os.path.join("assets","styles.css"), "r", encoding="utf-8") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.sidebar.title("Intertek Executive Insights")
st.sidebar.success("Data is **persisted** in SQLite.")
st.sidebar.divider()
st.sidebar.caption("Tip: Use the **Data Admin** page to back up or import CSV/Excel.")

st.title("📊 Executive Overview")

clients = df_from_records(db.list_table("clients", "WHERE is_active=1"))
tasks = df_from_records(db.list_table("tasks"))
regions = df_from_records(db.list_table("regions"))

open_tasks = (tasks["status"] != "Completed").sum() if not tasks.empty else 0
completed = (tasks["status"] == "Completed").sum() if not tasks.empty else 0
overdue = 0
if not tasks.empty and "due_date" in tasks.columns:
    from dateutil import parser
    today = datetime.utcnow().date()
    def is_overdue(row):
        try:
            due = parser.parse(str(row["due_date"])).date() if row["due_date"] else None
        except Exception:
            due = None
        return (row["status"] != "Completed") and bool(due and due < today)
    overdue = tasks.apply(is_overdue, axis=1).sum()

c1,c2,c3,c4 = st.columns(4)
c1.metric("Active Clients", int(len(clients)))
c2.metric("Open Tasks", int(open_tasks))
c3.metric("Completed", int(completed))
c4.metric("Overdue", int(overdue))

st.write("---")
st.subheader("Quick Actions")
qc1,qc2,qc3 = st.columns(3)
with qc1:
    st.page_link("pages/01_Clients.py", label="Manage Clients", icon="👥")
with qc2:
    st.page_link("pages/02_Tasks.py", label="Manage Tasks", icon="✅")
with qc3:
    st.page_link("pages/03_Analytics.py", label="Analytics & Reports", icon="📈")

st.write("")
st.info("Use the sidebar to navigate pages. All changes are saved immediately to `data/intertek.db`.")
