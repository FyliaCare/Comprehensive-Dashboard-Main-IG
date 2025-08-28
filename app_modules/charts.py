import pandas as pd
import plotly.express as px
from .utils import coerce_date

def status_funnel(tasks_df: pd.DataFrame):
    if tasks_df.empty:
        return px.bar(pd.DataFrame({"Status": [], "Count": []}), x="Status", y="Count", title="Tasks by Status")
    agg = tasks_df.groupby("status").size().reset_index(name="Count").sort_values("Count", ascending=False)
    return px.bar(agg, x="status", y="Count", title="Tasks by Status", text="Count")

def tasks_histogram(tasks_df: pd.DataFrame, field="due_date"):
    if tasks_df.empty or field not in tasks_df.columns:
        return px.histogram(pd.DataFrame({"Date": []}), x="Date", title="Task Timeline")
    df = tasks_df.copy()
    df[field] = df[field].apply(coerce_date)
    df = df.dropna(subset=[field])
    return px.histogram(df, x=field, nbins=24, title=f"Histogram • {field.replace('_',' ').title()}" )

def workload_by_industry(tasks_df: pd.DataFrame, clients_df: pd.DataFrame, industries_df: pd.DataFrame):
    if tasks_df.empty:
        return px.bar(pd.DataFrame({"Industry": [], "Tasks": []}), x="Industry", y="Tasks", title="Workload by Industry")
    merged = tasks_df.merge(clients_df[["id","industry_id"]], left_on="client_id", right_on="id", how="left", suffixes=("","_client"))
    merged = merged.merge(industries_df[["id","name"]], left_on="industry_id", right_on="id", how="left")
    agg = merged.groupby("name").size().reset_index(name="Tasks").sort_values("Tasks", ascending=False)
    agg.rename(columns={"name":"Industry"}, inplace=True)
    return px.bar(agg, x="Industry", y="Tasks", title="Workload by Industry", text="Tasks")

def on_time_completion(tasks_df: pd.DataFrame):
    if tasks_df.empty:
        return px.pie(pd.DataFrame({"Status": [], "Count": []}), names="Status", values="Count", title="On-time vs Late")
    df = tasks_df.copy()
    df["due"] = df["due_date"].apply(coerce_date)
    df["done"] = df["completed_date"].apply(coerce_date)
    def classify(row):
        if row["status"] != "Completed" or pd.isna(row["done"]):
            return "Not Completed"
        if pd.isna(row["due"]) or row["done"] <= row["due"]:
            return "On Time"
        return "Late"
    df["cls"] = df.apply(classify, axis=1)
    agg = df.groupby("cls").size().reset_index(name="Count")
    return px.pie(agg, names="cls", values="Count", title="On-time Completion")

def overdue_trend(tasks_df: pd.DataFrame):
    if tasks_df.empty:
        return px.line(pd.DataFrame({"Date": [], "Overdue": []}), x="Date", y="Overdue", title="Overdue Trendline")
    df = tasks_df.copy()
    df["due"] = pd.to_datetime(df["due_date"], errors="coerce")
    today = pd.Timestamp.today().normalize()
    df["overdue"] = ((df["status"] != "Completed") & (df["due"].notna()) & (df["due"] < today)).astype(int)
    agg = df.groupby(df["due"].dt.date)["overdue"].sum().reset_index(name="Overdue")
    agg.rename(columns={"due":"Date"}, inplace=True)
    return px.line(agg, x="Date", y="Overdue", markers=True, title="Overdue Trendline")
