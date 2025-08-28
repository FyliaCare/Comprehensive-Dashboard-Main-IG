import pandas as pd
from dateutil import parser
from datetime import datetime, date

STATUSES = ["Open", "In Progress", "Completed", "Blocked"]
PRIORITIES = ["Low", "Medium", "High", "Critical"]

def coerce_date(x):
    if not x:
        return None
    if isinstance(x, (datetime, date)):
        return x
    try:
        return parser.parse(str(x)).date()
    except Exception:
        return None

def df_from_records(records):
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records)
