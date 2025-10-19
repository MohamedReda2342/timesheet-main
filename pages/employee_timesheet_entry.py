# pages/employee_timesheet_entry.py
import streamlit as st
import datetime
from lib import db, auth

# ================================================================
# 🔐 Role check and page setup
# ================================================================
st.set_page_config(page_title="Weekly Timesheet", layout="wide")
auth.login_required(roles=["user", "admin", "approver"])

user_info = auth.get_current_user()
user_id = user_info["user_id"]

# ================================================================
# 🧩 Database Helpers
# ================================================================
def fetch_assigned_tasks_for_week(conn, user_id, week_start_date, week_end_date):
    """
    Fetch tasks assigned to the user for active projects whose start/end dates overlap
    the selected week period.
    """
    cur = conn.cursor(dictionary=True)
    sql = """
        SELECT
            p.project_id, p.project_name, t.task_id, t.task_name, p.start_date, p.end_date
        FROM user_tasks ut
        JOIN tasks t ON ut.task_id = t.task_id
        JOIN projects p ON t.project_id = p.project_id
        WHERE
            ut.user_id = %s
            AND p.status = 'active'
            AND (
                (p.start_date <= %s AND p.end_date >= %s) OR
                (p.start_date BETWEEN %s AND %s) OR
                (p.end_date BETWEEN %s AND %s) OR
                (p.start_date IS NULL AND p.end_date IS NULL)
            )
        ORDER BY p.project_name, t.task_name
    """
    params = (
        user_id,
        week_end_date, week_start_date,  # overlap check
        week_start_date, week_end_date,  # start within week
        week_start_date, week_end_date,  # end within week
    )
    cur.execute(sql, params)
    rows = cur.fetchall()
    cur.close()
    return rows


def fetch_entries_for_week(conn, user_id, week_start_date):
    """Fetch existing timesheet entries for the selected week."""
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT te.*, p.project_name, t.task_name
        FROM timesheet_entries te
        JOIN projects p ON te.project_id = p.project_id
        LEFT JOIN tasks t ON te.task_id = t.task_id
        WHERE te.user_id = %s AND te.week_start_date = %s
    """, (user_id, week_start_date))
    rows = cur.fetchall()
    cur.close()
    return rows


def get_week_status(conn, user_id, week_start_date):
    """Determine the timesheet status for the current week."""
    cur = conn.cursor(dictionary=True)
    cur.execute("""
        SELECT DISTINCT status
        FROM timesheet_entries
        WHERE user_id = %s AND week_start_date = %s
    """, (user_id, week_start_date))
    rows = cur.fetchall()
    cur.close()

    if rows:
        statuses = {r["status"].lower() for r in rows if r.get("status")}
        if "approved" in statuses:
            return "approved"
        if "submitted" in statuses:
            return "submitted"
        if "rejected" in statuses:
            return "rejected"
        if "draft" in statuses:
            return "draft"
    return "draft"


def upsert_weekly_entry(conn, data):
    """
    Smart upsert logic:
    - Update existing row if status is draft/submitted/approved.
    - Insert new row if existing status is rejected.
    """
    cur = conn.cursor(dictionary=True)
    check_sql = """
        SELECT entry_id, status
        FROM timesheet_entries
        WHERE user_id = %s AND project_id = %s AND task_id = %s AND week_start_date = %s
        ORDER BY entry_id DESC LIMIT 1
    """
    cur.execute(check_sql, (data["user_id"], data["project_id"], data["task_id"], data["week_start_date"]))
    existing = cur.fetchone()

    if existing:
        if existing["status"].lower() == "rejected":
            # Insert new row when re-submitting a rejected entry
            insert_sql = """
                INSERT INTO timesheet_entries (
                    user_id, project_id, task_id, week_start_date,
                    sunday_hours, monday_hours, tuesday_hours, wednesday_hours,
                    thursday_hours, friday_hours, saturday_hours, status
                ) VALUES (
                    %(user_id)s, %(project_id)s, %(task_id)s, %(week_start_date)s,
                    %(sunday)s, %(monday)s, %(tuesday)s, %(wednesday)s,
                    %(thursday)s, %(friday)s, %(saturday)s, %(status)s
                )
            """
            cur.execute(insert_sql, data)
        else:
            # Update existing entry
            update_sql = """
                UPDATE timesheet_entries
                SET
                    sunday_hours = %(sunday)s,
                    monday_hours = %(monday)s,
                    tuesday_hours = %(tuesday)s,
                    wednesday_hours = %(wednesday)s,
                    thursday_hours = %(thursday)s,
                    friday_hours = %(friday)s,
                    saturday_hours = %(saturday)s,
                    status = %(status)s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE entry_id = %(entry_id)s
            """
            params = dict(data)
            params["entry_id"] = existing["entry_id"]
            cur.execute(update_sql, params)
    else:
        # Brand new entry
        insert_sql = """
            INSERT INTO timesheet_entries (
                user_id, project_id, task_id, week_start_date,
                sunday_hours, monday_hours, tuesday_hours, wednesday_hours,
                thursday_hours, friday_hours, saturday_hours, status
            ) VALUES (
                %(user_id)s, %(project_id)s, %(task_id)s, %(week_start_date)s,
                %(sunday)s, %(monday)s, %(tuesday)s, %(wednesday)s,
                %(thursday)s, %(friday)s, %(saturday)s, %(status)s
            )
        """
        cur.execute(insert_sql, data)
    cur.close()


# ================================================================
# 🔄 Data loading and saving logic
# ================================================================
def load_week_data(user_id, start_date, end_date):
    conn = db.get_db_connection()
    assigned_tasks = fetch_assigned_tasks_for_week(conn, user_id, start_date, end_date)
    existing_entries = fetch_entries_for_week(conn, user_id, start_date)
    conn.close()

    all_rows_map = {}

    # Assigned tasks as blank
    for t in assigned_tasks:
        key = (t["project_id"], t["task_id"])
        all_rows_map[key] = {
            "project_id": t["project_id"],
            "task_id": t["task_id"],
            "project_name": t["project_name"],
            "task_name": t["task_name"],
            "hours": {},
            "status": "draft",
        }

    # Existing entries overwrite
    for e in existing_entries:
        key = (e["project_id"], e["task_id"])
        hours = {
            "sunday": format_hours_to_hhmm(e.get("sunday_hours")),
            "monday": format_hours_to_hhmm(e.get("monday_hours")),
            "tuesday": format_hours_to_hhmm(e.get("tuesday_hours")),
            "wednesday": format_hours_to_hhmm(e.get("wednesday_hours")),
            "thursday": format_hours_to_hhmm(e.get("thursday_hours")),
            "friday": format_hours_to_hhmm(e.get("friday_hours")),
            "saturday": format_hours_to_hhmm(e.get("saturday_hours")),
        }
        all_rows_map[key] = {
            "project_id": e["project_id"],
            "task_id": e["task_id"],
            "project_name": e["project_name"],
            "task_name": e["task_name"],
            "hours": hours,
            "status": e["status"],
        }

    st.session_state["timesheet_rows"] = sorted(all_rows_map.values(), key=lambda x: (x["project_name"], x["task_name"]))


def save_timesheet(user_id, start_date, status):
    conn = db.get_db_connection()
    day_keys = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]

    try:
        conn.start_transaction()
        for row in st.session_state.get("timesheet_rows", []):
            data = {
                "user_id": user_id,
                "project_id": row["project_id"],
                "task_id": row.get("task_id"),
                "week_start_date": start_date,
                "status": status,
            }
            for day in day_keys:
                data[day] = parse_hhmm_to_hours(row.get("hours", {}).get(day, "0:00"))
            upsert_weekly_entry(conn, data)
        conn.commit()
        st.success(f"✅ Timesheet saved as **{status.upper()}**.")
    except Exception as e:
        conn.rollback()
        st.error(f"❌ Failed to save timesheet: {e}")
    finally:
        conn.close()

    load_week_data(user_id, start_date, start_date + datetime.timedelta(days=6))
    st.rerun()


# ================================================================
# 🕒 Time utilities
# ================================================================
def parse_hhmm_to_hours(txt):
    if not txt:
        return 0.0
    try:
        txt = str(txt).strip()
        if ":" in txt:
            h, m = map(float, txt.split(":"))
            return h + m / 60.0
        return float(txt)
    except (ValueError, TypeError):
        return 0.0


def format_hours_to_hhmm(hours):
    if not hours or float(hours) <= 0:
        return ""
    total_minutes = int(round(float(hours) * 60))
    h, m = divmod(total_minutes, 60)
    return f"{h}:{m:02d}"


# ================================================================
# 🎨 Main UI
# ================================================================
st.title("📅 Weekly Timesheet")
st.write(f"Employee: **{user_info['full_name']}**")

if "ts_week_start" not in st.session_state:
    today = datetime.date.today()
    st.session_state["ts_week_start"] = today - datetime.timedelta(days=(today.weekday() + 1) % 7)

start_date = st.session_state["ts_week_start"]
end_date = start_date + datetime.timedelta(days=6)

# Week navigation
c1, c2, c3 = st.columns([1.5, 6, 1.5])
if c1.button("◀ Previous Week"):
    st.session_state["ts_week_start"] -= datetime.timedelta(days=7)
    st.rerun()
c2.markdown(f"<h3 style='text-align:center;'>{start_date.strftime('%d %b')} → {end_date.strftime('%d %b %Y')}</h3>", unsafe_allow_html=True)
if c3.button("Next Week ▶"):
    st.session_state["ts_week_start"] += datetime.timedelta(days=7)
    st.rerun()

# Week status
conn = db.get_db_connection()
week_status = get_week_status(conn, user_id, start_date)
conn.close()

status_colors = {"draft": "gray", "submitted": "blue", "approved": "green", "rejected": "red"}
st.markdown(f"<h4 style='color:{status_colors.get(week_status, 'black')};'>🧾 Week Status: {week_status.upper()}</h4>", unsafe_allow_html=True)

# Load data
load_week_data(user_id, start_date, end_date)
rows = st.session_state.get("timesheet_rows", [])
day_keys = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
day_names = [(start_date + datetime.timedelta(days=i)).strftime("%a").upper() for i in range(7)]

# Header
header = st.columns([3, 4] + [1] * 7 + [1.5])
header[0].markdown("**PROJECT**")
header[1].markdown("**TASK**")
for i, n in enumerate(day_names):
    header[2 + i].markdown(f"**{n}**")
header[-1].markdown("**ROW TOTAL**")

# Rows
if not rows:
    st.info("No assigned tasks for this week.")
else:
    for i, row in enumerate(rows):
        cols = st.columns([3, 4] + [1] * 7 + [1.5])
        cols[0].markdown(row.get("project_name", ""))
        cols[1].markdown(row.get("task_name", ""))
        row_total = 0.0
        for j, day in enumerate(day_keys):
            val = row.get("hours", {}).get(day, "")
            if week_status in ["approved", "submitted"]:
                cols[2 + j].markdown(val if val else "")
            else:
                input_val = cols[2 + j].text_input(
                    f"cell_{i}_{j}", value=val, placeholder="0:00", label_visibility="collapsed"
                )
                row.setdefault("hours", {})[day] = input_val
                row_total += parse_hhmm_to_hours(input_val)
        cols[-1].markdown(f"**{format_hours_to_hhmm(row_total)}**" if row_total > 0 else "")

    # Totals
    st.markdown("---")
    foot = st.columns([3, 4] + [1] * 7 + [1.5])
    foot[0].markdown("#### TOTALS")
    grand_total = 0.0
    for j, day in enumerate(day_keys):
        day_total = sum(parse_hhmm_to_hours(r.get("hours", {}).get(day, "")) for r in rows)
        grand_total += day_total
        foot[2 + j].markdown(f"**{format_hours_to_hhmm(day_total)}**" if day_total > 0 else "")
    foot[-1].markdown(f"### {format_hours_to_hhmm(grand_total)}")

# ================================================================
# 💾 Buttons
# ================================================================
st.markdown("---")
b1, b2, _ = st.columns([2, 2, 8])

if week_status in ["draft", "rejected"]:
    if b1.button("💾 Save Draft", use_container_width=True):
        if not rows:
            st.warning("No rows to save.")
        else:
            save_timesheet(user_id, start_date, "draft")

    if b2.button("📤 Submit", type="primary", use_container_width=True):
        if not rows:
            st.warning("No rows to submit.")
        else:
            save_timesheet(user_id, start_date, "submitted")

elif week_status == "submitted":
    st.info("⏳ Timesheet submitted. Awaiting approval — editing disabled.")
elif week_status == "approved":
    st.success("✅ Timesheet approved and locked.")
