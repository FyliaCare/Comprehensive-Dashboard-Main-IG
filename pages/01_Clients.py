import streamlit as st
from app_modules import db
from app_modules.utils import df_from_records

st.set_page_config(page_title="Clients", page_icon="👥", layout="wide")
db.init_db()

st.title("👥 Clients")

industries = db.list_table("industries")
regions = db.list_table("regions")

# ------------------------------------------------
# Add Client Form
# ------------------------------------------------
with st.expander("➕ Add New Client", expanded=False):
    with st.form("add_client"):
        name = st.text_input("Client Name*", placeholder="Company Ltd.")
        industry = st.selectbox(
            "Industry",
            options=[(i["id"], i["name"]) for i in industries],
            format_func=lambda x: x[1] if isinstance(x, tuple) else x,
            index=None
        )
        region = st.selectbox(
            "Region (optional)",
            options=[(r["id"], f'{r["name"]} ({r["country"] or "-"})') for r in regions],
            format_func=lambda x: x[1] if isinstance(x, tuple) else x,
            index=None
        )
        contact_person = st.text_input("Contact Person")
        contact_email = st.text_input("Contact Email")
        contact_phone = st.text_input("Contact Phone")
        notes = st.text_area("Notes")

        submitted = st.form_submit_button("Create Client")
        if submitted:
            if not name.strip():
                st.error("Name is required.")
            else:
                payload = {
                    "name": name.strip(),
                    "industry_id": industry[0] if industry else None,
                    "region_id": region[0] if region else None,
                    "contact_person": contact_person.strip() or None,
                    "contact_email": contact_email.strip() or None,
                    "contact_phone": contact_phone.strip() or None,
                    "notes": notes or None,
                    "is_active": 1
                }
                try:
                    db.insert("clients", payload)
                    st.success("Client created.")
                except Exception as e:
                    st.error(f"Error: {e}")

st.divider()

# ------------------------------------------------
# Clients List & Edit
# ------------------------------------------------
clients = df_from_records(db.list_table("clients"))
if clients.empty:
    st.warning("No clients yet. Add your first client above.")
else:
    st.dataframe(clients.drop(columns=["created_at", "updated_at"]), use_container_width=True, hide_index=True)

    # Wrap edit section in expander
    with st.expander("✏️ Edit / Archive Client", expanded=False):
        ids = clients["id"].tolist()
        target_id = st.selectbox(
            "Select Client",
            options=ids,
            format_func=lambda i: clients.loc[clients["id"] == i, "name"].values[0] if i in ids else "-"
        )

        if target_id:
            row = clients[clients["id"] == target_id].iloc[0]
            with st.form("edit_client"):
                name = st.text_input("Client Name*", value=row["name"])
                industry = st.selectbox(
                    "Industry",
                    options=[(i["id"], i["name"]) for i in industries],
                    format_func=lambda x: x[1],
                    index=([i["id"] for i in industries].index(row["industry_id"]) if row["industry_id"] in [i["id"] for i in industries] else 0)
                )
                region_opts = [(None, "— None —")] + [(r["id"], f'{r["name"]} ({r["country"] or "-"})') for r in regions]
                region_idx = 0
                for idx, opt in enumerate(region_opts):
                    if opt[0] == row["region_id"]:
                        region_idx = idx
                region = st.selectbox("Region", options=region_opts, index=region_idx, format_func=lambda x: x[1])
                contact_person = st.text_input("Contact Person", value=row.get("contact_person") or "")
                contact_email = st.text_input("Contact Email", value=row.get("contact_email") or "")
                contact_phone = st.text_input("Contact Phone", value=row.get("contact_phone") or "")
                notes = st.text_area("Notes", value=row.get("notes") or "")
                is_active = st.checkbox("Active", value=bool(row["is_active"]))

                c1, c2, c3 = st.columns(3)
                with c1:
                    if st.form_submit_button("Save Changes"):
                        payload = {
                            "name": name.strip(),
                            "industry_id": industry[0],
                            "region_id": region[0],
                            "contact_person": contact_person.strip() or None,
                            "contact_email": contact_email.strip() or None,
                            "contact_phone": contact_phone.strip() or None,
                            "notes": notes or None,
                            "is_active": 1 if is_active else 0
                        }
                        db.update("clients", int(target_id), payload)
                        st.success("Updated.")
                with c2:
                    if st.form_submit_button("Archive (Deactivate)"):
                        db.update("clients", int(target_id), {"is_active": 0})
                        st.info("Client archived.")
                with c3:
                    if st.form_submit_button("Delete Permanently"):
                        db.delete("clients", int(target_id))
                        st.warning("Deleted.")
