# ./tabs/tab_tasks.py
import streamlit as st
from utils import manager_queries as mq
from utils.state_helpers import clear_other_dialogs

@st.dialog("Task Form")
def task_form_dialog(task_id, user_id):
    task = mq.get_task(task_id) if task_id else {}
    is_edit = bool(task_id)
    
    st.subheader(f"{'Edit' if is_edit else 'Add'} Global Task")
    
    with st.form("task_form"):
        name = st.text_input("Task Name", value=task.get('task_name', ''))
        
        # Fetch ALL task types (Manager creating a global task might want to see all options)
        # Or pass None to see everything
        task_types = mq.fetch_task_types(dep_id_filter=None)
        
        if not task_types:
            st.error("No Task Types found.")
            st.stop()

        # Update Display to include Department Name
        type_opts = {
            t['TaskTypeId']: f"{t['TaskTypeName']} - {t['DepName'] or 'Global'}" 
            for t in task_types
        }
        curr_type = task.get('TaskTypeId')
        idx_type = list(type_opts.keys()).index(curr_type) if curr_type in type_opts else 0
        sel_type = st.selectbox("Task Type", options=type_opts.keys(), format_func=lambda x: type_opts[x], index=idx_type)


        if st.form_submit_button("💾 Save Task Definition"):
            if not name:
                st.error("Task Name is required.")
            else:
                data = {
                    "task_id": task_id,
                    "task_name": name,
                    "TaskTypeId": sel_type,
                    "created_by": user_id
                }
                mq.upsert_task(data)
                st.success("Task saved successfully!")
                
                # Close dialog
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
    c1.subheader("Global Task Definitions")
    
    if c2.button("➕ Create New Task", type="primary", use_container_width=True):
        clear_other_dialogs("show_task_dialog")
        st.session_state.edit_task_id = None
        st.session_state.show_task_dialog = True
        st.rerun() # Force rerun to update state immediately

    tasks = mq.get_tasks_for_manager(user['user_id'])
    
    if not tasks:
        st.info("No tasks defined.")
    else:
        # Columns: Name, Type, Edit, Del
        cols = st.columns([5, 3, 0.5, 0.5])
        headers = ["Task Name", "Type", "Edit", "Del"]
        for c, h in zip(cols, headers): c.write(f"**{h}**")

        for t in tasks:
            c = st.columns([5, 3, 0.5, 0.5])
            c[0].write(t['task_name'])
            c[1].write(t['TaskTypeName'] or "-")

            if c[2].button("✏️", key=f"edt_{t['task_id']}"):
                clear_other_dialogs("show_task_dialog")
                st.session_state.edit_task_id = t['task_id']
                st.session_state.show_task_dialog = True
                st.rerun()
                
            if c[3].button("🗑️", key=f"del_def_{t['task_id']}"):
                clear_other_dialogs("delete_def_info")
                st.session_state.delete_def_info = t
                st.rerun()