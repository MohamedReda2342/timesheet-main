# ./utils/state_helpers.py
import streamlit as st

def clear_other_dialogs(current_key):
    """
    Clears other dialog keys from session state to prevent 
    'Only one dialog is allowed' errors in Streamlit.
    """
    dialog_keys = [
        "show_assignment_wizard", 
        "show_task_dialog", 
        "manage_assign_info", 
        "view_task_info", 
        "delete_task_info", 
        "reject_entry_info",
        "edit_assignment_info",
        "delete_def_info",
        "view_assign",
        "edit_assign",
        "del_assign",
        # Project Admin Keys
        "show_project_dialog",
        "view_project_info",
        "delete_project_info",
        "edit_user_info",
        "delete_user_info",
        # Task Type Keys (Updated)
        "show_type_dialog" 
    ]
    
    for key in dialog_keys:
        if key != current_key and key in st.session_state:
            del st.session_state[key]