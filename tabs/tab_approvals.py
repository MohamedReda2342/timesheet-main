# ./tabs/tab_approvals.py
import streamlit as st
import pandas as pd
from datetime import date, timedelta
from utils import manager_queries as mq
from utils.state_helpers import clear_other_dialogs, reset_dialog_state
from lib.constants import ROLE_ID_ADMIN, ROLE_ID_DEPT_MANAGER, ROLE_ID_PROJECT_MANAGER

# ========================================================
# 🎨 Dialogs
# ========================================================

@st.dialog("Reject Timesheet")
def reject_timesheet_dialog(entry, approver_id):
    st.warning(f"Rejecting timesheet for {entry['employee_name']}")
    with st.form("rejection_form"):
        comment = st.text_area("Reason (Required)")
        
        c1, c2 = st.columns(2)
        if c1.form_submit_button("Confirm Rejection", type="primary"):
            if not comment:
                st.error("Reason required.")
            else:
                mq.update_entry_status(entry['entry_id'], approver_id, 'rejected', comment)
                st.success("Rejected.")
                if "reject_entry_info" in st.session_state:
                    del st.session_state["reject_entry_info"]
                st.rerun()
        
        if c2.form_submit_button("Cancel"):
             if "reject_entry_info" in st.session_state:
                del st.session_state["reject_entry_info"]
             st.rerun()

@st.dialog("✏️ Edit Entry (Admin)")
def edit_entry_dialog(entry_summary, admin_user_id):
    # Fetch full details from DB (hours, IDs)
    entry_id = entry_summary['entry_id']
    full_entry = mq.get_timesheet_entry_details(entry_id)
    
    if not full_entry:
        st.error("Entry not found.")
        return

    st.caption(f"Employee: {entry_summary['employee_name']} | Week: {entry_summary['week_start_date']}")

    with st.form("edit_entry_full_form"):
        # 1. Project & Task Selection
        col_pt1, col_pt2 = st.columns(2)
        
        all_projects = mq.fetch_all_active_projects()
        proj_opts = {p['project_id']: p['project_name'] for p in all_projects}
        curr_proj = full_entry.get('project_id')
        idx_proj = list(proj_opts.keys()).index(curr_proj) if curr_proj in proj_opts else 0
        sel_proj = col_pt1.selectbox("Project", options=proj_opts.keys(), format_func=lambda x: proj_opts[x], index=idx_proj)
        
        task_types = mq.fetch_task_types()
        type_opts = {t['TaskTypeId']: t['TaskTypeName'] for t in task_types}
        
        curr_type = full_entry.get('TaskTypeId')
        if curr_type and curr_type in type_opts:
            idx_type = list(type_opts.keys()).index(curr_type)
        else:
            idx_type = 0
            
        sel_type = col_pt2.selectbox("Task Type", options=type_opts.keys(), format_func=lambda x: type_opts[x], index=idx_type)
        
        tasks = mq.fetch_tasks_by_type(sel_type)
        task_opts = {t['task_id']: t['task_name'] for t in tasks}
        
        curr_task = full_entry.get('task_id')
        idx_task = list(task_opts.keys()).index(curr_task) if curr_task in task_opts else 0
        
        sel_task = st.selectbox("Task", options=task_opts.keys(), format_func=lambda x: task_opts[x], index=idx_task)

        st.markdown("---")
        st.write("**Hours**")
        
        cols_h = st.columns(7)
        days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
        new_hours = {}
        
        for i, day in enumerate(days):
            val = int(full_entry.get(f"{day}_hours") or 0)
            safe_max = max(24, val) 
            
            new_hours[day] = cols_h[i].number_input(
                day[:3].capitalize(), 
                min_value=0, 
                max_value=safe_max,
                step=1,       
                format="%d",  
                value=val
            )

        st.markdown("---")
        
        c_stat, c_note = st.columns([1, 2])
        status_opts = ["draft", "submitted", "approved", "rejected"]
        curr_status = full_entry.get("status", "submitted").lower()
        idx_stat = status_opts.index(curr_status) if curr_status in status_opts else 1
        
        sel_status = c_stat.selectbox("Status", status_opts, index=idx_stat)
        notes = c_note.text_input("Notes", value=full_entry.get("notes") or "")

        if st.form_submit_button("💾 Save Changes"):
            total_hours = sum(new_hours.values())
            
            if total_hours > 40:
                st.error(f"❌ Limit Exceeded: Total hours ({total_hours}) cannot exceed 40 per week.")
            elif not sel_task:
                st.error("Task is required.")
            else:
                data = {
                    "entry_id": entry_id,
                    "project_id": sel_proj,
                    "task_id": sel_task,
                    "status": sel_status,
                    "notes": notes,
                    **new_hours
                }
                mq.update_timesheet_entry_full(data)
                st.success("Entry updated successfully!")
                
                if "edit_entry_info" in st.session_state:
                    del st.session_state["edit_entry_info"]
                st.rerun()

@st.dialog("➕ Admin: Insert Entry")
def admin_insert_entry_dialog(admin_user_id):
    st.caption("Insert a time entry on behalf of an employee. It will be **Approved** automatically.")
    
    with st.form("admin_create_entry"):
        # 1. Employee
        all_emps = mq.get_all_employees()
        emp_opts = {e['EmpId']: f"{e['EmpName']} ({e['SAP_ID']})" for e in all_emps}
        sel_emp = st.selectbox("Select Employee", options=emp_opts.keys(), format_func=lambda x: emp_opts[x])
        
        # 2. Project
        all_projs = mq.fetch_all_active_projects()
        proj_opts = {p['project_id']: p['project_name'] for p in all_projs}
        sel_proj = st.selectbox("Select Project", options=proj_opts.keys(), format_func=lambda x: proj_opts[x])
        
        # 3. Task
        c_type, c_task = st.columns(2)
        task_types = mq.fetch_task_types()
        type_opts = {t['TaskTypeId']: t['TaskTypeName'] for t in task_types}
        sel_type = c_type.selectbox("Task Type", options=type_opts.keys(), format_func=lambda x: type_opts[x])
        
        tasks = mq.fetch_tasks_by_type(sel_type)
        if not tasks:
            c_task.warning("No tasks.")
            sel_task = None
        else:
            task_opts = {t['task_id']: t['task_name'] for t in tasks}
            sel_task = c_task.selectbox("Task", options=task_opts.keys(), format_func=lambda x: task_opts[x])
            
        st.markdown("---")
        
        # 4. Date & Hours
        # Week selection logic
        c_date, _ = st.columns(2)
        week_start_input = c_date.date_input("Week Start Date", value=date.today() - timedelta(days=date.today().weekday()))
        
        # Adjust to true week start if needed (assuming Mon or Sun based on existing logic)
        # Here we trust the Admin picks the correct date, or we can force-snap it.
        # Let's verify standard Monday start for consistency:
        # standard_start = week_start_input - timedelta(days=week_start_input.weekday())
        # Using input directly to allow flexibility if business logic varies.
        
        st.write("**Daily Hours**")
        cols = st.columns(7)
        days = ['sunday', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday']
        hours = {}
        for i, d in enumerate(days):
            hours[d] = cols[i].number_input(d[:3].capitalize(), min_value=0, max_value=24, step=1, value=0)
            
        notes = st.text_area("Notes", "Entry inserted by Admin")
        
        if st.form_submit_button("✅ Save & Approve"):
            if not sel_task:
                st.error("Please select a task.")
            elif sum(hours.values()) == 0:
                st.warning("Total hours is 0.")
            else:
                data = {
                    "target_user_id": sel_emp,
                    "project_id": sel_proj,
                    "task_id": sel_task,
                    "week_start_date": week_start_input,
                    "notes": notes,
                    **hours
                }
                try:
                    mq.create_admin_timesheet_entry(data, admin_user_id)
                    st.success("Entry Created and Approved!")
                    if "show_admin_entry_dialog" in st.session_state:
                        del st.session_state["show_admin_entry_dialog"]
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# ========================================================
# Main Render
# ========================================================

def render(user, is_admin=False):
    c1, c2 = st.columns([3, 1])
    c1.subheader("Pending & Submitted Timesheets")
    
    # Refresh / Admin Action Buttons
    with c2:
        rc1, rc2 = st.columns([1, 1])
        if rc1.button("🔄 Refresh"):
            reset_dialog_state()
            st.rerun()
        
        # --- NEW BUTTON FOR ADMIN ---
        if is_admin:
            if rc2.button("➕ Insert Entry"):
                clear_other_dialogs("show_admin_entry_dialog")
                st.session_state.show_admin_entry_dialog = True
                st.rerun()

    # Handle Admin Dialog Trigger
    if st.session_state.get("show_admin_entry_dialog"):
        admin_insert_entry_dialog(user['user_id'])

    # Determine Role ID robustly
    role_id = user.get('role_id')
    if role_id is None:
        if user.get('role') == 'admin': 
            role_id = ROLE_ID_ADMIN
        elif user.get('role') == 'dept_manager': 
            role_id = ROLE_ID_DEPT_MANAGER
        else: 
            role_id = ROLE_ID_PROJECT_MANAGER

    # Fetch entries (SQL should filter, but we will double check)
    entries = mq.fetch_submitted_weekly_entries(user['user_id'], role_id)
    
    # --- Strict Logic: Fetch Allowed Projects for this User ---
    allowed_projects = mq.fetch_approver_projects(user['user_id'], is_admin)
    allowed_project_names = [p['project_name'] for p in allowed_projects]
    
    if not entries:
        st.info("No pending timesheets.")
    else:
        df = pd.DataFrame(entries)
        
        # STRICT FILTER: Ensure we only show allowed projects
        if not is_admin:
            df = df[df['project_name'].isin(allowed_project_names)]
            
        if df.empty:
            st.info("No pending timesheets for your assigned projects.")
            return

        # --- Filters Section (FIXED LAYOUT) ---
        fc1, fc2, fc3 = st.columns(3)
        
        unique_emps = sorted(df["employee_name"].unique().tolist())
        
        emp_filter = fc1.selectbox(
            "Employee", 
            ["All"] + unique_emps, 
            key="approvals_emp_filter", 
            on_change=reset_dialog_state
        )
        
        unique_visible_projects = sorted(df["project_name"].unique().tolist())
        proj_filter = fc2.selectbox(
            "Project", 
            ["All"] + unique_visible_projects, 
            key="approvals_proj_filter",
            on_change=reset_dialog_state
        )
        
        status_filter = fc3.selectbox(
            "Status", 
            ["All", "draft", "submitted", "approved", "rejected"], 
            key="approvals_status_filter",
            on_change=reset_dialog_state
        )
        
        # Apply UI Filters
        filtered = df.copy()
        if emp_filter != "All": filtered = filtered[filtered["employee_name"] == emp_filter]
        if proj_filter != "All": filtered = filtered[filtered["project_name"] == proj_filter]
        if status_filter != "All": filtered = filtered[filtered["status"] == status_filter]

        if filtered.empty:
            st.warning("No matches found.")
        else:
            if is_admin:
                cols = st.columns([3, 3, 2, 2, 1.5, 1.5, 1])
                headers = ["Employee", "Project / Task", "Week", "Hrs", "Approve", "Reject", "Edit"]
            else:
                cols = st.columns([3, 3, 2, 2, 2, 2])
                headers = ["Employee", "Project / Task", "Week", "Hrs", "Approve", "Reject"]
                
            for c, h in zip(cols, headers): c.write(f"**{h}**")

            for row in filtered.to_dict("records"):
                if is_admin:
                    c = st.columns([3, 3, 2, 2, 1.5, 1.5, 1])
                else:
                    c = st.columns([3, 3, 2, 2, 2, 2])
                    
                c[0].write(row['employee_name'])
                c[1].write(f"{row['project_name']} / {row['task_name'] or '--'}")
                c[2].write(str(row['week_start_date']))
                c[3].write(f"{row['total_hours']:.2f}")

                if row["status"] == "approved":
                    c[4].success("Approved")
                elif row["status"] == "rejected":
                    c[5].error("Rejected")
                else:
                    if c[4].button("✅", key=f"app_{row['entry_id']}"):
                        mq.update_entry_status(row['entry_id'], user['user_id'], 'approved')
                        st.rerun()
                    if c[5].button("❌", key=f"rej_{row['entry_id']}"):
                        clear_other_dialogs("reject_entry_info")
                        st.session_state.reject_entry_info = row
                        st.rerun()
                
                if is_admin:
                    if c[6].button("✏️", key=f"adm_edit_{row['entry_id']}"):
                        clear_other_dialogs("edit_entry_info")
                        st.session_state.edit_entry_info = row
                        st.rerun()

                        