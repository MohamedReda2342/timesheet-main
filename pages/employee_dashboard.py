import streamlit as st
import datetime
import pandas as pd
from lib import auth, employee_queries as eq
from utils.state_helpers import track_page_visit

# ================================================================
# 🛠️ Helpers
# ================================================================

def parse_val(val):
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0

def get_valid_assignments_map(user_id, start, end):
    """
    Returns a dictionary mapping AssignmentId -> {Details}
    """
    raw_list = eq.fetch_assigned_tasks_for_week(user_id, start, end)
    assignments_map = {}
    
    for a in raw_list:
        # Create a display label: "Project - Task (Role)"
        label = f"{a['project_name']} - {a['task_name']}"
        if a.get('assignment_name'):
            label += f" ({a['assignment_name']})"
            
        assignments_map[a['AssignmentId']] = {
            "label": label,
            "project_id": a["project_id"],
            "project_name": a["project_name"],
            "task_id": a["task_id"],
            "task_name": a["task_name"],
            "assignment_name": a.get("assignment_name")
        }
            
    return assignments_map

# ================================================================
# 🔄 State Management
# ================================================================

def init_rows(user_id, start_date, valid_map):
    """
    Loads existing data from DB into Session State.
    Attempts to backfill assignment_id if missing but matches valid project/task.
    """
    if "ts_rows" not in st.session_state:
        # Fetch existing DB entries
        entries = eq.fetch_entries_for_week(user_id, start_date)
        rows = []
        
        for e in entries:
            aid = e.get("AssignmentId")
            pid = e["project_id"]
            tid = e["task_id"]
            
            # Auto-match legacy entry to valid assignment if Aid is missing
            if not aid:
                for valid_aid, details in valid_map.items():
                    if details["project_id"] == pid and details["task_id"] == tid:
                        aid = valid_aid
                        break

            rows.append({
                "assignment_id": aid,
                "project_id": pid,
                "task_id": tid,
                "sunday": e.get("sunday_hours", 0.0),
                "monday": e.get("monday_hours", 0.0),
                "tuesday": e.get("tuesday_hours", 0.0),
                "wednesday": e.get("wednesday_hours", 0.0),
                "thursday": e.get("thursday_hours", 0.0),
                "friday": e.get("friday_hours", 0.0),
                "saturday": e.get("saturday_hours", 0.0),
            })
            
        # If no entries, start with one empty row
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

# ================================================================
# 🔐 Page Setup
# ================================================================
st.set_page_config(page_title="Weekly Timesheet", layout="wide")
track_page_visit("employee_timesheet")
auth.login_required(roles=["user", "admin", "approver"])

user_info = auth.get_current_user()
user_id = user_info["user_id"]

# Initialize Date
if "ts_week_start" not in st.session_state:
    today = datetime.date.today()
    st.session_state["ts_week_start"] = today - datetime.timedelta(days=today.weekday())

start_date = st.session_state["ts_week_start"]
end_date = start_date + datetime.timedelta(days=6)

# Fetch Master Data FIRST (needed for init_rows)
valid_assignments_map = get_valid_assignments_map(user_id, start_date, end_date)

# Initialize Row State (Must happen after date set)
state_key = f"loaded_{user_id}_{start_date}"
if state_key not in st.session_state:
    if "ts_rows" in st.session_state: del st.session_state.ts_rows
    st.session_state[state_key] = True

init_rows(user_id, start_date, valid_assignments_map)

# ================================================================
# 🎨 Header & Navigation
# ================================================================

st.title("📅 Weekly Timesheet")
st.caption(f"Employee: {user_info['full_name']}")

c1, c2, c3 = st.columns([1, 4, 1])
if c1.button("◀ Prev"):
    st.session_state["ts_week_start"] -= datetime.timedelta(days=7)
    del st.session_state[state_key] # Force reload
    st.rerun()

c2.markdown(f"<h3 style='text-align: center'>{start_date.strftime('%d %b')} - {end_date.strftime('%d %b %Y')}</h3>", unsafe_allow_html=True)

if c3.button("Next ▶"):
    st.session_state["ts_week_start"] += datetime.timedelta(days=7)
    del st.session_state[state_key] # Force reload
    st.rerun()

# Status Check
week_status = eq.get_week_status(user_id, start_date)
status_colors = {"draft": "grey", "submitted": "blue", "approved": "green", "rejected": "red"}
st.markdown(f"**Status:** <span style='color:{status_colors.get(week_status, 'black')}'>**{week_status.upper()}**</span>", unsafe_allow_html=True)

if week_status == "rejected":
    reason = eq.get_latest_rejection_reason(user_id, start_date)
    st.error(f"🚫 **Action Required: Timesheet Rejected**\n\n**Reason:** {reason}")

is_editable = week_status in ["draft", "rejected"]

# ================================================================
# 📝 Timesheet Rows (Dynamic Form)
# ================================================================
st.markdown("---")

# Header Row
# Adjusted columns to fit Assignment Name
h_cols = st.columns([2.5, 1.5, 1.5, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.5])
headers = ["Assignment", "Project", "Task", "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", ""]
for col, h in zip(h_cols, headers):
    col.write(f"**{h}**")

# Dynamic Rows
for i, row in enumerate(st.session_state.ts_rows):
    cols = st.columns([2.5, 1.5, 1.5, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.5])
    
    # 1. Assignment Dropdown (Master)
    curr_aid = row.get("assignment_id")
    
    # Handle legacy/inactive assignments
    assign_opts = valid_assignments_map.copy()
    if curr_aid and curr_aid not in assign_opts:
        # If current assignment is not in valid list (e.g., removed/expired), add placeholder
        assign_opts[curr_aid] = {
            "label": "(Inactive Assignment)", 
            "project_name": "Unknown", 
            "task_name": "Unknown"
        }

    selected_aid = cols[0].selectbox(
        "Assignment", 
        options=list(assign_opts.keys()), 
        format_func=lambda x: assign_opts[x]["label"],
        key=f"assign_{i}",
        index=list(assign_opts.keys()).index(curr_aid) if curr_aid in assign_opts else None,
        placeholder="Select Assignment...",
        label_visibility="collapsed",
        disabled=not is_editable
    )
    
    # Update State Logic
    if selected_aid != curr_aid:
        update_row_value(i, "assignment_id", selected_aid)
        if selected_aid:
            details = assign_opts[selected_aid]
            update_row_value(i, "project_id", details.get("project_id"))
            update_row_value(i, "task_id", details.get("task_id"))
        st.rerun()

    # Derived Values
    disp_project = assign_opts[selected_aid]["project_name"] if selected_aid else "-"
    disp_task = assign_opts[selected_aid]["task_name"] if selected_aid else "-"

    # 2. Project (Read-Only/Disabled)
    cols[1].text_input("Project", value=disp_project, key=f"p_{i}", disabled=True, label_visibility="collapsed")

    # 3. Task (Read-Only/Disabled)
    cols[2].text_input("Task", value=disp_task, key=f"t_{i}", disabled=True, label_visibility="collapsed")

    # 4. Days Inputs
    days = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
    for d_idx, day in enumerate(days):
        val = cols[d_idx + 3].number_input(
            day,
            min_value=0.0, max_value=24.0, step=0.5,
            value=float(row.get(day, 0.0)),
            key=f"{day}_{i}",
            label_visibility="collapsed",
            disabled=not is_editable
        )
        if val != row.get(day):
            update_row_value(i, day, val)

    # 5. Delete Button
    if is_editable:
        if cols[10].button("🗑️", key=f"del_{i}"):
            remove_row(i)
            st.rerun()

st.write("")

# Add Row Button
if is_editable:
    if st.button("➕ Add Row"):
        add_row()
        st.rerun()

# ================================================================
# 💾 Saving Logic
# ================================================================

def save_timesheet(status):
    total_hours = 0
    clean_data = []
    
    for r in st.session_state.ts_rows:
        # Skip rows without assignment
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
        
        # Force reload from DB
        del st.session_state[state_key]
        st.rerun()
        
    except Exception as e:
        st.error(f"Error saving: {e}")


# Footer Actions
st.write("---")
# Calculate Total
grand_total = sum([sum([row[d] for d in days]) for row in st.session_state.ts_rows])
st.caption(f"**Total Weekly Hours:** {grand_total:.2f}")

# --- Validation: Check Previous Week ---
prev_week_start = start_date - datetime.timedelta(days=7)
prev_week_status = eq.get_week_status(user_id, prev_week_start)
can_submit = True

if prev_week_status == "draft":
    st.warning(f"⚠️ You cannot submit this week until the previous week ({prev_week_start.strftime('%d %b')}) is submitted.")
    can_submit = False

c_save, c_submit, _ = st.columns([1, 1, 5])

if is_editable:
    if c_save.button("💾 Save Draft"):
        save_timesheet("draft")
        
    if c_submit.button("🚀 Submit", type="primary", disabled=not can_submit):
        save_timesheet("submitted")
elif week_status == "submitted":
    st.info("Submitted - Waiting for approval.")