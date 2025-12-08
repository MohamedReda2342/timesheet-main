# ./utils/state_helpers.py
import streamlit as st

def get_dialog_keys():
    """Returns the list of all dialog keys used in the app."""
    return [
        # Assignments
        "show_assignment_wizard", 
        "view_assign",
        "edit_assign",
        "del_assign",
        
        # Approvals
        "reject_entry_info",
        "edit_entry_info", # Added this
        
        # Tasks
        "show_task_dialog", 
        "edit_task_id", 
        "delete_def_info",
        
        # Projects
        "show_project_dialog",
        "edit_project_id", 
        "view_project_info",
        "delete_project_info",
        
        # Task Types
        "show_type_dialog",
        "edit_type_id"
    ]

def reset_dialog_state():
    """
    Force clears ALL dialog keys. 
    Used when navigating between pages to prevent 'sticky' modals.
    """
    keys = get_dialog_keys()
    for key in keys:
        if key in st.session_state:
            del st.session_state[key]

def clear_other_dialogs(current_key):
    """
    Clears other dialog keys from session state to prevent 
    'Only one dialog is allowed' errors in Streamlit.
    """
    keys = get_dialog_keys()
    for key in keys:
        if key != current_key and key in st.session_state:
            del st.session_state[key]

def track_page_visit(page_name):
    """
    Call this at the top of every page.
    If the page_name has changed (user navigated), it clears all dialog states.
    """
    if "current_page" not in st.session_state:
        st.session_state["current_page"] = page_name
        return

    if st.session_state["current_page"] != page_name:
        reset_dialog_state()
        st.session_state["current_page"] = page_name