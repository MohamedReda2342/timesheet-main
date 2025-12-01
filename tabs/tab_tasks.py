# ./tabs/tab_tasks.py
import streamlit as st
from utils import manager_queries as mq
from utils.state_helpers import clear_other_dialogs

@st.dialog("Task Form")
def task_form_dialog(task_id, user_id):
    task = mq.get_task(task_id) if task_id else {}
    is_edit = bool(task_id)
    
    st.subheader(f"{'Edit' if is_edit else 'Add'} Task Definition")
    
    with st.form("task_form"):
        projects = mq.fetch_approver_projects(user_id)
        task_types = mq.fetch_task_types()
        
        proj_opts = {p['project_id']: p['project_name'] for p in projects}
        curr_proj = task.get('project_id')
        idx_proj = list(proj_opts.keys()).index(curr_proj) if curr_proj in proj_opts else 0
        sel_proj = st.selectbox("Project", options=proj_opts.keys(), format_func=lambda x: proj_opts[x], index=idx_proj)
        
        name = st.text_input("Task Name", value=task.get('task_name', ''))
        
        type_opts = {t['TaskTypeId']: t['TaskTypeName'] for t in task_types}
        curr_type = task.get('TaskTypeId')
        idx_type = list(type_opts.keys()).index(curr_type) if curr_type in type_opts else 0
        sel_type = st.selectbox("Task Type", options=type_opts.keys(), format_func=lambda x: type_opts[x], index=idx_type)
        
        if st.form_submit_button("💾 Save Task Definition"):
            if not name:
                st.error("Task Name is required.")
            else:
                data = {
                    "task_id": task_id,
                    "project_id": sel_proj,
                    "task_name": name,
                    "TaskTypeId": sel_type,
                    "created_by": user_id
                }
                mq.upsert_task(data)
                st.success("Task saved successfully!")
                
                # CLOSE DIALOG MANUALLY
                if "show_task_dialog" in st.session_state:
                    del st.session_state["show_task_dialog"]
                if "edit_task_id" in st.session_state:
                    del st.session_state["edit_task_id"]
                    
                st.rerun()

@st.dialog("Delete Task Definition")
def confirm_delete_dialog(task):
    st.warning(f"Delete task **{task['task_name']}**?")
    st.error("⚠️ Deleting this task will remove ALL employee assignments linked to it.")
    col1, col2 = st.columns(2)
    if col1.button("Yes, Delete", type="primary"):
        try:
            mq.delete_task(task['task_id'])
            st.success("Task deleted.")
            
            # CLOSE DIALOG MANUALLY
            if "delete_def_info" in st.session_state:
                del st.session_state["delete_def_info"]
                
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")
    if col2.button("Cancel"):
        if "delete_def_info" in st.session_state:
            del st.session_state["delete_def_info"]
        st.rerun()

def render(user):
    c1, c2 = st.columns([3, 1])
    c1.subheader("Task Definitions")
    
    if c2.button("➕ Create New Task", type="primary", use_container_width=True):
        clear_other_dialogs("show_task_dialog")
        st.session_state.edit_task_id = None
        st.session_state.show_task_dialog = True
        st.rerun() # Force rerun to update state immediately

    tasks = mq.get_tasks_for_manager(user['user_id'])
    
    if not tasks:
        st.info("No tasks defined.")
    else:
        cols = st.columns([2, 2, 2, 1, 0.5, 0.5])
        headers = ["Project", "Task Name", "Type", "Created", "Edit", "Del"]
        for c, h in zip(cols, headers): c.write(f"**{h}**")

        for t in tasks:
            c = st.columns([2, 2, 2, 1, 0.5, 0.5])
            c[0].write(t['project_name'])
            c[1].write(t['task_name'])
            c[2].write(t['TaskTypeName'] or "-")
            c[3].write("---") 

            if c[4].button("✏️", key=f"edt_{t['task_id']}"):
                clear_other_dialogs("show_task_dialog")
                st.session_state.edit_task_id = t['task_id']
                st.session_state.show_task_dialog = True
                st.rerun()
                
            if c[5].button("🗑️", key=f"del_def_{t['task_id']}"):
                clear_other_dialogs("delete_def_info")
                st.session_state.delete_def_info = t
                st.rerun()