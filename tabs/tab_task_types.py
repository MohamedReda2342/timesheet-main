# ./tabs/tab_task_types.py
import streamlit as st
from lib import admin_queries as aq
from utils.state_helpers import clear_other_dialogs

@st.dialog("Task Type Form")
def task_type_dialog(type_id=None):
    is_edit = bool(type_id)
    current_data = aq.get_task_type(type_id) if type_id else {}
    
    st.subheader(f"{'Edit' if is_edit else 'Add'} Task Type")
    
    # Fetch Departments for Dropdown
    departments = aq.fetch_departments()
    dep_opts = {d['DepId']: d['DepName'] for d in departments}
    # Add a "None/Global" option if you want Task Types to be optional
    # dep_opts[None] = "Global / No Department"

    with st.form("task_type_form"):
        name = st.text_input("Task Type Name", value=current_data.get("TaskTypeName", ""))
        
        # Department Selection
        curr_dep = current_data.get("DepId")
        # Handle index finding safely
        if curr_dep in dep_opts:
            idx = list(dep_opts.keys()).index(curr_dep)
        else:
            idx = 0
            
        selected_dep_id = st.selectbox(
            "Department", 
            options=dep_opts.keys(), 
            format_func=lambda x: dep_opts[x],
            index=idx,
            help="Link this Task Type to a specific Department."
        )

        if st.form_submit_button("💾 Save"):
            if not name:
                st.error("Task Type Name is required.")
            else:
                try:
                    # Pass selected_dep_id to upsert
                    aq.upsert_task_type(type_id, name, selected_dep_id)
                    st.success("Saved successfully!")
                    
                    if "show_type_dialog" in st.session_state:
                        del st.session_state["show_type_dialog"]
                    if "edit_type_id" in st.session_state:
                        del st.session_state["edit_type_id"]
                        
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving: {e}")

def render():
    col1, col2 = st.columns([3, 1])
    col1.subheader("Manage Task Types")
    
    with col2:
        if st.button("➕ New Task Type", type="primary", use_container_width=True):
            clear_other_dialogs("show_type_dialog")
            st.session_state.edit_type_id = None
            st.session_state.show_type_dialog = True
            st.rerun()

    types = aq.fetch_task_types()
    
    if not types:
        st.info("No task types found.")
    else:
        # Added Department Column
        cols = st.columns([1, 2, 2, 1])
        cols[0].write("**ID**")
        cols[1].write("**Type Name**")
        cols[2].write("**Department**")
        cols[3].write("**Edit**")
        
        for t in types:
            c = st.columns([1, 2, 2, 1])
            c[0].write(t['TaskTypeId'])
            c[1].write(t['TaskTypeName'])
            c[2].write(t['DepName'] or "Global") # Handle NULLs if any
            
            if c[3].button("✏️", key=f"edt_typ_{t['TaskTypeId']}"):
                clear_other_dialogs("show_type_dialog")
                st.session_state.edit_type_id = t['TaskTypeId']
                st.session_state.show_type_dialog = True
                st.rerun()