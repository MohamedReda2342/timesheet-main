# ./pages/employee_timesheet_entry.py
import streamlit as st
import datetime
import requests
from lib import auth, employee_queries as eq

# ================================================================
# 🛠️ Utility Functions
# ================================================================

def get_egypt_holidays(year=None):
    if not year:
        year = datetime.date.today().year
    url = f"https://date.nager.at/api/v3/PublicHolidays/{year}/EG"
    try:
        res = requests.get(url, timeout=2)
        if res.status_code == 200:
            data = res.json()
            return {datetime.date.fromisoformat(item["date"]) for item in data}
        return set()
    except Exception:
        return set()

def parse_hhmm_to_hours(txt):
    """
    Strictly parses input to integer-only hours. 
    Returns float X.0 for compatibility.
    """
    if not txt: return 0.0
    try:
        txt = str(txt).strip()
        # Reject decimals or colons
        if "." in txt or ":" in txt:
            return 0.0 
        
        val = int(txt)
        return float(val)
    except (ValueError, TypeError):
        return 0.0

def format_hours_to_hhmm(hours):
    """Formats float hours to integer string."""
    if not hours or float(hours) <= 0: return ""
    return str(int(hours))

# ================================================================
# 🔐 Page Setup
# ================================================================
st.set_page_config(page_title="Weekly Timesheet", layout="wide")
auth.login_required(roles=["user", "admin", "approver"])

user_info = auth.get_current_user()
user_id = user_info["user_id"]

# ================================================================
# 🔄 Logic
# ================================================================

def load_week_data(user_id, start_date, end_date):
    assigned_tasks = eq.fetch_assigned_tasks_for_week(user_id, start_date, end_date)
    existing_entries = eq.fetch_entries_for_week(user_id, start_date)

    all_rows_map = {}

    # 1. Build Map from Assignments
    for t in assigned_tasks:
        key = t["AssignmentId"]
        all_rows_map[key] = {
            "AssignmentId": t["AssignmentId"],
            "assignment_name": t.get("assignment_name", "Assignment"),
            "assignment_status": t.get("assignment_status", "active"),
            "project_id": t["project_id"],
            "task_id": t["task_id"],
            "project_name": t["project_name"],
            "task_name": t["task_name"],
            "hours": {},
            "status": "draft",
        }

    # 2. Overlay DB Entries
    for e in existing_entries:
        aid = e.get("AssignmentId")
        key = aid
        
        hours = {
            "sunday": format_hours_to_hhmm(e.get("sunday_hours")),
            "monday": format_hours_to_hhmm(e.get("monday_hours")),
            "tuesday": format_hours_to_hhmm(e.get("tuesday_hours")),
            "wednesday": format_hours_to_hhmm(e.get("wednesday_hours")),
            "thursday": format_hours_to_hhmm(e.get("thursday_hours")),
            "friday": format_hours_to_hhmm(e.get("friday_hours")),
            "saturday": format_hours_to_hhmm(e.get("saturday_hours")),
        }

        if key and key in all_rows_map:
            all_rows_map[key]["hours"] = hours
            all_rows_map[key]["status"] = e["status"]
        elif not key:
            # Legacy entry fallback
            found = False
            for k, val in all_rows_map.items():
                if val["project_id"] == e["project_id"] and val["task_id"] == e["task_id"]:
                    val["hours"] = hours
                    val["status"] = e["status"]
                    found = True
                    break
            if not found:
                ghost_key = f"ghost_{e['entry_id']}"
                all_rows_map[ghost_key] = {
                    "AssignmentId": None,
                    "assignment_name": "(Legacy/Removed)",
                    "assignment_status": "inactive",
                    "project_id": e["project_id"],
                    "task_id": e["task_id"],
                    "project_name": e["project_name"],
                    "task_name": e["task_name"],
                    "hours": hours,
                    "status": e["status"],
                }

    st.session_state["timesheet_rows"] = sorted(all_rows_map.values(), key=lambda x: (x["project_name"], x["assignment_name"]))

def handle_save(status_type):
    day_keys = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
    rows_to_save = st.session_state.get("timesheet_rows", [])
    
    if not rows_to_save:
        st.warning("No tasks assigned.")
        return

    weekly_total = 0.0
    for row in rows_to_save:
        for day in day_keys:
             # Validation: Check if input is valid integer string
             raw_val = str(row.get("hours", {}).get(day, "")).strip()
             if raw_val:
                 if not raw_val.isdigit():
                     st.error(f"❌ Invalid input '{raw_val}' for {row['assignment_name']}. Only whole numbers allowed.")
                     return
             
             val = parse_hhmm_to_hours(raw_val)
             weekly_total += val
    
    if weekly_total > 40.0:
        st.error(f"❌ Limit Exceeded: You have logged **{int(weekly_total)} hours**. Maximum allowed is 40 hours/week.")
        return

    try:
        for row in rows_to_save:
            data = {
                "user_id": user_id,
                "AssignmentId": row.get("AssignmentId"),
                "project_id": row["project_id"],
                "task_id": row["task_id"],
                "week_start_date": st.session_state["ts_week_start"],
                "status": status_type,
            }
            for day in day_keys:
                data[day] = parse_hhmm_to_hours(row.get("hours", {}).get(day, "0"))
            
            eq.upsert_weekly_entry(data)
            
        st.success(f"✅ Timesheet {status_type}.")
        st.rerun()
    except Exception as e:
        st.error(f"❌ Error saving: {e}")

# ================================================================
# 🎨 Main UI
# ================================================================

if "ts_week_start" not in st.session_state:
    today = datetime.date.today()
    st.session_state["ts_week_start"] = today - datetime.timedelta(days=today.weekday())

start_date = st.session_state["ts_week_start"]
end_date = start_date + datetime.timedelta(days=6)

st.title("📅 Weekly Timesheet")
st.write(f"User: **{user_info['full_name']}**")

c1, c2, c3 = st.columns([1, 4, 1])
if c1.button("◀ Prev"):
    st.session_state["ts_week_start"] -= datetime.timedelta(days=7)
    st.rerun()
c2.markdown(f"<h3 style='text-align: center'>{start_date.strftime('%d %b')} - {end_date.strftime('%d %b %Y')}</h3>", unsafe_allow_html=True)
if c3.button("Next ▶"):
    st.session_state["ts_week_start"] += datetime.timedelta(days=7)
    st.rerun()

try:
    week_status = eq.get_week_status(user_id, start_date)
except Exception as e:
    st.error(f"DB Error: {e}")
    week_status = "draft"

status_colors = {"draft": "grey", "submitted": "blue", "approved": "green", "rejected": "red"}
st.markdown(f"**Status:** <span style='color:{status_colors.get(week_status, 'black')}'>**{week_status.upper()}**</span>", unsafe_allow_html=True)

if week_status == "rejected":
    reason = eq.get_latest_rejection_reason(user_id, start_date)
    st.error(f"🚫 **Rejection Reason:** {reason}")

load_week_data(user_id, start_date, end_date)
rows = st.session_state["timesheet_rows"]
holidays = get_egypt_holidays(start_date.year)

# Fetch Vacations
vacations_raw = eq.fetch_approved_vacations_for_week(user_id, start_date, end_date)
vacation_dates = set()
for v in vacations_raw:
    v_start = v.get('From')
    v_end = v.get('To')
    
    # Robust conversion to date objects
    if isinstance(v_start, datetime.datetime): v_start = v_start.date()
    if isinstance(v_end, datetime.datetime): v_end = v_end.date()
    
    if v_start and v_end:
        delta = v_end - v_start
        for i in range(delta.days + 1):
            vacation_dates.add(v_start + datetime.timedelta(days=i))

# Grid Header
day_names = [(start_date + datetime.timedelta(days=i)).strftime("%a %d") for i in range(7)]
cols_spec = [3, 2, 2] + [1]*7 + [1] 
header = st.columns(cols_spec)
header[0].write("**Assignment**")
header[1].write("**Task**")
header[2].write("**Project**")
for i, d in enumerate(day_names):
    header[3+i].write(f"**{d}**")
header[-1].write("**Total**")

st.markdown("---")

# Grid Rows
day_keys = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
grand_total = 0.0
day_totals = {d: 0.0 for d in day_keys}

for idx, row in enumerate(rows):
    c = st.columns(cols_spec)
    
    assign_status = row.get('assignment_status', 'active').lower()
    assign_name = row.get('assignment_name', '-')
    
    status_icon = ""
    if assign_status == "hold": status_icon = "⏸️"
    elif assign_status == "completed": status_icon = "✅"
    
    c[0].write(f"{assign_name} {status_icon}")
    c[1].caption(row['task_name'])
    c[2].caption(row['project_name'])
    
    row_sum = 0.0
    row_disabled = (assign_status != 'active')
    
    for i, day in enumerate(day_keys):
        current_date = start_date + datetime.timedelta(days=i)
        val = row["hours"].get(day, "")
        
        disabled = (week_status in ["submitted", "approved"]) or row_disabled
        is_holiday = (current_date in holidays)
        is_vacation = (current_date in vacation_dates)
        
        if is_vacation:
            c[3+i].write("✈️")
            if not disabled: 
                row["hours"][day] = "0" # Logic reset
        elif is_holiday:
            c[3+i].write("🏖️")
            if not disabled: 
                row["hours"][day] = "0"
        else:
            new_val = c[3+i].text_input(
                f"h_{idx}_{day}", 
                value=val, 
                label_visibility="collapsed",
                disabled=disabled,
                placeholder="-" if row_disabled else "0"
            )
            if not disabled:
                row["hours"][day] = new_val
            
            hrs = parse_hhmm_to_hours(new_val)
            row_sum += hrs
            day_totals[day] += hrs
            
    c[-1].write(f"**{int(row_sum)}**")
    grand_total += row_sum

# Footer
st.markdown("---")
f = st.columns(cols_spec)
f[0].write("**TOTALS**")
for i, day in enumerate(day_keys):
    f[3+i].write(f"**{int(day_totals[day])}**")
f[-1].write(f"**{int(grand_total)}**")

# Actions
st.write("")
ac1, ac2, _ = st.columns([1, 1, 6])
if week_status in ["draft", "rejected"]:
    if ac1.button("💾 Save Draft", use_container_width=True):
        handle_save("draft")
    if ac2.button("🚀 Submit Week", type="primary", use_container_width=True):
        handle_save("submitted")
elif week_status == "submitted":
    st.info("Timesheet submitted.")
elif week_status == "approved":
    st.success("Timesheet approved.")