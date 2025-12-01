# ./pages/admin_reports_dashboard.py
# import streamlit as st
# import pandas as pd
# from datetime import date, timedelta
# from lib import db, auth

# # =========================================================
# # 🔐 Access Control & Page Setup
# # =========================================================
# st.set_page_config(page_title="Reports Dashboard", layout="wide")
# auth.login_required(roles=["admin", "approver"])
# user = auth.get_current_user()
# st.title("📊 Reports & Analytics Dashboard")

# # =========================================================
# # 🧩 Helper Queries
# # =========================================================
# def fetch_summary_metrics():
#     conn = db.get_db_connection()
#     cur = conn.cursor(dictionary=True)
#     cur.execute("""
#         SELECT 
#             SUM(total_hours) AS total_hours,
#             SUM(CASE WHEN status='submitted' THEN 1 ELSE 0 END) AS submitted_count,
#             SUM(CASE WHEN status='approved' THEN 1 ELSE 0 END) AS approved_count,
#             SUM(CASE WHEN status='rejected' THEN 1 ELSE 0 END) AS rejected_count
#         FROM timesheet_entries
#     """)
#     summary = cur.fetchone()

#     cur.execute("SELECT COUNT(*) AS active_projects FROM projects WHERE status='active'")
#     summary["active_projects"] = cur.fetchone()["active_projects"]

#     cur.execute("SELECT COUNT(*) AS total_tasks FROM tasks")
#     summary["total_tasks"] = cur.fetchone()["total_tasks"]

#     cur.close()
#     conn.close()
#     return summary


# def fetch_timesheet_report(start, end, project=None, user_id=None, status=None):
#     conn = db.get_db_connection()
#     cur = conn.cursor(dictionary=True)

#     sql = """
#         SELECT 
#             u.full_name AS employee_name,
#             p.project_name,
#             t.task_name,
#             te.week_start_date,
#             te.total_hours,
#             te.status
#         FROM timesheet_entries te
#         JOIN users u ON te.user_id = u.user_id
#         JOIN projects p ON te.project_id = p.project_id
#         LEFT JOIN tasks t ON te.task_id = t.task_id
#         WHERE te.week_start_date BETWEEN %s AND %s
#     """
#     params = [start, end]

#     if project:
#         sql += " AND p.project_id = %s"
#         params.append(project)
#     if user_id:
#         sql += " AND u.user_id = %s"
#         params.append(user_id)
#     if status and status != "All":
#         sql += " AND te.status = %s"
#         params.append(status)

#     cur.execute(sql, params)
#     rows = cur.fetchall()
#     cur.close()
#     conn.close()
#     return pd.DataFrame(rows)


# def fetch_project_utilization(start, end):
#     conn = db.get_db_connection()
#     cur = conn.cursor(dictionary=True)
#     cur.execute("""
#         SELECT 
#             p.project_name,
#             SUM(te.total_hours) AS total_hours
#         FROM timesheet_entries te
#         JOIN projects p ON te.project_id = p.project_id
#         WHERE te.week_start_date BETWEEN %s AND %s
#         GROUP BY p.project_name
#         ORDER BY total_hours DESC
#     """, (start, end))
#     data = cur.fetchall()
#     cur.close()
#     conn.close()
#     return pd.DataFrame(data)


# def fetch_approvals_report():
#     conn = db.get_db_connection()
#     cur = conn.cursor(dictionary=True)
#     cur.execute("""
#         SELECT 
#             u.full_name AS employee_name,
#             a.approver_id,
#             ap.full_name AS approver_name,
#             a.decision,
#             a.comment,
#             a.decision_ts
#         FROM approvals a
#         JOIN timesheet_entries te ON a.entry_id = te.entry_id
#         JOIN users u ON te.user_id = u.user_id
#         JOIN users ap ON a.approver_id = ap.user_id
#         ORDER BY a.decision_ts DESC
#     """)
#     rows = cur.fetchall()
#     cur.close()
#     conn.close()
#     return pd.DataFrame(rows)


# def fetch_user_performance(start, end):
#     conn = db.get_db_connection()
#     cur = conn.cursor(dictionary=True)
#     cur.execute("""
#         SELECT 
#             u.full_name,
#             SUM(te.total_hours) AS total_hours,
#             SUM(CASE WHEN te.status='approved' THEN te.total_hours ELSE 0 END) AS approved_hours,
#             COUNT(DISTINCT te.week_start_date) AS weeks_worked
#         FROM timesheet_entries te
#         JOIN users u ON te.user_id = u.user_id
#         WHERE te.week_start_date BETWEEN %s AND %s
#         GROUP BY u.user_id
#         ORDER BY total_hours DESC
#     """, (start, end))
#     rows = cur.fetchall()
#     cur.close()
#     conn.close()
#     return pd.DataFrame(rows)

# # =========================================================
# # 🎯 Summary KPIs
# # =========================================================
# summary = fetch_summary_metrics()

# st.markdown("### 📈 Overview Metrics")
# col1, col2, col3, col4, col5 = st.columns(5)
# col1.metric("🕒 Total Hours", f"{summary['total_hours'] or 0:.2f}")
# col2.metric("📤 Submitted", summary["submitted_count"])
# col3.metric("✅ Approved", summary["approved_count"])
# col4.metric("❌ Rejected", summary["rejected_count"])
# col5.metric("📁 Active Projects", summary["active_projects"])

# st.markdown("---")

# # =========================================================
# # 📅 Filters
# # =========================================================
# today = date.today()
# start_date = st.date_input("From", today - timedelta(days=30))
# end_date = st.date_input("To", today)

# conn = db.get_db_connection()
# projects = pd.read_sql("SELECT project_id, project_name FROM projects ORDER BY project_name", conn)
# users = pd.read_sql("SELECT user_id, full_name FROM users ORDER BY full_name", conn)
# conn.close()

# col1, col2, col3 = st.columns(3)
# project_filter = col1.selectbox("Project", ["All"] + projects["project_name"].tolist())
# user_filter = col2.selectbox("Employee", ["All"] + users["full_name"].tolist())
# status_filter = col3.selectbox("Status", ["All", "draft", "submitted", "approved", "rejected"])

# # Map names → IDs
# project_id = None if project_filter == "All" else projects.loc[projects["project_name"] == project_filter, "project_id"].values[0]
# user_id = None if user_filter == "All" else users.loc[users["full_name"] == user_filter, "user_id"].values[0]

# st.markdown("---")

# # =========================================================
# # 📊 Reports Tabs
# # =========================================================
# tab1, tab2, tab3, tab4 = st.tabs([
#     "📘 Timesheet Summary",
#     "📗 Project Utilization",
#     "📙 Approvals",
#     "📕 User Performance"
# ])

# # --- Tab 1: Timesheet Summary
# with tab1:
#     df = fetch_timesheet_report(start_date, end_date, project_id, user_id, status_filter)
#     st.dataframe(df, use_container_width=True)
#     if not df.empty:
#         st.download_button("⬇️ Download CSV", df.to_csv(index=False).encode(), "timesheet_summary.csv", "text/csv")

# # --- Tab 2: Project Utilization
# with tab2:
#     df = fetch_project_utilization(start_date, end_date)
#     st.bar_chart(df.set_index("project_name"))
#     st.dataframe(df, use_container_width=True)

# # --- Tab 3: Approvals Report
# with tab3:
#     df = fetch_approvals_report()
#     st.dataframe(df, use_container_width=True)

# # --- Tab 4: User Performance
# with tab4:
#     df = fetch_user_performance(start_date, end_date)
#     st.dataframe(df, use_container_width=True)
#     if not df.empty:
#         st.download_button("⬇️ Download CSV", df.to_csv(index=False).encode(), "user_performance.csv", "text/csv")
