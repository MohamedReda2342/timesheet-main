# pages/employee_timesheet_entry.py
import streamlit as st
import pandas as pd
import datetime
from lib import db
from util.employee_dashboard_home import employee_dashboard_home
# ================================================================
# 🔐 Role check
# ================================================================
def require_role(allowed_roles):
    if "role" not in st.session_state:
        st.error("Access denied. Please log in.")
        st.stop()
    if st.session_state.role not in allowed_roles:
        st.error("You are not authorized to view this page.")
        st.stop()

# ================================================================
# 🧩 Database helpers
# ================================================================
def fetch_active_projects(conn, start_date, end_date):
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT project_id, project_name
        FROM projects
        WHERE status='active'
          AND (start_date IS NULL OR start_date <= %s)
          AND (end_date IS NULL OR end_date >= %s)
        ORDER BY project_name
    """, (end_date, start_date))
    rows = cur.fetchall()
    cur.close()
    return rows

def fetch_tasks_for_project(conn, project_id):
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT task_id, task_name FROM tasks WHERE project_id=%s ORDER BY task_name", (project_id,))
    rows = cur.fetchall()
    cur.close()
    return rows

def fetch_entries_for_week(conn, user_id, start_date, end_date):
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT * FROM timesheet_entries
        WHERE user_id=%s AND entry_date BETWEEN %s AND %s
        ORDER BY entry_date
    """, (user_id, start_date, end_date))
    rows = cur.fetchall()
    cur.close()
    return rows

def insert_entry(conn, user_id, project_id, task_id, entry_date, hours, status="draft"):
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO timesheet_entries (user_id, project_id, task_id, entry_date, hours, status)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (user_id, project_id, task_id, entry_date, hours, status))
    eid = cur.lastrowid
    cur.close()
    return eid

def update_entry(conn, entry_id, project_id, task_id, hours, status="draft"):
    cur = conn.cursor()
    cur.execute("""
        UPDATE timesheet_entries
        SET project_id=%s, task_id=%s, hours=%s, status=%s
        WHERE entry_id=%s
    """, (project_id, task_id, hours, status, entry_id))
    cur.close()

# ================================================================
# 🕒 Utilities
# ================================================================
def parse_hhmm_to_hours(txt: str) -> float:
    """Convert 'hh:mm' or numeric strings to hours as float. Returns 0.0 for empty/invalid."""
    if not txt:
        return 0.0
    try:
        txt = str(txt).strip()
        if ":" in txt:
            parts = txt.split(":")
            if len(parts) != 2:
                return 0.0
            h = float(parts[0])
            m = float(parts[1])
            if m < 0 or m >= 60:
                return 0.0
            return h + m / 60.0
        return float(txt)
    except Exception:
        return 0.0


def format_hours_to_hhmm(hours: float) -> str:
    """Convert float hours to hh:mm format. Returns empty string for <=0."""
    if not hours or hours <= 0:
        return ""
    total = int(round(hours * 60))
    h, m = divmod(total, 60)
    return f"{h}:{m:02d}"


def validate_hhmm_input(s):
    if not s or str(s).strip() == "":
        return None
    try:
        val = parse_hhmm_to_hours(s)
        if val < 0:
            return "Negative"
        if val > 24:
            return ">24h"
        return None
    except:
        return "Invalid"

# ================================================================
# 🔄 Data load
# ================================================================
def load_week_data(user_id, start_date, end_date):
    conn = db.get_db()
    active_projects = fetch_active_projects(conn, start_date, end_date)
    project_map = {p["project_id"]: p["project_name"] for p in active_projects}

    rows = []
    # create rows for each active project and its tasks
    for p in active_projects:
        tasks = fetch_tasks_for_project(conn, p["project_id"])
        if not tasks:
            rows.append({
                "project_id": p["project_id"],
                "project_name": p["project_name"],
                "task_id": None,
                "task_name": "",
                "cells": {}
            })
        else:
            for t in tasks:
                rows.append({
                    "project_id": p["project_id"],
                    "project_name": p["project_name"],
                    "task_id": t["task_id"],
                    "task_name": t["task_name"],
                    "cells": {}
                })

    # attach existing entries (even if project/task not active) to rows or create rows for them
    entries = fetch_entries_for_week(conn, user_id, start_date, end_date)
    for e in entries:
        found = False
        for r in rows:
            if r["project_id"] == e["project_id"] and (r["task_id"] == e["task_id"] or (not r["task_id"] and not e["task_id"])):
                dkey = e["entry_date"].isoformat()
                r["cells"][dkey] = {"hours": format_hours_to_hhmm(float(e["hours"])), "entry_id": e["entry_id"]}
                found = True
                break
        if not found:
            proj_name = project_map.get(e["project_id"], f"Project {e['project_id']}")
            rows.append({
                "project_id": e["project_id"],
                "project_name": proj_name,
                "task_id": e.get("task_id"),
                "task_name": "",
                "cells": {
                    e["entry_date"].isoformat(): {"hours": format_hours_to_hhmm(float(e["hours"])), "entry_id": e["entry_id"]}
                },
            })

    conn.close()
    st.session_state["timesheet_rows"] = rows

# ================================================================
# 💾 Save
# ================================================================
def save_timesheet(user_id, start_date, status):
    conn = db.get_db()
    end_date = start_date + datetime.timedelta(days=4)
    day_dates = [start_date + datetime.timedelta(days=i) for i in range(5)]

    try:
        conn.start_transaction()
    except:
        pass

    for row in st.session_state.get("timesheet_rows", []):
        project_id = row.get("project_id")
        task_id = row.get("task_id")
        if not project_id:
            continue

        for d in day_dates:
            iso = d.isoformat()
            cell = row.get("cells", {}).get(iso, {})
            val = parse_hhmm_to_hours(cell.get("hours", ""))
            if val is None or val == 0:
                continue

            eid = cell.get("entry_id")
            if eid:
                update_entry(conn, eid, project_id, task_id, val, status)
            else:
                new_id = insert_entry(conn, user_id, project_id, task_id, d, val, status)
                # ensure cell exists
                row.setdefault("cells", {}).setdefault(iso, {})["entry_id"] = new_id

    try:
        conn.commit()
    except:
        pass
    try:
        conn.close()
    except:
        pass

# ================================================================
# 🎨 UI
# ================================================================
def employee_timesheet_entry():
    require_role(["user", "admin"])
    st.set_page_config(page_title="Weekly Timesheet", layout="wide")
    user_id = st.session_state.get("user_id")
    if not user_id:
        st.error("Please log in.")
        st.stop()

    # week logic: start on Sunday
    if "ts_week_start" not in st.session_state:
        today = datetime.date.today()
        # weekday(): Mon=0..Sun=6. To get Sunday: subtract (weekday+1)%7
        sunday = today - datetime.timedelta(days=(today.weekday() + 1) % 7)
        st.session_state["ts_week_start"] = sunday

    start_date = st.session_state["ts_week_start"]
    end_date = start_date + datetime.timedelta(days=4)  # Sunday -> Thursday

    cols = st.columns([1, 6, 1])
    if cols[0].button("◀"):
        st.session_state["ts_week_start"] -= datetime.timedelta(days=7)
        st.rerun()
    cols[1].markdown(
        f"<h3 style='text-align:center;'>{start_date.strftime('%d %b')} → {end_date.strftime('%d %b %Y')}</h3>",
        unsafe_allow_html=True
    )
    if cols[2].button("▶"):
        st.session_state["ts_week_start"] += datetime.timedelta(days=7)
        st.rerun()

    # load rows for the week when needed
    if "ts_loaded_week" not in st.session_state or st.session_state["ts_loaded_week"] != start_date.isoformat():
        load_week_data(user_id, start_date, end_date)
        st.session_state["ts_loaded_week"] = start_date.isoformat()

    rows = st.session_state.get("timesheet_rows", [])

    # fetch active projects for dropdown options
    conn = db.get_db()
    all_projects = fetch_active_projects(conn, start_date, end_date)
    # map: project_name -> project_id (order preserved by list)
    project_names = [p["project_name"] for p in all_projects]
    project_options = {p["project_name"]: p["project_id"] for p in all_projects}
    conn.close()

    # Header: day names only (e.g. SUN MON ...)
    days = [start_date + datetime.timedelta(days=i) for i in range(5)]
    header_cols = st.columns([3, 4] + [1] * 5 + [1])
    header_cols[0].markdown("**PROJECT**")
    header_cols[1].markdown("**TASK**")
    for i, d in enumerate(days):
        header_cols[2 + i].markdown(f"**{d.strftime('%a').upper()}**")
    header_cols[-1].markdown("**Total**")

    # Table rows
    for i, row in enumerate(rows):
        # defensive defaults
        row.setdefault("cells", {})
        row.setdefault("project_name", "")
        row.setdefault("task_name", None)
        cols = st.columns([3, 4] + [1] * 5 + [1])

        # Project dropdown
        selected_project_name = None
        if row.get("project_id"):
            # try to find the name (may be missing if project inactive)
            try:
                selected_project_name = next((n for n, pid in project_options.items() if pid == row.get("project_id")), None)
            except Exception:
                selected_project_name = None

        proj_list = [""] + project_names
        proj_index = 0
        if selected_project_name:
            try:
                proj_index = proj_list.index(selected_project_name)
            except ValueError:
                proj_index = 0

        new_project = cols[0].selectbox("", proj_list, index=proj_index, key=f"proj_{i}")
        row["project_id"] = project_options.get(new_project) if new_project else None
        row["project_name"] = new_project or ""

        # Task dropdown (disabled until project chosen)
        task_options = []
        if row["project_id"]:
            conn2 = db.get_db()
            task_rows = fetch_tasks_for_project(conn2, row["project_id"])
            conn2.close()
            task_options = [t["task_name"] for t in task_rows]

        task_list = [""] + task_options
        task_index = 0
        if row.get("task_name") in task_options:
            try:
                task_index = task_list.index(row.get("task_name"))
            except:
                task_index = 0

        task_disabled = not bool(row.get("project_id"))
        new_task = cols[1].selectbox("", task_list, index=task_index, key=f"task_{i}", disabled=task_disabled)
        row["task_name"] = new_task or ""
        # fetch and set task_id if possible
        if new_task and row.get("project_id"):
            conn3 = db.get_db()
            cur = conn3.cursor(dictionary=True)
            cur.execute("SELECT task_id FROM tasks WHERE project_id=%s AND task_name=%s", (row["project_id"], new_task))
            task_row = cur.fetchone()
            cur.close()
            conn3.close()
            if task_row:
                row["task_id"] = task_row["task_id"]
            else:
                row["task_id"] = None
        else:
            # if no task chosen, keep existing task_id only if it matches name
            if not new_task:
                row["task_id"] = row.get("task_id")

        # daily inputs and row total
        row_total = 0.0
        for j, d in enumerate(days):
            iso = d.isoformat()
            current = row.get("cells", {}).get(iso, {}).get("hours", "")
            txt = cols[2 + j].text_input("", value=current, key=f"cell_{i}_{iso}", placeholder="0:00")
            err = validate_hhmm_input(txt)
            if err:
                cols[2 + j].caption(f"⚠️ {err}")
            # store back
            row.setdefault("cells", {})[iso] = {"hours": txt, "entry_id": row.get("cells", {}).get(iso, {}).get("entry_id")}
            val = parse_hhmm_to_hours(txt)
            row_total += (val or 0.0)
        cols[-1].markdown(f"**{format_hours_to_hhmm(row_total)}**" if row_total > 0 else "")

    # Totals row
    # st.markdown("---")
    foot = st.columns([3, 4] + [1] * 5 + [1])
    foot[0].markdown("**Totals**")
    foot[1].markdown("")

    grand_total = 0.0
    for j, d in enumerate(days):
        day_total = 0.0
        for r in rows:
            cell_val = r.get("cells", {}).get(d.isoformat(), {}).get("hours", "")
            hours_val = parse_hhmm_to_hours(cell_val)
            day_total += (hours_val or 0.0)
        grand_total += day_total
        foot[2 + j].markdown(f"**{format_hours_to_hhmm(day_total)}**" if day_total > 0 else "")

    # Buttons at bottom
    st.markdown("---")
    b1, b2, b3, b4 = st.columns([2, 2, 2, 2])
    with b1:
        if st.button("+ Add Row"):
            st.session_state.setdefault("timesheet_rows", []).append({"project_id": None, "task_id": None, "cells": {}})
            st.rerun()
    with b2:
        if st.button("💾 Save Draft"):
            save_timesheet(user_id, start_date, "draft")
            st.success("Saved as draft.")
    with b3:
        if st.button("📤 Submit"):
            save_timesheet(user_id, start_date, "submitted")
            st.success("Submitted.")
    with b4:
        if st.button("🔁 Refresh"):
            load_week_data(user_id, start_date, end_date)
            st.rerun()

# ================================================================
tab1, tab2= st.tabs(["🏠 Home","📅 Weekly Timesheets"])
# -------------------------------- TAB 1: Home --------------------------------
with tab1:
    employee_dashboard_home()
with tab2:
    employee_timesheet_entry()