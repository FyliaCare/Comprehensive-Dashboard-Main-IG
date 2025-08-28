import streamlit as st
from datetime import date
from app_modules import db
from app_modules.utils import df_from_records, STATUSES, PRIORITIES

st.set_page_config(page_title="Tasks", page_icon="✅", layout="wide")
db.init_db()

st.title("✅ Action Points / Tasks")

# -------------------------------
# Add Task Form
# -------------------------------
clients = db.list_table("clients", "WHERE is_active=1")
client_options = [(None, "— None —")] + [(c["id"], c["name"]) for c in clients]

with st.expander("➕ Add Task", expanded=False):
    with st.form("add_task"):
        title = st.text_input("Title*", placeholder="E.g., 'Safety Audit — Refinery A'")
        client = st.selectbox("Client", options=client_options, index=0, format_func=lambda x: x[1])
        owner = st.text_input("Owner / Assignee")
        priority = st.selectbox("Priority", options=PRIORITIES, index=1)
        status = st.selectbox("Status", options=STATUSES, index=0)
        c1,c2,c3 = st.columns(3)
        with c1:
            start_date = st.date_input("Start Date", value=None)
        with c2:
            due_date = st.date_input("Due Date", value=None)
        with c3:
            completed_date = st.date_input("Completed Date", value=None)
        description = st.text_area("Description / Notes", height=120)
        submitted = st.form_submit_button("Create Task")
        if submitted:
            if not title.strip():
                st.error("Title is required.")
            else:
                payload = {
                    "title": title.strip(),
                    "client_id": client[0],
                    "owner": owner.strip() or None,
                    "priority": priority,
                    "status": status,
                    "start_date": str(start_date) if start_date else None,
                    "due_date": str(due_date) if due_date else None,
                    "completed_date": str(completed_date) if completed_date else None,
                    "description": description or None,
                }
                try:
                    db.insert("tasks", payload)
                    st.success("Task created.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

st.divider()

# -------------------------------
# Checklist Display
# -------------------------------
tasks = df_from_records(db.list_table("tasks"))
if tasks.empty:
    st.warning("No tasks yet. Add a task above.")
else:
    st.subheader("📋 Task Checklist")

    for _, row in tasks.iterrows():
        is_done = row["status"] == "Completed"
        new_state = st.checkbox(
            f"{row['title']}  —  (Owner: {row.get('owner') or 'Unassigned'}, Priority: {row.get('priority')})",
            value=is_done,
            key=f"task_{row['id']}"
        )
        if new_state != is_done:
            if new_state:
                db.update("tasks", int(row["id"]), {
                    "status": "Completed",
                    "completed_date": str(date.today())
                })
                st.success(f"Marked '{row['title']}' as Completed.")
            else:
                db.update("tasks", int(row["id"]), {
                    "status": "Open",
                    "completed_date": None
                })
                st.info(f"Reopened '{row['title']}'.")
            st.rerun()

    st.divider()

    # -------------------------------
    # Full Data Table
    # -------------------------------
    st.dataframe(
        tasks.drop(columns=["created_at","updated_at"]),
        use_container_width=True,
        hide_index=True
    )

    # -------------------------------
    # Edit / Update Section
    # -------------------------------
        # -------------------------------
    # Edit / Update Section (Collapsible)
    # -------------------------------
    with st.expander("✏️ Edit / Update Task", expanded=False):
        ids = tasks["id"].tolist()
        target_id = st.selectbox(
            "Select Task",
            options=ids,
            format_func=lambda i: tasks.loc[tasks["id"]==i, "title"].values[0] if i in ids else "-"
        )
        if target_id:
            row = tasks[tasks["id"]==target_id].iloc[0]
            with st.form("edit_task"):
                title = st.text_input("Title*", value=row["title"])
                client = st.selectbox("Client", options=client_options,
                                      index= next((i for i,x in enumerate(client_options) if x[0]==row.get("client_id")), 0),
                                      format_func=lambda x: x[1])
                owner = st.text_input("Owner / Assignee", value=row.get("owner") or "")
                priority = st.selectbox("Priority", options=PRIORITIES,
                                        index=PRIORITIES.index(row.get("priority","Medium")) if row.get("priority") in PRIORITIES else 1)
                status = st.selectbox("Status", options=STATUSES,
                                      index=STATUSES.index(row.get("status","Open")) if row.get("status") in STATUSES else 0)
                c1,c2,c3 = st.columns(3)
                with c1:
                    start_date = st.date_input("Start Date", value=row.get("start_date"))
                with c2:
                    due_date = st.date_input("Due Date", value=row.get("due_date"))
                with c3:
                    completed_date = st.date_input("Completed Date", value=row.get("completed_date"))
                description = st.text_area("Description / Notes", value=row.get("description") or "", height=120)
                c1,c2,c3 = st.columns(3)
                with c1:
                    if st.form_submit_button("Save Changes"):
                        payload = {
                            "title": title.strip(),
                            "client_id": client[0],
                            "owner": owner.strip() or None,
                            "priority": priority,
                            "status": status,
                            "start_date": str(start_date) if start_date else None,
                            "due_date": str(due_date) if due_date else None,
                            "completed_date": str(completed_date) if completed_date else None,
                            "description": description or None,
                        }
                        db.update("tasks", int(target_id), payload)
                        st.success("Updated.")
                with c2:
                    if st.form_submit_button("Mark Completed Today"):
                        db.update("tasks", int(target_id), {"status": "Completed", "completed_date": str(date.today())})
                        st.success("Marked completed.")
                with c3:
                    if st.form_submit_button("Delete Task"):
                        db.delete("tasks", int(target_id))
                        st.warning("Deleted.")
