import io
import pandas as pd
import streamlit as st
from app_modules import db
from app_modules.utils import df_from_records

st.set_page_config(page_title="Data Admin", page_icon="🧰", layout="wide")
db.init_db()

st.title("🧰 Data Admin — Backup / Import / Maintenance")

st.subheader("Export")
c1,c2 = st.columns(2)
with c1:
    if st.button("Download CSV ZIP"):
        dfs = {
            "clients.csv": df_from_records(db.list_table("clients")),
            "tasks.csv": df_from_records(db.list_table("tasks")),
            "regions.csv": df_from_records(db.list_table("regions")),
            "industries.csv": df_from_records(db.list_table("industries")),
        }
        import zipfile, tempfile, os
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
        with zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED) as z:
            for name, df in dfs.items():
                csv_bytes = df.to_csv(index=False).encode("utf-8")
                z.writestr(name, csv_bytes)
        with open(tmp.name, "rb") as f:
            st.download_button("Download CSV Bundle", f, file_name="intertek_export.zip", mime="application/zip")
with c2:
    if st.button("Download Excel Workbook"):
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
            df_from_records(db.list_table("clients")).to_excel(writer, sheet_name="clients", index=False)
            df_from_records(db.list_table("tasks")).to_excel(writer, sheet_name="tasks", index=False)
            df_from_records(db.list_table("regions")).to_excel(writer, sheet_name="regions", index=False)
            df_from_records(db.list_table("industries")).to_excel(writer, sheet_name="industries", index=False)
        st.download_button("Download intertek.xlsx", data=out.getvalue(), file_name="intertek.xlsx")

st.divider()

st.subheader("Import")
tab1, tab2 = st.tabs(["CSV files", "Excel workbook"])

with tab1:
    st.write("Upload any of: `clients.csv`, `tasks.csv`, `regions.csv`, `industries.csv`. Unknown files are ignored.")
    csvs = st.file_uploader("Upload one or more CSVs", type=["csv"], accept_multiple_files=True)
    if csvs:
        for file in csvs:
            name = file.name.lower()
            df = pd.read_csv(file)
            if name == "industries.csv":
                for _, r in df.iterrows():
                    try:
                        db.insert("industries", {"name": r.get("name")})
                    except Exception:
                        pass
            elif name == "clients.csv":
                for _, r in df.iterrows():
                    payload = {k: r.get(k) for k in ["name","industry_id","region_id","contact_person","contact_email","contact_phone","notes","is_active"]}
                    try:
                        db.insert("clients", payload)
                    except Exception:
                        pass
            elif name == "tasks.csv":
                for _, r in df.iterrows():
                    payload = {k: r.get(k) for k in ["title","client_id","owner","priority","status","start_date","due_date","completed_date","description"]}
                    try:
                        db.insert("tasks", payload)
                    except Exception:
                        pass
            elif name == "regions.csv":
                for _, r in df.iterrows():
                    payload = {k: r.get(k) for k in ["name","country","latitude","longitude","weight","color","notes"]}
                    try:
                        db.insert("regions", payload)
                    except Exception:
                        pass
        st.success("Import complete.")

with tab2:
    xls = st.file_uploader("Upload Excel (.xlsx)", type=["xlsx"])
    if xls:
        x = pd.ExcelFile(xls)
        for sheet in x.sheet_names:
            df = x.parse(sheet)
            s = sheet.lower()
            if s == "industries":
                for _, r in df.iterrows():
                    try:
                        db.insert("industries", {"name": r.get("name")})
                    except Exception:
                        pass
            elif s == "clients":
                for _, r in df.iterrows():
                    payload = {k: r.get(k) for k in ["name","industry_id","region_id","contact_person","contact_email","contact_phone","notes","is_active"]}
                    try:
                        db.insert("clients", payload)
                    except Exception:
                        pass
            elif s == "tasks":
                for _, r in df.iterrows():
                    payload = {k: r.get(k) for k in ["title","client_id","owner","priority","status","start_date","due_date","completed_date","description"]}
                    try:
                        db.insert("tasks", payload)
                    except Exception:
                        pass
            elif s == "regions":
                for _, r in df.iterrows():
                    payload = {k: r.get(k) for k in ["name","country","latitude","longitude","weight","color","notes"]}
                    try:
                        db.insert("regions", payload)
                    except Exception:
                        pass
        st.success("Excel import complete.")

st.divider()
st.subheader("Maintenance")
if st.button("Reset ALL data (irreversible)"):
    import os
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "intertek.db"))
    try:
        os.remove(path)
        db.init_db()
        st.warning("Database reset. Default industries re-seeded.")
    except FileNotFoundError:
        db.init_db()
        st.info("New database created.")
