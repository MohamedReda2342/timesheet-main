# ./tabs/tab_task_types.py
import streamlit as st
from lib import admin_queries as aq
from utils.state_helpers import clear_other_dialogs

@st.dialog("Task Type Form")
def task_type_dialog(type_id=None):
    is_edit = bool(type_id)
    # If editing, fetch current data. If adding, empty dict.
    current_data = aq.get_task_type(type_id) if type_id else {}
    
    st.subheader(f"{'Edit' if is_edit else 'Add'} Task Type")
    
    with st.form("task_type_form"):
        name = st.text_input("Task Type Name", value=current_data.get("TaskTypeName", ""))
        
        if st.form_submit_button("💾 Save"):
            if not name:
                st.error("Name is required.")
            else:
                try:
                    aq.upsert_task_type(type_id, name)
                    st.success("Saved!")
                    
                    # Close dialog
                    if "show_type_dialog" in st.session_state:
                        del st.session_state["show_type_dialog"]
                    if "edit_type_id" in st.session_state:
                        del st.session_state["edit_type_id"]
                        
                    st.rerun()
                except Exception as e:
                    st.error(f"Error saving: {e}")

def render():
    c1, c2 = st.columns([3, 1])
    c1.subheader("Task Types")
    
    if c2.button("➕ New Task Type", type="primary", use_container_width=True):
        clear_other_dialogs("show_type_dialog")
        st.session_state.edit_type_id = None
        st.session_state.show_type_dialog = True
        st.rerun()

    types = aq.fetch_task_types()
    
    if not types:
        st.info("No task types found.")
    else:
        # Updated Column Structure: No Delete
        cols = st.columns([1, 3, 1])
        cols[0].write("**ID**")
        cols[1].write("**Type Name**")
        cols[2].write("**Edit**")
        
        for t in types:
            c = st.columns([1, 3, 1])
            c[0].write(t['TaskTypeId'])
            c[1].write(t['TaskTypeName'])
            
            if c[2].button("✏️", key=f"edt_typ_{t['TaskTypeId']}"):
                clear_other_dialogs("show_type_dialog")
                st.session_state.edit_type_id = t['TaskTypeId']
                st.session_state.show_type_dialog = True
                st.rerun()