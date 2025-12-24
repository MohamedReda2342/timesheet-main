# ./views/employee_timesheet.py
import streamlit as st
import datetime
from lib import employee_queries as eq
from lib import auth
from utils.state_helpers import track_page_visit

track_page_visit("employee_timesheet")
user = auth.get_current_user()
user_id = user["user_id"]

# --- Dialogs ---
@st.dialog("📋 Assignment Details")
def show_assignment_details(data):
    st.subheader(f"{data['assignment_name'] or 'Assignment Details'}")
    
    st.markdown(f"""
    | Field | Value |
    | :--- | :--- |
    | **Project** | {data['project_name']} |
    | **Task** | {data['task_name']} |
    | **Dates** | {data['assign_start']} to {data['assign_end'] or 'Ongoing'} |
    """)
    
    st.markdown("### 📝 Notes")
    st.info(data['notes'] or "No notes provided.")

# --- Helpers ---
def get_valid_assignments_map(user_id, start, end):
    raw_list = eq.fetch_assigned_tasks_for_week(user_id, start, end)
    assignments_map = {}
    for a in raw_list:
        label = f"{a['project_name']} - {a['task_name']}"
        if a.get('assignment_name'):
            label += f" ({a['assignment_name']})"
        assignments_map[a['AssignmentId']] = {
            "label": label,
            "project_id": a["project_id"],
            "project_name": a["project_name"],
            "task_id": a["task_id"],
            "task_name": a["task_name"],
            "assignment_name": a.get("assignment_name"),
            "notes": a.get("notes"),
            "assign_start": a.get("assign_start"),
            "assign_end": a.get("assign_end")
        }
    return assignments_map

def init_rows(user_id, start_date, valid_map):
    if "ts_rows" not in st.session_state:
        entries = eq.fetch_entries_for_week(user_id, start_date)
        rows = []
        for e in entries:
            aid = e.get("AssignmentId")
            pid = e["project_id"]
            tid = e["task_id"]
            if not aid:
                for valid_aid, details in valid_map.items():
                    if details["project_id"] == pid and details["task_id"] == tid:
                        aid = valid_aid
                        break
            rows.append({
                "assignment_id": aid, "project_id": pid, "task_id": tid,
                "sunday": e.get("sunday_hours", 0.0), "monday": e.get("monday_hours", 0.0),
                "tuesday": e.get("tuesday_hours", 0.0), "wednesday": e.get("wednesday_hours", 0.0),
                "thursday": e.get("thursday_hours", 0.0), "friday": e.get("friday_hours", 0.0),
                "saturday": e.get("saturday_hours", 0.0),
            })
        if not rows:
            rows.append(create_empty_row())
        st.session_state.ts_rows = rows

def create_empty_row():
    return {
        "assignment_id": None, "project_id": None, "task_id": None,
        "sunday": 0.0, "monday": 0.0, "tuesday": 0.0, "wednesday": 0.0,
        "thursday": 0.0, "friday": 0.0, "saturday": 0.0
    }

def add_row():
    st.session_state.ts_rows.append(create_empty_row())

def remove_row(index):
    st.session_state.ts_rows.pop(index)

def update_row_value(index, key, value):
    st.session_state.ts_rows[index][key] = value

def save_timesheet(status, user_id, start_date):
    days = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
    total_hours = 0
    clean_data = []
    
    for r in st.session_state.ts_rows:
        if not r.get('assignment_id'):
            continue
        row_sum = sum([r[d] for d in days])
        total_hours += row_sum
        entry = {
            "user_id": user_id,
            "week_start_date": start_date,
            "status": status,
            "project_id": r['project_id'],
            "task_id": r['task_id'],
            "AssignmentId": r['assignment_id'],
            "sunday": r['sunday'], "monday": r['monday'], "tuesday": r['tuesday'],
            "wednesday": r['wednesday'], "thursday": r['thursday'], "friday": r['friday'],
            "saturday": r['saturday']
        }
        clean_data.append(entry)

    if total_hours > 40.0:
        st.error(f"❌ Limit Exceeded: {total_hours} hours logged. Max 40 allowed.")
        return

    try:
        if not clean_data and status == 'submitted':
             st.error("Cannot submit empty timesheet.")
             return
        for data in clean_data:
            eq.upsert_weekly_entry(data)
        st.success(f"✅ Timesheet {status} successfully.")
        del st.session_state[f"loaded_{user_id}_{start_date}"]
        st.rerun()
    except Exception as e:
        st.error(f"Error saving: {e}")

# --- Logic ---

if "ts_week_start" not in st.session_state:
    today = datetime.date.today()
    st.session_state["ts_week_start"] = today - datetime.timedelta(days=today.weekday())

start_date = st.session_state["ts_week_start"]
end_date = start_date + datetime.timedelta(days=6)

valid_assignments_map = get_valid_assignments_map(user_id, start_date, end_date)

state_key = f"loaded_{user_id}_{start_date}"
if state_key not in st.session_state:
    if "ts_rows" in st.session_state: del st.session_state.ts_rows
    st.session_state[state_key] = True

init_rows(user_id, start_date, valid_assignments_map)

st.title("📅 Weekly Timesheet")

c1, c2, c3 = st.columns([1, 4, 1])
if c1.button("◀ Prev"):
    st.session_state["ts_week_start"] -= datetime.timedelta(days=7)
    del st.session_state[state_key]
    st.rerun()

c2.markdown(f"<h3 style='text-align: center'>{start_date.strftime('%d %b')} - {end_date.strftime('%d %b %Y')}</h3>", unsafe_allow_html=True)

if c3.button("Next ▶"):
    st.session_state["ts_week_start"] += datetime.timedelta(days=7)
    del st.session_state[state_key]
    st.rerun()

week_status = eq.get_week_status(user_id, start_date)
status_colors = {"draft": "grey", "submitted": "blue", "approved": "green", "rejected": "red"}
st.markdown(f"**Status:** <span style='color:{status_colors.get(week_status, 'black')}'>**{week_status.upper()}**</span>", unsafe_allow_html=True)

if week_status == "rejected":
    reason = eq.get_latest_rejection_reason(user_id, start_date)
    st.error(f"🚫 **Action Required: Timesheet Rejected**\n\n**Reason:** {reason}")

is_editable = week_status in ["draft", "rejected"]

st.markdown("---")

# Headers - UPDATED LAYOUT
# Removing Project/Task columns, Adding 'Info' column
# Grid: Assignment (3.5), Info (0.5), 7 Days (0.8 each), Delete (0.5)
h_cols = st.columns([3.5, 0.5, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.5])
headers = ["Assignment", "Info", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", ""]
for col, h in zip(h_cols, headers):
    col.write(f"**{h}**")

days = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]

for i, row in enumerate(st.session_state.ts_rows):
    cols = st.columns([3.5, 0.5, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.5])
    
    curr_aid = row.get("assignment_id")
    assign_opts = valid_assignments_map.copy()
    if curr_aid and curr_aid not in assign_opts:
        assign_opts[curr_aid] = {"label": "(Inactive)", "project_name": "Unknown", "task_name": "Unknown"}

    selected_aid = cols[0].selectbox(
        f"assign_{i}", options=list(assign_opts.keys()), 
        format_func=lambda x: assign_opts[x]["label"],
        key=f"assign_dd_{i}",
        index=list(assign_opts.keys()).index(curr_aid) if curr_aid in assign_opts else None,
        label_visibility="collapsed", disabled=not is_editable
    )
    
    if selected_aid != curr_aid:
        update_row_value(i, "assignment_id", selected_aid)
        if selected_aid:
            details = assign_opts[selected_aid]
            update_row_value(i, "project_id", details.get("project_id"))
            update_row_value(i, "task_id", details.get("task_id"))
        st.rerun()

    # 2. View Info Button
    # Only enabled if assignment is selected
    if selected_aid:
        if cols[1].button("ℹ️", key=f"inf_{i}", help="View Project/Task Details"):
            show_assignment_details(assign_opts[selected_aid])
    else:
         cols[1].write("") # Spacer

    # 3. Days Inputs
    for d_idx, day in enumerate(days):
        val = cols[d_idx + 2].number_input(
            f"{day}_{i}", min_value=0.0, max_value=24.0, step=0.5,
            value=float(row.get(day, 0.0)), key=f"{day}_num_{i}",
            label_visibility="collapsed", disabled=not is_editable
        )
        if val != row.get(day):
            update_row_value(i, day, val)

    if is_editable:
        if cols[9].button("🗑️", key=f"del_{i}"):
            remove_row(i)
            st.rerun()

if is_editable:
    if st.button("➕ Add Row"):
        add_row()
        st.rerun()

st.write("---")
grand_total = sum([sum([row[d] for d in days]) for row in st.session_state.ts_rows])
st.caption(f"**Total Weekly Hours:** {grand_total:.2f}")

# Check previous week status
prev_week_start = start_date - datetime.timedelta(days=7)
prev_week_status = eq.get_week_status(user_id, prev_week_start)
can_submit = True

# Logic: Only block if previous week is Rejected OR (Draft AND has actual saved entries)
# This prevents blocking new employees who have no history for the previous week.
if prev_week_status == "rejected":
    st.warning(f"⚠️ You cannot submit this week until the previous week ({prev_week_start.strftime('%d %b')}) is submitted (Status: Rejected).")
    can_submit = False
elif prev_week_status == "draft":
    # Check if this is a "real" draft (has data) or just empty history
    prev_week_entries = eq.fetch_entries_for_week(user_id, prev_week_start)
    if prev_week_entries:
        st.warning(f"⚠️ You cannot submit this week until the previous week ({prev_week_start.strftime('%d %b')}) is submitted.")
        can_submit = False

c_save, c_submit, _ = st.columns([1, 1, 5])

if is_editable:
    if c_save.button("💾 Save Draft"):
        save_timesheet("draft", user_id, start_date)
        
    if c_submit.button("🚀 Submit", type="primary", disabled=not can_submit):
        save_timesheet("submitted", user_id, start_date)
elif week_status == "submitted":
    st.info("Submitted - Waiting for approval.")

    