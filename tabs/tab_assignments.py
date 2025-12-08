# ./tabs/tab_assignments.py
import streamlit as st
from datetime import date
from utils import manager_queries as mq
from utils.state_helpers import clear_other_dialogs

# ==================================================
# Dialogs
# ==================================================

@st.dialog("➕ New Assignment")
def assignment_wizard_dialog(user_id, is_admin):
    st.subheader("Add New Assignment")
    
    # Step 1: Project (Context for the assignment)
    # Passed is_admin to fetch ALL projects if admin
    projects = mq.fetch_approver_projects(user_id, is_admin)
    if not projects:
        st.error("No projects found.")
        return

    proj_opts = {p['project_id']: p['project_name'] for p in projects}
    sel_proj = st.selectbox("1. Select Project", options=proj_opts.keys(), format_func=lambda x: proj_opts[x])

    # Step 2: Task Type
    task_types = mq.fetch_task_types()
    type_opts = {t['TaskTypeId']: t['TaskTypeName'] for t in task_types}
    sel_type = st.selectbox("2. Select Task Type", options=type_opts.keys(), format_func=lambda x: type_opts[x])
    
    # Step 3: Global Task (Filtered by Type ONLY)
    tasks = mq.fetch_tasks_by_type(sel_type)
    
    if not tasks:
        st.warning("No tasks found for this Task Type.")
        if is_admin:
            st.info("Please create Global Tasks in the **Task Definitions** tab.")
        return

    task_opts = {t['task_id']: t['task_name'] for t in tasks}
    sel_task = st.selectbox("3. Select Task", options=task_opts.keys(), format_func=lambda x: task_opts[x])
    
    # Step 4: Assignment Details
    st.markdown("---")
    st.write("**4. Assignment Details**")
    
    all_emps = mq.get_all_employees()
    emp_opts = {e['EmpId']: f"{e['EmpName']} ({e['SAP_ID']})" for e in all_emps}
    sel_emp = st.selectbox("Employee", options=emp_opts.keys(), format_func=lambda x: emp_opts[x])
    
    c1, c2 = st.columns(2)
    assign_name = c1.text_input("Assignment Role/Name", value="Contributor")
    hrs = c2.number_input("Planned Hours", min_value=0, step=1, value=0)
    
    c3, c4 = st.columns(2)
    start_dt = c3.date_input("Start Date", value=date.today())
    end_dt = c4.date_input("End Date", value=None)
    
    notes = st.text_area("Notes")
    
    if st.button("✅ Create Assignment", type="primary"):
        data = {
            "AssignmentId": None,
            "project_id": sel_proj,
            "task_id": sel_task,
            "EmpId": sel_emp,
            "assignment_name": assign_name,
            "planned_hours": hrs,
            "notes": notes,
            "start_date": start_dt,
            "end_date": end_dt,
            "status": "active"
        }
        mq.upsert_assignment(data)
        st.success("Assignment created!")
        
        # CLOSE DIALOG
        if "show_assignment_wizard" in st.session_state:
            del st.session_state["show_assignment_wizard"]
        st.rerun()

@st.dialog("✏️ Edit Assignment")
def edit_assignment_dialog(assign, user_id, is_admin):
    st.subheader(f"Edit Assignment")
    
    with st.form("edit_assign_form"):
        # 1. Project Selection
        # Passed is_admin to fetch ALL projects if admin
        projects = mq.fetch_approver_projects(user_id, is_admin)
        if not projects:
            st.error("No projects found.")
            st.stop()
            
        proj_opts = {p['project_id']: p['project_name'] for p in projects}
        
        curr_proj = assign.get('project_id')
        idx_proj = list(proj_opts.keys()).index(curr_proj) if curr_proj in proj_opts else 0
        sel_proj = st.selectbox("1. Project", options=proj_opts.keys(), format_func=lambda x: proj_opts[x], index=idx_proj)

        # 2. Task Type Selection
        task_types = mq.fetch_task_types()
        type_opts = {t['TaskTypeId']: t['TaskTypeName'] for t in task_types}
        
        curr_type = assign.get('TaskTypeId')
        idx_type = list(type_opts.keys()).index(curr_type) if curr_type in type_opts else 0
        sel_type = st.selectbox("2. Task Type", options=type_opts.keys(), format_func=lambda x: type_opts[x], index=idx_type)
        
        # 3. Task Selection (Global filtered by Type ONLY)
        tasks = mq.fetch_tasks_by_type(sel_type)
        
        if not tasks:
            st.warning("No tasks found for this Type.")
            st.form_submit_button("Cannot Save (No Task)")
            return 
            
        task_opts = {t['task_id']: t['task_name'] for t in tasks}
        
        curr_task = assign.get('task_id')
        idx_task = list(task_opts.keys()).index(curr_task) if curr_task in task_opts else 0
        sel_task = st.selectbox("3. Task", options=task_opts.keys(), format_func=lambda x: task_opts[x], index=idx_task)

        st.markdown("---")
        
        # 4. Details
        all_emps = mq.get_all_employees()
        emp_opts = {e['EmpId']: f"{e['EmpName']} ({e['SAP_ID']})" for e in all_emps}
        
        curr_emp = assign.get('EmpId')
        idx_emp = list(emp_opts.keys()).index(curr_emp) if curr_emp in emp_opts else 0
        sel_emp = st.selectbox("Employee", options=emp_opts.keys(), format_func=lambda x: emp_opts[x], index=idx_emp)
        
        name = st.text_input("Assignment Name", value=assign.get('assignment_name', ''))
        
        c1, c2 = st.columns(2)
        hrs = c1.number_input("Planned Hours", min_value=0, step=1, value=int(assign.get('planned_hours') or 0))
        status = c2.selectbox("Status", ["active", "completed", "on-hold"], index=["active", "completed", "on-hold"].index(assign.get('status', 'active')))
        
        c3, c4 = st.columns(2)
        start_dt = c3.date_input("Start Date", value=assign.get('start_date') or date.today())
        end_dt = c4.date_input("End Date", value=assign.get('end_date') or None)
        
        notes = st.text_area("Notes", value=assign.get('notes') or "")
        
        if st.form_submit_button("💾 Save Changes"):
            data = {
                "AssignmentId": assign['AssignmentId'],
                "project_id": sel_proj,
                "task_id": sel_task, 
                "EmpId": sel_emp,
                "assignment_name": name,
                "planned_hours": hrs,
                "notes": notes,
                "start_date": start_dt,
                "end_date": end_dt,
                "status": status
            }
            mq.upsert_assignment(data)
            st.success("Updated!")
            
            # CLOSE DIALOG
            if "edit_assign" in st.session_state:
                del st.session_state["edit_assign"]
            st.rerun()

@st.dialog("Delete Assignment")
def confirm_delete_dialog(assign):
    st.warning(f"Delete assignment for **{assign['EmpName']}**?")
    st.caption(f"Task: {assign['task_name']} | Project: {assign['project_name']}")
    col1, col2 = st.columns(2)
    if col1.button("Yes, Delete", type="primary"):
        mq.delete_assignment(assign['AssignmentId'])
        st.success("Deleted.")
        
        if "del_assign" in st.session_state:
            del st.session_state["del_assign"]
        st.rerun()
        
    if col2.button("Cancel"):
        if "del_assign" in st.session_state:
            del st.session_state["del_assign"]
        st.rerun()

@st.dialog("ℹ️ Assignment Details")
def view_assignment_dialog(assign):
    st.subheader(f"📋 Details")
    st.markdown(f"""
    | Field | Value |
    | :--- | :--- |
    | **Project** | {assign['project_name']} |
    | **Task** | {assign['task_name']} |
    | **Type** | {assign['TaskTypeName']} |
    | **Employee** | {assign['EmpName']} (SAP: {assign['SAP_ID']}) |
    | **Role** | {assign['assignment_name'] or '-'} |
    | **Status** | {assign['status']} |
    | **Hours** | {int(assign['planned_hours'] or 0)} |
    | **Dates** | {assign['start_date']} to {assign['end_date'] or 'Ongoing'} |
    | **Notes** | {assign['notes'] or '-'} |
    """)
    if st.button("Close"):
        if "view_assign" in st.session_state:
            del st.session_state["view_assign"]
        st.rerun()

# ==================================================
# Main Render
# ==================================================

def render(user, is_admin):
    c1, c2 = st.columns([3, 1])
    c1.subheader("Project Assignments")
    
    if c2.button("➕ New Assignment", type="primary", use_container_width=True):
        clear_other_dialogs("show_assignment_wizard")
        st.session_state.show_assignment_wizard = True
        st.rerun()

    # Passed is_admin to fetch ALL assignments if admin
    assignments = mq.get_all_assignments_for_manager(user['user_id'], is_admin)
    
    if not assignments:
        st.info("No active assignments found.")
        if is_admin:
            st.markdown("""
            **To get started:**
            1. Define Global Tasks in the **Task Definitions** tab.
            2. Click **➕ New Assignment** to link an Employee to a Task on a Project.
            """)
        else:
             st.markdown("No assignments found.")
    else:  
        cols = st.columns([2, 2, 2, 1, 1, 0.5, 0.5, 0.5])
        headers = ["Employee", "Project", "Task", "Planned Hours", "Status", "View", "Edit", "Del"]
        for c, h in zip(cols, headers): c.write(f"**{h}**")

        for a in assignments:
            c = st.columns([2, 2, 2, 1, 1, 0.5, 0.5, 0.5])
            c[0].write(a['EmpName'])
            c[1].write(a['project_name'])
            c[2].write(a['task_name'])
            c[3].write(f"{int(a['planned_hours'] or 0)}")
            c[4].write(a['status'])
            
            if c[5].button("👁️", key=f"v_{a['AssignmentId']}"):
                clear_other_dialogs("view_assign")
                st.session_state.view_assign = a
                st.rerun()
            
            if c[6].button("✏️", key=f"e_{a['AssignmentId']}"):
                clear_other_dialogs("edit_assign")
                st.session_state.edit_assign = a
                st.rerun()
                
            if c[7].button("🗑️", key=f"d_{a['AssignmentId']}"):
                clear_other_dialogs("del_assign")
                st.session_state.del_assign = a
                st.rerun()